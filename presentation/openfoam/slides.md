# OpenFOAMパートのスライド構成（第8版）

HPC（OpenFOAM）パートの発表の正本です。第7版（11/01、本編14枚、約10分）を、ユーザーがチームメイトと話しながら付けたコメント（11/02）を受けて作り直したのが第8版です（本編20枚、約12分）。話すことがあるので枚数は増えてよく、スライドの文は短く、時間は表で示し、「律速を測って、それに対して最適化した」という背景と手法の流れを一番大事にします。骨組み、スライドの文、原稿はこの文書で決め、デッキは`deck/build.sh`で作ります（下の「発表の準備」）。

- 出力のデッキは`~/apac26/Tokyo Rapids with RIKEN Presentation HPC (8th edition).pptx`（HPCだけの43枚）です。チームはHPCとAIを別のデッキにし（11/02、ユーザーがHPCだけの`Tokyo Rapids with RIKEN Presentation HPC.pptx`を置いた）、OneDriveで編集して、チームメイトがrobocopyで定期的にBoxへ上げています。この出力から、ユーザーがOneDriveのデッキへ貼ります。ユーザーのコメント付きのデッキは上書きしません。
- 第7版の出力（AIパートも含む174枚）は`(HPC revised).pptx`という名前でしたが、ユーザーが11/02に`~/apac26`から外しました。第7版のこの文書はgitの`0bb74e3`、第6版はgitの`a1f18a3`にあります。表紙、Q&A目次、補足のノートは`deck/notes.py`にあります。
- スライドの文と話す原稿は英語、原稿の訳とメモは日本語です。想定問答も、英語の答えに日本語の訳を付けています。
- 数値は公式指標（2 step目以降の1 stepの平均時間、s/step）で、主に4ノードの値で話します。図の1点は1ジョブです。
- この文書のスライドの番号は、表紙を数えない番号です。デッキでは1つ大きくなります（この文書の5枚目がデッキの6枚目）。
- 図の素材はBoxの`presentation/openfoam/`にあります：`figures/`（グラフ）、`flow/`（ParaViewで描いた流れの動画と絵）、`decomposition/`（ParaViewで描いた分割の絵。第8版では、ノードとNUMA領域ごとに塗った`decomposition-numa.png`と、玄界で描いたBasicとmultiLevelの`decomposition-numa-scotch-domains-vs-multilevel.png`を使う）。

## 方針（10/31）

AIパートのチームメイトから、デッキについて指摘がありました（10/31。AIパート向けですが、HPCにもそのまま当てはまります）。

- 1タスク約10分なので、1枚を見せられるのは30秒ほど。今の枚は詰め込みすぎで、30秒では読み取れない。
- 重複する枚が多い。ルールを作った人にルールを説明する必要はない。最終結果を公式のベースラインと並べて見せ、そこから取り組みの順に話す。
- 見た目がよくても読み取りにくいグラフはやめる。これはAIパートのrooflineのことです。HPCはrooflineを使っていないので、示しません。
- 小さな注記や、余白を埋めるだけの飾りなど、伝えることに効かないものは外す。「What we changed」のような言い回しや注記は、いかにもAIが書いたように見えるので減らす。
- 取り組みの段に番号を付け、詳しく説明する枚でもその番号で指す。

これを受けて、HPCは次のようにしました。

- 時間を短くするのではなく、必要のないことを話さないことで、10分を意味のある本質的な説明の時間にする。
- スライドは単純に、堅くする（下の「見た目と言葉の決まり」）。
- HPCは取り組み方がAIと違う（段を積み上げるのではなく、測る → 律速を見つける → 直す、を繰り返した）ので、同じ形にはせず、外せないものを並べて骨組みを作る。

## 経緯

第7版は11/01に、ユーザーと9回に分けて詰めました。第8版は11/02です。今の決まりは下の各節にまとめてあり、ここには何をなぜ変えたかだけを残します。

- 1回目（骨組み）：HPCを先に、AIを後に話す。色と図は今のデッキのものを流用する。ばらつきは毎回の比較で測っているので1枚にまとめず、時間の図にSDを書いて、Basicの結果の枚で話し終える。採用の基準は、なぜその大きさで採用してよいかを論理で言えるようにする（Q36）。効かなかったことは典型的で効きそうに見えた手に絞り、高度な試みは補足に回す。権限がなくて読めなかった量をどう特定したかは必ず話す。おまけ（#68）は最後に短く話す。ASPIRE-2Aを選んだ理由、Cdの収束、call stackの図は補足に置き、rooflineは示さない。流れの動画は置くだけで、ISC26の参照の絵の視点は再現しない。有効数字をそろえる。
- 2回目（構成）：ユーザーの案の4幕（Baseline → Basic、Basic → Bonus、scalingと効かなかったこと、おまけ）にする。採用の基準は結果より前に言う。プロファイリングは律速の候補ごとの表にし、BaselineとBasicの2回、同じ見方で見せる。箇条は1つの完結した文にし、変更の番号（(1)〜(5)）はやめる。
- 3回目（ユーザーの日本語の原稿案を受けて）：原稿はスライドを読み上げないが、載っているものは全部説明する。したことは過去形、図の説明と今も成り立つことは現在形にする。2枚目の図は、全ジョブが対照より速いかが一目で分かり、「1点が1ジョブ」の読み方を一度見せられるので残す。MPIの上位3つは、原因が分かる前に置く（3枚目「一番大きいのはMPI」→ 4枚目「中身は待ちで、遅いrankがいる」→ 5枚目「/procで原因を見つけて直す」）。原因の後に見せると話が後戻りするから。プロファイルが40 stepであることの理由は質疑で答える（Q28）。結論の枚は足さず、14枚目の最後の1文で終える（1枚目が要約を兼ね、質疑はAIパートの後なので）。
- 4回目（原稿の訳への指摘を受けて）：同じものは同じ語で呼ぶ（decomposition、computation）。「均等な分割」とは言わず、何が均等になったか（rankごとの計算時間）を言う。実験は前提から言う。2枚目は個々の最適化の名前を出さない。各枚の言い方を直した（4枚目は秒で言う、8枚目は「疎行列をなめるループ」と言う、10枚目は「大きく2つ」と言う、など）。1分に約130語で見積もり直し、要らない文を削った。
- 5回目（第7版のデッキを見て、見た目）：完全な黒の太字、強調は紺、数値に単位、時間は縦軸、図に番号と一文の注釈、プロットにSD、余白をならす。1枚目は、ユーザーが手で作った案（`(HPC revised, user draft 11-01).pptx`に保存）を受けて流れの図にした。11枚目にBasicとBonusの各ジョブの図を足した。scalingは対数軸をやめて線形の軸にした（形は7回目と8回目に変えた）。
- 6回目（ユーザーの依頼、夜）：表にも番号と注釈（表の上）を付けた。AIパートの謝辞の後に、HPCとAIの記録の枚を足した。call stackのflame graphを作った。第7版のビルドで補足の5枚が表示のままだったのを直した。
- 7回目：最初の段を、BasicとBonusと同じく大文字の「Baseline」にした（ソースを変える前のrunの「pre-change baseline」は小文字のまま）。10枚目にmultiLevelの分割の絵を足した。scalingを1つの軸にまとめた（枠ごとに目盛りが違うと、時間が半分ずつになる様子が見えにくいため）。
- 8回目（ユーザーの案）：主催者の結果を「Official」と呼ぶことにした（「Common Baselines」は主催者の文書の名前で、聞く側には「公式の結果」の方が伝わる）。流れの動画を1枚目から7枚目へ移した（1枚目が詰まり、7枚目の箇条の下が空いていたため）。scalingを、ノード数ごとに公式の結果、Baseline、Basic、Bonusを並べる形にした。
- 9回目（提出物の準備と合わせて）：Qwenと共通の再現性スライドを外した（ユーザー。10/21に消えたときは誤りだったので、意図を確かめた）。OpenFOAMの提出物には技術レポートと図を置かないことにした（「根拠」の提出物の行）。STREAMとNUMAのやさしい説明を、9枚目と5枚目のメモに足した。ユーザーがこの版を第7版として確定した。想定問答に日本語訳を付け、今の発表から来そうにない5問（Q3、Q11、Q12、Q14、Q25）を外し、各問に答えるときに映す枚を書いた（ユーザー）。
- 第8版（11/02、ユーザーがチームメイトと話して付けたコメントとメモを受けて。ユーザーは就寝中で、翌朝に確かめる。下の番号はこの最初の版のもの）：
  - 全体：枚数は増えてよい。スライドの文は短く、時間は表で。グラフの時間の軸は原点0から描き、ばらつきを見るために範囲を狭めるときは、0との間を波線で省略する（`deck_plots.py`の`zoomed()`）。「律速に対して最適化した」流れを一番大事にし、1枚目の原稿にも入れた。デッキはHPCだけにした（AIパートと、HPCとAIの記録の枚は出さない）。
  - 3、11枚目：「Computation」の行を「Outside MPI」にした（MPIの外の時間で、計算とメモリ待ちを含む）。
  - 4枚目：MPIの表を回数順と時間順の2つに分け、よく呼ばれる呼び出しの時間も書き、512 rankの合計とrankあたりを書き分けた。遅いrankは、最速・中央値・最遅で言う。
  - 5、6枚目：固定を2枚に。なぜ固定するか（NUMA）から話し、ノードのアイコンの図を描いた。結果の枚は、Baselineと同じhierarchicalでの固定なし・ありの比較にし、Baseline自身のジョブも並べた（第7版の図のNeitherはscotchで、Baselineではなかった）。ばらつきが小さくなったことも話す。scotchでの4通りの図は補足へ。
  - 7枚目：分割の絵をノードとNUMA領域ごとの色にし、最も遅いrank、面、時間を表にした。
  - 8、9枚目：Basicの結果に公式の結果を足し、時間を表に、図に矢印を付けた。同じ図の横にBasicの後のMPIの表を置く枚を足した。
  - 10、19枚目：効かなかった手を、BasicとBonusに分けて全部見せ、+−ではなくslower／fasterで書き、ふつうは効く手と直感に反した手を紺にして理由を言う（補足の全部の一覧は外した）。
  - 12枚目：配置の実験を、CPUとメモリのアイコンで描いたノードの図にした。128/8と32/16を試さなかった理由をメモに書いた。
  - 13〜16枚目：Bonusを分割（multiLevel）、ソースの変更の意図別の一覧2枚、変更を図にした例（0002と0001）に分けた。試した分割の全部は補足へ。
  - 17枚目：Bonusの結果に公式の結果とBaselineを足し、段ごとの比較を表にし、カウンタの図は補足だけにした。
  - 18枚目：並列効率ではなく、1ノードの何倍速いかの表にした。
  - 20枚目：#68（固定反復でだけ効く変更）は運営に合法か問い合わせ中なので、そのまま。違法なら、おまけと結論の枚ごと消す。
  - ユーザーの質問への答えは、各枚のメモにある：NeitherとBaselineの違い（6枚目）、renumberMesh（10枚目）、MPIの時間は合計か（4枚目）、128/8と32/16（12枚目）、公式の結果のscotchが遅い理由（8枚目）、ほかの分割（13枚目と補足の33枚目）。
- 第8版の2回目（11/02、ユーザーが第8版を見て。ASPIRE-2AにはVPNの問題で入れないので、ジョブは流さない）：
  - Basicの順番：分割はOpenFOAMの高速化で最も一般的な手（Task Rulesも「Decomposition (try this first)」）なので、最初に考えて試した、という流れにした。scotch（5枚目）→ 置き場所を確かめて固定が外れていると分かる（6枚目）→ scotchでの4通りの固定（7枚目。第7版の図に戻した。各実験の結果を示せるので）→ scotchをノードの木に写す（8枚目、新規）→ Basicの結果（9枚目）→ 効かなかったこと（11枚目）。実際の順（ASPIRE-2Aでは最初からscotchで流し、9/21に固定が外れていると分かり、10/03にscotchで固定の4通りを測った）とも合う。第8版の最初の版の固定の図（Baselineと同じhierarchicalでの比較）は補足の30枚目へ移した。
  - 分割の設定は`decomposeParDict`の書き方で示す（5、8、14枚目。scotchのdomains (2 4 16)とmultiLevel (4 2 4 16)）。
  - 図と表に日付を書かない（固定の図と表、補足の再実行の表）。
  - #68：運営の答え（11/02、Slack）は「固定反復で残差の計算と大域和を省くのは1 stepの仕事を減らすことで、Bonusも含めてどの段でも数えない。他のチームと比べる値は、残差を計算し続けるrunのものでなければならない。どこまで行くかを見せたいなら別の枚にしてよいが、その枚は採点しない。同じ残差をより安く計算し、計算も出力も続けるなら、自分の変更なしのrunと結果が合う限りBonusに残せる」。ユーザーの判断で、おまけと結論の枚（最初の版の20枚目）を消し、最終結果は20枚目の最後の1文で言う。残差を省かずに安く作る0012と0016は、この答えのとおりBonusに残る。
  - 13枚目：配置の実験の図を、CPUとメモリの帯の簡単な図にした（ユーザー：今のはリアルだが分かりにくい。CPU、memoryと書いて、半分になったのが分かるように。矢印はよい）。
  - 9枚目（Basic results）はそのまま（ユーザー：良くなっている）。
  - ユーザーの質問への答え：分割の絵はdomains (2 4 16)の後か（5枚目のメモ：前のplain scotch）、分割は最も一般的な手か（5枚目のメモ）、実験の順番（6枚目のメモ）、renumberMeshで速くする方法はなかったか（11枚目のメモ）。
- 第8版の3回目（11/02夜、ユーザーが2回目の版を見て）：
  - 1枚目：公式の記録を「hierarchical 3.415 s/step」「scotch 3.576 s/step」と、分割の名前を付けて書く。
  - s/stepをsと略さない。表の見出しにs/stepがあれば値は数字だけ（10枚目など、本編と補足の全部の表）。図の平均も「s/step」と書く。
  - ユーザーが出力を手で直して保存した3か所を取り込んだ（17:51、取り込むことはユーザーに確かめた）：4枚目の右の表を左へ寄せて広げた（MPI_Allreduceが1行に入る）、5枚目の絵の見出し「hierarchical (16 8 4)」、14枚目の絵の見出し「multiLevel (4 2 4 16)」（ユーザーの手ではmultilevelと小文字だったが、OpenFOAMの名前どおりLを大文字にすることもユーザーに確かめた）。
  - 13枚目：CPUの箱とメモリのチャネルを、NUMA領域ごとにまとめて隙間を空けた。1つの箱が8コア（L3の組）であることをメモに書いた（ユーザーの質問「4コアをフル、8コアを半分で合ってる？」）。
  - domainsを入れたscotchの分割の絵：ASPIRE-2Aに入れないので、玄界で同じ設定の分割を作った（`decomposition/decomposition-genkai.pjm`、PJM 7236147、ユーザー：玄界で動かしてscpすればよい）。BasicもmultiLevelも、512のサブ領域ごとのセル数と隣り合う組ごとの共有面が、ASPIRE-2Aの計測runと全部一致した。抜き出した面は`~/apac26/decomposition-genkai-20261102/`。玄界にParaViewがなかったので、ユーザーの案で玄界にParaView 6.0.1をビルドして描き（`/fast/pj26000080/paraview/6.0.1-osmesa`）、scpで持ってきた。描き直したmultiLevelは10/09の絵とバイト単位で同じだったので、画角と色は同じ。BasicとmultiLevelを並べた絵はBoxの`presentation/openfoam/decomposition/decomposition-numa-scotch-domains-vs-multilevel.png`（`decomposition/README.md`）。
- 第8版の4回目（11/02夜、ユーザーが`(8th edition_tmp).pptx`の原稿の訳に書いた指摘と、デッキでの手直しを受けて。下の番号はこの文書の番号）：
  - 全体：時間の比較は、小さくてもよいので各ジョブの図にする（図でジョブの本数、時間、SDが分かる）。図の横の表からJobsの列を外した（7、9枚目、補足30枚目）。5枚目は時間の表を図にした。
  - 1枚目：1文目を短くし、出発点をBaselineと呼ぶ（訳のとおり）。公式の記録の行を「hierarchical:」「scotch:」とタブで揃えた形はユーザーの手直しで、取り込んだ。
  - 2枚目：Cdを0.5%以内に保つことと、改善の理由をプロファイルで説明することはルールに書いてあるので言わず、3つ目の項目を「ルールのとおり計算を変えない」と短くした。「20回に1回」の文を外した。
  - 3枚目：MPIの46%のうち42%が他のrankを待つ時間だと、表と原稿で示す（ユーザー：これだとMPIが最大の律速に見えない。computingとwaitingを示せる必要がある）。「3.650 s/step」はユーザーの手直し。
  - 4枚目：中央値（1.96 s）を外した。
  - 5枚目：scotchは切る面をできるだけ少なくする分け方だと原稿で言う（ユーザーの質問への答え）。絵の下に色の凡例を置いた（ユーザー：元の絵にあった凡例が欲しい）。
  - 7、8枚目：交互に流したことは2枚目で言っているので言わない（スライドの文と図の注釈からも外した）。
  - 10枚目：呼び出しの回数も4枚目と同じく表にし、9枚目と同じ図を外した（ユーザー：callも書くならグラフを消すのも1つの方法）。
  - 11枚目：紺の行を「効きそうだと思ったもの」と言う。コンパイラが効かない理由は12枚目で分かるので、ここでは言わない（スライドの1行も外した）。renumberMeshは原稿から外し、メモと想定問答のQ39に答えを置いた（ユーザー：聞かれそう、やっていないのはマイナスの印象、Basicで変えられないのか問題文を確かめて → 補遺F1とFAQのとおり、Basicでは変えられない）。
  - 14枚目：左の絵をplain scotchから、玄界で描いたBasic（domains (2 4 16)）に替え、色の凡例を置いた（ユーザー：scotchの絵を更新して載せる）。
  - 19枚目：Bonusの倍率が小さい理由の文を原稿から外した（メモに残した）。
  - 20枚目：紺を「予想外だったもの」と言い、最後に「This ends the HPC part.」で終える。
  - 表紙のノートの日本語のメモを外した（ユーザーが消していた）。
- 第8版の5回目（11/02深夜、ユーザーが4回目の版を見て）：
  - CPUとメモリの図（6枚目のノードの絵、13枚目の帯）：rankが動くコアを紺、使うメモリチャネルを緑に分けた（ユーザー：`_tmp`で手直ししたように色を分ける。メモリは基板っぽい緑。緑はユーザーが選んだテーマの緑の25%暗い色、548235）。13枚目は、半分にした数（64 ranks、8 channels、Half the cores、Half the channels）を赤に、1つ目の矢印を黒にしたユーザーの手直しも取り込んだ。
  - 図からジョブの本数を外した（ユーザー：グラフの「3 jobs」などは不要）。目盛りの本数、1本だけの公式の結果のSDの代わりの「1 job」、scalingの凡例の「1 job」、補足の各変更の図の「3 v 3」。本数は点で分かる。
  - renumberMeshを詳しく調べ直した（ユーザーの質問：問題文では取り組むべきものだが、やっていない。どれくらい効果が見込めるか）。答えは11枚目のメモとQ39。
- 第8版の6回目（11/03未明、ユーザーが5回目の版を見て）：
  - 矢印を黒にした（1枚目の流れ、6枚目のlocal memory、13枚目の2本、17枚目の図、各ジョブの図の変化の矢印）。remote memoryへの矢印は灰色のまま、変化の%と「2.2 times the time」は紺のまま（ユーザー：黒い矢印に。timeは青でいい。remote memoryは灰色でもいい）。
  - 17枚目の左右の間に細い縦線（ユーザーの手直しを取り込んだ）。注釈の揃えや文の位置は、ユーザーが最後に手で整えるので取り込まない。
  - 19枚目（scaling）：表をやめて図をスライドの高さまで大きくし、何倍速いかと4倍を超える理由を図形で重ねた（ユーザー：ごちゃついている。図だけにしてpptの矢印や文字を重ねれば、表がいらず図も見やすい）。表がなくなったので、20枚目の表はTable 15になった。
  - renumberMeshの答え（Q39）を、分割、固定、Cuthill–McKeeで局所性がすでに取れている、という形にした（ユーザー：やっていないのは痛いので、どう守るかが大事。固定と領域ごとの分割で振り直しはあまり問題にならない、と言えるか）。
- 第8版の7回目（11/03朝、ユーザーが6回目の版を見て書いたメモを受けて。ユーザーは就寝中）：
  - Basicの順番を「固定 → 分割 → ノードの木」にした（ユーザー：固定の実験と、domainsを入れる前のscotchの結果が、どれもBasicの結果の時間に見えて論理が怪しい。実際は固定されていないと分かっていて、固定すれば速くなると予想できたので先にやった、という話がきれい。hierarchicalで固定の実験をしていればよかった）。hierarchicalでの固定なし・ありの比較は#36にあった（10/02、交互、−11.2%。補足30枚目にあった図）。#36には、固定と分割を掛け合わせた4通り（hierarchicalとscotch、それぞれ固定なしとあり）が全部そろっていて、どの段も交互の比較になる：固定（hierarchicalで−11.2%）→ scotch（固定ありで−10.5%）→ ノードの木（−0.7%）。実際の順も、固定が外れていると分かって直した（9/21）のが先で、分割の比較（10/02）は固定してから測った。5枚目（固定）→ 6枚目（固定の結果：hierarchicalの2通りとscotchの4通りを1つの図に）→ 7枚目（分割：固定したhierarchicalとscotch）→ 8枚目（ノードの木）→ 9枚目（Basicの結果に、段ごとの表）。
  - 3枚目の最後で、MPIから見た理由を言う（ユーザー：MPIの方が割合が小さく見えるのに、なぜ優先したのかと聞かれそう）：待ちは遅いrankのせいで、rankを待たせるもの（どこで動くかとメッシュの切り方）はBasicで変えられる。質疑はQ40、Q41（固定を先にした理由。固定すると分割の効果がはっきり出た。補足30枚目を固定と分割の掛け合わせの枚にした）。
  - 10枚目（Basicで効かなかったこと）をBasicの最後に、11枚目（Basicの後のMPI）と12枚目（Basicのプロファイル）をBonusの始まりにした（ユーザー：効かなかったことはBasicの最後に。BasicからBonusへ行くところでプロファイルし、そこでMPIも見せられる）。11枚目の原稿は「For the Bonus」で始める。フッターは付けない（ユーザー：スライドを見れば分かる）。
  - コンパイラが効かなかったことは、10枚目では結果だけ言い、理由（メモリ律速）は13枚目（メモリの限界）で言う（ユーザー：メモリに取り組んだのはBonusなので、考察はBonusの後で）。
  - 12枚目：MPIの外の81%のうち、コアは計算で忙しくなかったことを表と原稿で言う（ユーザー：ビジーではないという書き方、CPU使用率はどうか）。CPU使用率は、メモリを待つコアもMPIで待つコアも100%と数えるので区別できない。代わりにコアのカウンタ（1サイクルに0.4〜0.7命令）を使う（Q42）。
  - 図の矢印と変化の%（と、補足の図の%、scalingの倍率）を図の画像から外し、PowerPointの図形にした（ユーザー：手で微調整するので。時間は埋め込みのまま）。`deck_plots.py`が図ごとに`<図>.json`を書き、`build_deck.py`の`overlay()`が重ねる。
  - ノート：メモをやめ、各枚に関係しそうな想定質問（重なってよい）と、関係する補足の枚を書いた（ユーザー：メモは乱雑で分かりにくい）。各枚の節の「想定質問：」「補足：」の行から作り、答えは想定問答の節から引く。メモはこの文書にだけ残る。
  - 15、16枚目：一緒に測った変更は「with 0008, 0010  −2.0%」と、withを前に、%を右端にそろえた（ユーザー：%を縦に比べやすく）。
  - ユーザーの手直し（11/03 2:24の保存）を取り込んだ：17枚目の「−2.3%」「−3.4%」を赤に、19枚目の4倍を超える理由の文の位置。
  - renumberMeshのほかの並べ方を玄界で測った（ユーザー：ほかの方法では速くならないと否定できればよい。玄界でのテストはしてよい）。課題のケースを4ノード448 rankで、既定のCuthill–McKee、逆順（RCM）、並べ替えなし、spring、乱数の順を40反復ずつ、4巡。既定に対してRCM −0.2%（ばらつきの中、1巡は遅い）、なし+0.7%、spring +3.3%、乱数+10.6%で、既定より速い並べ方はなかった。どの並べ方もCdを変えた（40反復目で最大1.3%）。補足43枚目（Other renumberings on Genkai）を足し、Q39の答えを「測った」形にした（`renumber/README.md`、`data/renumber_genkai.csv`）。

## 外せないもの

| | 外せないもの | 理由 | 本編 |
|---|---|---|---|
| a | 結果：公式の結果（Official）、私たちのBaseline、Basic、Bonus（4ノード） | 公式の結果（主催者の共通ベースライン）は、自分の結果の横に示す決まり（`tasks/5. Common Baselines.md`） | 1、9、18 |
| b | abstract：BasicとBonusで、どの律速に何をしたか | 結果と道筋を先に見せる | 1 |
| c | ParaViewの流れ（動画を流すだけ） | ISC26 SCCのOpenFOAM課題（Virtual Part、Task 4） | 9 |
| d | 採用の基準と、その論理 | チームの取り組み方の芯。主催者もSlack（10/30共有）で発表に入れてほしいと答えた | 2 |
| e | プロファイリング：律速の候補ごとの測り方と、寄与の大きさ | Task RulesのPresentation Excellence | 3、12 |
| f | MPIの上位3つ（呼び出し回数と合計時間、4ノード） | ISC26の課題（Task 3）。APACのTask Rulesも「MPI profiling and analysis are strongly recommended」 | 4（Basicの後は11） |
| g | 権限がなくて読めない量を、別の方法で特定したこと | チームが力を注いだところ | 5（`/proc`）、3（IMB）、13（配置の実験、STREAM） |
| h | 速くなった最適化と、なぜ効いたか | Task Rules | 5〜9、14〜18 |
| i | ばらつき（ノイズ） | 旧課題の資料。どの比較でも測っている | 全部の時間の図（標準偏差）、3（BaselineのSD）、6（固定で小さくなった）、9（Basic） |
| j | Bonusの4点（R3：何を変えたか、なぜ同じ計算か、証拠、自分のBasicに対する速度向上） | `tasks/README.md` R3 | 15〜17（何を、なぜ同じか）、18（証拠、速度向上） |
| k | 1/2/4ノードのscaling | Task RulesのPresentation Guidelines、ISC26のTask 2 | 19 |
| l | 分割方法を変えた効果 | ISC26のTask 5 | 7、8、14 |
| m | 典型的なのに効かなかった手と、その理由 | `tasks/README.md` R3、主催者のSlackでの回答 | 10、20（コンパイラの理由は13） |
| n | 今の律速 | 何が残っているかを言えること | 20 |
| o | 数えなかった高速化（おまけ） | 線引きを自分で言えることを見せる | 外した（運営の答え、11/02：どの段でも数えない。ユーザーの判断で枚ごと消した） |

補足に必ず置くもの：ASPIRE-2Aを選んだ理由（Q1）、Cdの収束のグラフ（ISC26のTask 4）、call stackの図（段階ごとの棒とflame graph）、試した分割の全部。効かなかったことの全部は、第8版から本編（10枚目と20枚目）にあります。

## 並べ方

測る → 律速を見つける → それに対して直す、を繰り返した順に並べます（ユーザー、11/02：この流れが最も大事）。

- 1枚目：結果（公式の結果と、Baseline → Basic → Bonus）と、BasicとBonusでどの律速に何をしたか。
- 2枚目：何を残すかの決め方。この後の数字は全部これで決めたので、結果より前に言います。
- Baseline → Basic（3〜10枚目）：律速の候補ごとの測り方。MPIが46%で、その大半（42%）は他のrankを待つ時間で、rankを待たせるものはBasicで変えられる（3）→ MPIの中身は待ちで、同じセル数なのに遅いrankがいる（4）→ 置き場所を確かめると、NUMAのために固定するはずが外れていた（5）→ hierarchicalで固定の効果、scotchで片方だけの固定、ばらつき（6）→ 固定した上で、分割をscotchにする（7）→ scotchをノードの木に写す（8）→ Basicの結果と段ごとの表（9）→ Basicで効かなかった手（10）。11/03に「固定 → 分割」の順にしました（ユーザー。経緯の7回目）。
- Basic → Bonus（11〜18枚目）：Bonusのために、3枚目と同じ見方でBasicをプロファイルする。MPIの待ちが減った（11）→ 残りはMPIの外で、コアは計算で忙しくない。メモリのカウンタは読めない（12）→ 読めないメモリ帯域を、配置の実験とSTREAMで確かめ、コンパイラが効かなかった理由もここで言う（13）→ 分割を機械の階層に沿わせる（14）→ 運ぶデータを減らすソースの変更の一覧（15、16）と図にした例（17）→ 結果（18）。
- scalingと終わり（19、20枚目）：1/2/4ノードと、4ノードで4倍を超える理由（19）→ Bonusで効かなかった手と、今の律速（20）。最後の1文で最終結果（2.360 s/step、Baselineより35.3%短い）に戻って終えます。結論だけの枚は置きません（1枚目が要約を兼ねる）。
- デッキでは、チームの表紙（1枚目）の次に、この20枚が2〜21枚目として並びます。この文書の番号は、表紙を数えない番号です。

## 見た目と言葉の決まり

- 1枚に1つのこと。本文は4行までで、文は短くします。時間を言うだけの文は表にします（ユーザー、11/02）。図と表は、多くて2つまでです（7、8、9、10、14、18、19枚目など）。
- OpenFOAMの設定は、OpenFOAMの書き方（`decomposeParDict`の行）で示します（ユーザー、11/02：multiLevel (4 2 4 16)やscotchのdomainsは文法に沿って示す方が分かりやすい）。等幅の字（Consolas）で、左に細い線を引きます。
- 図と表に、実験や最適化をした日付は書きません（ユーザー、11/02）。日付はメモに書きます。
- 見出しは、何の枚かを表す短い語句にします（MPI calls on 4 nodesなど）。見出しにコロンや矢印を入れません。
- 箇条は、1つの完結した文で書き切ります。カンマと括弧はできるだけ使いません（英語として自然な範囲で）。表のセルも短い文か語句にします。
- 原稿でも、コロン、セミコロン、ダッシュ（—）は使いません。
- 原稿は、スライドを読み上げません。ただし、スライドに載っている文、図、表は、どれも原稿で説明します（「In the figure」「as the table shows」のように指してから、意味を言う）。
- 同じものは、スライドでも原稿でも同じ語で呼びます。英語の技術発表では、言い換えるより同じ語をくり返す方が分かりやすいからです。分割はdecomposition（splitは使わない）、rankの仕事量はcomputationです。プロファイルでMPIの外の時間は「Outside MPI」と呼び、中身は「computing and waiting for memory」と言います（computationだけだとCPUの計算時間に見えるため、11/02）。
- 効かなかった手の結果は、+−ではなく「0.8% slower」「0.4% faster」「no change, within 0.1%」のように言葉で書きます（ユーザー、11/02）。採用した変更の表（15、16、18枚目）は、1 stepの時間の変化を−3.4%のように書きます。
- 段の名前はBaseline、Basic、Bonusで、私たちの最初の段も大文字で「Baseline」と書きます（ソースを変える前のrunの「pre-change baseline」は小文字）。主催者の公式の結果は「Official」と呼びます（出典の文書名はCommon Baselines）。
- 時制：取り組んだことと測った結果は過去形（We pinned、A step dropped）、図表の説明と今も成り立つ事実は現在形（The figure shows、Linux keeps each page where it was first written、memory bandwidth limits the solver）にします。スライドの箇条も同じです。
- 見出しの下の主張の行、TAKEAWAYやLESSONの札、出典やrun IDの小さな注記、余白を埋めるカードやアイコンは置きません。出典と細かい条件はノートに書きます。
- 図には、通し番号とどういう図かを一文で書いた注釈を、図の下に付けます（「Figure 3. Each job of a change that was kept and of one that was not, against its control on 4 nodes.」）。本編はFigure 1から、補足はFigure S1からです。表にも、通し番号と一文の注釈を、表の上に付けます（「Table 2. The top three MPI calls of the Baseline by count and by time, from CrayPAT over 40 steps.」）。本編はTable 1から、補足はTable S1からです。
- 標語や対句（「Benchmarks decide, profiles explain」など）、「What we changed」「How we worked」のような見出し、中黒（·）でのつなぎは使いません。
- 色は今のデッキの色合い（`deck/palette.py`）のままにします。黒い文字は完全な黒（#000000）です。箱（カード）や飾りの図形は使わず、区切りは余白と細い線にします。表は横の罫線だけにします。
- スライドの文字は、できるだけ太字にします。強調はテーマ色の青（紺）で示し、太さでは示しません。Baseline、Basic、Bonusの語は段の色です。
- CPUとメモリの図では、rankが動くコアを紺、使うメモリチャネルを基板のような緑にして分けます（ユーザー、11/02の5回目。`_tmp`での手直しのとおり、`palette.MEMORY`）。
- 矢印は黒にします（ユーザー、11/03。1枚目の流れの矢印は手直しのとおり3 pt）。remote memoryへの矢印だけは灰色です。図の中の変化の%は紺のままです。17枚目の変更の図の上の4ノードの変化は、ユーザーの手直しのとおり赤です（11/03）。
- 図の矢印と変化の%、scalingの倍率は、図の画像に入れず、PowerPointの図形として図の上に重ねます。時間（平均とSD）は画像のままです（ユーザー、11/03：手で微調整するので）。`deck_plots.py`が図ごとに矢印と文字の位置を`<図>.json`に書き、`build_deck.py`の`overlay()`が重ねます。
- 一緒に測った変更の値は、「with 0008, 0010  −2.0%」のようにwithを前に置き、%を右端にそろえます（ユーザー、11/03：%を縦に比べやすく）。
- 数値には、よほど場所が足りないとき以外、単位を付けます（2.898 s/step、290 M calls、43.1 s）。1 stepの時間の単位はs/stepで、sと略しません。表の見出しや行の名前にs/stepと書いたときは、値には単位を付けません（ユーザー、11/02の2回目）。図の平均の数字には「2.898 s/step」と書き、群が近い図では単位を次の行に置きます。
- 図は今のもの（`deck/deck_plots.py`の各ジョブの点の図など）を流用し、時間は縦軸にします。プロットには、点の近くに必ず平均（単位付き）と標準偏差（SD）を書きます。ジョブの本数は点で分かるので、目盛りにも凡例にも書きません（ユーザー、11/02の5回目）。図の中の見出しも、コロンを使わない文にします。
- 時間を比べるときは、小さくてもよいので各ジョブの図にします。図の横の表には、ジョブの本数を書きません（図で本数、時間、SDが分かるため。ユーザー、11/02の4回目）。
- 時間の軸は原点0から描きます。ばらつきを見るために範囲を狭めるときは、0から範囲の下までを細い帯に縮め、軸に波線を入れて省略を示します（ユーザー、11/02、`deck_plots.py`の`zoomed()`）。段どうしの変化は、図に矢印と%で書きます。
- 文字の大きさは、本文18 pt以上、表16 pt以上です。余白が多い枚は、図を大きくするか、文字を大きくするか、行間を広げて、ものが平均的に置かれた状態にします。
- 原稿は英語です。聞く側の余裕も見て、1分に約130語（1秒に約2.2語）として時間を見積もります。第8版は約12分半です（HPCとAIを合わせて15〜20分の中で、チームが配分を決める）。
- ノートには、英語の原稿、訳、その枚に関係しそうな想定質問（重なってよい。答えは想定問答の節から引く）、関係する補足の枚を書きます（ユーザー、11/03：メモは乱雑で分かりにくい）。各枚の節の「想定質問：」と「補足：」の行から作ります。補足は「30（Pinning and decomposition）」のように、デッキの番号と見出しで書き、ビルドが見出しと照らし合わせます。メモはこの文書だけに残します。

## 数値の決まり（有効数字）

- s/stepは有効数字4桁にします（3.650、2.898、2.360、14.57、6.372）。Basic以降の4ノードのジョブの標準偏差は0.002〜0.004 s（0.07〜0.16%）で、4桁目がちょうどその大きさです。1%未満の差もこの桁なら見えます。これより細かい桁はノイズです。
- 標準偏差は%で書きます（SD 0.07%）。図では平均の上に「2.898 s/step」「SD 0.07%」と書きます。1本だけの公式の結果には、SDを書きません。
- %は小数1桁にします（−20.6%、−18.6%、−0.7%）。0.1%に満たない差は「within 0.1%」と書きます。
- 倍率は有効数字3桁（1.55×、4.61×）です。scalingは、並列効率ではなく1ノードの何倍速いかで示します（11/02）。
- Cdの差は、F3の照合に使った値の桁（−0.00041%など）で書きます。他者の値は出典の桁のまま引きます（主催者の3.415）。
- それぞれの変更は、同じ時期の自分の対照と比べた値で言います。だから段ごとに始点の値が少し違います（固定の対照のhierarchicalは3.670、固定したhierarchicalは3.257、ノードの木の対照は2.918、本編のBaselineは3.650）。11/03から、Basicの段はどれも交互の比較です（固定 → 分割 → ノードの木）。交互でないのは、補足30枚目とQ41の、固定なしのscotch対hierarchical（10/02と10/03）だけです。

主な数値（4ノード、平均、SD、本数）：

| | s/step | SD | 本数 | 出典 |
|---|---:|---:|---:|---|
| 主催者の共通ベースライン（スライドではOfficial。hierarchical / scotch） | 3.415 / 3.576 | | 1 / 1 | `tasks/5. Common Baselines.md` |
| 私たちのBaseline | 3.650 | 4.1% | 3 | #62 |
| Basic | 2.898 | 0.07% | 5 | #63 |
| Bonus | 2.360 | 0.16% | 3 | #69 |
| Bonus＋数えなかった変更（#68、運営の答えでどの段でも数えない。デッキから外した） | 2.166 | 0.26% | 3 | #68 |

1/2ノード：Baseline 14.57（SD 2.0%、6本）／7.427（2.0%、3本）、Basic 13.36（0.02%、3本）／6.372（0.08%、3本）、Bonus 10.23（0.32%、3本）／4.992（0.25%、3本）。4ノードは1ノードの何倍速いかで、Baseline 3.99×、Basic 4.61×、Bonus 4.34×です（並列効率なら1.00、1.15、1.08）。

段ごと（4ノード、同じ時期の対照と交互に）：

| 変更 | 対照 → 候補（s/step） | 変化 | 本数 |
|---|---|---:|---|
| 固定（hierarchicalで、6枚目） | 3.670 → 3.257 | −11.2% | 3対3 |
| scotch（固定あり、7枚目） | 3.257 → 2.915 | −10.5% | 3対3 |
| 固定（scotchで、6枚目の4通り） | 3.395 → 2.917 | −14.1% | 2対3 |
| scotch（固定なし、補足30枚目。交互ではない） | 3.670 → 3.395 | −7.5% | 3対2 |
| ノードの木への対応付け（8枚目） | 2.918 → 2.898 | −0.7% | 5対5 |
| multiLevel（対照はscotchの既定） | 2.918 → 2.873 | −1.5% | 4対4 |
| 最初の4つ（0001〜0004、1つずつ） | 2.873 → 2.599 | −3.4、−2.3、−1.3、−2.8% | 3〜4対3〜4 |
| 後の10個（最終計測でまとめて） | 2.603 → 2.360 | −9.3% | 3対3 |
| 不採用の例：AOCC 5.0／AOCL 5.1 | 2.910、2.911 | within 0.1%（範囲が重なる） | 3対3 |

（後の10個は、1つずつの比較では−2.0%（0006〜0010）、−1.0%（0011）、−0.3%（0012）、−2.5%（0013〜0015）、−3.8%（0016）です。数値は`data/*.csv`から計算しました。）

律速の寄与（4ノード、rankの時間に対する割合）：

| 律速の候補 | 測り方 | Baseline | Basicの後 |
|---|---|---|---|
| 遅いrankを待つ時間 | CrayPAT、OpenFOAM profiling | 42%（MPIが46%、そのうちWaitallとAllreduceがrankの169.6 sのうち70.7 s） | MPIが19%、その大半が待ち |
| CPUとメモリの置き場所 | 実行中の全rankの`/proc` | 0/512 rankが自分のコア、自分の領域のメモリ9% | 512/512、58% |
| 通信の転送そのもの | 毎回のIMB、MPIの呼び出し回数 | 大域和は1 stepで約0.02 s（1%未満） | 同じ |
| 演算 | uProf、コンパイラの比較 | 約0.1 flop/B、IPC 0.4〜0.7 | コンパイラを変えても±0.13%以内 |
| メモリ帯域 | 配置の実験、同じノードでのSTREAM、コアのカウンタ | （測っていない） | 1 stepの約97%が帯域に比例 |
| ファイルI/O、OSのノイズ | 時間の計測、割り込みの数 | 0.01%、0.8% | 同じ |

（約97%：配置の実験（#61）の、全チャネルの2.887 s/stepと半分のチャネルの6.347 s/step、STREAMの279と125 GB/sから、「帯域に比例する部分＋比例しない部分」に当てはめた見積もりです。比例しない部分は1 stepあたり約0.08 sです。半分のチャネルの配置はL3も半分にするので、「メモリ側（DRAMの帯域とL3）」の寄与です。これらは別々のrunと道具の値で、VTuneのtop-downのように足して100%にはなりません。）

## 本編（20枚、約12分半）

| # | 見出し | 載せること | 図・表 | 目安 |
|---|---|---|---|---|
| 1 | OpenFOAM on ASPIRE-2A | 私たちのBaseline → Basic → Bonusの時間の流れと、公式の結果（Official） | 時間の流れ、Figure 1 メッシュ（話さない） | 0:30 |
| 2 | Criteria for keeping a change | 交互に流し、全ジョブが対照より速いときだけ残す。ソースの変更は計算を変えない | Figure 2 採用と不採用の例の各ジョブ | 0:35 |
| 3 | Profiling the Baseline | 自分たちのビルドと3.650 s/step（SD 4.1%）。律速の候補ごとの測り方と結果。MPIは46%で、その大半（42%）は他のrankを待つ時間。待たせるものはBasicで変えられるので、MPIから見た | Table 1 | 1:00 |
| 4 | MPI calls on 4 nodes | 回数の上位3つと時間の上位3つを2つの表に。512 rankの合計とrankあたり。待ちと、最速・最遅のrank | Table 2、Table 3 | 0:45 |
| 5 | CPU and memory pinning | なぜ固定するか（NUMA）、`/proc`で見つけたこと（Baseline）、原因、直し方 | Figure 3 ノードのアイコンの図 | 0:45 |
| 6 | Pinning results | hierarchicalで固定なしと両方の固定（−11.2%）、scotchで4通り（−14.1%）を1つの図に。片方だけでは効かない。SDも小さくなった | Figure 4 2つの分割と各配置の各ジョブ | 0:45 |
| 7 | Decomposition | 固定した上で分割をscotchに。hierarchicalとscotchを`decomposeParDict`の書き方で、固定した各ジョブの図（目盛りに面の数、−10.5%）、NUMAごとの色の絵と凡例 | Figure 5 各ジョブ、Figure 6 分割の絵 | 0:50 |
| 8 | Scotch on the node tree | `scotchCoeffs`のdomains (2 4 16)とdomainWeights。木の段ごとの重みと面の変化、各ジョブ | Table 4、Figure 7 plain scotchと対応付けの各ジョブ | 0:45 |
| 9 | Basic results | 段ごとの比較の表（固定、scotch、ノードの木、Baselineに対して）と、公式の結果、Baseline、Basicの各ジョブの図。ばらつきも小さくなった | Table 5、Figure 8 流れの動画（話さない）、Figure 9 各ジョブ | 0:35 |
| 10 | What did not help in Basic | Basicで試して残さなかった手の全部。効きそうだと思った手（紺）と、ネットワークが効かなかった理由（コンパイラは結果だけ） | Table 6 | 0:30 |
| 11 | MPI after Basic | Bonusのために、4枚目と同じ2つの表（回数と時間、rankあたり）をBaselineとBasicで。回数は同じ3つで、待ちが減った | Table 7、Table 8 | 0:35 |
| 12 | Profiling Basic | 3枚目と同じ見方の表。MPIは46% → 19%、MPIの外が81%で、コアは計算で忙しくない（1サイクルに0.4〜0.7命令）、メモリのカウンタは読めない | Table 9 | 0:35 |
| 13 | Measuring the memory limit | コアを半分、チャネルを半分にした配置を、CPUとメモリの帯で。コンパイラが効かなかった理由。1 stepの約97%が帯域に比例 | Figure 10 3つの配置のノード | 0:55 |
| 14 | multiLevel decomposition | Basicの範囲外の分割、Basicの対応付けとの違い（`decomposeParDict`を左右に）、得られること（面の表）、BasicとmultiLevelのNUMAごとの絵と凡例 | Table 10、Figure 11 分割の絵 | 0:40 |
| 15 | Source changes by intent (1/2) | 14の変更の考え方。運ぶデータを減らす。7つは配列をなめる回数を減らす | Table 11 | 0:30 |
| 16 | Source changes by intent (2/2) | 残りの7つ（コピー、使われない値、大域和） | Table 12 | 0:20 |
| 17 | Two source changes in pictures | 0002（Uを1回で）と0001（コピーなし）を左右に図で | Figure 12、Figure 13 | 0:30 |
| 18 | Bonus results | 公式の結果と3つの段の各ジョブ。段ごとの比較の表。Cd | Table 13、Figure 14 | 0:35 |
| 19 | Scaling from 1 to 4 nodes | 1/2/4ノードの各ジョブを大きな図で。1ノードの何倍速いかと、4倍を超える理由（L3）を図に重ねる | Figure 15 | 0:35 |
| 20 | What did not help in the Bonus | Bonusで試して残さなかった手の全部（予想外だったものを紺に）と、今の律速。最後に最終結果と、HPCの発表の終わり | Table 14 | 0:45 |

原稿は合わせて約1,650語です。1分に約130語で見積もると原稿だけで約12分40秒です（1分に140語なら約11分50秒。第7版は14枚で約10分）。HPCとAIの発表は合わせて15〜20分（`tasks/2. OpenFOAM HPC Task Rules.md`のPresentation Guidelines。配分はチームが決める）なので、AIパートの時間と合わせて決めます。削るときは下の「時間が足りないとき（削る順）」の順にします。

### 1. OpenFOAM on ASPIRE-2A（0:30）

スライド：上半分は4ノードの1 stepの時間の流れ。Our Baseline 3.650 s/step（case defaults。その下に小さく「Official」と、「hierarchical:」「scotch:」の後にタブで揃えた「3.415 s/step」「3.576 s/step」。ユーザー、11/02：公式の記録のhierarchicalとscotchを明記する。タブで揃えた形は4回目のユーザーの手直し）→ −20.6% → Basic 2.898 s/step（binding and rank balance。11/03に固定を先にした順に合わせた）→ −18.6% → Bonus 2.360 s/step（less data moved per step）。下半分はFigure 1、メッシュの細かさの絵（「Refinement level of the 65.3 million cells, finest near the car.」）。

原稿（約30秒）：We optimised OpenFOAM on ASPIRE-2A. On four nodes our Baseline took 3.650 seconds per step. Basic brought it down to 2.898 seconds and the Bonus to 2.360 seconds. In Basic the ranks waited for each other, so we fixed the lost CPU and memory binding and the imbalance between ranks. In the Bonus memory bandwidth limited the solver, so we reduced the data each step moves.

訳：私たちはASPIRE-2Aで最適化を行いました。4ノードで、Baselineは1 step 3.650秒でした。Basicで2.898秒、Bonusで2.360秒になりました。Basicではrankが互いを待っていたので、外れていたCPUとメモリの固定と、rankの間の不均衡を直しました。Bonusではメモリ帯域が律速だったので、1 stepで運ぶデータを減らしました。

想定質問：Q1、Q8、Q27、Q18
補足：24（ASPIRE-2A and why we chose it）、25（Build, MPI and run settings）、27（The organisers' reference）、28（Reproducing our results）

メモ：
- BasicとBonusの文で、何が律速だったかを言います（ユーザー、11/02：「ボトルネックに対して最適化した」という背景と手法の流れが最も大事）。1文目は、ユーザーが訳を「私たちはASPIRE-2Aで最適化を行いました」と短くし、出発点を「baseline」と呼んだのに合わせました（11/02の4回目）。
- メッシュの絵と、公式の結果（Official）の小さな行は、見せるだけで原稿では触れません。公式の結果は`tasks/5. Common Baselines.md`の値です（ASPIRE-2A、4ノード、サイトの`OpenFOAM/2512`モジュール、ケース既定、Allrun一式を1ジョブずつ、固定なし。3.415 s/stepがhierarchical、3.576 s/stepがscotch）。9枚目の表と図で話します。
- Baselineに対して、Bonusは−35.3%（1.55×）です。この%は20枚目の最後の1文で言います。

### 2. Criteria for keeping a change（0:35）

スライドの文（番号付き）：

1. Candidate and control ran in turns in the same period with at least 3 jobs each on 4 nodes.
2. We kept a change only if every candidate job was faster than every control job.
3. Source changes had to keep the computation the same, as the rules require.

図（右、Figure 2）：`deck/deck_plots.py`の`p07_rule`。パネルの見出しは「Kept」「Not kept」だけで、個々の変更の名前は出しません。第8版から、時間の軸を0から描き、各ジョブの差が見える範囲の下を波線で省略しています（ユーザー、11/02）。

原稿（約35秒）：First, we set a rule for which changes to keep. Each candidate optimisation and its control ran in turns in the same period, at least three jobs each on four nodes. We decided to keep a change only if every job with it beat every job without it. The figure shows a change that passed and one that did not. Source changes also had to keep the computation the same, as the rules require.

訳：まず、どの変更を残すかの決まりを作りました。最適化候補とその対照を、同じ時期に交互に、4ノードで3本以上ずつ流しました。変更ありの全ジョブが、変更なしの全ジョブより速いときだけ採用することに決めました。図は、通った例と通らなかった例です。ソースの変更では、ルールのとおり、計算の中身を変えないことも条件にしました。

想定質問：Q36、Q37、Q7
補足：26（Run-to-run variation over 92 jobs）

メモ：
- 3つ目の項目（ユーザー、11/02の4回目：Cdを0.5%以内に保つことと、改善の理由をプロファイルで説明することはルールに書いてあるので、わざわざ言わない。計算が同じであることを条件にした、と簡単に言う程度で）：第8版の3回目までは「Source changes had to keep Cd within 0.5% of the unmodified code.」「A profile had to explain why the change helped.」の2項目でした。中身はF3のCd ±0.5%と、R3の「なぜ同じ計算か」「証拠」です（15〜18枚目）。
- 図を残す理由：全ジョブが対照より速いかどうかが、点の分かれ方で一目で分かります。以降の時間の図も同じ「1点が1ジョブ」の描き方なので、ここで読み方を一度見せておけます。
- 例の中身（Kept：ノードへの対応付け、2.918 → 2.898 s/step、5本ずつ。Not kept：AOCC、2.910と2.911 s/step、3本ずつ）は言いません。
- Basicはソースを変えません。分割を変えるとCdは数%動きますが、それはルールが認めた変更です（デッキの41枚目）。だからCdの条件は、ソースの変更（Bonus）にだけ付きます（F3の±0.5%）。
- 2つ目の項目の確率：効果がなければ、全候補が全対照より速い確率は1/C(n+m, n)です。3対3で1/20、4対4で1/70、5対5で1/252。原稿では言いません（ユーザーが訳から「20回に1回」の文を消した、11/02の4回目）。聞かれたら答えます（Q36）。
- どの大きさなら採用してよいかの論理（Q36）：決まった最小値はなく、「全ジョブが対照より速い」こと自体が、改善がばらつきより大きいことを求めます。固定したscotchの29本（4ノード、10月初め）のSDは0.19%でした。ばらつきを正規分布として数えると（11/01の模擬計算、各20万回）、3本ずつの判定が通る確率は、効果がなければ5%、改善がSDの2倍（約0.4%）で62%、3倍（約0.6%）で89%、4倍で98%、5倍（約1%）で99.8%です。5本ずつにすると偶然の確率は0.4%（1/252）に下がります（3倍で77%）。
- 経緯：最初（10月初めまで）は「1%以上」も条件にしていました。ばらつきを測る前で、9月には84%、91%遅い単発のjobもあったからです。ばらつきが分かって外しました（REPORT §4）。採用した13段のうち11段は1%以上で、1%未満は対応付け（−0.7%、5対5）と0012（−0.3%、3対3）の2つです。
- 毎回対照を流した理由（Q37）：同じコミットを別の時期に測り直すと、−0.35%〜+0.19%ずれました（`data/changes_ab.csv`）。小さめの改善（0.3〜1.3%）と同じ大きさです。
- 固定反復のときだけ効く変更（#68）は、テストを通っても数えません。運営の答え（11/02）でもどの段でも数えないと決まり、デッキから外しました（想定問答のQ34）。

### 3. Profiling the Baseline（1:00）

スライドの文（表の上に2行）：

- Our Baseline was unmodified v2512 built with GCC 11.2 and run on Cray MPICH over UCX.
- It took 3.650 s/step on 4 nodes with an SD of 4.1% over 3 jobs.

表の注釈（表の上）：Table 1. Each possible bottleneck of our Baseline, how we measured it and what we found.

| Possible bottleneck | How we measured it | What we found |
|---|---|---|
| MPI | CrayPAT and OpenFOAM profiling | 46% of each rank's time, 42% waiting for other ranks |
| Outside MPI | CrayPAT and AMD uProf | The other 54%, computing and waiting for memory |
| Network transfer | IMB after every run | Global sums took about 0.02 s per step |
| File I/O and OS noise | Timers and interrupt counts | 0.01% and 0.8% of the time |

原稿（約60秒）：We took as our Baseline unmodified OpenFOAM v2512 with the case defaults, built with GCC 11.2 and run on Cray MPICH over UCX. On four nodes it took 3.650 seconds per step, with a standard deviation of 4.1 percent. The table lists each possible bottleneck. MPI took 46 percent of each rank's time, and almost all of it, 42 percent, was waiting for other ranks. The other 54 percent was outside MPI, where the cores compute and wait for memory. Global sums took only about 0.02 seconds per step, and file I/O and OS noise were below 1 percent. A waiting rank does no work, and what makes ranks wait, where they run and how the mesh is cut, can be changed in Basic. So we looked inside the MPI time first.

訳：私たちは、改変していないOpenFOAM v2512をケースの既定のまま、GCC 11.2、UCXの上のCray MPICHで流したものをBaselineとしました。4ノードで1 step 3.650秒、標準偏差は4.1%でした。表は、律速の候補を並べたものです。MPIは各rankの時間の46%で、そのほとんど、時間の42%は他のrankを待つ時間でした。残りの54%はMPIの外で、コアが計算し、メモリを待っている時間です。大域和は1 stepで約0.02秒しかかからず、ファイルI/OとOSのノイズは1%未満でした。待っているrankは何も仕事をしていません。そして、rankを待たせるもの、つまりrankがどこで動くかとメッシュの切り方は、Basicで変えられます。そこで、まずMPIの時間の中身を見ました。

想定質問：Q40、Q38、Q28、Q31
補足：25（Build, MPI and run settings）、29（Is the network the bottleneck?）

メモ：
- MPIから見た理由（ユーザー、11/03：MPIの方が割合が小さく見えるのに、なぜ優先したのかと聞かれてもおかしくない）：46%のうち42%は待ちで、待ちは最も遅いrankの計算の長さで決まります。rankを待たせるもの（置き場所とメッシュの切り方）はジョブスクリプトと`decomposeParDict`で変えられるのでBasicの範囲、MPIの外の計算そのものはソースを変えないと速くならないのでBonusです。原稿の最後の2文で言い、詳しくはQ40で答えます。
- 待ちの42%（ユーザー、11/02の4回目：この表だとMPIが最も大きい律速には見えない。computingとwaitingを示せる必要がありそう）：CrayPAT（38219766511）のrankあたりで、MPI_Waitall 43.10 sとMPI_Allreduce 27.62 s、合わせて70.72 sが、プロセスの時間169.57 sの41.7%です（MPIの78.26 sの90%。4枚目の表）。MPIの外の54%は計算とメモリ待ちを合わせたもので、ASPIRE-2Aではカウンタで分けられません（uncoreのカウンタが読めない）。1 stepは最も遅いrankで決まり、待っているrankは仕事をしていないので、まず待ち、つまりrankの間の差を調べた、という順です。聞かれたら：54%の中身がメモリ待ちであることは、Basicの後に配置の実験で確かめました（13枚目）。
- 「Computation」の行を「Outside MPI」にしました（ユーザー、11/02：computationはCPUの計算時間に見えるが、実際はMPIの外の時間で、メモリを待つ時間も含む）。中身は「計算とメモリ待ち」と表と原稿で言います。12枚目も同じ言葉にしました。
- 2行目の「3.650 s/step」は、ユーザーがデッキで「3.650 s per step」から直したものです（11/02の4回目）。原稿の1文目は、ユーザーの訳（「…で流したものをbaselineとしました」）に合わせました。
- ビルドと設定：未改変のv2512、GCC 11.2（`PrgEnv-gnu/8.3.3`、`-O3`）、AOCL-LibM、Cray MPICH 8.1.15（UCX）、ケースの既定のhierarchical (16 8 4)、起動時の固定（`mpiexec --cpu-bind depth`、サイトの推奨）。Basic、Bonusも同じビルド、スクリプト、測り方です（REPORT §3、§5）。
- SDの4.1%は#62の3本（3.53〜3.82 s/step）です。英語ではstandard deviationと言います。
- 出典：`/proc`とOpenFOAM profilingは38219862855、CrayPATは38219766511、uProfは38219770656（#62）。
- 46%：CrayPATで、MPIはrankの時間の46%です。プロファイラの下のrunなので、1 stepは3.85 s（計測runは3.650）です。残りの54%（MPIの外）は、命令を実行している時間と、メモリからデータが来るのを待っている時間を合わせたものです。uProfでは、Gauss-Seidelの平滑化、残差、行列とベクトルの積がその約4分の1で、12枚目でメモリを疑う理由の1つになります。
- 大域和：1 stepにUで15回×3成分、kとωで8回ずつ、pでGAMG 12サイクル（最粗段のPCGは35回）回すので、rankあたり1 stepに約14,000回の送信と約1,600回の大域和があります。IMBで1回の大域和（8バイト、512 rank）は約12 µsなので、1 stepで約0.02 sです。
- ファイルI/Oは計測区間の0.01%、OSのノイズ（割り込みの処理）は各コアの時間の0.8%です（#46）。
- 寄与を%で言えるのは、時間の内訳（CrayPAT、OpenFOAM profiling）と実験からです。ASPIRE-2AではuncoreのカウンタもIBSも読めず、VTuneのtop-downのような分け方はできません（Q38）。

### 4. MPI calls on 4 nodes（0:45）

表は2つで、同じ枚に左右に並べます（ユーザー、11/02：表を2つに割る。よく呼ばれる呼び出しの時間も書く。時間が合計かrankあたりかを明記する）。

表の注釈（左）：Table 2. The three MPI calls made most often, summed over the 512 ranks.

| Call | Calls, all ranks | Time, all ranks |
|---|---:|---:|
| MPI_Isend | 290 M calls | 839 s |
| MPI_Irecv | 290 M calls | 167 s |
| MPI_Test | 289 M calls | 24 s |

表の注釈（右）：Table 3. The three MPI calls that took the most time, summed over the 512 ranks and per rank.

| Call | Time, all ranks | Time per rank | Share of MPI |
|---|---:|---:|---:|
| MPI_Waitall | 22,069 s | 43.1 s | 55% |
| MPI_Allreduce | 14,140 s | 27.6 s | 35% |
| MPI_Bcast | 1,289 s | 2.5 s | 3% |

表の下の箇条：

- Isend, Irecv and Test exchange halo values with neighbouring subdomains and took little time.
- Waitall and Allreduce wait for other ranks and took 90% of the MPI time.
- With equal cells the fastest rank computed for 1.34 s/step and the slowest for 2.88 s/step.

原稿（約45秒）：This is the result of MPI profiling on four nodes. On the left are the calls made most often. Isend, Irecv and Test exchange halo values with neighbouring subdomains and took little time. On the right are the calls that took the most time. Waitall and Allreduce wait for other ranks and took 90 percent of the MPI time. With equal cells, the fastest rank computed for 1.34 seconds per step and the slowest for 2.88, and the others waited for the slowest. So we asked why ranks with the same work were so different.

訳：これは4ノードで実行したときのMPIプロファイリングの結果です。左は、呼び出し回数が多かったものです。Isend、Irecv、Testは隣のサブ領域と境界の値（halo）を交換する呼び出しで、時間はわずかでした。右は、最も時間のかかった呼び出しです。WaitallとAllreduceは他のrankを待つ呼び出しで、MPIの時間の90%を占めました。セル数は同じなのに、最も速いrankは1 stepに1.34秒、最も遅いrankは2.88秒計算していて、ほかのrankは最も遅いrankを待っていました。そこで、同じ仕事のrankがなぜこれほど違うのかを調べました。

想定質問：Q2、Q29、Q28、Q40
補足：29（Is the network the bottleneck?）

メモ：
- 11/02の4回目（ユーザーの訳）：スライドから中央値（1.96 s）を外し、原稿では40 stepであることと、右の表が全rankの合計とrankあたりであることを言いません（表の見出しと注釈にはあります）。最速と最遅の値は「s/step」で書きます（3枚目の「3.650 s/step」の手直しに合わせた）。
- ユーザーの質問「timeは各rankのtotal？」への答え：表の「all ranks」は512 rankの合計です（CrayPATのrankあたりの平均×512。43.1026 × 512 = 22,069）。ISC26の課題（Task 3）の「total CPU time consumed」に合わせました。1つのrankの値は右の表の「Time per rank」です（Waitall 43.1 s）。ただし、CrayPATの計測区間はプロセス全体（メッシュの読み込み、準備、40 step）で、40 stepだけではありません（プロセスの時間はrankあたり169.57 s、40 × 3.850 = 154 s）。
- よく呼ばれる3つの時間（rankあたり）：Isend 1.639 s（MPIの2.1%）、Irecv 0.326 s（0.4%）、Test 0.047 s（0.06%）。時間の上位3つの回数（rankあたり）：Waitall 52,933回（合計27.10 M）、Allreduce 63,085回（32.30 M）、Bcast 1,219回（0.62 M）。回数の上位3つはrankあたり566,107回（Isend、Irecv）と563,646回（Test）です。
- 最速と最遅（ユーザー、11/02：中央値と最遅ではなく、最速と最遅で）：OpenFOAM profiling（38219862855、全512 rank、40 step）の、rankごとの計算時間（ループの時間からPstreamを引いたもの）の最小53.63 s、中央値78.56 s、最大115.02 sを40で割った値です。最遅は最速の2.1倍、中央値の1.46倍です。セル数の差は最大でも平均の+0.002%です。
- 「most ranks waited for the slowest」：大域和のたびに全rankがそろうので、1 stepは最も遅いrankで決まり、ほかのrankはその差だけWaitallとAllreduceで待ちます。rankごとのMPIの時間は35〜112秒でした。
- APACのルールもMPIのプロファイルを強く勧めています（`tasks/2. OpenFOAM HPC Task Rules.md`の「MPI profiling and analysis are strongly recommended.」）。ISC26の課題（Task 3）も同じです。Baselineの値を見せるのは、手を入れる前のアプリケーションを測るのが自然だからです。Basicの後の同じ表は11枚目です。
- 次の枚へのつなぎ（11/03から）：同じセル数なのに遅いrankがいる → まずrankがどこで動いているかを確かめる（5枚目、固定）。第8版の2回目〜6回目は、ここから分割（最も一般的な手）へつないでいました。
- 40 step：理由は聞かれたら答えます（Q28）。
- 「subdomain」は、分割したメッシュのうち1つのrankが受け持つ部分です。

### 5. CPU and memory pinning（0:45）

スライド：左にノードのアイコンの図（Figure 3。CPU 0とCPU 1、それぞれ4つのNUMA領域、各領域に16コアと2本のメモリチャネル。1つのrank（紺のコア）から、自分の領域のチャネル（local memory、緑のチャネルと黒の矢印）と、もう一方のCPUの領域のチャネル（remote memory、灰色の矢印）へ。CPUは紺、メモリは緑で分ける）。右に4つの段（ユーザー、11/02：なぜ固定するのかから話す。文は短く）。11/03から、Basicの最初の手です（ユーザー：固定されていないと分かっていて、固定すれば速くなると予想できたので先にやった、という話がきれい）。

- Expected：A rank that stays on one core keeps its data in the memory of its own NUMA domain, the closest.
- Found：During the solve no rank stayed on its own core and only 9% of its memory was local.
- Cause：The launcher had bound each rank but MPI_Init removed the binding.
- Fixed：numactl binds the memory before each rank starts and a watcher re-pins the rank with taskset.

原稿（約45秒）：A rank's speed depends first on where it runs. A node has two CPUs of four NUMA domains, each with sixteen cores and two memory channels. A rank that stays on one core keeps its data in its own domain's memory, the closest, so pinning usually makes a memory-heavy code faster and its runs repeatable. But /proc of every rank during the solve showed that no rank stayed on its own core, and only 9 percent of its memory was local. MPI_Init had removed the launcher's binding. Now numactl binds the memory before each rank starts, and a watcher re-pins the rank with taskset.

訳：rankの速さは、まずどこで動くかで決まります。1ノードには、4つのNUMA領域を持つCPUが2つあり、各領域は16コアと2本のメモリチャネルでできています。1つのコアに留まるrankは、自分のデータを自分の領域のメモリ、つまり一番近いメモリに置いたまま使えるので、固定すれば、メモリをよく使うコードは速くなり、runごとの結果もそろうのがふつうです。ところが、実行中に全rankの/procを読むと、どのrankも自分のコアに留まっておらず、自分の領域にあるメモリは9%だけでした。MPI_Initが、launcherのかけた固定を外していたのです。今は、numactlが各rankの起動前にメモリを縛り、見張りのプロセスがtasksetでrankを固定し直します。

想定質問：Q17、Q41、Q27、Q40
補足：30（Pinning and decomposition）、25（Build, MPI and run settings）

メモ：
- 流れ（ユーザー、11/03）：固定されていないと分かっていて、固定すれば速くなると予想できたので、分割より先に直した、という順です。実際の順も同じです。ASPIRE-2Aでは最初からscotchで流していましたが（玄界とGadiの経験から）、9/20〜21に2ノードのrunの配置の記録で、MPI_Initの後に全rankが256 CPUに広がることを見つけ（`TASK_2a.md`）、LD_PRELOADでMPI_Initの直後に固定し直すinterposerで直しました。分割を測って比べたのは、その後です（#36、10/02）。10/02〜03（#36 A3）に、Basicでは使えないLD_PRELOADを外す方法を探して、scotchで4通りの固定を測り（次の枚）、numactl＋見張りを採りました。第8版の2回目〜6回目は、分割を先にしていました（分割はOpenFOAMで最も一般的な手、というユーザーの11/02の案）。
- Foundの数値：私たちのBaseline（hierarchical、固定なし、#62、38219862855）の`/proc`で、solverの実行中に自分のコアに固定されていたrankは0/512、自分のNUMA領域にあるページはrankの中央値で8.7%でした（8領域に均等に散れば12.5%）。scotchで固定なしのrun（#36 A3、37131371136）でも0/128、7%です（第8版の6回目までは、scotchの7%を書いていた）。頼んだ配置と、実行中の`/proc`で見た実際の配置を分けて確かめたことが、この発見の要点です。
- やさしい説明：NUMAと固定（11/01、ユーザーの質問から）：
  - ノードの中の階層：1ノードにCPU（ソケット）が2つあり、1つのCPUは4つのNUMA領域に分かれています（ノードで8つ）。1つのNUMA領域は、16コアと、そこに直結した2本のメモリチャネル（DRAM）の組です。L3（32 MB）は8コアずつで共有するので、1つの領域に2つあります。ノード全体では128コアに16チャネル（理論409.6 GB/s、STREAM約279 GB/s）で、1つの領域では16コアが2本（理論51.2 GB/s、STREAM約35 GB/s）を分け合います。
  - どのコアもノードの全メモリを読めます。ただ、自分の領域のDRAMは近くて速く、ほかの領域のDRAMはCPUの中の接続（もう一方のソケットならソケット間の接続も）を通るので遅く、ほかの領域の帯域も食います。図の黒の矢印（local）と灰色の矢印（remote）がこれです。
  - コアを固定する：rankを特定のコアに縛り、OSに別のコアへ動かさせないことです。動かされると、L1、L2、L3に載っていたデータが使えなくなり、別の領域へ動けば自分のデータが遠いメモリに残ります。2つのrankが同じコアに乗って、片方が待つこともあります。
  - メモリを固定する：rankのデータを、どの領域のDRAMに置くかを決めることです。Linuxは既定で、ページに最初に書き込んだときに動いていたコアの領域にそのページを置き、後からは動かしません（first touch）。今回は固定が外れてrankが動き回るうちにデータを書いたので、ページが8つの領域に散らばり、自分の領域にあるのは9%だけでした。`numactl --membind`は、rankが動き出す前に「この領域のDRAMにだけ置く」と決める指定です。
  - コアとメモリの両方を固定して初めて、rankは自分の領域の近いDRAMから読み続け、自分のデータをL1〜L3に載せたまま使い続けられます。片方だけでは速くならなかったことは、次の枚（scotchでの4通りの比較）にあります。
  - 誰が何を決めるか（MPIはOpen MPIではなくCray MPICHです）：メッシュ → rankはOpenFOAMの分割（decomposePar）が決め、サブ領域 i をrank i が解きます。rank → コアは、ランチャー（PALSの`mpiexec --cpu-bind`）の固定と、見張りの`taskset`での戻しが決めます（1ノード128 rankで、ノードの中ではk番目のrankがk番のコア）。コア → メモリは、`numactl --membind`でそのコアのNUMA領域のDRAMに置きます。L3はキャッシュなので割り当てるものではなく、コアを固定すれば、そのコアの組のL3を自動で使います。
  - この3つがつながるので、サブ領域 i → rank i → コア → NUMA領域 → そのDRAM と決まります。8枚目の「ノードの木」は、面を多く共有する隣どうしのサブ領域に、同じ領域、同じソケット、同じノードに乗る番号を振る工夫です。
- 固定が外れた原因：診断ジョブ（PBS 24944881、2ノード、256 rank）で、全rankが`MPI_Init`の直前は1 CPUに固定され、直後は256 CPUに広がっていました。サイトの推奨どおりの書き方（`--cpu-bind depth -d 1`）でも、既定のOFIでもUCXでも同じでした（`TASK_2a.md`）。サイトのMPI（PALSとCray MPICH）のどこが外すのかまでは突き止めていません。
- numactlが効く理由：exec前に設定したメモリの方針はプロセスのもので、`MPI_Init`は外しません。見張りは`run/keep-rank-affinity.sh`で、各ノードに1つ置き、`simpleFoam`のプロセスが現れたらすぐ、そのlocal rankのコアに`taskset`で戻します。全ジョブのログで、各ノード128/128 rankが固定されています（REPORT §6.1）。
- `LD_PRELOAD`はBasicでは使えないので、ジョブスクリプトだけでできる形にしました（F1：job script、rank placement、affinity。Q17）。
- 両方固定した後、自分の領域にあるメモリは58%です（domainsを入れる前のBasicで、ノード0の128 rankを`/proc`で見た中央値）。100%にならないのは、共有ライブラリやMPIの共有バッファのように複数のrankが使う部分は1つの領域にしか置けないためと考えていますが、確かめていません。
- 主催者のASPIRE-2Aのノートには固定の話がなく、主催者の参照runも固定していません。同じ機械を使うチームとの一番の差です（Q27）。

### 6. Pinning results（0:45）

スライド：左に3行、右に図（Figure 4、`deck/deck_plots.py`の`p10_pinning`）。図は1つの軸に、hierarchical（Baselineの分割）のNeither（固定なし）とCPU and memory（両方の固定）、scotchのNeither、CPU only、Memory only、CPU and memoryの各ジョブを並べ、原点0から波線で省略します。各分割のNeitherからCPU and memoryへの矢印と%（−11.2%、−14.1%）は図形で重ねます。注釈は「Each job under each placement of the ranks on 4 nodes, with hierarchical and with scotch.」。ユーザー、11/03：hierarchicalで固定の実験をしていたらすごく良かったかも（#36にあった）。11/02の2回目：scotchでの4通りの図は各実験の結果を示せてよい。両方を1つの図にしました。

- Pinning both took 11.2% off a step with hierarchical and 14.1% with scotch.
- Pinning only the CPU or only the memory did not help.
- Pinned jobs varied less, so smaller gains could be seen.

原稿（約45秒）：We measured the pinning first on the Baseline's decomposition, hierarchical, where pinning both the CPU and the memory took 11.2 percent off a step. We also pinned each half alone on scotch, the decomposition we come to next. Pinning only the CPU came 12 to 16 seconds after each rank started, when its memory was already placed, and pinning only the memory let the rank move away from it. Only both together helped, here by 14.1 percent. The pinned jobs also varied less, so our rule could see smaller gains.

訳：固定は、まずBaselineの分割、hierarchicalで測りました。CPUとメモリの両方を固定すると、1 stepが11.2%短くなりました。次の枚で扱う分割、scotchでは、片方ずつの固定も測りました。CPUだけを固定すると、各rankが起動してから12〜16秒後で、そのときにはメモリはもう置かれていました。メモリだけを固定すると、rankがメモリから離れて動いてしまいました。両方を固定したときだけ効き、ここでは14.1%短くなりました。固定したジョブはばらつきも小さく、私たちの決まりでより小さな改善まで確かめられるようになりました。

想定質問：Q41、Q15、Q17、Q27
補足：30（Pinning and decomposition）

メモ：
- 図（11/03）：hierarchicalの2つは#36（10/02）の同じ時期の3本ずつで、固定なしは`data/start_unpinned.csv`（3.6983、3.5850、3.7270。3.670、SD 2.0%）、固定ありは`data/decomposition_basic.csv`のhierarchical 4ノード（3.2912、3.2593、3.2217。3.257、SD 1.1%）。範囲は重なりません。このときの固定はLD_PRELOADでMPI_Initの直後に固定し直す方法で、Basicのnumactl＋見張りと同じ速さです（scotchで2.919と2.917）。scotchの4つは`data/pinning.csv`（#36 A3、10/03）。図と表には日付を書きません。第8版の最初の版の本編の図（Baselineと、hierarchicalの固定なし・あり）は補足30枚目にありましたが、11/03にその比較を本編のこの図に入れ、補足30枚目は固定と分割の掛け合わせの枚にしました。scotchの4通りの時間の表は、時間が図にあるので外しました。
- scotchの4通りの中身：Neither＝PALSの`--cpu-bind`と`--mem-bind`だけ（MPI_Initで外れる。solve中の固定は0/128、自分の領域のページ7%）。CPU only＝見張りの`taskset`だけ（起動12〜16秒後に固定し直す、128/128）。Memory only＝`numactl --membind`だけ（0/128、57%）。CPU and memory＝`numactl --membind`＋見張り（128/128、58%、Basicで採用）。時間はNeither 3.395（2本、SD 0.78%）、CPU only 3.474（3本、SD 2.0%）、Memory only 4.380（1本）、CPU and memory 2.917（3本、SD 0.13%）。同じファイルに、LD_PRELOADの固定（2.919 s、2本）と、PALSの`--mem-bind`＋見張り（3.469 s、2本、40%）もあります。
- CPU onlyがNeitherより速くならなかった理由（平均は2.3%遅いが、範囲はわずかに重なる）：見張りが固定し直すまでの数秒（メッシュの読み込みとfieldの確保）に、ページが別のNUMA領域に置かれ、そのまま残るからと考えています（#36。最初の25 stepから遅い）。Memory onlyは、メモリは自分の領域にあるのにrankが別のコア（別の領域）へ動くので、ほぼすべての読み書きが遠いメモリになります（Neitherより29%遅い）。
- ばらつき（ユーザー、11/02の1回目：固定でSDが小さくなることも話す）：Baseline 4.1%、hierarchicalの固定なし2.0% → 固定あり1.1%、scotchのNeither 0.78%（2本）→ 両方0.13%。固定したscotchの29本（4ノード、10月初め）のSDは0.19%です。固定が外れていると、遅いrankがrunごとに違う場所に出るので、ジョブのばらつきが大きくなります。2枚目の決まり（全ジョブが対照より速い）は、ばらつきが小さいほど小さな改善を通します（SDの3倍の改善が3対3で89%通る）。
- 固定と分割の関係（Q41、補足30枚目）：固定なしでscotchは7.5%、固定ありで10.5%短くし、固定はhierarchicalで11.2%、scotchで14.1%短くしました。互いに相手の効果を大きくしています。最も遅いrankの計算は、中央値の1.46倍（固定なし、Baseline）→ 1.16倍（固定あり、hierarchical）→ 1.06倍（固定あり、scotch）です。固定なしのscotch対hierarchicalは交互ではない（10/02と10/03）ので、原稿では言いません。
- ユーザーの質問（11/02の1回目）「NeitherはBaselineより速い。裏で何か最適化した？」への答え：していません。scotchのNeitherはscotch（固定なし）、Baselineはhierarchical（固定なし）で、その差は分割です（補足30枚目の−7.5%）。

### 7. Decomposition（0:50）

スライド：左に、ケース既定の分割とscotchを`decomposeParDict`の書き方で示し（ユーザー、11/02の2回目：multiLevelやscotchのdomainsはOpenFOAMの文法で示した方が分かりやすい）、その下に各ジョブの図（Figure 5）。右にhierarchicalとscotchの分割の絵（Figure 6、ノードとNUMA領域ごとの色）と、その下に色の凡例。11/03から、固定した後の枚です（ユーザー：固定が先）。

左上の見出しとコード：

- The case default, as in our Baseline：`method  hierarchical;`、`hierarchicalCoeffs { n (16 8 4); }`
- The decomposition we kept：`method  scotch;`

図（左下、Figure 5）：`deck/deck_plots.py`の`p05_decomposition`。どちらも固定したhierarchicalとscotchの各ジョブ（#36、交互に3本ずつ）、原点0から波線で省略した軸、矢印と%（−10.5%、図形）。目盛りに分割の名前とサブ領域の間の面の数（4.31 M、2.93 M）。注釈は「Each job of the two decompositions, both pinned, on 4 nodes, with the faces between subdomains.」

凡例（絵の下）：node 1〜4の名前の下に、それぞれ8つのNUMA領域の濃淡。

原稿（約50秒）：With every rank pinned, the slowest ranks were those whose subdomains held more work. Our Baseline used the case default, hierarchical, which cuts the mesh into 16 by 8 by 4 slabs of equal cells. The pictures colour each subdomain by node and NUMA domain. The ranks whose slabs held much of the car's surface computed more. scotch instead cuts the mesh as a graph, with as few faces between subdomains as possible. It kept the cells within about 1 percent of equal, and as the figure shows, it had 32 percent fewer faces between subdomains and took 10.5 percent off a step.

訳：すべてのrankを固定すると、最も遅いrankは、サブ領域に仕事を多く含むrankになりました。私たちのBaselineは、ケース既定のhierarchicalで、メッシュを16×8×4の、セル数の等しい板に切ります。絵は、各サブ領域をノードとNUMA領域ごとに塗ったものです。車の表面を多く含む板を受け持つrankは、計算が多くなりました。scotchは、代わりにメッシュをグラフとして、サブ領域の間の面ができるだけ少なくなるように切ります。セル数の差を約1%以内でそろえたまま、図のとおり、サブ領域の間の面を32%減らし、1 stepの時間を10.5%短くしました。

想定質問：Q19、Q4、Q30、Q21、Q41
補足：31（Hierarchical against scotch）、33（Decompositions we tried）、30（Pinning and decomposition）

メモ：
- 11/03（ユーザー：固定が先）：図を、固定なしの2つ（Baselineと#36 A3のNeither、交互ではない、−7.0%）から、固定した2つ（#36、交互に3本ずつ）に替えました。これで、2枚目の決まり（交互に流す）から外れる比較が本編からなくなりました。見出し「The first change we tried」は「The decomposition we kept」にしました。
- 図の時間：`data/decomposition_basic.csv`の4ノード。hierarchical 3.2912、3.2593、3.2217（3.257、SD 1.1%）、scotch 2.9154、2.9227、2.9054（2.915、SD 0.30%）、範囲は重なりません。固定はLD_PRELOAD（Basicのnumactl＋見張りと同じ速さ）。1/2ノードでは−1.3／−2.5%です（補足31枚目、Q30）。ノード数が多いほど効く理由は確かめていません。
- 1文目の根拠：固定したrunで、rankごとの計算時間の最大/中央値がhierarchicalで1.16、scotchで1.06でした（CrayPATの（プロセス − MPI）、#38、37181991433、37176272426、37182420190）。hierarchicalの偏りは、壁の面（車の表面）の数と相関しました（#38）。固定なしのBaselineでは1.46で、置き場所による偏りが上乗せされていました（補足30枚目）。
- scotchの分け方（ユーザーの質問、11/02の4回目「面の接触数を減らすように分割する方法？」）：はい。scotchはメッシュをグラフ（セルが点、隣り合うセルの共有面が辺）として分割し、各部分のセル数をほぼそろえる条件の下で、切る辺の数、つまりサブ領域の間の面の数をできるだけ少なくします（ここでは最大のサブ領域が平均の+1.07%）。hierarchicalは座標の方向に順に切るだけで、面の数は見ません。
- 分割はOpenFOAMの高速化で最も一般的な手で、Task Rulesも「Decomposition (try this first): method, number of MPI ranks, and the settings for that method. Compiler flags and MPI tuning will not fix a bad decomposition.」と書いています。ASPIRE-2Aでは最初からscotchで流していました（玄界とGadiの経験から）。ケース既定のhierarchicalは公式の基準として後から測り（#34、9/24）、2つを比べたのは固定の後です（#36、10/02）。
- 面の数とサブ領域の大きさ：`decomposePar.log`から（Boxの`presentation/openfoam/decomposition/README.md`）。hierarchicalは431万面、最大のサブ領域は平均の+0.002%。scotchは293万面（−32%）、最大+1.07%。
- 絵：Boxの`decomposition-numa.png`（#39、10/09、`decomposePar -cellDist`、セル数と共有面の数は計測runの`decomposePar.log`と全部一致）。色はノードを色相（青、橙、緑、紫）、ノードの中の8つのNUMA領域を濃淡で分けています（rank rはノードr // 128、NUMA領域(r // 16) % 8）。scotchの列はdomains (2 4 16)を入れる前のplain scotchで、この図のscotchと同じ分け方です（ユーザーの質問「numaごとのdecompositionの画像はdomain(2,4,16)のあと？」への答え：前です。照合したのは10/05ごろのBasicの4ノードrun 37202026690で、domainsはまだ入っていなかった）。domainsを入れたscotchの絵は11/02に玄界で作り、14枚目にmultiLevelと並べて載せました（分割は計測runと全部一致。Boxの`decomposition-numa-scotch-domains-vs-multilevel.png`、`decomposition/README.md`）。
- 凡例：Boxの絵の下にある凡例と同じ色を、PowerPointの図形で描いています（`decomposition/render.py`のノードの色相、青、橙、緑、紫と、NUMA領域ごとに45%暗い色から45%明るい色までの8つの濃淡。`build_deck.py`の`numa_key()`）。node 1がrank 0〜127です。
- 分け方：hierarchical (16 8 4)は、x方向に16、y方向に8、z方向に4つ、セル数が等しくなるように平らに切ります。`hierarchicalCoeffs`には`delta 0.001`と`order xyz`もありますが、スライドでは`n`だけにしました（既定の値）。
- ISC26の課題（Task 5）の「分割方法を変えて、性能への効果を示す」に当たります。試した分割の全部は補足の33枚目です。

### 8. Scotch on the node tree（0:45）

スライド：左に`decomposeParDict`の`scotchCoeffs`（ユーザー、11/02の2回目：scotchのdomainsはOpenFOAMの書き方で示す）と表（Table 5）、右に図（Figure 7）。

左上の見出しとコード（decomposeParDict of Basic）：

```
method  scotch;
scotchCoeffs
{
    domains        (2 4 16);
    domainWeights  (0.125 0.0625 0.015625);
    strategy       "…";
}
```

表の注釈（表の上）：Table 5. The tree that domains describes, with its faces against plain scotch.

| Between two | Cost | Faces |
|---|---:|---:|
| nodes | 64 | −22.7% |
| sockets | 8 | −21.3% |
| NUMA domains | 4 | −10.4% |
| cores | 1 | +3.3% |

図：plain scotch（灰）とdomainsを入れたscotch（黄）の各5本、原点0から波線で省略した軸、矢印（−0.7%）。注釈は「Each job of plain scotch and of scotch mapped onto the node, both pinned, on 4 nodes.」

原稿（約45秒）：Then we told scotch about the node. In decomposeParDict, domains describes a node as two sockets of four NUMA domains of sixteen cores, and OpenFOAM adds the four nodes on top. The weights make a face between two nodes cost 64 times one between two cores, as the table shows, so scotch keeps subdomains that share many faces close together. The strategy keeps the cells within 1 percent of equal. Faces between nodes, sockets and NUMA domains fell by 10 to 23 percent, while all faces rose by 3 percent. Against plain scotch, this took another 0.7 percent off a step.

訳：次に、scotchにノードの形を教えました。decomposeParDictで、domainsは1ノードを「2つのソケット、各4つのNUMA領域、各16コア」と表し、OpenFOAMがその上に4つのノードを足します。表のとおり、重みによって、2つのノードの間の面は、2つのコアの間の面の64倍の重さになるので、scotchは面を多く共有するサブ領域どうしを近くに置きます。strategyは、セル数を1%以内でそろえます。ノード、ソケット、NUMA領域の間の面は10〜23%減り、面の全体は3%増えました。比べると、これで1 stepがさらに0.7%短くなりました。

想定質問：Q10、Q4、Q30
補足：33（Decompositions we tried）

メモ：
- 11/02の4回目（ユーザー）：「交互に流して」は2枚目で言っているので言いません。図の注釈からも「alternated」を外しました（比較は5対5の交互です）。
- 中身（ユーザー、11/02の2回目）：`run/prepare.pbs`がBasicのときに書く`scotchCoeffs`そのままです。`strategy`の中身は長いので「…」にしました（全文は`submission/openfoam/run/prepare.pbs`）。Scotch 6.1が既定で組み立てる戦略（`SCOTCH_stratGraphMapBuild`、512分割、偏りの許容0.01）に、`SCOTCH_STRATBALANCE`の項（最後の厳密な均衡化`x{bal=0.01}`など）を足しただけです。偏りを抑えたのは、計算時間がセル数でほぼ決まり、偏ると遅くなったからです（#37、#45）。domainsとdomainWeightsだけの版は−0.66%、strategyを足して−0.82%でした（#38）。
- 仕組み：未改変のv2512の`scotchDecomp`は、`domains`と`domainWeights`から木構造の対象アーキテクチャ（Scotchのtree-leaf）を作り、分割をその木へ写します（`scotchDecomp.H`に使い方）。`domains`の積（128）が`numberOfSubdomains`（512）より小さいので、重み1の最上段（ノード）が自動で加わります。重みは整数に直され、512 rankではリンクの重みが「ノード64 / ソケット8 / NUMA 4 / コア1」になります（#38。整数への変換が切り捨てなので、2進で正確に表せる値にした）。表の「Cost」はこれです。分割した後に割り当て直すのではなく、1回の分割の中で、面を多く共有する塊どうしを同じノード、ソケット、NUMA領域に入れます（ユーザーの言う「scotchでdomainごとに分ける」）。
- 面の数（REPORT §6.3、`decomposePar.log`から、plain scotchに対して）：ノード間−22.7%、ソケット間−21.3%、NUMA領域間−10.4%、コアの間（サブ領域の間の全部の面）+3.3%。1つのサブ領域の隣の数の最大は66 → 40です。
- 図：#63の5対5（交互）。対照（plain scotch）2.918 s（SD 0.22%）、候補2.898 s（SD 0.07%）で、全runが対照より速く、2枚目の決まりを通りました（2枚目の図のKeptと同じデータ）。1・2ノードではほぼ変わりません（+0.29%、+0.07%、#38）。
- Basicの範囲であること：分割の方法はscotchのままで、その係数（`scotchCoeffs`）を変えるだけです（F1、Q10）。
- 絵：domainsを入れたscotchの分割の絵は、11/02に玄界で作りました（7枚目の絵は入れる前のplain scotch）。分割は計測runと全部一致し、multiLevelと同じ画角と色で並べた絵がBoxの`decomposition-numa-scotch-domains-vs-multilevel.png`にあります（`decomposition/README.md`の「玄界での作り直し」）。デッキでは14枚目にmultiLevelと並べて載せました（11/02の4回目、ユーザー：scotchの絵を更新して載せる）。この枚はコード、表、図で埋まっているので載せていません。
- multiLevel（Bonus）との違いは14枚目です。Basicで採用したのは、scotch、固定、ノードの木の3つです。

### 9. Basic results（0:35）

スライド：左上に表、左下に流れの動画（Figure 8、話さない）、右に図（Figure 9）。ユーザー、11/02：公式の結果もプロットする、時間は文ではなく表で、矢印も（2回目に「良くなっている」）。11/03：表を、Bonusの結果と同じ形の段ごとの比較にした（ユーザー：固定もdomainsもBasicの結果の時間に見えて、各段の結果が足りない）。公式の結果の時間は図のラベルにあります。

表の注釈（表の上）：Table 5. Each Basic step against its control on 4 nodes.

| Step | s/step | Change |
|---|---:|---:|
| CPU and memory pinning | 3.670 → 3.257 | −11.2% |
| scotch instead of hierarchical | 3.257 → 2.915 | −10.5% |
| scotch mapped onto the node | 2.918 → 2.898 | −0.7% |
| Basic against our Baseline | 3.650 → 2.898 | −20.6% |

図：公式の結果2本（hierarchicalは白抜き、scotchは灰色）、Baselineの3本、Basicの5本。原点0から波線で省略した軸。BaselineからBasicへの矢印と%（−20.6%、図形）。

原稿（約35秒）：With these three changes, Basic took 2.898 seconds per step on four nodes, 20.6 percent less than our Baseline. The table gives each step against its own control, 11.2 percent for the pinning, 10.5 for scotch and 0.7 for the mapping. The figure also shows the official runs, which used the site's module without pinning. Basic was 15 percent faster than the faster of them, and the spread between identical jobs fell from 4.1 to 0.07 percent.

訳：この3つの変更で、Basicは4ノードで1 step 2.898秒になり、私たちのBaselineより20.6%短くなりました。表は、各段をそれぞれの対照と比べたもので、固定で11.2%、scotchで10.5%、対応付けで0.7%でした。図には公式の結果も載せています。サイトのモジュールで、固定なしで流したものです。Basicはその速いほうより15%速く、同じジョブどうしのばらつきは4.1%から0.07%に小さくなりました。

想定質問：Q15、Q22、Q27、Q18
補足：27（The organisers' reference）、28（Reproducing our results）、30（Pinning and decomposition）

メモ：
- 表の各行（11/03）：固定は#36のhierarchicalの固定なし（3本）と固定あり（3本）、scotchは#36の固定したhierarchicalとscotch（交互に3本ずつ）、対応付けは#63の5対5、最後の行は時期の違うBaseline（#62、10/12）とBasic（#63、10/15〜16）です。各段を掛け合わせると3.650 × 0.888 × 0.895 × 0.993 ≈ 2.88で、実際の2.898との差（約0.6%）は時期の違いです。表のJobsの列は、図で本数が分かるので外しています（ユーザー、11/02の4回目）。公式の結果は1本ずつ、Baselineは3本、Basicは5本です。
- 公式の結果（Official）：`tasks/5. Common Baselines.md`（4ノード、サイトの`OpenFOAM/2512`モジュール、ケース既定、Allrun一式を1ジョブずつ、オプションなしのmpirun、固定なし）。Basicは公式のhierarchical（3.415）に対して−15.1%、scotch（3.576）に対して−19.0%です。
- ユーザーの質問（11/02）「officialはpinされていなくて、scotchが遅くなっている？」への答え：はい、公式の結果は固定していません。そのうえ1ジョブずつです。主催者のscotchのジョブは4ノードで12%もばらついている（補足の27枚目）ので、1本ずつではhierarchicalとscotchのどちらが速いかは決められません。固定した私たちの交互の比較では、scotchがhierarchicalより10.5%速かった（7枚目、補足31枚目）。
- 流れの動画は、見せるだけで原稿では触れません。玄界で流した可視化用のrun（未改変v2512、4ノード448 rank、scotch、150反復。Boxの`presentation/openfoam/flow/README.md`）で、ASPIRE-2AのBasicのrunではありません（Q22）。デッキでは、この枚を入力の2枚目（動画のあった枚）の上に作るので、動画の自動再生の設定がそのまま残ります。
- ばらつきが小さくなった理由：遅いrankがrunごとに違う場所に出るのは、固定が外れていたときの症状です（#36）。固定だけを戻したhierarchicalでSDは1.1%、固定したscotchで0.13〜0.3%（6、7枚目）、ノードの木に写したBasicで0.07%になりました。
- Basicで採用したのは、固定、scotch、ノードの木への対応付けの3つだけです（5〜8枚目）。自分たちのビルド（GCC `-O3`、AOCL-LibM）、UCX、ノードのローカルディスクへのケースの配置は、Baselineからすでに同じです。
- 出典：Baselineは#62（10/12）、Basicは10/15〜16の5本（#63）。

### 10. What did not help in Basic（0:30）

スライド：表と1行（ユーザー、11/02：+−ではなく、何%悪化・改善と書く。やって効かなかったことを全部見せ、印象的なもの（直感に反するもの、一般には速くなるはずのもの）を強調して説明する。Basicで効かなかったものはBasicの結果のあたりで話す）。紺の行は、効きそうだと思った手です（11/02の4回目のユーザーの言い方）。11/03から、Basicの最後の枚です（ユーザー：Basicの範囲で効かなかったものはBasicの最後に。Basicの後のMPIは、Bonusへ向かうプロファイルで見せる）。

表の注釈（表の上）：Table 6. Each Basic idea we tried and did not keep, with its time per step against its control on 4 nodes.

| Idea | Time per step |
|---|---|
| Compiler flags -march=znver3, -O2 and LTO | no change, at most 0.1% slower |
| AMD compilers AOCC 5.0 and AOCL 5.1 | no change, within 0.1% |
| GCC profile-guided optimisation | 0.1% slower |
| UCX over RC with 55% more network bandwidth | no change, within 0.1% |
| Rank reordering with 92% fewer faces between nodes | 0.1% slower |
| Default OFI transport with the organisers' workarounds | 0.8% slower |
| OpenFOAM's communication switches | no gain, and one crashed |
| glibc malloc thresholds | 0.4% faster, within the spread |
| Two ranks per core (SMT) | 5.7 times slower |

- Network changes cannot shorten the wait for the slowest rank.

原稿（約30秒）：These are the Basic ideas we tried that did not help, and the ones in blue are those we expected to help. No compiler setting changed a step by more than 0.1 percent. Fifty-five percent more network bandwidth and 92 percent fewer faces between nodes changed nothing either, because the ranks waited for the slowest rank, not for data.

訳：Basicの方法で試したものの、効かなかったものを示します。紺の行は、効きそうだと思ったものです。コンパイラの設定はどれも1 stepを0.1%も変えませんでした。ネットワークの帯域を55%増やしても、ノード間の面を92%減らしても、何も変わりませんでした。rankが待っていたのはデータではなく、最も遅いrankだったからです。

想定質問：Q43、Q2、Q16、Q29、Q39
補足：25（Build, MPI and run settings）、29（Is the network the bottleneck?）、43（Other renumberings on Genkai）

メモ：
- コンパイラ（ユーザー、11/03）：Basicの範囲では結果だけを言い、理由（ループが命令ではなくメモリを待っている）は、メモリに取り組むBonusの側、13枚目で言います（ユーザー：メモリにアプローチしていたのはBonusなので、考察はBonusの後で）。第8版の6回目までは「the profile on the next slide shows why」と言い、12枚目で理由を言っていました。聞かれたらQ43で答えます。renumberMeshは原稿から外しています（下の項目、Q39）。
- renumberMeshを変えなかったこと（ユーザー、11/02の4回目：変えなかったことを聞かれそう。効果がなかった根拠はある？効きそうなものはある？やっていないのはマイナスの印象。Basicで変えられないのか問題文を確かめて）。自分からは言わず、聞かれたらQ39で答えます：
  - 問題文：Basicでは変えられません。Task Rulesの補遺F1（l.204）「`renumberMesh -constant -overwrite -parallel` runs exactly as written, with its default method. Adding `-dict`, `-renumber-method`, or `-renumber-coeffs` is Bonus work.」、FAQ（l.262）「Can I add `-dict` to `renumberMesh`? Not in Basic. Yes in Bonus.」。Allowed Optimizationsの「Mesh renumbering: Use of official v2512 `renumberMesh`」（l.70）は公式のrenumberMeshを使うことで、どう流すかは補遺F1が決めています。Bonusの例にも「Other renumbering methods or options (`-dict`, `-renumber-method`, `blockSize`, `zoltan` …)」（F2）とあります。
  - 効果が小さいと見た根拠：
    - 分割と固定（ユーザーの案、11/03を正確にした形）：4ノードでは各rankが約12万8千セルのまとまった塊を受け持ち、1つの場は約1 MBで、コアあたりのL3（4 MB）より小さいです。固定で、rankは自分のコアのL2とL3、自分のNUMA領域のメモリに留まります。分割が粗い並べ替えの役をしていて、塊が4分の1になる1ノード → 4ノードで、1セル・1 stepあたりのDRAMからのL1 refillは0.70倍になりました（#66、uProf、Basic。19枚目のメモ、補足42枚目）。固定だけでは理由になりません（固定はキャッシュの中身を保つだけで、何が載るかは並びが決める）。
    - 既定ですでにCuthill–McKeeで並べている。Basicの4ノードのログ（Boxの`openfoam/results/4node/renumberMesh.log`）では、band（番号が最も離れた隣どうしの差）が128,811 → 14,165、profile（各セルから、番号が最も離れた隣までの差の和）が2.27e11 → 1.66e11で、1セルあたり3,471 → 2,536です。
    - 面を順に回るループが同時に触るセルは、この約2,500個です。Uとgrad(U)なら約240 KBで、Zen 3のコアごとのL2（512 KB）に収まります。つまり各セルの値は、ループごとにほぼ1回だけDRAMから読まれています。並べ替えで減らせるDRAMの読み込みは、ほとんど残っていません（1 stepの約97%はメモリ帯域に沿う、13枚目）。
    - 玄界で、この課題のケースでほかの並べ方を測りました（11/03、Q39、補足43枚目、`renumber/README.md`）。4ノード、448 rank、40反復を4巡で、既定のCuthill–McKeeに対して、逆順（RCM）−0.19%（3巡で速く1巡で遅い、ばらつきの中）、並べ替えなし+0.70%、spring +3.26%、乱数の順+10.6%でした。どの並べ方も既定より速くはならず、Cdは並べ方ごとに変わりました（40反復目で最大1.3%）。旧課題（cavity3D-64M、1本ずつ）では、なしに対してCuthill–McKeeが+0.91%、ブロック局所のCuthill–McKeeが+0.94%でした。
    - ASPIRE-2Aのプロファイルでは、遅いrankの余分な時間は全部の面のループに散らばっていて、セルの並びを指していませんでした（#40、#41）。
  - Bonusでの注意（11/02深夜に確かめた）：この課題のソルバは、どれも反復回数を固定したGauss–Seidelです（pのGAMGの平滑化、U、k、omegaのsmoothSolver。`fvSolution.fixedIter`）。掃く順番はセルの番号の順なので、並べ替えると毎回の近似解が変わり、Cdも変わります（coefficient.datはビット一致しない）。だから並べ替えはF3の±0.5%の確認が要ります。私たちの変更でも、Gauss–Seidelの更新の順を変えた重ね合わせはCdを1.20%動かし、F3を外れました（20枚目）。分割を変えるだけでも、150 stepのCdは数%違います（公式のhierarchical 0.2739、scotch 0.2840、Basic 0.2930）。
  - 選べる並べ方：v2512の`renumberMesh`は、Bonusなら`-renumber-method`と`-renumber-coeffs`、`-dict`で並べ方を変えられます（`CuthillMcKee`とその逆順の`RCM`、`spring`、`random`、`none`、`structured`（層状のメッシュ向け）、`manual`（番号のファイル）。SloanはBoost、zoltanはZoltanのライブラリが要り、玄界の私たちのビルドにはどちらも入っていない）。`-dict`では`blockSize`（各サブ領域をブロックに分けてから中を並べる）や`sortCoupledFaceCells`（プロセッサ境界のセルを最後にする）も使えます。v2512のソース（玄界のミラーのタグOpenFOAM-v2512）で確かめました。
- renumberMeshの経緯（ユーザーの質問、11/02「renumberMeshってなんかやった？」）：ASPIRE-2Aでは変えても外しても測っていません。全runがAllrunの`renumberMesh -constant -overwrite -parallel`を、既定の方法（Cuthill–McKee）で流しています（Boxの`openfoam/results/4node/renumberMesh.log`：`Using renumber-method: CuthillMcKee [default]`、bandwidthは2.27e11 → 1.66e11）。候補には3回挙げましたが流していません（#37 F3：既定がすでにCuthill–McKeeで、玄界で1%未満、どのプロファイルもセルの並びを指していなかった。#40/#41：遅いrankの余分な時間は全部の面のループに散らばっていた。#69の候補R1（`reverse`、`structured`）は未実施）。11/03に、ユーザーの許可を得て玄界でほかの並べ方を測りました（Q39）。
- 行ごとの数値と出典：
  - コンパイラのフラグ：`-march=znver3` +0.03%、`-O2` +0.02%、LTO +0.13%（3対3、対照と範囲が重なる、`data/compiler_options.csv`、#36 D）。
  - AOCC 5.0／AOCL 5.1：+0.03%（3対3、2枚目の図のNot kept）。
  - GCCのPGO：+0.13%（1ノードで+0.08%、#59）。
  - UCX over RC：IMBの1 MiBのSendrecvが6.7 → 10.4 GB/s（+55%）、1 stepは−0.01%（Basic、4対4、#58）。
  - rankの並べ替え（`MPICH_RANK_REORDER_METHOD=3`、hierarchicalで）：ノード間の面−91.6%、1 stepは+0.1%（3対3、10/02、#36 B）。1つのrankの待ちは自分の計算で決まります（R² 0.77）。
  - 既定のOFI（主催者の回避策`FI_OFI_RXM_USE_SRX=0`）：+0.77%（3対3）、`FI_VERBS_PREFER_XRC=0`は+0.50%（1対1）。Cdは同じ（#56、#60、Q16）。
  - OpenFOAMの通信スイッチ（topoControl、nbx、pbufs）：改善なし。commsType scheduledは落ちた（REPORT §10、gitの`c562b50`）。
  - glibcのmallocの閾値：−0.4%（3本）。ばらつきと区別できず、残していません（Q36）。
  - SMT（1コア2 rank）：中央値で5.7倍遅い。step 2〜22のうち16 stepが11〜28 s、残り5 stepは数分止まった（#43）。原因は切り分けていません。
- 強調した行（紺）：コンパイラの3行、ネットワーク帯域、rankの並べ替え。効きそうだと思ったのに効かなかったもので、ネットワークの理由をスライドの1行と原稿で言い、コンパイラの理由は13枚目で言います。SMTは5.7倍と目立ちますが、原因を切り分けていないので強調しません。
- 理由の根拠：コンパイラ → ループは1バイトあたり約0.1 flopで、メモリを待っている（12枚目、13枚目）。ネットワーク → MPIの時間は転送ではなく、最も遅いrankを待つ時間（4枚目、11枚目）。
- 表の数字の書き方：+−ではなく、slower／faster／no changeで書きます。0.1%未満は「within 0.1%」です（「数値の決まり」）。

### 11. MPI after Basic（0:35）

スライド：4枚目と同じく、左に回数の表、右に時間の表を、どちらもrankあたりでBaselineとBasicを並べ、その下に2行（ユーザー、11/02の4回目：callも書いた方がいい？callも書くならグラフを消すのも1つの方法。最初の版の9枚目と同じ図は外した）。11/03から、Bonusの始まりの枚です（ユーザー：MPIを速くしたのがBasicで、その後メモリが律速というところから始まったのがBonus。Basicの後の枚にBonusの始まり感があってもよい。フッターはいらない）。

表の注釈（左）：Table 7. The MPI calls made most often, per rank, our Baseline against Basic before its node mapping.

| Call | Baseline | Basic |
|---|---:|---:|
| MPI_Isend | 566,107 | 597,033 |
| MPI_Irecv | 566,107 | 597,033 |
| MPI_Test and others | 565,883 | 596,475 |

表の注釈（右）：Table 8. The MPI calls that took the most time, per rank, in the same CrayPAT runs of 40 steps.

| Call | Baseline | Basic |
|---|---:|---:|
| MPI_Waitall | 43.1 s | 10.2 s |
| MPI_Allreduce | 27.6 s | 12.9 s |
| MPI_Bcast | 2.5 s | 1.4 s |
| All MPI calls | 78.3 s | 26.7 s |
| Share of the time | 46% | 19% |

- The most frequent calls stayed the same three, with about 5% more calls.
- The wait in Waitall fell by 76% because the ranks now finish their computation together.

原稿（約35秒）：For the Bonus, we first profiled Basic in the same way as our Baseline. On the left, the calls made most often stayed the same three, with about 5 percent more calls. On the right, each rank's time in Waitall fell from 43 to 10 seconds, and in all MPI calls from 78 to 27. MPI fell from 46 to 19 percent of the time, because the ranks now finish their computation together.

訳：Bonusに向けて、まずBasicを、Baselineと同じ方法でプロファイルしました。左のとおり、最も多く呼ばれる呼び出しは同じ3つのままで、回数は約5%増えました。右のとおり、各rankのWaitallの時間は43秒から10秒に、MPI全体では78秒から27秒に減りました。rankが計算をそろって終えるようになったので、MPIは時間の46%から19%になりました。

想定質問：Q2、Q26、Q21
補足：29（Is the network the bottleneck?）

メモ：
- 1文目（11/03）：「For the Bonus」で始めて、ここからBonusに入ることを言います（ユーザーの案。フッターに段を書くのは、スライドを見れば分かるのでやめた）。
- 回数の表（11/02の4回目）：rankあたりの平均です（4枚目の表は512 rankの合計）。Basicの既定のレポート（Boxの`openfoam/analysis/pat-report-basic.txt`）は、時間の小さい呼び出しを表に出さず、MPI_Testの回数がありません。そこで3行目は、MPIの全部の呼び出しから、Basicのレポートに出る6つ（Isend、Irecv、Waitall、Allreduce、Bcast、Comm_dup）を引いた残りを、両方とも同じ引き方で書きました。Baselineではその565,883回のうち563,646回がMPI_Testで、残りの2,238回はAllgather、Send、Recvなどの準備の呼び出しです（`pat-report-baseline-calls.txt`）。BasicのMPI_Testだけの回数は、ASPIRE-2Aで`pat_report -T`を流し直せば出ます（今は入れない）。回数の増え方は、Isend、Irecvが+5.5%、3行目が+5.4%、MPIの全部の呼び出し（1,815,336回 → 1,907,850回）が+5.1%です（全部の行は、数字が列に収まらないので表から外した）。scotchのサブ領域の方が隣の数が多いためと考えていますが、確かめていません。
- Basicのプロファイルは対応付けの前のものです（CrayPAT 37176272426、#36 A4、10/04、commit 718acb3、plain scotch、numactlと見張りで固定、プロファイラの下で3.063 s/step）。対応付けた（domainsを入れた）Basicのプロファイルはありません。対応付けで4ノードの1 stepは0.7%しか変わらないので、表の見出しにだけ「before its node mapping」と書き、原稿では言いません。
- Basicのrankあたりの値：Allreduce 12.890 s（MPIの48.0%）、Waitall 10.245 s（38.2%）、Bcast 1.412 s（5.3%）、MPI全体26.75 s（137.57 sの19.4%）。回数は左の表のほか、Allreduceが63,129回、Waitallが52,960回です。時間の上位はAllreduceとWaitallの順に入れ替わりました（表の行はBaselineの順のまま）。
- 減り方：Waitallは−76%、MPI全体は−66%。
- 「rankが計算をそろって終える」の根拠：rankごとの計算時間の最大/中央値が、Baselineの1.46（OpenFOAM profiling、38219862855）から、対応付けの前のBasicの1.063（OpenFOAM profiling、37714968610、#57）になりました（固定したhierarchicalでは1.16、補足30枚目）。Basicのrankごとの計算は1 stepあたり2.23／2.45／2.60 s（最速／中央値／最遅）ですが、中央値はBaseline（1.96 s）より大きいので、中央値どうしは比べません（聞かれたら：Baselineでは多くのrankが待っている間、計算しているrankがメモリ帯域を多く使えた、と考えていますが、確かめていません）。

### 12. Profiling Basic（0:35）

表の注釈（表の上）：Table 9. Each possible bottleneck after Basic, how we measured it and what we found.

| Possible bottleneck | How we measured it | What we found after Basic |
|---|---|---|
| MPI | CrayPAT | Fell from 46% to 19% of the time |
| Outside MPI | CrayPAT | The other 81%, computing and waiting for memory |
| Computing | AMD uProf core counters | Only 0.4 to 0.7 instructions per cycle and about 0.1 flop per byte, so the cores were mostly waiting |
| Memory bandwidth | Memory controller counters | Not readable by users on ASPIRE-2A |

原稿（約35秒）：In the same profile, the other 81 percent of the time was outside MPI, but the cores were not busy computing. They ran only 0.4 to 0.7 instructions per cycle, and their hottest loops run over the sparse matrix with about 0.1 flop for every byte they read. So the cores were mostly waiting for memory. But on ASPIRE-2A users cannot read the memory controller counters that would show it.

訳：同じプロファイルで、残りの81%の時間はMPIの外でしたが、コアは計算で忙しかったわけではありません。コアは1サイクルに0.4〜0.7命令しか実行しておらず、最も重いループは疎行列をなめるもので、読む1バイトあたり約0.1 flopしか計算しません。つまり、コアはほとんどメモリを待っていました。ところが、ASPIRE-2Aでは、それを示すメモリコントローラのカウンタを利用者が読めません。

想定質問：Q42、Q43、Q38、Q35、Q23
補足：39（Hardware counters）

メモ：
- 11/03（ユーザー：MPIの外の中でも、実際に計算している時間が短い、ビジーではないという書き方があるとよい。CPU使用率を見るのはどうか）：「Core speed」の行を「Computing」にし、MPIの外が計算で忙しくなかったことを、1サイクルあたりの命令数と1バイトあたりのflopで言います。CPU使用率（topやsar）は、メモリを待っている間もコアを使用中と数え、Cray MPICHの待ちもCPUを回して待つので、どのコアも約100%になり、計算と待ちを分けられません（Q42）。命令数はコアのカウンタ（uProf）から取れます。コンパイラの行（「no compiler setting helped」）は、13枚目で理由と一緒に言うので、この表から外しました（ユーザー：考察はBonusの後で）。
- 3枚目と同じ行の並べ方で見せると、律速がMPI（待ち）からメモリに移ったことを比べやすいです。MPIの46% → 19%は11枚目で話したので、原稿では81%から言います。
- 「疎行列をなめるループ」：Gauss-Seidelの平滑化、残差（b − Ax）、行列とベクトルの積（Amul）。どれも行列の全部の係数を1回ずつ読み、掛けて足すだけです。
- 81%：Basic（対応付けの前）のCrayPATで、MPIが1 stepの19%です（37176272426、#36 A4）。
- 約0.1 flop/B：Gauss-Seidel、残差、Amulは、内部の面1つにつき約4 flopの計算に、係数2つ（16 B）と番地（4 B）とセルの値を合わせて30〜40 Bを読みます。コアを使い切るには約14 flop/Bが要ります（ノードの倍精度ピーク約4.1 TFLOP/s ÷ STREAM約290 GB/s、Q35）。
- IPC：0.4〜0.7は第6版の値です。1ノードで最初の4つを測った#55では、計算部分の平均が0.36（変更なし）と0.39（最初の4つ）でした。uProfの1/2/4ノードの測定（#66、Basic、全sampleで）では、1セル・1 stepあたりの命令÷cyclesが0.53、0.58、0.67です。Zen 3のコアは1サイクルに最大6つの命令を処理に回せます（dispatch幅）。
- ASPIRE-2AのノードではSTREAMが16コア（L3ごとに1コア）で約290 GB/sに飽和します（#36）。

### 13. Measuring the memory limit（0:55）

スライド：3つの配置を縦に並べます（Figure 10）。各段が1つのノードで、上の帯が「CPU」（16の箱、1つの箱がL3を共有する8コア、rankが動くコアの割合だけ下から紺）、下の帯が「Memory」（16本のチャネル、使うものが緑）。箱とチャネルは2つずつNUMA領域にまとめ、領域の間に隙間、CPUの間にもっと広い隙間を空けます（ユーザー、11/02の3回目）。帯の右に「128 ranks / 16 channels」「64 ranks / 16 channels」「64 ranks / 8 channels」（半分になった数を赤）、その右に1 stepの時間とSTREAMの帯域、その右に段の間の矢印（「Half the cores / the same time」「Half the channels / 2.2 times the time」。どちらも黒の矢印で、原因を赤、2.2倍を紺）。色はユーザーの手直し（11/02の5回目に取り込み）：CPUは紺、メモリは基板っぽい緑。矢印は11/03に2本とも黒にした。下に1文：A step slowed as much as the bandwidth fell, so about 97% of it follows the memory bandwidth. ユーザー、11/02の2回目：第8版の最初の版のチップの絵はリアルだが分かりにくい。CPU、memoryと書いて、半分になったのが分かるように簡単に。矢印はよい。

原稿（約55秒）：So we tested the memory by moving the ranks. Each row is one node, with its CPU blocks of eight cores above its sixteen memory channels, grouped by NUMA domain, the cores in use in blue and the channels in use in green. With half the cores on all sixteen channels, a step took the same time, so the cores do not set the speed, which is also why no compiler setting helped in Basic. With the same 64 ranks on eight channels, it took 2.2 times as long, and STREAM, the standard memory bandwidth benchmark, fell by the same factor on the same nodes. So about 97 percent of a step follows the memory bandwidth.

訳：そこで、rankを動かしてメモリを確かめました。各段が1つのノードで、8コアずつのCPUの箱の下に16本のメモリチャネルを並べ、NUMA領域ごとにまとめて、使っているコアを紺、使っているチャネルを緑で示しています。16本のチャネルを全部使ったままコアを半分にすると、1 stepの時間は同じだったので、速さを決めているのはコアではありません。Basicでコンパイラの設定が効かなかったのも、このためです。同じ64 rankを8本のチャネルに詰めると2.2倍かかり、メモリ帯域の標準的なベンチマークであるSTREAMも、同じノードで同じ比だけ落ちました。だから1 stepの約97%は、メモリ帯域に沿っています。

想定質問：Q23、Q24、Q26、Q43、Q44
補足：32（The placement experiment in full）

メモ：
- コンパイラの理由（11/03）：10枚目では結果だけを言い、理由はここで言います（ユーザー：メモリに取り組んだのはBonusなので、考察はBonusの後で）。コアを半分にしても同じ時間なので、命令を速くしても1 stepは縮みません。詳しくはQ43。
- 図の読み方（ユーザーの質問、11/02の2回目「4コアをフル、8コアを半分で合ってる？」）：1つの箱は1コアではなく、L3を共有する8コアの組です（1 CPUに8つ、1ノードに16）。spread64はCPUごとに8つの箱がどれも半分（各L3の8コアのうち4コア）、packed64はCPUごとに4つの箱が満杯（最初の2つのNUMA領域の32コア）で4つが空です。どちらも1 CPUに32 rank、1ノードに64 rankです。箱は2つずつNUMA領域にまとめ、領域の間に隙間を、CPUの間にもっと広い隙間を空けました（ユーザー、11/02：NUMA別に空白）。チャネルも同じく、1つのNUMA領域に2本です。
- 図の配置（#61の`platforms/aspire2a/rank-cpus.txt`のとおり。spread64はcommit `9922d4b`でコア0〜3、8〜11、16〜19、…、120〜123、packed64は`8758705`でコア0〜31と64〜95）：full128は全コア。spread64は各L3（8コア）に4 rankずつ（図では16の箱がどれも半分まで紺）、8つのNUMA領域すべてで、16本のチャネルを全部使います。packed64は各CPUの最初の2つのNUMA領域（各16コア）に詰め、残りの2つの領域を空けるので、使うチャネルは8本です（local rank lのCPUは(l / 32) × 64 + l % 32。片方のソケットに詰めないのは、ソケットごとの電力とブーストの条件をspread64とそろえるため）。spread64とpacked64は同じ256分割、同じrankなので、計算は同じで`coefficient.dat`はビット一致します。
- 数値：Basic（対応付けの前）、4ノード、150 step。128 rank/ノード 2.920（1本）、64 rank（16チャネル）2.887（2本）、64 rank（8チャネル）6.347（2本）s/step（`data/memory_placement.csv`）。STREAMのtriad（c = a + 3b）を同じジョブの中でソルバの後に、同じノード、同じ配置で流し、274、279、125 GB/s/ノード（`data/triad_placement.csv`）。帯域の比は2.23倍、1 stepの比は2.20倍です。
- 約97%の出し方：1 stepを「帯域に比例する部分b × （全チャネルの帯域 ÷ その配置の帯域）＋ 比例しない部分a」と置き、spread64とpacked64に当てはめると、b ≈ 2.81 s、a ≈ 0.08 sで、2.81 / 2.887 ≈ 97%です。MPIの待ちも、最も遅いrankのメモリ律速の計算を待っているので、この「比例する部分」に入ります（Q26）。
- やさしい説明（11/01）：STREAMはJohn McCalpinが作った、持続的に出せるメモリ帯域を測る標準のベンチマークで、OpenFOAMとは別のソフトです。だから、STREAMの値だけで「OpenFOAMはメモリ律速」とは言えません。根拠は、置き場所だけを変えたときに、OpenFOAMの時間がSTREAMの帯域の変化と同じ比で変わったことです。STREAMの値は、そのノードで素直な読み書きなら実際に出る帯域です（理論409.6 GB/sの約68%）。OpenFOAMが実際に使っている帯域は分からない（カウンタが読めず、読み方が飛び飛び）ので、絶対値は議論せず、配置ごとの帯域の比だけをSTREAMから借ります。このとき、OpenFOAMが使える帯域もSTREAMと同じ比で増減すると仮定しています（同じチャネルを使うので自然な仮定ですが、仮定ではあります）。
- 128コアに16チャネルは、帯域をたくさん使うコードには厳しい比です。1コアあたり約2.2 GB/s（STREAM 279 GB/s ÷ 128）。1バイトあたり約15 flop計算しないとコアを使い切れませんが、OpenFOAMの重いループは約0.1 flop/Bです。
- 質疑対策（ユーザー、11/02）：128 rankを8チャネルにしなかった理由と、32 rank/ノードを試さなかった理由はQ44にまとめました。
- 限界：チャネルを半分にした配置はL3も半分にするので、DRAMの帯域とL3の容量の寄与は分けられません（どちらもメモリ側の資源）。コアを半分にした比較は分割が512から256に変わりますが、比例しない部分は1 stepあたり約0.08 sなので、分割の違いでは「同じ時間」を説明できません（Q23）。
- 読めないものと、代わりに使った方法：rankの実際の置き場所は実行中の`/proc`（5枚目）、メモリ帯域は配置を変える実験と同じノードでのSTREAM（この枚）、rankごとのDRAMの転送量はコアのカウンタ（補足の39枚目、Q21）、ネットワークは毎回のIMBとネットワーク側だけを変える比較（3枚目、10枚目、Q31）。IBSも読めません（`perf_event_paranoid=2`、Q35）。

### 14. multiLevel decomposition（0:40）

スライド：左上にBasicとBonusの`decomposeParDict`を左右に並べ（ユーザー、11/02の2回目：multiLevel 4 2 4 16やscotchのdomainsはOpenFOAMの文法で示す）、左下に表、右にBasic（domains (2 4 16)のscotch、見出しは「scotch (2 4 16)」）とmultiLevelの分割の絵（Figure 11、NUMAごとの色）と、その下に色の凡例。ユーザー、11/02：Bonusの分割で1枚使う。Basicでは使えない分割方法を試したかった、NUMAに結び付ける、scotchのdomainsとmultiLevelの違いと利点、NUMAごとの絵。11/02の4回目：左の絵を、玄界で描いたBasicの絵に替えた（scotchの絵を更新して載せる）。

左上のコード（見出し「Basic, one scotch run」と「Bonus, scotch per level」）：

```
method  scotch;                method  multiLevel;
scotchCoeffs                   multiLevelCoeffs
{                              {
    domains  (2 4 16);             method   scotch;
    // and its weights             domains  (4 2 4 16);
}                              }
```

表の注釈（表の上）：Table 10. Each against plain scotch on 4 nodes.

| | Basic | multiLevel |
|---|---:|---:|
| Faces between nodes | −22.7% | −38.3% |
| Faces between sockets | −21.3% | −33.5% |
| Faces between NUMA domains | −10.4% | −25.7% |
| Time per step | −0.7% | −1.5% |

原稿（約40秒）：In the Bonus we looked at decompositions outside the scope of Basic. On the left, Basic runs scotch once on the node tree. multiLevel instead runs scotch at each level, four nodes, then two sockets, four NUMA domains and sixteen cores. So each node, socket and NUMA domain gets one compact block, as the pictures show. In the table it cut more faces between them than Basic, and a step took 1.5 percent less time than with plain scotch.

訳：Bonusでは、Basicの範囲外の分割について検討しました。左のとおり、Basicはノードの木の上でscotchを1回流します。multiLevelは、代わりに段ごとにscotchを流します。4つのノード、次に2つのソケット、4つのNUMA領域、16のコアです。だから絵のとおり、ノード、ソケット、NUMA領域のそれぞれが1つのまとまった塊になります。表のとおり、それらの間の面をBasicより多く減らし、1 stepはplain scotchより1.5%短くなりました。

想定質問：Q10、Q4、Q5
補足：33（Decompositions we tried）

メモ：
- なぜ分割を変えたか（ユーザー、11/02）：分割はOpenFOAMで典型的な高速化の手で（Task Rulesにも「Decomposition (try this first)」）、hierarchicalとscotch以外の方法はBonusです（F2）。Basicで使えない方法のうち、機械の形（ノード → ソケット → NUMA領域 → コア）に沿うmultiLevelを選びました。5枚目のNUMAの話と8枚目のノードの木の続きで、隣どうしのサブ領域ができるだけ同じNUMA領域、同じソケット、同じノードに入れば、遠いメモリや遅い接続を通る交換が減ります。
- Basicの対応付けとの違い：どちらも分割に機械の階層を教えますが、対応付け（Basic）は、scotchの1回の分割の中で、ノードの木を目標にして面を多く共有する塊を近くに置きます（`scotchCoeffs`の`domains (2 4 16)`）。multiLevel（Bonus）は、まずメッシュを4つのノードに分け、各部分を2つのソケットに、さらに4つのNUMA領域に、16のコアにと、段ごとにscotchを別々に回します（`multiLevelCoeffs`、4ノードで`domains (4 2 4 16)`、2ノードで`(2 2 4 16)`、1ノードで`(2 4 16)`。`run/prepare.pbs`が書く。スライドのコードは4ノードのもの。Basicのコードの`// and its weights`は、8枚目の`domainWeights`と`strategy`を省いた印）。段ごとに切るぶん、各段をまたぐ面はより減りますが、セル数の偏りは大きくなります（最大のサブ領域が平均の1.0107倍（plain scotch）に対して1.0186倍）。
- 表の数値：multiLevelはplain scotchに対して、ノード間の面337,324 → 208,092、ソケット間492,282 → 327,131、NUMA領域間1,047,405 → 778,614（#42のコメント、`decomposePar.log`から）、全体の面は2.93 M → 2.81 M（−3.9%）。時間は2.918 → 2.873 s/step（4対4、#42、10/04）。Basicの対応付けはREPORT §6.3と#63（5対5）。
- 効いた仕組みは切り分けていません。ノード間の面を92%減らしたrankの並べ替えは効かなかった（10枚目）ので、ノード間の通信量だけでは説明できません。だから「運ぶデータを減らす」はソースの変更にだけ言います。
- multiLevelとBasicを同じ時期に直接比べたことはありません。時期をまたぐと、Basic 2.8976（5本、10/15〜16）に対して、#61のmultiLevel 2.8688（2本、10/10、128 rank/ノード）で−1.0%です。
- 絵：Boxの`decomposition-numa-scotch-domains-vs-multilevel.png`の2つの列です。左はBasic（scotchのdomains (2 4 16)、面3.02 M、最大のサブ領域+1.00%）、右はmultiLevel（最終Bonusと同じ分割、面2.81 M、+1.86%）。どちらも11/02に玄界で作った分割（計測runと全部一致）を、玄界にビルドしたParaView 6.0.1で同じ画角と色で描いたもので、multiLevelの絵は10/09の絵とバイト単位で同じです（`decomposition/README.md`）。色はノードを色相、NUMA領域を濃淡で分けています（絵の下の凡例、7枚目のメモ）。11/02の4回目に、左の絵をplain scotchからBasicに替えました（ユーザー：scotchの絵を更新して載せる）。表の比較の相手（plain scotch）の絵は7枚目にあります。
- 試した分割の全部（(4 128)、(4 2 8 8)、重み、METISなど）は補足の33枚目です（ユーザー、11/02：ほかの分割方法も検討したか）。

### 15. Source changes by intent (1/2)（0:30）

スライド：表（Table 11。7つの変更、意図の行「Fewer passes over the data」、各変更の番号、何を減らしたか、4ノードの1 stepの変化）と、その下に1文：None of the 14 changes alters the iterations, the convergence tests or the discretisation. 一緒に測った変更は、1つの値を並んだ行にまとめて、withを前に、%を右端にそろえて書きます（0006と0009は「with 0008, 0010  −2.0%」、0013と0015は「with 0014  −2.5%」。ユーザー、11/03：%を縦に比べやすく）。

原稿（約30秒）：The larger part of the Bonus was the source code. Since memory bandwidth limits the solver, our 14 changes make each step move less data, and we grouped them by intent. Seven remove passes over the data. For example, the turbulence model now passes over the cells 13 times instead of 80. None of them alters the iterations, the convergence tests or the discretisation.

訳：Bonusの大きい部分は、ソースコードの変更です。メモリ帯域が律速なので、14の変更で1 stepに運ぶデータを減らしました。それを意図ごとにまとめています。7つは、データをなめる回数を減らすものです。例えば乱流モデルは、セルを80回ではなく13回なめるようになりました。どの変更も、反復回数、収束判定、離散化を変えません。

想定質問：Q32、Q33、Q7
補足：36（Source changes in detail (1/2)）、37（Source changes in detail (2/2)）、38（Effect of each Bonus change）

メモ：
- 一覧を2枚に分け、意図別にしました（ユーザー、11/02：patchの一覧は見せる、2枚くらい、意図別）。意図と番号：fewer passes（0002、0004、0006、0009、0013、0015、0016）、no copies or zero fills（0001、0011、0014）、no values that nobody reads（0003、0008、0010）、fewer global sums（0012）。0005（#68）と0007はBonusに入っていません。
- 4ノードの変化は、直前の構成と比べた値です（`data/changes_ab.csv`、`submission/openfoam/bonus/README.md`）。0006、0008〜0010は一緒に測って−1.99%、0013〜0015も一緒に−2.48%（対照の数日後に測った）、0016は−3.80%（同じく数日後）。最初の4つは1つずつ（3〜4対3〜4）。
- 丸めが変わり得るのは0011、0012、0016の3つ（足す順序が変わる）なので、「same arithmetic」ではなく、変えないものを並べて言います。Cdの確認は18枚目。
- 見つけ方：最初の4つは最も重いループ、後の10個は最初の4つの版（fa4f5b0）のCrayPATのstack sample（#53）を関数別・呼び出し経路別に集計し直して（補足の34、35枚目）、v2512のソースを読んで候補を順位付けしました（#69、実装はCodex）。
- 「why the result is the same」は補足の36、37枚目（Source changes in detail）にあります。R3の「何を変えたか」「なぜ同じ計算か」はこの2枚と補足です。

### 16. Source changes by intent (2/2)（0:20）

スライド：表（Table 12。意図の行「No copies or zero fills」「No values that nobody reads」「Fewer global sums」と、各変更。一緒に測った変更は15枚目と同じく「with 0013, 0015  −2.5%」の形）。

原稿（約20秒）：The other seven remove copies and zero fills, values that nobody reads, and global sums. For example, six callers built boundary values, exchanged them with their neighbours and threw them away. On four nodes each change took 0.3 to 3.8 percent off a step.

訳：残りの7つは、コピーとゼロ埋め、誰も読まない値、大域和を減らすものです。例えば6か所の呼び出し元は、境界の値を作って隣と交換し、それを捨てていました。4ノードで、それぞれの変更は1 stepを0.3〜3.8%短くしました。

想定質問：Q32、Q33
補足：36（Source changes in detail (1/2)）、37（Source changes in detail (2/2)）

メモ：
- 「six callers」は0003です：ラプラシアンの非直交補正、bounded対流項の`fvm::Sp`、補正付き対流項、連続の式の誤差、`pEqn`の右辺、kOmegaSSTの`divU`（Q32）。
- 0.3〜3.8%：一緒に測った束も含めた、4ノードでの1つずつの比較の範囲（0012の−0.30%から0016の−3.80%）。
- 0012（CGの1反復で大域和1回）は−0.3%と小さいですが、3本とも一貫して速く、2枚目の決まりを通りました。

### 17. Two source changes in pictures（0:30）

スライド：左に0002（Uの3成分を1回で）、右に0001（ソルバのコピーをなくす）の図（ユーザー、11/02：今のUの例のように、効果が分かりやすいpatchを左右に図示する）。それぞれ見出し（番号と名前）、4ノードと1ノードの変化（4ノードの「−2.3%」「−3.4%」は赤。ユーザーの11/03 2:24の手直しを取り込んだ）、図、注釈。左右の間に細い黒の縦線（ユーザーの手直し、11/03に取り込み）。図の矢印は黒。

原稿（約30秒）：Here are two of them. On the left, the three components of the velocity share one matrix, but the code read it once for each. Now one pass updates all three, which saved 2.3 percent on four nodes. On the right, the solvers formed each residual in a new field and then copied it. Now they write it in place, which saved 3.4 percent.

訳：そのうち2つを図にしました。左は、速度の3成分が1つの行列を共有しているのに、コードは成分ごとにその行列を読んでいました。今は1回で3成分を更新し、4ノードで2.3%短くなりました。右は、ソルバが残差を新しい場に作ってからコピーしていました。今はその場で書くので、3.4%短くなりました。

想定質問：Q6、Q33
補足：36（Source changes in detail (1/2)）、38（Effect of each Bonus change）

メモ：
- 0002：U（速度）の式を`smoothSolver`＋`GaussSeidel`で解くとき、新しい`smoothSolver::solveGaussSeidelComponents`が、共有の行列の配列を1回なめる間に3成分を平滑化します。分離解法では成分は独立なので、各成分は同じ演算を同じ順序で受けます。1ノード−6.39%、2ノード−4.13%、4ノード−2.29%。1ノードで最もよく効くのは、各rankのデータが多く、キャッシュに収まりにくいからです（Q6）。
- 0001：`smoothSolver`は、新しい場を返してからコピーする版ではなく、すでにある「その場で書く」`lduMatrix::residual`を使います。GAMGは最も細かい段の残差を、コピーしてから引く代わりに1回の`subtract(r, source, Apsi)`で作ります。同じ関数が同じ残差を計算し、なくなるのは確保とコピーだけです。1ノード−2.19%、2ノード−2.94%、4ノード−3.39%。
- 図の「b − Aψ」は残差の式です（bは右辺、Aは行列、ψは解）。
- ほかに図にしやすい例：0016（Gauss–Seidelの最後のsweepの中で残差を作り、行列を1回なめる処理と境界の交換を1回ずつ減らす、4ノード−3.80%）、0013（kOmegaSSTの場の式を80回から13回のセルのループに）。時間があれば2枚目の例の枚を作れます。

### 18. Bonus results（0:35）

スライド：左に表（Table 13）と1行、右に図（Figure 14。公式の結果2本、Baseline、Basic、Bonusの各ジョブ、原点0から波線で省略、BasicからBonusへの矢印と%（−18.6%、図形））。ユーザー、11/02：OfficialとBaselineも載せる。L1など細かい話は外す。全部入れたときの時間と、Basicからmultilevelに変えたときの比較。カウンタの図は補足の39枚目へ。

表の注釈（表の上）：Table 13. Each Bonus step against its control on 4 nodes.

| Step | s/step | Change |
|---|---:|---:|
| multiLevel instead of plain scotch | 2.918 → 2.873 | −1.5% |
| First four source changes | 2.873 → 2.599 | −9.5% |
| Ten more source changes | 2.603 → 2.360 | −9.3% |
| Bonus against Basic | 2.898 → 2.360 | −18.6% |

- Cd stayed within 0.0005% of the unmodified code at 1, 2 and 4 nodes.

原稿（約35秒）：With all of this, the Bonus took 2.360 seconds per step on four nodes, 18.6 percent less than Basic and 35 percent less than our Baseline. The table gives each step against its own control. multiLevel saved 1.5 percent, the first four source changes 9.5 percent and the ten later ones 9.3 percent. And Cd stayed within 0.0005 percent of the unmodified code at one, two and four nodes.

訳：これらをすべて入れると、Bonusは4ノードで1 step 2.360秒になり、Basicより18.6%、私たちのBaselineより35%短くなりました。表は、各段をそれぞれの対照と比べた値です。multiLevelで1.5%、最初の4つのソースの変更で9.5%、後の10個で9.3%短くなりました。そしてCdは、1、2、4ノードで、変更していないコードから0.0005%以内でした。

想定質問：Q7、Q13、Q33、Q34
補足：38（Effect of each Bonus change）、39（Hardware counters）、40（Drag coefficient over the iterations）、41（Drag coefficient checks）

メモ：
- 表の各行：multiLevelはplain scotchと4対4（#42、10/04）。最初の4つは1つずつ直前の版と比べ（−3.4、−2.3、−1.3、−2.8%）、その積み重ねで2.873 → 2.599（fa4f5b0の10/07の平均）。後の10個は最終計測（10/26、#69）でfa4f5b0と交互に3本ずつ（2.603 → 2.360、範囲は重ならない）。最後の行は、Basic（10/15〜16）とBonus（10/26）の時期をまたいだ比較です。最終計測のfa4f5b0は10/07の自分の平均から0.15%以内だったので、その間に機械は変わっていません（`bonus/README.md`）。
- 公式の結果に対して、Bonusは−30.9%（hierarchical）、−34.0%（scotch）です。
- Cdの証拠（R3）：(a) 0001〜0004の版は、変更前のrun（同じmultiLevelの分割とrank数で、ソースの変更を外したもの）と1/2/4ノードで`coefficient.dat`がバイト一致し、`simpleFoam.log`の全stepの残差（16桁）、反復回数、連続の式の誤差、kとωのboundingが全行一致しました（371、771、1,475行）。(b) 14すべてのCdは、変更前のrunに対して+1.2 × 10⁻¹²（相対）、−0.00002%、−0.00041%（1/2/4ノード）で、F3の±0.5%の1000分の1以下です（Q7、Q33）。
- なぜ速くなったか（聞かれたら、補足の39枚目）：最初の4つの変更では、1ノードで命令は4.1%しか減らないのに、DRAMからのL1 refillは17.2%減り、1 stepは12.3%速くなりました（#55）。取り除いたのは、大きな配列を最初から最後までなめるだけの処理（Uの行列の読み直し、場のコピー、面の上の一時的な場）で、1要素あたりの命令は少ないのに、配列はキャッシュに収まらないので、なめるたびにDRAMから読み直していました。チャネルを半分にすると、同じ4つの変更の改善が7.9%から11.4%に増えました（#61）。数えているのはL1のdemand refillで、DRAMの転送バイト数ではありません（Q38）。第7版ではこの図が本編にありましたが、細かいので補足だけにしました（ユーザー、11/02）。
- 提出スクリプトでの再実行（10/26）も、記録の平均から−0.31〜+0.22%で、`coefficient.dat`はバイト一致しました（Q18）。

### 19. Scaling from 1 to 4 nodes（0:35）

スライド：図だけ（Figure 15、`p17_scaling`。1、2、4ノードごとに公式の結果とBaseline、Basic、Bonusの各ジョブ、原点0からの1つの軸、点線は1ノードからの理想）。図をスライドの高さまで大きくし、表をやめました。2ノードと4ノードの私たちの各段のラベルの上に、1ノードの何倍速いか（1.96×、2.10×、2.05×、3.99×、4.61×、4.34×）を段の色で、4ノードの群の上の空いたところに1文「Over 4 times on 4 nodes because each rank's arrays fit in the L3 cache.」を、スライドの図形として重ねます（ユーザー、11/03：ごちゃついている。図だけにして、pptの矢印や文字を上から重ねて何倍かを示せば、表がいらなくなり図も見やすい。図形なので手で動かせる）。倍率の数字と置き場所は`deck_plots.py`が`p17_scaling.json`に書き、`build_deck.py`の`overlay()`が重ねます。1文の位置は、ユーザーが11/03 2:24に手で動かした位置です。公式の結果の倍率はメモだけにしました。ユーザー、11/02：グラフはかなり良い。並列効率の1.xxではなく、1ノードの何倍速くなったかで示す。L3に載りやすくなった分速くなった、という考察。

原稿（約35秒）：This is strong scaling on one, two and four nodes with the official runs, and the dashes mark ideal scaling from one node. The numbers above our jobs give how many times faster each is than on one node. On four nodes Basic was 4.61 times faster and the Bonus 4.34 times, more than four. There each rank's arrays shrink to about 1 megabyte and fit in the L3 cache, so fewer bytes come from memory.

訳：これは、1、2、4ノードでのstrong scalingで、公式の結果も並べています。点線は、1ノードから理想どおりにスケールしたときの時間です。図の上の数字は、私たちの各段が1ノードの何倍速いかです。4ノードでBasicは4.61倍、Bonusは4.34倍速く、4倍を超えました。4ノードでは各rankの配列が約1 MBに縮んでL3キャッシュに収まり、メモリから来るバイトが減るからです。

想定質問：Q6、Q30
補足：42（Why the speedup exceeds 4）

メモ：
- Bonusの倍率がBasicより小さい理由の文（「Bonusはすでに運ぶデータを減らしているので、この効果が小さくなります」）は原稿から外しました（ユーザー、11/02の4回目：いるかな？）。聞かれたら、その文と下の項目で答えます。
- 倍率の値：1ノードの平均 ÷ 2、4ノードの平均（図と同じジョブ）。私たちの段は2ノードでBaseline 1.96×、Basic 2.10×、Bonus 2.05×、4ノードで3.99×、4.61×、4.34×。公式の結果（スライドには載せない、1本ずつ）はhierarchicalが2.06×と4.30×、scotchが1.95×と3.93×です。Baseline 14.57／7.427／3.650（6／3／3本）、Basic 13.36／6.372／2.898（3／3／5本）、Bonus 10.23／4.992／2.360（3／3／3本）、公式hierarchical 14.67／7.118／3.415、公式scotch 14.05／7.196／3.576 s/step。並列効率（4ノードの倍率 ÷ 4）は、Baseline 1.00、Basic 1.15、Bonus 1.08、公式1.07と0.98です。
- 4倍を超える理由は、カウンタで確かめました（#66、uProf、Basic、1/2/4ノード）。1セル・1 stepあたりのDRAMからのL1 refillは、4ノードで1ノードの0.70倍です。セルの配列がrankあたり4 MB（1ノード）から1 MB（4ノード）になり、コアあたり4 MBのL3に収まります（補足の42枚目、Q6）。
- Bonusの倍率が下がるのは、1ノードの時間をより多く減らしたからで、4ノードが遅くなったからではありません（後の10個は1ノード−12.2%、4ノード−9.3%）。
- 公式のhierarchicalも4.30倍と4倍を超えています。固定なしの1本ずつなので、理由は調べていません。
- strong scalingです。同じメッシュ（65,334,765セル）を1/2/4ノード（128/256/512 rank）で解きます。ケースは1/2/4ノードで40/80/150 stepですが、指標は1 stepの時間なので比べられます。
- 図の描き方：対数軸をやめ（11/01の5回目）、1つの線形の軸にまとめ（7回目）、ノード数ごとに公式の結果と3つの段を並べました（8回目）。第8版では一度、表を入れるために図の高さを縮めましたが、6回目（11/03）に表をやめ、図をスライドの高さまで大きくして倍率を図形で重ねました。

### 20. What did not help in the Bonus（0:45）

スライド：表と2行（10枚目と同じ書き方。紺の行は、直感に反したもの、ふつうは効くはずのもの）。発表の最後の枚で、原稿の最後の1文で最終結果に戻ります（#68とまとめの枚を消したため、11/02の2回目）。

表の注釈（表の上）：Table 14. Each Bonus idea we tried and did not keep, with its time per step against its control on 4 nodes.

| Idea | Time per step |
|---|---|
| Cell weights to balance the faces in scotch or multiLevel | 2.2% to 6.5% slower |
| METIS balancing both cells and faces | 1.5% slower |
| GAMG coarsest level gathered on one rank | 5.0% slower |
| The same on one rank per node or per NUMA domain | 1.0% slower or 0.3% faster |
| UCX over RC between nodes | 0.2% faster, within the spread |
| Gauss–Seidel overlapped with its halo exchange | 8.3% slower and Cd 1.2% lower |
| bound() averaging only the bounded cells | not run, it needs another global sum |

- Balancing the faces unbalanced the cells, and fewer ranks in the global sums did not shorten the wait.
- Now a step is limited by memory traffic and by the ranks that read the most from DRAM.

原稿（約45秒）：These are the Bonus ideas that did not help, the unexpected ones in blue. Cell weights and METIS balanced the faces but unbalanced the cells. Gathering the coarsest level of the pressure solver removed most global sums, but the ranks still waited for the slowest one. Overlapping a sweep with its halo exchange was slower and moved Cd too far. So what limits a step now is memory traffic, and the slowest ranks read the most from DRAM. Our final result is 2.360 seconds per step on four nodes, 35.3 percent less than our Baseline. This ends the HPC part.

訳：Bonusで効かなかった手です。予想外のものを紺にしました。セルの重みとMETISは、面をそろえた代わりにセル数をそろえられなくしました。圧力のソルバの最も粗い段を集めると大域和の大半はなくなりましたが、rankは相変わらず最も遅いrankを待ちました。sweepと境界の交換を重ねると遅くなり、Cdも動きすぎました。だから今1 stepを決めているのはメモリの読み書きの量で、最も遅いrankは、DRAMから最も多く読むrankです。私たちの最終結果は、4ノードで1 step 2.360秒、Baselineより35.3%短くなりました。以上でHPC側の発表を終わります。

想定質問：Q20、Q34、Q39、Q4、Q5、Q21
補足：33（Decompositions we tried）、34（Where a Bonus step goes）、35（Call stacks of a Bonus step）、43（Other renumberings on Genkai）

メモ：
- 行ごとの数値と出典：
  - セルの重み：multiLevelに0001を入れた版で、点の割合の重み×2が+2.2%、×12が+6.1%（1対4、#37。×12は32ビットのScotchであふれた）、scotchで境界のセルに重み2（`weightField` 2:1）が+6.5%（3対6、#37 F1）。重み×2でセル数の偏りは1.073に増えました。車輪と床下のセルに重み3のmultiLevelは+10.8%と+64%で、Cdが−2.6%動いてF3も満たしません（#33、補足の33枚目）。
  - METISの2つの制約（セルと面、段ごとに`method manual`）：面の均衡は良くなったが、サブ領域の間の面が18%増えて+1.46%（2対3、#45）。
  - GAMGの最粗段を1つのrankに集める（`processorAgglomerator masterCoarsest`）：+4.95%（40 step）。ノードごと（`nProcessorsPerMaster 128`）は+1.02%、NUMA領域ごと（16）は−0.25%（1本ずつ、Cdは対照から0.002%以内）。最粗段は`MPI_Allreduce`の呼び出しの81%を出しますが、時間は1 stepの約0.6%です（#58、#69）。
  - UCX over RC：0001〜0004のBonusで−0.16%（4対4、範囲が重なる）。Basicでは−0.01%（10枚目）。
  - Gauss–Seidelの内部のセルを、境界の値が届く間にsweepする（0018）：+8.32%（3本）、Cd −1.20%でF3を満たしません。512 rankで、セルが隣の新しい値を見る順序が変わるためです（#69）。
  - bound()の平均を対象のセルだけで（0017）：大域和が1回増えて、節約より高くつくので流していません（#69）。
- 強調した行（紺）：予想外だったもの（ユーザー、11/02の4回目の言い方）。重みとMETIS（面をそろえれば速くなりそうなのに遅くなった）、GAMGの最粗段を集めるもの（大域和の大半を消したのに効かなかった）、重ね合わせ（通信を隠す定番の手なのに遅く、Cdも動いた）。
- ほかに：境界の交換と計算を重ねる余地は1%未満と見積もり（#49）、代わりに使われない交換を省いた（0003）。計測区間のファイルI/Oは1 stepの約0.01%で、律速ではありません（#46）。
- 今の律速と次の手（Q20、Q34）：U・k・ωの組み立てを項をまたいで融合すれば、運ぶバイトをさらに減らせます。rank間の差（最も遅いrankの計算は中央値の1.07倍）は、セル数ではなくDRAMからの読み込み量に沿います（r = +0.69、#66）。renumberMeshのほかの並べ方は、玄界で既定より速くなりませんでした（11/03、Q39、補足43枚目）。見込みは合わせて数%です。英語の答え：「Move fewer bytes still. Fusing the assembly of U, k and omega across terms removes a few more passes over the face arrays. We expect a few per cent from it.」
- 最後の2文（11/02の2回目と4回目）：#68のおまけとまとめの枚を消したので、この枚で最終結果に戻り（1枚目の流れと同じ数字）、「This ends the HPC part.」（以上でHPC側の発表を終わります、ユーザー）で終えます。AIパートへ渡す一言を足すかはチームで決めます。

## 入れなかったもの

- roofline：HPCでは使っていないので、本編にも補足にも置きません（質疑ではQ35で答えます）。
- 流れの1枚：動画を置くだけにしました（9枚目）。
- ばらつきだけの1枚：時間の図にSDを書き、6枚目（固定）と9枚目（Basic）で話します。92本の詳細は補足です。
- R3の4点だけの1枚：15〜17枚目（何を、なぜ同じか）と18枚目（証拠、速度向上）に分けて入れました。
- ASPIRE-2Aの構成とBaselineの設定の枚：3枚目の1行目（ビルドとMPI）と5枚目のノードの図で触れ、詳しくは補足に置きます。
- 結論の1枚：1枚目が要約を兼ね、20枚目の最後の1文で最終結果に戻ります。
- 数えなかった高速化（#68、固定反復でだけ効く残差と大域和の省略。最終Bonusの上で2.166 s/step）：運営の答え（11/02）で、どの段でも数えないと決まりました。別の枚で見せてもよいが採点しない、とのことで、ユーザーの判断で枚ごと消しました。聞かれたときの答えはQ34。
- カウンタの図（第7版の11枚目にあった、最初の4つの変更の命令とDRAMからのrefill）：細かいので補足の39枚目だけにしました（ユーザー、11/02）。18枚目のメモで、聞かれたときの答えを書いています。
- 11/02の4回目に原稿から外したもの（ユーザーの訳への指摘から）：2枚目の「20回に1回」と、Cdとプロファイルの決まり（ルールにあるため）、4枚目の中央値と「40 step」「全rankの合計とrankあたり」、10枚目のコンパイラの理由（11/03から13枚目で言う）とrenumberMesh（Q39）、19枚目のBonusの倍率が小さい理由。どれも各枚のメモに残しています。
- 固定なしの分割の比較（hierarchical対scotch、−7.5%、交互ではない）：11/03に、固定を先にする順にしたので本編から外し、補足30枚目とQ41に置きました。

## 時間が足りないとき（削る順）

第8版は約12分半です。AIパートとの配分で短くするときは、この順に削ります。

1. 17枚目（変更を図にした例）を飛ばし、16枚目の最後に「the solvers now write each residual in place instead of copying it」と1文足す（−25秒）。
2. 11枚目（Basicの後のMPI）を飛ばし、12枚目の最初に「For the Bonus we profiled Basic again, and MPI fell from 46 to 19 percent of the time」と1文足す（−25秒）。
3. 16枚目を15枚目の最後の1文（the other seven remove copies, unused values and global sums）にまとめる（−15秒）。
4. 8枚目（ノードの木）を飛ばし、7枚目の最後に「Mapping the subdomains onto the node saved another 0.7 percent」と1文足す（−35秒）。

2枚目（採用の基準）、3枚目（律速の候補のプロファイル）、4枚目（MPI）、5、6枚目（固定）、7枚目（分割）、13枚目（読めない量の測り方）は削りません。

## 残っていること（チームで決めること）

- 発表の最後の記録の枚：第7版では、AIパートの謝辞の後にHPCとAIの記録の枚を置いていました。第8版はHPCだけのデッキなので出しません。チームのデッキの「OUR RESULTS」の枚を使うときは、HPCの公式の結果を「Official」と書くかどうかをチームで決めます。
- 発表時間の配分（HPCとAIを合わせて15〜20分）。

## 第7版の本編との対応

| 第7版の本編 | 第8版（11/03の7回目の番号） |
|---|---|
| 1 OpenFOAM on ASPIRE-2A | 1（原稿に律速を入れた） |
| 2 Criteria for keeping a change | 2（図の軸を0から） |
| 3 Profiling the Baseline | 3（Outside MPI、MPIから見た理由） |
| 4 MPI calls on 4 nodes | 4（表を2つに。合計とrankあたり。最速・最遅） |
| 5 CPU and memory pinning | 5（なぜ固定するか、ノードの図）、6（hierarchicalでの固定とscotchでの4通りを1つの図に）、補足30（固定と分割の掛け合わせ） |
| 6 Decomposition | 7（固定した上での分割、`decomposeParDict`、NUMAごとの絵）、8（ノードの木、新規） |
| 7 Basic results | 9（段ごとの表、公式の結果、矢印）、11（Basicの後のMPI、Bonusの始まり） |
| 8 Profiling Basic | 12（Outside MPI、コアは忙しくない） |
| 9 Measuring the memory limit | 13（CPUとメモリの帯の図、コンパイラが効かない理由） |
| 10 Bonus optimizations | 14（multiLevel、`decomposeParDict`）、15、16（変更の意図別の一覧）、17（変更を図にした例） |
| 11 Bonus results | 18（公式の結果とBaseline、段ごとの表）、補足39（カウンタ） |
| 12 Scaling from 1 to 4 nodes | 19（1ノードの何倍速いか） |
| 13 What did not help | 10（Basic）、20（Bonusと今の律速、最後に最終結果）。補足の全部の一覧はここへ移した |
| 14 An uncounted gain and our result | 外した（#68は運営の答えでどの段でも数えない） |

## 補足（質疑用、20枚）

補足も本編と同じ決まり（短い見出し、主張の行なし、図にはFigure S1から、表にはTable S1からの番号と一文の注釈）で作っています。デッキでは補足の扉が22枚目、Q&A目次が23枚目、補足が24〜43枚目で、どれもスライドショーでは非表示です。

| まとまり | デッキの補足（枚目） |
|---|---|
| Setup and measurement | ASPIRE-2A and why we chose it（24、Q1）、Build, MPI and run settings（25）、Run-to-run variation over 92 jobs（26）、The organisers' reference（27）、Reproducing our results（28） |
| Basic | Is the network the bottleneck?（29）、Pinning and decomposition（30、固定と分割の掛け合わせと遅いrankの比、11/03）、Hierarchical against scotch（31、1/2/4ノード）、The placement experiment in full（32） |
| Bonus | Decompositions we tried（33、新規）、Where a Bonus step goes（34、段階ごとのcall stack）、Call stacks of a Bonus step（35、flame graph）、Source changes in detail (1/2)（36）、(2/2)（37）、Effect of each Bonus change（38）、Hardware counters（39） |
| Results | Drag coefficient over the iterations（40）、Drag coefficient checks（41）、Why the speedup exceeds 4（42）、Other renumberings on Genkai（43、11/03） |

外したもの：Not adopted: the full list（第8版で本編の10枚目と20枚目に移した）、Pinning only the CPU or the memory（11/02の2回目に本編へ戻した。今は6枚目）、Pinning with hierarchical（11/03に本編6枚目の図へ入れ、この枠は固定と分割の掛け合わせにした）。第7版までに外したもの（Optimization strategy、Bottlenecks we measured、Experiment automationなど）の中身は、第6版のslides.md（git `a1f18a3`）と想定問答に残っています。

第8版で新しく作った補足：

- Pinning and decomposition（11/03）：hierarchicalとscotchを、それぞれ固定なしと固定ありで比べた表（#36、4ノード）と、最も遅いrankの計算の中央値に対する比（1.46 → 1.16 → 1.06）の表です。固定と分割が互いの効果を大きくしたこと、つまり固定を先にした理由を見せます（Q41）。11/02から11/03までは「Pinning with hierarchical」（Baselineと、hierarchicalの固定なし・ありを交互に流した比較の図と表）でしたが、その比較は11/03に本編6枚目の図に入りました。
- Decompositions we tried：計測した分割の全部を、それぞれの対照に対する結果で並べた表です（ユーザー、11/02：ほかの分割方法も検討したか）。出典はノート（`deck/notes.py`の`s_decompositions`）。
- Other renumberings on Genkai（11/03）：renumberMeshのほかの並べ方を、玄界で課題のケースを使って既定と比べた表です（Q39）。表と文は`data/renumber_genkai.csv`から作ります（`build_deck.py`の`s_renumber()`）。

11/01に作った補足（Drag coefficient over the iterations、Where a Bonus step goes、Call stacks of a Bonus step）の説明は、gitの第7版（`0bb74e3`）のこの節にあります。

---

## 想定問答

英語の回答は、質疑で言う形の下書きです。各問の下に日本語訳（訳）を付けました。「見せる枚」は、答えるときに映すとよい枚で、番号は第8版のデッキの番号です（本編は2〜21枚目、補足は24〜43枚目、Q&A目次は23枚目）。ビルドが、番号と見出しがデッキと合うかを確かめます。今の発表から来そうにない問（Q3、Q11、Q12、Q14、Q25）は11/01に外しました。番号はほかの節から参照しているので、振り直していません。Q39（renumberMesh）は11/02の4回目に、Q40〜Q44は11/03に足しました。11/03から、本編の各枚のノートに、その枚に関係する問をここから引いて載せます（「（メモ）」の行は載せない）。
**Q1. Why ASPIRE-2A?**（なぜASPIRE-2Aを選んだのですか）
見せる枚：24（ASPIRE-2A and why we chose it）
- Last year we competed on Gadi, so this year we wanted to learn the other contest machine.
- Storage. OpenFOAM works with very many files: one unpacked OpenFOAM tree is about 36,000 files, and every decomposed 65M case adds thousands of `processor*` files. Our Gadi project has 1 TiB and about 212,000 files on `/scratch`; in August, three runs setting up at the same time already hit that file limit. On ASPIRE-2A we have 100 TB and 200 million files, so we could keep the builds, the decomposed cases and the raw records of every run.

訳：
- 昨年はGadiで出場したので、今年はもう一方の大会のマシンを学びたいと考えました。
- ストレージです。OpenFOAMは非常に多くのファイルを扱います。展開したOpenFOAMのツリー1つで約36,000ファイルあり、分割した65Mのケース1つごとに、数千個の`processor*`ファイルが加わります。Gadiの私たちのプロジェクトは、`/scratch`の枠が1 TiB、約212,000ファイルで、8月には、同時に準備をしていた3つのrunで、すでにこのファイル数の上限に達しました。ASPIRE-2Aでは100 TB、2億ファイルの枠があるので、ビルド、分割したケース、すべてのrunの生の記録を残すことができました。

- （メモ）Gadiの利用停止のことは自分からは言いません。「ノードが空いていた」は言いません（今回、4ノードは4時間以上、qdevの1ノードは3時間以上待った記録があります）。数字の出典は`platforms/gadi/README.md`（inode上限212,100、2026-08-17の3件同時の`Disk quota exceeded`）と、ASPIRE-2Aの`lfs quota`（100 TB、2億inode、2026-10-07）です。

**Q2. MPI waiting is large. Why didn't MPI tuning help?**（MPIの待ちが大きいのに、なぜMPIのチューニングは効かなかったのですか）
見せる枚：5（MPI calls on 4 nodes）、12（MPI after Basic）、11（What did not help in Basic）
- Most of the MPI time is waiting: ranks that finish early wait at the next exchange or global sum. Per-rank MPI time ranges from 20 to 37 s. Library or switch tuning cannot remove that wait; only less work or better balance can. The OpenFOAM communication switches we tried gave no gain. Two later checks agree: UCX over RC raised the IMB bandwidth between nodes by 55% but changed a step by −0.01% (Basic) and −0.16% (the Bonus of the first four changes), and moving the GAMG coarsest level, which issues 81% of the `MPI_Allreduce` calls, from 512 ranks to 32 changed it by −0.25%.

訳：
- MPIの時間の大部分は待ちです。早く終わったrankは、次の境界の交換か大域和で待ちます。rankごとのMPIの時間は20〜37 sです。ライブラリやスイッチの調整ではこの待ちはなくせず、なくせるのは仕事を減らすか、バランスを良くすることだけです。試したOpenFOAMの通信スイッチでは改善しませんでした。その後の2つの確認も、これと一致しています。UCX over RCでノード間のIMBの帯域は55%上がりましたが、1 stepの時間の変化は−0.01%（Basic）と−0.16%（最初の4つの変更のBonus）でした。また、`MPI_Allreduce`の呼び出しの81%を出すGAMGの最粗段を、512 rankから32 rankに移すと、変化は−0.25%でした。

**Q4. Is equal cell count enough?**（セル数をそろえるだけで十分ですか）
見せる枚：8（Decomposition）、21（What did not help in the Bonus）、33（Decompositions we tried）
- It mattered most. When we weighted cells by their face and point work, the cell counts became uneven and it got slower (+2.2%, +6.1%). A METIS two-constraint split balanced faces better but added 18% processor faces (+1.46%). The remaining imbalance (max/median 1.07) is still open.

訳：
- セル数をそろえることが最も重要でした。面と点の仕事量でセルに重みを付けると、セル数が不均一になり、遅くなりました（+2.2%、+6.1%）。METISの2制約の分割では、面のバランスは良くなりましたが、サブ領域の間の面が18%増えました（+1.46%）。残っている不均衡（max/median 1.07）は、まだ解決していません。

**Q5. Why did the weighting make it worse?**（なぜ重み付けで悪化したのですか）
見せる枚：21（What did not help in the Bonus）、33（Decompositions we tried）
- Static weights moved cells away from an even split: the cell-count imbalance grew to 1.073 with weight ×2. With ×12, the top-level split broke down and the faces between nodes grew five times.

訳：
- 静的な重みによって、セルの配分が均等な分割から離れました。重み×2で、セル数の不均衡は1.073まで大きくなりました。×12では最上位の分割が崩れ、ノード間の面が5倍に増えました。

**Q6. Why are the effects different on 1, 2 and 4 nodes?**（なぜ1、2、4ノードで効果が違うのですか）
見せる枚：20（Scaling from 1 to 4 nodes）、38（Effect of each Bonus change）、42（Why the speedup exceeds 4）
- On 1 node each rank holds four times more data than on 4 nodes, so more of it comes from DRAM. Removing array passes therefore saves more on 1 node (reading the U matrix once instead of three times: −6.4% against −2.3%; the ten later changes together: −12.2% against −9.3%). On 1 node we measured it for the first four changes: L1 refills from DRAM fall 17% while instructions fall 4%. On 4 nodes we tested the same idea by giving each core less memory bandwidth: with 64 ranks per node the first four changes gain 7.9% on all memory channels and 11.4% on half of them. This is also why the Bonus scales less well than Basic (4.34 against 4.61 times faster on 4 nodes than on 1): it saves most on 1 node. The same reasoning explains the super-linear scaling, and there we measured counters at 1, 2 and 4 nodes: per cell and step, the L1 refills from DRAM fall by 30% from 1 to 4 nodes, almost all in the sparse-matrix kernels, whose scattered cell arrays shrink to 1 MB per rank and fit in L3.

訳：
- 1ノードでは、各rankが4ノードのときの4倍のデータを持つので、そのうちDRAMから来る割合が大きくなります。そのため、配列をなめる処理を減らすと、1ノードのほうが大きく節約できます（Uの行列を3回ではなく1回だけ読む変更で−6.4%に対して−2.3%、後の10個の変更の合計で−12.2%に対して−9.3%）。1ノードでは最初の4つの変更についてこれを測り、DRAMからのL1 refillが17%減ったのに対し、命令数の減少は4%でした。4ノードでは、各コアが使えるメモリ帯域を減らして、同じ考えを確かめました。ノードあたり64 rankで、最初の4つの変更による改善は、すべてのメモリチャネルでは7.9%、半分のメモリチャネルでは11.4%でした。BonusがBasicほどスケールしない（4ノードで1ノードの4.34倍に対して4.61倍）のもこのためで、Bonusは1ノードで最も大きく節約します。同じ理屈で超線形のスケーリングも説明でき、こちらは1、2、4ノードでカウンタを測りました。1セル・1 stepあたりのDRAMからのL1 refillは、1ノードから4ノードで30%減り、そのほとんどは疎行列のカーネルでの減少です。これらのカーネルが飛び飛びに読むセルの配列は、1 rankあたり1 MBまで小さくなり、L3に収まります。

**Q7. What is proven and what is not?**（何が実証されていて、何が実証されていないのですか）
見せる枚：14（Measuring the memory limit）、19（Bonus results）、41（Drag coefficient checks）
- Proven: the timings (alternated controls, 3 or more runs on 4 nodes), the same computation (the first four changes: bit-identical `coefficient.dat` and identical solver logs, every residual to 16 digits; all fourteen: Cd within 0.0005% at 1, 2 and 4 nodes, F3), and the pinning problem (seen in `/proc` during the solve).
- Shown by experiment on 4 nodes: the step time follows the memory bandwidth, not the number of cores (half the cores: −1% to +2%; half the memory channels: 2.1–2.2× slower, as the bandwidth drops 2.22×), and the first four changes gain more when each core has less memory bandwidth.
- Measured with hardware counters (1 node, the first four changes): L1 refills from DRAM fall by 17% with 4% fewer instructions.
- Not proven: the DRAM traffic in bytes and the share of the peak bandwidth (we cannot read the memory-controller counters), how much of the memory effect is DRAM bandwidth and how much is L3 capacity, and the counters of the ten later changes. We present those as hypotheses. (The cache explanation of the super-linear scaling is now measured with counters at 1, 2 and 4 nodes; see Q6.)

訳：
- 実証済みのもの：時間（対照と交互に流し、4ノードで3本以上）、同じ計算であること（最初の4つの変更では、`coefficient.dat`がビット単位で一致し、ソルバのログも一致して、すべての残差が16桁まで同じ。14個すべてでは、1、2、4ノードでCdが0.0005%以内、F3）、そして固定の問題（求解中の`/proc`で確認）です。
- 4ノードの実験で示したもの：1 stepの時間がコア数ではなくメモリ帯域に従うこと（コアを半分にすると−1%〜+2%、メモリチャネルを半分にすると2.1〜2.2倍遅くなり、帯域は2.22分の1になる）、そして各コアが使えるメモリ帯域が少ないほど、最初の4つの変更の改善が大きくなることです。
- ハードウェアカウンタで測ったもの（1ノード、最初の4つの変更）：DRAMからのL1 refillが17%減り、命令数は4%減ったことです。
- 実証できていないもの：バイト単位のDRAMの転送量と、ピーク帯域に対する割合（メモリコントローラのカウンタを読めないため）、メモリの効果のうちどれだけがDRAMの帯域で、どれだけがL3の容量によるのか、そして後の10個の変更のカウンタです。これらは仮説として示しています。（超線形スケーリングのキャッシュによる説明は、今は1、2、4ノードでカウンタを測ってあります。Q6を参照してください。）

**Q8. Why rebuild OpenFOAM instead of using the site module?**（なぜサイトのモジュールを使わず、OpenFOAMをビルドし直したのですか）
見せる枚：25（Build, MPI and run settings）
- A single run with the site module gave the same speed (−0.08%). Our own build records exactly what ran, and the Bonus patches need a build anyway.

訳：
- サイトのモジュールで1回流したrunは、同じ速さでした（−0.08%）。自分たちのビルドなら何が実行されたかを正確に記録でき、Bonusのパッチにはどのみちビルドが必要です。

**Q9. Is AOCL-LibM allowed in Basic?**（AOCL-LibMはBasicで認められていますか）
見せる枚：25（Build, MPI and run settings）
- It is a math library linked through `FOAM_EXTRA_LDFLAGS`. Precision stays IEEE double, and we use no value-unsafe flags.

訳：
- `FOAM_EXTRA_LDFLAGS`でリンクする数学ライブラリです。精度はIEEEの倍精度のままで、値を変えうるフラグは使っていません。

- （メモ）関数によっては最後の桁がglibcと違い得ます。Basicの範囲かを聞かれたら、ビルド設定（F1）の範囲と考えていると答えます。

**Q10. Is multiLevel used in Basic?**（BasicでmultiLevelを使っていますか）
見せる枚：9（Scotch on the node tree）、15（multiLevel decomposition）
- No. Basic uses `scotch`, mapped onto the node's sockets and NUMA domains through the method's own settings (`scotchCoeffs`), which F1 leaves free in Basic. `multiLevel` is a different decomposition method, so it is part of the Bonus.

訳：
- いいえ。Basicでは`scotch`を使い、この手法自身の設定（`scotchCoeffs`）で、ノードのソケットとNUMA領域に対応付けています。F1では、この設定はBasicで自由に決めてよいことになっています。`multiLevel`は別の分割手法なので、Bonusに含まれます。

**Q13. Why is your Cd different from the organisers' reference?**（なぜCdが主催者の参照値と違うのですか）
見せる枚：40（Drag coefficient over the iterations）、41（Drag coefficient checks）
- With `scotch` and its defaults our Cd at 150 steps was 0.284049, against 0.283983 in the organisers' `scotch` runs (a relative 2.3e-4). When we ran the site module once with our own scripts and decomposition, we got their value exactly (0.28398300763231610). So that difference comes from our build (for example, we link AMD's math library), not from the decomposition or the method. Our final Basic maps the decomposition onto the node, and a different decomposition moves Cd at 150 steps: 0.293016 (+3.2%).

訳：
- 既定の設定の`scotch`で、私たちの150 stepのCdは0.284049でした。主催者の`scotch`のrunでは0.283983で、相対差は2.3e-4です。サイトのモジュールを私たちのスクリプトと分割で1回流すと、主催者の値と完全に一致しました（0.28398300763231610）。したがって、この差は分割や手法ではなく、私たちのビルドから来ています（たとえば、AMDの数学ライブラリをリンクしています）。最終のBasicは分割をノードに対応付けていて、分割が違うと150 stepのCdは動きます。0.293016（+3.2%）です。

**Q15. Why is your run-to-run spread so much smaller than the organisers'?**（なぜrunごとのばらつきが主催者よりずっと小さいのですか）
見せる枚：10（Basic results）、27（The organisers' reference）
- Our 5 Basic runs on 4 nodes lie within 0.18%; the organisers' 5 `scotch` runs spread over 12%. It is not UCX: our runs with the organisers' transport (OFI with `FI_OFI_RXM_USE_SRX=0`) also lie within 0.26%. The main remaining difference is the placement — every rank pinned with its memory on its NUMA domain. Our own Baseline without working pinning varied by 8% (3.53–3.82 s/step).

訳：
- 4ノードでの私たちのBasicの5本は0.18%以内に収まっていますが、主催者の`scotch`の5本は12%の幅でばらついています。UCXのためではありません。主催者と同じ転送方式（`FI_OFI_RXM_USE_SRX=0`を付けたOFI）で流した私たちのrunも、0.26%以内に収まっています。残る主な違いは配置で、すべてのrankを、そのメモリとともに自分のNUMA領域に固定しています。固定が効いていなかった私たちのBaselineは、8%ばらつきました（3.53〜3.82 s/step）。

**Q16. Why UCX and not the site's default OFI?**（なぜサイト既定のOFIではなくUCXなのですか）
見せる枚：25（Build, MPI and run settings）、29（Is the network the bottleneck?）
- In September, every 2- and 4-node run with the default OFI provider died with SIGBUS at `MPI_Finalize`, while UCX completed every run. The organisers have since found that `FI_OFI_RXM_USE_SRX=0` avoids the crash, so we compared again with everything else as in Basic (then without the mapping): 3 alternated 4-node runs each, OFI 2.942 against UCX 2.920 s/step (+0.77%, ranges not overlapping), the same Cd, no crash. Their other workaround, `FI_VERBS_PREFER_XRC=0`, was +0.50% (one run each), also with the same Cd. So UCX stays.

訳：
- 9月には、既定のOFIプロバイダを使った2ノードと4ノードのrunがすべて`MPI_Finalize`でSIGBUSにより落ちましたが、UCXではすべてのrunが完了しました。その後、主催者が`FI_OFI_RXM_USE_SRX=0`でこのクラッシュを避けられることを見つけたので、ほかはすべてBasicと同じ条件（当時は対応付けなし）で比べ直しました。4ノードでそれぞれ3本を交互に流し、OFIは2.942、UCXは2.920 s/stepで（+0.77%、範囲は重ならず）、Cdは同じで、クラッシュもありませんでした。主催者のもう1つの回避策`FI_VERBS_PREFER_XRC=0`は+0.50%（各1本）で、こちらもCdは同じでした。そのため、UCXのままにしています。

**Q17. Is the pinning fix allowed in Basic?**（固定の修正はBasicで認められていますか）
見せる枚：6（CPU and memory pinning）、7（Pinning results）
- Yes. It is job-script placement: `numactl` sets the memory policy before each rank starts, and `taskset` sets the CPU affinity from outside. F1 lists job scripts, rank placement and affinity as Basic. Our Basic runs do not use `LD_PRELOAD`, which would be Bonus work. We used it only in our first pinning experiments, and the Basic way is as fast.

訳：
- はい。これはジョブスクリプトでの配置です。各rankが始まる前に`numactl`がメモリポリシーを設定し、`taskset`が外からCPUアフィニティを設定します。F1は、ジョブスクリプト、rankの配置、アフィニティをBasicとして挙げています。Basicのrunでは`LD_PRELOAD`を使っていません。使えばBonusの作業になります。使ったのは最初の固定の実験だけで、Basicのやり方も同じ速さです。

- （メモ、11/03）Pinning resultsの図のhierarchicalの固定ありと、Decompositionの図の比較（#36、10/02）は、numactl＋見張りに置き換える前の、LD_PRELOADでMPI_Initの直後に固定し直す方法で測った実験です。scotchで2つの速さは同じでした（LD_PRELOADの2.919とnumactl＋見張りの2.917、`data/pinning.csv`）。Basicの記録（Basic resultsの5本）はnumactl＋見張りです。

**Q18. Can the organisers reproduce your Basic number?**（主催者はBasicの数値を再現できますか）
見せる枚：28（Reproducing our results）
- Yes. `build/build.pbs` builds from the official public sources, and `run/submit.sh 1|2|4` runs the whole Allrun chain with plain `qsub`. We re-ran them ourselves (the final Basic on 2026-10-16, the final Bonus on 2026-10-26): at every node count `coefficient.dat` was byte-identical to our recorded runs, and the time within 0.4% of our recorded means (Basic on 4 nodes: 2.9046 against 2.8976 s/step; Bonus on 4 nodes: 2.3651 against 2.3600).

訳：
- はい。`build/build.pbs`は公式の公開ソースからビルドし、`run/submit.sh 1|2|4`は普通の`qsub`でAllrunの一連の処理をすべて流します。私たち自身でも流し直しました（最終のBasicは2026-10-16、最終のBonusは2026-10-26）。どのノード数でも`coefficient.dat`は記録したrunとバイト単位で一致し、時間も記録した平均から0.4%以内でした（4ノードのBasic：2.9046に対して2.8976 s/step、4ノードのBonus：2.3651に対して2.3600）。

**Q19. Why did you not tune the hierarchical coefficients instead?**（なぜ代わりにhierarchicalの係数を調整しなかったのですか）
見せる枚：8（Decomposition）、31（Hierarchical against scotch）
- We kept the case default `(16 8 4)` as the control. scotch was 10.5% faster on 4 nodes in alternated runs, so we spent the remaining effort on scotch and on placement. We have not searched other `nHierarchical` factorisations.

訳：
- ケースの既定の`(16 8 4)`を対照として残しました。交互に流したrunでは4ノードでscotchが10.5%速かったので、残りの労力はscotchと配置に使いました。ほかの`nHierarchical`の因数分解は探索していません。

**Q20. What would you do next?**（次に取り組むなら何をしますか）
見せる枚：21（What did not help in the Bonus）、35（Call stacks of a Bonus step）
- Moving fewer bytes still: fuse the assembly of U, k and omega across terms, which removes a few more passes over the face arrays. (The GAMG residual with its restriction and the Laplacian coefficients with the diagonal, which we listed here before, are now done: `0015` and `0006`.)
- The remaining imbalance between ranks (Q21): the slower ranks are the ones that read more from DRAM. Weights and more even cell counts did not help, and on Genkai none of renumberMesh's other cell orders beat the default (Q39). Making the global sums cheaper (the GAMG coarsest level on fewer ranks) or the network faster (UCX over RC) did not help either (Q2).
- We expect a few per cent from these (Q34).

訳：
- 運ぶバイトをさらに減らすことです。U、k、omegaの組み立てを項をまたいで融合すれば、面の配列をなめる処理がさらにいくつか減ります。（以前ここに挙げていた、GAMGの残差とその制限、ラプラシアンの係数と対角は、今は`0015`と`0006`で実施済みです。）
- rankの間に残っている不均衡です（Q21）。遅いrankはDRAMから多く読むrankです。重みやセル数をもっと均等にすることは効かず、玄界ではrenumberMeshのほかの並べ方も既定より速くなりませんでした（Q39）。大域和を軽くすること（GAMGの最粗段を少ないrankで）や、ネットワークを速くすること（UCX over RC）も効きませんでした（Q2）。
- これらで数%の改善を見込んでいます（Q34）。

**Q21. Do you know where the imbalance between ranks comes from?**（rankの間の不均衡がどこから来るのか分かっていますか）
見せる枚：8（Decomposition）、21（What did not help in the Bonus）、42（Why the speedup exceeds 4）
- Partly. With OpenFOAM's own profiling on all 512 ranks, the computation per rank still varies by 6% (max/median 1.063). Cell counts are balanced within 1% and do not explain it; wall faces explain a little (r = 0.43, 2.8% of the work). Balancing the wall part perfectly would only take it to 1.056, so a wall-weighted split is not worth it. Nodes and NUMA domains show no systematic difference; the variation follows groups of neighbouring subdomains, so it is a property of the mesh regions. Hardware counters on 32 ranks of 4 nodes (#66) show what it is: the slowest and the fastest rank execute about the same number of instructions, but the slowest reads more than twice as many lines from DRAM. A rank's computation follows its DRAM refills (r = +0.69), not its instructions (r = −0.09) or its cells (r = +0.24): it depends on how well each subdomain's data fits in cache.

訳：
- 一部は分かっています。OpenFOAM自身のプロファイリングを512 rankすべてで取ると、rankごとの計算はまだ6%ばらついています（max/median 1.063）。セル数は1%以内でそろっていて、これでは説明できません。壁の面で少しは説明できます（r = 0.43、仕事の2.8%）。壁の部分を完全にそろえても1.056にしかならないので、壁で重み付けした分割はやる価値がありません。ノードやNUMA領域による系統的な違いはなく、ばらつきは隣り合うサブ領域のまとまりに沿っているので、メッシュの領域の性質です。4ノードの32 rankで取ったハードウェアカウンタ（#66）が、その正体を示しています。最も遅いrankと最も速いrankは、ほぼ同じ数の命令を実行していますが、最も遅いrankはDRAMから2倍を超える数のラインを読んでいます。rankの計算はDRAMからのrefillに従い（r = +0.69）、命令数（r = −0.09）やセル数（r = +0.24）には従いません。つまり、各サブ領域のデータがキャッシュにどれだけよく収まるかで決まります。

**Q22. Is the flow video from your scored run?**（流れの動画は採点対象のrunのものですか）
見せる枚：10（Basic results）
- No. Benchmark runs write no flow fields (`controlDict.noWrite`), so we ran the same official case once more with output function objects added: on Genkai, 4 nodes, 150 iterations, because ASPIRE-2A had no free nodes that day. It is a picture of the flow, not a measurement, and the flow does not depend on the machine. The added outputs do not change the computation: its Cd after 150 iterations, 0.28455000886604298, is identical to every digit with Genkai's official 4-node run.

訳：
- いいえ。ベンチマークのrunは流れ場を書き出さない（`controlDict.noWrite`）ので、出力用のfunction objectを加えて、同じ公式のケースをもう一度流しました。その日はASPIRE-2Aに空きノードがなかったので、玄界で4ノード、150反復で流しました。これは流れの絵であって測定ではなく、流れはマシンによりません。追加した出力は計算を変えません。150反復後のCdは0.28455000886604298で、玄界の公式の手順の4ノードのrunと全桁一致します。

- （メモ）自分からは言わず、聞かれたら答えます。Cdが全桁一致するのは同じ機械・同じ分割の公式runとで、ASPIRE-2Aの値とは分割が違うので数%違います（150 stepでは分割でCdが動きます、デッキの40枚目）。

**Q23. How do you know it is memory-bound if you could not read the memory counters?**（メモリのカウンタを読めなかったのに、どうしてメモリ律速だと分かるのですか）
見せる枚：14（Measuring the memory limit）、32（The placement experiment in full）
- On ASPIRE-2A users cannot read the memory-controller counters, so we tested it by moving the ranks. On 4 nodes, 64 ranks per node are as fast as 128 when they keep all memory channels, and 2.1–2.2× slower when the same 64 ranks share half of the channels — as much as the measured bandwidth drops. Compiler flags and PGO change nothing (within 0.13%), and our first four patches, which keep every operation, gain the most where memory is scarcest.

訳：
- ASPIRE-2Aでは利用者はメモリコントローラのカウンタを読めないので、rankを動かして確かめました。4ノードで、ノードあたり64 rankは、すべてのメモリチャネルを使えるときは128 rankと同じ速さで、同じ64 rankが半分のメモリチャネルを共有すると2.1〜2.2倍遅くなりました。これは測った帯域の低下と同じ大きさです。コンパイラのフラグやPGOでは何も変わらず（0.13%以内）、すべての演算を残したままの最初の4つのパッチは、メモリが最も乏しいところで最も大きく改善しました。

- （メモ）コアを半分にした比較は、分割が512から256に変わります。ただ、帯域に比例しない部分は1 stepあたり約0.1 sしかないので、分割の違いで「コアが半分でも同じ速さ」を説明することはできません。チャネルを半分にした比較は、分割もrankも同じです（#61）。

**Q24. Bandwidth or latency?**（帯域ですか、レイテンシですか）
見せる枚：14（Measuring the memory limit）、32（The placement experiment in full）
- Bandwidth. If the latency of each core's memory requests set the speed, halving the cores would halve the throughput; it changed by −1% to +2%. Halving the memory channels slowed a step 2.1–2.2×, in line with the bandwidth (2.22×).

訳：
- 帯域です。もし各コアのメモリ要求のレイテンシで速さが決まるなら、コアを半分にするとスループットも半分になるはずですが、変化は−1%〜+2%でした。メモリチャネルを半分にすると1 stepは2.1〜2.2倍遅くなり、帯域（2.22分の1）に見合っていました。

- （メモ）1コア2 rankのSMT（#43）では5.7倍遅くなり、どちらとも決められませんでした。今回の配置の実験で決まりました。

**Q26. MPI is 19% of a step. How can the step follow the bandwidth?**（MPIは1 stepの19%です。それなのに、どうして1 stepが帯域に従うのですか）
見せる枚：13（Profiling Basic）、14（Measuring the memory limit）
- Most of the MPI time is waiting for the slowest rank, and that rank's computation is bandwidth-bound, so the wait grows and shrinks with it. When we halved the memory channels, the whole step slowed with the bandwidth; only about 0.1 s per step does not scale with it.

訳：
- MPIの時間の大部分は最も遅いrankを待つ時間で、そのrankの計算は帯域律速なので、待ちもその計算に合わせて伸び縮みします。メモリチャネルを半分にしたときは、1 step全体が帯域に合わせて遅くなりました。帯域に比例しないのは、1 stepあたり約0.1 sだけです。

**Q27. Why was your Baseline slower than the organisers' hierarchical run (3.65 against 3.415 s/step)?**（なぜBaselineは主催者のhierarchicalのrunより遅かったのですか（3.65に対して3.415 s/step））
見せる枚：2（OpenFOAM on ASPIRE-2A）、30（Pinning and decomposition）、27（The organisers' reference）
- Our Baseline asked the launcher to pin each rank, but the binding was removed during `MPI_Init`, and each rank's pages ended up spread over all eight NUMA domains (9% on its own). The organisers' runs ask for no binding. We think that is why ours was slower, but we have not isolated it, because the build and the MPI transport also differ.

訳：
- 私たちのBaselineはlauncherに各rankの固定を指示していましたが、`MPI_Init`の間に固定が外れ、各rankのページは8つのNUMA領域すべてに散らばっていました（自分のNUMA領域にあったのは9%）。主催者のrunは固定を指示していません。私たちのほうが遅かったのはこのためだと考えていますが、ビルドとMPIの転送方式も違うので、この要因だけを切り分けてはいません。

**Q28. Are 40-step profile runs representative? Do the profilers change the result?**（40 stepのプロファイル用のrunは代表的と言えますか。プロファイラは結果を変えますか）
見せる枚：4（Profiling the Baseline）、5（MPI calls on 4 nodes）
- Yes. The case fixes every iteration count, so every step does the same work, and 40 steps show the same pattern as 150. The official case itself runs 40 steps on one node. We use profiles only to see where the time goes and why. The profilers change a step by −1% to +6%, so every time we report comes from runs without a profiler.

訳：
- はい。このケースはすべての反復回数を固定しているので、どのstepも同じ仕事をし、40 stepでも150 stepと同じ傾向が出ます。公式のケース自体も、1ノードでは40 stepを流します。プロファイルは、時間がどこに、なぜかかっているかを見るためだけに使っています。プロファイラを付けると1 stepの時間は−1%〜+6%変わるので、報告している時間はすべて、プロファイラなしのrunのものです。

- （メモ）`fvSolution.fixedIter`：pはGAMG 12サイクル（最粗段のPCG 35回）、Uの3成分は15回ずつ、kとωは8回ずつです（REPORT §2）。ケースは1/2/4ノードで40/80/150 stepです。40 stepでも、1 rankあたり約56万回の送信と約6.4万回の大域和を数えるので、割合は十分に安定します。プロファイルの時間を結果に使わないので、短くしても結果の精度は落ちません。

**Q29. In OpenFOAM, isn't the exchange across subdomain boundaries the bottleneck?**（OpenFOAMでは、境界の交換がボトルネックではないのですか）
見せる枚：11（What did not help in Basic）、29（Is the network the bottleneck?）
- Not by volume. Each subdomain exchanges the values on its processor faces at every solver iteration, but cutting the faces between nodes by 92% changed a step by +0.1%, and 55% more network bandwidth (UCX over RC) by −0.01%. What costs time is the synchronisation: about 1,600 global sums per step make every rank wait for the slowest one, and the slowest ranks have almost no neighbours on other nodes. So we fixed the placement and balanced the work instead.

訳：
- 量の点ではそうではありません。各サブ領域は、ソルバの反復のたびにサブ領域の間の面の値を交換しますが、ノード間の面を92%減らしたときの1 stepの変化は+0.1%、ネットワークの帯域を55%増やしたとき（UCX over RC）は−0.01%でした。時間がかかっているのは同期です。1 stepあたり約1,600回の大域和で、すべてのrankが最も遅いrankを待たされます。そして、最も遅いrankには、ほかのノード上の隣接rankがほとんどありません。そこで代わりに、配置を直し、仕事を均等にしました。

**Q30. Why does the Basic gain grow with the node count?**（なぜBasicの改善はノード数とともに大きくなるのですか）
見せる枚：20（Scaling from 1 to 4 nodes）、31（Hierarchical against scotch）
- Mostly through the decomposition: scotch gains 1.3%, 2.5% and 10.5% on 1, 2 and 4 nodes, and mapping it onto the node gains only on 4 nodes (0.7%). We think the axis-aligned cuts of hierarchical become more uneven when the subdomains are small, but we have not verified it.

訳：
- 主に分割によるものです。scotchによる改善は1、2、4ノードで1.3%、2.5%、10.5%で、それをノードに対応付けて改善したのは4ノードだけでした（0.7%）。サブ領域が小さいと、hierarchicalの軸に沿った切り方がより不均一になるのだと考えていますが、確かめてはいません。

**Q31. Did you profile the network?**（ネットワークのプロファイリングはしましたか）
見せる枚：4（Profiling the Baseline）、29（Is the network the bottleneck?）
- Yes, at three levels. Every benchmark run ends with an MPI benchmark (IMB) on the same nodes, so we know the bandwidth and the global-sum time of each job. CrayPAT gave the time and count of every MPI call on every rank, and each rank's message count matches its number of neighbours in the decomposition exactly. Then we changed only the network side: 55% more bandwidth (UCX over RC), 92% fewer faces between nodes, another transport (OFI). None made a step more than 0.25% faster. A rank's wait follows its own computation (R² 0.77), not its neighbours. We did not read NIC or switch counters.

訳：
- はい、3つのレベルでしました。ベンチマークのrunはすべて、最後に同じノードでMPIのベンチマーク（IMB）を流すので、ジョブごとの帯域と大域和の時間が分かります。CrayPATで、すべてのrankのすべてのMPI呼び出しの時間と回数を取りました。各rankのメッセージの数は、分割での隣接rankの数と正確に一致します。次に、ネットワーク側だけを変えました。帯域を55%増やし（UCX over RC）、ノード間の面を92%減らし、別の転送方式（OFI）を使いました。どれも、1 stepを0.25%を超えて速くはしませんでした。rankの待ちは自分自身の計算に従い（R² 0.77）、隣のrankには従いません。NICやスイッチのカウンタは読んでいません。

**Q32. Your third change skips boundary updates. Isn't skipping boundary checks prohibited?**（3つ目の変更は境界の更新を省いています。境界のチェックを省くことは禁止されていないのですか）
見せる枚：17（Source changes by intent (2/2)）、36（Source changes in detail (1/2)）
- It skips no check. At six places the code formed a surface integral (a divergence), built its boundary values, exchanged them across processor boundaries, and then used only the cell values. We form the same cell values with the same loop and skip only the boundary values that nobody reads. The boundary conditions of the solved fields, every exchange the solution uses, and the bounding of k and omega are unchanged; the bounding appears in our logs as often and with the same values as in the pre-change baseline.

訳：
- チェックは1つも省いていません。元のコードは6か所で、面積分（発散）を作り、その境界値を作り、それをサブ領域の境界をまたいで交換してから、セルの値だけを使っていました。私たちは同じループで同じセルの値を作り、誰も読まない境界値だけを省きます。解く場の境界条件、解が使うすべての境界の交換、kとomegaのboundingは変わりません。boundingはログに、変更前のrunと同じ回数、同じ値で現れます。

- （メモ）R2の禁止事項は「skipping boundary or validity checks」です。no unused boundary updatesは、内部の値しか使わない6か所（ラプラシアンの非直交補正、bounded対流項の`fvm::Sp`、補正付き対流項、連続の式の誤差、`pEqn.H`の右辺、kOmegaSSTの`divU`）で、`fvc::div`と`fvc::surfaceIntegrate`を`fvc::surfaceIntegrateInternal`に置き換えるだけです。中身は同じ`surfaceIntegrate`のループで、境界値を作って評価する処理（coupled境界の交換を含む）だけを省きます。

**Q33. Instructions fell 4%. Did you reduce the work per step?**（命令数が4%減りました。1 stepあたりの仕事を減らしたのですか）
見せる枚：19（Bonus results）、36（Source changes in detail (1/2)）、37（Source changes in detail (2/2)）
- Not the numerical work. Every solve does the same sweeps, residuals and norms as before: in the logs of the pre-change baseline and the Bonus of the first four changes, every solve of every step has the same iteration count and the same residuals, to 16 digits. The instructions we removed are copies, allocations and temporary face fields, the second and third pass over the same matrix arrays, and boundary values that nobody reads. The ten later changes keep the iteration counts and the convergence tests too; three of them change the order of some sums, and Cd moves by at most 0.0005%.

訳：
- 数値計算の仕事は減らしていません。どの求解も、以前と同じsweep、残差、ノルムを計算します。変更前のrunと、最初の4つの変更のBonusのログでは、すべてのstepのすべての求解で、反復回数が同じで、残差も16桁まで同じです。減らした命令は、コピー、メモリ確保、一時的な面の場、同じ行列の配列を2回目と3回目になめる処理、そして誰も読まない境界値です。後の10個の変更も、反復回数と収束判定を保っています。そのうち3つは一部の和の順序を変え、Cdは最大0.0005%動きます。

- （メモ）命令数−4.1%に対して、DRAMからのrefillは−17.2%、cyclesは−10.8%です（最初の4つ、補足のHardware counters）。ログの比較は本編18枚目のメモにあります（1/2/4ノードで371、771、1,475行が全行一致）。

**Q34. Is another 10% possible?**（さらに10%の改善は可能ですか）
見せる枚：21（What did not help in the Bonus）、35（Call stacks of a Bonus step）
- Not easily with the same math and the same work per step. Our third round found 9% more by removing ten more passes, copies and global sums, mostly in the turbulence model and the Gauss–Seidel sweeps. A step still follows the memory traffic, so only moving fewer bytes or reusing more data from cache can help. What is left, fusing the assembly of U, k and omega across terms, would give a few per cent, and on Genkai no other cell order beat the default (Q39). Gains of 10% more would need a different computation (fewer iterations, lower precision), which the rules prohibit, or skipping the residuals that only the convergence tests need, which works only because this benchmark fixes the iterations. That gave −8.2% on the final Bonus, but it is less work per step, so it counts in no tier and we left it out.

訳：
- 同じ数学のまま、1 stepあたりの仕事も同じでは、簡単ではありません。3回目の取り組みでは、主に乱流モデルとGauss–Seidelのsweepで、配列をなめる処理、コピー、大域和をもう10個減らし、さらに9%改善しました。1 stepは今もメモリの転送量に従うので、効くのは運ぶバイトを減らすか、キャッシュのデータをもっと再利用することだけです。残っているもの、つまりU、k、omegaの組み立てを項をまたいで融合することで得られるのは数%でしょう。玄界では、ほかのセルの並べ方も既定より速くなりませんでした（Q39）。さらに10%を得るには、規則で禁止されている別の計算（反復を減らす、精度を下げる）か、収束判定にしか使わない残差を省くことが必要でしょう。後者はこのベンチマークが反復回数を固定しているからできることで、最終のBonusで−8.2%でしたが、1 stepの仕事を減らすことになるので、どの段でも数えず、発表から外しました。
- （メモ、#68、11/02）：最終Bonusの上の0019（固定反復のsmoothSolverと最粗段のPCGで、反復ごとの残差と大域和を最後の反復の後の1回にする）：4ノード3本で平均2.166 s/step（SD 0.26%）、`coefficient.dat`は最終Bonusとバイト一致。運営の答え（11/02、Slack）：「fixedIterの下で残差の計算とそのAllreduceを省くのは1 stepの仕事を減らすことで、Bonusを含めどの段でも数えない。他のチームと比べる値は、残差を計算し続けるrunのものでなければならない。どこまで行くかを見せたいなら別の枚にしてよいが、採点しない。同じ残差をより安く計算し、計算も出力も続けるなら、自分の変更なしのrunと結果が合う限りBonusに残せる」。ユーザーの判断で、発表から外しました（第8版の最初の版の20枚目）。残差を省かずに安く作る0012と0016は、この答えのとおりBonusに残ります。

- （メモ）10/16には「数%の見込み」と答えていた案（GAMGの残差と制限、ラプラシアンの係数と対角）は0015と0006で入り、kOmegaSSTの場の式（0013）や残差の作り方（0016）と合わせて−9.3%でした。Basicでは、#61でノードあたり64 rank（全チャネル）が128 rankより1.1%速かった（対応付けの前、各2本）程度です。Gauss-Seidelの複数sweepを、更新の順序を保ったままキャッシュの中で回す（temporal blocking）なら大きく減らせる可能性はありますが、非構造メッシュではまだ研究の段階で、更新の順序を変える重ね合わせ（0018）はCdを1.2%動かしました。

**Q35. Why no roofline?**（なぜrooflineを示さないのですか）
見せる枚：13（Profiling Basic）、14（Measuring the memory limit）
- We measured the ceilings on one node: read bandwidth from L1, L2, L3 and DRAM (15.3 TB/s, 8.0 TB/s, 4.4 TB/s, 360 GB/s), under a nominal 4.1 TFLOP/s. But we cannot place measured points for the solver: the DRAM bytes need the memory-controller counters, which users cannot read, and the core counters miss the lines that the prefetchers bring in. So we showed the limit by experiment instead: halving the memory bandwidth makes a step 2.2× slower, halving the cores does not. The sparse-matrix sweeps do about 0.1 flop per byte, far below the compute ceiling.

訳：
- 1ノードで天井は測りました。公称4.1 TFLOP/sの下にある、L1、L2、L3、DRAMからの読み出し帯域です（15.3 TB/s、8.0 TB/s、4.4 TB/s、360 GB/s）。しかし、ソルバの測定点は置けません。DRAMのバイト数にはメモリコントローラのカウンタが必要ですが、利用者はそれを読めず、コアのカウンタはプリフェッチャが持ってくるラインを取りこぼします。そこで代わりに、実験で限界を示しました。メモリ帯域を半分にすると1 stepは2.2倍遅くなり、コアを半分にしてもそうはなりません。疎行列をなめるループは1バイトあたり約0.1 flopで、計算の天井よりはるかに下です。

- （メモ）天井はチームの測定（PBS 26004695、10/26、1ノード、128コア、各3回の中央値）。DRAM read 360 GB/sは読むだけのカーネルで、STREAM triad（約290 GB/s）とは読み書きの形が違います。チームがrooflineの1枚を作りましたが（10/26）、ソルバの点を測れないので、11/01からHPCでは示さないことにしました。

**Q36. Do you require a minimum gain, such as 1%?**（1%のような最低限の改善幅を求めていますか）
見せる枚：3（Criteria for keeping a change）
- No fixed minimum. A change is kept when every job with it beats every job without it, in alternated runs. That already demands a gain that stands clear of the spread between identical jobs, which is about 0.2% once the ranks are pinned. A 1% gain is five times that and passes almost every time. We started with a 1% minimum, before we had measured the spread; in September single jobs had been up to 90% slower. Once 29 pinned jobs on 4 nodes showed a standard deviation of 0.19%, we dropped it. Since then two smaller gains passed: mapping the decomposition onto the node, −0.7% with five jobs each, and one global sum per CG iteration, −0.3% with three jobs each and no overlap. A −0.4% change to the malloc thresholds did not separate from the spread, so we did not keep it.

訳：
- 決まった最低値はありません。交互に流したrunで、変更ありの全ジョブが変更なしの全ジョブより速いとき、その変更を残します。この条件だけで、同じジョブどうしのばらつきからはっきり離れた改善が必要になり、そのばらつきはrankを固定すれば約0.2%です。1%の改善はその5倍で、ほぼ毎回通ります。最初は、ばらつきを測る前に、1%の最低値で始めました。9月には、単発のジョブが最大90%遅くなっていました。4ノードで固定した29本のジョブの標準偏差が0.19%と分かったところで、この最低値をやめました。それ以降、より小さい改善が2つ通りました。分割のノードへの対応付け（各5本で−0.7%）と、CGの1反復につき大域和を1回にする変更（各3本で−0.3%、重なりなし）です。mallocの閾値の変更は−0.4%でしたが、ばらつきから分離できなかったので、残しませんでした。

- （メモ）REPORT §4。正規分布を仮定すると、3本ずつの判定が通る確率は、効果がなければ5%、改善がSDの2倍で62%、3倍で89%、5倍で99.8%です（本編2枚目のメモ）。採用した13段のうち11段は1%以上です。

**Q37. Did you really need a control run every time?**（本当に毎回、対照のrunが必要だったのですか）
見せる枚：3（Criteria for keeping a change）、26（Run-to-run variation over 92 jobs）
- For gains of our size, yes. The same build measured in two different periods differed by up to 0.35%, which is as large as several of our gains, from 0.3% to 1.3%. Comparing with a run from another day could hide a real gain or show one that is not there. Some periods were much worse: in September single jobs ran 84% and 91% slower, and one slow job once made us reject scotch, which later turned out to be 10.5% faster in alternated runs. The control also cost little. In a chain of changes the previous candidate became the next control, so for the ten later changes almost no extra runs were needed. For the large first fixes a control was not strictly necessary, but it kept every decision under one rule.

訳：
- 私たちの改善の大きさでは、はい、必要でした。同じビルドを2つの違う時期に測ると最大0.35%違い、これは0.3%〜1.3%という私たちの改善のいくつかと同じくらいの大きさです。別の日のrunと比べると、本当の改善を隠したり、ない改善を見せたりするおそれがあります。ずっと悪い時期もありました。9月には単発のジョブが84%と91%遅くなり、遅いジョブ1本のために一度scotchを捨てましたが、scotchは後に、交互に流したrunで10.5%速いと分かりました。対照のコストも小さいものでした。変更を順に重ねるときは、前の候補が次の対照になったので、後の10個の変更ではほとんど追加のrunが要りませんでした。最初の大きな修正では対照は厳密には必要ありませんでしたが、対照があることで、すべての判断を1つの規則で行えました。

- （メモ）同じコミットの時期違い：57b6567は2.718と2.708（−0.35%）、e2730dbは2.776と2.781（+0.19%）、20d285bは2.673と2.675、fa4f5b0は2.599（10/07）と2.597（#69の対照）と2.603（10/26）。どれも`data/changes_ab.csv`の3〜4本の平均です。scotchを一度捨てたのは9/27の1本（5.03 s/step）です。後の10個の比較では、前の候補のrunがそのまま次の対照です（同じActionsのrun ID）。

**Q38. Can you give a breakdown like VTune's top-down analysis?**（VTuneのトップダウン分析のような内訳を示せますか）
見せる枚：4（Profiling the Baseline）、13（Profiling Basic）
- Not from hardware counters. On ASPIRE-2A users cannot read the uncore counters or use IBS, and uProf gives only core counters. We built the breakdown from timers and experiments instead. In the Baseline, ranks spend about 42% of their time waiting in MPI, global sums take about 0.02 s of a step, file I/O 0.01% and OS noise 0.8%. After Basic, MPI is 19% of a step, and the placement runs show that about 97% of a step follows the memory bandwidth. These numbers come from different runs and tools, so they do not add up to exactly 100%.

訳：
- ハードウェアカウンタからは示せません。ASPIRE-2Aでは、利用者はuncoreのカウンタを読めず、IBSも使えません。uProfで取れるのはコアのカウンタだけです。そこで代わりに、タイマーと実験から内訳を作りました。Baselineでは、rankは時間の約42%をMPIの待ちに使い、大域和は1 stepのうち約0.02 s、ファイルI/Oは0.01%、OSのノイズは0.8%です。Basicの後では、MPIは1 stepの19%で、配置のrunからは、1 stepの約97%がメモリ帯域に従うことが分かります。これらの数値は別々のrunとツールから得たものなので、合計はちょうど100%にはなりません。

- （メモ）本編3枚目の表と、「数値の決まり」の「律速の寄与」の表です。約42%はWaitallとAllreduceの70.72 sを、rankのプロセスの時間169.57 sで割った値です（11/02の4回目に、46% × 90%から数えた約41%を直した）。約97%は、配置の実験の時間とSTREAMの帯域からの当てはめです（本編13枚目のメモ）。

**Q39. Why didn't you change renumberMesh?**（なぜrenumberMeshを変えなかったのですか）
見せる枚：43（Other renumberings on Genkai）、11（What did not help in Basic）
- In Basic the rules fix it, and all our jobs ran the default, Cuthill–McKee. For the Bonus we measured the other orders on Genkai, with the official case on four nodes, each order once in each of four rounds. No renumbering was 0.7 percent slower, spring 3 percent and a random order 11 percent, and reverse Cuthill–McKee was within the spread, faster in three rounds and slower in one. So no order beat the default, and every order also changed Cd, since this benchmark's Gauss–Seidel sweeps the cells in their order.
- If asked why the default leaves so little: the locality that renumbering buys is already there. The decomposition gives each rank a compact piece of 128,000 cells, about 1 MB per field, within its share of the L3 cache. Pinning keeps that cache and the rank's memory with its own core. And Cuthill–McKee keeps each face loop within about 2,500 cells, inside the L2. We measured this cache fit from 1 to 4 nodes, 30% fewer refills from DRAM per cell, and it is why Basic scaled 4.61 times. What still comes from DRAM is each array once per pass, which no order changes, so our Bonus removed passes instead.

訳：
- Basicではルールで決まっていて、私たちのジョブはすべて既定のCuthill–McKeeで流しています。Bonusに向けては、ほかの並べ方を玄界で測りました。課題のケースそのものを4ノードで、各並べ方を4巡の各巡で1回ずつです。並べ替えなしは0.7%、springは3%、乱数の順は11%遅く、逆順のCuthill–McKeeはばらつきの中で、3巡で速く1巡で遅くなりました。どの並べ方も既定より速くはならず、さらにどの並べ方もCdを変えました。この課題のGauss–Seidelは、セルを番号の順に掃くからです。
- 既定でなぜ残りが小さいのかと聞かれたら：並べ替えで得られる局所性は、すでにあります。分割で、各rankは12万8千セルのまとまった塊を受け持ち、1つの場は約1 MBで、そのrankが使えるL3の分に収まります。固定で、そのキャッシュとrankのメモリは、自分のコアのそばに留まります。そしてCuthill–McKeeが、面のループが一度に触るセルを約2,500個に収め、L2に載せます。このキャッシュへの収まりは、1ノードから4ノードでセルあたりのDRAMからのrefillが30%減ったことで測っていて、Basicが4.61倍速くなった理由でもあります。それでもDRAMから来るのは、各配列をループごとに1回読む分で、これはどんな並べ方でも変わりません。だからBonusでは、ループの回数を減らしました。

- （メモ、11/03）玄界の比較（ユーザー：ほかの方法では速くならないと否定できればよい。玄界でのテストはしてよい）：`renumber/README.md`、`data/renumber_genkai.csv`、補足43枚目。4ノード×112 rank、plain scotchの448分割、40反復、5つの並べ方（既定、RCM、none、spring、random）を1巡に1回ずつ、巡ごとに順番をずらして4巡。既定1.958 s/stepに対して、RCM −0.19%（−0.38、−0.49、−0.21、+0.31%）、none +0.70%、spring +3.26%、random +10.6%。Cdは並べ方ごとに4巡とも同じで、40反復目で既定に対してRCM −1.32%、none −1.21%、spring −0.65%、random +0.09%。玄界はコアあたりL2 2 MB（ASPIRE-2Aは0.5 MB）なので、ASPIRE-2Aの時間ではなく傾向として言います（「on Genkai」）。11/02までの弱いところ（ほかの並べ方を測っていない）は、これで「測った」と言えるようになりました。ASPIRE-2Aで測るなら、同じ比較を4ノードで流します。
- （メモ、11/03）2つ目の項目は、ユーザーの案「CPUとメモリを固定し、領域ごとにメッシュを分けているので、番号の振り直しはあまり問題にならない」を正確にした答えです。固定だけでは理由になりません（固定はキャッシュの中身を保つだけで、何が載るかは並びが決める）。分割（塊が小さくまとまる）、固定（キャッシュとメモリが自分のコアのそば）、Cuthill–McKee（塊の中の並び）の3つがそろって、局所性はすでに取れている、と言います。30%は#66のuProf（Basic、1/2/4ノード）で、1セル・1 stepあたりのDRAMからのL1 refillが4ノードで1ノードの0.70倍（19枚目のメモ、補足42枚目）。
- （メモ、11/02深夜）L2に収まる話、Cdが変わる話、v2512で選べる並べ方は、本編10枚目のメモにあります（Basicの4ノードのrenumberMeshのログ、v2512のソース、`fvSolution.fixedIter`、重ね合わせのCd −1.20%）。各サブ領域の並べ直しが最も遅いrank（DRAMから最も多く読む）に効く見込みは、玄界の結果からも小さいと考えます。
- （メモ、11/02の4回目に足した）ユーザー：変えなかったことを聞かれそう。やっていないのはマイナスの印象なので、根拠と次の手を言えるように。規則の出典はTask Rulesの補遺F1（l.204）、FAQ（l.262）、F2のBonusの例です。玄界の旧課題はcavity3D-64M、v2606、448 rank、2026-08-13の1本ずつで、なしに対してCuthill–McKee +0.91%、ブロック局所 +0.94%（FVOPS、`research/runtime-optimization-experiments.md`のPhase 5）。プロファイルは#40、#41、最も遅いrankとDRAMは#66（r = +0.69）。本編10枚目のメモも見てください。

**Q40. Outside MPI was the larger share in your Baseline. Why did you start with MPI?**（Baselineでは、MPIの外の方が大きかったのに、なぜMPIから始めたのですか）
見せる枚：4（Profiling the Baseline）、5（MPI calls on 4 nodes）、30（Pinning and decomposition）
- Because most of the MPI time was not MPI work. 42 of the 46 percent was ranks waiting, doing nothing, because the slowest rank was still computing, and with equal cells the slowest rank computed 2.1 times as long as the fastest. What makes a rank slow, where it runs and how the mesh is cut, is what Basic lets us change, while making the computing itself faster needs source changes, which is the Bonus.
- And /proc showed a known flaw: no rank stayed on its core and only 9 percent of its memory was local. Pinning a memory-bound code also speeds up its computing, since its memory becomes local. So Basic took 20.6 percent off a step, and the wait in Waitall fell by 76 percent.

訳：
- MPIの時間の大半は、MPIの仕事ではなかったからです。46%のうち42%は、最も遅いrankがまだ計算しているために、rankが何もせずに待っている時間で、セル数は同じなのに、最も遅いrankは最も速いrankの2.1倍の時間計算していました。rankを遅くするもの、つまりどこで動くかとメッシュの切り方は、Basicで変えられます。一方、計算そのものを速くするにはソースの変更が要り、それはBonusです。
- そして/procで、よく知られた欠陥が見つかりました。どのrankも自分のコアに留まらず、自分の領域にあるメモリは9%だけでした。メモリ律速のコードを固定すれば、メモリが近くなるので計算も速くなります。こうしてBasicは1 stepを20.6%短くし、Waitallの待ちは76%減りました。

- （メモ）ユーザーの問い（11/03）「BasicでMPIの方が割合小さく見えるのに、何でこっちを優先したのって聞かれてもおかしくない」への答えです。Profiling the Baselineの原稿の最後の2文が短い形です。

**Q41. Why did you pin before trying another decomposition?**（なぜ分割より先に固定したのですか）
見せる枚：7（Pinning results）、30（Pinning and decomposition）
- An unpinned rank moves between cores and leaves its memory spread over the node, so the slowest rank is wherever the placement went wrong, and the jobs vary a lot, by 4.1 percent for our Baseline. That hides what a better decomposition gains. Pinning first made every later comparison sharper: the jobs varied by 1.1 percent with hierarchical and 0.13 percent with scotch.
- The two fixes also helped each other. Without pinning, scotch saved 7.5 percent, and with pinning 10.5. Pinning saved 11.2 percent with hierarchical and 14.1 with scotch. The slowest rank computed 1.46 times as long as the median rank without pinning, 1.16 times once pinned, and 1.06 times with scotch as well.

訳：
- 固定されていないrankはコアの間を動き、メモリをノードじゅうに散らかすので、最も遅いrankは置き場所がうまくいかなかったところになり、ジョブのばらつきも大きくなります（Baselineで4.1%）。これでは、よい分割で得られる効果が隠れます。先に固定したことで、後の比較はどれもはっきりしました（ばらつきはhierarchicalで1.1%、scotchで0.13%）。
- 2つの修正は互いを助けました。固定なしではscotchは7.5%、固定ありでは10.5%短くしました。固定はhierarchicalで11.2%、scotchで14.1%短くしました。最も遅いrankの計算は、固定なしで中央値の1.46倍、固定すると1.16倍、scotchも入れると1.06倍でした。

- （メモ、11/03）固定なしのscotch対hierarchicalは同じ実験の中でも交互ではなく（10/02と10/03）、差はばらつき（SD 2.0%と0.78%）の2倍ほどなので、「helped each other」までにとどめます。遅いrankの比は道具が2つ混ざっています（OpenFOAM profilingとCrayPAT。補足30枚目のノート）。

**Q42. Did you look at CPU utilisation?**（CPU使用率は見ましたか）
見せる枚：13（Profiling Basic）、14（Measuring the memory limit）
- It cannot tell computing from waiting. The operating system counts a core as busy while it waits for memory, and MPI spins while it waits for other ranks, so every core would show close to 100 percent. The core counters tell them apart: in the solver the cores retired only 0.4 to 0.7 instructions per cycle. And the placement experiment did: half of the cores did the same work in the same time, so each core had room for twice the work.

訳：
- CPU使用率では、計算と待ちを分けられません。OSは、メモリを待っている間もコアを使用中と数え、MPIは他のrankを待つ間もCPUを回して待つので、どのコアも100%近くになるはずです。分けられるのはコアのカウンタで、ソルバの中でコアは1サイクルに0.4〜0.7命令しか実行していませんでした。そして配置の実験です。半分のコアで同じ仕事が同じ時間で終わったので、各コアには2倍の仕事をする余裕がありました。

- （メモ）ユーザーの案（11/03「CPU使用率を見るとかはどう？」）への答えです。私たちのrunのCPU使用率そのものは記録していないので、「would show」と言います。

**Q43. Why did no compiler setting help?**（なぜコンパイラの設定は効かなかったのですか）
見せる枚：11（What did not help in Basic）、13（Profiling Basic）、14（Measuring the memory limit）
- Because the cores were waiting for memory, not computing. The hottest loops do about 0.1 flop per byte, and the cores retired only 0.4 to 0.7 instructions per cycle. A compiler makes the instructions faster, not the memory. The placement experiment showed it directly: with half the cores a step took the same time.
- What helped was moving fewer bytes, which is our Bonus. On one node the first four source changes cut the L1 refills from DRAM by 17 percent while the instructions fell by only 4 percent, and a step got 12 percent shorter.

訳：
- コアが計算ではなく、メモリを待っていたからです。最も重いループは1バイトあたり約0.1 flopで、コアは1サイクルに0.4〜0.7命令しか実行していませんでした。コンパイラは命令を速くしますが、メモリは速くしません。配置の実験がそれを直接示しています。コアを半分にしても、1 stepの時間は同じでした。
- 効いたのは、運ぶバイトを減らすこと、つまりBonusです。1ノードで、最初の4つのソースの変更は、DRAMからのL1 refillを17%減らし、命令は4%しか減らさず、1 stepは12%短くなりました。

- （メモ、11/03）ユーザー：Basicでは結果だけを言い、メモリ律速だからという考察はBonusの側で。本編ではMeasuring the memory limitの原稿の1文（which is also why no compiler setting helped in Basic）です。

**Q44. Why not 128 ranks on 8 channels, or 32 ranks per node?**（なぜ8チャネルに128 rankや、ノードあたり32 rankを試さなかったのですか）
見せる枚：14（Measuring the memory limit）、32（The placement experiment in full）
- 8 channels belong to 4 NUMA domains of 64 cores, so 128 ranks there would put two ranks on a core, and two ranks per core was 5.7 times slower in its own right. 64 ranks on 8 channels keep one rank per core and the same decomposition as 64 ranks on 16, so only the channels change.
- Half of the cores were already as fast as all of them, so fewer cores would not have told us more. 32 ranks per node would also change the decomposition and make each rank's data four times larger, which mixes in the cache.

訳：
- 8本のチャネルは4つのNUMA領域、64コアのものなので、そこに128 rankを置くと1コアに2 rankになります。1コア2 rankは、それだけで5.7倍遅くなりました。8チャネルに64 rankなら、1コア1 rankのまま、16チャネルに64 rankと同じ分割で、チャネルの数だけが変わります。
- コアを半分にしても、すべて使うのと同じ速さだったので、コアをさらに減らしても分かることは増えません。ノードあたり32 rankでは分割も変わり、各rankのデータが4倍になって、キャッシュの効果が混ざります。

- （メモ）ユーザーの質問（11/02）への答えで、Measuring the memory limitのメモにあったものをまとめました。32 rank/ノードは流していません（4ノードのSUも限られていた）。STREAMはノードあたり16スレッド（L3ごとに1つ）で飽和するので、32 rankでも帯域は使い切れて、時間はほぼ同じと予想します。

---

## 発表の準備

- デッキは`deck/build.sh`で作ります（入力はBoxの10/31版のデッキのコピー、出力は`~/apac26/Tokyo Rapids with RIKEN Presentation HPC (8th edition).pptx`、3つ目の引数はBoxの`presentation/openfoam/decomposition/`の写し、作り方と確かめ方は`deck/README.md`）。並びは、表紙1、本編2〜21、補足の扉22、Q&A目次23、補足24〜43で、HPCだけのデッキです。スライドショーで映るのは1〜21枚目です。
- 本編のノートは、この文書の各スライドの節（原稿、訳、想定質問、補足）と想定問答の節から作ります。原稿や答えを直したら、この文書を直してビルドし直せば、ノートに入ります。メモはノートに入りません（11/03から）。
- 本編の図はFigure 1〜15、表はTable 1〜14です（各枚の節に番号を書いています）。図と表の注釈の文は`deck/build_deck.py`にあります。ノードのアイコンの図（5枚目）、CPUとメモリの帯の図（13枚目）、変更の図（17枚目）は、PowerPointの図形で描いています（`build_deck.py`の`node()`、`usage_bar()`、`u_diagram()`、`residual_diagram()`）。図の矢印と%、scalingの倍率も図形です（`overlay()`）。`decomposeParDict`の行（7、8、14枚目）は`code()`で、等幅の字（Consolas）で書きます。分割の絵の下の色の凡例（7、14枚目）は`numa_key()`です。
- 本編20枚を、タイマーで通して練習します（目安12分）。数字は読むのに時間がかかるので、語数から見積もった時間より長くなりがちです。各枚で「何を言わないか」も決めておきます。
- 数値は提出物の`README.md`と同じものを、有効数字4桁で使います（2.898／2.360、公式の結果（Official）の3.415／3.576、Baselineは3.650）。%は小数1桁です（−18.6%）。

## 根拠

- 公式のルール：`tasks/2. OpenFOAM HPC Task Rules.md`（Required contentの「MPI profiling and analysis are strongly recommended.」、Presentation Guidelines、Presentation Excellence）、`tasks/README.md`（R3、R4）、`tasks/5. Common Baselines.md`（10/20）。
- ISC26 SCCのOpenFOAM課題（Virtual Part、https://hpcadvisorycouncil.atlassian.net/wiki/spaces/HPCWORKS/pages/3700260877 、10/31に読み直した）：Task 2は1/2/4ノードのscalability、Task 3は4ノードでのMPIの上位3つ（回数と合計CPU時間）、Task 4はParaViewでの可視化とログからのCdの収束グラフ、Task 5（bonus）は分割方法を変えた効果です。どれも「チームの発表で示す」とあります。
- 図の元データ：リポジトリの`presentation/openfoam/data/`。主な数値の平均とSDは、11/01にこのフォルダのCSVから計算し直しました。主催者の参照値は`tasks/4.3 OpenFOAM Application Notes - ASPIRE-2A.md`とそのログ（`tasks/4.3-aspire2a-logs/`）です。
- 反復ごとのCd：Boxの`openfoam/results/<n>node/coefficient.dat`（Basic）、`openfoam/bonus/results/`（Bonus）、`openfoam/bonus/f3-baseline/`（ソースを変える前のrun）。
- call stack：`research/profile-reaggregation-fa4f5b0/`（#53のCrayPATのstack sampleの集計）。flame graphの元は`data/callstack_folded_fa4f5b0.txt`で、同じフォルダの`analyse.py`が、成果物の保管庫の生のsample（Actions 37529785072の`profile-raw.tar.zst`）から書き出します。
- ParaViewの絵と動画：`flow/README.md`（流れ）、`decomposition/README.md`（分割。第8版は`decomposition-numa.png`と、玄界で描いた`decomposition-numa-scotch-domains-vs-multilevel.png`を使う）。
- BasicのMPIの回数：Boxの`openfoam/analysis/pat-report-basic.txt`（37176272426、既定のレポートで、MPI_Testなど時間の小さい呼び出しは表に出ない）と`pat-report-baseline-calls.txt`（38219766511、`pat_report -T`で全部の呼び出し）。
- 第8版のために調べ直したこと（11/02、サブエージェント）：renumberMeshの扱い（#37、#40、#41、#69、`research/runtime-optimization-experiments.md`）、試した分割の全部（#32、#33、#35〜#38、#42、#45、#63）、BasicのCrayPAT（Boxの`openfoam/analysis/pat-report-basic.txt`、37176272426）、BaselineのよくされるMPI呼び出しの時間（38219766511）、rankごとの計算時間（38219862855、37714968610）、固定のジョブの日付（`data/pinning.csv`は10/03、第7版のメモの10/07は誤り）、multiLevelとBasicの比較（同じ時期には測っていない）。
- 固定が`MPI_Init`の中で外れることの診断：`TASK_2a.md`（PBS 24911705〜24944881。直前と直後の固定を記録した）。直し方はREPORT §6.1と`submission/openfoam/run/keep-rank-affinity.sh`。
- 実験の記録：issue #36〜#38（Basic）、#42、#44、#50、#51（Bonus）、#41、#53（profile）、#46（I/O、OSノイズ）、#47（ばらつき）、#48、#49（通信）、#54（提出スクリプトの再現）、#55（カウンタ）、#56、#60（OFIとUCX）、#57（OpenFOAM組み込みのprofiling）、#58（UCXのRC、GAMGの最も粗い段）、#59（PGO）、#61（コアとメモリのどちらが律速かを、配置だけを変えて確かめた実験）、#62（Baselineの1/2/4ノードとプロファイル）、#63（Basicのscotchの対応付け）、#66（ノード数ごとのカウンタ、rank間の不均衡）、#67（10/15の精査と取り組みの一覧）、#68（固定反復で使われない残差）、#69（Bonusの後の10個、最終計測、提出スクリプトでの再実行）。11/01の時点で、10/26の最終計測より新しい結果はありません（mainにもブランチにも、issueにもなし）。
- 各runの公式の結果（`result.txt`）と`coefficient.dat`：成果物の保管庫（Actionsのrun IDごとのフォルダ）。
- 採否の決め方のデータ：`data/changes_ab.csv`（変更ごとの対照と候補の各ジョブ）、`data/decomposition_basic.csv`（scotchとhierarchical、固定ありのhierarchical）、`data/compiler_options.csv`（2枚目の図のAOCC）、`data/start_unpinned.csv`（固定なしのhierarchical、本編6枚目と補足30枚目）と`data/pinning.csv`（scotchでの4通りの固定、本編6枚目。Neitherは補足30枚目の固定なしのscotchでもある）。
- 実験の順番（11/02の2回目に調べ直した）：ASPIRE-2Aでは最初からscotchで流した（`TASK_2a.md`の9月の項目。GNUの1ノードのbaselineもScotch 128分割）。9/20〜21に、2ノードのrunの配置の記録で固定が外れていると分かり、LD_PRELOADのinterposerで直した（`f0763e9`、`1f60daf`、`450def6`）。ケース既定のhierarchicalの4ノードは#34（9/24）。#36（10/02〜03）で、固定ありのhierarchical対scotch（交互）、固定なしのhierarchical、scotchでの4通りの固定を測り、numactl＋見張りに置き換えた（`5abefc1`、`8d54c41`）。scotchのdomainsは#38（10/05、−0.82%）で試し、#63（10/15〜16）で採用した。
- 提出物：Boxの`Tokyo_Rapids_with_RIKEN_Submission/openfoam/`（台本と説明はリポジトリの`submission/openfoam/`と同じ）。技術レポート（`REPORT.md`）と図（`figures/`）は、11/01に提出物から外しました。スライドの補足に分析と証拠がそろっていて、図はBoxの`presentation/`にあるからです（ユーザーの判断）。メモの「REPORT §n」は、gitの`c562b50`の`submission/openfoam/REPORT.md`の節です。
