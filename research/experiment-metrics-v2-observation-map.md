# OpenFOAM v2 観測マップ

## この文書の役割

この文書は、各factについて「どこにある値を、誰が、いつ取得するか」を固定する実装契約で
ある。[概要計画](./experiment-metrics-v2-plan.md)が情報モデルと比較規則を定め、本書が実コード・
command・artifactへの配線を定める。

key registryへ入れるには、次の六項目を全て埋めなければならない。

1. authoritative source: object、structured file、command、またはsource symbol
2. producer: そのsourceを一度だけ読むowner
3. capture moment: 値が確定し、まだ失われていない時点
4. raw destination: `run/key/value`または耐久artifact
5. validation: 誤読、scope混同、部分取得を検出する規則
6. absence semantics: 非該当、未到達、取得失敗のどれか

sourceの優先順位は、native object/API、machine-readable command/file、専用structured marker、
stable log parser、汎用text regexの順とする。下位sourceを使う場合はfixtureと上位sourceの照合を
必須にする。設定fileに書いた値を、実効値として扱ってはならない。

## 値の段階とscope

同じ名前の値でも次の段階が違えば別factである。

| 段階 | 意味 | 例 |
|---|---|---|
| requested | 人間またはschedulerへ要求した値 | PJM node/proc、decomposition method |
| launch-effective | exec直前に構成された値 | 実argv、exec環境、CPU affinity |
| runtime-observed | programが初期化後に使用した値 | OpenFOAM header、Pstream state |
| result-observed | 実行により生じた値 | ExecutionTime、residual、exit code |

requestedとruntime-observedが一致しても、一方は他方の完全な代替ではない。比較viewで照合し、
rawで上書きしない。一方、同じsource recordから常に復元できるcount、first、last、average等は
subsetなのでraw keyを作らない。

## producerと時系列

```text
Actions runner
  create regular-run manifest or qualification-allocation parent plus two child manifests
  verify clean/reachable Git state and build sidecar
  record exact pjsub argv and subject ID
  submit PJM without BigQuery credentials
  save stdout/stderr, outcome, and the job ID when returned

PJM supervisor
  snapshot job-entry environment
  write subject kind/ID, PJM_JOBID, and qualification ordered child IDs
  record requested scheduler shape and actual outer argv
  run preparation stages
  launch same-rank wrapper -> OpenFOAM

same-rank wrapper (each rank)
  write placement/environment delta to its rank-specific source file
  exec solver without an extra MPI launch

OpenFOAM shared startup hook
  append startup-applied state after UPstream initialization to its rank-specific JSONL
  append runtime-current state after Time/controlDict resolution
  send only actual runtime control changes thereafter; observation failure never changes solver exit/numerics

allocation-local post-run auditor
  regular: inspect mesh/partition only after the scored solver
  qualification: inspect both arms only after arm 2; never between arms

Actions runner
  after PJM terminal state, parse any saved solver log even after timeout/failure
  reduce rank-specific source files and validate the variant-specific expected-file manifest
  regular: merge -> GitHub Artifact upload -> publish
  qualification: package parent evidence and both child source/log/metrics in one artifact set
```

`run-manifest.json`で生成したrun IDを全producerが読む。各processで再計算しない。target hookは
local file descriptorまたはnode-local fileへ一つのstructured eventを書くのみで、metrics key、
BigQuery、retryを知らない。

## fact別の取得契約

表の「欠損」はraw valueへ空文字を入れる意味ではない。keyを出さず、post-runのexpected-file検証と
`collection-status.json`のcompleteness reasonで説明する。
これはapplicableかつexpectedなfamilyだけの規則である。bench/qualificationでprofile-onlyとなる列は
consumerでNULLを返すだけで、raw key、family status、Evidence、reasonを作らない。

| fact family | authoritative source | producer / capture moment | raw keyまたはartifact | validation | 欠損時の扱い |
|---|---|---|---|---|---|
| run/subject identity | runnerが一度生成したsubject/child manifests | `runner.manifest` / provision前 | raw tableの`run`列、run/allocation manifest artifact | regular subject ID=run ID、qualification subject ID=allocation ID、ordered child/arm、全fragmentのrun一致。run/allocation IDはglobal unique/safe path。PJM job IDを含めない | manifestなしでは投入しない |
| metrics contract | Git管理`openfoam-v2.toml`とlane/run variantが選んだexpected producer graph | `runner.manifest` / provision前 | `run.metrics_contract`、contract/protocol artifact | contract ID/content hash、exact producer version、view compatibility、mixed contract禁止、family/列の`applicable_run_variants`、applicable missing policyとinapplicable projection policyの分離 | required familyならcomparison不適格。非適用列はconsumerでNULLだけを返す |
| source track | Gitのscore reference/profile base、実checkout head、purpose/qualification arm | `runner.manifest` / provision前 | tagged-union canonical source-track artifact、content hash、`control/source-track-validation.json` | benchはreference/head、profileはprofile base/head、qualification OFFはhead=score reference、ONはreference ancestorかつcanonical tree diff=build/bundleのinstrumentation patch identity。diff algorithm/version/base/head/expected patch/passをsubmit前にsealしquery時Git参照なし。clean HEAD/tree、reachability/source archive、submodule/mode/symlink/LFSも検証。moving branch名をidentityにせずdiff/hashをrawへ保存しない | jobを投入しない |
| instrumentation bundle | Git管理bundle manifest、build sidecar、実launch設定 | `runner.manifest` / submit前、`runner.postrun` / run後照合 | canonical manifest artifact。consumer hashはartifact contentから導出 | hook/probe/sample設定、wrapper executable hash、contract version、env capture scope、build patchの列挙と実activation一致。labelだけで同一視しない | benchのrequired bundleならcomparison不適格。profile-only bundleはbenchでproducerを持たない |
| instrumentation qualification decision | Git管理D-001 decision record | `runner.manifest` / bench submit前 | manifest fields、`control/instrumentation-qualification-decision.json`、Runsのdecision hash/status | canonical hash、adopt/reject、qualification protocol、reference/candidate tuple、bundle/build/workload/toolchain/MPI、evidence一致。通常bench tupleを再構成して照合 | 無計測benchはnot_required。未存在/未回答はpending、reject/異値はrejected/invalidでscore不適格 |
| scheduler binding | `pjsub` argv/stdout/stderr/responseとPJM側job-entry file | `runner.submission` / pjsub前後、および`pjm.supervisor` / entry直後 | normal runまたはqualification allocationのsubmission result/binding、`control/job-entry.json` | normalはrun ID、qualificationはallocation ID+ordered child IDsをrunner responseと`PJM_JOBID`へ照合。childへ共通値を複写せずparent join | reject、応答不明、片方欠損、不一致はattempt/comparison不適格。自動復旧しない |
| producer completion | producerのnormal closeとStageRunnerのchild outcome | `pjm.supervisor`または`StageRunner` / return後 | producer fragment、stage termination、post-run collection status | variant別expected producer/file/keyを一度検査 | 欠損はcollection incomplete。失敗runのpartialはbest effort回収 |
| protocol assignment | Git管理protocolとrunnerの割当record | `runner.manifest` / job投入前 | `experiment.block_id`、`experiment.block_order`、`experiment.replicate_index`、`experiment.pair_id`、`experiment.planned_replicate_group_id`、`experiment.planned_comparison_set_id`、qualification armを含むplanned treatment tuple | contract/protocol/policy hash込みcanonical tupleからgroup/set IDを再計算、run purpose、予定/max attempt、stopping rule、lane membership、pair IDの一意性 | purpose別comparison不適格。attempted groupやpairを観測値・順序から推測しない |
| qualification allocation | Git管理paired scheduleとrunnerが一度作るparent manifest | `runner.manifest` / pair submit前、`pjm.supervisor` / entry、`runner.postrun` / terminal後 | allocation ID、scheduler binding/accounting、job-entry env、minimal hardware、pair/ordered child IDs、OFF/ON order、common binding | 一allocation一pair、二childの独立manifest/log/metrics、child parent ref、block ID=allocation ID、同じartifact set、pair間は別allocation | arm間crash/未起動/未完成は回収できたfileだけ保存しpair不適格。片armを別allocationへ再pairしない |
| OpenFOAM/ThirdParty source | checkout直後、`.git`削除前の各`git rev-parse HEAD` | `build.packager` / build開始前 | `control/build-sidecar.json`、比較用source commit索引 | moving branch名でなくfull commit。完成buildとsidecarを対応付ける | build artifactを公開しない |
| toolchain/build | `mpiicx --version`、`mpiicpx --version`、`mpirun --version`、`readelf --dynamic <icoFoam>`、`ldd <icoFoam>`、完成binary/archive | `build.packager` / archive完成時 | immutable build sidecarとartifact identity索引、各command raw output | LC_ALL=C、DT_NEEDED、resolved path/hash、binary/archive hash、sidecar schema | build不完全としてreuse禁止 |
| actual workload identity | setup後にsolverが読む実caseのworkload-defining memberとsolver executable/argv | `pjm.supervisor` / setup完了後、blockMesh前 | `case.workload_identity`、`source/workload-manifest.json` | `0/`、`constant/transportProperties`、`system/controlDict`、`fvSchemes`、`fvSolution`、`blockMeshDict`等のcontract列挙memberをpath、size、SHA-256でsealしprotocol workload identityと照合。generated `decomposeParDict`はpartition factだけが所有 | 欠損・member差・hash不一致はcomparison不適格 |
| full job-entry environment | `env -0`相当のNUL区切りprocess environment | `pjm.supervisor` / script entry直後、module/unset前 | regularは`env.job_entry.*`と`source/env/job-entry.snapshot`、qualificationはparent snapshotとallocation env projection | byte-exact name escapeと全value Base64、entry count fixture。child rawへ複写せずEnvironmentがblock/allocation join | applicable snapshot collector failed |
| full exec environment | supervisor baselineと各solver wrapperのbyte environment | applicable score bundle/profile/qualification ONの`pjm.supervisor` + `exec.wrapper`、runner reducer / mpirun直前、各rank exec直前、terminal後 | `env.host_exec.common.*`、`source/env/host-exec.snapshot`、`source/env/rank-<rank>.delta.json` | rank別source file、`os.environb`相当、common+delta full復元、expected全rank | applicable variantではconfiguration incomplete。qualification OFFは非適用でNULLだけ |
| scheduler request | Git管理lane、PJM script identity、runnerが実行するexact `pjsub` argv | `runner.submission` / submit直前 | regularは`run`の`scheduler.request`、qualificationはparent evidence artifact/allocation projection | lane.nodes/ranks/rscgrp/transportとscript/argv overrideを照合。child rawへ複写しない | invalid protocol assignment |
| scheduler accounting | `pjstat --history -S --choose jid,st,sdt,elp,ec,sn,pc,nnumu,mmszu,uctmut,sctmut --data --delimiter "\t" <job>` | `runner.postrun` / terminal state後 | regularは`scheduler.accounting`と`source/scheduler/pjstat.{stdout,stderr}`/`pjstat-version.txt`、qualificationはparent raw/allocation projection | field list/unit/job ID固定、requestedとの一致はview判定。childはallocation IDでjoin | 取得fieldだけ欠損扱い。host/rank/rscgrpを捏造しない |
| observed topology/placement | solverと同じMPI launch内のglobal/local rank、`hostname`、CPU/NUMA affinity | applicable score bundle/profile/qualification ONの`exec.wrapper`、runner reducer / exec直前、terminal後 | `parallel.rank_placement` | rank別source file、別`mpirun`禁止、実証済みrank env名、expected rank/host/count | applicable variantではtopology incomplete。qualification OFFは非適用でNULLだけ |
| actual argv | stage wrapperが`subprocess`へ渡すargv配列 | `StageRunner` / spawn直前 | stage別launch argv、solverは`run.launch_argv` | shell再構成文字列ではなく配列。spawnしたargvとbyte単位で一致 | stage未開始またはconfiguration incomplete |
| run timing/outcome | supervisorのUTC clock、monotonic clock、最終status | `pjm.supervisor` / entry時とpost-run回収後 | `run.started_at`、`run.finished_at`、`run.elapsed_sec`、outcome/exit | wall timestamp pairとmonotonic elapsedを別clockとして保持、solver validityと分離 | 保存できたterminationとstage outcomeから中断を表す |
| stage outcomes | supervisorの同じmonotonic clockとraw child wait status | `StageRunner` / spawn直前とwait直後 | `perf.stage.<name>.wall_time_sec`、`run.stage.<name>.termination` | exit/signal/spawn_errorをJSONで区別し、BigQuery時間を含めない | termination objectで中断を表現 |
| minimal hardware identity | scheduler/node queryのnode class、CPU model/stepping | `pjm.supervisor` / regularはrun前、qualificationはallocation内でarm 1前に一度、allocated nodeごと | regularは`hardware.identity_min`、qualificationはparent `source/hardware/identity-min.*`とallocation projection | observed host集合、全node consensus、one-shot capture。qualification childはparent sourceをjoinしrawへ複写しない | applicable hardware identity incomplete |
| full hardware topology（profile only） | `LC_ALL=C lscpu --json`、`/sys/devices/system/cpu/online`、`/sys/devices/system/node/online`、各nodeの`cpulist`/`meminfo`、`/proc/meminfo` | `postrun.auditor` / profile solver終了後、allocated nodeごと | `hardware.topology_full`とcommand/file raw artifact | observed hostname集合、exact file membership/parser fixture | profileではhardware incomplete。bench consumerはNULLだけを返す |
| mesh topology | exact buildにlinkした`mesh-facts` probeの`fvMesh::nCells/nFaces/nPoints/nInternalFaces`と`LC_ALL=C checkMesh` raw log | `postrun.auditor` / regularはsolver後、qualificationはarm 2終了後だけ | `mesh.topology`、probe JSON、complete checkMesh log | native method値、probe/checkMesh exit、schema completeness | official scoreとは分離しcomparison不適格 |
| requested partition | 実際に使用したgenerated `decomposeParDict` | `pjm.supervisor` / decomposePar直前 | `mesh.partition.requested`、dict artifact | argvが指すfileとartifact identity一致 | preparation failure |
| observed partition | serial mesh/order、processor addressing、decompose/check output | `postrun.auditor` / regularはsolver後、qualificationはarm 2終了後だけ | `mesh.partition.observed` | rank/local-index順保持、global cell一回、signed face addressing、expected subdomain集合 | partition incomplete |
| runtime header | OpenFOAM startupが出すBuild/Arch/Exec/nProcs/Hosts | `runner.log_parser` / PJM terminal後、`logs/log.icoFoam`があれば | `solver.runtime_header` | `argList.C` symbol/format golden、host sum=nProcs。Exec stringをargvへ逆変換しない | configuration incomplete |
| Pstream startup-applied | `UPstream::init()`、node comm state、`attachOurBuffers()`後の実buffer | applicable score bundle/profile/qualification ONの`openfoam.startup` -> rank別JSONL、`runner.pstream_parser` / attach完了後emit、terminal後reduce | `solver.pstream.startup_applied.rank.<rank>` | configured/clamped/attached byte、node control、expected全rank、banner非依存 | applicable variantで欠損ならreason/Evidenceあり。qualification OFFは非適用でNULLだけ |
| Pstream runtime-current | `Time::setControls()`でcase override済みの登録switch | applicable score bundle/profile/qualification ONの`openfoam.runtime_config` -> rank別JSONL、`runner.pstream_parser` / time loop前emit、terminal後reduce | `solver.pstream.runtime_current.rank.<rank>` | floatTransfer、node controls、usingNodeComms等をsymbol対応、false/0明示、expected全rank | applicable variantで欠損ならreason/Evidenceあり。qualification OFFは非適用でNULLだけ |
| Pstream runtime changes | `Time::readModifiedObjects()`からの実control変更 | applicable score bundle/profile/qualification ONの`openfoam.runtime_config` -> rank別JSONL、`runner.pstream_parser`がterminal後に一度reduce | `solver.pstream.change_events.rank.<rank>` ordered array | startup/runtime sentinelが揃いchange 0件だけ`[]`、complete-line/event count/sequence/old/new一致 | applicable variantで欠損ならreason/Evidenceあり。qualification OFFは非適用でNULLだけ |
| time-step timing | 保存済みsolver logの`Time =`と同一stepの`ExecutionTime = ... ClockTime = ...` | `runner.log_parser` / PJM terminal後 | `solver.step_timings` | 原lexemeとnullable numeric、全match順序。単調性/有限性はcomparison evaluator | 得られたcomplete recordだけ保存しofficial/comparison理由を分離 |
| pressure solves | 保存済みsolver logの各`Solving for p` record | `runner.log_parser` / PJM terminal後 | `solver.pressure_solves` | initial/final residual/iterationsを同じrecordに保持、match数と公式期待数を照合 | 部分配列を保存しinvalid reasonを出す |
| official markers | complete solver logとcanonical official evaluator | `runner.log_parser` / PJM terminal後 | `solver.log_markers`、official validityはview | shell validity semanticsのgolden parity後、固定locale/decimal evaluatorを共有 | parse failureとofficial invalidとscore算出不能を区別 |
| primary score inputs | `solver.step_timings`の先頭/末尾ExecutionTimeと公式固定定数 | BigQuery view / query時 | rawへscoreを重複保存しない | fixed decimal/roundingのcanonical evaluatorと`64,000,000 * 4 / trim`をgolden照合 | source record不足ならNULLと理由 |
| artifact identity | localで作ったrun bundle、profileだけのraw tar、build sidecar | `runner.packager` / GitHub Artifact upload前 | artifact URI、bundle/profile hash、build source/hash、`artifact-manifest.json` | build/workload/env/placement/PJM raw+version/`logs/pjm-job.log`/`logs/log.icoFoam`/`results/result.txt`を列挙し、profileは`<runtime>/runs/<run>/profile/raw`のperf/APS/VTune raw、tool metadata、exact profiler argvも回収。benchではprofile artifact/placeholder/absence recordを作らない | uploadできなければrun-level archive failure。benchのprofile consumerは理由なしNULLだけ |
| audit subject binding | 元runのimmutable mesh/build artifact manifestとcontent identity | `runner.audit_manifest` / 別audit job投入前 | audit runの`audit.subject_artifact_identity` | remote hashを再検証し、registryでtransfer可としたartifact-derived familyだけjoin | 欠損時はstandalone auditで元runへjoinしない |
| archive/publish result | GitHub Artifact upload結果、SCP結果、BigQuery response | workflow archive job/`Publisher` / upload・転送・送信後 | workflow logとData Status | SCP成功後だけGitHub Artifactを削除。失敗はArtifactを残してjob failure | scientific familyへ理由を伝播せず、run-level状態だけにする |

## OpenFOAM内hookの位置

runtime headerの既存producerはOpenFOAMの共通startup pathであり、solver固有の`icoFoam.C`へ
同じ値を再実装しない。Build/Arch/ExecとnProcs/Hostsは`argList.C`、pressure lineは
`SolverPerformance.C`のsource symbolへ固定する。

Pstreamは一地点では不足する。`argList` constructor内の`runControl_.runPar()`で
`UPstream::init()`が走った後も、`createTime.H`の`Time`構築がcaseの`OptimisationSwitches`を
適用するためである。次の二境界と変更境界を使う。

1. startup-applied: `UPstream::init()`の`attachOurBuffers()`完了後。`UPstream::nodeCommsControl_`、
   `nodeCommsMin_`、`usingNodeComms(worldComm)`、`numNodes()`、`topologyControl_`、configured
   `mpiBufferSize`、`MPI_BUFFER_SIZE`適用/clamp後の実`attachedBufLen`を記録する。
2. runtime-current: `Time` constructorの`setControls()`後、time loop前。`floatTransfer`、
   `nProcsSimpleSum`、`nProcsNonblockingExchange`、`tuning_NBX_`、`PstreamBuffers::algorithm`、
   `defaultCommsType`、`nPollProcInterfaces`、`maxCommsSize`、current `nodeCommsControl_`、
   `nodeCommsMin_`、`topologyControl_`、`usingNodeComms(worldComm)`を記録する。
3. runtime change: `Time::readModifiedObjects()`で上記値が実際に変わった時だけold/new eventを出す。

hookは`bannerEnabled()`の外に置き、全rankがrank-scoped eventを出す。version、producer、scope、
payloadを持つが、event write失敗でsolverの数値処理やexit codeを変えない。in-process hookには
別のsupervisor eventを偽造せず、expected event欠損としてpost-run completenessに出す。対象versionごとに
symbolとfull commitをregistry source欄へ固定し、line番号だけを契約にしない。

## 現実装からの変更点

| 現在の箇所 | 問題 | v2での境界 |
|---|---|---|
| `experiment-metrics/.../context.py` | 各呼出しでrun IDを再構成する | runnerがmanifestを一度作り全producerは読むだけ |
| `experiment-metrics/.../cli.py`のcollectorとstage | collection直後に`send()`し、timed child完了後もnetworkへ接続する | pure fact -> Recorder。publishはrunnerだけ |
| `experiment-metrics/.../sender.py` | BigQuery credential/retryがcompute側packageにある | `publish.py`へ隔離しPJM bundle/環境からcredentialを除去 |
| `.github/workflows/genkai.yml`の`job_environment` | BigQuery credentialをPJMへ渡している | runnerに保持し、最初にcredential移動、その後に全env snapshotを有効化 |
| `scripts/build-openfoam.sh` | moving branchをcheckoutしcommit記録前に`.git`を削除する | resolved commitsを先にbuild sidecarへ書き、完成archiveと対応付ける |
| `scripts/run-openfoam.pjm`の`run-start` | 記録argvと実際のprofiler-wrapper付きargvが違う | `StageRunner`のspawn地点のargv配列を唯一のlaunch sourceにする |
| 同PJM scriptのsolver non-zero分岐 | official parser前にexitし失敗runの原始結果を失う | `finally`相当でcomplete log parserを常に実行 |
| 同PJM scriptのcleanup | Artifact upload前にcaseを削除し得る | variant別expected fileをGitHub Artifactへuploadできた後に削除 |
| 現行case/result/mesh collector | motorBike前提や未呼出し経路が混在し、compute timeoutではparserが走らない | runnerのcavity3D pure log parserとallocation-local mesh auditorへ分離 |
| `tasks/parse_result.sh` | 現公式semanticsの正本だがshell parse/丸めが暗黙でcomplete recordではない | v2 canonical evaluatorとgolden parity後、その薄いCLIへ置換 |

## laneとsidecar契約

`experiments/lanes/openfoam-genkai-{1,2,4}.toml`はnode数だけでなく、rank数、resource group、
transport policy、required logical producer、instrumentation modeを明示する。rank数をcore数から
暗黙推定しない。runnerはlane、PJM script identity、exact `pjsub` argvを一つのrequest recordへ
sealする。validationは次の独立sourceを照合する。

```text
lane.nodes = request.nodes = accounting.nnumu
           = distinct(runtime_header.hosts) = distinct(placement.hosts)
lane.ranks = decomposeParDict.numberOfSubdomains = runtime_header.nProcs
           = runtime_header.host_rank_sum = placement record count
```

accounting commandが返さないhost/rank/resource-group fieldはaccounting factに含めない。2/4 nodeで
launch-effective environmentに`I_MPI_FABRICS=shm`があればlaunchを拒否する。

各rank wrapperは衝突しない`source/placement/rank-<rank>.json`とrank environment sourceへ一度書いてsolverを
execする。daemon、IPC、ACKは置かない。runner reducerはPJM supervisor baseline environmentと各rank deltaから
full environmentを再構成し、placement canonical arrayとともに一つのlogical producer fragmentへ変換する。
post-run validatorがexpected rank cardinalityを検査する。

## validation fixture

最低限、次のfixtureをGit管理する。

- 公式valid log、step不足、solve不足、iteration不一致、NaN/Inf、truncated log
- ExecutionTime非単調、ClockTime同値、scientific notation、`1.2.3`、trim zero、score算出不能
- `bannerEnabled=false`、`writeHosts` 0/1/2、hostsum欠損、複数nProcs/Hosts block
- 一行に複数NaN/Inf、`End`で始まる別行、official INVALIDだがprocess exit 0
- 1/2/4 nodeのruntime headerとrank placement、host sum不一致
- Pstreamのstartup/runtime override、false、0、default、明示値、runtime change、banner無効event
- protocol workload fixtureと、setup後のcase member一つを変えた不一致fixture
- variant applicability grid：profile-only collectorのprofile失敗はreasonあり、benchは理由/status/EvidenceなしNULL、qualification OFFのON専用列は同じNULL、qualification ONの同collector失敗はreasonあり
- tagged-union source trackのbench/profile/qualification OFF/ON、base非ancestor、instrumentation以外の差分、checkout tree不一致、同bundleでbase/workload/toolchainだけ変更、moving branch名が同じでもcommitが異なるfixture
- qualification allocationの一pair二child、二pair混入を全pair reject、child順/arm不一致、別allocationへの再pair、arm間crash、片child未起動/metrics未完成fixture
- instrumentation bundleのhook/sample interval一つだけを変えたhash差とactual activation不一致fixture
- D-001 decisionの未存在、non-adopt、hash不一致、candidate tuple不一致、adopt完全一致fixture
- supervisor common environmentとrank追加/変更/削除deltaのfull byte snapshot復元
- 同じlogical dictを異なる挿入順で作ったcanonical JSON
- 正常close、program failure、途中JSON line、missing fragment、異値conflict
- OpenFOAM artifact移管のhappy path、GitHub upload失敗、SCP失敗

全fixtureで、raw row集合、completeness reason、comparison eligibility、公式parser parityを検査する。

## 未決定事項

bench/profile分離と、benchのprofile-only metricは値をNULLにするだけで原因/status/Evidenceを作らないことは
ユーザー確定済みである。score runに許す最小bench bundleの統計上限D-001はユーザー確認待ちである。決まるまでは
profiler、polling、verbose MPI/Pstream trace、full placement診断はprofile-only、未qualificationのinline eventは
audit-onlyとする。閾値を文書へ仮置きしてscore/qualification eligibleへ混入させない。
