# OpenFOAM on Genkai and Gadi

Genkai 上で OpenFOAM の競技ワークロードを実行し、ビルド方法や実行性能の改善による影響を比較するためのリポジトリです。

現在の対象は、OpenFOAM.com v2512の`simpleFoam`で実行する公式`occDrivAerStaticMesh` coarse mesh（65,334,765 cells）です。公式ケースのcommit、Zenodo meshのMD5/SHA-256、ノード数ごとの40/80/150 iterationは[`benchmark/workload.json`](benchmark/workload.json)を正本とします。玄界とGadiのどちらでも通常計測とVTune profileを同じワークロードで実行します。

調査内容と現行構成は以下に分けて記録しています。

- [過去のOpenFOAMビルド調査](research/build-performance/README.md)
- [過去の実行性能調査](research/runtime-performance/README.md)
- [複数クラスタの実装判断](research/multi-cluster-workflow.md)

実装は [共通の入口](.github/workflows/openfoam.yml)、[玄界](.github/workflows/genkai.yml)、[Gadi](.github/workflows/gadi.yml)、[Gadiの記憶領域](platforms/gadi/README.md)、[ビルドスクリプト](scripts/build-openfoam.sh)、[実行スクリプト](scripts/run-openfoam.sh)を参照してください。

## GitHub Actionsからの起動

`OpenFOAM` を手動実行し、`run_genkai`、`run_gadi`、`node_count`を指定します。玄界とGadiは同時に選択できます。どちらも選択しなければクラスタのジョブはすべてスキップされます。通常計測は`profile=false`、VTune計測は`profile=true`とします。

pushではコミットメッセージに`[cluster:genkai]`、`[cluster:gadi]`を含めて実行先を指定し、`[nodes:1]`、`[nodes:2]`、`[nodes:4]`でノード数を指定します。ノード数を省略した場合は1です。両方のクラスタを同時に指定できます。`[profile]`を含めるとVTune計測になり、rank 0の`hotspots`を使います。

push時は、最新コミットメッセージの先頭が `[require-build]` なら各クラスタで新しくビルドし、それ以外は現在のコミットからfirst-parentを遡って同じクラスタにある最新の利用可能な成果物を再利用します。手動実行では `[require-build]` を無視して同じ探索を行い、利用可能な成果物がない場合だけ新しくビルドします。再利用時はsource、toolchain、build定義の一致を条件にしません。

## VTuneによるプロファイル

プロファイルも通常実行と同じ`OpenFOAM`から起動します。MPI rank 0へ60秒間Intel VTuneの`hotspots`解析を接続して計測します。
計測後、上位ホットスポットはGitHub Actionsの実行概要に表として表示されます。Perfetto用のトレースは生成しません。
VTuneの完全な結果は、玄界では`/home/pj26000080/share/openfoam-vtune/`、Gadiでは`/scratch/hb15/tk7779/openfoam/gadi/profile/`以下に保持され、実行概要に保存先が記録されます。
