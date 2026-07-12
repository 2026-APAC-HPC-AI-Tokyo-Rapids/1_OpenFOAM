# 試行から得た判断

この記録は、2026-05 から 2026-07 に workflow と Actions 実行で確認した事項を、現在の意思決定に使える形に整理したものである。性能値の多くは OpenFOAM v2412 の試行であり、現在の v2606 と直接比較できる値ではない。数値は共有 runner 上の観測値であり、他環境での性能値ではない。

## 1. まず再現可能な full build を作る

初期には source の置き場、OpenFOAM の初期化、ADIOS2 / CGAL の version、FFTW の link path、ccache の有無、ログの取り方を順に修正した。full build を成立させるには、単に compiler を選ぶだけでなく、OpenFOAM が期待する ThirdParty の配置と link 時の探索 path を合わせる必要があった。

現在残っている判断は次のとおりである。

- source archive は共有 cache から展開し、展開済み source と生成物は run ごとに作る。
- OpenFOAM の `bashrc` 読み込み中だけ shell の `-e` / `-u` を外す。OpenFOAM 自身の初期化が未定義変数と中間失敗を許容するためである。
- `Allwmake -log` の終了 status を失わないよう `bash -o pipefail` で実行する。失敗した build を成功扱いにしないことを、短い console output より優先する。
- build log は artifact に残す。大量の通常出力を console に流さず、失敗時だけ error を要約する。

## 2. 並列度は 120 を基準にする

30、60、90、120 の `Allwmake -j` を比較した。観測された中央値はそれぞれ 19分46秒、18分21秒、20分17秒、16分26秒だった。少なくともこの比較では、120 が最良であり、60 や 90 へ下げても安定化はしなかった。

したがって現在は `-j 120` を固定している。ただしこれは「120 が常に最速」という一般則ではない。shared runner では I/O と metadata access の競合が大きく、比較回数が少ない設定同士の差は偶然の揺らぎを含む。160 以上は未検証であり、変更するなら複数回の交互実行で評価する。

## 3. queue なし、GNU linker を維持する

Allwmake の queue あり／なしと lld を試した。

- ccache が warm な状態では、queue を導入しても全体時間の利点を確認できなかった。現在は queue なしである。
- Icx から lld を使うために OpenFOAM の link rule を patch し、`--allow-shlib-undefined` も含めて互換性を試した。部分的に成功する run はあったが、その後の full build で link 失敗が再発した。
- GNU ld は full build の成功を継続している。lld を保持するだけの安定した短縮効果は得られなかったため、lld 用 patch は撤去した。

この結論は linker の優劣ではなく、この OpenFOAM version、Icx、Intel MPI、ThirdParty の組合せにおける保守性の判断である。

## 4. ccache は有効だが、全体を支配しない

ccache の warm build では hit 率が約 99.5% である。実コンパイルの再実行を大幅に減らせるため、ccache は残すべきである。

一方で、cache を毎回 tmpfs へコピーする方式はコピー自体に約82秒かかり、中央値は 24分26秒となった。runner 既定の cache storage を使う方式は 16分26秒、事前に tmpfs に置いた cache は 16分09秒だった。後者の差は run 間の揺らぎより小さく、永続 cache を毎回コピーする複雑さを正当化しない。

ccache hit 後にも、dependency generation、directory scan、link、install、短命 process の起動は残る。したがって hit 率だけを見て「build が速いはず」と判断してはいけない。

## 5. 時間の揺らぎは build の外部条件として扱う

同じ 120 並列、同じ source、同程度の ccache hit 率でも、Allwmake の build 時間は約14分台から23分台まで変動した。

直近の比較では、通常 run `28992544864` の job 全体は 15分47秒、`Build OpenFOAM` は 14分43秒だった。一方、同じ120並列の run `29015734524` は job 全体 24分17秒、build は 23分09秒だった。checkout、展開、archive、upload の差は小さく、増加した約8分半のほぼ全てが build step にある。ccache hit 率はいずれも 99.50% だった。

この比較だけで原因を断定はできないが、workflow の待機や source download、cache miss では説明しにくい。共有ファイルシステム、compiler / header の参照、ccache storage など、tmpfs の外に残る共有資源の競合として扱うのが妥当である。

結論として、単一 run の wall time を改善効果の証拠にしない。最適化候補は同条件で複数回測り、step 時間、log の工程時刻、ccache 状態を併記する。

## 6. v2606 への更新と build path の正規化

OpenFOAM v2606 は公式 source archive と ThirdParty archive から取得し、既存 patch の適用箇所を確認した。ADIOS2 2.12.1 は v2606 の既定になったため専用 patch を削除し、CGAL、Icx、timestamp の patch は v2606 の source に合わせて更新した。full build が成功したことまで確認している。

version 付き source directory をそのまま使うと、`CCACHE_BASEDIR` から見た相対 path に OpenFOAM version が残り、version 更新時に cache key が分離する。そこで展開後の directory を `OpenFOAM` と `ThirdParty` に正規化した。v2606 の `bashrc` と ThirdParty 探索がこの配置で正しく初期化されることを確認したうえで採用した。

統計を累積値と取り違えないよう、Allwmake の直前で `ccache --zero-stats` を実行する。v2606 の warm build `29069152863` は 4,789 cacheable call のうち 4,688 hit、101 miss で、hit 率は 97.89% だった。Allwmake は約27分51秒であり、約16分だった v2412 の速い run より長い。ただし call 数の増加は約0.7%に留まり、v2606 の workload 増加だけでは差を説明できない。ThirdParty の増加に加え、libraries と applications が v2412 の遅い run とほぼ同じ時間になっているため、共有環境の変動を含むと考えるのが妥当である。

## 7. build archive の再利用は明示的に選ぶ

full build の成果物を run number 名の `tar.zst` として共有領域へ保存し、後続の `run` job が常に現在の run number だけを参照できる構成にした。ここで述べる `skip_build` と `[skip-build]` は当時の workflow における指定である。現在は手動実行の `require_build`、または push の `[require-build]` でフルビルドを明示する。

workflow は第一親を1コミットずつ遡り、成功済みの実ビルドと対応する archive を探す。互換性を差分から推測しないため、判断基準は単純だが、指定側が source、patch、compiler設定の互換性に責任を持つ。

push run `29077779599` では、当時の `[skip-build]` を認識し、再利用だけを行った直前の run を飛ばして実ビルドの run number `85` を選んだ。Download、Prepare、Extract、Build、Archive はすべて skip され、現在の run number 名へのハードリンク作成と後続の `run` job が成功した。
