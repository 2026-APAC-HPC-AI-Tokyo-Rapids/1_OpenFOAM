# genkai.yml全面改稿以降の設計履歴

## 対象範囲

2026年6月の`genkai.yml`全面改稿以降を対象とする。最終的なworkflowだけを見ると分からない、採用理由、失敗実験、撤去した構成を記録する。

## 現在の設計

| 項目 | 現在の方針 | 理由 |
|---|---|---|
| Compiler | Intel oneAPI `mpiicx` / `mpiicpx` | 実行環境とIntel MPIへ合わせる |
| Linker | GNU ld | lldではOpenFOAMのlink ruleと共有library依存を解決できなかった |
| Build directory | `/dev/shm`上の`mktemp` | source、dependency、object、link出力をLustreから隔離する |
| Parallelism | 120 | 30、60、90、120の比較で中央値が最短だった |
| Allwmake queue | 無効 | ccache warm時は二段階走査と同期点の固定費が勝った |
| ccache storage | server既定の`/fast` | tmpfsコピーは総時間を悪化させた |
| ccache temp | build用tmpfs配下 | 32MBの`/run/user`ではなく大容量の`/dev/shm`を使う |
| ccache path normalization | `CCACHE_BASEDIR` | runごとに変わる`mktemp`パスを正規化する |
| Source archive | 共有永続cache | downloadを毎回繰り返さない |
| Build log | artifact | 膨大なAllwmake出力でActions画面を壊さない |
| Profiling | timestamp、`perf stat`、frame-pointer `perf record`、`time -v` | 実行時間への有意な影響がなく、artifactも約28MBだった |

## Workflow構造の整理

全面改稿では、肥大化していた単一build stepを次の責務へ分割した。

1. Checkout
2. Source archive download
3. `/dev/shm` build directory作成
4. Source展開とpatch適用
5. OpenFOAM build
6. Log artifact upload
7. Cleanup

環境変数は可能な限りjobの`env:`へ集約し、実行時に確定する`OPENFOAM_BUILD_TMPDIR`、`CCACHE_BASEDIR`、`CCACHE_TEMPDIR`だけを`GITHUB_ENV`へ書き出す。変数名は実体を表すものへ整理し、不要になったarchive temporary path、build symlink、独自`CCACHE_DIR`指定を削除した。

## Source取得とpatch

- URL全体を変数化せず、URL中のversion部分だけを環境変数で置換する。
- `wget --no-clobber`で既存archiveを再利用し、独自download関数やtemporary archive pathを持たない。
- OpenFOAMとThirdPartyをloopで展開する。
- `patches/*.patch`を全件適用し、workflowへpatch名を列挙しない。
- ADIOS2 2.12.1、CGAL 6.1.1、Icx preprocessor対応をpatchとして追跡する。

追加・削除したpatchはGitの差分だけで管理でき、workflow側の変更は不要になった。

## tmpfs buildとccache

毎回変わるbuild pathを同一pathへ見せるsymlink案を検討したが、`CCACHE_BASEDIR`で目的を満たせるため廃止した。`CCACHE_DIR`はserver設定を尊重し、workflowから削除した。

serverのccache設定は次の特徴を持つ。

- cache directory: `/fast/pj26000080/ccache_cache_dir`
- max size: 50GB
- direct mode: enabled
- inode cache: enabled
- temporary directory既定値: `/run/user/18176/ccache-tmp`

`/run/user/18176`は32MBのtmpfs、`/dev/shm`は約504GBだったため、temporary directoryだけをbuild用`/dev/shm`配下へ変更した。

ccache cache全体をtmpfsへコピーする実験では、毎回のコピーに約82秒かかり、総時間中央値は24分26秒へ悪化した。コピー済みcacheでも16分09秒で、server cacheの16分26秒に対して1.7%改善に留まった。このためstorageはserver既定を維持している。

## Allwmake log

Allwmakeのstdoutは20MB、12万行規模になり、Actions画面へ直接流すとブラウザ操作に支障が出る。現在は`-s -log=FILE`を使い、stdoutを`/dev/null`へ送り、失敗時だけerror patternをstderrへ抽出する。

`-log`内部の`tee`でbuild失敗を失わないよう、Allwmakeを`bash -o pipefail`で実行する。ログはartifactへ保存し、run IDとattemptで識別する。

profilingでは`AllwmakeParseArguments`へ`awk`を挟み、全行へ秒単位timestampを付けた。実測で有意な遅延がなく、工程時間の分解に有効なため維持している。

## `-q`の検証

`-q`はobject生成を集約した後にlinkを行うため、cold buildでは有効でも、ccache warm時には次の固定費が目立つ。

- 全directoryの事前走査
- object phaseとlink phaseの同期点
- 第二passの依存確認
- 大量の短命processとmetadata access

GNU ldで比較した結果、`-q`ありは14分53秒、`-q`なしは12分50秒と14分40秒だった。共有ノードの変動は大きいが、単純で平均も速い`-q`なしを採用した。

## lldの検証

Intel CompilerはLLVM系だが、OpenFOAM-v2412のIcx link ruleはGNU ld前提だった。次の段階まで試したが採用できなかった。

1. `-fuse-ld=lld`の導入
2. lld非対応の`--add-needed`をIcx ruleから除去
3. `--allow-shlib-undefined`の追加
4. queueあり・なし双方の確認

`-lfiniteVolume`等のlibrary探索失敗と、Pstream / MPI関連の大量のundefined symbolが発生した。完全対応にはlibrary依存順序とlink ruleの保守が必要で、速度効果を確認する前に変更範囲が大きくなったためGNU ldへ戻した。

## 並列数の検証

| Parallelism | Median |
|---:|---:|
| 30 | 19分46秒 |
| 60 | 18分21秒 |
| 90 | 20分17秒 |
| 120 | 16分26秒 |

120は60より約10.4%速かった。System CPUは増加したが、Lustre待ちを隠す効果が勝ったため120を採用した。

## Profilingの試行

段階的に次を試した。

1. `/usr/bin/time -v`
2. 5秒intervalの`perf stat -d`
3. 9Hz、call graphなしの`perf record`
4. 1Hz、DWARF call graph
5. 1Hz、frame-pointer call graph
6. `pidstat`

DWARF方式はrawデータ735MBとなり、継続利用には過大だった。frame-pointer方式はraw約138MB、artifact圧縮後約28MBで、wall timeへの有意な影響もなかったため維持した。`pidstat`は他userのprocessが混入するか、親perf processしか追跡できず、有効な追加情報を得られなかったため撤去した。

profilingから、実コンパイルよりLustre clientのpage faultとmetadata lockが支配的であることが分かった。詳細は[調査結果](findings.md)を参照する。

## 得られた原則

- ccache hit率だけではbuildが速いとは限らない。dependency生成、link、install、file scanは残る。
- tmpfs化は実際にそのpathを参照する処理だけに効く。toolchainやcacheがLustre上ならI/Oは残る。
- 多数の小fileを個別に扱うより、単一archiveで復元する方がLustreに適する可能性が高い。
- 共有ノードでは単発runを信用せず、反復と逆順実行で時間帯の偏りを抑える。
- 高速化施策は同時投入せず、queue、linker、parallelism、cache placementを個別にA/Bする。
- workflowの単純さも性能と同じ評価対象にする。効果が誤差範囲の構成は残さない。
