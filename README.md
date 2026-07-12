# OpenFOAM HPC task

九州大学の Genkai 環境を対象に、OpenFOAM をソースからビルドし、`motorBike` の
短時間スモークテストを実行するためのリポジトリです。GitHub Actions では、ビルド済み
アーカイブを再利用して、通常の変更での実行時間を抑えます。

## リポジトリの構成

| 場所 | 内容 |
| --- | --- |
| [`.github/`](.github/README.md) | Genkai 上で動作する GitHub Actions workflow |
| [`scripts/`](scripts/README.md) | ビルドと実行で呼び出す補助スクリプト |
| [`patches/`](patches/README.md) | OpenFOAM source に適用する差分 |
| [`research/`](research/README.md) | ビルド性能の調査記録と計測方針 |
| [`outdated/`](outdated/README.md) | 以前の Slurm 実験に関する参考資料 |

## CI の動き

`genkai.yml` は次の順に処理します。

1. OpenFOAM v2606 と依存ライブラリを必要に応じてビルドし、`tar.zst` に保存する。
2. 保存済みアーカイブから実行専用の runtime tree を用意する。
3. 1 ノード・120 MPI プロセスで `motorBike` tutorial のメッシュ生成と `simpleFoam` を実行する。

push 時は、最新コミットのメッセージに **`[require-build]` が含まれる場合だけ**
ソースからビルドします。含まれない場合は第一親の履歴から直近の成功したビルド成果物を
再利用します。source、patch、compiler 設定を変えたときは、互換性を保つため先頭に
`[require-build]` を付けてください。手動実行では `require_build` 入力で同じ選択を行えます。

## 前提

この設定は self-hosted Genkai runner 専用です。Intel oneAPI 2025.1.3、Intel MPI、
ccache、zstd、PJM、および workflow に記載した共有パスが必要です。別環境で利用する場合は、
まず workflow の runner label、module 名、共有ストレージのパスを置き換えてください。

ビルド構成と性能計測の詳細は
[`research/build-performance/`](research/build-performance/README.md) を参照してください。
