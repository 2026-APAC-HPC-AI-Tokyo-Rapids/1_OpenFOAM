# 分割の可視化（#39）

4ノードrunの512分割が、メッシュのどこをどう切っているかを比べる画像です。ケース既定のhierarchical (16 8 4)、Basicのscotch、最終BonusのmultiLevel (4 2 4 16)の3つを、同じカメラ・同じ色の決め方で描きました。

## 分割の作り方と、計測runと同じ分割であること

| 項目 | 内容 |
|---|---|
| 計算機 | ASPIRE-2Aの共有ノード1台（4コア、240 GB）、直列 |
| Actions / PBS | 37938090398 / 25739475（2026-10-09、約1時間）。一時workflow `.github/workflows/visualize-decomposition.yml`（画像の作成後に削除。commit `f7b157f`で見られる）。1回目（37936651800 / 25739427）は、`set -u`の下で`restore0Dir`を引数なしで呼んで止まったので直した |
| ビルド | 計測runが使ったBasicのビルド（`builds/37888149985`、未改変v2512、GCC 11.2、UCX） |
| 計測runと同じ分割であること | 3つとも、512のサブ領域ごとのセル数と、隣り合うサブ領域の組ごとの共有面の数（hierarchical 5,478組、scotch 5,774組、multiLevel 5,302組）が、計測runの`decomposePar.log`と全部一致した。照合先は、scotchがBasicの4ノードrun（Actions 37202026690）、multiLevelが最終Bonusの4ノードrun（37445116747）、hierarchicalが主催者の4ノードrun（`tasks/4.3-aspire2a-logs/hierarchical-4node/`） |
| 生の出力 | https://mizuha-dev.com/files/openfoam-artifacts/37938090398/aspire2a/decomposition-visualization/decomposition-visualization.tar.zst（107 MB）。3つの`decomposePar.log`、抜き出した面（EnSight、時刻1、2、3がhierarchical、scotch、multiLevel） |

## ファイル

| ファイル | 中身 |
|---|---|
| `decomposition.pbs` | ASPIRE-2Aの共有ノード1台（4コア）の直列ジョブ。計測runのBasicのビルドの`decomposePar -cellDist`で3通りに分け、各セルのサブ領域番号（cellDist）を時刻1、2、3に置き、`simpleFoam -postProcess`を1回流して抜き出す |
| `decompositionSurfaces` | 抜き出すfunction object。車体表面、中心断面（y = 0）、車軸の高さの水平断面（z = 0）、ホイールベース中央の横断面（x = 1.4 m）。各セルの値のまま（補間しない）なので、サブ領域の境目がはっきり出る |
| `render.py` | ParaView（pvbatch）で手法・視点・色分けごとの画像を描く |
| `compose.py` | 画像を並べ、各`decomposePar.log`の数値と色の凡例を付ける |

## 作り方

1. 出力`decomposition-visualization.tar.zst`を取得して展開する（上の表のURL）。
2. `env -u DISPLAY -u WAYLAND_DISPLAY LD_LIBRARY_PATH=<ParaView>/lib/mesa GALLIUM_DRIVER=llvmpipe <ParaView>/bin/pvbatch-real --no-mpi presentation/openfoam/decomposition/render.py <展開した出力> <出力先>`（ParaViewは`../flow/README.md`と同じ5.13.3のヘッドレス版）。
3. `uv run presentation/openfoam/decomposition/compose.py <出力先>`。

## 画像（Boxの`presentation/openfoam/decomposition/`）

| ファイル | 内容 |
|---|---|
| `decomposition-subdomains.png` | 3つの分割（列）を、車体表面、中心断面（横から）、ホイールベース中央の横断面（後ろから前を見る）の3段で、サブ領域ごとの色で描いたもの（3840×2220）。見出しに`decomposePar.log`の数値 |
| `decomposition-numa.png` | 同じ並びを、ノードとNUMA領域の色で |
| `decomposition-subdomains-baseline-vs-basic.png`、`decomposition-numa-baseline-vs-basic.png` | ケース既定のhierarchical（baseline）とBasic（scotch）の2列だけ（3840×3330） |
| `decomposition-subdomains-basic-vs-bonus.png`、`decomposition-numa-basic-vs-bonus.png` | Basic（scotch）と最終Bonus（multiLevel）の2列だけ（3840×3330） |
| `panels/<手法>-<視点>-<色分け>.png` | 1枚ずつの画像（車体は1920×1080、断面は1920×840）。スライドに1枚ずつ貼る用 |

色の決め方：

- サブ領域ごと（`subdomains`）：512のサブ領域それぞれに別の色。番号に黄金比を掛けた小数部で色を決めるので、番号の近いサブ領域（隣り合うことが多い）どうしは離れた色になります。
- ノードとNUMA（`numa`）：rank rはノードr // 128、NUMA領域(r // 16) % 8で動きます（runの配置どおり）。ノードを色相（青、橙、緑、紫）、ノード内の8つのNUMA領域を濃淡で分けます。

読み方：

- hierarchical (16 8 4)は、x方向に16、y方向に8、z方向に4つ、セル数が等しくなるように平らに切ります。車の近くはセルが細かいので、薄い板のようなサブ領域になり、隣と接する面が増えます（サブ領域間の面が431万で、scotchより47 %多い）。セル数はほぼ完全に均等です（最大でも平均より0.002 %多いだけ）。ノードは高さ方向の4つの層になり、下からノード1〜4です。
- scotchは、サブ領域間の面が少なくなるように、まとまった塊に分けます（293万面）。セル数の偏りは最大1.07 %です。
- multiLevel (4 2 4 16)は、ノード、ソケット、NUMA領域、コアの順に、各段をscotchで分けます。ノードとNUMA領域ごとに連続した塊になり、サブ領域間の面はscotchより3.9 %少ない281万です。代わりにセル数の偏りは最大1.86 %です。
- 画像はセルの並びだけを示します。どの分割が速いかは、同じ時期に交互に流した計測で比べています（`../slides.md`の9枚目と11枚目、`submission/openfoam/bonus/README.md`）。
