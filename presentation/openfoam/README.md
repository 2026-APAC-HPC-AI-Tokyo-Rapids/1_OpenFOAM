# OpenFOAMパートの発表素材

- `slides.md`：スライドの構成と、載せる文（英語）・話す内容（日本語）・想定問答。
- `figures.py`：`data/`のCSVから図と表の画像を作ります。`uv run presentation/openfoam/figures.py <出力先>`で、`<名前>.png`（貼り付け用）と`<名前>.svg`（編集用）を出力します。
- 出力した画像は、提出用Boxの`Tokyo_Rapids_with_RIKEN_Submission/presentation/openfoam/figures/`に置きます。画像はリポジトリには入れません。
- `flow/`：流れの動画と画像（ParaView）を作る可視化用runの設定と描画スクリプト。`flow/README.md`を参照してください。動画と画像はBoxの`presentation/openfoam/flow/`に置きます。
- `decomposition/`：4ノードの512分割（hierarchical、scotch、multiLevel）がメッシュをどう切っているかの画像を作るジョブと描画スクリプト。`decomposition/README.md`を参照してください。画像はBoxの`presentation/openfoam/decomposition/`に置きます。

## data/

図に使う値だけを、各runの記録から抜き出したものです。runの生の記録は成果物の保管庫にあり、比較の経緯は各issueにあります。

| ファイル | 中身 | 出典 |
|---|---|---|
| `final_runs.csv` | 最終構成（Basic 6396eeb、Bonus fa4f5b0）の全20本 | 保管済みバンドルの`results/result.txt`（公式parser） |
| `changes_ab.csv` | Bonusの変更ごとの、同時期の対照と候補 | #42、#44、#50、#51の表 |
| `decomposition_basic.csv` | scotchとhierarchicalの交互測定（1/2/4ノード、各3本） | #36（4ノード）、#38（1/2ノード） |
| `pinning.csv` | CPU/NUMA固定の切り分け（4ノード） | #36 A3 |
| `step_regions_4node.csv` | 1 stepの区間ごとの経過時間（OpenFOAM組み込みのprofiling、4ノード40 stepの診断run、512 rankの中央値・最小・最大） | #57（Actions 37714968610）の`processor*/40/uniform/profiling` |
| `counters_1node.csv` | パッチの有無（各2本）のuProf `data_access`のカウンタ。計算部分（MPI、UCX、Pstreamを除く）のrank 16〜112の平均 | #55（37580443881、37583693730、37580444029、37580455271）の`profile/raw/uprof/reports/` |
| `memory_placement.csv` | 配置だけを変えた4ノードの16本（Basic、パッチを外したBonus、Bonus × full128・spread64・packed64）の公式値と`coefficient.dat`のハッシュ | #61の各runの`results/result.txt`と`results/coefficient.dat` |
| `triad_placement.csv` | 同じrunのノードごとのtriadの帯域（solverの後に3つの配置で測った値） | #61の各runの`logs/pbs.log` |
| `start_unpinned.csv` | 最初の状態（hierarchical、固定が外れたまま）の4ノード3本。`decomposition_basic.csv`の固定ありhierarchicalと同時期 | #36 A |
| `compiler_options.csv` | コンパイラとフラグの比較（4ノード、各3本） | #36 D |
| `craypat_summary.csv` | CrayPATの3本（Basic、パッチ0002〜0004の前、最終Bonus）の時間 | 各runの`pat-report.txt`のTable 1、2、4 |
| `rank_compute.csv` | rankごとの計算時間（process − MPI）、パッチの前と後 | 37261721692、37529785072のCrayPAT（pe別） |
| `organiser_reference_aspire2a.csv` | 主催者のASPIRE-2Aの参照run（既定の設定と、MPIの環境変数を変えたrun） | `tasks/4.3-aspire2a-logs/`の`50_simpleFoam.*.log`と`coefficient.dat` |
| `bench_runs_sep21_oct05.csv` | 2026-09-21〜10-05のASPIRE-2Aの通常計測run（開始時刻はUTC） | 保管済みバンドルの記録（#47） |
