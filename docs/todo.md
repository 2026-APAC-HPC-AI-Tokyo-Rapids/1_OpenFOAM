# todo

- オーバーエンジニアリングはしない
- 実験内容と部分的な結果と考察を`docs/`に残す(bigqueryの内容をすべて出したりはしないが、参照できるようにしておく)
- 現行課題は`tasks/`、旧課題は`old_tasks/`を正本とし、旧課題の性能結果を流用しない
- 提出先はASPIRE-2A、玄界は練習用とする。Gadiは使用しない

## 1. ASPIRE-2Aの自動実験環境

- [ ] home-lab runnerからASPIRE-2Aへ非対話で接続できるようにする
- [ ] ASPIRE-2Aのmodule、PBS、PALS/Cray MPICH、scratch、quota、計算ノードを実機で確認する
- [ ] `platforms/aspire2a/`と`.github/workflows/aspire2a.yml`を追加する
  - 共通`OpenFOAM` workflowから手動実行と`[cluster:aspire2a]`で起動する
  - 1/2/4ノード、通常計測/profile、ビルド再利用を既存クラスタと同じ入口で扱う
  - ビルド、ケース、キャッシュ、成果物は他クラスタと共有しない
- [ ] 安価なPBSジョブで投入、待機、終了判定、ログ回収、後片付けを確認する
- [ ] 公式判定からartifact回収、BigQuery送信までをE2Eで自動化する
  - [収集する情報](bigquery-metrics.md)に従う
  - BigQuery認証情報は計算ノードへ渡さない

## 2. ベースライン

- [ ] 現行課題のAllrun、固定入力、変更可能項目、評価方法を理解する
- [ ] ASPIRE-2Aの`openfoam/2512`を使い、まず1ノードで公式ケースを完走する
- [ ] 同じ条件を複数回実行してrun間ノイズを測る
- [ ] 同一条件で1/2/4ノードの基準系列を取得する
  - 公式`VALID`、平均秒/step、$C_d$、全準備工程、実使用入力を確認する
  - 40/80/150反復は計算量が違うため、通常のstrong scalingとは呼ばない

## 3. 計測と最適化

- [ ] 4ノード実行をprofileし、計算、MPI通信、負荷不均衡、メモリ、I/Oのどれが支配的か調べる
- [ ] rank数と配置、領域分割、MPI設定、データ配置、ビルド設定の順に候補を検討する
- [ ] 一度に主要因を1つだけ変え、実験ごとに追跡可能なcommitを作る
- [ ] 候補と対照を複数回測り、run間ノイズを超えた改善だけを採用する
- [ ] 実験の仮説、条件、結果、採否はIssueと`docs/`の短いレポートに残す

## 4. 提出

- [ ] 最終条件でASPIRE-2Aの1/2/4ノード系列と再現runを取得する
- [ ] 必須ログ、入力辞書、ビルド情報、`coefficient.dat`をテキストで揃える
- [ ] 基準との差、run間分布、ボトルネック、採用・不採用の理由をスライドにまとめる
- [ ] 不要なバイナリ、一時workflow、残留PBSジョブ、クラスタ上の一時データを確認する

## リンク集

- ISC26 OpenFOAM virtual: https://hpcadvisorycouncil.atlassian.net/wiki/spaces/HPCWORKS/pages/3700260877/Getting+Started+with+OpenFOAM+for+ISC26+SCC+Virtual+Part
- ISC26 OpenFOAM in person:https://hpcadvisorycouncil.atlassian.net/wiki/spaces/HPCWORKS/pages/4314791937/Getting+Started+with+OpenFOAM+task+for+ISC26+SCC+In-Person+Part
- コンテストサイト: https://www.hpcadvisorycouncil.com/events/2026/APAC-AI-HPC/
- The first OpenFOAM HPC Challenge: https://arxiv.org/html/2603.27565v1
- メッシュのリポジトリ: https://develop.openfoam.com/committees/hpc/-/tree/develop/incompressible/simpleFoam/occDrivAerStaticMesh
- 65M mesh: https://zenodo.org/records/15012221/files/polyMesh_65M.tar.gz?download=1
