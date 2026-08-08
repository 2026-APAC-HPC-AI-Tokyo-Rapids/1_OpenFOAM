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
  create and fsync run-manifest.json
  verify clean/reachable Git state and build sidecar
  submit PJM without BigQuery credentials
  fsync immutable run-to-PJM submission binding

PJM supervisor
  snapshot job-entry environment
  record requested scheduler shape and actual outer argv
  start one node-local rank-record collector per allocated node
  run preparation stages
  launch same-rank wrapper -> OpenFOAM

same-rank wrapper (each rank)
  send placement/environment delta to the node-local collector and await durable ACK
  exec solver without an extra MPI launch

OpenFOAM shared startup hook
  emit startup-applied state after UPstream initialization
  emit runtime-current state after Time/controlDict resolution, before the time loop
  emit only actual runtime control changes thereafter

allocation-local post-run auditor
  inspect mesh/partition only after the scored solver

Actions runner
  after PJM terminal state, parse any saved solver log even after timeout/failure
  reduce durable node rank-record sidecars
  merge -> validate -> archive and verify -> publish/replay
```

`run-manifest.json`で生成したrun IDを全producerが読む。各processで再計算しない。target hookは
local file descriptorまたはnode-local fileへ一つのstructured eventを書くのみで、metrics key、
BigQuery、retryを知らない。

## fact別の取得契約

表の「欠損」はraw valueへ空文字を入れる意味ではない。keyを出さず、対応producerのlifecycleと
completeness reasonで説明する。

| fact family | authoritative source | producer / capture moment | raw keyまたはartifact | validation | 欠損時の扱い |
|---|---|---|---|---|---|
| run identity | runnerが一度生成してfsyncした`run-manifest.json` | `runner.manifest` / provision前 | raw tableの`run`列、manifest artifact | repository、Actions run/attempt、submissionごとの128-bit nonceと全fragmentのrun一致。PJM job IDを含めない | manifestなしでは投入しない |
| metrics contract | Git管理registry/schema version | `runner.manifest` / provision前 | `run.metrics_contract` | registry/view compatibility | comparison不適格 |
| scheduler binding | `pjsub`の成功応答とPJM job ID | `runner.submission` / submit直後 | `scheduler.job_id`、immutable submission-binding artifact | run ID、submit response、job entryの`PJM_JOBID`一致 | jobを追跡不能として停止 |
| producer lifecycle | supervisorのcollector/child境界 | `pjm.supervisor`または`StageRunner` / 呼出し前とreturn後、`Recorder`が永続化 | 独立`lifecycle/<producer>.jsonl`のstarted/final | complete line salvage、末尾partial破棄、data fragmentと別owner | startedのみを中断、journalなしを未到達 |
| protocol assignment | Git管理protocolとrunnerの割当record | `runner.manifest` / job投入前 | `experiment.block_id`、`block_order`、`replicate_index` | protocol commit、予定attempt、laneへのmembership | comparison不適格、推測しない |
| experiment source | checkout済み`1_OpenFOAM`の`git rev-parse HEAD`とclean/reachability check | `runner.manifest` / provision前 | repository/full commit | dirty tree拒否、remote到達または耐久bundleを要求 | jobを投入しない |
| OpenFOAM/ThirdParty source | checkout直後、`.git`削除前の各`git rev-parse HEAD` | `build.finalizer` / build開始前 | build sidecar、比較用source commit索引 | moving branch名でなくfull commit。archive後にsidecarをcommit markerとしてrename | build artifactを公開しない |
| toolchain/build | `mpiicx --version`、`mpiicpx --version`、`mpirun --version`、`readelf --dynamic <icoFoam>`、`ldd <icoFoam>`、完成binary/archive | `build.finalizer` / archive完成時 | immutable build sidecarとartifact identity索引、各command raw output | LC_ALL=C、DT_NEEDED、resolved path/hash、binary/archive hash、sidecar schema | build不完全としてreuse禁止 |
| full job-entry environment | `env -0`相当のNUL区切りprocess environment | `pjm.supervisor` / script entry直後、module/unset前 | `env.job_entry.*` | byte-exact name escapeと全value Base64、entry count fixture | snapshot collector failed |
| full exec environment | supervisor baselineと各solver wrapperのbyte environment | `pjm.supervisor` + `exec.wrapper`、runner reducer / mpirun直前、各rank exec直前、terminal後 | `env.host_exec.common.*`、rank delta、removed names | durable node sidecar、`os.environb`相当、common+delta full復元、expected全rank | configuration incomplete |
| scheduler request | Git管理lane、PJM script identity、runnerが実行するexact `pjsub` argv | `runner.submission` / submit直前 | `scheduler.request` | lane.nodes/ranks/rscgrp/transportとscript/argv overrideを照合 | invalid protocol assignment |
| scheduler accounting | `pjstat --history -S --choose jid,st,sdt,elp,ec,sn,pc,nnumu,mmszu,uctmut,sctmut --data --delimiter "\t" <job>` | `runner.finalizer` / terminal state後 | `scheduler.accounting`、stdout/stderr/PJM version artifact | field list/unit/job ID固定、requestedとの一致はview判定 | 取得fieldだけ欠損扱い。host/rank/rscgrpを捏造しない |
| observed topology/placement | solverと同じMPI launch内のglobal/local rank、`hostname`、CPU/NUMA affinity | `exec.wrapper` -> node collector、runner reducer / exec直前、terminal後 | `parallel.rank_placement` | durable node sidecar、別`mpirun`禁止、実証済みrank env名、expected rank/host/count | topology incomplete |
| actual argv | stage wrapperが`subprocess`へ渡すargv配列 | `StageRunner` / spawn直前 | stage別launch argv、solverは`run.launch_argv` | shell再構成文字列ではなく配列。spawnしたargvとbyte単位で一致 | stage未開始またはconfiguration incomplete |
| run timing/outcome | supervisorのUTC clock、monotonic clock、最終status | `pjm.supervisor` / entry時とpost-run回収後 | `run.started_at`、`run.finished_at`、`run.elapsed_sec`、outcome/exit | wall timestamp pairとmonotonic elapsedを別clockとして保持、solver validityと分離 | lifecycleから中断理由を出す |
| stage outcomes | supervisorの同じmonotonic clockとraw child wait status | `StageRunner` / spawn直前とwait直後 | `perf.stage.<name>.wall_time_sec`、`run.stage.<name>.termination` | exit/signal/spawn_errorをJSONで区別し、BigQuery時間を含めない | started/final lifecycleで中断を表現 |
| node hardware | `LC_ALL=C lscpu --json`、`/sys/devices/system/cpu/online`、`/sys/devices/system/node/online`、各nodeの`cpulist`/`meminfo`、`/proc/meminfo` | `postrun.auditor` / solver終了後、allocated nodeごと | `hardware.nodes`、command/file raw artifact | host-invariant fieldsだけ、observed hostname集合、exact file membership/parser fixture | hardware completenessだけfalse。scoreは保持 |
| mesh topology | exact buildにlinkした`mesh-facts` probeの`fvMesh::nCells/nFaces/nPoints/nInternalFaces`と`LC_ALL=C checkMesh` raw log | `postrun.auditor` / solver終了後 | `mesh.topology`、probe JSON、complete checkMesh log | native method値、probe/checkMesh exit、schema completeness | official scoreとは分離しcomparison不適格 |
| requested partition | 実際に使用したgenerated `decomposeParDict` | `pjm.supervisor` / decomposePar直前 | `mesh.partition.requested`、dict artifact | argvが指すfileとartifact identity一致 | preparation failure |
| observed partition | serial mesh/order、processor addressing、decompose/check output | `postrun.auditor` / solver終了後 | `mesh.partition.observed` | rank/local-index順保持、global cell一回、signed face addressing、expected subdomain集合 | partition incomplete |
| runtime header | OpenFOAM startupが出すBuild/Arch/Exec/nProcs/Hosts | `runner.log_parser` / PJM terminal後、保存logがあれば | `solver.runtime_header` | `argList.C` symbol/format golden、host sum=nProcs。Exec stringをargvへ逆変換しない | configuration incomplete |
| Pstream startup-applied | `UPstream::init()`、node comm state、`attachOurBuffers()`後の実buffer | `openfoam.startup` / attach完了後、各rank | `solver.pstream.startup_applied.rank.<rank>` | configured/clamped/attached byte、node control、expected全rank。banner非依存 | expected structured event missing |
| Pstream runtime-current | `Time::setControls()`でcase override済みの登録switch | `openfoam.runtime_config` / `Time`構築後time loop前、各rank | `solver.pstream.runtime_current.rank.<rank>` | floatTransfer、node controls、usingNodeComms等をsymbol対応、false/0明示、expected全rank | expected structured event missing |
| Pstream runtime changes | `Time::readModifiedObjects()`からの実control変更 | `openfoam.runtime_config`がrank別event logへappend、`runner.pstream_parser`がterminal後に一度reduce | `solver.pstream.change_events.rank.<rank>` ordered array | expected全rankへ常に出力、`[]`=観測済み0件、complete-line/event count/sequence/old/new一致 | key不在またはevent不整合ならconfiguration incomplete |
| time-step timing | 保存済みsolver logの`Time =`と同一stepの`ExecutionTime = ... ClockTime = ...` | `runner.log_parser` / PJM terminal後 | `solver.step_timings` | 原lexemeとnullable numeric、全match順序。単調性/有限性はcomparison evaluator | 得られたcomplete recordだけ保存しofficial/comparison理由を分離 |
| pressure solves | 保存済みsolver logの各`Solving for p` record | `runner.log_parser` / PJM terminal後 | `solver.pressure_solves` | initial/final residual/iterationsを同じrecordに保持、match数と公式期待数を照合 | 部分配列を保存しinvalid reasonを出す |
| official markers | complete solver logとcanonical official evaluator | `runner.log_parser` / PJM terminal後 | `solver.log_markers`、official validityはview | shell validity semanticsのgolden parity後、固定locale/decimal evaluatorを共有 | parse failureとofficial invalidとscore算出不能を区別 |
| primary score inputs | `solver.step_timings`の先頭/末尾ExecutionTimeと公式固定定数 | BigQuery view / query時 | rawへscoreを重複保存しない | fixed decimal/roundingのcanonical evaluatorと`64,000,000 * 4 / trim`をgolden照合 | source record不足ならNULLと理由 |
| artifact identity | localでsealしたrun bundleとdeterministic archive URI | `runner.finalizer` / final merge前 | artifact URI、bundle hash、manifest identity | bundle対象を固定してhashし、metrics sidecar自身を含めない | bundleをsealせずquarantine |
| audit subject binding | 元runのimmutable mesh/build artifact manifestとcontent identity | `runner.audit_manifest` / 別audit job投入前 | audit runの`audit.subject_artifact_identity` | remote hashを再検証し、registryでtransfer可としたartifact-derived familyだけjoin | 欠損時はstandalone auditで元runへjoinしない |
| delivery receipt | remote PUT/checksum verify、BigQuery publish response | `ArtifactStore`/`Publisher` / run WAL seal後 | run WAL外のappend-only delivery ledger/outer manifest | run/bundle hash/attempt一致、replay冪等 | retry pending。run WALへ書き戻さない |

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
supervisor lifecycleを偽造せず、expected event欠損としてcompletenessに出す。対象versionごとに
symbolとfull commitをregistry source欄へ固定し、line番号だけを契約にしない。

## 現実装からの変更点

| 現在の箇所 | 問題 | v2での境界 |
|---|---|---|
| `experiment-metrics/.../context.py` | 各呼出しでrun IDを再構成する | runnerがmanifestを一度作り全producerは読むだけ |
| `experiment-metrics/.../cli.py`のcollectorとstage | collection直後に`send()`し、timed child完了後もnetworkへ接続する | pure fact -> Recorder。publishはrunnerだけ |
| `experiment-metrics/.../sender.py` | BigQuery credential/retryがcompute側packageにある | `publish.py`へ隔離しPJM bundle/環境からcredentialを除去 |
| `.github/workflows/genkai.yml`の`job_environment` | BigQuery credentialをPJMへ渡している | runnerに保持し、最初にcredential移動、その後に全env snapshotを有効化 |
| `scripts/build-openfoam.sh` | moving branchをcheckoutしcommit記録前に`.git`を削除する | resolved commitsを先にsidecarへfsyncし、artifactとatomic publish |
| `scripts/run-openfoam.pjm`の`run-start` | 記録argvと実際のprofiler-wrapper付きargvが違う | `StageRunner`のspawn地点のargv配列を唯一のlaunch sourceにする |
| 同PJM scriptのsolver non-zero分岐 | official parser前にexitし失敗runの原始結果を失う | `finally`相当でcomplete log parserを常に実行 |
| 同PJM scriptのcleanup | archive検証前にcaseを削除する | runnerのremote verify後だけ削除、失敗時quarantine |
| 現行case/result/mesh collector | motorBike前提や未呼出し経路が混在し、compute timeoutではparserが走らない | runner/reconcilerのcavity3D pure log parserとallocation-local mesh auditorへ分離 |
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

全rankがshared filesystem上の一journalへ直接書かない。各nodeのsingle-writer collectorがlocal IPCで
rank recordを受け、expected local rankが揃った時点で一つのnode sidecarをshared storageへ
write+fsync+renameし、その後にwrapperへACKする。これによりsolver開始前にtimeout/node failureから
回収可能になる。runner reducerはPJM supervisor baseline environmentと各rank deltaからfull
environmentを再構成し、placement canonical arrayとともに一つのlogical producer fragmentへ変換する。
wrapper個々に重複するcollector lifecycle keyは作らず、node collector/reducer lifecycleとexpected
rank cardinalityを使う。

## validation fixture

最低限、次のfixtureをGit管理する。

- 公式valid log、step不足、solve不足、iteration不一致、NaN/Inf、truncated log
- ExecutionTime非単調、ClockTime同値、scientific notation、`1.2.3`、trim zero、score算出不能
- `bannerEnabled=false`、`writeHosts` 0/1/2、hostsum欠損、複数nProcs/Hosts block
- 一行に複数NaN/Inf、`End`で始まる別行、official INVALIDだがprocess exit 0
- 1/2/4 nodeのruntime headerとrank placement、host sum不一致
- Pstreamのstartup/runtime override、false、0、default、明示値、runtime change、banner無効event
- supervisor common environmentとrank追加/変更/削除deltaのfull byte snapshot復元
- 同じlogical dictを異なる挿入順で作ったcanonical JSON
- append直後crash、途中JSON line、missing fragment、同値replay、異値conflict
- archive upload成功、checksum不一致、唯一copyしかない状態

全fixtureで、raw row集合、completeness reason、comparison eligibility、公式parser parityを検査する。

## 未決定事項

score runに許す計測の上限はユーザー確認待ちである。決まるまでは、effective config、result、
phase boundaryの軽量local eventだけをscore候補へ入れ、GPU/CPU polling、profiler、verbose MPI debug、
full placement診断は`instrumentation.mode=audit`として別groupにする。閾値を文書へ仮置きして
comparison eligibleへ混入させない。
