# 実験メトリクス収集システム

## 目的

スーパーコンピュータ環境上で実行されるOpenFOAMの計算実験について、再現条件、実行性能、成否判定、および数値精度の健全性を実行（run）単位でGoogle BigQueryへ記録する。Googleスプレッドシートは直接のデータ保存先とはせず、Connected Sheets等を用いて必要なキーのみをクエリし、横持ちの比較表へ変換して活用する。

OpenFOAMの反復ステップごとの詳細な時系列データはBigQueryへは送信しない。1回の実行に対する実験設定値、計測所要時間、最終収束値、および末尾ウィンドウの集約統計量のみを対象とする。

## 確定した収集モジュール構成

| 設計ドキュメント | 実装識別名 | 主な収集キー | 送信タイミング |
|---|---|---|---|
| [01-run-and-source.md](experiment-metrics/01-run-and-source.md) | `run_source` | `run.*`, `git.*` | ジョブ開始直後、全処理終了直後 |
| [02-scheduler.md](experiment-metrics/02-scheduler.md) | `scheduler_pjm` | `scheduler.*`, `resource.job.*` | PJMジョブ終了検知直後 |
| [03-platform.md](experiment-metrics/03-platform.md) | `platform` | `system.*`, `hardware.*`, `env.*` | 計算前処理の開始前 |
| [04-case-and-mesh.md](experiment-metrics/04-case-and-mesh.md) | `case_config`, `mesh` | `case.*`, `mesh.*` | メッシュ生成前、ソルバー実行前 |
| [05-parallel.md](experiment-metrics/05-parallel.md) | `parallel_config` | `parallel.*` | ソルバー実行直前 |
| [06-timing-and-resource.md](experiment-metrics/06-timing-and-resource.md) | `stage_runner` | `perf.*`, `run.stage.*` | 各ステージ処理の完了直後 |
| [07-solver-and-result.md](experiment-metrics/07-solver-and-result.md) | `solver_status`, `aero_result`, `field_result` | `solver.*`, `result.*` | ソルバー完了直後 |
| [08-artifact.md](experiment-metrics/08-artifact.md) | `numerical_summary` | `artifact.numerical_summary.*` | 数値検証サマリー生成直後 |

本モジュール分割は、データの取得元、取得タイミング、およびエラー処理方針が共通する項目を論理的にまとめるためのものである。BigQueryのテーブルスキーマをモジュールごとに細分化することはない。

## BigQueryの格納スキーマ仕様

生データテーブル（raw table）は、以下の3列のみで構成される。

```text
run    STRING NOT NULL
key    STRING NOT NULL
value  STRING NOT NULL
```

データ格納例：

| run | key | value |
|---|---|---:|
| `openfoam-123456-1-98765` | `parallel.decomposition.subdomains` | `"120"` |
| `openfoam-123456-1-98765` | `mesh.cell_count` | `"356630"` |
| `openfoam-123456-1-98765` | `result.aero.cd.tail.mean` | `"0.512345"` |
| `openfoam-123456-1-98765` | `resource.job.memory.max_rss_bytes` | `""` |

`value` 列は、BigQuery上では常に単一のSTRINGスカラーとして格納される。取得された値が整数（int）、浮動小数点数（float）、真偽値（bool）、またはタイムスタンプである場合は、正規化された文字列表現に変換する。取得値がリスト配列である場合は、要素ごとの個別レコードへ展開せず、Pythonの `str(list)` 等により単一のSTRING値として集約する。複雑なネストオブジェクトや独自JSONスキーマはテーブルへ持ち込まない。また、イベントIDや計測時刻といった管理列をテーブルに追加することもない。

正常終了した実行において、`(run, key)` のペアは論理的に一意である。テーブルは追記専用（append-only）として運用し、ネットワーク再試行等によって完全に同一の `(run, key, value)` が重複挿入された場合は、参照ビュー側のクエリで自動的に重複排除（deduplicate）を行う。同一の `(run, key)` に対して異なる `value` が観測された場合は、データ競合（conflict）として検出し、分析用ビューから隔離する。

テーブルには取り込み時間パーティショニング（ingestion-time partitioning）を適用し、`run` および `key` でクラスタリングを行う。数値、真偽値、タイムスタンプへの型変換は、参照ビュー側で `SAFE_CAST` 関数を用いて実施する。

## キー命名規則

- 原則として英小文字、数字、およびアンダースコアを用い、階層構造はピリオド（`.`）で区切る。
- 同種の構成要素に安定した論理名が存在する場合は、インデックス番号よりもその名前を優先する。
- ベクトル、タプル、コマンド引数列など、順序性を有する複数要素の値を要素番号付きのサブプロパティへ細分化して展開しない。取得単位のリスト全体を単一のSTRING値として保持する。
- 成果物、プローブ観測点、物理フィールドなど、固有の意味を持つ対象には安定した論理識別名を用いる。
- 時間の単位は原則として秒とし、キー末尾に `_sec` を付与する。データ量はバイト単位とし、`_bytes` を付与する。
- 0〜100の百分率は `_percent`、0〜1の無次元比率は `_ratio` とする。
- 単位の異なる値、あるいは最小値（min）、最大値（max）、平均値（mean）、最終値（final）など統計的意味が異なる値は、必ず別々のキーとして定義する。

通常のメトリクスキーの正規表現パターンは以下の通りである。

```text
^[a-z][a-z0-9_]*(\.(?:[a-z][a-z0-9_]*|[0-9]+))*$
```

環境変数キーに限り、大文字・小文字を維持したまま以下のパターンを許容する。

```text
^env\.[A-Za-z][A-Za-z0-9_]*$
^env\.encoded\.[0-9a-f]+$
^env\.bytes\.(?:[A-Za-z][A-Za-z0-9_]*|encoded\.[0-9a-f]+)$
```

## 値のエンコード規則

- 整数は符号付き10進表記、浮動小数点数は有限値のロケール非依存10進表記とする。
- 真偽値は小文字の `true` または `false` とする。
- タイムスタンプはタイムゾーン情報を含むISO 8601形式とする。
- 数値データに単位表記、桁区切りカンマ、`NaN`、無限大（Infinity）を含めてはならない。
- 取得コマンドの失敗、対象の列・値の欠損、または型変換エラーが発生した場合は、該当キーの値を空文字（`""`）として保存する。
- 値が実際に空文字列である環境変数についても、空文字として保存する。
- リスト構造は、Pythonの `str(list)` による単一のスカラー文字列として格納する。
- 改行コードを含む文字列も、単一のスカラー文字列としてそのまま保持可能である。

各キーの論理型は各モジュール仕様書において厳密に定義されており、送信時にその型に応じた正規のSTRING文字列へ変換する。参照ビュー側では `NULLIF(value, '')` を用いて空文字をSQLの `NULL` へ変換した上で `SAFE_CAST` を適用する。BigQueryの物理テーブル自体は `STRING NOT NULL` の3列仕様を一貫して維持する。

## コレクターの独立性と非照合原則

コレクターの責務は、定義された取得元から正確に値を読み取り、BigQueryへ送信することに限定される。他の環境変数、外部設定ファイル、公称スペック値、想定プロファイル、あるいはベースラインデータとの一致検証（整合性チェック）をコレクター内部で実施してはならない。

たとえば、`numberOfSubdomains` は `system/decomposeParDict.6` から読み取るのみであり、`OPENFOAM_MPI_PROCS` や `PJM_MPI_PROC` との照合は行わない。最終計算時刻もファイルから読み取るだけであり、`endTime` との一致判定をコレクター側で行うことは避ける。

コマンドの実行失敗、目的の値の欠落、あるいは数値変換不能が発生した場合は、送信予定であった各キーを `value=""` として送信する。収集処理における警告メッセージは標準エラー出力へ記録する。メトリクス取得の失敗のみを理由としてOpenFOAMの計算パイプライン自体を中断させてはならない。

## 環境変数の網羅的保存と非重複原則

計算プロセスが保持する環境変数は、`os.environb` を用いて例外なく全件保存する。許可リスト（allowlist）、拒否リスト（denylist）、および機密情報フィルタリングは一切介在させない。

ただし、BigQuery送信用の一時認証JSONは実験条件そのものではない。CLIの起動直後に専用環境変数からメモリ上へ読み込んだ上でプロセス環境から即座に削除し、その後にコレクター群を起動する。したがって、`EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_JSON` およびPJM搬送用の `EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_BASE64` は計算プロセスの環境変数には残存せず、`env.*` として外部送信されることはない。これらを除くすべての実験環境変数にはいかなるフィルタも適用しない。

環境変数から導出可能な情報を、別の名前空間へ勝手に正規化、分割、あるいは複製して保存することは厳禁とする。たとえば、以下のような重複エイリアスキーは作成しない。

```text
github.*
software.openfoam.*
software.module.*
scheduler.job_id
parallel.mpi.fabric
parallel.cpu_binding.profile
```

GitHub Actions、PJM、OpenFOAM、環境モジュール、およびMPIの設定値は、BigQuery上で `env.GITHUB_*`、`env.PJM_*`、`env.WM_*`、`env.LOADEDMODULES`、`env.I_MPI_*` を直接参照する。一方、環境変数以外の独立した正本を持つGit情報、カーネル/CPUの実測値、ランチャー起動引数、OpenFOAM辞書設定値、および `pjstat` 会計値については、固有の個別メトリクスとして記録する。

環境変数名がASCIIの `[A-Za-z][A-Za-z0-9_]*` に合致する場合は `env.<name>` とする。それ以外の文字を含む場合は、変数名の生バイト列を小文字の16進数文字列へ変換して `env.encoded.<hex>` とする。値がUTF-8として無効なバイト列を含む場合は、生バイト列をBase64化し、同一の名前トークンを `env.bytes.<name-token>` の配下に格納する。このBase64化は、単一の値を可逆的に保存するためのエンコード処理であり、複数値をまとめるためのものではない。

## データ収集および送信のライフサイクル

```text
コレクターが正本データソースから情報を取得
  → 必要な値を抽出して正規化STRING化
  → 同一契機で取得されたレコード群をメモリ上で単一バッチ化
  → Google BigQueryへ直ちにHTTP送信
  → 正常応答を確認後、メモリ上のバッチを破棄
```

1メトリクスごとに個別HTTPリクエストを発行することはせず、同一のコマンド、API、またはファイルから同時に得られた値を1つのバッチにまとめて送信する。全実行が完了するまでデータをメモリ内に滞留させることはしない。また、送信待ちの一時ファイル、ローカルスプール領域、キュー等は一切作成しない。プロセス内での短時間のリトライ処理中のみバッチデータをメモリ上に保持する。

OpenFOAM自身が出力する `postProcessing` 配下のテーブル群や、ユーザー向けの `numerical-summary.md` は正規の計算結果であり、転送用の一時ファイルではない。コレクターが独自にコマンドの生出力をディスクへ退避させることは禁止する。

ジョブ開始、実行環境、ケース設定、メッシュ情報などのバッチは確定直後に順次送信されるため、その後に計算ノードがクラッシュした場合であっても、送信済みのレコードは確実にBigQuery側に残る。強制終了が発生した場合は、終了バッチや結果バッチが存在しないこと自体が「実行未完了」を示す確実な証跡となる。

## 共通コンポーネント構成

実装は [`experiment-metrics/`](../experiment-metrics/) 配下のPythonパッケージとして集約し、以下の共通処理をコレクター本体から分離して再利用する。

| コンポーネント | 責務・役割 |
|---|---|
| `CommandRunner` | シェルを介さない厳密なargv配列実行、`LC_ALL=C` 設定、タイムアウト制御、終了コード取得、パイプ読み取り |
| `ScalarCodec` | 整数、浮動小数点数、真偽値、タイムスタンプ、リストの正規化STRING変換 |
| `KeyValidator` | 通常メトリクスキーおよび環境変数キーの構文検証と組み立て |
| `OpenFoamDictionaryReader` | `foamDictionary -entry ... -value` の実行および値の抽出 |
| `OpenFoamTokenizer` | スカラー、単語、括弧付き3次元ベクトルの字句解析 |
| `OpenFoamTableReader` | ヘッダー列名による安全な列選択と、最終行および末尾ウィンドウの読み取り |
| `FileHasher` | 通常ファイルのSHA-256ハッシュ計算および正規化入力マニフェストハッシュの生成 |
| `StageRunner` | `monotonic_ns` を用いた高精度計時と各ステージの終了コード取得 |
| `BatchSender` | HTTPリクエスト構築、認証ヘッダー付与、BigQueryへの送信、レスポンス検証、プロセス内リトライ制御 |

コレクターの概念的インターフェースは以下の通りである。

```text
collect(context) -> list[Metric(key, value)]
send(run, records) -> success
```

コレクター自体はBigQueryのクライアントライブラリへ直接依存しない。呼び出し側が `collect` の返り値を受け取った直後にエンコードおよび送信を行い、成功を確認した後にレコードを破棄する。

## パーサー選定方針

データ取得の手法は、以下の優先順位に従って決定する。

1. 公式が提供する機械可読な構造化フォーマット
2. 単一の値を返す公式コマンドまたはAPI
3. OSカーネルが提供する構造化インターフェース
4. 公式の列ヘッダー付きテーブル形式
5. バージョン固定された人間向けテキスト出力パーサー

| 取得対象 | 採用した取得手法 | 人間向けテキスト解析の要否 |
|---|---|---|
| 全環境変数 | Python `os.environb` によるバイト列取得 | 不要 |
| OS諸元、カーネル、ホスト名、CPUアフィニティ | Python標準ライブラリAPI | 不要 |
| CPUトポロジー | `lscpu --json` ＋ 標準JSONパーサー | 不要 |
| 主記憶総量 | `/proc/meminfo` の固定トークン字句解析 | 不要 |
| Gitリポジトリ情報 | 単一の値を返す `git` コマンド | 不要 |
| OpenFOAM辞書設定 | `foamDictionary -entry ... -value` | 不要 |
| ソルバー完了状態・数値結果 | v2606 function objectテーブル ＋ トークンパーサー | 不要 |
| PJM終了会計統計 | `pjstat --data --delimiter` による整形済み出力解析 | 不要 |
| メッシュ統計・品質判定 | v2606 `checkMesh` 成功行の固定トークンパーサー | 唯一の例外として許容 |

`checkMesh` についてのみ、OpenFOAM v2606にJSON等の構造化出力オプションが存在しないため、既知の固定行頭ラベルの直後に出現する数値を読み取る。ソルバーログ（`simpleFoam.log` 等）に対して汎用的な正規表現パターンマッチングを適用することは避ける。また、コレクター内部で値同士の整合性を検証することはしない。

## Google BigQueryへの送信仕様

オーバーヘッドの極小化を最優先とし、BigQuery REST APIの `tabledata.insertAll` エンドポイントに対してUTF-8エンコードされたJSONリクエストを直接送信する。送信先のプロジェクト、データセット、テーブル、およびロケーション設定は、[`experiment-metrics/pyproject.toml`](../experiment-metrics/pyproject.toml) 内の `tool.experiment-metrics.bigquery` セクションから読み込む。

OpenFOAM用の標準送信先テーブルは以下の通りである。

```text
apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_metrics
```

データセット名およびテーブル名の双方に `openfoam_` プレフィックスを付与し、BigQuery Explorer等のGUI上で別ワークロードのメトリクスと明瞭に区別できるようにしている。Python実行環境における外部依存関係は認証用の `google-auth` のみに限定し、HTTP通信およびJSON処理には標準ライブラリを利用する。大規模データ向けにはStorage Write APIが推奨されるが、本システムは1回の実行あたりのバッチ数が少数であるため、重量級のgRPC依存関係を排除できるREST方式を採用している。認証にはApplication Default Credentials（ADC）およびスコープ `https://www.googleapis.com/auth/bigquery.insertdata` を使用する。サービスアカウント等のプリンシパルには、少なくとも `bigquery.tables.updateData`、`bigquery.tables.get`、`bigquery.datasets.get` の権限を付与する。

リクエストボディには複数の行を含めることができるが、各行の `json` オブジェクトは以下の3列のみで構成される。

```json
{
  "skipInvalidRows": false,
  "ignoreUnknownValues": false,
  "rows": [
    {
      "insertId": "<sha256(run NUL key NUL value)>",
      "json": {
        "run": "openfoam-123456-1-98765",
        "key": "mesh.cell_count",
        "value": "356630"
      }
    }
  ]
}
```

`insertId` は一時的なネットワーク瞬断等による再送時のベストエフォートな重複抑制に利用されるトランスポート用メタデータであり、テーブルの列データや普遍的なイベントIDではない。最終的な重複排除は参照ビュー側で行う。

HTTPステータスコード 429、500、502、503、504、およびTCP通信切断のみを一時的エラー（transient error）とみなし、メモリ上に保持された同一バッチを最大3回まで再送する（リトライ間隔は1秒、2秒、4秒を上限とするジッター付き指数バックオフ）。認証エラー、スキーマ不整合、および行バリデーションエラーについては再送を行わない。恒久的なエラーまたはリトライ上限到達時はエラー内容を標準エラー出力へ記録するが、OpenFOAMの計算パイプライン自体の成否判定は変更せず、ディスクへの退避スプール等も作成しない。

## 意図して収集しない項目一覧

```text
OpenFOAMの反復ステップごとの生ログデータ
秒単位の動的なCPU・メモリ使用率推移
巨大なログテキスト全文やバイナリフィールドデータ本体
他の保存済みレコードから一意に算出可能な派生値
環境変数から取得可能な値の別名エイリアスや細分化データ
ベースラインとの差分比率、高速化率（speedup）、並列化効率
複数回実行にまたがる平均値、中央値、標準偏差等の統計量
物理量別のベースラインが確定していない段階での validation.passed 判定
```

複数回実行間の統計集約、データ型の変換、ピボットテーブル化、および許容閾値に基づく判定処理は、BigQueryのビューまたはConnected Sheets側において実施する。

## 参照仕様

- BigQuery `tabledata.insertAll` API リファレンス: <https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/insertAll>
- BigQuery ストリーミングインサートと重複抑制: <https://cloud.google.com/bigquery/docs/streaming-data-into-bigquery>
- Application Default Credentials（ADC）の概要: <https://cloud.google.com/docs/authentication/application-default-credentials>
