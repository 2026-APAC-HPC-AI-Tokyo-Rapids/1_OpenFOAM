# チームのデッキのOpenFOAMパートを作るスクリプト

チームのデッキを入力にして、OpenFOAMパートを [`../slides.md`](../slides.md) の第7版（11/01）で作り直したpptxを出力します。スライドの文、原稿、根拠の正本は `slides.md` で、このフォルダはそれをpptxにする道具です。

```bash
presentation/openfoam/deck/build.sh [INPUT.pptx] [OUTPUT.pptx]
```

- 入力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation.pptx`、出力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx` です。入力の元はBoxの `Tokyo_Rapids_with_RIKEN_Submission/presentation/` にあります。デッキはリポジトリに入れません。Boxのpptxはチームが別に編集しているので、上書きしません。
- 入力は、OpenFOAMパートが10/29のビルドのまま（1〜46枚目：表紙、本編2〜21でチームのrooflineが14、補足の扉22、Q&A目次23、補足24〜45、共通の再現性スライド46）で、47枚目からAIパートが続くデッキです。11/01には、Boxのデッキ（10/31、184枚。AIパートだけがチームの手で更新されていた）をWindows側でコピーして入力にしました。
- `build.sh` は、まず `deck_figures.py` で `../figures.py` の図をデッキ用に描き、`deck_plots.py` で各ジョブの点を描く図とCdの収束の図をスライドの大きさで描きます。次に `build_deck.py` でpptxを作ります。図は一時フォルダに描き、終われば消します。
- 出力のOpenFOAMパートは、表紙1、本編2〜15（`slides.md` の本編1〜14）、補足の扉16、Q&A目次17、補足18〜35（18枚）です。入力の46枚目にあったQwenと共通の再現性スライドは、11/01にユーザーの判断で外しました。AIパートは36枚目からで、その謝辞（ACKNOWLEDGEMENTS）の後に、HPCとAIの記録をまとめた1枚（OUR RESULTS: HPC AND AI）を足します（11/01の入力では59枚目）。スライドショーで映るのは本編とAIパートの表示される枚と記録の枚で、補足の扉から補足の最後までは非表示です。
- チームはデッキをOneDriveで編集し、チームメイトがrobocopyで定期的にBoxへ上げています（11/01）。11/01 14:52のBoxのデッキには、この第7版のHPCパートがすでに貼り込まれていて（スライドIDは新しい）、OpenFOAMパートが10/29のビルドではないので、このスクリプトの入力にはなりません。HPCの枚を直すときは、これまでの入力（Boxの10/31版のコピー）から作り、OneDriveのデッキへはユーザーが貼ります。
- 各スライドは入力のスライドの上で作り直すので、slide idと、チームが2桁の番号のために広げたスライド番号の欄が残ります。flame graphの枚と記録の枚も入力の余った枚の上に作り、残りの10枚（チームのrooflineと共通の再現性スライドを含む）は消します。PowerPointのセクション（入力では全スライドが1つのセクション）も新しい並びに合わせます。
- 本編のノートは `slides.md` の各スライドの節（原稿、訳、メモ）から作ります（`build_deck.py` の `plan_notes()`）。原稿を直すときは `slides.md` だけを直せばよく、ビルドし直すとノートに入ります。表紙、Q&A目次、補足のノートは `notes.py` にあります。
- AIパートは1バイトも変えずに残し、記録の枚はその枚と枚の間に挟みます。記録の枚のAIの数字（`build_deck.py` の `AI_FLOW`）はAIパートのRESULTSとSUMMARYの枚の値で、AIパートの表示される枚からその値が消えるとビルドが止まります。そのときは `AI_FLOW` と `notes.py` の記録の枚のノートを直します。

## ファイル

| ファイル | 中身 |
|---|---|
| `build_deck.py` | 各スライドの中身と並び。1つの関数が1枚を作る。入力のOpenFOAMパート46枚の題名が10/29版と違えば止まる |
| `notes.py` | 表紙、Q&A目次、補足のノート（質疑で言う英語の答えと、チーム向けの日本語のメモ） |
| `decklib.py` | テンプレートに合わせた文字、表、グラフの部品。数字と単位を改行で分けない `tidy()` と、Baseline・Basic・Bonusの語に色を付ける `tier_runs()` |
| `palette.py` | スライドと図の色 |
| `deck_figures.py` | `../figures.py` をデッキ用に実行する（補足の92本のばらつきの図に使う） |
| `deck_plots.py` | 速さを比べる図（各ジョブの点と平均の棒、平均とSDの数字）、Cdの収束の図、call stackのflame graphを、スライドに置く大きさで描く |
| `render.ps1` | PowerPointでスライドをPNGに書き出す（Windows、確認用） |
| `qa_grid.py` | 書き出したPNGを並べた一覧画像を作る（確認用） |
| `qa_gaps.py` | 書き出したPNGで、各スライドの内容の下に残った余白を測る（確認用） |

図の元データは `../data/` です。11/01に足した3つは次のとおりです。

- `cd_iterations_4node.csv`：4ノードの各反復のCd。Basic、Bonus、ソースを変える前のrunは、Boxの提出物の `openfoam/results/4node/`、`openfoam/bonus/results/4node/`、`openfoam/bonus/f3-baseline/4node/` の `coefficient.dat` から、主催者のhierarchicalとscotchは `tasks/4.3-aspire2a-logs/*-4node/coefficient.dat` から取りました。
- `callstack_phases_fa4f5b0.csv`：最初の4つの変更の版（fa4f5b0、#53）のCrayPATのstack sample 2,396本の、段階ごとの数とそのうちMPIの中にあった数。`../../../research/profile-reaggregation-fa4f5b0/summary.md` の「Phase totals」と「MPI by step phase」の表から写しました。
- `callstack_folded_fa4f5b0.txt`：同じ2,396本を、flame graphの形（「段階;関数;…;関数 本数」の1行が1通りのstack、390行）に折りたたんだもの。MPIの中のstackは、OpenFOAMが呼んだMPIの関数で止めています。成果物の保管庫の生のsample（Actions 37529785072 の `profile-raw.tar.zst` の `profile/raw/craypat/stack-samples/rank-*.txt`）から、`uv run -q --no-project python -I analyse.py <stack-samples> <summary.md> <この.txt>` で書き出しました（`analyse.py` は `research/profile-reaggregation-fa4f5b0/`）。段階ごとの本数とMPIの本数は `callstack_phases_fa4f5b0.csv` と一致します。

## 作りの決まり（第7版）

`slides.md` の「見た目と言葉の決まり」をデッキで守るための決まりです。11/01にユーザーが決めたもの（真っ黒で太字の文字、青の強調、単位、縦軸の時間、図の番号と注釈、SD、余白をならす）を含みます。

- テンプレートのレイアウト「白背景_タイトルとテキスト_横のコピー」に載せ、タイトルはマスターの32 pt、本文はメイリオです。タイトルはチームのAIパートに合わせて大文字にします。
- 文字は完全な黒（`palette.INK` = 000000）で、太字が既定です（`add_text()`、`table()`、`bullets()`、図の中の文字も）。強調はテーマ色の紺（`NAVY`）で示し、太さでは示しません。
- タイトルの下の主張の行、TAKEAWAYの札、余白を埋めるカードは置きません。文の塊の上には、短い見出し（紺）を置きます。
- 図には、図の下に「Figure N. 一文の注釈」を付けます（`caption()`、`figure()`）。表には、表の上に「Table N. 一文の注釈」を付けます（`table_caption()`、11/01の6回目から）。番号はスライドの順に数え、本編はFigure 1、Table 1から、補足はFigure S1、Table S1からです。注釈は1行に収まる長さにします。
- 箇条は1つの完結した文で書きます。本文は18 pt以上、表は16 pt以上です（補足の大きな表は11 ptまで下げています）。余白が多い枚は、図を大きくするか、文字を大きくするか、行間（`line`）を広げて、下端の線（7.0 in）の近くまで使います。
- 数値には、よほど場所が足りないとき以外、単位を付けます（3.650 s、290 M calls）。表で列の見出しに単位があるときも、本編ではセルに単位を書きます。
- 表は横の罫線だけです。見出しの行は白地に紺で、下に紺の線を引きます（`decklib.table()` の既定）。
- 段の名前は、Basic、Bonusと同じく先頭を大文字にして「Baseline」と書きます（11/01の7回目）。主催者の公式の結果（`tasks/5. Common Baselines.md` の共通ベースライン）は、スライドでは「Official」と書きます（8回目）。ソースを変える前のrun（pre-change baseline）は私たちのBaselineではないので、小文字のままです。
- 色は `palette.py` にまとめてあります。Baselineは緑、Basicは黄（濃い黄土色）、Bonusは赤で、本文、表、見出しのどこに出ても、その語は自動でその段の色になります（`tier_runs()`）。主催者の「common baseline」「Common baseline」と、「pre-change baseline」には色を付けません。
- 時間の図は、時間を縦軸にし、各ジョブの点、平均の棒、各群の上に平均（有効数字4桁、単位付き）と標準偏差（%）を描きます（`deck_plots.py` の `stats()`）。1本しかないときは「1 job」と書きます。カウンタの図は、変更なしと変更ありの2本ずつの4つの組を点にし、その変化のSDを書きます。scalingは原点0からの1つの線形の軸に、1、2、4ノードごとに公式の結果（主催者のhierarchicalとscotchを1本ずつ、`data/organiser_reference_aspire2a.csv` の「full chain」「defaults」）、Baseline、Basic、Bonusを並べ、私たちの各段の1ノードの平均から求めた理想の時間を点線で描きます。12列の注記が重ならないように、図はスライドの横幅いっぱいに置き、公式の結果の注記は点の下に書きます（11/01の8回目。5回目はノード数ごとの枠で縦軸を枠ごとに半分、7回目は段ごとの並びだった）。
- 数値は `s/step` と書き、%の前に空白を入れません（「21%」）。`tidy()` は「21 %」を「21%」に直します。
- 見出しが1行に収まらないと本文に重なるので、大文字で32文字ほどまでにします（11/01に、本編15枚目と補足の2枚を短くした）。
- 分割の絵、流れの動画、メッシュの絵は、入力のデッキに入っているものを使います。流れの動画とメッシュの絵は入力の2枚目にあり、動画の自動再生はその枚のタイミングの設定にあるので、動画を置く本編7枚目（デッキの8枚目）を入力の2枚目の上に作り、本編1枚目には入力の2枚目からメッシュの画像を写します（11/01の8回目）。分割の絵は3列×3段の合成画像から、本編6枚目（デッキの7枚目）ではhierarchicalとscotchの列を切り出し、本編10枚目（デッキの11枚目）ではmultiLevelの列を段ごとに切り出して横に並べます（`DECOMP_VIEWS` は各段の上下の切り取りで、ParaViewが段の隅に書いた小さな注記を除きます）。

## 確かめ方

1. `build.sh` が `saved ... with N slides` と全スライドの題名を出して終わること。11/01の入力（184枚）では174枚です。
2. `render.ps1` で書き出して、全スライドを等倍で見る。見るのは、文字のはみ出し、見出しの折り返し、要素の重なり、表の数字が別の行に分かれていないか、です。PowerPointは255文字を超えるパスを開けないので、`render.ps1` は短いパスにコピーしてから開きます。

    ```bash
    powershell.exe -File "$(wslpath -w presentation/openfoam/deck/render.ps1)" -Pptx "$(wslpath -w "$HOME/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx")" -OutDir 'C:\Users\<you>\AppData\Local\Temp\deck_png' -Slides "1,2,3"
    ```

3. 入力のAIパート（47枚目〜）と出力のAIパート（36枚目〜、記録の枚を除く）で、各スライドのXMLとノートのXMLがバイト単位で同じこと（python-pptxで `slide.part.blob` と `notes_slide.part.blob` を比べる）。11/01の入力では、入力の47〜69枚目が出力の36〜58枚目、70〜184枚目が60〜174枚目です。
4. Q&A目次（17枚目）の各行が、その番号のスライドへ飛ぶこと。
5. スライドショーで非表示（`<p:sld show="0">`）なのが、補足の扉から補足の最後まで（16〜35枚目）と、入力で非表示だったAIパートの枚だけで、本編と記録の枚は表示されること。

## 注意

- `build_deck.py` は、入力のスライドを位置で使い、素材（動画、メッシュの絵、分割の絵）もそこから拾います。チームがOpenFOAMパートを直したデッキを入力にするときは、先に変更前のデッキと1枚ずつ比べて手直し（足したスライド、直した数値や配置）を探し、意図したものか確かめてから `INPUT_TITLES` と各スライドの位置を書き換えます。
- 出力のpptxを手で直したときは、作り直す前に、その変更を `build_deck.py` か `slides.md` に入れます。作り直すと上書きされるためです。入れる前に、その変更が意図したものか確かめます（10/21にpptxから消えていた再現性スライドは誤って消したものでしたが、11/01に出力から消えていたときは、ユーザーが外すと決めたものでした）。
- 第6版の出力は `~/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised, 6th edition).pptx` に残してあります。第6版のコードはgitの `a1f18a3` 以前です。
- 11/01にユーザーが出力に手で足した案（2枚目を複製した3枚目、6版の結論のような流れの図）は、`~/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised, user draft 11-01).pptx` に残してあります。その案は、本編2枚目の流れの図（`flow()`）として取り込みました。ほかの枚に手直しはありませんでした（図形と文字とノートを1枚ずつ比べた）。
- PowerPointはen dash（3.19–3.58）の後ろで改行します。改行を避けたい範囲は「3.19 to 3.58」と書きます（`tidy()` が改行しない空白でつなぎます）。
- 改行しない空白でつないだ語が枠より長いと、PowerPointはその語の途中で折ります。表の列は「−12.16%」や「2 nodes」が収まる幅にします。
- グラフのデータラベルの書式に条件（`[<2]""` など）を書くときは、`bar_chart()` の `label_format` に渡します。`number_format` はグラフのXMLにそのまま入るので、`<` を書くと壊れます。
