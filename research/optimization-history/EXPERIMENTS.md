# OpenFOAM 過去の試行と判断の訂正

実装の説明は[コード変更の追跡](CODE_CHANGES.md)、変更前後の原文と完全コミットSHAは[差分原本の索引](code-diffs/README.md)を参照。

[総括](README.md)の補遺。2026年10月8日取得のIssue、会話、保存ログに基づく。時間短縮のなかった試行、測定前に止めた案、後で覆った判断を分ける。

## ASPIRE移行と初期の分割比較

GNU／Cray MPICH UCXで公式1/2/4ノード経路を成立させた。初期OFIは障害を起こし、動作したUCXを標準とした。OFIの実行障害を受けてUCXを採用した。後の#56ではSRXを無効化してOFIを完走させ、各3runの速度比較でUCXを維持している。[ツールチェーン再構築 #30](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/30)

2ノードでscotchからnode-aware multiLevel `(2 128)`へ変更すると、跨ノード面99,591→77,691、隣接関係89→80に減ったが、総面数2,116,218→2,132,699は増えた。初回6.358126秒/stepはscotchの2run平均より0.208%短いだけで、優位性は未確定だった。最初のActions35690097285は未使用の`large_output_dir`チェックでsolver前に失敗し、分割済みキャッシュを保持して35692457935で再実行した。準備段階で失敗し、solver性能は未測定。

4ノードではmultiLevel `(4 128)`4run平均2.884153→NUMA階層 `(4 2 4 16)`3run平均2.866837秒、0.600%短縮。全候補が全対照より速かった。比較条件：割当てホストに差がある。40step CrayPATのP2P送信量は233.495→206.535 GB、NUMA境界面は878,523→778,614に減少したが、通信量の削減が時間短縮に寄与したと考えられる。[分割比較 #32](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/32#issuecomment-5791935134)

## 9月のruntimeスクリーニング

OpenCode `ses_f21f1a3a7ffeK33I9xfIZWTh91`の引き継ぎと[#35](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/35)を照合した。以下は4ノード512rank、40反復の探索結果。

| 変更 | Actions | 秒/step | 比較・判断 |
| --- | --- | ---: | --- |
| hierarchical対照 | 36373671818 | 3.214143072384615 | 同じ探索群の基準 |
| nbx.tuning=1 | 36375558400 | 3.201891518076923 | 約0.38%短縮。1%超の改善を示さず不採用 |
| pbufs.tuning=1 | 36375610008 | 3.250510255538461 | 約1.13%悪化、不採用 |
| unifiedGeometricField=1 | 36380214006 | 3.249373434948718 | 約1.10%悪化、不採用 |
| multiLevel `(4 2 4 16)` | 36377437153 | 2.846726740179488 | 階層比較の別基準 |
| multiLevel `(4 2 8 8)` | 36377508967 | 2.865665523923077 | L3整合を狙ったが約0.67%悪化、不採用 |

`commsType=scheduled`はActions36311011900のpotentialFoamと36313378631のsimpleFoamでGAMGの`scale()`／`Vcycle()`中にSIGFPE。既定nonBlockingへ戻した。速さを測れる正常結果がないので速度劣化率を与えない。

`topoControl=2`のActions36368984582は2.861892秒だったが、実際の分割はmultiLevelだった。hierarchical基準との比較を撤回し、multiLevel150反復3run平均2.866837との約−0.17%という位置付けに訂正された。単runの微差のため採用を見送った。

当時のkahip/metis/ptscotch候補は分解ライブラリの実体がなく、dummy stubだった。kahipは「library not loaded」で停止。分割準備の段階で失敗し、solver性能は未測定。後の#45では別途METISをビルドし、実際の多制約分割を測って不採用としている。各試行に実行状態と測定結果を記載した。

## SMTは計算を遅くし、律速の判別にも使えなかった

4ノード1024rank、1物理coreあたり2rankのActions37293949085は53分で22step。step2〜22の診断中央値16.75秒に対し、同時期512rankの公式値は2.925664秒。比較条件：途中solverログの診断中央値と完走した公式平均。比は約5.7倍だった。長いqueue待ち込みでActions上限に達し、cleanupがPBSを削除した。[SMT #43](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/43#issuecomment-5998972572)

affinityは4ノードとも256/256固定、メモリ使用量は合計250.8 GBで要求1600 GB以下、明示的なMPI/UCXエラーはなかった。processor面は32.6%増えたが、数分停止を含む遅れ全体の説明にはならない。補助スレッド・OS処理がbusy-polling rankを押しのける仮説は未検証。したがってこの結果だけで「帯域律速」か「レイテンシ律速」かは決められず、不採用として追加runを行わなかった。

## I/OとMPI待ちを切り分けて、不要な実験を避けた

I/O診断ではrank0の書込みは約29.3回、7,718 byte/step、他の観測rankは0。観測区間の`write_bytes`と自発的context switchは0で、CPU外の時間は書き込まないrankにも生じた。CPU時間と経過時間の差は割込みと整合し、I/O待ちが主因とは考えにくかった。そのためfileHandlerなどの比較は追加しなかった。測定対象は1ノード。[I/O #46](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/46)

multiLevelの512rankではノード間相手数は平均1.30、共有面の7.4%がノード間。40stepの2つのCrayPAT runで、Waitall時間は自分の計算時間と負に相関（約−0.88）。ノード間相手数を加えても説明力の増加は小さく、遅いrankの多くはノード境界にいなかった。この証拠に基づき、段別分割調整の追加実行を見送った。「MPI待ちが大きい」ことと「ネットワークを速くすれば同じ割合で速くなる」ことは異なる。[通信相手数 #48](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/48)

境界交換と計算のオーバーラップ案も、遅いrankの境界field交換がサンプルの2.43%、一箇所最大0.77%で、そこへ重ねる独立計算がなく、実装を見送った。ただし「結果の境界値を捨てている交換」は発見できた。これを後の#50で他の小変更とまとめ、実測改善につなげた。見送った案から得た知見と、その案自体の採否を分けて記録する。[通信診断 #49](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/49)

## 後で覆った解釈

9月の会話には、2ノード6.51〜6.53秒に対し9.55秒・12.47秒というrunを、host対やラック配置に帰属する強い表現がある。後の183件のVALID benchを対象とした監査では、キャビネット数・シャーシ数では遅さを説明できず、同じhostを後に使って正常な時間で走った。host組の固定的な差という初期仮説は撤回した。[測定変動 #47](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/47)

同じく、scotchの5.03秒という単一runを根拠にした初期の棄却は#36で撤回され、同条件反復後にscotchが最良Basicとなった。反復比較の結果に基づいてscotch採用へ更新した。

## 会話・Git・実行記録の役割

- OpenCode上記セッションは9月の提案、実装、失敗、訂正を含む。M1の固定反復時の残差・ノルム計算省略は**提案**であり、採用済み0001のin-place残差とコピー融合とは異なる。
- Codex `019ff703-1b2d-7191-b4ce-ef1a178894a0`、rollout5137行ではDIC＋PCGを「推奨、main未変更」としていた。後のGitマージと新規ビルド確認により採用へ進んだ。採用時点はGitのマージ履歴で確認した。
- Codex `019f0e96-231c-7812-9d34-b4945c8bdeb1`、3273行はccacheヒット約99.5%のビルドを調査し、Lustreのpage fault・metadata操作、system CPU、短命プロセスの多さを報告する。build時間には共有FSのpage fault・metadata操作と短命プロセス起動が影響したと考えられる。
- OpenCode `ses_0b01c597cffeo6rWTEA4LGAbmi`／`ses_0afe87907ffeZbZp5PXzi6tKza`は2026年7月のprovision・ログstream・artifact命名の整備。`814130f`／`5826471`のGit履歴へ対応する。solver性能の変化は未測定。

## 初期ビルドの並列度とキャッシュ

v2412を中心とした玄界のAllwmake比較は、30/60/90/120並列の中央値が19分46秒／18分21秒／20分17秒／16分26秒。120並列は30並列比で約16.86%短縮した。90並列は60並列より遅かった。共有FSのmetadata待ちを多重化で隠す面がある。160以上は未測定。WM_SCHEDの内部queue制御はwarm cache下で追加の短縮を示さず不採用とした。[ビルド実験](../build-performance/trial-record.md)

パスをOpenFOAM／ThirdPartyに正規化してccacheキーへのversion名混入を防ぎ、計測前に統計をzero resetした。これはヒット率と来歴の比較を正しくする措置である。ヒット率約99.5%でも、同条件runのbuildが14分43秒と23分09秒へ変動した。変動はbuild工程内で発生した。各runの原因を特定するFS counterは未取得。

## 最終Bonusの保存アーカイブによる数値照合

未改変multiLevel版と最終Bonus `fa4f5b0` の同ノード数同士を比較し、保存された`results/coefficient.dat`全体がバイト単位で一致した。1ノードは37207608105対37529406508（13,404 bytes）、2ノードは37207589090対37529430470（25,565 bytes）、4ノードは37209554319対37445116747（46,844 bytes）。照合条件：各pairで同じmultiLevel分割とiteration数。

6個の`run-artifacts.tar.zst`からresult、run manifest、build sidecar、rank placementを直接読んだ。未改変版のbuild definitionは`5abefc1`、最終Bonusは`fa4f5b0`、双方のOpenFOAM upstream sourceは`5a55da3`。各runの128/256/512rankすべてに単一CPU affinityの保存記録がある。保存snapshotで各rankの配置を確認した。[比較結果・アーカイブSHA256・build/source来歴](final-bundle-audit.json)に再照合用の情報を記録した。

## 整数ラベル幅と浮動小数点精度

[#13の9月4日回答記録](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/13#issuecomment-5534033127)では現行65M課題のDP + label32が許可された。整数のmesh addressingにlabel32、浮動小数点に倍精度を使用した。旧cavity課題での保留から現行課題での承認へ判断が変わった履歴として扱う。最終build sidecarもDP/Int32を記録している。label64との同条件A/Bは未確認で、単独の性能効果は未測定。

## 旧cavity課題で棄却した分割・MPI・並べ替え

次の値は玄界のcavity3D/v2606/icoFoam、M FVOPSである。[旧実験台帳](../runtime-optimization-experiments.md)にrun ID・条件の詳細が残る。

| 候補 | 観測と比較 | 判断・説明 |
|---|---|---|
| 480rank hierarchical／multiLevel | 初回7.8745／7.9404。solverはVALIDだが旧metrics schemaがScotch専用で分割詳細を拒否 | 分割詳細の収集schemaが原因。schema v2へ修正して再測定 |
| 448rankノード・NUMA対応multiLevel | 2run中央値8.0706対Scotch3run中央値8.0025、+0.85%。総境界面−28.9%、ノード間面−54.6% | 事前の1%採用基準未満で不採用。通信面数削減が同率の実時間改善にはならなかった。事前に定めた採用閾値は性能改善1% |
| Intel MPI autotuning | 適用31647180395は8.0251、対照31647182300は7.9652、+0.75%。solver全体51.576対51.563秒 | FVOPSの採点区間では微増だがsolver全体は短縮せず、不採用。探索負荷を含むrunは7.9061 |
| 通常Cuthill–McKee | 31649038444は8.0630、対照31649040528は7.9900、+0.91% | ランク内局所性改善を狙ったが1%基準未満 |
| blockSize32768の局所Cuthill–McKee | 31649727744は8.0655、対照31649729689は7.9900、+0.94% | 通常版を大きく超えず不採用。通常版との差は小さかった |

## 玄界・Gadiでのメモリ診断と、測れなかったもの

旧cavityの玄界VTuneではノードDRAM平均約399GB/s、観測最大約495GB/s、高利用率時間91%以上。DIC/Amul/PCGのメモリ走査削減を優先する根拠になった。現行occDrivAerに移った後の玄界4ノード448rankでは、32559806220／32560022792がDRAM平均422.944／426.630GB/s、高利用率時間99.7／100.0%。問題が変わってもこの環境ではメモリ側の負荷が強いという診断だった。

Gadiの現行課題4ノード416rankはVTune sampling driverがなく、標準memory-accessおよび帯域収集付きhpc-performanceがexit1となった。solverのVALIDとは別の収集失敗である。driverless/PEBSへ切り替えた32594112966／32594130332ではMemory Bound48.6／63.1%、packed FP約17%を観測したが、ノードDRAM帯域自体は得られていない。計装runの時間は2.18463／2.16387秒/反復。GadiのノードDRAM帯域は未測定。

観測対象rankではremoteメモリアクセスがほぼなく、TLB walkも小さかったため、Huge PageやNUMA再配置を優先候補とする根拠は弱かった。測定対象は玄界・Gadiの観測rank。ASPIREでは後にMPI_InitによるCPU pin解除を確認した。

## 公式課題以前：motorBikeのランク数とMPI調整

玄界のOpenFOAM v2606/simpleFoam、356,630セル、endTime3000のmotorBikeでの結果。小規模な動作確認ケースとして測定した。[当時の全試行表](../runtime-performance/README.md)とCodex会話`019f8e6f-c27d-72e2-a2bb-29732fca7765`（2313・3087行）を照合した。

| 変更 | 結果 | なぜ効いたか／採否 |
|---|---|---|
| 2ノード240→120rank | solver ClockTime105→56秒、46.67%短縮。最終Actions30008427515も56秒、MPI起動込み63.31秒 | 240rankでは約1,486セル/rankと小さく、計算より通信・起動負荷が重かった。APSでMPI平均151.27→51.80秒、Allreduce56.04→18.42秒という診断も得た。APSの値は計装runで測定 |
| さらに60/90rankへ削減 | solver76/68秒へ悪化 | 並列度不足。rank削減による計算並列度の低下が原因と考えられる |
| 135/150/165/180rank | solver54/55/53/57秒、MPI込み64.88/65.31/68.10/71.72秒 | 一部はsolver単体で速いが起動全体では120rankに負け、不採用 |
| 1ノード120rank、全MPI工程へ`I_MPI_FABRICS=shm` | 基準#141→最終#152（30012289152）：solver111→101秒（9.01%短縮）、MPI込み120.81→104.06秒（13.86%）、Actionsログ追跡区間201→165秒（17.91%） | 既定が単一ノードでもmlx providerを選んだため、共有メモリだけに限定して初期化負荷を減らした。solver・MPI起動込み・Actions追跡区間をそれぞれ測定 |
| pin core/scatter/compact | 1ノードで105/106秒、実CPU一覧は既定と同じ | 配置変更が実効的に起きず、採用根拠なし |
| Allreduce全サイズ固定 | recursive doublingは25分でTime943まで、未完走。Knomial112秒、SHM Knomial106秒 | メッセージサイズを無視した一律指定では改善せず。shm単独を採用 |
| `topoControl=16`／`nPollProcInterfaces=-1` | 2ノード240rankで107／114秒。基準105秒に対し悪化 | 階層縮約・即時pollを追加しても当該ケースでは有益でなかった |
| MPI autotune | 240rankでは105→103秒、120rankでは56→58秒 | ランク構成依存で、選択後の120rankでは不採用 |

`perf stat`の有無を各2回比較した別会話`019f9251-a27d-73f3-a9c6-16d356c8e04b`（1112行）ではClockTimeが無効107/107秒、有効105/109秒で平均はいずれも107秒。CPU ExecutionTime平均は63.43対61.69秒だったが、壁時計の改善を示さない。計測を外すことによる確実な高速化は確認できず、当時は有効のままとした。

## 現行65M課題へ移行した後の玄界参考測定

9月7日の玄界v2512/DP/Int32/scotch比較では、4ノード448rankが各2run平均1.981699015秒/step、480rankは2.119487170秒/stepで、480rankは6.95%遅かった。現行課題でも448rankの方が速かった。候補`32ae88c`は採用せず、`archive/genkai-4n-480r-20260907`タグへ保存した。比較条件：hardware収集修正前の4runで、割当環境の一致は未確認。低下の原因は未特定。[全結果・Actionsリンク](../2026-09-07-official-e2e.md)。

同一構成commit`e944313`の1/2/4ノードは8.159013426／4.129346025／1.985350880秒/step。各40/80/150反復、rank数120/240/448で、全件VALID。玄界の参考値として、node数ごとのstep平均を記録した。

準備時間については`b9960e5`で既存case cache hit時の不要なPJM準備jobを省略した。一方、Python3.6の誤選択によるhardware収集失敗と接続設定の旧形式によるprofile転送失敗はそれぞれ`c62a364`／`c1017ca`で修正し、残っていたrawは計算を再投入せず回収した。solverの成功、観測の欠落、成果物転送の失敗を別々に記録する必要がある。

## ビルド選択・キャッシュの管理コスト

初期の成果物選択は第一親履歴を1commitずつ遡ってActions APIへ問い合わせ、約496commitの探索に13分以上を要した。クラスタ内sidecarをrun ID降順に調べ、build inputs・サイズ・SHA256一致で再利用する方式へ移行した。API問合せの削減で選択工程を短くする狙いだった。新方式の同条件反復時間は未測定。[ビルド試行記録](../build-performance/trial-record.md)。

バージョン名入りの相対ソースパスがccache keyを分離していたため、展開先を`OpenFOAM`／`ThirdParty`へ正規化し、Allwmake直前のzero-statsで当該buildの統計に限定した。同じソースのcache再利用を可能にし、buildごとのhit率を測定した。hit率99.50%の2runで、build時間は14分43秒（28992544864）と23分09秒（29015734524）だった。共有I/O競合などが原因候補となるが、runごとの原因は未特定。

## ASPIRE初期の448rank/L3配置と、未実行SMT試行

[#35の比較](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/35#issuecomment-5852175549)では同じhierarchical `(7 8 8)`・448rankで、7rank/L3を16組へ分散する36286767867が3.443525344秒、8rank/L3を14組に詰める36289009710が3.950424491秒だった。単pairの時間差は12.83%短縮。しかし512rank hierarchical基準約3.244826秒より両方とも遅く、448rankは不採用となった。

当時はL3利用範囲による説明を採ったが、この記録は後の#36でMPI_Init後のCPU affinity解除を特定する前のもの。solver中の配置は未確認だったため、12.83%差の原因は保留とした。後の固定修正・反復比較ではscotchをBasicに採用した。

最初のSMT1024rank試行36291497979はcase準備まで成功したが、PBSのnode_pool不足で実行開始せず、Actionsの6時間上限で終了した。性能値もCdもない。[未実行の記録](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/35#issuecomment-5854835193)。後の#43で実際に22step進んだ遅いSMT試行とは別である。

## 境界セル・点数で重みを付ける分割

#37では境界面の処理負荷を見積もって分割を均す方法も試した。[境界セル2:1](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/37)はscotch3run平均3.1067秒、無重みBasic6run平均2.9169秒に対し約6.5%遅かった。推定負荷の最大/平均は1.076→1.023へ改善したが、セル数の最大/平均は1.011→1.101へ悪化した。境界面の回帰係数（セル0.85個相当、R²0.42）が真の追加コストを表すとは限らず、相関に基づく重みで実際の負荷を均せなかった。9月の車輪・下面セル3:1も不採用だった。

[点数モデルの比較](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/issues/37#issuecomment-5982497060)では、パッチ付きmultiLevel対照4run平均2.7759秒に対し、重み倍率2の37217605578は2.8367秒（約2.2%遅い）、倍率12の37215108809は2.9441秒（約6.1%遅い）。倍率2は点数の最大/平均1.089→1.039へ改善した一方、セル数が1.073へ偏った。倍率12はノード間面208,092→1,039,557へ増加し、重みの中間加算による32-bit整数あふれが原因候補として記録された。overflowは診断上の推定であり、今回独立に実行再現してはいない。いずれも不採用で、後の多制約METIS試行とは別の履歴である。

## ccache再共有：小さなコストを承知で維持した設定

[31948680575の比較](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/31948680575)は同一ログインノード・warm cacheでreshare false/trueを各3試行測定した。cacheable1789、local hit1785、miss4は全試行同じ。remote writeはfalse8件、true3574件で、再共有が実際に発生した。

Gadiのbuild中央値は249.630→248.953秒で−0.27%、job全体259.578→259.633秒とほぼ同じ。玄界は300.497→311.158秒（+3.55%）、job全体350.584→364.854秒（+4.07%）。比較条件：各3試行で測定範囲に重なりあり。共有先を常に補完する利便性を優先し、reshare=trueを維持した。再共有によりremote writeが増えたことが、玄界の時間増加の原因と考えられる。[設計・全測定値](../ccache-reshare.md)。

車輪・下面3:1の初期比較について、Codex `01a0d95d-b1ba-79b1-a6a7-ae0e9d37ef77`の監視記録では同commit3922bdcの36163983502が4.70489秒、反復36173691744が3.17697秒、両方VALID・Cd0.28382494。同じweighted case cacheを再利用したが割当hostは異なり、IMB結果も一貫せず差の原因を確定していない。実行ごとの変動が大きかった。この会話では巨大case archiveのcostWeight内容までは検査していないことも明記されている。
