# OpenFOAM v2 contract schema handoff（旧merge/projection設計資料）

> この文書は旧contractの履歴資料である。現行のrun/key/value送信と、
> 重いmesh再走査を行わないcontractは
> `research/experiment-metrics-v2-key-catalog.md` を正本とする。

## 役割

本文書は[`experiment-metrics-v2-plan.md`](experiment-metrics-v2-plan.md)の方針と
[`experiment-metrics-v2-observation-map.md`](experiment-metrics-v2-observation-map.md)の取得対応を、
`openfoam-v2.toml`とJSON Schemaへ転記するためのフィールドレベルの正本である。実装者はフィールド名、型、enum、ソース、
リデューサを独自に解釈・拡張してはならない。新しいフィールドが必要な場合は、事前に本文書およびコントラクトIDを更新する。

本文書はraw値を複製しない。ソースartifact、`run/key/value`ファクト、クエリ時のコンシューマの関係のみを定義する。
フィールド名末尾の`?`はoptional、値型の`|null`のみがnullableを表す。

## canonical identity

| 項目 | v1定義 |
|---|---|
| repository ID | 固定文字列 `apac2026-openfoam`。実行時のGit remote URLはidentityに使用しない |
| regular run ID | `r-` + OS CSPRNG 16バイトの小文字16進数32文字 |
| JSON canonical bytes | RFC 8785 JCS、UTF-8。オブジェクトキーの重複、NaN、Infinityは禁止 |
| committed TOML identity | チェックアウトしたファイルの実バイト列に対するSHA-256。改行やコメントの変更も別identityとして扱う |
| Git object identity | `{object_hash_algorithm:enum "sha1"|"sha256",oid}`。oidはアルゴリズムに応じ正確な小文字40桁または64桁の16進数 |
| artifact member path | アーカイブのルートからの相対POSIXパス。絶対パス、`..`、空のコンポーネントは禁止 |
| runtime-only locator | `locator_kind=runtime_relative_ephemeral`とケース/実行時ルートからの相対POSIXパス |

IDはPJMジョブID、PID、実行時刻、ブランチ名から生成してはならない。マニフェスト自身のハッシュはマニフェスト本文へは含めず、参照側または
外部マニフェストに配置する。

## source track v1

`source-track-projection/v1`は全フィールド必須（required）、`additionalProperties=false`の
`{schema_version:const "source-track-projection/v1",run_id,run_purpose:enum "bench"|"profile",
repository_identity:const "apac2026-openfoam",object_hash_algorithm:enum "sha1"|"sha256",
score_reference_commit:oid|null,profile_base_commit:oid|null,source_head_commit:oid,
source_track_manifest_sha256:sha256,source_member:relative POSIX path,source_sha256:sha256}`である。
bench runはscore reference、profile runはprofile baseを使用する。

subjectマニフェストに埋め込む`source-track/v1`は
`object_hash_algorithm/base_role/base_commit/head_commit`を持つ閉じたオブジェクト（closed object）である。
bench runでは`base_role=score_reference`、profile runでは`base_role=profile_base`とし、baseがheadの祖先（ancestor）であることを
ジョブ投入前に検証する。開発時のOFF/ONソース差分はv2 artifactへ保存しない。
## subject manifest v1

`control/run-manifest.json`は次の閉じたフィールドを持つ。v2で永続化するrunの用途（purpose）は`bench|profile`のみである。

| field | type | 必須区分 |
|---|---|---:|
| `schema_version` | const `run-manifest/v1` | 必須 |
| `subject_kind` | const `regular_run` | 必須 |
| `run_id` | run ID | 必須 |
| `run_purpose` | enum `bench|profile` | 必須 |
| `repository_id` | const `apac2026-openfoam` | 必須 |
| `source_track` | `<source-track/v1>` | 必須 |
| `observed_control_plane_sha256` | SHA-256 | 必須 |
| `instrumentation_bundle_sha256` | SHA-256 | 必須 |

非該当フィールドはJSONの`null`ではなく項目自体を欠落（absent）させる。期待されるプロデューサ/ファイルの集合はマニフェストへ複写せず、
実装の用途適用性（purpose applicability）とバンドルコンポーネント選択からファイナライザが1回導出する。

開発中の非擾乱確認は通常のv2 runマニフェスト、artifact、Fact、リレーション、決定記録へ保存しない。
一時的な比較出力は確認後に破棄し、コントラクトにrunバリアントやコンシューマを追加しない。

## instrumentation bundle v1

`control/instrumentation-bundle.json`は全フィールド必須、`additionalProperties=false`の次の閉じたオブジェクトである。

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

`component`は全フィールド必須の
`{component_id:nonempty string,sink_ids:sorted unique string[],activation:activation}`であり、
component IDはUTF-8バイト順に一意とする。`activation`は
`kind`でタグ付けされた次の5種類のみとし、すべてのユニオンメンバーは`additionalProperties=false`、記載フィールドをすべて必須とする。

```text
{kind:"in_process_hook", source_commit_role:const "openfoam_source",
 source_path:repository-relative POSIX path, symbol:nonempty string, event_schema_id:nonempty string}
{kind:"executable", artifact_relative_path:relative POSIX path,
 argv_template:nonempty argv-argument-template array}
{kind:"sampler", artifact_relative_path:relative POSIX path,
 argv_template:nonempty argv-argument-template array, sample_interval_sec:positive finite decimal}
{kind:"control", control_id:nonempty contract-registry ID, timeout_sec:positive finite decimal}
{kind:"postrun_parser", parser_id:nonempty string, source_schema_id:nonempty string}
```

template segmentは閉じたユニオン `{literal:nonempty string}`、
`{token:enum "runtime_root"|"case_root"|"artifact_root"|"component_executable"|"node_ordinal"|"global_rank"|
"invocation_id"|"subject_run_id"|"expected_global_ranks"}`、
`{token:const "stage_executable",role:enum "icoFoam"|"blockMesh"|"decomposePar"|"checkMesh"|"mesh-facts"|"partition-audit"}`、
`{token:const "provisioned_executable",role:const "perf"}`、
`{token:const "sink_path",sink_id:nonempty string}`、`{token:const "rank_sink_template",sink_id:nonempty string}`とする。argv argument templateは空でない
セグメント配列とし、隣接するliteralは1つに結合する。sink pathはバインドされた`source_id`のレジストリ`path_template`からのみ取得する。
`artifact_relative_path`はsource trackに記録された実行チェックアウトを基準とする。実際に起動された
絶対パスとargvはStageRunner Factが管理する。
`stage_executable(role)`はbuild-provision validationにおける同一roleの検証済み絶対realpathへ展開する。
executableおよびsamplerにおいてPATH探索やフォールバックは許可しない。実際のrun ID、絶対実行時ルート、実際のタイムスタンプはバンドルのバイト列に含めない。ランナーは
`score -> bench`、`profile -> profile`の固定マッピングによってバンドルを1つ選択し、
その全コンポーネントを一度アクティベートする。コンポーネント別の適用性はこのマッピングの完全な重複となるため保存しない。
bench runは通常コントラクトのscoreバンドルを使用する。開発時確認の証跡は保存および継続的な照合を行わない。用途（purpose）はsubjectマニフェスト、実argv/cwdはStageRunner Fact、
sink path templateはソースレジストリ、実バイト列を含む外部ファイルidentityはartifactマニフェストが管理する。`sink_bindings`はsink IDバイト順に一意かつ
source IDについて一意であり、全コンポーネントの`sink_ids`の和集合とバインディングID集合は完全に一致する。各バインディングソースのプロデューサactivationは、
そのsink IDを持つコンポーネントIDの`bundle_component`と完全に一致する。sink tokenおよびコンポーネントのIDは対応するバインディングに存在し、hookの`source_commit_role`は
ビルドプロベナンスに同名のcommitが存在すること、`source_path`はそのビルドソースツリー内に存在することを検証する。
最終的な実行時バイトidentityはビルドセマンティックハッシュが保持し、バンドルへcommit OIDを複写しない。
ランナーはアクティベート前に、当該バリアントとプロトコルのnode/rank/invocationコンテキストで使用するsinkを1回レンダリングし、全パスが相対的に安全（relative-safe）であり、かつ
コントラクトから展開された全プロデューサインスタンス `(sink_id,node_ordinal,global_rank,stage_name,invocation_id)` の間でグローバルに一意であることを検証する。
レンダリングされた相対sinkパスはsubjectの絶対実行時ルートに結合して正規化し、結果のrealpathの親ディレクトリが実行時ルート内に
収まる場合のみ絶対sinkパスとして採用する。環境変数値のテンプレートは`{literal:nonempty string}`、
`{token:const "subject_run_id"}`、`{token:const "absolute_sink_path",sink_id:nonempty string}`のみからなる閉じたユニオンとする。
バインディング名はバイト順に一意、sink IDは`sink_bindings`に存在し、ランナーはソルバー起動環境へレンダリング結果を一度設定する。
同一の単一インスタンスバインディングのみ、単一パスでよい。executableおよびsamplerのargv第0引数は正確に1つの
`component_executable`セグメントとし、同トークンはテンプレート内で1回のみ出現させ、シェルを介さずにargv配列を直接spawnする。
`stage_executable(role)`は第1引数以降にのみ配置できる。
`provisioned_executable(role="perf")`トークンも第1引数以降にのみ配置し、build-provision validationの
検証済み絶対パスへ展開する。`rank_sink_template`はprofileのハッシュ済みrankラッパーのみが使用でき、`global_rank`を1つ含む
バインディングソースのパスプレビューを、そのトークンのみリテラル`@@GLOBAL_RANK@@`として残した絶対パスプレビューへ展開する。リテラルセグメント内での
同一マーカーの記述は禁止する。ランナーは期待されるrank集合へ事前展開されたパスの一意性を検証し、
ラッパーはMPIプロセス内の`PMI_RANK`を符号なし整数として読み取り、`0 <= rank < expected_global_ranks`を確認してその単一パスのみをレンダリングする。
他のrank環境変数の探索や共通ファイルへのフォールバックは行わない。profileバンドルのハッシュ済みrankラッパーがargvの第0引数となり、
各rankでこのトークンのperfを直接起動する。
実行後の第二アクティベーション判定、フォールバックバンドル、曖昧な軽量ラベルなどは作成しない。

referenceバンドルは`source_paths=[]`、`components=[]`、`environment_capture_scopes=[]`、`sink_bindings=[]`、
`environment_bindings=[]`に固定する。
scoreおよびprofileバンドルは`source_paths`と`components`を非空とする。共通の外側タイマー、ログ、中立的な結果はコントラクトグラフが
管理し、referenceバンドルの疑似コンポーネントとしては扱わない。
コントラクトは閉じた`source_path_policy={score_allowed:sorted unique repository-relative POSIX paths,
profile_only:sorted unique repository-relative POSIX paths}`を一度保持し、両集合を互いに素（disjoint）とする。scoreの`source_paths`は
`score_allowed`の部分集合、profileは両集合の和集合の部分集合とする。scoreのallowlistは計測実装およびそのバンドル/プロトコルの
メタデータのみを列挙し、ワークロードの厳密な7ファイルパス、実行設定、PJM、共通ランナー、profile専用パスは含めない。

## environment snapshot v1

全スコープの`.snapshot`は名前のバイト順による`name\0value\0`の反復形式とする。POSIX環境変数のname/valueにはNUL文字を
含められないため、可逆的かつ損失のない（lossless）表現となる。末尾も必ずNULで終端する。パーサーは生のname/valueを変更せず、BigQueryファクトではnameを
単射エスケープし、`host-exec.snapshot`のUTF-8値を平文で保存する。このフォーマットを使用するのは`source/env/job-entry.snapshot`と
`source/env/host-exec.snapshot`のみである。

rank別の環境変数差分は収集しない。rank/ノード固有の情報はプロセス配置、スケジューラ、ハードウェアの各スキーマが管理する。

## control artifact schemas

以下はすべて全記載フィールド必須、`additionalProperties=false`である。`member`は閉じた
`{path:relative POSIX path,size_bytes:uint,sha256:sha256}`、`process-outcome`は閉じたユニオン
`{kind:const "exit",code:int}` | `{kind:const "signal",signal:positive int}` |
`{kind:const "spawn_error"}`である。稀な障害に対するリトライカウンタ、原因コード、代替ソースは追加しない。

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

`scheduler-request/v1`は投入時における個別の要求スナップショット（requested snapshot）である。初版の玄界canaryテストにおける
設定値は`(nodes,ranks)=(1,120),(2,120),(4,120)`であり、`ranks % nodes = 0`、リソースグループ`a-batch`、
Scotch 120領域分割、正確な`mpirun -np 120 -ppn <120/nodes>`を要求する。トランスポートポリシーは1ノード時のみ
`shm`、2/4ノード時は`shm:ofi`とする。ノード/rank別のプロデューサインスタンスはプロトコルの`nodes`と`ranks`から展開し、
ノード数別の専用スキーマやcollectorは作成しない。各値はBigQueryおよびスプレッドシートでも独立列へ投影し、組み合わせIDやオブジェクトは設けない。

`member-with-role`は`member`にコントラクトレジストリの閉じたsource-roleを1つ加えたオブジェクトであり、パスのバイト順に一意に整列する。
バンドルマニフェストは自身や外部のsidecarを含めない。artifactのfilesは記載されたrole順に一意であり、bench runでは
`run_bundle,metrics`、profile runでは`run_bundle,metrics,profile_raw`を過不足なく1件ずつ保持する。ファイル名はroleから
`run-artifacts.tar.zst|metrics.jsonl|profile-raw.tar.zst`へ一意に導出され、マニフェストへ重複記録しない。
artifactマニフェスト自身およびアップロードIDは含めない。計算処理やcollectorが失敗した場合であっても、スーパーバイザがファイナライザまで到達できたrunは、
完成済みのログ/ソースおよび`collection_complete=false`を保持する通常のartifactセットを1回生成する。
`request_sha256`は実際のスケジューラ要求ファイルのバイト列ハッシュであり、terminal argv末尾のジョブIDはsubmissionおよびjob-entryと一致が確認されたIDである。

`scheduler-accounting/v1`は固定されたコマンド`pjstat --history -S --choose jid,st,sdt,elp,ec,sn,pc,nnumu,mmszu,uctmut,sctmut --data --delimiter "\t" <source-specific-job-id>`の1行を次の閉じたオブジェクトとして保持する。返却された`jid`はargv末尾のIDと一致しなければならない。

```text
schema_version: const "scheduler-accounting/v1"
jid, st, sdt: string
elp: {lexeme:string, seconds:finite decimal|null}
ec, sn, pc, nnumu: {lexeme:string, value:int|null}
mmszu: {lexeme:string, bytes:uint|null}
uctmut, sctmut: {lexeme:string, seconds:finite decimal|null}
```

`elp.seconds`は括弧内の十進数秒、`uctmut/sctmut.seconds`はミリ秒の字句を`decimal / 1000`で換算した値、
`mmszu.bytes`は括弧内の十進数をパースした値である。
コマンドの生のstdout/stderr/バージョンはログmemberに残し、数値パースが不可能な場合は対応する数値フィールドのみをnullとする。

フィールド別の`missing_*`、原因コード、問題発生数、収集検証ファイルなどは保存しない。ファイナライザは不変な
コントラクト/プロトコル/バンドルから導出された期待プロデューサ/ファイル集合をメモリ上で1回照合し、rawファクト
`collection_complete:bool`およびマージ済み`metrics.jsonl`を生成する。
ワークフローが取得するGitHub artifact ID、SCP成否、ホームパスは、1試行1行の運用テーブルのみが管理する。

## 開発時の非擾乱確認

実装中に行うOFF/ON比較はv2の収集対象外である。比較用ジョブ、標準出力、集計値はその場で
性能低下がないことを確認するためだけに用い、runマニフェスト、artifactセット、BigQuery、スプレッドシート、
Git管理下の決定記録へは保存しない。したがって非擾乱確認用のrun、スキーマ、リレーションは定義しない。
## OpenFOAM compound schemas

### requested partition v2

`source/mesh/decomposeParDict`のファイルバイトSHA-256をidentityとし、`mesh.partition.requested`は次の項目のみを投影する。

```text
schema_version: "partition-requested/v2"
source_sha256: sha256
subdomains: positive int
method: enum "scotch" | "hierarchical" | "multiLevel"
```

これは`decomposePar`をspawnする直前に、実際のargvが参照するファイルバイト列から生成する。method固有の係数はrawコピーにのみ
残し、別メトリクスへは展開しない。将来的にmethodを追加する場合はスキーマおよびコントラクトを更新する。
Runsテーブルの`requested_partition_identity`はこの`source_sha256`そのものとし、ラッパーオブジェクトを再ハッシュしない。

### Pstream source v1

全レコードエンベロープは全フィールド必須、`additionalProperties=false`の
`{schema_version:const "openfoam-pstream-event/v1",run_id:validated run ID,
producer_id:const "openfoam.pstream-hook/v1",rank:uint,sequence:uint,
event_type:enum "startup_applied"|"runtime_current"|"runtime_change",payload:event-specific closed object}`である。
`payload`はイベントタイプと下記スキーマのいずれか1つに正確に対応し、他イベントのフィールドは保持しない。sequenceはrankごとに0から開始し、
ファイル順に1ずつ連続して増加する。startup/runtimeの番兵レコードを各1件保持し、startup → runtime → runtime_change*の順序とする。
エンベロープのrun IDはrunマニフェストと一致させ、rankはファイル名と一致させる。

`startup_applied` payload:

- `node_comms_control:int`
- `node_comms_min:int`
- `using_node_comms:bool`
- `num_nodes:positive int`
- `topology_control:int`
- `configured_mpi_buffer_value:int`（optimisation switchのaccepted signed value）
- `environment_mpi_buffer_bytes_applied:positive int|null`（環境変数値が有効な正の整数として採用された場合のみ値を設定）
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

`runtime_change` payloadは`field`を上記runtimeフィールドのenumとし、`old`と`new`をそのフィールドと同一の論理型とする。
配列の順序はソースの`sequence`昇順とし、変更が0件の場合のみ`[]`を生成する。
`configured_mpi_buffer_value`は負数や0も正当なraw設定値として保持し、環境変数の不存在、パース失敗、非正値の場合は
`environment_mpi_buffer_bytes_applied=null`とする。`attached_buffer_bytes`のみがクランプ後の実アタッチ量である。
`pstream_buffers_algorithm`はソースの整数値をそのまま保存し、`<=0`/`>0`の真偽値クラスを第2のraw値としては設けない。
`max_comms_size`も符号付き整数値をそのまま保存し、負数をバイト単位へ曖昧に変換しない。

### observed partition v1

`source/mesh/partition-observed.json`は全フィールド必須、全オブジェクト`additionalProperties=false`の次の閉じたスキーマを持つ。

v1プロトコルは全OpenFOAMステージの正確なargvに`-fileHandler uncollated`を指定し、ランタイムヘッダーにおける実際の
`fileHandler=uncollated`を要求する。パーティションリーダーは`processor<rank>/constant/polyMesh`のみを対象とし、
`processors<N>`の集約配置（collated layout）は自動探索しない。別ハンドラを検証する場合はプロトコルおよびスキーマを更新する。

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

`subdomains`はrank昇順かつrankについて一意、`interfaces`は`(lower_rank,upper_rank)`昇順かつ一意とし、
`lower_rank < upper_rank`を満たすものとする。subdomain配列長およびrank集合はrequested partitionのsubdomainsと一致させ、
`sum(cell_count)`は`mesh-topology/v1.cells`と一致させる。globalセル数やsubdomain数をこのオブジェクトへ重複して記録しない。

`serial_mesh`はシリアルメッシュの`constant/polyMesh/{points,faces,owner,neighbour,boundary}`を記載フィールド順に過不足なく1件ずつ保持する。
各subdomainの`mesh`はプロセッサ側の`points/faces/owner/neighbour/boundary`に、`addressing`は
`cellProcAddressing/faceProcAddressing/pointProcAddressing/boundaryProcAddressing`に1対1で対応する。
SHA-256はヘッダーを含む実ファイルのバイト列ハッシュ、パスはケースルートからの相対POSIXパスとする。
`min/max/mean/imbalance`は`subdomains[].cell_count`の完全な部分集合であるためrawへは保存せずview側で導出する。
`observed_partition_identity`は、パスとサイズを除外したシリアルメッシュ5ファイルのSHA-256、rank/セル数/プロセッサメッシュ5ファイルのSHA-256/アドレッシング4ファイルのSHA-256、およびinterfaceタプルのJCS射影に対する
SHA-256とする。

`partition-audit`は`<resolved-partition-audit> -case <case> -fileHandler uncollated -constant -output <case>/source/mesh/partition-observed.json`の単一経路のみを用い、ソルバー終了後に該当ケースに対して1度実行する。
これは同一ビルドsidecarのOpenFOAMへリンクしたネイティブユーティリティであり、`polyMesh`、`labelIOList`、`processorPolyPatch` APIを通じて
ASCII/バイナリ形式、ラベル幅、エンディアンの差異をOpenFOAM自身に解釈させ、符号付き`faceProcAddressing`の正負符号を保持する。
シリアルメッシュを1度読み込み、プロセッサディレクトリはrank順に1つずつメモリ解放しながら処理する。グローバルなセル/面/点の
存在検証にはメッシュサイズで上限が決まるビットセットを用い、interfaceの照合にはマップ済みグローバル面ID集合のみを保持することで、全プロセッサメッシュの同時メモリ保持を回避する。64MセルcanaryにおいてピークRSSがノードメモリの25%以下となることをリリーステストで検証するが、別パーサーやメモリ超過時のフォールバック処理は作成しない。各プロセッサパッチを
`lower_rank=min(myProcNo,neighbProcNo)`、`upper_rank=max(...)`へ正規化し、双方のrankの境界（boundary）に過不足なく1回ずつ存在し、かつ`nFaces`が一致する場合にのみ1つのinterfaceへ集約する。セルアドレッシングから各シリアルセルが全rankにわたって過不足なく1回現れること、interface検証はlower/upper各rankのsubdomainが1度保持するboundaryロケータから読み取り、interface側へロケータを重複記録しない。
rankは`0..len(subdomains)-1`でなければならない。セルアドレッシングはローカルセル数と同一長であり、各値は
`0 <= value < mesh-topology.cells`を満たしrank内で一意、全rankの和集合が各シリアルセルを過不足なく1回含むものとする。
面アドレッシングはゼロを禁止し、`1 <= abs(label) <= mesh-topology.faces`を満たし、ローカル面数と同一長とする。
シリアルメッシュのowner/neighbourとセルアドレッシングから、各シリアル内部面の両側セルが属するrankを求める。同一rankに属する場合はそのrankの
非プロセッサ面として過不足なく1回、異なるrankに属する場合は双方のrankの対応プロセッサパッチに過不足なく1回ずつ現れ、2つのエントリの
`abs(faceProcAddressing)-1`が同一で正負符号が反対でなければならない。シリアル境界面はownerセルのrankにおける非プロセッサパッチに過不足なく1回のみ現れる。したがって全グローバル面の出現回数は、未分割内部面および境界面が1回、分割内部面が計2回となり、余分な出現や欠落を許容しない。各プロセッサパッチ間でも、マップされたグローバル面ID集合および件数が対向側と完全に一致しなければならない。
点アドレッシングはローカル点数と同一長であり、rank内で一意、各値は`0 <= value < mesh-topology.points`とし、rank間の重複は許容するが
全rankの和集合はシリアル点集合と完全に一致させる。各ローカル面の頂点リストを点アドレッシングによってシリアルIDへ写像し、対応するシリアル面の
頂点巡回順と、面アドレッシングが正であれば巡回回転（cyclic rotation）、負であれば逆巡回回転（reverse cyclic rotation）として完全に一致させる。
境界アドレッシングはローカル境界パッチ数と同一長とし、プロセッサパッチは`-1`、非プロセッサパッチはシリアル境界インデックスの範囲内であり、
プロセッサメッシュ境界のパッチタイプおよびパッチ名との対応が一致しなければならない。

### mesh、solver log v1

本節のオブジェクトは全フィールド必須、フィールド名末尾の`?`はoptional、値型の`|null`のみがnullable、
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

公式ヘッダーに`Hosts`ブロックが存在しない場合は`hosts=[]`とする。ブロックが存在する場合はホスト名のバイト順に一意に正規化し、
各rank数を正の符号なし整数とし、`sum(ranks)=nprocs`とする。Build/Arch/Exec/nProcs/fileHandler/Hostsが複数回出現する場合は、
パース後の閉じたヘッダーオブジェクトがすべて完全一致する場合にのみ1つのオブジェクトへ集約し、1つでも異なればヘッダーソースを不成立とする。
`hosts=[]`自体は公式マーカーの妥当性をfalseとはせず、ホスト照合を必要とする比較のみを不適格とする。

`pressure-solve`に定数フィールド`field="p"`は保存しない。ソース正規表現は`Solving for p`のみとする。NaNやInfinity等の
非有限残差は生の字句（lexeme）を保持したうえで数値をnullとし、公式妥当性をfalseとする。配列はログの出現順とし、
単一要素から初回値、最終値、カウント等の第2のraw keyを作成しない。

## build、probe、実行source recordのclosed schema

Git管理下の実行設定はartifactへコピーせず、そのIDやハッシュ値もメトリクスへ保存しない。実行時に読み取る設定構造（shape）は以下の通りである。

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

すべてのv1プロトコルにおいて`ranks % nodes = 0`を要求し、期待されるノード序数は`0..nodes-1`、期待されるグローバルrankは
`0..ranks-1`、期待されるノードあたりrank数は`ranks/nodes`として個別フィールドから展開する。要求されるプロデューサはコントラクトの
バリアント適用性（variant applicability）が、計測モードはプロトコルおよびバンドル選択が管理する。
最上位の`control_plane_files[].path`はscoreバンドルの
`source_paths`と重複せず、各blob OIDは実行時チェックアウトと完全に一致させる。実行設定用の別マニフェストや
そのID/ハッシュは作成せず、`nodes`、`ranks`、`resource_group`、`transport_policy`をプロトコルが個別に保持する。
期待されるワークロードidentityは、厳密な7ファイルパスのpath/size/SHA-256配列に対するJCSハッシュである。
`observed_control_plane_sha256`は各runの実行チェックアウトから
プロトコルパス順に一度観測し、別artifactやFactへ配列を重複記録しない。

`control/build-sidecar.json`は全フィールド必須、`additionalProperties=false`の次の`build-sidecar/v1`である。

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
partition_audit_source: {source_commit_role:const "build_definition",
  repository_paths:exactly 3 sorted unique repository-relative POSIX paths,
  git_blob_oids:exactly 3 algorithm-constrained full OIDs}
```

source commitおよびtoolchain配列は記載role順に各role過不足なく1回ずつ現れる。runtime objectは閉じたユニオン
  `{kind:"executable",role:enum "icoFoam"|"blockMesh"|"decomposePar"|"checkMesh"|"mesh-facts"|"partition-audit"|"capture-hardware",
  path:relative POSIX path,size_bytes:uint,sha256:sha256}`または
  `{kind:"shared_library",path:relative POSIX path,soname:nonempty string,size_bytes:uint,sha256:sha256}`である。パスのバイト順に一意とし、7つの
  executable roleを過不足なく1回ずつ必須とする。
パーティション監査ソースblobのアルゴリズム/OIDツリーは`source_commits[commit_role="build_definition"]`から継承し、
`partition_audit_source.repository_paths[i]`と`git_blob_oids[i]`は同一のパスバイト順オフセットで対応する。キャプチャの生成エントリポイントハッシュは
`capture-hardware` runtime objectが保持する。
  ワークフローのrun/試行は運用ビルド行のみが管理し、コンテンツハッシュ付きsidecarへは含めない。
  共有ライブラリ集合は、6つのELF実行可能ファイル（`capture-hardware`を除く）の`DT_NEEDED`を`RPATH/RUNPATH`およびビルド時ローダー解決により再帰的に
  解決したうち、ビルドアーカイブが保持する実ファイルの全体である。シンボリックリンクはアーカイブ内で解決し、
  リンク先の相対パス、サイズ、コンテンツSHA-256を一度保存する。リンク切れ（dangling）やアーカイブ外への参照、未解決のアーカイブ所有
  `DT_NEEDED`が存在する場合はビルドを公開しない。システム/MPIライブラリはクロージャへ複製せず、ツールチェーン/プロビジョニングソースが管理する。
  ツールチェーンargvはrole別に`[resolved mpiicx,"--version"]`、`[resolved mpiicpx,"--version"]`、
  `[resolved mpirun,"--version"]`、`[resolved readelf,"--dynamic",<runtime_objects role="icoFoam"のbuild path>]`へ固定し、
  PATH探索後の曖昧なコマンド名や別ターゲットは許容しない。`compiler_identity`は先頭2つのroleに対する
  `{role,outcome,stdout_b64,stderr_b64}`順序付き配列、ビルド時`mpi_identity`は`mpirun_version`の同オブジェクトに対するJCSハッシュである。
- `experiment-metrics/native/mesh-facts/{mesh-facts.C,Make/files,Make/options}`をGit追跡ソースとし、ビルドワークフローは
  厳密に対象OpenFOAMビルドへリンクしてアーカイブの`bin/mesh-facts`へ収録する。プロビジョニング時は
  `<runtime>/provisions/<build-sidecar-sha256>/bin/mesh-facts`へ配置する。
- `experiment-metrics/native/partition-audit/{partition-audit.C,Make/files,Make/options}`をGit追跡ソースとし、同一のOpenFOAMへ
  リンクしてアーカイブの`bin/partition-audit`へ収録し、プロビジョニング先の同名パスへ配置する。3ファイルのパス順blob OIDを
  `partition_audit_source`で封印し、runtime objectのハッシュおよびビルド出力と照合する。
- `capture-hardware`のGit追跡ソースは
  `experiment-metrics/src/experiment_metrics/probes/capture_hardware.py`、インストール先エントリポイントは
  `<runtime>/provisions/<build-sidecar-sha256>/bin/capture-hardware`である。ビルドワークフローはOpenFOAMの`Allwmake`完了後に`icoFoam`、`blockMesh`、
  `decomposePar`、`checkMesh`、`mesh-facts`、`partition-audit`が起動可能であることを検証した後にアーカイブおよびsidecarを公開する。
- `control/build-provision-validation.json`は全フィールド必須、`additionalProperties=false`の
  `{schema_version:const "build-provision-validation/v1",build_sidecar_sha256:sha256,
  run_variant:enum "bench"|"profile",
  executables:[{role:enum "icoFoam"|"blockMesh"|"decomposePar"|"checkMesh"|"mesh-facts"|"partition-audit"|"capture-hardware"|"mpirun"|"perf",
  requested_path:string,resolved_realpath:string,size_bytes:uint,sha256:sha256}],
  ldd_raw:exactly 6 [{role:enum "icoFoam"|"blockMesh"|"decomposePar"|"checkMesh"|"mesh-facts"|"partition-audit",
  source:member}],launcher_version:{argv:exact [resolved mpirun realpath,"--version"],outcome:process-outcome,
  stdout:member,stderr:member},profiler_version?:{argv:exact [resolved perf realpath,"--version"],outcome:process-outcome,
  stdout:member,stderr:member},resolved_libmpi:{path:string,sha256:sha256}|null}`である。executablesは基本8 roleを記載順に過不足なく1件ずつ保持し、
  profile runのみ末尾に`perf`を過不足なく1件加える。
  profiler versionはprofile runで必須、他バリアントでは項目自体を欠落（absent）とする。
  validation JSONハッシュが6つのlddパース入力も間接的に封印する。バリデータは各resolved executableから実際に解決された
  推移的（transitive）なアーカイブ所有依存関係集合をbuild sidecarの`runtime_objects[kind="shared_library"]`へ相対パスで対応付け、
  6集合の和集合とsidecar集合を完全一致させ、プロビジョニング先のコンテンツハッシュも完全一致させる。
  アーカイブ/プロビジョニングのOpenFOAMビルドルート内へ解決された依存関係は、DT_NEEDED SONAMEとsidecar共有ライブラリの`soname`が
  過不足なく1対1で対応し、パスおよびハッシュも一致しなければならない。ルート外依存関係はldd rawに残し、libmpi以外を巨大なシステムSONAMEの
  allowlistで囲い込まない。ルート外であるにもかかわらずOpenFOAMプロビジョニングパスへシンボリックリンクで戻るようなターゲットは拒絶する。6つのroleのlddから得られた
  libmpiのパス/ハッシュは、非空集合が過不足なく1組のdistinctペアになることを要求し、その1組のペアのみを射影へ保持する。
  ポリシーIDはコントラクトハッシュから結合し、runレコードへ重複記録しない。
  照合結果の第2配列や真偽値フラグは保存せず、ldd rawとsidecarから導出する。
  全ステージはこの解決済み絶対パスを使用する。
- `build-provenance-projection/v1`は全フィールド必須の
  `{schema_version:const "build-provenance-projection/v1",precision:enum "SP"|"DP",label_bits:enum 32|64,compile_flags:string[],
  commits:[{repository_id:string,commit_role:enum "build_definition"|"openfoam_source"|"thirdparty_source",
  object_hash_algorithm:enum "sha1"|"sha256",oid:algorithm-constrained full OID},...],build_archive_sha256:sha256,
  toolchain_observations:[{role:enum "mpiicx_version"|"mpiicpx_version"|"mpirun_version"|"icofoam_dynamic",
  outcome:process-outcome,stdout_member:relative POSIX path,stdout_b64:base64,
  stderr_member:relative POSIX path,stderr_b64:base64},...],runtime_objects:[runtime object union above,...],
  source_member:relative POSIX path,source_sha256:sha256}`である。`source_sha256`がbuild-sidecar identityを兼ね、
  commitsはcommit_role順に過不足なく3件、toolchain observationは記載role順に過不足なく4件、runtime objectはパスのバイト順に一意で
  executable roleについて一意かつ過不足なく7件とする。セマンティックオブジェクトは射影からsource-memberパスのみを除外した
  role/outcome/stdout/stderrを使用する。`compiler_identity`と`mpi_identity`も対応するobservationの同一の閉じた射影をview側でハッシュ化する。
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
  source_member:relative POSIX path,source_sha256:sha256}`である。ビルド時の情報と実行時の情報を同一行に混在させない。
  executableは記載role順かつ一意で基本8 roleを過不足なく1件ずつ保持し、profile runのみ末尾に`perf`を過不足なく1件保持する。
  全MPIステージおよびハードウェアワンショット実行はこの検証済み絶対パスの`mpirun`を使用し、PATH探索は行わない。
  profiler versionオブジェクトはprofile runのみ全フィールド非nullとし、他バリアントでは全フィールドnullとする。
`runtime-mpi-semantic/v1`は射影からパス/memberロケータを除外した
`{schema_version:const "runtime-mpi-semantic/v1",mpirun_sha256:sha256,
launcher_version:{outcome:process-outcome,stdout_b64:base64,stderr_b64:base64},resolved_libmpi_sha256:sha256|null}`の
`SHA-256(JCS(object))`である。`mpi_execution_identity`はこのハッシュを表示し、スコア計測の必須一致性（must-match）および
適格性判定に用いる。開発時確認の一時出力へこのハッシュを永続化しない。
- `source/placement/rank-<rank>.json`は`schema_version:const "rank-placement/v1"/run_id/global_rank/local_rank/local_size/hostname/
  cpu_affinity/numa_mems`を保持する。global/local rankは非負整数、local sizeは正の整数、hostnameは空でない文字列、
  `cpu_affinity`は狭義単調増加する一意な符号なし整数配列、`numa_mems`はカーネルリスト文法の文字列またはnullとする。
  global rankの情報源候補は`PMI_RANK`、local rank/sizeは
  `MPI_LOCALRANKID/MPI_LOCALNRANKS`、affinityは`os.sched_getaffinity(0)`、NUMA情報は
  `/proc/self/status`の`Mems_allowed_list`、hostnameは`gethostname()`とする。
  宣言された各設定のcanaryテスト自体でこれらrank環境変数の存在と期待集合が確認できたrunのみを適合性評価の対象とし、
  欠損時における代替のrank情報源は持たない。
  リデューサはファイル名内のrankと`global_rank`、全ファイルのrun IDとsubjectマニフェスト、global rank集合と
  `0..requested_ranks-1`を完全一致させる。各レコードで`0 <= local_rank < local_size`であること、各hostname内で
  local sizeが同一値に一致し、local rank集合が`0..local_size-1`であることも要求する。完成した
  `parallel.rank_placement`配列はglobal rank昇順へ正規化する。

`multi-node-placement/v1`バリデータは新しいrawや原因フィールドを作成せず、プロトコルの個別実行設定、スケジューラ要求/アカウンティング、
`decomposeParDict.numberOfSubdomains`、`solver.runtime_header`、全`rank-placement/v1`、およびソルバー起動時の実効環境変数を
一度だけ照合する。requestのnodes/ranks/resource group/transport policyはプロトコルの各フィールドと完全一致し、
accountingの`nnumu`、runtime headerのdistinct Hosts数、placementのdistinct hostname数は`protocol.nodes`と一致し、辞書のsubdomain数、
headerの`nProcs`/Hosts rank総和、placement件数/global rank集合は`protocol.ranks`と一致しなければならない。各placement
hostnameは正確に`protocol.ranks/protocol.nodes`件を保持し、headerのhostname/rank数マルチセットとplacementから導出した同マルチセットを
完全一致させ、全レコードの`local_size`も同値とする。全rankの起動時実効環境変数において実際の`I_MPI_FABRICS`が
単一値であり、かつプロトコルのtransport policyと一致していること、`nodes > 1`かつ値が`shm`であればinvalidと判定する。配置側の必要な情報源が欠損していれば
バリデータは不成立、全情報源が揃ったうえで不一致があればinvalidとし、トポロジー用の真偽値列、原因列、検証成果物は設けない。
トランスポート情報源のみ同一規則によって既存の`transport_valid`へ投影する。これはbench/profileの双方に適用する。
bench runの`score_comparison_eligible`はバリデータ成立および`transport_valid=true`を直接要求する。
完全導出可能なトポロジー/affinity検証用真偽値フラグは設けない。
- `run.stage.<name>.launch`は`argv:string[]/cwd:string/stderr_mode:stdout|separate`のみを保持する。
  run所有のステージは`block_mesh|decompose_par|solver|check_mesh|mesh_facts|partition_audit|minimal_hardware_capture|profile_hardware_capture`であり、
  最後の2つは通常全バリアント/profile runのみに適用する。terminationは
  `{kind:"exit",code:int}`、`{kind:"signal",signal:int}`、`{kind:"spawn_error"}`の閉じたユニオンとする。
  StageRunnerは子プロセスのstdout/stderrを対応するstage/solverログにのみ書き出し、`tee`やechoによって`logs/pjm-job.log`へ重複記録しない。
  PJMログはスーパーバイザ/オーケストレーションメッセージのみを保持する。
- `perf.pipeline.wall_time_sec`はbench/profileのみにおいて`blockMesh`のspawn直前からソルバーのwait直後までを計測し、
  実行後のスキャン/ハッシュ計算/アーカイブ処理時間は含めない。`run.elapsed_sec`はPJMスクリプトエントリから計算ノード回収終了までを計測する。
- 全OpenFOAM実行可能ファイルの解決済みサブ引数には`-fileHandler uncollated`が過不足なく1回含まれる。メッシュ情報源は
  `mesh-facts -case <case> -fileHandler uncollated -constant`、完全ログは
  `LC_ALL=C checkMesh -case <case> -fileHandler uncollated -constant`で取得し、いずれもStageRunnerを経由して実行する。
- minimal hardwareの`source/hardware/node-<ordinal>.json`は`hardware-node/v1`形式であり、
  `schema_version:const "hardware-node/v1"/node_ordinal:uint/hostname:string`、`commands={lscpu:{argv:["lscpu","--json"],exit_code:int,stderr_member:relative POSIX path}}`、`lscpu_json:object|null`、および次の閉じた`platform_settings`を持つ。
  `platform_settings={kernel_release:string|null,online_cpus:uint[]|null,isolated_cpus:uint[]|null,nohz_full_cpus:uint[]|null,memory:{total_bytes:uint|null,hugepage_size_bytes:uint|null,hugepages_total:uint|null},numa_balancing_enabled:bool|null,boost:{source_path:string|null,raw:string|null,enabled:bool|null},cpufreq_policies:[{policy_id:uint,related_cpus:uint[],driver:string|null,governor:string|null,min_hz:uint|null,max_hz:uint|null},...]|null}`であり、全フィールド必須、`additionalProperties=false`である。
  `lscpu_json`は`LC_ALL=C lscpu --json`のパース済みrawオブジェクトであり、同一レコードへ派生CPU identityを重複記録しない。
  プローブのargvは`capture-hardware --mode minimal --subject-kind regular_run --subject-id <run-id> --output-root <absolute run>/source/hardware`を共通プレフィックスとし、1ノード構成では
  `--node-ordinal 0`、マルチノード構成では`--node-ordinal-from-env PMI_RANK`を末尾に付与する。プローブはsubjectマニフェストと
  出力ルートのrealpath包含関係を検証し、パスからIDを推測しない。
  `platform_settings`の情報源と正規化規則は以下に固定する。
  - kernel release: `/proc/sys/kernel/osrelease`のトリム後文字列。
  - CPU set: `/sys/devices/system/cpu/{online,isolated,nohz_full}`のカーネルリスト文法。空ファイルは空配列。
  - メモリ: `/proc/meminfo`の`MemTotal`および`Hugepagesize`はkB値を1024倍してバイト換算、`HugePages_Total`は符号なし整数。
  - NUMA balancing: `/proc/sys/kernel/numa_balancing`の`0|1`をブール値へ変換。
  - boost: `/sys/devices/system/cpu/cpufreq/boost`の`0|1`を優先し、存在しなければ`/sys/devices/system/cpu/intel_pstate/no_turbo`の`0|1`を反転。`{source_path,raw,enabled}`を保持。
  - cpufreq: 数値ポリシーID順に`/sys/devices/system/cpu/cpufreq/policy*`を読み取り、`related_cpus`、`scaling_driver`、`scaling_governor`、`scaling_min_freq`、`scaling_max_freq`を使用。周波数はkHzを1000倍してHz換算。`related_cpus`はASCII空白区切りの符号なし整数を狭義単調増加する一意な配列へ変換。
  CPUリストファイルが存在して空であれば`[]`、インターフェースが存在しないか読み取り不能であればnullとする。cpufreqルートが存在してポリシーが0件であれば`[]`、ルートが存在しないか列挙不能であればnullとする。profile側へ同一の値を再収録しない。`nohz_full`のみ空白トリム後のリテラル`(null)`も`[]`へ正規化する。

`minimal-hardware-projection/v1`は全フィールド必須の
`{schema_version:const "minimal-hardware-projection/v1",subject_kind:const "regular_run",subject_id:string,node_ordinal:uint,
hostname:string,cpu_identity:{architecture,model_name,vendor_id,cpu_family,model,stepping:string|null,
physical_cores:uint|null,numa_nodes:uint|null},platform_settings:<hardware-node/v1のclosed settings>,
source_member:relative POSIX path,source_sha256:sha256}`である。CPU identityは`lscpu_json.field`からASCII末尾コロンを
過不足なく1つ除去したラベル `Architecture/Model name/Vendor ID/CPU family/Model/Stepping/Socket(s)/Core(s) per socket/NUMA node(s)` を用いてパースし、
`physical_cores=Socket(s)*Core(s) per socket`、必要なラベルが欠落している場合はnullとする。

`source/workload-manifest.json`は各runの実際のケースから作成する、全フィールド必須、
`additionalProperties=false`の閉じた
`workload-manifest/v1={schema_version:const "workload-manifest/v1",
members:exactly 7 [{path:one of exact paths,size_bytes:uint,sha256:sha256}]}`のみを保持する。パスのバイト順による厳密な7ファイルパスは`0/U`、`0/p`、
`constant/transportProperties`、`system/controlDict`、`system/fvSchemes`、`system/fvSolution`、
`system/blockMeshDict`である。ワークロードidentityはmembers配列のJCS SHA-256であり、Factへ複写せずマニフェスト射影が管理する。
各ファイルは同一バイト列を`source/workload/<path>`へコピーする。publisherの行スキーマは次の閉じたオブジェクトである。

```text
workload-manifest-projection/v1 = {schema_version:const "workload-manifest-projection/v1", subject_kind:const "regular_run",
  subject_id:string, workload_identity:sha256, source_member:relative POSIX path, source_sha256:sha256}
workload-member-projection/v1 = {schema_version:const "workload-member-projection/v1", subject_kind:const "regular_run",
  subject_id:string, path:one of the exact 7 paths,
  content_b64:base64}
```

member行は親マニフェスト射影を`subject_kind/subject_id`で結合し、マニフェストidentity、ソースmember/ハッシュ、
コンテンツから完全に導出可能なサイズ/ハッシュを各行へ再掲しない。publisherはデコードしたバイト列のサイズ/ハッシュをソースマニフェスト
memberと照合し、consumer viewが必要に応じて同一の算定式で導出する。
consumerの`workload_id`はプロトコルの次元、`workload_manifest_identity`は競合のないマニフェスト射影、
`workload_match`は両者が存在する場合にのみ`expected_workload_identity = workload_identity`を評価して返し、片側の欠損または競合時はNULLとする。

profile hardwareの`capture.json`は全フィールド必須、`additionalProperties=false`の閉じた
`profile-hardware-capture/v1={schema_version:const "profile-hardware-capture/v1",run_id:run ID,node_ordinal:uint,hostname:nonempty string,
members:[{role:enum "proc_meminfo"|"numa_cpulist"|"numa_meminfo",numa_node_id:uint|null,
path:relative POSIX path,size_bytes:uint,sha256:sha256}]}`である。
membersはrole/node/path順に一意とし、proc_meminfoはnode IDがnullで過不足なく1件、NUMAの2つのroleは検出されたノードごとに同一IDを1件ずつ保持する。
読み取り元はrole/node IDから`/proc/meminfo`、`/sys/devices/system/node/node<id>/cpulist`、同`meminfo`へ一意に導出し、
同一の`source_path`をレコードへ重複記録しない。外部のワンショット実行のargvおよび成否はStageRunnerの`profile_hardware_capture`ステージが一度管理する。
publisherは閉じたタグ付きレコードを
`openfoam_profile_hardware_raw_v2`へ転記する。行は全フィールド必須、`additionalProperties=false`の
`profile-hardware-projection/v1={schema_version:const "profile-hardware-projection/v1",run_id,node_ordinal:uint,hostname:nonempty string,record_kind:enum
"node_summary"|"numa_node",numa_node_id:uint|null,postrun_mem_available_bytes:uint|null,
cpulist:string|null,mem_total_bytes:uint|null,mem_free_bytes:uint|null,
source_members:[{role:enum "capture"|"proc_meminfo"|"numa_cpulist"|"numa_meminfo",
path:relative POSIX path,sha256:sha256},...]}`である。全行に過不足なく1件の`capture`を保持させ、node summaryではNUMAフィールドを、
NUMA行ではpostrunフィールドをnullとし、NUMA行の`source_members`はcapture/cpulist/meminfoを別エントリとして保持する。
captureは`gethostname()`を記録し、同一runのminimal hardwareとノード序数集合・ホスト名集合および各
`(node_ordinal, hostname)`を完全一致させる。`/proc/meminfo`はASCII形式の`Key: uint kB`のうち`MemAvailable`を、NUMAの
`node<id>/meminfo`は`^Node <id> (MemTotal|MemFree):[ \t]+([0-9]+)[ \t]+kB$`を各過不足なく1回要求し、
別ノードIDのプレフィックスを拒絶してkB値を1024倍してバイト換算する。重複キー、非整数、
オーバーフロー、単位不一致が検出された場合、そのキャプチャは公開しない。`cpulist`はASCII空白をトリムしてカーネルリスト文法をパースし、
狭義単調増加する一意なCPU集合を最小範囲表記へ正規化する。空ファイルは空文字列、読み取り不能時は該当値をnullとする。
`profile_hardware/v1`リデューサはこのテーブルからconsumerへ投影する。
同一内容の複合rawフラグメントは作成しない。
profile post-runのプレフィックスは`capture-hardware --mode profile-postrun --subject-kind regular_run --subject-id <run-id>
--output-root <absolute run>/profile/raw/hardware --node-ordinal-from-env PMI_RANK`に固定する。

profile canaryテストにおいて、プロビジョニング検証の`perf --version`とrankラッパーが各ソルバーrankで起動する次の正確な子argvを固定する。
`<resolved-perf> stat --no-big-num -x, -o <profile>/perf/rank-<global-rank>.csv -e cycles,instructions,branches,branch-misses,cache-misses -- <resolved-icoFoam> <solver-subargv...>`。
profileバンドルのハッシュ済み実行可能コンポーネントがMPIのrank実行可能ファイルとなり、argvテンプレートは
`<component_executable> --run-id <subject_run_id> --expected-ranks <expected_global_ranks> --output <rank_sink_template> --perf <provisioned_executable role="perf"> --solver <stage_executable role="icoFoam"> -- <solver-subargv...>`に固定する。
ラッパーは`PMI_RANK`からrank別のsinkを一度レンダリングし、シェルを介さずに上記子argvをspawnする。ランチャー側で単一CSVを収集する形式はとらず、
マルチノード構成であっても各rankのプロセスクリーのみを計測する。ラッパーまたは子プロセスの失敗時に、perfなしでソルバーを再実行してはならない。
`perf-csv/v1`は7列形式の`count_lexeme,unit,event_name,running_ns_lexeme,percent_running_lexeme,metric_value_lexeme,metric_unit`に固定する。各rankの情報源は閉じた
`perf-stat/v1={schema_version:const "perf-stat/v1",run_id:run ID,global_rank:uint,items:exactly 5 [item,...]}`であり、itemは
`event_name:enum "cycles"|"instructions"|"branches"|"branch-misses"|"cache-misses"/raw_count_lexeme:string/count:decimal|null/unit:string|null/running_ns:decimal|null/percent_running:decimal|null`である。
`enabled_ns = running_ns / (percent_running / 100)`はconsumer変換でのみ導出され、パーセンテージが0またはnullの場合はnullとする。
raw itemへ重複記録しない。itemsは上記enumの記載順に各イベント過不足なく1回ずつ現れ、CSVも同一のファイル内順序を要求する。
未サポートまたは未カウントのイベントであっても行自体は必須とし、そのカウントのみ`null`とする。他の数値フィールドは各字句が数値であれば保持する。
マルチプレックスされたレコードも`count/running_ns/percent_running`を保持する。step/pressure/perfの行序数は、順序付き配列のオフセットからpublisherが
射影時に一度導出し、itemへ重複記録しない。
`runner.perf_parser`がターミナル終了後かつアーカイブ前に、profile runのみにおいて期待される全グローバルrankのCSVを読み取り、source memberが
`profile/raw/perf/rank-<global_rank>.csv`であり、レコードのrun IDが包含マニフェストと一致し、rank集合が`0..expected_ranks-1`と完全一致することを検証して、
`profile.perf_stat.rank.<rank>`フラグメントをrankごとに1回出力する。欠落したrankはNULLとし、フリート全体の値を一部のrankから外挿してはならない。

Pstreamフックは`OPENFOAM_METRICS_PSTREAM_DIR=<absolute runtime>/runs/<run-id>/domain/pstream`をsinkバインディング、
`OPENFOAM_METRICS_RUN_ID=<validated run ID>`をidentityバインディングとする。スーパーバイザは`mpirun`の実行前にこのディレクトリを
1度作成し、パスコンポーネントとidentityバインディングがrunマニフェストのrun IDと一致することを検証する。フックは絶対パス
ディレクトリ文字列からrun IDを推測してはならない。
scoreおよびprofileバンドルはこのフックコンポーネントを持つ場合、環境変数バインディングを名前のバイト順に過不足なく
`OPENFOAM_METRICS_PSTREAM_DIR={absolute_sink_path:<pstream sink ID>}`、
`OPENFOAM_METRICS_RUN_ID={subject_run_id}`の2件保持する。ランナーやフック内でのコンポーネントIDのハードコードによる補完は行わない。
`UPstream::myProcNo()`の確定後に各rankが`rank-<rank>.jsonl`をオープンし、上記エンベロープを行バッファリングで追記する。
正常終了時にflush/closeする。書き込み失敗を理由にソルバー計算を停止させてはならず、そのrunの`collection_complete`がfalseになるのみで、
フォールバック先や再送キューは作成しない。

profile runの完全なハードウェアrawデータはノード序数ごとに
`profile/raw/hardware/node-<ordinal>/{proc-meminfo.txt,numa/node-<id>-cpulist.txt,numa/node-<id>-meminfo.txt,capture.json}`に固定する。`capture-hardware`は公開CLIコマンドではなく、
`collect`から呼び出される内部プローブである。minimal hardwareのrawノードレコードのみを正本とし、ノード序数順の
CPU識別文字列配列をconsumerへ投影する。コンセンサスはview側の派生項目とし、rawへは保存しない。

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
Collective通信ベンチマークではmin/avg/maxをそれぞれの列に格納する。存在しない列はNULL、AllreduceのbandwidthはNULLとし、値の再計算は行わない。

プロジェクション名は`mpi_network_results_v2`、グレインは`(run_id, benchmark, process_count, message_bytes)`、行スキーマは`mpi-network-result/v2`である。
source instance grainは`run_id + source/network/imb-mpi1/stdout.txt`とし、instance identityにはartifact manifestが保持する当該メンバーのSHA-256ハッシュを用いる。各行へハッシュ値を重複して記録してはならない。

## artifact projection registry v1

アーティファクトをBigQueryへ転記するエントリは`[[artifact_projection]]`の形式で定義を閉じ、標準フィールド（canonical fields）は以下のみに限定する。

```text
id, base_table_id, relation_id, conflict_relation_id,
source_artifact_id, source_schema_id, row_schema_id, row_grain,
subject_scopes, publisher_id, transform_id,
conflict_rule, source_member_field?, source_sha256_field?,
source_instance_grain?, source_instance_sha256_field?, parent_projection_id?, parent_join_columns?,
duplication_justification
```

`subject_scopes`はタグ付き配列であり、run ownerの場合は`{owner_scope="run", applicable_run_variants=[...]}`、build ownerの場合は`{owner_scope="build"}`とする。publisherは1つのソースインスタンスを1回のBigQueryロードジョブによって物理ベーステーブル（physical base table）へ追記（append）する。論理リレーション（logical relation）では、全列が完全一致する重複行を1件へと集約（deduplicate）する。
`source_instance_grain`が同一であるにもかかわらずインスタンスハッシュが異なる場合は当該インスタンスの全行を、また同一のrow grainでペイロードが異なる場合はその全行をコンフリクトリレーション（conflict relation）へと隔離し、コンシューマの参照対象から除外する。direct lineageを表す2フィールド、または`parent_projection_id`と明示的な`parent_join_columns`のペアのいずれか一方のみを必須とする。v1エントリは以下のとおりである。

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

直接エントリ（direct entry）のsource-instance grainは、source trackでは`run + subject manifest member`、build provenanceでは`source_sha256`、build provisionでは`run + validation member`、minimal hardwareでは`run/node + node member`、workload manifestでは`run + manifest member`、profile hardwareでは`run/node + capture member`とする。対応するインスタンスハッシュはそれぞれ、subject manifest SHA-256、build-sidecar SHA-256、validation source SHA-256、node source SHA-256、workload manifest source SHA-256、capture SHA-256に固定する。
workload memberはコンフリクトフリーなmanifest親レコードへと結合するため、direct source-instanceフィールドを持たない。
以下に示す上書き（override）を除き、direct entryは`source_member_field=source_member`および`source_sha256_field=source_instance_sha256_field=source_sha256`に固定する。
profile hardwareエントリは、`source_member_field=source_members[role="capture"].path`および`source_sha256_field=source_instance_sha256_field=source_members[role="capture"].sha256`という一意なセレクタに固定する。

## producer/source registry v1

規約における`[[producer]]`は、共通フィールドである`id:nonempty unique string`、`activation`、`instances`に対し、以下の閉じた所有関係の直和型（closed ownership union）を追加する。

```text
{owner_scope:const "run", applicable_run_variants:nonempty unique variant[]}
```

run ownerの`activation`は`{kind:"always"}`または`{kind:"bundle_component", component_id:nonempty string}`のいずれかであり、後者のコンポーネントIDは適用対象となる各バリアントが選択するバンドル内に厳密に1つだけ存在する。`instances`は`{kind:"singleton"}`または`{kind:"cartesian", axes:nonempty sorted unique subset of ["node_ordinal", "global_rank", "stage_name", "invocation_id"]}`とする。
軸（axes）の期待値集合は、プロトコルの個別実行設定、プロトコルスケジュール、および規約で定義されたステージ集合のみから導出する。

`path-template`は空でないセグメント配列であり、各セグメントは`{literal:nonempty string}`または`{token:enum "node_ordinal"|"global_rank"|"stage_name"|"invocation_id"}`の閉じた直和型とする。隣接するリテラルは1つに結合し、展開（レンダリング）後は相対POSIXパスとして評価する。テンプレート内のトークンには、プロデューサーが持つ軸の真部分集合または部分集合のみを使用する。

`[[source]]`は全フィールドが必須（required）の定義であり、以下の構造を持つ。

```text
{
  id: nonempty unique string,
  producer_id: existing producer ID,
  source_role: nonempty contract role,
  storage: enum "fact_fragment"|"run_bundle"|"profile_raw",
  path_template: path-template,
  schema_id: nonempty schema ID,
  required_when_applicable: bool
}
```

同一ストレージ内において、展開後のパスはグローバルに一意でなければならない。
プロデューサーごとの`storage="fact_fragment"`ソースは0件または1件とし、そのソースの`path_template`のみをライターおよびファイナライザーの正本として扱う。プロデューサー側へ同一テンプレートを重複して定義してはならない。各`[[fact]].source_id`は厳密に1つのソースに解決され、`member-with-role.role`は厳密に1つのレジストリロールに解決される。
ファイナライザーはバリアントおよびバンドルからプロデューサーを選定し、インスタンスを1度だけ展開してソースパス集合および必須フラグメント集合を取得する。これとは別にコード側で期待値テーブルを保持したり、フォールバック探索を行ったり、マニフェストへ期待値集合を複製したりすることは禁止する。

## fact registry v1

各`[[fact]]`は以下のフィールドをすべて保持する。

```text
id, key_pattern, source_id, schema_id, logical_type, unit, cardinality,
capture_id, validator_id, reducer_id, duplication_justification?
```

ソース情報からプロデューサー、owner scope、適用対象バリアント、必須性を一意に結合（join）し、ファクト定義側へ冗長に複製してはならない。
`(source.schema_id, fact.schema_id, validator_id, reducer_id)`の組み合わせは、規約に定義された閉じたリデューサーシグネチャカタログ（closed reducer signature catalog）内に厳密に1つだけ存在しなければならず、同一バリアントで有効なファクトキーパターン同士を重複（overlap）させてはならない。

自由形式の文字列によるsource/reducer/validationの記述は許可しない。v1ファミリーにおけるルーティング規則は以下によって完結する。

| key pattern/family | owner/source | validator/reducer | schema/type |
|---|---|---|---|
| `run.identity.*` | `runner.manifest` / subject manifest | `identity/v1` / `identity_projection/v1` | scalar run identity |
| `run.started_at|finished_at|elapsed_sec|exit_code` | `pjm.supervisor` / clocks+exit | `run_lifecycle/v1` / `identity/v1` | timestamp/seconds/int。`run_outcome`はexit code 0/非0からビューとして導出 |
| `run.stage.<name>.launch|termination`, `perf.stage.<name>.wall_time_sec` | `StageRunner` / spawn+wait | `stage_record/v1` / `identity/v1` | 上記スキーマ/有限秒 |
| `perf.pipeline.wall_time_sec` | `pjm.supervisor` / monotonic boundaries | `finite_seconds/v1` / `identity/v1` | 有限秒（regular bench/profileのみ） |
| `collection_complete` | `finalizer` / in-memory expected-vs-observed set | `bool/v1` / `identity/v1` | bool |
| `artifact.build_manifest_sha256|instrumentation_bundle_sha256` | runner/package manifests | `artifact_index/v1` / `artifact_projection/v1` | SHA-256 |
| `scheduler.request` | `runner.submission` / submission request | `scheduler_request/v1` / `identity/v1` | `scheduler-request/v1` JSON |
| `scheduler.accounting` | `runner.postrun` / pjstat raw | `scheduler_accounting/v1` / `pjstat/v1` | `scheduler-accounting/v1` JSON |
| `scheduler.submit_job_id|scheduler.job_entry_job_id` | finalizer / submission result + job-entry | `job_id/v1` / `identity/v1` | ソース固有文字列（欠損時はキー自体を非保持） |
| `env.*` | supervisor / host-exec snapshot | `environment_snapshot/v1` / `environment/v1` | UTF-8 plain string |
| `parallel.rank_placement` | rank wrapper / rank placement sources | `rank_placement/v1` / `rank_placement/v1` | ordered JSON array |
| `mesh.topology` | postrun auditor / mesh probe | `mesh_topology/v1` / `identity/v1` | `mesh-topology/v1` JSON |
| `mesh.partition.requested|observed` | supervisor/auditor / dict+mesh files | respective schema validator/reducer | 上記スキーマ |
| `solver.runtime_header` | log parser / solver log | `openfoam_header/v1` / 同一 | JSON |
| `solver.pstream.*` | Pstream parser / rank JSONL | `pstream_rank/v1` / 同一 | 上記スキーマ |
| `solver.step_timings|pressure_solves|log_markers` | log parser / solver log | respective schema validator/reducer | 上記スキーマ |
| `profile.perf_stat.rank.<rank>` | `runner.perf_parser` / 終了後のランク別プロファイルCSV | `perf_stat/v1` / `perf_stat/v1` | ランク別の厳密に5つの順序付きイベントレコード -> 論理テーブル`openfoam_perf_counters_v2`。perfのバージョンはbuild-provisionソースのみが保持 |
| `network.imb_mpi1.*`, `software.imb_mpi1.version` | network capture / validated argv+IMB output | `imb_config/v1` / `identity_projection/v1` | 独立したスカラーFact |
| `run.stage.network_imb_mpi1.termination`, `perf.stage.network_imb_mpi1.wall_time_sec` | `StageRunner` / spawn+wait | `stage_record/v1` / `identity/v1` | 通信測定の失敗はソルバーの終了状態（termination）を変更しない |

`openfoam_rank_placements_v2`は、`parallel.rank_placement`の順序付き配列を`(run, global_rank)`へと1度だけUNNEST展開し、ホスト名、ローカルランク/サイズ、CPUアフィニティ、NUMAメモリノードを情報欠落なく（lossless）提示する。これはコンシューマ向けビュー（consumer view）であり、新たなFactやアーティファクトプロジェクションを生成するものではない。コンフリクトフリーなFactが実在する場合にのみ`CROSS JOIN UNNEST`を行い、ソースの欠損時、非適用時、コンフリクト発生時は0行を返す。期待されるランク構造へのLEFT JOINやプレースホルダー行の生成は行わない。

計画書に記載されたコンシューマ列（consumer columns）は、以下のリデューサーIDのみを使用できる。

- identity: `identity_projection/v1`
- source/artifact: `artifact_projection/v1`
- quality: `completeness/v1` または `official_openfoam/v1`
- hardware/config consensus: `consensus/v1`
- solver/performance: `official_openfoam/v1`
- profile counter: `perf_counter_projection/v1`
- environment: `environment_decode/v1`
- Data Status: `archive_attempt_status/v1`

コンシューマ列のエントリ定義は、`name/type/unit/source_refs/scope_cardinality/reducer_id/conflict_rule/transform_id/applicable_run_variants/dimension_name/allowed_classes`によって完結する。`source_refs`は順序付きの`[{kind="fact"|"projection"|"dimension", id, json_path?, bindings?}, ...]`であり、異種ソースの混在とリデューサーへの入力順序を明示する。
`dimension`は実行の計画時/観測時ディメンションを参照し、`projection`はコンフリクトフリーな論理リレーションをクエリする。
アーカイブメンバーを直接読み出す`artifact`参照は許可せず、データリネージはプロジェクションのソースメンバーおよびハッシュ値からのみ追跡する。
プロジェクション参照の`bindings`は空でない`[{applicable_run_variants, consumer_field, projection_field, projection_subject_kind}]`であり、バリアント集合全体を重複なく網羅する。
runをキーとするプロジェクションは`run_id -> run_id`、通常のサブジェクトをキーとするプロジェクションは`run_id -> subject_id, regular_run`、ビルドプロジェクションはFactの`artifact.build_manifest_sha256 -> source_sha256, build`を明記し、SQL生成系に暗黙の結合条件を残さない。
dimension参照の`bindings`は順序付きかつ空でない`[{consumer_field, dimension_field}, ...]`である。
`workload_id`および`expected_workload_identity`は実行マニフェストの計画時ディメンションから取得し、実際のワークロードプロジェクションと比較検証する。
計画書に記載された列のうち、このエントリ定義を持たない列は生成しない。

## NULLと不完全run

取得できなかった固定幅コンシューマ値、および当該バリアントにおいて非適用の値は、いずれも`NULL`のみを返す。source-grainの縦長リレーション（long relation）は実在するソース行のみを提示し、欠損行や非適用行、フィールド別の理由コード（reason code）、missingステータス、プレースホルダー行などは生成しない。実行レベル（run-level）では、期待されるソースファイルとプロデューサー出力がすべて揃ったかを表すフラグ`collection_complete`のみを保持し、これが`false`であっても詳細な原因分類は要求しない。これは、稀に発生する採取失敗を過剰な耐久処理で救済するための規約ではなく、正常実行パスにおいて取得対象が当初から実装漏れとなる事態を厳格に防止するための規約である。

## package ownership

パッケージの所有関係および構成物は以下のとおり整理する。

- `run-artifacts.tar.zst`: control、source、domain、log、resultの各ディレクトリ、およびtarアーカイブ直下の`bundle.manifest.json`
- `metrics.jsonl`: マージ済みの生メトリクス行（raw rows）のみ
- `profile-raw.tar.zst`: profileプロトコルにおいて該当するperfの生データおよびハードウェアの生データのみ
- `artifact-manifest.json`: 上記の外部ファイル群の識別情報（identity）のみ
- ワークフロー運用行（workflow operational row）: GitHub Artifact ID、配置先（home destination）、アップロード/SCP/パブリッシュの結果状態のみ

ランタイム処理では、バンドルマニフェストを`archive-staging/bundle.manifest.json`として生成し、tarアーカイブ内ではベース名`bundle.manifest.json`として格納する。GitHub Artifactに含める基本ファイルは、`run-artifacts.tar.zst`、`metrics.jsonl`、`artifact-manifest.json`である。バンドルURIは、生メトリクスからではなくワークフロー運用行から結合する。
同一の実バイト列を2つのtarアーカイブへ重複して格納してはならない。benchプロトコルでは、profile用tarアーカイブや欠損補填用のレコードを作成しない。
マージに成功したプロデューサーフラグメントは`metrics.jsonl`の完全な部分集合となるため、個別アーティファクトとしては保存せず、ランタイムの一時ファイルは削除する。マージ前の部分ファイルや一時ファイル（partial/tmp）は障害調査のために作業領域に残存する場合があるが、publisherへのFact入力として用いてはならない。

プロファイル機能の初版では、ハッシュ検証済みのランク別ラッパーによる`perf stat`モードのみを対象とする。実装時には、当該スクリプトの厳密な引数（exact argv）、プロビジョニング検証時の`perf --version`、およびイベントリストを規約として固定し、ランク別の出力CSVを`event_name/raw_count_lexeme/count/unit/running_ns/percent_running`の順序付きレコードへと集約（reduce）する。
unsupportedまたはnot-countedとなったカウント値のみをnullとし、個別の非数値フィールドのみをnullとして扱い、時分割多重化（multiplexed）された数値データを破棄してはならない。
宣言された各設定において、プロファイルの予備検証（canary）を実施する前に厳密なargvおよびイベントリストを確定できない場合は、その設定におけるプロファイル計測を開始してはならない。
