"""Speaker notes: an English script for the presenter, then a Japanese memo for the team (sources, caveats, Q&A)."""

NOTES = {}

NOTES["title"] = """
[0:08]
EN: We are Tokyo Rapids with RIKEN. We made OpenFOAM 1.40 times faster on four ASPIRE-2A nodes, with the same math.

訳（参考）: Tokyo Rapids with RIKENです。ASPIRE-2Aの4ノードで、同じ計算のままOpenFOAMを1.40倍速くしました。

JP: 名乗りと結果だけ言って、すぐ次へ進む。
"""

NOTES["overview"] = """
[0:30]
EN: The task is a steady simulation of the air around a car, on a fixed mesh of 65 million cells. The iterations are fixed, so every step does the same work, and the score is the time per step on four nodes. Our result: 3.65 seconds with the case defaults, 2.90 with Basic tuning, and 2.60 with the Bonus. That is 1.40 times faster, with the same build, scripts and measurement.

訳（参考）: 課題は、6,500万セルの固定したメッシュで、車のまわりの空気の流れを定常計算することです。反復回数が固定なので、どのstepも同じ仕事をし、スコアは4ノードでの1 stepの時間です。結果は、ケースの既定で3.65秒、Basicのチューニングで2.90秒、Bonusで2.60秒。同じビルド、スクリプト、測り方で、1.40倍速くなりました。

JP:
- 反復回数は固定（fvSolution.fixedIter：pはGAMGで12サイクル、最粗段はPCG 35回、Uは3成分それぞれGauss-Seidel 15回、kとωは8回）。どのstepも同じ仕事なので、1 stepの平均で比べられる。
- 動画は場を書き出すための別runで、計測runではない（計測runは controlDict.noWrite で場を書かない）。Q22：同じ公式ケースに出力のfunction objectだけ足して流した。Cdは同じ機械・同じ分割の公式runと全桁一致。
- 比べる基準は、同じビルド・同じスクリプト・同じ測り方で取った自分たちのbaseline。主催者の値は5枚目で参考として出すだけ。
"""

NOTES["aspire"] = """
[0:20]
EN: We used ASPIRE-2A: eight NUMA domains of 16 cores per node. One thing to remember: just 16 of the 128 cores already fill the memory bandwidth. We chose ASPIRE-2A because OpenFOAM needs very many files, and its file quota is a thousand times Gadi's.

訳（参考）: ASPIRE-2Aを使いました。1ノードは、16コアずつのNUMA領域が8つです。1つ覚えておいてください：128コアのうち16コアだけで、もうメモリ帯域を使い切ります。ASPIRE-2Aを選んだのは、OpenFOAMがとても多くのファイルを使い、ファイル数の上限がGadiの1000倍あるからです。

JP:
- 帯域：カタログ409.6 GB/s、STREAMで約290 GB/s。L3ごとに1スレッド（ノードで16）で飽和（#36）。128コア全部では269〜273 GB/s。
- ネットワークの出典：TOP500「ASPIRE 2A (CPU Partition) - HPE Cray EX425, AMD EPYC 7713 64C 2GHz, Slingshot-10」、NSCC「All nodes are connected with HPE Slingshot Interconnect (Dragonfly Topology)」。ジョブから見えるNICはMellanox製（mlx5）で、UCXとOFIの両方が使える。
- Q1（なぜASPIRE-2A）：昨年はGadiだったので今年はもう一方を学びたかった。OpenFOAMのビルド1つで約36,000ファイル、分割ケースごとに数千ファイル。Gadiでは8月に3件同時の準備で上限（212,100 inode）に達した。ASPIRE-2Aは100 TB・2億inode（Gadiのプロジェクトは0.2 M files・1 TB）。
- 言わないこと：Gadiの利用停止、「ノードが空いていた」（実際は4ノードで4時間以上待った記録がある）。
"""

NOTES["baseline_settings"] = """
[0:20]
EN: Our baseline is the case as shipped, on our own build of the official source, with the ranks bound by the launcher as the site recommends. Every point you will see is one job, with at least three jobs per condition.

訳（参考）: baselineは配布されたままのケースです。公式のソースから自分たちでビルドし、rankはサイトの推奨どおり起動コマンドで固定しています。これから見せる点はどれも1つのジョブで、1つの条件につき3本以上流しています。

JP:
- （聞かれたら）ビルドの中身：公式v2512、GCC 11.2 -O3、AMDの数学ライブラリ、Cray MPICH over UCX。サイトのモジュールと同じ速さで、何を使ったかを正確に記録でき、Bonusのパッチにもビルドが要る。分割はケース既定のhierarchical。
- module load PrgEnv-gnu/8.3.3 craype-x86-milan aocl/4.0.0-gcc11.2 → module swap craype-network-ofi craype-network-ucx → module swap cray-mpich cray-mpich-ucx/8.1.15。
- UCXにした理由：9月、既定のOFIでは2・4ノードのrunが毎回 MPI_Finalize でSIGBUSになり、Allrunのままだと最初の並列ステップで止まる。UCXでは全run完走。後で主催者が見つけたOFIの回避策2つも、私たちの構成ではUCXより遅い（+0.77%、+0.50%、Cdは同じ。Q16）。
- 自前ビルド：サイトのモジュールと同じ速さ（−0.08%、Q8）。ccacheで作り直しは60分→5分半。
- Q9（AOCL-LibMはBasicで良いか）：FOAM_EXTRA_LDFLAGSでリンクする数学ライブラリで、IEEE倍精度のまま、値が変わるflagは使っていない（F1のビルド設定の範囲）。
- 「ここで頼んだ固定が、実は外れていた」が8枚目につながる。
"""

NOTES["baseline_results"] = """
[0:25]
EN: The baseline scales perfectly: a step falls to a quarter from one to four nodes. But it is slow, 3.65 seconds on four nodes, and unsteady: identical jobs differ by up to 8 percent. The open circles are the organisers' runs, for reference only; we compare against our own baseline. Slow and unsteady at the same time suggests something is misconfigured.

訳（参考）: baselineはきれいにスケールし、1ノードから4ノードで1 stepが4分の1になります。でも遅く、4ノードで3.65秒です。しかも不安定で、同じ設定のジョブでも最大8%ばらつきます。白丸は主催者のrunで、参考として示すだけです。比較は自分たちのbaselineに対して行います。遅くて不安定なのは、何かの設定がおかしいサインです。

JP:
- 図の白丸は主催者のhierarchicalの1本ずつ（14.67／7.12／3.41 s/step、tasks 4.3）。サイトのビルド、既定のMPI、固定なしで、条件が違う。スライドの下にあった注記は、図と口頭に移した。
- ばらつきの原因は、固定が外れて遅いrankが毎回違う場所に出ること（#36の症状）。8枚目で示す。
- 1ノードの分割は(16 8 1)で、主催者の(16 4 2)と違う。
- 日付の違う値を並べられる理由：baselineと同じ日（10/12）に流したscotchの対照は10/05の平均から0.2%以内。10/15〜16の対照も10/05、10/06の平均から0.2%以内。#36の3本（10/02〜03、平均3.670）とも0.5%で合う。
- Q27（なぜ主催者より遅いか）：固定が MPI_Init で外れ、ページが8領域に散った（自領域9%）。主催者は固定を頼んでいない。ビルドとMPIも違うので切り分けてはいない。
"""

NOTES["measure"] = """
[0:25]
EN: Benchmark runs carry no profiler and give every number in this talk. Profilers change a step by up to six percent, so profile runs only tell us where and why. And our rule: a change is kept only if every job with it beats every job without it, run alternately in the same period.

訳（参考）: 計測のrunにはプロファイラを入れず、この発表の数字はすべてそこから取っています。プロファイラは1 stepを最大6%変えるので、プロファイルのrunは「どこで」「なぜ」を見るためだけに使います。採否の決まりは、同じ時期に交互に流し、変更ありの全ジョブが変更なしの全ジョブより速いときだけ採用する、です。

JP:
- 表の道具は指すだけで、1つずつは読まない。プロファイラは1 stepを−1%〜+6%変える（baselineはCrayPATの下で3.85 s、計測runで3.65 s）。
- 40 stepのプロファイルで足りる理由：反復回数が固定で、どのstepも同じ仕事（Q28）。
- IMBは毎回のbenchmark runでsolverの後に流し、そのノード同士の帯域と大域和の時間を記録している。NICやスイッチのカウンタは読んでいない。
- メモリコントローラのカウンタとIBSは利用者に読めない（perf_event_paranoid=2）。帯域は13枚目の配置実験で確かめた。
- 採否：最初は「1%以上」も条件にしていたが、run間のばらつきが4ノードで約0.2%（10月のpinnedなscotch 29本で標準偏差0.19%）と分かってから外した。0.7%の差（分割の対応付け）も5本ずつで区別できた。
- Q11：プロファイルは別の診断runで取り、benchmark runにはプロファイラを入れていない。
"""

NOTES["mpi_profile"] = """
[0:35]
EN: We profiled the baseline with CrayPAT on four nodes, all 512 ranks. By number of calls, the top three are MPI_Isend, MPI_Irecv and MPI_Test: the halo exchange with the neighbouring subdomains, 93 percent of all calls. By time, the top three are MPI_Waitall, MPI_Allreduce and MPI_Bcast. Waitall and Allreduce take 90 percent of the MPI time, and both wait for other ranks. It is waiting, not transfer: MPI time per rank ranges from 35 to 112 seconds, with equal cell counts. So why are some ranks late?

訳（参考）: baselineを、4ノード・全512 rankでCrayPATでプロファイルしました。呼び出し回数の上位3つはMPI_Isend、MPI_Irecv、MPI_Testで、隣のサブ領域との境界の値のやり取りです。全呼び出しの93%を占めます。時間の上位3つはMPI_Waitall、MPI_Allreduce、MPI_Bcastです。WaitallとAllreduceでMPIの時間の90%を占め、どちらも他のrankを待つ呼び出しです。つまり転送ではなく待ちです。セル数は同じなのに、rankごとのMPIの時間は35秒から112秒までばらつきます。では、なぜ遅れるrankがあるのでしょうか。

JP:
- 同じ主催者のISC26 SCCのOpenFOAM課題（https://hpcadvisorycouncil.atlassian.net/wiki/spaces/HPCWORKS/pages/3700260877）が「4ノードで任意のMPIプロファイラを使い、呼び出し回数と合計CPU時間でそれぞれ上位3つのMPI呼び出しを発表で示せ」と求めている。APACの課題文にはないが、同じ審査員が見る可能性が高いので本編に置いた（10/20）。
- 測ったのは全512 rank。スライドの値はrankあたり（512 rankの平均、40 step）。上位3つの順位は、512 rankの合計で並べても同じ。合計はスライドから外し、ここに残す（聞かれたら答える）。512 rankの合計：MPI_Isend・MPI_Irecvは各2.90億回、MPI_Testは2.89億回、MPI全体で9.29億回。CPU時間はMPI_Waitall 22,069 s、MPI_Allreduce 14,140 s、MPI_Bcast 1,289 s（スライドは3桁に丸めた）。
- 割合：MPIはrankの時間169.6 sのうち78.3 s（46%）。Waitall 55%、Allreduce 35%、Bcast 3%（MPIの時間に対して）。回数の上位3つは、MPIの呼び出し全体（rankあたり181.5万回）の93%。
- 4位以下：回数はMPI_Allreduce 63,085回（1 stepに約1,600回の大域和）、MPI_Waitall 52,933回。時間はMPI_Comm_dup 1.8 s、MPI_Isend 1.6 s。
- プロファイラの下では3.85 s/step（計測runは3.65）。時間は「どこで」を見るためだけに使う（6枚目）。
- Basicの後（CrayPAT、#53）：回数の上位3つは同じ。時間はMPI_Allreduce 48%、MPI_Waitall 38%に入れ替わり、MPIはstepの19%。
- 待ちの原因は次の8枚目（固定が外れる → 計算が不均一 → 全員が待つ）。
- Q2（MPIの待ちが大きいのに、なぜMPIのチューニングが効かないか）EN: Most of the MPI time is waiting: ranks that finish early wait at the next exchange or global sum. Library or switch tuning cannot remove that wait; only less work or better balance can. UCX over RC raised the IMB bandwidth by 55% but changed a step by −0.01%, and moving the GAMG coarsest level, which issues 81% of the MPI_Allreduce calls, to 32 ranks changed it by −0.25%.
- 出典：CrayPAT 38219766511（#62）、data/baseline_profile_4node.csv。
"""

NOTES["baseline_analysis"] = """
[0:40]
EN: Three findings explain it. First, /proc during the solve: none of the 512 ranks was on its own core, and only 9 percent of a rank's memory was on its own NUMA domain. The binding we asked for was removed while MPI initialised. Second, the computation per rank ranged from 54 to 115 seconds. Third, 46 percent of the time is MPI, mostly waiting. With about 1,600 global sums per step, one slow rank holds up all the others. And the computation itself is mostly sparse-matrix sweeps, which stream the whole matrix with little arithmetic. That comes back later.

訳（参考）: 3つの発見で説明できます。1つ目。計算中の/procを見ると、512 rankのどれも自分のコアに固定されておらず、自分のNUMA領域にあるメモリは9%だけでした。頼んだ固定が、MPIの初期化の途中で外されていたのです。2つ目。rankごとの計算時間は54秒から115秒までばらついていました。3つ目。時間の46%がMPIで、その多くは待ちです。1 stepに約1,600回、全rankで値を足し合わせるので、遅いrankが1つあると全員が待ちます。そして計算そのものの多くは疎行列のsweepで、行列全体を少しの演算で読み流します。これは後で効いてきます。

JP:
- uProf（32 rankをサンプル、self CPU time、40 step）：GaussSeidelSmoother::smooth 394.6 s、lduMatrix::residual 228.9 s、lduMatrix::Amul 53.1 s。rankあたり12.3 + 7.2 + 1.7 = 21.1 sで、rankあたりの計算時間（OpenFOAM profilingの中央値78.6 s）の約27%。次はmultiply 30.6 s、gaussGrad 29.2 s、dotInterpolate 27.7 s。
- 以前この下にあったLESSONの札（Check what is already broken before hunting for gains）は外し、次の9枚目の方針の1行目（Fix what is broken first）にした。
- MPIの上位3つ（回数と時間）は7枚目。rankごとのMPI時間は35〜112 s。最も遅いrankの計算は中央値の1.46倍。
- セル数はほぼ完全に均等（最大でも平均+0.002%）なので、差は仕事の量ではなく待ち。
- 自領域のページは中央値8.7%。8領域に均等に散れば12.5%なので、ほぼランダム。全rankが256 CPUのどこでも動ける状態だった。
- 固定反復：1 stepにUで15回×3成分、kとωで8回ずつ、pでGAMG 12サイクル（最粗段PCG 35回）。rankあたり1 stepに約14,000回の送信と約1,600回の大域和。
- 交換する量は律速ではない：ノード間の面を92%減らしても、帯域を55%上げても速くならない（18枚目、Q29）。
- 出典：CrayPAT 38219766511、OpenFOAM profilingと/proc 38219862855、uProf 38219770656（#62）。
"""

NOTES["strategy"] = """
[0:35]
EN: So our strategy: fix what is broken first, then follow the measured bottleneck, one change at a time. Each round, we measure a baseline, profile it, name the bottleneck, change one thing, and keep it only if it beats its control. Then we profile the new baseline. Round one found the lost binding and the uneven work: Basic, from 3.65 to 2.90 seconds. Round two found memory bandwidth: the Bonus, down to 2.60. Basic changes no source code; the Bonus does, and must prove the math is the same.

訳（参考）: そこで方針は、まず壊れているものを直し、次に測った律速を1つずつ追う、です。1回ごとに、baselineを測り、プロファイルし、律速を決め、1つだけ変え、対照より速いときだけ残します。そして新しいbaselineをまたプロファイルします。1回目は外れた固定と不均一な仕事を見つけ、Basicで3.65秒から2.90秒になりました。2回目はメモリ帯域を見つけ、Bonusで2.60秒になりました。Basicはソースを変えません。Bonusは変えるので、計算が同じであることを示す必要があります。

JP:
- 8枚目の「壊れているものを先に直す」を、ここで方針として言う（8枚目のLESSONの札は外した）。3の「What is broken?」が最初の問い。
- 下の表は話の道筋の予告：1行目は10〜12枚目、2行目は13〜16枚目、3行目は19枚目（What remains）。
- 以前の本編9枚目（律速の候補ごとに測ったことと方針の表。ネットワーク、演算、I/O、OSノイズを含む）は、補足の最初（BOTTLENECKS WE MEASURED）に移した。
- BasicとBonusの線引き（F1、F2）：Basicはソース未改変、ビルド・ジョブスクリプト・配置、分割はhierarchicalかscotchまで（その係数は自由）。Bonusはソース変更とそれ以外の分割方法で、F3の自己証明が要る。
- Q（どう計画したか）にはこの1枚で答える。3回目の候補はQ20のとおり（rankごとの実測時間を重みにした分割、U・k・ωの組み立ての融合、GAMGの残差と制限の融合。数%の見込み）。
"""

NOTES["basic_pinning"] = """
[0:40]
EN: First, we put the lost binding back. Linux keeps a memory page where it was first written, so data allocated off-core stays remote for the whole run. We fixed it in the job script only: numactl binds each rank's memory, and a watcher re-pins each rank to its core. Both halves are needed: CPU only gives 3.47 seconds, memory only 4.38, both 2.92. On the default split, this alone is 11 percent faster. The organisers' runs are not pinned, so this is where we differ most from other teams.

訳（参考）: まず、外れた固定を戻しました。Linuxはメモリのページを最初に書かれた場所に置いたままにするので、別のコアで確保したデータは、run中ずっと遠いメモリに残ります。ジョブスクリプトだけで直しました。numactlで各rankのメモリを縛り、見張り役が各rankを自分のコアに固定し直します。両方が必要で、CPUだけなら3.47秒、メモリだけなら4.38秒、両方そろって2.92秒です。既定の分割でも、これだけで11%速くなります。主催者のrunは固定していないので、ここが他のチームとの一番の違いです。

JP:
- 「頼んだ配置」と「実際の配置」を区別したことが要点。起動コマンドの指定は正しく、外れていたのは実行中の/procで分かった。
- CPUだけ戻すと、戻すまでの12〜16秒に確保したデータが遠くに残る（3.47）。メモリだけ縛るとCPUが別の領域へ動き、全部のアクセスが遠くなる（4.38）。
- LD_PRELOADでMPI_Initの直後に固定する方法も同じ速さだが、ルールではBonus扱い。Basicはジョブスクリプトだけでできる形にした（F1：job scripts, rank placement, affinity）。全ジョブで各ノード128/128固定。
- −11%は、hierarchicalのまま固定だけを足した同時期の比較（3.670 → 3.257、10/02〜03、3本ずつ、#36）。図はscotchでの切り分け（data/pinning.csv、各1〜3本）。
- 図の意図：CPUの固定とメモリの縛りの片方だけでは速くならず、両方そろって初めて速いこと。「Neither」はbaselineと同じ状態（起動時に頼んだ固定がMPI_Initで外れる）。
- 「512 of 512」：Basicの全ジョブで、各ノードの見張り役がbound=128/128（4ノードで512 rank全部）を出している。58%は対応付けの前のBasicで、ノード0の128 rankを/procで見た中央値（#36 A3）。
- Q17（Basicで許されるか）：numactlはrank起動前のメモリポリシー、tasksetは外からのCPU affinityで、F1の「job scripts, rank placement, affinity」に入る。
- 主催者のscotch 5本は3.19〜3.58 s/stepで12%ばらつく（Q15）。ノートどおりに進めると、この辺りに来る。
"""

NOTES["basic_decomp"] = """
[0:35]
EN: Second, we gave every rank the same work. The default split cuts thin slabs, and ranks with much of the car's surface get more work: an imbalance of 1.16. scotch cuts compact blocks: a third fewer faces, an imbalance of 1.06, and minus 10.5 percent on four nodes. Mapping the split onto each node's sockets and NUMA domains gave another 0.7 percent; all five jobs beat all five controls. One slow job once made us reject scotch; since then we never decide from one job.

訳（参考）: 次に、どのrankにも同じ仕事を割り当てました。既定の分割は薄い板に切るので、車の表面を多く含むrankの仕事が多くなり、偏りは1.16でした。scotchはまとまった塊に切るので、面は3分の1減り、偏りは1.06になり、4ノードで10.5%速くなりました。さらに分割を各ノードのソケットとNUMA領域に対応付けると0.7%速くなり、5本すべてが対照の5本より速くなりました。一度は遅いジョブ1本のせいでscotchを捨てかけたので、それ以来、1本では決めていません。

JP:
- 不均衡はrankの計算時間の最大/中央値（CrayPAT、どちらも固定あり）。hierarchicalの不均衡は壁の面（車の表面）の数と相関（#38）。
- scotchで中央値rankのMPI_Waitallは18.7 sから9.4〜10.8 sに半減。
- ノード間の通信が理由ではない：rankの並べ替え（MPICH_RANK_REORDER_METHOD=3）でノード間の面を92%減らしても+0.1%。
- ノード数が多いほど効く理由は確かめていない（Q30）。
- 対応付け（#63）：scotchCoeffsの domains (2 4 16)、domainWeights、strategy（Scotchのtree-leaf target）。面の総数は+3.3%だが、ノード・ソケット・NUMA領域をまたぐ面は−22.7%・−21.3%・−10.4%。4ノードで2.917726 → 2.897638（5本ずつ交互、−0.69%）。1・2ノードはほぼ変わらない。
- 絵は対応付けの前のscotch。右の図は1/2/4ノードの各ジョブ（data/decomposition_basic.csv、3本ずつ、#36、#38）。縦軸はパネルごとに違う。
- 「1本の遅いjobでscotchを捨てかけた」話は、スライドの斜体の1行をやめて口頭だけにした（EN原稿の最後の文）。9/27の1本が5.03 s/stepだった（Q3）。
- Q10：multiLevelはBasicで使っていない（別の分割方法なのでBonus）。
- Q19：hierarchicalの係数は対照としてケース既定(16 8 4)のまま。他の分解は探していない。
"""

NOTES["basic_results"] = """
[0:30]
EN: Together, Basic takes a step on four nodes from 3.65 to 2.90 seconds, minus 21 percent, with unmodified OpenFOAM. The profiles show why: every rank on its own core, the slowest rank 6 percent above the median instead of 46, and MPI down from 46 to 19 percent. And it is steady: five jobs within 0.18 percent, which matters because the organisers re-run exactly this configuration.

訳（参考）: 合わせて、Basicは改変していないOpenFOAMのまま、4ノードで1 stepを3.65秒から2.90秒、21%短くしました。プロファイルがその理由を示しています。全rankが自分のコアにいて、最も遅いrankは中央値より46%ではなく6%遅いだけになり、MPIは時間の46%から19%に減りました。しかも安定していて、5本が0.18%以内に収まります。主催者はまさにこの構成を再実行して採点するので、これは大事です。

JP:
- 出典：s/stepはbaselineが#62、Basicは10/15の5本（#63）。「(profile run)」の2行は対応付けの前のBasic（scotch既定）のプロファイルrun。対応付けで4ノードは0.7%しか変わらない（以前の「*」の注記はここに移した）。
- 「0 of 512 → 512 of 512」：baselineは/procで全512 rankを見て、自分のコアに固定されたrankは0（#62）。Basicは全ジョブで各ノードの見張り役がbound=128/128を出す（4ノードで512 of 512）。以前の「128 of 128 per node」は同じことの書き方の違いで、512 of 512にそろえた。
- /procで見たメモリの置き場所は、baselineが全512 rank（#62）、Basicはノード0の128 rank（#36 A3）。自領域のメモリは9% → 58%。
- 1・2ノードの効果（−8%、−14%）は17枚目で見せる。OpenFOAM profilingはbaselineが#62、Basicが#57。CrayPATはbaselineが#62、Basicが37176272426（#36 A4）。
- 固定後も自領域のページが58%なのは、共有ライブラリやMPIの共有バッファのように複数rankが使う部分は1つの領域にしか置けないためと考えているが、未確認。「各rankのデータ（メッシュと場）を自分の領域に置いた」と言う。
- 残る19%のMPIも、多くは遅いrankを待つ時間（Q2、Q21）。
- 提出スクリプトでの再実行：2.905 s/step（記録の平均2.898に対して+0.24%、Cdはビット一致）。
"""

NOTES["bandwidth"] = """
[0:35]
EN: After Basic, what sets the speed? We can't read memory counters on ASPIRE-2A, so we moved the ranks instead. With half the cores but all 16 memory channels, nothing changed. With the same ranks on half the channels, a step took 2.2 times as long, as much as the bandwidth dropped. So the step follows memory bandwidth. The sweeps do about 0.1 flop per byte, a hundredth of what keeps the cores busy. So the next move is not faster bytes, but fewer bytes.

訳（参考）: Basicの後、何が速さを決めているのか。ASPIRE-2Aではメモリのカウンタを読めないので、rankの置き場所を変えて確かめました。コアを半分にしても、16本のメモリチャネルを全部使えば何も変わりませんでした。同じrankをチャネル半分に置くと、帯域が落ちたのと同じだけ、1 stepが2.2倍かかりました。つまり1 stepはメモリ帯域で決まります。sweepの演算は1バイトあたり約0.1 flopで、コアを忙しくさせるのに要る量の100分の1です。だから次の一手は、バイトを速く運ぶことではなく、運ぶバイトを減らすことです。

JP:
- 実験（#61）：4ノード、150 step、各2本、全rankをCPUとメモリに固定。full128（提出の配置）、spread64（64 rank/ノード、16個のL3と16チャネル全部）、packed64（同じ64 rank・同じ分割で8個のL3と8チャネル）。
- triad（同じノード、solverの後）：274／279／125 GB/s/ノード。
- 解釈：演算や各コアのメモリ要求のレイテンシで決まるなら、コア半分で約2倍遅くなるはず。そうならず、チャネル半分で帯域と同じだけ遅くなった（Q23、Q24）。
- 限界：packed64はL3も半分にしているので、DRAM帯域とL3容量の寄与は分けられない（どちらもメモリ側の資源）。
- 演算密度（Q35）：Gauss-Seidel、残差、Amulは内部の面1つにつき約4 flopに対して30〜40 B（係数2つ16 B、番地4 B、セルの値）を読む。約0.1 flop/B。ノードの倍精度ピーク（128 × 2.0 GHz × 16 flop ≈ 4.1 TFLOP/s）÷ 290 GB/s ≈ 14 flop/B。IPCは0.4〜0.7。
- rooflineは測れない：DRAMのバイト数はメモリコントローラのカウンタが要り、コアのカウンタはプリフェッチの分を数えない。
- Q26（MPIが19%なのになぜ帯域に従う）：MPIの多くは遅いrankを待つ時間で、その遅いrankの計算が帯域律速なので、待ちも帯域とともに伸び縮みする。帯域に比例しない部分は1 stepあたり約0.1 sだけ。
- コンパイラ、フラグ、PGOが±0.13%以内しか変えなかったこととも合う（18枚目）。
"""

NOTES["bonus_opt"] = """
[0:40]
EN: The Bonus does the same arithmetic with fewer bytes moved. First, multiLevel splits the mesh by node, then socket, NUMA domain and core, so each node gets one connected part of the car. Then four source changes, each removing data movement, not arithmetic. The clearest example: the three velocity components share one matrix, but the code read it three times. We read it once and update all three, with the same operations in the same order. The others remove temporary copies, boundary values nobody reads, and temporary face fields.

訳（参考）: Bonusは、同じ演算を、運ぶバイトを減らして行います。まずmultiLevelで、メッシュをノード、ソケット、NUMA領域、コアの順に分けるので、各ノードが車の一続きの部分を受け持ちます。次に4つのソースの変更で、どれも演算ではなくデータの移動を減らします。一番分かりやすい例は、速度の3成分が同じ行列を使うのに、元のコードは行列を3回読んでいたことです。私たちは1回読んで3成分を更新し、演算と順番は同じままです。残りの変更は、一時的なコピー、誰も読まない境界の値、一時的な面の場をなくすものです。

JP:
- 絵は#39の分割の描画（Boxの presentation/openfoam/decomposition/panels/ の multiLevel-car-subdomains.png と multiLevel-car-numa.png）。左はサブ領域ごと、右はノードとNUMA領域で塗ったもの。3つの分割を並べた絵と面の数の表は補足（THE THREE SPLITS）。
- Bonusになる理由（F2）：hierarchical・scotch以外の分割方法とソースの変更はBonus。
- Q（Uだけなのか）：Uに固有なのは「U components in one pass」だけ。Uは3成分が同じ行列を使うので1回で読める。k、ω、pは成分が1つなので、まとめる相手がない。kとωは別の式（別の行列）で、kOmegaSSTはωを解いてから新しいωでkを解くので、1回にまとめると計算の順序が変わる。残りの3つ（no copies：smoothSolverとGAMG、no unused boundary updates：pEqn.HやkOmegaSSTを含む6か所、fused face loops：全部の場の勾配と面積分）は、p・U・k・ωのすべてに効いている。
- multiLevel：(4 2 4 16)／(2 2 4 16)／(2 4 16)。scotch既定に対してノード・ソケット・NUMA領域をまたぐ面が−38%・−34%・−26%、総数2.81 M（−3.9%）。パッチなしで4ノード−1.54%（4本ずつ）。
- 変更の中身（提出物の bonus/README.md と bonus/patches/0001〜0004）：
  no copies in the solvers（0001）：smoothSolverは残差を新しい場に作ってコピー、GAMGはsourceをコピーしてから引いていた → 同じ関数でその場に計算。
  U components in one pass（0002）：Gauss-SeidelがUの共有行列を成分ごとに3回読んでいた → 1回で3成分。
  no unused boundary updates（0003）：6か所で面積分の境界値を作ってprocessor境界で交換し、セルの値しか使っていなかった → 誰も読まない境界値だけ省く。
  fused face loops（0004）：補間した面の場と積の場を足す前に作っていた → 同じ式を足すループの中で、同じ面の順に評価。
- Q32（境界のチェックを省いていないか）：チェックは1つも省いていない。解く場の境界条件、解が使う交換、kとωのboundingは不変で、ログのboundingも同じ回数・同じ値。
"""

NOTES["bonus_results"] = """
[0:30]
EN: Each job at one, two and four nodes: Basic, the multiLevel split alone, and the Bonus. The split alone changes little; the source changes do the rest: the Bonus is 12.7, 11.5 and 10.3 percent faster than Basic. And it is the same math: against the split with unchanged source, coefficient.dat is bit-identical at every node count, and every solver log line matches to 16 digits. The cards answer the four questions the rules ask of Bonus work.

訳（参考）: 1、2、4ノードの各ジョブです。Basic、multiLevelの分割だけ、そしてBonusです。分割だけではほとんど変わらず、残りはソースの変更によるもので、BonusはBasicより12.7%、11.5%、10.3%速くなりました。そして計算は同じです。ソースを変えていない同じ分割と比べて、coefficient.datはどのノード数でもビット単位で一致し、solverのログも全行が16桁まで一致しています。下のカードは、ルールがBonusに求める4つの問いへの答えです。

JP:
- 図の中央（白抜きの赤）は「multiLevelの分割だけ、ソースは未改変」のrun（#42、data/changes_ab.csv、1/2ノードは各1本、4ノードは4本、10/02〜04）。F3の照合相手（pre-change baseline）と同じ構成。4ノードで2.873 s/stepで、Basic（2.898）との差は小さい。そこからソース変更で2.599（−9.5%）。BasicとBonusは別の日のrunだが、10/12と10/15に流した対照は0.2%以内で一致している。
- Q（multiLevelだけのbaselineはどこにあるか）：この図の中央の列。時間はscotch既定に対して−1.5%（4ノード、4本ずつ）、Cdの照合は下のEvidenceのカード。
- カードの4点（R3）：何を変えたか（4つのpatchとmultiLevelの辞書、テキストで提出）、なぜ同じ計算か（メモリの使い方だけを変え、演算とその順番は変えない）、証拠（ビット一致とログの全行一致）、Basicに対する速度向上。
- 4ノード512 rankで、4つの変更をすべて外したbaselineと最終Bonusの coefficient.dat がビット一致（SHA-256 1/2/4ノード 36d35283…、2a49a26d…、8952a056…）。
- 固定反復（tolerance 0、relTol 0）なので、U・k・ωの残差や連続の式の誤差の誤りは解に戻らず coefficient.dat では見えない。そこで提出物の simpleFoam.log（bonus/f3-baseline/ と bonus/results/）を比べた：全stepの残差（16桁）、反復回数、連続の式の誤差、kとωのboundingが1/2/4ノードとも全行一致（371、771、1,475行）。違うのはホスト名、パス、日時、時間の行だけ。
- multiLevelだけの変更（ソース未改変）はSanity checkで確かめる：80 stepのCdは0.323でscotch既定（0.327）や主催者のscotchと同程度（Q12）。
- 変更ごとの効果（補足）：4ノードでmultiLevel −1.5%（scotch既定に対して）、ソース変更は順に−3.4、−2.3、−1.3、−2.8%（直前の構成を対照に同時期3〜4本ずつ）。別々の実験なので足し合わせない。
- Q33（命令−4%は仕事を減らしたのでは）：数値的な仕事は同じ。ログで全solveの反復回数と残差が16桁一致。減らした命令はコピー、確保、一時的な面の場、同じ行列への2回目・3回目のpass、誰も読まない境界値。
"""

NOTES["bonus_analysis"] = """
[0:20]
EN: Do the patches really move fewer bytes? Yes: instructions fall only 4 percent, but refills from DRAM fall 17 percent. And with less bandwidth per core, the same patches gain more: 7.9 percent on all channels, 11.4 on half of them.

訳（参考）: 本当に運ぶバイトが減ったのか。はい。命令数は4%しか減らないのに、DRAMからの読み込みは17%減りました。さらに、1コアあたりの帯域が少ないほど、同じ変更がよく効きます。全チャネルで7.9%、半分のチャネルで11.4%です。

JP:
- （時間があれば）右下のカード：CrayPATでも、rankあたりの計算時間は9%減り、MPIの時間は変わらない。
- uProf（#55）：1ノード128 rank、40 step、multiLevel (2 4 16)、data_accessをNUMA領域ごとに1 rank（rank 0は出力も書くので除く）、計算部分のみ（MPI、UCX、Pstreamを除く）、パッチの有無で各2本。cycles −10.8%、instructions −4.1%、L1 data accesses −5.8%、L1 refills from DRAM −17.2%、from L2 −0.2%、L2 accesses incl. prefetch −9.6%。IPC 0.360 → 0.388。同じ側の2本は全カウンタで約4%以内で一致。
- 言い過ぎない点：数えているのはL1のdemand refillで、DRAMの転送バイト数ではない（uncoreのカウンタは権限がない）。カウンタは1ノードだけ。IPCは0.36 → 0.39（以前スライドの下にあった注記）。
- 4ノードの配置実験（#61）：同じ分割・64 rank/ノードで、全チャネルなら−7.9%、半分のチャネルなら−11.4%（提出の128 rank/ノードでは−9.5%）。
- CrayPAT（#53）：最初の変更だけのBonusから最終Bonusまで、rankあたりの計算時間104.2 → 94.9 s（40 step）、MPIは約23.5 sのまま。
- Q25（refillの多くがL2から来るならキャッシュに乗っているのでは）：demand refillはハードウェアプリフェッチを数えない。流す配列はプリフェッチャがDRAMからL2へ運ぶので、ロードはL2ヒットに見える。パッチでプリフェッチ込みのL2アクセスが10%、DRAM refillが17%減った。
"""

NOTES["scaling"] = """
[0:35]
EN: Every job at one, two and four nodes, on log axes, where ideal scaling is a straight line. Both tiers are faster at every node count, and the efficiency from one to four nodes rises from 1.00 to 1.15. Basic gains grow with node count, mostly from scotch. The source changes gain most on one node, where each rank holds more data. Efficiency above one is cache: on four nodes the cell arrays fit in L3, and DRAM refills per cell fall by 30 percent.

訳（参考）: 1、2、4ノードの各ジョブを対数軸で描いたもので、理想的なスケーリングは直線になります。どちらの段もすべてのノード数で速くなり、1ノードから4ノードの並列効率は1.00から1.15に上がりました。Basicの効果はノード数とともに大きくなり、その多くはscotchによるものです。ソースの変更は、各rankのデータが多い1ノードで最もよく効きます。効率が1を超えるのはキャッシュのためで、4ノードではセルの配列がL3に収まり、1セルあたりのDRAMからの読み込みが30%減ります。

JP:
- ルールが求める「1/2/4ノードのscaling」と「4ノードのbefore/after」をこの1枚で見せる。
- （聞かれたら）baselineに対してBasicは−8／−14／−21%、Bonusは−20／−24／−29%（1/2/4ノード）。
- 本数（1/2/4ノード）：baseline 6/3/3、Basic 3/3/5、Bonus 3/3/3。Baseline 10/12（#62）、Basic 10/15〜16（#63）、Bonus 10/06。10/12と10/15に流した対照は0.2%以内で一致。
- Basicの効果がノード数とともに大きくなる理由は確かめていない（Q30）。hierarchicalの軸に沿った切り方が、サブ領域が小さいほど偏るためと考えている。
- ソースの変更が1ノードでよく効くのは、各rankのデータが4倍あり、DRAMから来る量が多いため（U in one pass：1ノード−6.4%、4ノード−2.3%）。
- カウンタ（#66、対応付けの前のBasic、uProf、1/2/4ノード）：1セル・1 stepあたりのcyclesは4ノードで1ノードの0.843倍、DRAMからのL1 refillは0.697倍。平滑化・残差・行列とベクトルの積のDRAM refillは0.30／0.40／0.42倍、セルの場を順に流すループは0.95倍のまま。セルの配列はrankあたり1ノードで4 MB、4ノードで1 MB、L3はコアあたり4 MB。面の配列（4ノードでも約16 MB）はどのノード数でも収まらない。
- 1・2ノードの変更ごとの値の多くは1本どうしの比較なので、本編では傾向だけ言う（補足）。
"""

NOTES["not_helped"] = """
[0:35]
EN: Just as important is what did not help: compiler flags, PGO, other MPI transports, more network bandwidth. None moved a step by more than a few tenths of a percent, because none moves fewer bytes, and MPI time is waiting, not transfer. Fewer faces alone did not help either: 92 percent fewer faces between nodes gave plus 0.1 percent. What paid off was even work. And we did not stack small gains that we cannot separate from the noise.

訳（参考）: 効かなかったことも同じくらい大事です。コンパイラのフラグ、PGO、別のMPIの転送方式、ネットワークの帯域を上げること。どれも1 stepを0.数%しか動かしませんでした。どれも運ぶバイトを減らさず、MPIの時間は転送ではなく待ちだからです。面を減らすだけでも効きませんでした。ノード間の面を92%減らして+0.1%です。効いたのは、仕事をそろえることでした。そして、ばらつきと区別できない小さな改善は、積み重ねませんでした。

JP:
- 面の数と時間の関係（補足のTHE THREE SPLITSに表）：rankの並べ替えはサブ領域そのものを変えず、ノード間の面だけ−92%で+0.1%。scotchは面の総数−32%と計算の偏り1.16 → 1.06で−10.5%。ノードへの対応付けはノード間の面−23%で−0.7%、multiLevelは−38%で−1.5%。METISの2制約は面が18%増えて+1.5%。面を減らすこと自体は小さく効くが、効いたのは計算を均すことの方。
- UCXのRCはIMBの帯域を55%上げたが、1 stepは−0.01%（Basic）、−0.16%（Bonus）（4本ずつ）。
- GAMGの最も粗い段はMPI_Allreduceの呼び出しの81%を出すが、時間はstepの約0.6%。32 rank（NUMA領域ごと）に集めて−0.25%、4 rankで+1.02%、1 rankで+4.95%。
- 重み付けはセル数を崩してかえって遅くなった：×2で不均衡1.073、×12では最上位の分割が崩れノード間の面が5倍（Q4、Q5）。METISの2制約は面のバランスは良いがprocessor面が18%増えて+1.46%。
- OpenFOAMの通信スイッチ（topoControl、nbx.tuning、pbufs.tuning）も効果なし。commsType scheduledはGAMGで落ちた。
- mallocの閾値（−0.4%、3本）は、ばらつきと区別できず、測り直していない。
- 小さな改善を積み重ねない理由：run間のばらつき（4ノードで約0.2%）と区別できない改善は、たまたま速かったrunかもしれず、積み重ねるとそのrunに合わせることになる（過学習）。採用したのは同じ時期に交互に流して全runが対照より速かったものだけ（6枚目）。0.7%の対応付けも5本ずつで確かめてから採用した。
- 全部の一覧は補足（Not adopted）。Q2：MPIの待ちが大きいのにMPIのチューニングが効かない理由も同じ。
"""

NOTES["conclusion"] = """
[0:35]
EN: To conclude: with the same math, a step on four nodes went from 3.65 to 2.60 seconds, 1.40 times faster. Each change removed a bottleneck we measured first: the lost binding, the uneven work, and memory traffic. What remains is memory bandwidth, and a 7 percent difference between ranks. How we worked: know the noise, fix what is broken first, follow the bottleneck, and judge by the time per step, not by proxy metrics. One more thing before we close.

訳（参考）: まとめです。同じ計算のまま、4ノードで1 stepは3.65秒から2.60秒になり、1.40倍速くなりました。どの変更も、先に測った律速を取り除いたものです。外れた固定、不均一な仕事、メモリの読み書きです。残っているのは、メモリ帯域と、rank間の7%の差です。進め方は、ばらつきを知る、壊れたものを先に直す、律速を追う、そして代理の指標ではなく1 stepの時間で判断する、でした。最後にもう1つだけ。

JP:
- 最初と最後で同じ数字を言う：「同じ計算のまま、4ノードで3.65秒から2.60秒、1.40倍」。
- 最後の一言のあと、20枚目（おまけ、#68）に進む。時間がなければ20枚目を飛ばして、ここで「Thank you」で終える。
- 右下の「How we worked」は、旧課題の資料が重視していた姿勢（ばらつきを先に測る、壊れているものを先に直す、律速を測ってから手を打つ、代理指標ではなく1 stepの時間で判断する）を、私たちの経緯で言い直したもの。代理指標（proxy metrics）は、速さと関係しそうに見える別の量のこと：ノード間の面の数、ネットワークの帯域、IPCや命令数など。18枚目のとおり、これらを良くしても1 stepは速くならなかった。
- 表の右列は、それぞれ同じ時期の対照に対する値で、足し合わせない（以前は左下の文に書いていた）。時間があれば「Basicで置き場所と仕事の均等さを直して21%、Bonusで運ぶデータを減らしてさらに10%」と足す。
- run間のばらつきは8%から0.2%になった。再実行で採点されるので、ばらつきが小さいことも強み（提出スクリプトでの再実行は2.905 s/step、補足）。
- （聞かれたら）主催者の参照runはscotchで3.30 s/step、ばらつき12%。サイトのビルド、既定のMPI、固定なしと条件が違うので直接の比較にしない（補足）。
- 「What remains」の出典（どれも最終Bonusの測定）：メモリ帯域は配置の実験（#61）で、Bonusでもチャネル半分で2.11倍遅い。計算時間の差はCrayPATのrankごとの値（#53）で、最も遅いrankは中央値の1.067倍（Basicの全rankのOpenFOAM profilingでは1.063、#57）。MPIはプロセス時間の19.9%（#53、Basicは19.4%）。計算時間の差はセル数では説明できず、DRAMからの読み込み量で決まる（Q21、#66）。
- （聞かれたら）あとどれだけ速くなるか：数%の見込みで、どれもBonusの側の手（ソースの変更か、Basicで許されない分割の重み付け）。Basicの範囲（ビルド、MPI、配置、分割の係数）で効く手は、試した限りもう残っていない。Q20、Q34。
- Q7（何が証明済みか）：証明済み＝時間（同時期の対照、4ノード3本以上）、coefficient.datのビット一致とsolverログの全行一致、固定の問題（実行中の/proc）。4ノードの実験で示した＝時間がコア数でなく帯域に従うこと、パッチは1コアあたりの帯域が少ないほど効くこと。カウンタで測った（1ノード）＝DRAM refill −17%、命令 −4%。未証明＝DRAMの転送バイト数とピーク帯域に対する割合、DRAM帯域とL3容量の寄与の分離。
- Q20（次に何をするか）：残る不均衡（rankごとの実測時間を重みにする等）と、さらに運ぶデータを減らすこと（U・k・ωの組み立ての融合、GAMGの残差と制限の融合）。数%の見込みで、もう10%は見込んでいない（Q34）。
"""

# ---------------------------------------------------------------- supplementary
NOTES["index"] = """
JP: 質疑用の補足スライドの目次です。各行をクリックすると、そのスライドへ飛びます（スライドショー中）。スライド番号を打ってEnterでも飛べます。MPIの呼び出しの上位3つは本編7枚目、進め方（以前の補足OPTIMIZATION PLAN）は本編9枚目のOPTIMIZATION STRATEGY、#68（数えなかった高速化）は本編20枚目にあるので、ここには載せていません。補足の図と表は Figure S1、Table S1 から番号を振り直しています。
"""

NOTES["s_bottlenecks"] = """
EN (Q, did you check the network, the compiler, I/O?): Yes, each candidate was measured on four nodes. The network: 55% more bandwidth or 92% fewer faces between nodes changed nothing. The arithmetic: compiler flags, another compiler and PGO stayed within 0.13%. File I/O is 0.01% of a step, and OS noise 0.8% of each core's time. What limits a step is the placement of memory, the balance between ranks, and memory bandwidth.

JP: 以前の本編9枚目（10/21に補足へ移した）。本編9枚目は進め方（5つの手順と実際の回り方）になった。ネットワークの行：UCXのRCでIMB帯域+55%、rankの並べ替えでノード間の面−92%、どちらも1 stepは変わらない（補足のネットワークの頁）。OSノイズ：割り込みの処理に各コアの時間の0.8%（#46）。変えるにはrootが要る。メモリ帯域の根拠（配置を変える実験）は本編13枚目。
"""

NOTES["s_splits"] = """
EN (Q, did fewer faces between subdomains help?): Only together with even work. scotch cut the faces between subdomains by a third and evened the computation per rank (slowest to median 1.16 to 1.06): minus 10.5 percent. Reordering the ranks cut the faces between nodes by 92 percent without changing the subdomains: plus 0.1 percent. Mapping the split onto the node and multiLevel cut the faces between nodes by 23 and 38 percent: minus 0.7 and minus 1.5 percent. So the exchanged volume is not what limits a step; the waiting for the slowest rank is.

JP: 絵は#39の分割の描画（Boxの presentation/openfoam/decomposition/decomposition-numa.png の車体の段。色＝ノード、濃淡＝NUMA領域）。hierarchicalはノードが高さ方向の4つの層、scotchはノードの境目がばらばら、multiLevelはノードごとに連続した塊。面の数は各decomposePar.logから（hierarchical 4.31 M、scotch 2.93 M、multiLevel 2.81 M）。ノード間の面は、scotch既定337,324、対応付け後260,748（−22.7%）、multiLevelはscotch既定から−38%（REPORT §6.3、§8）。hierarchicalのノード間の面の数は数えていない。METISの2制約はprocessor面+18%で+1.46%（bonus/README.md）。時間はどれも同じ時期の対照に対する値。
"""

NOTES["s_noise"] = """
EN (Q3, why did you first reject scotch?): One job on 27 September took 5.03 s/step, an outlier from a slow period. When we alternated three jobs of each in the same period, scotch was 10.5% faster. Since then we never decide from a single job.
EN (Q28, are 40-step profiles representative?): With fixed iterations every step does the same work, so 40 steps show the same pattern as 150. Profilers change a step by −1% to +6%, so we never use profiled times as results.

JP: #47。92本、29構成（同じcommit・build・ノード数・分割で3本以上）、2026-09-21〜10-05。多くは構成の中央値から±0.4%以内。9月には84%、91%遅い単発のrunがあった。run内のstep間の標準偏差とrun間のばらつきは別物で、150 stepを150個の独立な標本として扱わない。遅い回の原因をホストだけに断定しない（同じホストで後に正常なrunがある）。
"""

NOTES["s_automation"] = """
JP: 1つのcommitが1つの実験条件。すべてのrunはGitHub Actionsから起動し、ビルドと分割済みケースは入力が同じときだけ再利用する。プロファイラは別の診断ジョブでだけ使い、benchmarkの計測区間には入れない。複数のrunnerが並行してジョブを投げるので、対照と候補を同じ時期に交互に測れる。
"""

NOTES["s_build"] = """
EN (Q8, why rebuild?): A run with the site module gave the same speed (−0.08%). Our own build records exactly what ran, and the Bonus patches need a build anyway.
EN (Q16, why UCX?): In September every 2- and 4-node run with the default OFI died with SIGBUS at MPI_Finalize; UCX completed every run. The organisers' later workarounds were +0.77% and +0.50% slower than UCX under our placement, with the same Cd.

JP: /scratch（Lustre、共有）にメッシュ、ビルド、run directory。各ノードは分割済みケースをノードローカルの$TMPDIRへコピーし、solverはそこだけを読み書きする（-hostRoots、-ioRanks）。計測区間のファイルI/Oは実行時間の約0.01%（#46）。homeはrunに使わず、/dev/shmはnoexecなのでビルド中のコンパイラキャッシュだけ。
"""

NOTES["s_reference"] = """
EN (Q15, why is your spread so much smaller?): Our 5 Basic jobs on 4 nodes lie within 0.18%; the organisers' 5 scotch jobs spread over 12%. It is not UCX: our jobs with the organisers' transport also lie within 0.26%. The main difference is the placement: every rank pinned with its memory on its NUMA domain. Our own baseline without working pinning varied by 8%.

JP: 主催者の設定（tasks 4.3）：サイトのモジュール、オプションなしのmpirun、既定のMPI設定、固定なし。主催者のscotchの平均に対して、Basicは−8／−13／−12%、Bonusは−19／−23／−21%（1/2/4ノード）。ビルド、MPIの転送方式、配置がすべて違うので差の原因は1つではない。参考として見せるだけで、本編の比較は自分たちのbaselineに対して行う。
"""

NOTES["s_step"] = """
EN (Q21, where does the imbalance come from?): Partly known. With OpenFOAM's own profiling on all 512 ranks, the computation per rank still varies by 6% (max/median 1.063). Cell counts are balanced within 1% and do not explain it; wall faces explain a little (r = 0.43). Hardware counters on 32 ranks show what it is: the slowest and the fastest rank execute about the same number of instructions, but the slowest reads more than twice as many lines from DRAM. A rank's computation follows its DRAM refills (r = +0.69), not its instructions (r = −0.09) or its cells (r = +0.24).

JP: OpenFOAM組み込みのprofiling（profiling {} と parProfiling function object）、Basic、4ノード、40 stepの診断run、全rank（#57）。rankあたりの計算時間（ループ時間−Pstream）は中央値97.95 s、最大104.17 s。セル数との相関+0.06、壁の面+0.43、processor面−0.16（両方で27%を説明）。壁の面が少ないrankほど次のsolveの始めで長く待つ。
"""

NOTES["s_path"] = """
JP: 4ノードで1つずつ足した経路。各段はそれぞれ同じ時期の対照に対する値で、足し合わせない。始点は#36の3本（10/02〜03、平均3.670）で、本編のbaseline 3.65（#62、10/12）と同じ構成。固定は当時LD_PRELOADで入れていた（Basicのnumactl＋tasksetと同じ速さ）。
start 3.670 → 固定 3.257 → scotch 2.915 → ノードへの対応付け＝Basic 2.898 → multiLevel 2.873 → no copies 2.776 → U in one pass 2.718 → no unused boundary updates 2.672 → fused face loops＝Bonus 2.599。
"""

NOTES["s_network"] = """
EN (Q29, isn't the exchange across subdomain boundaries the bottleneck?): Not by volume. Cutting the faces between nodes by 92% changed a step by +0.1%, and 55% more network bandwidth by −0.01%. What costs time is the synchronisation: about 1,600 global sums per step make every rank wait for the slowest one, and the slowest ranks have almost no neighbours on other nodes.
EN (Q31, did you profile the network?): Yes, at three levels: IMB after every benchmark run, CrayPAT per call and rank, and experiments that changed only the network side. We did not read NIC or switch counters.

JP: rankごとのMPI_Isendの回数は、分割から数えた隣のrankの数と相関+1.000（1つの隣に1 stepあたり約1,324通）。メッセージの数は分割で決まり、待ちは計算の不均衡で決まる（#48）。16の最も遅いrankのうち13はノード外の隣を持たない。
"""

NOTES["s_ofi"] = """
EN (Q14, did you see the SIGBUS?): No. It comes from the default OFI provider at MPI_Finalize. Our job scripts use Cray MPICH over UCX, and every step of every run returned 0.

JP: #56、#60。Basic（対応付けの前）、4ノード、MPIの転送方式だけを変更、同じ時期に交互。全run VALID、SIGBUSなし、Cdは同じ（0.28404934573921931）。OFI自身のばらつきも0.26%なので、私たちのrunのばらつきが小さいのはUCXのおかげではない（Q15）。
"""

NOTES["s_cores"] = """
EN (Q23, how do you know it is memory-bound without the memory counters?): On 4 nodes, 64 ranks per node are as fast as 128 when they keep all memory channels, and 2.1–2.2× slower when the same 64 ranks share half the channels, as much as the measured bandwidth drops. Compiler flags and PGO change nothing, and our patches, which keep every operation, gain most where memory is scarcest.
EN (Q24, bandwidth or latency?): Bandwidth. If the latency of each core's requests set the speed, halving the cores would halve the throughput; it changed by −1% to +2%.

JP: コアを半分にした比較は分割が512から256に変わるが、帯域に比例しない部分は1 stepあたり約0.1 sしかないので、分割の違いで「コアが半分でも同じ速さ」は説明できない。チャネルを半分にした比較は分割もrankも同じ（#61）。coefficient.datはspread64とpacked64の間で、またbaselineとBonusの間で、各配置でビット一致。全rankがCPUに固定されたまま（keeper 64/64、128/128）。
"""

NOTES["s_changes"] = """
EN (Q32, isn't skipping boundary updates prohibited?): It skips no check. At six places the code built boundary values of a surface integral, exchanged them across processor boundaries, and then used only the cell values. We form the same cell values with the same loop and skip only the values nobody reads. Boundary conditions, every exchange the solution uses, and the bounding of k and omega are unchanged.

JP: no unused boundary updatesの6か所：ラプラシアンの非直交補正、bounded対流項のfvm::Sp、補正付き対流項、連続の式の誤差、pEqn.Hの右辺、kOmegaSSTのdivU。fvc::divとfvc::surfaceIntegrateをfvc::surfaceIntegrateInternalに置き換えるだけで、中身は同じsurfaceIntegrateのループ。patchのファイル名は提出物で0001〜0004。
"""

NOTES["s_detail"] = """
JP: 提出物のpatch（bonus/patches/）の要点。次のスライドと合わせて、関数名と各変更の対照比較（同じ時期に3本ずつ）を示す。掲載コードは引数・名称を短くした要約。面の順序と成分ごとの収束判定は保たれる。各効果は直前の構成を対照にした同時期の値。coefficient.datは同じ分割の未改変ビルドと1/2/4ノードでビット一致（以前スライドの下にあった注記）。
"""

NOTES["s_each"] = """
EN (Q6, why are the effects different on 1, 2 and 4 nodes?): On 1 node each rank holds four times more data than on 4 nodes, so more of it comes from DRAM, and removing array passes saves more there (U in one pass: −6.4% against −2.3%). On 4 nodes we tested the same idea by giving each core less memory: with 64 ranks per node the patches gain 7.9% on all channels and 11.4% on half of them.

JP: 各変更を直前の構成と同じ時期に比べた値で、別々の実験なので足し合わせない。4ノードは3〜4本ずつ、1・2ノードの多くは1本どうし。どのソース変更も coefficient.dat はビット一致。
"""

NOTES["s_profiles"] = """
JP: 図の中央の「multiLevel + no copies only」は、multiLevelに最初のソース変更（no copies in the solvers）だけを入れた版。CrayPATの診断run（4ノード、512 rank、40 step）。最初の変更だけを入れたBonusから最終Bonusまで、rankあたりの計算時間は104.2 → 94.9 s、MPIは約23.5 sで変わらない。rank間の差（最大/中央値1.07）は残る。段階別の割合（stack）は版をまたいだ効果の大きさには使わない（#53）。
"""

NOTES["s_efficiency"] = """
EN (Q6, super-linear scaling): We measured counters at 1, 2 and 4 nodes: per cell and step, the L1 refills from DRAM fall by 30% from 1 to 4 nodes, almost all in the sparse-matrix kernels, whose scattered cell arrays shrink to 1 MB per rank and fit in L3.

JP: #66、Basic（対応付けの前）、uProf data_access、NUMA領域ごとに1 rank、rank数・step数・rankあたりのセル数で正規化。1セルあたりの時間は4ノードで0.873倍（このconfigの効率1.145）。
"""

NOTES["s_cd"] = """
EN (Q12, why is the 80-step Cd below the reference?): Cd after 80 steps depends on the decomposition. The organisers' own scotch run also gives 0.327 at 80 steps, and their notes say hierarchical and scotch differ by 0.7%, 3.0% and 3.5% at 40, 80 and 150 steps. The Bonus value is identical to its unmodified baseline, so the gap does not come from our source changes.
EN (Q13, why does your Cd differ from the organisers'?): With the same split, ours is 0.284049 against their 0.283983. With the site module and our scripts we got their value exactly, so the difference comes from our build (AMD's math library), not from the method.

JP: 主催者の値は tasks/4.3 の表と「What Cd tells you」（2ノード80 stepでhierarchical 0.336869、scotch 0.327130）。目安の0.34はOHC-1の別の機械での値（0.334〜0.345）。
"""

NOTES["s_repro"] = """
EN (Q18, can the organisers reproduce your Basic number?): Yes. build/build.pbs builds from the official public sources, and run/submit.sh 1|2|4 runs the whole Allrun chain with plain qsub. We re-ran them ourselves: coefficient.dat was bit-identical at every node count, and the time within 0.4% of our recorded means.

JP: #54、#63。Basicの再実行は別の日・別のホストで記録より0.24〜0.36%遅いが、10月の多くのrunが入る±0.5%の中。ビルドは共用のqdevで遅くなることがあるので、build.pbsのwalltimeを4時間にした。
"""

NOTES["s_rejected"] = """
EN (Q4, is equal cell count enough?): It mattered most. Weighting cells by their face and point work made cell counts uneven and slower (+2.2%, +6.1%); a METIS two-constraint split balanced faces better but added 18% processor faces (+1.46%).
EN (Q20, what would you do next?): Balance each stage using measured per-rank times, and move fewer bytes still: fuse the assembly of U, k and omega across terms, or the GAMG residual with its restriction. We expect a few per cent from these, not another 10%.

JP: 全一覧（REPORT §10）。重み付き分割は3回試してすべて遅くなった（#37、#45）。壁の面で取り切っても1.063 → 1.056の見込み（#57）。
"""

NOTES["s_compiler"] = """
JP: #36 D。4ノード、scotch、各3本、同じ時期（2026-10-03）。網掛けは対照の範囲で、どの平均もその範囲の中。PGOは+0.13%（#59、Cdはビット一致）。ループがメモリを待っていて命令を待っていないので、コンパイラでは速くならない。
"""

NOTES["extra"] = """
[0:30]
EN: One more thing: a gain we did not count. In the call stacks, every sweep ended with a residual and an MPI_Allreduce for the convergence check. With fixed iterations, all but the last of those results are thrown away. Computing it only once takes a step from 2.60 to 2.25 seconds, bit-identical. We did not count it: it only helps the benchmark's fixed iterations, and skipping that work could be read as less work per step, which the rules prohibit. Thank you.

訳（参考）: 最後に、数えなかった高速化です。call stackを見ると、どのsweepも、収束判定のための残差とMPI_Allreduceで終わっていました。反復回数が固定なので、その結果は最後の1回以外捨てられています。1回だけ計算するようにすると、1 stepは2.60秒から2.25秒になり、結果はビット単位で同じです。でもこれは数えていません。ベンチマークの固定反復にしか効かず、省いた計算が、ルールが禁じる「1 stepあたりの仕事を減らすこと」と読まれ得るからです。ありがとうございました。

JP:
- 見つけた経緯（#68の本文）：#53のeu-stack（最終Bonus、4ノード、48 rank）で、Uの3成分のGauss-Seidelに残差1.1%＋gSumMag（Allreduce）1.2%＋normFactor 1.1%、k・ωのsmoothSolverにgSumMag 1.2%、normFactor 2.5%などが出ていた。v2512のソースでは、smoothSolverは毎sweepの後に残差を作ってAllreduceし、収束判定に使う。tolerance 0・relTol 0では判定が成立しないので、最後の1回以外の結果は捨てられる（最粗段のPCGもminIter = maxIter = 35で同じ）。
- 以前の「LESSON: Speed up the computation, not the benchmark」の札は外した。言うなら口頭で。
- #68、branch experiment/issue68-skip-unused-residuals（e2e2ae8、最終Bonus fa4f5b0の上）、patch 0005-skip-unused-convergence-residuals.patch。4ノード2.250 vs 2.595 s/step（−13.3%、同時期に交互に3本ずつ、範囲は重ならない）。1ノード10.29 s/step（−11.8%）、2ノード4.93（−12.7%）は各1本。今のBasic（2.898）からは4ノードで−22.3%。
- coefficient.datは1/2/4ノードでビット一致、solverログ1,323行（全残差と反復回数）が全行一致。
- 数えない理由：固定反復はベンチマークの取り決め（ケースのREADME、OHC-1は、hardware trackでfvSolution.fixedIter、software trackはfvSolution.fixedTol（pはtolerance 1e-7・relTol 0.01、U・k・ωは1e-8・0.1）から始めるとしている）。fixedTolでは元のコードが走る。ルールは「less work per step」を禁止しており、省いたノルムを仕事と読まれ得る。Bonusの4つの変更は、どの収束設定でも効く。
- 考え方自体はOpenFOAMにもある：v2512のsmoothSolverは、nSweepsが負のときは決まった回数だけ回して残差を計算しない。
- 言い方：「過学習」というより「計測の取り決めにだけ効く高速化」（Goodhartの法則の例）。Bonusの4つの変更はどの収束設定でも捨てられる計算を省いたもので、fixedTolでも効く。この線引きを言えることが、この1枚の価値。旧課題の資料の「代理指標を良くしても意味がない」と同じ姿勢を、自分たちの結果に当てはめた例として話せる。1 stepの約0.35秒（約13%）が、この規模での収束判定の値段。
- Q34（もう10%速くならないのか）：同じ計算・同じ仕事量では難しい。1 stepはメモリ帯域に従うので、運ぶバイトを減らすかキャッシュの再利用を増やすしかない。残っている案（U・k・ωの組み立ての融合、GAMGの残差と制限の融合、ラプラシアンの係数と対角の融合）は面の配列への往復を1〜2回ずつ減らすもので、合わせて数%の見込み。10%の利得には、ルールで禁止された別の計算か、この1枚のようにベンチマークの固定反復だけで許される変更が要る。
"""
