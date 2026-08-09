# OpenFOAM v2 観測マップ

## この文書の役割

この文書は、各factについて「どこにある値を、誰が、いつ取得するか」を固定する実装契約で
ある。[概要計画](./experiment-metrics-v2-plan.md)が情報モデルと比較規則、
[contract schema handoff](./experiment-metrics-v2-contract-schemas.md)がfield-level shapeを定め、本書が実コード・
command・artifactへの配線を定める。

key registryへ入れるには、次の六項目を全て埋めなければならない。

1. authoritative source: object、structured file、command、またはsource symbol
2. producer: そのsourceを一度だけ読むowner
3. capture moment: 値が確定し、まだ失われていない時点
4. raw destination: `run/key/value`または耐久artifact
5. validation: 誤読、scope混同、部分取得を検出する規則
6. applicability: どのrun variantで取得するか

sourceの優先順位は、native object/API、machine-readable command/file、専用structured marker、
stable log parser、汎用text regexの順とする。選んだsourceをfixtureで確認する。通常runで同じ値を
上位・下位sourceから二重取得する必要はない。設定fileに書いた値を、実効値として扱ってはならない。

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
  qualification: package allocation source and each non-null child source/log/metrics in one artifact set
```

`run-manifest.json`で生成したrun IDを全producerが読む。各processで再計算しない。target hookは
local file descriptorまたはnode-local fileへ一つのstructured eventを書くのみで、metrics key、
BigQuery、retryを知らない。

## fact別の取得契約

表の「欠損」はraw valueへ空文字を入れる意味ではない。keyを出さず、consumerは`NULL`を返す。
required sourceならrun-level `collection_complete=false`とするだけで、原因、family status、欠損用placeholderを
作らない。非適用のprofile-only列も同じく`NULL`だけだが、`collection_complete`の判定対象にはしない。

| fact family | authoritative source | producer / capture moment | raw keyまたはartifact | validation | 欠損時の扱い |
|---|---|---|---|---|---|
| run/subject identity | runnerが一度生成したsubject/child manifests | `runner.manifest` / provision前 | raw tableの`run`列、regularは`control/run-manifest.json`、qualificationはparent `control/qualification-allocation-manifest.json`とchild manifest | manifestに汎用subject IDは保存せず、projection時にregular/child subject ID=run ID、allocation subject ID=allocation IDと導出。parent ordered childとchild armを照合し、block/order/replicateはallocation/protocol/array offsetから導出。PJM job IDを含めない | manifestなしでは投入しない |
| metrics contract | Git管理`openfoam-v2.toml`とlane/run variantが選んだexpected producer graph | `runner.manifest` / provision前 | `run.metrics_contract`、`control/contract.toml`、resolved laneと元lane path/SHA-256を含む`control/protocol.toml` | contract ID/content hash、exact producer version、view compatibility、mixed contract禁止、family/列の`applicable_run_variants` | required family欠損なら`collection_complete=false`。非適用列はNULL |
| source track / control plane | Gitのscore reference/profile base、実checkout head、purpose/qualification arm、protocol列挙control fileの実blob | `runner.manifest` / provision前、publisher / archive後 | compact source-track projection。実control-plane JCS hashはregular manifestまたはqualification parent manifest/allocation projectionが一度所有。qualification ONだけ`control/source-track-diff.json` | base/head規則、ON diff path集合=score bundle paths。control-plane filesは実checkoutからprotocol path順にhashし、protocol/contextの配列hashへ照合。childへ配列/hashを複写せずparent join | jobを投入しない |
| instrumentation bundle | Git管理purpose-neutral semantic bundle、build sidecar | `runner.manifest` / submit前 | `control/instrumentation-bundle.json`とsubject manifestのbundle SHA-256。actual argv/sinkはstage/artifact source | hook/probe/sample設定、wrapper executable hash、contract version、env capture scope、source path allowlist、relative argv template、sink source ID、solver process environment binding。sink path templateはcontract source registryだけが所有。referenceはempty、qualification ONと採用後benchは同じscore bytes | required source欠損なら`collection_complete=false`。profile-only bundleはbenchでproducerを持たない |
| instrumentation qualification decision | Git管理D-001 decision record | `runner.manifest` / bench submit前 | manifestのdecision ID/hashからdecision context viewへexact join。artifact copyは作らない | namespace protocolがlane/reference/workload/reference+score bundle/control-plane blobs/5-pair scheduleを所有し、decisionがqualified source diff、observed build-semantic pair、eligible childで一値のruntime MPI semantic、verdictを所有。対象subsetをdecisionへ再掲しない | 未回答はdecision NULL。profileはscoreへ混ぜない |
| scheduler join | `pjsub` argv/stdout/stderr/responseとPJM側job-entry file | `runner.submission` / pjsub前後、および`pjm.supervisor` / entry直後、finalizer / terminal後 | regularは`scheduler.submit_job_id`と`scheduler.job_entry_job_id`、qualificationはallocation projection。binding file/booleanは作らない | normalは二scalar、qualificationはallocation ID+ordered child IDsをquery時照合。childへ共通値を複写しない | 欠損値はNULL。不一致はcomparison不適格 |
| producer completion | producerのnormal closeとStageRunnerのchild outcome | `pjm.supervisor`または`StageRunner` / return後 | 完成producer fragment、stage termination | immutable contract/bundleからexpected fragment/fileを一回導出し`collection_complete`を決める。merge後fragmentは削除 | 欠損値はNULL。partial/tmpは手元に残り得るがartifact/mergeへ入れない |
| protocol assignment | Git管理protocolとrunnerの割当record | `runner.manifest` / job投入前 | regularはplanned-treatmentのblock ID/order、replicate index、planned group/set ID、dimensions。qualification childはtop-level pair/arm、planned set/dimensionsだけ | closed namespace+purpose+dimensionsからgroup/set IDを再計算。qualificationのblock ID/order/replicateはallocation ID、parent/set child offset、protocol pair offsetから導出しchildへ複写しない | purpose別comparison不適格。attempted groupやpairを観測値・順序から推測しない |
| qualification allocation | Git管理paired scheduleとrunnerが一度作るparent manifest | `runner.manifest` / pair submit前、`pjm.supervisor` / entry、`runner.postrun` / terminal後 | namespace、allocation ID、submission/job-entryの二job ID、scheduler request/accounting/terminal、observed control-plane hash、nullable job-entry env、minimal hardware、pair/ordered child IDs、OFF/ON order | parent/set/projectionのordered IDs、job-entryは実在時だけ照合。protocol pair arm order/offset、child arm/parent hash、parent↔child namespace/lane、OFF/ON bundle、request↔parentを一回照合 | arm間crash/未起動/未完成はsetのchild artifactをNULLにしてpair不適格。片armを別allocationへ再pairしない |
| repository/OpenFOAM/ThirdParty source | checkout直後、`.git`削除前の各repositoryで実行する`git rev-parse --show-object-format`と`git rev-parse HEAD` | `build.packager` / build開始前 | `control/build-sidecar.json`、比較用source commit索引 | repository ID、`sha1|sha256`、algorithmに対応する40/64-hex full OIDをrole別に保存。moving branch名を使わない | build artifactを公開しない |
| toolchain/build | build時の`mpiicx --version`、`mpiicpx --version`、`mpirun --version`、`readelf --dynamic <icoFoam>`、完成binary/archive。provision時の`realpath`/hash/`ldd` | `build.packager` / archive完成時、`pjm.supervisor` / provision後、publisher / archive後 | `control/build-sidecar.json`、`control/build-provision-validation.json`、`openfoam_build_provenance_raw_v2`、`openfoam_build_provisions_raw_v2` | six ELF executableとarchive-owned closure、source identityを持つprobe、実MPI launcher/libmpiを一度seal。run-time MPI semanticはmpirun hash+version output+libmpi hashで比較。profileはsystem `perf` hash/versionも同じprovision recordが一度所有 | build不完全ならreuseしない。run時欠損はNULL |
| actual workload | setup後にsolverが読む実caseのworkload-defining member bytes | regularとqualification各childの`pjm.supervisor` / 各case setup完了後、blockMesh前。publisher / archive後 | `source/workload-manifest.json`、exact `source/workload/<path>`、`openfoam_workload_manifests_raw_v2`、`openfoam_workload_members_raw_v2` | exact allowlistは`0/U`、`0/p`、`constant/transportProperties`、`system/controlDict`、`system/fvSchemes`、`system/fvSolution`、`system/blockMeshDict`。artifact manifestはpath/size/SHA-256、member relationはpath/exact content bytesだけを所有しsize/hashはview派生。OFF/ON別caseを各childが観測し、両identityとexpected identityを照合 | 欠損・member差・hash不一致はcomparison不適格 |
| full job-entry environment | `env -0`相当のNUL区切りprocess environment | `pjm.supervisor` / script entry直後、module/unset前 | regularは`env.job_entry.*`と`source/env/job-entry.snapshot`、qualificationはparent snapshotとallocation env projection | byte-exact name escapeと全value Base64、entry count fixture。child rawへ複写せずEnvironmentがblock/allocation join | 欠損値はNULL、requiredなら`collection_complete=false` |
| full exec environment | supervisor baselineと各solver wrapperのbyte environment | applicable score bundle/profile/qualification ONの`pjm.supervisor` + `exec.wrapper`、runner reducer / mpirun直前、各rank exec直前、terminal後 | `env.host_exec.common.*`、`source/env/host-exec.snapshot`、`source/env/rank-<rank>.delta.json` | rank別source file、`os.environb`相当、common+delta full復元、expected全rank | 欠損値とqualification OFF consumerはNULL。requiredなら`collection_complete=false` |
| scheduler request | Git管理lane、PJM script identity、runnerが実行するexact `pjsub` argv | `runner.submission` / submit直前 | regularは`run`の`scheduler.request`、qualificationはallocation artifact/raw projection | lane.nodes/ranks/rscgrp/transportとscript/argv overrideを照合。child rawへ複写しない | 欠損値はNULL。invalidなら投入しない |
| scheduler accounting | `pjstat --history -S --choose jid,st,sdt,elp,ec,sn,pc,nnumu,mmszu,uctmut,sctmut --data --delimiter "\t" <job>` | `runner.postrun` / terminal state後 | regularは`scheduler.accounting`と`source/scheduler/pjstat.{stdout,stderr}`/`pjstat-version.txt`、qualificationはparent raw/allocation projection | field list/unit/job ID固定、requestedとの一致はview判定。childはallocation IDでjoin | 取得できないfieldはNULL。host/rank/rscgrpを捏造しない |
| observed topology/placement | solverと同じMPI launch内のglobal/local rank、`hostname`、CPU/NUMA affinity | applicable score bundle/profile/qualification ONの`exec.wrapper`、runner reducer / exec直前、terminal後 | `source/placement/rank-<rank>.json`と`parallel.rank_placement`、consumer `openfoam_rank_placements_v2` | rank別source file、別`mpirun`禁止、lane canary自身で確認するrank env、filename/global rank/run ID、global rank連続集合、hostname内local size consensusとlocal rank連続集合 | 固定幅consumerは欠損・qualification OFFでNULL、long consumerは0行。required欠損なら`collection_complete=false` |
| actual launch | stage wrapperが`subprocess`へ渡すargv/cwd/stderr mode | `StageRunner` / spawn直前 | `run.stage.<name>.launch` | shell再構成文字列ではなくclosed object。全OpenFOAM executable sub-argvに`-fileHandler uncollated`をexactly once要求し、solver専用subset keyは作らない | stage未開始ならNULL |
| run timing/outcome | supervisorのUTC clock、monotonic clock、最終exit | `pjm.supervisor` / regularはPJM entry→compute回収終了、qualificationは各child orchestration直前→そのchild回収終了 | `run.started_at`、`run.finished_at`、`run.elapsed_sec`、`run.exit_code` | wall timestamp pairとmonotonic elapsedを別clockとして保持。`run_outcome`はexit codeからview導出。allocation共通のscheduler request/accounting/terminalは親projだけが所有し、別allocation lifecycleは作らない | 保存できたterminationとstage outcomeから中断を表す |
| stage outcomes | supervisorの同じmonotonic clockとraw child wait status | `StageRunner` / spawn直前とwait直後 | `perf.stage.<name>.wall_time_sec`、`run.stage.<name>.termination`、regularだけ`perf.pipeline.wall_time_sec` | exit/signal/spawn_errorをJSONで区別。qualification pipelineは二child準備時間が混ざるため非適用NULL | termination objectで中断を表現 |
| minimal hardware/settings | allocated nodeごとの`LC_ALL=C lscpu --json`とkernel/cpufreq/boost/NUMA/memory設定 | internal `collect` probe。1 nodeは直接、multi-nodeはtimed solver外one-shot / regularはrun前、qualificationはarm 1前。publisher / archive後 | node sourceとsubject-keyed raw relation。regular launchはrun stage、qualification launch/terminationはparent `control/minimal-hardware-stage.json`/allocation projectionが一度所有 | subject kind/ID/output rootをexact argvで渡す。sourceはraw lscpu/settings、projectionはCPU identity/settings。node ordinal順consensusはview派生 | 欠損値はNULL、requiredなら`collection_complete=false` |
| full hardware topology（profile only） | minimal hardwareに含まれない各NUMA nodeの`cpulist`/`meminfo`とpost-run `/proc/meminfo` | `postrun.auditor` / profile solver終了後に`mpirun -np <nodes> -ppn 1 <provision>/bin/capture-hardware --mode profile-postrun --subject-kind regular_run --subject-id <run> --output-root <run>/profile/raw/hardware --node-ordinal-from-env PMI_RANK`、publisher / archive後 | `profile/raw/hardware/node-<ordinal>/{proc-meminfo.txt,numa/...,capture.json}`と`openfoam_profile_hardware_raw_v2` | hostnameを含むcaptureをminimal hardwareの`(node_ordinal,hostname)`と照合。meminfo key/kB→bytes、cpulist canonicalization、exact file membershipをfixture化。publisherがsource member/hash付きrecordを転記 | 欠損値はNULL。bench consumerもNULL |
| mesh topology | exact buildにlinkした`<provision>/bin/mesh-facts` probeとOpenFOAM付属`checkMesh` raw log | `StageRunner` / regularはsolver後に一case、qualificationはarm 2終了後に両child caseへ各一回 | `source/mesh/mesh-topology.json`、`logs/checkMesh.log`、`mesh.topology` | build sidecar/provision validationのrealpath/hashと照合。exact argvはresolved absolute path + `-case <case> -fileHandler uncollated -constant` | 欠損値はNULL、requiredなら`collection_complete=false` |
| requested partition | 実際に使用したgenerated `decomposeParDict` | `pjm.supervisor` / decomposePar spawn直前 | `source/mesh/decomposeParDict`と`mesh.partition.requested={source_sha256,subdomains,method}` | 実argvが指すfile bytesをcopyして同じbytesからrecordを作る | 欠損値はNULL、stageは失敗 |
| observed partition | serial/processor mesh bytes、processor addressing、decompose/check output | native `partition-audit` / regularはsolver後に一case、qualificationはarm 2終了後に両child caseへ各一回 | `source/mesh/partition-observed.json`、`logs/checkMesh.log`、`mesh.partition.observed` | build/provisionでhash検査したOpenFOAM native utilityを`-case ... -fileHandler uncollated -constant -output ...`の一経路だけ使う。serial meshを一度、processor dirをrank順に処理し、global cell一回、owner/neighbourに基づくglobal face出現数、peer間face ID/符号、point unionとface vertex cycle、boundary mapping、expected subdomain集合を検査。64M-cell canaryでpeak RSS <= node memory 25%。summaryはview派生 | 欠損値はNULL。requiredなら`collection_complete=false`。fallback parserなし |
| runtime header | OpenFOAM startupが出すBuild/Arch/Exec/fileHandler/nProcs/Hosts | `runner.log_parser` / PJM terminal後、`logs/log.icoFoam`があれば | `logs/log.icoFoam`から`solver.runtime_header` | `argList.C` symbol/format golden、Hostsなしは`[]`、presentならhost sum=nProcs、複数blockはexact一致時だけreduce、actual fileHandler=uncollated。Exec stringをargvへ逆変換しない | 欠損値はNULL。requiredなら`collection_complete=false` |
| Pstream startup-applied | `UPstream::init()`、node comm state、`attachOurBuffers()`後の実buffer | applicable score bundle/profile/qualification ONの`openfoam.startup` -> rank別JSONL、`runner.pstream_parser` / attach完了後emit、terminal後reduce | `solver.pstream.startup_applied.rank.<rank>` | configured/clamped/attached byte、node control、expected全rank、banner非依存 | 欠損値はNULL。qualification OFFもNULL |
| Pstream runtime-current | `Time::setControls()`でcase override済みの登録switch | applicable score bundle/profile/qualification ONの`openfoam.runtime_config` -> rank別JSONL、`runner.pstream_parser` / time loop前emit、terminal後reduce | `solver.pstream.runtime_current.rank.<rank>` | floatTransfer、node controls、usingNodeComms等をsymbol対応、false/0明示、expected全rank | 欠損値はNULL。qualification OFFもNULL |
| Pstream runtime changes | `Time::readModifiedObjects()`からの実control変更 | applicable score bundle/profile/qualification ONの`openfoam.runtime_config` -> rank別JSONL、`runner.pstream_parser`がterminal後に一度reduce | `solver.pstream.change_events.rank.<rank>` ordered array | startup/runtime sentinelが揃いchange 0件だけ`[]`、complete-line/event count/sequence/old/new一致 | 欠損値はNULL。qualification OFFもNULL |
| time-step timing | 保存済みsolver logの`Time =`と同一stepの`ExecutionTime = ... ClockTime = ...` | `runner.log_parser` / PJM terminal後 | `solver.step_timings` | 原lexemeとnullable numeric、全match順序。単調性/有限性はcomparison evaluator | 得られたcomplete recordだけ保存 |
| pressure solves | 保存済みsolver logの各`Solving for p` record | `runner.log_parser` / PJM terminal後 | `solver.pressure_solves` | initial/final residual/iterationsの原lexemeとparsed valueを同じrecordに保持 | 得られたcomplete recordだけ保存 |
| official markers | complete solver logとcanonical official evaluator | `runner.log_parser` / PJM terminal後 | `solver.log_markers`、official validityはview | shell validity semanticsのgolden parity後、固定locale/decimal evaluatorを共有 | source不足はNULL、公式規則不成立は`official_log_valid=false` |
| primary score inputs | `solver.step_timings`の先頭/末尾ExecutionTimeと公式固定定数 | BigQuery view / query時 | rawへscoreを重複保存しない | fixed decimal/roundingのcanonical evaluatorと`64,000,000 * 4 / trim`をgolden照合 | source record不足ならNULL |
| perf stat（profile only） | resolved/hash済み`perf`によるrank別`perf stat --no-big-num -x, -o <profile>/perf/rank-<rank>.csv -e cycles,instructions,branches,branch-misses,cache-misses`。versionはbuild-provision sourceが所有 | hash済みrank wrapper / 各solver rank process treeの開始から終了、`runner.perf_parser` / terminal後 | wrapperは`profile/raw/perf/rank-<rank>.csv`、parserは`profile.perf_stat.rank.<rank>` fragment、consumerは`openfoam_perf_counters_v2` | wrapperは`PMI_RANK`とexpected rank範囲を検査。各CSVは固定7列、exact five events/順序、filename/rank/run binding。viewはprofile run×rank×event skeletonへLEFT JOINし、running ns/percentからenabled nsだけを導出 | profileの欠損値は理由なしNULL。benchには非適用placeholder行を作らない。perfなしの再実行はしない |
| artifact identity | localで作ったrun bundle、qualification allocation archive/set manifest、profileだけのraw tar、build sidecar | `runner.packager` / GitHub Artifact upload前 | `archive-staging/bundle.manifest.json`、`artifact-manifest.json`、qualificationの`qualification-set-manifest.json`。hashはartifact dimension、URIはworkflow operational join | OpenFOAM基準の外側pathでallocationとchildを分離。run bundleはsource/log/result、profile tarはrank別perf CSVと追加hardware rawだけ。perf versionはbuild-provision sourceだけが所有し、byteを別tarへ重複しない | uploadできなければworkflow failure。consumer値はNULL |
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
   `mpiBufferSize`のaccepted signed value、正整数として採用された`MPI_BUFFER_SIZE`、clamp後の実`attachedBufLen`を記録する。
2. runtime-current: `Time` constructorの`setControls()`後、time loop前。`floatTransfer`、
   `nProcsSimpleSum`、`nProcsNonblockingExchange`、`tuning_NBX_`、`PstreamBuffers::algorithm`、
   `defaultCommsType`、`nPollProcInterfaces`、`maxCommsSize`、current `nodeCommsControl_`、
   `nodeCommsMin_`、`topologyControl_`、`usingNodeComms(worldComm)`を記録する。
3. runtime change: `Time::readModifiedObjects()`で上記値が実際に変わった時だけold/new eventを出す。

hookは`bannerEnabled()`の外に置き、全rankがrank-scoped eventを出す。version、producer、scope、
payloadを持つが、event write失敗でsolverの数値処理やexit codeを変えない。in-process hookには
別のsupervisor eventを偽造せず、expected event欠損としてpost-run completenessに出す。対象versionごとに
symbolとfull commitをregistry source欄へ固定し、line番号だけを契約にしない。
唯一のsink bindingは`OPENFOAM_METRICS_PSTREAM_DIR`で、rank確定後に`rank-<rank>.jsonl`へline-buffered appendする。

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

D-003は初版からlane-driven multi-node対応とし、Genkai 1/2/4 nodeを実機conformance対象にすることで確定した。
各laneはnode数だけでなく、rank数、resource group、transport policyを一度所有する。required logical producerは
contractのvariant applicability、instrumentation modeはprotocol/bundle selectionだけが所有する。rank数をcore数から
暗黙推定しない。runnerはlane、PJM script identity、
exact `pjsub` argvを一つのrequest recordへsealする。初版canaryは総rank数120のbalanced配置
`openfoam-genkai-n1-r120`、`openfoam-genkai-n2-r120`、`openfoam-genkai-n4-r120`で、順に120、60、30 rank/node、
resource groupは`a-batch`、decompositionはScotch 120、launcherは`mpirun -np 120 -ppn <120/nodes>`とする。
1 nodeだけ`I_MPI_FABRICS=shm`、2/4 nodeは`I_MPI_FABRICS=shm:ofi`とする。1 nodeは現行64M workloadで実証済み、
2 nodeは旧workloadで基盤だけ実証済み、4 nodeは未実証なので、後二者に性能期待値を置かず一回の通常canaryで
取得成否を確認する。自動retry、代替lane、node数別collectorは作らない。validationは次の独立sourceを照合する。

```text
lane.nodes = request.nodes = accounting.nnumu
           = distinct(runtime_header.hosts) = distinct(placement.hosts)
lane.ranks = decomposeParDict.numberOfSubdomains = runtime_header.nProcs
           = runtime_header.host_rank_sum = placement record count
```

accounting commandが返さないhost/rank/resource-group fieldはaccounting factに含めない。multi-node laneで
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
- 各in-scope laneのruntime headerとrank placement、host sum不一致
- Pstreamのstartup/runtime override、false、0、default、明示値、runtime change、banner無効event
- protocol workload fixtureと、setup後のcase member一つを変えた不一致fixture
- variant applicability grid：profile-only collectorのprofile失敗、bench非適用、qualification OFF非適用はいずれもconsumer値がNULL。required source欠損時だけrun-level `collection_complete=false`
- compact source trackのbench/profile/qualification OFF/ON、base非ancestor、score bundle source path外差分、control-plane blob差、checkout tree不一致、同bundleでbase/workload/toolchainだけ変更、moving branch名が同じでもcommitが異なるfixture
- qualification allocationの一pair二child、二pair混入を全pair reject、child順/arm不一致、別allocationへの再pair、arm間crash、片child未起動/metrics未完成fixture
- instrumentation bundleのhook/sample interval一つだけを変えたhash差fixture
- D-001 decisionの未存在、non-adopt、対象pair不一致、adopt完全一致fixture
- supervisor common environmentとrank追加/変更/削除deltaのfull byte snapshot復元
- 同じlogical dictを異なる挿入順で作ったcanonical JSON
- 正常close、program failure、完成fragment欠損、異値conflict。途中fileはmerge/artifactへ入れない
- OpenFOAM artifact移管のhappy path、GitHub upload失敗、SCP失敗

全fixtureで、raw row集合、`collection_complete`、comparison eligibility、公式parser parityを検査する。

## 未決定事項

bench/profile分離と、取得できなかった値およびprofile-only metricは値をNULLにするだけで原因/status/欠損用recordを
作らないこと、極稀な失敗を救う多段safeguardは作らないことはユーザー確定済みである。
D-003は2026-08-09にユーザー回答「基本的にはマルチノード対応型の収集」で確定した。OpenFOAMでは上記の
1/2/4-node canaryを実機conformance対象とし、Qwenでも同じlane-driven cardinality原則を使う。残る質問は
Qwen profiler D-004、最後に確定laneごとの最小bench bundleの統計上限D-001である。決まるまではprofiler、
polling、verbose MPI/Pstream trace、full placement診断はprofile-only、未qualificationのinline eventはaudit-onlyとする。
未実証2/4-node canaryは成功扱いせず、実観測が揃ったrunだけをscore/qualification eligibleにする。
