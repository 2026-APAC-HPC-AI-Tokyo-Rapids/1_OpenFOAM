# 現在のビルド構成

ここでは玄界のビルドを扱う。Gadiはコンパイラ、MPI、記憶領域が異なるため、[Gadi用ワークフロー](../../.github/workflows/gadi.yml)と[運用方針](../../platforms/gadi/README.md)を参照する。

## ビルドの定義

| 項目 | 設定 |
|---|---|
| OpenFOAM | v2606 |
| 追加依存 | ADIOS2 2.12.1、CGAL 6.1.1 |
| compiler / MPI | `intel/2025.1.3`モジュールのIntel C++ 2025.1.1、Intel MPI 2021.15 |
| OpenFOAM 設定 | `WM_COMPILER=Icx`、`WM_MPLIB=INTELMPI`、DP、64-bit label |
| Allwmake | `-j 120 -s`、queue なし |
| compiler cache | ccache。CMake の C/C++ launcher にも使用 |

ADIOS2 と CGAL の source は workflow が明示した version を使う。CGAL の version 選択、Icx の C preprocessor、Allwmake の timestamp 出力は、Org 管理の `3_OpenFOAM_Src` に直接反映している。ビルドは同 repository の `master` を checkout するため、これらの変更はソース履歴の一部として管理される。

## ディレクトリとキャッシュ

処理を三つの置き場に分けている。

| 種別 | 置き場 | 意図 |
|---|---|---|
| source archive | 共有の source cache | download を再利用する |
| 展開済み source・object・log | 実行ごとの `/dev/shm/openfoam-<run-id>-...` | build tree の大量 I/O を runner のメモリ上へ閉じる |
| ccache の本体 | runner 既定の cache storage | warm cache を実行間で再利用する |
| ccache の一時ファイル | run用一時ディレクトリの `ccache` | 一時ファイルを build archive から分離する |
| build archive | 共有の builds directory | run number ごとの `tar.zst` を後続jobから利用する |

archive 展開後の version 付きディレクトリは、build root 内の `OpenFOAM` と `ThirdParty` に正規化する。`OpenFOAM/ThirdParty` は後者への symlink とし、OpenFOAM の標準的な探索規則を維持する。さらに `CCACHE_BASEDIR` を build root に設定し、実行ごとの一時パスと OpenFOAM version を cache key に持ち込まない。cleanup は当該 run-id の `mktemp` ディレクトリだけに限定する。

`/dev/shm` は build tree を高速化する手段であって、すべての I/O を隔離するものではない。compiler、標準 header、module、ccache storage は共有ストレージ側に残る。そのため、build root を tmpfs 化しても時間変動は残る。

## build archive の作成と再利用

ビルド成果物は`${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_ID}.tar.zst`として保存する。push時だけ、コミットメッセージ先頭の`[require-build]`で新規ビルドを指定する。手動実行ではコミットメッセージを読まない。

再利用時は現在のコミットから第一親を順に遡り、通常実行、玄界プロファイル、旧玄界ワークフローの成功履歴を調べる。圧縮ファイルと付随記録が残り、記録されたSHAと一致する成果物を現在の実行番号へハードリンクする。利用可能な成果物がなければ新しくビルドする。ソース、ツールチェーン、ビルド依存、生成物を変えるコミットは`[require-build]`を付けてpushする。

実行時は選択した成果物を展開し、ケース準備、計算ジョブ、公式判定、メトリクス作成、成果物回収までを同じActions実行内で完了する。

## 実行時の観測点

通常の成功 run では、次を確認する。

- GitHub Actions の job / step 所要時間。runner の待機と `Build OpenFOAM` の遅延を分ける。
- artifact の `allwmake.log`。`3_OpenFOAM_Src` の Allwmake ログ処理が各行に時刻を付けるため、遅延した工程を絞れる。
- `ccache --show-stats`。Allwmake の直前に統計を zero clear するため、その build だけの hit 率、cacheable call 数、miss 数、local / remote storage の状態を確認できる。
- 失敗時の `allwmake.log` と Actions の失敗ログ。workflow は console へ error の要約を出し、完全な log は artifact として残す。

現在 `scripts/build-profiler.sh` はコマンドをそのまま実行する薄い wrapper である。過去の詳細プロファイリングは継続計測には採用していないため、CPU 時間、context switch、perf 結果は最新 run からは得られない。必要な仮説ができたときだけ、比較対象を決めた A/B 計測として復活させる。
