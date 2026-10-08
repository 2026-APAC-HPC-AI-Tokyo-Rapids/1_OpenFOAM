# OpenFOAMパートのスライド構成（第2版）

チームのデッキ（`Tokyo Rapids with RIKEN Presentation.pptx`）の2枚目にある構成案に沿って、OpenFOAMパートの中身を書いたものです。

- スライドに載せる文は英語、話す内容（メモ）は日本語です。
- 図と表は`figures/`にあります（`.png`は貼り付け用、`.svg`は編集用）。作り直すときは、リポジトリで`uv run presentation/openfoam/figures.py <出力先>`を実行します。
- 数値はすべて公式指標`Average wall-clock time per time step`（2 step目以降の平均、秒/step）です。1点は1ジョブです。
- 第1版（16枚、約11分）から、採点基準に合わせて本編を9枚・約9分に絞りました。外した内容は「時間が余ったら」と「補足」に移しました。

---

## よい発表にするための方針

### 採点の仕組み（tasks/README.md R3・R4、Task RulesのPresentation Guidelines）

- OpenFOAMは50点です。
  - 審査員の点が35点：Basic 20点、Bonus 15点。
  - 性能と再検証が15点：主催者がBasicを再実行し、4ノードのAverageで順位を付けます。
- 審査員が見るもの：
  - 最適化を「flagの一覧」ではなく「問題解決の筋道」として話しているか（Presentation Excellence）。
  - ボトルネックの特定と、なぜその変更が効いたのかの説明。4ノード指標のbefore/after。1/2/4ノードのスケーリング。
  - Bonusは4点がそろっているか（R3）：何を変えたか（テキスト）、なぜ同じ計算か（審査員が確かめられる短い論拠）、証拠（自分の変更前baselineとのCd比較とログ）、自分のBasicに対する同じ機械での速度向上。
  - 説明できない結果は、速くても点になりにくい。うまくいかなかった実験でも、筋道が通っていれば評価され得る。
  - 特に堅実なBasicのチューニングには、Bonus点が付き得る。

### ここから決めた発表の方針

1. **Basicに時間を割く。** 20点あり、再実行もされます。CPU固定の発見（MPI_Initで固定が外れる）は「特に堅実なBasicのチューニング」に当たる、いちばんの見せ場です。
2. **最初に答えを言う。** 1枚目で4ノードの結果と3つの柱（配置、分割、運ぶデータ）を言い、最後にもう一度まとめます。
3. **改善ごとに同じ順で話す。** 症状 → 診断（何を測って分かったか）→ 対策 → 効果（同時期の対照、run数）→ 理由。
4. **BonusはR3の4点を1枚で見せる。** 審査員が表と照らし合わせやすいように、4つのマスに分けます。
5. **測ったことと仮説を分ける。** 例：DRAMの話は、カウンタで確かめた範囲（1ノード、demand refill）だけ言い切り、スケーリングのキャッシュ説明は仮説のままにします。
6. **数値は全スライドで同じにする。** 4ノード：出発点3.670、Basic 2.920（出発点から−20.4 %）、Bonus 2.599（Basicから−11.0 %）、主催者のscotch平均3.296。小数は3桁まで。
7. **1枚1メッセージ。** タイトルは主張の文にし、図は1つ、強調する数字は赤の1か所にします。y軸が0から始まらない図は、その旨を図の下に書いてあります。

### 時間配分

- 本編は9枚で約9分です。Qwenとの配分で時間が余れば、「時間が余ったら」の2b・4b・5bを足します（各0.5〜1分）。
- 質疑は10分（Qwenと共通）。想定問答と補足スライドで受けます。

---

## 本編（9枚、約9分）

| # | スライドの主張（タイトル） | 主な図 | 目安 | 採点上の役割 |
|---|---|---|---|---|
| 1 | Same math, faster on 4 nodes | ParaView（#39）、大きな数字 | 1:00 | 結論と3本柱 |
| 2 | One node has 8 NUMA domains; this is how we run on it | `fig11_node_layout` | 1:00 | 機械の理解 |
| 3 | Where the time goes | `fig18_step_breakdown`、`fig09_mpi_breakdown`（Basicの行） | 1:00 | ボトルネックの特定 |
| 4 | Basic 1: the launcher's pinning disappears at MPI_Init | `fig06_pinning` | 1:30 | Basic（見せ場） |
| 5 | Basic 2: scotch splits the mesh better | `fig05_decomposition_basic` | 1:00 | Basic |
| 6 | Bonus: the same arithmetic, fewer bytes moved | `fig03_changes_4node`、R3の4マス、`fig17_counters` | 1:30 | Bonus |
| 7 | Same math, proven | `tab02_f3_check` | 0:30 | Bonus（F3） |
| 8 | From 3.67 to 2.60 s/step | `fig16_journey`、`fig02_scaling` | 1:00 | before/after、スケーリング |
| 9 | What did not work, what we learned | `tab04_not_adopted`（抜粋） | 0:30 | 筋道、再現性 |

### 1. Same math, faster on 4 nodes

**Title:** Same math, faster: Basic 2.920 s/step, Bonus 2.599 s/step on 4 nodes

- Official case: `occDrivAerStaticMesh` 65M cells, `simpleFoam`, 1 / 2 / 4 nodes with 40 / 80 / 150 steps on ASPIRE-2A.
- Basic (unmodified v2512, re-run by the organisers): **2.920 s/step**, 11 % faster than the organisers' vanilla `scotch` runs (3.296).
- Bonus (multiLevel split + 4 source patches): **2.599 s/step**, −11.0 % against our Basic, `coefficient.dat` bit-identical.
- Three levers: where memory lives, how the mesh is split, how many bytes the loops move.

図：ParaViewの画像か動画（#39、Ackvyさん）と、大きな数字3つ（3.296 → 2.920 → 2.599）。

メモ（1分）：
- 最初の10秒で数字を言います：「主催者の参照3.30秒に対して、Basicは2.92秒、Bonusは2.60秒です」。
- 「同じ計算のまま速くした」ことを強調します。コンテストの標語（Make the same math faster）と同じ言葉を使います。
- ParaViewの図は、場を書き出すための別runで作ったものだと一言添えます。
- 「以降は、どう見つけたかを3本柱の順に話します」で次へ。

### 2. One node has 8 NUMA domains; this is how we run on it

**Title:** An ASPIRE-2A node has 8 NUMA domains of 16 cores — we run one rank per core

- 2 × AMD EPYC 7713 (Zen 3), 128 cores, 8 NUMA domains, 32 MB L3 per 8-core CCX; 440 GB per node.
- 128 MPI ranks per node, SMT off. Cray MPICH 8.1.15 over UCX.
- Our own build of the official v2512 (GCC 11.2, `-O3`, AMD AOCL-LibM); the decomposed case is copied to node-local storage on every node.

図：`figures/fig11_node_layout.png`

メモ（1分）：
- この木構造（ノード → ソケット → NUMA → コア）が、Basicの固定（スライド4）とBonusのmultiLevel `(4 2 4 16)`（スライド6）の両方につながる、と予告します。
- UCXを選んだ理由は1文だけ：既定のOFIは2/4ノードの`MPI_Finalize`でSIGBUSになり、UCXは全runが完走した。主催者の回避策（`FI_OFI_RXM_USE_SRX=0`）を入れたOFIも、同じ配置で0.77 %遅かった（Q16、#56）。
- ASPIRE-2Aを選んだ理由は聞かれたら答えます（Q1：去年はGadiだったこと、ファイル数と容量の上限）。

### 3. Where the time goes

**Title:** Where the time goes: memory-bound loops, and ranks waiting for the slowest one

- A step on 4 nodes (OpenFOAM's own profiling, every rank): p solve (GAMG) 26 %, U solve 22 %, k and omega 9 %, function objects 2 %, and 41 % outside the solvers (assembly, gradients, turbulence model).
- CrayPAT on 4 nodes, 512 ranks (a separate 40-step run): MPI is 19.4 % of the time; the rest is computation.
- The MPI time is mostly `MPI_Allreduce` (global sums) and `MPI_Waitall` (halo exchange), and it ranges from 20 s to 37 s per rank: early ranks wait for the slowest.
- The computation is bound by memory traffic: one core per L3 already saturates a node's memory bandwidth (STREAM, about 94 % of peak), and compiler flags change nothing (within 0.13 %).
- So: (1) keep each rank's memory next to its core, (2) give every rank the same work, (3) move fewer bytes per step.

図：`figures/fig18_step_breakdown.png`（1 stepの内訳）と`figures/fig09_mpi_breakdown.png`（Basicの行だけ）。`fig13_solver_flow`は補足に回すか、小さく添えます。

メモ（1分）：
- 「計算・メモリ・MPI・I/Oの円グラフ」にはしません。メモリ待ちは計算の中にあり、MPI待ちには他rankの計算待ちも入っているからです。
- I/Oは計測区間の約0.01 %（#46）。
- 内訳はOpenFOAM組み込みのprofilingで、4ノードの40 stepの診断runで測りました（#57）。区間の時間は経過時間で、区間内のMPIの待ちを含みます。
- 「memory-bound」の根拠は3つ：STREAMでL3あたり1 coreでもノードの帯域が飽和すること（#36、STREAMの数え方で290 GB/s、書き込み時の読み込みを含めると約387 GB/sでカタログ値409.6 GB/sの約94 %）、コンパイラやフラグを変えても0.13 %以内しか変わらないこと（#36 D）、計算部分のIPCが0.36と低いこと（#55のuProf、1ノード）。

### 4. Basic 1: the launcher's pinning disappears at MPI_Init

**Title:** The launcher's CPU and memory binding disappears at MPI_Init — putting it back saves 16–19 %

- Symptom: random slow ranks in every run; compute imbalance 1.4–1.6 and MPI at 35–43 % of the time, unrelated to the subdomains.
- Diagnosis: `/proc` during the solve showed every rank allowed on all 256 CPUs, with a median of 7 % of its pages on its own NUMA domain.
- Fix (Basic-legal, no `LD_PRELOAD`): each rank starts under `numactl --membind=<its NUMA domain>`, and one watcher per node re-pins each rank with `taskset`.
- Effect (4 nodes, scotch): 2.917 s/step against 3.40–3.47 without it (16–19 % slower); as fast as an `LD_PRELOAD` interposer. Imbalance 1.06, MPI 19 %. Every job log shows 128/128 ranks pinned.

図：`figures/fig06_pinning.png`

メモ（1分30秒）：
- 要点は「設定した配置」と「実際の配置」を区別したことです。`--cpu-bind`は正しく渡していましたが、`MPI_Init`の途中で外されていました。`/proc`の記録で見つけました。
- なぜ両方要るか：CPUだけ戻すと、戻るまでの十数秒に確保したメモリが遠いNUMAに残ります（keeperだけ：3.47）。メモリだけ縛ると、CPUが別のNUMAへ動いて、全アクセスが遠くなります（numactlだけ：4.38）。
- 固定前は「遅いrank」がrunごとにランダムに出ていました（rankのMPI時間19〜102 s）。固定後は19〜36 sに収まりました（#36、#38）。
- 経路図（スライド8）の−11.2 %は、hierarchicalで固定だけを足したときの同時期の比較です。scotchでは固定なしの各方式が16〜19 %遅く、効果は分割によって違います。聞かれたらこう答えます。
- Basicで許される範囲（F1：job script、配置、affinity）でやったことを言います。

### 5. Basic 2: scotch splits the mesh better

**Title:** scotch splits the mesh better than the case-default hierarchical — 10.5 % on 4 nodes

- 4 nodes: hierarchical (16 8 4) 3.257 → scotch 2.914 s/step (3 runs each, alternated in the same period). 2 nodes −2.5 %, 1 node −1.3 %.
- Why: the axis-aligned cuts of hierarchical give some ranks many wall faces and more work (imbalance 1.16, correlated with the wall-face count). scotch balances the work (imbalance 1.06), and the median rank's halo wait halves (18.7 → 9.4–10.8 s).
- Not why: fewer faces between nodes. Re-ordering ranks to cut those faces by 92 % changed nothing.
- One single slow run (5.03 s, 2026-09-27) first made us drop scotch. Since then: 3 or more runs per side, alternated, one condition per commit.

図：`figures/fig05_decomposition_basic.png`

メモ（1分）：
- 不均衡と境界面数の相関（hierarchicalでr = −0.37）、Waitallの減少は、CrayPATのrank別の値です（#38）。rankの並べ替え（`MPICH_RANK_REORDER_METHOD=3`）でノード間の面を92 %減らしても速さが変わらなかったので、ノード間の通信は律速ではありません（#36 B）。
- ノード数が増えるほど効く理由は確かめていません。聞かれたら「4ノードでは1 rankあたりの領域が小さく、軸に沿った切り方の偏りが目立つため、と考えているが未検証」と答えます。
- scotchの係数（`domains`、`domainWeights`）は4ノードで−0.82 %、1/2ノードで効果なし。採用の基準（1 %）に届かず不採用。
- 「1本で決めない」という測り方の話は、このエピソードで済ませます（5bの図は時間が余ったら）。

### 6. Bonus: the same arithmetic, fewer bytes moved

**Title:** Bonus: the same arithmetic with fewer bytes moved — another 11 % on 4 nodes

| What changed (as text in the submission) | Why it is the same math |
|---|---|
| `multiLevel` split following the machine: (4 2 4 16) = nodes, sockets, NUMA domains, cores. 4 patches to v2512 (0001–0004). | Each patch keeps every arithmetic expression and its order. It only removes temporary fields, copies, repeated passes over the same arrays, and boundary updates whose result was thrown away. |
| **Evidence** | **Speedup against our Basic, same machine** |
| `coefficient.dat` bit-identical to our pre-change baseline at 1, 2 and 4 nodes, and for each patch on its own. | −11.0 % (4 nodes), −11.4 % (2 nodes), −12.7 % (1 node). |

- Hardware counters (1 node, AMD uProf): with the patches, L1 refills from DRAM fall 17 % while instructions fall only 4 % — the same math with less data moved.

図：`figures/fig03_changes_4node.png`（変更ごとの前後、同時期の対照）。表は`tab03_bonus_changes`。

メモ（1分30秒）：
- 方針：「メモリを速くする」のではなく「運ぶデータを減らす」。スライド3の memory-bound という診断から来ています。
- 例を1つだけ擬似コードで見せます（0002）：

```
before: for c in (x, y, z): for each cell: read lower/upper/diag/addressing; update U_c
after:  for each cell: read lower/upper/diag/addressing once; update U_x, U_y, U_z
```

- 効果はノード数が少ないほど大きい（0002：1ノード−6.4 %、4ノード−2.3 %）。rankあたりのデータが多いほどDRAMから来る量が多いからだ、と説明します。
- カウンタ（#55、`fig17_counters`）：1ノードでパッチの有無を2本ずつ測り、計算部分（MPIを除く）で比べました。cycles −10.8 %、命令数 −4.1 %、L1アクセス −5.8 %、DRAMからのL1 refill −17.2 %、L2へのアクセス（prefetch込み）−9.6 %、IPC 0.36 → 0.39。L2からのrefillは変わりません。「計算は同じで、DRAMから運ぶデータが減った」ことの直接の根拠です。
- 言い過ぎない点：数えているのはL1のdemand refillで、DRAMの転送バイト数ではありません（uncoreの計測は権限がなく使えません）。4ノードでは測っていません。
- 各%は別々の実験で、足し合わせません。

### 7. Same math, proven

**Title:** Same math, proven: `coefficient.dat` is bit-identical at 1, 2 and 4 nodes

- Pre-change baseline: the same multiLevel split and rank counts, with the patches removed (unmodified v2512).
- Every Bonus run at every node count gives the same file, byte for byte — the strongest form of F3.
- Each patch was also checked on its own against the configuration just before it, at 1, 2 and 4 nodes.

図：`figures/tab02_f3_check.png`

メモ（30秒）：
- なぜビット一致するか：浮動小数点の演算そのものと順番を変えていないからです。変えたのはメモリの持ち方と、捨てられていた仕事だけ。
- multiLevelだけの変更（ソースは未改変）は、ルール上はSanity checkで確かめます。80 stepのCdは0.32〜0.33で目安より少し低いですが、Basic（scotch）も同じです（Q12）。

### 8. From 3.67 to 2.60 s/step

**Title:** From 3.67 to 2.60 s/step on 4 nodes: −20 % from Basic tuning, another −11 % from the Bonus

- Path on 4 nodes: start (case-default split, binding lost) 3.670 → pinning 3.257 → scotch = Basic 2.920 → Bonus 2.599. Each step was measured against its own control in the same period.
- Scaling 1 → 4 nodes: parallel efficiency 1.14 (Basic) and 1.12 (Bonus).
- Against the organisers' vanilla `scotch` runs: Basic −11 %, Bonus −21 %; our run-to-run spread is 0.35 % against their 12 %.

| Nodes | Basic | Bonus | Bonus vs Basic |
|---|---:|---:|---:|
| 1 | 13.364 (n=3) | 11.668 (n=3) | −12.7 % |
| 2 | 6.367 (n=3) | 5.641 (n=3) | −11.4 % |
| 4 | 2.920 (n=5) | 2.599 (n=3) | −11.0 % |

図：`figures/fig16_journey.png`（主役）、`figures/fig02_scaling.png`。主催者との1/2/4ノードの比較は補足S6（`fig14`）。

メモ（1分）：
- 経路図は「どの順で何をして、いくつ速くなったか」を1枚で見せるためのものです。赤い%は、それぞれ同時期の対照に対する値で、足し合わせません。
- 出発点（3.670）は私たちの最初の状態で、主催者の参照（hierarchicalで3.415）より遅いことに触れます。固定が外れたとき、各rankのページは自分のNUMAに中央値7 %しかありませんでした。固定を頼まない場合より悪くなったのはこのためと考えていますが、主催者とはビルドもMPIも違うので確かめてはいません。
- 固定した後のhierarchicalの3本（3.257）は、当時の`LD_PRELOAD`による固定で測ったものです。Basicで使う`numactl`＋`taskset`は同じ速さです（スライド4の図）。
- 効率が1を超える理由は、rankあたりのデータがキャッシュに入りやすくなるためという仮説です。カウンタは1ノードのパッチ前後だけで、ノード数による違いは測っていません。
- 主催者との差は条件がまとめて違うので、原因を1つに断定しません（ビルド、MPI、配置）。
- 再現性：提出した単独スクリプトをそのまま流し直し、Basic・Bonusの1/2/4ノードすべてで`coefficient.dat`がビット一致、時間は記録の平均から±0.24 %以内でした。4ノードBasicは2.9200（記録の平均2.9196）（#54）。

### 9. What did not work, what we learned

**Title:** What did not work, what we learned, and how to reproduce it

- Did not help (3 runs each): `-march=znver3`, AOCC 5.0, `-O2`, LTO (all within 0.13 %); OpenFOAM communication switches; weighted or METIS partitions (+1.5 % to +6 %); SMT (5.7× slower).
- Learned: measure what actually runs, not what was requested; one job is one data point; prove "same math" bit for bit.
- Reproduce: `build/build.pbs` and `run/submit.sh 1|2|4` with plain `qsub`; checked by re-running them on 2026-10-07.

図：`figures/tab04_not_adopted.png`の抜粋（3〜4行）。

メモ（30秒）：
- 不採用でも「何が否定できたか」を言います。例：重み付けで面や点の偏りを均すと、セル数が偏ってかえって遅くなりました。
- 最後の一言：「同じ計算のまま、Basicで主催者の参照より11 %、Bonusでさらに11 %」。

---

## 時間が余ったら（本編に足せるスライド）

### 2b. Build, storage and MPI

**Message:** We build OpenFOAM ourselves, keep all case I/O on node-local storage, and run Cray MPICH over UCX.

- Build: official v2512 source, GCC 11.2 with `-O3`, AMD math library, in a 1-node PBS job (16 cores). Every run records which build it used.
- Storage: `/scratch` (Lustre, shared) holds the mesh, builds and run directories; every node copies the decomposed case into its own node-local `$TMPDIR`, and the solver reads and writes only there (`-hostRoots`, `-ioRanks`). File I/O in the timed steps is about 0.01 % of the run time.
- MPI: Cray MPICH 8.1.15 over UCX instead of the default OFI provider.

図：`figures/fig15_storage_flow.png`、`figures/tab05_environment.png`

### 4b. How we measured and profiled

**Message:** Every performance number comes from runs with no profiler. Profilers run in separate short runs, and each one answers one question.

- Benchmark runs: only the official metric. A network test (IMB) runs after the solver, outside the timed steps.
- CrayPAT (`pat_run -g mpi`): 4-node, 40-step diagnostic runs with a warm-up step first.
- Call-stack samples (eu-stack), AMD uProf, a `/proc` sampler (CPU binding, NUMA page placement, I/O) and partition statistics answered the remaining questions.

図：`figures/tab06_profiling.png`

メモ：
- 「計装が測定を変えない」ように、計測runとプロファイルrunを分けたことを強調します。
- プロファイルを流し直す手順は、提出物の`analysis/README.md`にあります（`run/submit.sh 4 basic craypat`）。

### 5b. Measuring honestly

**Message:** One job is one data point. We compare against controls run in the same period, because single runs can mislead.

- 92 runs in 29 repeated configurations (2026-09-21 to 10-05): most lie within ±0.4 % of their configuration's median.
- But single runs were 84 % and 91 % slower in September.

図：`figures/fig08_variability.png`

メモ：
- run内のstep間の標準偏差と、run間のばらつきは別物です。150 stepを150個の独立な標本として扱いません。
- 遅い回の原因をホストだけに断定しません。同じホストで後に正常なrunがあります（#47）。

---

## 補足（質疑用）

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

### S6. Against the organisers' reference (1, 2 and 4 nodes)

図：`figures/fig14_vs_organiser_reference.png`

- Organisers' setup (ASPIRE-2A notes, tasks 4.3): site module, `mpirun` with no options, default MPI settings, no binding.
- Against their `scotch` mean: Basic −8 / −13 / −11 %, Bonus −19 / −23 / −21 % on 1 / 2 / 4 nodes.

### S7. The submitted scripts reproduce the results（#54）

- 2026-10-07, Actions 37584763848: the official sources downloaded from their public URLs, built with `build/build.pbs`, every run started with `run/submit.sh`.
- Basic and Bonus at 1, 2 and 4 nodes: `coefficient.dat` bit-identical to the recorded runs; s/step within 0.24 % of the recorded means (Basic 4 nodes: 2.9200 against 2.9196).
- Both CrayPAT profiles: 3.065 and 2.701 s/step under CrayPAT against 3.063 and 2.712; the same number of MPI calls per rank.

| | 1 node | 2 nodes | 4 nodes |
|---|---:|---:|---:|
| Basic, re-run (recorded mean) | 13.333 (13.364) | 6.371 (6.367) | 2.920 (2.920) |
| Bonus, re-run (recorded mean) | 11.644 (11.668) | 5.650 (5.641) | 2.601 (2.599) |

### S8. Hardware counters before and after the patches（#55）

図：`figures/fig17_counters.png`

- 1 node, 128 ranks, 40 steps, multiLevel (2 4 16); AMD uProf `data_access` on one rank per NUMA domain; 2 runs with the patches (fa4f5b0) and 2 without (the same commit with `patches/openfoam/` removed).
- Computation only (MPI, UCX and Pstream left out), mean of 7 ranks: cycles −10.8 %, instructions −4.1 %, L1 data accesses −5.8 %, L1 refills from DRAM −17.2 %, from L2 −0.2 %, L2 accesses including prefetches −9.6 %; IPC 0.360 → 0.388.
- Two runs of the same side agree within about 4 % on every counter. Both sides give the same `coefficient.dat` (Cd 0.43827636195043501).

### S10. Where a step goes, and where the imbalance is（#57）

図：`figures/fig18_step_breakdown.png`

- OpenFOAM's built-in profiling (`profiling {}` and the `parProfiling` function object), Basic, 4 nodes, a 40-step diagnostic run with every rank's results.
- Computation per rank (loop time minus Pstream time): median 97.95 s, max 104.17 s (max/median 1.063) over 40 steps.
- Correlation with the computation: cell count r = +0.06 (balanced within 1 %), wall faces r = +0.43, processor faces r = −0.16; both together explain 27 %.
- Ranks with fewer wall faces wait longer at the start of the next solve (U r = −0.72, omega r = −0.60); the wall shear stress function object grows with the wall faces (r = +0.76).

### S9. OFI against UCX under our placement（#56）

- Basic configuration on 4 nodes, only the MPI transport changed; 3 runs each, alternated in the same period (2026-10-07).
- UCX (main): 2.9176, 2.9168, 2.9246 s/step, mean 2.9197. OFI with `FI_OFI_RXM_USE_SRX=0`: 2.9452, 2.9374, 2.9438, mean 2.9421 (+0.77 %).
- All 6 runs VALID, every step returned 0 (no SIGBUS), the same `coefficient.dat` Cd (0.28404934573921931).
- OFI's own spread is also 0.26 %, so the narrow spread of our runs does not come from UCX (Q15).

---

## 想定問答

英語の回答は、質疑で言う形の下書きです。

**Q1. Why ASPIRE-2A?**
- Last year we competed on Gadi, so this year we wanted to learn the other contest machine.
- Storage. OpenFOAM works with very many files: one unpacked OpenFOAM tree is about 36,000 files, and every decomposed 65M case adds thousands of `processor*` files. Our Gadi project has 1 TiB and about 212,000 files on `/scratch`; in August, three runs setting up at the same time already hit that file limit. On ASPIRE-2A we have 100 TB and 200 million files, so we could keep the builds, the decomposed cases and the raw records of every run.
- （メモ）Gadiの利用停止のことは自分からは言いません。「ノードが空いていた」は言いません（今回、4ノードは4時間以上、qdevの1ノードは3時間以上待った記録があります）。数字の出典は`platforms/gadi/README.md`（inode上限212,100、2026-08-17の3件同時の`Disk quota exceeded`）と、ASPIRE-2Aの`lfs quota`（100 TB、2億inode、2026-10-07）です。

**Q2. MPI waiting is large. Why didn't MPI tuning help?**
- Most of the MPI time is waiting: ranks that finish early wait at the next exchange or global sum. Per-rank MPI time ranges from 20 to 37 s. Library or switch tuning cannot remove that wait; only less work or better balance can. The OpenFOAM communication switches we tried gave no gain.

**Q3. Why did you first reject scotch and then adopt it?**
- One run on 2026-09-27 took 5.03 s/step, an outlier from a slow period. When we alternated three runs of each in the same period, scotch was 10.5 % faster. Since then we never decide from a single run.

**Q4. Is equal cell count enough?**
- It mattered most. When we weighted cells by their face and point work, the cell counts became uneven and it got slower (+2.2 %, +6.1 %). A METIS two-constraint split balanced faces better but added 18 % processor faces (+1.46 %). The remaining imbalance (max/median 1.07) is still open.

**Q5. Why did the weighting make it worse?**
- Static weights moved cells away from an even split: the cell-count imbalance grew to 1.073 with weight ×2. With ×12, the top-level split broke down and the faces between nodes grew five times.

**Q6. Why are the effects different on 1, 2 and 4 nodes?**
- On 1 node each rank holds four times more data than on 4 nodes, so more of it comes from DRAM. Removing array passes therefore saves more on 1 node (0002: −6.4 % against −2.3 %). On 1 node we measured it: with the patches, L1 refills from DRAM fall 17 % while instructions fall 4 %. The same reasoning fits the super-linear scaling, but we have not measured counters across node counts.

**Q7. What is proven and what is not?**
- Proven: the timings (same-period controls, 3 or more runs on 4 nodes), bit-identical `coefficient.dat`, and the pinning problem (seen in `/proc` during the solve).
- Measured with hardware counters (1 node): the patches cut L1 refills from DRAM by 17 % with 4 % fewer instructions.
- Not proven: the DRAM traffic in bytes (we cannot read the memory-controller counters), the effect on 4 nodes, and the cache explanation of the super-linear scaling. We present those as hypotheses.

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

**Q13. Why is your Cd different from the organisers' reference?**
- Our Basic Cd at 150 steps is 0.284049, against 0.283983 in the organisers' `scotch` runs (a relative 2.3e-4). When we ran the site module once with our own scripts and decomposition, we got their value exactly (0.28398300763231610). So the difference comes from our build (for example, we link AMD's math library), not from the decomposition or the method.

**Q14. The organisers saw a signal 7 (SIGBUS) at the end of 2- and 4-node runs. Did you?**
- No. That comes from the default OFI provider at `MPI_Finalize`. Our job scripts use Cray MPICH over UCX, and every step of every run returned 0.

**Q15. Why is your run-to-run spread so much smaller than the organisers'?**
- Our 5 Basic runs on 4 nodes lie within 0.35 %; the organisers' 5 `scotch` runs spread over 12 %. It is not UCX: our runs with the organisers' transport (OFI with `FI_OFI_RXM_USE_SRX=0`) also lie within 0.26 %. The main remaining difference is the placement — every rank pinned with its memory on its NUMA domain — which also removed the random slow ranks we saw before pinning.

**Q16. Why UCX and not the site's default OFI?**
- In September, every 2- and 4-node run with the default OFI provider died with SIGBUS at `MPI_Finalize`, while UCX completed every run. The organisers have since found that `FI_OFI_RXM_USE_SRX=0` avoids the crash, so we compared again with everything else as in Basic: 3 alternated 4-node runs each, OFI 2.942 against UCX 2.920 s/step (+0.77 %, ranges not overlapping), the same Cd, no crash. So UCX stays.

**Q17. Is the pinning fix allowed in Basic?**
- Yes. It is job-script placement: `numactl` sets the memory policy before each rank starts, and `taskset` sets the CPU affinity from outside. F1 lists job scripts, rank placement and affinity as Basic. We did not use `LD_PRELOAD`, which would be Bonus work.

**Q18. Can the organisers reproduce your Basic number?**
- Yes. `build/build.pbs` builds from the official public sources, and `run/submit.sh 1|2|4` runs the whole Allrun chain with plain `qsub`. We re-ran them ourselves on 2026-10-07: at every node count `coefficient.dat` was bit-identical and the time within 0.24 % of our recorded mean; on 4 nodes 2.9200 against 2.9196 s/step.

**Q19. Why did you not tune the hierarchical coefficients instead?**
- We kept the case default `(16 8 4)` as the control. scotch was 10.5 % faster on 4 nodes in alternated runs, so we spent the remaining effort on scotch and on placement. We have not searched other `nHierarchical` factorisations.

**Q20. What would you do next?**
- The global sums: about half of the MPI time is `MPI_Allreduce`, mostly the global sums of the linear solvers. And the remaining imbalance between ranks, whose cause we have only narrowed down (Q21).

**Q21. Do you know where the imbalance between ranks comes from?**
- Partly. With OpenFOAM's own profiling on all 512 ranks, the computation per rank still varies by 6 % (max/median 1.063). Cell counts are balanced within 1 % and do not explain it; wall faces explain a little (r = 0.43, 2.8 % of the work). Balancing the wall part perfectly would only take it to 1.056, so a wall-weighted split is not worth it. Nodes and NUMA domains show no systematic difference; the variation follows groups of neighbouring subdomains, so it is a property of the mesh regions, and most of it is still unexplained.

---

## 発表の準備

- 本編9枚を、タイマーで通しで練習します。各スライドに「時間が足りないときの1文」を決めておきます。
- 話す人と交代の位置を決めます（Qwenとの切り替えも）。
- 数字は提出物の`README.md`と同じものを使います（2.920 / 2.599 / −11.0 %、3.296）。
- 補足スライド（S1〜S9）は本編の後ろに置き、質疑ですぐ出せるようにします。
- 図の文字が小さければ、`.svg`を開いて拡大するか、pptxの側で注記を大きく書き直します。

## 根拠

- 図の元データ：リポジトリの`presentation/openfoam/data/`。主催者の参照値は`tasks/4.3 OpenFOAM Application Notes - ASPIRE-2A.md`とそのログ（`tasks/4.3-aspire2a-logs/`）。
- 実験の記録：issue #36〜#38（Basic）、#42、#44、#50、#51（Bonus）、#41、#53（profile）、#46（I/O）、#47（ばらつき）、#48、#49（通信）、#54（提出スクリプトの再現）、#55（カウンタ）、#56（OFIとUCX）。
- 提出物：Boxの`Tokyo_Rapids_with_RIKEN_Submission/openfoam/`。
