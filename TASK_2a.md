NSCC公式資料、ASPIRE 2Aの実環境、HPE Cray Programming Environment、AMD AOCC/AOCL/uProfの公式資料、このリポジトリの履歴とActions、およびBigQuery Connected Sheetsから得られる情報をもとに、ASPIRE 2AでOpenFOAMを安全かつ再現可能にビルド・実行・計測できるように、このプロジェクトを更新してください。
以下にチェックマーク付きのTODOリストを随時更新しつつ作業を完遂してください。作業中に必要となるサブ計画と検証ゲートは、得られた事実に基づいてインクリメンタルに作成してください。
ASPIRE 2Aでは、PBS、PALS、Cray MPICH、Slingshot対応のCray Programming Environmentを基盤とし、AMD EPYC Milan向けに構成してください。GNUを比較基準として維持し、AOCCはGNU版とのビルド互換性、数値正当性、性能を実測して採否を決めてください。AOCLはASPIRE 2Aの標準構成へ一括導入して構いません。実際に利用されたライブラリと数値・性能への影響を記録し、Cray側ライブラリとの競合や意図しないlinkを残さないでください。Intel MPI、Intel VTune、MKLおよびIntel固有の実行設定をASPIRE 2A経路へ持ち込まないでください。マシンのカタログスペックから導ける理論値からどの程度乖離があるのかも考えつつ最適化を行ってください。
ASPIRE 2AのprofileにはAMD uProfを使用し、solverとは独立した収集状態、構造化メトリクス、検証済みraw artifactを保存してください。ビルドと計算はPBS計算ノード上で行い、source、build、case、run、profileのidentityと実際のmodule、compiler、MPI、CPU targetを追跡できるようにしてください。
実装と計測経路を完成させるだけでなく、ASPIRE 2Aで実際に1/2/4ノードのベンチマークとprofileを行い、得られたボトルネックに基づいてOpenFOAM設定、ビルド設定、実行方法およびこのリポジトリのコードを改善してください。改善前後を同一条件の複数runで比較し、数値正当性を維持した改善だけを採用してください。公式採点対象となる4ノードまで検証し、途中の結果から自分で進められる範囲の最適化を進めてください。
2026-09-20に`origin/main`へ追加された`1dcf3bf`、`e61d0e2`、`156eb75`、`ef799c6`、`ecac8db`はプロジェクト所有者が作成したものと確認できず、未署名です。公開済み履歴は書き換えず、変更内容と実行境界を監査したうえで修正してください。既存のGenkai/Gadi経路、過去の計測結果および成果物を維持してください。
BigQuery計測スキーマと次のConnected Sheetsを一体の成果物として扱い、ASPIRE 2Aのcluster、toolchain、compiler、MPI、AOCL使用条件、profile tool、node/rank構成、実行結果および主要性能値を既存クラスタと比較できるようにしてください。BigQuery側を変更した場合は、データソース、抽出範囲、表示表、式および見出しも整合させ、既存の行、式、表示および書式を失わないようにしてください。
private-reference-omitted
このタスクでは、ファイル調査、静的テスト、SSHアクセスによる診断、および上記Connected Sheetsの読み取りと必要な編集を許可します。commit、push、Actions起動、PBSジョブ投入も行って構いません。全ての権限を付与します。`[cluster:aspire2a]`による自動実行も許可します。
公式Slack(2026apachpcai-vtf5729.slack.com),tomokazu@tomokazu-ubuntu-server:/home/tomokazu/.local/bin/discrawl,公式リポジトリ(./task)や、過去のCodexの会話履歴から得られる情報も作業の参考としてください。
tomokazu@tomokazu-ubuntu-server:/home/tomokazu/actions-runnerにあるself-hosted runnerの設定を、Actionsの仕様とクラスタ接続の確認に使用してください。
ASPIRE 2Aは復旧しています。Gadiはダウンが継続しているため、Gadiでの新規実機検証を前提にせず、既存経路を静的テストと過去の証拠から退行確認してください。
既存コードの偶然の複雑さや重複も整理してください。ただし抽象化や機能を目的化せず、YAGNI原則に従い、正確で外科的な、無駄のない、テスト可能で読みやすいコードを維持してください。
今までも行ってきたように、作業をGitHubのIssue・Sub Issueとして記録し、進捗と検証結果を定期的にIssueのコメントへ追加してください。Issue本文とコメントは日本語で作成してください。日本語の作成は`agy`コマンド経由でGemini 3.8 Flashへ依頼し、`agy`には内容を英語で伝えたうえで、Gemini側で自然な日本語へ翻訳して出力するよう明記してください。
最適化においては、闇雲にコードを書き換えて当たりはずれを見るのではなく、プロファイリングに基づき、遅い個所を、演算量が大きいのか、メモリ帯域がボトルネックなのか、同期待ちが生じているのかなど、原因の根本を明確にする姿勢を忘れないでください。
このマシン上で追加したいパッケージ等ある場合は、tmux session:rootを用いてください。また、Pythonならuv,TS/JSならbunが使えます。

## 作業チェックリスト

- [ ] 未検証のASPIRE 2A変更を監査し、リポジトリの慣行に沿わないコードを整理する。
- [ ] ASPIRE 2A推奨環境に沿ってビルド、実行、cache、成果物およびidentityの境界を完成させる。
- [ ] GNU版とAOCC版のビルド、数値正当性および性能を比較し、採用するtoolchainを決定する。
- [ ] AOCLをASPIRE 2Aの構成へ導入し、link、ライブラリ競合、数値差および性能差を検証する。
- [ ] AMD uProfの収集、解析、構造化メトリクスおよびraw artifactの保存経路を完成させる。
- [ ] ASPIRE 2Aの1/2/4ノードでベンチマークとprofileを実行し、ボトルネックに基づくコードおよび実行構成の改善を比較・採用する。
- [ ] BigQueryの計測スキーマとConnected SheetsをASPIRE 2A対応に更新し、既存クラスタとの比較表示を確認する。
- [ ] コードをYAGNI原則に沿って整理し、workflow、shell、parser、計測スキーマ、成果物およびConnected Sheetsの変更を検証して、Genkai/Gadiに退行がないことを確認する。
- [ ] 実装、実測結果、採用判断、残る制約および外部成果物の所在をリポジトリ内に記録する。

完了時には、ASPIRE 2AでOpenFOAMのビルド、実行、計測、成果物回収が再現可能に完走し、Cray MPICH/PALS/Slingshotの使用、採用toolchainとAOCLの検証結果、AMD uProfの結果、改善前後のベンチマーク、採用したコード改善、BigQuery Connected Sheetsへの反映を証拠から確認できる状態にしてください。
