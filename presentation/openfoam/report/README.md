# 提出物のテクニカルレポートの図と付録

`submission/openfoam/TECHNICAL_REPORT.md`（2026-11-04に作成、11-05に図を追加）の図、付録A、検査を作るスクリプトです。
レポートの本文は手で書いています。数値はすべて `../data/*.csv` とBoxの提出物のログから取っています。

| ファイル | 役割 |
|---|---|
| `report_plots.py` | `../deck/deck_plots.py` をそのまま動かし、デッキではスライドの図形として重ねる矢印、変化の%、scalingの倍率を画像に描き込む。200 dpi |
| `make_figures.py` | レポートの21枚を `submission/openfoam/figures/` に集める。デッキの図、`../figures.py` の2枚（ばらつき、配置の実験）、スライドから切り出した図形の図3枚、分割の絵3枚（Boxのpanelsから合成し、各画角の古いラベルを外して色の凡例を付ける） |
| `appendix.py` | 付録A（比較に使った全ジョブとActionsのrun ID）を `../data/*.csv` から書く。レポートの `## Appendix A` の下に貼る |
| `lint_report.py` | 表の列の数、表・図・節の番号の順、参照先、画像の有無、使わない文字（emダッシュ、中黒）を確かめる |

作り直し方（WSL、作業用フォルダを `$work` とする）:

1. `uv run presentation/openfoam/report/report_plots.py presentation/openfoam/deck $work/figs_plots`
2. `uv run presentation/openfoam/deck/deck_figures.py presentation/openfoam/figures.py $work/figs_team`
3. Windows側で、Boxの `presentation/openfoam/decomposition/panels/*-numa.png` を `$work/panels/` へコピーする（WSLからはBoxを読めない）。
4. Windows側で、HPCのデッキ（第8版のビルド）のスライド9、17、22を `../deck/render.ps1 -Width 2400 -Slides "9,17,22"` で `$work/slides/` に書き出す（2400×1350。`make_figures.py` の切り出し位置はこの大きさが前提）。
5. `uv run presentation/openfoam/report/make_figures.py $work submission/openfoam/figures`
6. 付録A: `uv run presentation/openfoam/report/appendix.py presentation/openfoam/data $work/appendix_a.md`
7. 検査: `uv run presentation/openfoam/report/lint_report.py submission/openfoam/TECHNICAL_REPORT.md`

Boxの提出物 `openfoam/` には、レポートと `figures/` を同じ形でコピーします。
