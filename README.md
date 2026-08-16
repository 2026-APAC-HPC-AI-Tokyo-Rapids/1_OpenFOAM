# OpenFOAM on Genkai

Genkai 上で OpenFOAM の競技ワークロードを実行し、ビルド方法や実行性能の改善による影響を比較するためのリポジトリです。

調査内容と現行構成は以下に分けて記録しています。

- [OpenFOAM のビルド](research/build-performance/README.md)
- [OpenFOAM の実行](research/runtime-performance/README.md)
- [複数クラスタの実装判断](research/multi-cluster-workflow.md)

実装は [共通の入口](.github/workflows/openfoam.yml)、[玄界](.github/workflows/genkai.yml)、[Gadi](.github/workflows/gadi.yml)、[Gadiの記憶領域](platforms/gadi/README.md)、[ビルドスクリプト](scripts/build-openfoam.sh)、[実行スクリプト](scripts/run-openfoam.sh)を参照してください。

## GitHub Actionsからの起動

通常の実行は `OpenFOAM` を手動実行し、`run_genkai`、`run_gadi`、`node_count` を指定します。玄界とGadiは同時に選択できます。どちらも選択しなければクラスタのジョブはすべてスキップされます。

pushではコミットメッセージに `[cluster:genkai]`、`[cluster:gadi]` を含めて実行先を指定し、`[nodes:1]`、`[nodes:2]`、`[nodes:4]` でノード数を指定します。ノード数を省略した場合は1です。両方のクラスタを同時に指定できます。

push時は、最新コミットメッセージの先頭が `[require-build]` なら各クラスタで新しくビルドし、それ以外は同じクラスタにある直近の利用可能な成果物を再利用します。手動実行では `[require-build]` を無視して既存成果物を再利用し、利用可能な成果物がない場合だけ新しくビルドします。

## VTuneによるプロファイル

プロファイルは `Profile OpenFOAM on Genkai` から起動します。`profile_rank` で選んだMPI rank（既定値0）へ60秒間Intel VTuneを接続して計測します。
`profile_analysis=hotspots`は関数別CPU時間、`hpc-performance`はCPUパイプライン、メモリ階層、DRAM帯域、FPU・ベクトル化の特性を取得します。
計測後、上位ホットスポットはGitHub Actionsの実行概要に表として表示されます。Perfetto用のトレースは生成しません。
VTuneの完全な結果は玄界の `/home/pj26000080/share/openfoam-vtune/` 以下に保持され、実行概要に保存先が記録されます。
