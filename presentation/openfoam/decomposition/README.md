# 分割の可視化（#39）

4ノードrunの512分割が、メッシュのどこをどう切っているかを比べる画像です。ケース既定のhierarchical (16 8 4)、plain scotch（10/16までのBasic）、最終BonusのmultiLevel (4 2 4 16)の3つを、同じカメラ・同じ色の決め方で描きました（10/09、ASPIRE-2A）。11/02には、今のBasic（scotchをノードの木に写す`scotchCoeffs`の`domains (2 4 16)`、#63）とmultiLevelの分割を玄界で作り直しました（下の「玄界での作り直し」）。

## 分割の作り方と、計測runと同じ分割であること

| 項目 | 内容 |
|---|---|
| 計算機 | ASPIRE-2Aの共有ノード1台（4コア、240 GB）、直列 |
| Actions / PBS | 37938090398 / 25739475（2026-10-09、約1時間）。一時workflow `.github/workflows/visualize-decomposition.yml`（画像の作成後に削除。commit `f7b157f`で見られる）。1回目（37936651800 / 25739427）は、`set -u`の下で`restore0Dir`を引数なしで呼んで止まったので直した |
| ビルド | 計測runが使ったBasicのビルド（`builds/37888149985`、未改変v2512、GCC 11.2、UCX） |
| 計測runと同じ分割であること | 3つとも、512のサブ領域ごとのセル数と、隣り合うサブ領域の組ごとの共有面の数（hierarchical 5,478組、scotch 5,774組、multiLevel 5,302組）が、計測runの`decomposePar.log`と全部一致した。照合先は、scotchがBasicの4ノードrun（Actions 37202026690）、multiLevelが最終Bonusの4ノードrun（37445116747）、hierarchicalが主催者の4ノードrun（`tasks/4.3-aspire2a-logs/hierarchical-4node/`） |
| 生の出力 | https://mizuha-dev.com/files/openfoam-artifacts/37938090398/aspire2a/decomposition-visualization/decomposition-visualization.tar.zst（107 MB）。3つの`decomposePar.log`、抜き出した面（EnSight、時刻1、2、3がhierarchical、scotch、multiLevel） |

照合した「Basicの4ノードrun」（37202026690）は、#63でノードの木を入れる前のもので、分割はplain scotchです。

## 玄界での作り直し（11/02）

ユーザーが、`domains`を入れた今のBasicの分割をmultiLevelと同じ画角・色で比べたいと言ったので（11/02）、ASPIRE-2Aに入れなかったこの日、玄界で同じ設定の分割を作りました。

| 項目 | 内容 |
|---|---|
| 計算機 | 玄界の1ノード（a-batch）。2つの`decomposePar`を並べて流した（PJM 7236147、11/02 18:18〜18:33、15分）。SSHから`pjsub`で投入（ユーザー：玄界で動かしてscpすればよい） |
| ビルド | 玄界のrunが使う未改変v2512（`/home/pj26000080/share/openfoam-build/builds/35722802934.tar.zst`、Intel oneAPI 2025.1、`linux64IcxDPInt32Opt`、Scotch 6.1.0） |
| 分割 | 今のBasic：`scotch`に、`run/prepare.pbs`が足す`scotchCoeffs`（`domains (2 4 16)`、`domainWeights`、`strategy`）。最終Bonus：`multiLevel`に`multiLevelCoeffs`（`method scotch; domains (4 2 4 16);`）。どちらもケースの`decomposeParDict`（#63で`scotchCoeffs`が入る前のもの）に足した |
| 計測runと同じ分割であること | 2つとも、512のサブ領域ごとのセル数と、隣り合う組ごとの共有面の数が、ASPIRE-2Aの計測runの`decomposePar.log`と全部一致した。Basicは2,941組、サブ領域の間の面3,022,295枚、最大のサブ領域は平均の+1.00%（Boxの提出物`openfoam/results/4node/decomposePar.log`）。multiLevelは2,651組、2,811,816枚、+1.86%（`openfoam/bonus/results/4node/decomposePar.log`）。コンパイラがGCCからIntelに変わっても、Scotch 6.1.0は同じ分割を出した |
| 生の出力 | `~/apac26/decomposition-genkai-20261102/decomposition-visualization-genkai.tar.zst`（107 MB、SHA-256 `d6005fa6c35db0064b197276415831370747a3b56b78cd54cade2e9af8fa83a6`）。抜き出した面（EnSight、時刻1がBasic、2がmultiLevel）、2つの`decomposePar.log`と使った`decomposeParDict`、ジョブのログ。玄界の作業ディレクトリは消した |

経緯：

- 1回目（PJM 7236100）は、計算ノードのOSの`libstdc++`にGCC 13の`GLIBCXX_3.4.32`がなく、`decomposePar`が起動しなかった。玄界のCIを動かすアカウントは自分で入れたGCCを使っているので、このアカウントでは、Intel oneAPI 2025.1.3のAdvisorに入っている`libstdc++.so.6.0.32`を作業ディレクトリに`libstdc++.so.6`として置いて使った（Advisorの`libstdc++.so.6`は小さな中継のライブラリで、`std::cerr`がなく使えない）。
- 2時間と1時間で要求すると開始の見込みが翌日の13:00になり、30分で要求するとすぐに始まった（流れの可視化のときと同じ）。
- 玄界にはParaViewがなかった（モジュール、`/home/app`、プロジェクトの共有フォルダを探した）。ユーザーの案（玄界にParaViewを入れて描き、scpで持ってくる。コンパイラは動くモジュールでよい）で、OpenFOAMのThirdParty v2512に入っているParaView 6.0.1のソースをビルドした（`paraview-genkai.pjm`、PJM 7236528、19分）。GCC 12（`gcc-toolset/12`）、OSのPython 3.11（numpyあり）、QtとMPIなし、XとEGLを切って、VTKが実行時にOSMesa（`llvm/7.1.0`の後に`mesa/20.3.5`モジュール、llvmpipe）を読み込む。入れた先は`/fast/pj26000080/paraview/6.0.1-osmesa`（600 MB、グループで読める。ビルドの作業ディレクトリは消した）。
- 描画は`render-genkai.pjm`（PJM 7236585、1分ほど）。Mesa 20.3.5のllvmpipeはテクスチャバッファの上限が65,536なので、セルの色付けで「上限を超えた」という警告が出るが、絵には影響しない。描き直したmultiLevelの6枚は、10/09の絵（ParaView 5.13.3）とバイト単位で同じだった。だから、Basic（ノードの木）の6枚も、10/09の絵と同じ画角と色で比べられる。

## ファイル

| ファイル | 中身 |
|---|---|
| `decomposition.pbs` | ASPIRE-2Aの共有ノード1台（4コア）の直列ジョブ。計測runのBasicのビルドの`decomposePar -cellDist`で3通りに分け、各セルのサブ領域番号（cellDist）を時刻1、2、3に置き、`simpleFoam -postProcess`を1回流して抜き出す |
| `decomposition-genkai.pjm` | 玄界の1ノードのジョブ（11/02）。今のBasicとmultiLevelの2通りを並べて分け、cellDistを時刻1、2に置いて抜き出す。作業ディレクトリに展開したビルド、ケース、`decomposeParDict`、`decompositionSurfaces`、`prepare.pbs`（`strategy`を読む）を置いてから投入する |
| `paraview-genkai.pjm` | 玄界でParaView 6.0.1を、画面なし（OSMesa）・Python付きでビルドして入れるジョブ |
| `render-genkai.pjm` | 玄界で、入れたParaViewの`pvbatch`で`render.py`を流すジョブ |
| `decompositionSurfaces` | 抜き出すfunction object。車体表面、中心断面（y = 0）、車軸の高さの水平断面（z = 0）、ホイールベース中央の横断面（x = 1.4 m）。各セルの値のまま（補間しない）なので、サブ領域の境目がはっきり出る |
| `render.py` | ParaView（pvbatch）で手法・視点・色分けごとの画像を描く |
| `compose.py` | 画像を並べ、各`decomposePar.log`の数値と色の凡例を付ける |

## 作り方

1. 出力`decomposition-visualization.tar.zst`を取得して展開する（上の表のURL）。玄界の作り直しは`decomposition-visualization-genkai.tar.zst`（上の表）。
2. `env -u DISPLAY -u WAYLAND_DISPLAY LD_LIBRARY_PATH=<ParaView>/lib/mesa GALLIUM_DRIVER=llvmpipe <ParaView>/bin/pvbatch-real --no-mpi presentation/openfoam/decomposition/render.py <展開した出力> <出力先>`（ParaViewは`../flow/README.md`と同じ5.13.3のヘッドレス版）。玄界の作り直しでは、最後に`scotchDomains multiLevel`を足す（時刻1、2の分割の名前）。
3. `uv run presentation/openfoam/decomposition/compose.py <出力先>`。玄界の作り直しからは、`decomposition-<色分け>-scotch-domains-vs-multilevel.png`ができる。

## 画像（Boxの`presentation/openfoam/decomposition/`）

| ファイル | 内容 |
|---|---|
| `decomposition-subdomains.png` | 3つの分割（列）を、車体表面、中心断面（横から）、ホイールベース中央の横断面（後ろから前を見る）の3段で、サブ領域ごとの色で描いたもの（3840×2220）。見出しに`decomposePar.log`の数値 |
| `decomposition-numa.png` | 同じ並びを、ノードとNUMA領域の色で |
| `decomposition-subdomains-baseline-vs-basic.png`、`decomposition-numa-baseline-vs-basic.png` | ケース既定のhierarchical（baseline）とBasic（scotch）の2列だけ（3840×3330） |
| `decomposition-subdomains-basic-vs-bonus.png`、`decomposition-numa-basic-vs-bonus.png` | Basic（scotch）と最終Bonus（multiLevel）の2列だけ（3840×3330） |
| `decomposition-subdomains-scotch-domains-vs-multilevel.png`、`decomposition-numa-scotch-domains-vs-multilevel.png` | 今のBasic（scotchをノードの木に写したもの、`domains (2 4 16)`）と最終Bonus（multiLevel）の2列（3840×3330、11/02、玄界） |
| `panels/<手法>-<視点>-<色分け>.png` | 1枚ずつの画像（車体は1920×1080、断面は1920×840）。スライドに1枚ずつ貼る用。今のBasicは`scotchDomains-…` |

色の決め方：

- サブ領域ごと（`subdomains`）：512のサブ領域それぞれに別の色。番号に黄金比を掛けた小数部で色を決めるので、番号の近いサブ領域（隣り合うことが多い）どうしは離れた色になります。
- ノードとNUMA（`numa`）：rank rはノードr // 128、NUMA領域(r // 16) % 8で動きます（runの配置どおり）。ノードを色相（青、橙、緑、紫）、ノード内の8つのNUMA領域を濃淡で分けます。

読み方：

- hierarchical (16 8 4)は、x方向に16、y方向に8、z方向に4つ、セル数が等しくなるように平らに切ります。車の近くはセルが細かいので、薄い板のようなサブ領域になり、隣と接する面が増えます（サブ領域間の面が431万で、scotchより47 %多い）。セル数はほぼ完全に均等です（最大でも平均より0.002 %多いだけ）。ノードは高さ方向の4つの層になり、下からノード1〜4です。
- plain scotchは、サブ領域間の面が少なくなるように、まとまった塊に分けます（293万面）。セル数の偏りは最大1.07 %です。今のBasic（ノードの木）は、全体の面が3.3 %多い302万ですが、ノード、ソケット、NUMA領域をまたぐ面を10〜23 %減らします（`../slides.md`の8枚目、絵は`decomposition-numa-scotch-domains-vs-multilevel.png`）。
- multiLevel (4 2 4 16)は、ノード、ソケット、NUMA領域、コアの順に、各段をscotchで分けます。ノードとNUMA領域ごとに連続した塊になり、サブ領域間の面はscotchより3.9 %少ない281万です。代わりにセル数の偏りは最大1.86 %です。
- 画像はセルの並びだけを示します。どの分割が速いかは、同じ時期に交互に流した計測で比べています（`../slides.md`の6枚目と10枚目、`submission/openfoam/bonus/README.md`）。
