# OpenFOAM experiment metrics v2 キーカタログ

## この文書の読み方

この文書は、2026-08-10 時点の v2 plan、observation map、contract schemas にある
収集予定値を、v1 の「英小文字・数字・アンダースコアを使い、カテゴリをピリオドで
階層化する」規則へ揃えた一覧である。v2 の構造化 record 内の field 名がそのまま
BigQuery key になるとは限らないため、表の「キー」を検索・比較用の標準名とし、元の
record field は「収集方法」に記す。

- `<name>`、`<rank>`、`<node>`、`<ordinal>` は実値へ置換する。
- `{a,b}` は同じ prefix に属する全 leaf を列挙した省略表記である。
- `[]` は順序を保つ long relation または配列要素であり、1つの scalar value へ潰さない。
- 「raw」は collector が観測する値、「派生」は view/reducer で算出する値である。
- `schema_version`、record ID、path、argv、member hash など、観測の再現性に必要だが
  科学・性能比較用ではない field は最後の lineage 表に分ける。
- v2 master docs を内容の正本とし、v1 文書はキー階層の命名だけに参照する。
- 実行設定をまとめるID/objectは作らない。`nodes`、`ranks`、`resource_group`、`transport_policy`は
  独立keyで保持し、スプレッドシートでも一key一列にする。

## 1. Run、stage、artifact

| キー | 意味 | 収集方法（コマンド／関数） | 適用・種別 |
|---|---|---|---|
| `run.identity.{run_id,run_purpose,repository_id}` | run ID、用途、repository | runner が Git 管理の run manifest を読み `identity_projection/v1` で投影 | bench/profile、raw |
| `run.instrumentation_bundle_sha256` | 適用 instrumentation bundle identity | run manifest と bundle manifest を照合 | bench/profile、raw |
| `run.{started_at,finished_at}` | run の開始・終了 UTC 時刻 | PJM supervisor の wall clock | 全 variant、raw |
| `run.elapsed_sec` | supervisor 範囲の run 経過秒 | `time.monotonic_ns()` 相当の開始・終了差 | 全 variant、raw |
| `run.exit_code` | run の終了コード | supervisor が pipeline 終了時に確定 | 全 variant、raw |
| `run.outcome` | `succeeded` / `failed` | `run.exit_code == 0` から view で導出 | 全 variant、派生。raw には保存しない |
| `run.stage.<name>.launch.{argv,cwd,stderr_mode}` | stage の実起動条件 | `StageRunner` が shell を介さず spawn する直前に argv、cwd、stderr 処理を記録 | 対象 stage、raw |
| `run.stage.<name>.termination.kind` | `exit` / `signal` / `spawn_error` | `StageRunner` の spawn/wait 結果を closed union として記録 | 対象 stage、raw |
| `run.stage.<name>.termination.code` | 通常終了時の exit code | `wait` の process outcome | `kind=exit` のみ、raw |
| `run.stage.<name>.termination.signal` | signal 終了時の signal 番号 | `wait` の process outcome | `kind=signal` のみ、raw |
| `perf.stage.<name>.wall_time_sec` | stage 単位の外側 wall time | `StageRunner` の spawn 直前から child wait 完了までを monotonic clock で計時 | 対象 stage、raw |
| `perf.pipeline.wall_time_sec` | mesh 生成開始から solver wait 完了まで | PJM supervisor が `blockMesh` 直前と solver wait 直後を monotonic 計時 | regular bench/profile、raw |
| `collection_complete` | 必要なproducer/fileが全部揃ったか | finalizer が実装上のexpected setとobserved setを比較 | bench/profile、raw bool。理由別fieldは作らない |
| `artifact.build_manifest_sha256` | build manifest の identity | packager が canonical manifest を SHA-256 | 全 variant、raw lineage key |
| `artifact.instrumentation_bundle_sha256` | instrumentation bundle の identity | packager が bundle manifest を SHA-256 | 全 variant、raw lineage key |
| `source.track.{head_commit,score_reference_commit,profile_base_commit,manifest_sha256}` | source track の head/base commit と manifest identity | subject manifest の `source_track` を Git object と照合して projection | variant 依存、raw projection |
| `source.{openfoam_commit,thirdparty_commit}` | build に使った OpenFOAM/ThirdParty commit | build sidecar と source repository Git OID を照合 | 全 solver run、raw provenance |
| `artifact.build_artifact_sha256` | build artifact identity | build sidecar | bench/profile、raw lineage |
| `workload.{id,manifest_identity}` | workload logical ID と exact 7-member identity | workload manifest を JCS SHA-256 | workload 適用 run、raw projection |

`<name>` の標準 stage 集合は `block_mesh`、`decompose_par`、`solver`、`check_mesh`、
`mesh_facts`、`partition_audit` である。minimal hardware と profile hardware/perf の
capture stage は適用 variant だけ追加する。

| stage別の完全なキー展開 | 収集方法 |
|---|---|
| `run.stage.block_mesh.{launch,termination}` / `perf.stage.block_mesh.wall_time_sec` | `StageRunner` の spawn/wait |
| `run.stage.decompose_par.{launch,termination}` / `perf.stage.decompose_par.wall_time_sec` | 同上 |
| `run.stage.solver.{launch,termination}` / `perf.stage.solver.wall_time_sec` | 同上 |
| `run.stage.check_mesh.{launch,termination}` / `perf.stage.check_mesh.wall_time_sec` | 同上 |
| `run.stage.mesh_facts.{launch,termination}` / `perf.stage.mesh_facts.wall_time_sec` | 同上 |
| `run.stage.partition_audit.{launch,termination}` / `perf.stage.partition_audit.wall_time_sec` | 同上 |
| `run.stage.minimal_hardware_capture.{launch,termination}` / `perf.stage.minimal_hardware_capture.wall_time_sec` | 適用 variant の minimal hardware capture |
| `run.stage.profile_hardware_capture.{launch,termination}` / `perf.stage.profile_hardware_capture.wall_time_sec` | profile-only hardware capture |
| `run.stage.network_imb_mpi1.{launch,termination}` / `perf.stage.network_imb_mpi1.wall_time_sec` | solver成功後のIMB-MPI1。失敗してもsolver成功は維持 |

各 `launch` は `{argv,cwd,stderr_mode}`、各 `termination` は `kind` と union に応じた
`code` または `signal` まで展開する。

## 2. Scheduler と environment

| キー | 意味 | 収集方法（コマンド／関数） | 適用・種別 |
|---|---|---|---|
| `scheduler.request.nodes` | 要求 node 数 | 実行設定と実 `pjsub` request から記録・照合 | 全run、raw。独立列 |
| `scheduler.request.ranks` | 要求 MPI rank 数 | 実行設定と実 `mpirun` request から記録・照合 | 全run、raw。独立列 |
| `scheduler.request.resource_group` | PJM resource group | 実行設定と実submit argv | 全run、raw。独立列 |
| `scheduler.request.transport_policy` | MPI transport policy | 実行設定とlaunch-effective環境を照合 | 全run、raw。独立列 |
| `scheduler.request.subject_manifest_sha256` | submit 対象 manifest | submission runner が file bytes を SHA-256 | 全run、raw lineage |
| `scheduler.request.pjm_script.{repository_path,sha256}` | 使用した PJM script と hash | 実 submit 前に repository file を hash | 全run、raw lineage |
| `scheduler.request.argv` | 実際の submit argv | submission runner が argv 配列を保存 | 全run、raw control field |
| `scheduler.submit_job_id` | `pjsub` が返した job ID | submission result parser | bench/profile、raw。欠損時は key absent |
| `scheduler.job_entry_job_id` | job entry で見えた job ID | `PJM_JOBID` / `PJM_JOB_ID` の job-entry snapshot | 同上、raw。欠損時は key absent |
| `scheduler.accounting.{jid,st,sdt}` | PJM job ID、terminal state、開始時刻の raw 語彙 | `pjstat --history -S --choose jid,st,sdt,elp,ec,sn,pc,nnumu,mmszu,uctmut,sctmut --data --delimiter "\t" <job-id>` | bench/profile、raw |
| `scheduler.accounting.elp.{lexeme,seconds}` | scheduler elapsed の raw 表現と秒 | 同 `pjstat` 行を固定 column parser で解析 | 同上、raw。parse 失敗時 `seconds=null` |
| `scheduler.accounting.ec.{lexeme,value}` | scheduler exit code の raw 表現と整数 | 同上 | 同上、raw nullable numeric |
| `scheduler.accounting.sn.{lexeme,value}` | signal/status 数値の raw 表現と整数 | 同上 | 同上、raw nullable numeric |
| `scheduler.accounting.pc.{lexeme,value}` | PJM code の raw 表現と整数 | 同上 | 同上、raw nullable numeric |
| `scheduler.accounting.nnumu.{lexeme,value}` | allocation node 数の raw 表現と整数 | 同上 | 同上、raw nullable numeric |
| `scheduler.accounting.mmszu.{lexeme,bytes}` | 最大 RSS の raw 表現と bytes | 同上。括弧内 byte 値を parse | 同上、raw nullable numeric |
| `scheduler.accounting.uctmut.{lexeme,seconds}` | user CPU time | 同上。millisecond 表現を秒へ変換 | 同上、raw nullable numeric |
| `scheduler.accounting.sctmut.{lexeme,seconds}` | system CPU time | 同上。millisecond 表現を秒へ変換 | 同上、raw nullable numeric |
| `env.job_entry.<escaped_name>` | job entry 環境 | name/value の `name\0value\0` snapshot を name byte 順に保存し value を Base64 化 | scheduler entry、raw dynamic family |
| `env.host_exec.common.<escaped_name>` | 全 rank 共通の launch-effective host 環境 | rank wrapper が全環境を byte-exact snapshot、common/delta reducer で共通分を投影 | bench/profile、raw projection |
| `env.host_exec.rank.<rank>.delta.<escaped_name>` | rank 固有の追加・変更環境値 | 同 rank snapshot と common snapshot の byte-exact delta | 同上、raw projection |
| `env.host_exec.rank.<rank>.removed_names` | common から当該 rank で消えた環境変数名 | `removed_names_b64` を name byte 順の可逆 list として投影 | 同上、raw projection |

## 3. Platform、hardware、rank placement

| キー | 意味 | 収集方法（コマンド／関数） | 適用・種別 |
|---|---|---|---|
| `hardware.node.<ordinal>.hostname` | node hostname | minimal hardware probe の `gethostname()` | bench/profile、raw |
| `hardware.node.<ordinal>.lscpu_json` | CPU topology の raw JSON | `LC_ALL=C lscpu --json` | 同上、raw nullable object |
| `hardware.node.<ordinal>.cpu_identity.{architecture,model_name,vendor_id,cpu_family,model,stepping}` | CPU identity | `lscpu_json` の対応 label を parser で投影 | 同上、派生 projection nullable |
| `hardware.node.<ordinal>.cpu_identity.{physical_cores,numa_nodes}` | physical core 数、NUMA node 数 | `lscpu_json` の socket/core/node 情報から導出 | 同上、派生 projection nullable |
| `hardware.node.<ordinal>.platform.kernel_release` | kernel release | `/proc/sys/kernel/osrelease` | 同上、raw nullable |
| `hardware.node.<ordinal>.platform.{online_cpus,isolated_cpus,nohz_full_cpus}` | online/isolated/nohz-full CPU 集合 | `/sys/devices/system/cpu/{online,isolated,nohz_full}` を canonical range parser で読む | 同上、raw nullable、空集合は `[]` |
| `hardware.node.<ordinal>.memory.{total_bytes,hugepage_size_bytes,hugepages_total}` | node memory と hugepage 設定 | `/proc/meminfo` を byte 単位へ変換 | 同上、raw nullable |
| `hardware.node.<ordinal>.numa_balancing_enabled` | automatic NUMA balancing | `/proc/sys/kernel/numa_balancing` | 同上、raw nullable |
| `hardware.node.<ordinal>.cpu_boost.{source_path,raw,enabled}` | CPU boost の取得元、raw 値、有効状態 | cpufreq `boost`、なければ `intel_pstate/no_turbo` | 同上、raw nullable |
| `hardware.node.<ordinal>.cpufreq_policy.<policy_id>.{related_cpus,driver,governor,min_hz,max_hz}` | policy 別 CPU、driver、governor、周波数範囲 | `/sys/devices/system/cpu/cpufreq/policy*`。kHz は Hz へ変換 | 同上、raw nullable |
| `parallel.rank.<rank>.{global_rank,local_rank,local_size}` | global/local rank と node 内 rank 数 | rank wrapper が `PMI_RANK`、`MPI_LOCALRANKID` など launch-effective 値を記録 | bench/profile、raw |
| `parallel.rank.<rank>.hostname` | rank 実行 host | rank wrapper の `gethostname()` | 同上、raw |
| `parallel.rank.<rank>.cpu_affinity` | rank の CPU affinity 集合 | `os.sched_getaffinity(0)` | 同上、raw ordered unique integers |
| `parallel.rank.<rank>.numa_mems` | rank に許可された NUMA memory node | `/proc/self/status` の `Mems_allowed_list` | 同上、raw nullable |

## 4. Mesh と partition

| キー | 意味 | 収集方法（コマンド／関数） | 適用・種別 |
|---|---|---|---|
| `mesh.topology.{cells,faces,points,internal_faces}` | mesh の cell、face、point、internal face 数 | native `mesh-facts -case <case>` で OpenFOAM API から取得 | 全 solver run、raw |
| `mesh.partition.requested.source_sha256` | 実際に使った `decomposeParDict` の byte identity | `decomposePar` 直前に実 argv が参照する file を SHA-256 | 全 solver run、raw lineage |
| `mesh.partition.requested.subdomains` | 要求 subdomain 数 | 同 dictionary の `numberOfSubdomains` を native/dictionary parser で読む | 全 solver run、raw |
| `mesh.partition.requested.method` | partition method | 同 dictionary の `method` を読む | 全 solver run、raw。現 contract は `scotch` |
| `mesh.partition.serial.{points,faces,owner,neighbour,boundary}.{size_bytes,sha256}` | serial polyMesh 5 member の identity | native `partition-audit` が各 file を hash | 全 solver run、raw lineage |
| `mesh.partition.rank.<rank>.cell_count` | subdomain 別 cell 数 | native `partition-audit` が processor mesh を走査 | 全 solver run、raw |
| `mesh.partition.rank.<rank>.mesh.{points,faces,owner,neighbour,boundary}.{size_bytes,sha256}` | processor mesh 5 member の identity | `partition-audit` | 全 solver run、raw lineage |
| `mesh.partition.rank.<rank>.addressing.{cell,face,point,boundary}.{size_bytes,sha256}` | 4 addressing file の identity | `partition-audit` | 全 solver run、raw lineage |
| `mesh.partition.interface.<lower_rank>.<upper_rank>.face_count` | rank pair 間 interface face 数 | `partition-audit` が processor boundary を監査 | 全 solver run、raw |
| `mesh.partition.requested_identity` | requested partition identity | `mesh.partition.requested.source_sha256` をそのまま consumer へ投影 | query/view 用 projection。再 hash しない |
| `mesh.partition.observed_identity` | observed partition の canonical identity | serial/subdomain/interface audit object を JCS SHA-256 | query/view 用 projection |

## 5. Solver runtime、log、結果

| キー | 意味 | 収集方法（コマンド／関数） | 適用・種別 |
|---|---|---|---|
| `solver.runtime_header.{build,arch,exec,file_handler,nprocs}` | OpenFOAM banner の build、arch、実行名、file handler、MPI rank 数 | 保存済み solver log の canonical official-log parser | 全 solver run、raw |
| `solver.runtime_header.hosts[]` | banner の `{hostname,ranks}` long relation | solver log の `Hosts` block を parse。hostnameをkey segmentへ埋めず、記載なしは空 relation | 全 solver run、raw |
| `solver.pstream.startup_applied.rank.<rank>.{node_comms_control,node_comms_min,using_node_comms,num_nodes,topology_control}` | `UPstream::init()` 後の実適用通信設定 | OpenFOAM Pstream hook が rank JSONL event を生成 | bench/profile、raw |
| `solver.pstream.startup_applied.rank.<rank>.configured_mpi_buffer_value` | 設定された MPI buffer 値 | 同 hook。signed 値をそのまま保存 | 同上、raw |
| `solver.pstream.startup_applied.rank.<rank>.environment_mpi_buffer_bytes_applied` | 環境から実適用された MPI buffer bytes | 同 hook と launch-effective env | 同上、raw nullable |
| `solver.pstream.startup_applied.rank.<rank>.attached_buffer_bytes` | clamp 後に実際に attach した bytes | `attachOurBuffers()` 後の hook | 同上、raw |
| `solver.pstream.runtime_current.rank.<rank>.{float_transfer,using_node_comms}` | runtime の transfer/node comms bool | `Time::setControls()` 後、time loop 前の hook | 同上、raw |
| `solver.pstream.runtime_current.rank.<rank>.{n_procs_simple_sum,n_procs_nonblocking_exchange,tuning_nbx,pstream_buffers_algorithm}` | runtime の Pstream integer tuning | 同 hook | 同上、raw |
| `solver.pstream.runtime_current.rank.<rank>.default_comms_type` | default communications type | 同 hook | 同上、raw enum |
| `solver.pstream.runtime_current.rank.<rank>.{n_poll_proc_interfaces,max_comms_size,node_comms_control,node_comms_min,topology_control}` | polling、message size、node/topology tuning | 同 hook | 同上、raw |
| `solver.pstream.change_events.rank.<rank>` | runtime dictionary 再読込による設定変更の順序付き `{field,old,new}` array | `Time::readModifiedObjects()` hook。sentinel が揃い変更0件なら空 array | 同上、raw ordered events |
| `solver.step.<ordinal>.simulation_time.{lexeme,value}` | step の simulation time raw/数値 | solver log の `Time =` を parse | 全 solver run、raw nullable numeric |
| `solver.step.<ordinal>.execution_time.{lexeme,sec}` | OpenFOAM `ExecutionTime` raw/秒 | 同一 step の timing line を parse | 全 solver run、raw nullable numeric |
| `solver.step.<ordinal>.clock_time.{lexeme,sec}` | OpenFOAM `ClockTime` raw/秒 | 同上 | 全 solver run、raw nullable numeric |
| `solver.pressure_solve.<ordinal>.simulation_time.{lexeme,value}` | `p` solve 時点の simulation time | `Solving for p` line と直前の time marker | 全 solver run、raw nullable numeric |
| `solver.pressure_solve.<ordinal>.initial_residual.{lexeme,value}` | pressure initial residual | `Solving for p` line parser | 全 solver run、raw nullable numeric |
| `solver.pressure_solve.<ordinal>.final_residual.{lexeme,value}` | pressure final residual | 同上 | 全 solver run、raw nullable numeric |
| `solver.pressure_solve.<ordinal>.iterations.{lexeme,value}` | pressure iteration 数 | 同上 | 全 solver run、raw nullable numeric |
| `solver.log.end_count` | `End` marker 数 | canonical official-log parser | 全 solver run、raw |
| `solver.log.badnum_line_count` | NaN/Inf を含む line 数 | 同 parser | 全 solver run、raw |
| `solver.log.cell_count` | log が報告した cell 数 | 同 parser | 全 solver run、raw nullable |
| `result.official.trim_sec` | official score に使う ExecutionTime の trim 区間 | official-log-valid な step timing の最後−最初 | official result source が有効な run、派生 |
| `result.official.fvops_trim_m` | `64,000,000 * 4 / trim_sec / 1e6` | official result reducer | official result source が有効な run、派生 |

## 6. MPI network metrics

| キー | 意味 | 収集方法（コマンド／関数） | 適用・種別 |
|---|---|---|---|
| `network.imb_mpi1.process_count` | IMBのMPI process数 | solverと同じprocess数を完全argvの`-npmin`とIMB sectionで照合 | bench/profile、raw scalar |
| `network.imb_mpi1.message_size.min_bytes` | 最小message size | 固定値0 | bench/profile、raw scalar |
| `network.imb_mpi1.message_size.max_bytes` | 最大message size | 固定値4194304 | bench/profile、raw scalar |
| `network.imb_mpi1.iteration.max_per_sample` | sample当たり最大iteration | argv `-iter 1000` | bench/profile、raw scalar |
| `network.imb_mpi1.iteration.time_limit_sec` | sample time limit | argv `-time 1` | bench/profile、raw scalar |
| `network.imb_mpi1.iteration.policy` | iteration policy | argv `-iter_policy dynamic` | bench/profile、raw scalar |
| `software.imb_mpi1.version` | 実行したIMB-MPI1 version | raw stdoutのversion marker | bench/profile、raw scalar nullable |

`mpi_network_results_v2`は`(run_id,benchmark,process_count,message_bytes)` grainのlong relationで、
`iterations,time_min_us,time_avg_us,time_max_us,bandwidth_mbytes_per_sec,source_member`を持つ。
PingPong/Sendrecv/Allreduceの実在rowだけを返し、存在しない列はNULLにする。平均/最大帯域、代表latency、
`ib_*_{bw,lat}`は保存せずquery時に導出する。

## 7. Profile-only metrics

| キー | 意味 | 収集方法（コマンド／関数） | 適用・種別 |
|---|---|---|---|
| `profile.perf.rank.<rank>.{cycles,instructions,branches,branch_misses,cache_misses}.raw_count_lexeme` | 5種の perf counter raw count | rank wrapper が `perf stat --no-big-num -x, -e cycles,instructions,branches,branch-misses,cache-misses` を実行し CSV parser で読む。hyphen は v1 key 規則に合わせ underscore 化 | profile-only、raw |
| `profile.perf.rank.<rank>.{cycles,instructions,branches,branch_misses,cache_misses}.count` | 5種の parse 済み counter | 同 CSV parser | profile-only、raw nullable |
| `profile.perf.rank.<rank>.{cycles,instructions,branches,branch_misses,cache_misses}.unit` | 5種の counter unit | 同 CSV parser | profile-only、raw nullable |
| `profile.perf.rank.<rank>.{cycles,instructions,branches,branch_misses,cache_misses}.running_ns` | 5種の event running time | 同 CSV parser | profile-only、raw nullable |
| `profile.perf.rank.<rank>.{cycles,instructions,branches,branch_misses,cache_misses}.percent_running` | enabled 時間に対する running 割合 | 同 CSV parser | profile-only、raw nullable |
| `profile.perf.rank.<rank>.{cycles,instructions,branches,branch_misses,cache_misses}.enabled_ns` | 5種の event enabled 時間 | `running_ns / (percent_running / 100)` | profile-only、派生 |
| `profile.hardware.node.<node>.memory.available_bytes.postrun` | solver 後の MemAvailable | profile hardware capture が `/proc/meminfo` を読む | profile-only、raw nullable |
| `profile.hardware.node.<node>.numa.<id>.cpulist` | NUMA node の CPU 集合 | `/sys/devices/system/node/node<id>/cpulist` | profile-only、raw nullable |
| `profile.hardware.node.<node>.numa.<id>.memory.{total_bytes,free_bytes}` | NUMA node memory | node `<id>/meminfo` を parse | profile-only、raw nullable |
| `profile.hardware.numa_cpu_layout_identity` | 全 node の NUMA CPU layout identity | profile NUMA cpulist relationを canonical JSON 化 | profile-only、派生 nullable |
| `profile.hardware.postrun_memory_available_bytes_min` | node 間の post-run MemAvailable 最小値 | profile hardware node summary の `min` | profile-only、派生 nullable |

## 8. Consumer/view でのみ作る値

| キー | 意味 | 算出方法 |
|---|---|---|
| `validation.transport_valid` | 実 transport が個別policyと整合するか | 全 rank の launch-effective `I_MPI_FABRICS`、protocolのtransport/node数を reducer で照合 |
| `validation.placement_valid` | request/accounting/header/rank placement の整合 | protocolのnodes/ranks、`nnumu`、header Hosts/nProcs、rank集合を exact 比較。raw reason field は作らない |
| `validation.official_log_valid` | official log 自体が contract の marker/timing/numeric 規則を満たすか | canonical official-log reducer。`Hosts` 欠損や比較 eligibility は別 gate |
| `eligibility.score_comparison` | v2 consumer `score_comparison_eligible`。bench score 比較へ入れられるか | collection、placement、transport、official-log、workload 条件の view |
| `run.termination.solver.{kind,exit_code,signal}` | v2 consumer `solver_termination_kind` / `solver_exit_code` / `solver_signal` | `run.stage.solver.termination` の closed union を consumer へ展開 |
| `perf.solver.outer_wall_sec` | solver stage 外側時間 | `perf.stage.solver.wall_time_sec` の response projection |
| `perf.stage.block_mesh.wall_sec` | blockMesh 外側時間 | `perf.stage.block_mesh.wall_time_sec` の response projection |
| `perf.stage.decompose_par.wall_sec` | decomposePar 外側時間 | `perf.stage.decompose_par.wall_time_sec` の response projection |
| `perf.pipeline.end_to_end.wall_sec` | regular pipeline 外側時間 | `perf.pipeline.wall_time_sec` の response projection |
| `resource.job.memory.max_rss_bytes` | job 最大 RSS | `scheduler.accounting.mmszu.bytes` を view で投影 |
| `resource.job.cpu.{user_time_sec,system_time_sec}` | job の user/system CPU time | `uctmut.seconds` / `sctmut.seconds` を view で投影 |
| `scheduler.{terminal_state,exit_code}` | scheduler terminal state と exit code | accounting/terminal source を run consumer へ projection |
| `execution.{nodes,ranks,resource_group,transport_policy}` | 予定した個別実行設定 | 実行設定とscheduler requestの一致済みprojection | consumer projection。各leafを独立列にする |
| `topology.{requested_nodes,requested_ranks,allocated_nodes}` | request と allocation の node/rank 数 | 個別request field と `nnumu` を独立 projection |
| `topology.{solver_host_count,solver_nprocs,placement_host_count,placement_rank_count}` | solver header と placement の観測 cardinality | runtime header / rank placement relation を count |
| `topology.{resource_group,transport_policy,effective_transport,effective_file_handler}` | 個別policy と runtime 実効値 | scheduler request、rank env consensus、runtime header を projection |
| `topology.placement_affinity_signature` | rank/local-rank順の pinning shape | CPU-set cardinality、overlap、NUMA binding を canonical JSON 化 |
| `workload.match` | expected workload と observed workload の一致 | protocol expected identity と `workload.manifest_identity` を比較 |
| `build.{precision,artifact_sha256,compiler_identity,mpi_identity}` | build precision、artifact、compiler、build-time MPI | build manifest/sidecar を projection |
| `mpi.execution_identity` | run-time MPI identity | launch-effective environment と resolved launcher provenance を projection |
| `hardware.consensus.{cpu_model,kernel_release,physical_cores_per_node,numa_nodes_per_node,memory_total_bytes}` | node 間 CPU/kernel/memory consensus | minimal hardware rowsを consensus reducer。不一致・欠損は NULL |
| `hardware.consensus.{cpu_governor,cpu_frequency_max_hz,cpu_boost_enabled,numa_balancing}` | node 間 platform-setting consensus | cpufreq/boost/NUMA rowsを consensus reducer。不一致・欠損は NULL |
| `mesh.partition.rank_cell_count.{min,max,mean,imbalance}` | rank 別 cell 数の分布 | `mesh.partition.rank.<rank>.cell_count` から query 時に算出 |
| `solver.pstream.change_event_count` | runtime Pstream 変更件数 | 完全な change event relation を count |
| `solver.pstream.{float_transfer,default_comms_type,pstream_buffers_algorithm,using_node_comms}` | rank 間で一致した主要 runtime Pstream 値 | startup/runtime rank records の consensus projection |
| `solver.pstream.{node_comms_control,node_comms_min,topology_control}` | rank 間で一致した node/topology tuning | 同 consensus projection |
| `solver.pstream.{configured_mpi_buffer_value,environment_mpi_buffer_bytes_applied,attached_buffer_bytes}` | rank 間で一致した buffer 設定/実適用値 | startup rank records の consensus projection |
| `solver.pstream.{n_procs_simple_sum,n_procs_nonblocking_exchange,tuning_nbx,n_poll_proc_interfaces,max_comms_size}` | rank 間で一致した integer tuning | runtime rank records の consensus projection |

## 9. Lineage/control field と非収集項目

| 区分 | field／キー | 扱い |
|---|---|---|
| lineage/control | `schema_version`、`run_id`、`allocation_id`、`producer_id`、`sequence`、`event_type`、source member/path/hash、argv、stdout/stderr member | artifact の検証・再現・join に保持するが、科学メトリクス表の leaf key とは数えない |
| 非収集 | network用`lane`、`qualification*`、`block_id`、`block_order`、`replicate_index`、`pair_id`、contract/protocol ID・hash | 各runを独立に扱い、通信設定は独立scalarへ展開する |
| 非収集 | MPI summary、`ib_*_bw`、`ib_*_lat` | message size別long relationからquery時に導出する |
| 非収集 | `run.stage.<name>.exit_code` | v2 は `termination.{kind,code,signal}` に置換 |
| 非収集 | `solver.argv` | 完全な outer launch argv が正本。solver 部分だけを複製しない |
| 非収集 | `allocated_ranks` | `pjstat` から得られないため推測しない |
| 非収集 | `partition_valid`、placement/transport の reason/status 群 | source fact と既存 validity/eligibility projection だけを使う |
| 非収集 | `profile.perf.*.missing` / `.reason` / `.status` | profile の欠損は NULL、bench は row 自体を作らない |
| 非収集 | v1 の `solver.linear.*`、`solver.continuity.*`、`result.aero.*`、`result.field.*`、`result.flux.*`、`result.probe.*` | v2 の official score contract には含めない |
| 非収集 | mesh quality の min/max/mean、field hash、warning/fatal/bounding count、`solver.converged`、`validation.passed` | 曖昧、過敏、または baseline 依存のため collector では作らない |

## 10. 実装状況

この表は「v2 で収集する予定」の契約であり、現行 `experiment-metrics` package の実装済み
一覧ではない。現行実装は v1 の scalar/即時送信方式であり、v2 に必要な runner manifest、
structured termination、native `mesh-facts` / `partition-audit`、Pstream hook、rank 別 perf、
finalizer/packager、runner-only publisher は未実装である。

## 参照元

- `research/experiment-metrics-v2-plan.md`
- `research/experiment-metrics-v2-observation-map.md`
- `research/experiment-metrics-v2-contract-schemas.md`
- `research/experiment-metrics.md` と `research/experiment-metrics/01-*.md`〜`08-*.md`
  （キー階層規則の参照）
