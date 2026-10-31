# OpenFOAMパートのスライド構成（第7版、作り直し中）

10/31に方針を変え、HPCの本編を14枚・約10分で作り直しています。時間は短くしません。話さなくてよいこと（ルールの説明、飾り、重複）を削り、10分を本質的な説明に使います。この文書で構成、スライドの文、原稿を詰めてから、デッキを作り直します。

- それまでは、改訂版pptx（`~/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx`）と`deck/build_deck.py`は第6版（10/30、本編20枚・約10分15秒）のままです。
- 第6版までのスライドごとの詳しいメモ（数値の来歴、出典、但し書き）は、git履歴の第6版（commit `a1f18a3`の`presentation/openfoam/slides.md`）と、デッキのノート（`deck/notes.py`）にあります。この版では、本編に残す話の根拠だけを、各スライドのメモに書き直しました。
- スライドの文と話す原稿は英語、原稿の訳とメモは日本語です。
- 数値は公式指標（2 step目以降の1 stepの平均時間、s/step）で、主に4ノードの値で話します。図の1点は1ジョブです。
- 図はBoxの`presentation/openfoam/`にあります：`figures/`（グラフ）、`flow/`（ParaViewで描いた流れの絵）、`decomposition/`（ParaViewで描いた分割の絵）。

## 10/31の方針転換

AIパートのチームメイトから、デッキについて指摘がありました（10/31。AIパート向けですが、HPCにもそのまま当てはまります）。

- 1タスク約10分なので、1枚を見せられるのは30秒ほど。今の枚は詰め込みすぎで、30秒では読み取れない。
- 重複する枚が多い。ルールを作った人にルールを説明する必要はない。最終結果を公式のベースラインと並べて見せ、そこから取り組みの順に話す。
- 見た目がよくても読み取りにくいグラフはやめ、単純にする。
- 小さな注記や、余白を埋めるだけの飾りなど、伝えることに効かないものは外す。「What we changed」のような言い回しや注記は、いかにもAIが書いたように見えるので減らす。
- 取り組みの段に番号を付け、詳しく説明する枚でもその番号で指す。

これを受けて、HPCは次のようにします（10/31に決定）。

- 時間を短くするのではなく、必要のないことを話さないことで、10分を意味のある本質的な説明の時間にする。
- スライドは単純に、堅くする（下の「見た目と言葉の決まり」）。
- HPCは取り組み方がAIと違う（段を積み上げるのではなく、測る → 律速を見つける → 直す、を繰り返した）ので、同じ形にはせず、次のものを必ず入れて組み直す。

| 必ず入れるもの | 理由 | 本編 |
|---|---|---|
| abstract：baseline（主催者、自分たち）→ Basic → Bonus。各段のボトルネックとやったことを1行ずつ | 結果を先に見せる。主催者の共通ベースラインは、自分の結果の横に示す決まり（`tasks/5. Common Baselines.md`） | 2 |
| ノイズの測定 | 旧課題の資料が、小さな改善を信じる前に自分のばらつきを知ることを求めていた | 4 |
| 採用の基準 | チームの取り組み方の芯。主催者もSlack（10/30共有）で、何を残すかの決め方を発表に入れてほしいと答えた | 5 |
| ParaViewでの可視化 | 同じ主催者のISC26 SCCのOpenFOAM課題（Virtual Part、Task 4）が求めている | 3 |
| 呼び出しの多いMPI | 同じくISC26の課題（Task 3）が、4ノードでの上位3つ（回数と合計時間）を求めている | 6 |
| プロファイリング | どうやって律速を見つけたか（Task RulesのPresentation Excellence） | 7、10 |
| 速くなった最適化 | 何を変えて、なぜ効いたか | 8、9、11、12 |

ほかに、ルール上外せないもの：

- 1/2/4ノードのscaling（Task RulesのPresentation Guidelines、ISC26のTask 2）→ 14枚目
- Bonusの4点（R3：何を変えたか、なぜ同じ計算か、証拠、自分のBasicに対する速度向上）→ 12枚目
- ISC26の課題のほかの項目：ログから描くCdの収束グラフ（Task 4）は12枚目の図、分割方法を変えた効果（Task 5）は9枚目と11枚目
- 理由と検証のある「効かなかった実験」（`tasks/README.md` R3、主催者のSlackでの回答）→ 13枚目

## 見た目と言葉の決まり

- 1枚に1つのこと。図か表は1つまで、本文は4行まで（2枚目の要約だけは例外）。
- 見出しは、何の枚かを表す短い語句にします（Run-to-run variation、MPI calls on 4 nodesなど）。見出しにコロンや矢印を入れません。
- 見出しの下の主張の行、TAKEAWAYやLESSONの札、Figure N・Table Nの番号、出典やrun IDの小さな注記、余白を埋めるカードやアイコンは置きません。出典と細かい条件はノートに書きます。
- 文は、数字の入った平叙文にします。標語や対句（「Benchmarks decide, profiles explain」「Move fewer bytes, not the same bytes faster」など）、「What we changed」「How we worked」のような見出し、ダッシュ（—）や中黒（·）でのつなぎは使いません。
- 数字には単位（s/step）と、何と比べたか（vs our baseline、vs Basic、vs its control）を付けます。s/stepは小数2桁（1%未満の差を見せるときだけ3桁）、%は整数（1つの変更をその対照と比べた値だけ小数1桁）です。
- 箱（カード）や飾りの図形は使いません。区切りは余白と細い線にし、表は横の罫線だけにします。
- 色は、文字を黒（濃い灰色）、強調を1色だけにします。baseline、Basic、Bonusの語は色分けしません。グラフは、主催者とbaselineを灰色、BasicとBonusを強調色の濃淡で描きます。強調色はAIパートとそろえます。
- 各ジョブを点で描く図は、ノイズ（4枚目）と採用の基準（5枚目）だけにします。ほかは表か単純な棒グラフです。
- 変更の番号：Basicの3つを(1)〜(3)、Bonusの2つを(4)と(5)にし、2枚目、8枚目（(1)）、9枚目（(2)と(3)）、11枚目（(4)と(5)）で同じ番号を使います。
- 文字の大きさは、本文18 pt以上、表16 pt以上です。
- 原稿は英語です。時間は1秒に約2.5語として見積もり、話す間を入れて約10分です。ノートには、英語の原稿、訳、メモの順に書きます。

## 本編（14枚、約10分）

| # | 見出し | 載せること | 図・表 | 目安 |
|---|---|---|---|---|
| 1 | Title | 課題名とチーム名 | | 0:05 |
| 2 | Summary | 主催者の共通ベースラインと私たちのbaseline、Basic、Bonus（4ノード）。BasicとBonusは、ボトルネックとやったことを1行ずつ | 箇条書き（表のように縦をそろえる） | 0:50 |
| 3 | Flow around the DrivAer car | ケース（65.3 Mセル、固定反復）と、4ノード512 rank | ParaViewの絵 | 0:20 |
| 4 | Run-to-run variation | 同じ設定のばらつき（baseline 8%、Basic 0.18%）、単発で最大91%遅い、計測runにプロファイラを付けない | 各ジョブの、平均からのずれ | 0:35 |
| 5 | Criteria for keeping a change | 4つのテスト、採用と不採用の例 | 2つの例の各ジョブ | 0:45 |
| 6 | MPI calls on 4 nodes | 回数の上位3つと、時間の上位3つ | 表 | 0:35 |
| 7 | Profiling the baseline | 道具ごとに分かったこと：固定が外れる、計算が不均一、速いrankが待つ | 表（道具と、分かったこと） | 0:45 |
| 8 | CPU and memory pinning | (1) ジョブスクリプトでの固定。片方だけでは効かない理由（first touch） | 4本の棒（両方、CPUだけ、なし、メモリだけ） | 0:45 |
| 9 | Decomposition | (2) scotchで仕事がそろう、(3) ノードへの対応付け。Basicの合計 | hierarchicalとscotchの分割の絵（ParaView） | 0:45 |
| 10 | Bottleneck after Basic | コア半分では変わらず、チャネル半分で2.2倍遅い。コンパイラは±0.13%以内。約0.1 flop/B | 3本の棒 | 0:45 |
| 11 | Bonus optimizations | (4) multiLevel、(5) 14のソース変更（4つの種類と、どう見つけたか）。DRAMからの読み込みが17%減る | Uの3成分を1回で読む例 | 1:00 |
| 12 | Bonus evidence | R3の4点 | 4行の表、Cdの収束グラフ | 0:40 |
| 13 | What did not help | 効かなかった5つと、その理由 | 表 | 0:40 |
| 14 | Results on 1, 2 and 4 nodes | 1/2/4ノードのs/stepと並列効率、1.55×、残っている律速 | 表 | 0:45 |

原稿の合計は約9分15秒で、話す間を入れて約10分です。

流れ：結果（2）→ 何を計算しているか（3）→ どう測り、どう決めるか（4、5）→ 何が遅いか（6、7）→ Basic（8、9）→ Basicの後の律速（10）→ Bonus（11、12）→ 効かなかったこと（13）→ 1/2/4ノード（14）。測る → 律速を見つける → 直す、を2回まわした順です。

効かなかった実験は13枚目にまとめ、その前でも律速を示す証拠として話します：AOCC（5枚目の不採用の例）、ネットワークの帯域（6枚目の原稿）、ノード間の面を減らすこと（9枚目の原稿）、コンパイラのフラグとPGO（10枚目）。全部の一覧は補足に置きます。

### 1. Title（0:05）

スライド：課題名（OpenFOAM on ASPIRE-2A）とチーム名だけです。今のタイトルの枚のままでかまいません。

原稿：Our HPC task: OpenFOAM on ASPIRE-2A.

訳：HPCの課題、ASPIRE-2AでのOpenFOAMです。

### 2. Summary（0:50）

スライドの文（見出しの横に「4 nodes, average time per step」）：

- Common baseline (organisers): 3.415 s/step (hierarchical), 3.576 s/step (scotch)
- Our baseline: 3.65 s/step (case defaults on our own build of OpenFOAM v2512)
- Basic: 2.90 s/step (−21% vs our baseline)
  - Bottleneck: lost CPU and memory binding, and uneven work per rank
  - What we did: (1) CPU and memory pinning per rank, (2) scotch decomposition, (3) scotch mapped onto the node
- Bonus: 2.36 s/step (−19% vs Basic)
  - Bottleneck: memory bandwidth
  - What we did: (4) multiLevel decomposition, (5) 14 source changes that move fewer bytes, with Cd within 0.0005%

段の名前と時間を左に大きく、BottleneckとWhat we didを右に並べ、表のように縦をそろえます。

原稿（約50秒）：First, the result on four nodes. The organisers' common baseline is 3.415 seconds per step with hierarchical and 3.576 with scotch. Our own baseline, the case defaults on our own build, took 3.65. There, the ranks lost their CPU and memory binding, and the work per rank was uneven. Basic fixes both, with pinning in the job script and a scotch decomposition mapped onto the node: 2.90 seconds, 21 percent faster. After Basic, memory bandwidth limits a step, so the Bonus moves fewer bytes, with a multiLevel decomposition and fourteen source changes: 2.36 seconds, 19 percent faster than Basic, with the same computation.

訳：まず4ノードの結果です。主催者の共通ベースラインは、hierarchicalで1 step 3.415秒、scotchで3.576秒です。私たちのbaseline（ケースの既定のまま、自分たちのビルド）は3.65秒でした。そこでは、rankのCPUとメモリの固定が外れ、rankごとの仕事も不均一でした。Basicでは、ジョブスクリプトでの固定と、ノードに対応付けたscotchの分割で両方を直し、2.90秒、21%速くなりました。Basicの後はメモリ帯域が律速なので、Bonusでは運ぶバイトを減らします。multiLevelの分割と14のソース変更で2.36秒になり、同じ計算のままBasicより19%速くなりました。

メモ：
- 共通ベースラインの出典は`tasks/5. Common Baselines.md`です（ASPIRE-2A、4ノード、サイトの`OpenFOAM/2512`モジュール、ケース既定、Allrun一式を1ジョブずつ流した値）。聞かれたら：共通ベースラインに対して、Basicは−15%（hierarchical比）と−19%（scotch比）、Bonusは−31%と−34%です。
- 比べる基準は、同じビルド・スクリプト・測り方で取った私たちのbaselineです。主催者の値は、ビルド、MPI、配置が違うので参考にとどめます。Bonusの%は、R3どおり自分のBasicに対する値です。
- 私たちのbaseline（3.65）が共通ベースラインのhierarchical（3.415）より遅い理由はQ27です。
- 数値：baseline 3.65（3本、10/12、#62）、Basic 2.898（5本、10/15〜16、#63）、Bonus 2.360（3本、10/26、#69）。baselineに対して−21%と−35%（1.55×）です。
- Bottleneckの行は、その段で取り除いた律速です（Basicの行は、baselineのプロファイルで見つけた律速）。

### 3. Flow around the DrivAer car（0:20）

スライドの文：

- occDrivAerStaticMesh: 65.3 M cells, simpleFoam (k-ω SST), a fixed number of solver iterations per step
- 4 nodes of ASPIRE-2A, 128 cores each: 512 MPI ranks

図：ParaViewの絵を大きく1枚。候補は`flow/stills/streamlines-iteration-150.png`（流線と車体表面の圧力係数）か、`flow/stills/planes-iteration-150.png`（中心断面と水平断面の流速）です。

原稿（約20秒）：This is the case: air flowing around the DrivAer car at 140 kilometres per hour, 65 million cells, solved with simpleFoam. Each step runs a fixed number of solver iterations, so every step does the same work. We run it on four nodes, 512 MPI ranks. We drew the flow with ParaView, from the same case with field output added.

訳：これがケースです。時速140 kmで走るDrivAerの車の周りの空気の流れで、6,500万セルをsimpleFoamで解きます。1 stepの反復回数は固定なので、どのstepも同じ仕事です。4ノード、512 MPI rankで流します。流れは、同じケースに場の出力だけを足したrunから、ParaViewで描きました。

メモ：
- 絵の作り方は`flow/README.md`です（ParaView 5.13.3のpvbatch）。可視化のrunは玄界の4ノード（448 rank、scotch、150反復）で、ASPIRE-2Aの4ノードが空かなかったためです。計測runではなく出力のfunction objectを足しただけで、150反復目のCdは玄界の公式手順のrunと全桁一致しました（Q22）。自分からは言わず、聞かれたら答えます。
- 動画（`flow-iterations.mp4`、`flow-streamlines.mp4`）は20秒には長いので、本編は静止画にします。
- ISC26の課題は、参照の絵（OHC-1のpreliminary results）を再現するよう書いています。視点をそれに合わせるかは未定です。
- 固定反復や指標の定義は、審査員が作った決まりなので説明しません。「どのstepも同じ仕事」とだけ言います。

### 4. Run-to-run variation（0:35）

スライドの文：

- Each setup runs 3 or more times on 4 nodes
- Spread between identical jobs: 8% in our baseline, 0.18% after Basic
- Single jobs ran up to 91% slower (September), so one job never decides
- Timing runs carry no profiler; profilers change a step by −1% to +6%

図（作る）：4ノードの各ジョブを、その段の平均からのずれ（%）で点にした図です。baseline 3本、Basic 5本、Bonus 3本。baselineは−3%〜+5%に散り、BasicとBonusは0の線に重なります。

原稿（約35秒）：Before trusting any gain, we measured our noise. Every setup runs at least three times on four nodes. In our baseline, identical jobs differed by 8 percent; after Basic, by 0.18 percent, because pinning removed the slow ranks. Over 92 runs of 29 repeated setups, most landed within 0.4 percent of their median, but single jobs can be far off: in September, two ran 84 and 91 percent slower. So one job never decides, and timing runs never carry a profiler.

訳：改善を信じる前に、ばらつきを測りました。どの設定も、4ノードで3本以上流します。baselineでは同じ設定のジョブが8%ばらつき、Basicの後は0.18%です。固定で遅いrankがいなくなったからです。29の設定を繰り返した92本では、多くが自分の中央値から0.4%以内でしたが、単発のジョブは大きく外れることがあり、9月には84%、91%遅いものがありました。だから1本では決めず、時間を測るrunにはプロファイラを付けません。

メモ：
- データ：baselineは`data/baseline_runs.csv`の4ノード3本（3.6003、3.5313、3.8170 s/step、#62）、Basicは`data/final_runs.csv`の5本（2.8944〜2.8996）、Bonusは同じく3本（2.3557〜2.3627、0.29%）です。
- 92本・29設定の繰り返しは9/21〜10/05です（`data/bench_runs_sep21_oct05.csv`、#47）。9/27の1本（5.03 s/step）で一度scotchを捨て、同じ時期に交互に流した3本ずつで覆しました（Q3）。
- プロファイラ：baselineはCrayPATの下で3.85、計測runで3.65 s/stepです。道具によって−1%〜+6%変わるので、プロファイルは別のrun（4ノード、40 step）で取り、その時間は結果にも判断にも使いません（Q28）。
- 旧課題の資料（`1_1_OpenFOAM_Measurements_and_Guidance.md` §1.1）の「小さな改善を信じる前に、同じ構成を繰り返して自分のばらつきを知る」に当たる枚です。旧資料の数値は使いません。

### 5. Criteria for keeping a change（0:45）

スライドの文（番号付き）：

1. Alternate with a control: candidate and control run in turns, in the same period, 3 or more jobs each on 4 nodes
2. Every candidate job is faster than every control job. A change with no effect passes this by chance 1 time in 20 at 3 v 3
3. Same computation: Basic changes no source; the Bonus keeps Cd within ±0.5% at 1, 2 and 4 nodes
4. A profile explains the gain

図（右）：テスト2を、2つの小さな変更の各ジョブで見せます（4ノード、候補と対照を同じ時期に）。第6版のFigure 6（`deck/deck_plots.py`の`p07_rule`）から、番号と副題を外して使います。

- Kept: scotch mapped onto the node, −0.69% (5 v 5, no overlap)
- Not kept: AOCC instead of GCC, +0.03% (3 v 3, overlap)

原稿（約45秒）：We keep a change only if it passes four tests. It runs in turns with a control, in the same period, at least three jobs each on four nodes. Every job with the change must be faster than every job without it; a change with no effect passes that by chance once in twenty. The computation must stay the same. And a profile must explain the gain. So the size of the gain does not decide. Mapping the decomposition onto the node gained only 0.7 percent, but all five jobs beat all five controls, so we kept it. The AOCC compiler overlapped its control, so we did not.

訳：変更を残すのは、4つのテストを通ったときだけです。同じ時期に対照と交互に、4ノードで3本以上ずつ流します。変更ありの全ジョブが、変更なしの全ジョブより速いこと。効果のない変更が偶然これを通るのは、3対3で20回に1回です。計算が同じであること。そして、プロファイルで改善の理由を説明できること。だから、改善の大きさでは決めません。ノードへの対応付けは0.7%だけでしたが、5本すべてが対照の5本より速かったので残しました。AOCCは対照と重なったので、残しませんでした。

メモ：
- テスト2の確率：効果がなければ、候補と対照の並び方はどれも同じ確からしさなので、全候補が全対照より速い確率は1/C(n+m, n)です。3対3で1/20、4対4で1/70、5対5で1/252。最小の改善幅は決めていません（run間のばらつきが4ノードで約0.2%のため）。
- 図のデータ：対応付けは#63（10/15、5本ずつ交互、2.918 → 2.898 s/step）、AOCCは`data/compiler_options.csv`（#36 D、10/03、3本ずつ）です。
- 採用した変更は、どれも4ノードでテスト1と2を満たします（`data/changes_ab.csv`、`data/decomposition_basic.csv`）：scotchは3対3、対応付けは5対5、multiLevelと0001は4対4、ほかは3対3です。0013〜0015と0016は対照の数日後に測りましたが、後の10個は最終計測でまとめて、0001〜0004の版と交互に流しました（3対3、範囲は重ならない）。
- （聞かれたら）t検定でない理由：本数が3〜5本と少なく、ジョブ間の差の分布も分かりません。順位だけを見る判定なら分布を仮定せずにすみ、偶然の確率も数えられます。そのかわり保守的で、小さな本当の改善を見逃し得ます（mallocの閾値の−0.4%は3本で区別できず、測り直していません）。
- 固定反復のときだけ効く変更（#68、最終Bonusの上で−8.2%）は、テストを通っても数えません（補足）。
- 主催者のSlackでの回答（10/30共有）：測り方、ばらつきを小さく保つ方法、何を残すかの決め方は、発表と提出物に入れてほしい。とても丁寧なBasicのチューニングには、Bonus点も付き得る（R3の最後の文）。

### 6. MPI calls on 4 nodes（0:35）

スライドの文（表の上に「CrayPAT on our baseline: 4 nodes, 512 ranks, 40 steps」）：

| Most calls | Calls, all ranks | Most time | Time, all ranks (share of MPI) |
|---|---:|---|---:|
| MPI_Isend | 290 M | MPI_Waitall | 22,069 s (55%) |
| MPI_Irecv | 290 M | MPI_Allreduce | 14,140 s (35%) |
| MPI_Test | 289 M | MPI_Bcast | 1,289 s (3%) |

- The calls are the halo exchange with neighbouring subdomains (93% of all calls)
- The time is waiting for other ranks (90% of the MPI time); MPI is 46% of a rank's time

原稿（約35秒）：With CrayPAT on four nodes, the most frequent MPI calls are Isend, Irecv and Test, about 290 million each over all ranks: the halo exchange with neighbouring subdomains. The time goes to Waitall and Allreduce, 90 percent of the MPI time, and both wait for other ranks. MPI is 46 percent of a rank's time. A faster network does not help: later, 55 percent more bandwidth changed a step by only 0.01 percent. So why do the ranks wait?

訳：4ノードのCrayPATでは、回数の多いMPI呼び出しはIsend、Irecv、Testで、全rankでそれぞれ約2.9億回です。隣のサブ領域との境界の値の交換です。一方、時間はWaitallとAllreduceがMPIの時間の90%を占め、どちらも他のrankを待つ呼び出しです。MPIはrankの時間の46%です。ネットワークを速くしても効かず、後に帯域を55%上げても1 stepは0.01%しか変わりませんでした。では、なぜrankは待つのか。

メモ：
- CrayPAT 38219766511（#62）、`data/baseline_profile_4node.csv`。表は512 rankの合計です（ISC26の課題の「total CPU time consumed」に合わせました）。rankあたりでは、Isend・Irecv 566,107回、Test 563,646回、Waitall 43.1 s、Allreduce 27.6 s、Bcast 2.5 s（MPIはrankあたり78.3 s）です。順位はどちらでも同じです。
- ISC26の課題（Task 3）：「Run any MPI profiler to profile the simulation on 4 nodes. What are the 3 most used MPI calls in terms of number of calls and in terms of total CPU time consumed?」
- 待ちであって転送ではない証拠：rankごとのMPI時間は35〜112秒で、セル数はほぼ完全に均等です。UCXのRCでIMBの帯域を55%上げても1 stepは−0.01%（Basic）、rankの並べ替えでノード間の面を92%減らしても+0.1%でした（Q2、Q29、Q31）。
- Basicの後（#53）も回数の上位3つは同じで、時間はAllreduce 48%、Waitall 38%に入れ替わります。MPIはstepの19%になります。

### 7. Profiling the baseline（0:45）

スライドの文（4ノード、512 rank）：

| Tool | What it showed |
|---|---|
| /proc during the solve | 0 of 512 ranks stay on their own core; 9% of a rank's memory is on its own NUMA domain |
| OpenFOAM profiling | Equal cell counts, but the slowest rank computes 1.46× as long as the median |
| CrayPAT | MPI time per rank from 35 to 112 s: fast ranks wait at each of about 1,600 global sums per step |
| AMD uProf | Most computation is sparse-matrix sweeps, with little arithmetic per byte |

- 表の下の1行：The launcher binds each rank, but the binding is removed during MPI_Init

原稿（約45秒）：We profiled the baseline with four tools. In /proc during the solve, none of the 512 ranks stayed on its own core, and only 9 percent of a rank's memory was on its own NUMA domain. OpenFOAM's own profiling shows the effect: the cell counts are equal, but the slowest rank computes 1.46 times as long as the median. CrayPAT shows the cost: a step has about 1,600 global sums, and at each one the fast ranks wait for the slowest. uProf shows where the computation goes: sparse-matrix sweeps, with little arithmetic per byte. The cause: the launcher binds each rank, but the binding is removed inside MPI_Init.

訳：baselineを4つの道具でプロファイルしました。解いている最中の/procでは、512 rankのどれも自分のコアに留まっておらず、rankのメモリのうち自分のNUMA領域にあるのは9%だけでした。OpenFOAMのprofilingにその結果が出ています。セル数は等しいのに、最も遅いrankの計算は中央値の1.46倍です。CrayPATには、その代償が出ています。1 stepに約1,600回の大域和があり、そのたびに速いrankが最も遅いrankを待ちます。uProfでは、計算の中心は疎行列の掃き出しで、1バイトあたりの演算がとても少ないことが分かります。原因は、起動時に頼んだ固定が、MPI_Initの中で外されていたことでした。

メモ：
- 出典：`/proc`とOpenFOAM profilingは38219862855、CrayPATは38219766511、uProfは38219770656（#62）。
- 9%は512 rankの中央値8.7%です（8領域に均等に散れば12.5%）。1.46はrankごとの計算時間（40 stepで54〜115 s）の最大/中央値で、セル数の差は最大でも平均の+0.002%です。
- 大域和の数：1 stepにUで15回×3成分、kとωで8回ずつ、pでGAMG 12サイクル（最粗段のPCGは35回）回すので、rankあたり1 stepに約14,000回の送信と約1,600回の大域和があります。
- uProf：Gauss-Seidelの平滑化、残差、行列とベクトルの積で計算の約4分の1です。どれも疎行列を1回なめる処理で、約0.1 flop/Bです（10枚目につながる）。
- 頼んだ配置（起動コマンドの`--cpu-bind depth`）と実際の配置（実行中の`/proc`）を分けて確かめたことが、この発見の要点です。旧課題の資料の「利得を探す前に、すでに壊れているものを確かめる」に当たります。
- 主催者のASPIRE-2Aのノートには固定の話がなく、主催者の参照runも固定していません。同じ機械を使うチームとの一番の差です（Q27）。

### 8. CPU and memory pinning（0:45）

スライドの文：

- (1) In the job script: numactl binds each rank's memory to its NUMA domain; one watcher per node pins each rank back to its core (taskset)
- During the solve: 512 of 512 ranks on their own core; 58% of a rank's memory is local (was 9%)
- Both halves are needed: Linux keeps a page where it was first written
- 3.65 → 3.26 s/step (−11%)

図：1 stepの時間の4本の棒（4ノード、scotchの分割）。Both 2.92、CPU only 3.47、Neither 3.40、Memory only 4.38 s/step（`data/pinning.csv`）。第6版のFigure 8は各ジョブの点でしたが、平均の棒にします。

原稿（約45秒）：The first Basic change puts the binding back, in the job script only. Each rank starts under numactl, so its memory is bound to its own NUMA domain, and one watcher per node pins each rank back to its core. Both halves are needed. Linux keeps a page where it was first written, so if only the CPU is fixed, the data allocated before that stays remote; if only the memory is bound, the rank runs on another domain and every access is remote. With both, every rank stays on its core and 58 percent of its memory is local, instead of 9. A step drops from 3.65 to 3.26 seconds, 11 percent.

訳：Basicの1つ目の変更は、ジョブスクリプトだけで固定を戻すことです。各rankをnumactlの下で起動してメモリを自分のNUMA領域に縛り、ノードごとに1つの見張りのプロセスが、各rankを自分のコアに固定し直します。両方が必要です。Linuxはページを最初に書かれた場所に置いたままにするので、CPUだけ固定すると、それまでに確保したデータは遠いメモリに残ります。メモリだけ縛ると、rankが別の領域で動き、全部のアクセスが遠くなります。両方そろうと、全rankが自分のコアに留まり、メモリの58%（以前は9%）が近くに来ます。1 stepは3.65秒から3.26秒に、11%短くなりました。

メモ：
- −11%は、hierarchicalのまま固定だけを足した同じ時期の比較です（3.670 → 3.257、−11.2%、10/02〜03、3本ずつ）。3.26/3.65から計算すると−10.7%になるので、整数%で書きます。このときの固定は`LD_PRELOAD`で`MPI_Init`の直後に固定する方法で、Basicの`numactl`＋`taskset`と同じ速さです。
- 図は、scotchの分割での比較です（各1〜3本）。CPUだけ戻すと、戻すまでの12〜16秒に確保したデータが遠くに残ります。Neitherはbaselineと同じ状態（起動時の固定が外れたまま）です。
- `LD_PRELOAD`はBasicでは使えないので、ジョブスクリプトだけでできる形にしました（F1：job script、rank placement、affinity。Q17）。全ジョブのログで、各ノード128/128 rankが固定されています。
- 58%は、対応付けの前のBasicでノード0の128 rankを`/proc`で見た中央値です。100%にならないのは、共有ライブラリやMPIの共有バッファのように複数のrankが使う部分は1つの領域にしか置けないためと考えていますが、確かめていません。

### 9. Decomposition（0:45）

スライドの文：

- hierarchical cuts thin slabs: ranks near the car get more faces and more work
- (2) scotch cuts compact blocks and evens the work (slowest/median rank 1.16 → 1.06): 3.26 → 2.92 s/step (−10.5%)
- (3) scotch mapped onto sockets and NUMA domains (scotchCoeffs): 2.92 → 2.90 s/step (−0.7%)
- Basic: 2.90 s/step (−21% vs our baseline); MPI falls from 46% to 19% of the time

図：hierarchicalとscotchの分割（車体表面をサブ領域ごとに塗った2枚、ParaView）。Boxの`decomposition/panels/`の車体の絵（hierarchicalとscotchの`*-car-subdomains.png`）です。

原稿（約45秒）：The second Basic change is the decomposition. The case default, hierarchical, cuts the mesh into thin slabs along the axes. Near the car the cells are small, so some ranks get many more faces and more work, and the slowest computes 16 percent longer than the median. scotch cuts compact blocks: the work evens out to 6 percent, and a step drops another 10.5 percent. It is the even work that counts: cutting the faces between nodes by 92 percent alone changed nothing. Last, we mapped the scotch decomposition onto sockets and NUMA domains, 0.7 percent more. Basic: 2.90 seconds per step, 21 percent faster than our baseline.

訳：Basicの2つ目の変更は分割です。ケースの既定のhierarchicalは、軸に沿ってメッシュを薄い板に切ります。車の近くはセルが小さいので、一部のrankは面も仕事もずっと多くなり、最も遅いrankの計算は中央値より16%長くなります。scotchはまとまった塊に切るので、仕事の差は6%にそろい、1 stepはさらに10.5%短くなりました。効いているのは仕事がそろうことで、ノード間の面を92%減らしただけでは何も変わりませんでした。最後に、scotchの分割をソケットとNUMA領域に対応付けて、さらに0.7%です。Basicは1 step 2.90秒で、私たちのbaselineより21%速くなりました。

メモ：
- (2)：サブ領域間の面は4.31 M → 2.93 M（−32%）、計算の最大/中央値は1.16 → 1.06です（どちらも固定あり、CrayPAT）。hierarchicalの偏りは、壁の面（車の表面）の数と相関しました（#38）。scotch対hierarchicalは1/2/4ノードで−1.3／−2.5／−10.5%です（交互に3本ずつ、`data/decomposition_basic.csv`）。ノード数が多いほど効く理由は確かめていません（Q30）。
- 「面だけでは効かない」：rankの並べ替え（`MPICH_RANK_REORDER_METHOD=3`）は、サブ領域を変えずにノード間の面を92%減らしましたが、+0.1%でした（13枚目、Q29）。
- (3)：`scotchCoeffs`の`domains`、`domainWeights`、`strategy`で、ノード → ソケット → NUMA領域 → コアの木に合わせました。ノード、ソケット、NUMA領域をまたぐ面が23%、21%、10%減ります。2.918 → 2.898で、5本ずつ交互に流して全runが対照より速かったものです（5枚目の例）。1・2ノードではほぼ変わりません。
- 46% → 19%はプロファイルrun（CrayPAT）の値で、Basicのプロファイルは対応付けの前のものです（対応付けで4ノードのstepは0.7%しか変わりません）。ほかに、計算の最大/中央値は1.46 → 1.06、ばらつきは8% → 0.18%になりました。
- 図のscotchは対応付けの前のものです。ISC26の課題（Task 5）の「分割方法を変えて、性能への効果を示す」にも当たります。

### 10. Bottleneck after Basic（0:45）

スライドの文：

- Memory bandwidth sets the speed of a step
- Half the cores, all 16 memory channels: no change (×0.99)
- The same ranks on half the channels: 2.2× slower; triad bandwidth 279 → 125 GB/s
- Compiler flags, AOCC, LTO and PGO: within ±0.13%

図（作る）：1 stepの時間の3本の棒（Basic、4ノード、2本ずつの平均）。128 ranks per node on 16 channels 2.92、64 ranks on 16 channels 2.89、64 ranks on 8 channels 6.35 s/step。

原稿（約45秒）：After Basic, what limits a step? Users cannot read the memory controller counters on ASPIRE-2A, so we moved the ranks instead. With half the cores on all sixteen memory channels, a step takes the same time. With the same ranks on half the channels, it takes 2.2 times as long, as much as the measured bandwidth drops. Compiler flags, another compiler and PGO changed less than 0.13 percent. The reason is the arithmetic intensity: the sparse-matrix sweeps do about 0.1 flop per byte, a hundred times less than what keeps the cores busy. So memory bandwidth sets the speed, and to go faster we must move fewer bytes.

訳：Basicの後、何がstepの速さを決めているのか。ASPIRE-2Aでは利用者がメモリコントローラのカウンタを読めないので、rankの置き場所を変えて確かめました。16本のメモリチャネルを全部使ったままコアを半分にしても、1 stepの時間は同じです。同じrankを半分のチャネルに載せると2.2倍かかり、測った帯域の落ち方と同じです。コンパイラのフラグ、別のコンパイラ、PGOは0.13%も変えませんでした。理由は演算密度です。疎行列の掃き出しは1バイトあたり約0.1 flopしか計算せず、コアを忙しくするのに要る量の100分の1です。だから速さを決めているのはメモリ帯域で、速くするには運ぶバイトを減らすしかありません。

メモ：
- #61（10/10、4ノード、150 step、各2本、全rankをCPUとそのNUMA領域に固定）。Basic（対応付けの前）は、128 rank/ノード 2.920、64 rank（16チャネル）2.887、64 rank（8チャネル）6.347 s/stepです（`data/memory_placement.csv`）。チャネル半分は×2.20、0001〜0004のBonusでは×2.11でした。triadは同じノードで274、279、125 GB/s/ノードです（`data/triad_placement.csv`）。
- 限界：チャネルを半分にした配置はL3も半分にするので、DRAMの帯域とL3の容量の寄与は分けられません（どちらもメモリ側の資源です）。コアを半分にした比較は分割が512から256に変わりますが、帯域に比例しない部分は1 stepあたり約0.1 sしかありません（Q23）。
- 約0.1 flop/B：内部の面1つに約4 flopで、係数2つ（16 B）、番地（4 B）、セルの値を合わせて30〜40 Bを読みます。ノードの倍精度ピーク約4.1 TFLOP/sをSTREAMの約290 GB/sで割った約14 flop/Bの、約1/100です（Q35）。ノードは128コア、8 NUMA領域、16チャネルです（ASPIRE-2Aの枚は補足）。
- コンパイラ：`-march=znver3`、`-O2`、LTO、AOCC 5.0／AOCL 5.1、GCCのPGOのどれも±0.13%以内でした（`data/compiler_options.csv`、#36 D、#59）。効かなかった実験を、律速の証拠として話す行です。
- rooflineは補足です（チームが測った天井。ソルバの点は測れていません）。

### 11. Bonus optimizations（1:00）

スライドの文：

- (4) multiLevel decomposition (nodes, sockets, NUMA domains, cores; scotch at each level): 2.90 → 2.87 s/step
- (5) 14 source changes that move fewer bytes: 2.87 → 2.36 s/step
  - no copies or zero fills
  - fewer passes over the same arrays
  - no values that nobody reads
  - fewer global sums
- First four changes, 1 node: 4% fewer instructions, 17% fewer refills from DRAM

図（右）：例として、速度の3成分が同じ行列を使うので、3回ではなく1回読む図（第6版のFigure 13、`fig25_u_in_one_pass`と同じ内容）。

原稿（約1分）：The Bonus moves fewer bytes. Four: a multiLevel decomposition that follows the machine, nodes first, then sockets, NUMA domains and cores, with scotch at each level. Five: fourteen source changes. For example, the three velocity components use the same matrix, but the code read it three times; now it reads it once and updates all three. The first four changes target the hottest loops: Gauss–Seidel sweeps, residuals and face loops. We found the other ten by profiling the Bonus again; its call stacks pointed to the turbulence model, the sweeps and the global sums of the coarsest CG. Together they remove copies and zero fills, extra passes over the same arrays, values that nobody reads, and extra global sums. For the first four, the counters show 4 percent fewer instructions but 17 percent fewer refills from DRAM: the gain is in the bytes.

訳：Bonusでは運ぶバイトを減らします。4つ目は、機械の形に沿ったmultiLevelの分割です。ノード、ソケット、NUMA領域、コアの順に、各段をscotchで分けます。5つ目は、14のソース変更です。例えば、速度の3成分は同じ行列を使うのに、元のコードは行列を3回読んでいました。1回読んで3成分を更新するようにしました。最初の4つの変更は、最も重いループ（Gauss-Seidelの掃き出し、残差、面のループ）を狙ったものです。残りの10個は、Bonusをもう一度プロファイルして見つけました。call stackが、乱流モデル、掃き出し、最粗段のCGの大域和を指していました。14の変更は合わせて、コピーとゼロ埋め、同じ配列を何度も読む処理、誰も読まない値、余分な大域和を取り除きます。最初の4つでは、命令は4%しか減らないのに、DRAMからの読み込みは17%減りました。効いているのはバイトの量です。

メモ：
- Bonusになる理由：hierarchicalとscotch以外の分割方法と、ソースの変更はBonusです（F2）。
- (4) multiLevel (4 2 4 16)：サブ領域間の面は2.81 M（scotchの既定は2.93 M）で、ノード間の面はscotchより38%少なくなります。単独の効果は、scotchの既定に対して−1.5%です（#42、4対4）。2.90 → 2.87は、Basic（2.898）とmultiLevelだけのrun（2.873）を並べた値で、直接の対照ではありません。
- (5) 14の変更の種類と番号（スライドには載せません）：no copies or zero fills（0001、0011、0014）、fewer passes（0002、0004、0006、0009、0013、0015、0016）、no unused values（0003、0008、0010）、fewer global sums（0012）。全文は提出物の`bonus/README.md`とpatchです（補足）。0005（#68）と0007はBonusに入っていません。
- 段ごとの値：最初の4つ（0001〜0004）で2.87 → 2.60、後の10個で2.60 → 2.36（−9.34%、1/2/4ノードでfa4f5b0と交互に3本ずつ、範囲は重ならない）。
- 後の10個の見つけ方：最初の4つの版（fa4f5b0）のcall stack（#53）を、関数別・呼び出し経路別に集計し直し（`research/profile-reaggregation-fa4f5b0/`）、v2512のソースを読んで候補を順位付けしました。kOmegaSSTが標本の27%（場の式、勾配、kとωの解き）、最粗段のPCGはほとんどが大域和でした（#69、実装はCodex）。
- Uの例は0002です（1ノード−6.4%、4ノード−2.3%）。
- カウンタ（#55、1ノード、uProf、計算部分だけ、各2本）：命令−4.1%、cycles −10.8%、L1のDRAMからのrefill −17.2%。数えているのはL1のdemand refillで、DRAMの転送バイト数ではありません（Q25）。後の10個はカウンタで測っていません。

### 12. Bonus evidence（0:40）

スライドの文（4行の表）：

| | |
|---|---|
| What changed | 14 patches and the multiLevel dictionaries, submitted as text |
| Why it is the same computation | The iterations, convergence tests and discretisation stay; only copies, extra passes, unread values and extra global sums go |
| Evidence | Cd within 0.0005% of the unmodified run at 1, 2 and 4 nodes (F3 allows ±0.5%); the first four changes are bit-identical, log lines too |
| Speedup vs our Basic | −23% / −22% / −19% on 1 / 2 / 4 nodes, on the same machine |

図（作る）：4ノード150反復のCdの収束（反復ごとのCd）。ソースを変える前のrun（同じmultiLevelの分割）とBonusの2本で、線が重なります。ISC26の課題の「ログから描くCdの収束グラフ」も兼ねます。

原稿（約40秒）：For the Bonus, four points. What changed: fourteen patches and the multiLevel dictionaries, submitted as text. Why it is the same computation: the iterations, the convergence tests and the discretisation stay; only copies, extra passes, unread values and extra global sums go. The evidence: Cd stays within 0.0005 percent of the unmodified run at one, two and four nodes, a thousand times inside the allowed 0.5 percent, and the first four changes are bit-identical, down to every line of the solver log. And against our own Basic, the Bonus is 23, 22 and 19 percent faster on one, two and four nodes.

訳：Bonusについて4点です。何を変えたか：14のパッチとmultiLevelの設定で、テキストで提出しています。なぜ同じ計算か：反復回数、収束判定、離散化はそのままで、取り除いたのはコピー、余分な読み直し、誰も読まない値、余分な大域和だけです。証拠：Cdは1、2、4ノードで変更前のrunから0.0005%以内で、許される0.5%の1000分の1です。最初の4つの変更は、ソルバのログの全行までビット一致です。そして自分たちのBasicに対して、1、2、4ノードで23%、22%、19%速くなりました。

メモ：
- R3の4点（What changed、Why it is the same math、Evidence、Speedup against your own Basic result）に1行ずつ答える枚です。
- 証拠の2段（REPORT §8.3、`bonus/README.md`）：(a) 0001〜0004の版は、変更前のrun（pre-change baseline：同じmultiLevelの分割とrank数で、ソースの変更を外したもの）と1/2/4ノードで`coefficient.dat`がバイト一致し、`simpleFoam.log`の全stepの残差（16桁）、反復回数、連続の式の誤差、kとωのboundingが全行一致しました（371、771、1,475行）。(b) 14すべてのCdは、変更前のrunに対して+1.2 × 10⁻¹²（相対）、−0.00002%、−0.00041%（1/2/4ノード）です。
- 丸めが変わり得るのは0011、0012、0016の3つ（足す順序が変わる）なので、「same arithmetic」ではなく「same computation」と言います。反復回数が固定（`tolerance 0`、`relTol 0`）なので、ログの残差まで比べました（Q7、Q33）。
- 速度向上：Basic 13.365／6.372／2.898、Bonus 10.234／4.992／2.360 s/step（−23.4／−21.7／−18.6%）。Bonusは10/26の最終計測です（#69）。提出スクリプトでの再実行（10/26）も、記録の平均から−0.31〜+0.22%で、`coefficient.dat`はバイト一致しました（Q18）。
- 図：成果物の保管庫にある4ノードのrunの`coefficient.dat`から、反復ごとのCdを2本描きます。線は重なって1本に見えるので、図の中に「two runs; largest difference 0.0005%」のように書くか、差を下の細いパネルに描きます。時間がなければ表だけにします。

### 13. What did not help（0:40）

スライドの文（表）：

| Idea | Time per step vs control (4 nodes) | Why it did not help |
|---|---|---|
| Compiler flags, AOCC, LTO, PGO | within ±0.13% | The loops wait on memory, not on instructions |
| Other MPI transports: OFI, UCX over RC (+55% bandwidth) | −0.16% to +0.77% | MPI time is waiting for the slowest rank, not transfer |
| Rank reordering: 92% fewer faces between nodes | +0.1% | Fewer bytes between nodes do not shorten the wait |
| Weighted cells, METIS with two constraints | +1.5% to +6.1% | Uneven cells, or more faces between subdomains |
| Gauss–Seidel overlapped with the halo exchange | +8.3%, Cd −1.2% | A new update order: outside F3, and slower |

原稿（約40秒）：Not everything helped, and the reasons confirm the bottlenecks. Compiler flags, another compiler and PGO changed less than 0.13 percent, because the loops wait on memory. Other MPI transports did not help, because the MPI time is waiting for the slowest rank, not transfer; for the same reason, 92 percent fewer faces between nodes changed nothing. Weighting cells made the cell counts uneven, and slower. And overlapping the Gauss–Seidel sweep with the halo exchange changed the update order: Cd moved 1.2 percent, outside the check, and it was slower, so we dropped it.

訳：効かなかったこともあり、その理由が律速の見立てを裏付けています。コンパイラのフラグ、別のコンパイラ、PGOは0.13%も変えませんでした。ループがメモリを待っているからです。MPIの転送方式を変えても効きませんでした。MPIの時間は転送ではなく、最も遅いrankを待つ時間だからです。同じ理由で、ノード間の面を92%減らしても何も変わりませんでした。セルに重みを付けると、セル数が不均一になって遅くなりました。そして、Gauss-Seidelの掃き出しを境界の交換と重ねると、更新の順序が変わってCdが1.2%動き、判定の範囲を外れ、しかも遅かったので、やめました。

メモ：
- 主催者は、理由と検証のある「効かなかった実験」も点になると答えています（`tasks/README.md` R3、Slack）。全部の一覧（SMT、GAMGの最粗段、mallocの閾値、0017など）は補足です。
- UCXのRCはIMBの帯域を55%上げましたが、1 stepは−0.01%（Basic）、−0.16%（0001〜0004のBonus）でした。OFIは`FI_OFI_RXM_USE_SRX=0`で+0.77%（3本ずつ交互、Q16）。
- 重み付け：×2、×12の重みと、METISの2制約（面の均衡）は+1.5%〜+6.1%です（Q4、Q5）。
- 0018（#69）：内部セルの掃き出しをprocessor境界の値の交換と重ねました。4ノード3本で+8.32%、Cd −1.20%でF3の±0.5%を外れました。512 rankでは、セルが隣の新しい値を見る順序が変わることが、丸めを超えてCdを動かしました。
- 「proxy metrics」とは言わず、何が良くなって何が変わらなかったかを、そのまま言います。

### 14. Results on 1, 2 and 4 nodes（0:45）

スライドの文：

| s/step | 1 node | 2 nodes | 4 nodes | Efficiency, 1 → 4 nodes |
|---|---:|---:|---:|---:|
| Our baseline | 14.57 | 7.43 | 3.65 | 1.00 |
| Basic | 13.36 | 6.37 | 2.90 | 1.15 |
| Bonus | 10.23 | 4.99 | 2.36 | 1.08 |

- Common baseline (organisers), 4 nodes: 3.415 s/step (hierarchical), 3.576 s/step (scotch)
- 4 nodes: 3.65 → 2.36 s/step, 1.55× faster with the same computation

原稿（約45秒）：Finally, one, two and four nodes. Basic and the Bonus are faster than our baseline at every node count. Parallel efficiency from one to four nodes rises from 1.00 to 1.15 with Basic: on four nodes, each rank's arrays shrink to about 1 megabyte and fit in the L3 cache. The Bonus saves most on one node, where each rank holds four times more data, so its efficiency is 1.08. On four nodes, a step went from 3.65 to 2.36 seconds: 1.55 times faster, with the same computation. What remains is memory traffic, and an imbalance between ranks that follows their reads from DRAM. Thank you.

訳：最後に、1、2、4ノードです。BasicとBonusは、どのノード数でもbaselineより速くなりました。1ノードから4ノードへの並列効率は、Basicで1.00から1.15に上がりました。4ノードでは各rankの配列が約1 MBに縮み、L3キャッシュに収まるからです。Bonusは、各rankのデータが4倍ある1ノードで最もよく効くので、効率は1.08です。4ノードでは1 stepが3.65秒から2.36秒になり、同じ計算のまま1.55倍速くなりました。残っているのはメモリの読み書きの量と、rank間の差です。その差は、各rankがDRAMから読む量に沿っています。ありがとうございました。

メモ：
- 本数（1/2/4ノード）：baseline 6/3/3（#62）、Basic 3/3/5（#63）、Bonus 3/3/3（#69）。
- 効率が1を超える理由は、カウンタで確かめました（#66、uProf、1/2/4ノード）。1セル・1 stepあたりのDRAMからのL1 refillは、4ノードで1ノードの0.70倍です。セルの配列がrankあたり4 MB（1ノード）から1 MB（4ノード）になり、コアあたり4 MBのL3に収まります（Q6）。
- Bonusの効率が下がるのは、1ノードの時間をより多く減らしたからで、4ノードが遅くなったからではありません。
- 残っていること：U・k・ωの組み立てを項をまたいで融合する（運ぶバイトをさらに減らす）、部分領域ごとのセルの並べ替え（rank間の差はセル数ではなくDRAMからの読み込み量に沿う、r = +0.69、#66）。数%の見込みです（Q20、Q34）。
- 共通ベースラインは4ノードの値だけです（`tasks/5. Common Baselines.md`）。

## 入れなかった枚（補足に置く）

- The path on 4 nodes：(1)〜(5)の各段の時間の棒（3.65 → 3.26 → 2.92 → 2.90 → 2.87 → 2.60 → 2.36 s/step）。2枚目と14枚目で足りるので本編には入れません。
- A gain we did not count（#68）：固定反復のときだけ効く−8.2%を、Bonusに数えなかったこと。線引きの話としては良いのですが、Bonusの本筋ではないので補足にします。
- ASPIRE-2Aの構成、baselineの設定、rooflineなど：質疑で出します。

## Qwenに時間を回すとき（削る順）

1. 3枚目の原稿を最初の1文だけにする（−10秒）。
2. 13枚目を補足へ移し、主な理由は5、6、9、10枚目の中で言う（−40秒）。
3. 8枚目と9枚目を1枚にし、図は分割の絵だけにする（−30秒）。

4、5、6枚目（ノイズ、採用の基準、MPIの上位3つ）は、必ず入れると決めた枚なので削りません。

## 決めること

- HPCとAIの順番。HPCは約10分です（Qwenと合わせて15〜20分の中で）。
- 強調色。今のHPCは紺で、baseline・Basic・Bonusを色分けしています。AIパートの色にそろえるか。
- 3枚目の絵：静止画1枚（流線と車体のCp）か、2枚（それに断面の流速）か。ISC26の参照の絵の視点に合わせるか。
- 12枚目のCdの収束グラフを作るか（作らなければ表だけ）。
- おまけ（#68）を本編の最後に残すか（この案では補足）。

## 第6版の本編との対応

| 第6版の本編 | 第7版 |
|---|---|
| 1 Title | 1 |
| 2 OpenFOAM TASK OVERVIEW | 結果は2枚目、ケースと絵は3枚目。指標とstep数の説明は外す |
| 3 ASPIRE-2A | 補足。10枚目の原稿とメモで、16本のメモリチャネルだけ触れる |
| 4 BASELINE SETTINGS | 補足。2枚目に「case defaults on our own build」 |
| 5 BASELINE RESULTS | 2枚目（3.65）、4枚目（8%）、14枚目（1/2/4ノード） |
| 6 HOW WE MEASURE AND PROFILE | 4枚目（ノイズ、計測runにプロファイラを付けない）、7枚目（道具） |
| 7 HOW WE DECIDE WHAT TO KEEP | 5枚目 |
| 8 MPI PROFILE ON 4 NODES | 6枚目（値をrankあたりから512 rankの合計にした） |
| 9 BASELINE ANALYSIS | 7枚目 |
| 10 BASIC OPTIMIZATION (1/2) | 8枚目（各ジョブの点の図を、平均の棒にした） |
| 11 BASIC OPTIMIZATION (2/2) | 9枚目（1/2/4ノードの分割の比較は補足） |
| 12 BASIC RESULTS | 9枚目の最下行、14枚目 |
| 13 MEMORY BANDWIDTH SETS THE SPEED | 10枚目 |
| 14 BONUS OPTIMIZATION | 11枚目 |
| 15 BONUS RESULTS | 12枚目（R3の4点）、14枚目（1/2/4ノード） |
| 16 BONUS ANALYSIS | 11枚目の最下行（カウンタ）。細部は補足 |
| 17 SCALING ANALYSIS | 14枚目 |
| 18 WHAT DID NOT HELP, AND WHY | 13枚目（5行にし、下の3つの問いは外した） |
| 19 CONCLUSION | 2枚目と14枚目。残っている律速は14枚目の原稿 |
| 20 EXTRA: A GAIN WE DID NOT COUNT | 補足 |

## 補足（質疑用）

補足も本編と同じ決まり（短い見出し、注記なし、1枚1つのこと）で作り直します。どれを残すかは、本編が決まってから決めます。今の候補です（括弧は第6版の改訂版pptxでの番号）。

| まとまり | 補足 |
|---|---|
| 進め方と環境 | ASPIRE-2A（本編3）、Baseline settings（本編4）、Build, storage and MPI（27）、Experiment automation（26）、Optimization strategy（23）、Bottlenecks we measured（24） |
| 測り方 | Measuring honestly（25、92本のばらつき）、The organisers' reference（41）、Reproducing our results（44） |
| Basic | hierarchical and scotch on 1, 2 and 4 nodes（本編11の図）、Where a step goes after Basic（28）、Is the network the bottleneck?（30）、OFI against UCX（31）、The three splits（32） |
| Bonus | Cores or memory?（33）、HPC roofline（34、チームが作成）、The source changes（35、36）、Source changes in detail（37、38）、Effect of each Bonus change（39）、Profiles before and after（40）、Hardware counters（本編16）、Drag coefficient checks（43） |
| 結果 | The path on 4 nodes（29）、Why the efficiency exceeds 1（42）、Not adopted: the full list（45）、Compiler and flags（46）、A gain we did not count（本編20、#68） |

各補足の中身は、第6版のslides.md（git `a1f18a3`）の「補足」の節と、デッキのノートにあります。Qwenと共通の再現性スライドは、そのまま残します。

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
- （メモ）命令数−4.1%に対して、DRAMからのrefillは−17.2%、cyclesは−10.8%です（最初の4つ、補足のHardware counters）。ログの比較は本編12枚目のメモにあります（1/2/4ノードで371、771、1,475行が全行一致）。

**Q34. Is another 10% possible?**
- Not easily with the same math and the same work per step. Our third round found 9% more by removing ten more passes, copies and global sums, mostly in the turbulence model and the Gauss–Seidel sweeps. A step still follows the memory traffic, so only moving fewer bytes or reusing more data from cache can help. What is left — fusing the assembly of U, k and omega across terms, renumbering cells for locality — would give a few per cent. Gains of 10% more would need a different computation (fewer iterations, lower precision), which the rules prohibit, or a change that only the benchmark's fixed iterations allow (a supporting slide: −8% on the final Bonus, not counted).
- （メモ）10/16には「数%の見込み」と答えていた案（GAMGの残差と制限、ラプラシアンの係数と対角）は0015と0006で入り、kOmegaSSTの場の式（0013）や残差の作り方（0016）と合わせて−9.3%でした。Basicでは、#61でノードあたり64 rank（全チャネル）が128 rankより1.1%速かった（対応付けの前、各2本）程度です。Gauss-Seidelの複数sweepを、更新の順序を保ったままキャッシュの中で回す（temporal blocking）なら大きく減らせる可能性はありますが、非構造メッシュではまだ研究の段階で、更新の順序を変える重ね合わせ（0018）はCdを1.2%動かしました。

**Q35. Can you show a roofline?**
- Yes, with measured ceilings (a supporting slide made by our team): on one node, read bandwidth from L1, L2, L3 and DRAM (15.3 TB/s, 8.0 TB/s, 4.4 TB/s, 360 GB/s), under a nominal 4.1 TFLOP/s. The sparse-matrix sweeps do about 0.1 flop per byte, far below every ceiling, so a step is bound by the bytes it moves, and halving the bandwidth makes it 2.2× slower. What we cannot place are measured points for the solver: the DRAM bytes need the memory-controller counters, which users cannot read, and the core counters miss the lines that the prefetchers bring in. The arrows on the slide are schematic; their times are measured.
- （メモ）天井はチームの測定（PBS 26004695、10/26、1ノード、128コア、各3回の中央値）。DRAM read 360 GB/sは読むだけのカーネルで、STREAM triad（約290 GB/s）とは読み書きの形が違います。

---

## 発表の準備

- この文書で本編14枚を決めてから、`deck/build_deck.py`を作り直します。今のコードは第6版の本編20枚を、チームのデッキの同じ枚の上に作り直す形なので、本編の組み方とノート（`deck/notes.py`）を大きく変えます。補足は、本編が決まってから整理します。
- 見た目（強調色、見出しの形、フォント）は、AIパートの作り直しとそろえます。
- 作る図：4枚目（各ジョブの平均からのずれ）、8枚目（4本の棒）、10枚目（3本の棒）、12枚目（Cdの収束）。描き直す図：5枚目（第6版のFigure 6から番号と副題を外す）、9枚目（分割の絵2枚）、11枚目（Uの例）。
- 3枚目のParaViewの絵を選びます。
- 本編14枚を、タイマーで通して練習します（目安10分）。各枚で「何を言わないか」も決めておきます。
- 数値は提出物の`README.md`と同じものを使います（2.898／2.360／−18.56%、共通ベースラインの3.415／3.576）。baselineは3.65です。

## 根拠

- 公式のルール：`tasks/2. OpenFOAM HPC Task Rules.md`（Presentation Guidelines、Presentation Excellence）、`tasks/README.md`（R3、R4）、`tasks/5. Common Baselines.md`（10/20）。
- ISC26 SCCのOpenFOAM課題（Virtual Part、https://hpcadvisorycouncil.atlassian.net/wiki/spaces/HPCWORKS/pages/3700260877 、10/31に読み直した）：Task 2は1/2/4ノードのscalability、Task 3は4ノードでのMPIの上位3つ（回数と合計CPU時間）、Task 4はParaViewでの可視化とログからのCdの収束グラフ、Task 5（bonus）は分割方法を変えた効果です。どれも「チームの発表で示す」とあります。
- 図の元データ：リポジトリの`presentation/openfoam/data/`。主催者の参照値は`tasks/4.3 OpenFOAM Application Notes - ASPIRE-2A.md`とそのログ（`tasks/4.3-aspire2a-logs/`）です。
- ParaViewの絵：`flow/README.md`（流れ）、`decomposition/README.md`（分割）。
- 実験の記録：issue #36〜#38（Basic）、#42、#44、#50、#51（Bonus）、#41、#53（profile）、#46（I/O、OSノイズ）、#47（ばらつき）、#48、#49（通信）、#54（提出スクリプトの再現）、#55（カウンタ）、#56、#60（OFIとUCX）、#57（OpenFOAM組み込みのprofiling）、#58（UCXのRC、GAMGの最も粗い段）、#59（PGO）、#61（コアとメモリのどちらが律速かを、配置だけを変えて確かめた実験）、#62（baselineの1/2/4ノードとプロファイル）、#63（Basicのscotchの対応付け）、#66（ノード数ごとのカウンタ、rank間の不均衡）、#67（10/15の精査と取り組みの一覧）、#68（固定反復で使われない残差）、#69（Bonusの後の10個、最終計測、提出スクリプトでの再実行）。
- 各runの公式の結果（`result.txt`）と`coefficient.dat`：成果物の保管庫（Actionsのrun IDごとのフォルダ）。
- 採否の決め方のデータ：`data/changes_ab.csv`（変更ごとの対照と候補の各ジョブ）、`data/decomposition_basic.csv`（scotchとhierarchical）、`data/compiler_options.csv`（5枚目の図のAOCC）。
- 提出物：Boxの`Tokyo_Rapids_with_RIKEN_Submission/openfoam/`。
