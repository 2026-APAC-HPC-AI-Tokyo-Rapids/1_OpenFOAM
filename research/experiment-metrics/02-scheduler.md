# ジョブスケジューラ収集モジュール

## モジュール境界

実装上の識別名は `scheduler_pjm` とする。本モジュールは九州大学「玄界」のPJM（Fujitsu Technical Computing Suite）環境を対象とし、セルフホストランナーがジョブ終了後に1度だけメトリクスを取得する。

PJMが提供するすべての環境変数は、[実行環境収集モジュール](03-platform.md)によって `env.*` として網羅的に保存される。環境変数から取得可能な値を `scheduler.*` として二重に複製することはない。本モジュールが記録するのは、ジョブ終了後に `pjstat` コマンドから取得される会計情報（accounting）のみである。

取得にあたっては、少なくとも `env.PJM_JOBID`、`env.PJM_RSCGRP`、`env.PJM_NODE`、`env.PJM_MPI_PROC`、`env.PJM_ELAPSE`、`env.PJM_ELAPSE_SEC` を直接参照する。環境中に存在するその他のPJM関連変数も選別することなくすべて保存される。

## 確定メトリクス

### ジョブ終了後に取得する終了バッチ

| キー | 論理型 | PJM項目 | 取得方法 |
|---|---|---|---|
| `scheduler.state` | string | `st` | `pjstat` の整形済み出力（processed form）をそのまま保存 |
| `scheduler.started_at` | timestamp | `sdt` | `YYYY/MM/DD hh:mm:ss` をISO 8601形式へ変換 |
| `scheduler.elapsed_sec` | int | `elp` | 括弧内に併記される秒数値を抽出 |
| `scheduler.exit_code` | int | `ec` | 10進整数へ変換 |
| `scheduler.signal` | int | `sn` | 値が0以外の場合のみ送信 |
| `scheduler.pjm_code` | int | `pc` | PJM自体の終了理由コード |
| `scheduler.node_count.allocated` | int | `nnumu` | 10進整数へ変換 |
| `resource.job.memory.max_rss_bytes` | int | `mmszu` | 括弧内のバイト（bytes）値を抽出 |
| `resource.job.cpu.user_time_sec` | float | `uctmut` | ミリ秒値を1000で除算 |
| `resource.job.cpu.system_time_sec` | float | `sctmut` | ミリ秒値を1000で除算 |

ランナー上でジョブ終了を検知した後、以下のコマンドを実行する。

```bash
LC_ALL=C pjstat --history -S --choose jid,st,sdt,elp,ec,sn,pc,nnumu,mmszu,uctmut,sctmut --data --delimiter $'\t' "${PJM_JOB_ID}"
```

`--data` オプションはPJMが提供する機械可読な整形済み出力であり、端末の表示桁位置や空白幅には依存しない。ヘッダー行とデータ行をタブ文字で分割し、`--choose` に指定した順序に従ってデータフィールドを読み取る。なお、`jid`（ジョブID）は照会キーとしてのみ使用し、環境変数との再照合や別キーへの保存は行わない。

`mmszu` については、PJMが表示するMiB単位の丸め値ではなく、括弧内に併記される厳密なバイト数を用いる。`elp` についても `DD hh:mm:ss (s)` の括弧内の秒数値 `s` を取得し、1秒未満が切り上げられたPJMの確定値として保存する。`sdt` には玄界のシステムタイムゾーンである `Asia/Tokyo`（+09:00）を付与し、たとえば `2026/07/30 12:34:56` を `2026-07-30T12:34:56+09:00` へと変換する。`uctmut` および `sctmut` の定義単位はミリ秒であるため、秒単位へ変換する。`pjstat` の実行が失敗した場合や出力項目が存在しない場合は、該当キーの値を空文字として送信する。なお、`st`、`ec`、`pc` 間の整合性検証やジョブ状態の独自再分類は行わない。

## 失敗時の扱い

- `PJM_JOBID` は `pjstat` の照会および `run` 識別子の生成に必須である。値そのものは `env.PJM_JOBID` にのみ一元保存する。
- 終了バッチの取得成否は、計算結果自体の成否判定に影響を与えない。
- 終了情報を取得できなかった場合でも、ローカル待機キューや一時スプールファイルは作成しない。
- `pjstat` の履歴保持期間が満了する前に、同一のワークフロー実行内で直ちに情報を取得する。

## 採用しない値

| 除外項目 | 除外理由 |
|---|---|
| スケジューラ側の終了時刻 | 開始時刻と経過時間から一意に算出可能であるため |
| ジョブID、ジョブ名、リソースグループ名、要求ノード数/ランク数、経過時間上限値 | PJM環境変数が `env.*` として網羅的に保存されるため、別名での重複を避けるため |
| 要求コア数 | PJM環境変数に含まれており、現状はMPIプロセス数とも一致するため |
| ノード別の会計情報 | ジョブ全体のマクロな比較には集約値で十分であるため |
| `pjstat` 通常表示の列情報 | 人間向けの固定幅テキスト表示の解析に依存することを避けるため |

## 参照仕様

- Fujitsu PJM `pjstat` command reference: <https://software.fujitsu.com/jp/manual/manualfiles/m220010/j2ul2466/02enz008/j2ul-2466-02enz0.pdf>
- Fujitsu HPC user guide, job status and statistics: <https://doc.cloud.global.fujitsu.com/lib/common/jp/hpc-user-manual/CheckJobStatus/>
- 玄界 リソースグループ仕様: <https://www.cc.kyushu-u.ac.jp/scp/en/usage/resource_groups/>
