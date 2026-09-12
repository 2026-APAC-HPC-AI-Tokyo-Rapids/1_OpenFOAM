# 実行識別・ソースコード収集モジュール

## モジュール境界

実装上の識別名は `run_source` とする。本モジュールは、実行識別名、実行ライフサイクル、Gitチェックアウト状態、およびGitHub Actionsとの対応関係を管理する。呼び出しは、開始バッチと終了バッチの計2回のみ行う。

- 開始バッチは、最初の処理工程を起動する直前に送信する。
- 終了バッチは、パイプラインの全処理が完了した直後に送信する。
- 一部の補助メトリクスが取得できない場合であっても、計算実験自体は開始する。
- 外部シグナル等による強制終了時は、終了バッチが存在しない状態を許容する。

## `run` 識別子の生成規則

GitHub ActionsからPJMジョブを投入する標準経路では、以下のフォーマットで識別子を生成する。

```text
openfoam-<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT>-<PJM_JOBID>
```

Actions側の投入スクリプトは、少なくとも `GITHUB_RUN_ID`、`GITHUB_RUN_ATTEMPT`、`GITHUB_REPOSITORY`、`GITHUB_SHA` をPJMジョブ環境へ明示的に渡す。PJMが自動設定する `PJM_JOBID` とともに、プラットフォームモジュールが元の環境変数名そのままの `env.*` として保存する。

手動実行（直接投入）時は以下のフォーマットを使用する。なお、`started_at_utc` は `YYYYMMDDTHHMMSSffffffZ` 形式とする。

```text
openfoam-manual-<PJM_JOBID>-<started_at_utc>
```

実行識別子の生成に必要な最小限の構成要素のみ、実行の一意特定に不可欠であるため必須要件とする。

## 確定メトリクス

| キー | 論理型 | 取得時点 | 正となる取得元 | 取得方法 |
|---|---|---|---|---|
| `run.started_at` | timestamp | 開始時 | コレクター | 現在のUTC時刻をISO 8601形式で生成 |
| `run.finished_at` | timestamp | 終了時 | コレクター | 現在のUTC時刻をISO 8601形式で生成 |
| `run.elapsed_sec` | float | 終了時 | コレクター | `time.monotonic_ns()` の開始・終了差分（秒換算） |
| `run.outcome` | enum | 終了時 | パイプライン監視処理 | 後述の固定語彙へ正規化 |
| `run.exit_code` | int | 終了時 | パイプライン監視処理 | 最初に失敗したステージの終了コード（全成功時は `0`） |
| `run.signal` | int | シグナル終了時のみ | Python `subprocess` 終了コード | 負の終了コードの絶対値 |
| `run.command` | string | 開始時 | 起動用引数列 | argvを `shlex.join()` で結合したシェル表現 |
| `git.repository` | string | 開始時 | Git | `GITHUB_REPOSITORY` が環境変数に存在しない場合のみ `git remote get-url origin` |
| `git.commit` | string | 開始時 | Git | `GITHUB_SHA` が環境変数に存在しない場合のみ `git rev-parse --verify HEAD` |
| `git.is_dirty` | bool | 開始時 | Git | `git status --porcelain=v1 --untracked-files=normal` の出力が空か否か |

Actions実行時は、リポジトリおよびコミットは `env.GITHUB_REPOSITORY` および `env.GITHUB_SHA` から特定できるため、`git.repository` および `git.commit` は送信しない。手動実行等で対応する環境変数が存在しない場合に限り、Gitコマンドを正本とするフォールバックキーを送信する。一方、作業ツリーの変更有無（`git.is_dirty`）は環境変数からは判別できないため、Gitリポジトリが参照可能なすべての実行で送信する。

`run.outcome` の語彙は以下に固定する。

```text
succeeded
failed
cancelled
```

## 読み取り規則

- Gitコマンドは `LC_ALL=C` を指定し、対象リポジトリを `-C` オプションで明示して実行する。
- Gitコマンドが複数行を出力した場合、先頭行を採用する。コマンド失敗時は該当キーを空文字とする。
- `git.is_dirty` については出力テキストをそのまま保存せず、出力が空か否かの真偽値のみを保持する。
- プロセス監視処理が実際に渡した引数配列（argv）を用い、`shlex.join()` によって完全復元可能なシェル表現文字列を生成する。
- 実時刻（wall-clock time）と経過時間計測用の単調増加クロック（monotonic clock）を混用してはならない。

## 採用しない値

| 除外項目 | 除外理由 |
|---|---|
| ブランチ名、タグ名 | コミットハッシュを一意に確定できず、再現性の主識別子として不適であるため |
| `git.diff_hash` | 未追跡ファイルを含む完全なダーティ状態を一意かつ可逆に表現できないため |
| `github.*` | `GITHUB_*` 環境変数を網羅的に `env.*` へ記録するため重複となるため |
| GitHub Actions実行URL | リポジトリ名と実行IDから後から一意に導出可能な派生値であるため |
| コマンド引数の要素別キー展開 | 単一の実行条件を多数のレコードへ過剰に細分化してしまうため |

コマンド引数は `shlex.join()` による復元可能な単一の文字列（STRING）として保存する。これは、配列構造を要素ごとの個別メトリクスへ展開しないというBigQueryテーブル設計方針に準拠したものである。

## 参照仕様

- Git `rev-parse`: <https://git-scm.com/docs/git-rev-parse>
- Git `status --porcelain`: <https://git-scm.com/docs/git-status#_porcelain_format_version_1>
- GitHub Actions既定の環境変数: <https://docs.github.com/actions/reference/variables-reference>
