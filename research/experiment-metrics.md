# 実験メトリクス収集システム

## 目的

スパコン上のOpenFOAM実験について、再現条件、性能、成否、数値精度の異常を
run単位でBigQueryへ記録する。Googleスプレッドシートは保存先にせず、
Connected Sheets等から必要なキーだけを横持ちの表へ変換する。

OpenFOAMのiterationごとの値はBigQueryへ送らない。1 runに対する設定値、実測値、
最終値、末尾windowの集約値だけを対象とする。

## 確定した収集モジュール

| 文書 | 実装単位 | 主なキー | 送信時点 |
|---|---|---|---|
| [01-run-and-source.md](experiment-metrics/01-run-and-source.md) | `run_source` | `run.*`, `git.*` | 開始直後、終了直後 |
| [02-scheduler.md](experiment-metrics/02-scheduler.md) | `scheduler_pjm` | `scheduler.*`, `resource.job.*` | PJM終了直後 |
| [03-platform.md](experiment-metrics/03-platform.md) | `platform` | `system.*`, `hardware.*`, `env.*` | 計算開始前 |
| [04-case-and-mesh.md](experiment-metrics/04-case-and-mesh.md) | `case_config`, `mesh` | `case.*`, `mesh.*` | meshing前、solver前 |
| [05-parallel.md](experiment-metrics/05-parallel.md) | `parallel_config` | `parallel.*` | solver前 |
| [06-timing-and-resource.md](experiment-metrics/06-timing-and-resource.md) | `stage_runner` | `perf.*`, `run.stage.*` | 各stage終了直後 |
| [07-solver-and-result.md](experiment-metrics/07-solver-and-result.md) | `solver_status`, `aero_result`, `field_result` | `solver.*`, `result.*` | solver終了直後 |
| [08-artifact.md](experiment-metrics/08-artifact.md) | `numerical_summary` | `artifact.numerical_summary.*` | summary完成直後 |

分類は取得元、取得時点、失敗方針が同じ値をまとめるためのものである。
BigQuery schemaをmoduleごとに分けない。

## BigQueryの保存形式

raw tableの列は次の3つだけとする。

```text
run    STRING NOT NULL
key    STRING NOT NULL
value  STRING NOT NULL
```

| run | key | value |
|---|---|---:|
| `openfoam-123456-1-98765` | `parallel.decomposition.subdomains` | `"120"` |
| `openfoam-123456-1-98765` | `mesh.cell_count` | `"356630"` |
| `openfoam-123456-1-98765` | `result.aero.cd.tail.mean` | `"0.512345"` |
| `openfoam-123456-1-98765` | `resource.job.memory.max_rss_bytes` | `""` |

`value`はBigQuery上で必ず1つのSTRINGスカラーである。取得値がint、float、bool、
timestampならcanonicalな文字列表現にする。取得値がlistなら要素ごとのrecordへ展開せず、
Pythonの`str(list)`で1つのSTRINGにする。objectや独自JSON schemaは格納しない。
event IDや計測時刻などの列は追加しない。

通常の成功runでは`(run, key)`を一意とする。raw tableはappend-onlyとし、
再試行で完全に同一の`(run, key, value)`が入った場合は参照viewで除去する。
同じ`(run, key)`に異なるvalueがあればデータ競合としてviewから隔離する。

tableはingestion-time partitioningを使い、`run`, `key`でclusterする。数値、bool、
timestampへの型変換は参照viewで`SAFE_CAST`する。

## キー規則

- 通常は英小文字、数字、アンダースコアを使い、階層をピリオドで区切る。
- 同種要素に安定した名前があれば、その名前を数字より優先する。
- vector、tuple、command引数など順序を持つ複数値を、要素番号のsub-propertyへ
  展開しない。取得単位のlist全体を1つのSTRING valueとして保持する。
- 成果物、probe地点、fieldなど固有の意味を持つ対象には安定した論理名を使う。
- 時間は原則秒で`_sec`、data量はbyteで`_bytes`を末尾に付ける。
- 0–100の割合は`_percent`、0–1の比率は`_ratio`とする。
- 単位の異なる値、min/max/mean/finalなど意味の異なる値は別キーにする。

通常キーの形式は次である。

```text
^[a-z][a-z0-9_]*(\.(?:[a-z][a-z0-9_]*|[0-9]+))*$
```

環境変数キーだけは大文字小文字を変えず、次も許す。

```text
^env\.[A-Za-z][A-Za-z0-9_]*$
^env\.encoded\.[0-9a-f]+$
^env\.bytes\.(?:[A-Za-z][A-Za-z0-9_]*|encoded\.[0-9a-f]+)$
```

## 値規則

- intは符号付き10進整数、floatは有限のlocale非依存10進表記とする。
- boolは小文字の`true`または`false`とする。
- timestampはtimezoneを含むISO 8601とする。
- 数値に単位、桁区切り、`NaN`、infinityを含めない。
- 取得commandの失敗、目的の列・値の欠損、型変換失敗は空文字を保存する。
- 値が実際に空の環境変数も空文字を保存する。
- listはPythonの`str(list)`で1つのscalar stringとして保持する。
- 改行を含む文字列は1つのscalar stringとして保持できる。

論理型はmodule文書で固定し、送信時にその型をSTRINGへ変換する。
参照viewでは`NULLIF(value, '')`を使い、空文字をSQL `NULL`としてから
`SAFE_CAST`する。raw tableは`STRING NOT NULL`の3列仕様を維持する。

## 収集器は照合をしない

collectorの役割は、表に記した取得元から値を読み、BigQueryへ送るところまでとする。
別の環境変数、設定値、公称値、想定profile、baselineとの一致確認は行わない。

例えば`numberOfSubdomains`は`system/decomposeParDict.6`から読み、
`OPENFOAM_MPI_PROCS`や`PJM_MPI_PROC`と照合しない。最終simulation timeも読み取るだけで、
`endTime`との一致判定はcollectorでは行わない。

commandが失敗した、目的の値がない、数値として読めない場合は、予定していた各キーを
`value=""`で送る。収集上の警告は標準エラーへ出す。メトリクスの取得失敗だけを
理由にOpenFOAMの実験を停止しない。

## 環境変数の非重複原則

計算プロセスが持つ環境変数を`os.environb`から問答無用で全件保存する。
allowlist、denylist、秘密情報filterを設けない。

BigQuery送信専用の認証JSONは実験条件ではない。CLI起動直後に専用環境変数から
メモリへ移して環境から削除し、その後にcollectorを起動する。したがって
`EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_JSON`と、PJM搬送用の
`EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_BASE64`は計算プロセスの環境に残らず、
`env.*`として収集されない。これ以外の実験環境変数にはfilterを設けない。

環境変数から分かる情報は、別namespaceへ正規化、分割、複製して保存しない。
例えば次の別名は作らない。

```text
github.*
software.openfoam.*
software.module.*
scheduler.job_id
parallel.mpi.fabric
parallel.cpu_binding.profile
```

GitHub、PJM、OpenFOAM、module、MPIの値は`env.GITHUB_*`, `env.PJM_*`,
`env.WM_*`, `env.LOADEDMODULES`, `env.I_MPI_*`をBigQuery上で直接参照する。
環境変数以外の正本を持つGit情報、kernel/CPU実測、launcher引数、OpenFOAM辞書値、
`pjstat` accounting値は個別メトリクスとして残す。

環境変数名がASCIIの`[A-Za-z][A-Za-z0-9_]*`なら`env.<name>`とする。
それ以外は名前のraw byte列を小文字hex化して`env.encoded.<hex>`とする。
値がUTF-8でなければraw byte列をBase64化し、同じname tokenを
`env.bytes.<name-token>`の下に置く。このBase64は1つの値を可逆保存するための
encodingであり、複数値の梱包ではない。

## 取得・送信ライフサイクル

```text
collectorが正本から取得
  → 必要な値を読み取ってSTRING化
  → 同時に得たrecordをメモリ上で1 batch化
  → BigQueryへ直ちに送信
  → 応答確認後にbatchを破棄
```

1 metricごとのHTTP requestは行わず、同じcommand/API/fileから同時に得る値を
1 batchにする。全runの値を終了まで溜め込まない。送信待ちの一時ファイル、
local spool、queueを作らない。process内での短い再試行中だけbatchを保持する。

OpenFOAM自身が生成する`postProcessing`表と、ユーザー向け
`numerical-summary.md`は計算結果であり、transport用一時ファイルではない。
collectorが独自にraw command出力をfileへ退避することは禁止する。

開始、環境、case、meshなどのbatchは確定直後に送るため、その後nodeがcrashしても
既送信分は残る。強制終了では終了・結果batchがないこと自体がrun未完了の印となる。

## 共通component

実装は[`experiment-metrics/`](../experiment-metrics/)のPython packageに置き、
次をcollectorから分離して共用する。

| component | 責務 |
|---|---|
| `CommandRunner` | shellを介さないargv実行、`LC_ALL=C`、timeout、return code、pipe読取 |
| `ScalarCodec` | int/float/bool/timestamp/listの単一STRING化 |
| `KeyValidator` | 通常キーと環境変数キーの組み立て |
| `OpenFoamDictionaryReader` | `foamDictionary -entry ... -value`の実行と値の読取 |
| `OpenFoamTokenizer` | scalar、word、括弧付きvectorのtoken化 |
| `OpenFoamTableReader` | header名による列選択と最終行・末尾windowの読取 |
| `FileHasher` | regular file SHA-256とcanonical manifest hash |
| `StageRunner` | `monotonic_ns`計時とstage return code取得 |
| `BatchSender` | request生成、認証、送信、応答検証、process内再試行 |

collectorの概念的interfaceは次である。

```text
collect(context) -> list[Metric(key, value)]
send(run, records) -> success
```

collectorはBigQuery clientへ直接依存しない。呼び出し側は`collect`の返却直後に
encode、sendし、成功後にrecordを破棄する。

## Parser選択

取得方法は次の優先順に固定する。

1. 公式の機械可読形式
2. 1値を返す公式command/API
3. OSが提供する構造化interface
4. 公式の列header付き表
5. version固定の人間向けtext parser

| 取得対象 | 採用方法 | 人間向けtext解析 |
|---|---|---|
| 全環境変数 | Python `os.environb` | 不要 |
| OS/kernel/hostname/affinity | Python API | 不要 |
| CPU | `lscpu --json` + JSON parser | 不要 |
| memory total | `/proc/meminfo`の固定token grammar | 不要 |
| Git | 1値を返す`git` command | 不要 |
| OpenFOAM辞書 | `foamDictionary -entry ... -value` | 不要 |
| solver/result | v2606 function object表 + token parser | 不要 |
| PJM終了統計 | `pjstat --data --delimiter` | 不要 |
| mesh統計・品質 | v2606 `checkMesh`成功行の固定token parser | 唯一の例外 |

`checkMesh`だけはv2606にJSON等がないため、既知の行頭labelから直後の数値を読む。
solver logへ汎用正規表現を掛けない。collectorは値同士の整合性までは判定しない。

## BigQueryへの送信

軽量さを優先し、BigQuery REST APIの`tabledata.insertAll`へUTF-8 JSON requestを送る。
送信先のproject、dataset、tableとlocationは
[`experiment-metrics/pyproject.toml`](../experiment-metrics/pyproject.toml)の
`tool.experiment-metrics.bigquery`から読む。
OpenFOAM用の送信先は
`apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_metrics`とする。
datasetとtableの両方に`openfoam_`を付け、別workloadのメトリクスとBigQuery
Explorer上で区別できるようにする。
Python側の外部依存は認証用`google-auth`だけとし、HTTPとJSONは標準libraryを使える。
新規の高throughput用途ではStorage Write APIが推奨されるが、本システムはrun当たり
少数batchなので、gRPC依存を増やさないこの方式に固定する。認証はApplication Default
Credentialsと`https://www.googleapis.com/auth/bigquery.insertdata` scopeを使う。
principalには少なくとも`bigquery.tables.updateData`, `bigquery.tables.get`,
`bigquery.datasets.get`を与える。

request bodyで複数rowを包むが、各rowの`json`は3列だけである。

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

`insertId`は再試行時のbest-effort重複抑制に使うtransport metadataであり、
table列やevent IDではない。最終的な重複処理は参照viewで行う。

HTTP 429、500、502、503、504と通信切断だけを一時errorとし、同じmemory batchを
最大3回、1秒・2秒・4秒を上限とするjitter付きbackoffで再送する。
認証・schema・row validation errorは再送しない。恒久失敗または再試行枯渇は
標準エラーへ記録するが、OpenFOAM pipelineの成否は変更せず、diskへも退避しない。

## 収集しない値

```text
OpenFOAMのiteration/stepごとのraw値
秒単位のCPU・memory利用率
大きなlogやbinary field本体
他の保存値から一意に計算できる派生値
環境変数の別名・分解値
baseline差、speedup、parallel efficiency
複数runの平均、中央値、標準偏差
物理量別baselineがない段階のvalidation.passed
```

run間の集計、型変換、pivot、許容差判定はBigQuery viewまたはSheetsで行う。

## 参照仕様

- BigQuery `tabledata.insertAll`:
  <https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/insertAll>
- BigQuery streaming insertとbest-effort重複抑制:
  <https://cloud.google.com/bigquery/docs/streaming-data-into-bigquery>
- Application Default Credentials:
  <https://cloud.google.com/docs/authentication/application-default-credentials>
