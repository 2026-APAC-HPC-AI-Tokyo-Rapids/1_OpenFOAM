"""Speaker notes of the cover, the Q&A index and the supporting slides: an English answer for the questions the slide is for,
then a Japanese memo for the team (sources, caveats); the cover's like the main slides', what to say first. The notes of
the 24 main slides come from ../slides.md (build_deck.py plan_notes), where what to say, the script, its translation and
the memo are written."""

NOTES = {}

NOTES["cover"] = """
[0:05]
言うこと:
- チーム名（Tokyo Rapids with RIKEN）を言う
- HPCの課題、OpenFOAMの発表から始める

参考原稿（EN）: We are Tokyo Rapids with RIKEN. We start with the HPC task, OpenFOAM.

訳: Tokyo Rapids with RIKENです。HPCの課題、OpenFOAMから始めます。
"""

NOTES["index"] = """
JP: 質疑用の補足スライドの目次です。各行をクリックすると、そのスライドへ飛びます（スライドショー中）。スライド番号を打ってEnterでも飛べます。補足は20枚です（第8版で、試して残さなかったことの一覧を本編（デッキ14枚目と25枚目）へ移し、固定と分割の掛け合わせ（11/03）、試した分割の一覧、玄界でのほかの並べ方（11/03）を足した。外したものは slides.md の「補足」の節）。補足はスライドショーでは非表示なので、本編の後に流れて映ることはありません。MPIの上位3つはデッキ6枚目、採否の決まりはデッキ3枚目にあるので、ここには載せていません。本編の各枚のノートには、その枚に関係する想定質問と補足の枚が書いてあります（11/03）。数えなかった高速化（#68）は、運営の答え（11/02、どの段でも数えない）を受けてデッキから外しました（聞かれたときの答えは slides.md の想定問答）。
"""

NOTES["s_aspire"] = """
EN (Q1, why ASPIRE-2A?): Last year we competed on Gadi, so this year we wanted to learn the other contest machine. And OpenFOAM works with very many files. One build is about 36,000 files, and every decomposed case adds thousands. Our Gadi project allows 0.2 million files and 1 TB, and in August three setups at the same time already hit the file limit. ASPIRE-2A allows 200 million files and 100 TB, so we could keep every build, case and run record.

JP:
- 帯域：カタログ409.6 GB/s、STREAMで約290 GB/s。L3ごとに1スレッド（ノードで16）で飽和（#36）。128コア全部では269〜273 GB/s。
- ネットワークの出典：TOP500「ASPIRE 2A (CPU Partition) - HPE Cray EX425, AMD EPYC 7713 64C 2GHz, Slingshot-10」、NSCC「All nodes are connected with HPE Slingshot Interconnect (Dragonfly Topology)」。ジョブから見えるNICはMellanox製（mlx5）で、UCXとOFIの両方が使える。
- 数字の出典は platforms/gadi/README.md（inode上限212,100、2026-08-17の3件同時の Disk quota exceeded）と、ASPIRE-2Aの lfs quota（100 TB、2億inode、2026-10-07）。
- 言わないこと：Gadiの利用停止、「ノードが空いていた」（実際は4ノードで4時間以上待った記録がある）。
"""

NOTES["s_settings"] = """
EN (Q8, why rebuild?): A run with the site module gave the same speed, minus 0.08 percent. Our own build records exactly what ran, and the Bonus patches need a build anyway.
EN (Q16, why UCX?): In September every 2- and 4-node run with the default OFI died with SIGBUS at MPI_Finalize, while UCX completed every run. The organisers' later workarounds avoid the crash, but under our placement they were 0.77 and 0.50 percent slower than UCX, with the same Cd.
EN (Q17, is the pinning fix allowed in Basic?): Yes. numactl sets the memory policy before each rank starts, and taskset sets the CPU affinity from outside. F1 lists job scripts, rank placement and affinity as Basic.

JP:
- モジュール：PrgEnv-gnu/8.3.3、aocl/4.0.0、cray-mpich-ucx/8.1.15（craype-network-ucx）。
- ストレージ：/scratch（Lustre、共有）にメッシュ、ビルド、run directory。各ノードは分割済みケースをノードローカルの$TMPDIRへコピーし、solverはそこだけを読み書きする（-hostRoots、-ioRanks）。計測区間のファイルI/Oは実行時間の約0.01%（#46）。
- OFIとUCX（#56、#60）：Basic（対応付けの前）、4ノード、転送方式だけを変更、同じ時期に交互。OFI（FI_OFI_RXM_USE_SRX=0）2.942 対 UCX 2.920 s/step（+0.77%、範囲は重ならない）、FI_VERBS_PREFER_XRC=0は+0.50%（1本ずつ）。Cdは同じ、SIGBUSなし。OFI自身のばらつきも0.26%なので、私たちのrunのばらつきが小さいのはUCXのおかげではない（Q15）。
- 固定：LD_PRELOADは使っていない（Bonusの範囲になるため）。全ジョブのログで、各ノード128/128 rankが固定されている。
"""

NOTES["s_noise"] = """
EN (if asked why one job is never enough, an example): One job on 27 September took 5.03 s/step, an outlier from a slow period. When we alternated three jobs of each in the same period, scotch was 10.5% faster. Since then we never decide from a single job.
EN (Q28, are 40-step profiles representative?): With fixed iterations every step does the same work, so 40 steps show the same pattern as 150. Profilers change a step by −1% to +6%, so we never use profiled times as results.

JP: #47。92本、29構成（同じcommit・build・ノード数・分割で3本以上）、2026-09-21〜10-05。多くは構成の中央値から±0.4%以内。9月には84%、91%遅い単発のrunがあった。run内のstep間の標準偏差とrun間のばらつきは別物で、150 stepを150個の独立な標本として扱わない。遅い回の原因をホストだけに断定しない（同じホストで後に正常なrunがある）。
"""

NOTES["s_reference"] = """
EN (Q15, why is your spread so much smaller?): Our 5 Basic jobs on 4 nodes lie within 0.18%; the organisers' 5 scotch jobs spread over 12%. It is not UCX: our jobs with the organisers' transport also lie within 0.26%. The main difference is the placement: every rank pinned with its memory on its NUMA domain. Our own Baseline without working pinning varied by 8%.

JP: 主催者の設定（tasks 4.3）：サイトのモジュール、オプションなしのmpirun、既定のMPI設定、固定なし。主催者のscotchの平均に対して、Basicは−8／−13／−12%、Bonusは−29／−32／−28%（1/2/4ノード）。ビルド、MPIの転送方式、配置がすべて違うので差の原因は1つではない。参考として見せるだけで、本編の比較は自分たちのBaselineに対して行う。
"""

NOTES["s_repro"] = """
EN (Q18, can the organisers reproduce your Basic number?): Yes. build/build.pbs builds from the official public sources, and run/submit.sh 1|2|4 runs the whole Allrun chain with plain qsub. We re-ran them ourselves, for Basic and for the final Bonus: coefficient.dat was byte-identical at every node count, and the time within 0.4% of our recorded means.

JP: #54、#63、#69。Basicの再実行（10/16、Actions 38843636251）は別の日・別のホストで記録より0.24〜0.36%遅いが、10月の多くのrunが入る±0.5%の中。最終Bonusの再実行（10/26、Actions 40248914838）は、公開URLのソースにbonus/patchesの14個を当ててビルド（PBS 25990973、1時間9分）し、記録の平均に対して−0.31／−0.24／+0.22%、coefficient.datは最終計測とバイト一致。0001〜0004の版の再実行（10/07、−0.21〜+0.16%）は表から外した。ビルドは共用のqdevで遅くなることがあるので、build.pbsのwalltimeを4時間にした。
"""

NOTES["s_network"] = """
EN (Q29, isn't the exchange across subdomain boundaries the bottleneck?): Not by volume. Reordering the ranks so that neighbouring subdomains shared a node cut the faces between nodes by 92% with the same subdomains and changed a step by +0.1%, and 55% more network bandwidth by −0.01%. What costs time is the synchronisation: about 1,600 global sums per step make every rank wait for the slowest one, and the slowest ranks have almost no neighbours on other nodes.
EN (Q31, did you profile the network?): Yes, at three levels: IMB after every benchmark run, CrayPAT per call and rank, and experiments that changed only the network side. We did not read NIC or switch counters.

JP: rankごとのMPI_Isendの回数は、分割から数えた隣のrankの数と相関+1.000（1つの隣に1 stepあたり約1,324通）。メッセージの数は分割で決まり、待ちは計算の不均衡で決まる（#48）。16の最も遅いrankのうち13はノード外の隣を持たない。
"""

NOTES["s_pinning_decomposition"] = """
EN (Q41, without pinning scotch did not run in turns with hierarchical; how sure is the 6.1 percent?): Our Baseline ran nine days after the six unpinned scotch jobs, and its jobs spread over 8 percent, but five of the six scotch jobs were faster than all three Baseline jobs, by 6.1 percent on average. The same setting ran again in the pinning experiment, three jobs at 3.670 seconds, and all six scotch jobs were faster than those. We kept scotch on the comparison in turns once every rank was pinned, three jobs each, 10.5 percent less. The two fixes also helped each other: the slowest rank computed 1.46 times as long as the median rank without pinning, 1.16 times once pinned and 1.06 times with scotch as well.

JP:
- 11/03の10回目と11回目（ユーザー：分割 → 固定 → ノードの木の順に。固定なしのscotchのジョブは、対照と比べていなくても実験条件は同じなので全部プロットする）：本編7枚目（デッキ8枚目、Decomposition results）で固定なしのhierarchicalとscotchを比べるので、この枚は、その比較が交互でないことと、固定した後の交互の比較（−10.5%）を見せる枚になった。12回目に、固定なしのhierarchicalを私たちのBaselineの3.650にした（ユーザー：3.670と3.650の2つの値があるのはよくない。Baselineに合わせる）。
- データ（4ノード）：hierarchicalの固定なしは私たちのBaseline（#62、10/12、data/baseline_runs.csv の3.6003、3.5313、3.8170。3.650、SD 4.1%）、固定ありは #36（10/02）の data/decomposition_basic.csv の3.2912、3.2593、3.2217（3.257、SD 1.07%）で、−10.7%。固定の実験で交互に流した固定なしのhierarchical（#36、data/start_unpinned.csv の3.6983、3.5850、3.7270。3.670、SD 2.05%）に対してなら−11.2%で、スライドでは使わず、Q41で「同じ設定をもう一度測った値」として言うだけ。scotchの固定ありは同じファイルの2.9154、2.9227、2.9054（2.915）。hierarchicalの2つとscotchの固定ありは10/02に交互に流した。固定ありはLD_PRELOADでMPI_Initの直後に固定し直す方法で、Basicのnumactl＋見張りと同じ速さ（scotchで2.919と2.917）。
- 固定なしのscotchは、10/03の#36 A3の固定なしの6本すべて（data/pinning.csv のNeither）：PALSの`--cpu-bind`と`--mem-bind`を頼んだ2本（`d890a4d`、3.3763、3.4137）と、BaselineのようにPALSの`--cpu-bind depth`だけを頼み、前処理を別のPBSジョブに分けた4本（`04a89cf`と`b8bd859`、3.5561、3.3593、3.4248、3.4368）。どれもMPI_Initで固定が外れた（d890a4dは実行中の/procで0/128、4本目の37125347729はノード0の128 rankすべてが`Cpus_allowed_list 0-255`、issue #36）。6本で3.428（SD 2.0%）、Baselineより6.1%短い。6本のうち5本はBaselineの3本のどれより速く（Baselineの最も速い3.5313より遅いのは3.5561の1本）、固定の実験の固定なしのhierarchical（3.670）の3本には6本とも速い。10回目までは、ほかの配置と同じ土台（`1854ea6`）の2本だけ（3.395）だった。
- scotchの固定の効果は、この表では10/02に交互に流した固定（LD_PRELOAD、2.915）に対して−15.0%、本編9枚目（デッキ10枚目、Pinning results）の図では同じ日の両方の固定（numactl＋見張り、2.917）に対して−14.9%。比べた固定のジョブが違うだけで、どちらも正しい。
- 遅いrankの比：hierarchical・固定なしは私たちのBaseline（OpenFOAM profiling、38219862855、rankごとの計算115.02 / 78.56 s）、hierarchical・固定ありはCrayPATの（プロセス − MPI）（#38、37181991433）、scotch・固定ありはBasicの対応付けの前（OpenFOAM profiling、37714968610、104.17 / 97.95 s）。道具が2つ混ざっているので、比の傾向として見せる。
"""

NOTES["s_renumber"] = """
EN (Q39, if asked whether we measured the other orders): Not on ASPIRE-2A, but on another machine, Genkai, with the official case on four nodes, each order once in each of four rounds. No renumbering was 0.7 percent slower, spring 3 percent and a random order 11 percent. Reverse Cuthill–McKee was within the spread, faster in three rounds and slower in one. So no order beat the default, as their principles say, and every order changed Cd, by up to 1.3 percent after 40 iterations.

JP:
- 出典：data/renumber_genkai.csv、presentation/openfoam/renumber/（README.md、renumber-genkai.pjm、analyse.py）。玄界、4ノード×112 rank、plain scotchの448分割、未改変のv2512（Actions 35722802934のビルド）、40反復、5つの並べ方を1巡に1回ずつ、巡ごとに順番をずらして4巡（PJM 7238151で1〜2巡、7238163で3〜4巡。1つの巡は同じ4ノード）。準備（decomposePar）はPJM 7238148。
- 既定（Cuthill–McKee）は平均1.958 s/step。RCM −0.19%（巡ごとに−0.38、−0.49、−0.21、+0.31%）、none +0.70%（4巡とも遅い）、spring +3.26%、random +10.6%。私たちの決まり（全候補が全対照より速い）では、どれも残りません。
- Cdは並べ方ごとに4巡とも同じで、並べ方の間では違います（40反復目、既定0.43768に対してRCM −1.32%、none −1.21%、spring −0.65%、random +0.09%）。固定反復のGauss–Seidelがセルの番号の順に掃くためです。並べ方を変えるなら、F3（公式の反復数で、変更前のrunとCdが±0.5%以内）を確かめる必要があります。
- 玄界はコアあたりL2 2 MB（ASPIRE-2Aは0.5 MB）、L3はソケットで112.5 MB（ASPIRE-2AはコアあたりL3 4 MB）。4ノードで各rankは約14.6万セルを受け持ちます。ASPIRE-2Aでの時間ではなく、傾向として見せます。
- renumberMeshのband（番号が最も離れた隣どうしの差、448分割の最大）とprofile（1セルあたり）：既定11,347と2,705、RCM 11,347と2,562、none 146,078と3,880、spring 68,712と3,025、random 147,291と54,368。
"""

NOTES["s_scotch"] = """
EN (Q30, why does the Basic gain grow with the node count?): Mostly through the decomposition. scotch gains 1.3, 2.5 and 10.5 percent on 1, 2 and 4 nodes, and the node tree gains only on 4 nodes. We think the axis-aligned cuts of hierarchical become more uneven when the subdomains are small, but we have not verified it.

JP: data/decomposition_basic.csv（同じ配置、交互に3本ずつ、どちらも固定あり）。4ノードの−10.5%は補足34枚目の表とQ41の値（本編7枚目、デッキ8枚目の−6.1%は固定なしで、私たちのBaselineに対して）。どちらも色を付けない（Baseline、Basic、Bonus以外の結果に色を付けない、ユーザー、11/03）。ISC26の課題（Task 5、分割方法を変えた効果）にも当たる。hierarchicalの偏りは壁の面（車の表面）の数と相関した（#38）。
"""

NOTES["s_cores"] = """
EN (Q23, how do you know it is memory-bound without the memory counters?): On 4 nodes, 64 ranks per node are as fast as 128 when they keep all memory channels, and 2.1–2.2× slower when the same 64 ranks share half the channels, as much as the measured bandwidth drops. Compiler flags and PGO change nothing, and our first four patches, which keep every operation, gain most where memory is scarcest.
EN (Q24, bandwidth or latency?): Bandwidth. If the latency of each core's requests set the speed, halving the cores would halve the throughput; it changed by −1% to +2%.

JP: コアを半分にした比較は分割が512から256に変わるが、帯域に比例しない部分は1 stepあたり約0.1 sしかないので、分割の違いで「コアが半分でも同じ速さ」は説明できない。チャネルを半分にした比較は分割もrankも同じ（#61）。表の「Bonus」は0001〜0004の版（fa4f5b0、10/10）で、後の10個の配置実験はしていない。coefficient.datはspread64とpacked64の間で、またパッチの有無の間で、各配置でビット一致。全rankがCPUに固定されたまま（keeper 64/64、128/128）。
"""

NOTES["s_callstack"] = """
EN (Q, how did you find the ten later changes?): We re-aggregated the CrayPAT call-stack samples of the Bonus with the first four changes by function and call path. The turbulence model's correction took 27 percent of the samples, mostly field algebra, gradients and the k and omega solves. The Gauss–Seidel sweeps and residuals came next, and the coarsest CG, which is mostly global sums. We read the v2512 source behind each and ranked the candidates.

JP:
- 出典：research/profile-reaggregation-fa4f5b0/summary.md（#53、fa4f5b0、4ノード、512 rankのうち48 rank、時間ループの中の標本2,396本）。段階はmainの直下の呼び出し先で分けた（pの解き31.8%、kOmegaSSTのcorrect 26.9%、Uの解き20.5%、Uの組み立て11.8%、pの組み立て6.6%）。MPIは各段階の標本のうちMPIの中にあったもの（pの解きでは53%）。3%未満の段階（function objects、U・fluxの補正、連続の式の誤差）は other にまとめた。データは data/callstack_phases_fa4f5b0.csv。
- stack sampleはMPIの割合を約1.8倍に多く見せる（#53）ので、MPIの割合の大きさにはCrayPATのタイマーの値（Basicで19%）を使う。
- 最終Bonus（14の変更）のcall stackは取っていない。関数の段まで描いたflame graphは次の枚（同じ標本）。
"""

NOTES["s_flame"] = """
EN (Q, which functions took the time?): These are the same samples, by function. Each tower is a chain of calls and its width is its share of the samples. The widest are GAMG for the pressure, the k-omega SST correction and the Gauss–Seidel sweeps for U. At the coarsest GAMG level almost every sample was in MPI, mostly global sums, which led us to one global sum per CG iteration. The k-omega SST correction was mostly field algebra over the cells, which led us to single cell loops.

JP:
- 出典：生のsample（Actions 37529785072 の profile-raw.tar.zst、成果物の保管庫、7,117,215 bytes、SHA-256はartifact-manifest.jsonと一致）を11/01に取り直し、research/profile-reaggregation-fa4f5b0/analyse.py で data/callstack_folded_fa4f5b0.txt（390通りのstack）を書き出した。summary.md は出典のパスの1行を除いて同じものが出る。段階ごとの本数とMPIの本数は、前の枚の data/callstack_phases_fa4f5b0.csv と全段階で一致。
- 描き方：下から時間ループ、段階、関数の順。MPIの中のstackは、OpenFOAMが呼んだMPIの関数（MPI_Allreduceなど）で止め、ライブラリの中の関数はその箱に含めた。15段目より上（2本だけ）は描いていない。幅が0.4%以下の箱には名前を書いていない。
- 数字：GAMG（p）752本 31.4%、kOmegaSSTのcorrect 644本 26.9%、UのGauss–Seidel（smoothSolver::solveGaussSeidelComponents）455本 19.0%。GAMGの最も粗い段（solveCoarsestLevel）158本 6.6%のうち155本がMPIの中（MPI_Allreduceが118本）。GAMGのscale（補正の倍率）は228本 9.5%で、うちMPIが127本。MPI全体は748本（31.2%）。
- stack sampleはMPIの割合を約1.8倍に多く見せる（#53）ので、MPIの大きさを言うときはCrayPATのタイマーの値を使う。最終Bonus（14の変更）のcall stackは取っていない。
"""

NOTES["s_decompositions"] = """
EN (Q4, is equal cell count enough?): It mattered most. Weighting cells by their face and point work made the cell counts uneven and slower, by 2.2 to 6.5 percent, and a METIS decomposition with two constraints balanced the faces better but added 18 percent more faces between subdomains, 1.5 percent slower.
EN (if asked whether we tried other methods): Yes, the table lists every decomposition we timed. kahip, METIS and ptscotch on their own did not run, because the build had only stub libraries for them, and simple and structured we did not try.

JP:
- 出典（11/02に調べ直した）：hierarchical (4 8 16)のzyxは#35（1本を別の日の5本と比べた）、並べ替えは#36 B（3対3、10/02）、scotchは#36（3対3）、対応付けは#63（5対5、10/16に採用）、品質重視のScotchの戦略は#63（892861f、1本）。multiLevel (4 128)は#32（2対2、9/22、LD_PRELOADの固定）、(4 2 4 16)は#42（plain scotchに対して4対4、numactlの固定）、(4 2 8 8)は#35（1対1、40 step）。車輪と床下のセルに重み3は#33（tag 3922bdc、+64%と+10.8%、2対3、Cd −2.595%でF3を満たさない）、境界のセルに重み2（weightField 2:1）は#37 F1（3対6）、点の割合での重み×2と×12は#37（0001ありのmultiLevelに対して1対4、×12は32ビットのScotchであふれた）、METISの2つの制約（段ごとにmethod manual）は#45（e2730dbに対して2対3、10/05）。kahip、metis、ptscotchは9/29に、ビルドのライブラリがスタブだけで動かなかった（#35）。
- 壁の面で重みを取り切っても、計算の最大/中央値は1.063 → 1.056の見込みだった（#57）。
"""

NOTES["s_changes"] = """
EN (Q32, isn't skipping boundary updates prohibited?): It skips no check. At six places the code built boundary values of a surface integral, exchanged them across processor boundaries, and then used only the cell values. We form the same cell values with the same loop and skip only the values nobody reads. Boundary conditions, every exchange the solution uses, and the bounding of k and omega are unchanged.

JP: 最初の4つ（0001〜0004）。no unused boundary updatesの6か所：ラプラシアンの非直交補正、bounded対流項のfvm::Sp、補正付き対流項、連続の式の誤差、pEqn.Hの右辺、kOmegaSSTのdivU。fvc::divとfvc::surfaceIntegrateをfvc::surfaceIntegrateInternalに置き換えるだけで、中身は同じsurfaceIntegrateのループ。patchのファイル名は提出物で0001〜0004。後の10個は次の(2/2)。
"""

NOTES["s_changes2"] = """
EN (Q, are the later changes still the same computation?): Yes, in the sense of the rules. None changes the iteration counts, the convergence tests, the number of steps or the discretisation, and every solve does its full work. Seven keep every operation and its order. Three can change the order of some sums: the Gauss–Seidel source is added last instead of first, the coarsest-level CG takes one global sum per iteration instead of three, and the residual is formed inside the last sweep. In exact arithmetic the iterates are the same; Cd moves by at most 0.0005 percent.

JP: #69。実装はCodex（GPT-6.1 Sol）、各パッチと説明は提出物の bonus/patches/ と bonus/README.md。fa4f5b0（0001〜0004）の#53のcall stackを集計し直して候補を順位付けし、4ノードで直前の構成と3本ずつ比べた（0013〜0015、0016は対照の数日後）。最後に1/2/4ノードでfa4f5b0と交互に3本ずつ流し、−12.16／−11.44／−9.34%。
- 0010（wallShearStressを壁だけで計算）は、本番ケースでは値を書き出さずログにも出ないので、ローカルの逐次の試験（151,600セル、40 step。0010を外した版と、coefficient.dat、最終時刻のU・p・k・ω・nut・cp・wallShearStressがビット一致）を証拠にした。
- 0012はDIC前処理のPCGだけをChronopoulos/Gear型にする（Ghysels & Vanroose 2014）。どの許容誤差でも収束判定と反復の意味は同じ（minIter/maxIter、特異性の判定、報告する残差も）。35反復で大域和が105回から36回に。単独では−0.30%と小さいが、3本とも一貫して速く、Cdの差も極小なので束に残した。
- 0014の運動量予測子は、圧力勾配をsourceに足してから解き、元に戻す（対角はビット単位で戻るので、A()・H()・H1()は元の行列を見る）。
- 実装しなかったもの：P1（勾配の使い回し）はfvSolutionのcacheと同じ効果をソースで有効にする形になり、F2の線引きで裏口と読まれ得るので、チームの判断で見送った。0017（bound()の平均を対象セルだけで）は大域和が1回増えるので実施せず。0018は不採用（デッキ25枚目の表）。0005（#68）は、運営の答え（11/02）でどの段でも数えないと決まり、デッキから外した。
- 意図別の一覧はデッキ20、21枚目、図にした例（0002と0001）はデッキ22枚目。
"""

NOTES["s_each"] = """
EN (Q6, why are the effects different on 1, 2 and 4 nodes?): On 1 node each rank holds four times more data than on 4 nodes, so more of it comes from DRAM, and removing array passes saves more there: U in one pass gains 6.4% against 2.3%, and the ten later changes 12.2% against 9.3%. On 4 nodes we tested the same idea by giving each core less memory: with 64 ranks per node the first four changes gain 7.9% on all channels and 11.4% on half of them.

JP: 各変更を直前の構成と比べた値で、別々の実験なので足し合わせない。4ノードは3〜4本ずつで、*の2つ（0013〜0015、0016）は対照の数日後に測った。1・2ノードの多くは1本どうし。最後の行は最終計測（10/26、fa4f5b0と1bc34b9を交互に3本ずつ）。図は各ジョブを自分の対照の平均に対する%で描いたもので、灰色の対照の点の散らばり（±0.2%程度）がその時期のばらつき。coefficient.datは0011と0012以外の変更でビット一致（4ノード）。
"""

NOTES["s_counters"] = """
EN (if asked why most demand refills come from L2, isn't the data in cache?): Demand refills do not count hardware prefetches. The arrays we stream are brought from DRAM into L2 by the prefetcher, so their loads show up as L2 hits. With the first four patches, L2 accesses including prefetches fall 10 percent and DRAM refills 17 percent.

JP:
- カウンタ（#55）：1ノード、128 rank、40 step、multiLevel、uProfのdata_accessをNUMA領域ごとに1 rank、最初の4つの版と変更なしの版を各2本。計算部分だけ（MPI、UCX、Pstreamを除く）の7 rankの平均。同じ側の2本は、どのカウンタも約4%以内で一致した。
- 右の表：チャネルの比較は#61（4ノード、64 rank/ノード、各2本）。ノード数の比較は#69の最終計測（1/2/4ノードで交互に3本ずつ）。
- 言い過ぎない点：数えているのはL1のdemand refillで、DRAMの転送バイト数ではない（uncoreのカウンタは読めない）。後の10個はカウンタで測っていない。考察は slides.md の22枚目（Bonus results）のメモ。第7版では本編のBonus resultsにこのカウンタの図があったが、細かいので第8版で補足だけにした（ユーザー、11/02）。
"""

NOTES["s_cd_iterations"] = """
EN (if asked why Cd differs between decompositions): Cd after a fixed number of iterations depends on the decomposition. The organisers' own hierarchical and scotch runs end 3.5 percent apart after 150 iterations, and ours lie in that kind of range. The Bonus and the same decomposition without its source changes end 0.0004 percent apart.

JP:
- ISC26の課題（Task 4）の「ログから描くCdの収束グラフ」に当たる。4ノード、150反復。Basic（Boxの openfoam/results/4node/coefficient.dat）、Bonus（openfoam/bonus/results/4node/）、ソースを変える前のrun（openfoam/bonus/f3-baseline/4node/）、主催者のhierarchicalとscotch（tasks/4.3-aspire2a-logs/*-4node/coefficient.dat）。データは data/cd_iterations_4node.csv。
- 150反復の値：Basic 0.29302、Bonus 0.29139、変更前 0.29139、主催者のhierarchical 0.27392、scotch 0.28398。BonusとBasicの差は分割の違い（multiLevelと対応付けたscotch）で、ソースの変更ではない（Q13）。
"""

NOTES["s_cd"] = """
EN (if asked why the 80-step Cd is below the OHC-1 values): Cd after 80 steps depends on the decomposition. The organisers' own scotch run also gives 0.327 at 80 steps, and their notes say hierarchical and scotch differ by 0.7%, 3.0% and 3.5% at 40, 80 and 150 steps. The Bonus differs from its unmodified baseline by at most 0.0005%, so the gap does not come from our source changes.
EN (Q13, why does your Cd differ from the organisers'?): With the same decomposition, ours is 0.284049 against their 0.283983. With the site module and our scripts we got their value exactly, so the difference comes from our build (AMD's math library), not from the method.

JP: 主催者の値は tasks/4.3 の表と「What Cd tells you」（2ノード80 stepでhierarchical 0.336869、scotch 0.327130）。目安の0.34はOHC-1の別の機械での値（0.334〜0.345）。Bonusの欄は最終Bonus（1bc34b9）で、pre-change baseline（同じmultiLevelでパッチなし）とは5桁まで同じ。F3の値：1ノード 0.43827636195094927 対 0.43827636195043501（相対+1.2×10⁻¹²）、2ノード 0.32285928314184348 対 0.32285935413723610（−0.00002%）、4ノード 0.29138659643758436 対 0.29138777754153217（−0.00041%）。
"""

NOTES["s_efficiency"] = """
EN (Q6, super-linear scaling): We measured counters at 1, 2 and 4 nodes: per cell and step, the L1 refills from DRAM fall by 30% from 1 to 4 nodes, almost all in the sparse-matrix kernels, whose scattered cell arrays shrink to 1 MB per rank and fit in L3.

JP: #66、Basic（対応付けの前）、uProf data_access、NUMA領域ごとに1 rank、rank数・step数・rankあたりのセル数で正規化。1セルあたりの時間は4ノードで0.873倍（1ノードに対して4.58倍速い。並列効率で言えば1.145）。デッキ24枚目（Scaling）は第8版から、効率ではなく「1ノードの何倍速いか」で示す（ユーザー、11/02）。
"""
