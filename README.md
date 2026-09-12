# 玄界とGadiでのOpenFOAM実行

本リポジトリは、九州大学「玄界」およびNCI「Gadi」においてOpenFOAMの競技ワークロードを実行し、ビルド最適化や実行性能改善の影響を評価・比較するためのリポジトリです。

現在の対象ワークロードは、OpenFOAM.com v2512の`simpleFoam`で実行する公式の`occDrivAerStaticMesh`粗格子（65,334,765セル）です。公式ケースのリビジョン（コミットハッシュ）、Zenodo上で配布されているメッシュのMD5/SHA-256、およびノード数ごとの反復回数（40/80/150反復）については、[`benchmark/workload.json`](benchmark/workload.json)を正本とします。玄界・Gadiの双方において、同一課題で通常計測およびIntel VTuneによるプロファイル計測を実施します。

公式採点対象はGadi（`normalsr`キュー）またはASPIRE-2Aの4 CPUノード環境です。本リポジトリではGadiを公式採点対象とし、玄界は先行開発および参考計測の位置付けとしています。1ノードおよび2ノードの実行はスケーリング特性の確認を目的としています。評価指標は`simpleFoam`ログに出力される`Average wall-clock time per time step`（2ステップ目以降の平均秒数）であり、値が小さいほど高速と評価されます。準備時間（Allrunの全工程）は採点対象外ですが、すべての準備工程を完了することが必須要件です。なお、アーキテクチャの異なるクラスタ間で絶対時間を直接比較して優劣やスコアを競うことはしません。

抗力係数 $C_d$ は `postProcessing/forceCoeffsAll/*/coefficient.dat` の最終ステップから抽出し、既報値（40ステップ: 約0.43、80ステップ: 約0.34、150ステップ: 約0.28〜0.29）と併記します。公式ルールにおいて許容誤差幅は定義されていないため、本リポジトリ独自の合否判定は設けていません。公式ルールと実装の対応関係については[ルール対応表](research/official-rules.md)を、提出物の詳細については[提出手順](submission/README.md)を参照してください。

調査記録および現行の構成方針は以下のドキュメントにまとめています。

- [過去のOpenFOAMビルド調査](research/build-performance/README.md)
- [過去の実行性能調査](research/runtime-performance/README.md)
- [複数クラスタの実装判断](research/multi-cluster-workflow.md)

ワークフローおよびスクリプトの実装については、[共通の入口](.github/workflows/openfoam.yml)、[玄界用ワークフロー](.github/workflows/genkai.yml)、[Gadi用ワークフロー](.github/workflows/gadi.yml)、[Gadiの記憶領域設計](platforms/gadi/README.md)、[ビルドスクリプト](scripts/build-openfoam.sh)、[実行スクリプト](scripts/run-openfoam.sh)を参照してください。

## GitHub Actionsからの起動

クラスタ上の処理を担当するジョブは、セルフホストランナー（`[self-hosted, home-lab]`）上で起動し、玄界向けには`genkai-shell --github-shell`、Gadi向けには`gadi-shell --github-shell`をカスタムシェル（custom shell）として直接利用します。リポジトリのチェックアウトや各ステップの実行環境は、ログインノード上の実行固有の一時ディレクトリへ転送され、共有キャッシュ、ビルド成果物、ケースキャッシュ、および実行ディレクトリ（RUN_DIR）の既存パス構成は維持されます。

手動実行（workflow_dispatch）時はワークフロー`OpenFOAM`を選択し、`run_genkai`、`run_gadi`、`node_count`を指定して起動します。玄界とGadiは同時に選択可能です。両方とも無効にした場合はクラスタ上のジョブはすべてスキップされます。通常計測を行う場合は`profile=false`、VTuneによるプロファイル計測を行う場合は`profile=true`を指定します。

プッシュによる自動実行では、コミットメッセージに`[cluster:genkai]`や`[cluster:gadi]`を含めて実行先クラスタを指定し、`[nodes:1]`、`[nodes:2]`、`[nodes:4]`でノード数を指定します（ノード数の指定を省略した場合は1ノードとなります）。両方のクラスタを同時に指定することも可能です。また、`[profile]`を含めるとVTune計測となり、MPIランク0を対象とした`hotspots`解析が実行されます。

プッシュ時、最新コミットメッセージの先頭に`[require-build]`が含まれている場合は、各クラスタで新規ビルドを強制実行します。それ以外の場合は、現在のコミットから第一親（first-parent）を遡って同一クラスタで利用可能な既存のビルド成果物を探索します。再利用の判定にあたっては、成果物のサイドカーに記録された元のビルドコミットと比較し、OpenFOAMおよびThirdPartyのソース、共通およびクラスタ別のビルド設定、ネイティブツール群、ビルド対象プローブのいずれにも変更がないことを確認します。ランタイム設定、解析スクリプト、ドキュメントのみの変更であれば既存のビルド成果物を再利用します。同一コミット内に複数の成果物候補がある場合は、より新しいものから順に検証します。手動実行時はコミットメッセージのタグを参照せず、適合する成果物が存在しない場合に新規ビルドを行います。

ビルド処理本体は`scripts/build-openfoam.sh {genkai|gadi}`に集約されており、環境モジュール（module）、ソース展開、並列数などのクラスタ依存設定は`platforms/{genkai,gadi}/build-environment.sh`で管理しています。

## VTuneによるプロファイル

プロファイル計測も、通常実行と同様に`OpenFOAM`ワークフローから起動します。MPIランク0に対して60秒間、Intel VTuneの`hotspots`解析をアタッチして計測を行います。

計測完了後、上位のホットスポット関数はGitHub Actionsの実行サマリーにテーブル形式で表示されます。なお、Perfetto用のトレースファイルは生成しません。

VTuneの完全な解析結果およびParaView用の分割済みケースデータは、固定成果物と同じクラスタ側の`RUN_DIR`配下の`large-output/{vtune,paraview}`に出力されます。通常の`noWrite`設定では、保存されるフィールドデータは初期状態（時刻0）のものであり、最終反復ステップのフィールドデータではありません。最終反復の状態確認にはソルバーログおよび`coefficient.dat`を使用します。プロファイルの完了後、自宅サーバー上の`home-lab`ランナーがこれらの大容量出力を直接回収します。整合性検証済みの圧縮データとマニフェストは、自宅サーバーの`/hdd_raid/samba/net_share/openfoam-artifacts/<github-run-id>/<cluster>/openfoam-<cluster>-v2-<run-id>/large-output/`に保存され、固定成果物の配置が完了した後にクラスタ側の`RUN_DIR`全体が削除されます。VTuneが結果ディレクトリを生成しなかった場合でも、エラーログを含む固定プロファイル成果物とParaViewケースは保持され、large-outputマニフェスト内の`vtune_result_available=false`によって完全結果が存在しない旨が記録されます。ParaView用データは、単一の`paraview-case.tar.zst`を展開した上で`occDrivAerStaticMesh.foam`を開くことで可視化できます。なお、データの転送または保存に失敗した場合は、調査のためクラスタ側の`RUN_DIR`がそのまま保持されます。

成果物の転送には、ランナー環境にセットアップ済みの`genkai-shell`または`gadi-shell`と既存のSSH鍵を使用するため、転送専用の外部設定ファイルは不要です。転送元パスはワークフロー実行時に`RUN_DIR`から動的に決定され、自宅サーバー側の保存ルートは`OPENFOAM_ARTIFACT_ARCHIVE_ROOT`環境変数経由で渡されます。
