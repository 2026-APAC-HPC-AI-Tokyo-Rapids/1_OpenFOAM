# OpenFOAM experiment metrics v2 直接送信キーカタログ

## 現行contract

2026-08-12以降の実装の正本である。BigQueryは
`openfoam_metrics(run STRING, key STRING, value STRING)` 一表だけを使用する。
各producerはfragmentをatomic renameで確定した直後に同じ行を直接送信する。
merge、finalize、projection、consumer view、conflict table、`metrics.jsonl`、自動再送は使わない。

source trackは `source.track.head_commit`（このrepositoryのGit commit SHA）だけとする。
pushは常にbench、手動dispatchだけがbench/profileを選択する。profileはVTune
hotspotsへ一本化する。通常runでrank別environmentは収集しない。

## 直接送信するキー

`*`は実際のnode、rank、stage、workload memberまたはIMB measurement識別子へ置換する。
JSON値もBigQuery上ではcanonical JSON文字列として格納する。

| key pattern | 値・用途 | producer |
|---|---|---|
| `run.identity.{run_id,run_purpose,repository_id}` | run識別 | runner manifest |
| `run.instrumentation_bundle_sha256` | instrumentation bundle識別 | runner manifest |
| `source.track.head_commit` | 実checkoutのGit commit SHA | runner manifest |
| `artifact.build_manifest_sha256` | build manifest SHA-256 | build provenance |
| `build.provenance` | OpenFOAM/ThirdParty commit、compiler/MPI、build artifact identity | compute-side build parser |
| `build.provision` | 実行binary、MPI launcher/library、provision照合結果 | compute-side provision parser |
| `workload.manifest` | workload ID、exact 7-member identity | compute-side workload capture |
| `workload.member.{initial_u,initial_p,transport_properties,block_mesh_dict,control_dict,fv_schemes,fv_solution}` | solver入力7 fileの原byte（Base64） | compute-side workload capture |
| `scheduler.request` | nodes、ranks、resource group、transport、submit argv/script identity | runner submission |
| `scheduler.{submit_job_id,job_entry_job_id}` | scheduler job ID | runner / compute |
| `scheduler.accounting` | terminal state、elapsed、exit、node数、全体memory/CPU accountingとnode別usage配列 | runner postrun |
| `run.{started_at,finished_at,elapsed_sec,exit_code}` | PJM lifecycle | compute supervisor |
| `run.stage.<stage>.{launch,termination}` | exact argv/cwdとexit/signal結果 | compute StageRunner |
| `perf.stage.<stage>.wall_time_sec` | stage外側wall time | compute StageRunner |
| `perf.pipeline.wall_time_sec` | solverを含むprimary pipeline wall time | compute supervisor |
| `env.*` | MPI launch直前の共通host environment（credential除外済み） | compute environment parser |
| `parallel.rank_placement` | 全rankのrank/local rank/hostname/affinity/NUMAをglobal-rank順の一JSONに集約 | compute placement parser |
| `hardware.minimal.node.<ordinal>` | 各nodeのCPU、kernel、memory、NUMA/boost/cpufreq設定 | compute hardware parser |
| `mesh.topology` | 下記 `mesh-topology/v2` | compute saved-log parser |
| `mesh.partition.requested` | 使用dictのSHA-256、subdomains、method | compute saved-log parser |
| `mesh.partition.observed` | 下記 `partition-observed/v2` | compute saved-log parser |
| `solver.runtime_header` | Build/Arch/Exec/fileHandler/nProcs/Hosts | runner saved-log parser |
| `solver.step_timings` | simulation time、ExecutionTime、ClockTimeの順序付き配列 | runner saved-log parser |
| `solver.pressure_solves` | pressure solve residual/iterationの順序付き配列 | runner saved-log parser |
| `solver.log_markers` | End/bad-number/cell marker | runner saved-log parser |
| `result.official` | validity、trim秒、FVOPS、公式result text | runner result parser |
| `solver.pstream.{startup_applied,runtime_current,change_events}` | 全rank一致を検証した共通Pstream値 | runner Pstream reducer |
| `solver.pstream.rank_exceptions` | 共通値との差が実在するrankだけ（通常はkeyなし） | runner Pstream reducer |
| `network.imb_mpi1.{process_count,message_size.*,iteration.*}` | IMB実行設定 | compute IMB parser |
| `software.imb_mpi1.version` | IMB version | compute IMB parser |
| `network.imb_mpi1.result.<benchmark>.<message_bytes>` | PingPong/Sendrecv/Allreduce各測定row | compute IMB parser |
| `profile.vtune_hotspots.rank.0` | profile-only VTune設定、version、source identity、全function hotspot | compute VTune parser |
| `profile.hardware.node.<ordinal>` | profile-only postrun memory/NUMA detail | compute profile hardware parser |

通常benchのstage集合は `case_prepare`、`solver`、`minimal_hardware_capture`、
`network_imb_mpi1` である。profileだけ `profile_hardware_capture` を加える。
IMBとprofile hardwareはsolver終了後の独立stageであり、solver性能比へ混ぜない。

## 復活した構成・性能比較情報の具体形

旧projectionから必要な意味情報は次のraw JSONへ移した。DB側のprojectionは作らない。

### `mesh.topology`

```json
{"schema_version":"mesh-topology/v2","cells":64000000,"faces":192480000,"points":64481201,"internal_faces":191520000}
```

値はprepare時に既に保存された `blockMesh.log` の `nCells`、`nFaces`、`nPoints`、
`nInternalFaces` から読む。meshを再度openしない。

### `mesh.partition.requested`

```json
{"schema_version":"partition-requested/v1","source_sha256":"...","subdomains":120,"method":"scotch"}
```

### `mesh.partition.observed`

```json
{
  "schema_version":"partition-observed/v2",
  "subdomains":[
    {"rank":0,"cell_count":529491,"processor_patch_count":8,"processor_face_count":38997}
  ],
  "interfaces":[
    {"lower_rank":0,"upper_rank":1,"face_count":3657}
  ]
}
```

全rank分を持つ理由はpartition imbalanceと通信面積を後から評価するためである。
取得元はprepare時に既に保存された小さな `decomposePar.log` だけで、processor meshを再走査しない。
全rankのcell合計、rank集合、interfaceの双方向一致をparserで検証する。

### `hardware.minimal.node.<ordinal>` と `parallel.rank_placement`

hardwareはrankごとではなくnodeごとに一度収集する。rankごとに必要なのはplacement/affinityだけなので、
`parallel.rank_placement` 一JSONに集約する。これによりnode構成、CPU設定、rank配置を比較でき、
同一node内で重複する全環境情報の収集は避ける。

### `build.provenance`、`build.provision`、`workload.manifest`

compiler/MPI/build identity、実行binary identity、OpenFOAM/ThirdParty commit、exact workload identityを保持する。
source track側には重複させず、このrepositoryについては `source.track.head_commit` だけを持つ。

## 明示的に収集しないもの

- `mesh-facts` と `partition-audit` はruntimeで起動しない。
- serial `polyMesh` 5 memberのsize/hashは収集しない。
- rankごとのprocessor mesh 5 memberのsize/hashは収集しない。
- rankごとのcell/face/point/boundary addressingのsize/hashは収集しない。
- rankごとのenvironment snapshotは生成・保存しない。
- VTune profileは収集しない。
- `collection_complete`、owner/type registry conflict、projection/consumer用keyは作らない。
- DB側の最新値選択、merge、重複排除は行わない。

上記mesh hash群は64M-cell meshをsolver後に数分かけて読み直すため、構成別速度評価に必要な情報量に
対して費用が過大である。必要なtopology、rank cell分布、processor face分布、interface face数は
保存済みlogから数秒未満で得る。

## failure semantics

fragment確定後のBigQuery送信は500行chunk、retryなし、insertIdなしである。同一行の重複を許容する。
送信失敗、mesh log解析失敗、IMB/profile収集失敗はwarningとして残すが、既に成功したsolver結果を失敗へ変更しない。
fragmentは診断artifactであり再送queueではない。
