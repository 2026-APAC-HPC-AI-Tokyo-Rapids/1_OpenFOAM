# OpenFOAMパートのスライド構成（第7版、作り直し中）

10/31から、HPCの本編を作り直しています（11/01の時点で13枚、約10分）。時間は短くせず、話さなくてよいこと（ルールの説明、飾り、重複）を削って、10分を本質的な説明に使います。スライドにはまだ手を付けず、この文書で骨組み、スライドの文、原稿を詰めてから、デッキを作り直します。

- それまでは、改訂版pptx（`~/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx`）と`deck/build_deck.py`は第6版（10/30、本編20枚・約10分15秒）のままです。
- 第6版までのスライドごとの詳しいメモ（数値の来歴、出典、但し書き）は、git履歴の第6版（commit `a1f18a3`の`presentation/openfoam/slides.md`）と、デッキのノート（`deck/notes.py`）にあります。この版では、本編に残す話の根拠だけを、各スライドのメモに書き直しました。
- スライドの文と話す原稿は英語、原稿の訳とメモは日本語です。
- 数値は公式指標（2 step目以降の1 stepの平均時間、s/step）で、主に4ノードの値で話します。図の1点は1ジョブです。
- 図はBoxの`presentation/openfoam/`にあります：`figures/`（グラフ）、`flow/`（ParaViewで描いた流れの動画と絵）、`decomposition/`（ParaViewで描いた分割の絵）。

## 10/31の方針転換

AIパートのチームメイトから、デッキについて指摘がありました（10/31。AIパート向けですが、HPCにもそのまま当てはまります）。

- 1タスク約10分なので、1枚を見せられるのは30秒ほど。今の枚は詰め込みすぎで、30秒では読み取れない。
- 重複する枚が多い。ルールを作った人にルールを説明する必要はない。最終結果を公式のベースラインと並べて見せ、そこから取り組みの順に話す。
- 見た目がよくても読み取りにくいグラフはやめる。これはAIパートのroofline（58枚目）のことです。HPCはrooflineを使っていないので、示しません。
- 小さな注記や、余白を埋めるだけの飾りなど、伝えることに効かないものは外す。「What we changed」のような言い回しや注記は、いかにもAIが書いたように見えるので減らす。
- 取り組みの段に番号を付け、詳しく説明する枚でもその番号で指す。

これを受けて、HPCは次のようにします（10/31に決定）。

- 時間を短くするのではなく、必要のないことを話さないことで、10分を意味のある本質的な説明の時間にする。
- スライドは単純に、堅くする（下の「見た目と言葉の決まり」）。
- HPCは取り組み方がAIと違う（段を積み上げるのではなく、測る → 律速を見つける → 直す、を繰り返した）ので、同じ形にはせず、外せないものを並べて骨組みを作る。

## 11/01に決めたこと

- HPCを先に、AIを後に話します。
- 色は、今のデッキの色合い（`deck/palette.py`）を使います。
- 図は、今使っているもの（`deck/deck_plots.py`の各ジョブの図、分割の絵、流れの動画など）を流用します。
- 流れの様子は、1枚目に動画を置くだけにします（原稿では触れず、流しておく）。第7版の最初の案の3枚目（流れの1枚）はなくしました。ISC26の参照の絵の視点は再現しません（ISCの課題ではないため）。
- ばらつきは、どの比較でも毎回測っています。だから最初の1枚にまとめず、時間の図に標準偏差を書き、Basicの結果の枚で「固定が外れていたことも原因で大きかったばらつきが、Basicで小さくなった」と言って、ばらつきの話を終えます。
- 採用の基準は、「なぜその大きさなら採用してよいか」を論理で言えるようにします（7枚目、Q36）。
- 効かなかったことは、典型的で効きそうに見えた手（コンパイラとオプション、ネットワーク、面を減らす・そろえる分割）に絞ります。高度な試み（境界交換との重ね合わせ、GAMGの最粗段など）は補足にします。
- 権限がなくて読めなかった量（メモリ帯域など）を、別の方法でどう特定したかは、必ず話します（3、8、9枚目）。
- おまけ（#68、数えなかった高速化）は、最後に短く話します。
- ASPIRE-2Aを使ったことは口頭で言い（1枚目の見出しにもある）、選んだ理由は補足に置きます（必ず聞かれるので）。
- Cdの収束のグラフは補足に置きます。
- rooflineは示しません。補足からも外します。
- 呼び出しのツリー（VTuneのようなcall stackの図）は、作れれば補足に置きます。手元にCrayPATのstack sampleの集計があるので、作れる見込みです（補足の節）。
- 有効数字をそろえます（下の「数値の決まり」）。

## 外せないもの

| | 外せないもの | 理由 | 本編 |
|---|---|---|---|
| a | 結果：主催者の共通ベースライン、私たちのbaseline、Basic、Bonus（4ノード） | 共通ベースラインは自分の結果の横に示す決まり（`tasks/5. Common Baselines.md`） | 1 |
| b | abstract：各段の律速とやったことを、1行ずつ | 結果を先に、道筋も先に見せる | 1（短く）、詳しくは2〜10 |
| c | ParaViewの流れ（動画を流すだけ） | ISC26 SCCのOpenFOAM課題（Virtual Part、Task 4） | 1 |
| d | MPIの上位3つ（呼び出し回数と合計時間、4ノード） | ISC26の課題（Task 3） | 2 |
| e | プロファイリング：律速をどう見つけたか | Task RulesのPresentation Excellence | 3、8 |
| f | 権限がなくて読めない量を、別の方法で特定したこと | チームが力を注いだところ | 3（`/proc`）、8（配置の実験、triad、コアのカウンタ）、9（IMB） |
| g | 速くなった最適化と、なぜ効いたか | Task Rules | 4、5、10 |
| h | ばらつき（ノイズ） | 旧課題の資料。どの比較でも測っている | 全部の時間の図（標準偏差）、6（Basicで小さくなった） |
| i | 採用の基準と、その論理 | チームの取り組み方の芯。主催者もSlack（10/30共有）で発表に入れてほしいと答えた | 7 |
| j | 典型的なのに効かなかった手と、その理由 | `tasks/README.md` R3、主催者のSlackでの回答 | 9 |
| k | Bonusの4点（R3：何を変えたか、なぜ同じ計算か、証拠、自分のBasicに対する速度向上） | `tasks/README.md` R3 | 10、11 |
| l | 1/2/4ノードのscaling | Task RulesのPresentation Guidelines、ISC26のTask 2 | 12 |
| m | 分割方法を変えた効果 | ISC26のTask 5 | 5、10 |
| n | 数えなかった高速化（おまけ） | 線引きを自分で言えることを見せる | 13 |

補足に必ず置くもの：ASPIRE-2Aを選んだ理由（Q1）、Cdの収束のグラフ（ISC26のTask 4）、効かなかったことの全部の一覧、call stackの図（作れれば）。

## 並べ方

1. 結果と道筋を先に見せる（1）。
2. 最初の律速を見つける：MPIの上位3つ → 道具ごとに分かったこと（2、3）。
3. Basicで直す：固定 → 分割 → 結果。ばらつきもここで小さくなる（4〜6）。
4. 小さな差を判定する決め方を示す（7）。ばらつきが小さくなった後なので、「誤差より大きいか」を数字で言えます。例も、Basicの対応付け（−0.7%で採用）とAOCC（不採用）です。
5. 次の律速を、読めないカウンタの代わりに実験で特定する（8）。
6. 典型的な手が効かなかった理由が、見つけた律速で説明できる（9）。
7. Bonusで運ぶバイトを減らす。何を変えたか、同じ計算である証拠（10、11）。
8. 1/2/4ノードで締める（12）。おまけを短く（13）。

測る → 律速を見つける → 直す、を2回まわした順です。

## 見た目と言葉の決まり

- 1枚に1つのこと。図か表は1つまで、本文は4行まで（1枚目だけは例外）。
- 見出しは、何の枚かを表す短い語句にします（MPI calls on 4 nodesなど）。見出しにコロンや矢印を入れません。
- 見出しの下の主張の行、TAKEAWAYやLESSONの札、Figure N・Table Nの番号、出典やrun IDの小さな注記、余白を埋めるカードやアイコンは置きません。出典と細かい条件はノートに書きます。
- 文は、数字の入った平叙文にします。標語や対句（「Benchmarks decide, profiles explain」「Move fewer bytes, not the same bytes faster」など）、「What we changed」「How we worked」のような見出し、ダッシュ（—）や中黒（·）でのつなぎは使いません。
- 色は今のデッキの色合い（`deck/palette.py`）のままにします。箱（カード）や飾りの図形は使わず、区切りは余白と細い線にします。表は横の罫線だけにします。
- 図は今のもの（`deck/deck_plots.py`の各ジョブの点の図など）を流用します。Figure Nの番号と副題を外し、時間の図には平均と標準偏差（SD）を書き添えます。
- 変更の番号：Basicの3つを(1)〜(3)、Bonusの2つを(4)と(5)にし、1枚目の道筋と、4、5、10枚目で同じ番号を使います。
- 文字の大きさは、本文18 pt以上、表16 pt以上です。
- 原稿は英語です。時間は1秒に約2.5語として見積もり、話す間を入れて約10分です。ノートには、英語の原稿、訳、メモの順に書きます。

## 数値の決まり（有効数字）

- s/stepは有効数字4桁にします（3.650、2.898、2.360、14.57、6.372）。Basic以降の4ノードのジョブの標準偏差は0.002〜0.004 s（0.07〜0.16%）で、4桁目がちょうどその大きさです。1%未満の差もこの桁なら見えます。これより細かい桁はノイズです。
- 標準偏差は%で書きます（SD 0.07%）。図では平均の横に「2.898 s/step, SD 0.07%, 5 jobs」のように書きます。
- %は小数1桁にします（−20.6%、−18.6%、−0.7%）。0.1%に満たない差は「within 0.1%」と書きます。
- 倍率は有効数字3桁（1.55×）、並列効率は小数2桁（1.15）です。
- Cdの差は、F3の照合に使った値の桁（−0.00041%など）で書きます。他者の値は出典の桁のまま引きます（主催者の3.415）。
- それぞれの変更は、同じ時期の自分の対照と比べた値で言います。だから段ごとに始点の値が少し違います（固定の比較の対照は3.670、本編のbaselineは3.650）。

主な数値（4ノード、平均、SD、本数）：

| | s/step | SD | 本数 | 出典 |
|---|---:|---:|---:|---|
| 主催者の共通ベースライン（hierarchical / scotch） | 3.415 / 3.576 | | 1 / 1 | `tasks/5. Common Baselines.md` |
| 私たちのbaseline | 3.650 | 4.1% | 3 | #62 |
| Basic | 2.898 | 0.07% | 5 | #63 |
| Bonus | 2.360 | 0.16% | 3 | #69 |
| Bonus＋数えなかった変更（おまけ） | 2.166 | 0.26% | 3 | #68 |

1/2ノード：baseline 14.57（SD 2.0%、6本）／7.427（2.0%、3本）、Basic 13.36（0.02%、3本）／6.372（0.08%、3本）、Bonus 10.23（0.32%、3本）／4.992（0.25%、3本）。並列効率（1 → 4ノード）はbaseline 1.00、Basic 1.15、Bonus 1.08です。

段ごと（4ノード、同じ時期の対照と交互に）：

| 変更 | 対照 → 候補（s/step） | 変化 | 本数 |
|---|---|---:|---|
| (1) 固定（ケース既定の分割で） | 3.670 → 3.257 | −11.2% | 3対3 |
| (2) scotch | 3.257 → 2.915 | −10.5% | 3対3 |
| (3) ノードへの対応付け | 2.918 → 2.898 | −0.7% | 5対5 |
| (4) multiLevel（対照はscotchの既定） | 2.918 → 2.873 | −1.5% | 4対4 |
| (5) 最初の4つ（0001〜0004、1つずつ） | 2.873 → 2.599 | −3.4、−2.3、−1.3、−2.8% | 3〜4対3〜4 |
| (5) 後の10個（最終計測でまとめて） | 2.603 → 2.360 | −9.3% | 3対3 |
| 不採用の例：AOCC 5.0／AOCL 5.1 | 2.910、2.911 | within 0.1%（範囲が重なる） | 3対3 |

（後の10個は、1つずつの比較では−2.0%（0006〜0010）、−1.0%（0011）、−0.3%（0012）、−2.5%（0013〜0015）、−3.8%（0016）です。数値は`data/*.csv`から計算しました。）

## 本編（13枚、約10分）

| # | 見出し | 載せること | 図・表 | 目安 |
|---|---|---|---|---|
| 1 | OpenFOAM on ASPIRE-2A | 共通ベースライン、私たちのbaseline、Basic、Bonusの時間を大きく。BasicとBonusに律速と手を短く1行 | 流れの動画（話さない） | 0:40 |
| 2 | MPI calls on 4 nodes | 回数の上位3つと、時間の上位3つ | 表 | 0:30 |
| 3 | Profiling the baseline | 道具ごとに分かったこと：固定が外れる、計算が不均一、速いrankが待つ | 表 | 0:50 |
| 4 | CPU and memory pinning | (1) ジョブスクリプトでの固定。片方だけでは効かない理由 | 4つの固定のしかたの各ジョブ（今の図） | 0:45 |
| 5 | Decomposition | (2) scotchで仕事がそろう、(3) ノードへの対応付け | hierarchicalとscotchの分割の絵（ParaView） | 0:40 |
| 6 | Basic results | 3.650 → 2.898 s/step。ばらつきもSD 4.1% → 0.07% | baselineとBasicの各ジョブ（今の図） | 0:35 |
| 7 | Criteria for keeping a change | 4つのテスト。改善がばらつきよりはっきり大きいことを求める | 採用と不採用の例の各ジョブ（今の図） | 0:50 |
| 8 | Bottleneck after Basic | メモリのカウンタが読めないので、配置を変えて確かめた。メモリ帯域が律速 | メモリチャネルの図（今の図） | 0:50 |
| 9 | What did not help | 典型的な4つの手と、効かなかった理由 | 表 | 0:40 |
| 10 | Bonus optimizations | (4) multiLevel、(5) 14のソース変更と見つけ方。DRAMからの読み込みが17%減る | Uの3成分を1回で読む例（今の図） | 1:00 |
| 11 | Bonus evidence | R3の4点 | 4行の表 | 0:40 |
| 12 | Results on 1, 2 and 4 nodes | 1/2/4ノードの時間と並列効率、1.55× | 3つの段の各ジョブ（今の図） | 0:40 |
| 13 | A gain we did not count | 固定反復でだけ効く−8.2%を数えなかったこと | なし | 0:30 |

原稿の合計は約9分10秒で、話す間を入れて約10分です。

### 1. OpenFOAM on ASPIRE-2A（0:40）

1枚目は、タイトルと要約を兼ねます（下の「1枚目の作り方」）。

スライドの文（右に縦に並べる。4 nodes, s/step）：

- Common baseline (organisers): 3.415 (hierarchical), 3.576 (scotch)
- Our baseline: 3.650 (case defaults, our own build of v2512)
- Basic: 2.898, −20.6%
  - lost CPU and memory binding, uneven work → (1) pinning, (2) scotch, (3) mapped onto the node
- Bonus: 2.360, −18.6% vs Basic
  - memory bandwidth → (4) multiLevel, (5) 14 source changes that move fewer bytes

図（左）：流れの動画（`flow/flow-streamlines.mp4`か`flow/flow-iterations.mp4`、ParaView）。繰り返し、音なしで流し、原稿では触れません。

原稿（約40秒）：Our HPC task: OpenFOAM on ASPIRE-2A. On four nodes, the organisers' common baseline takes 3.415 seconds per step with hierarchical and 3.576 with scotch, and our own baseline, the case defaults on our build, 3.650. Basic fixes two problems, lost CPU and memory binding and uneven work per rank: 2.898 seconds, 20.6 percent less. The Bonus then moves fewer bytes, because memory bandwidth limits a step, with the same computation: 2.360 seconds, 18.6 percent less than Basic. The rest of the talk is how we found each limit, and how we decided what to keep.

訳：HPCの課題、ASPIRE-2AでのOpenFOAMです。4ノードで、主催者の共通ベースラインはhierarchicalで1 step 3.415秒、scotchで3.576秒、私たちのbaseline（ケースの既定のまま、自分たちのビルド）は3.650秒です。Basicは、CPUとメモリの固定が外れていたこと、rankごとの仕事が不均一だったことの2つを直し、2.898秒、20.6%短くなりました。その後はメモリ帯域が律速なので、Bonusでは同じ計算のまま運ぶバイトを減らし、2.360秒、Basicより18.6%短くなりました。この後は、それぞれの律速をどう見つけ、何を残すかをどう決めたかを話します。

メモ：
- 共通ベースラインの出典は`tasks/5. Common Baselines.md`です（ASPIRE-2A、4ノード、サイトの`OpenFOAM/2512`モジュール、ケース既定、Allrun一式を1ジョブずつ）。聞かれたら：共通ベースラインに対して、Basicは−15.1%（hierarchical比）と−19.0%（scotch比）、Bonusは−30.9%と−34.0%です。
- 比べる基準は、同じビルド・スクリプト・測り方で取った私たちのbaselineです。主催者の値は、ビルド、MPI、配置が違うので参考にとどめます。私たちのbaseline（3.650）が共通ベースラインのhierarchical（3.415）より遅い理由はQ27です。
- baselineに対して、Bonusは−35.3%（1.55×）です。

1枚目の作り方（11/01のお遊びの案への意見）：
- 「時間と割合だけをバンと載せて、すぐ説明に入る」のは良いと思います。結果が先に目に入り、文字も少なくなります。
- ただ、BasicとBonusの下の1行（律速 → 手）は残すのを勧めます。道筋の地図になり、2枚目以降で「今どこの話か」が分かるからです。1行は小さくてかまいません。
- タイトルに時間の変遷を載せるのは、やりすぎではありません。ただ、次の枚に同じ数字が並ぶと重なるので、タイトルと要約を1枚にまとめるのが良いと思います（この案）。HPCを先に話すので、デッキの表紙の次がこの1枚になります。

### 2. MPI calls on 4 nodes（0:30）

スライドの文（表の上に「CrayPAT on our baseline: 4 nodes, 512 ranks, 40 steps」）：

| Most calls | Calls, all ranks | Most time | Time, all ranks (share of MPI) |
|---|---:|---|---:|
| MPI_Isend | 290 M | MPI_Waitall | 22,069 s (55%) |
| MPI_Irecv | 290 M | MPI_Allreduce | 14,140 s (35%) |
| MPI_Test | 289 M | MPI_Bcast | 1,289 s (3%) |

- The calls are the halo exchange with neighbouring subdomains (93% of all calls)
- The time is waiting for other ranks (90% of the MPI time); MPI is 46% of a rank's time

原稿（約30秒）：We began by profiling the baseline. With CrayPAT on four nodes, the most frequent MPI calls are Isend, Irecv and Test, about 290 million each over all ranks: the halo exchange with neighbouring subdomains. The time goes to Waitall and Allreduce, 90 percent of the MPI time, and both wait for other ranks. MPI is 46 percent of a rank's time. So why do the ranks wait?

訳：まずbaselineをプロファイルしました。4ノードのCrayPATでは、回数の多いMPI呼び出しはIsend、Irecv、Testで、全rankでそれぞれ約2.9億回です。隣のサブ領域との境界の値の交換です。一方、時間はWaitallとAllreduceがMPIの時間の90%を占め、どちらも他のrankを待つ呼び出しです。MPIはrankの時間の46%です。では、なぜrankは待つのか。

メモ：
- CrayPAT 38219766511（#62）、`data/baseline_profile_4node.csv`。表は512 rankの合計です（ISC26の課題の「total CPU time consumed」に合わせました）。rankあたりでは、Isend・Irecv 566,107回、Test 563,646回、Waitall 43.1 s、Allreduce 27.6 s、Bcast 2.5 s（MPIはrankあたり78.3 s）です。順位はどちらでも同じです。
- ISC26の課題（Task 3）：「Run any MPI profiler to profile the simulation on 4 nodes. What are the 3 most used MPI calls in terms of number of calls and in terms of total CPU time consumed?」
- 待ちであって転送ではない証拠：rankごとのMPI時間は35〜112秒で、セル数はほぼ完全に均等です。ネットワークを速くしても効かなかったことは9枚目で話します（Q2、Q29、Q31）。
- Basicの後（#53）も回数の上位3つは同じで、時間はAllreduce 48%、Waitall 38%に入れ替わります。MPIはstepの19%になります。

### 3. Profiling the baseline（0:50）

スライドの文（4ノード、512 rank）：

| Tool | What it showed |
|---|---|
| /proc of every rank during the solve | 0 of 512 ranks stay on their own core; 9% of a rank's memory is on its own NUMA domain |
| OpenFOAM profiling | Equal cell counts, but the slowest rank computes 1.46× as long as the median |
| CrayPAT | MPI time per rank from 35 to 112 s: fast ranks wait at each of about 1,600 global sums per step |
| AMD uProf | Most computation is sparse-matrix sweeps, with little arithmetic per byte |

- 表の下の1行：The launcher binds each rank, but the binding is removed during MPI_Init

原稿（約50秒）：We profiled the baseline with four tools. We had asked the launcher to bind each rank, so we checked the real state in /proc of every rank during the solve: none of the 512 ranks stayed on its own core, and only 9 percent of a rank's memory was on its own NUMA domain. The binding was removed inside MPI_Init. OpenFOAM's own profiling shows the effect: the cell counts are equal, but the slowest rank computes 1.46 times as long as the median. CrayPAT shows the cost: at each of about 1,600 global sums per step, the fast ranks wait for the slowest. And uProf shows where the computation goes: sparse-matrix sweeps, with little arithmetic per byte.

訳：baselineを4つの道具でプロファイルしました。起動時に各rankの固定を頼んでいたので、実際の状態を、解いている最中の全rankの/procで確かめました。512 rankのどれも自分のコアに留まっておらず、rankのメモリのうち自分のNUMA領域にあるのは9%だけでした。固定は、MPI_Initの中で外されていたのです。OpenFOAMのprofilingにその結果が出ています。セル数は等しいのに、最も遅いrankの計算は中央値の1.46倍です。CrayPATには、その代償が出ています。1 stepに約1,600回ある大域和のたびに、速いrankが最も遅いrankを待ちます。そしてuProfでは、計算の中心は疎行列の掃き出しで、1バイトあたりの演算がとても少ないことが分かります。

メモ：
- 出典：`/proc`とOpenFOAM profilingは38219862855、CrayPATは38219766511、uProfは38219770656（#62）。
- 9%は512 rankの中央値8.7%です（8領域に均等に散れば12.5%）。1.46はrankごとの計算時間（40 stepで54〜115 s）の最大/中央値で、セル数の差は最大でも平均の+0.002%です。
- 大域和の数：1 stepにUで15回×3成分、kとωで8回ずつ、pでGAMG 12サイクル（最粗段のPCGは35回）回すので、rankあたり1 stepに約14,000回の送信と約1,600回の大域和があります。
- uProf：Gauss-Seidelの平滑化、残差、行列とベクトルの積で計算の約4分の1です。どれも疎行列を1回なめる処理で、約0.1 flop/Bです（8枚目につながる）。
- 頼んだ配置（起動コマンドの`--cpu-bind depth`）と実際の配置（実行中の`/proc`）を分けて確かめたことが、この発見の要点です。旧課題の資料の「利得を探す前に、すでに壊れているものを確かめる」に当たります。
- 主催者のASPIRE-2Aのノートには固定の話がなく、主催者の参照runも固定していません。同じ機械を使うチームとの一番の差です（Q27）。

### 4. CPU and memory pinning（0:45）

スライドの文：

- (1) In the job script: numactl binds each rank's memory to its NUMA domain; one watcher per node pins each rank back to its core (taskset)
- During the solve: 512 of 512 ranks on their own core; 58% of a rank's memory is local (was 9%)
- Both halves are needed: Linux keeps each page where it was first written
- Case-default split, same period: 3.670 → 3.257 s/step (−11.2%, 3 v 3)

図：第6版のFigure 8（`deck/deck_plots.py`の`p10_pinning`、4ノード、scotchの分割、各ジョブ）を流用し、平均とSDを書き添えます。Both 2.917（SD 0.13%、3本）、CPU only 3.474（2.0%、3本）、Neither 3.395（0.78%、2本）、Memory only 4.380（1本）s/step。

原稿（約45秒）：The first fix puts the binding back, in the job script only. Each rank starts under numactl, so its memory is bound to its own NUMA domain, and one watcher per node pins each rank back to its core. Both halves are needed. Linux keeps each page where it was first written, so pinning only the CPU is no faster than doing nothing, and binding only the memory is much slower. With both, every rank stays on its core and 58 percent of its memory is local, instead of 9. In the same period, a step drops from 3.670 to 3.257 seconds, 11.2 percent.

訳：1つ目の対策は、ジョブスクリプトだけで固定を戻すことです。各rankをnumactlの下で起動してメモリを自分のNUMA領域に縛り、ノードごとに1つの見張りのプロセスが、各rankを自分のコアに固定し直します。両方が必要です。Linuxはページを最初に書かれた場所に置いたままにするので、CPUだけ固定しても何もしないのと同じ速さで、メモリだけ縛るとずっと遅くなります。両方そろうと、全rankが自分のコアに留まり、メモリの58%（以前は9%）が近くに来ます。同じ時期の比較で、1 stepは3.670秒から3.257秒に、11.2%短くなりました。

メモ：
- −11.2%は、hierarchicalのまま固定だけを足した同じ時期の比較です（10/02〜03、3本ずつ、範囲は重ならない、`data/start_unpinned.csv`と`data/decomposition_basic.csv`）。このときの固定は`LD_PRELOAD`で`MPI_Init`の直後に固定する方法で、Basicの`numactl`＋`taskset`と同じ速さです（2.919と2.917）。
- 図はscotchの分割での比較で、測った時期が違います（10/07）。CPUだけ戻すと、戻すまでの12〜16秒に確保したデータが遠くに残ります。Neitherはbaselineと同じ状態（起動時の固定が外れたまま）です。CPU onlyとNeitherは範囲が重なるので、「速くならない」と言います。
- `LD_PRELOAD`はBasicでは使えないので、ジョブスクリプトだけでできる形にしました（F1：job script、rank placement、affinity。Q17）。全ジョブのログで、各ノード128/128 rankが固定されています。
- 58%は、対応付けの前のBasicでノード0の128 rankを`/proc`で見た中央値です。100%にならないのは、共有ライブラリやMPIの共有バッファのように複数のrankが使う部分は1つの領域にしか置けないためと考えていますが、確かめていません。

### 5. Decomposition（0:40）

スライドの文：

- hierarchical cuts thin slabs: ranks near the car get more faces and more work
- (2) scotch cuts compact blocks and evens the work (slowest/median rank 1.16 → 1.06): 3.257 → 2.915 s/step (−10.5%, 3 v 3)
- (3) scotch mapped onto sockets and NUMA domains (scotchCoeffs): 2.918 → 2.898 s/step (−0.7%, 5 v 5)

図：hierarchicalとscotchの分割（車体表面をサブ領域ごとに塗った絵、ParaView）。第6版のFigure 9と同じ絵を流用します。

原稿（約40秒）：The second fix is the decomposition. The case default, hierarchical, cuts the mesh into thin slabs along the axes. Near the car the cells are small, so some ranks get many more faces and more work: the slowest computes 16 percent longer than the median. scotch cuts compact blocks: the difference falls to 6 percent, and a step drops from 3.257 to 2.915 seconds, 10.5 percent. Then we mapped the scotch decomposition onto the sockets and NUMA domains of each node, 0.7 percent more.

訳：2つ目の対策は分割です。ケースの既定のhierarchicalは、軸に沿ってメッシュを薄い板に切ります。車の近くはセルが小さいので、一部のrankは面も仕事もずっと多くなり、最も遅いrankの計算は中央値より16%長くなります。scotchはまとまった塊に切るので、その差は6%になり、1 stepは3.257秒から2.915秒に、10.5%短くなりました。さらに、scotchの分割を各ノードのソケットとNUMA領域に対応付けて、0.7%短くなりました。

メモ：
- (2)：サブ領域間の面は4.31 M → 2.93 M（−32%）、計算の最大/中央値は1.16 → 1.06です（どちらも固定あり、CrayPAT）。hierarchicalの偏りは、壁の面（車の表面）の数と相関しました（#38）。scotch対hierarchicalは1/2/4ノードで−1.3／−2.5／−10.5%です（交互に3本ずつ、`data/decomposition_basic.csv`）。ノード数が多いほど効く理由は確かめていません（Q30）。
- (3)：`scotchCoeffs`の`domains`、`domainWeights`、`strategy`で、ノード → ソケット → NUMA領域 → コアの木に合わせました。ノード、ソケット、NUMA領域をまたぐ面が23%、21%、10%減ります。対照（scotchの既定）2.918（SD 0.22%）、候補2.898（SD 0.07%）で、5本ずつ交互に流して全runが対照より速かったものです（7枚目の例）。1・2ノードではほぼ変わりません。
- 図のscotchは対応付けの前のものです。ISC26の課題（Task 5）の「分割方法を変えて、性能への効果を示す」にも当たります。

### 6. Basic results（0:35）

スライドの文：

- 3.650 → 2.898 s/step (−20.6%)
- Spread between identical jobs: SD 4.1% → 0.07%
- Slowest/median rank 1.46 → 1.06; MPI 46% → 19% of the time

図：第6版のFigure 11（`deck/deck_plots.py`の`p12_basic`、4ノード、baselineの3本とBasicの5本）を流用し、平均とSDを書き添えます。

原稿（約35秒）：Together, Basic takes 2.898 seconds per step, 20.6 percent less than our baseline. It also made the runs steady. The baseline's jobs varied with a standard deviation of 4.1 percent, partly because each run put its slow, unpinned ranks in different places; Basic's five jobs vary by 0.07 percent. From here on, differences well below 1 percent can be measured. The slowest rank now computes only 6 percent longer than the median, and MPI falls from 46 to 19 percent of the time.

訳：合わせて、Basicは1 step 2.898秒で、私たちのbaselineより20.6%短くなりました。runも安定しました。baselineのジョブは標準偏差4.1%でばらつきました。固定の外れた遅いrankが、runごとに違う場所に出たことも原因です。Basicの5本のばらつきは0.07%です。ここからは、1%よりずっと小さい差も測れます。最も遅いrankの計算は中央値より6%長いだけになり、MPIは時間の46%から19%に減りました。

メモ：
- ばらつきの話はこの枚で終えます。以降の図には、平均とSDを書くだけにします。
- 遅いrankがrunごとに違う場所に出るのは、固定が外れていたときの症状です（#36）。ただし固定だけを戻したhierarchical（10/02〜03）でもSDは1.1%あり、scotchで仕事をそろえて0.3%、対応付けたBasicで0.07%になりました。だから「固定が外れていたことも原因」と言い、固定だけのおかげとは言いません。
- 92本・29設定の繰り返し（9/21〜10/05、`data/bench_runs_sep21_oct05.csv`、#47）では、多くが自分の設定の中央値から±0.4%以内でした。84%、91%遅い単発のrunは9月です（補足）。
- 46% → 19%はプロファイルrun（CrayPAT）の値で、Basicのプロファイルは対応付けの前のものです（対応付けで4ノードのstepは0.7%しか変わりません）。
- プロファイラは1 stepを−1%〜+6%変えるので、時間はプロファイラのない計測runだけで測ります（Q28）。
- 出典：baselineは#62（10/12）、Basicは10/15〜16の5本（#63）。

### 7. Criteria for keeping a change（0:50）

スライドの文（番号付き）：

1. Candidate and control alternate in the same period, 3 or more jobs each on 4 nodes
2. Keep it only if every candidate job is faster than every control job, so the gain must stand clear of the spread. By chance this happens 1 time in 20 at 3 v 3
3. Same computation: Basic changes no source; the Bonus keeps Cd within ±0.5% at 1, 2 and 4 nodes
4. A profile explains the gain

図（右）：第6版のFigure 6（`deck/deck_plots.py`の`p07_rule`）を流用し、番号と副題を外して、平均とSDを書き添えます。

- Kept: scotch mapped onto the node, 2.918 → 2.898 s/step, −0.7% (5 v 5, no overlap)
- Not kept: AOCC instead of GCC, 2.910 and 2.911 s/step (3 v 3, overlap)

原稿（約50秒）：This is how we decide what to keep. Candidate and control run in turns in the same period, at least three jobs each on four nodes. We keep a change only if every job with it is faster than every job without it; a change with no effect would pass by chance once in twenty. The computation must stay the same, and a profile must explain the gain. With steady runs, identical jobs differ by about 0.2 percent, so a gain of 1 percent passes almost every time. A smaller gain passes only if it still stands clear of the spread: mapping onto the node gained 0.7 percent, and all five jobs beat all five controls. AOCC overlapped its control, so we did not keep it.

訳：何を残すかは、こう決めます。候補と対照を同じ時期に交互に、4ノードで3本以上ずつ流します。変更ありの全ジョブが、変更なしの全ジョブより速いときだけ残します。効果のない変更が偶然これを通るのは20回に1回です。計算が同じであること、そしてプロファイルで改善の理由を説明できることも求めます。runが安定した今、同じ設定のジョブの差は約0.2%なので、1%の改善ならほぼ必ず通ります。それより小さい改善は、ばらつきからはっきり離れているときだけ通ります。ノードへの対応付けは0.7%でしたが、5本すべてが対照の5本より速くなりました。AOCCは対照と重なったので、残しませんでした。

メモ：
- テスト2の確率：効果がなければ、候補と対照の並び方はどれも同じ確からしさなので、全候補が全対照より速い確率は1/C(n+m, n)です。3対3で1/20、4対4で1/70、5対5で1/252。
- 「どの大きさなら採用してよいか」の論理（Q36）：決まった最小値はなく、「全ジョブが対照より速い」こと自体が、改善がばらつきより大きいことを求めます。固定したscotchの29本（4ノード、10月初め）のSDは0.19%でした。ばらつきを正規分布として数えると（11/01の模擬計算、各20万回）、3本ずつの判定が通る確率は、効果がなければ5%（1/20）、改善がSDの2倍（約0.4%）で62%、3倍（約0.6%）で89%、4倍で98%、5倍（約1%）で99.8%です。5本ずつにすると偶然の確率は0.4%（1/252）に下がり、同じ改善でも通りにくくなります（3倍で77%）。だから1%の改善はほぼ必ず通り、それより小さい改善は、ばらつきがとくに小さいときか、本数を増やして確かめたときだけ残ります。
- 経緯：最初（10月初めまで）は「1%以上」も条件にしていました。ばらつきを測る前で、9月には84%、91%遅い単発のjobもあったからです。ばらつきが分かって外しました（REPORT §4）。採用した13段のうち11段は1%以上で、1%未満は対応付け（−0.7%、5対5）と0012（−0.3%、3対3。その日の対照と候補のSDは0.07%と0.14%）の2つです。mallocの閾値（−0.4%、3本）はばらつきと区別できず、採用していません。
- 図のデータ：対応付けは#63（10/15、5本ずつ交互）、AOCCは`data/compiler_options.csv`（#36 D、10/03、3本ずつ）です。
- 採用した変更は、どれも4ノードでテスト1と2を満たします（`data/changes_ab.csv`、`data/decomposition_basic.csv`）。0013〜0015と0016は対照の数日後に測りましたが、後の10個は最終計測でまとめて、0001〜0004の版と交互に流しました（3対3、範囲は重ならない）。
- （聞かれたら）t検定でない理由：本数が3〜5本と少なく、ジョブ間の差の分布も分かりません。順位だけを見る判定なら分布を仮定せずにすみ、偶然の確率も数えられます。
- 固定反復のときだけ効く変更（#68）は、テストを通っても数えません（13枚目）。

### 8. Bottleneck after Basic（0:50）

スライドの文：

- Users cannot read the memory-controller counters (perf_event_paranoid=2), so we changed only where the ranks run
- Half the cores, all 16 memory channels: ×0.99
- The same ranks on half the channels: ×2.20; STREAM triad on those nodes: 279 → 125 GB/s
- A step is limited by memory bandwidth: the sparse-matrix sweeps do about 0.1 flop per byte

図：第6版の13枚目の、16本のメモリチャネルを四角で描き、使う本数を塗った図（PowerPointの図形）を流用します。カードの背景は外します。

原稿（約50秒）：After Basic, what limits a step? On ASPIRE-2A, users cannot read the memory controller counters, so we could not measure the DRAM traffic directly. Instead, we changed only where the ranks run. With half the cores, still using all sixteen memory channels, a step takes the same time. With the same ranks and the same split packed onto half the channels, it takes 2.2 times as long, and STREAM on those nodes drops by the same factor. So memory bandwidth sets the speed: the sweeps do about 0.1 flop per byte. For the traffic of each rank, we use core counters instead: refills of the L1 cache from DRAM.

訳：Basicの後、何がstepの速さを決めているのか。ASPIRE-2Aでは利用者がメモリコントローラのカウンタを読めないので、DRAMの転送量を直接は測れません。そこで、rankの置き場所だけを変えました。16本のメモリチャネルを全部使ったままコアを半分にしても、1 stepの時間は同じです。同じrank、同じ分割のまま半分のチャネルに詰めると2.2倍かかり、そのノードで測ったSTREAMも同じだけ落ちます。だから速さを決めているのはメモリ帯域で、掃き出しは1バイトあたり約0.1 flopしか計算しません。rankごとの転送量は、代わりにコアのカウンタ（DRAMからL1への読み込み）で見ています。

メモ：
- #61（10/10、4ノード、150 step、全rankをCPUとそのNUMA領域に固定）。Basic（対応付けの前）は、128 rank/ノード 2.920（1本）、64 rank（16チャネル）2.887（2本）、64 rank（8チャネル）6.347（2本）s/stepです（`data/memory_placement.csv`）。0001〜0004のBonusでは×1.02と×2.11でした。triadは同じノードで274、279、125 GB/s/ノードです（`data/triad_placement.csv`）。
- 限界：チャネルを半分にした配置はL3も半分にするので、DRAMの帯域とL3の容量の寄与は分けられません（どちらもメモリ側の資源です）。コアを半分にした比較は分割が512から256に変わりますが、帯域に比例しない部分は1 stepあたり約0.1 sしかありません（Q23）。
- 約0.1 flop/B：内部の面1つに約4 flopで、係数2つ（16 B）、番地（4 B）、セルの値を合わせて30〜40 Bを読みます。ノードの倍精度ピーク約4.1 TFLOP/sをSTREAMの約290 GB/sで割った約14 flop/Bの、約1/100です（Q35）。ノードは128コア、8 NUMA領域、16チャネルです。
- 読めないものと、代わりに使った方法（チームが力を注いだところ。この枚と3、9、10枚目で言う）：
  - rankの実際の置き場所：起動時の指定ではなく、実行中の`/proc`（3枚目）
  - メモリ帯域：配置を変える実験と、同じノードでのSTREAM triad（この枚）
  - rankごとのDRAMの転送量：コアのカウンタ（L1のDRAMからのrefill、uProf）（10枚目、Q21、Q25）
  - ネットワーク：NICやスイッチのカウンタの代わりに、毎回のrunの後のIMBと、ネットワーク側だけを変える比較（9枚目、Q31）
- IBSも読めません（`perf_event_paranoid=2`）。

### 9. What did not help（0:40）

スライドの文（表）：

| Idea | Time per step vs control (4 nodes) | Why it did not help |
|---|---|---|
| Compiler flags, AOCC, LTO, PGO | within ±0.13% | The loops wait on memory, not on instructions |
| Faster network: UCX over RC (+55% bandwidth), OFI | −0.2% to +0.8% | MPI time is waiting for the slowest rank, not transfer |
| 92% fewer faces between nodes (rank reordering) | +0.1% | Fewer bytes between nodes do not shorten the wait |
| Balancing faces: weighted cells, METIS with two constraints | +1.5% to +6.1% | Uneven cell counts, or 18% more faces between subdomains |

原稿（約40秒）：Typical tuning did not help, and each failure points to the limits we found. Compiler flags, another compiler, link-time optimisation and PGO changed less than 0.13 percent: the loops wait on memory, not on instructions. A faster MPI transport, with 55 percent more bandwidth, changed nothing: the MPI time is waiting for the slowest rank, not transfer. For the same reason, cutting the faces between nodes by 92 percent changed nothing. And balancing faces with weights or two-constraint METIS made the cell counts uneven, or added faces, and was slower.

訳：典型的なチューニングは効かず、どの失敗も、見つけた律速を指しています。コンパイラのフラグ、別のコンパイラ、リンク時最適化、PGOは0.13%も変えませんでした。ループが待っているのは命令ではなくメモリだからです。帯域が55%高いMPIの転送方式にしても、何も変わりませんでした。MPIの時間は転送ではなく、最も遅いrankを待つ時間だからです。同じ理由で、ノード間の面を92%減らしても何も変わりませんでした。そして、重みや2つの制約のMETISで面をそろえようとすると、セル数が不均一になるか面が増え、遅くなりました。

メモ：
- 主催者は、理由と検証のある「効かなかった実験」も点になると答えています（`tasks/README.md` R3、Slack）。高度な試み（境界交換との重ね合わせ0018、GAMGの最粗段を少ないrankで、SMT、mallocの閾値、0017など）は補足の一覧です。
- コンパイラ：`-march=znver3` +0.03%、AOCC 5.0／AOCL 5.1 +0.03%、`-O2` +0.02%、LTO +0.13%（どれも対照と範囲が重なる、3本ずつ、`data/compiler_options.csv`）。GCCのPGOも同じ範囲です（#59）。
- ネットワーク：UCXのRCはIMBの帯域を55%上げましたが、1 stepは−0.01%（Basic）、−0.16%（0001〜0004のBonus）でした（4対4）。OFI（`FI_OFI_RXM_USE_SRX=0`）は+0.77%です（3対3、Q16）。
- rankの並べ替え（`MPICH_RANK_REORDER_METHOD=3`）は、サブ領域を変えずにノード間の面を92%減らしましたが+0.1%でした（Q29）。1つのrankの待ちは、隣の数ではなく自分の計算で決まります（R² 0.77、補足）。
- 重み付け：×2で+2.2%、×12で+6.1%（セル数の偏りが1.073に増えた）。METISの2つの制約は面の均衡を良くしましたが、サブ領域間の面が18%増えて+1.46%でした（Q4、Q5）。

### 10. Bonus optimizations（1:00）

スライドの文：

- (4) multiLevel decomposition (nodes, sockets, NUMA domains, cores; scotch at each level): −1.5%
- (5) 14 source changes that move fewer bytes: the first four −9.5%, ten more −9.3%
  - no copies or zero fills
  - fewer passes over the same arrays
  - no values that nobody reads
  - fewer global sums
- First four changes, 1 node: 4% fewer instructions, 17% fewer refills from DRAM

図（右）：例として、速度の3成分が同じ行列を使うので、3回ではなく1回読む図（第6版のFigure 13、`fig25_u_in_one_pass`と同じ内容）を流用します。

原稿（約1分）：The Bonus moves fewer bytes. Four: a multiLevel decomposition that follows the machine, nodes, then sockets, NUMA domains and cores, with scotch at each level: 1.5 percent. Five: fourteen source changes. For example, the three velocity components use the same matrix, but the code read it three times; now it reads it once and updates all three. The first four target the hottest loops: Gauss–Seidel sweeps, residuals and face loops. We found the other ten by profiling the Bonus again; its call stacks pointed to the turbulence model, the sweeps and the global sums of the coarsest CG. Each round gained about 9 percent. For the first four, the counters show 4 percent fewer instructions but 17 percent fewer refills from DRAM: the gain is in the bytes.

訳：Bonusでは運ぶバイトを減らします。4つ目は、機械の形に沿ったmultiLevelの分割です。ノード、ソケット、NUMA領域、コアの順に、各段をscotchで分けます。1.5%です。5つ目は14のソース変更です。例えば、速度の3成分は同じ行列を使うのに、元のコードは行列を3回読んでいました。1回読んで3成分を更新するようにしました。最初の4つは、最も重いループ（Gauss-Seidelの掃き出し、残差、面のループ）を狙ったものです。残りの10個は、Bonusをもう一度プロファイルして見つけました。call stackが、乱流モデル、掃き出し、最粗段のCGの大域和を指していました。どちらの回も約9%です。最初の4つでは、命令は4%しか減らないのに、DRAMからの読み込みは17%減りました。効いているのはバイトの量です。

メモ：
- Bonusになる理由：hierarchicalとscotch以外の分割方法と、ソースの変更はBonusです（F2）。
- (4) multiLevel (4 2 4 16)：対照はscotchの既定で、2.918 → 2.873 s/step（4対4、#42）。サブ領域間の面は2.81 M（scotchの既定は2.93 M）で、ノード間の面は38%少なくなります。
- (5) 最初の4つは1つずつ直前の版と比べ、−3.4%（0001）、−2.3%（0002）、−1.3%（0003）、−2.8%（0004）、合わせて2.873 → 2.599 s/step（−9.5%）。後の10個は最終計測でまとめて0001〜0004の版と比べ、2.603 → 2.360 s/step（−9.3%、1/2/4ノードで交互に3本ずつ、範囲は重ならない）。
- 14の変更の種類と番号（スライドには載せません）：no copies or zero fills（0001、0011、0014）、fewer passes（0002、0004、0006、0009、0013、0015、0016）、no unused values（0003、0008、0010）、fewer global sums（0012）。全文は提出物の`bonus/README.md`とpatchです（補足）。0005（#68）と0007はBonusに入っていません。
- 後の10個の見つけ方：最初の4つの版（fa4f5b0）のCrayPATのstack sample（#53）を、関数別・呼び出し経路別に集計し直し（`research/profile-reaggregation-fa4f5b0/`）、v2512のソースを読んで候補を順位付けしました。kOmegaSSTが標本の27%（場の式、勾配、kとωの解き）、最粗段のPCGはほとんどが大域和でした（#69、実装はCodex）。その木の図は補足に置きます。
- Uの例は0002です（1ノード−6.4%、4ノード−2.3%）。
- カウンタ（#55、1ノード、uProf、計算部分だけ、各2本）：命令−4.1%、cycles −10.8%、L1のDRAMからのrefill −17.2%。数えているのはL1のdemand refillで、DRAMの転送バイト数ではありません（Q25）。後の10個はカウンタで測っていません。

### 11. Bonus evidence（0:40）

スライドの文（4行の表）：

| | |
|---|---|
| What changed | 14 patches and the multiLevel dictionaries, submitted as text |
| Why it is the same computation | The iterations, convergence tests and discretisation stay; only copies, extra passes, unread values and extra global sums go |
| Evidence | Cd within 0.0005% of the unmodified run at 1, 2 and 4 nodes (F3 allows ±0.5%); the first four changes are bit-identical, log lines too |
| Speedup vs our Basic | −23.4% / −21.7% / −18.6% on 1 / 2 / 4 nodes, on the same machine |

原稿（約40秒）：For the Bonus, four points. What changed: fourteen patches and the multiLevel dictionaries, submitted as text. Why it is the same computation: the iterations, the convergence tests and the discretisation stay; only copies, extra passes, unread values and extra global sums go. The evidence: Cd stays within 0.0005 percent of the unmodified run at one, two and four nodes, a thousand times inside the allowed 0.5 percent, and the first four changes are bit-identical, down to every line of the solver log. And against our own Basic, the Bonus is 23.4, 21.7 and 18.6 percent faster on one, two and four nodes.

訳：Bonusについて4点です。何を変えたか：14のパッチとmultiLevelの設定で、テキストで提出しています。なぜ同じ計算か：反復回数、収束判定、離散化はそのままで、取り除いたのはコピー、余分な読み直し、誰も読まない値、余分な大域和だけです。証拠：Cdは1、2、4ノードで変更前のrunから0.0005%以内で、許される0.5%の1000分の1です。最初の4つの変更は、ソルバのログの全行までビット一致です。そして自分たちのBasicに対して、1、2、4ノードで23.4%、21.7%、18.6%速くなりました。

メモ：
- R3の4点（What changed、Why it is the same math、Evidence、Speedup against your own Basic result）に1行ずつ答える枚です。Cdの収束のグラフは補足です。
- 証拠の2段（REPORT §8.3、`bonus/README.md`）：(a) 0001〜0004の版は、変更前のrun（pre-change baseline：同じmultiLevelの分割とrank数で、ソースの変更を外したもの）と1/2/4ノードで`coefficient.dat`がバイト一致し、`simpleFoam.log`の全stepの残差（16桁）、反復回数、連続の式の誤差、kとωのboundingが全行一致しました（371、771、1,475行）。(b) 14すべてのCdは、変更前のrunに対して+1.2 × 10⁻¹²（相対）、−0.00002%、−0.00041%（1/2/4ノード）です。
- 丸めが変わり得るのは0011、0012、0016の3つ（足す順序が変わる）なので、「same arithmetic」ではなく「same computation」と言います。反復回数が固定（`tolerance 0`、`relTol 0`）なので、ログの残差まで比べました（Q7、Q33）。
- 速度向上：Basic 13.36／6.372／2.898、Bonus 10.23／4.992／2.360 s/step。Bonusは10/26の最終計測です（#69）。提出スクリプトでの再実行（10/26）も、記録の平均から−0.31〜+0.22%で、`coefficient.dat`はバイト一致しました（Q18）。

### 12. Results on 1, 2 and 4 nodes（0:40）

スライドの文：

- 図の下の1行：4 nodes: 3.650 → 2.360 s/step, 1.55× faster with the same computation

図：第6版のFigure 16（`deck/deck_plots.py`の`p17_scaling`、baseline、Basic、Bonusの各ジョブ、対数軸、1ノードからの理想の線）を流用します。各点の横に平均（4桁）を書き、凡例に並列効率（1.00、1.15、1.08）を書きます。

| s/step（SD） | 1 node | 2 nodes | 4 nodes | Efficiency, 1 → 4 nodes |
|---|---:|---:|---:|---:|
| Our baseline | 14.57 (2.0%) | 7.427 (2.0%) | 3.650 (4.1%) | 1.00 |
| Basic | 13.36 (0.02%) | 6.372 (0.08%) | 2.898 (0.07%) | 1.15 |
| Bonus | 10.23 (0.32%) | 4.992 (0.25%) | 2.360 (0.16%) | 1.08 |

（表は図に書く値の一覧です。図だけで読みにくければ、表を図の代わりにします。）

原稿（約40秒）：On one, two and four nodes, Basic and the Bonus are faster than our baseline at every node count. Parallel efficiency from one to four nodes rises from 1.00 to 1.15 with Basic: on four nodes, each rank's arrays shrink to about 1 megabyte and fit in the L3 cache. The Bonus saves most on one node, where each rank holds four times more data, so its efficiency is 1.08. On four nodes, a step went from 3.650 to 2.360 seconds: 1.55 times faster, with the same computation. What remains is memory traffic, and an imbalance between ranks that follows their reads from DRAM.

訳：1、2、4ノードでは、BasicとBonusは、どのノード数でもbaselineより速くなりました。1ノードから4ノードへの並列効率は、Basicで1.00から1.15に上がりました。4ノードでは各rankの配列が約1 MBに縮み、L3キャッシュに収まるからです。Bonusは、各rankのデータが4倍ある1ノードで最もよく効くので、効率は1.08です。4ノードでは1 stepが3.650秒から2.360秒になり、同じ計算のまま1.55倍速くなりました。残っているのはメモリの読み書きの量と、rank間の差です。その差は、各rankがDRAMから読む量に沿っています。

メモ：
- 本数（1/2/4ノード）：baseline 6/3/3（#62）、Basic 3/3/5（#63）、Bonus 3/3/3（#69）。
- 効率が1を超える理由は、カウンタで確かめました（#66、uProf、1/2/4ノード）。1セル・1 stepあたりのDRAMからのL1 refillは、4ノードで1ノードの0.70倍です。セルの配列がrankあたり4 MB（1ノード）から1 MB（4ノード）になり、コアあたり4 MBのL3に収まります（Q6）。
- Bonusの効率が下がるのは、1ノードの時間をより多く減らしたからで、4ノードが遅くなったからではありません。
- 残っていること：U・k・ωの組み立てを項をまたいで融合する（運ぶバイトをさらに減らす）、部分領域ごとのセルの並べ替え（rank間の差はセル数ではなくDRAMからの読み込み量に沿う、r = +0.69、#66）。数%の見込みです（Q20、Q34）。

### 13. A gain we did not count（0:30）

スライドの文：

- With fixed iterations, every sweep still computes a residual and a global sum for a convergence test that can never stop the solve
- Computing it once, after the last sweep: 2.360 → 2.166 s/step (−8.2%), coefficient.dat byte-identical
- Not counted: it helps only the benchmark's fixed-iteration setting

原稿（約30秒）：One more thing. With the benchmark's fixed iterations, every sweep still computes a residual and a global sum for a convergence test that can never stop the solve. Computing it once, after the last sweep, takes the Bonus from 2.360 to 2.166 seconds per step, with a byte-identical Cd. We did not count it, because it helps only the fixed-iteration setting of the benchmark. Thank you.

訳：最後にもう1つ。ベンチマークの反復回数は固定なので、収束判定で解を止めることはないのに、掃き出しのたびに残差と大域和を計算しています。最後の掃き出しの後に1回だけ計算すると、Bonusは1 step 2.360秒から2.166秒になり、Cdはバイト一致しました。ただ、ベンチマークの固定反復の設定でしか効かないので、数えていません。ありがとうございました。

メモ：
- #68。最終Bonusの上の0019（branch `experiment/issue68-on-bonus-final`）：4ノード3本 2.173／2.163／2.163、平均2.166 s/step（SD 0.26%）。対照は新たに流さず、最終Bonusの最終計測の値（2.360）と比べたので、交互の比較ではありません。`coefficient.dat`は3本とも最終Bonusとバイト一致です。
- 数えない理由：ケースのもう1つの設定`fvSolution.fixedTol`（普通の運用に近い設定）では元のコードが走ります。ルールの「less work per step」の禁止に触れると読まれ得ます。Bonusの14の変更は、どの収束設定でも効き、収束判定を1つも省きません。
- この枚の価値は速さではなく、「計測の取り決めにだけ効く高速化は数えない」と自分で線を引けることです。時間がなければ飛ばします。

## 入れなかったもの

- roofline：HPCでは使っていないので、本編にも補足にも置きません（質疑ではQ35で答えます）。
- 流れの1枚（第7版の最初の案の3枚目）：1枚目に動画を置くだけにしました。
- ばらつきだけの1枚：時間の図にSDを書き、6枚目で話し終えます。92本の詳細は補足です。
- ASPIRE-2Aの構成とbaselineの設定の枚：口頭で触れ、補足に置きます。
- 4ノードで段ごとの時間を並べた棒：1枚目と各枚の数字で足ります。

## Qwenに時間を回すとき（削る順）

1. 13枚目（おまけ）を飛ばし、12枚目で「Thank you」と言う（−30秒）。
2. 9枚目（効かなかったこと）を補足へ移し、理由は8枚目で一言だけ言う（−40秒）。
3. 6枚目（Basicの結果）を5枚目の最下行（3.650 → 2.898、SD 4.1% → 0.07%）にまとめる（−25秒）。

2枚目（MPI）、7枚目（採用の基準）、8枚目（読めない量の測り方）は削りません。

## まだ決めていないこと

- 1枚目の形：時間と割合だけにするか、BasicとBonusの下の1行（律速 → 手）を残すか（この案は残す）。
- 9枚目（効かなかったこと）の位置：Bonusの前（この案。律速の説明を受けて「だから典型的な手は効かない」と言える）か、最後か。
- call stackの図を作るか（補足）。

## 第6版の本編との対応

| 第6版の本編 | 第7版 |
|---|---|
| 1 Title、2 OpenFOAM TASK OVERVIEW | 1（タイトルと要約を1枚に。流れの動画も1枚目） |
| 3 ASPIRE-2A、4 BASELINE SETTINGS | 補足（口頭で触れる） |
| 5 BASELINE RESULTS | 1（3.650）、6（ばらつき）、12（1/2/4ノード） |
| 6 HOW WE MEASURE AND PROFILE | 3（道具）、6（計測runにプロファイラを付けない） |
| 7 HOW WE DECIDE WHAT TO KEEP | 7（Basicの後に移した） |
| 8 MPI PROFILE ON 4 NODES | 2（値を512 rankの合計にした） |
| 9 BASELINE ANALYSIS | 3 |
| 10 BASIC OPTIMIZATION (1/2) | 4 |
| 11 BASIC OPTIMIZATION (2/2) | 5（1/2/4ノードの分割の比較は補足） |
| 12 BASIC RESULTS | 6 |
| 13 MEMORY BANDWIDTH SETS THE SPEED | 8（読めないカウンタの代わりの方法を前に出した） |
| 14 BONUS OPTIMIZATION | 10 |
| 15 BONUS RESULTS | 11（R3の4点）、12（1/2/4ノード） |
| 16 BONUS ANALYSIS | 10の最下行（カウンタ）。細部は補足 |
| 17 SCALING ANALYSIS | 12 |
| 18 WHAT DID NOT HELP, AND WHY | 9（典型的な4つに絞った。ほかは補足の一覧） |
| 19 CONCLUSION | 1と12。残っている律速は12の原稿 |
| 20 EXTRA: A GAIN WE DID NOT COUNT | 13 |

## 補足（質疑用、15枚ほどに絞る）

補足も本編と同じ決まり（短い見出し、注記なし、1枚1つのこと）で作り直します。第6版の24枚から、質疑で出しそうなものだけを残します（括弧は第6版の改訂版pptxでの番号）。

| まとまり | 残す補足 |
|---|---|
| 環境と測り方 | Why ASPIRE-2A（本編3から。Q1の答え）、Build, MPI and run settings（本編4、27、31をまとめる）、Run-to-run variation over 92 runs（25）、The organisers' reference（41）、Reproducing our results（44） |
| Basic | Is the network the bottleneck?（30）、hierarchical and scotch on 1, 2 and 4 nodes（本編11の図） |
| Bonus | The placement experiment in full（33）、Where a Bonus step goes: call stacks（新規、下）、The fourteen source changes（35、36）、Effect of each Bonus change（39）、Hardware counters（本編16）、Drag coefficient over the iterations（新規、下）と照合の値（43） |
| 結果 | Why the efficiency exceeds 1（42）、Not adopted: the full list（45、46をまとめる） |

外すもの：Optimization strategy（23）、Bottlenecks we measured（24）、Experiment automation（26）、Where a step goes after Basic（28）、The path on 4 nodes（29）、The three splits（32）、HPC roofline（34）、Source changes in detail（37、38）、Profiles before and after（40）。中身は第6版のslides.md（git `a1f18a3`）と想定問答に残っています。Qwenと共通の再現性スライドは、そのまま残します。

新しく作る補足：

- Drag coefficient over the iterations：150反復のCdを反復ごとに描きます（4ノード）。Basic（Boxの`openfoam/results/4node/coefficient.dat`）、Bonus（`openfoam/bonus/results/4node/`）、ソースを変える前のrun（`openfoam/bonus/f3-baseline/4node/`）、主催者のhierarchicalとscotch（リポジトリの`tasks/4.3-aspire2a-logs/*-4node/coefficient.dat`）。Bonusと変更前のrunは線が重なり、分割が違うrunどうしは150反復で数%違う（Q12、Q13）ことが1枚で見えます。ISC26の課題（Task 4）の「ログから描くCdの収束グラフ」にも当たります。
- Where a Bonus step goes (call stacks)：最初の4つの版（fa4f5b0、4ノード、512 rankのうち48 rank）のCrayPATのstack sample 2,396本の集計（`research/profile-reaggregation-fa4f5b0/summary.md`）から、段階 → 関数の2〜3段の木（VTuneのような横長の帯の図）を描きます。段階の割合は、pの解き31.8%、kOmegaSSTのcorrect 26.9%、Uの解き20.5%、Uの組み立て11.8%、pの組み立て6.6%です。後の10個を見つけた根拠の図です。stack sampleはMPIの割合を約1.8倍に多く見せます（#53）。生のsample（Actions 37529785072の`profile-raw.tar.zst`、成果物の保管庫）を使えば、全部のstackのflame graphにもできます。
- 最終Bonus（14の変更）のcall stackは取っていないので、図は最初の4つの版のものだと見出しに書きます。

---

## 想定問答

英語の回答は、質疑で言う形の下書きです。

**Q1. Why ASPIRE-2A?**
- Last year we competed on Gadi, so this year we wanted to learn the other contest machine.
- Storage. OpenFOAM works with very many files: one unpacked OpenFOAM tree is about 36,000 files, and every decomposed 65M case adds thousands of `processor*` files. Our Gadi project has 1 TiB and about 212,000 files on `/scratch`; in August, three runs setting up at the same time already hit that file limit. On ASPIRE-2A we have 100 TB and 200 million files, so we could keep the builds, the decomposed cases and the raw records of every run.
- （メモ）Gadiの利用停止のことは自分からは言いません。「ノードが空いていた」は言いません（今回、4ノードは4時間以上、qdevの1ノードは3時間以上待った記録があります）。数字の出典は`platforms/gadi/README.md`（inode上限212,100、2026-08-17の3件同時の`Disk quota exceeded`）と、ASPIRE-2Aの`lfs quota`（100 TB、2億inode、2026-10-07）です。

**Q2. MPI waiting is large. Why didn't MPI tuning help?**
- Most of the MPI time is waiting: ranks that finish early wait at the next exchange or global sum. Per-rank MPI time ranges from 20 to 37 s. Library or switch tuning cannot remove that wait; only less work or better balance can. The OpenFOAM communication switches we tried gave no gain. Two later checks agree: UCX over RC raised the IMB bandwidth between nodes by 55% but changed a step by −0.01% (Basic) and −0.16% (the Bonus of the first four changes), and moving the GAMG coarsest level, which issues 81% of the `MPI_Allreduce` calls, from 512 ranks to 32 changed it by −0.25%.

**Q3. Why did you first reject scotch and then adopt it?**
- One run on 2026-09-27 took 5.03 s/step, an outlier from a slow period. When we alternated three runs of each in the same period, scotch was 10.5% faster. Since then we never decide from a single run.

**Q4. Is equal cell count enough?**
- It mattered most. When we weighted cells by their face and point work, the cell counts became uneven and it got slower (+2.2%, +6.1%). A METIS two-constraint split balanced faces better but added 18% processor faces (+1.46%). The remaining imbalance (max/median 1.07) is still open.

**Q5. Why did the weighting make it worse?**
- Static weights moved cells away from an even split: the cell-count imbalance grew to 1.073 with weight ×2. With ×12, the top-level split broke down and the faces between nodes grew five times.

**Q6. Why are the effects different on 1, 2 and 4 nodes?**
- On 1 node each rank holds four times more data than on 4 nodes, so more of it comes from DRAM. Removing array passes therefore saves more on 1 node (reading the U matrix once instead of three times: −6.4% against −2.3%; the ten later changes together: −12.2% against −9.3%). On 1 node we measured it for the first four changes: L1 refills from DRAM fall 17% while instructions fall 4%. On 4 nodes we tested the same idea by giving each core less memory: with 64 ranks per node the first four changes gain 7.9% on all memory channels and 11.4% on half of them. This is also why the Bonus scales less well than Basic (1.08 against 1.15): it saves most on 1 node. The same reasoning explains the super-linear scaling, and there we measured counters at 1, 2 and 4 nodes: per cell and step, the L1 refills from DRAM fall by 30% from 1 to 4 nodes, almost all in the sparse-matrix kernels, whose scattered cell arrays shrink to 1 MB per rank and fit in L3.

**Q7. What is proven and what is not?**
- Proven: the timings (alternated controls, 3 or more runs on 4 nodes), the same computation (the first four changes: bit-identical `coefficient.dat` and identical solver logs, every residual to 16 digits; all fourteen: Cd within 0.0005% at 1, 2 and 4 nodes, F3), and the pinning problem (seen in `/proc` during the solve).
- Shown by experiment on 4 nodes: the step time follows the memory bandwidth, not the number of cores (half the cores: −1% to +2%; half the memory channels: 2.1–2.2× slower, as the bandwidth drops 2.22×), and the first four changes gain more when each core has less memory.
- Measured with hardware counters (1 node, the first four changes): L1 refills from DRAM fall by 17% with 4% fewer instructions.
- Not proven: the DRAM traffic in bytes and the share of the peak bandwidth (we cannot read the memory-controller counters), how much of the memory effect is DRAM bandwidth and how much is L3 capacity, and the counters of the ten later changes. We present those as hypotheses. (The cache explanation of the super-linear scaling is now measured with counters at 1, 2 and 4 nodes; see Q6.)

**Q8. Why rebuild OpenFOAM instead of using the site module?**
- A single run with the site module gave the same speed (−0.08%). Our own build records exactly what ran, and the Bonus patches need a build anyway.

**Q9. Is AOCL-LibM allowed in Basic?**
- It is a math library linked through `FOAM_EXTRA_LDFLAGS`. Precision stays IEEE double, and we use no value-unsafe flags.
- （メモ）関数によっては最後の桁がglibcと違い得ます。Basicの範囲かを聞かれたら、ビルド設定（F1）の範囲と考えていると答えます。

**Q10. Is multiLevel used in Basic?**
- No. Basic uses `scotch`, mapped onto the node's sockets and NUMA domains through the method's own settings (`scotchCoeffs`), which F1 leaves free in Basic. `multiLevel` is a different decomposition method, so it is part of the Bonus.

**Q11. Did profiling affect the benchmark numbers?**
- No. Profiles come from separate diagnostic runs. Benchmark runs have no profiler.

**Q12. Why is the 80-step Cd below the reference?**
- Cd after 80 steps depends on the decomposition. The organisers' own `scotch` run on ASPIRE-2A also gives 0.327 at 80 steps, and their notes say that `hierarchical` and `scotch` differ by 0.7%, 3.0% and 3.5% at 40, 80 and 150 steps. Our Basic (`scotch` mapped onto the node) gives 0.334, `scotch` with its defaults 0.327, and the Bonus (`multiLevel`) 0.323. Against `scotch` with its defaults, the mapping moves Cd by +0.8%, +2.1% and +3.2% and `multiLevel` by +0.5%, −1.3% and +2.6%, no more than the organisers' two methods differ from each other. The Bonus differs from its unmodified baseline by at most 0.0005%, so the gap does not come from our source changes.
- （メモ）主催者の値は`tasks/4.3 OpenFOAM Application Notes - ASPIRE-2A.md`の表と「What Cd tells you」です（2ノード80 stepでhierarchical 0.336869、scotch 0.327130）。目安の0.34は、OHC-1の別の機械での値（0.334〜0.345）です。

**Q13. Why is your Cd different from the organisers' reference?**
- With `scotch` and its defaults our Cd at 150 steps was 0.284049, against 0.283983 in the organisers' `scotch` runs (a relative 2.3e-4). When we ran the site module once with our own scripts and decomposition, we got their value exactly (0.28398300763231610). So that difference comes from our build (for example, we link AMD's math library), not from the decomposition or the method. Our final Basic maps the decomposition onto the node, and a different decomposition moves Cd at 150 steps: 0.293016 (+3.2%).

**Q14. The organisers saw a signal 7 (SIGBUS) at the end of 2- and 4-node runs. Did you?**
- No. That comes from the default OFI provider at `MPI_Finalize`. Our job scripts use Cray MPICH over UCX, and every step of every run returned 0.

**Q15. Why is your run-to-run spread so much smaller than the organisers'?**
- Our 5 Basic runs on 4 nodes lie within 0.18%; the organisers' 5 `scotch` runs spread over 12%. It is not UCX: our runs with the organisers' transport (OFI with `FI_OFI_RXM_USE_SRX=0`) also lie within 0.26%. The main remaining difference is the placement — every rank pinned with its memory on its NUMA domain. Our own baseline without working pinning varied by 8% (3.53–3.82 s/step).

**Q16. Why UCX and not the site's default OFI?**
- In September, every 2- and 4-node run with the default OFI provider died with SIGBUS at `MPI_Finalize`, while UCX completed every run. The organisers have since found that `FI_OFI_RXM_USE_SRX=0` avoids the crash, so we compared again with everything else as in Basic (then without the mapping): 3 alternated 4-node runs each, OFI 2.942 against UCX 2.920 s/step (+0.77%, ranges not overlapping), the same Cd, no crash. Their other workaround, `FI_VERBS_PREFER_XRC=0`, was +0.50% (one run each), also with the same Cd. So UCX stays.

**Q17. Is the pinning fix allowed in Basic?**
- Yes. It is job-script placement: `numactl` sets the memory policy before each rank starts, and `taskset` sets the CPU affinity from outside. F1 lists job scripts, rank placement and affinity as Basic. We did not use `LD_PRELOAD`, which would be Bonus work.

**Q18. Can the organisers reproduce your Basic number?**
- Yes. `build/build.pbs` builds from the official public sources, and `run/submit.sh 1|2|4` runs the whole Allrun chain with plain `qsub`. We re-ran them ourselves (the final Basic on 2026-10-16, the final Bonus on 2026-10-26): at every node count `coefficient.dat` was byte-identical to our recorded runs, and the time within 0.4% of our recorded means (Basic on 4 nodes: 2.9046 against 2.8976 s/step; Bonus on 4 nodes: 2.3651 against 2.3600).

**Q19. Why did you not tune the hierarchical coefficients instead?**
- We kept the case default `(16 8 4)` as the control. scotch was 10.5% faster on 4 nodes in alternated runs, so we spent the remaining effort on scotch and on placement. We have not searched other `nHierarchical` factorisations.

**Q20. What would you do next?**
- Moving fewer bytes still: fuse the assembly of U, k and omega across terms, which removes a few more passes over the face arrays. (The GAMG residual with its restriction and the Laplacian coefficients with the diagonal, which we listed here before, are now done: `0015` and `0006`.)
- The remaining imbalance between ranks (Q21): the slower ranks are the ones that read more from DRAM, so renumbering the cells of each subdomain for locality is more promising than weights or more even cell counts. Making the global sums cheaper (the GAMG coarsest level on fewer ranks) or the network faster (UCX over RC) did not help (Q2).
- We expect a few per cent from these (Q34).

**Q21. Do you know where the imbalance between ranks comes from?**
- Partly. With OpenFOAM's own profiling on all 512 ranks, the computation per rank still varies by 6% (max/median 1.063). Cell counts are balanced within 1% and do not explain it; wall faces explain a little (r = 0.43, 2.8% of the work). Balancing the wall part perfectly would only take it to 1.056, so a wall-weighted split is not worth it. Nodes and NUMA domains show no systematic difference; the variation follows groups of neighbouring subdomains, so it is a property of the mesh regions. Hardware counters on 32 ranks of 4 nodes (#66) show what it is: the slowest and the fastest rank execute about the same number of instructions, but the slowest reads more than twice as many lines from DRAM. A rank's computation follows its DRAM refills (r = +0.69), not its instructions (r = −0.09) or its cells (r = +0.24): it depends on how well each subdomain's data fits in cache.

**Q22. Is the flow video from your scored run?**
- No. Benchmark runs write no flow fields (`controlDict.noWrite`), so we ran the same official case once more with output function objects added: on Genkai, 4 nodes, 150 iterations, because ASPIRE-2A had no free nodes that day. It is a picture of the flow, not a measurement, and the flow does not depend on the machine. The added outputs do not change the computation: its Cd after 150 iterations, 0.28455000886604298, is identical to every digit with Genkai's official 4-node run.
- （メモ）自分からは言わず、聞かれたら答えます。Cdが全桁一致するのは同じ機械・同じ分割の公式runとで、ASPIRE-2Aの値とは分割が違うので数%違います（150 stepでは分割でCdが動きます、Q12）。

**Q23. How do you know it is memory-bound if you could not read the memory counters?**
- On ASPIRE-2A users cannot read the memory-controller counters, so we tested it by moving the ranks. On 4 nodes, 64 ranks per node are as fast as 128 when they keep all memory channels, and 2.1–2.2× slower when the same 64 ranks share half of the channels — as much as the measured bandwidth drops. Compiler flags and PGO change nothing (within 0.13%), and our first four patches, which keep every operation, gain the most where memory is scarcest.
- （メモ）コアを半分にした比較は、分割が512から256に変わります。ただ、帯域に比例しない部分は1 stepあたり約0.1 sしかないので、分割の違いで「コアが半分でも同じ速さ」を説明することはできません。チャネルを半分にした比較は、分割もrankも同じです（#61）。

**Q24. Bandwidth or latency?**
- Bandwidth. If the latency of each core's memory requests set the speed, halving the cores would halve the throughput; it changed by −1% to +2%. Halving the memory channels slowed a step 2.1–2.2×, in line with the bandwidth (2.22×).
- （メモ）1コア2 rankのSMT（#43）では5.7倍遅くなり、どちらとも決められませんでした。今回の配置の実験で決まりました。

**Q25. Most demand refills come from L2. Isn't the data in cache?**
- Demand refills do not count hardware prefetches. The arrays we stream are brought from DRAM into L2 by the prefetcher, so their loads show up as L2 hits. With the first four patches, L2 accesses including prefetches fall 10% and DRAM refills 17%.

**Q26. MPI is 19% of a step. How can the step follow the bandwidth?**
- Most of the MPI time is waiting for the slowest rank, and that rank's computation is bandwidth-bound, so the wait grows and shrinks with it. When we halved the memory channels, the whole step slowed with the bandwidth; only about 0.1 s per step does not scale with it.

**Q27. Why was your baseline slower than the organisers' hierarchical run (3.65 against 3.415 s/step)?**
- Our baseline asked the launcher to pin each rank, but the binding was removed during `MPI_Init`, and each rank's pages ended up spread over all eight NUMA domains (9% on its own). The organisers' runs ask for no binding. We think that is why ours was slower, but we have not isolated it, because the build and the MPI transport also differ.

**Q28. Are 40-step profile runs representative? Do the profilers change the result?**
- With fixed iterations every step does the same work, so 40 steps show the same pattern as 150. The profilers change a step by −1% to +6%, so we never use profiled times as results. Every number we report comes from runs without a profiler.

**Q29. In OpenFOAM, isn't the exchange across subdomain boundaries the bottleneck?**
- Not by volume. Each subdomain exchanges the values on its processor faces at every solver iteration, but cutting the faces between nodes by 92% changed a step by +0.1%, and 55% more network bandwidth (UCX over RC) by −0.01%. What costs time is the synchronisation: about 1,600 global sums per step make every rank wait for the slowest one, and the slowest ranks have almost no neighbours on other nodes. So we fixed the placement and balanced the work instead.

**Q31. Did you profile the network?**
- Yes, at three levels. Every benchmark run ends with an MPI benchmark (IMB) on the same nodes, so we know the bandwidth and the global-sum time of each job. CrayPAT gave the time and count of every MPI call on every rank, and each rank's message count matches its number of neighbours in the decomposition exactly. Then we changed only the network side: 55% more bandwidth (UCX over RC), 92% fewer faces between nodes, another transport (OFI). None made a step more than 0.25% faster. A rank's wait follows its own computation (R² 0.77), not its neighbours. We did not read NIC or switch counters.

**Q30. Why does the Basic gain grow with the node count?**
- Mostly through the decomposition: scotch gains 1.3%, 2.5% and 10.5% on 1, 2 and 4 nodes, and mapping it onto the node gains only on 4 nodes (0.7%). We think the axis-aligned cuts of hierarchical become more uneven when the subdomains are small, but we have not verified it.

**Q32. Your third change skips boundary updates. Isn't skipping boundary checks prohibited?**
- It skips no check. At six places the code formed a surface integral (a divergence), built its boundary values, exchanged them across processor boundaries, and then used only the cell values. We form the same cell values with the same loop and skip only the boundary values that nobody reads. The boundary conditions of the solved fields, every exchange the solution uses, and the bounding of k and omega are unchanged; the bounding appears in our logs as often and with the same values as in the baseline.
- （メモ）R2の禁止事項は「skipping boundary or validity checks」です。no unused boundary updatesは、内部の値しか使わない6か所（ラプラシアンの非直交補正、bounded対流項の`fvm::Sp`、補正付き対流項、連続の式の誤差、`pEqn.H`の右辺、kOmegaSSTの`divU`）で、`fvc::div`と`fvc::surfaceIntegrate`を`fvc::surfaceIntegrateInternal`に置き換えるだけです。中身は同じ`surfaceIntegrate`のループで、境界値を作って評価する処理（coupled境界の交換を含む）だけを省きます。

**Q33. Instructions fell 4%. Did you reduce the work per step?**
- Not the numerical work. Every solve does the same sweeps, residuals and norms as before: in the logs of the baseline and the Bonus of the first four changes, every solve of every step has the same iteration count and the same residuals, to 16 digits. The instructions we removed are copies, allocations and temporary face fields, the second and third pass over the same matrix arrays, and boundary values that nobody reads. The ten later changes keep the iteration counts and the convergence tests too; three of them change the order of some sums, and Cd moves by at most 0.0005%.
- （メモ）命令数−4.1%に対して、DRAMからのrefillは−17.2%、cyclesは−10.8%です（最初の4つ、補足のHardware counters）。ログの比較は本編11枚目のメモにあります（1/2/4ノードで371、771、1,475行が全行一致）。

**Q34. Is another 10% possible?**
- Not easily with the same math and the same work per step. Our third round found 9% more by removing ten more passes, copies and global sums, mostly in the turbulence model and the Gauss–Seidel sweeps. A step still follows the memory traffic, so only moving fewer bytes or reusing more data from cache can help. What is left — fusing the assembly of U, k and omega across terms, renumbering cells for locality — would give a few per cent. Gains of 10% more would need a different computation (fewer iterations, lower precision), which the rules prohibit, or a change that only the benchmark's fixed iterations allow (our last slide: −8.2% on the final Bonus, not counted).
- （メモ）10/16には「数%の見込み」と答えていた案（GAMGの残差と制限、ラプラシアンの係数と対角）は0015と0006で入り、kOmegaSSTの場の式（0013）や残差の作り方（0016）と合わせて−9.3%でした。Basicでは、#61でノードあたり64 rank（全チャネル）が128 rankより1.1%速かった（対応付けの前、各2本）程度です。Gauss-Seidelの複数sweepを、更新の順序を保ったままキャッシュの中で回す（temporal blocking）なら大きく減らせる可能性はありますが、非構造メッシュではまだ研究の段階で、更新の順序を変える重ね合わせ（0018）はCdを1.2%動かしました。

**Q35. Why no roofline?**
- We measured the ceilings on one node: read bandwidth from L1, L2, L3 and DRAM (15.3 TB/s, 8.0 TB/s, 4.4 TB/s, 360 GB/s), under a nominal 4.1 TFLOP/s. But we cannot place measured points for the solver: the DRAM bytes need the memory-controller counters, which users cannot read, and the core counters miss the lines that the prefetchers bring in. So we showed the limit by experiment instead: halving the memory bandwidth makes a step 2.2× slower, halving the cores does not. The sparse-matrix sweeps do about 0.1 flop per byte, far below the compute ceiling.
- （メモ）天井はチームの測定（PBS 26004695、10/26、1ノード、128コア、各3回の中央値）。DRAM read 360 GB/sは読むだけのカーネルで、STREAM triad（約290 GB/s）とは読み書きの形が違います。チームがrooflineの1枚を作りましたが（10/26）、ソルバの点を測れないので、11/01からHPCでは示さないことにしました。

**Q36. Do you require a minimum gain, such as 1%?**
- No fixed minimum. A change is kept when every job with it beats every job without it, in alternated runs. That already demands a gain that stands clear of the spread between identical jobs, which is about 0.2% once the ranks are pinned. A 1% gain is five times that and passes almost every time. We started with a 1% minimum, before we had measured the spread; in September single jobs had been up to 90% slower. Once 29 pinned jobs on 4 nodes showed a standard deviation of 0.19%, we dropped it. Since then two smaller gains passed: mapping the decomposition onto the node, −0.7% with five jobs each, and one global sum per CG iteration, −0.3% with three jobs each and no overlap. A −0.4% change to the malloc thresholds did not separate from the spread, so we did not keep it.
- （メモ）REPORT §4。正規分布を仮定すると、3本ずつの判定が通る確率は、効果がなければ5%、改善がSDの2倍で62%、3倍で89%、5倍で99.8%です（本編7枚目のメモ）。採用した13段のうち11段は1%以上です。

---

## 発表の準備

- この文書で本編13枚を決めてから、`deck/build_deck.py`を作り直します。今のコードは第6版の本編20枚を、チームのデッキの同じ枚の上に作り直す形なので、本編の組み方とノート（`deck/notes.py`）を大きく変えます。補足は、本編が決まってから整理します。
- 図は今のものを流用します：`p10_pinning`（4枚目）、分割の絵（5枚目）、`p12_basic`（6枚目）、`p07_rule`（7枚目）、メモリチャネルの図（8枚目）、Uの例（10枚目）、`p17_scaling`（12枚目）、流れの動画（1枚目）。どれもFigure Nの番号と副題を外し、時間の図には平均とSDを書き添えます。
- 新しく作る図は補足の2枚です（Cdの収束、call stackの木）。
- 本編13枚を、タイマーで通して練習します（目安10分）。各枚で「何を言わないか」も決めておきます。
- 数値は提出物の`README.md`と同じものを、有効数字4桁で使います（2.898／2.360、共通ベースラインの3.415／3.576、baselineは3.650）。%は小数1桁です（−18.6%）。

## 根拠

- 公式のルール：`tasks/2. OpenFOAM HPC Task Rules.md`（Presentation Guidelines、Presentation Excellence）、`tasks/README.md`（R3、R4）、`tasks/5. Common Baselines.md`（10/20）。
- ISC26 SCCのOpenFOAM課題（Virtual Part、https://hpcadvisorycouncil.atlassian.net/wiki/spaces/HPCWORKS/pages/3700260877 、10/31に読み直した）：Task 2は1/2/4ノードのscalability、Task 3は4ノードでのMPIの上位3つ（回数と合計CPU時間）、Task 4はParaViewでの可視化とログからのCdの収束グラフ、Task 5（bonus）は分割方法を変えた効果です。どれも「チームの発表で示す」とあります。
- 図の元データ：リポジトリの`presentation/openfoam/data/`。主な数値の平均とSDは、11/01にこのフォルダのCSVから計算し直しました。主催者の参照値は`tasks/4.3 OpenFOAM Application Notes - ASPIRE-2A.md`とそのログ（`tasks/4.3-aspire2a-logs/`）です。
- 反復ごとのCd：Boxの`openfoam/results/<n>node/coefficient.dat`（Basic）、`openfoam/bonus/results/`（Bonus）、`openfoam/bonus/f3-baseline/`（ソースを変える前のrun）。
- call stack：`research/profile-reaggregation-fa4f5b0/`（#53のCrayPATのstack sampleの集計）。
- ParaViewの絵と動画：`flow/README.md`（流れ）、`decomposition/README.md`（分割）。
- 実験の記録：issue #36〜#38（Basic）、#42、#44、#50、#51（Bonus）、#41、#53（profile）、#46（I/O、OSノイズ）、#47（ばらつき）、#48、#49（通信）、#54（提出スクリプトの再現）、#55（カウンタ）、#56、#60（OFIとUCX）、#57（OpenFOAM組み込みのprofiling）、#58（UCXのRC、GAMGの最も粗い段）、#59（PGO）、#61（コアとメモリのどちらが律速かを、配置だけを変えて確かめた実験）、#62（baselineの1/2/4ノードとプロファイル）、#63（Basicのscotchの対応付け）、#66（ノード数ごとのカウンタ、rank間の不均衡）、#67（10/15の精査と取り組みの一覧）、#68（固定反復で使われない残差）、#69（Bonusの後の10個、最終計測、提出スクリプトでの再実行）。11/01の時点で、10/26の最終計測より新しい結果はありません（mainにもブランチにも、issueにもなし）。
- 各runの公式の結果（`result.txt`）と`coefficient.dat`：成果物の保管庫（Actionsのrun IDごとのフォルダ）。
- 採否の決め方のデータ：`data/changes_ab.csv`（変更ごとの対照と候補の各ジョブ）、`data/decomposition_basic.csv`（scotchとhierarchical）、`data/compiler_options.csv`（7枚目の図のAOCC）、`data/start_unpinned.csv`と`data/pinning.csv`（固定）。
- 提出物：Boxの`Tokyo_Rapids_with_RIKEN_Submission/openfoam/`。
