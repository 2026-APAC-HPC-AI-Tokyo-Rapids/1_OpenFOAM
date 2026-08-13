# cavity3D-64M runtime最適化実験台帳

本台帳は、実験の完了または決定的なstatic調査のたびに更新する。Timingに関する主張
には、公式にvalidと判定されたbench結果だけを使用する。

## 状況

- 現在のphase：Phase 0のnoise確認およびPhase 1のfull-core screening。
- 現在のbuild：既存のOpenFOAM v2606 Icx/Intel MPI archive。再利用予定。
- 現在のproduction preset：1 node、総rank数120、Scotch、`I_MPI_FABRICS=shm`。
- 現在のhypothesis：120 rank固定のcanary構成では2および4 nodeの割当を十分に利用
  できない。小さなMPI runtime調整を行う前に、physical coreを使い切るlayoutが優位に
  なるはずである。
- commit `948e11f`での最初のfull-core screenは完了した。2 node/240 rankで
  3.3997 M FVOPS、4 node/480 rankで6.8139 Mを得て、いずれもvalidだった。同時実行
  した1 node repeatでは1.6996 Mだった。
- commit `a5390da`でfull-core workflow `31634782784`（2/240）と
  `31634785406`（4/480）をrepeat中である。次のcontrolled factorは4 node/448 rank
  で、各NUMA domainにつき1 CPUを意図的に予約する。

## 本研究に採用した既存evidence

| Evidence | 変更要因 | 結果 | 判断 |
|---|---|---|---|
| Actions 256 / run `r-c4bb4bb3c51a6a6724aa7177ea1d01e6` | 1 node、120 Scotch rank | VALID、1.6398 M FVOPS | baseline sample |
| Actions 257 / run `r-fef72f7255e44a077f5fa2b1b115b0df` | 2 node、引き続き120 rank | VALID、3.1718 M FVOPS | canaryのみ。full-core baselineではない |
| Actions 258 / run `r-c2aef4bc0f5dd083a8790751af269342` | 4 node、引き続き120 rank | VALID、4.9488 M FVOPS | canaryのみ。full-core baselineではない |
| Actions 277 / run `r-efdfb255f9d7c78e7eb9c7df59bcab5c` | 1 node/120のrepeat | VALID、1.6392 M FVOPS | 0.04%以内で一致 |
| Actions 278 / run `r-49e4a417a55f2278a211f483d720b391` | VTune rank 0 | VALID profile、DIC 45.8%、Amul 26.1% | sampling対象rankはlocality律速 |
| Actions 279 / run `r-6227d22fbc780cd0ad71df88fd19ed2c` | merge後の1 node/120 | VALID、1.6270 M FVOPS | baseline sample。1.6398 Mより約0.8%低い |
| Actions 280 / run `r-321efbd20828499c944ad987c4170a68` | named `scotch-1n-120r` presetとcontent-addressed 120-way case cache | VALID、1.6400 M FVOPS、39.025 s/step | 新preset pathは従来baselineと一致。並行full-core screeningへ進む |
| Actions 281 / run `r-0af1f803cd25cfc680fed74ca4a2e067` | 2 node、240 Scotch rank | VALID、3.3997 M FVOPS、18.825 s/step | 従来の2-node/120-rank canaryを7.2%上回る。現在の1-node rangeが4.4%のため、採用前にrepeatする |
| Actions 282 / run `r-91ee8cc4584bd7464cfc3a82b2a405fa` | 4 node、480 Scotch rank | VALID、6.8139 M FVOPS、9.393 s/step | 従来の4-node/120-rank canaryを37.7%上回る。full-core layoutを維持 |
| Actions 283 / run `r-0cb4e46f0158a5bf0437f6c1bf5b1106` | 1-node named-preset repeat、cache hit | VALID、1.6996 M FVOPS、37.655 s/step | 予想外に速いがvalid。観測した4.4% rangeを暫定noise thresholdとする |
| Actions 284 / run `r-c500507dc433575dde90bfcb4073be8f` | 2-node/240-rank repeat、cache hit | VALID、3.4015 M FVOPS、18.815 s/step | 最初の3.3997 Mと0.05%以内で一致。full-core 2-node layoutを採用 |
| Actions 285 / run `r-95df043fc37d34b11df231699019ce85` | 4-node/480-rank repeat、cache hit | VALID、7.8264 M FVOPS、8.178 s/step | 最初のrepeatを14.9%上回る。full-coreの改善は確実だが、4-node noiseのため交互にrepeatする |
| Actions 286 / run `r-8bf1d07cc38e52ced65c4cf1095bfc52` | 4 node、448 Scotch rank、balanced NUMA reserve | VALID、8.0025 M FVOPS、7.997 s/step | 隣接する480-rank結果を2.25%上回るが、観測済み4-node range内。採用前にrepeatする |

## 基盤に関する観測：Actions 280

- 日付とcommit：2026-08-13 JST、`948e11f`。
- Actions / PJM：`31627088350`、preparation job `6467089`、solver job
  `6467176`。
- Case preparation：cache miss。`blockMesh`と120-way Scotch decompositionは
  30分のPJM制限内に完了した。Actions preparation jobは20m29sを要し、cache
  `daba43a5b54c39cda0874fdff2f9c7f6d06200d8e34f8266eada33194b3a235f`を公開した。
- Solver：公式結果は`STATUS: VALID`、`FVOPS_trim=1.6400M`、
  `s_per_step=39.025`、`trim_time=156.1s`。1 node上で5/5 step、120 rank。
- 健全性：`run-success`が存在し、必要なActions jobはすべて成功した。固定のv2および
  公式result artifactはuploadされ、home archiveへcopyされた後、設計どおりGitHub上の
  copyを削除した。PJM job `6467176`は完了後の`pjstat`に存在しなかった。
- 解釈：preset/cacheの一般化はreference resultを測定可能な範囲で変化させなかった。
  最初のcache-miss pipelineでは5-step solverよりcase preparationが支配的であり、
  immutable decompositionの再利用は実験campaignにとって重要である。
- 判断：この結果をPhase 0 sampleとして保持し、buildせず`scotch-2n-240r`と
  `scotch-4n-480r`へ進む。計画した現workflowでのnoise sample数を満たすため、
  1-node repeatをもう1件投入した。

## Phase 0結果：暫定noise range

現在利用可能な比較可能かつvalidな1-node結果5件は、1.6270、1.6392、1.6398、
1.6400、1.6996 M FVOPSである。medianは1.6398 M、minimum-to-maximum spanはmedianの
4.4%である。最新結果はmedianより3.6%高いため、測定されたenvironmental causeなしに
invalidなoutlierとして除外できない。交互のrepeatでこのrangeが狭まるまでは、4.4%
未満のcandidate改善を区別不能として扱う。

## Phase 1 screen：physical coreをすべて使用

同時にdispatchした3 workflowはすべて、公式parse、固定artifact upload、home-server
archivalを含めterminal successに達した。共有filesystemを保護するためpreparation job
は直列のままとし、solverは自身のimmutable cacheが公開され次第実行できた。

| Actions | Node/rank | Prepare PJM/cache | Solver PJM/run | 公式結果 | Solver/pipeline wall |
|---:|---:|---|---|---|---|
| 281 (`31629648195`) | 2 / 240 | `6467212`、cache miss、`a69a992f...` | `6467289`、`r-0af1f803cd25cfc680fed74ca4a2e067` | VALID、3.3997 M、18.825 s/step | 121.824 / 123.490 s |
| 282 (`31629651069`) | 4 / 480 | `6467287`、cache miss、`25d0ec32...` | `6467377`、`r-91ee8cc4584bd7464cfc3a82b2a405fa` | VALID、6.8139 M、9.393 s/step | 56.860 / 58.525 s |
| 283 (`31629672240`) | 1 / 120 | `6467376`、cache hit、`daba43a5...` | `6467389`、`r-0cb4e46f0158a5bf0437f6c1bf5b1106` | VALID、1.6996 M、37.655 s/step | 202.274 / 203.950 s |

240-way Scotch partitionはunique interface face 3,529,391、rank pair 1,372、平均
neighbour 11.43、最大19、264,000--269,332 cells/rankであり、連続する120-rank node
境界を跨ぐfaceは303,351だった。480-way partitionはunique interface face 4,653,839、
rank pair 2,998、平均neighbour 12.49、最大23、131,931--134,666 cells/rankであり、
連続する3つの120-rank node境界を跨ぐfaceは727,567だった。取得したplacementから、
各nodeでlocal rankが正確に120個、rankごとに異なるCPUが1個ずつであることを確認した。

従来の120-rank固定canaryと比べ、240 rankでは2-node FVOPSが7.2%、480 rankでは
4-node FVOPSが37.7%改善した。1.6400 Mのvalidation runに対し、最初のfull-core結果は
2.07xおよび4.15xにscaleした。4-node結果は測定noiseを明確に上回るためfull-core rank
occupancyを維持する。改善幅が小さい2-node結果はrepeatを必要とする。次のdecomposition
phaseでは、急増するinterface countを対象とし、rank groupをnodeおよびNUMA geometryに
対応させるべきである。

## Phase 2準備：balanced 112 ranks/node

compute-node hardware captureでは、NUMA node 0--7が連続した15-CPU range `0-14`、
`15-29`、...、`105-119`に対応する。一般的な448-rank launchではCPU 0--111を使い、
idleな8 CPUすべてが最後のNUMA domain末尾に集中する。Preset `scotch-4n-448r`では
代わりにlocal rankを`0-13,15-28,30-43,45-58,60-73,75-88,90-103,105-118`へbindし、
各NUMA domainの最後のCPUを予約する。これはPhase 2で意図したresource layoutとして、
rank数とbalanced CPU reservationを同時に変更する。DecompositionはScotch、transportは
`shm:ofi`のままとする。480 rankとのscore比較前に、全4 nodeでrankごとのplacementが
このsetと完全に一致することを確認する。

Actions 286（`31635007954`）では、全4 nodeで意図したplacementを確認した。Nodeごとに
異なる112 CPUを使い、CPU 14、29、44、59、74、89、104、119は不使用だった。
Preparation PJM `6467443`はcache `1170485d...`を公開し、solver PJM `6467537`は
run `r-8bf1d07cc38e52ced65c4cf1095bfc52`で公式`STATUS: VALID`、8.0025 M FVOPS、
solver wall 51.385 s、pipeline wall 53.056 sを得た。448-way partitionはinterface face
4,537,155、rank pair 2,797、139,315--144,285 cells/rankで、連続する112-rank node
groupを跨ぐfaceは704,792だった。Actionsとhome-server artifact archivalはいずれも成功し、
実験が所有するPJM jobは残らなかった。

この単一結果は隣接する7.8264 Mの480-rank repeatを2.25%上回るが、2件の480-rank
結果自体に14.9%の幅がある。したがって、NUMA domainごとに1 coreを予約する案は有望
ではあるが未採用である。全coreを使わないと本workloadが明確に悪化するという強い仮定
は否定され、partition screen後に448/480を交互にrepeatする根拠となった。

## Phase 3準備：geometric partition screen

2件の480-rank candidateでは、Scotch baselineに対してnode数、rank数、Intel MPI設定、
cell arithmeticを固定する。

- `hierarchical-4n-480r`は`xyz`順序で直接の`(6 8 10)` splitを使用する。uniformな
  400-cubed meshに対する解析的なaxis-plane interface countは3,360,000 faceであり、
  processor-boundary表現の詳細を考慮する前の値でScotchの測定値4,653,839を27.8%
  下回る。
- `multilevel-node-numa-4n-480r`は、4つのnode rank groupに`(1 2 2)`、nodeごとの8つの
  NUMA groupに`(2 4 1)`、NUMA groupごとの15 rankに`(3 1 5)`を適用する。積は同じ
  最終grid `(6 8 10)`だが、連続する120-rank node placementが外側のgeometric domainと
  対応するようrank numberingを設計している。

Geometric case生成は、意図的に独立したprepare scriptとcache identityで実装する。
既存のScotch prepare scriptを拡張するとscript digestが変わり、公開済みの120、240、
480-way Scotch cacheや処理中の448-way cacheを不必要に無効化するためである。両
geometric candidateのpreparationは、共有filesystem上の他の処理と引き続き直列化する。
Solverの失敗でvalidなimmutable cacheを削除してはならない。

最初のdirect-hierarchical runであるActions 287（`31635570359`）は、solverと公式parser
を正常完了し、7.8745 M FVOPS、8.127 s/stepを得た
（`r-0724eeff7878fb21867b61f6f7e2f1f5`、solver PJM `6467689`）。Solver wallは
52.711 s、pipeline wallは54.402 sで、artifactもarchiveされた。しかし独立した
mesh-facts stageは、requested-partition v1 contractがScotchしか許容しないため、実効
dictionaryを拒否した。このためscoreはvalidだが、partition比較用runとしては不完全で
ある。観測した失敗にはrequested-partition v2で対処し、method enumを`scotch`、
`hierarchical`、`multiLevel`のみにした。Method固有dictionaryはraw source copyだけに
保持し、そのSHA-256で識別する。採用判断の前に、両geometric candidateを更新後のE2E
parserで再実行する必要がある。v2以前のmultilevel workflow、Actions 288
（`31635572939`）も後にterminal successへ達し、validな7.9404 Mをarchiveしたが、
schema修正前のためpartition factは除外する。

v2 rerunは完全なpartition factを伴って`run-success`へ到達した。

| Method / run | 公式結果 | Solver/pipeline wall | 総interface face | Cross-node face | Cross-15-rank-group face |
|---|---:|---:|---:|---:|---:|
| direct hierarchical / `r-a5b01db9af5238c920e6897afbc7c4f8` | VALID、6.7815 M、9.438 s/step | 57.945 / 59.685 s | 3,402,564 | 537,572 | 1,989,739 |
| node-NUMA multi-level / `r-e212e71fb3656f6c9b86d31299f30085` | VALID、7.9306 M、8.070 s/step | 52.506 / 54.179 s | 3,399,744 | 320,000 | 1,440,000 |

両partitionのcell balanceはほぼ完全である。480-way Scotch partitionに比べ、
multi-levelでは総interface faceが26.9%、rank-pair countが2,998から2,108、平均
neighbourが12.49から8.78、cross-node faceが56.0%減少した。v2 multi-level結果は、
v2以前のvalid solver結果7.9404 Mと0.12%以内で一致した。一方、direct-hierarchical v2
結果は総interface countが近いにもかかわらず6.7815 Mまで低下した。これは総interface
countだけでなく、rank numberingとtopologyの対応が重要であることを示す。両
requested-partition v2 workflowはterminal Actions successへ達した。Actions 289
（`31639528519`、direct hierarchical）とActions 290（`31639530786`、multi-level）で
ある。Home-server archivalを含む必要な全jobが成功し、両方に`run-success`があり、
実験が所有するPJM jobは残らなかった。Multi-levelを次へ進め、direct hierarchicalは
棄却する。

## Phase 4準備：topology-boundary profile

完全なmulti-level partition factから、inter-node faceが最も多いrankは346、345、149、
148、331、330、134、133で、それぞれ6,030 faceである。そこでnamed profile preset
`multilevel-node-numa-r346-4n-480r`は、最良のdecompositionと全runtime設定を維持し、
defaultのrank 0ではなくrank 346をinstrumentする。これによりprofile母集団をbench
scoreから分離したまま、測定済みのboundary rankを対象にできる。この結果から、MPI
wait/transferが新しいIntel MPIまたはOpenFOAM communication実験に値するほど大きいか
判断する。既知のnegative設定`topoControl=16`と`nPollProcInterfaces=-1`は、このprofile
が反証を示さない限り除外する。

Rank-346 profileはActions `31642562397`である。同時に、交互のcache-hit repeatとして
`31642564622`（multi-level）、`31642567524`（448-rank Scotch）、`31642570205`
（480-rank Scotch）を並行投入した。Score distributionに含めるのは3件のbench runだけ
である。

4 workflowはすべてterminal successに達しartifactをarchiveした。Multi-level repeatは
7.8745 M FVOPSで、以前の2結果7.9306/7.9404 Mと0.8%以内で一致した。448-rank Scotch
repeatは7.9850 Mで、8.0025 Mと0.22%以内で一致した。対して480-rank Scotch repeatは
6.7315 Mで、3結果は6.7315、6.8139、7.8264 Mとなった。448-rank medianは7.9938 M、
480-rank medianは6.8139 Mで、前者が17.3%上回り、より安定している。したがって、
120 ranks/nodeよりbalanced 112 ranks/nodeを採用する。

Profile run `r-50ed9d8a6f67bc10dee84032df2e5c57`はvalidだったがscore比較から除外する。
Rank 346のreported CPU time 31.190 sの内訳は、DIC preconditioning 46.4%、
`lduMatrix::Amul` 24.8%、PCG scalar solve 10.0%、`PMPI_Allreduce` 7.8%、その他の明示的な
MPI/UCX send、wait、progress functionが約1.6%だった。Boundary rankもcompute/locality
律速であり、MPI collective tuningのsampled upper boundは約10%である。Intelの文書に
よれば、application autotuningはtopology固有であり、`I_MPI_TUNING_MODE=auto`と
`I_MPI_TUNING_BIN_DUMP`で生成し、`I_MPI_TUNING_BIN`でfileを使用できる。これは組み合わせ
た448-rank topology-aware partitionの測定まで保留し、以前の120/240-rank trialは条件が
混在していたため、negativeなscreen 1件で終了する。参照：Intel MPI
[Autotuning](https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/current/autotuning.html)
および[tuning environment variables](https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-15/tuning-environment-variables.html)。

## Phase 2/3の組み合わせcandidate：448-rank node-NUMA multi-level

安定したresource layoutとtopology-aware partitionを、4 node group、nodeごとの8 NUMA
group、NUMA groupごとの14 rankとして正確に組み合わせる。Geometric factor
`(1 2 2)`、`(1 2 4)`、`(7 2 1)`の積はbalancedな最終grid `(7 8 8)`となり、連続する
112-rank node groupと14-rank NUMA groupを維持する。Preset
`multilevel-node-numa-4n-448r`は、採用済み448-rank Scotchに対してpartitionだけを、
次へ進めた480-rank multi-level結果に対してrank数/placementだけを変更する。このcaseは
独立したimmutable cacheを持つため、従来のgeometric cacheもScotch cacheも無効化しない。

Actions 295（`31643727848`）は組み合わせcandidateのE2Eを完了した。Preparation PJM
`6467911`はcache `7366e001...`を公開し、solver PJM `6467970`は
`r-6f3e551e3c054d9baa58425e2dd6d202`を生成した。公式結果はVALID、8.0757 M FVOPS、
7.925 s/step、solver wall 51.676 s、pipeline wall 53.262 sだった。Placementは採用済み
112-rank/node CPU setと一致した。Partitionはinterface face 3,226,624、rank pair 2,008、
平均neighbour 8.96、最大12、142,857--142,858 cells/rank、cross-node face 320,000、
cross-14-rank-group face 1,600,000だった。これは現在のbest single scoreであり、448-way
Scotchに比べ総faceを28.9%、cross-node faceを54.6%削減する。448-way Scotch medianに
対する1.0%の優位は単一runとして判断thresholdに近すぎるため、Actions `31645708556`
（multi-level）と`31645711266`（Scotch control）を交互のcache-hit repeat pairとした。

このpairも残留PJM jobなしでE2Eを完了した。Actions `31645708556`はmulti-level cacheを
solver PJM `6467998`で実行し、`r-2f7657cc91c87bdcda8e68451367701b`を生成した。公式
VALID、8.0655 M FVOPS、7.935 s/step、solver/pipeline wallは50.694/52.372 sだった。
Actions `31645711266`はScotch controlをsolver PJM `6467989`で実行し、
`r-c3aa0970c4b8792f42f4ff5c02830886`を生成した。公式VALID、8.0025 M FVOPS、
7.997 s/step、solver/pipeline wallは51.295/53.017 sだった。いずれも正確な4 x 112-rank
placementを使用し、必要なActions/archive jobはすべて成功し、固定artifactはhome-server
archiveに保持された。

2件のmulti-level結果は8.0757、8.0655 M（median 8.0706 M、range 0.13%）だった。
3件のScotch結果は8.0025、7.9850、8.0025 M（median 8.0025 M、range 0.22%）だった。
Multi-levelは一貫して高速だが、medianの優位は0.85%にすぎず、事前に定めた最低1%の
採用thresholdを下回る。したがってpartition結果は統計的に区別不能と記録し、より単純な
448-rank Scotch設定を4-node構成として採用する。Node/NUMA-aware partitionは、性能改善
を主張せず、記録済みのnear-tieおよびcommunication topologyの有用な説明として残す。
Runtime-switch screenには448-rank Scotchを使用し、threshold未満のpartition効果を次の
要因へ暗黙に混ぜない。

## Phase 4判断：Intel MPI autotuning screen 1件

Profileではcollective tuningのsampled upper boundが約10%、`PMPI_Allreduce`だけで7.8%
のため、controlled screen 1件には根拠がある。Intel MPI 2021.16文書ではapplication
autotuningはplatform固有でIntel processorのみをsupportするとされ、玄界group Aは
Intel Xeon Platinum 8490Hを使用するため対象となる。最初のrunでは、完全に同じ
4-node/448-rank/112-rank-per-node Scotch topology上でtuning binaryを生成する。この
timed resultはsearchを含むため探索的なものとする。別runでbinaryを使用した場合だけ、
変更なしのScotch controlと比較できる。生成失敗または使用時の結果がcontrol以下なら
この軸を終了し、collective algorithmを手動で強制するsweepは行わない。

Actions `31646485229`は既存buildとcached 448-way Scotch caseを使ってapplication tuning
binaryを生成した。Solver PJM `6468020`は公式VALID、7.9061 M FVOPS、8.095 s/step、
solver/pipeline wall 52.044/53.864 sを得た。このrunではapplication searchが有効なため、
scoreを採用比較から除外する。正確な4 x 112-rank placementを確認し、全Actions/archive
jobが成功し、PJM jobは残らなかった。生成された889,965-byte binaryのSHA-256は
`cc1ee2e1ce1181298a10cc60bb1dd38971a9ecce5a6fb6b215a8e6d30211c3f0`で、runで取得した
copyとimmutable shared copyは一致した。Actions `31647180395`でこのbinaryを使用し、
同時投入したActions `31647182300`を同一commit/buildの変更なしScotch controlとする。

Pairの両runは正常完了した。Binary使用側のActions `31647180395`、solver PJM
`6468068`、run `r-fc9f80e8263daf85d8412d0ff5499983`は、公式VALID 8.0251 M FVOPS、
7.975 s/step、solver/pipeline wall 51.576/53.184 sだった。使用した889,965-byte source
copyのSHA-256は上記と完全に一致した。Control側のActions `31647182300`、solver PJM
`6468063`、run `r-10b85e0fce6dbe046445562b04fa9ae0`は、公式VALID 7.9652 M FVOPS、
8.035 s/step、solver/pipeline wall 51.563/53.950 sだった。両方とも正確な4 x 112
placementでarchivalまで完了し、PJM jobを残さなかった。

Binary使用時のscoreは同時実行controlを0.75%上回ったが、最低1%の採用threshold未満
だった。さらに重要なことに、solver wallは0.03%遅く、見かけのscore差はE2E solverの
改善ではなくtrimmed intervalによる。したがって、このtopologyではIntel MPI application
autotuningを棄却する。Default Intel MPI collective selectionを引き続き採用し、事前に
定めたstop ruleに従ってalgorithm sweepは行わない。

## Phase 5準備：decomposition後のcell ordering

公式task guidanceではdecomposition後に`renumberMesh -constant -overwrite -parallel`を
適用しており、公開済みの通常Cuthill-McKee結果は同等から1.4%低速だった。実験ではこの
適用位置を正確に維持する。縮小buildには`renumberMesh`、`renumberMethods` library、
reconstruct dependencyを追加し、すべてbuild sidecarへ記録する。Ordered caseの構築時
だけpreparationに4 nodeと448 rankを使い、既存448-way Scotch cacheのimmutable derivative
として保存する。Solver repeatではこのcacheをmaterializeするだけで、renumbering costを
負担しない。

Candidateは通常Cuthill-McKeeと、rank内をScotchで分割する概算`blockSize 32768`の
block-local Cuthill-McKeeの2件とする。Node/rank placement、partition membership、MPI
設定、workload、solverは同一に保つ。両方をscreeningし、32768-cell版でFVOPSまたは
測定したmemory behaviourが改善した場合に限り`blockSize 65536`を試す。

Commit `f3958b7`で必要な新buildを要求した。Push Actions `31647838535`はarchiveを再利用
せず7m31sでbuildし、build archive 301（476,685,265 byte、SHA-256
`3890cf74252d4b8ec0f2d66d64f6523a8cd7498018ad5cf8d3b06a06b085f984`）を公開した。
closed sidecarとprovision validationには`renumberMesh`および`renumberMethods`/reconstruct
dependency closureが含まれる。Default 1-node E2E run、solver PJM `6468124`、run
`r-864a780dc7b9f19d5dbc1b377ddfaf4c`は、1 node上の120 rankで公式VALID、
1.7019 M FVOPS、37.605 s/stepだった。全Actions/archive jobが成功し、PJM処理は
残らなかった。Actions `31649038444`で通常Cuthill-McKeeをscreeningし、同一buildの変更なし
Scotch control `31649040528`とpairにした。Ordering phaseでは旧buildのscoreを直接の
controlにしない。

通常orderingのpairはE2Eを完了した。Cuthill側のActions `31649038444`、preparation PJM
`6468155`、solver PJM `6468164`は、base Scotch cache `1170485d...365c56`からの
immutable derivative cache `70ab1aa4...82d968`を使用した。公式結果はVALID、
8.0630 M FVOPS、7.938 s/step、trimmed time 31.75 sだった。同一buildで変更なしのcontrol
Actions `31649040528`、solver PJM `6468166`は公式VALID、7.9900 M FVOPS、
8.010 s/step、trimmed time 32.04 sだった。両方とも正確な4 x 112 placement、scheduler
elapsed 82 sで、固定artifactをすべてarchiveし、PJM jobを残さなかった。Cuthill-McKeeは
pairのcontrolより0.91%高いが、1%の採用threshold未満のため単独では次へ進めない。
Actions `31649727744`で構造の異なる32768-cell block-local orderingをscreeningし、同一
buildで変更なしのcontrol `31649729689`とpairにする。

Block-localのpairもE2Eを完了した。Actions `31649727744`、preparation PJM `6468189`、
solver PJM `6468193`はderivative cache `7f685f00...c480359a`を使い、公式VALID
8.0655 M FVOPS、7.935 s/step、trimmed time 31.74 sを得た。同一buildで変更なしのcontrol
Actions `31649729689`、preparation PJM `6468192`、solver PJM `6468194`は公式VALID
7.9900 M FVOPS、8.010 s/step、trimmed time 32.04 sだった。両方ともscheduler elapsed
81 s、正確な4 x 112 placementでarchivalに成功し、PJM jobを残さなかった。Block-local
orderingはpairのcontrolより0.94%高いが、やはり1%の採用threshold未満で、通常
Cuthill-McKeeの0.91%とほぼ同一である。

どちらのordering candidateも採用条件を満たさず、32768-cell candidateは65536-cell
trialの前提も満たさない。したがって、公開済みの通常renumberingが同等からnegative
だったevidenceとも整合して、このphaseは適切に構成したnon-advancing candidate 2件で
終了する。Renumberingは採用しない。Ordered immutable cacheとraw logは研究evidenceと
して保持し、solver qualificationには変更なしのScotch cacheを使用する。

## Phase 6準備：同一buildでの最終qualification

選択した再現可能な構成は、1 nodeで120 rank、2 nodeで240 rank、4 nodeでbalanced
448 rankであり、すべてScotch、default Intel MPI collective selection、cell renumbering
なし、1 nodeでは`shm`、複数nodeでは`shm:ofi`を使用する。最終distributionにはbuild
archive 301だけを使い、古いbuild結果はcontextとして残す。Node数ごとに公式VALIDな
独立submissionを5件収集し、immutable case cacheを再利用しつつ異なるnode allocationを
許容する。単一runを結論とせず、median、range、4-node/1-node strong scalingを報告する。

## 最終qualification結果

選択した構成の15 runはすべて、Actions -> PJM -> 公式parser -> 固定artifact -> home
archiveの全経路を完了した。すべて公式VALIDで、正確なplacementと同じbuild内容を使用し、
実験が所有するPJM jobを残さなかった。305など後のarchive番号はarchive 301へのhardlink
である。Archive size 476,685,265 byte、SHA-256
`3890cf74252d4b8ec0f2d66d64f6523a8cd7498018ad5cf8d3b06a06b085f984`は同一で、sidecar
identityとinodeも一致する。

| 選択layout | Actions run | FVOPS sample (M) | Median | Min--max | Relative range |
|---|---|---|---:|---:|---:|
| 1 node、120 rank、Scotch | `31647838535`, `31650357613`, `31650362362`, `31650359704`, `31650364015` | 1.7019, 1.6433, 1.7021, 1.7009, 1.6410 | 1.7009 M | 1.6410--1.7021 M | 3.59% |
| 2 node、240 rank、Scotch | `31650366010`, `31650367910`, `31650369815`, `31650371822`, `31650373910` | 3.4129, 3.3939, 3.4006, 3.1817, 3.1730 | 3.3939 M | 3.1730--3.4129 M | 7.07% |
| 4 node、448 rank、balanced Scotch | `31649040528`, `31649729689`, `31650375882`, `31650377899`, `31650379863` | 7.9900, 7.9900, 8.0050, 7.9850, 7.9875 | 7.9900 M | 7.9850--8.0050 M | 0.25% |

Medianでの2-node/1-node strong scalingは1.995x、4-node/1-nodeは4.697x、
4-node/2-nodeは2.354xである。見かけ上superlinearな4-node scalingは、この固定workload
と選択したrank数での観測として報告し、これらrunを超えて一般化しない。4-node
distributionは非常にtightであり、1-および2-nodeのrangeは、個々のbest scoreではなく
medianを正とする理由を示している。

したがって最終的に選択したpresetは次のとおりである。

- `scotch-1n-120r`：120 ranks/node、default binding、`I_MPI_FABRICS=shm`。
- `scotch-2n-240r`：120 ranks/node、default binding、`I_MPI_FABRICS=shm:ofi`。
- `scotch-4n-448r`：112 ranks/node。明示的なbalanced processor listにより各15-core
  NUMA domainで1 CPUを予約し、`I_MPI_FABRICS=shm:ofi`を使用。

すべてdefault Intel MPI collective selectionを使用し、cell renumberingは行わない。
4-node node/NUMA multi-level partition、MPI autotuning、通常Cuthill-McKee、block-local
Cuthill-McKeeは実験evidenceとして保持するが、反復測定した改善が事前に定めた1%
thresholdを超えなかったため採用しない。Direct hierarchicalと480-rank Scotchは、測定
したsolver性能または安定性、あるいはその両方を根拠に棄却する。

## Issue #14：採用済み4-node/448-rank構成のVTune profile

DIC cell-gatherとPCG loop fusionを統合した現行sourceで、採用済み
`scotch-4n-448r`をVTune Hotspotsで測定した。当初のActions #332はrank 0だけを観測したが、
過去のAPSでrank 0のMPI fractionが他rankより低かったため、それだけでは通信とload
imbalanceを代表しない。Commit `53512405eeeae088cc14ae574aeb2ed10dca8cdd`でprofile対象rankを
workflow inputから選択し、scheduler request、PJM環境、canonical factへ記録するようにした。
起動条件は比較軸を増やさないため、`hotspots`、software sampling、stack収集なし、60秒attach
のままとした。この条件は低い擾乱で関数別exclusive CPU timeを得る目的には妥当だが、全rankの
wall-clock通信待ちを直接測るものではない。

同commitのActions #334でtask-minimal buildを新規作成し、通常1-node E2Eを公式VALID、artifact
退避、PJM cleanupまで完走させた。続くrank 0、3、365のprofileは同じbuild archive #334、
474,567,727 byte、SHA-256
`34260960b2e8a105bc0c73cdd655a2e08c60016c3d161b1de478a8e173410b99`を再利用した。Rank 3は
cross-node faceが0のinterior rank、rank 365は16,967 faceで最大のcross-node boundary rank、
rank 0はその中間である。

| Actions / rank | neighbour | interface face | cross-node face | DIC | Amul | PCG | 3 kernel合計 | 明示的MPI/transport | MPI busy wait |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| #337 / 0 | 13 | 17,374 | 10,144 | 43.76% | 24.13% | 9.51% | 77.40% | 11.96% | 2.54% |
| #335 / 3 | 8 | 14,385 | 0 | 40.86% | 24.73% | 9.01% | 74.60% | 13.94% | 0.38% |
| #336 / 365 | 16 | 22,486 | 16,967 | 47.46% | 23.72% | 9.52% | 80.70% | 9.96% | 0.78% |

「明示的MPI/transport」は`libmpi`、UCX、UCT、UCS、OFI moduleに帰属したCPU timeの合計、
「MPI busy wait」はVTune CSVの同名列の合計であり、sleep中のelapsed timeは含まない。
Rank間で明示的MPI比率は9.96--13.94%、主要3 kernel比率は74.60--80.70%と動くため、単一rank
から448 rank全体の通信量やcritical pathを一般化してはいけない。一方、interior rankと最大
cross-node rankの両方でもDIC、Amul、PCGが上位でCPU timeの約4分の3以上を占めた。したがって
rank 0だけを根拠にした数値は代表値として撤回するが、「次の主要なsource最適化対象は
DIC/Amul/PCGの計算・memory locality」という判断は複数rankでも支持される。Job-wideの同期を
問う場合はHotspotsの起動引数を膨らませず、別runでVTune `hpc-performance`またはIntel Trace
Analyzer and Collectorを使用する。

#337のrank 0はrun `r-b7ed06944df8357bc0e77e51a2836201`、PJM `6471390`、8.6195 M
FVOPS、7.425 s/step、#335のrank 3はrun `r-66cacfee0b504c36f4c1984b230a4d01`、PJM
`6471352`、8.3524 M、7.663 s/step、#336のrank 365はrun
`r-cffd7a87ce1aadae5290aa31771aa716`、PJM `6471350`、8.4155 M、7.605 s/stepだった。
すべて公式VALID、5/5 step、10/10 solve、VTune collection/target exit code 0で、固定artifactと
home archiveを回収し、PJM jobはterminalである。Profile scoreはbench distributionから除外する。

同じcommitでは、役割を終えた一時的なv2 overhead workflow、棄却済みのgeometric、multilevel、
renumber、MPI autotune用script/preset、およびそれらだけに必要だった`renumberMesh` build roleを
削除した。通常運用は採用済みの3つのScotch presetへ限定し、拒否候補の測定結果は本research
記録と過去のActions artifactを正本として残す。

### 主要kernelのHPC Performance Characterization

主要kernelがmemory側か演算器側かを判定するため、通常benchとsoftware Hotspotsとは分離して
VTune `hpc-performance`を同じ#334 build、4 node、448 rank、60秒上限で実行した。最初の
hardware sampling実装はsoftware Hotspots用のPID attachを流用し、次にVTune直下へ対象rankを
置いたが、玄界のIntel SEP driverは対象processの関数sampleを残さず、node-wide DRAM bandwidth
だけで1,000 MB上限へ到達した。Actions #338--#345はこのcollector境界の診断runであり、性能
結論には用いない。Full resultの`perfrun` logで`system-wide mode=0`、SEP選択、Perf無効化、
`Total Thread Count=0`、関数CSV headerのみを確認した。

Commit `766d4dd46432fe95e6ee23b9701328ca01d2ae00`では、HPC analysisだけstack collectionを有効に
した。Intel VTune 2025.3.0はこれによりLinux Perf driverless collectionを選択し、VTune直下の
`icoFoam` rankへcore eventを帰属できた。Software Hotspotsは従来どおりstackなしattachを維持
する。確定runはrank 3のActions #346（run
`r-34d9fc894ca09f4d7c24bc3c542bdb4f`、PJM `6471767`）とrank 365のActions #347
（run `r-a0fa79f5768bac061c5dde276cb15b10`、PJM `6471920`）で、いずれも公式VALID、5/5 step、
10/10 solve、collection/target exit 0、artifact回収、PJM cleanupまで完走した。関数reportは
それぞれ388行、401行の実データを持つ。

以下はVTuneがloopとして分離した同名function内のCPU time正値行を合計し、各指標をそのCPU
timeで加重平均した値である。Memory Boundとその階層内訳はpipeline stallの分類であり、割合を
単純加算する指標ではない。

| Rank | Kernel | loop CPU time | Memory Bound | L3 Bound | DRAM Bound | packed FP | CPI |
|---:|---|---:|---:|---:|---:|---:|---:|
| 3 | DIC precondition | 2.795 s | 67.2% | 20.9% | 48.3% | 0.0% | 1.42 |
| 3 | `lduMatrix::Amul` | 1.435 s | 64.9% | 23.7% | 43.6% | 14.3% | 1.52 |
| 3 | PCG scalar solve | 0.620 s | 89.6% | 27.6% | 47.0% | 74.5% | 1.79 |
| 365 | DIC precondition | 1.245 s | 68.5% | 21.3% | 49.4% | 0.0% | 1.6 |
| 365 | `lduMatrix::Amul` | 0.625 s | 71.7% | 20.0% | 49.4% | 20.8% | 1.6 |
| 365 | PCG scalar solve | 0.285 s | 67.3% | 20.9% | 58.2% | 86.9% | 1.8 |

Run全体のMemory Boundもrank 3で58.7%、rank 365で60.4%とVTuneがhigh判定した。主要3 kernelは
両rankですべて64%以上がMemory Boundで、L3/DRAM stallが大きい。DIC loopはpacked FP 0%、
Amulも14--21%であり、PCG loopだけが75--87%までvector化されている。したがって現時点では
演算器 throughputよりmemory hierarchy、特にDRAM/locality側が
主要制約である。Rank 0だけに依存せず、interior rank 3と最大cross-node boundary rank 365で
同じ分類になった。一方、summaryのDRAM bandwidth 383--385 GB/sは同居するnode全体のuncore
値なので、選択rankや個別kernelへ帰属させない。次に深掘りする場合は、通常benchの引数を
増やさず、同じ複数rank方針の独立したVTune Memory Access analysisでNUMA、local/remote DRAM、
cache missを確認する。

## Issue #15：compiler tuning比較

条件はworkflow matrixやdispatch inputでは切り替えず、各条件を`main`上の独立commitとして
`[require-build]`付きでpushする。各commitの`build_condition`、`WM_COMPILE_OPTION`、
`FOAM_EXTRA_CXXFLAGS`をbuild sidecarへ記録し、run時にもsidecarのcompile optionから同じ
`WM_OPTIONS`を再構成できたことを検証する。各buildでは同じ
`-qopt-report=3 -qopt-report-phase=loop,vec,cg`を付け、optimization reportをbuild artifactへ
保存するため、report収集自体は比較因子にならない。

上流v2606 ruleと直近build #348のsidecarを確認した結果、現行C++ baselineはIssue本文にある
`-O2`ではなく、`Opt`の`-O3 -fp-model=precise`である。比較順序は次の通りとする。

1. `baseline`: `Opt`、追加target flagなし
2. `opt-avx512`: `OptAVX512`、`-O3 -xCORE-AVX512`
3. `opt-avx512-zmm-high`: 2に`-qopt-zmm-usage=high`を追加
4. `opt-sapphirerapids`: `Opt`に`-march=sapphirerapids -mtune=sapphirerapids`を追加

すべて`scotch-4n-448r`の公式workload、decomposition、MPI layout、runtime optionを固定し、
公式VALID、FVOPS、s/step、solver/pipeline wall、iteration/residualを比較する。

## 実験template

### 実験ID

- 日付とcommit：
- Actions run / PJM job / run ID：
- 仮説：
- 比較baseline：
- 単一の変更要因：
- Node数 / rank数 / ranks per node：
- Decompositionとordering：
- MPI/OpenFOAM runtime設定：
- 公式結果とvalidity：
- Solverおよびpipeline wall time：
- Partitionおよびplacementの観測：
- ArtifactおよびBigQueryの状況：
- 解釈：
- 判断と次の実験：
