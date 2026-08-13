# OpenFOAM on Genkai

Genkai 上で OpenFOAM の競技ワークロードを実行し、ビルド方法や実行性能の改善による影響を比較するためのリポジトリです。

調査内容と現行構成は以下に分けて記録しています。

- [OpenFOAM のビルド](research/build-performance/README.md)
- [OpenFOAM の実行](research/runtime-performance/README.md)

実装は [Genkai workflow](.github/workflows/genkai.yml)、[ビルドスクリプト](scripts/build-openfoam.sh)、[実行スクリプト](scripts/run-openfoam.pjm)を参照してください。

## VTune hotspots summary

push からの起動は常に benchmark です。`OpenFOAM on genkai` を手動実行するときだけ `run_purpose` で `bench` または `profile` を選択できます。
`profile` は `profile_rank` で選んだMPI rank（既定値0）へ60秒間Intel VTuneをattachして計測します。
計測後、上位 hotspot は GitHub Actions の run summary に表として表示されます。
このモードでは Perfetto 用 trace を生成しません。
VTune の完全な result directory は Genkai の `~/openfoam-vtune/` 以下に保持され、Actions summary に保存先が記録されます。
