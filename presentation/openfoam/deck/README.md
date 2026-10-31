# チームのデッキのOpenFOAMパートを作るスクリプト

チームのデッキを入力にして、OpenFOAMパートを [`../slides.md`](../slides.md) の第7版（11/01）で作り直したpptxを出力します。スライドの文、原稿、根拠の正本は `slides.md` で、このフォルダはそれをpptxにする道具です。

```bash
presentation/openfoam/deck/build.sh [INPUT.pptx] [OUTPUT.pptx]
```

- 入力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation.pptx`、出力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx` です。入力の元はBoxの `Tokyo_Rapids_with_RIKEN_Submission/presentation/` にあります。デッキはリポジトリに入れません。Boxのpptxはチームが別に編集しているので、上書きしません。
- 入力は、OpenFOAMパートが10/29のビルドのまま（1〜46枚目：表紙、本編2〜21でチームのrooflineが14、補足の扉22、Q&A目次23、補足24〜45、共通の再現性スライド46）で、47枚目からAIパートが続くデッキです。11/01には、Boxのデッキ（10/31、184枚。AIパートだけがチームの手で更新されていた）をWindows側でコピーして入力にしました。
- `build.sh` は、まず `deck_figures.py` で `../figures.py` の図をデッキ用に描き、`deck_plots.py` で各ジョブの点を描く図とCdの収束の図をスライドの大きさで描きます。次に `build_deck.py` でpptxを作ります。図は一時フォルダに描き、終われば消します。
- 出力のOpenFOAMパートは、表紙1、本編2〜15（`slides.md` の本編1〜14）、補足の扉16、Q&A目次17、補足18〜34（17枚）、共通の再現性スライド35です。AIパートは36枚目からです。
- 各スライドは入力のスライドの上で作り直すので、slide idと、チームが2桁の番号のために広げたスライド番号の欄が残ります。余った11枚（チームのrooflineを含む）は消します。PowerPointのセクション（入力では全スライドが1つのセクション）も新しい並びに合わせます。
- 本編のノートは `slides.md` の各スライドの節（原稿、訳、メモ）から作ります（`build_deck.py` の `plan_notes()`）。原稿を直すときは `slides.md` だけを直せばよく、ビルドし直すとノートに入ります。表紙、Q&A目次、補足のノートは `notes.py` にあります。
- AIパートは1バイトも変えずに残します。共通の再現性スライドは、OpenFOAMのpatchの並びだけを最終版にします（すでに最終版なら何もしません）。

## ファイル

| ファイル | 中身 |
|---|---|
| `build_deck.py` | 各スライドの中身と並び。1つの関数が1枚を作る。入力のOpenFOAMパート46枚の題名が10/29版と違えば止まる |
| `notes.py` | 表紙、Q&A目次、補足のノート（質疑で言う英語の答えと、チーム向けの日本語のメモ） |
| `decklib.py` | テンプレートに合わせた文字、表、グラフの部品。数字と単位を改行で分けない `tidy()` と、baseline・Basic・Bonusの語に色を付ける `tier_runs()` |
| `palette.py` | スライドと図の色 |
| `deck_figures.py` | `../figures.py` をデッキ用に実行する（補足の92本のばらつきの図に使う） |
| `deck_plots.py` | 速さを比べる図（各ジョブの点と平均の棒、平均とSDの数字）と、Cdの収束の図を、スライドに置く大きさで描く |
| `render.ps1` | PowerPointでスライドをPNGに書き出す（Windows、確認用） |
| `qa_grid.py` | 書き出したPNGを並べた一覧画像を作る（確認用） |
| `qa_gaps.py` | 書き出したPNGで、各スライドの内容の下に残った余白を測る（確認用） |

図の元データは `../data/` です。11/01に足した2つは次のとおりです。

- `cd_iterations_4node.csv`：4ノードの各反復のCd。Basic、Bonus、ソースを変える前のrunは、Boxの提出物の `openfoam/results/4node/`、`openfoam/bonus/results/4node/`、`openfoam/bonus/f3-baseline/4node/` の `coefficient.dat` から、主催者のhierarchicalとscotchは `tasks/4.3-aspire2a-logs/*-4node/coefficient.dat` から取りました。
- `callstack_phases_fa4f5b0.csv`：最初の4つの変更の版（fa4f5b0、#53）のCrayPATのstack sample 2,396本の、段階ごとの数とそのうちMPIの中にあった数。`../../../research/profile-reaggregation-fa4f5b0/summary.md` の「Phase totals」と「MPI by step phase」の表から写しました。

## 作りの決まり（第7版）

`slides.md` の「見た目と言葉の決まり」をデッキで守るための決まりです。

- テンプレートのレイアウト「白背景_タイトルとテキスト_横のコピー」に載せ、タイトルはマスターの32 pt、本文はメイリオです。タイトルはチームのAIパートに合わせて大文字にします。
- タイトルの下の主張の行、TAKEAWAYの札、Figure N・Table Nの番号、余白を埋めるカードは置きません。図や表の上には、何の図かを表す短い見出し（紺の太字）だけを置きます。
- 箇条は1つの完結した文で書きます。本文は18 pt以上、表は16 pt以上です（補足の大きな表は11 ptまで下げています）。
- 表は横の罫線だけです。見出しの行は白地に紺の太字で、下に紺の線を引きます（`decklib.table()` の既定）。
- 色は `palette.py` にまとめてあります。baselineは緑、Basicは黄（濃い黄土色）、Bonusは赤で、本文、表、見出しのどこに出ても、その語は自動でその段の色になります（`tier_runs()`）。主催者の「common baseline」「Common baseline」には色を付けません。紫は遅いもの・壊れているもの（待ち、読めないカウンタ、遅い配置）だけに使い、1枚で強調するのは1つまでにします。
- 時間の図には、各ジョブの点、平均の棒、平均（有効数字4桁）と標準偏差（%）を描きます（`deck_plots.py` の `stats()`）。1本しかないときは「1 job」と書きます。
- 数値は `s/step` と書き、%の前に空白を入れません（「21%」）。`tidy()` は「21 %」を「21%」に直します。
- 見出しが1行に収まらないと本文に重なるので、大文字で32文字ほどまでにします（11/01に、本編15枚目と補足の2枚を短くした）。
- 分割の絵、流れの動画は、入力のデッキに入っているものを使います。分割の絵は3列×3段の合成画像から列を切り出しています。

## 確かめ方

1. `build.sh` が `saved ... with N slides` と全スライドの題名を出して終わること。11/01の入力（184枚）では173枚です。
2. `render.ps1` で書き出して、全スライドを等倍で見る。見るのは、文字のはみ出し、見出しの折り返し、要素の重なり、表の数字が別の行に分かれていないか、です。PowerPointは255文字を超えるパスを開けないので、`render.ps1` は短いパスにコピーしてから開きます。

    ```bash
    powershell.exe -File "$(wslpath -w presentation/openfoam/deck/render.ps1)" -Pptx "$(wslpath -w "$HOME/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx")" -OutDir 'C:\Users\<you>\AppData\Local\Temp\deck_png' -Slides "1,2,3"
    ```

3. 入力のAIパート（47枚目〜）と出力のAIパート（36枚目〜）で、各スライドのXMLとノートのXMLがバイト単位で同じこと（python-pptxで `slide.part.blob` と `notes_slide.part.blob` を比べる）。
4. Q&A目次（17枚目）の各行が、その番号のスライドへ飛ぶこと。

## 注意

- `build_deck.py` は、入力のスライドを位置で使い、素材（動画、分割の絵、共通の再現性スライド）もそこから拾います。チームがOpenFOAMパートを直したデッキを入力にするときは、先に変更前のデッキと1枚ずつ比べて手直し（足したスライド、直した数値や配置）を探し、意図したものか確かめてから `INPUT_TITLES` と各スライドの位置を書き換えます。
- 出力のpptxを手で直したときは、作り直す前に、その変更を `build_deck.py` か `slides.md` に入れます。作り直すと上書きされるためです。入れる前に、その変更が意図したものか確かめます（10/21にpptxから消えていた再現性スライドは、誤って消したものでした）。
- 第6版の出力は `~/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised, 6th edition).pptx` に残してあります。第6版のコードはgitの `a1f18a3` 以前です。
- PowerPointはen dash（3.19–3.58）の後ろで改行します。改行を避けたい範囲は「3.19 to 3.58」と書きます（`tidy()` が改行しない空白でつなぎます）。
- 改行しない空白でつないだ語が枠より長いと、PowerPointはその語の途中で折ります。表の列は「−12.16%」や「2 nodes」が収まる幅にします。
- グラフのデータラベルの書式に条件（`[<2]""` など）を書くときは、`bar_chart()` の `label_format` に渡します。`number_format` はグラフのXMLにそのまま入るので、`<` を書くと壊れます。
