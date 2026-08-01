# 実行識別・ソースコード収集モジュール

## モジュール境界

実装名は `run_source` とする。実行名、実行ライフサイクル、Git checkout、
GitHub Actionsとの対応を扱う。開始バッチと終了バッチの2回だけ呼び出す。

- 開始バッチは最初の処理を起動する前に送る。
- 終了バッチはpipelineの全処理が終わった直後に送る。
- 取得できない補助メトリクスがあっても実験は開始する。
- 強制終了では終了バッチが存在しないことを許容する。

## `run` の生成規則

GitHub ActionsからPJMジョブを実行する現在の経路では、次の文字列を使う。

```text
openfoam-<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT>-<PJM_JOBID>
```

Actions投入処理は少なくとも`GITHUB_RUN_ID`、`GITHUB_RUN_ATTEMPT`、
`GITHUB_REPOSITORY`、`GITHUB_SHA`をPJM job環境へ明示的に渡す。PJMが設定する
`PJM_JOBID`とともに、platform moduleが元の名前の`env.*`として保存する。

手動投入では次を使う。`started_at_utc` は `YYYYMMDDTHHMMSSffffffZ` とする。

```text
openfoam-manual-<PJM_JOBID>-<started_at_utc>
```

run名の生成に必要な構成要素だけは、実行を識別できないため必須とする。

## 確定メトリクス

| キー | 論理型 | 取得時点 | 正となる取得元 | 取得方法 |
|---|---|---|---|---|
| `run.started_at` | timestamp | 開始時 | collector | UTC現在時刻をISO 8601で生成 |
| `run.finished_at` | timestamp | 終了時 | collector | UTC現在時刻をISO 8601で生成 |
| `run.elapsed_sec` | float | 終了時 | collector | `time.monotonic_ns()` の開始・終了差 |
| `run.outcome` | enum | 終了時 | pipeline supervisor | 下記の固定語彙へ正規化 |
| `run.exit_code` | int | 終了時 | pipeline supervisor | 最初に失敗したstageのreturn code。全成功は`0` |
| `run.signal` | int | signal終了時だけ | Python `subprocess` return code | 負のreturn codeの絶対値 |
| `run.command` | string | 開始時 | 起動用引数列 | argvを`shlex.join()`したshell表現 |
| `git.repository` | string | 開始時 | Git | `GITHUB_REPOSITORY`が環境にない場合だけ`git remote get-url origin` |
| `git.commit` | string | 開始時 | Git | `GITHUB_SHA`が環境にない場合だけ`git rev-parse --verify HEAD` |
| `git.is_dirty` | bool | 開始時 | Git | `git status --porcelain=v1 --untracked-files=normal` が空か |

Actions実行ではrepositoryとcommitは`env.GITHUB_REPOSITORY`と`env.GITHUB_SHA`から
分かるため、`git.repository`と`git.commit`を送らない。手動実行で対応する環境変数が
ない場合だけ、Gitを正本とするfallbackキーを送る。`git.is_dirty`は環境変数から
分からないため、repositoryが利用できる全runで送る。

`run.outcome` の語彙は次に固定する。

```text
succeeded
failed
cancelled
```

## 読み取り規則

- Gitコマンドは `LC_ALL=C`、対象repositoryを `-C` で明示して実行する。
- Gitコマンドが値を返した場合、その先頭行を使う。失敗時は対象キーを空文字にする。
- `git.is_dirty` だけは複数行出力を値へ保存せず、空か否かだけを使う。
- supervisorが実際に渡す配列を使い、`shlex.join()`で復元可能なshell表現にする。
- 日時のwall clockと経過時間用のmonotonic clockを混用しない。

## 採用しない値

| 値 | 理由 |
|---|---|
| branch、tag | commitを一意に定めず、再現性の主識別子にならない |
| `git.diff_hash` | untracked fileを含む完全なdirty状態を一意に表せない |
| `github.*` | `GITHUB_*`環境変数を全件`env.*`へ保存するため重複する |
| GitHub run URL | repositoryとrun IDから後で作れる派生値 |
| commandを1本の文字列にした値 | 引数境界を失い、複数値を1つのvalueへ詰め込む |

## 参照仕様

- Git `rev-parse`: <https://git-scm.com/docs/git-rev-parse>
- Git `status --porcelain`: <https://git-scm.com/docs/git-status#_porcelain_format_version_1>
- GitHub Actions既定環境変数:
  <https://docs.github.com/actions/reference/variables-reference>
