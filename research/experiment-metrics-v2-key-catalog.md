# OpenFOAM experiment metrics v2 キーカタログ

## 現行コントラクト仕様

本ドキュメントは、2026年8月12日以降に確定した実装仕様の正本である。Google BigQueryは以下の3列のみで構成される単一のテーブルを使用する。

```sql
openfoam_metrics(run STRING, key STRING, value STRING)
```

各プロデューサー（計測処理）は、診断用メトリクスフラグメント（断片ファイル）をアトミックなリネーム操作（rename）によって確定する。ジョブスケジューラ上の計算ジョブが完了状態へ移行した後、ログインノード上で動作するGitHub Actionsランナーが確定済みフラグメントを回収し、BigQueryへ一度だけ追記送信する。
なお、中央集約的なマージ処理、ファイナライズ処理、物理スキーマへの射影（projection）、ユーザー向けコンシューマビュー、競合解消テーブル、単一の `metrics.jsonl` 生成、および自動再送制御は設けていない。

ソース追跡（source track）キーは `source.track.head_commit`（本リポジトリのGitコミットSHAハッシュ）のみとする。プッシュ実行時は `[profile]` タグ、手動実行（workflow_dispatch）時は `profile` 入力パラメータにより通常ベンチマーク（bench）とプロファイル計測（profile）を切り替える。プロファイル計測の諸条件は `benchmark/profile.json` を通じてGitコミット履歴上で追跡する。なお、通常ベンチマーク実行においてランク別の環境変数差分は収集しない。

## BigQueryへ送信するメトリクスキー一覧

パターン表記中の `*` は、実際のノード番号、ランク番号、ステージ名、ワークロード構成要素、またはIMB測定識別子へ置換される。JSON形式の構造化データも、BigQuery上ではRFC 8785準拠の正規化JSON（canonical JSON）文字列として `value` 列に格納される。

| キーパターン | 格納する値・用途 | プロデューサー（取得元） |
|---|---|---|
| `run.identity.{run_id,run_purpose,repository_id}` | 実行の一意識別情報 | ランナー（`runner.manifest`） |
| `run.instrumentation_bundle_sha256` | 計装バンドルのSHA-256識別子 | ランナー（`runner.manifest`） |
| `source.track.head_commit` | 実際にチェックアウトされたGitコミットSHAハッシュ | ランナー（`runner.manifest`） |
| `artifact.build_manifest_sha256` | ビルドマニフェストのSHA-256識別子 | ビルド来歴パーサー |
| `build.provenance` | OpenFOAM/ThirdPartyのコミット、コンパイラ/MPI構成、ビルド成果物識別情報 | 計算ノード側のビルド情報パーサー |
| `build.provision` | 実行バイナリ、MPIランチャー/ライブラリ、プロビジョニング照合結果 | 計算ノード側のプロビジョニング検証パーサー |
| `workload.manifest` | ワークロードID、公式ケースのコミット、固定入力辞書およびメッシュの識別情報 | 計算ノード側のワークロード抽出処理 |
| `scheduler.request` | 要求ノード数、ランク数、リソースグループ、通信ポリシー、投入引数列/スクリプト識別情報 | ランナー（ジョブ投入処理） |
| `scheduler.{submit_job_id,job_entry_job_id}` | ジョブスケジューラのジョブID | ランナー / 計算ノードジョブ初期化処理 |
| `scheduler.accounting` | 終了ステータス、経過時間、終了コード、割当ノード数、全体メモリ/CPU会計値およびノード別使用量配列 | ランナー（ジョブ完了後処理） |
| `run.{started_at,finished_at,elapsed_sec,exit_code}` | PJMジョブ全体のライフサイクル計測値 | 計算ノード側のパイプライン監視処理 |
| `run.stage.<stage>.{launch,termination}` | 各ステージの厳密な引数列（argv）、作業ディレクトリ（cwd）、終了コード/シグナル情報 | 計算ノード側の `StageRunner` |
| `perf.stage.<stage>.wall_time_sec` | ステージ外部から計測した経過時間（wall-clock time） | 計算ノード側の `StageRunner` |
| `perf.pipeline.wall_time_sec` | ソルバーを含む主要パイプライン全体の経過時間（wall-clock time） | 計算ノード側のパイプライン監視処理 |
| `env.*` | MPI起動直前の共通ホスト環境変数（認証情報を除外済み） | 計算ノード側の環境変数パーサー |
| `parallel.rank_placement` | 全ランクのグローバルランク、ローカルランク、ホスト名、CPUアフィニティ、NUMAアフィニティを集約した単一JSON | 計算ノード側のプロセス配置パーサー |
| `hardware.minimal.node.<ordinal>` | 各ノードのCPU諸元、カーネル、メモリ、NUMA/ブースト/cpufreq設定 | 計算ノード側のハードウェア情報パーサー |
| `mesh.topology` | メッシュトポロジー情報（後述の `mesh-topology/v2` 形式） | 計算ノード側の保存ログパーサー |
| `mesh.partition.requested` | 使用した辞書ファイルのSHA-256、サブドメイン数、分割手法 | 計算ノード側の保存ログパーサー |
| `mesh.partition.observed` | 実際に観測された領域分割情報（後述の `partition-observed/v2` 形式） | 計算ノード側の保存ログパーサー |
| `solver.runtime_header` | ソルバー起動ヘッダー（Build, Arch, Exec, fileHandler, nProcs, Hosts） | ランナー側の保存ログパーサー |
| `solver.step_timings` | 各反復ステップの計算時刻（Time）、ExecutionTime、ClockTimeの順序付き配列 | ランナー側の保存ログパーサー |
| `solver.pressure_solves` | 圧力方程式（Solving for p）の残差および反復回数の順序付き配列 | ランナー側の保存ログパーサー |
| `solver.log_markers` | 正常終了マーカー（End）、異常数値行数（bad-number）、セル数マーカー | ランナー側の保存ログパーサー |
| `result.official` | 公式判定の有効性（validity）、2ステップ目以降の平均秒/step、標準偏差、反復回数、公式判定テキスト | ランナー側の公式結果パーサー |
| `result.aero_sanity` | 最終ステップ、抗力係数（$C_d$）、既報参考値、取得元ファイル情報（独自の合否閾値なし） | ランナー側の係数パーサー |
| `solver.pstream.{startup_applied,runtime_current,change_events}` | 全ランクでの一致が検証された共通Pstream通信設定値 | ランナー側のPstreamリデューサー |
| `solver.pstream.rank_exceptions` | 共通設定値との差分が実際に発生したランクの情報（通常は出力なし） | ランナー側のPstreamリデューサー |
| `network.imb_mpi1.{process_count,message_size.*,iteration.*}` | Intel MPI Benchmarks（IMB-MPI1）の実行パラメータ設定 | 計算ノード側のIMBパーサー |
| `software.imb_mpi1.version` | IMB-MPI1のバージョン識別情報 | 計算ノード側のIMBパーサー |
| `network.imb_mpi1.result.<benchmark>.<message_bytes>` | PingPong、Sendrecv、Allreduceの各メッセージ長における実測レコード | 計算ノード側のIMBパーサー |
| `profile.vtune_hotspots` | プロファイル専用: VTune設定、計測対象ランク、バージョン、ソース識別子、関数別ホットスポット一覧 | 計算ノード側のVTuneパーサー |
| `profile.hardware.node.<ordinal>` | プロファイル専用: 計算終了後のメモリ詳細およびNUMAトポロジー詳細 | 計算ノード側のプロファイルハードウェアパーサー |

通常ベンチマーク実行におけるステージ集合は、`case_prepare`、`renumber_mesh`、`potential_foam`、`apply_boundary_layer`、`rank_placement`、`solver`、`minimal_hardware_capture`、`network_imb_mpi1` である。
プロファイル計測実行では、独立した `rank_placement` の代わりにソルバーのラッパー内で配置情報を記録し、追加で `profile_warmup` および `profile_hardware_capture` を実行する。
なお、IMBネットワークベンチマークおよびプロファイル用ハードウェア情報の収集はソルバー完了後の独立ステージであり、公式のソルバー性能評価時間には混入させない。

## 構成および性能比較情報の具体的データ構造

旧設計のプロジェクションから移行した主要な構造化情報は、以下の生JSON形式で保持される。データベース側での複雑なビュー変換には依存しない。

### `mesh.topology`

```json
{"schema_version":"mesh-topology/v2","cells":64000000,"faces":192480000,"points":64481201,"internal_faces":191520000}
```

※上記のセル数等の数値は旧課題における例示フォーマットである。現行の実行においては、前処理段階で保存された `checkMesh.log` から値を抽出する。メッシュファイル群を再オープンして走査することはない。

### `mesh.partition.requested`

```json
{"schema_version":"partition-requested/v2","source_sha256":"...","subdomains":120,"method":"scotch"}
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

全ランク分の情報を保持する目的は、領域分割の不均衡度（imbalance）およびプロセス間通信の境界面積を事後的に正しく評価するためである。
情報の取得元は、前処理時に生成・保存された小さなテキストファイル `decomposePar.log` のみであり、各プロセッサディレクトリ配下のメッシュデータを再走査することはない。全ランクのセル数合計、ランク番号集合、および境界面の双方向整合性はパーサーにより検証される。

### `hardware.minimal.node.<ordinal>` と `parallel.rank_placement`

ハードウェア構成情報は、ランク単位ではなくノード単位で1度だけ収集する。ランク単位で個別に必要な情報はプロセス配置およびアフィニティ（affinity）のみであるため、これらを `parallel.rank_placement` という単一のJSONに集約している。これにより、ノード構成、CPU設定、およびランク配置を過不足なく比較可能とし、同一ノード内で完全に重複する環境情報の多重収集を排除している。

### `build.provenance`、`build.provision`、`workload.manifest`

コンパイラ、MPI、ビルド識別情報、実行バイナリの識別情報、OpenFOAMおよびThirdPartyのコミットハッシュ、ならびに厳密なワークロード識別ハッシュを保持する。これらはソース追跡側とは重複させず、本リポジトリ自身の識別としては `source.track.head_commit` のみを記録する。

## 明示的に収集しない項目

- `mesh-facts` および `partition-audit` の実行時ネイティブバイナリ呼び出しは行わない。
- シリアルメッシュの `polyMesh` 5ファイル（points, faces, owner, neighbour, boundary）のファイルサイズおよびハッシュは収集しない。
- ランクごとの領域分割メッシュ5ファイルのファイルサイズおよびハッシュは収集しない。
- ランクごとのアドレッシングファイル群（cell/face/point/boundary addressing）のファイルサイズおよびハッシュは収集しない。
- ランクごとの環境変数スナップショットは生成・保存しない。
- 通常ベンチマーク実行においてIntel VTuneプロファイルを収集することはない。
- `collection_complete` フラグ、所有者/型レジストリの競合表、およびプロジェクション/コンシューマ用の中間キーは生成しない。
- データベース側での動的な最新値選択、自動マージ、重複排除ロジックは構築しない。

上記の巨大なメッシュファイル群のハッシュ計算は、64Mセル規模のメッシュにおいてソルバー完了後に数分間の再読み込みを要し、構成別の性能評価に必要な情報量に対してI/Oオーバーヘッドが過大である。必要なトポロジー情報、ランク別セル数分布、プロセッサ境界パッチ数、および境界面数は、保存済みのログテキストから数秒以内で取得可能である。

## 障害時のエラーセマンティクス

確定したフラグメントのBigQueryへの送信は、500行単位のチャンクで行い、再試行制御や `insertId` による重複排除は行わない。同一行の重複蓄積を許容する設計である。
なお、ネットワーク送信の失敗、メッシュログの解析失敗、あるいはIMB/プロファイル計測の失敗が発生した場合でも、それらは警告ログ（warning）として記録するのみとし、すでに正常終了したソルバーの計算結果ステータスを失敗へ変更することはない。フラグメントファイルは診断用の成果物であり、再送キューとしては扱わない。
