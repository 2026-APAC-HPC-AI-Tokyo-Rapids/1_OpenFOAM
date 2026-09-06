# 公式65Mケースの玄界E2Eとランク数比較

## 結論と範囲

玄界4ノードは448ランクを維持する。480ランク候補は各2回の比較で平均step時間が6.95%増え、今回の条件では採用する根拠がなかった。OpenFOAMのsolverソース、公式物理条件、固定反復数は変更していない。

これは玄界での参考検証であり、Gadi/ASPIRE-2Aの公式スコアではない。両採点環境は障害中とのユーザー連絡に基づき実行していない。公式要件との対応は[official-rules.md](official-rules.md)、進捗と障害の記録は[Issue #27](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/27)を参照。

## 来歴と正本

- 基準ビルド: [Actions 34051411071](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34051411071)、build定義 `ad25caf3f16ee186d42497e098913495061453a2`。
- OpenFOAM.com v2512、DP/label32、Intel compiler/MPI、公式65,334,765セル、Scotch、uncollated。実際のコンパイル設定、実行ファイル、MPIは各runのbuild sidecarとprovision validationが正本。
- raw成果物: home-lab `/hdd_raid/samba/net_share/openfoam-artifacts/<Actions id>/genkai/`。固定bundleのmanifestを検証して以下の結果を再解析した。
- 比較用メトリクス: BigQuery `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_metrics` の `result.official` / `result.aero_sanity`。実ログ・Cdとの一致を確認した。計算ノードへBigQuery資格情報は渡していない。

## 同一コミットの1/2/4ノード系列

基準commitは `e944313d62fd56744e7f36b34a0f490c071a07cb`。build/MPI/workload/mesh/準備スクリプト/計装と、ノード依存値を除く実使用入力の一致を正式scaling CLIで確認した。

| ノード | ranks | steps | 平均秒/step | 最終Cd | Actions |
| --- | --- | --- | --- | --- | --- |
| 1 | 120 | 40 | 8.159013426102565 | 0.43590741346883244 | [34052149354](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34052149354) |
| 2 | 240 | 80 | 4.129346024594936 | 0.33852274430525320 | [34052151091](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34052151091) |
| 4 | 448 | 150 | 1.985350879583894 | 0.28455000886604298 | [34052897447](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34052897447) |

全件公式`VALID`。平均は最初のstepを除いたwall-clock時間で、準備やprofileの時間ではない。1ノードはshm、複数ノードはshm:ofi。反復数とrank数が異なるため、同一の総仕事量を処理するstrong-scaling試験とは区別する。Cdに公式の合否閾値はなく、referenceとの比較はsanity確認に限る。

`uv run --project experiment-metrics python -m experiment_metrics.scaling` に3件のURLとartifact directory、`--output-dir`を指定し、172 UTF-8テキストファイルを生成した。必須ログ、結果、実入力、来歴とbinary非混入を確認。再生成方法は[submission/README.md](../submission/README.md)。表の標準偏差は測定対象step間のばらつきであり、run間のばらつきではない。

## 448対480ランク

候補commit `32ae88c01338e9f80ae0002157ea7aff1c7b1bba` は基準e944313の子で、4ノードの使用rank数を448から480へ変えた。build、MPI、メッシュ、150step、準備条件を固定し、既存のランク配置規則に従う112対120 ranks/nodeを比較した。

| ranks | 1回目の平均秒/step | 2回目の平均秒/step | 2run平均 | Actions |
| --- | --- | --- | --- | --- |
| 448 | 1.985350879583894 | 1.978047149865772 | 1.981699014724833 | [34052897447](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34052897447), [34052963885](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34052963885) |
| 480 | 2.103996287375839 | 2.134978052127516 | 2.1194871697516775 | [34052154891](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34052154891), [34052965770](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34052965770) |

各条件の2回で最終Cdは一致した。480ではstep時間のばらつきも大きかった。ただし比較4runは下記の修正前hardware取得障害に該当し、ノードごとのhardware観測が欠けるため、ノード環境の同一性は未検証である。これは2回ずつの観測であり、全クラスタ・全配置で480が必ず不利という主張ではない。差の原因を単一ランクのprofileだけで断定しない。

候補はmainへ取り込まず、`archive/genkai-4n-480r-20260907`タグへ履歴を保存して一時ブランチを削除した。

## 段階別時間とprofile

新規ビルドを含む初回448run [34051411071](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34051411071)（ad25caf、`r-6b6de8ca2866ebd6b628e598652d2bbe`、上記e944313の比較系列とは別）では、PJM実行465秒のうちsolver stageが321.9秒、case配置が72.3秒、renumberが11.8秒、potentialFoamが12.7秒、applyBoundaryLayerが7.1秒だった。公式149step合計296.25秒とsolver stage全体は異なる指標。新規build、mesh準備、queueもworkflow全体の時間へ影響しており、全所要時間だけからsolverのボトルネックを推測しない。

4ノードprofile [34052899061](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34052899061) はrank0へ60秒のVTune hotspots収集を接続し、221関数・報告CPU時間57.27秒を取得した。GaussSeidel平滑化17.60%、行列残差11.18%、Allreduce7.80%、行列積5.70%、Waitall3.11%。これは1ランクのサンプル内訳であり、全rank・全実行の割合ではない。profileのstep時間を上記bench比較には使用しない。

warmupの時刻0 coefficientは`profile/raw/warmup-postProcessing`へ退避し、正式150stepの`results/coefficient.dat`と分離した。ParaViewには448分割のmeshと保存済み時刻0のfieldがある。noWrite設定のため最終150stepのfieldではなく、最終値の検証はsolverログとCdによる。

## 実障害と修正後検証

- `b9960e5`: 利用可能なrank/toolchain/content別case cacheでも準備ジョブを投入していたため、login側の既存identity確認でhit時の投入を省略。[回帰34053564239](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34053564239)は成功。
- `c62a364`: MPIへ固定済みのPATHが古いOS Python3.6を選び、複数ノードのhardware取得に失敗。配備済みinterpreterを明示し、失敗ログも固定bundleへ保存する。[2ノードprofile34054205977](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34054205977)でminimal/profileの両段階がexit0、両nodeのraw SHAとBigQuery一致を確認。34 raw memberと18 profile.hardware factsも照合した。solverは80step VALID、Cdは0.33852274430525320。修正前runのhardware記録欠落は遡って成功扱いにしない。
- `c1017ca`: profile転送がrunner内にない旧設定ファイルを要求して失敗。既存のクラスタ接続ラッパーへ移行。取得済み出力は残り、一時回収Actionsで計算を再実行せず復旧する。

4ノードprofileの保存は[回収Actions34054785959](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34054785959)で成功。固定成果物、VTune、10,519,515,667 bytesのParaView archiveを検証し、元run directoryと転送stagingの削除を確認した。2ノードprofileの大容量回収も[34055572506](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/34055572506)で成功。元の2件のActionsは転送失敗の履歴として残し、計算を再投入せず回収を別Actionsへ記録した。復旧専用の一時workflowは役割を終えたため削除した。

通常bench8件はActions全体で成功し、profile2件も上記の復旧を含め保存まで完了した。#21/#23/#24/#25は完了。#22のGadi PBS実機確認のみ、障害復旧後の後続事項として残す。
