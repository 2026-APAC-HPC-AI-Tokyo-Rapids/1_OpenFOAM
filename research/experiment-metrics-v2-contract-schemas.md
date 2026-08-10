# OpenFOAM v2 contract schema handoff

## 役割

この文書は[`experiment-metrics-v2-plan.md`](experiment-metrics-v2-plan.md)の方針と
[`experiment-metrics-v2-observation-map.md`](experiment-metrics-v2-observation-map.md)の取得対応を、
`openfoam-v2.toml`とJSON Schemaへ転記するためのfield-level正本である。実装者はfield名、型、enum、source、
reducerを追加解釈しない。新しいfieldが必要なら先にこの文書とcontract IDを更新する。

この文書はraw valueを複製しない。source artifact、`run/key/value` fact、query-time consumerの関係だけを定義する。
field名末尾の`?`はoptional、値型の`|null`だけがnullableである。

## canonical identity

| 項目 | v1定義 |
|---|---|
| repository ID | fixed string `apac2026-openfoam`。runtimeのGit remote URLはidentityに使わない |
| regular run ID | `r-` + OS CSPRNG 16 byteのlowercase hex 32文字 |
| JSON canonical bytes | RFC 8785 JCS、UTF-8。object key重複、NaN、Infinity禁止 |
| committed TOML identity | checkoutしたfileの実byte列にSHA-256。改行・comment変更も別identity |
| Git object identity | `{object_hash_algorithm:enum "sha1"|"sha256",oid}`。oidはalgorithmに応じexact lowercase 40-hexまたは64-hex |
| artifact member path | archive rootからのrelative POSIX path。absolute path、`..`、空componentは禁止 |
| runtime-only locator | `locator_kind=runtime_relative_ephemeral`とcase/runtime rootからのrelative POSIX path |

IDはPJM job ID、PID、時刻、branch名から生成しない。manifest自身のhashはmanifest本文へ入れず、参照側または
outer manifestに置く。

## source track v1

`source-track-projection/v1`は全field required、`additionalProperties=false`の
`{schema_version:const "source-track-projection/v1",run_id,run_purpose:enum "bench"|"profile",
repository_identity:const "apac2026-openfoam",object_hash_algorithm:enum "sha1"|"sha256",
score_reference_commit:oid|null,profile_base_commit:oid|null,source_head_commit:oid,
source_track_manifest_sha256:sha256,source_member:relative POSIX path,source_sha256:sha256}`である。
benchはscore reference、profileはprofile baseを使う。

subject manifestにembedする`source-track/v1`は
`object_hash_algorithm/base_role/base_commit/head_commit`を持つclosed objectである。
benchは`base_role=score_reference`、profileは`base_role=profile_base`とし、baseがheadのancestorであることを
投入前に検証する。開発時のOFF/ON source diffはv2 artifactへ保存しない。
## subject manifest v1

`control/run-manifest.json`は次のclosed fieldを持つ。v2で永続化するrun purposeは`bench|profile`だけである。

| field | type | requirement |
|---|---|---:|
| `schema_version` | const `run-manifest/v1` | required |
| `subject_kind` | const `regular_run` | required |
| `run_id` | run ID | required |
| `run_purpose` | enum `bench|profile` | required |
| `repository_id` | const `apac2026-openfoam` | required |
| `source_track` | `<source-track/v1>` | required |
| `observed_control_plane_sha256` | SHA-256 | required |
| `instrumentation_bundle_sha256` | SHA-256 | required |

非該当fieldはJSON `null`でなくabsentにする。expected producer/file集合はmanifestへ複写せず、
実装のpurpose applicabilityとbundle component selectionからfinalizerが一回導出する。

開発中の非擾乱確認は通常のv2 run manifest、artifact、Fact、relation、decision recordへ保存しない。
一時的な比較出力は確認後に破棄し、contractにはrun variantやconsumerを追加しない。

## instrumentation bundle v1

`control/instrumentation-bundle.json`は全field required、`additionalProperties=false`の次のclosed objectである。

```text
schema_version: const "instrumentation-bundle/v1"
bundle_track: enum "reference" | "score" | "profile"
source_paths: sorted unique repository-relative POSIX paths
components: component[]
environment_capture_scopes: sorted unique subset of ["job_entry", "host_exec_rank"]
sink_bindings: [{sink_id:nonempty string, source_id:existing source registry ID,
 buffering_mode:enum "line_buffered"|"stage_buffered"}, ...]
environment_bindings: [{name:nonempty POSIX environment name,scope:const "solver_process_tree",
 value_template:nonempty environment-value-template segment array}, ...]
```

`component`は全field requiredの
`{component_id:nonempty string,sink_ids:sorted unique string[],activation:activation}`で、
component ID UTF-8 byte順uniqueとする。`activation`は
`kind`でtagした次の五つだけで、全union memberは`additionalProperties=false`、記載fieldをすべてrequiredにする。

```text
{kind:"in_process_hook", source_commit_role:const "openfoam_source",
 source_path:repository-relative POSIX path, symbol:nonempty string, event_schema_id:nonempty string}
{kind:"executable", artifact_relative_path:relative POSIX path, content_sha256:sha256,
 argv_template:nonempty argv-argument-template array}
{kind:"sampler", artifact_relative_path:relative POSIX path, content_sha256:sha256,
 argv_template:nonempty argv-argument-template array, sample_interval_sec:positive finite decimal}
{kind:"control", control_id:nonempty contract-registry ID, timeout_sec:positive finite decimal}
{kind:"postrun_parser", parser_id:nonempty string, source_schema_id:nonempty string}
```

template segmentはclosed union `{literal:nonempty string}`、
`{token:enum "runtime_root"|"case_root"|"artifact_root"|"component_executable"|"node_ordinal"|"global_rank"|
"invocation_id"|"subject_run_id"|"expected_global_ranks"}`、
`{token:const "stage_executable",role:enum "icoFoam"|"blockMesh"|"decomposePar"|"checkMesh"|"mesh-facts"|"partition-audit"}`、
`{token:const "provisioned_executable",role:const "perf"}`、
`{token:const "sink_path",sink_id:nonempty string}`、`{token:const "rank_sink_template",sink_id:nonempty string}`とする。argv argument templateはnonempty
segment arrayで、adjacent literalは一つに結合する。sink pathはbinding `source_id`のregistry `path_template`だけから得る。
`artifact_root`はsource-track headのclean checkoutから作るread-only instrumentation payload root、
`artifact_relative_path`はそのroot基準である。runnerはactivate直前にrealpathがroot外へ出ないことと実fileの
size/content SHA-256をbundle宣言へ一致させ、`component_executable`をその検査済みabsolute realpathだけへ展開する。
`stage_executable(role)`はbuild-provision validationの同role検査済みabsolute realpathだけへ展開する。
executable/samplerで別root、PATH検索、hash不一致fallbackを許さない。実run ID、absolute runtime root、実時刻はbundle byteに含めない。runnerは
`score -> bench`、`profile -> profile`の固定写像でbundleを一つ選び、
その全componentを一度activateする。component別applicabilityはこの写像の完全な複写になるため保存しない。
benchは通常contractのscore bundleを使う。開発時確認のevidenceは保存・継続照合しない。purposeはsubject manifest、実argv/cwdはStageRunner Fact、
sink path templateはsource registry、実byteを含むouter file identityはartifact manifestが所有する。`sink_bindings`はsink ID byte順uniqueかつ
source ID uniqueで、全component `sink_ids`のunionとbinding ID集合はexact一致する。各binding sourceのproducer activationは
そのsink IDを持つcomponent IDの`bundle_component`とexact一致する。sink token/componentのIDは対応bindingに存在し、hookの`source_commit_role`は
build provenanceの同名commitが存在すること、`source_path`はそのbuilt source tree内に存在することを検査する。
最終runtime byte identityはbuild semantic hashが所有し、bundleへcommit OIDを複写しない。
runnerはactivate前に当該variantとprotocolのnode/rank/invocation contextで使うsinkを一回renderし、全pathがrelative-safeかつ
contractから展開した全producer instance `(sink_id,node_ordinal,global_rank,stage_name,invocation_id)`間でglobal uniqueなことを検査する。
render済みrelative sink pathはsubjectのabsolute runtime rootにjoinして正規化し、resultのrealpath parentがruntime root内に
留まる時だけabsolute sink pathとする。environment value templateは`{literal:nonempty string}`、
`{token:const "subject_run_id"}`、`{token:const "absolute_sink_path",sink_id:nonempty string}`だけのclosed unionである。
binding nameはbyte順unique、sink IDは`sink_bindings`に存在し、runnerはsolver launch environmentへrender結果を一度設定する。
同一single-instance bindingだけは一pathでよい。executable/samplerのargv第0 argumentはexactly一つの
`component_executable` segment、同tokenはtemplate内exactly onceとし、shellを介さずargv arrayを直接spawnする。
`stage_executable(role)`は第1 argument以降だけに置ける。
`provisioned_executable(role="perf")` tokenも第1 argument以降だけに置き、build-provision validationの
検査済みabsolute pathへ展開する。`rank_sink_template`はprofileのhash済みrank wrapperだけが使え、`global_rank`を一個含む
binding sourceのpath templateを、そのtokenだけliteral `@@GLOBAL_RANK@@`として残したabsolute templateへ展開する。literal segmentには
同markerを禁止する。runnerは期待rank集合へ事前展開したpathの一意性を検査し、
wrapperはMPI process内の`PMI_RANK`をuintとして読み、`0 <= rank < expected_global_ranks`を確認してその一pathだけをrenderする。
別rank envの探索や共通fileへのfallbackはしない。profile bundleのhash済みrank wrapperがargv第0になり、
各rankでこのtokenのperfを直接起動する。
post-runの第二activation判定、fallback bundle、曖昧な軽量labelは作らない。

reference bundleは`source_paths=[]`、`components=[]`、`environment_capture_scopes=[]`、`sink_bindings=[]`、
`environment_bindings=[]`に固定する。
score/profile bundleは`source_paths`と`components`をnonemptyにする。共通の外側timer/log/neutral resultはcontract graphが
所有し、reference bundleの疑似componentにしない。
contractはclosed `source_path_policy={score_allowed:sorted unique repository-relative POSIX paths,
profile_only:sorted unique repository-relative POSIX paths}`を一度所有し、両集合をdisjointにする。score `source_paths`は
`score_allowed`のsubset、profileは両集合のunionのsubsetである。score allowlistはinstrumentation実装とそのbundle/protocol
metadataだけを列挙し、workload exact 7 paths、実行設定/PJM/common runner、profile-only pathを含めない。

## environment snapshot v1

全scopeの`.snapshot`はname byte順の`name\0value\0`反復である。POSIX environmentのname/valueはNULを
含められないためlosslessである。最後もNULで終える。parserはraw name/valueを変更せず、BigQuery factではnameを
単射escapeしvalueをBase64にする。このformatを使うのは`source/env/job-entry.snapshot`と
`source/env/host-exec.snapshot`だけである。

`source/env/rank-<rank>.delta.json`は`rank-env-delta/v1`のclosed objectで、次を持つ。全fieldはrequired、
`additionalProperties=false`である。

```text
schema_version: const "rank-env-delta/v1"
common_snapshot_sha256: sha256
rank: nonnegative integer
added_or_changed: [{name_b64: base64, value_b64: base64}, ...]
removed_names_b64: [base64, ...]
```

両arrayはdecode後のname byte順、nameは各array内uniqueかつ二array間disjointである。common snapshotへdeltaを
適用した結果だけを`env.host_exec.rank.<rank>.*`へ展開し、delta自身のfield別raw keyは作らない。

## control artifact schemas

以下はすべて全記載field required、`additionalProperties=false`である。`member`はclosed
`{path:relative POSIX path,size_bytes:uint,sha256:sha256}`、`process-outcome`はclosed union
`{kind:const "exit",code:int}` | `{kind:const "signal",signal:positive int}` |
`{kind:const "spawn_error"}`である。rare failure用のretry counter、reason、代替sourceは追加しない。

```text
scheduler-request/v1 = {
  schema_version:const "scheduler-request/v1", subject_manifest_sha256:sha256,
  nodes:positive uint, ranks:positive uint,
  resource_group:nonempty string, transport_policy:nonempty string,
  pjm_script:{repository_path:repository-relative POSIX path,sha256:sha256},
  argv:nonempty string[]
}
submission-result/v1 = {
  schema_version:const "submission-result/v1", request_sha256:sha256,
  outcome:process-outcome, stdout:member, stderr:member, parsed_job_id:nonempty string|null
}
job-entry/v1 =
  {schema_version:const "job-entry/v1",subject_kind:const "regular_run",run_id:run ID,
   pjm_job_id:nonempty string,entry_utc:RFC3339 UTC,environment_snapshot:member}
scheduler-terminal/v1 = {
  schema_version:const "scheduler-terminal/v1",argv:nonempty string[],outcome:process-outcome,
  stdout:member,stderr:member,observed_terminal_utc:RFC3339 UTC
}
stage-launch/v1 = {
  schema_version:const "stage-launch/v1",argv:nonempty string[],cwd:string,
  stderr_mode:enum "stdout"|"separate"
}
stage-termination/v1 = {schema_version:const "stage-termination/v1",outcome:process-outcome}
bundle-manifest/v1 =
  {schema_version:const "bundle-manifest/v1",subject_kind:const "regular_run",
   run_id:run ID,members:member-with-role[]}
artifact-manifest/v1 = {
  schema_version:const "artifact-manifest/v1",logical_artifact_name:nonempty string,
  files:[{role:enum "run_bundle"|"metrics"|"profile_raw",
          size_bytes:uint,sha256:sha256}, ...]
}
```

`scheduler-request/v1`はsubmit時の個別requested snapshotである。初版Genkai canaryの
設定値は`(nodes,ranks)=(1,120),(2,120),(4,120)`で、`ranks % nodes = 0`、resource group `a-batch`、
Scotch 120 subdomain、exact `mpirun -np 120 -ppn <120/nodes>`を要求する。transport policyは1 nodeだけ
`shm`、2/4 nodeは`shm:ofi`である。node/rank別producer instanceはprotocolの`nodes`と`ranks`から展開し、
node数別schemaやcollectorを作らない。各値はBigQuery/Sheetsでも独立列へ投影し、組み合わせID/objectを作らない。

`member-with-role`は`member`へcontract registryのclosed source-roleを一つ加えたobjectで、path byte順uniqueにsortする。
bundle manifestはself/outer sidecarを含めない。artifact filesは記載role順uniqueで、benchは
`run_bundle,metrics`、profileは`run_bundle,metrics,profile_raw`をexactly once持つ。filenameはroleから
`run-artifacts.tar.zst|metrics.jsonl|profile-raw.tar.zst`へ固定導出し、manifestへ複写しない。
artifact manifest自身とupload IDは含めない。compute/collectorが失敗してもsupervisorがfinalizerまで到達できたrunは、
完成済みlog/sourceと`collection_complete=false`を持つ通常artifact setを一度作る。
`request_sha256`は実scheduler request file bytes、terminal argv末尾job IDはsubmission/job-entryの一致済みIDである。

`scheduler-accounting/v1`は固定`pjstat --history -S --choose jid,st,sdt,elp,ec,sn,pc,nnumu,mmszu,uctmut,sctmut
--data --delimiter "\t" <source-specific-job-id>`の一rowを次のclosed objectで保持する。返却`jid`はargv末尾IDと一致必須である。

```text
schema_version: const "scheduler-accounting/v1"
jid, st, sdt: string
elp: {lexeme:string, seconds:finite decimal|null}
ec, sn, pc, nnumu: {lexeme:string, value:int|null}
mmszu: {lexeme:string, bytes:uint|null}
uctmut, sctmut: {lexeme:string, seconds:finite decimal|null}
```

`elp.seconds`は括弧内decimal seconds、`uctmut/sctmut.seconds`はmillisecond lexemeを`decimal / 1000`、
`mmszu.bytes`は括弧内decimalをparseする。
commandのraw stdout/stderr/versionはlog memberに残し、数値parse不能時は対応numericだけnullにする。

field別`missing_*`、reason、issue count、collection validation fileは保存しない。finalizerはimmutable
contract/protocol/bundleから導出したexpected producer/file集合をメモリ上で一回照合し、raw fact
`collection_complete:bool`とmerge済み`metrics.jsonl`を作る。
workflowが得るGitHub artifact ID、SCP outcome、home pathは一attempt一rowのoperational tableだけが所有する。

## 開発時の非擾乱確認

実装中に行うOFF/ON比較はv2の収集対象外である。比較用job、標準出力、集計値はその場で
性能低下がないことを確認するためだけに使い、run manifest、artifact set、BigQuery、Sheets、
Git管理decision recordへ保存しない。したがって非擾乱確認用のrun/schema/relationは定義しない。
## OpenFOAM compound schemas

### requested partition v1

`source/mesh/decomposeParDict`のfile-byte SHA-256をidentityとし、`mesh.partition.requested`は次だけを投影する。

```text
schema_version: "partition-requested/v1"
source_sha256: sha256
subdomains: positive int
method: enum "scotch"
```

これは`decomposePar`をspawnする直前に、実argvが参照するfile bytesから作る。method-specific係数はraw copyにだけ
残し、別metricへ展開しない。将来methodを追加する時はschema/contractを更新する。
Runsの`requested_partition_identity`はこの`source_sha256`そのものとし、wrapper objectを再hashしない。

### Pstream source v1

全record envelopeは全field required、`additionalProperties=false`の
`{schema_version:const "openfoam-pstream-event/v1",run_id:validated run ID,
producer_id:const "openfoam.pstream-hook/v1",rank:uint,sequence:uint,
event_type:enum "startup_applied"|"runtime_current"|"runtime_change",payload:event-specific closed object}`である。
`payload`はevent typeと下記schemaの一つにexact対応し、他eventのfieldを持たない。sequenceはrankごとに0開始で
file順に1ずつ連続する。startup/runtime sentinelを各1件持ち、startup→runtime→runtime_change*順にする。
envelope run IDはrun manifestと一致、rankはfilenameと一致させる。

`startup_applied` payload:

- `node_comms_control:int`
- `node_comms_min:int`
- `using_node_comms:bool`
- `num_nodes:positive int`
- `topology_control:int`
- `configured_mpi_buffer_value:int`（optimisation switchのaccepted signed value）
- `environment_mpi_buffer_bytes_applied:positive int|null`（環境値が有効な正整数として採用された時だけ値）
- `attached_buffer_bytes:nonnegative int`

`runtime_current` payload:

- `float_transfer:bool`
- `n_procs_simple_sum:int`
- `n_procs_nonblocking_exchange:int`
- `tuning_nbx:int`
- `pstream_buffers_algorithm:int`
- `default_comms_type:enum "buffered"|"scheduled"|"nonBlocking"`
- `n_poll_proc_interfaces:int`
- `max_comms_size:int`
- `node_comms_control:int`
- `node_comms_min:int`
- `topology_control:int`
- `using_node_comms:bool`

`runtime_change` payloadは`field`を上記runtime field enum、`old`と`new`をそのfieldと同じlogical typeにする。
array orderはsource `sequence`昇順で、変更0件だけ`[]`を生成する。
`configured_mpi_buffer_value`は負/0も合法なraw accepted settingとして保持し、環境の不存在、parse不能、非正値は
`environment_mpi_buffer_bytes_applied=null`とする。`attached_buffer_bytes`だけがclamp後の実attachment量である。
`pstream_buffers_algorithm`はsource integerをそのまま保存し、`<=0`/`>0`のclass booleanを第二raw値にしない。
`max_comms_size`もsigned source integerを保存し、負値をbytesへ曖昧変換しない。

### observed partition v1

`source/mesh/partition-observed.json`は全field required、全object `additionalProperties=false`の次のclosed schemaを持つ。

v1 protocolは全OpenFOAM stageのexact argvに`-fileHandler uncollated`を置き、runtime headerのactual
`fileHandler=uncollated`を要求する。partition readerは`processor<rank>/constant/polyMesh`だけを対象とし、
`processors<N>` collated layoutを自動探索しない。別handlerを試す時はprotocol/schemaを更新する。

```text
partition-observed/v1 = {
  schema_version: const "partition-observed/v1",
  serial_mesh: {points:locator,faces:locator,owner:locator,neighbour:locator,boundary:locator},
  subdomains: [{rank:uint, cell_count:positive int,
    mesh:{points:locator,faces:locator,owner:locator,neighbour:locator,boundary:locator},
    addressing:{cell:locator,face:locator,point:locator,boundary:locator}}, ...],
  interfaces: [{lower_rank:uint, upper_rank:uint, n_faces:positive int}, ...]
}
locator = {locator_kind:const "runtime_relative_ephemeral",
  path:relative POSIX path, size_bytes:uint, sha256:sha256}
```

`subdomains`はrank昇順でrank unique、`interfaces`は`(lower_rank,upper_rank)`昇順unique、
`lower_rank < upper_rank`とする。subdomain array長とrank集合はrequested partitionのsubdomainsに一致、
`sum(cell_count)`は`mesh-topology/v1.cells`に一致させ、global cells/subdomain countをこのobjectへ複写しない。

`serial_mesh`はserial `constant/polyMesh/{points,faces,owner,neighbour,boundary}`を記載field順にexactly一件ずつ持つ。
各subdomain `mesh`はprocessor側`points/faces/owner/neighbour/boundary`、`addressing`は
`cellProcAddressing/faceProcAddressing/pointProcAddressing/boundaryProcAddressing`に一対一対応する。
SHA-256はheader込み実file bytes、pathはcase-relative POSIX pathである。
`min/max/mean/imbalance`は`subdomains[].cell_count`の完全な部分集合なのでrawへ保存せずviewで導出する。
`observed_partition_identity`はpath/sizeを除いたserial mesh五SHA-256、rank/cell count/processor mesh五SHA-256/
addressing四SHA-256、interface tupleのJCS projectionの
SHA-256とする。

`partition-audit`は`<resolved-partition-audit> -case <case> -fileHandler uncollated -constant
-output <case>/source/mesh/partition-observed.json`の一経路だけを使い、solver終了後にそのcaseへ一度実行する。
これは同じbuild sidecarのOpenFOAMへlinkしたnative utilityで、`polyMesh`、`labelIOList`、`processorPolyPatch` APIから
ASCII/binary、label width/endiannessの差をOpenFOAM自身に読ませ、signed `faceProcAddressing`の符号を保持する。
serial meshを一度読み、processor directoryはrank順に一つずつ開放しながら処理する。global cell/face/pointの
存在検査はmesh sizeで上限が決まるbitset、interface照合はmapped global face ID集合だけを保持し、全processor meshを
同時保持しない。64M-cell canaryでpeak RSSをnode memoryの25%以下とすることをrelease testで確認するが、別parserや
memory超過時fallbackは作らない。各processor patchを
`lower_rank=min(myProcNo,neighbProcNo)`、`upper_rank=max(...)`へcanonicalizeし、両rankのboundaryに
exactly onceずつ存在して`nFaces`が一致する時だけ一interfaceにreduceする。cell addressingから各serial cellが全rankへexactly once、
interface検証はlower/upper各rankのsubdomainが一度所有するboundary locatorから読み、interfaceへlocatorを複写しない。
rankは`0..len(subdomains)-1`でなければならない。cell addressingはlocal cell数と同長、各値は
`0 <= value < mesh-topology.cells`でrank内unique、全rank unionが各serial cell exactly onceである。
face addressingはzero禁止、`1 <= abs(label) <= mesh-topology.faces`、local face数と同長である。
serial owner/neighbourとcell addressingから各serial internal faceの両cellが属するrankを求める。同rankならそのrankの
nonprocessor faceとしてexactly一回、異rankなら両rankの対応processor patchにexactly一回ずつ現れ、二entryの
`abs(faceProcAddressing)-1`が同じで符号が反対でなければならない。serial boundary faceはowner cellのrankの
nonprocessor patchにexactly一回だけ現れる。したがって全global faceの出現数はunsplit internal/boundaryが一回、split internalが
二回であり、余分・欠落を許さない。各processor peer patchについてもmapped global face ID集合と件数を両側でexact一致させる。
point addressingはlocal point数と同長、rank内unique、各値`0 <= value < mesh-topology.points`とし、rank間重複は許すが
全rank unionはserial point集合と一致させる。各local faceのpoint listをpoint addressingでserial IDへ写し、対応serial faceの
vertex cycleと、face addressingが正ならcyclic rotation、負ならreverse cyclic rotationとしてexact一致させる。
boundary addressingはlocal boundary patch数と同長、processor patchは`-1`、非processor patchはserial boundary index範囲で、
processor mesh boundaryのpatch type/nameとの対応が一致しなければならない。

### mesh、solver log v1

この節のobjectは全field required、field名末尾の`?`はoptional、値型の`|null`だけがnullable、
`additionalProperties=false`である。

```text
mesh-topology/v1 = {schema_version:const "mesh-topology/v1", cells:uint, faces:uint, points:uint, internal_faces:uint}
openfoam-header/v1 = {schema_version:const "openfoam-header/v1", build:string, arch:string, exec:string,
  file_handler:const "uncollated", nprocs:uint, hosts:[{hostname:string,ranks:uint}, ...]}
step-timing/v1 item = {simulation_time_lexeme:string|null, simulation_time:decimal|null,
  execution_lexeme:string, execution_sec:finite decimal|null,
  clock_lexeme:string|null, clock_sec:finite decimal|null}
pressure-solve/v1 item = {simulation_time_lexeme:string|null,
  initial_residual_lexeme:string, initial_residual:finite decimal|null,
  final_residual_lexeme:string, final_residual:finite decimal|null,
  iterations_lexeme:string|null, iterations:uint|null}
official-marker/v1 = {schema_version:const "official-marker/v1", end_count:uint, badnum_line_count:uint, log_ncells:uint|null}
```

official headerに`Hosts` blockがなければ`hosts=[]`とする。blockがあればhostname byte順uniqueにcanonicalizeし、
各rank countをpositive uint、`sum(ranks)=nprocs`とする。Build/Arch/Exec/nProcs/fileHandler/Hostsが複数回現れる場合は、
parse後のclosed header objectがすべてexact一致する時だけ一objectへreduceし、一つでも違えばheader sourceを不成立にする。
`hosts=[]`自体はofficial marker validityをfalseにせず、host照合を必要とするcomparisonだけを不適格にする。

`pressure-solve`に定数`field="p"`は保存しない。source regexは`Solving for p`だけである。NaN/Infinity等の
nonfinite residualはlexemeを残してnumericをnullとし、official validityはfalseにする。arrayはlog順で、
一要素からfirst/last/count等の第二raw keyを作らない。

## build、probe、実行source recordのclosed schema

Git管理の実行設定はartifactへcopyせず、ID/hashもmetricへ保存しない。実行時に読む設定shapeは次である。

```text
run_purpose: enum "bench"|"profile"
repository: {repository_id:const "apac2026-openfoam",object_hash_algorithm:enum "sha1"|"sha256"}
control_plane_files:nonempty sorted unique [{path:repository-relative POSIX path,
  blob_oid:repository algorithm-constrained full OID}]
nodes: positive uint
ranks: positive uint
resource_group: nonempty string
transport_policy: nonempty string
workload: {workload_id:nonempty string,expected_workload_identity:sha256}
```

全v1 protocolで`ranks % nodes = 0`を要求し、expected node ordinalは`0..nodes-1`、expected global rankは
`0..ranks-1`、expected rank/nodeは`ranks/nodes`として個別fieldから展開する。required producerはcontractの
variant applicability、instrumentation modeはprotocol/bundle selectionが所有する。
top-level `control_plane_files[].path`はscore bundle
`source_paths`と非重複で、各blob OIDは実行checkoutとexact一致させる。実行設定用の別manifestや
そのID/hashは作らず、`nodes`、`ranks`、`resource_group`、`transport_policy`をprotocolが個別に所有する。
expected workload identityはexact 7 pathのpath/size/SHA-256 arrayのJCS hashである。
`observed_control_plane_sha256`は各runの実行checkoutから
protocol path順に一度観測し、別artifact/Factsへ配列を複写しない。

`control/build-sidecar.json`は全field required、`additionalProperties=false`の次の`build-sidecar/v1`である。

```text
schema_version: const "build-sidecar/v1"
source_commits: exactly 3 [{repository_id:string,
  commit_role:enum "build_definition"|"openfoam_source"|"thirdparty_source",
  object_hash_algorithm:enum "sha1"|"sha256",oid:algorithm-constrained full OID}]
toolchain_commands: exactly 4 [{role:enum "mpiicx_version"|"mpiicpx_version"|"mpirun_version"|"icofoam_dynamic",
  argv:nonempty string[],stdout:member,stderr:member,outcome:process-outcome}]
compile_flags: string[]
precision: enum "SP"|"DP"
label_bits: enum 32|64
build_archive: member
runtime_objects: runtime-object[]
capture_hardware_source: {source_commit_role:const "build_definition",repository_path:repository-relative POSIX path,
  git_blob_oid:algorithm-constrained full OID}
partition_audit_source: {source_commit_role:const "build_definition",
  repository_paths:exactly 3 sorted unique repository-relative POSIX paths,
  git_blob_oids:exactly 3 algorithm-constrained full OIDs}
```

source commit/toolchain arraysは記載role順に各role exactly onceである。runtime objectはclosed union
  `{kind:"executable",role:enum "icoFoam"|"blockMesh"|"decomposePar"|"checkMesh"|"mesh-facts"|"partition-audit"|"capture-hardware",
  path:relative POSIX path,size_bytes:uint,sha256:sha256}`または
  `{kind:"shared_library",path:relative POSIX path,soname:nonempty string,size_bytes:uint,sha256:sha256}`である。path byte順unique、七つの
  executable roleをexactly once必須にする。
capture/partition source blobのalgorithm/OID treeは`source_commits[commit_role="build_definition"]`から継承し、
`partition_audit_source.repository_paths[i]`と`git_blob_oids[i]`は同じpath byte順offsetで対応する。captureの生成entrypoint hashは
同じsource bytesからinstallした`capture-hardware` runtime objectのhashと照合する。entrypointはtracked source bytesを
そのままinstallするものとし、shebangを含む全byteがsource blob contentとexact一致しなければsidecarを公開しない。
  workflow run/attemptはoperational build rowだけが所有し、content-hashed sidecarへ入れない。
  shared library集合は六つのELF executable（`capture-hardware`を除く）の`DT_NEEDED`を`RPATH/RUNPATH`とbuild時loader resolutionで再帰的に
  解決したうち、build archiveが所有する実fileの全体である。symlinkはarchive内で解決し、
  targetのrelative path/size/content SHA-256を一度保存する。dangling/out-of-archive target、未解決のarchive-owned
  `DT_NEEDED`があればbuildを公開しない。system/MPI libraryはclosureに複写せずtoolchain/provision sourceが所有する。
  toolchain argvはrole別に`[resolved mpiicx,"--version"]`、`[resolved mpiicpx,"--version"]`、
  `[resolved mpirun,"--version"]`、`[resolved readelf,"--dynamic",<runtime_objects role="icoFoam"のbuild path>]`へ固定し、
  PATH検索後の曖昧なcommand名や別targetを許さない。`compiler_identity`は先頭二roleの
  `{role,outcome,stdout_b64,stderr_b64}` ordered array、build時`mpi_identity`は`mpirun_version`同objectのJCS hashである。
- `experiment-metrics/native/mesh-facts/{mesh-facts.C,Make/files,Make/options}`をtracked sourceとし、build workflowは
  exact OpenFOAM buildにlinkしてarchiveの`bin/mesh-facts`へ収録する。provisionは
  `<runtime>/provisions/<build-sidecar-sha256>/bin/mesh-facts`へ配置する。
- `experiment-metrics/native/partition-audit/{partition-audit.C,Make/files,Make/options}`をtracked sourceとし、同じOpenFOAMへ
  linkしてarchiveの`bin/partition-audit`へ収録し、provisionの同名pathへ配置する。三fileのpath順blob OIDを
  `partition_audit_source`でsealし、runtime object hashとbuild outputを照合する。
- `capture-hardware`のtracked sourceは
  `experiment-metrics/src/experiment_metrics/probes/capture_hardware.py`、installed entrypointは
  `<runtime>/provisions/<build-sidecar-sha256>/bin/capture-hardware`である。build workflowはOpenFOAM `Allwmake`後に`icoFoam`、`blockMesh`、
  `decomposePar`、`checkMesh`、`mesh-facts`、`partition-audit`を起動可能か検査してからarchive/sidecarを公開する。
- `control/build-provision-validation.json`は全field required、`additionalProperties=false`の
  `{schema_version:const "build-provision-validation/v1",build_sidecar_sha256:sha256,
  run_variant:enum "bench"|"profile",
  executables:[{role:enum "icoFoam"|"blockMesh"|"decomposePar"|"checkMesh"|"mesh-facts"|"partition-audit"|"capture-hardware"|"mpirun"|"perf",
  requested_path:string,resolved_realpath:string,size_bytes:uint,sha256:sha256}],
  ldd_raw:exactly 6 [{role:enum "icoFoam"|"blockMesh"|"decomposePar"|"checkMesh"|"mesh-facts"|"partition-audit",
  source:member}],launcher_version:{argv:exact [resolved mpirun realpath,"--version"],outcome:process-outcome,
  stdout:member,stderr:member},profiler_version?:{argv:exact [resolved perf realpath,"--version"],outcome:process-outcome,
  stdout:member,stderr:member},resolved_libmpi:{path:string,sha256:sha256}|null}`である。executablesはbase八roleを記載順にexactly once、
  profileだけ末尾perfをexactly once加える。
  profiler versionはprofileでrequired、他variantでabsentである。
  validation JSON hashが六つのldd parse入力も間接sealする。validatorは各resolved executableから実際に解決した
  transitive archive-owned dependency集合をbuild sidecar `runtime_objects[kind="shared_library"]`へrelative pathで対応付け、
  六集合のunionとsidecar集合をexact一致させ、provision先content hashもexact一致させる。
  archive/provisionのOpenFOAM build root内へ解決したdependencyは、DT_NEEDED SONAMEとsidecar shared-library `soname`が
  exactly one対応してpath/hashも一致しなければならない。root外dependencyはldd rawへ残し、libmpi以外を巨大なsystem SONAME
  allowlistで囲まない。root外なのにOpenFOAM provision pathへsymlinkで戻るtargetはrejectする。六roleのlddから得た
  libmpi path/hashはnonempty集合がexactly one distinct pairになることを要求し、その一pairだけをprojectionへ持つ。
  policy IDはcontract hashからjoinしrun recordへ複写しない。
  照合結果の第二array/booleanは保存せずldd rawとsidecarから導出する。
  全stageはこのresolved absolute pathを使う。
- `build-provenance-projection/v1`は全field requiredの
  `{schema_version:const "build-provenance-projection/v1",precision:enum "SP"|"DP",label_bits:enum 32|64,compile_flags:string[],
  commits:[{repository_id:string,commit_role:enum "build_definition"|"openfoam_source"|"thirdparty_source",
  object_hash_algorithm:enum "sha1"|"sha256",oid:algorithm-constrained full OID},...],build_archive_sha256:sha256,
  toolchain_observations:[{role:enum "mpiicx_version"|"mpiicpx_version"|"mpirun_version"|"icofoam_dynamic",
  outcome:process-outcome,stdout_member:relative POSIX path,stdout_b64:base64,
  stderr_member:relative POSIX path,stderr_b64:base64},...],runtime_objects:[runtime object union above,...],
  source_member:relative POSIX path,source_sha256:sha256}`である。`source_sha256`がbuild-sidecar identityを兼ね、
  commitsはcommit_role順にexactly 3、toolchain observationは記載role順にexactly 4、runtime objectはpath byte順uniqueで
  executable role unique/exactly 7とする。semantic objectはprojectionからsource-member pathだけを除いた
  role/outcome/stdout/stderrを使う。`compiler_identity`と`mpi_identity`も対応observationの同じclosed projectionをviewでhashする。
- `build-provision-projection/v1`は
  `{schema_version:const "build-provision-projection/v1",run_id,build_sidecar_sha256,executables:[{role:enum "icoFoam"|"blockMesh"|"decomposePar"|
  "checkMesh"|"mesh-facts"|"partition-audit"|"capture-hardware"|"mpirun"|"perf",requested_path:string,resolved_realpath:string,
  size_bytes:uint,sha256:sha256},...],ldd_sources:exactly 6 [{role:enum "icoFoam"|"blockMesh"|"decomposePar"|
  "checkMesh"|"mesh-facts"|"partition-audit",source_member:relative POSIX path,content_b64:base64}],
  launcher_version:{argv:exact [resolved mpirun realpath,"--version"],outcome:process-outcome,
  stdout_member:relative POSIX path,stdout_b64:base64,stderr_member:relative POSIX path,stderr_b64:base64},
  profiler_version:{argv:exact [resolved perf realpath,"--version"]|null,outcome:process-outcome|null,
  stdout_member:relative POSIX path|null,stdout_b64:base64|null,stderr_member:relative POSIX path|null,stderr_b64:base64|null},
  resolved_libmpi_path:string|null,resolved_libmpi_sha256:sha256|null,
  source_member:relative POSIX path,source_sha256:sha256}`である。build時とrun時を同じrowへ混ぜない。
  executableは記載role順/uniqueでbase 8 roleをexactly once、profileだけ末尾`perf`をexactly once持つ。
  全MPI stageとhardware one-shotはこの検査済みabsolute `mpirun`を使い、PATH検索しない。
  profiler version objectはprofileだけ全field non-null、他variantは全field nullとする。
`runtime-mpi-semantic/v1`はprojectionからpath/member locatorを除いた
`{schema_version:const "runtime-mpi-semantic/v1",mpirun_sha256:sha256,
launcher_version:{outcome:process-outcome,stdout_b64:base64,stderr_b64:base64},resolved_libmpi_sha256:sha256|null}`の
`SHA-256(JCS(object))`である。`mpi_execution_identity`はこのhashを表示し、scoreのmust-matchと
eligibilityへ使う。開発時確認の一時出力へこのhashを永続化しない。
- `source/placement/rank-<rank>.json`は`schema_version:const "rank-placement/v1"/run_id/global_rank/local_rank/local_size/hostname/
  cpu_affinity/numa_mems`を持つ。global/local rankはnonnegative integer、local sizeはpositive integer、hostnameはnonempty string、
  `cpu_affinity`はstrictly increasing unique uint array、`numa_mems`はkernel list grammarのstringまたはnullである。
  global rankのsource候補は`PMI_RANK`、local rank/sizeは
  `MPI_LOCALRANKID/MPI_LOCALNRANKS`、affinityは`os.sched_getaffinity(0)`、NUMAは
  `/proc/self/status`の`Mems_allowed_list`、hostnameは`gethostname()`をsourceにする。
  各declared設定のcanary自身でこれらrank envの存在と期待集合を確認できたrunだけをconformance eligibleにし、
  欠損時の代替rank sourceは持たない。
  reducerはfilenameのrankと`global_rank`、全fileのrun IDとsubject manifest、global rank集合と
  `0..requested_ranks-1`をexact一致させる。各recordで`0 <= local_rank < local_size`、各hostname内で
  local sizeが一値に一致し、local rank集合が`0..local_size-1`であることも要求する。完成
  `parallel.rank_placement` arrayはglobal rank昇順へcanonicalizeする。

`multi-node-placement/v1` validatorは新しいrawやreason fieldを作らず、protocolの個別実行設定、scheduler request/accounting、
`decomposeParDict.numberOfSubdomains`、`solver.runtime_header`、全`rank-placement/v1`、solver launch-effective environmentを
一度だけ照合する。requestのnodes/ranks/resource group/transport policyはprotocolの各fieldとexact一致し、
accounting `nnumu`、runtime headerのdistinct Hosts、placementのdistinct hostnameは`protocol.nodes`、dictionary subdomain、
header `nProcs`/Hosts rank sum、placement count/global rank集合は`protocol.ranks`と一致しなければならない。各placement
hostnameはexact `protocol.ranks/protocol.nodes`件を持ち、headerのhostname/rank-count multisetとplacementから導出した同multisetを
exact一致させ、全recordの`local_size`も同値にする。全rankのlaunch-effective environmentで実`I_MPI_FABRICS`が
一値かつprotocolのtransport policyと一致し、`nodes > 1`かつ値が`shm`ならinvalidにする。配置側の必要sourceが欠ければ
validatorは不成立、全sourceが揃って不一致ならinvalidとし、topology用boolean列、原因列、validation artifactは作らない。
transport sourceだけは同じ規則で既存`transport_valid`へ投影する。これはbench/profileに適用する。
benchの`score_comparison_eligible`はvalidator成立と`transport_valid=true`を直接要求する。
完全導出できるtopology/affinity validation booleanは作らない。
- `run.stage.<name>.launch`は`argv:string[]/cwd:string/stderr_mode:stdout|separate`だけを持つ。
  run-owned stageは`block_mesh|decompose_par|solver|check_mesh|mesh_facts|partition_audit|minimal_hardware_capture|profile_hardware_capture`で、
  最後の二つはregular全variant/profileだけに適用する。terminationは
  `{kind:"exit",code:int}`、`{kind:"signal",signal:int}`、`{kind:"spawn_error"}`のclosed unionとする。
  StageRunnerはchild stdout/stderrを対応stage/solver logにだけ書き、`tee`やechoで`logs/pjm-job.log`へ複写しない。
  PJM logはsupervisor/orchestration messageだけを所有する。
- `perf.pipeline.wall_time_sec`はbench/profileだけで`blockMesh` spawn直前からsolver wait直後まで、
  post-run scan/hash/archiveを含めない。`run.elapsed_sec`はPJM script entryからcompute回収終了までを取る。
- 全OpenFOAM executableのresolved sub-argvは`-fileHandler uncollated`をexactly once含む。mesh sourceは
  `mesh-facts -case <case> -fileHandler uncollated -constant`、complete logは
  `LC_ALL=C checkMesh -case <case> -fileHandler uncollated -constant`で取り、いずれもStageRunnerを通す。
- minimal hardwareの`source/hardware/node-<ordinal>.json`は`hardware-node/v1`で、
  `schema_version:const "hardware-node/v1"/node_ordinal:uint/hostname:string`、`commands={lscpu:{argv:["lscpu","--json"],
  exit_code:int,stderr_member:relative POSIX path}}`、`lscpu_json:object|null`、次のclosed `platform_settings`を持つ。
  `platform_settings={kernel_release:string|null,
  online_cpus:uint[]|null,isolated_cpus:uint[]|null,nohz_full_cpus:uint[]|null,
  memory:{total_bytes:uint|null,hugepage_size_bytes:uint|null,hugepages_total:uint|null},
  numa_balancing_enabled:bool|null,boost:{source_path:string|null,raw:string|null,enabled:bool|null},
  cpufreq_policies:[{policy_id:uint,related_cpus:uint[],driver:string|null,governor:string|null,
  min_hz:uint|null,max_hz:uint|null},...]|null}`で、全field required、`additionalProperties=false`である。
  `lscpu_json`は`LC_ALL=C lscpu --json`のparse済みraw objectで、同じrecordへderived CPU identityを複写しない。
  probe argvは`capture-hardware --mode minimal --subject-kind regular_run --subject-id <run-id>
  --output-root <absolute run>/source/hardware`を共通prefixとし、1 nodeは
  `--node-ordinal 0`、multi-nodeは`--node-ordinal-from-env PMI_RANK`を末尾に加える。probeはsubject manifestと
  output rootのrealpath containmentを検査し、IDをpathから推測しない。
  `platform_settings`のsourceと正規化は次へ固定する。
  - kernel release=`/proc/sys/kernel/osrelease` trim後string。
  - CPU set=`/sys/devices/system/cpu/{online,isolated,nohz_full}`のkernel list grammar。emptyはempty array。
  - `/proc/meminfo`の`MemTotal`と`Hugepagesize`はkBを1024倍してbytes、`HugePages_Total`はuint。
  - NUMA balancing=`/proc/sys/kernel/numa_balancing`の`0|1`をboolへ変換する。
  - boostは`/sys/devices/system/cpu/cpufreq/boost`の`0|1`を優先し、なければ
    `/sys/devices/system/cpu/intel_pstate/no_turbo`の`0|1`を反転する。`{source_path,raw,enabled}`を持つ。
  - cpufreqはnumeric policy ID順に`/sys/devices/system/cpu/cpufreq/policy*`を読み、`related_cpus`、
    `scaling_driver`、`scaling_governor`、`scaling_min_freq`、`scaling_max_freq`を使う。frequencyはkHzを1000倍してHzにする。
    `related_cpus`はASCII whitespace区切りuintをstrictly increasing unique arrayへ変換する。
  CPU-list fileは存在して空なら`[]`、interface不存在またはread不能ならnullにする。cpufreq rootが存在してpolicyが
  0件なら`[]`、root不存在または列挙不能ならnullにする。profile側へ同じ値を再収録しない。
  `nohz_full`だけはwhitespace trim後のliteral `(null)`も`[]`へcanonicalizeする。

`minimal-hardware-projection/v1`は全field requiredの
`{schema_version:const "minimal-hardware-projection/v1",subject_kind:const "regular_run",subject_id:string,node_ordinal:uint,
hostname:string,cpu_identity:{architecture,model_name,vendor_id,cpu_family,model,stepping:string|null,
physical_cores:uint|null,numa_nodes:uint|null},platform_settings:<hardware-node/v1のclosed settings>,
source_member:relative POSIX path,source_sha256:sha256}`である。CPU identityは`lscpu_json.field`からASCII末尾colonを
exactly oneつ除去したlabel `Architecture/Model name/Vendor ID/CPU family/Model/Stepping/Socket(s)/
Core(s) per socket/NUMA node(s)`でparseし、`physical_cores=Socket(s)*Core(s) per socket`、必要label欠損時はnullにする。

`source/workload-manifest.json`は各runの実caseから作る、全field required、
`additionalProperties=false`のclosed
`workload-manifest/v1={schema_version:const "workload-manifest/v1",
members:exactly 7 [{path:one of exact paths,size_bytes:uint,sha256:sha256}]}`だけを持つ。path byte順のexact pathsは`0/U`、`0/p`、
`constant/transportProperties`、`system/controlDict`、`system/fvSchemes`、`system/fvSolution`、
`system/blockMeshDict`。workload identityはmembers arrayのJCS SHA-256で、Factへ複写せずmanifest projectionが所有する。
各fileは同じbytesを`source/workload/<path>`へcopyする。publisher row schemaは次のclosed objectである。

```text
workload-manifest-projection/v1 = {schema_version:const "workload-manifest-projection/v1", subject_kind:const "regular_run",
  subject_id:string, workload_identity:sha256, source_member:relative POSIX path, source_sha256:sha256}
workload-member-projection/v1 = {schema_version:const "workload-member-projection/v1", subject_kind:const "regular_run",
  subject_id:string, path:one of the exact 7 paths,
  content_b64:base64}
```

member rowは親manifest projectionを`subject_kind/subject_id`でjoinし、manifest identity、source member/hash、
contentから完全導出できるsize/hashを各rowへ再掲しない。publisherはdecodeしたbytesのsize/hashをsource manifest
memberと照合し、consumer viewが必要時に同じ式で導出する。
consumer `workload_id`はprotocol dimension、`workload_manifest_identity`はconflict-free manifest projection、
`workload_match`は両方が存在する時だけ`expected_workload_identity = workload_identity`を返し、片側欠損/conflictはNULLにする。

profile hardwareの`capture.json`は全field required、`additionalProperties=false`のclosed
`profile-hardware-capture/v1={schema_version:const "profile-hardware-capture/v1",run_id:run ID,node_ordinal:uint,hostname:nonempty string,
members:[{role:enum "proc_meminfo"|"numa_cpulist"|"numa_meminfo",numa_node_id:uint|null,
path:relative POSIX path,size_bytes:uint,sha256:sha256}]}`である。
membersはrole/node/path順unique、proc_meminfoはnode ID nullでexactly one、NUMA二roleは検出nodeごとに同じIDを一件ずつ持つ。
読取元はrole/node IDから`/proc/meminfo`、`/sys/devices/system/node/node<id>/cpulist`、同`meminfo`へ固定導出し、
同じ`source_path`をrecordへ複写しない。outer one-shot argv/outcomeはStageRunnerの`profile_hardware_capture` stageが一度所有する。
publisherはclosed tagged recordを
`openfoam_profile_hardware_raw_v2`へ転記する。rowは全field required、`additionalProperties=false`の
`profile-hardware-projection/v1={schema_version:const "profile-hardware-projection/v1",run_id,node_ordinal:uint,hostname:nonempty string,record_kind:enum
"node_summary"|"numa_node",numa_node_id:uint|null,postrun_mem_available_bytes:uint|null,
cpulist:string|null,mem_total_bytes:uint|null,mem_free_bytes:uint|null,
source_members:[{role:enum "capture"|"proc_meminfo"|"numa_cpulist"|"numa_meminfo",
path:relative POSIX path,sha256:sha256},...]}`である。全rowにexactly one `capture`を持たせ、node summaryではNUMA field、
NUMA rowではpostrun fieldをnullにし、NUMA rowの`source_members`はcapture/cpulist/meminfoを別entryで保持する。
captureは`gethostname()`を記録し、同runのminimal hardwareとordinal集合・hostname集合および各
`(node_ordinal,hostname)`をexact一致させる。`/proc/meminfo`はASCII `Key: uint kB`のうち`MemAvailable`を、NUMA
`node<id>/meminfo`は`^Node <id> (MemTotal|MemFree):[ \t]+([0-9]+)[ \t]+kB$`を各exactly once要求し、
別node IDのprefixをrejectしてkBを1024倍してbytesへ変換する。duplicate key、非uint、
overflow、unit不一致はそのcaptureを公開しない。`cpulist`はASCII whitespaceをtrimしてkernel list grammarをparseし、
strictly increasing unique CPU集合を最小range表記へcanonicalizeする。空fileは空string、read不能は該当値をnullにする。
`profile_hardware/v1` reducerはこのtableからconsumerへ投影する。
同じ内容のcompound raw fragmentは作らない。
profile post-run prefixは`capture-hardware --mode profile-postrun --subject-kind regular_run --subject-id <run-id>
--output-root <absolute run>/profile/raw/hardware --node-ordinal-from-env PMI_RANK`へ固定する。

profile canaryでprovision validationの`perf --version`とrank wrapperが各solver rankで起動する次のexact child argvを固定する。
`<resolved-perf> stat --no-big-num -x, -o <profile>/perf/rank-<global-rank>.csv -e cycles,instructions,branches,branch-misses,cache-misses -- <resolved-icoFoam> <solver-subargv...>`。
profile bundleのhash済みexecutable componentがMPIのrank executableとなり、argv templateは
`<component_executable> --run-id <subject_run_id> --expected-ranks <expected_global_ranks> --output <rank_sink_template> --perf
<provisioned_executable role="perf"> --solver <stage_executable role="icoFoam"> -- <solver-subargv...>`へ固定する。
wrapperは`PMI_RANK`からrank別sinkを一度renderし、shellを介さず上記child argvをspawnする。launcher側で一CSVを取らず、
multi-nodeでも各rankのprocess treeだけを測る。wrapper/childの失敗時にperfなしでsolverを再実行しない。
`perf-csv/v1`は7列`count_lexeme,unit,event_name,running_ns_lexeme,percent_running_lexeme,
metric_value_lexeme,metric_unit`に固定する。各rank sourceはclosed
`perf-stat/v1={schema_version:const "perf-stat/v1",run_id:run ID,global_rank:uint,items:exactly 5 [item,...]}`で、itemは
`event_name:enum "cycles"|"instructions"|"branches"|"branch-misses"|"cache-misses"/raw_count_lexeme:string/count:decimal|null/unit:string|null/
running_ns:decimal|null/percent_running:decimal|null`である。
`enabled_ns = running_ns / (percent_running / 100)`はconsumer transformだけが導出し、percentageが0/nullならnullとする。
raw itemへ複写しない。itemsは上記enumの記載順に各event exactly onceで、CSVも同じfile順を要求する。
unsupported/not-counted eventもrow自体は必須とし、そのcountだけ`null`にする。他のnumeric fieldは各lexemeがnumericなら保持する。
multiplexed recordも`count/running_ns/percent_running`を保持する。step/pressure/perfのrow ordinalはordered array offsetからpublisherが
projection時に一度導出し、itemへ複写しない。
`runner.perf_parser`がterminal後、archive前にprofile runだけexpected global rank全CSVを読み、source memberが
`profile/raw/perf/rank-<global_rank>.csv`、record run IDがenclosing manifest、rank集合が`0..expected_ranks-1`と一致することを検査して、
`profile.perf_stat.rank.<rank>` fragmentをrankごとに一度emitする。欠けたrankはNULLで、fleet値を部分rankから外挿しない。

Pstream hookは`OPENFOAM_METRICS_PSTREAM_DIR=<absolute runtime>/runs/<run-id>/domain/pstream`をsink binding、
`OPENFOAM_METRICS_RUN_ID=<validated run ID>`をidentity bindingとする。supervisorは`mpirun`前にこのdirectoryを
一度作り、path componentとidentity bindingがrun manifest run IDに一致することを検査する。hookはabsolute
directory文字列からrun IDを推測しない。
score/profile bundleはこのhook componentを持つ時、環境bindingをname byte順にexactly
`OPENFOAM_METRICS_PSTREAM_DIR={absolute_sink_path:<pstream sink ID>}`、
`OPENFOAM_METRICS_RUN_ID={subject_run_id}`の二件持つ。runnerやhook内のcomponent ID hard-codeで補完しない。
`UPstream::myProcNo()`確定後に各rankが`rank-<rank>.jsonl`をopenし、上記envelopeをline-buffered appendする。
正常close時にflush/closeする。write失敗はsolver計算を止めず、そのrunの`collection_complete`がfalseになるだけで、
fallback sinkや再送queueは作らない。

profileのfull hardware rawはnode ordinalごとに
`profile/raw/hardware/node-<ordinal>/{proc-meminfo.txt,
numa/node-<id>-cpulist.txt,numa/node-<id>-meminfo.txt,capture.json}`へ固定する。`capture-hardware`は公開CLIでなく
`collect`から呼ぶinternal probeである。minimal hardwareのraw node recordだけを正本にし、node ordinal順の
CPU識別string配列をconsumerへ投影する。consensusはview派生でrawへ保存しない。

## network captureとIMB projection v1

```text
network-command/v1 = {
  schema_version:const "network-command/v1", stage_name:const "network_imb_mpi1",
  argv:nonempty string[], cwd:string
}

mpi-network-result/v2 = {
  run_id:nonempty string,
  benchmark:enum "PingPong"|"Sendrecv"|"Allreduce",
  process_count:uint>0, message_bytes:uint, iterations:uint>0,
  time_min_us:finite number|null, time_avg_us:finite number|null,
  time_max_us:finite number|null,
  bandwidth_mbytes_per_sec:finite number>=0|null,
  source_member:nonempty relative POSIX path
}
```

IMB source instanceは`source/network/imb-mpi1/{argv.json,stdout.txt,stderr.txt}`をexact membershipとし、
argvはprocess count、`-msglog 0:22`、`-iter 1000`、`-time 1`、`-iter_policy dynamic`、
`PingPong Sendrecv Allreduce`を検証する。parserはstdoutのcomplete benchmark sectionを全体としてacceptするpure functionである。
truncated/parse不能sourceから一部rowを出さない。transfer benchmarkは出力されたsingle/max timeを`time_max_us`へ置き、
collectiveはmin/avg/maxを各列へ置く。存在しない列はNULL、AllreduceのbandwidthはNULLとし、値を再計算しない。

projectionは`mpi_network_results_v2`、grainは
`(run_id,benchmark,process_count,message_bytes)`、row schemaは`mpi-network-result/v2`である。
source instance grainは`run_id + source/network/imb-mpi1/stdout.txt`、instance identityはartifact manifestが所有する
同member SHA-256とする。rowへhashを複写しない。

## artifact projection registry v1

artifactをBigQueryへ転記するentryは`[[artifact_projection]]`で閉じ、canonical fieldは次だけとする。

```text
id, base_table_id, relation_id, conflict_relation_id,
source_artifact_id, source_schema_id, row_schema_id, row_grain,
subject_scopes, publisher_id, transform_id,
conflict_rule, source_member_field?, source_sha256_field?,
source_instance_grain?, source_instance_sha256_field?, parent_projection_id?, parent_join_columns?,
duplication_justification
```

`subject_scopes`はtagged arrayで、run ownerは
`{owner_scope="run",applicable_run_variants=[...]}`、build ownerは`{owner_scope="build"}`とする。publisherは一source instanceを一つの
BigQuery load jobでphysical base tableへappendする。logical relationは全列完全一致を一件へdedupeする。
`source_instance_grain`が同じなのにinstance hashが異なる場合はそのinstanceの全rowを、次に同じrow grainでpayloadが
異なる場合はその全rowをconflict relationへ残し、consumerから外す。direct lineageの二field、または
`parent_projection_id`と明示的`parent_join_columns`の組のどちらか一方だけを必須にする。v1 entryは次である。

| id / relation | source -> row schema | grain | applicability |
|---|---|---|---|
| `openfoam.source_track` / `openfoam_source_tracks_raw_v2` | subject manifest source-track record -> `source-track-projection/v1` | run | run: all variants |
| `openfoam.build_provenance` / `openfoam_build_provenance_raw_v2` | `build-sidecar/v1`+referenced raw -> `build-provenance-projection/v1` | source SHA-256 | build |
| `openfoam.build_provision` / `openfoam_build_provisions_raw_v2` | `build-provision-validation/v1`+ldd raw -> `build-provision-projection/v1` | run | run: all variants |
| `openfoam.minimal_hardware` / `openfoam_minimal_hardware_raw_v2` | `hardware-node/v1` -> `minimal-hardware-projection/v1` | run, node ordinal | run: bench/profile |
| `openfoam.workload_manifest` / `openfoam_workload_manifests_raw_v2` | `workload-manifest/v1` -> `workload-manifest-projection/v1` | subject kind/ID | run: all variants |
| `openfoam.workload_member` / `openfoam_workload_members_raw_v2` | copied exact member -> `workload-member-projection/v1` | subject kind/ID, path | run: all variants; parent=`openfoam.workload_manifest`, join subject kind/ID |
| `openfoam.profile_hardware` / `openfoam_profile_hardware_raw_v2` | `profile-hardware-capture/v1` -> `profile-hardware-projection/v1` | run, node ordinal, kind, NUMA ID | profile |
| `openfoam.mpi_network` / `mpi_network_results_v2` | IMB stdout -> `mpi-network-result/v2` | run, benchmark, process count, message bytes | run: bench/profile; solver成功時 |

direct entryのsource-instance grainはsource track=`run + subject manifest member`、build provenance=`source_sha256`、build provision=`run + validation member`、
minimal hardware=`run/node + node member`、workload manifest=`run + manifest member`、profile hardware=
`run/node + capture member`、対応instance hashはそれぞれsubject manifest SHA-256、
build-sidecar SHA-256、validation source SHA-256、node source SHA-256、workload manifest source SHA-256、capture SHA-256に固定する。
workload memberはconflict-free manifest parentへjoinするためdirect source-instance fieldを持たない。
以下のoverrideを除くdirect entryは`source_member_field=source_member`、
`source_sha256_field=source_instance_sha256_field=source_sha256`に固定する。
profile hardware entryは`source_member_field=source_members[role="capture"].path`、
`source_sha256_field=source_instance_sha256_field=source_members[role="capture"].sha256`という一意selectorに固定する。

## producer/source registry v1

contractの`[[producer]]`は共通field
`id:nonempty unique string/activation/instances`に、次のclosed ownership unionを加える。

```text
{owner_scope:const "run", applicable_run_variants:nonempty unique variant[]}
```

run ownerのactivationは`{kind:"always"}`または`{kind:"bundle_component",component_id:nonempty string}`で、後者のcomponent IDは各applicable variantが
選ぶbundleにexactly one存在する。`instances`は`{kind:"singleton"}`または
`{kind:"cartesian",axes:nonempty sorted unique subset of ["node_ordinal","global_rank","stage_name","invocation_id"]}`である。
axis expected集合はprotocolの個別実行設定、protocol schedule、contract stage setだけから得る。

`path-template`はnonempty segment arrayで、segmentは`{literal:nonempty string}`または
`{token:enum "node_ordinal"|"global_rank"|"stage_name"|"invocation_id"}`のclosed unionである。adjacent literalを一つに結合し、
render後はrelative POSIX pathとする。templateのtokenはproducer axesのsubsetだけを使う。

`[[source]]`は全field requiredの
`{id:nonempty unique string,producer_id:existing producer ID,source_role:nonempty contract role,
storage:enum "fact_fragment"|"run_bundle"|"profile_raw",
path_template:path-template,schema_id:nonempty schema ID,required_when_applicable:bool}`である。同じstorage内で展開後pathをglobal uniqueにする。
producerごとの`storage="fact_fragment"` sourceは0-or-1件とし、そのsource `path_template`だけをwriter/finalizerの正本にする。
producerへ同じtemplateを複写しない。各`[[fact]].source_id`はexactly one source、`member-with-role.role`はexactly one registry roleへ解決する。
finalizerはvariant/bundleからproducerを選び、instanceを一度展開し、
source path集合とrequired fragment集合を得る。別のcode-side expected table、fallback discovery、manifestへのexpected集合copyを作らない。

## fact registry v1

各`[[fact]]`は次のfieldをすべて持つ。

```text
id, key_pattern, source_id, schema_id, logical_type, unit, cardinality,
capture_id, validator_id, reducer_id, duplication_justification?
```

sourceからproducer、owner scope、applicable variant、requirednessを一意にjoinし、factへ複写しない。
`(source.schema_id,fact.schema_id,validator_id,reducer_id)`はcontractのclosed reducer signature catalogにexactly one存在し、
同じvariantで有効なfact key pattern同士をoverlapさせない。

自由文のsource/reducer/validationは許可しない。v1 familyのroutingは次で閉じる。

| key pattern/family | owner/source | validator/reducer | schema/type |
|---|---|---|---|
| `run.identity.*` | `runner.manifest` / subject manifest | `identity/v1` / `identity_projection/v1` | scalar run identity |
| `run.started_at|finished_at|elapsed_sec|exit_code` | `pjm.supervisor` / clocks+exit | `run_lifecycle/v1` / `identity/v1` | timestamp/seconds/int。`run_outcome`はexit code 0/非0からview導出 |
| `run.stage.<name>.launch|termination`, `perf.stage.<name>.wall_time_sec` | `StageRunner` / spawn+wait | `stage_record/v1` / `identity/v1` | schemas above/finite seconds |
| `perf.pipeline.wall_time_sec` | `pjm.supervisor` / monotonic boundaries | `finite_seconds/v1` / `identity/v1` | finite seconds; regular bench/profile only |
| `collection_complete` | `finalizer` / in-memory expected-vs-observed set | `bool/v1` / `identity/v1` | bool |
| `artifact.build_manifest_sha256|instrumentation_bundle_sha256` | runner/package manifests | `artifact_index/v1` / `artifact_projection/v1` | SHA-256 |
| `scheduler.request` | `runner.submission` / submission request | `scheduler_request/v1` / `identity/v1` | `scheduler-request/v1` JSON |
| `scheduler.accounting` | `runner.postrun` / pjstat raw | `scheduler_accounting/v1` / `pjstat/v1` | `scheduler-accounting/v1` JSON |
| `scheduler.submit_job_id|scheduler.job_entry_job_id` | finalizer / submission result + job-entry | `job_id/v1` / `identity/v1` | source-specific string、欠損時key absent |
| `env.job_entry.*` | supervisor / job-entry snapshot | `environment_snapshot/v1` / `environment/v1` | Base64 string |
| `env.host_exec.common.*`, `env.host_exec.rank.<rank>.*` | supervisor+rank wrapper / snapshot+delta | `rank_env/v1` / `environment_common_delta/v1` | Base64 string |
| `parallel.rank_placement` | rank wrapper / rank placement sources | `rank_placement/v1` / `rank_placement/v1` | ordered JSON array |
| `mesh.topology` | postrun auditor / mesh probe | `mesh_topology/v1` / `identity/v1` | `mesh-topology/v1` JSON |
| `mesh.partition.requested|observed` | supervisor/auditor / dict+mesh files | respective schema validator/reducer | schemas above |
| `solver.runtime_header` | log parser / solver log | `openfoam_header/v1` / same | JSON |
| `solver.pstream.*` | Pstream parser / rank JSONL | `pstream_rank/v1` / same | schemas above |
| `solver.step_timings|pressure_solves|log_markers` | log parser / solver log | respective schema validator/reducer | schemas above |
| `profile.perf_stat.rank.<rank>` | `runner.perf_parser` / rank別profile CSV after terminal | `perf_stat/v1` / `perf_stat/v1` | rank別exact five ordered event records -> logical `openfoam_perf_counters_v2`。perf versionはbuild-provision sourceだけが所有 |
| `network.imb_mpi1.*`, `software.imb_mpi1.version` | network capture / validated argv+IMB output | `imb_config/v1` / `identity_projection/v1` | 独立scalar facts |
| `run.stage.network_imb_mpi1.termination`, `perf.stage.network_imb_mpi1.wall_time_sec` | `StageRunner` / spawn+wait | `stage_record/v1` / `identity/v1` | 通信失敗はsolver terminationを変更しない |

`openfoam_rank_placements_v2`は`parallel.rank_placement`のordered arrayを`(run,global_rank)`へ一度だけUNNESTし、
hostname、local rank/size、CPU affinity、NUMA memsをlosslessに表示する。これはconsumer viewであり、新しいFactや
artifact projectionを作らない。conflict-free Factが実在する時だけCROSS JOIN UNNESTし、source欠損、非適用、conflict時は
0行とする。expected-rank skeletonへのLEFT JOINやplaceholder rowは作らない。

consumer columns listed in the plan may only use these reducer IDs:

- identity: `identity_projection/v1`
- source/artifact: `artifact_projection/v1`
- quality: `completeness/v1`または`official_openfoam/v1`
- hardware/config consensus: `consensus/v1`
- solver/performance: `official_openfoam/v1`
- profile counter: `perf_counter_projection/v1`
- environment: `environment_decode/v1`
- Data Status: `archive_attempt_status/v1`

A consumer column entry is closed by
`name/type/unit/source_refs/scope_cardinality/reducer_id/conflict_rule/transform_id/applicable_run_variants/
dimension_name/allowed_classes`。`source_refs`はordered
`[{kind="fact"|"projection"|"dimension",id,json_path?,bindings?},...]`で、異種sourceの混合とreducer入力順を明示する。
`dimension`はrunのplanned/observed dimension、projectionはconflict-free logical relationをqueryする。
archive memberを直接読む`artifact` refは許さず、lineageだけprojectionのsource member/hashから辿る。
projection refの`bindings`はnonempty
`[{applicable_run_variants,consumer_field,projection_field,projection_subject_kind}]`で、variant集合を重複なく覆う。
run-keyed projectionは`run_id -> run_id`、regular subject-keyed projectionは
`run_id -> subject_id, regular_run`、build projectionはFact
`artifact.build_manifest_sha256 -> source_sha256, build`を明記し、SQL生成器へ暗黙joinを残さない。
dimension refの`bindings`はordered nonempty `[{consumer_field,dimension_field},...]`である。
`workload_id`と`expected_workload_identity`はrun manifestのplanned dimensionから得て、actual workload projectionと比較する。
plan記載列でこのentryを持たない列は
生成しない。

## NULLと不完全run

取得できなかった固定幅consumer値と当該variantで非適用の値は、どちらも`NULL`だけを返す。source-grainのlong relationは
実在source rowだけを表示し、欠損/非適用row、field別reason code、missing status、placeholderを作らない。run-levelではexpected source fileとproducer outputが揃ったかを
表す`collection_complete`だけを持ち、falseでも原因分類を要求しない。これは稀な採取失敗を多段の耐久処理で
救済するための契約ではなく、正常pathで取得対象が初めから実装漏れになることを防ぐための契約である。

## package ownership

- `run-artifacts.tar.zst`: control/source/domain/log/resultとtar rootの`bundle.manifest.json`
- `metrics.jsonl`: merge済みraw rowsだけ
- `profile-raw.tar.zst`: profile protocolでapplicableなperf rawとhardware rawだけ
- `artifact-manifest.json`: 上記outer fileのidentityだけ
- workflow operational row: GitHub artifact ID、home destination、upload/SCP/publish outcomeだけ

runtimeではbundle manifestを`archive-staging/bundle.manifest.json`へ作り、tar内ではbasename
`bundle.manifest.json`にする。GitHub Artifact内の基本fileは`run-artifacts.tar.zst`、`metrics.jsonl`、
`artifact-manifest.json`である。bundle URIはraw metricでなくworkflow operational rowからjoinする。
同じ実byteを二つのtarへ入れない。benchではprofile tarや欠損用recordを作らない。
成功merge後のproducer fragmentは`metrics.jsonl`の完全な部分集合なのでartifactへ入れず、runtime一時fileを
削除する。merge前のpartial/tmpは失敗診断で手元に残り得るが、publisherのFact入力にしない。

profile初版はhash済みrank wrapperの`perf stat` modeだけを対象にする。実装時にそのscriptのexact argv、
provision validationの`perf --version`、event listをcontractへ固定し、rank別CSVを
`event_name/raw_count_lexeme/count/unit/running_ns/percent_running`の順序付きrecordへreduceする。
unsupported/not-counted countだけnull、個別の非numeric fieldだけnullとし、
multiplexed numericは捨てない。
各declared設定のprofile canary前にexact argv/event listを固定できない場合、その設定ではprofileを開始しない。
