# チームのデッキのOpenFOAMパートを作るスクリプト

チームのデッキを入力にして、OpenFOAMパートを [`../slides.md`](../slides.md) の第8版（11/03の10回目まで）で作り直し、HPCだけのpptxを出力します。スライドの文、原稿、根拠の正本は `slides.md` で、このフォルダはそれをpptxにする道具です。

```bash
presentation/openfoam/deck/build.sh [INPUT.pptx] [OUTPUT.pptx] [PICTURES]
```

- 入力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation.pptx`、出力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation HPC (8th edition).pptx` です。入力の元はBoxの `Tokyo_Rapids_with_RIKEN_Submission/presentation/` にあります。デッキはリポジトリに入れません。Boxのpptxと、ユーザーがコメントを付けた `~/apac26/Tokyo Rapids with RIKEN Presentation HPC.pptx` は、チームが別に編集しているので、上書きしません。
- `PICTURES` は、Boxの `presentation/openfoam/decomposition/` の写しです（WSLからはBoxを読めないので、Windows側でコピーする）。既定は `~/apac26/decomposition` で、そこの `decomposition-numa.png`（分割をノードとNUMA領域ごとに塗った絵、3840×2220）と `decomposition-numa-scotch-domains-vs-multilevel.png`（玄界で描いたBasicとmultiLevel、3840×3330）を使います。
- 入力は、OpenFOAMパートが10/29のビルドのまま（1〜46枚目：表紙、本編2〜21でチームのrooflineが14、補足の扉22、Q&A目次23、補足24〜45、共通の再現性スライド46）で、47枚目からAIパートが続くデッキです。11/01からは、Boxのデッキ（10/31、184枚）をWindows側でコピーして入力にしています。
- `build.sh` は、まず分割の絵を一時フォルダに写し、`deck_figures.py` で `../figures.py` の図をデッキ用に描き、`deck_plots.py` で各ジョブの点を描く図とCdの収束の図をスライドの大きさで描きます。次に `build_deck.py` でpptxを作ります。一時フォルダは終われば消します。
- 出力はHPCだけのデッキです（11/02、チームがHPCとAIのデッキを分けたため）：表紙1、本編2〜21（`slides.md` の本編1〜20）、補足の扉22、Q&A目次23、補足24〜43（20枚）。スライドショーで映るのは1〜21枚目で、補足の扉から補足の最後までは非表示です。入力のAIパート、チームのroofline、Qwenと共通の再現性スライド（11/01にユーザーの判断で外した）は出力しません。
- チームはデッキをOneDriveで編集し、チームメイトがrobocopyで定期的にBoxへ上げています。HPCの枚を直すときは、これまでの入力（Boxの10/31版のコピー）から作り、OneDriveのデッキへはユーザーが貼ります。
- 各スライドは入力のスライドの上で作り直すので、slide idと、チームが2桁の番号のために広げたスライド番号の欄が残ります。第8版で増えた本編の枚と補足の枚は、入力の余った枚（補足だった非表示の枚とチームのroofline）の上に作り、本編に使う枚は表示にします（`main_slide()`）。PowerPointのセクションも新しい並びに合わせます。
- 本編のノートは `slides.md` の各スライドの節から作ります（`build_deck.py` の `plan_notes()`。本編が20枚でなければ止まる）。原稿、訳、その枚の「想定質問：」に挙げた問（答えは `slides.md` の想定問答の節から、「（メモ）」の行を除いて引く）、「補足：」に挙げた補足の枚の順です（ユーザー、11/03：メモは乱雑で分かりにくいので、関係する想定質問と補足を）。メモはノートに入りません。原稿や答えを直すときは `slides.md` だけを直せばよく、ビルドし直すとノートに入ります。表紙、Q&A目次、補足のノートは `notes.py` にあります。
- `slides.md` の「補足：」と「見せる枚：」は、「30（Pinning and decomposition）」のようにデッキの番号と見出しで書きます。`check_references()` が出力の見出しと照らし合わせ、合わないものを `slides.md: slide 30 is ...` と出します（枚の並びを変えたときに、参照を直し忘れないため）。

## ファイル

| ファイル | 中身 |
|---|---|
| `build_deck.py` | 各スライドの中身と並び。1つの関数が1枚を作る。入力のOpenFOAMパート46枚の題名が10/29版と違えば止まる。ノードのアイコンの図（`Node`、`node()`）、CPUとメモリの帯の図（`usage_bar()`）、変更の図（`u_diagram()`、`residual_diagram()`）もここで図形として描く。`decomposeParDict`の行は`code()`で、等幅の字（Consolas）で書く |
| `notes.py` | 表紙、Q&A目次、補足のノート（質疑で言う英語の答えと、チーム向けの日本語のメモ） |
| `decklib.py` | テンプレートに合わせた文字、表、グラフの部品。数字と単位を改行で分けない `tidy()` と、Baseline・Basic・Bonusの語に色を付ける `tier_runs()` |
| `palette.py` | スライドと図の色 |
| `deck_figures.py` | `../figures.py` をデッキ用に実行する（補足の92本のばらつきの図に使う） |
| `deck_plots.py` | 速さを比べる図（各ジョブの点と平均の棒、平均とSDの数字）、Cdの収束の図、call stackのflame graphを、スライドに置く大きさで描く。段どうしの矢印と変化の%、scalingの倍率は画像に入れず、図ごとの `<図>.json` に位置を書く（`layout()`） |
| `render.ps1` | PowerPointでスライドをPNGに書き出す（Windows、確認用） |
| `qa_grid.py` | 書き出したPNGを並べた一覧画像を作る（確認用） |
| `qa_gaps.py` | 書き出したPNGで、各スライドの内容の下に残った余白を測る（確認用） |

図の元データは `../data/` です。11/01に足した3つは次のとおりです。

- `cd_iterations_4node.csv`：4ノードの各反復のCd。Basic、Bonus、ソースを変える前のrunは、Boxの提出物の `openfoam/results/4node/`、`openfoam/bonus/results/4node/`、`openfoam/bonus/f3-baseline/4node/` の `coefficient.dat` から、主催者のhierarchicalとscotchは `tasks/4.3-aspire2a-logs/*-4node/coefficient.dat` から取りました。
- `callstack_phases_fa4f5b0.csv`：最初の4つの変更の版（fa4f5b0、#53）のCrayPATのstack sample 2,396本の、段階ごとの数とそのうちMPIの中にあった数。`../../../research/profile-reaggregation-fa4f5b0/summary.md` の「Phase totals」と「MPI by step phase」の表から写しました。
- `callstack_folded_fa4f5b0.txt`：同じ2,396本を、flame graphの形（「段階;関数;…;関数 本数」の1行が1通りのstack、390行）に折りたたんだもの。MPIの中のstackは、OpenFOAMが呼んだMPIの関数で止めています。成果物の保管庫の生のsample（Actions 37529785072 の `profile-raw.tar.zst` の `profile/raw/craypat/stack-samples/rank-*.txt`）から、`uv run -q --no-project python -I analyse.py <stack-samples> <summary.md> <この.txt>` で書き出しました（`analyse.py` は `research/profile-reaggregation-fa4f5b0/`）。段階ごとの本数とMPIの本数は `callstack_phases_fa4f5b0.csv` と一致します。

## 作りの決まり

`slides.md` の「見た目と言葉の決まり」をデッキで守るための決まりです。11/01と11/02にユーザーが決めたもの（真っ黒で太字の文字、青の強調、単位、縦軸の時間と原点0、図の番号と注釈、SD、余白をならす）を含みます。

- テンプレートのレイアウト「白背景_タイトルとテキスト_横のコピー」に載せ、タイトルはマスターの32 pt、本文はメイリオです。タイトルは大文字にします。
- 文字は完全な黒（`palette.INK` = 000000）で、太字が既定です（`add_text()`、`table()`、`bullets()`、図の中の文字も）。強調はテーマ色の紺（`NAVY`）で示し、太さでは示しません。
- タイトルの下の主張の行、TAKEAWAYの札、余白を埋めるカードは置きません。文の塊の上には、短い見出し（紺）を置きます（固定の枚の「Expected」「Found」「Cause」「Fixed」も同じ、`steps()`）。
- 図には、図の下に「Figure N. 一文の注釈」を付けます（`caption()`、`figure()`）。表には、表の上に「Table N. 一文の注釈」を付けます（`table_caption()`）。番号はスライドの順に数え、本編はFigure 1、Table 1から、補足はFigure S1、Table S1からです。
- 箇条は1つの完結した文で短く書きます。時間を言うだけの文は表にします（11/02）。本文は18 pt以上、表は16 pt以上です（補足の大きな表は11 ptまで下げています）。表の行は1行に収まる文にします（PowerPointでは、メイリオの太字16 ptは1文字あたり約0.14 inで、8 inの列に約57文字）。
- 数値には、よほど場所が足りないとき以外、単位を付けます（3.650 s、290 M calls）。効かなかった手の結果は、+−ではなく「0.8% slower」のように言葉で書きます（11/02）。図と表には、実験をした日付を書きません（11/02の2回目）。
- OpenFOAMの設定は、`decomposeParDict`の行をそのまま、等幅の字で左に細い線を引いて示します（`code()`、11/02の2回目）。長い値（scotchの`strategy`）は「…」にします。
- 表は横の罫線だけです。見出しの行は白地に紺で、下に紺の線を引きます（`decklib.table()` の既定）。まとまりの行（意図別の変更の表）は薄い地に紺で、列をまたいで1つにします。一緒に測った変更の値は、並んだ行のセルを縦に1つにして（`merge_down()`）、「with 0008, 0010  −2.0%」のようにwithを前に、%を右端にそろえて書きます（11/03）。
- 段の名前は、Basic、Bonusと同じく先頭を大文字にして「Baseline」と書きます。主催者の公式の結果（`tasks/5. Common Baselines.md` の共通ベースライン）は、スライドでは「Official」と書きます。ソースを変える前のrun（pre-change baseline）は私たちのBaselineではないので、小文字のままです。
- 色は `palette.py` にまとめてあります。Baselineは緑、Basicは黄（濃い黄土色）、Bonusは赤で、本文、表、見出しのどこに出ても、その語は自動でその段の色になります（`tier_runs()`）。CPUとメモリの図（`node()`、`usage_bar()`）は、rankが動くコアを紺、使うメモリチャネルを基板のような緑（`MEMORY`）にします。メモリの限界の枚では、半分にした数を赤（`RED`）にします（どちらもユーザーの手直し、11/02）。チャネルを半分にした段の時間と帯域も赤で、「2.2 times the time」は黒です（ユーザーの手直し、11/03 18:29）。変更を図にした枚の4ノードの変化も赤です（ユーザーの手直し、11/03）。各ジョブの図の上の変化の矢印と%は赤で、矢印は6 ptです（`overlay()`、`tiers()`、`pairs()`、ユーザーの手直し、11/03 19:19）。そのほかの矢印は黒で（remote memoryへの矢印だけ灰色）、1枚目の流れとメモリの限界の枚の矢印は6 ptです。分割の絵の上の名前はテンプレートの青（`PICTURE`、003894）、変更を図にした枚の箱の文字は黒です（どれも11/03 19:19の手直し）。表の「3.650 → 2.898」のような時間は、段のものを段の色にします（`chain()`、同じ手直し）。私たちのBaselineの値は、どの枚でも3.650（#62）です（11/03の12回目）。色を付ける結果は、Baseline、Basic、Bonusにあたるものだけで、どこに出ても同じ色にします（ユーザー、11/03の10回目）。固定なしのhierarchical（私たちのBaselineの設定）はBaselineの色、ノードの木（Basic）はBasicの色です（採否の例の図のKept、固定の図のNeither、分割の2枚の表の時間）。それ以外の結果（固定したhierarchical、plain scotch、配置の実験など）は、図の点を灰（`FAINT`）、平均と目盛りと見出しを黒にします（8回目と9回目：Basicの色が記録以外に出るのも、pinnedやscotchが青いのも混乱しやすい）。強調は矢印と紺です（10回目：紺は強調に使ってよい）。紺にするのは、表の見出しの行、効かなかった手の表の強調した行、固定の図で両方を固定して短くなった2群（点、平均の線、時間。紺の群の目盛りの名前は黒、`tiers()`、11回目）、分割の3枚（5、8、14枚目）の表の時間の変化です。92本のばらつきの図（`../figures.py` の `variability()`）は、ノード数を灰の濃淡と点の形で分けます。
- 時間の図は、時間を縦軸にし、各ジョブの点、平均の棒、各群の上に平均（有効数字4桁、単位付き）と標準偏差（%）を描きます（`deck_plots.py` の `stats()`）。1本しかないときはSDを書きません。ジョブの本数は点で分かるので、目盛りにも凡例にも書きません（11/02）。時間の軸は原点0から描き、ジョブの差が見える範囲の下は細い帯に縮めて、軸に波線を入れます（`zoomed()`、11/02）。段どうしの変化は赤の矢印と赤の%で示します（`tiers()`、11/03 19:19の手直し）。長い矢印の%はその中ほどの下に置けます（`arrows` の `(i, j, "below")`）。scalingは原点0からの1つの線形の軸に、1、2、4ノードごとに公式の結果、Baseline、Basic、Bonusを並べ、理想の時間を点線で描きます。scalingの図はスライドの高さまで大きくし、4倍を超える理由の文は、ユーザーが手で動かした位置に置きます（11/03）。
- 図の矢印、変化の%（補足の図の%も）、scalingの1ノードの何倍速いかは、画像に入れず、手で動かせるようにスライドの図形として図の上に重ねます（ユーザー、11/03：手で微調整するので。時間の数字は画像のまま）。`deck_plots.py` の `layout()` が、図を描き終えた位置を図の左下からの割合で `<図>.json` に書き（矢印の始点と終点、文字と揃え、大きさ、色）、`build_deck.py` の `figure()` が図を置くときに `overlay()` で重ねます。図にすでに描いた文字は、`layout(lift=...)` が位置を測ってから画像から外します。重ねた図形には、選択ウィンドウで見分けられるように、矢印は「Arrow k」、文字は「Number −10.7%」のように最初の行で名前を付けます（11/03の8回目）。
- 数値は `s/step` と書き、%の前に空白を入れません（「21%」）。`tidy()` は「21 %」を「21%」に直します。
- 見出しが1行に収まらないと本文に重なるので、大文字で32文字ほどまでにします。
- 流れの動画とメッシュの絵は、入力のデッキに入っているものを使います。どちらも入力の2枚目にあり、動画の自動再生はその枚のタイミングの設定にあるので、動画を置く本編9枚目（デッキの10枚目）を入力の2枚目の上に作り、本編1枚目には入力の2枚目からメッシュの画像を写します。分割の絵は、Boxの絵から列を切り出します。本編5枚目は`decomposition-numa.png`（3列×3段）のhierarchicalとscotch（domains (2 4 16)を入れる前のplain scotch）、8枚目は同じplain scotchと、`decomposition-numa-scotch-domains-vs-multilevel.png`（11/02に玄界で描いた2列×3段）のBasic（ノードの木）、14枚目は2つ目の絵のBasicとmultiLevelを使います。5枚目と8枚目は14枚目と同じ配置で、左に2つの分割のコードと、面と時間の表、右に2つの絵を置きます（`decomposition_pair()`、ユーザー、11/03の10回目）。どれも3つの画角（車体、中心断面、断面）を、各画角の左上の小さなラベルを外して1つずつ切り出し、中心断面と断面の間に細い隙間を空けて重ねます（`decomp_panel()`、`VIEW_ROWS`。10/09の絵のplain scotchの列のラベルは「Basic: scotch」のままで、今のBasicと食い違うので外す）。2つの絵は同じ段組みを1.5倍にしたものなので、行の位置はどちらの絵でも同じ割合です。凡例は、Boxの絵と同じ色（`../decomposition/render.py`）を、絵の下にPowerPointの図形で描きます（`numa_key()`）。

## 確かめ方

1. `build.sh` が `saved ... with N slides` と全スライドの題名を出して終わること。11/01の入力（184枚）では43枚です。
2. `render.ps1` で書き出して、全スライドを等倍で見る。見るのは、文字のはみ出し、見出しの折り返し、要素の重なり、表の行の折り返し（行が伸びて下の文に重なる）、表の数字が別の行に分かれていないか、です。PowerPointは255文字を超えるパスを開けないので、`render.ps1` は短いパスにコピーしてから開きます。

    ```bash
    powershell.exe -File "$(wslpath -w presentation/openfoam/deck/render.ps1)" -Pptx "$(wslpath -w "$HOME/apac26/Tokyo Rapids with RIKEN Presentation HPC (8th edition).pptx")" -OutDir 'C:\Users\<you>\AppData\Local\Temp\deck_png' -Slides "1,2,3"
    ```

3. Q&A目次（23枚目）の各行が、その番号のスライドへ飛ぶこと。
4. スライドショーで非表示（`<p:sld show="0">`）なのが、補足の扉から補足の最後まで（22〜43枚目）だけで、本編は表示されること。

## 注意

- `build_deck.py` は、入力のスライドを位置で使い、素材（動画、メッシュの絵）もそこから拾います。チームがOpenFOAMパートを直したデッキを入力にするときは、先に変更前のデッキと1枚ずつ比べて手直し（足したスライド、直した数値や配置）を探し、意図したものか確かめてから `INPUT_TITLES` と各スライドの位置を書き換えます。
- 出力のpptxを手で直したときは、作り直す前に、その変更を `build_deck.py` か `slides.md` に入れます。作り直すと上書きされるためです。入れる前に、その変更が意図したものか確かめます（10/21にpptxから消えていた再現性スライドは誤って消したものでしたが、11/01に出力から消えていたときは、ユーザーが外すと決めたものでした）。
- 第6版のコードはgitの `a1f18a3` 以前、第7版（AIパートも含む174枚）は `0bb74e3` です。
- PowerPointはen dash（3.19–3.58）の後ろで改行します。改行を避けたい範囲は「3.19 to 3.58」と書きます（`tidy()` が改行しない空白でつなぎます）。
- 改行しない空白でつないだ語が枠より長いと、PowerPointはその語の途中で折ります。表の列は「−12.16%」や「2 nodes」が収まる幅にします。
- グラフのデータラベルの書式に条件（`[<2]""` など）を書くときは、`bar_chart()` の `label_format` に渡します。`number_format` はグラフのXMLにそのまま入るので、`<` を書くと壊れます。
