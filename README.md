# OpenFOAM on Genkai

Genkai 上で OpenFOAM の競技ワークロードを実行し、ビルド方法や実行性能の改善による影響を比較するためのリポジトリです。

調査内容と現行構成は以下に分けて記録しています。

- [OpenFOAM のビルド](research/build-performance/README.md)
- [OpenFOAM の実行](research/runtime-performance/README.md)

実装は [Genkai workflow](.github/workflows/genkai.yml)、[ビルドスクリプト](scripts/build-openfoam.sh)、[実行スクリプト](scripts/run-openfoam.pjm)を参照してください。
