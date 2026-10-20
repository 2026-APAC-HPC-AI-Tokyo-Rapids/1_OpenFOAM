# チームのデッキのOpenFOAMパートを作るスクリプト

10/15版のチームのデッキを入力にして、OpenFOAMパートを作り直したpptxを出力します。作り直すのは本編20枚、補足の扉、Q&A目次、補足20枚です。スライドの主張、原稿、根拠の正本は [`../slides.md`](../slides.md) で、このフォルダはそれをpptxにする道具です。

```bash
presentation/openfoam/deck/build.sh [INPUT.pptx] [OUTPUT.pptx] [ASSETDIR]
```

- 入力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation.pptx`、出力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx` です。入力の元はBoxの `Tokyo_Rapids_with_RIKEN_Submission/presentation/` にあります。デッキはリポジトリに入れません。
- `ASSETDIR`（既定は `~/apac26/deck-assets`）には、入力のデッキにも `figures.py` にもない画像を置きます。今は `multiLevel-car-numa.png`（14枚目、ノードとNUMA領域で色分けしたmultiLevelの分割）だけで、Boxの `presentation/openfoam/decomposition/panels/` からコピーします。WSLからはBoxのファイルを読めない（I/Oエラーになる）ので、Windows側でコピーします。
- `build.sh` は、まず `deck_figures.py` で `../figures.py` の図をデッキ用に描きます（下の「作りの決まり」）。次に `build_deck.py` でpptxを作ります。図は一時フォルダに描き、終われば消します。
- AIパート（入力の25枚目以降）は1バイトも変えずに残します。共通の再現性スライド（入力の24枚目）は、固定の文字になっていたスライド番号の欄だけを番号のフィールドに置き換えて残します。

## ファイル

| ファイル | 中身 |
|---|---|
| `build_deck.py` | 各スライドの中身と並び。1つの関数が1枚を作る。入力が10/15版のデッキでなければ止まる |
| `notes.py` | 各スライドのノート。発表者が読む英語の原稿と、チーム向けの日本語のメモ（出典、注意、想定問答） |
| `decklib.py` | テンプレートに合わせた文字、カード、表、グラフの部品。数字と単位を改行で分けない `tidy()` と、baseline・Basic・Bonusの語に色を付ける `tier_runs()` |
| `palette.py` | スライドと図の色（下の「作りの決まり」） |
| `deck_figures.py` | `../figures.py` をデッキ用に実行する：図の下の注記を描かず、色と数値の書き方をスライドにそろえる。`figures.py` 自体は変えないので、レポートの図はそのまま |
| `render.ps1` | PowerPointでスライドをPNGに書き出す（Windows、確認用） |
| `qa_grid.py` | 書き出したPNGを並べた一覧画像を作る（確認用） |
| `qa_gaps.py` | 書き出したPNGで、各スライドの内容の下に残った余白を測る（確認用） |

## 作りの決まり

- テンプレートのレイアウト「白背景_タイトルとテキスト_横のコピー」に載せ、タイトルはマスターの32 pt、主張の1行は紺の20 pt（補足は18 pt）、本文はメイリオです。
- 本文は主張の下（1.6 in）から下端の線（7.0 in、スライド番号の上）までを使い、下に帯を残しません。空いたときは、まず図、グラフ、表を大きくし、次に文字を少し大きくし、残りを塊の間隔に配ります。キャプションとLESSONは下端の線にそろえます（`caption()`の既定はy=6.62、`lesson()`はy=6.52）。
- 色は `palette.py` にまとめてあります。
  - アクセントは紺（主張の1行、カードの見出し、箇条書きの点、表の見出し）です。
  - baselineはプラム、Basicは緑、Bonusは焦げ橙で、どれもアクセントの紺と見分けがつく色にしています。
  - 赤は、遅いもの・壊れているものだけに使います（固定が外れたrank、待ち時間、チャネル半分で遅くなる、など）。改善の数字はその段の色（Basicなら緑、Bonusなら橙）で書きます。
  - 文字の色はプロジェクタで薄く見えないよう濃くしています。背景の塗り（カード、表）は薄いままです。
  - 1枚に使う色をしぼります。強調したいもの1つに色を付け、ほかは紺と黒（灰）で書きます。
- baseline、Basic、Bonusの語は、本文、表、見出しのどこに出ても、自動でその段の色になります（`tier_runs()`）。凡例を置かなくても色が覚えられるようにするためです。白抜きの文字（表の見出し、札）と、「pre-change baseline」「its own baseline」（パッチを外したBonusのこと）、「the new baseline」は色を付けません。
- 数値は `s/step` と書き、%の前に空白を入れません（「21%」）。`tidy()` は「21 %」を「21%」に直します。`figures.py` も同じ書き方で描きます。`deck_figures.py` は、図の負の数をマイナス記号（−）にします（「21 %」「s / step」が紛れ込んでも直します）。
- 表とグラフは、PowerPointで編集できる表とグラフで作ります。各runの点を描く図（ばらつき、4ノードの道筋、コンパイラの比較、baselineのscaling）だけ、`figures.py` の画像を使います。
- 分割の絵、流れの動画、メッシュの図は、入力のデッキに入っているものを使います。分割の絵は3列×3段の合成画像から列と段を切り出しています。14枚目のmultiLevelの絵だけは `ASSETDIR` から取ります。
- 数値は [`../../../submission/openfoam/REPORT.md`](../../../submission/openfoam/REPORT.md) と `../data/*.csv` から取ります。数値を変えるときは、`slides.md`、`notes.py`、`build_deck.py` の3か所をそろえます。桁の決まりは `slides.md` の「数値の桁」にあります。

## 確かめ方

1. `build.sh` が `saved ... with 54 slides` と54枚の題名を出して終わること。
2. `render.ps1` で書き出して、全スライドを等倍で見る。見るのは、文字のはみ出し、要素の重なり、数字と単位や「1 v 1」が別の行に分かれていないか、です。PowerPointは255文字を超えるパスを開けないので、`render.ps1` は短いパスにコピーしてから開きます。

    ```bash
    powershell.exe -File "$(wslpath -w presentation/openfoam/deck/render.ps1)" -Pptx "$(wslpath -w "$HOME/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx")" -OutDir 'C:\Users\<you>\AppData\Local\Temp\deck_png'
    ```

3. `qa_gaps.py` で、各スライドの内容の下の余白を測る。内容のあるスライドは0.6〜0.8 inになります。1 inを超えるスライドは、下に帯が空いています（LESSONや縦中央にそろえた注記だけの列は除く）。

    ```bash
    uv run presentation/openfoam/deck/qa_gaps.py /mnt/c/Users/<you>/AppData/Local/Temp/deck_png
    ```

4. Q&A目次（22枚目）の各行が、その番号のスライドへ飛ぶこと。

## 注意

- `build_deck.py` は、入力のスライドの位置で素材を拾います（動画、メッシュ図、分割の絵、パッチ詳細の2枚）。だから入力は10/15版のデッキに限ります。チームがAIパートを更新したデッキでOpenFOAMパートを作り直すときは、次のどちらかにします。
  - この出力の1〜43枚目を、PowerPointの「スライドの再利用」で更新後のデッキへ移す。
  - `build_deck.py` の入力の確かめ（`check_input`）と素材の拾い方を、新しいデッキに合わせて書き換える。
- PowerPointはen dash（3.19–3.58）の後ろで改行します。改行を避けたい範囲は「3.19 to 3.58」と書きます（`tidy()` が改行しない空白でつなぎます）。
- 改行しない空白でつないだ語が枠より長いと、PowerPointはその語の途中で折ります。表の列は「−1.54%」や「2 nodes」が収まる幅にします。
