# 現在のビルド構成

ここでいう「現在」は `main` の [Genkai workflow](../../.github/workflows/genkai.yml) を指す。環境に依存するため、別の runner や OpenFOAM version にこの設定をそのまま転用してはならない。

## ビルドの定義

| 項目 | 設定 |
|---|---|
| OpenFOAM | v2412 |
| 追加依存 | ADIOS2 2.12.1、CGAL 6.1.1 |
| compiler / MPI | Intel oneAPI 2025.1.3 の `mpiicx` / `mpiicpx`、Intel MPI |
| OpenFOAM 設定 | `WM_COMPILER=Icx`、`WM_MPLIB=INTELMPI`、DP、64-bit label |
| Allwmake | `-j 120 -s`、queue なし |
| compiler cache | ccache。CMake の C/C++ launcher にも使用 |

ADIOS2 と CGAL の version は OpenFOAM の既定値と異なるため、対応する patch を毎回適用する。Icx では C preprocessor の置換も必要である。適用対象は [patches](../../patches) に置き、workflow は `patches/*.patch` を全件適用する。このため、patch の追加・削除はビルド定義の変更として扱う。

## ディレクトリとキャッシュ

処理を三つの置き場に分けている。

| 種別 | 置き場 | 意図 |
|---|---|---|
| source archive | 共有の source cache | download を再利用する |
| 展開済み source・object・log | 実行ごとの `/dev/shm/openfoam-<run-id>-...` | build tree の大量 I/O を runner のメモリ上へ閉じる |
| ccache の本体 | runner 既定の cache storage | warm cache を実行間で再利用する |
| ccache の一時ファイル | 実行ごとの `/dev/shm/ccache-<run-id>-...` | 一時ファイルを build archive から分離する |

実行ごとに build path が変わるため、`CCACHE_BASEDIR` を build root に設定してパス差を cache key に持ち込まない。cleanup は当該 run-id の `mktemp` ディレクトリだけに限定する。

`/dev/shm` は build tree を高速化する手段であって、すべての I/O を隔離するものではない。compiler、標準 header、module、ccache storage は共有ストレージ側に残る。そのため、build root を tmpfs 化しても時間変動は残る。

## 実行時の観測点

通常の成功 run では、次を確認する。

- GitHub Actions の job / step 所要時間。runner の待機と `Build OpenFOAM` の遅延を分ける。
- artifact の `allwmake.log`。`allwmake-timestamps.patch` により各行に時刻が付くため、遅延した工程を絞れる。
- `ccache --show-stats`。hit 率だけでなく、cacheable call 数、miss 数、local / remote storage の状態を確認する。
- 失敗時の `allwmake.log` と Actions の失敗ログ。workflow は console へ error の要約を出し、完全な log は artifact として残す。

現在 `scripts/build-profiler.sh` はコマンドをそのまま実行する薄い wrapper である。過去の詳細プロファイリングは継続計測には採用していないため、CPU 時間、context switch、perf 結果は最新 run からは得られない。必要な仮説ができたときだけ、比較対象を決めた A/B 計測として復活させる。
