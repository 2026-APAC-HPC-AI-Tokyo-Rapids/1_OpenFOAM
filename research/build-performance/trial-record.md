# 試行から得た判断

この記録は、2026-05 から 2026-07 に workflow と Actions 実行で確認した事項を、現在の意思決定に使える形に整理したものである。数値は共有 runner 上の観測値であり、他環境での性能値ではない。

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
