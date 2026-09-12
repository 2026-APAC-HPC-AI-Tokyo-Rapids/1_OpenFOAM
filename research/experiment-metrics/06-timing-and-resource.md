# 実測時間・リソース使用量収集モジュール

## モジュール境界

実装上の識別名は `stage_runner` とする。すべての外部コマンドを共通のラッパー経由で起動し、経過時間（wall-clock time）および終了コード（exit code）を取得する。各コマンドの完了時に直ちに2つのレコードをBigQueryへ送信し、パイプライン終了までメモリ内に保持することはしない。

PJMが測定するジョブ全体のCPU時間および最大消費メモリ（RSS）については、[ジョブスケジューラ収集モジュール](02-scheduler.md)が同一の `pjstat` 終了バッチから `resource.job.*` として送信する。PythonプロセスやGNU time等を用いてMPIプロセスクリーを不完全に再測定することは避ける。

## 確定メトリクス

パイプラインの各ステージ名は以下のように固定する。

```text
surface_feature_extract
block_mesh
decompose_par
snappy_hex_mesh
topo_set
potential_foam
check_mesh
simple_foam
result_archive
```

各ステージについて、以下の2つのキーを送信する。

```text
perf.stage.<stage_name>.wall_time_sec
run.stage.<stage_name>.exit_code
```

さらに、パイプライン監視処理が全体の所要時間として以下を送信する。

```text
perf.pipeline.wall_time_sec
```

送信キーの具体例：

```text
perf.stage.simple_foam.wall_time_sec
run.stage.simple_foam.exit_code
```

## 計測方法

対象コマンドの起動直前とプロセス待機（wait）完了直後に `time.monotonic_ns()` を呼び出し、その差分を `1_000_000_000` で除算して秒数を算出する。子プロセスに渡す引数列（argv）の構築や標準入出力パイプの準備処理は、開始時刻の記録前に完了させておく。

```text
t0 = monotonic_ns()
process = spawn(argv)
return_code = wait(process)
t1 = monotonic_ns()
wall_time_sec = (t1 - t0) / 1_000_000_000
send_immediately(wall_time_sec, return_code)
```

ステージ経過時間には、対象コマンドの実行、MPIの初期化・終了処理、およびコレクターがパイプ出力を読み切るまでの時間を含める。BigQueryへのネットワーク送信時間はこれに含めない。時刻精度の劣化を防ぐため、送信前に適切な精度の数値文字列へ変換する。

パイプライン全体の所要時間は、最初のステージ開始直前から最終ステージの完了直後までの時間とする。ステージ間におけるケース辞書の編集、フィールドファイルのコピー、ハッシュ計算等の処理時間も含むため、個別ステージの所要時間の単純な総和とは一致しない。

## 失敗時の扱い

- コマンドが外部シグナルにより終了した場合、Python `subprocess` が返す負の終了コードの絶対値をシグナル番号として記録する。
- 特定のステージが失敗した場合であっても、当該ステージの2レコードを正常に送信した上でパイプライン全体の実行を停止する。
- 失敗したステージ以降の後続ステージについては、実行もメトリクス送信も行わない。
- 送信失敗時は共通トランスポート層のエラーハンドリング規則に従い、本計測モジュール独自のリトライキュー等は作成しない。

## リソース使用量

収集する項目および取得元は以下のように確定する。

| キー | 取得元 | 単位換算 |
|---|---|---|
| `resource.job.memory.max_rss_bytes` | PJM `mmszu` | 括弧内のバイト値 |
| `resource.job.cpu.user_time_sec` | PJM `uctmut` | ミリ秒値 ÷ 1000 |
| `resource.job.cpu.system_time_sec` | PJM `sctmut` | ミリ秒値 ÷ 1000 |

これらの指標はソルバー単体のみならず、メッシュ生成、後処理、および各種シェル処理を含むPJMジョブ全体のリソース消費量を表す。キー階層における `job` の指定を省略してはならない。

## 採用しない値

| 除外項目 | 除外理由 |
|---|---|
| OpenFOAM の `ExecutionTime`、`ClockTime` | コマンドランチャー視点の経過時間より範囲が狭く、ログテキスト解析が必要となるため |
| GNU time によるRSSおよびCPU時間 | MPI並列ジョブ全体の消費量を正確に反映する保証がないため |
| プロセスのI/Oバイト数 | 共有ファイルシステムと分散MPIプロセスの全体像を一意に定義できないため |
| GPU消費エネルギー | 現在の対象キューである `a-batch` はCPU専用であるため |
| ステージ別のCPU時間およびRSS | PJMがステージ別の詳細統計を提供しておらず、オーバーヘッドなしに正確に取得することが困難なため |
| プロファイラによるパフォーマンスカウンタ | 通常実行の共通メトリクスではなく、専用のプロファイル解析成果物として扱うべきであるため |

## 参照仕様

- Python 単調増加クロック: <https://docs.python.org/3/library/time.html#time.monotonic_ns>
- Python `subprocess` 終了コード: <https://docs.python.org/3/library/subprocess.html#subprocess.Popen.returncode>
- Fujitsu PJM 統計項目定義: <https://software.fujitsu.com/jp/manual/manualfiles/m220010/j2ul2466/02enz008/j2ul-2466-02enz0.pdf>
