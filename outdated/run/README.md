# 旧実行スクリプト

`submit.sh` は、以前の Slurm 環境で `occDrivAerStaticMesh` case の `Allrun` を投入するための
参考 script です。ジョブ名と標準出力先、作業ディレクトリは当時の環境に固定されています。

現行 CI の smoke test はこの script を使用せず、
[`scripts/run-openfoam.sh`](../../scripts/run-openfoam.sh) を PJM job から実行します。
なお `submit.sh` には過去の実験時の記述が残っているため、再利用前には内容を必ず点検してください。
