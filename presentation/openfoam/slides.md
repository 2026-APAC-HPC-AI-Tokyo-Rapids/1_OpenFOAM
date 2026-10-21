# OpenFOAMパートのスライド構成（第4版）

チームのデッキ（Boxの`Tokyo_Rapids_with_RIKEN_Submission/presentation/Tokyo Rapids with RIKEN Presentation.pptx`）の新しい流れ（#52、10/13のメモ）に合わせて、第2版（本編9枚）を組み直したものです。第4版（10/19）では、旧課題の資料が勧めていた姿勢を話の筋道に取り込み、デッキにも反映しました（下の「旧課題の資料から取り入れた姿勢」）。

- スライドに載せる文は英語、話す内容（メモ）は日本語です。デッキのノートには、発表者が読む英語の原稿と日本語のメモの両方を入れてあります。
- 図と表はBoxの`presentation/openfoam/figures/`（`.png`は貼り付け用、`.svg`は編集用）にあります。分割の絵は`decomposition/`、流れの動画は`flow/`です。図は、リポジトリで`uv run presentation/openfoam/figures.py <出力先>`を実行すると作り直せます。
- デッキのOpenFOAMパートは、`presentation/openfoam/deck/build.sh`で、この文書の構成どおりに作り直せます（`deck/README.md`）。改訂版は`Tokyo Rapids with RIKEN Presentation (HPC revised).pptx`です。
- 数値はすべて公式指標`Average wall-clock time per time step`（2 step目以降の平均、秒/step）です。1点は1ジョブです。
- baselineは#62の測定（ケース既定のhierarchical、起動時の固定だけ、1/2/4ノード、2026-10-12）です。第2版の出発点3.670（#36、10/02〜03の4ノード3本）と同じ構成で、差は0.5%です。本編の数値は3.65にそろえます。

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

- Basicに、scotchの分割をノードの木（ソケット、NUMA領域、コア）に対応付ける`scotchCoeffs`を足しました（#63）。4ノードは2.92 → 2.90 s/step（−0.69%）です。本編と補足の数値と図を、すべて新しいBasicにそろえました。
- 「1%以上速いものだけ採用」という言い方をやめ、実際に使った採否の決め方（同じ時期に交互に流し、候補の全runが対照の全runより速い）で書きました（6枚目、17枚目）。run間のばらつきは約0.2%で、「1%未満はノイズ」とは言えないためです。
- 「もう10%速くならないのか」「rooflineは」に答えるQ34、Q35と、12枚目の演算密度の1行を足しました。#66のカウンタで、超線形（Q6）とrank間の不均衡（Q21）の説明も更新しました。
- 固定反復のときだけ効く#68の結果を、数えなかった結果として補足S17に置きました。本編の最後に見せるかは、チームで決めます。

### 10/17の更新

- 比べる基準は、同じビルド・同じスクリプト・同じ測り方で取った自分たちのbaselineにそろえます。主催者の参照（scotch 5本、平均3.30 s/step、ばらつき12%）は、ビルド、MPIの転送方式、配置が違うので、5枚目と補足S9で参考として見せるだけにします（主催者のscotchに対してBasicは−12%、Bonusは−21%）。
- 固定が`MPI_Init`で外れる問題は、主催者のASPIRE-2Aのノートに書かれておらず、主催者の参照runも固定していません。同じ機械を使うチームとの一番の差なので、9枚目のメモで、そう言うようにしました。
- 玄界の測定値は使いません。公式のクラスタはGadiとASPIRE-2Aだけで、ほかの機械の結果は私たちのASPIRE-2Aの結果の証拠になりません。流れの動画は計測ではないので、そのまま使います（Q22）。

### 10/19の更新（第4版）

- 旧課題の資料（old-tasksの`1_1_OpenFOAM_Measurements_and_Guidance.md`、`1_OpenFOAM_HPC_Task_Rules.md`、`README.md`）が勧めていた姿勢を、話の筋道として取り込みました。旧課題の数値（13.7%、93%、2.5倍など）は、#52の10/06のコメントどおり使いません。下の「旧課題の資料から取り入れた姿勢」にまとめました。
- デッキに反映しました。表とグラフはPowerPointの表とグラフにし、`tab*.png`は使いません。主張の1行は、20 ptで1行に収まる長さに短くし、この文書の**Message**もデッキと同じ文にそろえました。
- #68（固定反復のときだけ効く−13%）を、おまけとして本編の最後（19枚目）に置きました。補足S17から移したものです。
- 17枚目の見出しを「WHAT DID NOT HELP, AND WHY」に、主張を「Proxy metrics improved; the time per step did not」にしました。
- 18枚目（結論）を、旧Rules §8.2の最適化表の形（変えたこと、取り除いた律速とその証拠、4ノードでの効果）にし、最後に「HOW WE WORKED」の1行を置きました。
- 補足の扉の後ろに、クリックで各補足へ飛べるQ&A目次（21枚目）を足しました。
- 10/08版の旧スライド4枚（旧18・19・22・23枚目）を外しました。本編と重なり、Basic 2.9196や「10.97–12.69%」のような古い数値が残っていたためです。パッチ詳細の2枚（旧20・21枚目）は、補足の33・34枚目として作り直しました。
- 「数値の桁」の決まりを足しました。

### 10/20の更新

- MPIのプロファイル（呼び出し回数と時間の上位3つ）を、補足から本編7枚目「MPI PROFILE ON 4 NODES」に移しました。同じ主催者のISC26 SCCのOpenFOAM課題（[課題のページ](https://hpcadvisorycouncil.atlassian.net/wiki/spaces/HPCWORKS/pages/3700260877)）が、「4ノードで任意のMPIプロファイラを使い、呼び出し回数と合計CPU時間でそれぞれ上位3つのMPI呼び出しを発表で示せ」と求めているためです。本編は20枚になり、7枚目より後ろの番号は1つずつずれました。
- 補足の先頭（23枚目）に「OPTIMIZATION PLAN」を足しました。baseline → プロファイル → 律速 → 1つ変える → 対照と比べる、を繰り返す進め方と、実際の3回の回り方を1枚にしたものです。
- デッキの各スライドの下に残っていた1〜2.7 inの余白をなくし、内容を下端（約7.0 in、スライド番号の上）までそろえて配置し直しました。表の行と文字、グラフ、図を大きくし、残りは塊の間隔に配りました。主張と数値は変えていません。
- 11枚目（BASIC OPTIMIZATION (2/2)）の分割の絵に横断面の段を足し（4枚目と同じ3段）、20枚目（#68）の右側をカード2枚に、補足25枚目（EXPERIMENT AUTOMATION）の7段の流れに番号を付けました。
- ISC26の課題のほかの項目のうち、1/2/4ノードのscalingは本編17枚目、分割方法を変えた効果（Bonus）は11枚目と補足36枚目、ParaViewの絵は2枚目の動画で見せています。ログから描くCdの収束グラフは、まだデッキにありません。
- 表記をそろえました。`s/step`と書き（「s / step」をやめた）、%の前に空白を入れません（「21%」）。デッキ、ノート、この文書を直し、`tidy()`も「21 %」を「21%」に直します。図（`figures.py`の画像）の%と負の数も、`deck/deck_figures.py`でデッキの書き方にそろえます。
- 色を見直しました（`deck/palette.py`）。アクセントの紺と区別できるよう、Basicを青から緑に、baselineをプラムに、Bonusを焦げ橙にし、文字の色を濃くしました。赤は遅いもの・壊れているものだけに使い、改善の数字はその段の色で書きます。baseline、Basic、Bonusの語は、見出しと本文のどこに出てもその段の色になります（凡例なしで色を覚えられるように）。
- 4枚目のModulesを、表の外の灰色の注記から、表の最後の行に移しました。
- 14枚目（BONUS OPTIMIZATION）に、multiLevelの分割をノード（色相）とNUMA領域（濃淡）で塗った絵を足しました（Boxの`decomposition/panels/multiLevel-car-numa.png`）。サブ領域ごとに塗るとscotchとほとんど同じに見えるので、ノード → NUMA領域の木に沿って分けていることが見える塗り方にしました。
- 20枚目（#68）は%ではなく時間で書きました：2.595 → 2.250 s/step、使われない収束判定は1 stepあたり約0.35秒。
- 19枚目の「What remains」に出典（配置の実験、CrayPAT）を書き、最終Bonusの値にしました：最も遅いrankの計算は中央値の1.067倍（7%）、MPIはプロセス時間の19.9%（20%）。それまでの「6%」「19%」は、Basicのprofilingの値でした。

### 10/21の更新

- 提出物（`REPORT.md`、`README.md`、`analysis/README.md`、`bonus/README.md`）と`figures.py`の図も、`s/step`と「21%」の書き方にそろえました。Boxの`presentation/openfoam/figures/`と`openfoam/figures/`の図は、描き直したものに置き換えました。図の色は元のまま（Basicは青）で、デッキの図だけが`deck/palette.py`の色です。
- REPORT 13章の「6%（1.063）」「MPI 19%」はBasicの値で、19枚目の「7%」「20%」（最終Bonusの値）とは対象が違うだけです。

デッキ（チームのレビューの2回目）：

- 色を変えました（`deck/palette.py`）：baselineは緑、Basicは黄（濃い黄土色）、Bonusは赤で、作業が進むほど暖かい色になります。遅いもの・壊れているものは紫です。3枚目のGadiのquotaは、マイナス点として紫にしました。
- スライドの下に置いていた小さな注記（出典、但し書き）をやめ、ノートに移しました。issue番号（#62など）は、審査員がリポジトリを見ないので、スライドからすべて外しました（ノートには残します）。
- 図と表に、スライドの順に番号を付けました（本編Figure 1〜15・Table 1〜8、補足Figure S1〜S10・Table S1〜S11）。見出しは、何を比べているかが分かる文にしました。
- 速さを比べる図を、棒グラフから「各ジョブを点、平均を棒」で描く図にしました（`deck/deck_plots.py`）。ノード数ごとの時間、変化、何本で測ったかが1枚で見えます。5枚目（主催者のhierarchicalの値も図の中に書いた）、10、11、12、15、17枚目と、補足27、37枚目です。
- 7枚目：512 rank分の合計の注記を外し、ノートに残しました（聞かれたら答える）。上の1行を図の見出しにして、測ったのは全512 rankで値はその平均だと書きました。
- 8枚目：uProfの「Hottest functions」の小さな1行を「Where the computation goes」の箱にし（Gauss-Seidel、残差、A·xで計算の約4分の1）、LESSONの札は外しました。その言葉は9枚目の主張にしました。
- 9枚目：補足にあった進め方（OPTIMIZATION PLAN）を本編に上げ、OPTIMIZATION STRATEGYにしました。主張は「Fix what is broken first, then follow the measured bottleneck」です。それまでの律速 → 戦略の表は、補足23枚目（BOTTLENECKS WE MEASURED）に移しました。本編は20枚のままです。
- 10枚目：右の図の意図（CPUの固定とメモリの縛りは、片方だけでは速くならない）が伝わるよう、各ジョブの点の図にし、行の名前を「Both / CPU only / Neither / Memory only」にしました。
- 11枚目：最下行の斜体の教訓（1本で決めない）を外し、口頭で話します。
- 12枚目：「0 of 512 → 128 of 128 per node」を「0 of 512 → 512 of 512」にそろえました（各ノード128/128を4ノード分まとめただけで、同じことです）。右の大きな「2.90」を、4ノードの各ジョブの図にしました。
- 13枚目：札の「LESSON」を「TAKEAWAY」にしました。
- 14枚目：multiLevelをサブ領域ごとに塗った絵を、ノードとNUMA領域で塗った絵の左に並べました。3つの分割を並べた絵と、面の数と時間の表は、補足32枚目（THE THREE SPLITS: FACES OR EVEN WORK?）に足しました。
- 15枚目：表を、Basic、multiLevelだけ（ソース未改変、F3の照合相手）、Bonusの各ジョブの図にしました。
- 18枚目：表をBasicの案、Bonusの案の順に並べ、「Fewer faces?」の問いを足しました（面だけ減らしても速くならず、効いたのは仕事をそろえた分）。
- 19枚目：「What remains」を2つの箇条書きにし、「HOW WE WORKED」の札を右下の箱にして、「proxies」を「proxy metrics such as faces or counters」と言い換えました。
- 20枚目：LESSONの札を外し、「How we found it」（最終Bonusのcall stackで、毎sweepの残差とAllreduceの結果が、最後の1回以外は捨てられていた）を足しました。
- 補足42枚目（Not adopted）：Basicの案、Bonusの案、そのほかの工夫の順に並べ替えました（文は変えていません）。
- 共通の再現性スライド（旧43枚目）は、チームが10/21にpptxから外したので、`build_deck.py`でも外しました。

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

1. **問題解決の筋道で並べる。** baselineを測る → 測り方 → MPIのプロファイル → 何が遅いか → 戦略 → Basic（メモリの置き場所と仕事の均等さ）→ Basicの後に残る律速はメモリ帯域 → Bonus（運ぶデータを減らす）→ scaling → 効かなかったこと → まとめ → おまけ（数えなかった高速化、#68）。
2. **1枚1メッセージで軽くする。** 見出しはデッキと同じ大文字のラベルにし、その下に主張を1行書きます。図か表は1つ、強調する数字は1〜2個です。細かい数字はメモと補足に回します。
3. **測り方は1枚にまとめる（6枚目）。** 以降のスライドでは、道具の名前を括弧で添えるだけにします。
4. **BasicとBonusは同じ順で話す。** 何を変えたか → 結果 → プロファイルで確かめた理由。
5. **測ったことと仮説を分ける。** 並列効率が1を超える理由（セルの配列がL3に収まる）は、ノード数ごとのカウンタで確かめました（#66）。DRAMの転送バイト数と、ピーク帯域に対する割合は測れないので、未測定として話します。
6. **数値をデッキ全体でそろえる。** 4ノード：baseline 3.65、Basic 2.90（−21%）、Bonus 2.60（−29%、1.40×）。BonusはBasicから−10.3%。並列効率（1→4ノード）はbaseline 1.00、Basic 1.15、Bonus 1.12。参考：主催者のhierarchicalは3.415、scotchは5本の平均3.296（3.19〜3.58）。主催者のscotchに対して、Basicは−12%、Bonusは−21%。ただし主催者のrunはビルド、MPI、配置が違うので、本編の比較は自分たちのbaselineに対して行います。
7. **速さは各ジョブの点で見せる。** 平均だけの棒グラフにせず、ノード数ごとの時間、変化、本数が見える図にします（`deck/deck_plots.py`）。差を見せるため縦軸が0から始まらない図があるので、変化は図の中に%で書きます。
8. **小さな注記を置かない。** 出典とissue番号はノートに書き、図の条件は図の見出しの下の1行に書きます。図と表には番号（Figure 1、Table 1、補足はFigure S1、Table S1）を付けます。

### 旧課題の資料から取り入れた姿勢

旧課題（cavity3D、icoFoam、FVOPS）の資料は、作問者が実験の進め方として何を重んじるかを、測定つきで書いていました。課題は変わりましたが、審査員は同じなので、その姿勢を私たちの経緯で示します。旧資料の数値は使わず、私たちの測定で話します（#52の10/06のコメント）。

| 旧資料の考え方 | 出典 | 私たちの経緯 | 置いた場所 |
|---|---|---|---|
| 小さな改善を信じる前に、同じ構成を繰り返して自分のばらつきを知る。少ない本数はばらつきを小さく見せる | 1_1 §1.1、README | baselineは8%ばらつき、Basicでは0.18%。候補と対照を同じ時期に交互に流し、全runが対照より速いときだけ採用。9/27の1本（5.03秒）で一度scotchを捨て、交互の3本ずつで覆した | 6枚目（「Know the noise before trusting a gain」のカード）、11枚目のメモ（1本で決めない話） |
| 利得を探す前に、すでに壊れているものがないか確かめる。誤った固定1つで数倍遅くなり、どんな最適化も取り戻せない | 1_1 §2.2、README | 起動時に頼んだ固定が`MPI_Init`で外れていた（0/512、自領域のメモリ9%）。直すだけで−11% | 9枚目の主張「Fix what is broken first, then follow the measured bottleneck」、10枚目 |
| 最適化の価値は、取り除いた律速の分だけ。代理指標（境界面の数、行列の帯幅）は、時間を動かさずに大きく動き得る | 1_1 §2.1 | ノード間の面を92%減らしても+0.1%、ネットワークの帯域を55%上げても−0.01%、面の均衡を良くしたMETISは+1.46% | 18枚目の主張「Proxy metrics improved; the time per step did not」と「Fewer faces?」の行、補足32枚目 |
| 帯域の壁に近いなら、バイトを速く運ぶのではなく、運ぶバイトを減らす | 1_1 §2.3、README | チャネル半分で2.2倍遅く、コア半分では変わらない。コンパイラやPGOは±0.13%以内。Bonusは演算を変えずにDRAMからの読み込みを17%減らした | 13枚目のTAKEAWAY「Move fewer bytes, not the same bytes faster」、14〜16枚目 |
| 予算は仮説のためにあり、総当たりのためではない。12の筋の通った実験は、同じ結果の300 runに勝る | 1_1 §1、Rules §6.1、README | 測ったボトルネックから次の一手を決めた。効かなかった実験も、なぜ効かなかったかと一緒に見せる | 9枚目（進め方の5段と、実際の回り方の表）、18枚目、補足23枚目（律速の候補ごとに測ったこと） |
| 最適化表では「なぜ効くと考えたか」「律速だった証拠」の列が点の大半を占める | Rules §8.2 | 4つの採用した変更を、取り除いた律速とその証拠と一緒に並べる | 19枚目の表 |
| baseline、結果、その間の道筋を見せる。scalingを説明する。スライドの数字はすべて守れるように | Rules §9 | 本編の順序そのもの。4ノードの道筋は補足29枚目 | 本編全体、補足29枚目 |

結論の右下の「How we worked」（Know the noise · fix what is broken first · follow the measured bottleneck · judge by the time per step, not by proxy metrics such as faces or counters）は、この表の要約です。代理指標（proxy metrics）は、速さと関係しそうに見える別の量（ノード間の面の数、ネットワークの帯域、IPCや命令数）のことです。#68をおまけで見せるのも同じ姿勢で、「ベンチマークの取り決めにだけ効く高速化は数えない」と線を引けることを示します。

### 数値の桁

今の桁（4ノードのs/stepは3桁）のままでよいと考えます。run間のばらつきは4ノードで約0.2%で、2.90の最後の桁（0.01秒＝0.3%）とほぼ同じ大きさだからです。これより細かい桁はノイズで、粗くすると差が消えます。そのうえで、次のように使い分けます。

- **s/step**：本編の見出しと一覧の表は小数2桁（3.65、2.90、2.60、14.57など）。
- **1%未満の差を見せるとき**：差が見えるように小数3桁（scotchの対応付け2.918 → 2.898、#68の2.250 vs 2.595）。
- **証拠の表**：照合する相手と同じ桁。Bonusの1/2/4ノード（15枚目、13.365など）は提出物のREADMEと、再実行の表（補足41枚目）は記録の値と照合するので、元の桁のままです。
- **%**：1つの変更を自分の対照と比べた値は小数1桁（−10.5%、−0.7%、−10.3%）。baselineに対する累積（−21%、−29%）と見出しの丸め（「10% faster」「4% fewer」）は整数。倍率は1.40×。
- **他者の値**：出典の桁のまま引きます（主催者の3.415）。
- **書き方**：`s/step`と書き、%の前に空白を入れません（「21%」。%は単位ではないため）。負の数はマイナス記号（−）で書きます。
- 1枚の中で同じ量の桁を混ぜません。
- 注意：10枚目の見出し「3.65 → 3.26 s/step (−11%)」の3.65は#62のbaseline、3.26は#36の固定ありで、−11%は同時期の3.670 → 3.257（−11.2%）から来ています。3.26/3.65から計算すると−10.7%になるので、見出しは整数%のままにします。聞かれたら、Checkの行にある同時期の比較（3.67 → 3.26、3本ずつ）を示します。

### 時間配分

- 各スライドの目安は、ゆっくり話した場合の上限で、合計は約12分45秒（本編19枚で約12分10秒、おまけの20枚目が約35秒）です。発表は英語ネイティブが担当するので、少し速めに話せば20枚で約11分に収まります。
- Qwenに時間を回すときだけ、下の「削るとき」を使います。時間がなければ、おまけの20枚目を飛ばして、19枚目で終えます。
- 質疑（10分、Qwenと共通）は、補足スライドと想定問答で受けます。

---

## 本編（20枚、約12分45秒）

改訂版pptxの番号です。主張（Message）はデッキの文と同じです。「旧課題」の列は、上の「旧課題の資料から取り入れた姿勢」との対応です。

| # | 見出し（デッキ） | スライドの主張（1行） | 主な図 | 目安 | 旧課題 |
|---|---|---|---|---|---|
| 1 | Title | | | 0:10 | |
| 2 | OpenFOAM TASK OVERVIEW | Make the same math faster: same mesh, same solver, same work | 流れの動画、メッシュ、4ノードの結果（3.65 → 2.90 → 2.60） | 0:45 | |
| 3 | ASPIRE-2A | 8 NUMA domains per node; 16 cores already fill the bandwidth | 仕様の表、ノードの図（図形） | 0:35 | |
| 4 | BASELINE SETTINGS | We start from the case defaults, on our own build of v2512 | 設定の表、hierarchicalの分割の絵 | 0:35 | |
| 5 | BASELINE RESULTS | 3.65 s/step on 4 nodes: linear scaling, but slow and unsteady | Figure 5（各ジョブの点と、主催者のhierarchicalの値）、数字3つ | 0:30 | |
| 6 | HOW WE MEASURE AND PROFILE | Benchmark runs give the numbers; profile runs explain them | 道具の表、採否の決め方とノイズのカード | 0:35 | ノイズを先に知る |
| 7 | MPI PROFILE ON 4 NODES | Most calls are halo exchanges; most time goes to the calls that wait | 回数と時間の上位3つ（2枚のカード、棒） | 0:40 | |
| 8 | BASELINE ANALYSIS | Binding lost at MPI_Init → uneven computation → everyone waits | 3つの箱の鎖、「Why one slow rank matters」と「Where the computation goes」の箱 | 0:50 | 壊れているものを先に |
| 9 | OPTIMIZATION STRATEGY | Fix what is broken first, then follow the measured bottleneck | 進め方の5段（Baseline → Profile → Bottleneck → Change one thing → Check）、実際の回り方の表（Table 4） | 0:40 | 壊れているものを先に、仮説から次の一手 |
| 10 | BASIC OPTIMIZATION (1/2) | Putting the lost binding back: 3.65 → 3.26 s/step (−11%) | 原因 → 対策 → 確認、Figure 7（各ジョブの点：Both / CPU only / Neither / Memory only） | 0:50 | 壊れているものを先に |
| 11 | BASIC OPTIMIZATION (2/2) | scotch cuts compact blocks: 3.26 → 2.92 s/step (−10.5%) | hierarchicalとscotchの絵、Figure 9（1/2/4ノードの各ジョブ）、対応付け | 0:40 | 1本で決めない（メモ） |
| 12 | BASIC RESULTS | −21% on 4 nodes, and the profiles show why | before/afterの表（Table 5）、Figure 10（4ノードの各ジョブ） | 0:35 | |
| 13 | MEMORY BANDWIDTH SETS THE SPEED | Half the memory channels: 2.2× slower. Half the cores: no change | 2つの実験のカード（チャネルの図）、TAKEAWAY | 0:45 | 運ぶバイトを減らす |
| 14 | BONUS OPTIMIZATION | The same arithmetic with fewer bytes moved | multiLevelの絵2枚（サブ領域ごと、ノードとNUMA領域）、変更の一覧、Uを1回で読む図（図形） | 0:50 | 運ぶバイトを減らす |
| 15 | BONUS RESULTS | Bit-identical Cd, and 10% faster than our Basic | Figure 13（Basic、multiLevelだけ、Bonusの各ジョブ）、R3の4点のカード | 0:35 | |
| 16 | BONUS ANALYSIS | 4% fewer instructions, but 17% fewer refills from DRAM | カウンタの棒グラフ、配置の実験、CrayPAT | 0:35 | 運ぶバイトを減らす |
| 17 | SCALING ANALYSIS | Faster at 1, 2 and 4 nodes; parallel efficiency 1.00 → 1.15 | Figure 15（3つの段の各ジョブ、対数軸）、s/stepと効率の表 | 0:40 | scalingを説明する |
| 18 | WHAT DID NOT HELP, AND WHY | Proxy metrics improved; the time per step did not | 効かなかったことの表（Basic、Bonusの順）、3つの問い | 0:40 | 代理指標は時間を動かさない |
| 19 | CONCLUSION | 1.40× faster on 4 nodes, with the same math | 数字3つ、最適化表、What remains、How we worked | 0:40 | 最適化表、全体の要約 |
| 20 | EXTRA: A GAIN WE DID NOT COUNT | 2.595 → 2.250 s/step and bit-identical, but only with fixed iterations | 数字3つ、見つけた経緯、何をするか、数えない理由 | 0:35 | 代理指標と同じ線引き |

旧pptxの18〜24枚目（10/08版の旧スライド）のうち、18・19・22・23枚目は本編と重なるので外し、20・21枚目（パッチの詳細）は補足35・36枚目として作り直しました。24枚目（再現性）はQwenと共通のスライドでしたが、チームが10/21にpptxから外したので、改訂版にも入れていません。

### 1. Title（0:10）

旧pptxの1枚目のままです。ノートだけ足しました。

### 2. OpenFOAM TASK OVERVIEW（0:45）

**Message:** Make the same math faster: same mesh, same solver, same work

- Case: steady flow around a car at 140 km/h; simpleFoam (k-ω SST), OpenFOAM v2512
- Mesh: `occDrivAerStaticMesh`, 65.3 M cells, finest near the car; the mesh is fixed
- Step: fixed solver iterations → the same work every step
- Metric: average time per step (steps 2 to N) on 4 nodes; scaling on 1 / 2 / 4 nodes (40 / 80 / 150 steps)
- Our result on 4 nodes: 3.65 (Baseline) → 2.90 (Basic, −21%) → 2.60 s/step (Bonus, −29%); 1.40× faster with the same build, scripts and measurement

図：流れの動画（Boxの`flow/flow-iterations.mp4`）と、メッシュの図（旧pptxの2枚目のもの）。結果は左下の帯に、答えを先に出す形で置きました。

メモ（45秒）：
- 車の周りの空気の流れを計算するケースを、同じ計算のまま速くする課題です。メッシュは固定で、車の近くほど細かく、車輪は回りません。
- 反復の回数が固定です（`fvSolution.fixedIter`：pはGAMGで12サイクル、Uは3成分それぞれGauss-Seidelで15回、kとωは8回）。どのstepも同じ仕事なので、1 stepの平均時間で比べられます。
- 動画は、場を書き出すための別runです。計測runは場を書き出さないので、同じ公式ケースに出力だけを足して流しました（Q22）。
- 最後に答えを先に言います：「4ノードで3.65秒だった1 stepが、Basicで2.90秒、Bonusで2.60秒になりました」。比べる基準は、同じビルド・同じスクリプト・同じ測り方で取った自分たちのbaselineです。主催者の値は、ビルド、MPI、配置が違うので、5枚目で参考として見せます。

### 3. ASPIRE-2A（0:35）

**Message:** 8 NUMA domains per node; 16 cores already fill the bandwidth

- Processor: 2 × EPYC 7713 (Zen 3): 128 cores, 2.0 GHz
- NUMA, cache: 8 NUMA × 16 cores; 32 MB L3 per 8 cores
- Memory: 512 GB DDR4-3200, 16 channels, 409.6 GB/s peak; ≈ 290 GB/s (STREAM triad), reached with only 16 of 128 cores (one per L3)
- Network: HPE Slingshot-10 (100 Gb/s), dragonfly
- Software: Cray PE: GCC 11.2, Cray MPICH 8.1.15, PBS Pro
- Why ASPIRE-2A: OpenFOAM works with very many files. Gadi project quota: 0.2 M files, 1 TB; ASPIRE-2A: 200 M files, 100 TB

図：ノードの図（2ソケット × 4 NUMA領域、各16コア・2チャネル）。`fig11_node_layout`は文字が約5 ptで投影すると読めないので、PowerPointの図形で描き直しました。

メモ（35秒）：
- 旧pptxの「EPIC」は「EPYC」に、「4x NUMA domains」は「8 NUMA domains（ソケットあたり4）」に直しました。
- 帯域はカタログ値で409.6 GB/sですが、STREAMでは約290 GB/sで、L3ごとに1コア（ノードで16コア）使うだけで飽和します（#36）。これが後の「メモリ帯域が律速」の伏線です。
- 選んだ理由はファイル数と容量の上限です（Q1）。OpenFOAMのビルド1つで約36,000ファイル、分割したケースごとに数千ファイルが増えます。
- ネットワークの出典：TOP500のシステム名が「ASPIRE 2A (CPU Partition) - HPE Cray EX425, AMD EPYC 7713 64C 2GHz, Slingshot-10」です（https://top500.org/system/180078/）。NSCCのページには「All nodes are connected with HPE Slingshot Interconnect (Dragonfly Topology)」とあります（https://www.nscc.sg/aspire-2a/）。100 Gb/sはSlingshot-10の世代のNICの速さです（NSCCのページで「100G」と書いてあるのはHigh Frequency nodesの項）。ジョブから見えるNICはMellanox製（mlx5）で、UCXとOFIのどちらも使えます。

### 4. BASELINE SETTINGS（0:35）

**Message:** We start from the case defaults, on our own build of v2512

- Build: official v2512, GCC 11.2 `-O3`, AMD AOCL-LibM; Cray MPICH 8.1.15 over UCX
- Decomposition: case-default `hierarchical`, (16 8 1) / (16 8 2) / (16 8 4) on 1 / 2 / 4 nodes
- Placement: 128 ranks per node, one per core, bound by the launcher (`mpiexec --cpu-bind depth`)
- Measurement: at least 3 jobs per condition; each point is one job
- Modules（表の最後の行）: `PrgEnv-gnu/8.3.3`, `aocl/4.0.0`, `cray-mpich-ucx/8.1.15`

図：hierarchicalの分割の絵（車体表面、中心断面、横断面の3段。旧pptxの`decomposition-subdomains.png`から左の列を切り出したもの）。scotchの絵は11枚目まで見せません。

メモ（35秒）：
- OpenFOAMは公式のソースから自分たちでビルドしました。サイトのモジュールと同じ速さで（−0.08%、Q8）、何を使ったかを正確に記録でき、Bonusのパッチも当てられます。ccacheで、作り直しは60分から5分半になりました。
- UCXにした理由（pptxのメモのとおり）：既定のOFIでは、9月に2・4ノードのrunが毎回`MPI_Finalize`でSIGBUSになり、UCXでは全runが完走しました。主催者が後で見つけた2つの回避策も、私たちの構成ではUCXより遅いです（+0.77%、+0.50%。Q16）。
- 配置はサイトの推奨どおりの起動方法です。「ここで頼んだ固定が、実は外れていた」が8枚目につながります。

### 5. BASELINE RESULTS（0:30）

**Message:** 3.65 s/step on 4 nodes: linear scaling, but slow and unsteady

- 3.65 s/step on 4 nodes (mean of 3 jobs)
- 4.0× from 1 to 4 nodes: parallel efficiency 1.00
- 8% spread between jobs of one setup (3.53–3.82 s/step)
- （図の下に強調）Slow and unsteady at the same time: a sign that something is misconfigured

図：Figure 5「Time per step on 1, 2 and 4 nodes, each job」（`deck/deck_plots.py`の`p05_baseline_scaling`）。各ジョブの点と平均の棒、1ノードの平均から引いた理想の線、主催者のhierarchicalの1本ずつを白丸とその値（14.67／7.12／3.41）で描きます。右に数字3つ。以前の下の注記（主催者の3.415はサイトのビルド・既定のMPI・固定なし、比較は自分たちのbaselineに対して）は、図の凡例と口頭に移しました。

旧課題との対応：「遅くて不安定」は、旧資料が「baselineから大きく外れるなら設定の誤り」と言っていた形そのものです。ここで「何かがおかしい」と言い切ると、7・8枚目の発見が筋道としてつながります。

メモ（30秒）：
- 「スケーリングはきれいだが、遅く、ばらつく」。ばらつきは、固定が外れて遅いrankが毎回違う場所に出るためで（#36の症状）、8枚目で原因を示します。
- 1ノードの分割は(16 8 1)で、主催者の(16 4 2)と違います（図の注記）。
- 測った日が違う値を並べられる理由：baselineと同じ日（10/12）に流したscotchの対照は、10/05の平均から0.2%以内でした。10/15〜16に流したscotchとBonusの対照も、それぞれ10/05、10/06の平均から0.2%以内です。だから、baseline（10/12）、Bonus（10/06）、Basic（10/15〜16）を並べられます。#36の3本（10/02〜03、平均3.670）とも0.5%で合います。

### 6. HOW WE MEASURE AND PROFILE（0:35、新規）

**Message:** Benchmark runs give the numbers; profile runs explain them

| Tool | When it runs | Question it answers |
|---|---|---|
| Official metric | Every benchmark run, no profiler | How long does a step take? |
| IMB-MPI1 | After the solver, every benchmark run | How fast is the network between these nodes? |
| CrayPAT | Profile runs: 4 nodes, 40 steps | Which MPI calls take the time, per rank? |
| OpenFOAM profiling | Profile runs | Which solver stage takes the time, per rank? |
| AMD uProf | Profile runs | Which functions use the CPU? Hardware counters |
| `/proc` in the job | Profile runs | Is each rank on its own core? Where is its memory? |

下に2枚のカード：
- Decision rule：Candidate and control alternate in the same period, at least 3 jobs each on 4 nodes. A change is kept only if every job with it beats every job without it.
- Know the noise before trusting a gain：One setup, repeated: 8% spread in our baseline, 0.18% after Basic. Profilers shift a step by −1% to +6%, so profiled times are never results.

図：上の表（PowerPointの表）。`tab06_profiling`は古い結果が入っているので使いません。

旧課題との対応：旧資料が「いちばん安く、いちばん飛ばされる実験」と呼んでいた、ばらつきを先に測ることです。2枚目のカードの見出しは、その考え方をそのまま言葉にしたものです。

メモ（35秒）：
- プロファイラは1 stepの時間を−1%〜+6%変えます（baselineでは、CrayPATの下で3.85秒、計測runで3.65秒）。だからプロファイルの時間は比較に使わず、「どこで」「なぜ」にだけ使います。
- 40 stepで足りる理由：反復回数が固定なので、どのstepも同じ仕事です。
- 道具は、それぞれ1つの問いに答えます。CrayPATはMPIの関数ごとの時間と回数、OpenFOAM組み込みのprofilingは区間ごとの時間を全512 rankで、uProfは関数ごとのCPU時間とハードウェアカウンタ、`/proc`は実行中のCPUの固定とメモリのページの置き場所です。
- ネットワークは、毎回のrunでsolverの後にIMB（MPIのベンチマーク）を流し、そのノードどうしの帯域と大域和の時間を記録しています。ネットワーク側だけを変える比較もしました（補足S16、Q31）。NICやスイッチのハードウェアカウンタは読んでいません。
- メモリコントローラのカウンタは、利用者には読めません（`perf_event_paranoid=2`）。そこで帯域は、rankの置き場所を変える実験で確かめました（13枚目）。
- 採否の決め方：候補と対照を同じ時期に交互に流し（4ノードで3本以上ずつ）、候補の全runが対照の全runより速いものだけを採用しました。採用した変更は、4ノードではどれもこれを満たします。run間のばらつきは4ノードで約0.2%なので、0.7%の差（scotchの対応付け、5本ずつ）でも区別できます。最初は「1%以上」も条件にしていましたが、ばらつきが小さいとわかってから外しました。

### 7. MPI PROFILE ON 4 NODES（0:40、10/20に補足S1から移動）

同じ主催者のISC26 SCCのOpenFOAM課題が求める「4ノードで任意のMPIプロファイラを使い、呼び出し回数と合計CPU時間でそれぞれ上位3つのMPI呼び出しを示す」に答える1枚です。

**Message:** Most calls are halo exchanges; most time goes to the calls that wait

図の見出し（Figure 6）：CrayPAT on our baseline: 4 nodes, all 512 ranks, 40 steps; values per rank are the mean of the 512 ranks

左のカード「Top 3 by number of calls」（calls per rank in 40 steps, of 1.82 M MPI calls per rank）：
1. `MPI_Isend` 566,107
2. `MPI_Irecv` 566,107
3. `MPI_Test` 563,646
- 93% of all calls: the non-blocking halo exchange with the neighbouring subdomains

右のカード「Top 3 by total time」（seconds per rank, and share of the 78.3 s of MPI per rank）：
1. `MPI_Waitall` 43.1 s（55%）
2. `MPI_Allreduce` 27.6 s（35%）
3. `MPI_Bcast` 2.5 s（3%）
- 90% of the MPI time waits for other ranks, and MPI is 46% of a rank's time

最下段：Waiting, not transfer: MPI time per rank ranges from 35 to 112 s, with equal cell counts

512 rank分の合計（MPI_Isend・MPI_Irecvは各2.90億回、MPI_Testは2.89億回、CPU時間はMPI_Waitall 22,100 s、MPI_Allreduce 14,100 s、MPI_Bcast 1,290 s）は、10/21にスライドから外してメモに残しました。順位は合計でもrankあたりでも同じです。

図：2枚のカード。各行に順位、関数名、値と、上位の値に対する長さの棒（回数は紺、待つ呼び出しである時間の上位2つは紫）。

メモ（40秒）：
- 回数の上位3つは、隣のサブ領域とのデータ交換（非ブロッキングの送受信と、その完了の確認）です。時間の上位3つのうち、WaitallとAllreduceは他のrankを待つ呼び出しです。
- 測ったのは全512 rankで、値はrankあたり（512 rankの平均）です。課題の「合計CPU時間」は512 rank分を足した値で、聞かれたら答えます（MPI_Waitall 22,069 s、MPI_Allreduce 14,140 s、MPI_Bcast 1,289 s）。順位はどちらでも同じです。
- 待ちであって転送ではありません。rankごとのMPI時間は35〜112秒ですが、セル数はほぼ完全に均等です。なぜ遅いrankが出るのかは、次の8枚目で示します。
- Basicの後（#53）も回数の上位3つは同じで、時間はMPI_Allreduce 48%、MPI_Waitall 38%に入れ替わります。MPIはstepの19%になります（12枚目）。
- 出典：CrayPAT 38219766511（#62）、`data/baseline_profile_4node.csv`。

### 8. BASELINE ANALYSIS（0:50）

**Message:** Binding lost at MPI_Init → uneven computation → everyone waits

図：3つの箱を矢印でつなぐ（PowerPointの図形。`fig24_baseline_chain`と同じ内容）
1. Binding lost (`/proc` during the solve): 0 / 512 ranks on their own core; removed during `MPI_Init`; 9% of a rank's memory on its own NUMA domain (random: 12.5%)
2. Uneven computation (OpenFOAM profiling, 512 ranks): slowest / median 1.46×; 54–115 s per rank in 40 steps; cell counts equal within 0.002%
3. Everyone waits (CrayPAT): MPI is 46% of the time, `MPI_Waitall` 55% and `MPI_Allreduce` 35% of it

下に2つの箱（10/21に、小さな1行とLESSONの札を置き換えた）：
- Why one slow rank matters: Every solver iteration exchanges halo values and takes a global sum: about 14,000 messages and 1,600 global sums per rank per step. When one rank is late, the other 511 wait.
- Where the computation goes (AMD uProf): Sparse-matrix sweeps lead: Gauss–Seidel smoothing, residuals and A·x are about a quarter of the computation. Each sweep streams the whole matrix with little arithmetic per byte.

LESSONの札（Check what is already broken before hunting for gains）は外し、その言葉を9枚目の主張「Fix what is broken first」にしました。

旧pptxの6枚目の表（`tab08_baseline_profile`）は、道具の列が6枚目と重なるので使いません。`tab07_baseline_mpi_calls`の内容は、7枚目（MPI PROFILE ON 4 NODES）にあります。

旧課題との対応：旧資料は「誤った固定1つで数倍遅くなり、どんな最適化も取り戻せない。利得を探す前に、すでに何かを手放していないか確かめよ」と書いていました。私たちの場合、固定は正しく頼んでいたのに、`MPI_Init`の中で外されていました。「頼んだ設定」と「実際の状態」を分けて確かめたことが、この発見の要点です。

メモ（50秒）：
- 回数が多いのは隣のrankとのデータ交換（`MPI_Isend`・`MPI_Irecv`、rankあたり40 stepで56.6万回）ですが、時間を使っているのは`MPI_Waitall`（43.1秒、MPIの55%）と`MPI_Allreduce`（27.6秒、35%）、つまり他のrankを待つ呼び出しです。
- rankごとのMPI時間は35〜112秒です。セル数はほぼ完全に均等（最大でも平均+0.002%）なので、この差は仕事の量ではなく待ちです。
- 原因は`/proc`で分かりました。512 rankのどれも自分のコアに固定されておらず（全員が256 CPUのどこでも動ける）、自分のNUMA領域にあるページは中央値8.7%でした。8領域に均等に散れば12.5%なので、ほぼ散らばっています。起動時に頼んだ固定が、`MPI_Init`の途中で外されていました。
- OpenFOAM固有の点（サブ領域どうしが接する面）：隣り合うサブ領域が接する面（processor面）の値を、Gauss-Seidelの1回ごと、残差の計算ごとに交換し、残差の大きさは全rankで足し合わせます。固定反復なので、1 stepにUで15回×3成分、kとωで8回ずつ、pでGAMGを12サイクル（最も粗い段ではPCGを35回）回します。rankあたり1 stepに約14,000回の送信と約1,600回の大域和です。512 rankが1 stepに千回以上そろうので、どこか1つのrankが遅いと全員が待ちます。
- 交換する量（processor面の数）が律速なのではありません。ノード間の面を92%減らしても、ネットワークの帯域を55%上げても、速くなりませんでした（18枚目、Q29）。
- 計算の中身はuProfで見ました。上位はGauss-Seidelの平滑化、残差、行列とベクトルの積で、どれも疎行列を1回なめる処理です（13枚目のメモリ帯域の話へ）。32 rankのself CPU time（40 step）は394.6 s、228.9 s、53.1 sで、rankあたり21.1 s。rankあたりの計算時間（OpenFOAM profilingの中央値78.6 s）の約27%なので「about a quarter」と書きました。
- 出典：CrayPAT 38219766511、OpenFOAM profilingと`/proc` 38219862855、uProf 38219770656（#62）。

### 9. OPTIMIZATION STRATEGY（0:40、10/21に補足の進め方から作り直し）

**Message:** Fix what is broken first, then follow the measured bottleneck

上に5段の流れ（番号付きの箱と矢印）。5から2へ戻る矢印に「next round: profile the new baseline」：
1. Baseline：Case defaults on our own build, 3 or more jobs per node count: know the spread
2. Profile：Separate profile runs: /proc, OpenFOAM profiling, CrayPAT, uProf, IMB
3. Bottleneck：What is broken? Why do the ranks wait? What limits one rank?
4. Change one thing：One commit per condition: job script and split (Basic), source (Bonus)
5. Check：Alternate with a control; keep it only if every job is faster. Bonus: Cd bit-identical

下に、実際に回した3回の表（Table 4. Our rounds on 4 nodes）：

| Round, from | Bottleneck found, and how | What we changed | 4 nodes |
|---|---|---|---|
| 1 baseline | Binding lost at MPI_Init, uneven work, MPI 46% waiting (/proc, OpenFOAM profiling, CrayPAT) | Pin CPU and memory, scotch, map the split onto the node (Basic) | 3.65 → 2.90 s/step |
| 2 Basic | Memory bandwidth: half the channels 2.2× slower, half the cores no change (placement runs) | Move fewer bytes: four source changes, multiLevel split (Bonus) | 2.90 → 2.60 s/step |
| 3 Bonus | Still memory bandwidth; the slowest rank computes 7% longer than the median (placement runs, CrayPAT) | Not done: weights from measured rank times, fusing more passes | next steps |

最下段に2つの札：BASIC = Unmodified source; hierarchical or scotch split. BONUS = Source changes or other splits; proven the same math.

図：上の5段（PowerPointの図形）と表。以前の9枚目（律速 → 戦略の表。ネットワーク、演算、I/O、OSノイズを測って外したことを含む）は、補足23枚目（BOTTLENECKS WE MEASURED）に移しました。

旧課題との対応：「利得を探す前に、すでに壊れているものがないか確かめる」と「予算は仮説のためにあり、総当たりのためではない」の2つを、進め方そのものとして見せます。8枚目のLESSONの言葉は、この主張にしました。審査の「Present a logical workflow: Tell the optimization as a problem-solving path」に、この1枚で答えます。

メモ（40秒）：
- 「Fix what is broken first」：3の最初の問いが「What is broken?」です。8枚目で見つけた固定の外れは、最適化ではなく故障の修理で、それを先にしました。
- 5段を1回ずつ言い、最後に「新しいbaselineをまたプロファイルする」と言います。表は話の予告で、1行目は10〜12枚目、2行目は13〜16枚目、3行目は19枚目（What remains）で話します。
- BasicとBonusの線引きを1文で言います：Basicはソースを変えず、ビルド、ジョブスクリプト、配置と、分割はhierarchicalかscotchまで。Bonusはソースの変更と、それ以外の分割方法で、同じ計算であることを示す必要があります。
- ネットワーク、演算、I/O、OSノイズはどうしたかと聞かれたら、補足23枚目を出します（どれも測って、律速ではないと分かった）。

### 10. BASIC OPTIMIZATION (1/2): CPU AND MEMORY PINNING（0:50）

デッキの見出しは「BASIC OPTIMIZATION (1/2)」です（32 ptで1行に収めるため）。

**Message:** Putting the lost binding back: 3.65 → 3.26 s/step (−11%)

- Cause: the launcher binds each rank, but the binding is removed from outside during `MPI_Init`. Linux keeps a page where it was first written (first touch), so data allocated off-core stays remote.
- Fix, in the job script only: each rank starts under `numactl`, with its memory bound to its own NUMA domain; one watcher per node re-pins each rank to its core with `taskset`.
- Check: During the solve, every rank is on its own core (512 of 512) and 58% of its pages are local (was 9%). Case-default split: 3.67 → 3.26 s/step, 3 v 3 jobs.

図：Figure 7「Each half alone is not enough」（4 nodes, scotch split, each job。`deck/deck_plots.py`の`p10_pinning`）。行は上から Both: Basic (numactl + keeper) 2.92、CPU only (taskset keeper) 3.47、Neither: the launcher's binding, lost 3.40、Memory only (numactl) 4.38 s/step（`data/pinning.csv`、各1〜3本）。意図は「CPUの固定とメモリの縛りは、片方だけでは速くならない。両方そろって初めて速い」です。Neitherはbaselineと同じ状態です。以前の下の注記（−11%の出どころ、`LD_PRELOAD`はBonus扱い）はメモに移しました。

メモ（50秒）：
- 要点は「頼んだ配置」と「実際の配置」を区別したことです。起動コマンドの指定は正しく、外れていたのは実行中の`/proc`を見て分かりました。
- Linuxは、ページを最初に書いたコアの近くに置き、後から動かしません（first touch）。データを確保する時点でrankが正しい場所にいないと、データは遠いメモリに置かれたままになります。
- CPUだけ戻すと、戻すまでの12〜16秒に確保したデータが遠くに残ります（3.47）。メモリだけ縛ると、CPUが別の領域へ動き、全部のアクセスが遠くなります（4.38）。
- `LD_PRELOAD`で`MPI_Init`の直後に固定する方法も同じ速さですが、Basicでは使えません。そこでジョブスクリプトだけでできるこの形にしました（F1：job script、rank placement、affinity）。全ジョブのログで、各ノード128/128 rankが固定されています（4ノードで512 of 512）。58%は対応付けの前のBasicで、ノード0の128 rankを`/proc`で見た中央値です。
- −11%は、hierarchicalのまま固定だけを足した同時期の比較です（3.670 → 3.257、10/02〜03。このときの固定は`LD_PRELOAD`で、Basicの`numactl`＋`taskset`と同じ速さ）。図はscotchでの比較で、固定なしの各方式は16〜19%遅くなります。
- ここが、同じASPIRE-2Aを使うチームとの一番の差です。主催者のASPIRE-2Aのノートには固定の話がなく、主催者の参照runも固定していないので、scotch 5本で3.19〜3.58と12%ばらつきます（Q15）。ノートどおりに進めると、この3.2〜3.6のあたりに来ます。

### 11. BASIC OPTIMIZATION (2/2): DECOMPOSITION（0:40）

デッキの見出しは「BASIC OPTIMIZATION (2/2)」です。

**Message:** scotch cuts compact blocks: 3.26 → 2.92 s/step (−10.5%)

- hierarchical cuts thin slabs along the axes; some ranks near the car get many wall faces and more work: 4.31 M faces between subdomains, slowest / median rank 1.16.
- scotch cuts compact blocks: 2.93 M faces (−32%), slowest / median rank 1.06.
- scotch against hierarchical, same placement, 3 jobs each, alternated: −1.3 / −2.5 / −10.5% on 1 / 2 / 4 nodes.
- Then: map the split onto the node. `scotchCoeffs` follow 2 sockets × 4 NUMA domains × 16 cores: 23% fewer faces between nodes; 2.918 → 2.898 s/step (−0.7%); all 5 jobs beat all 5 controls. No change on 1 and 2 nodes.

図：Figure 8（hierarchicalとscotchの分割の絵。車体表面、中心断面、横断面の3段。旧pptxの`decomposition-subdomains.png`から切り出したもの）と、Figure 9「scotch against hierarchical」（1/2/4ノードの各ジョブの点、3本ずつ交互。`deck/deck_plots.py`の`p11_scotch`。比べているのは1 stepの時間で、面の数ではありません）。以前の最下行の斜体（1本で決めない）は、10/21に外して口頭で話します。

旧課題との対応：メモの教訓（1本で決めない）は、旧資料の「少ない本数はばらつきを小さく見せる。何本必要かは機械で大きく違う」と同じです。1本の外れ値で判断を誤り、同時期の交互の比較で正しました。

メモ（40秒）：
- 不均衡は、rankの計算時間の最大/中央値です（CrayPAT、どちらも固定あり）。hierarchicalの不均衡は、壁の面（車の表面）の数と相関しました（#38）。セル数はほぼ完全にそろっているので、そろっていないのは面の仕事です。
- scotchにすると、中央値のrankの`MPI_Waitall`は18.7秒から9.4〜10.8秒に半減しました。
- ノード間の通信が理由ではありません。rankの並べ替え（`MPICH_RANK_REORDER_METHOD=3`）でノード間の面を92%減らしても、変わりませんでした（+0.1%）。
- 測り方の教訓をここで1つ話します：9/27の1本（5.03秒）が遅く、一度はscotchを捨てました。同じ時期に交互に3本ずつ流すと10.5%速く、判断を覆しました。以来、1本では決めません（Q3）。
- ノード数が多いほど効く理由は確かめていません（Q30）。
- scotchの係数（`domains`、`domainWeights`、`strategy`）で、分割をノードの木（ソケット、NUMA領域、コア）に対応付けました。サブ領域間の面の総数は3%増えますが、ノード・ソケット・NUMA領域をまたぐ面は23%・21%・10%減ります。10/05の3本ずつの比較では−0.82%で、当時の1%の基準に届かず見送りました。採点はBasicの4ノードの再実行なので、10/15に交互に5本ずつ測り直し、全runが対照より速い−0.69%で採用しました（#63）。1・2ノードではほぼ変わりません。絵は対応付けの前のscotchです。

### 12. BASIC RESULTS（0:35）

**Message:** −21% on 4 nodes, and the profiles show why

| 4 nodes | Baseline | Basic |
|---|---:|---:|
| s/step (jobs) | 3.65 (3) | **2.90 (5): −21%** |
| Spread between jobs | 8% | 0.18% |
| Ranks on their own core | 0 of 512 | 512 of 512 |
| Memory on the rank's own NUMA domain (median) | 9% | 58% |
| Computation, slowest / median rank (profile run) | 1.46 | 1.06 |
| MPI share of the time (profile run) | 46% | 19% |

図：上の表（Table 5）と、右にFigure 10「Each job on 4 nodes」（baselineの3本とBasicの5本の点、平均3.65と2.90、−21%。`deck/deck_plots.py`の`p12_basic`）。最下行：Steadier too: the organisers score a re-run of exactly this configuration.

「0 of 512 → 512 of 512」：以前は「128 of 128 per node」と書いていましたが、各ノード128/128を4ノード分まとめただけで同じことなので、baselineの「0 of 512」とそろえました。「(profile run)」の2行は対応付けの前のBasicのプロファイルrunで、以前の「*」の注記はメモに移しました。1・2ノードの効果（−8%、−14%）は17枚目で見せます。

メモ（35秒）：
- 固定と分割で、遅いrankがいなくなり（最大/中央値1.46 → 1.06）、待ち（MPI 46% → 19%）とrunごとのばらつき（8% → 0.18%）が減りました。
- 出典：s/stepはbaselineが#62、Basicは10/15の5本（#63）。プロファイルの2行は、対応付けの前のBasic（scotchの既定）のrunです。対応付けで4ノードのstepは0.7%しか変わらないので、そのまま使います。`/proc`はbaselineが全512 rank（#62）、Basicはノード0の128 rank（#36 A3）。OpenFOAM profilingはbaselineが#62、Basicが#57。CrayPATはbaselineが#62、Basicが37176272426（#36 A4）。
- 固定後も自分の領域にあるページが58%なのは、共有ライブラリやMPIの共有バッファのように、複数のrankが使う部分は1つの領域にしか置けないためと考えていますが、確かめていません。「各rankのデータ（メッシュと場）を自分の領域に置いた」と言います。
- 残った19%のMPIも、多くは遅いrankを待つ時間です（Q2、Q21）。

### 13. MEMORY BANDWIDTH SETS THE SPEED（0:45）

**Message:** Half the memory channels: 2.2× slower. Half the cores: no change

- No memory-controller counters on ASPIRE-2A, so we moved the ranks instead (4 nodes, every rank pinned, 2 jobs each).
- Half the cores (128 → 64 ranks per node, still on all 16 channels): × 0.99–1.02 time per step. If the cores set the speed: × 2.
- Half the memory channels (the same 64 ranks and split, on 8 of the 16 channels): × 2.11–2.20. Triad bandwidth: 279 → 125 GB/s (× 2.22).
- Arithmetic intensity agrees: the sparse-matrix sweeps do ≈ 0.1 flop per byte, about 1/100 of what keeps the cores busy (4.1 TFLOP/s ÷ 290 GB/s ≈ 14 flop/byte).
- 最下段のTAKEAWAY：Move fewer bytes, not the same bytes faster（10/21に札の語を「LESSON」から変えた）

図：2つの実験のカード。どちらにも16本のメモリチャネルを四角で描き、使っている本数（16本、8本）を色で見せます。`fig19_cores_or_memory`は補足33枚目の表に置き換えました。

旧課題との対応：旧資料は「帯域の壁に近ければ、バイトを速く運ぶのは行き止まりで、運ぶバイトを減らす余地が開いている」と書いていました。私たちはカウンタが読めないので、配置を変える実験で同じ結論に着き、それがBonusの方針になりました。旧資料の93%や2.5倍は使いません。

メモ（45秒）：
- 「Basicで置き場所と均等さを直した。では今、何が速さを決めているか」という問いから始めます。
- ASPIRE-2Aでは、利用者がメモリコントローラのカウンタ（DRAMの帯域）とIBSを読めません（`perf_event_paranoid=2`）。そこで、rankの置き場所だけを変えました（#61）。
- 実験（4ノード、150 step、各2本）：(a) 1ノード128 rankを64 rankにし、16本のメモリチャネルと16個のL3はそのまま使う（コアだけ半分）。(b) 同じ64 rank・同じ分割のまま、使うチャネルとL3を半分（8本・8個）にする。(a)は−1%〜+2%でほぼ変わらず、(b)は2.11〜2.20倍でした。同じノードで測ったtriadの帯域は、(b)で1/2.22です（274、279、125 GB/s/ノード）。
- 解釈：演算や、コアごとのメモリ要求の待ち時間（レイテンシ）で決まるなら、(a)で約2倍遅くなるはずです。そうならず、(b)で帯域と同じだけ遅くなったので、時間を決めているのはメモリ帯域です。
- 限界：(b)はL3も半分にしているので、DRAMの帯域とL3の容量の寄与は分けられません（どちらもメモリ側の資源です）。
- 演算密度（3行目、Q35）：Gauss-Seidel、残差、Amulは、内部の面1つにつき約4 flopの計算に、係数2つ（16 B）と番地（4 B）とセルの値を合わせて30〜40 Bを読みます。約0.1 flop/Bです。ノードの倍精度ピーク（128コア × 2.0 GHz × 16 flop ≈ 4.1 TFLOP/s）をSTREAM（約290 GB/s）で割った境目は約14 flop/Bなので、その約1/100です。演算器はほとんど待っていて、IPCは0.4〜0.7です。
- だから次の一手は「運ぶデータを減らす」です。コンパイラやフラグ、PGOが±0.13%以内しか変えなかったこととも合います（18枚目）。

### 14. BONUS OPTIMIZATION（0:50）

**Message:** The same arithmetic with fewer bytes moved

- A split that follows the machine: `multiLevel` (4 2 4 16) splits nodes → sockets → NUMA → cores, with scotch at each level: 38% fewer faces between nodes
- Four source changes that move fewer bytes:
  - No copies in the linear solvers
  - U components in one pass: the shared matrix is read once, not 3 times
  - No unused boundary updates: skip values nobody reads
  - Fused face loops: face values formed inside the sums
- Same math: every operation and its order are kept. Only copies, extra passes and values nobody reads are removed.

図：1の下にFigure 11（multiLevelの車体表面の絵2枚。左はサブ領域ごとに塗ったもの（Boxの`decomposition/panels/multiLevel-car-subdomains.png`）で11枚目のhierarchical・scotchと並べて見られる形、右はノード（色相）とNUMA領域（濃淡）で塗ったもの（`multiLevel-car-numa.png`）で、ノード → NUMA領域の木に沿って分けていることが見える）。右にFigure 12「Example: U components in one pass」（行列を3回読むか1回読むか。`fig25_u_in_one_pass`と同じ内容をPowerPointの図形で描いた）。3つの分割を並べた絵と面の数の表は補足32枚目です。1 stepのどこに効くかを見せたいときは`fig13_solver_flow`を使います。

メモ（50秒）：
- 13枚目の「帯域が律速」から来た方針です。メモリを速くするのではなく、運ぶデータを減らします。
- Bonusになる理由：hierarchical・scotch以外の分割方法と、ソースの変更はBonusです（F2）。
- multiLevelは、ノード → ソケット → NUMA領域 → コアの順に、各段をscotchで分けます。ノードとNUMA領域ごとにまとまった塊になり、サブ領域間の面は2.81 Mで、scotchの既定の2.93 M、Basic（対応付けたscotch）の3.02 Mより少なくなります（絵は`decomposition/decomposition-numa-basic-vs-bonus.png`）。
- 例は図の1つだけ話します。速度Uの3成分は、同じ行列（面ごとの係数と、どのセルどうしをつなぐかの番地）を使います。元のコードは成分ごとに行列を読み直していたので、1回読んで3成分を更新するようにしました。各成分の演算と順番は同じです。
- ほかの3つも同じ考え方です。線形ソルバーが毎回作っていた一時的な配列とそのコピーをやめた。結果を捨てていた境界の値の計算と交換をやめた。面の値を一時的な配列に作ってから足すのをやめ、足すループの中で作るようにした。
- 変更の中身の全文は、提出物の`bonus/README.md`とpatchにあります（補足S4。提出物ではpatchに0001〜0004の番号が付いています）。
- （聞かれたら）Uだけか：Uに固有なのは「U components in one pass」だけです。Uは3成分が同じ行列を使うので1回で読めますが、k、ω、pは成分が1つなので、まとめる相手がありません。kとωは別の式（別の行列）で、kOmegaSSTはωを解いてから、新しいωを使ってkを解くので、1回にまとめると計算の順序が変わります。残りの3つは全部の式に効いています：no copiesはsmoothSolver（U、k、ω）とGAMG（p）、no unused boundary updatesはpEqn.HやkOmegaSSTを含む6か所、fused face loopsは全部の場の勾配と面積分です。

### 15. BONUS RESULTS（0:35、新規）

**Message:** Bit-identical Cd, and 10% faster than our Basic

上にFigure 13「Each job: Basic, the multiLevel split alone, and the Bonus」（1/2/4ノードの3つのパネル。`deck/deck_plots.py`の`p15_bonus`）：

| Nodes (steps) | Basic | multiLevel, source unchanged | Bonus | Bonus vs Basic |
|---|---:|---:|---:|---:|
| 1 (40) | 13.365 (3 jobs) | 13.284 (1 job) | 11.668 (3 jobs) | −12.7% |
| 2 (80) | 6.372 (3 jobs) | 6.353 (1 job) | 5.641 (3 jobs) | −11.5% |
| 4 (150) | 2.898 (5 jobs) | 2.873 (4 jobs) | 2.599 (3 jobs) | −10.3% |

中央の「multiLevel, source unchanged」（白抜きの赤）は、F3の照合相手（pre-change baseline：同じmultiLevelの分割とrank数で、ソースの変更を外したもの）と同じ構成のrunです（#42、`data/changes_ab.csv`）。分割だけでは少ししか変わらず、残りはソースの変更によるものだと見えます。

図の下に、R3の4点に1つずつ答える4枚のカード：
- What changed：Four patches and the multiLevel dictionaries, submitted as text
- Why the same math：Only copies, extra passes and unread values are removed; every operation and its order is kept
- Evidence：Against the multiLevel split with the source unchanged: coefficient.dat bit-identical, all 371 / 771 / 1,475 log lines identical
- Speedup vs Basic：−12.7 / −11.5 / −10.3% on 1 / 2 / 4 nodes, on the same machine

変更ごとの効果は補足37枚目（Effect of each Bonus change）です。図の値は、提出物のREADMEと照合できるよう小数3桁にしています（「数値の桁」）。

メモ（35秒）：
- R3の4点のうち、「証拠」と「Basicに対する速度向上」がこの1枚です（「何を変えたか」「なぜ同じ計算か」は14枚目）。
- ビット一致する理由：浮動小数点の演算そのものと順番を変えていないからです。変えたのは、メモリの持ち方と、捨てられていた仕事だけです。
- 4ノード512 rankでは、4つの変更をすべて外したbaselineと、最終Bonusの`coefficient.dat`がビット一致しました（SHA-256 `8952a056…`）。
- ログも同じです。反復回数が固定（`tolerance 0`、`relTol 0`）なので、U・k・omegaの残差と連続の式の誤差は解に戻らず、`coefficient.dat`の比較では見えません。ソースの変更のうちno copies in the solvers、U components in one pass、no unused boundary updatesの3つは、ちょうどそこを触ります。そこで提出物の`simpleFoam.log`（`bonus/f3-baseline/`と`bonus/results/`）を比べました。全stepの残差（16桁）、反復回数、連続の式の誤差、kとomegaのboundingの値が、1/2/4ノードとも全行一致しました（371、771、1,475行）。違うのは、ホスト名、パス、日時と時間の行だけです。
- multiLevelだけの変更（ソースは未改変）は、ルール上はSanity checkで確かめます。80 stepのCdは0.323で目安より少し低いですが、scotchの既定（0.327）も主催者のscotchも同じです。Basic（対応付けたscotch）は0.334です（Q12）。
- 変更ごとの効果を聞かれたら補足S3を出します。4ノードで、multiLevel −1.5%（scotchの既定に対して）、ソースの変更が順に−3.4%、−2.3%、−1.3%、−2.8%です（どれも直前の構成を対照に、同じ時期に3〜4本ずつ）。別々の実験なので足し合わせません。合計の効果は、上の表で直接測っています。

### 16. BONUS ANALYSIS（0:35）

**Message:** 4% fewer instructions, but 17% fewer refills from DRAM

- Hardware counters (AMD uProf, 1 node, computation only, 2 jobs each side): time per step −12.3%, cycles −10.8%, instructions −4.1%, L1 data accesses −5.9%, L2 accesses incl. prefetch −9.6%, L1 refills from DRAM −17.2%.
- Less bandwidth per core, bigger gain (4 nodes, 64 ranks per node, the same patches): −7.9% on all 16 channels, −11.4% on 8 of 16.
- Computation shrinks, MPI does not (CrayPAT, 4 nodes): computation per rank 104.2 → 94.9 s in 40 steps; MPI stays ≈ 23.5 s.

図：Figure 14「Patched against unpatched, the same build」（カウンタの横棒グラフ。PowerPointのグラフ、`fig17_counters`の平均）と、右に2枚のカード。以前の下の注記（L1のdemand refillでDRAMのバイト数ではない、IPC 0.36 → 0.39）はメモに移しました。

メモ（35秒）：
- 「計算は同じで、DRAMから運ぶデータが減った」ことの直接の根拠です。命令数は4%しか減らないのに、DRAMからのrefillは17%減り、cyclesは11%減りました。IPCは0.36 → 0.39です。
- 言い過ぎない点：数えているのはL1のdemand refillで、DRAMの転送バイト数ではありません（uncoreのカウンタは権限がなく使えません）。カウンタは1ノードだけです。
- 4ノードでは、カウンタの代わりに配置の実験で確かめました（#61）。同じ分割・同じ64 rank/ノードで、全チャネルを使うとソースの変更は−7.9%、半分のチャネルでは−11.4%です（現行の128 rank/ノードでは−9.5%）。1コアあたりの帯域が少ないほど効くので、効果は運ぶデータを減らしたことによるものです。
- CrayPATの値：最初の変更（no copies in the solvers）だけを入れたBonusから最終Bonusまで、rankあたりの計算時間は104.2秒から94.9秒（40 step）。MPIは約23.5秒のままです。

### 17. SCALING ANALYSIS（0:40）

**Message:** Faster at 1, 2 and 4 nodes; parallel efficiency 1.00 → 1.15

- Against our baseline: Basic −8 / −14 / −21%, Bonus −20 / −24 / −29% on 1 / 2 / 4 nodes.
- Parallel efficiency, 1 → 4 nodes: baseline 1.00, Basic 1.15, Bonus 1.12.
- Basic gains most on 4 nodes (scotch: −1.3 / −2.5 / −10.5%); the source changes gain most on 1 node, where each rank holds 4× more data (U in one pass: −6.4% on 1 node, −2.3% on 4).
- Efficiency above 1 is cache: on 4 nodes the cell arrays shrink to 1 MB per rank and fit in L3; DRAM refills per cell −30% (uProf).

図：Figure 15「Time per step on 1, 2 and 4 nodes, each job」（baseline、Basic、Bonusの各ジョブの点と平均の棒を対数軸に描き、1ノードの平均から引いた理想の線を破線で添える。`deck/deck_plots.py`の`p17_scaling`。凡例に各段の並列効率）と、Table 6（平均のs/stepと効率）。理想の線の上にbaselineが乗り、BasicとBonusは4ノードで線より下に来る（効率が1を超える）ことが見えます。

メモ（40秒）：
- ルールが求める「1/2/4ノードのscaling」と「4ノードのbefore/after」を、この1枚で見せます。
- Basicの効果がノード数とともに大きくなるのは、主に分割の効果です（scotchが1/2/4ノードで−1.3/−2.5/−10.5%）。理由は確かめていません（Q30）。
- ソースの変更の効果が1ノードで大きいのは、rankあたりのデータが4倍あり、DRAMから来る量が多いからだと説明します。16枚目の「1コアあたりの帯域が少ないほど効く」と同じ向きです。
- 効率が1を超える理由は、カウンタで確かめました（#66、対応付けの前のBasic、uProf、1/2/4ノード）。1セル・1 stepあたりのサイクルは、4ノードで1ノードの0.84倍、DRAMからのL1 refillは0.70倍です。減ったのは、面の番地を通してセルの配列を飛び飛びに読み書きする疎行列の計算（平滑化、残差、行列とベクトルの積）で、DRAMからのrefillが60〜70%減ります。この配列はrankあたり1ノードで4 MB、4ノードで1 MBになり、コアあたり4 MBのL3に収まります。
- 1・2ノードの変更ごとの値の多くは1本どうしの比較なので、本編では傾向だけ言います（補足S3）。

### 18. WHAT DID NOT HELP, AND WHY（0:40）

第3版の見出しは「OPTIMIZATION IDEAS (NOT WORKED)」でした。主張を、旧課題の資料の言う「代理指標」の教訓にしました。

**Message:** Proxy metrics improved; the time per step did not

Table 7（10/21に、Basicの案、Bonusの案の順に並べ替えた）：

| Idea | Result (4 nodes) | Why it did not help |
|---|---|---|
| Compiler flags, AOCC, LTO, GCC PGO | within ±0.13% | The loops wait on memory, not on instructions |
| Other MPI transports: OFI, UCX over RC | −0.16% to +0.77% | MPI time is waiting for the slowest rank |
| Reordering ranks: 92% fewer inter-node faces | +0.1% | Fewer bytes between nodes do not cut the wait |
| malloc thresholds | −0.4% (3 jobs) | Too small to separate with 3 jobs; not re-tested |
| SMT: 2 ranks per core | 5.7× slower | Stalls of minutes; cause not isolated |
| GAMG coarsest level on fewer ranks | −0.25% to +4.95% | 81% of the global sums, ≈ 0.6% of the time |
| Weighted cells (×2, ×12), 2-constraint METIS | +1.5% to +6.1% | Uneven cells, or more faces between subdomains |

下に3行（紺の札に問い、右に答え）：
- Why no gain? None of them moves fewer bytes, and memory bandwidth sets the speed.
- Fewer faces? Only with even work: scotch −10.5%; 92% fewer faces between nodes alone, +0.1%.
- Why not combine them? Gains we cannot separate from the spread may be luck; stacking them is overfitting.

図：上の表（PowerPointの表。各行が1行に収まるように短くした）。コンパイラのフラグの細目や通信のスイッチを含む全部の一覧は、補足42枚目（Not adopted: the full list）です。面の数と時間の関係は補足32枚目（THE THREE SPLITS: FACES OR EVEN WORK?）です。

旧課題との対応：旧資料の「最適化の価値は、取り除いた律速の分だけ。代理指標は時間を動かさずに大きく動き得る」です。ノード間の面（−92%）、ネットワークの帯域（+55%）、METISの面の均衡は、どれも指標としては良くなりましたが、1 stepは動きませんでした。

メモ（40秒）：
- 一覧を指して、理由は2つにまとまると言います。1つはどれも運ぶデータを減らさないこと（速さを決めているのはメモリ帯域）。もう1つは、MPIの時間の多くが遅いrankを待つ時間で、通信を速くしても待ちは減らないことです。
- UCXのRCはIMBの帯域を55%上げましたが、1 stepは−0.01%（Basic）でした。GAMGの最も粗い段は`MPI_Allreduce`の呼び出しの81%を出しますが、時間はstepの約0.6%です。
- 重み付けは、セル数を崩してかえって遅くなりました（Q4、Q5）。
- 面を減らすこと（OpenFOAMで最初に思いつく最適化）：面だけ減らしても速くなりませんでした。rankの並べ替えはサブ領域を変えずにノード間の面を92%減らし、+0.1%。効いたのは仕事をそろえたことで、scotchは面を3分の1減らし、計算の偏りを1.16 → 1.06にして−10.5%。ノードへの対応付け（ノード間の面−23%）とmultiLevel（−38%）は−0.7%、−1.5%と小さく効きました（補足32枚目）。
- 小さな改善を組み合わせない理由：run間のばらつき（4ノードで約0.2%）と区別できない改善は、たまたま速かったrunかもしれません。確かめないまま積み重ねると、そのrunに合わせることになります（過学習）。採用したのは、同じ時期に交互に流して全runが対照より速かったものだけです（6枚目）。0.7%のscotchの対応付けも、5本ずつ流して確かめてから採用しました（11枚目）。mallocの閾値（−0.4%、3本）は、測り直していません。

### 19. CONCLUSION（0:40）

**Message:** 1.40× faster on 4 nodes, with the same math

上に数字のカード3枚（4ノードのs/stepと、1 / 2 / 4ノードの値）：
- 3.65 s/step: Baseline, case defaults (14.57 / 7.43 / 3.65)
- 2.90 s/step: Basic −21%, unmodified v2512 (13.36 / 6.37 / 2.90)
- 2.60 s/step: Bonus −29%, bit-identical Cd (11.67 / 5.64 / 2.60)

最適化表（旧Rules §8.2の形）：

Table 8「What we changed, the bottleneck it removed, and the gain on 4 nodes」：

| What we changed | The bottleneck it removes, and the evidence | vs own control |
|---|---|---|
| Pin CPU and memory (Basic) | Lost binding: 0 of 512 ranks pinned, 9% of memory local | −11% |
| scotch, then node mapping (Basic) | Uneven work near the car: slowest / median 1.16 → 1.06 | −10.5%, −0.7% |
| Four source changes (Bonus) | Memory bandwidth: half the channels → 2.2× slower | −9.5% |
| multiLevel split (Bonus) | Faces between nodes −38%, sockets −34%, NUMA −26% | −1.5% |

下に2つの箱（10/21に、1文の「What remains」とHOW WE WORKEDの札を作り直した）：
- What remains after the Bonus:
  - Memory bandwidth sets the speed: half the channels, 2.1× slower
  - The slowest rank computes 7% longer than the median; the rest wait (MPI 20% of a step)
- How we worked: Know the noise · fix what is broken first · follow the measured bottleneck · judge by the time per step, not by proxy metrics such as faces or counters
- （「What remains」の出典）帯域：#61の配置の実験で、Bonusもチャネル半分で2.11倍遅い。計算の差：#53のCrayPAT、最終Bonusで最も遅いrankは中央値の1.067倍（Basicの全rankのOpenFOAM profiling、#57では1.063）。MPI：#53、最終Bonusでプロセス時間の19.9%（Basicは19.4%）。
- 「proxies」は代理指標（proxy metrics）のことで、速さと関係しそうに見える別の量（ノード間の面の数、ネットワークの帯域、IPCや命令数）を指します。札の短い言い方では伝わらないので、例を添えた文にしました。
- 以前の「Each gain is against its own control; they are not added up」は、表の右列の見出し（vs own control）とメモにしました。

図：上の数字と表（PowerPointの表）。

旧課題との対応：旧Rulesの最適化表は「なぜ効くと考えたか」「律速だった証拠」の列が点の大半を占めるとしていました。真ん中の列がそれに当たります。右下の「How we worked」は、上の「旧課題の資料から取り入れた姿勢」の要約です。

メモ（40秒）：
- 最初と最後で同じ数字を言います：「同じ計算のまま、4ノードで3.65秒から2.60秒、1.40倍です」。
- run間のばらつきは8%から0.2%になりました。再実行で採点される以上、ばらつきが小さいことも強みです（提出スクリプトでの再実行は2.905 s/step、補足S10）。
- （参考、聞かれたら）主催者の参照runは、scotchで3.30秒、ばらつき12%です。サイトのビルド、既定のMPI、固定なしと条件が違うので、直接の比較にはしません（補足S9）。
- 効いたことの%は、それぞれ同時期の対照に対する値で、足し合わせません。
- 残る律速：配置の実験では、Bonusでもチャネル半分で2.11倍遅く、速さを決めているのは最適化の前後でメモリ帯域です。rankの計算時間の差（最大/中央値1.06）は、セル数では説明できず、壁の面で一部だけ説明できます（Q21）。
- 最後の一言：「Basicで置き場所と仕事の均等さを直して21%、Bonusで運ぶデータを減らしてさらに10%」。続けて「And one more thing」で20枚目へ進みます。時間がなければ、ここで終えます。

### 20. EXTRA: A GAIN WE DID NOT COUNT（0:35、おまけ、#68）

補足S17を本編へ移したものです（10/19）。

**Message:** 2.595 → 2.250 s/step and bit-identical, but only with fixed iterations

左に数字のカード3枚（10/20に%から時間の表記に変えた）：
- 2.595 → 2.250: s/step on 4 nodes, before → after; 3 jobs each, alternated; ranges do not overlap（−13.3%）
- bit-identical: coefficient.dat at 1, 2 and 4 nodes; all 1,323 solver log lines identical
- ≈ 0.35 s: of every 2.6 s Bonus step on 4 nodes goes to convergence checks that are never used（2.595 − 2.250 = 0.345秒、stepの約13%）

右にカード3枚（10/21に「How we found it」を足し、LESSONの札は外した）：
- How we found it: In the call stacks of the final Bonus, every sweep of the U, k and ω solvers ends with a residual and a global sum (MPI_Allreduce) for the convergence check. With tolerance 0 the check can never stop a solve, so every result but the last is thrown away.
- What it does: The patch computes the residual once, after the last sweep. The residuals and iteration counts in the log stay the same.
- Why it is not in our Bonus:
  - It helps only the benchmark's fixed-iteration setting: the case's own `fvSolution.fixedTol` runs the original code
  - The rules prohibit "less work per step", and the skipped norms could be read as work
  - Our four Bonus changes, in contrast, help with any convergence setting

見つけた経緯（#68の本文）：#53のeu-stack（最終Bonus、4ノード、48 rank）で、Uの3成分のGauss-Seidelに残差＋`gSumMag`（Allreduce）＋`normFactor`、k・ωのsmoothSolverにも`gSumMag`と`normFactor`が出ていました。v2512のソースでは、smoothSolverは毎sweepの後に残差を作ってAllreduceし、収束判定に使います。`tolerance 0`・`relTol 0`では判定が成立しないので、最後の1回以外の結果は捨てられます（最粗段のPCGも`minIter = maxIter = 35`で同じ）。

メモ（35秒）：
- 数値と出典は補足S17のメモのとおりです（#68、branch `experiment/issue68-skip-unused-residuals`、patch `0005-skip-unused-convergence-residuals.patch`）。
- この1枚の価値は、速さではなく線引きです。「計測の取り決めにだけ効く高速化は数えない」と自分で言えることを見せます。18枚目の「代理指標は時間を動かさない」と同じ姿勢で、代理（ベンチマークの設定）だけを良くする変更を、本当の高速化と区別しています。
- 最後に「Thank you」で終えます。

---

## 削るとき（Qwenに時間を回すとき）

- 20枚目（おまけ）を飛ばし、19枚目で終える（−35秒）。
- 6枚目を8枚目に入れる：`tab08_baseline_profile`（道具、測ったもの、結果の3列）を8枚目に置き、6枚目の「計測runとプロファイルrunを分けた」は4枚目の最後の行に1文で足します（−35秒）。
- 16枚目を15枚目に入れる：カウンタは15枚目に1行（DRAM refill −17%、命令 −4%）だけ書き、`fig17_counters`は補足にします（−35秒）。
- 9枚目の下の表（実際の回り方）は指すだけにして、5段の進め方だけを話します（−10秒）。
- 7枚目（MPIの上位3つ）は、主催者がISC26の課題で発表に求めた分析なので削りません。

## 時間が余ったら（足せる話）

- 4ノードで1つずつ足した経路（`fig16_journey`、補足29枚目）：どの順で何をして、いくつ速くなったかを1枚で見せます。始点は#36の3.670です。
- 律速の候補ごとに測ったこと（BOTTLENECKS WE MEASURED、補足23枚目）：ネットワーク、演算、I/O、OSノイズも測って外したことを見せます。
- 面の数か、仕事の均等さか（THE THREE SPLITS、補足32枚目）：3つの分割をノードごとに塗った絵と、面を減らしただけでは速くならなかったことを見せます。
- 測り方の教訓（`fig08_variability`、補足24枚目）：同じ構成のrunの多くは中央値から±0.4%に入りますが、9月には84%、91%遅い単発のrunがありました。

---

## 補足（質疑用）

改訂版pptxでは、21枚目が扉、22枚目がQ&A目次（各行をクリックするとその補足へ飛ぶ）で、補足は質問の流れに沿って次の順に並べました。下のS番号は第3版の番号で、メモと想定問答はS番号で参照しています。補足の図と表には、Figure S1、Table S1から番号を振っています（本編とは別）。

| 改訂版pptx | 見出し | 第3版 |
|---|---|---|
| 23 | BOTTLENECKS WE MEASURED（10/21に本編9枚目から移動、律速の候補ごとに測ったことと方針） | — |
| 24 | MEASURING HONESTLY | S12 |
| 25 | EXPERIMENT AUTOMATION（PowerPointの図形で描き直し、7段に番号） | S15 |
| 26 | BUILD, STORAGE AND MPI（同上） | S14 |
| 27 | THE ORGANISERS' REFERENCE（各ジョブの点の図：主催者のhierarchical・scotchと、私たちのBasic・Bonus） | S9 |
| 28 | WHERE A STEP GOES AFTER BASIC（棒グラフで描き直し） | S2 |
| 29 | THE PATH ON 4 NODES | S13 |
| 30 | IS THE NETWORK THE BOTTLENECK? | S16 |
| 31 | OFI AGAINST UCX | S11 |
| 32 | THE THREE SPLITS: FACES OR EVEN WORK?（10/21に新規） | — |
| 33 | CORES OR MEMORY?（表と、3つの配置の説明） | S7 |
| 34 | THE SOURCE CHANGES | S4 |
| 35、36 | SOURCE CHANGES IN DETAIL (1/2)、(2/2)（旧pptxの20・21枚目を作り直し） | S4 |
| 37 | EFFECT OF EACH BONUS CHANGE（4ノードの各ジョブの点の図と、1/2/4ノードの表） | S3 |
| 38 | PROFILES BEFORE AND AFTER（積み上げ棒グラフ） | S5 |
| 39 | WHY THE EFFICIENCY EXCEEDS 1 | Q6、#66 |
| 40 | DRAG COEFFICIENT CHECKS | Q12、Q13 |
| 41 | REPRODUCING OUR RESULTS | S10 |
| 42 | NOT ADOPTED: THE FULL LIST（10/21にBasic、Bonus、そのほかの順に並べ替え） | S8 |
| 43 | COMPILER AND FLAGS | S8 |

S1（MPIの呼び出し）は本編7枚目、S6（カウンタ）は本編16枚目、S17（#68）は本編20枚目、10/20に足した進め方（OPTIMIZATION PLAN）は本編9枚目にあります。Qwenと共通の再現性スライド（旧43枚目）は、チームが10/21に外しました。

### 補足23. BOTTLENECKS WE MEASURED（10/21、本編9枚目から移動）

**Message:** What limits a step: placement, balance and memory bandwidth

Table S1（律速の候補、4ノードで測ったこと、方針。上の3行を強調）：

| Bottleneck | Measured on 4 nodes | Our strategy |
|---|---|---|
| **Memory placement** | 0 of 512 ranks pinned; 9% of a rank's memory local | Pin CPU and memory (Basic) |
| **Load imbalance** | MPI 46% of the time, mostly waiting for the slowest rank | scotch (Basic), multiLevel (Bonus) |
| **Memory bandwidth** | Half the bandwidth → 2.2× slower; half the cores → no change | Move fewer bytes (Bonus) |
| Network | 55% more bandwidth or 92% fewer faces between nodes: no change | — |
| Arithmetic | Compiler flags, another compiler, PGO: within 0.13% | — |
| File I/O | 0.01% of a step | — |
| OS noise | 0.8% of each core's time | — (needs root) |

メモ：以前の本編9枚目の表を、手を打った順（置き場所 → 均等さ → 帯域）に並べ直したものです。ネットワークの行は、ノード間の転送方式をRCに替えて帯域を55%上げても、rankの並べ替えでノード間の面を92%減らしても、1 stepが変わらなかったこと（補足30枚目）。OSノイズは、割り込みの処理に各コアの時間の0.8%が使われていることで（#46）、変えるにはrootが要ります。

### 補足32. THE THREE SPLITS: FACES OR EVEN WORK?（10/21、新規）

**Message:** Fewer faces between nodes alone did not help; evening out the work did

上にFigure S7：3つの分割（hierarchical（case default）4.31 M faces、scotch（Basic）2.93 M faces、multiLevel（Bonus）2.81 M faces）の車体表面を、ノード（色相）とNUMA領域（濃淡）で塗った絵（Boxの`decomposition/decomposition-numa.png`の車体の段）。hierarchicalはノードが高さ方向の4つの層、scotchはノードの境目がばらばら、multiLevelはノードごとに連続した塊です。

下にTable S4（面の数と時間。どれも同じ時期の対照に対する4ノードの値）：

| What changed | Faces between subdomains | Faces between nodes | Work per rank | Time per step |
|---|---|---|---|---|
| scotch instead of hierarchical (Basic) | −32% | — | evened (1.16 → 1.06) | −10.5% |
| Reordering ranks, hierarchical split | unchanged | −92% | unchanged | +0.1% |
| scotch mapped onto the node (Basic) | +3.3% | −23% | — | −0.7% |
| multiLevel instead of scotch (Bonus) | −3.9% | −38% | — | −1.5% |
| METIS with two constraints (Bonus) | +18% | — | — | +1.5% |

メモ：OpenFOAMで最初に思いつく最適化は「サブ領域の面を減らして通信を減らす」ですが、面だけを減らしても速くなりませんでした（rankの並べ替え）。効いたのは計算の偏りを減らしたことで、ノード間の面を減らす分割（対応付け、multiLevel）は小さく効きました。MPIの時間の多くは遅いrankを待つ時間なので、交換する量より、仕事の均等さが効きます（Q2、Q29）。hierarchicalのノード間の面の数は数えていません。出典：面の数は各`decomposePar.log`（#39）とREPORT §6.2、§6.3、§8。時間はscotchが#36、#38、対応付けが#63、multiLevelが#42、rankの並べ替えがREPORT §10の表、METISが`bonus/README.md`。

### S1. MPI calls in the baseline（#62）

10/20に本編7枚目（MPI PROFILE ON 4 NODES）へ移しました。数値と出典は7枚目の節にあります。

### S2. Where a step goes after Basic, and where the imbalance is（#57）

図：`figures/fig18_step_breakdown.png`

- OpenFOAM's built-in profiling (`profiling {}` and the `parProfiling` function object), Basic, 4 nodes, a 40-step diagnostic run with every rank's results.
- Computation per rank (loop time minus Pstream time): median 97.95 s, max 104.17 s (max/median 1.063) over 40 steps.
- Correlation with the computation: cell count r = +0.06 (balanced within 1%), wall faces r = +0.43, processor faces r = −0.16; both together explain 27%.
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

- From the Bonus with only the first change (no copies in the solvers) to the final Bonus, computation per rank falls 8.9% (104.2 → 94.9 s); MPI stays at about 23.5 s.
- The spread between ranks stays (max/median 1.07).

### S6. Hardware counters before and after the patches（#55）

図：`figures/fig17_counters.png`

- 1 node, 128 ranks, 40 steps, multiLevel (2 4 16); AMD uProf `data_access` on one rank per NUMA domain; 2 runs with the four source changes (fa4f5b0) and 2 without (the same commit with `patches/openfoam/` removed).
- Computation only (MPI, UCX and Pstream left out), mean of 7 ranks: cycles −10.8%, instructions −4.1%, L1 data accesses −5.8%, L1 refills from DRAM −17.2%, from L2 −0.2%, L2 accesses including prefetches −9.6%; IPC 0.360 → 0.388.
- Two runs of the same side agree within about 4% on every counter. Both sides give the same `coefficient.dat` (Cd 0.43827636195043501).

### S7. Cores or memory? We moved the ranks, not the code（#61）

図：`figures/fig19_cores_or_memory.png`、`figures/fig20_memory_placement.png`

- ASPIRE-2A users cannot read the memory-controller counters or IBS (`perf_event_paranoid=2`), so we changed only where the ranks run. 4 nodes, 150 steps, 2 runs per condition (2026-10-10), every rank pinned to its CPU with its memory on that CPU's NUMA domain.
- full128: 128 ranks per node (the submitted placement). spread64: 64 ranks per node, 4 per L3, on all 16 L3s and 16 memory channels. packed64: the same 64 ranks and decomposition, 8 per L3, on 8 L3s and 8 channels.
- Triad on the same nodes after the solver: 274 / 279 / 125 GB/s per node.

| s/step | full128 | spread64 | packed64 | spread64 / full128 | packed64 / spread64 |
|---|---:|---:|---:|---:|---:|
| Basic (before the mapping) | 2.920 | 2.887 | 6.347 | 0.99 | 2.20 |
| Bonus without the patches | 2.869 | 2.874 | 6.321 | 1.00 | 2.20 |
| Bonus | 2.595 | 2.649 | 5.598 | 1.02 | 2.11 |
| patches (Bonus against the line above) | −9.5% | −7.9% | −11.4% | | |

- `coefficient.dat` is bit-identical between spread64 and packed64 of each configuration, and between the baseline and the Bonus at every placement. Every rank stayed on its CPU (keeper 64/64 or 128/128 on every node).

### S8. Not adopted (full list)

図：`figures/tab04_not_adopted.png`、コンパイラとフラグの比較は`figures/fig07_compiler_options.png`（改訂版pptxの補足43枚目）

### S9. Against the organisers' reference (1, 2 and 4 nodes)

図：`figures/fig14_vs_organiser_reference.png`

- Organisers' setup (ASPIRE-2A notes, tasks 4.3): site module, `mpirun` with no options, default MPI settings, no binding.
- Against their `scotch` mean: Basic −8 / −13 / −12%, Bonus −19 / −23 / −21% on 1 / 2 / 4 nodes.
- A reference, not a controlled comparison: the build, the MPI transport and the placement all differ from ours, so the gap has more than one cause. Our own comparisons use our baseline, with the same build, scripts and measurement.

### S10. The submitted scripts reproduce the results（#54、#63）

- The official sources downloaded from their public URLs, built with `build/build.pbs`, every run started with `run/submit.sh`: Bonus on 2026-10-07 (Actions 37584763848), Basic again on 2026-10-16 after the mapping was added (Actions 38843636251).
- At 1, 2 and 4 nodes `coefficient.dat` is bit-identical to the recorded runs. s/step: Bonus within 0.21% of the recorded means; Basic 0.24 – 0.36% slower, on other hosts on another day (4 nodes: 2.9046 against 2.8976).
- Both CrayPAT profiles (2026-10-07; Basic before the mapping, final Bonus): 3.065 and 2.701 s/step under CrayPAT against 3.063 and 2.712; the same number of MPI calls per rank.

| | 1 node | 2 nodes | 4 nodes |
|---|---:|---:|---:|
| Basic, re-run (recorded mean) | 13.413 (13.365) | 6.390 (6.372) | 2.905 (2.898) |
| Bonus, re-run (recorded mean) | 11.644 (11.668) | 5.650 (5.641) | 2.601 (2.599) |

### S11. OFI against UCX under our placement（#56、#60）

- Basic configuration (before the mapping) on 4 nodes, only the MPI transport changed; 3 runs each, alternated in the same period (2026-10-07).
- UCX (main): 2.9176, 2.9168, 2.9246 s/step, mean 2.9197. OFI with `FI_OFI_RXM_USE_SRX=0`: 2.9452, 2.9374, 2.9438, mean 2.9421 (+0.77%).
- All 6 runs VALID, every step returned 0 (no SIGBUS), the same `coefficient.dat` Cd (0.28404934573921931).
- OFI's own spread is also 0.26%, so the narrow spread of our runs does not come from UCX (Q15).
- The organisers' other workaround, `FI_VERBS_PREFER_XRC=0` (2026-10-09, one run each beside a UCX run): 2.9338 against 2.9192 s/step (+0.50%), the same Cd, no SIGBUS.

### S12. Measuring honestly（#47）

図：`figures/fig08_variability.png`

- 92 runs in 29 repeated configurations (2026-09-21 to 10-05): most lie within ±0.4% of their configuration's median.
- But single runs were 84% and 91% slower in September.
- run内のstep間の標準偏差と、run間のばらつきは別物です。150 stepを150個の独立な標本として扱いません。遅い回の原因をホストだけに断定しません（同じホストで後に正常なrunがあります）。

### S13. The path on 4 nodes

図：`figures/fig16_journey.png`

- start (case-default split, binding lost) 3.670 → pinning 3.257 → scotch 2.915 → mapped onto the node = Basic 2.898 → Bonus 2.599. Each step was measured against its own control in the same period.
- 始点は#36の3本（10/02〜03）で、本編のbaseline 3.65（#62、10/12）と同じ構成です。

### S14. Build, storage and MPI

図：`figures/fig15_storage_flow.png`、`figures/tab05_environment.png`

- Build: official v2512 source, GCC 11.2 with `-O3`, AMD math library, in a 1-node PBS job (16 cores). Every run records which build it used.
- Storage: `/scratch` (Lustre, shared) holds the mesh, builds and run directories; every node copies the decomposed case into its own node-local `$TMPDIR`, and the solver reads and writes only there (`-hostRoots`, `-ioRanks`). File I/O in the timed steps is about 0.01% of the run time.
- MPI: Cray MPICH 8.1.15 over UCX instead of the default OFI provider.

### S15. Experiment automation

図：`figures/fig12_pipeline.png`

### S16. Is the network the bottleneck? No（#36、#48、#56、#58、#60）

図：`figures/tab13_network_checks.png`

- We changed only the network side, four ways; none made a step more than 0.25% faster (table).
- One 8-byte global sum over 512 ranks takes about 12 µs (IMB), so the 1,600 global sums of a step cost about 0.02 s, under 1% of a step. The rest of the MPI time is waiting.
- Each rank's wait (`MPI_Waitall`) is explained by its own computation (R² 0.77); adding its number of neighbours and of neighbours on other nodes raises that only to 0.80. The ranks that set the step have almost no neighbours on other nodes (13 of the 16 slowest have none).
- Not measured: NIC and switch counters.
- （メモ）rankごとの`MPI_Isend`の回数は、分割から数えた隣のrankの数と相関+1.000で、1つの隣に1 stepあたり約1,324通を送っています。メッセージの数は分割で決まり、待ちは計算の不均衡で決まります（#48）。

### S17. Found but not claimed: residual norms that the fixed iterations never use（#68）

10/19に、おまけとして本編の最後（今の20枚目）へ移しました。下は元のメモで、20枚目のメモと合わせて使います。

**Message:** −13% on 4 nodes and bit-identical, but only because the benchmark fixes the iterations, so it is not part of our Bonus

- `fvSolution.fixedIter` sets `tolerance 0` and `relTol 0` for U, k and omega, and `minIter = maxIter = 35` for the coarsest-level PCG. The convergence check can never stop a solve early, so the residual norm computed after every sweep (a residual pass and a global sum) is only used after the last one.
- A patch computes it once, after the last iteration: 2.250 against 2.595 s/step on 4 nodes (−13.3%, 3 runs each, ranges not overlapping). `coefficient.dat` is bit-identical at 1, 2 and 4 nodes, and all 1,323 solver log lines (every residual and iteration count) are identical.
- Why we do not count it: it helps only the benchmark's fixed-iteration setting. The case's other dictionary, `fvSolution.fixedTol` (the production-like setting), runs the original code. The rules also prohibit "less work per step", and the skipped norms could be read as work.

図：なし（数値だけ）。

メモ：
- 固定反復はベンチマークの取り決めです。ケースのREADME（OpenFOAM HPC Challenge OHC-1）は、hardware trackでは`fvSolution.fixedIter`を使い、software trackは`fvSolution.fixedTol`（pはtolerance 1e-7・relTol 0.01、U・k・ωは1e-8・0.1、普通の運用値）から始めるように書いています。
- 考え方自体はOpenFOAMにもあります。v2512の`smoothSolver`は、`nSweeps`が負のときは決まった回数だけ回し、残差を計算しません。このパッチは、ベンチマークの書き方（tolerance 0、relTol 0、maxIter）で同じことをし、ログに出る最初と最後の残差は残します。
- 言い方：「過学習」というより「計測の取り決めにだけ効く高速化」（Goodhartの法則の例）です。ほかの設定で遅くなることはなく、条件を満たせばどの入力でもビット一致しますが、普通の運用では効きません。Bonusの4つの変更は、どの収束設定でも捨てられる計算を省いたもので、`fixedTol`でも効きます。この線引きを言えるのが、この1枚の価値です。
- わかったこと：512 rankでは、毎回の収束判定（残差の計算とその大域和）だけで、Bonusの1 stepの約13%を使っています。
- 数値：1ノード10.29 s/step（Bonusの11.67から−11.8%）、2ノード4.93（5.64から−12.7%）、各1本。今のBasic（2.898）からは、4ノードで−22.3%です。
- 出典：#68、branch `experiment/issue68-skip-unused-residuals`（e2e2ae8、最終Bonus fa4f5b0の上）、patch `0005-skip-unused-convergence-residuals.patch`。

---

## 想定問答

英語の回答は、質疑で言う形の下書きです。

**Q1. Why ASPIRE-2A?**
- Last year we competed on Gadi, so this year we wanted to learn the other contest machine.
- Storage. OpenFOAM works with very many files: one unpacked OpenFOAM tree is about 36,000 files, and every decomposed 65M case adds thousands of `processor*` files. Our Gadi project has 1 TiB and about 212,000 files on `/scratch`; in August, three runs setting up at the same time already hit that file limit. On ASPIRE-2A we have 100 TB and 200 million files, so we could keep the builds, the decomposed cases and the raw records of every run.
- （メモ）Gadiの利用停止のことは自分からは言いません。「ノードが空いていた」は言いません（今回、4ノードは4時間以上、qdevの1ノードは3時間以上待った記録があります）。数字の出典は`platforms/gadi/README.md`（inode上限212,100、2026-08-17の3件同時の`Disk quota exceeded`）と、ASPIRE-2Aの`lfs quota`（100 TB、2億inode、2026-10-07）です。

**Q2. MPI waiting is large. Why didn't MPI tuning help?**
- Most of the MPI time is waiting: ranks that finish early wait at the next exchange or global sum. Per-rank MPI time ranges from 20 to 37 s. Library or switch tuning cannot remove that wait; only less work or better balance can. The OpenFOAM communication switches we tried gave no gain. Two later checks agree: UCX over RC raised the IMB bandwidth between nodes by 55% but changed a step by −0.01% (Basic) and −0.16% (Bonus), and moving the GAMG coarsest level, which issues 81% of the `MPI_Allreduce` calls, from 512 ranks to 32 changed it by −0.25%.

**Q3. Why did you first reject scotch and then adopt it?**
- One run on 2026-09-27 took 5.03 s/step, an outlier from a slow period. When we alternated three runs of each in the same period, scotch was 10.5% faster. Since then we never decide from a single run.

**Q4. Is equal cell count enough?**
- It mattered most. When we weighted cells by their face and point work, the cell counts became uneven and it got slower (+2.2%, +6.1%). A METIS two-constraint split balanced faces better but added 18% processor faces (+1.46%). The remaining imbalance (max/median 1.07) is still open.

**Q5. Why did the weighting make it worse?**
- Static weights moved cells away from an even split: the cell-count imbalance grew to 1.073 with weight ×2. With ×12, the top-level split broke down and the faces between nodes grew five times.

**Q6. Why are the effects different on 1, 2 and 4 nodes?**
- On 1 node each rank holds four times more data than on 4 nodes, so more of it comes from DRAM. Removing array passes therefore saves more on 1 node (reading the U matrix once instead of three times: −6.4% against −2.3%). On 1 node we measured it: with the patches, L1 refills from DRAM fall 17% while instructions fall 4%. On 4 nodes we tested the same idea by giving each core less memory: with 64 ranks per node the patches gain 7.9% on all memory channels and 11.4% on half of them. The same reasoning explains the super-linear scaling, and there we measured counters at 1, 2 and 4 nodes: per cell and step, the L1 refills from DRAM fall by 30% from 1 to 4 nodes, almost all in the sparse-matrix kernels, whose scattered cell arrays shrink to 1 MB per rank and fit in L3.

**Q7. What is proven and what is not?**
- Proven: the timings (same-period controls, 3 or more runs on 4 nodes), bit-identical `coefficient.dat` and identical solver logs (every residual, to 16 digits), and the pinning problem (seen in `/proc` during the solve).
- Shown by experiment on 4 nodes: the step time follows the memory bandwidth, not the number of cores (half the cores: −1% to +2%; half the memory channels: 2.1–2.2× slower, as the bandwidth drops 2.22×), and the patches gain more when each core has less memory.
- Measured with hardware counters (1 node): the patches cut L1 refills from DRAM by 17% with 4% fewer instructions.
- Not proven: the DRAM traffic in bytes and the share of the peak bandwidth (we cannot read the memory-controller counters), and how much of the memory effect is DRAM bandwidth and how much is L3 capacity. We present those as hypotheses. (The cache explanation of the super-linear scaling is now measured with counters at 1, 2 and 4 nodes; see Q6.)

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
- Cd after 80 steps depends on the decomposition. The organisers' own `scotch` run on ASPIRE-2A also gives 0.327 at 80 steps, and their notes say that `hierarchical` and `scotch` differ by 0.7%, 3.0% and 3.5% at 40, 80 and 150 steps. Our Basic (`scotch` mapped onto the node) gives 0.334, `scotch` with its defaults 0.327, and the Bonus (`multiLevel`) 0.323. Against `scotch` with its defaults, the mapping moves Cd by +0.8%, +2.1% and +3.2% and `multiLevel` by +0.5%, −1.3% and +2.6%, no more than the organisers' two methods differ from each other. The Bonus value is identical to its unmodified baseline, so the gap does not come from our source changes.
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
- Yes. `build/build.pbs` builds from the official public sources, and `run/submit.sh 1|2|4` runs the whole Allrun chain with plain `qsub`. We re-ran them ourselves (Bonus on 2026-10-07, the final Basic on 2026-10-16): at every node count `coefficient.dat` was bit-identical to our recorded runs, and the time within 0.4% of our recorded means (Basic on 4 nodes: 2.9046 against 2.8976 s/step).

**Q19. Why did you not tune the hierarchical coefficients instead?**
- We kept the case default `(16 8 4)` as the control. scotch was 10.5% faster on 4 nodes in alternated runs, so we spent the remaining effort on scotch and on placement. We have not searched other `nHierarchical` factorisations.

**Q20. What would you do next?**
- The remaining imbalance between ranks (Q21): balance each stage of a step, for example with weights from measured per-rank times. Making the global sums cheaper (the GAMG coarsest level on fewer ranks) or the network faster (UCX over RC) did not help (Q2).
- Moving fewer bytes, the other lever: fusing the assembly of U, k and omega across terms, or the GAMG residual with its restriction. We expect a few per cent from these, not another 10% (Q34).

**Q21. Do you know where the imbalance between ranks comes from?**
- Partly. With OpenFOAM's own profiling on all 512 ranks, the computation per rank still varies by 6% (max/median 1.063). Cell counts are balanced within 1% and do not explain it; wall faces explain a little (r = 0.43, 2.8% of the work). Balancing the wall part perfectly would only take it to 1.056, so a wall-weighted split is not worth it. Nodes and NUMA domains show no systematic difference; the variation follows groups of neighbouring subdomains, so it is a property of the mesh regions. Hardware counters on 32 ranks of 4 nodes (#66) show what it is: the slowest and the fastest rank execute about the same number of instructions, but the slowest reads more than twice as many lines from DRAM. A rank's computation follows its DRAM refills (r = +0.69), not its instructions (r = −0.09) or its cells (r = +0.24): it depends on how well each subdomain's data fits in cache.

**Q22. Is the flow video from your scored run?**
- No. Benchmark runs write no flow fields (`controlDict.noWrite`), so we ran the same official case once more with output function objects added: on Genkai, 4 nodes, 150 iterations, because ASPIRE-2A had no free nodes that day. It is a picture of the flow, not a measurement, and the flow does not depend on the machine. The added outputs do not change the computation: its Cd after 150 iterations, 0.28455000886604298, is identical to every digit with Genkai's official 4-node run.
- （メモ）自分からは言わず、聞かれたら答えます。Cdが全桁一致するのは同じ機械・同じ分割の公式runとで、ASPIRE-2Aの値とは分割が違うので数%違います（150 stepでは分割でCdが動きます、Q12）。

**Q23. How do you know it is memory-bound if you could not read the memory counters?**
- On ASPIRE-2A users cannot read the memory-controller counters, so we tested it by moving the ranks. On 4 nodes, 64 ranks per node are as fast as 128 when they keep all memory channels, and 2.1–2.2× slower when the same 64 ranks share half of the channels — as much as the measured bandwidth drops. Compiler flags and PGO change nothing (within 0.13%), and our patches, which keep every operation, gain the most where memory is scarcest.
- （メモ）コアを半分にした比較は、分割が512から256に変わります。ただ、帯域に比例しない部分は1 stepあたり約0.1 sしかないので、分割の違いで「コアが半分でも同じ速さ」を説明することはできません。チャネルを半分にした比較は、分割もrankも同じです（#61）。

**Q24. Bandwidth or latency?**
- Bandwidth. If the latency of each core's memory requests set the speed, halving the cores would halve the throughput; it changed by −1% to +2%. Halving the memory channels slowed a step 2.1–2.2×, in line with the bandwidth (2.22×).
- （メモ）1コア2 rankのSMT（#43）では5.7倍遅くなり、どちらとも決められませんでした。今回の配置の実験で決まりました。

**Q25. Most demand refills come from L2. Isn't the data in cache?**
- Demand refills do not count hardware prefetches. The arrays we stream are brought from DRAM into L2 by the prefetcher, so their loads show up as L2 hits. With the patches, L2 accesses including prefetches fall 10% and DRAM refills 17%.

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
- Not the numerical work. Every solve does the same sweeps, residuals and norms as before: in the logs of the baseline and the Bonus, every solve of every step has the same iteration count and the same residuals, to 16 digits. The instructions we removed are copies, allocations and temporary face fields, the second and third pass over the same matrix arrays, and boundary values that nobody reads.
- （メモ）命令数−4.1%に対して、DRAMからのrefillは−17.2%、cyclesは−10.8%です（S6）。ログの比較は15枚目のメモにあります（1/2/4ノードで371、771、1,475行が全行一致）。

**Q34. Is another 10% possible?**
- Not with the same math and the same work per step, we think. A step follows the memory bandwidth (12th slide), so only moving fewer bytes or reusing more data from cache can help. Our remaining ideas — fusing the assembly of U, k and omega across terms, the GAMG residual with its restriction, the Laplacian coefficients with the diagonal — each remove a pass or two over the face arrays: a few per cent together. Gains of 10% need a different computation (fewer iterations, lower precision), which the rules prohibit, or a change that only the benchmark's fixed iterations allow (S17).
- （メモ）Basicでは、#61でノードあたり64 rank（全チャネル）が128 rankより1.1%速かった（対応付けの前、各2本）程度です。Gauss-Seidelの複数sweepを、更新の順序を保ったままキャッシュの中で回す（temporal blocking）なら大きく減らせる可能性はありますが、非構造メッシュではまだ研究の段階です。

**Q35. Can you show a roofline?**
- Not a measured one on ASPIRE-2A. The DRAM bytes need the memory-controller counters, which users cannot read, and the core counters miss the lines that the prefetchers bring in. What we can say: the sparse-matrix sweeps do about 0.1 flop per byte, about 1/100 of the ridge point of a node (4.1 TFLOP/s ÷ 290 GB/s ≈ 14 flop/byte), so they sit far under the bandwidth roof, and halving the bandwidth makes a step 2.2× slower.
- （メモ）rooflineの図を描くなら、帯域の屋根（290 GB/s）と、0.1 flop/Bの縦線までです。達成した性能の点は、FLOPを数えていないので置けません。

---

## 発表の準備

- pptxへの反映（10/20に済み）：第3版で挙げていた修正（「EPIC」→「EPYC」、8 NUMA domains、4枚目の図ほか）、第4版の変更（旧課題の姿勢、おまけの#68、Q&A目次、旧スライドの整理）、10/20の変更（配置の見直し、MPIの上位3つを本編7枚目へ、補足23枚目の進め方）、10/21の変更（色、注記とissue番号の削除、図と表の番号、各ジョブの点の図、進め方を本編9枚目へ、補足32枚目の追加、再現性スライドの削除）は、改訂版pptx（`Tokyo Rapids with RIKEN Presentation (HPC revised).pptx`）に入っています。作り直すときは`deck/build.sh`を使います。pptxを手で直したら、作り直す前にその変更を`deck/build_deck.py`に入れます。
- 改訂版pptxをBoxのデッキへ移すこと：Boxのデッキを置き換えるか、改訂版の1〜43枚目を「スライドの再利用」で移します。AIパート（44枚目以降）は改訂版でも元のデッキと同じです。
- 本編20枚を、タイマーで通しで練習します。各スライドに「時間が足りないときの1文」を決めておきます。
- 話す人と交代の位置を決めます（Qwenとの切り替えも）。HPCの後にAIを話すなら、補足（21〜43枚目）はスライドショーで「44」Enterで飛ばせます。
- 数値は提出物の`README.md`と同じものを使います（2.898 / 2.599 / −10.3%、3.296）。baselineは3.65です。桁は上の「数値の桁」に従います。
- 補足スライドは本編の後ろに置き、22枚目のQ&A目次から1クリックで出せます。
- （任意）ISC26の課題にある「ログから描くCdの収束グラフ」は、まだデッキにありません。足すなら、150 stepのrunの`coefficient.dat`から描いて補足40枚目（DRAG COEFFICIENT CHECKS）の隣に置きます。
- 図の文字が小さければ、`.svg`を開いて拡大するか、pptxの側で書き直します。デッキの各ジョブの点の図（`p*.png`）は`deck/deck_plots.py`がスライドの大きさで描くので、文字の大きさはそこで変えます。

## 根拠

- 図の元データ：リポジトリの`presentation/openfoam/data/`。主催者の参照値は`tasks/4.3 OpenFOAM Application Notes - ASPIRE-2A.md`とそのログ（`tasks/4.3-aspire2a-logs/`）。
- 実験の記録：issue #36〜#38（Basic）、#42、#44、#50、#51（Bonus）、#41、#53（profile）、#46（I/O、OSノイズ）、#47（ばらつき）、#48、#49（通信）、#54（提出スクリプトの再現）、#55（カウンタ）、#56、#60（OFIとUCX）、#57（OpenFOAM組み込みのprofiling）、#58（UCXのRC、GAMGの最も粗い段）、#59（PGO）、#61（コアとメモリのどちらが律速かを、配置だけを変えて確かめた実験）、#62（baselineの1/2/4ノードとプロファイル）、#63（Basicのscotchの対応付け）、#66（ノード数ごとのカウンタ、rank間の不均衡）、#68（固定反復で使われない残差）。
- 提出物：Boxの`Tokyo_Rapids_with_RIKEN_Submission/openfoam/`。
