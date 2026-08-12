# OpenFOAM on Genkai

Genkai 上で OpenFOAM の競技ワークロードを実行し、ビルド方法や実行性能の改善による影響を比較するためのリポジトリです。

調査内容と現行構成は以下に分けて記録しています。

- [OpenFOAM のビルド](research/build-performance/README.md)
- [OpenFOAM の実行](research/runtime-performance/README.md)

実装は [Genkai workflow](.github/workflows/genkai.yml)、[ビルドスクリプト](scripts/build-openfoam.sh)、[実行スクリプト](scripts/run-openfoam.pjm)を参照してください。

## VTune hotspots と Perfetto trace

`OpenFOAM on genkai` を手動実行するとき、`profile_mode` に `vtune-hotspots` を選ぶと MPI rank 0 を Intel VTune で計測します。
計測後、上位 hotspot は GitHub Actions の run summary に表として表示されます。
同じ VTune result から CPU time の時系列、時間帯別の上位関数、solver iteration、残差を含む Perfetto 用 JSON を生成します。
JSON と変換元の timeline、hotspots は `openfoam-vtune-perfetto-<run-id>` artifact からダウンロードできます。
JSON は [Perfetto UI](https://ui.perfetto.dev/) で開けます。
VTune の完全な result directory は Genkai の `~/openfoam-vtune/` 以下に保持され、Actions summary に保存先が記録されます。
