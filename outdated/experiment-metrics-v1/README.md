# experiment-metrics

OpenFOAM実験からrun単位の値を取得し、BigQueryの`run`, `key`, `value`の3列へ
直ちに送る小さなPythonプロジェクトです。collectorは値同士を照合しません。
取得失敗時は対象キーの`value`を空文字にします。

`value`は常に1つのSTRINGとして送ります。数値、bool、時刻などはスカラー表現にし、
取得値がlistの場合も要素ごとのキーへ展開せず、Pythonの`str(list)`による1つの文字列
として保存します。

## 設定

BigQueryの非機密設定は`pyproject.toml`に置く。

```toml
[tool.experiment-metrics.bigquery]
project = "apac-hpc-ai-tokyo-rapids-26"
dataset = "openfoam_experiment_metrics"
table = "openfoam_metrics"
location = "asia-northeast1"
```

GitHub ActionsではサービスアカウントJSONをrepository secret
`EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_JSON`へ保存する。runner上ではJSONを
そのまま環境変数から読み、PJMへ渡すときだけ区切り文字を避けるためBase64化する。
collectorはメモリ上でJSONへ戻して`google-auth`へ渡す。認証JSONをfileへは書かない。

認証用環境変数はCLI起動直後に取り出して環境から削除する。このため、計算プロセスの
全環境変数を保存する`platform` collectorにも認証情報は混入しない。

動作確認では`EXPERIMENT_METRICS_SINK=stdout`を指定すると、送信予定の3列を
標準出力へJSON Linesで表示できます。

## 開発

```bash
uv sync
uv run pytest
uv run experiment-metrics --help
```

## 主な呼び出し

```bash
experiment-metrics prepare-case --case-dir .
experiment-metrics collect platform --case-dir .
experiment-metrics stage simple_foam -- mpirun -np 120 simpleFoam -parallel
experiment-metrics collect solver-result --case-dir .
```
