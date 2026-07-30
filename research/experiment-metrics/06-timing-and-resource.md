# 実測時間・資源使用量収集モジュール

## モジュール境界

実装名は `stage_runner` とする。全外部commandを同じwrapperで起動し、
wall timeとreturn codeを取得する。各commandが終わるたびに2レコードを直ちに送り、
pipeline終了まで保持しない。

PJMが測定するジョブ全体のCPU時間と最大memoryは
[scheduler module](02-scheduler.md)が、同じ`pjstat`終了バッチから
`resource.job.*`として送る。MPI process treeをPythonやGNU timeで不完全に
再測定しない。

## 確定メトリクス

stage名は次に固定する。

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

各stageについて次の2キーを送る。

```text
perf.stage.<stage_name>.wall_time_sec
run.stage.<stage_name>.exit_code
```

さらにpipeline supervisorが次を送る。

```text
perf.pipeline.wall_time_sec
```

例：

```text
perf.stage.simple_foam.wall_time_sec
run.stage.simple_foam.exit_code
```

## 計測方法

command起動直前とwait完了直後に`time.monotonic_ns()`を読み、差を
`1_000_000_000`で割る。subprocessへ渡す引数列の構築、標準入出力pipeの準備は
開始時刻より前に行う。

```text
t0 = monotonic_ns()
process = spawn(argv)
return_code = wait(process)
t1 = monotonic_ns()
wall_time_sec = (t1 - t0) / 1_000_000_000
send_immediately(wall_time_sec, return_code)
```

wall timeには対象command、MPI初期化・終了、collectorがpipeを読み切る時間を含む。
BigQuery送信時間は含めない。clock精度を保つため、送信前に数値文字列へ変換する。

pipeline時間は最初のstage開始直前から最後に実行されたstageの終了直後までとする。
stage間のcase編集、field copy、hash取得も含むため、stage時間の単純合計とは
一致しない。

## 失敗時の扱い

- commandがsignalで終了した場合、Pythonの負のreturn codeをそのままstageへ保存する。
- stageが失敗しても、そのstageの2レコードを送ってからpipelineを停止する。
- 後続stageは実行も送信もしない。
- 送信失敗時は共通transportの規則に従い、計測module独自のqueueを作らない。

## 資源使用量

採用する値と取得元は次で確定する。

| キー | 取得元 | 単位変換 |
|---|---|---|
| `resource.job.memory.max_rss_bytes` | PJM `mmszu` | 括弧内bytes値 |
| `resource.job.cpu.user_time_sec` | PJM `uctmut` | ms÷1000 |
| `resource.job.cpu.system_time_sec` | PJM `sctmut` | ms÷1000 |

これらはsolverだけでなく、meshing、post-processing、shell処理を含むPJM job全体を
表す。キーの`job`階層を省略しない。

## 採用しない値

| 値 | 理由 |
|---|---|
| OpenFOAM `ExecutionTime`、`ClockTime` | launcher wall timeより範囲が狭く、ログ解析が必要 |
| GNU timeのRSS、CPU time | MPI job全体を表す保証がない |
| process I/O bytes | shared filesystemとMPI process全体の定義を固定できない |
| GPU energy | 現在のa-batchはCPU-only |
| stage別CPU/RSS | PJMがstage別統計を提供せず、軽量に正しく取得できない |
| profiler counter | 通常runの共通メトリクスではなく、専用profiling成果物 |

## 参照仕様

- Python monotonic clock:
  <https://docs.python.org/3/library/time.html#time.monotonic_ns>
- Python subprocess return code:
  <https://docs.python.org/3/library/subprocess.html#subprocess.Popen.returncode>
- PJM statistical item definitions:
  <https://software.fujitsu.com/jp/manual/manualfiles/m220010/j2ul2466/02enz008/j2ul-2466-02enz0.pdf>
