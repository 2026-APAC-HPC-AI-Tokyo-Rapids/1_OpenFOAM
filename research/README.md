# OpenFOAM 調査・作業記録

再現手順と提出物は [提出ガイド](../submission/README.md)、競技条件は [公式ルールとの対応](official-rules.md)から参照してください。

| 資料 | 内容・時点 |
| --- | --- |
| [最適化履歴](optimization-history/README.md) | 2026-10-08時点の調査。採用・不採用・失敗、コード差分と根拠の索引 |
| [Issue #35 引き継ぎ](2026-09-29-issue35-handoff.md) | 2026-09-29時点の計画・仮説。後続の判断は最適化タスクと各Issueを参照 |
| [キャッシュ帯域の校正](roofline-cache-calibration-20261026/README.md) | 2026-10-26のASPIRE-2A単一ノード測定。source・PBS・raw出力・集計を収録 |
| [ビルド性能](build-performance/README.md) | ビルド・キャッシュ・ツールチェーンの調査 |
| [実行性能](runtime-performance/README.md) | 通信・配置・ソルバーの調査 |
| [作業計画](../TASK.md) | 作業のチェックリスト |
| [ASPIRE作業記録](../TASK_2a.md) | ASPIRE環境・計画の記録 |
| [最適化タスク](../TASK_2a_optimization.md) | 最適化の進捗と判断の履歴 |

過去の引き継ぎや計画は記載日の記録です。測定値の来歴は元コミット・Actions・scheduler出力を保持し、推定や仮説を通常計測の結果として扱いません。
