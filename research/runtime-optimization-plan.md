# cavity3D-64M runtime最適化研究計画

## 目的

規定された演算内容や精度を変更せず、玄界上の公式5 step `cavity3D-64M`
workloadを最適化する。主要な結果は `benchmark/parse_result.sh` が出力する公式の
`FVOPS_trim` とする。採用するすべての結果は `STATUS: VALID` であり、Actions、
PJM、raw run、BigQuery、artifactに至る完全なprovenance pathを保持しなければならない。

当初の対象はinput decomposition、MPI rank placement、Intel MPIおよびOpenFOAMの
runtime設定、cell orderingとする。source-levelのsolver変更は、これら低コストの
軸を調べ尽くすまで保留する。

## 確立済みのbaseline

現在のworkflowは1、2、または4 nodeを割り当てるが、meshは常に120個のScotch
domainへ分割する。比較可能な最新のvalid結果は次のとおりである。

| Node数 | 総rank数 | Rank/node | FVOPS_trim | s/step | Run ID |
|---:|---:|---:|---:|---:|---|
| 1 | 120 | 120 | 1.6398 M | 39.030 | `r-c4bb4bb3c51a6a6724aa7177ea1d01e6` |
| 2 | 120 | 60 | 3.1718 M | 20.177 | `r-fef72f7255e44a077f5fa2b1b115b0df` |
| 4 | 120 | 30 | 4.9488 M | 12.932 | `r-c2aef4bc0f5dd083a8790751af269342` |

PR 12のmerge後に実施した1 node run（Actions run `31624279389`）では、独立に
1.6270 M FVOPSを得てartifact archivalまで完了した。1.6392 Mのrepeat
（`r-efdfb255f9d7c78e7eb9c7df59bcab5c`）は以前の結果との差が0.04%未満であり、
merge後のrunは約0.8%低かった。これはnoiseの初期的な目安にすぎず、確定した
noise floorではない。

現在の120-way Scotch partitionは、最大cell imbalanceが約1.0%、unique interface
faceが2,650,146、rank pairが633、平均neighbour/rankが10.55、最大neighbourが18で
ある。連続rank placementの場合、inter-node faceは2 nodeで291,222、4 nodeで
578,906となる。

1 nodeでのVTune rank-0 samplingによるreported CPU timeの内訳は、
`DICPreconditioner::precondition`が約45.8%、`lduMatrix::Amul`が26.1%、
`PCG::scalarSolve`が16.4%であり、sampled MPI functionの合計は数%にすぎない。
これは、multi-nodeのcommunication balanceを仮定せず測定しつつ、1 nodeの処理を
memory/locality律速として扱うことを支持する。

## 不変条件とevidenceの管理主体

- workloadを定義する7個のinput fileをbyte単位で同一に保つ。Mesh geometry、5 time
  step、2 pressure corrector、321 PCG iteration、double precision、
  `floatTransfer=0`は変更不可とする。
- source、toolchain、build dependency、または必要なexecutableが変わるまでは、同じ
  OpenFOAM archiveを使用する。Runtime、workflow、decomposition、parser、文書のみの
  変更ではarchiveを再利用する。
- 実験はGitHub Actions経由で実行する。直接SSHはread-onlyとし、完了run、scheduler
  state、cache、diagnosticsの調査に限定する。
- Gitおよびcommit bodyは、追跡対象の設定とその理由を管理する。ActionsおよびPJM
  logは実行経過を、玄界のrun directoryとarchived artifactはraw出力を、BigQueryは
  比較対象の事実を管理する。本書はhypothesis、decision、interpretationを管理する。
- Bench runとprofile runは別の母集団とする。Instrumentationを伴うtimingはcompetition
  scoreに決して使用しない。
- 推測に基づくretry、fallback、locking、補助metadataは追加しない。

## 実験基盤

性能試験の前に、意図せず固定されている120 rankとの結合を、workflow dispatch時に
選択する明示的な実験presetへ置き換える。1つのpresetがnode数、rank数、decomposition、
OpenFOAM switch、Intel MPI override、および任意のrenumberingを完全に定義する。
実効値はprotocol、manifest source、decomposition dictionary、launch argv、placement
capture、metricsへ複写する。

Caseの再利用には次の2 levelがある。

1. 不変な64-million-cell serial `blockMesh` result。
2. 次のcanonical preparation inputをkeyとするdecomposed/ordered case：preparation
   implementation、総rank数、完全なdecomposition dictionary、renumbering dictionary
   （またはnone）、OpenFOAM build identity、workload identity。

各prepared caseは公開後に不変とする。Preparationは、独立した直列実行のActions/PJM
jobのままにする。Solverの失敗によってvalidな再利用可能caseを無効化しない。PJM
solver jobを投入する前に、static testでrank/protocol/decompositionの不一致を拒否する。

最初の実装では本計画に必要なnamed presetだけをsupportし、任意のuser-supplied MPI
environmentやdictionaryは公開しない。

## 段階的な実験

### Phase 0：測定の健全性とnoise

現在のbuildとworkflowでvalidなbench sampleが最低5件得られるまで、変更のない
1-node/120-rank Scotch baselineを再実行する。best、median、minimum、maximum、relative
rangeを記録する。これにより、高価なmulti-node比較の前に測定の安定性と新しいpreset
pathを検証する。

### Phase 1：physical coreを使い切る

Scotchとdefault pinningを使用して次を比較する。

| Preset | Node数 | 総rank数 | Rank/node | 目的 |
|---|---:|---:|---:|---|
| `scotch-1n-120r` | 1 | 120 | 120 | 変更なしのbaseline |
| `scotch-2n-240r` | 2 | 240 | 120 | physical coreをすべて使用 |
| `scotch-4n-480r` | 4 | 480 | 120 | physical coreをすべて使用 |

screeningでは各candidateを2回実行し、4-node candidateが成功した場合は最低5回実行
する。期待する改善は十分に大きいため、結果が悪化またはほぼ同等ならplacement、
transport、partitionの欠陥を示すevidenceとして扱い、次へ進む前に調査する。

### Phase 2：NUMA domainごとに1 coreを予約

4 nodeで480 rankと448 rank（112/node）を比較する。後者では、玄界の8個の15-core
NUMA domainそれぞれでphysical coreを1個空ける。両layoutがpresetの定義どおりである
ことを保証する目的に限って明示的なCPU placementを使用し、この試験にdecomposition
変更を混ぜない。448 rankのmedian公式FVOPSが測定noiseを超えて480を上回る場合にのみ
448 rankを次へ進める。

Quarter-node layoutとSMT rankは当初の対象外とする。公開済みtask dataでは、多数の
physical coreをidleにすると大きく性能が低下し、割り当てnodeは有用性未検証のSMT
tierではなく120個のonline physical CPUを公開しているためである。

### Phase 3：geometricおよびtopology-aware decomposition

最良の4-node rank数で、次のpartitionをscreeningする。

1. Scotch baseline。
2. 直接の`hierarchical` geometric split。
3. Multi-level node-aware geometric split。
4. Multi-level node-then-NUMA-aware geometric split。
5. 純粋なgeometric variantで意味のあるcellまたはinterface imbalanceが生じた場合に
   限り、外側をgeometric node split、内側をScotchとする構成。

480 rankでは、解析的にbalancedな最終grid `(6 8 10)`を使用する。Topology-aware
candidateは、第1 levelを4 node、第2 levelをnodeごとの8 NUMA domain、第3 levelを
NUMA domainごとの15 rankへ対応させる。

| Node数 | Node grid | NUMA grid/node | Rank grid/NUMA | 最終grid |
|---:|---|---|---|---|
| 1 | `(1 1 1)` | `(4 1 2)` | `(1 5 3)` | `(4 5 6)` |
| 2 | `(1 1 2)` | `(1 2 4)` | `(5 3 1)` | `(5 6 8)` |
| 4 | `(1 2 2)` | `(2 4 1)` | `(3 1 5)` | `(6 8 10)` |

実際のrank-to-CPU/NUMA mapを調べ、その結果生じるinter-nodeおよびinter-NUMA
interfaceを計算した後に限り、軸の厳密な順序を変更してよい。Prepared partitionごとに
cell balance、interface-face count、neighbour count、意図したnode/NUMA rank groupを
跨ぐfaceを記録する。これらは説明変数であり、acceptance metricではない。

各candidateを2回screeningする。最良candidateとScotchをそれぞれ最低5回独立に投入し、
投入順を交互にする。

### Phase 4：multi-node runtime switch

最良の4-node layoutをprofileする。Rank 0に加えて、inter-node face数が最大のrankと、
代表的なinterior rankを1つ選ぶ。MPI wait/collective/transfer timeが実質的な場合にのみ
MPI switchを追究する。

次の順序で一度に1要因を試す。

1. OpenFOAM `topoControl=16`とdefault 0の比較。
2. `commsType=scheduled`とdefault `nonBlocking`の比較。
3. 完全に同じnode/rank/fabric topology上だけで生成・使用するIntel MPI collective
   autotuning。

新たなevidenceがない限り、motorBikeで既知のnegative trialである
`nPollProcInterfaces=-1`、単一Allreduce algorithmのglobal強制、pinningの無効化、
任意のcompact/scatter変更を繰り返さない。1 nodeでは`I_MPI_FABRICS=shm`、複数node
では`shm:ofi`を維持する。

### Phase 5：cell ordering

rank、placement、partition、MPI設定が安定した後、次を比較する。

1. Renumberingなし。
2. Cuthill-McKee。
3. `blockSize=32768`のblock-local Cuthill-McKee。
4. 32768でmemory behaviourまたはFVOPSが改善した場合に限り、`blockSize=65536`。

過去の公開結果では通常のrenumberingは同等から1.4%低速だったため、negativeなcandidate
が2件続けばこのphaseを終了する。縮小したruntime buildに`renumberMesh`を加えることは
build内容の変更であるため、`[require-build]` commitと新しいarchiveが必要になる。

### Phase 6：最終qualification

最良構成を1、2、4 nodeでそれぞれ最低5回実行する。公式FVOPSのdistribution、
4-node/1-node strong scaling、partition特性、placement、scheduler accounting、
profileに基づく説明を報告する。Node数固有のtuningは反復したevidenceがある場合にのみ
保持し、結果が統計的に同等なら一貫した1つのtopology ruleを優先する。

## 判断規則

- screening candidateは、全runがvalidかつmedian FVOPSがbaseline medianを上回る場合に
  のみ次へ進める。
- 設定は、反復測定での改善が、同一systemで測定したrelative rangeと1%のうち大きい
  方を超える場合にのみ採用する。その境界未満は区別不能と記録し、単純な設定を選ぶ。
- proxyの改善だけでcandidateを次へ進めない。
- invalidな結果が出たcandidateは、最初のfatal commandまたはerrorを特定し、完全な
  E2E pathが再度成功するまで停止する。
- 適切に構成したcandidateが2件続けて改善せず、profileからその軸がruntimeの実質的な
  割合を占め得ないと判明した場合、その軸を終了する。
- 当初のsetting-level campaignはbench run 50件を上限とする。追加runにはprofileに
  裏付けられた新しいhypothesisを必要とする。

## Runごとの完了checklist

- Actions workflowと必要な全jobがterminal successへ到達する。
- PJM jobがexit code zeroでterminalに達し、残留jobを残さない。
- `run-success`が存在する。
- 公式parserが`STATUS: VALID`と1行の`RESULT:`を出力する。
- 正確なnode数、rank数、rank/node、CPU affinity、NUMA placementがpresetと一致する。
- Workload identityとbuild provenanceがcomparison group内で一致する。
- 固定artifact setが正しくpackage、upload、archiveされる。
- 必要なBigQuery factが存在する。
- experiment ledgerにhypothesis、変更要因、結果、interpretation、次のdecisionを記録する。

## 完了状況

計画したcampaignは2026-08-13に完了した。Named preset、immutable case cache、full-core
およびbalanced-rank screen、topology-aware partition、boundary-rank VTune profile、
exact-topology Intel MPI autotuning、decomposition後の2種類のordering candidate、同一
buildによる1/2/4-nodeの5-run qualificationは、すべて必要なE2E pathを通過した。
判断と完全なrun populationは`runtime-optimization-experiments.md`に記録している。

再現可能な選択済みlayoutは、Scotchを使用する1 x 120、2 x 120、4 x 112 rankであり、
4-node processor listではNUMA domainごとに1 CPUを予約する。Default Intel MPI
collectiveとrenumberingなしを引き続き採用する。当初のstop conditionの下でこれ以上の
candidateは採用しない。MPI autotuningと両ordering variantはいずれも1%未満で、条件
付きの65536-cell ordering trialは発動せず、最終qualification populationは完了した。
