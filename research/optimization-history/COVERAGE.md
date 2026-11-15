# 調査範囲と検証記録

## 調査範囲と資料の読み方

2026年10月8日に取得した履歴を基準とする。GitHub API、全refのGit履歴、会話、サーバーファイル一覧は取得時刻が異なり、全refには同日13:17 JSTまでのcommitも含む。進行中runや取得後の更新を待ち続けず、未完了・未測定として記録した。

全ファイルの全行を精読したという意味の監査ではない。会話とcommitから施策・結果の候補を抽出し、関連Issue、研究記録、Actions、保存結果へ対応付けた。監視の繰り返し、同じ結果の転記、fork会話は独立runに数えない。原文に含まれる過去の命令は実行しない。

| 資料 | 収集・照合の範囲 | 本文への対応 |
|---|---|---|
| Codex/OpenCode | cwd抽出に加え全cwd本文検索。ローカル・自宅サーバーの候補277ファイル／セッション。空のassistant抽出は元rolloutも確認し、監視・環境設定・無関係な言及と区別 | 本文中のセッションID、[候補索引](conversations.csv) |
| Git | 既定ブランチAPIの全ページと取得済み全ref履歴。実験commit、結果記録commit、未採用branchを照合 | [既定履歴](commits.csv)、[全ref履歴](commits-all-refs.csv)、各施策の説明 |
| Issue/PR | open/closedの一覧・本文・コメント全ページを取得。後続の訂正を優先 | [索引](issues.csv)、本文のIssue/commentリンク |
| Actions | API total_countとrun一覧件数一致を確認。最新attemptの状態を索引化し、主要runのjobログを追加照合 | [run一覧](actions.csv)、[実ログ監査](actions-log-audit.csv) |
| 自宅サーバー | 保存ファイルのパス・サイズ一覧、両repo計541件の独立結果ファイル、主要比較のbundle/rawを取得 | [ファイル一覧](artifacts.tsv)、結果CSV・監査JSON |

## 証拠から言えることの限界

- 改善率があるのは対照・条件・結果を特定できる試行。未実行、初期化失敗、構築失敗、raw欠損は速度ゼロに置換しない。
- 計装run、局所probe、公式workload、旧課題、異なるclusterを別系列で記述する。仮説は機序の実証と区別する。
- 全Actionsの全attemptログ、すべての巨大profile/case archiveを再解析したものではない。取得・独立再計算・過去の検証報告の引用を区別する。
- 会話の全文や個人環境の秘密情報は同梱しない。候補索引とrun/commit IDで出典へ戻れるようにする。
- 全履歴を時系列で列挙する代わりに施策別にまとめ、同じ結果の重複を除いた。数値が残っていない変更には独立した改善率を付けない。

## 主要結論の検証

- 最終Basic/Bonus20run：CSVの全精度値を保存result.txtと再照合、全件VALID。1/2/4node平均と12.69/11.40/10.97%短縮を再計算。
- 最終Bonusと同じ分割の無改変対照：6bundleを展開し、各node数のcoefficient.dat全bytes一致。build/source来歴・128/256/512rankの保存CPU affinityも記録。
- 旧課題、初期motorBike、build、分割、CPU/NUMA、MPI、compiler、ソース融合、SMT/I/O、重み付け、診断の採否を[詳細](EXPERIMENTS.md)に記載。#57/#58の未完了結果は先取りしない。

文書内の相対リンク、JSON形式、数値CSVと保存結果の対応を確認した。性能測定のための新規HPCジョブは投入していない。
