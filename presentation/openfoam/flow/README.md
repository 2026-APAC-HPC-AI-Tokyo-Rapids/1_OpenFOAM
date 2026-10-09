# 流れの可視化（#39）

発表で、計算している流れそのものを見せるための動画と画像です。計測runは場を書き出さない（`controlDict.noWrite`の`writeInterval 100000`）ので、同じ公式ケースに出力用のfunction objectだけを足した可視化用のrunを1本流し、その出力をParaViewで描きました。メッシュの分割の可視化はチームメイトが別に進めています（#39）。

## 可視化用のrun

| 項目 | 内容 |
|---|---|
| 計算機 | 玄界、4ノード×112 rank（448 rank、scotch）、150反復。ASPIRE-2Aの4ノードが空かなかったため（下の「経緯」） |
| Actions | 37907133282（一時workflow `.github/workflows/visualize-flow-genkai.yml`、commit `ce7481a`。動画の作成後に削除） |
| PJM | 7039532（2026-10-09 17:48〜17:58 JST） |
| ビルド | mainの玄界runが再利用している未改変v2512（Actions 35722802934のビルド、Intel oneAPI 2025.1、Intel MPI、`linux64IcxDPInt32Opt`） |
| ケース | 玄界のケースキャッシュの448分割（`4e2fa5a5…`、2026-09-07作成）。ケースのファイルは今の`benchmark/occDrivAerStaticMesh`と同じ（case_identity `e3db1aba…`） |
| 同じ計算であること | 150反復目のCdは0.28455000886604298で、2026-09-07の玄界の公式手順の4ノードrun（Actions 34052897447、`research/2026-09-07-official-e2e.md`）と全桁一致した。出力を足しても計算は変わっていない。ASPIRE-2AのBasic（512 rank、GCC＋AOCL-LibM）の0.28404934573921931とは、分割とビルドが違うので+0.18 %違う |
| 1 stepの時間 | 1.97 s（出力の書き出しを含む。比較には使わない） |
| 生の出力 | https://mizuha-dev.com/files/openfoam-artifacts/37907133282/genkai/flow-visualization/flow-visualization.tar.zst（573 MB、展開すると838 MB）。ログ、使った`controlDict`、`postProcessing/`の全部 |

- 足したのは`flowVisualization`のfunction objectだけです。ケース、メッシュ、`fvSchemes`、`fvSolution.fixedIter`、Allrunの各工程とスイッチは公式のままです。
- 計測runではありません。出力の書き出しが計測区間に入るので、時間は比較に使いません。

## ファイル

| ファイル | 中身 |
|---|---|
| `flowVisualization` | 可視化用のfunction object。`controlDict.noWrite`の`functions`の最後に`#include`する。中心断面（y = 0）と車軸の高さの水平断面（z = 0）を5反復ごとに、車体表面の圧力係数（cp）と壁面せん断応力、全圧係数0の等値面、車の0.7 m前からの流線240本を150反復目に書き出す |
| `visualize-genkai.pjm` | 玄界で可視化用runを流すジョブ（4ノード448 rank、scotch、150反復、玄界のケースキャッシュの分割済みケースから） |
| `render.py` | ParaView（pvbatch）で動画のコマと静止画を描く |
| `make-videos.sh` | `render.py`を動かし、コマをMP4にする |

ASPIRE-2Aでは、提出用の`submission/openfoam/run/submit.sh 4 basic`に同じfunction objectを足して流す一時workflowも用意しましたが、4ノードが空かず、玄界のrunを使いました（下の「経緯」）。

## 作り方

1. 可視化用runの出力`flow-visualization.tar.zst`を取得して展開する（上の表のURL）。
2. ParaView 5.13.3のヘッドレス版（`ParaView-5.13.3-osmesa-MPI-Linux-Python3.10-x86_64.tar.gz`、paraview.org）を展開する。
3. `presentation/openfoam/flow/make-videos.sh <ParaViewのディレクトリ> <展開した出力> <出力先> "<計算機>"`を実行する。`<計算機>`はフッターに出す文字列（例：`Genkai, 4 nodes / 448 ranks`）。ノートPC（4コア、WSL2）で31分かかった（流線の動画の420コマがほとんどで、1コマ約3.6秒）。

ParaViewに同梱の既定の`lib/libOSMesa.so`はWSL2で`glewInit`の中で落ちたので、`make-videos.sh`は同梱のもう一つのMesa（`lib/mesa/`、llvmpipe）を使います。MP4はimageio-ffmpegに入っているffmpegで作ります（H.264、1920×1080、30 fps）。

## 動画と画像（Boxの`presentation/openfoam/flow/`）

| ファイル | 内容 |
|---|---|
| `flow-iterations.mp4` | 中心断面（横から）と車軸の高さの水平断面（上から）の流速の大きさ。5反復ごとに保存した30枚を、反復5から150まで順に見せる。左上に反復数と、その反復の`coefficient.dat`のCd |
| `flow-streamlines.mp4` | 150反復目の車体表面の圧力係数（Cp）と流線。流線に沿って、局所の流速で動く短い線を描き、カメラは車の左前から左後ろへ回る |
| `stills/planes-iteration-150.png` | `flow-iterations.mp4`の最後の画面（3840×2160） |
| `stills/streamlines-iteration-150.png` | 流線と車体のCp（3840×2160） |
| `stills/car-cp-iteration-150.png` | 車体表面のCpだけ（3840×2160） |
| `stills/wake-total-pressure-iteration-150.png` | 全圧係数0の等値面（境界層と後流、エネルギーを失った流れ）を流速で色付け（3840×2160） |

見るときの注意：

- simpleFoamは定常計算で、反復は時間ではありません。`flow-iterations.mp4`は、150反復の間に解がどう変わるかを示すもので、流れが時間とともに動く様子ではありません。150反復ではまだ収束の途中で、Cdも変わり続けています。
- `flow-streamlines.mp4`の動く線は演出です。150反復目の速度場の流線に沿って、その場所の流速で進むように描き、実時間の10分の1の速さで見せています。定常な速度場なので、流線は粒子の通り道と一致します。
- 色の範囲は固定です。流速0〜50 m/s（主流は38.9 m/s）、Cp −1〜1。範囲の外は端の色になります。

## 経緯

- 2026-10-09、ASPIRE-2Aで、提出用の`run/submit.sh 4 basic`に同じfunction objectを足す一時workflow（`visualize-flow.yml`、Actions 37897837720）を流した。ケースの準備（PBS 25736821）は終わったが、4ノードのsolve（PBS 25736822）が`node_pool`の不足で3時間近く待ったので、玄界に切り替え、取り消した。
- 玄界の1回目（Actions 37906282581）は1時間を要求して開始予定が翌0時だったので取り消し、30分に縮めた（実際は約10分で終わる）。2回目（37906771178）は、投入したディレクトリが計算ノードから見えず（`NO CURRENT DIR`）すぐに終わったので、作業ディレクトリから投入するよう直した。3回目（37907133282）が完走した。
- 取り消し・失敗したrunのログも、保管庫の`openfoam-artifacts/<Actions run>/`に残っている。
- 一時workflowは動画を作った後に削除した。玄界の`visualize-flow-genkai.yml`はcommit `ce7481a`、ASPIRE-2Aの`visualize-flow.yml`はcommit `9ee6d51`で見られる。
