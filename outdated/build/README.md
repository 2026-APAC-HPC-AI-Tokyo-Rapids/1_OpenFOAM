# 旧ビルドスクリプト

以前の Slurm 環境で OpenFOAM v2412 を取得・ビルドするための script です。

- `run.sh` は `programs/` を作成して OpenFOAM / ThirdParty archive を取得・展開し、`build.sh` を `sbatch` で投入します。
- `build.sh` は HPC-X を読み込み、OpenFOAM の `Allwmake` と一部 solver を 64 並列でビルドします。

どちらも `/home/apacsc14/ni/hpc` などの当時の絶対パスを持ちます。現行の GitHub Actions では
使用しないため、そのまま実行しないでください。
