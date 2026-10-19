# チームのデッキのOpenFOAMパートを作るスクリプト

10/15版のチームのデッキを入力にして、OpenFOAMパートを作り直したpptxを出力します。作り直すのは本編19枚、補足の扉、Q&A目次、補足20枚です。スライドの主張、原稿、根拠の正本は [`../slides.md`](../slides.md) で、このフォルダはそれをpptxにする道具です。

```bash
presentation/openfoam/deck/build.sh [INPUT.pptx] [OUTPUT.pptx]
```

- 入力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation.pptx`、出力の既定は `~/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx` です。入力の元はBoxの `Tokyo_Rapids_with_RIKEN_Submission/presentation/` にあります。デッキはリポジトリに入れません。
- `build.sh` は、まず `figures_nocaption.py` で `../figures.py` の図を描きます。図の下の小さな注記は描かず、スライド側に読める大きさで書き直すためです。次に `build_deck.py` でpptxを作ります。図は一時フォルダに描き、終われば消します。
- AIパート（入力の25枚目以降）は1バイトも変えずに残します。共通の再現性スライド（入力の24枚目）は、固定の文字になっていたスライド番号の欄だけを番号のフィールドに置き換えて残します。

## ファイル

| ファイル | 中身 |
|---|---|
| `build_deck.py` | 各スライドの中身と並び。1つの関数が1枚を作る。入力が10/15版のデッキでなければ止まる |
| `notes.py` | 各スライドのノート。発表者が読む英語の原稿と、チーム向けの日本語のメモ（出典、注意、想定問答） |
| `decklib.py` | テンプレートに合わせた文字、カード、表、グラフの部品と、数字と単位を改行で分けない `tidy()` |
| `figures_nocaption.py` | `../figures.py` を、図の下の注記なしで実行する |
| `render.ps1` | PowerPointでスライドをPNGに書き出す（Windows、確認用） |
| `qa_grid.py` | 書き出したPNGを並べた一覧画像を作る（確認用） |

## 作りの決まり

- テンプレートのレイアウト「白背景_タイトルとテキスト_横のコピー」に載せ、タイトルはマスターの32 pt、主張の1行は紺の20 pt（補足は18 pt）、本文はメイリオです。
- 色は `figures.py` と同じで、baselineはマゼンタ、Basicは青、Bonusはオレンジです。強調は赤（#C0392B）です。
- 表とグラフは、PowerPointで編集できる表とグラフで作ります。各runの点を描く図（ばらつき、4ノードの道筋、コンパイラの比較、baselineのscaling）だけ、`figures.py` の画像を使います。
- 分割の絵、流れの動画、メッシュの図は、入力のデッキに入っているものを使います。分割の絵は3列×3段の合成画像から列と段を切り出しています。
- 数値は [`../../../submission/openfoam/REPORT.md`](../../../submission/openfoam/REPORT.md) と `../data/*.csv` から取ります。数値を変えるときは、`slides.md`、`notes.py`、`build_deck.py` の3か所をそろえます。桁の決まりは `slides.md` の「数値の桁」にあります。

## 確かめ方

1. `build.sh` が `saved ... with 53 slides` と53枚の題名を出して終わること。
2. `render.ps1` で書き出して、全スライドを等倍で見る。見るのは、文字のはみ出し、要素の重なり、数字と単位や「1 v 1」が別の行に分かれていないか、です。PowerPointは255文字を超えるパスを開けないので、`render.ps1` は短いパスにコピーしてから開きます。

    ```bash
    powershell.exe -File "$(wslpath -w presentation/openfoam/deck/render.ps1)" -Pptx "$(wslpath -w "$HOME/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx")" -OutDir 'C:\Users\<you>\AppData\Local\Temp\deck_png'
    ```

3. Q&A目次（21枚目）の各行が、その番号のスライドへ飛ぶこと。

## 注意

- `build_deck.py` は、入力のスライドの位置で素材を拾います（動画、メッシュ図、分割の絵、パッチ詳細の2枚）。だから入力は10/15版のデッキに限ります。チームがAIパートを更新したデッキでOpenFOAMパートを作り直すときは、次のどちらかにします。
  - この出力の1〜42枚目を、PowerPointの「スライドの再利用」で更新後のデッキへ移す。
  - `build_deck.py` の入力の確かめ（`check_input`）と素材の拾い方を、新しいデッキに合わせて書き換える。
- PowerPointはen dash（3.19–3.58）の後ろで改行します。改行を避けたい範囲は「3.19 to 3.58」と書きます（`tidy()` が改行しない空白でつなぎます）。
- 改行しない空白でつないだ語が枠より長いと、PowerPointはその語の途中で折ります。表の列は「−1.54 %」や「2 nodes」が収まる幅にします。
