# 公式ルールと実装の対応

確認日: 2026-09-07。公式正本は[`tasks/2. OpenFOAM HPC Task Rules.md`](../tasks/2.%20OpenFOAM%20HPC%20Task%20Rules.md)、取得可能な公式HEADは`bc4e98fe6b96b6ed35120efe33a588ee441aae0b`。`tasks`という実際のsubmoduleを使用する（TASK.mdの`./task`はこの参照と解釈）。公式source repositoryには書き込まない。

9月4日の運営回答では、DP + label32と追加I/O flagsを許可し、Cdには公式の合否閾値がないことを確認した。discrawlのチームDiscord `現在のﾘﾎﾟｼﾞﾄﾘ`、2026-09-04の記録にも同じ回答とIssue #13/#26のcloseがある。回答の全文はこれらの正本に保持する。

| 要件 | 実装・証拠の所在 | 対応状況・検証 |
| --- | --- | --- |
| OpenFOAM.com v2512、倍精度、solverソース固定 | `scripts/build-openfoam.sh`、build sidecar、実行時provision validation | 設定と実際の実行ファイルを記録。別版・solver patchの過去実験は対象外 |
| 公式65M粗格子、固定fvSchemes/fvSolution | `benchmark/workload.json`、`benchmark/occDrivAerStaticMesh`、`source/workload` | メッシュを内容識別し、固定入力を保存 |
| 1/2/4ノードで40/80/150ステップ | workload、protocol、`benchmark/parse_result.sh` | 最終step、反復数、セル数、終了、平均step時間を検査 |
| decomposePar -constant、restore0Dir -processor、renumberMesh -constant -overwrite -parallel | `scripts/prepare-openfoam-case.sh`、`scripts/run-openfoam.sh`、各段階ログ | 分割結果は同cluster/build/分割条件のcacheを再利用し、準備ログも回収 |
| potentialFoam -initialiseUBCs -parallel、applyBoundaryLayer -ybl 0.0450244 -parallel、simpleFoam -parallel | `scripts/run-openfoam.sh`、段階別argv/log | 必須工程と既存switchを維持。追加I/O flagsは運営許可済み |
| 平均wall-clock秒/step（2ステップ目以降） | `results/result.txt`、`result.official` | 小さいほど高速。準備・profileの時間を通常benchのscoreへ混ぜない |
| 最終Cdとcoefficient.dat | `results/coefficient.dat`、`coefficient-source.json`、`result.aero_sanity` | 玄界bench/profileで回収・解析・永続保存・BigQuery一致を確認。数値範囲による独自失格判定なし。#22のGadi PBS実検証は障害復旧後に残る |
| 実使用decomposeParDict/controlDict/caseDefinition | `source/mesh`、Issue #27 | 玄界1/2/4ノードの実入力保存と成果物からの再解析を確認 |
| 同条件1/2/4ノードのscaling | `experiment_metrics.scaling`、Issue #24 | 同一e944313の実成果物で比較条件一致、表・172 UTF-8テキストファイルのexportを確認 |
| 採点クラスタと資源 | Gadi `normalsr`、4 CPUノード | 玄界は参考。Gadi/ASPIRE-2A障害中とのユーザー連絡に基づき玄界で検証 |
| 提出はテキスト、面接スライド | `submission/README.md` | mesh、processorディレクトリ、binaryを提出しない。Qwenと共通15〜20分の発表、10分Q&A。OpenFOAM評価は発表60%、性能40% |

玄界での成功はGadiのPBS/node-local動作や公式スコア達成の証拠とはしない。Gadi実検証の未実施を明示したうえで、共通処理とクラスタ固有部分のfixtureを確認する。

実行結果、ランク数比較、profileと観測された障害は[2026-09-07-official-e2e.md](2026-09-07-official-e2e.md)にまとめる。rawと比較用メトリクスの正本は、同文書から辿れるrun archiveとBigQueryに置く。

旧cavity3D、motorBike、v2606、FVOPSに基づく研究記録は過去の判断を追えるよう履歴として保存する。現行の科学条件・採点・最適化候補の根拠には使わない。
