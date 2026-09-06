# 玄界とGadiでのOpenFOAM実行

玄界およびGadi上でOpenFOAMの競技ワークロードを実行し、ビルド方法や実行性能の改善による影響を比較するためのリポジトリです。

現在の対象は、OpenFOAM.com v2512の`simpleFoam`で実行する公式`occDrivAerStaticMesh`粗格子（65,334,765セル）です。公式ケースのコミット、Zenodo上のメッシュのMD5/SHA-256、ノード数ごとの40/80/150反復は[`benchmark/workload.json`](benchmark/workload.json)を正本とします。玄界とGadiのどちらでも、同じ課題で通常計測とVTuneプロファイルを実行します。

公式採点対象はGadi（`normalsr`）またはASPIRE-2Aの4 CPUノードです。本リポジトリではGadiが採点対象、玄界は開発・参考計測に当たります。1/2ノードはスケーリングの参考です。評価指標は`simpleFoam`ログの`Average wall-clock time per time step`（2ステップ目以降の平均秒数）で、小さいほど高速です。準備時間は採点外ですが、Allrunの準備工程はすべて必須です。異なるクラスタの絶対時間を直接比較して優劣やスコアを決めません。

Cdは`postProcessing/forceCoeffsAll/*/coefficient.dat`の最終ステップから読み、40/80/150ステップで約0.43/0.34/0.28〜0.29という既報値と併記します。公式の許容幅はなく、Cdによる独自の合否判定は行いません。公式ルールと実装の対応は[ルール対応表](research/official-rules.md)、提出物は[提出手順](submission/README.md)を参照してください。

調査内容と現行構成は以下に分けて記録しています。

- [過去のOpenFOAMビルド調査](research/build-performance/README.md)
- [過去の実行性能調査](research/runtime-performance/README.md)
- [複数クラスタの実装判断](research/multi-cluster-workflow.md)

実装は [共通の入口](.github/workflows/openfoam.yml)、[玄界](.github/workflows/genkai.yml)、[Gadi](.github/workflows/gadi.yml)、[Gadiの記憶領域](platforms/gadi/README.md)、[ビルドスクリプト](scripts/build-openfoam.sh)、[実行スクリプト](scripts/run-openfoam.sh)を参照してください。

## GitHub Actionsからの起動

クラスタ処理を担当するjobは`[self-hosted, home-lab]`で起動し、玄界は`genkai-shell --github-shell`、Gadiは`gadi-shell --github-shell`をcustom shellとして直接使います。checkoutとstep環境はログインノード上のrun固有一時ディレクトリへ転送し、共有キャッシュ、ビルド成果物、ケースキャッシュ、run directoryの既存パスは変更しません。

`OpenFOAM`を手動実行し、`run_genkai`、`run_gadi`、`node_count`を指定します。玄界とGadiは同時に選択できます。どちらも選択しなければクラスタ上のジョブはすべて省略されます。通常計測は`profile=false`、VTune計測は`profile=true`とします。

プッシュではコミットメッセージに`[cluster:genkai]`、`[cluster:gadi]`を含めて実行先を指定し、`[nodes:1]`、`[nodes:2]`、`[nodes:4]`でノード数を指定します。ノード数を省略した場合は1です。両方のクラスタを同時に指定できます。`[profile]`を含めるとVTune計測になり、ランク0の`hotspots`解析を使います。

プッシュ時は、最新コミットメッセージの先頭が`[require-build]`なら各クラスタで新しくビルドします。それ以外は現在のコミットから第一親を辿り、同じクラスタの利用可能な成果物を探します。再利用候補はsidecarに記録された元のbuild commitと比較し、OpenFOAM/ThirdPartyのsource、共通・クラスタ別build設定、native tool、ビルドへ含めるprobeが変わっていないものに限ります。runtime・解析・文書だけの変更では既存成果物を再利用します。同一commit内では新しい候補から調べます。手動実行ではコミットメッセージを読まず、適合する成果物がなければビルドします。

ビルド本体は`scripts/build-openfoam.sh {genkai|gadi}`、module・source展開・並列数などのクラスタ差は`platforms/{genkai,gadi}/build-environment.sh`に置きます。

## VTuneによるプロファイル

プロファイルも通常実行と同じ`OpenFOAM`から起動します。MPIランク0へ60秒間Intel VTuneの`hotspots`解析を接続して計測します。
計測後、上位ホットスポットはGitHub Actionsの実行概要に表として表示されます。Perfetto用のトレースは生成しません。
VTuneの完全な結果とParaView用の分割ケースは、固定成果物と同じクラスタ側`RUN_DIR`の`large-output/{vtune,paraview}`へ出力します。通常のnoWrite設定では保存済みfieldは時刻0であり、最終反復のfieldではありません。最終反復の確認にはsolverログとcoefficient.datを使用します。プロファイルの成功後、自宅サーバー上の`home-lab` runnerがこれらを直接取得します。検証済みの圧縮結果とmanifestは`/hdd_raid/samba/net_share/openfoam-artifacts/<github-run-id>/<cluster>/openfoam-<cluster>-v2-<run-id>/large-output/`へ保存し、固定成果物の配置も成功した後に`RUN_DIR`全体を削除します。VTuneが結果ディレクトリを生成しなかった場合も、失敗ログを含む固定profile artifactとParaViewケースを保存し、large-output manifestの`vtune_result_available=false`で完全結果が存在しないことを明示します。ParaView用データは単一の`paraview-case.tar.zst`を展開し、`occDrivAerStaticMesh.foam`を開きます。転送または保管に失敗した場合は`RUN_DIR`をクラスタ側へ残します。

転送にはrunnerへ配置済みの`genkai-shell`または`gadi-shell`と既存SSH鍵を使います。転送専用の外部設定ファイルは不要です。転送元はworkflowが実行時の`RUN_DIR`から決定し、自宅側の保存rootは`OPENFOAM_ARTIFACT_ARCHIVE_ROOT`として渡します。
