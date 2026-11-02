# renumberMeshのほかの並べ方（玄界、11/03）

私たちの測ったrunは、どれもAllrunの`renumberMesh -constant -overwrite -parallel`を既定のCuthill–McKeeのまま流しています（Basicは補遺F1でそう決まっていて、`-dict`などはBonusの作業）。「ほかの並べ方なら速くなったのでは」という問い（想定問答のQ39）に、測った数字で答えるために、v2512で選べるほかの並べ方を、課題のケースそのもので比べました。ASPIRE-2Aに入れなかったので（VPN）、ユーザーの許可を得て玄界で流しました（11/03：玄界でテストしてみるのはやってもいい）。玄界の結果なので、ASPIRE-2Aでの速さそのものではなく、傾向を見るためのものです。

## 条件

| | |
|---|---|
| 計算機 | 玄界のノードグループA（Xeon Platinum 8490H × 2、1ノード120コア、コアあたりL2 2 MB、L3はソケットで112.5 MB）。4ノード、ノードあたり112 rank、448 rank。玄界のBasicのrunと同じ配置（`I_MPI_PIN_PROCESSOR_LIST`で15コアに1つ空ける） |
| ビルド | 玄界のrunが使う未改変のv2512（Actions 35722802934、Intel oneAPI 2025.1、Intel MPI、Scotch 6.1.0） |
| ケース | 公式のocc DrivAer 65M。`controlDict.noWrite`、`fvSolution.fixedIter`、分割はplain scotchで448分割（リポジトリの`decomposeParDict`のASPIRE-2A向けの`scotchCoeffs`は外した）。40反復、`startFrom startTime` |
| 並べ方 | `CuthillMcKee`（既定、Allrunのとおり`-dict`なし）、`RCM`（Cuthill–McKeeの逆順）、`none`（並べ替えなし、decomposeParの順＝元のメッシュの順）、`spring`（`springRenumber.H`の例の係数）、`random`（乱数の順、局所性の最も悪い例として）。`-dict`で読む`renumberMeshDict-*`はこのフォルダ |
| 手順 | 並べ方ごとに分割済みのケースを写し、Allrunのとおり`restore0Dir -processor`、`renumberMesh`、`potentialFoam`、`applyBoundaryLayer`を流す。その後、1巡で5つの並べ方を1回ずつ、巡ごとに順番をずらして流す。1つの巡は同じジョブ（同じ4ノード）の中で流す |
| 指標 | ケースの`wallClockTimeStatistics`が出す、2〜40 step目の1 stepの平均時間（公式の指標と同じ）。Cdは40 step目の値 |

## 結果

既定より速い並べ方はありませんでした。4巡とも、各巡の中で既定と比べた変化です（`../data/renumber_genkai.csv`、`analyse.py`の出力）。

| 並べ方 | 1 stepの時間 | 既定に対して | 巡ごと | band | profile/セル | Cd（40反復目） |
|---|---:|---:|---|---:|---:|---:|
| CuthillMcKee（既定） | 1.958 s/step（SD 0.45%） | | | 11,347 | 2,705 | 0.43768 |
| RCM | 1.954 | −0.19% | −0.38、−0.49、−0.21、+0.31% | 11,347 | 2,562 | −1.32% |
| none | 1.972 | +0.70% | +0.73、+0.76、+0.95、+0.37% | 146,078 | 3,880 | −1.21% |
| spring | 2.022 | +3.26% | +3.55、+2.44、+3.72、+3.33% | 68,712 | 3,025 | −0.65% |
| random | 2.166 | +10.6% | +10.9、+9.5、+10.8、+11.3% | 147,291 | 54,368 | +0.09% |

- 乱数の順が11%遅いので、並べ方は効きます。そのうえで既定のCuthill–McKeeは、v2512で選べる並べ方の中で最も速いか、RCMと区別がつきません。RCMは3巡で速く1巡で遅く、私たちの採用の決まり（全候補が全対照より速い）を通りません。
- Cdは、どの並べ方でも4巡とも同じ値で、並べ方の間では違います。固定反復のGauss–Seidelがセルを番号の順に掃くので、並べ方を変えると毎回の近似解が変わるためです。Bonusで並べ方を変えるなら、F3（公式の反復数で、変更前のrunとCdが±0.5%以内）の確認が要ります。
- bandは番号が最も離れた隣どうしの差（448分割の最大）、profileは各セルから番号が最も離れた隣までの差の和で、ここでは1セルあたりにしました。ASPIRE-2AのBasic（512分割、domainsあり）では、既定でbandが14,165、profileが1セルあたり2,536でした。
- 玄界の4ノードで各rankは約14.6万セル、1つの場は約1.2 MBで、コアあたり2 MBのL2に収まります（ASPIRE-2AはL2 0.5 MB、L3がコアあたり4 MB）。だからASPIRE-2Aでの時間そのものではなく、傾向として見ます。
- 時間の測り方：各runはそれぞれの写しのケースで、同じ初期条件（Allrunのとおり作った0）から40反復を流しました。巡は同じジョブ（同じ4ノード）の中で流し、1〜2巡はPJM 7238151、3〜4巡は7238163です。準備（decomposePar）はPJM 7238148、最初の試み7238142は、リポジトリの`decomposeParDict`のASPIRE-2A向けの`scotchCoeffs`（512分割用）のために止まりました。

## ファイル

| ファイル | 中身 |
|---|---|
| `renumber-genkai.pjm` | 玄界のジョブ。`STEP=prepare`（1ノード、メッシュの展開、decomposePar、並べ方ごとの写し）と`STEP=run`（4ノード、並べ替えと、巡ごとのsimpleFoam）。`run`は何度でも投げ直せ、済んだrunは飛ばす |
| `renumberMeshDict-*` | `-dict`で読む並べ方ごとの辞書 |
| `analyse.py` | 結果のフォルダから、runごとの時間、Cd、並べ方ごとのbandとprofileを`../data/renumber_genkai.csv`に書き、まとめを出す |
| `../data/renumber_genkai.csv` | 1行が1回のsimpleFoam |

生の結果（各runの`simpleFoam`のログと`postProcessing`、並べ方ごとの`renumberMesh`、`potentialFoam`、`applyBoundaryLayer`のログ、`decomposePar`のログ、PJMのログ）は、リポジトリの外の`~/apac26/renumber-genkai-20261103/`に置きました（12 MB）。玄界の作業フォルダ（68 GB）は、結果を写した後に消しました。

## 流し方

```bash
ssh genkai mkdir -p /fast/pj26000080/renumber-20261103
```

作業フォルダに、ビルドを`build/`に展開し（`zstd -dc <build>.tar.zst | tar -x -C build`）、`benchmark/occDrivAerStaticMesh`を`case/`に、このフォルダのpjmと辞書を置いてから、次の順に投げます（`renumber-genkai.pjm`の頭のコメントのとおり）。

```bash
pjsub -L rscgrp=a-batch -L node=1 -x STEP=prepare,WORK=<WORK> -o <WORK>/logs/%j.pjm.log -j renumber-genkai.pjm
```

```bash
pjsub -L rscgrp=a-batch -L node=4 --mpi proc=448 -x STEP=run,WORK=<WORK>,ROUNDS=4 -o <WORK>/logs/%j.pjm.log -j renumber-genkai.pjm
```

`results/`をscpで持ってきて、`uv run --no-project python -I analyse.py <results> ../data/renumber_genkai.csv`でまとめます。
