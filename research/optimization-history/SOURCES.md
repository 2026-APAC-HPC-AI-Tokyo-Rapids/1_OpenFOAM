# 1_OpenFOAM 最適化履歴の証拠索引

実装の説明は[コード変更の追跡](CODE_CHANGES.md)、変更前後の原文と完全コミットSHAは[差分原本の索引](code-diffs/README.md)を参照。

取得日: 2026年10月8日。[総括](README.md)と[調査範囲・検証記録](COVERAGE.md)を参照。

## 取得した資料

| 資料 | 件数と範囲 | 索引 |
| --- | --- | --- |
| GitHub Issue・PR一覧 | 58件、open/closed両方、本文取得済み | [issues.csv](issues.csv) |
| Issueコメント | 346件、全ページ取得済み | 各Issueのリンク先 |
| Actions | 942 run、APIのtotal_countと一致。再実行は各runの最新attempt | [actions.csv](actions.csv) |
| GitHub既定ブランチのコミット | 581件、全ページ取得済み | [commits.csv](commits.csv) |
| 全ローカル・取得済みremote refsのGit履歴 | git fetch後の全refを別途取得 | [全ref索引](commits-all-refs.csv) |
| 自宅サーバーの保存ファイル | 3064ファイル、パスとサイズ | [artifacts.tsv](artifacts.tsv) |
| 既存research・発表用CSV | origin/mainを読み取り専用取得 | GitHub origin/main |
| Codex・OpenCode履歴 | ローカルCodex199セッション、OpenCode7セッションを対象リポジトリ・関連作業ツリーから抽出。両リポジトリ合計 | 個人履歴のため全文はリポジトリに複製しない |

自宅サーバーの正本は `/hdd_raid/samba/net_share/openfoam-artifacts/`。ローカルの `/mnt/net_share/openfoam-artifacts/` からも参照できる。サーバーへ読み取り専用SSHで接続し、両リポジトリ合計541件の `result.txt`・`score.json`・`score-original.json`・`RESULT.md` を取得した。アーカイブ内だけにある結果はこの541件に含まれない。

## 解釈上の注意

- Actions successは性能改善の証明ではない。公式条件・実入力・数値検証・非計装ログと照合する。
- Actions failureでもsolverが完走した例がある。接続・回収失敗と計算失敗を分ける。
- GitHub artifactは自宅サーバー退避後に削除される運用がある。APIの空一覧だけでは証拠消失を意味しない。
- 進行中runは取得時点の状態。研究の結論をその後の未完了実験まで拡張しない。
- 会話の提案や実装予定を実測済みの結果として扱わない。古い引き継ぎの採否は後続Issueで更新されうる。

## 照合の進捗と限界

総括・失敗試行の本文、サーバー会話の抽出、主要比較の保存結果照合を実施済み。全refの実験・結果記録を点検し、会話から漏れていた初期試行も補った。全Actionsの全attemptログや、全サーバーアーカイブを展開して読了したとの主張ではない。

会話候補は[conversations.csv](conversations.csv)で元ファイルまで辿れる。forkされたCodexログは先頭metadataに親IDが残る場合があるため、`file_session_id`と`metadata_session_id`を分けた。候補索引の件数は独立した実験数ではなく、監視・提案・無関係な言及を含む。個人会話の原文はリポジトリへ複製しない。

## 追加照合

2026年10月8日、cwdによる抽出に加えて本文も検索した。キーワード一致はローカルCodex261・OpenCode7、自宅サーバーCodex8・OpenCode1の合計277履歴ファイル／セッション候補。これは候補集合で、無関係な言及や本調査自身も含みうる。全件を最適化の証拠とみなす数字ではない。原文は個人履歴の保管先に保持し、必要な発言の役割・行番号と実験結果を照合する。

最終比較20 runについて、[final-results.csv](final-results.csv)の時間と保存済み`result.txt`の全精度値・`STATUS: VALID`の一致を確認した。rawへのパスも同CSVに記載した。この検査だけでは全過去試行の網羅性やCdファイルのビット一致を独立証明しない。

主要Actionsの実ログを追加取得し、[確認箇所とログSHA256](actions-log-audit.csv)を記録した。ログ上のPBS終了・artifact回収と、別の結果ファイルに記録された性能値を区別している。

- [final-bundle-audit.json](final-bundle-audit.json): 自宅サーバー保存ファイルを2026年10月8日に直接読み、ハッシュと設定・結果を照合した追加監査。
