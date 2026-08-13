# DIC cell-gatherとPCG loop fusionの統合実験

## 目的と対象範囲

source levelの候補を一つずつ分離して評価し、4 nodeで事前に定めた1%の前進基準を
単独で超えた次の2変更だけを統合した。

- DIC前処理のforward/backward substitutionをcell単位のgatherへ変更する。
- PCGのresidual更新とL1 norm集計を同一loopへ統合する。

比較した候補と判断は次のとおりである。

| 候補 | 測定結果 | 判断 |
|---|---:|---|
| DIC cell-gather | 4 node平均 8.1490 M FVOPS | 統合候補 |
| PCG loop fusion | 4 node平均 8.1490 M FVOPS | 統合候補 |
| symmetric `Amul` CSR | 1 node平均 1.5803 M FVOPS | baseline範囲未満のため棄却 |
| DIC + PCG | 4 node平均 8.4573 M FVOPS | 採用 |

OpenFOAM source commit `b6164259aca1a06da1352efc2b31bd6b43fe19e7`は、変更前の
source baselineにDICとPCGの2変更だけを適用した実験用commitである。最終的には
source repositoryの`master`へmerge commit `7d59c05ec`として統合した。性能低下が
2回再現したsymmetric `Amul` CSRは含めていない。Workload、DP/Int64 build、toolchain、
partition、rank placement、MPI設定、公式parserは変更していない。

## 実装内容

DICではstableなlosort groupを使ってforward substitutionをupper cellごとに集約し、
owner-start groupを逆順に走査してbackward substitutionをlower cellごとに集約する。
依存方向とcell内のoperand順は維持する。20,000件の合法なLDU addressingを用いた
`-O0`および`-O3`の事前試験では、変更前後の結果がbit単位で一致した。

PCGでは`psi`とresidualを更新するloopにresidualのL1集計を統合し、PCG iterationごとの
residual array全走査を1回削減する。集計順、`solveScalar`、`sumOp`、communicator、
message tagおよびglobal reduction回数は変えない。Pipelined CGへのalgorithm変更ではない。

## Build来歴と1 nodeの数値検証

利用側commit `a0fba38483c9d4314804f2820da50a1820c399ec`は、combined source branchを
固定して新規buildを要求した。Push Actions `31661914834`はexact source OID
`b6164259...`をcheckoutし、build archive #328を公開した。

- Size：476,470,983 byte
- SHA-256：`2849a7985b485360a532c301920d67c24632cb879df276444b84d68381a5e3c2`

1 node qualificationのrun `r-68fc530086528eeeb9c77bbd7efc0acc`は公式`VALID`で、
1.7834 M FVOPS、35.888 s/stepだった。`End`を検出し、NaN/Infなし、5/5 step、
10/10 pressure solveを完了し、全solveが正確に321 iterationだった。Pressure residual列は
baselineと字句単位で完全一致した。Workload manifestとmesh-cache manifestにも差がなく、
120件のrank/CPU placement recordもすべて一致した。

## 4 node反復測定

次の2 runはexact build archive #328をhardlinkで再利用しており、OpenFOAMを再buildして
いない。

| Actions | Run ID | FVOPS_trim | s/step | 公式判定 |
|---|---|---:|---:|---|
| `31662737506` | `r-1ec10cd2d04f8ac54f7a2c42938a10c7` | 8.4824 M | 7.545 | VALID |
| `31662737579` | `r-765790d354b02123a1b337e253635d44` | 8.4321 M | 7.590 | VALID |

両runとも5/5 stepと10/10 solveを完了し、全solveが321 iteration、`End`あり、
NaN/Infなしだった。Residual軌跡は同じlayoutのbaselineと一致した。Placement recordは
各run 448件で、4 nodeそれぞれ112 rank、global rank 0--447、local rank 0--111、
追跡対象のbalanced singleton CPU affinityと一致した。

Preparation PJMとsolver PJMはすべてterminalである。公式result、manifest、固定run bundleは
home serverへcopyしてhashを検証した後、GitHub上の一時artifactを削除した。実験由来の
PJM job、build directory、provision directoryは残っていない。

## 結論

確立済みの4 node baselineは5 runのmedianが7.9900 M、範囲が7.9850--8.0050 Mである。
Combinedの2 run平均は8.4573 Mで、baseline medianより5.85%高く、両sampleともbaselineの
全範囲を上回った。また、DICまたはPCGを単独適用した2 run平均8.1490 Mより3.78%高い。
したがって2変更の効果は共存し、combined buildは単独候補より明確に優れる。

DIC cell-gatherとPCG loop fusionの組合せを採用する。数値不変性、exact build provenance、
4 nodeでの反復改善、artifact archivalおよびcleanupはすべてE2E完了条件を満たした。
利用側`main`はsource repositoryの一時的なexperiment branchではなく、統合後の`master`を
checkoutして新規buildする。
