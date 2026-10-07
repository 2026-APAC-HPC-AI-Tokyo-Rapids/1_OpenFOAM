# OpenFOAMパートのスライド構成（案）

チームのデッキ（`Tokyo Rapids with RIKEN Presentation.pptx`）の2枚目にある構成案に沿って、OpenFOAMパートの中身を書いたものです。

- スライドに載せる文は英語、話す内容（メモ）は日本語です。
- 図と表は`figures/`にあります（`.png`は貼り付け用、`.svg`は編集用）。作り直すときは、リポジトリで`uv run presentation/openfoam/figures.py <出力先>`を実行します。
- 数値はすべて公式指標`Average wall-clock time per time step`（2 step目以降の平均、秒/step）です。1点は1ジョブです。
- 持ち時間（Qwenと合わせて発表15〜20分、質疑10分）の配分はチームで決めます。下の目安では、OpenFOAMの本編が約9分です。

| # | タイトル | 主な図 | 目安 |
|---|---|---|---|
| 1 | Task, metric and rules | ParaView（#39） | 1分 |
| 2 | ASPIRE-2A node | `fig11_node_layout` | 0.5分 |
| 3 | What one step computes | `fig13_solver_flow` | 1分 |
| 4 | Baseline: where the time goes | `fig09_mpi_breakdown`（Basicの行） | 1分 |
| 5 | Measuring honestly | `fig08_variability` | 0.5分 |
| 6 | Basic 1: CPU and NUMA placement | `fig06_pinning` | 1分 |
| 7 | Basic 2: decomposition | `fig05_decomposition_basic` | 0.5分 |
| 8 | Bonus: move less data | `fig03_changes_4node`、`tab03_bonus_changes` | 1.5分 |
| 9 | Same math: F3 | `tab02_f3_check` | 0.5分 |
| 10 | Final performance and scaling | `fig01_final_runs`、`fig02_scaling` | 1分 |
| 11 | What did not work | `fig07_compiler_options`、`tab04_not_adopted` | 0.5分 |
| 12 | Summary | なし | 0.5分 |
| S1〜S5 | Supporting | 下に記載 | 質疑用 |

---

## 1. Task, metric and rules

**Message:** We made the official 65M-cell DrivAer case run faster on 4 nodes, without changing the computation.

- Case: `occDrivAerStaticMesh`, 65,334,765 cells, `simpleFoam` (steady SIMPLE, k-omega SST).
- Runs: 1 / 2 / 4 nodes with 40 / 80 / 150 steps. Score: the 4-node average wall-clock time per step.
- Basic: unmodified OpenFOAM v2512, `hierarchical` or `scotch` only. The organisers re-run it.
- Bonus: anything else that keeps the math. We prove it ourselves (F3: Cd against our own pre-change baseline).
- Result: 4 nodes, Basic **2.920 s/step**, Bonus **2.599 s/step** (−11.0 %).

図：ParaViewの画像か動画（#39、Ackvyさん）。

メモ：
- ParaViewの図は、場を書き出すための別runで作ったものです。計測runとは別だと一言添えます。
- 最初に結果を予告して、以降は「どう見つけたか」を話す流れにします。

## 2. ASPIRE-2A node

**Message:** One node has 8 NUMA domains of 16 cores. We run one rank per core and keep each rank's memory on its own NUMA domain.

- 2 × AMD EPYC 7713 (Zen 3), 128 cores, 8 NUMA domains (16 cores each), 32 MB L3 per 8-core CCX.
- 128 MPI ranks per node, SMT not used. Cray MPICH 8.1.15 over UCX.
- The case is copied to node-local storage on every node; each node reads and writes its own copy.

図：`figures/fig11_node_layout.png`

メモ：
- ASPIRE-2Aを選んだ理由はチームで書き足します。記録に残っていません（想定問答のQ1）。
- この図の木構造が、BonusのmultiLevel分割`(4 2 4 16)`につながります（スライド8）。

## 3. What one step computes

**Message:** Each step assembles and solves the U, p and k-omega equations. The loops stream large arrays, and MPI is used for halo exchanges and global sums.

- Preparation (not timed): decomposePar → restore0Dir → renumberMesh → potentialFoam → applyBoundaryLayer.
- Timed: simpleFoam steps 2 to N. U (smoothSolver + GaussSeidel), p (GAMG), k and omega (smoothSolver), then function objects (forces → Cd).
- Orange labels: where our Bonus patches act.

図：`figures/fig13_solver_flow.png`

メモ：
- 公式の時間は、準備工程を含まない（2 step目以降のsimpleFoam）ことをはっきり言います。
- パッチの番号は、ここでは場所を示すだけにして、中身はスライド8で話します。

## 4. Baseline: where the time goes

**Message:** In Basic, about 80 % of the time is computation. MPI takes about 20 %, and much of it is waiting for slower ranks.

- CrayPAT, 4 nodes, 512 ranks, 40 steps (a separate diagnostic run).
- Per rank: 137.6 s in total, MPI 26.7 s (19.4 %): `MPI_Allreduce` 12.9 s, `MPI_Waitall` 10.2 s.
- MPI time per rank ranges from 20 s to 37 s: ranks that finish early wait for the slowest one.
- So we targeted (1) where memory is placed, (2) how the mesh is split, (3) how much data the loops move.

図：`figures/fig09_mpi_breakdown.png`（このスライドではBasicの行だけ。3行の版はS2）

メモ：
- 「計算・メモリ・MPI・I/Oの円グラフ」にはしません（#52）。メモリ待ちは計算の中にあり、MPI待ちには他rankの計算待ちも入っています。
- I/Oは計測区間の約0.01 %でした（#46）。

## 5. Measuring honestly

**Message:** One job is one data point. We compare against controls run in the same period, because single runs can mislead.

- 92 runs in 29 repeated configurations (2026-09-21 to 10-05): most lie within ±0.4 % of their configuration's median.
- But single runs were 84 % and 91 % slower in September.
- A single slow scotch run (5.03 s, 2026-09-27) first made us drop scotch. Alternated repeats on 10-02 showed scotch 10.5 % *faster*.
- Rule since then: 3 or more runs per side at 4 nodes, alternated in the same period; one condition per commit.

図：`figures/fig08_variability.png`

メモ：
- run内のstep間の標準偏差と、run間のばらつきは別物です。150 stepを150個の独立な標本として扱いません。
- 遅い回の原因をホストだけに断定しません。同じホストで後に正常なrunがあります（#47）。

## 6. Basic 1: CPU and NUMA placement

**Message:** The launcher's CPU and memory binding was removed during `MPI_Init`. Restoring it without `LD_PRELOAD` avoided a 17–20 % loss.

- Seen in `/proc` during the solve: every rank allowed on all 256 CPUs and all 8 NUMA domains.
- Fast only when the CPU stays pinned **and** the memory is allocated on the rank's own NUMA domain.
- Adopted for Basic: each rank starts under `numactl --membind=<its NUMA domain>`, and a small per-node watcher re-pins each rank's main thread with `taskset`. Every job log confirms 128/128 ranks pinned.
- An `LD_PRELOAD` interposer is as fast, but `LD_PRELOAD` is Bonus-only, so Basic does not use it.

図：`figures/fig06_pinning.png`

メモ：
- 「設定した配置」と「実際の配置」を区別した点が要点です。外れていることは`/proc`の記録で見つけました。
- keeperだけだと遅い理由：固定が戻るまでの十数秒の間に確保したメモリが遠いNUMAに置かれ、固定を戻しても残るためです。

## 7. Basic 2: decomposition

**Message:** `scotch` beats the case-default `hierarchical` decomposition by 10.5 % on 4 nodes.

- 4 nodes: 3.257 → 2.915 s/step (3 runs each, alternated). 2 nodes −2.5 %, 1 node −1.3 %.
- Scotch's tree coefficients (`domains`, `domainWeights`): −0.82 % on 4 nodes, nothing on 1 and 2 nodes → not adopted (our threshold is 1 %).

図：`figures/fig05_decomposition_basic.png`

メモ：
- 効果が4ノードで大きく、1ノードで小さい理由（ノード間の境界）は、仮説として話します。分割の面数などの数値は#36〜#38にあります。

## 8. Bonus: move less data

**Message:** A NUMA-aware multiLevel decomposition and four patches that remove memory traffic make it another 11 % faster on 4 nodes.

- multiLevel decomposition following the machine: (nodes, sockets, NUMA domains, cores) = (4 2 4 16).
- Patches remove temporary fields, copies, repeated passes over the same arrays, and boundary exchanges whose result was discarded.
- Each change measured against the configuration just before it, in the same period (figure). Percentages are separate experiments; they are not added up.
- The gain is largest on 1 node (0002: −6.4 % on 1 node, −2.3 % on 4 nodes). This fits a memory-bound solver: with fewer nodes, more of each rank's data comes from DRAM.

図：`figures/fig03_changes_4node.png`、`figures/tab03_bonus_changes.png`（ノード数別は`fig04_changes_by_nodes`、S3）

メモ：
- 「メモリを速くする」のではなく「運ぶデータを減らす」方針に進んだ流れを話します（#52のcavity3Dの観点3）。
- DRAMの転送量はcounterで測っていません。ソース上の読み書きの削減と測った時間から言える範囲に留めます。
- 0002の前後は、擬似コードで見せると伝わりやすいです。

```
before: for c in (x, y, z): for each cell: read lower/upper/diag/addressing; update U_c
after:  for each cell: read lower/upper/diag/addressing once; update U_x, U_y, U_z
```

## 9. Same math: F3

**Message:** `coefficient.dat` is bit-identical to the pre-change baseline at 1, 2 and 4 nodes.

- Baseline: the same multiLevel decomposition and rank counts, with the patches removed (unmodified v2512).
- Every Bonus run at every node count gives the same file, byte for byte (the strongest form of F3).
- Why: the patches keep every arithmetic expression and its order; they only remove copies, temporaries and discarded work.
- Each patch was also checked on its own, at 1, 2 and 4 nodes.

図：`figures/tab02_f3_check.png`

メモ：
- multiLevelだけの変更（ソースは未改変）は、ルール上はSanity checkで確かめるものです。80 stepのCdは0.32〜0.33で、目安（0.334〜0.345）より少し低くなります。Basic（scotch）も同じなので、Bonusの変更が原因ではありません。

## 10. Final performance and scaling

**Message:** On 4 nodes, Basic runs at 2.920 s/step and Bonus at 2.599 s/step. Both scale super-linearly from 1 to 4 nodes.

| Nodes | Basic | Bonus | Bonus vs Basic |
|---|---:|---:|---:|
| 1 | 13.364 (n=3) | 11.668 (n=3) | −12.7 % |
| 2 | 6.367 (n=3) | 5.641 (n=3) | −11.4 % |
| 4 | 2.920 (n=5) | 2.599 (n=3) | −11.0 % |

- Run-to-run range: 0.35–0.38 % (Basic), 0.05–0.20 % (Bonus).
- Parallel efficiency at 4 nodes: 1.14 (Basic), 1.12 (Bonus).

図：`figures/fig01_final_runs.png`、`figures/fig02_scaling.png`（表は`tab01_final_results`）

メモ：
- 効率が1を超える理由は、rankあたりのデータがキャッシュに入りやすくなるためという仮説です。counterでは確かめていません。
- Bonusは1ノードの方が改善が大きいので、Bonusの効率はBasicよりわずかに低くなります。

## 11. What did not work

**Message:** Compiler flags, communication switches and smarter partition weights did not help. The limits are data movement and load balance.

- Compiler: `-march=znver3`, AOCC 5.0, `-O2`, LTO → within 0.13 % of the control (3 runs each).
- Weighted multiLevel cells: +2.2 % / +6.1 %. METIS two-constraint partition: +1.46 %.
- SMT (2 ranks per core): about 5.7 times slower.

図：`figures/fig07_compiler_options.png`、`figures/tab04_not_adopted.png`

メモ：
- 不採用でも「何が否定できたか」を言います。重み付けは、面や点の偏りを均すとセル数が偏り、かえって遅くなりました。

## 12. Summary

- Basic: keep each rank pinned with its memory local (avoids a 17–20 % loss), and use `scotch` (−10.5 % on 4 nodes).
- Bonus: NUMA-aware `multiLevel` plus four patches that move less data: −11.0 % on 4 nodes against our Basic, `coefficient.dat` bit-identical.
- Method: one condition per commit, same-period controls, 3 or more runs, profilers only in separate runs.
- Next: the imbalance between ranks remains (max/median 1.07); confirming the DRAM traffic with hardware counters.

---

## Supporting

### S1. Experiment automation

図：`figures/fig12_pipeline.png`。今のデッキの「実験の自動化」スライドに使えます。

### S2. Profiles before and after the patches

図：`figures/fig09_mpi_breakdown.png`（3行の版）、`figures/fig10_rank_compute.png`

- From "before 0002–0004" to the final Bonus, computation per rank falls 8.9 % (104.2 → 94.9 s); MPI stays at about 23.5 s.
- The spread between ranks stays (max/median 1.07).

### S3. Effect of each change by node count

図：`figures/fig04_changes_by_nodes.png`。1/2ノードの値の多くは、1本どうしの比較です（ラベルにrun数を書いてあります）。

### S4. Not adopted (full list)

図：`figures/tab04_not_adopted.png`

### S5. Final numbers

図：`figures/tab01_final_results.png`

---

## 想定問答

英語の回答は、質疑で言う形の下書きです。

**Q1. Why ASPIRE-2A?**
- （チームで記入）採点対象はGadiかASPIRE-2Aです。最終の計測はすべてASPIRE-2Aで行いました。選んだ理由は記録にないので、チームで決めて書き足します。

**Q2. MPI waiting is large. Why didn't MPI tuning help?**
- Most of the MPI time is waiting: ranks that finish early wait at the next exchange or global sum. Per-rank MPI time ranges from 20 to 37 s. Library or switch tuning cannot remove that wait; only less work or better balance can. The OpenFOAM communication switches we tried gave no gain.

**Q3. Why did you first reject scotch and then adopt it?**
- One run on 2026-09-27 took 5.03 s/step, an outlier from a slow period. When we alternated three runs of each in the same period, scotch was 10.5 % faster. Since then we never decide from a single run.

**Q4. Is equal cell count enough?**
- It mattered most. When we weighted cells by their face and point work, the cell counts became uneven and it got slower (+2.2 %, +6.1 %). A METIS two-constraint split balanced faces better but added 18 % processor faces (+1.46 %). The remaining imbalance (max/median 1.07) is still open.

**Q5. Why did the weighting make it worse?**
- Static weights moved cells away from an even split: the cell-count imbalance grew to 1.073 with weight ×2. With ×12, the top-level split broke down and the faces between nodes grew five times.

**Q6. Why are the effects different on 1, 2 and 4 nodes?**
- On 1 node each rank holds four times more data than on 4 nodes, so more of it comes from DRAM. Removing array passes therefore saves more on 1 node (0002: −6.4 % against −2.3 %). The same reasoning fits the super-linear scaling. We have not confirmed it with hardware counters.

**Q7. What is proven and what is not?**
- Proven: the timings (same-period controls, 3 or more runs on 4 nodes), bit-identical `coefficient.dat`, and the pinning problem (seen in `/proc` during the solve).
- Not proven: that DRAM traffic fell by the amount the source suggests, and the cache explanation of the scaling. We present those as hypotheses.

**Q8. Why rebuild OpenFOAM instead of using the site module?**
- A single run with the site module gave the same speed (−0.08 %). Our own build records exactly what ran, and the Bonus patches need a build anyway.

**Q9. Is AOCL-LibM allowed in Basic?**
- It is a math library linked through `FOAM_EXTRA_LDFLAGS`. Precision stays IEEE double, and we use no value-unsafe flags.
- （メモ）関数によっては最後の桁がglibcと違い得ます。Basicの範囲かを聞かれたら、ビルド設定（F1）の範囲と考えていると答えます。

**Q10. Is multiLevel used in Basic?**
- No. Basic uses `scotch`. `multiLevel` is a different decomposition method, so it is part of the Bonus.

**Q11. Did profiling affect the benchmark numbers?**
- No. Profiles come from separate diagnostic runs. Benchmark runs have no profiler.

**Q12. Why is the 80-step Cd below the reference?**
- Our Basic run with plain `scotch` gives 0.327 and the Bonus 0.323, against about 0.34 in the reference table. The Bonus value is identical to its unmodified baseline, so the gap does not come from our changes.

## 根拠

- 図の元データ：リポジトリの`presentation/openfoam/data/`。
- 実験の記録：issue #36〜#38（Basic）、#42、#44、#50、#51（Bonus）、#41、#53（profile）、#46（I/O）、#47（ばらつき）、#48、#49（通信）。
- 提出物：Boxの`Tokyo_Rapids_with_RIKEN_Submission/openfoam/`。
