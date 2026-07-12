# 補助スクリプト

GitHub Actions の workflow から呼び出す小さな shell script です。すべて Bash を前提とし、
エラーで停止する設定を使います。

| スクリプト | 役割 |
| --- | --- |
| `build-profiler.sh` | 指定されたコマンドをそのまま実行する build 用の計測フック |
| `exec-profiler.sh` | 指定されたコマンドをそのまま実行する実行時用の計測フック |
| `run-openfoam.sh` | provision 済み tree で `motorBike` を準備し、並列で実行する |

`run-openfoam.sh` の引数は `PROVISION_DIR RUN_DIR MPI_PROCS` です。Intel oneAPI と
Intel MPI の module を読み込み、OpenFOAM 環境を初期化した後、`snappyHexMesh`、
`topoSet`、`potentialFoam`、`simpleFoam` を順に実行します。CI では短時間で終えるため、
`controlDict` の `endTime` と `writeInterval` を 10 に変更します。

profiler script は現在は意図的に薄い wrapper です。詳細計測を導入する場合も、呼び出し元の
終了 status を変えないようにしてください。
