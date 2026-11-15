# OpenFOAM 最適化の経緯と実測結果

調査基準日：2026年10月8日。取得した履歴に基づく調査版。[調査範囲と検証記録](COVERAGE.md)に、独立照合した範囲と限界を示す。

読み方：本ページは結果の入口。[コード変更の追跡](CODE_CHANGES.md)では、変更前後のコード、ファイル・関数、適用条件、削減した処理と実測の対応を説明する。[差分原本](code-diffs/README.md)から固定コミットの実装全文を読める。試行全体は[詳細と不採用理由](EXPERIMENTS.md)、根拠は[出典と検証範囲](SOURCES.md)を参照。数値の原記録は同ディレクトリのCSV・JSONから辿れる。

ASPIRE-2Aでは、CPUとメモリの配置を安定させ、領域分割を調整した後、同じ計算を保ちながら一時配列・コピー・重複した面ループを減らした。採用済みの最終Bonusは、Basicに対し4ノードの平均時間を10.97%短縮した。通信量の削減、コンパイラ変更、分割の均等化は、それだけでは高速化につながらなかった。

## 比較する課題と指標

旧実験はcavity3D-64M、icoFoam、v2606、FVOPS（大きいほど良い）。現行の主要結果はoccDrivAerStaticMesh、65,334,765セル、simpleFoam、v2512、秒/step（小さいほど良い）。物理問題・ソルバー・反復条件ごとに結果をまとめた。玄界、Gadi、ASPIRE-2Aも別系列で扱う。

ASPIRE-2AはAMD EPYC 7713。1/2/4ノードで128/256/512 MPI rank、40/80/150 stepを使う。時間は初回を除いた公式parser結果。step間の標準偏差と、独立run間のばらつきは別物である。40反復スクリーニング、150反復の採点、profiler付き実行をそれぞれ記載する。

時間短縮率は `1 − 候補時間 / 対照時間`、速度比は `対照時間 / 候補時間`。累積効果は最終構成と基準の実測値で算出した。BasicとBonusの分割が異なるため、ソース変更の数値検証は同じ分割のパッチなし基準との比較で行う。[比較・self-proofの記録](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/42)

## 採用構成の到達点

Basicは`6396eeb`（scotch、ソース無変更）、Bonusは`fa4f5b0`（multiLevelと0001〜0004のパッチ）。以下は保存された各runの`result.txt`とCSVの全精度値を照合して再計算した。全20 runが`VALID`。run ID、PBS、Cd、原ログパスは[final-results.csv](final-results.csv)にある。

| ノード | Basic / Bonusのrun数 | Basic平均 秒/step | Bonus平均 秒/step | 時間短縮 | 速度比 | Bonus最小〜最大 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | 3 / 3 | 13.364347 | 11.668460 | 12.69% | 1.1453倍 | 11.665328〜11.670959 |
| 2 | 3 / 3 | 6.366659 | 5.640683 | 11.40% | 1.1287倍 | 5.633468〜5.644714 |
| 4 | 5 / 3 | 2.919579 | 2.599353 | 10.97% | 1.1232倍 | 2.597249〜2.601808 |

この表は確定した提出系列どうしを比較した。各変更の因果効果は下記の対照実験で評価する。比較条件：1/2/4ノードでそれぞれ40/80/150反復。

## 配置と分割でBasicを作る

Cray MPICH初期化中にCPU固定が外れ、初期割当てのページが別NUMAへ置かれる問題があった。起動引数だけでは実際の固定を保証できなかった。最終的に`numactl --membind`と外部からの`taskset`固定を組み合わせ、計算中の128/128 rankの配置を確認した。scotchで2.9191、2.9123、2.9189秒/step。一方、外部固定だけでは3.5488、3.4098、3.4629秒、PALSのメモリ指定と外部固定では3.4498、3.4875秒だった。CPU配置と最初のメモリ配置の両方が必要だった。比較条件：異なる時期の配置診断。[配置の検証](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/36)

固定を揃えた4ノード150 stepの各3runでは、hierarchical `(16 8 4)`平均3.2574秒からscotch平均2.9145秒へ約10.5%短縮。1ノードでは13.5229→13.3459秒（1.3%）、2ノードでは6.5282→6.3679秒（2.5%）だった。rankの計算量の偏りを緩和したことが改善の原因と考えられる。CrayPATの計算時間不均衡は固定hierarchicalの1.160に対し固定scotchで1.055〜1.072。profileの所要時間は通常benchの平均に入れていない。[Basicの最終記録](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/38)

## ソース変更で減らした処理

| 施策 | 変更と期待した機序 | 対照実験の結果 | 判断・根拠 |
| --- | --- | --- | --- |
| multiLevel | node→socket→NUMA→coreの階層に分割を対応。ノード間面337,324→208,092、processor面2,927,022→2,811,816 | パッチなし4ノード平均2.918057→2.873231秒、約1.54%短縮 | 採用。[#37](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/37)、[#42](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/42) |
| 0001 残差の一時配列・コピー削減 | 反復解法内で不要な中間場と読み直しを減らす。収束判定は維持 | 同じmultiLevelで2.873231→2.775911秒、約3.39%短縮 | 採用。1/2/4ノードでパッチなしとの`coefficient.dat`ビット一致。[#37](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/37) |
| 0002 Uの3成分融合 | 同じ係数行列を成分ごとに読み直さず、平滑化・残差計算をまとめる | 同時期4ノード各3run、2.781302→2.717522秒、約2.29%短縮 | 採用。変更範囲とF3は[#44](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/44) |
| 0003 境界交換と対流係数組立 | 捨てる結果の境界交換を省き、係数を一つの面ループで作る | 各3run、2.708041→2.672486秒、約1.31%短縮 | 採用。[#50](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/50) |
| 0004 勾配・積と面積分の融合 | 線形補間した面場や積の一時場を作らず、足し込みループ内で計算。境界処理と加算順を維持 | 各3run、2.674771→2.599353秒、2.82%短縮。候補最遅も対照最速より速い | 採用。初回はヘッダー依存でビルド失敗しテンプレート型へ修正。1/2/4ノードともCdファイル一致。[#51](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/51) |

これらの「読み書きを減らした」という説明は、コード構造だけでなく1ノードのuProf比較でも裏付けられる。パッチなし/あり各2runでは、L1データアクセス−5.8%、DRAMからのL1 demand refill−17.2%、命令数−4.1%、cycles−10.8%。測定条件：1ノード、rank当たりrun全体のイベント数。計装下の時間は13.299→11.666秒だった。[ハードウェアカウンタ比較 #55](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/55)

## 速くならなかった試行と見送った候補

| 試行 | 観測・判断 | 分かったこと |
| --- | --- | --- |
| hierarchicalのrank並べ替え | ノード間面−91.6%でも平均3.2608秒、対照比約+0.1%。不採用 | 通信量以外の計算負荷・待ちが残ったと考えられる。[#36](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/36) |
| scotch tleaf、偏り抑制 | 4ノード−0.64%、抑制付き−0.82%。当時の1%採用閾値未達。1/2ノードでは+0.29%/+0.07% | 4ノードの改善は小さく、1/2ノードは微増した。[#38](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/38) |
| METIS多制約分割 | 面数の偏りは改善したがprocessor面+17.9%。候補2run平均2.821827秒、対照3run2.781303秒、+1.46%遅い | 均等化の利益が境界増加で失われる。[#45](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/45) |
| GAMG masterCoarsestの初期試行 | 40反復3.373321秒、同条件基準比+4.95%。不採用 | 全512 rankの粗系を既定でmaster 0へ集約し、直列粗solveとgather/scatter待ちが増える。後日の段階集約案とは別。[#35](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/35) |
| コンパイラ・フラグ | GCC対照約2.9103秒。znver3約2.9113、AOCC約2.9112、O2約2.9108、LTO約2.9141。優位性なし | 間接アクセスと待ちの寄与が残ったと考えられる。[#36](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/36) |
| OFI＋SRX無効化 | 同時期各3runでUCX2.919704→OFI2.942136秒、+0.77%。Cd同一、SIGBUSなし | SIGBUSは解消し、実行時間は増えた。UCXを維持。[#56](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/56) |
| 小さな配列走査・確保の候補 | #41では局所寄与が小さく一旦見送り。後に#50で複数の小変更をまとめて実測 | #50では複数の小変更をまとめて約1.31%短縮した。[#41](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/41) |

## 旧cavity3Dでの成果と失敗

旧課題では120 rank固定のカナリアから資源全体を使う構成へ進め、最終qualificationのFVOPS中央値は1ノード120 rankで1.7009 M、2ノード240 rankで3.3939 M、4ノード448 rankで7.9900 M（各5run）。4ノードはNUMAごとに1 core空ける112 rank/nodeが、480 rankの不安定な結果より良かった。幾何分割、multiLevel、MPI自動調整、Cuthill–McKee系のリナンバリングは当時の採用基準を超えなかった。[旧実験台帳](../runtime-optimization-experiments.md)

DICをcell gatherへ変更し、PCGの残差更新とL1集計を融合すると、4ノード2run平均8.4573 M FVOPS。基準5run中央値7.9900 M比で性能+5.85%だった。残差走査とメモリへの繰返しアクセスを削る機序で、数値軌跡の一致を確認した。単独候補は各8.1490 M、対称AmulのCSR化は1ノード1.5803 Mで棄却。平均と中央値の比較である点にも注意する。[DIC・PCG統合記録](../dic-pcg-combined-experiment.md)

OptAVX512はFVOPS中央値−0.80%、Sapphire Rapids指定は−1.42%。ZMM highはSIGFPEで結果を生成できなかった。測定対象は旧v2606/icoFoam。低下の原因は未特定。

## ビルドと実験基盤の改善

ccacheの約99.5%ヒットでも依存解決・リンク・ファイル走査が残る。毎回tmpfsへキャッシュをコピーする方式はコピー約82秒に加えビルド中央値24分26秒となり、共有キャッシュ直参照16分26秒より遅かった。事前配置済みtmpfsは16分09秒だったが、17秒差は環境変動より小さい。lldもリンク互換性と安定した短縮を満たさず撤去した。[ビルド試行記録](../build-performance/trial-record.md)

分割済みケース、ビルドアーカイブの再利用は準備コストを省く。第一親履歴を496コミットAPIで遡る方式では選択に13分以上かかり、クラスタ内sidecarの検索へ移行した。これはsolverの秒/stepの改善とは別の、実験一周の短縮である。

## 証拠と調査範囲

[出典索引](SOURCES.md)からIssue・コミット・Actions・自宅サーバーの保存先を辿れる。会話・全refのコミット・Issue・保存結果を施策別に整理した。#30〜#35の診断、SMT・I/O・重み付き分割、旧課題と初期ビルドは[詳細記録](EXPERIMENTS.md)へ追記済み。#57/#58の追加実験は調査時点で未完了。

追加資料：[過去の試行と判断の訂正](EXPERIMENTS.md)、[Actions実ログの照合](actions-log-audit.csv)。
