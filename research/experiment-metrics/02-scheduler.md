# ジョブスケジューラ収集モジュール

## モジュール境界

実装名は `scheduler_pjm` とする。現在のGenkai/PJMだけを対象とし、
self-hosted runnerがジョブ終了後に1回だけ取得する。

PJMの全環境変数は[実行環境モジュール](03-platform.md)が`env.*`として保存する。
環境変数で得られる値は`scheduler.*`へ複製しない。このモジュールが保存するのは、
ジョブ終了後に`pjstat`から得るaccounting値だけである。

要求条件は少なくとも`env.PJM_JOBID`, `env.PJM_RSCGRP`, `env.PJM_NODE`,
`env.PJM_MPI_PROC`, `env.PJM_ELAPSE`, `env.PJM_ELAPSE_SEC`を直接参照する。
存在するその他のPJM変数も選別せず保存される。

## 確定メトリクス

### ジョブ終了後に取得する終了バッチ

| キー | 論理型 | PJM項目 | 取得方法 |
|---|---|---|---|
| `scheduler.state` | string | `st` | `pjstat`のprocessed formをそのまま保存 |
| `scheduler.started_at` | timestamp | `sdt` | `YYYY/MM/DD hh:mm:ss`をISO 8601へ変換 |
| `scheduler.elapsed_sec` | int | `elp` | 括弧内に併記される秒数 |
| `scheduler.exit_code` | int | `ec` | 10進整数へ変換 |
| `scheduler.signal` | int | `sn` | 値が0以外のときだけ送信 |
| `scheduler.pjm_code` | int | `pc` | PJM自体の終了理由コード |
| `scheduler.node_count.allocated` | int | `nnumu` | 10進整数へ変換 |
| `resource.job.memory.max_rss_bytes` | int | `mmszu` | 括弧内のbytes値を取得 |
| `resource.job.cpu.user_time_sec` | float | `uctmut` | millisecond値を1000で割る |
| `resource.job.cpu.system_time_sec` | float | `sctmut` | millisecond値を1000で割る |

runnerでジョブ終了後、次を実行する。

```bash
LC_ALL=C pjstat --history -S --choose jid,st,sdt,elp,ec,sn,pc,nnumu,mmszu,uctmut,sctmut --data --delimiter $'\t' "${PJM_JOB_ID}"
```

`--data`はPJMが提供するprocessed formであり、表示桁位置には依存しない。
headerとdataをtabでsplitし、data fieldを`--choose`へ指定した順序で読み取る。
`jid`は照会に使うだけで、環境変数との再照合や別キーへの保存は行わない。

`mmszu` はPJM表示のMiB丸め値ではなく、括弧内に併記されるbytes値を使う。
`elp`も`DD hh:mm:ss (s)`の`s`を使い、1秒未満が切り上げられるPJM値として保存する。
`sdt`はGenkaiのsystem timezoneであるAsia/Tokyoを付け、例えば
`2026/07/30 12:34:56`を`2026-07-30T12:34:56+09:00`へ変換する。
`uctmut`と`sctmut`の定義単位はmillisecondである。`pjstat`が失敗した場合や
出力されなかった項目は、該当キーを空文字で送る。
`st`、`ec`、`pc`間の整合性判定や状態の再分類は行わない。

## 失敗時の扱い

- `PJM_JOBID`は`pjstat`照会とrun名生成に必要である。
  値そのものは`env.PJM_JOBID`だけに保存する。
- 終了バッチは計算結果の成否を変更しない。
- 終了情報を取得できなくてもローカル待機キューや一時ファイルを作らない。
- `pjstat`の履歴保持期間を過ぎる前に、workflowの同じrun内で直ちに取得する。

## 採用しない値

| 値 | 理由 |
|---|---|
| scheduler側の終了時刻 | 開始時刻と経過時間から計算可能 |
| ジョブID、ジョブ名、resource group、要求node/rank数、経過時間上限 | PJM環境変数を`env.*`へ全件保存するため、別名で複製しない |
| 要求core数 | PJM環境変数に含まれ、現在はMPI process数とも一致する |
| nodeごとのaccounting | ジョブ全体の比較には集約値で十分 |
| `pjstat`通常表示の列 | 人間向け固定幅表示の解析になる |

## 参照仕様

- Fujitsu PJM `pjstat` command reference:
  <https://software.fujitsu.com/jp/manual/manualfiles/m220010/j2ul2466/02enz008/j2ul-2466-02enz0.pdf>
- Fujitsu HPC user guide, job status and statistics:
  <https://doc.cloud.global.fujitsu.com/lib/common/jp/hpc-user-manual/CheckJobStatus/>
- Genkai resource groups:
  <https://www.cc.kyushu-u.ac.jp/scp/en/usage/resource_groups/>
