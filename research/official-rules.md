# 大会公式ルールと本リポジトリ実装の対応関係

確認日: 2026-09-07。公式正本ドキュメントは [`tasks/2. OpenFOAM HPC Task Rules.md`](../tasks/2.%20OpenFOAM%20HPC%20Task%20Rules.md) であり、取得可能な公式HEADコミットは `bc4e98fe6b96b6ed35120efe33a588ee441aae0b` である。本リポジトリでは `tasks` という実体サブモジュールを参照する（TASK.md内の `./task` 表記もこの参照を指すと解釈する）。なお、公式ソースリポジトリへの直接の書き込みは行わない。

2026年9月4日の運営事務局からの回答において、倍精度（DP）＋32ビットラベル（label32）のビルド構成および追加のI/Oフラグ（`-hostRoots`, `-ioRanks` 等）の利用が正式に許可され、また抗力係数（$C_d$）に対して公式の厳密な合否判定閾値は設けないことが確認された。チームDiscordの `現在のﾘﾎﾟｼﾞﾄﾘ` チャンネルにおける2026-09-04の記録にも同内容の回答とIssue #13および#26のクローズ経緯が記録されている。回答の全文はこれらの正本記録に保持する。

| 公式要件 | 本リポジトリにおける実装・証拠の所在 | 対応状況および検証実績 |
| --- | --- | --- |
| OpenFOAM.com v2512、倍精度、ソルバーソースコード固定 | `scripts/build-openfoam.sh`、ビルドサイドカー、実行時プロビジョニング検証 | ビルド設定および実際に使用された実行バイナリを厳密に記録。他バージョンやソルバーパッチを用いた過去の実験は採点対象外として明確に区別 |
| 公式65M粗格子メッシュ、固定 `fvSchemes` / `fvSolution` | `benchmark/workload.json`、`benchmark/occDrivAerStaticMesh`、`source/workload` | メッシュのSHA-256ハッシュにより内容の一致を識別し、変更禁止の固定入力辞書を保存 |
| 1/2/4ノード環境で40/80/150反復を実行 | `benchmark/workload.json`、実行プロトコル、`benchmark/parse_result.sh` | 最終反復ステップ、反復回数、セル数、正常終了、平均ステップ時間を自動検査 |
| `decomposePar -constant`、`restore0Dir -processor`、`renumberMesh -constant -overwrite -parallel` | `scripts/prepare-openfoam-case.sh`、`scripts/run-openfoam.sh`、各ステージログ | 分割結果は同一クラスタ・ビルド・分割条件のキャッシュを再利用し、全準備工程のログも確実に回収 |
| `potentialFoam -initialiseUBCs -parallel`、`applyBoundaryLayer -ybl 0.0450244 -parallel`、`simpleFoam -parallel` | `scripts/run-openfoam.sh`、ステージ別引数（argv）およびログ | 必須工程および既存スイッチを維持。追加I/Oフラグ（分散ルート等）は運営事務局の許可を取得済み |
| 評価指標: 平均wall-clock秒/step（2ステップ目以降） | `results/result.txt`、BigQuery `result.official` | 小さいほど高速と評価。前処理時間やプロファイル計測の時間を通常ベンチマークのスコアに混入させない |
| 最終 $C_d$ の記録と `coefficient.dat` の提出 | `results/coefficient.dat`、`coefficient-source.json`、BigQuery `result.aero_sanity` | 玄界の通常ベンチマークおよびプロファイル実行において回収・解析・永続保存・BigQuery一致を確認。独自閾値による失格判定は設けない。Issue #22（GadiにおけるPBS実機検証）はクラスタ障害復旧後の後続タスクとする |
| 実際に使用した `decomposeParDict`、`controlDict`、`caseDefinition` | `source/mesh`、Issue #27 | 玄界1/2/4ノードにおける実入力ファイルの保存と成果物からの完全な再解析を確認済み |
| 同一条件における1/2/4ノードのスケーリング性能 | `experiment_metrics.scaling`、Issue #24 | 同一コミット `e944313` の実成果物を用いて比較条件の一致を検証し、スケーリング表および172件のUTF-8テキストファイルのエクスポートを確認 |
| 採点対象クラスタおよび計算資源 | NCI Gadi（`normalsr`キュー）、4 CPUノード | 玄界は参考・先行開発環境。Gadi/ASPIRE-2A障害中との連絡に基づき玄界にてE2E検証を先行実施 |
| 提出物仕様（テキストログ一式、面接プレゼンテーション） | `submission/README.md` | メッシュデータ本体、`processor*` ディレクトリ、バイナリは提出物に含めない。Qwenタスクと合わせた15〜20分の発表および10分の質疑応答。配点は発表60%、性能評価40% |

玄界における完走実績は、GadiのPBS環境やノードローカルストレージ（$PBS_JOBFS）での動作、および公式スコア達成の直接の証拠とはみなさない。Gadi実機検証が未実施である旨を明記した上で、共通処理とクラスタ固有処理のフィクスチャを慎重に確認する。

実行結果、ランク数比較、プロファイル解析結果、および観測された実障害の詳細は [2026-09-07-official-e2e.md](2026-09-07-official-e2e.md) にまとめている。生データおよび比較用メトリクスの正本は、同文書から参照可能な実行アーカイブおよびBigQueryに保存されている。

なお、旧cavity3D、motorBike、v2606、およびFVOPS指標に基づく過去の研究記録は、設計判断の経緯を追跡できるよう歴史的資料として保存している。これらは現行の物理的条件、採点基準、最適化候補の採否判断の直接の根拠としては用いない。
