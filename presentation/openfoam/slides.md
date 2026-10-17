# OpenFOAMパートのスライド構成（第3版）

チームのデッキ（Boxの`Tokyo_Rapids_with_RIKEN_Submission/presentation/Tokyo Rapids with RIKEN Presentation.pptx`）の新しい流れ（#52、10/13のメモ）に合わせて、第2版（本編9枚）を組み直したものです。

- スライドに載せる文は英語、話す内容（メモ）は日本語です。
- 図と表はBoxの`presentation/openfoam/figures/`（`.png`は貼り付け用、`.svg`は編集用）にあります。分割の絵は`decomposition/`、流れの動画は`flow/`です。図は、リポジトリで`uv run presentation/openfoam/figures.py <出力先>`を実行すると作り直せます。
- 数値はすべて公式指標`Average wall-clock time per time step`（2 step目以降の平均、秒/step）です。1点は1ジョブです。
- baselineは#62の測定（ケース既定のhierarchical、起動時の固定だけ、1/2/4ノード、2026-10-12）です。第2版の出発点3.670（#36、10/02〜03の4ノード3本）と同じ構成で、差は0.5 %です。本編の数値は3.65にそろえます。

### 第2版からの主な変更

- baselineを1枚から3枚（設定、結果、分析）にし、その間に「測り方」の1枚を足しました。
- BasicとBonusを、それぞれ「何を変えたか → 結果 → プロファイル」の順に分けました。
- 「メモリ帯域が律速」の実験（#61）を、BasicとBonusの間に置きました。Basicの後に残った律速を確かめ、Bonusの方針につなぐ位置です。
- scalingは、baseline・Basic・Bonusの3つを並べる1枚にして、Bonusの後に置きました。
- 「効かなかったこと」に理由の列を付けました。全部の一覧は補足に置きます。
- Bonusのソース変更は、番号（0001〜0004）ではなく、何をするかの名前で呼びます（no copies in the solvers、U components in one pass、no unused boundary updates、fused face loops）。番号は、提出物のpatchのファイル名として補足S4にだけ残します。
- ネットワーク側を確かめた結果を、補足S16と想定問答Q31にまとめました。
- 「同じ計算」の証拠を足しました。14枚目のメモとQ7に提出物のログの比較（残差などが全行一致）を書き、Q12に主催者の値を足し、想定問答にQ32（境界の更新を省くのは禁止事項か）とQ33（命令数が減ったのは仕事を減らしたからか）を足しました。

### 10/16の更新

- Basicに、scotchの分割をノードの木（ソケット、NUMA領域、コア）に対応付ける`scotchCoeffs`を足しました（#63）。4ノードは2.92 → 2.90 s/step（−0.69 %）です。本編と補足の数値と図を、すべて新しいBasicにそろえました。
- 「1 %以上速いものだけ採用」という言い方をやめ、実際に使った採否の決め方（同じ時期に交互に流し、候補の全runが対照の全runより速い）で書きました（6枚目、17枚目）。run間のばらつきは約0.2 %で、「1 %未満はノイズ」とは言えないためです。
- 「もう10 %速くならないのか」「rooflineは」に答えるQ34、Q35と、12枚目の演算密度の1行を足しました。#66のカウンタで、超線形（Q6）とrank間の不均衡（Q21）の説明も更新しました。
- 固定反復のときだけ効く#68の結果を、数えなかった結果として補足S17に置きました。本編の最後に見せるかは、チームで決めます。

---

## 方針

### 採点の仕組み（tasks/README.md R3・R4、Task RulesのPresentation Guidelines）

- 発表はQwenと合わせて15〜20分、質疑は10分です。2つのタスクの時間配分はチームで決めます。
- OpenFOAMは50点です。審査員が35点（Basic 20点、Bonus 15点）、性能と再検証が15点（主催者がBasicを再実行し、4ノードの値で順位を付けます）。
- 審査員が見るもの：
  - 最適化を「flagの一覧」ではなく「問題解決の筋道」として話しているか。
  - ボトルネックの特定と、なぜその変更が効いたかの説明。4ノードのbefore/after。1/2/4ノードのscaling。
  - Bonusの4点（R3）：何を変えたか、なぜ同じ計算か、証拠（自分の変更前baselineとのCd比較とログ）、同じ機械での自分のBasicに対する速度向上。
- 説明できない結果は、速くても点になりにくいです。筋道の通った「効かなかった実験」は評価され得ます。特に堅実なBasicのチューニングには、Bonus点が付き得ます。

### 構成の考え方

1. **問題解決の筋道で並べる。** baselineを測る → 測り方 → 何が遅いか → 戦略 → Basic（メモリの置き場所と仕事の均等さ）→ Basicの後に残る律速はメモリ帯域 → Bonus（運ぶデータを減らす）→ scaling → 効かなかったこと → まとめ。
2. **1枚1メッセージで軽くする。** 見出しはデッキと同じ大文字のラベルにし、その下に主張を1行書きます。図か表は1つ、強調する数字は1〜2個です。細かい数字はメモと補足に回します。
3. **測り方は1枚にまとめる（6枚目）。** 以降のスライドでは、道具の名前を括弧で添えるだけにします。
4. **BasicとBonusは同じ順で話す。** 何を変えたか → 結果 → プロファイルで確かめた理由。
5. **測ったことと仮説を分ける。** 並列効率が1を超える理由（キャッシュ）と、DRAMの転送バイト数は、仮説・未測定として話します。
6. **数値をデッキ全体でそろえる。** 4ノード：baseline 3.65、Basic 2.90（−21 %）、Bonus 2.60（−29 %、1.40×）。BonusはBasicから−10.3 %。並列効率（1→4ノード）はbaseline 1.00、Basic 1.15、Bonus 1.12。主催者のhierarchicalは3.415、scotchは5本の平均3.296。
7. **y軸が0から始まらない図**（`fig03`、`fig05`、`fig06`）は、その旨を図の下に書いてあります。

### 時間配分

- 各スライドの目安は、ゆっくり話した場合の上限で、合計は約11分30秒です。発表は英語ネイティブが担当するので、少し速めに話せば18枚で約10分に収まります。
- Qwenに時間を回すときだけ、下の「削るとき」を使います。
- 質疑（10分、Qwenと共通）は、補足スライドと想定問答で受けます。

---

## 本編（18枚、約11分30秒）

| # | 見出し（デッキ） | スライドの主張（1行） | 主な図 | 目安 | 今のpptx |
|---|---|---|---|---|---|
| 1 | Title | | | 0:10 | 1枚目 |
| 2 | TASK OVERVIEW | Make the same math faster on 1, 2 and 4 nodes | 流れの動画、メッシュ | 0:45 | 2枚目に結果を1行足す |
| 3 | ASPIRE-2A | 8 NUMA domains of 16 cores; 16 cores already fill the memory bandwidth | `fig11_node_layout` | 0:35 | 3枚目の表記を直す |
| 4 | BASELINE SETTINGS | We start from the case defaults, on our own build of v2512 | hierarchicalの分割の絵 | 0:35 | 4枚目の図をhierarchicalだけにする |
| 5 | BASELINE RESULTS | 3.65 s/step on 4 nodes: linear scaling, but slow and unsteady | `fig23_baseline_scaling` | 0:30 | 5枚目 |
| 6 | HOW WE MEASURE AND PROFILE | Benchmark runs give the numbers; separate profile runs explain them | `tab09_how_we_measure` | 0:35 | 新規 |
| 7 | BASELINE ANALYSIS | The binding is lost at MPI_Init, so ranks compute unevenly and wait | `fig24_baseline_chain` | 0:50 | 6枚目の表を図にする |
| 8 | OPTIMIZATION STRATEGY | Keep memory near each core, give every rank the same work, move fewer bytes | 7行の表（3行を強調） | 0:35 | 7枚目 |
| 9 | BASIC OPTIMIZATION (1/2) | Putting the lost binding back: 3.65 → 3.26 s/step (−11 %) | `fig06_pinning` | 0:50 | 8枚目 |
| 10 | BASIC OPTIMIZATION (2/2) | scotch cuts compact blocks: 3.26 → 2.92 s/step (−10.5 %); mapped onto the node, 2.90 (−0.7 %) | `decomposition-subdomains-baseline-vs-basic` | 0:40 | 新規 |
| 11 | BASIC RESULTS | −21 % on 4 nodes, and the profile shows why | `tab10_basic_before_after` | 0:35 | 9枚目 |
| 12 | MEMORY BANDWIDTH SETS THE SPEED | Half the memory channels: 2.2× slower. Half the cores: no change | `fig19_cores_or_memory` | 0:45 | 12枚目をここへ移す |
| 13 | BONUS OPTIMIZATION | The same arithmetic with fewer bytes moved | `fig25_u_in_one_pass` | 0:50 | 10枚目 |
| 14 | BONUS RESULTS | Bit-identical Cd, 10 % faster than our Basic | `tab11_bonus_results` | 0:35 | 新規 |
| 15 | BONUS ANALYSIS | 4 % fewer instructions, 17 % fewer refills from DRAM | `fig17_counters` | 0:35 | 11枚目 |
| 16 | SCALING ANALYSIS | Faster at 1, 2 and 4 nodes; parallel efficiency 1.00 → 1.15 | `fig22_before_after_scaling` | 0:40 | 13枚目 |
| 17 | OPTIMIZATION IDEAS (NOT WORKED) | What did not help, and why | `tab12_not_worked` | 0:40 | 14枚目 |
| 18 | CONCLUSION | 1.40× faster on 4 nodes with the same math | 表 | 0:40 | 15枚目 |

pptxの18〜24枚目（10/08版の旧スライド）は、20・21枚目（パッチの詳細）を補足S4に残し、18・19・22・23枚目は本編と重なるので外す候補です。24枚目（再現性）はQwenと共通なので、チームで決めます。

### 1. Title（0:10）

今の1枚目のままです。

### 2. TASK OVERVIEW（0:45）

**Message:** Make the same math faster on 1, 2 and 4 nodes

- Case: steady flow around a car at 140 km/h (`simpleFoam`, OpenFOAM v2512)
- Mesh: `occDrivAerStaticMesh`, 65.3 M cells, finest near the car
- Step: fixed solver iterations → the same work every step
- Metric: average time per step (steps 2 to N) on 4 nodes; scaling on 1 / 2 / 4 nodes (40 / 80 / 150 steps)
- （足す1行）Our result on 4 nodes: 3.65 → 2.90 s/step (Basic) → 2.60 s/step (Bonus)

図：流れの動画（Boxの`flow/flow-iterations.mp4`）と、メッシュの図（今の2枚目のまま）。

メモ（45秒）：
- 車の周りの空気の流れを計算するケースを、同じ計算のまま速くする課題です。メッシュは固定で、車の近くほど細かく、車輪は回りません。
- 反復の回数が固定です（`fvSolution.fixedIter`：pはGAMGで12サイクル、Uは3成分それぞれGauss-Seidelで15回、kとωは8回）。どのstepも同じ仕事なので、1 stepの平均時間で比べられます。
- 動画は、場を書き出すための別runです。計測runは場を書き出さないので、同じ公式ケースに出力だけを足して流しました（Q22）。
- 最後に答えを先に言います：「4ノードで3.65秒だった1 stepが、Basicで2.90秒、Bonusで2.60秒になりました」。

### 3. ASPIRE-2A（0:35）

**Message:** One node has 8 NUMA domains of 16 cores, and 16 cores already fill its memory bandwidth

- Processor: 2 × AMD EPYC 7713 (Zen 3, 64 cores, 2.0 GHz); 8 NUMA domains of 16 cores; 32 MB L3 per 8 cores
- Memory: 512 GB DDR4-3200, 16 channels: 409.6 GB/s peak, about 290 GB/s measured (STREAM), already with 16 cores
- Interconnect: HPE Slingshot-10 (100 Gb/s), Dragonfly topology
- Why ASPIRE-2A: OpenFOAM writes many files. Gadi: 0.2 M files and 1 TB; ASPIRE-2A: 200 M files and 100 TB

図：`figures/fig11_node_layout.png`。下の注記2行（keeperと`numactl`）はBasicの配置の説明なので、ここでは切り取ります。

メモ（35秒）：
- pptxの「EPIC」は「EPYC」に、「4x NUMA domains」は「8 NUMA domains（ソケットあたり4）」に直します。
- 帯域はカタログ値で409.6 GB/sですが、STREAMでは約290 GB/sで、L3ごとに1コア（ノードで16コア）使うだけで飽和します（#36）。これが後の「メモリ帯域が律速」の伏線です。
- 選んだ理由はファイル数と容量の上限です（Q1）。OpenFOAMのビルド1つで約36,000ファイル、分割したケースごとに数千ファイルが増えます。
- ネットワークの出典：TOP500のシステム名が「ASPIRE 2A (CPU Partition) - HPE Cray EX425, AMD EPYC 7713 64C 2GHz, Slingshot-10」です（https://top500.org/system/180078/）。NSCCのページには「All nodes are connected with HPE Slingshot Interconnect (Dragonfly Topology)」とあります（https://www.nscc.sg/aspire-2a/）。100 Gb/sはSlingshot-10の世代のNICの速さです（NSCCのページで「100G」と書いてあるのはHigh Frequency nodesの項）。ジョブから見えるNICはMellanox製（mlx5）で、UCXとOFIのどちらも使えます。

### 4. BASELINE SETTINGS（0:35）

**Message:** We start from the case defaults, on our own build of v2512

- Build: official v2512, GCC 11.2 `-O3`, AMD AOCL-LibM; Cray MPICH 8.1.15 over UCX
- Modules: `PrgEnv-gnu/8.3.3`, `aocl/4.0.0`, `cray-mpich-ucx/8.1.15`
- Decomposition: case-default `hierarchical`, (16 8 1) / (16 8 2) / (16 8 4) on 1 / 2 / 4 nodes
- Placement: 128 ranks per node, one per core, bound by the launcher (`mpiexec --cpu-bind depth`)
- Measurement: at least 3 jobs per condition; each point is one job

図：`decomposition/panels/hierarchical-car-subdomains.png`と`hierarchical-side-subdomains.png`（座標軸に沿った薄い板）。scotchとmultiLevelの絵は10枚目と13枚目まで見せません。今の4枚目の3列の絵（`decomposition-subdomains.png`）は、18枚目の振り返りに回します。

メモ（35秒）：
- OpenFOAMは公式のソースから自分たちでビルドしました。サイトのモジュールと同じ速さで（−0.08 %、Q8）、何を使ったかを正確に記録でき、Bonusのパッチも当てられます。ccacheで、作り直しは60分から5分半になりました。
- UCXにした理由（pptxのメモのとおり）：既定のOFIでは、9月に2・4ノードのrunが毎回`MPI_Finalize`でSIGBUSになり、UCXでは全runが完走しました。主催者が後で見つけた2つの回避策も、私たちの構成ではUCXより遅いです（+0.77 %、+0.50 %。Q16）。
- 配置はサイトの推奨どおりの起動方法です。「ここで頼んだ固定が、実は外れていた」が7枚目につながります。

### 5. BASELINE RESULTS（0:30）

**Message:** 3.65 s/step on 4 nodes: linear scaling, but slow and unsteady

- 4 nodes: 3.65 s/step, 7 % slower than the organisers' hierarchical run (3.415)
- 1 → 4 nodes: 4.0× faster (parallel efficiency 1.00)
- The same setup varies by 8 % between jobs (3.53–3.82 s/step)

図：`figures/fig23_baseline_scaling.png`

メモ（30秒）：
- 「スケーリングはきれいだが、遅く、ばらつく」。ばらつきは、固定が外れて遅いrankが毎回違う場所に出るためで（#36の症状）、7枚目で原因を示します。
- 1ノードの分割は(16 8 1)で、主催者の(16 4 2)と違います（図の注記）。
- 同じ日に流したBasicの対照は、10/05〜06の平均から0.2 %以内でした。だから10/05〜06に測ったBasic・Bonusと並べられます。#36の3本（10/02〜03、平均3.670）とも0.5 %で合います。

### 6. HOW WE MEASURE AND PROFILE（0:35、新規）

**Message:** Benchmark runs give the numbers; separate profile runs explain them

| Tool | When it runs | Question it answers |
|---|---|---|
| Official metric | Every benchmark run, with no profiler; at least 3 jobs per condition, alternated with a control | How long does a step take? |
| IMB-MPI1 | After the solver, in every benchmark run | How fast is the network between these nodes? |
| CrayPAT | Separate profile runs (4 nodes, 40 steps) | Which MPI calls take the time, on each rank? |
| OpenFOAM profiling | Separate profile runs | Which solver stage takes the time, on every rank? |
| AMD uProf | Separate profile runs | Which functions use the CPU? Hardware counters |
| `/proc` in the job | Separate profile runs | Is each rank on its own core? Where is its memory? |

下に1行：A change is kept only if every run with it beats every run without it, alternated in the same period.

図：`figures/tab09_how_we_measure.png`（上の表）。`tab06_profiling`は古い結果が入っているので使いません。

メモ（35秒）：
- プロファイラは1 stepの時間を−1 %〜+6 %変えます（baselineでは、CrayPATの下で3.85秒、計測runで3.65秒）。だからプロファイルの時間は比較に使わず、「どこで」「なぜ」にだけ使います。
- 40 stepで足りる理由：反復回数が固定なので、どのstepも同じ仕事です。
- 道具は、それぞれ1つの問いに答えます。CrayPATはMPIの関数ごとの時間と回数、OpenFOAM組み込みのprofilingは区間ごとの時間を全512 rankで、uProfは関数ごとのCPU時間とハードウェアカウンタ、`/proc`は実行中のCPUの固定とメモリのページの置き場所です。
- ネットワークは、毎回のrunでsolverの後にIMB（MPIのベンチマーク）を流し、そのノードどうしの帯域と大域和の時間を記録しています。ネットワーク側だけを変える比較もしました（補足S16、Q31）。NICやスイッチのハードウェアカウンタは読んでいません。
- メモリコントローラのカウンタは、利用者には読めません（`perf_event_paranoid=2`）。そこで帯域は、rankの置き場所を変える実験で確かめました（12枚目）。
- 採否の決め方：候補と対照を同じ時期に交互に流し（4ノードで3本以上ずつ）、候補の全runが対照の全runより速いものだけを採用しました。採用した変更は、4ノードではどれもこれを満たします。run間のばらつきは4ノードで約0.2 %なので、0.7 %の差（scotchの対応付け、5本ずつ）でも区別できます。最初は「1 %以上」も条件にしていましたが、ばらつきが小さいとわかってから外しました。

### 7. BASELINE ANALYSIS（0:50）

**Message:** The binding is lost at MPI_Init, so ranks compute unevenly and wait for each other

図：`figures/fig24_baseline_chain.png`（3つの箱を矢印でつなぐ）
1. Binding lost at MPI_Init (`/proc`): 0 of 512 ranks on their own core; 9 % of a rank's memory on its own NUMA domain
2. Uneven computation (OpenFOAM profiling): 54–115 s per rank in 40 steps, slowest / median 1.46
3. Everyone waits (CrayPAT): MPI is 46 % of the time, `MPI_Waitall` 55 % and `MPI_Allreduce` 35 % of it

図の下の1行：Why one slow rank matters: every solver iteration exchanges halos and takes a global sum, about 1,600 global sums per rank per step.

スライドに小さく1行（任意）：The hottest functions are sparse-matrix sweeps: Gauss–Seidel, residual, A·x (uProf).

今の6枚目の表（`tab08_baseline_profile`）は、道具の列が6枚目と重なるので使いません。`tab07_baseline_mpi_calls`は補足S1へ移します。

メモ（50秒）：
- 回数が多いのは隣のrankとのデータ交換（`MPI_Isend`・`MPI_Irecv`、rankあたり40 stepで56.6万回）ですが、時間を使っているのは`MPI_Waitall`（43.1秒、MPIの55 %）と`MPI_Allreduce`（27.6秒、35 %）、つまり他のrankを待つ呼び出しです。
- rankごとのMPI時間は35〜112秒です。セル数はほぼ完全に均等（最大でも平均+0.002 %）なので、この差は仕事の量ではなく待ちです。
- 原因は`/proc`で分かりました。512 rankのどれも自分のコアに固定されておらず（全員が256 CPUのどこでも動ける）、自分のNUMA領域にあるページは中央値8.7 %でした。8領域に均等に散れば12.5 %なので、ほぼ散らばっています。起動時に頼んだ固定が、`MPI_Init`の途中で外されていました。
- OpenFOAM固有の点（サブ領域どうしが接する面）：隣り合うサブ領域が接する面（processor面）の値を、Gauss-Seidelの1回ごと、残差の計算ごとに交換し、残差の大きさは全rankで足し合わせます。固定反復なので、1 stepにUで15回×3成分、kとωで8回ずつ、pでGAMGを12サイクル（最も粗い段ではPCGを35回）回します。rankあたり1 stepに約14,000回の送信と約1,600回の大域和です。512 rankが1 stepに千回以上そろうので、どこか1つのrankが遅いと全員が待ちます。
- 交換する量（processor面の数）が律速なのではありません。ノード間の面を92 %減らしても、ネットワークの帯域を55 %上げても、速くなりませんでした（17枚目、Q29）。
- 計算の中身はuProfで見ました。上位はGauss-Seidelの平滑化、残差、行列とベクトルの積で、どれも疎行列を1回なめる処理です（8枚目と12枚目のメモリ帯域の話へ）。
- 出典：CrayPAT 38219766511、OpenFOAM profilingと`/proc` 38219862855、uProf 38219770656（#62）。

### 8. OPTIMIZATION STRATEGY（0:35）

**Message:** Keep memory near each core, give every rank the same work, and move fewer bytes

| Bottleneck | Measured (4 nodes) | Our strategy |
|---|---|---|
| **Memory bandwidth** | Main limit: half the bandwidth → 2.2× slower; half the cores → no change | Move fewer bytes (Bonus) |
| **Memory placement** | 0 / 512 ranks pinned; 9 % of memory local | Pin each rank's CPU and memory (Basic) |
| **Load imbalance** | MPI 46 % of the time, mostly waiting | scotch (Basic), multiLevel (Bonus) |
| Network | 55 % more bandwidth, or 92 % fewer faces between nodes: no change | — |
| Computation | Compiler options: within 0.13 % | — |
| File I/O | 0.01 % of a step | — |
| OS noise | 0.8 % of each core's time | — (needs root) |

図：上の表。太字の3行に色を付けます（#52のメモ）。

メモ（35秒）：
- 計算の中心は疎行列のsweepで、毎回すべてのセルと面を読むので、演算に対して運ぶデータが多く、メモリ帯域で速さが決まります。さらに毎回の大域和のせいで、一番遅いrankが全体の速さを決めます。ネットワーク、演算、ファイルI/Oの影響は小さいと測りました。
- ネットワークの行：ノード間の転送方式をRCに替えて帯域を55 %上げても、rankの並べ替えでノード間の面を92 %減らしても、1 stepは変わりませんでした（補足S16）。
- そこでBasicでは「メモリを近くに置き、仕事をそろえる」、Bonusでは「運ぶデータを減らす」を狙いました。
- 1行目の根拠（配置を変える実験）は12枚目で見せます。ここでは結論だけ言います。
- BasicとBonusの線引きを1文で言います：Basicはソースを変えず、ビルド、ジョブスクリプト、配置と、分割はhierarchicalかscotchまで。Bonusはソースの変更と、それ以外の分割方法です。
- OSノイズは、割り込みの処理に各コアの時間の0.8 %が使われていることです（#46）。変えるにはrootが要ります。

### 9. BASIC OPTIMIZATION (1/2): CPU AND MEMORY PINNING（0:50）

**Message:** Putting the lost binding back: 3.65 → 3.26 s/step (−11 %)

- Cause: the launcher pins each rank, but the binding is removed from outside during `MPI_Init`.
- Fix, in the job script only: each rank starts under `numactl --membind=<its NUMA domain>`; one watcher per node re-pins each rank to its core with `taskset`.
- Both are needed (4 nodes, scotch): CPU only 3.47, memory only 4.38, both 2.92 s/step.

図：`figures/fig06_pinning.png`

メモ（50秒）：
- 要点は「頼んだ配置」と「実際の配置」を区別したことです。起動コマンドの指定は正しく、外れていたのは実行中の`/proc`を見て分かりました。
- Linuxは、ページを最初に書いたコアの近くに置き、後から動かしません（first touch）。データを確保する時点でrankが正しい場所にいないと、データは遠いメモリに置かれたままになります。
- CPUだけ戻すと、戻すまでの12〜16秒に確保したデータが遠くに残ります（3.47）。メモリだけ縛ると、CPUが別の領域へ動き、全部のアクセスが遠くなります（4.38）。
- `LD_PRELOAD`で`MPI_Init`の直後に固定する方法も同じ速さですが、Basicでは使えません。そこでジョブスクリプトだけでできるこの形にしました（F1：job script、rank placement、affinity）。全ジョブのログで、各ノード128/128 rankが固定されています。
- −11 %は、hierarchicalのまま固定だけを足した同時期の比較です（3.670 → 3.257、10/02〜03。このときの固定は`LD_PRELOAD`で、Basicの`numactl`＋`taskset`と同じ速さ）。図はscotchでの比較で、固定なしの各方式は16〜19 %遅くなります。

### 10. BASIC OPTIMIZATION (2/2): DECOMPOSITION（0:40、新規）

**Message:** scotch cuts the mesh into compact blocks: 3.26 → 2.92 s/step (−10.5 %); mapped onto the node, 2.90 (−0.7 %)

- hierarchical cuts thin slabs along the axes; some ranks near the car get many wall faces and more work (imbalance 1.16).
- scotch cuts compact blocks: 32 % fewer faces between subdomains (4.31 M → 2.93 M), imbalance 1.06.
- 3 jobs each, alternated: −10.5 % on 4 nodes, −2.5 % on 2, −1.3 % on 1.
- Mapped onto the node (`scotchCoeffs`: 2 sockets, 4 NUMA domains, 16 cores): 23 % / 21 % / 10 % fewer faces between nodes / sockets / NUMA domains; 2.918 → 2.898 s/step on 4 nodes (−0.69 %, 5 jobs each, alternated). No change on 1 and 2 nodes.

図：`decomposition/decomposition-subdomains-baseline-vs-basic.png`（hierarchicalとscotchを左右に並べ、車体表面、中心断面、横断面の3段。見出しにサブ領域間の面の数とセル数の偏り）。縦に長いので、上の2段だけ切り取って使ってもかまいません。時間の数字は`fig05_decomposition_basic`のものです。

メモ（40秒）：
- 不均衡は、rankの計算時間の最大/中央値です（CrayPAT、どちらも固定あり）。hierarchicalの不均衡は、壁の面（車の表面）の数と相関しました（#38）。セル数はほぼ完全にそろっているので、そろっていないのは面の仕事です。
- scotchにすると、中央値のrankの`MPI_Waitall`は18.7秒から9.4〜10.8秒に半減しました。
- ノード間の通信が理由ではありません。rankの並べ替え（`MPICH_RANK_REORDER_METHOD=3`）でノード間の面を92 %減らしても、変わりませんでした（+0.1 %）。
- 測り方の教訓をここで1つ話します：9/27の1本（5.03秒）が遅く、一度はscotchを捨てました。同じ時期に交互に3本ずつ流すと10.5 %速く、判断を覆しました。以来、1本では決めません（Q3）。
- ノード数が多いほど効く理由は確かめていません（Q30）。
- scotchの係数（`domains`、`domainWeights`、`strategy`）で、分割をノードの木（ソケット、NUMA領域、コア）に対応付けました。サブ領域間の面の総数は3 %増えますが、ノード・ソケット・NUMA領域をまたぐ面は23 %・21 %・10 %減ります。10/05の3本ずつの比較では−0.82 %で、当時の1 %の基準に届かず見送りました。採点はBasicの4ノードの再実行なので、10/15に交互に5本ずつ測り直し、全runが対照より速い−0.69 %で採用しました（#63）。1・2ノードではほぼ変わりません。絵は対応付けの前のscotchです。

### 11. BASIC RESULTS（0:35）

**Message:** −21 % on 4 nodes, and the profile shows why

| 4 nodes | Baseline | Basic |
|---|---:|---:|
| s / step (jobs) | 3.65 (3) | **2.90 (5): −21 %** |
| Spread between jobs | 8 % | 0.18 % |
| Ranks on their own core (`/proc`) | 0 / 512 | 512 / 512 |
| Memory on its own NUMA domain (median, `/proc`) | 9 % | 58 % |
| Computation per rank, max / median (OpenFOAM profiling; Basic before the mapping) | 1.46 | 1.06 |
| MPI share of the time (CrayPAT; Basic before the mapping) | 46 % | 19 % |

図：`figures/tab10_basic_before_after.png`（上の表）。1・2ノードの−8 %、−14 %は16枚目で見せます。

メモ（35秒）：
- 固定と分割で、遅いrankがいなくなり（最大/中央値1.46 → 1.06）、待ち（MPI 46 % → 19 %）とrunごとのばらつき（8 % → 0.18 %）が減りました。
- 出典：s/stepはbaselineが#62、Basicは10/15の5本（#63）。プロファイルの2行は、対応付けの前のBasic（scotchの既定）のrunです。対応付けで4ノードのstepは0.7 %しか変わらないので、そのまま使います。`/proc`はbaselineが全512 rank（#62）、Basicはノード0の128 rank（#36 A3）。OpenFOAM profilingはbaselineが#62、Basicが#57。CrayPATはbaselineが#62、Basicが37176272426（#36 A4）。
- 固定後も自分の領域にあるページが58 %なのは、共有ライブラリやMPIの共有バッファのように、複数のrankが使う部分は1つの領域にしか置けないためと考えていますが、確かめていません。「各rankのデータ（メッシュと場）を自分の領域に置いた」と言います。
- 残った19 %のMPIも、多くは遅いrankを待つ時間です（Q2、Q21）。

### 12. MEMORY BANDWIDTH SETS THE SPEED（0:45、Bonusの前へ移す）

**Message:** After Basic, memory bandwidth sets the speed: half the channels → 2.2× slower; half the cores → no change

- Memory-controller counters are not readable, so we moved the ranks instead (4 nodes, every rank pinned).
- Half the cores, on all 16 memory channels: × 0.99–1.02.
- Half the channels and L3, the same ranks and split: × 2.11–2.20, as much as the measured bandwidth drops (× 2.22).
- The sparse-matrix sweeps do about 0.1 flop per byte, about 1/100 of what would keep the cores busy (4.1 TFLOP/s ÷ 290 GB/s ≈ 14 flop/byte).

図：`figures/fig19_cores_or_memory.png`

メモ（45秒）：
- 「Basicで置き場所と均等さを直した。では今、何が速さを決めているか」という問いから始めます。
- ASPIRE-2Aでは、利用者がメモリコントローラのカウンタ（DRAMの帯域）とIBSを読めません（`perf_event_paranoid=2`）。そこで、rankの置き場所だけを変えました（#61）。
- 実験（4ノード、150 step、各2本）：(a) 1ノード128 rankを64 rankにし、16本のメモリチャネルと16個のL3はそのまま使う（コアだけ半分）。(b) 同じ64 rank・同じ分割のまま、使うチャネルとL3を半分（8本・8個）にする。(a)は−1 %〜+2 %でほぼ変わらず、(b)は2.11〜2.20倍でした。同じノードで測ったtriadの帯域は、(b)で1/2.22です（274、279、125 GB/s/ノード）。
- 解釈：演算や、コアごとのメモリ要求の待ち時間（レイテンシ）で決まるなら、(a)で約2倍遅くなるはずです。そうならず、(b)で帯域と同じだけ遅くなったので、時間を決めているのはメモリ帯域です。
- 限界：(b)はL3も半分にしているので、DRAMの帯域とL3の容量の寄与は分けられません（どちらもメモリ側の資源です）。
- 演算密度（3行目、Q35）：Gauss-Seidel、残差、Amulは、内部の面1つにつき約4 flopの計算に、係数2つ（16 B）と番地（4 B）とセルの値を合わせて30〜40 Bを読みます。約0.1 flop/Bです。ノードの倍精度ピーク（128コア × 2.0 GHz × 16 flop ≈ 4.1 TFLOP/s）をSTREAM（約290 GB/s）で割った境目は約14 flop/Bなので、その約1/100です。演算器はほとんど待っていて、IPCは0.4〜0.7です。
- だから次の一手は「運ぶデータを減らす」です。コンパイラやフラグ、PGOが±0.13 %以内しか変えなかったこととも合います（17枚目）。

### 13. BONUS OPTIMIZATION（0:50）

**Message:** The same arithmetic with fewer bytes moved

- A split that follows the machine: `multiLevel` (4 2 4 16) = nodes, sockets, NUMA domains, cores
- Four source changes that move fewer bytes:
  - no copies in the linear solvers
  - the three velocity components read the shared matrix once, not three times
  - no boundary updates whose result is thrown away
  - face values formed inside the summation loops, not in temporary fields
- Same math: every arithmetic expression and its order are kept

図：`figures/fig25_u_in_one_pass.png`（2つ目の変更を例に、行列を3回読むか1回読むか）。1 stepのどこに効くかを見せたいときは`fig13_solver_flow`を補足に置きます。

メモ（50秒）：
- 12枚目の「帯域が律速」から来た方針です。メモリを速くするのではなく、運ぶデータを減らします。
- Bonusになる理由：hierarchical・scotch以外の分割方法と、ソースの変更はBonusです（F2）。
- multiLevelは、ノード → ソケット → NUMA領域 → コアの順に、各段をscotchで分けます。ノードとNUMA領域ごとにまとまった塊になり、サブ領域間の面は2.81 Mで、scotchの既定の2.93 M、Basic（対応付けたscotch）の3.02 Mより少なくなります（絵は`decomposition/decomposition-numa-basic-vs-bonus.png`）。
- 例は図の1つだけ話します。速度Uの3成分は、同じ行列（面ごとの係数と、どのセルどうしをつなぐかの番地）を使います。元のコードは成分ごとに行列を読み直していたので、1回読んで3成分を更新するようにしました。各成分の演算と順番は同じです。
- ほかの3つも同じ考え方です。線形ソルバーが毎回作っていた一時的な配列とそのコピーをやめた。結果を捨てていた境界の値の計算と交換をやめた。面の値を一時的な配列に作ってから足すのをやめ、足すループの中で作るようにした。
- 変更の中身の全文は、提出物の`bonus/README.md`とpatchにあります（補足S4。提出物ではpatchに0001〜0004の番号が付いています）。

### 14. BONUS RESULTS（0:35、新規）

**Message:** Bit-identical Cd, and 10 % faster than our Basic

| Nodes (steps) | Basic s / step | Bonus s / step | Bonus vs Basic | `coefficient.dat` vs the pre-change baseline |
|---|---:|---:|---:|---|
| 1 (40) | 13.365 (3 jobs) | 11.668 (3 jobs) | −12.7 % | bit-identical |
| 2 (80) | 6.372 (3 jobs) | 5.641 (3 jobs) | −11.5 % | bit-identical |
| 4 (150) | 2.898 (5 jobs) | 2.599 (3 jobs) | −10.3 % | bit-identical |

- Pre-change baseline: the same multiLevel split and rank counts, with the source changes removed. Each change was also checked on its own.

図：`figures/tab11_bonus_results.png`（上の表）。変更ごとの効果（`fig03_changes_4node`）は補足S3です。

メモ（35秒）：
- R3の4点のうち、「証拠」と「Basicに対する速度向上」がこの1枚です（「何を変えたか」「なぜ同じ計算か」は13枚目）。
- ビット一致する理由：浮動小数点の演算そのものと順番を変えていないからです。変えたのは、メモリの持ち方と、捨てられていた仕事だけです。
- 4ノード512 rankでは、4つの変更をすべて外したbaselineと、最終Bonusの`coefficient.dat`がビット一致しました（SHA-256 `8952a056…`）。
- ログも同じです。反復回数が固定（`tolerance 0`、`relTol 0`）なので、U・k・omegaの残差と連続の式の誤差は解に戻らず、`coefficient.dat`の比較では見えません。ソースの変更のうちno copies in the solvers、U components in one pass、no unused boundary updatesの3つは、ちょうどそこを触ります。そこで提出物の`simpleFoam.log`（`bonus/f3-baseline/`と`bonus/results/`）を比べました。全stepの残差（16桁）、反復回数、連続の式の誤差、kとomegaのboundingの値が、1/2/4ノードとも全行一致しました（371、771、1,475行）。違うのは、ホスト名、パス、日時と時間の行だけです。
- multiLevelだけの変更（ソースは未改変）は、ルール上はSanity checkで確かめます。80 stepのCdは0.323で目安より少し低いですが、scotchの既定（0.327）も主催者のscotchも同じです。Basic（対応付けたscotch）は0.334です（Q12）。
- 変更ごとの効果を聞かれたら補足S3を出します。4ノードで、multiLevel −1.5 %（scotchの既定に対して）、ソースの変更が順に−3.4 %、−2.3 %、−1.3 %、−2.8 %です（どれも直前の構成を対照に、同じ時期に3〜4本ずつ）。別々の実験なので足し合わせません。合計の効果は、上の表で直接測っています。

### 15. BONUS ANALYSIS（0:35）

**Message:** 4 % fewer instructions, 17 % fewer refills from DRAM: the same math with less data moved

- Hardware counters (AMD uProf, 1 node, 2 jobs each side): cycles −10.8 %, instructions −4.1 %, L1 refills from DRAM −17.2 %.
- CrayPAT (4 nodes): computation per rank −9 % with the last three changes; MPI time unchanged.
- The less memory bandwidth per core, the more the source changes gain: −7.9 % on all channels, −11.4 % on half of them (4 nodes).

図：`figures/fig17_counters.png`

メモ（35秒）：
- 「計算は同じで、DRAMから運ぶデータが減った」ことの直接の根拠です。命令数は4 %しか減らないのに、DRAMからのrefillは17 %減り、cyclesは11 %減りました。IPCは0.36 → 0.39です。
- 言い過ぎない点：数えているのはL1のdemand refillで、DRAMの転送バイト数ではありません（uncoreのカウンタは権限がなく使えません）。カウンタは1ノードだけです。
- 4ノードでは、カウンタの代わりに配置の実験で確かめました（#61）。同じ分割・同じ64 rank/ノードで、全チャネルを使うとソースの変更は−7.9 %、半分のチャネルでは−11.4 %です（現行の128 rank/ノードでは−9.5 %）。1コアあたりの帯域が少ないほど効くので、効果は運ぶデータを減らしたことによるものです。
- CrayPATの値：最初の変更（no copies in the solvers）だけを入れたBonusから最終Bonusまで、rankあたりの計算時間は104.2秒から94.9秒（40 step）。MPIは約23.5秒のままです。

### 16. SCALING ANALYSIS（0:40）

**Message:** Faster at 1, 2 and 4 nodes; parallel efficiency 1.00 → 1.15

- Against our baseline: Basic −8 / −14 / −21 %, Bonus −20 / −24 / −29 % on 1 / 2 / 4 nodes.
- Parallel efficiency, 1 → 4 nodes: baseline 1.00, Basic 1.15, Bonus 1.12.
- Basic gains most on 4 nodes (scotch: −1.3 / −2.5 / −10.5 %); the source changes gain most on 1 node, where each rank holds 4× more data (U in one pass: −6.4 % on 1 node, −2.3 % on 4).

図：`figures/fig22_before_after_scaling.png`

メモ（40秒）：
- ルールが求める「1/2/4ノードのscaling」と「4ノードのbefore/after」を、この1枚で見せます。
- Basicの効果がノード数とともに大きくなるのは、主に分割の効果です（scotchが1/2/4ノードで−1.3/−2.5/−10.5 %）。理由は確かめていません（Q30）。
- ソースの変更の効果が1ノードで大きいのは、rankあたりのデータが4倍あり、DRAMから来る量が多いからだと説明します。15枚目の「1コアあたりの帯域が少ないほど効く」と同じ向きです。
- 効率が1を超える理由は、カウンタで確かめました（#66、対応付けの前のBasic、uProf、1/2/4ノード）。1セル・1 stepあたりのサイクルは、4ノードで1ノードの0.84倍、DRAMからのL1 refillは0.70倍です。減ったのは、面の番地を通してセルの配列を飛び飛びに読み書きする疎行列の計算（平滑化、残差、行列とベクトルの積）で、DRAMからのrefillが60〜70 %減ります。この配列はrankあたり1ノードで4 MB、4ノードで1 MBになり、コアあたり4 MBのL3に収まります。
- 1・2ノードの変更ごとの値の多くは1本どうしの比較なので、本編では傾向だけ言います（補足S3）。

### 17. OPTIMIZATION IDEAS (NOT WORKED)（0:40）

**Message:** What did not help, and why

| Idea | Result (4 nodes) | Why it did not help |
|---|---|---|
| Compiler flags (`-march=znver3`, AOCC, `-O2`, LTO), GCC PGO | within ±0.13 % | The loops wait on memory, not on instructions |
| MPI transport: OFI with the organisers' workarounds, UCX over RC, OpenFOAM comm switches | −0.16 % to +0.77 % | MPI time is waiting for the slowest rank, not transfer |
| Rank reordering (92 % fewer inter-node faces) | +0.1 % | The same: fewer bytes between nodes do not shorten the wait |
| GAMG coarsest level on fewer ranks | −0.25 % to +4.95 % | 81 % of the global sums, but about 0.6 % of the time |
| Weighted cells (×2, ×12), METIS with two constraints | +1.5 % to +6.1 % | Uneven cell counts, or more processor faces |
| malloc thresholds | −0.4 % (3 runs) | Too small to separate with 3 runs; not re-tested |
| SMT (2 ranks per core) | 5.7× slower | Stalls of minutes; cause not isolated |

下に2行：
- Why no gain? None of them moves fewer bytes, and memory bandwidth sets the speed.
- Why not combine them? Gains we cannot separate from the run-to-run spread may be luck; stacking them would be overfitting.

図：`figures/tab12_not_worked.png`（上の表）。全部の一覧（`tab04_not_adopted`）は補足S8です。

メモ（40秒）：
- 一覧を指して、理由は2つにまとまると言います。1つはどれも運ぶデータを減らさないこと（速さを決めているのはメモリ帯域）。もう1つは、MPIの時間の多くが遅いrankを待つ時間で、通信を速くしても待ちは減らないことです。
- UCXのRCはIMBの帯域を55 %上げましたが、1 stepは−0.01 %（Basic）でした。GAMGの最も粗い段は`MPI_Allreduce`の呼び出しの81 %を出しますが、時間はstepの約0.6 %です。
- 重み付けは、セル数を崩してかえって遅くなりました（Q4、Q5）。
- 小さな改善を組み合わせない理由：run間のばらつき（4ノードで約0.2 %）と区別できない改善は、たまたま速かったrunかもしれません。確かめないまま積み重ねると、そのrunに合わせることになります（過学習）。採用したのは、同じ時期に交互に流して全runが対照より速かったものだけです（6枚目）。0.7 %のscotchの対応付けも、5本ずつ流して確かめてから採用しました（10枚目）。mallocの閾値（−0.4 %、3本）は、測り直していません。

### 18. CONCLUSION（0:40）

**Message:** 1.40× faster on 4 nodes with the same math

| s / step | 1 node | 2 nodes | 4 nodes |
|---|---:|---:|---:|
| Baseline | 14.57 | 7.43 | 3.65 |
| Basic | 13.36 (−8 %) | 6.37 (−14 %) | **2.90 (−21 %)** |
| Bonus | 11.67 (−20 %) | 5.64 (−24 %) | **2.60 (−29 %)** |

- What worked: memory next to each core (pinning, −11 %), the same work for every rank (scotch, −10.5 %; mapped onto the node, −0.7 %), fewer bytes per step (4 source changes −9.5 %, multiLevel −1.5 %); each against its own control.
- What remains: memory bandwidth still sets the speed (half the channels: 2.1× slower even with the Bonus); MPI is 19 % of a step, mostly waiting, because ranks still differ by 6 % in computation.

図：上の表。分割の絵を添えるなら`decomposition/decomposition-subdomains.png`（hierarchical → scotch → multiLevel）にし、キャプションで固定とソースの変更にも触れます。

メモ（40秒）：
- 最初と最後で同じ数字を言います：「同じ計算のまま、4ノードで3.65秒から2.60秒、1.40倍です」。
- 効いたことの%は、それぞれ同時期の対照に対する値で、足し合わせません。
- 残る律速：配置の実験では、Bonusでもチャネル半分で2.11倍遅く、速さを決めているのは最適化の前後でメモリ帯域です。rankの計算時間の差（最大/中央値1.06）は、セル数では説明できず、壁の面で一部だけ説明できます（Q21）。
- 最後の一言：「Basicで置き場所と仕事の均等さを直して21 %、Bonusで運ぶデータを減らしてさらに10 %」。

---

## 削るとき（Qwenに時間を回すとき）

- 6枚目を7枚目に入れる：`tab08_baseline_profile`（道具、測ったもの、結果の3列）を7枚目に置き、6枚目の「計測runとプロファイルrunを分けた」は4枚目の最後の行に1文で足します（−35秒）。
- 15枚目を14枚目に入れる：カウンタは14枚目に1行（DRAM refill −17 %、命令 −4 %）だけ書き、`fig17_counters`は補足S6にします（−35秒）。
- 8枚目の表を、太字の3行だけにします（−10秒）。

## 時間が余ったら（足せる話）

- 4ノードで1つずつ足した経路（`fig16_journey`、補足S13）：どの順で何をして、いくつ速くなったかを1枚で見せます。始点は#36の3.670です。
- 測り方の教訓（`fig08_variability`、補足S12）：同じ構成のrunの多くは中央値から±0.4 %に入りますが、9月には84 %、91 %遅い単発のrunがありました。
- 数えなかった高速化（補足S17）：固定反復のときだけ効く−13 %です。結論の後に「おまけ」として見せられます。

---

## 補足（質疑用）

### S1. MPI calls in the baseline（#62）

図：`figures/tab07_baseline_mpi_calls.png`

- The most frequent calls are halo exchanges (`MPI_Isend`, `MPI_Irecv`: 566,107 per rank in 40 steps); the time goes to `MPI_Waitall` (43.1 s, 55 % of MPI) and `MPI_Allreduce` (27.6 s, 35 %).
- After Basic, the same three calls lead by count, and the time order swaps (`MPI_Allreduce` 48 %, `MPI_Waitall` 38 %).

### S2. Where a step goes after Basic, and where the imbalance is（#57）

図：`figures/fig18_step_breakdown.png`

- OpenFOAM's built-in profiling (`profiling {}` and the `parProfiling` function object), Basic, 4 nodes, a 40-step diagnostic run with every rank's results.
- Computation per rank (loop time minus Pstream time): median 97.95 s, max 104.17 s (max/median 1.063) over 40 steps.
- Correlation with the computation: cell count r = +0.06 (balanced within 1 %), wall faces r = +0.43, processor faces r = −0.16; both together explain 27 %.
- Ranks with fewer wall faces wait longer at the start of the next solve (U r = −0.72, omega r = −0.60); the wall shear stress function object grows with the wall faces (r = +0.76).

### S3. Effect of each Bonus change（4 nodes, and by node count）

図：`figures/fig03_changes_4node.png`（4ノード、各変更を直前の構成と同じ時期に3〜4本ずつ）、`figures/fig04_changes_by_nodes.png`（1/2ノードの値の多くは1本どうしの比較。ラベルにrun数を書いてあります）

### S4. The source changes in detail

図：`figures/tab03_bonus_changes.png`、`figures/fig13_solver_flow.png`（1 stepのどこに効くか）。提出物のpatchのファイル名は、上から順に0001〜0004です。

- No copies in the solvers (0001): `smoothSolver` uses the in-place `lduMatrix::residual`; GAMG forms its finest-level residual with one `subtract(r, source, Apsi)`.
- U components in one pass (0002): `smoothSolver::solveGaussSeidelComponents` smooths the three U components in one pass over the shared matrix arrays.
- No unused boundary updates (0003): `fvc::surfaceIntegrateInternal` builds only the internal field at six call sites that read only internal values; `gaussConvectionScheme::fvmDiv` builds lower, upper and diagonal in one face loop.
- Fused face loops (0004): with `linear` interpolation, `gaussGrad` forms the face value inside the face-sum loop; `surfaceIntegrateInternal(a, b)` forms the face product inside the integration loop.

### S5. Profiles before and after the source changes（#53）

図：`figures/fig09_mpi_breakdown.png`（3行の版）、`figures/fig10_rank_compute.png`

- From the Bonus with only the first change (no copies in the solvers) to the final Bonus, computation per rank falls 8.9 % (104.2 → 94.9 s); MPI stays at about 23.5 s.
- The spread between ranks stays (max/median 1.07).

### S6. Hardware counters before and after the patches（#55）

図：`figures/fig17_counters.png`

- 1 node, 128 ranks, 40 steps, multiLevel (2 4 16); AMD uProf `data_access` on one rank per NUMA domain; 2 runs with the four source changes (fa4f5b0) and 2 without (the same commit with `patches/openfoam/` removed).
- Computation only (MPI, UCX and Pstream left out), mean of 7 ranks: cycles −10.8 %, instructions −4.1 %, L1 data accesses −5.8 %, L1 refills from DRAM −17.2 %, from L2 −0.2 %, L2 accesses including prefetches −9.6 %; IPC 0.360 → 0.388.
- Two runs of the same side agree within about 4 % on every counter. Both sides give the same `coefficient.dat` (Cd 0.43827636195043501).

### S7. Cores or memory? We moved the ranks, not the code（#61）

図：`figures/fig19_cores_or_memory.png`、`figures/fig20_memory_placement.png`

- ASPIRE-2A users cannot read the memory-controller counters or IBS (`perf_event_paranoid=2`), so we changed only where the ranks run. 4 nodes, 150 steps, 2 runs per condition (2026-10-10), every rank pinned to its CPU with its memory on that CPU's NUMA domain.
- full128: 128 ranks per node (the submitted placement). spread64: 64 ranks per node, 4 per L3, on all 16 L3s and 16 memory channels. packed64: the same 64 ranks and decomposition, 8 per L3, on 8 L3s and 8 channels.
- Triad on the same nodes after the solver: 274 / 279 / 125 GB/s per node.

| s / step | full128 | spread64 | packed64 | spread64 / full128 | packed64 / spread64 |
|---|---:|---:|---:|---:|---:|
| Basic (before the mapping) | 2.920 | 2.887 | 6.347 | 0.99 | 2.20 |
| Bonus without the patches | 2.869 | 2.874 | 6.321 | 1.00 | 2.20 |
| Bonus | 2.595 | 2.649 | 5.598 | 1.02 | 2.11 |
| patches (Bonus against the line above) | −9.5 % | −7.9 % | −11.4 % | | |

- `coefficient.dat` is bit-identical between spread64 and packed64 of each configuration, and between the baseline and the Bonus at every placement. Every rank stayed on its CPU (keeper 64/64 or 128/128 on every node).

### S8. Not adopted (full list)

図：`figures/tab04_not_adopted.png`、コンパイラとフラグの比較は`figures/fig07_compiler_options.png`（pptxの17枚目）

### S9. Against the organisers' reference (1, 2 and 4 nodes)

図：`figures/fig14_vs_organiser_reference.png`

- Organisers' setup (ASPIRE-2A notes, tasks 4.3): site module, `mpirun` with no options, default MPI settings, no binding.
- Against their `scotch` mean: Basic −8 / −13 / −12 %, Bonus −19 / −23 / −21 % on 1 / 2 / 4 nodes.

### S10. The submitted scripts reproduce the results（#54、#63）

- The official sources downloaded from their public URLs, built with `build/build.pbs`, every run started with `run/submit.sh`: Bonus on 2026-10-07 (Actions 37584763848), Basic again on 2026-10-16 after the mapping was added (Actions 38843636251).
- At 1, 2 and 4 nodes `coefficient.dat` is bit-identical to the recorded runs. s/step: Bonus within 0.21 % of the recorded means; Basic 0.24 – 0.36 % slower, on other hosts on another day (4 nodes: 2.9046 against 2.8976).
- Both CrayPAT profiles (2026-10-07; Basic before the mapping, final Bonus): 3.065 and 2.701 s/step under CrayPAT against 3.063 and 2.712; the same number of MPI calls per rank.

| | 1 node | 2 nodes | 4 nodes |
|---|---:|---:|---:|
| Basic, re-run (recorded mean) | 13.413 (13.365) | 6.390 (6.372) | 2.905 (2.898) |
| Bonus, re-run (recorded mean) | 11.644 (11.668) | 5.650 (5.641) | 2.601 (2.599) |

### S11. OFI against UCX under our placement（#56、#60）

- Basic configuration (before the mapping) on 4 nodes, only the MPI transport changed; 3 runs each, alternated in the same period (2026-10-07).
- UCX (main): 2.9176, 2.9168, 2.9246 s/step, mean 2.9197. OFI with `FI_OFI_RXM_USE_SRX=0`: 2.9452, 2.9374, 2.9438, mean 2.9421 (+0.77 %).
- All 6 runs VALID, every step returned 0 (no SIGBUS), the same `coefficient.dat` Cd (0.28404934573921931).
- OFI's own spread is also 0.26 %, so the narrow spread of our runs does not come from UCX (Q15).
- The organisers' other workaround, `FI_VERBS_PREFER_XRC=0` (2026-10-09, one run each beside a UCX run): 2.9338 against 2.9192 s/step (+0.50 %), the same Cd, no SIGBUS.

### S12. Measuring honestly（#47）

図：`figures/fig08_variability.png`

- 92 runs in 29 repeated configurations (2026-09-21 to 10-05): most lie within ±0.4 % of their configuration's median.
- But single runs were 84 % and 91 % slower in September.
- run内のstep間の標準偏差と、run間のばらつきは別物です。150 stepを150個の独立な標本として扱いません。遅い回の原因をホストだけに断定しません（同じホストで後に正常なrunがあります）。

### S13. The path on 4 nodes

図：`figures/fig16_journey.png`

- start (case-default split, binding lost) 3.670 → pinning 3.257 → scotch 2.915 → mapped onto the node = Basic 2.898 → Bonus 2.599. Each step was measured against its own control in the same period.
- 始点は#36の3本（10/02〜03）で、本編のbaseline 3.65（#62、10/12）と同じ構成です。

### S14. Build, storage and MPI

図：`figures/fig15_storage_flow.png`、`figures/tab05_environment.png`

- Build: official v2512 source, GCC 11.2 with `-O3`, AMD math library, in a 1-node PBS job (16 cores). Every run records which build it used.
- Storage: `/scratch` (Lustre, shared) holds the mesh, builds and run directories; every node copies the decomposed case into its own node-local `$TMPDIR`, and the solver reads and writes only there (`-hostRoots`, `-ioRanks`). File I/O in the timed steps is about 0.01 % of the run time.
- MPI: Cray MPICH 8.1.15 over UCX instead of the default OFI provider.

### S15. Experiment automation

図：`figures/fig12_pipeline.png`

### S16. Is the network the bottleneck? No（#36、#48、#56、#58、#60）

図：`figures/tab13_network_checks.png`

- We changed only the network side, four ways; none made a step more than 0.25 % faster (table).
- One 8-byte global sum over 512 ranks takes about 12 µs (IMB), so the 1,600 global sums of a step cost about 0.02 s, under 1 % of a step. The rest of the MPI time is waiting.
- Each rank's wait (`MPI_Waitall`) is explained by its own computation (R² 0.77); adding its number of neighbours and of neighbours on other nodes raises that only to 0.80. The ranks that set the step have almost no neighbours on other nodes (13 of the 16 slowest have none).
- Not measured: NIC and switch counters.
- （メモ）rankごとの`MPI_Isend`の回数は、分割から数えた隣のrankの数と相関+1.000で、1つの隣に1 stepあたり約1,324通を送っています。メッセージの数は分割で決まり、待ちは計算の不均衡で決まります（#48）。

### S17. Found but not claimed: residual norms that the fixed iterations never use（#68）

本編の最後に「おまけ」として見せるかは、チームで決めます。

**Message:** −13 % on 4 nodes and bit-identical, but only because the benchmark fixes the iterations, so it is not part of our Bonus

- `fvSolution.fixedIter` sets `tolerance 0` and `relTol 0` for U, k and omega, and `minIter = maxIter = 35` for the coarsest-level PCG. The convergence check can never stop a solve early, so the residual norm computed after every sweep (a residual pass and a global sum) is only used after the last one.
- A patch computes it once, after the last iteration: 2.250 against 2.595 s/step on 4 nodes (−13.3 %, 3 runs each, ranges not overlapping). `coefficient.dat` is bit-identical at 1, 2 and 4 nodes, and all 1,323 solver log lines (every residual and iteration count) are identical.
- Why we do not count it: it helps only the benchmark's fixed-iteration setting. The case's other dictionary, `fvSolution.fixedTol` (the production-like setting), runs the original code. The rules also prohibit "less work per step", and the skipped norms could be read as work.

図：なし（数値だけ）。

メモ：
- 固定反復はベンチマークの取り決めです。ケースのREADME（OpenFOAM HPC Challenge OHC-1）は、hardware trackでは`fvSolution.fixedIter`を使い、software trackは`fvSolution.fixedTol`（pはtolerance 1e-7・relTol 0.01、U・k・ωは1e-8・0.1、普通の運用値）から始めるように書いています。
- 考え方自体はOpenFOAMにもあります。v2512の`smoothSolver`は、`nSweeps`が負のときは決まった回数だけ回し、残差を計算しません。このパッチは、ベンチマークの書き方（tolerance 0、relTol 0、maxIter）で同じことをし、ログに出る最初と最後の残差は残します。
- 言い方：「過学習」というより「計測の取り決めにだけ効く高速化」（Goodhartの法則の例）です。ほかの設定で遅くなることはなく、条件を満たせばどの入力でもビット一致しますが、普通の運用では効きません。Bonusの4つの変更は、どの収束設定でも捨てられる計算を省いたもので、`fixedTol`でも効きます。この線引きを言えるのが、この1枚の価値です。
- わかったこと：512 rankでは、毎回の収束判定（残差の計算とその大域和）だけで、Bonusの1 stepの約13 %を使っています。
- 数値：1ノード10.29 s/step（Bonusの11.67から−11.8 %）、2ノード4.93（5.64から−12.7 %）、各1本。今のBasic（2.898）からは、4ノードで−22.3 %です。
- 出典：#68、branch `experiment/issue68-skip-unused-residuals`（e2e2ae8、最終Bonus fa4f5b0の上）、patch `0005-skip-unused-convergence-residuals.patch`。

---

## 想定問答

英語の回答は、質疑で言う形の下書きです。

**Q1. Why ASPIRE-2A?**
- Last year we competed on Gadi, so this year we wanted to learn the other contest machine.
- Storage. OpenFOAM works with very many files: one unpacked OpenFOAM tree is about 36,000 files, and every decomposed 65M case adds thousands of `processor*` files. Our Gadi project has 1 TiB and about 212,000 files on `/scratch`; in August, three runs setting up at the same time already hit that file limit. On ASPIRE-2A we have 100 TB and 200 million files, so we could keep the builds, the decomposed cases and the raw records of every run.
- （メモ）Gadiの利用停止のことは自分からは言いません。「ノードが空いていた」は言いません（今回、4ノードは4時間以上、qdevの1ノードは3時間以上待った記録があります）。数字の出典は`platforms/gadi/README.md`（inode上限212,100、2026-08-17の3件同時の`Disk quota exceeded`）と、ASPIRE-2Aの`lfs quota`（100 TB、2億inode、2026-10-07）です。

**Q2. MPI waiting is large. Why didn't MPI tuning help?**
- Most of the MPI time is waiting: ranks that finish early wait at the next exchange or global sum. Per-rank MPI time ranges from 20 to 37 s. Library or switch tuning cannot remove that wait; only less work or better balance can. The OpenFOAM communication switches we tried gave no gain. Two later checks agree: UCX over RC raised the IMB bandwidth between nodes by 55 % but changed a step by −0.01 % (Basic) and −0.16 % (Bonus), and moving the GAMG coarsest level, which issues 81 % of the `MPI_Allreduce` calls, from 512 ranks to 32 changed it by −0.25 %.

**Q3. Why did you first reject scotch and then adopt it?**
- One run on 2026-09-27 took 5.03 s/step, an outlier from a slow period. When we alternated three runs of each in the same period, scotch was 10.5 % faster. Since then we never decide from a single run.

**Q4. Is equal cell count enough?**
- It mattered most. When we weighted cells by their face and point work, the cell counts became uneven and it got slower (+2.2 %, +6.1 %). A METIS two-constraint split balanced faces better but added 18 % processor faces (+1.46 %). The remaining imbalance (max/median 1.07) is still open.

**Q5. Why did the weighting make it worse?**
- Static weights moved cells away from an even split: the cell-count imbalance grew to 1.073 with weight ×2. With ×12, the top-level split broke down and the faces between nodes grew five times.

**Q6. Why are the effects different on 1, 2 and 4 nodes?**
- On 1 node each rank holds four times more data than on 4 nodes, so more of it comes from DRAM. Removing array passes therefore saves more on 1 node (reading the U matrix once instead of three times: −6.4 % against −2.3 %). On 1 node we measured it: with the patches, L1 refills from DRAM fall 17 % while instructions fall 4 %. On 4 nodes we tested the same idea by giving each core less memory: with 64 ranks per node the patches gain 7.9 % on all memory channels and 11.4 % on half of them. The same reasoning explains the super-linear scaling, and there we measured counters at 1, 2 and 4 nodes: per cell and step, the L1 refills from DRAM fall by 30 % from 1 to 4 nodes, almost all in the sparse-matrix kernels, whose scattered cell arrays shrink to 1 MB per rank and fit in L3.

**Q7. What is proven and what is not?**
- Proven: the timings (same-period controls, 3 or more runs on 4 nodes), bit-identical `coefficient.dat` and identical solver logs (every residual, to 16 digits), and the pinning problem (seen in `/proc` during the solve).
- Shown by experiment on 4 nodes: the step time follows the memory bandwidth, not the number of cores (half the cores: −1 % to +2 %; half the memory channels: 2.1–2.2× slower, as the bandwidth drops 2.22×), and the patches gain more when each core has less memory.
- Measured with hardware counters (1 node): the patches cut L1 refills from DRAM by 17 % with 4 % fewer instructions.
- Not proven: the DRAM traffic in bytes and the share of the peak bandwidth (we cannot read the memory-controller counters), and how much of the memory effect is DRAM bandwidth and how much is L3 capacity. We present those as hypotheses. (The cache explanation of the super-linear scaling is now measured with counters at 1, 2 and 4 nodes; see Q6.)

**Q8. Why rebuild OpenFOAM instead of using the site module?**
- A single run with the site module gave the same speed (−0.08 %). Our own build records exactly what ran, and the Bonus patches need a build anyway.

**Q9. Is AOCL-LibM allowed in Basic?**
- It is a math library linked through `FOAM_EXTRA_LDFLAGS`. Precision stays IEEE double, and we use no value-unsafe flags.
- （メモ）関数によっては最後の桁がglibcと違い得ます。Basicの範囲かを聞かれたら、ビルド設定（F1）の範囲と考えていると答えます。

**Q10. Is multiLevel used in Basic?**
- No. Basic uses `scotch`, mapped onto the node's sockets and NUMA domains through the method's own settings (`scotchCoeffs`), which F1 leaves free in Basic. `multiLevel` is a different decomposition method, so it is part of the Bonus.

**Q11. Did profiling affect the benchmark numbers?**
- No. Profiles come from separate diagnostic runs. Benchmark runs have no profiler.

**Q12. Why is the 80-step Cd below the reference?**
- Cd after 80 steps depends on the decomposition. The organisers' own `scotch` run on ASPIRE-2A also gives 0.327 at 80 steps, and their notes say that `hierarchical` and `scotch` differ by 0.7 %, 3.0 % and 3.5 % at 40, 80 and 150 steps. Our Basic (`scotch` mapped onto the node) gives 0.334, `scotch` with its defaults 0.327, and the Bonus (`multiLevel`) 0.323. Against `scotch` with its defaults, the mapping moves Cd by +0.8 %, +2.1 % and +3.2 % and `multiLevel` by +0.5 %, −1.3 % and +2.6 %, no more than the organisers' two methods differ from each other. The Bonus value is identical to its unmodified baseline, so the gap does not come from our source changes.
- （メモ）主催者の値は`tasks/4.3 OpenFOAM Application Notes - ASPIRE-2A.md`の表と「What Cd tells you」です（2ノード80 stepでhierarchical 0.336869、scotch 0.327130）。目安の0.34は、OHC-1の別の機械での値（0.334〜0.345）です。

**Q13. Why is your Cd different from the organisers' reference?**
- With `scotch` and its defaults our Cd at 150 steps was 0.284049, against 0.283983 in the organisers' `scotch` runs (a relative 2.3e-4). When we ran the site module once with our own scripts and decomposition, we got their value exactly (0.28398300763231610). So that difference comes from our build (for example, we link AMD's math library), not from the decomposition or the method. Our final Basic maps the decomposition onto the node, and a different decomposition moves Cd at 150 steps: 0.293016 (+3.2 %).

**Q14. The organisers saw a signal 7 (SIGBUS) at the end of 2- and 4-node runs. Did you?**
- No. That comes from the default OFI provider at `MPI_Finalize`. Our job scripts use Cray MPICH over UCX, and every step of every run returned 0.

**Q15. Why is your run-to-run spread so much smaller than the organisers'?**
- Our 5 Basic runs on 4 nodes lie within 0.18 %; the organisers' 5 `scotch` runs spread over 12 %. It is not UCX: our runs with the organisers' transport (OFI with `FI_OFI_RXM_USE_SRX=0`) also lie within 0.26 %. The main remaining difference is the placement — every rank pinned with its memory on its NUMA domain. Our own baseline without working pinning varied by 8 % (3.53–3.82 s/step).

**Q16. Why UCX and not the site's default OFI?**
- In September, every 2- and 4-node run with the default OFI provider died with SIGBUS at `MPI_Finalize`, while UCX completed every run. The organisers have since found that `FI_OFI_RXM_USE_SRX=0` avoids the crash, so we compared again with everything else as in Basic (then without the mapping): 3 alternated 4-node runs each, OFI 2.942 against UCX 2.920 s/step (+0.77 %, ranges not overlapping), the same Cd, no crash. Their other workaround, `FI_VERBS_PREFER_XRC=0`, was +0.50 % (one run each), also with the same Cd. So UCX stays.

**Q17. Is the pinning fix allowed in Basic?**
- Yes. It is job-script placement: `numactl` sets the memory policy before each rank starts, and `taskset` sets the CPU affinity from outside. F1 lists job scripts, rank placement and affinity as Basic. We did not use `LD_PRELOAD`, which would be Bonus work.

**Q18. Can the organisers reproduce your Basic number?**
- Yes. `build/build.pbs` builds from the official public sources, and `run/submit.sh 1|2|4` runs the whole Allrun chain with plain `qsub`. We re-ran them ourselves (Bonus on 2026-10-07, the final Basic on 2026-10-16): at every node count `coefficient.dat` was bit-identical to our recorded runs, and the time within 0.4 % of our recorded means (Basic on 4 nodes: 2.9046 against 2.8976 s/step).

**Q19. Why did you not tune the hierarchical coefficients instead?**
- We kept the case default `(16 8 4)` as the control. scotch was 10.5 % faster on 4 nodes in alternated runs, so we spent the remaining effort on scotch and on placement. We have not searched other `nHierarchical` factorisations.

**Q20. What would you do next?**
- The remaining imbalance between ranks (Q21): balance each stage of a step, for example with weights from measured per-rank times. Making the global sums cheaper (the GAMG coarsest level on fewer ranks) or the network faster (UCX over RC) did not help (Q2).
- Moving fewer bytes, the other lever: fusing the assembly of U, k and omega across terms, or the GAMG residual with its restriction. We expect a few per cent from these, not another 10 % (Q34).

**Q21. Do you know where the imbalance between ranks comes from?**
- Partly. With OpenFOAM's own profiling on all 512 ranks, the computation per rank still varies by 6 % (max/median 1.063). Cell counts are balanced within 1 % and do not explain it; wall faces explain a little (r = 0.43, 2.8 % of the work). Balancing the wall part perfectly would only take it to 1.056, so a wall-weighted split is not worth it. Nodes and NUMA domains show no systematic difference; the variation follows groups of neighbouring subdomains, so it is a property of the mesh regions. Hardware counters on 32 ranks of 4 nodes (#66) show what it is: the slowest and the fastest rank execute about the same number of instructions, but the slowest reads more than twice as many lines from DRAM. A rank's computation follows its DRAM refills (r = +0.69), not its instructions (r = −0.09) or its cells (r = +0.24): it depends on how well each subdomain's data fits in cache.

**Q22. Is the flow video from your scored run?**
- No. Benchmark runs write no flow fields (`controlDict.noWrite`), so the video comes from a separate run of the same official case with output function objects added. Only the outputs were added; the case, the mesh and the solver settings are the official ones.

**Q23. How do you know it is memory-bound if you could not read the memory counters?**
- On ASPIRE-2A users cannot read the memory-controller counters, so we tested it by moving the ranks. On 4 nodes, 64 ranks per node are as fast as 128 when they keep all memory channels, and 2.1–2.2× slower when the same 64 ranks share half of the channels — as much as the measured bandwidth drops. Compiler flags and PGO change nothing (within 0.13 %), and our patches, which keep every operation, gain the most where memory is scarcest.
- （メモ）コアを半分にした比較は、分割が512から256に変わります。ただ、帯域に比例しない部分は1 stepあたり約0.1 sしかないので、分割の違いで「コアが半分でも同じ速さ」を説明することはできません。チャネルを半分にした比較は、分割もrankも同じです（#61）。

**Q24. Bandwidth or latency?**
- Bandwidth. If the latency of each core's memory requests set the speed, halving the cores would halve the throughput; it changed by −1 % to +2 %. Halving the memory channels slowed a step 2.1–2.2×, in line with the bandwidth (2.22×).
- （メモ）1コア2 rankのSMT（#43）では5.7倍遅くなり、どちらとも決められませんでした。今回の配置の実験で決まりました。

**Q25. Most demand refills come from L2. Isn't the data in cache?**
- Demand refills do not count hardware prefetches. The arrays we stream are brought from DRAM into L2 by the prefetcher, so their loads show up as L2 hits. With the patches, L2 accesses including prefetches fall 10 % and DRAM refills 17 %.

**Q26. MPI is 19 % of a step. How can the step follow the bandwidth?**
- Most of the MPI time is waiting for the slowest rank, and that rank's computation is bandwidth-bound, so the wait grows and shrinks with it. When we halved the memory channels, the whole step slowed with the bandwidth; only about 0.1 s per step does not scale with it.

**Q27. Why was your baseline slower than the organisers' hierarchical run (3.65 against 3.415 s/step)?**
- Our baseline asked the launcher to pin each rank, but the binding was removed during `MPI_Init`, and each rank's pages ended up spread over all eight NUMA domains (9 % on its own). The organisers' runs ask for no binding. We think that is why ours was slower, but we have not isolated it, because the build and the MPI transport also differ.

**Q28. Are 40-step profile runs representative? Do the profilers change the result?**
- With fixed iterations every step does the same work, so 40 steps show the same pattern as 150. The profilers change a step by −1 % to +6 %, so we never use profiled times as results. Every number we report comes from runs without a profiler.

**Q29. In OpenFOAM, isn't the exchange across subdomain boundaries the bottleneck?**
- Not by volume. Each subdomain exchanges the values on its processor faces at every solver iteration, but cutting the faces between nodes by 92 % changed a step by +0.1 %, and 55 % more network bandwidth (UCX over RC) by −0.01 %. What costs time is the synchronisation: about 1,600 global sums per step make every rank wait for the slowest one, and the slowest ranks have almost no neighbours on other nodes. So we fixed the placement and balanced the work instead.

**Q31. Did you profile the network?**
- Yes, at three levels. Every benchmark run ends with an MPI benchmark (IMB) on the same nodes, so we know the bandwidth and the global-sum time of each job. CrayPAT gave the time and count of every MPI call on every rank, and each rank's message count matches its number of neighbours in the decomposition exactly. Then we changed only the network side: 55 % more bandwidth (UCX over RC), 92 % fewer faces between nodes, another transport (OFI). None made a step more than 0.25 % faster. A rank's wait follows its own computation (R² 0.77), not its neighbours. We did not read NIC or switch counters.

**Q30. Why does the Basic gain grow with the node count?**
- Mostly through the decomposition: scotch gains 1.3 %, 2.5 % and 10.5 % on 1, 2 and 4 nodes, and mapping it onto the node gains only on 4 nodes (0.7 %). We think the axis-aligned cuts of hierarchical become more uneven when the subdomains are small, but we have not verified it.

**Q32. Your third change skips boundary updates. Isn't skipping boundary checks prohibited?**
- It skips no check. At six places the code formed a surface integral (a divergence), built its boundary values, exchanged them across processor boundaries, and then used only the cell values. We form the same cell values with the same loop and skip only the boundary values that nobody reads. The boundary conditions of the solved fields, every exchange the solution uses, and the bounding of k and omega are unchanged; the bounding appears in our logs as often and with the same values as in the baseline.
- （メモ）R2の禁止事項は「skipping boundary or validity checks」です。no unused boundary updatesは、内部の値しか使わない6か所（ラプラシアンの非直交補正、bounded対流項の`fvm::Sp`、補正付き対流項、連続の式の誤差、`pEqn.H`の右辺、kOmegaSSTの`divU`）で、`fvc::div`と`fvc::surfaceIntegrate`を`fvc::surfaceIntegrateInternal`に置き換えるだけです。中身は同じ`surfaceIntegrate`のループで、境界値を作って評価する処理（coupled境界の交換を含む）だけを省きます。

**Q33. Instructions fell 4 %. Did you reduce the work per step?**
- Not the numerical work. Every solve does the same sweeps, residuals and norms as before: in the logs of the baseline and the Bonus, every solve of every step has the same iteration count and the same residuals, to 16 digits. The instructions we removed are copies, allocations and temporary face fields, the second and third pass over the same matrix arrays, and boundary values that nobody reads.
- （メモ）命令数−4.1 %に対して、DRAMからのrefillは−17.2 %、cyclesは−10.8 %です（S6）。ログの比較は14枚目のメモにあります（1/2/4ノードで371、771、1,475行が全行一致）。

**Q34. Is another 10 % possible?**
- Not with the same math and the same work per step, we think. A step follows the memory bandwidth (12th slide), so only moving fewer bytes or reusing more data from cache can help. Our remaining ideas — fusing the assembly of U, k and omega across terms, the GAMG residual with its restriction, the Laplacian coefficients with the diagonal — each remove a pass or two over the face arrays: a few per cent together. Gains of 10 % need a different computation (fewer iterations, lower precision), which the rules prohibit, or a change that only the benchmark's fixed iterations allow (S17).
- （メモ）Basicでは、#61でノードあたり64 rank（全チャネル）が128 rankより1.1 %速かった（対応付けの前、各2本）程度です。Gauss-Seidelの複数sweepを、更新の順序を保ったままキャッシュの中で回す（temporal blocking）なら大きく減らせる可能性はありますが、非構造メッシュではまだ研究の段階です。

**Q35. Can you show a roofline?**
- Not a measured one on ASPIRE-2A. The DRAM bytes need the memory-controller counters, which users cannot read, and the core counters miss the lines that the prefetchers bring in. What we can say: the sparse-matrix sweeps do about 0.1 flop per byte, about 1/100 of the ridge point of a node (4.1 TFLOP/s ÷ 290 GB/s ≈ 14 flop/byte), so they sit far under the bandwidth roof, and halving the bandwidth makes a step 2.2× slower.
- （メモ）rooflineの図を描くなら、帯域の屋根（290 GB/s）と、0.1 flop/Bの縦線までです。達成した性能の点は、FLOPを数えていないので置けません。

---

## 発表の準備

- pptxに反映すること：
  - 3枚目：「EPIC」→「EPYC」、「4x NUMA domains」→「8 NUMA domains (4 per socket)」。
  - 4枚目：図をhierarchicalの絵だけにします（3列の絵は18枚目へ）。
  - 6枚目（新規）と10枚目（新規）、14枚目（新規）を作ります。
  - 今の12枚目（HOW DID WE IDENTIFY MEMORY BOUND）をBasic RESULTSの後ろへ移します。
  - 今の14枚目（効かなかったこと）：mallocの行を「−0.4% (3 runs, not re-tested)」に、下の行を「Gains we cannot separate from the run-to-run spread may be luck. Stacking them would be overfitting」に直します（6枚目と17枚目の言い方と同じ）。
  - 補足S17（#68）を入れるなら、結論の後に置きます。
- 新しい図はBoxに置いてあります。`figures/`の`tab09`〜`tab13`、`fig24`、`fig25`、`fig19`、`fig20`と、`decomposition/`の`decomposition-subdomains-baseline-vs-basic.png`（NUMAで色分けした版も）です。パッチ番号を消した版で、`fig03`、`fig04`、`fig09`、`fig10`、`fig13`、`fig16`、`fig17`、`fig20`、`tab03`〜`tab06`も置き換えました。
- 本編18枚を、タイマーで通しで練習します。各スライドに「時間が足りないときの1文」を決めておきます。
- 話す人と交代の位置を決めます（Qwenとの切り替えも）。
- 数値は提出物の`README.md`と同じものを使います（2.898 / 2.599 / −10.3 %、3.296）。baselineは3.65です。
- 補足スライド（S1〜S17）は本編の後ろに置き、質疑ですぐ出せるようにします。
- 図の文字が小さければ、`.svg`を開いて拡大するか、pptxの側で注記を大きく書き直します。

## 根拠

- 図の元データ：リポジトリの`presentation/openfoam/data/`。主催者の参照値は`tasks/4.3 OpenFOAM Application Notes - ASPIRE-2A.md`とそのログ（`tasks/4.3-aspire2a-logs/`）。
- 実験の記録：issue #36〜#38（Basic）、#42、#44、#50、#51（Bonus）、#41、#53（profile）、#46（I/O、OSノイズ）、#47（ばらつき）、#48、#49（通信）、#54（提出スクリプトの再現）、#55（カウンタ）、#56、#60（OFIとUCX）、#57（OpenFOAM組み込みのprofiling）、#58（UCXのRC、GAMGの最も粗い段）、#59（PGO）、#61（コアとメモリのどちらが律速かを、配置だけを変えて確かめた実験）、#62（baselineの1/2/4ノードとプロファイル）、#63（Basicのscotchの対応付け）、#66（ノード数ごとのカウンタ、rank間の不均衡）、#68（固定反復で使われない残差）。
- 提出物：Boxの`Tokyo_Rapids_with_RIKEN_Submission/openfoam/`。
