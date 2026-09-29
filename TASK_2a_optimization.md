公式OpenFOAM HPC課題`occDrivAerStaticMesh`（65,334,765セル、`simpleFoam`、OpenFOAM.com v2512）を、採点対象であるASPIRE-2A（AMD EPYC 7713、標準compute node）またはGadi（`normalsr`、Intel Xeon Platinum 8470Q）の4 CPUノードで最適化してください。
評価指標は`simpleFoam`ログの`Average wall-clock time per time step`（2ステップ目以降、値が小さいほど良い）であり、1/2/4ノードはスケーリング確認、4ノードが採点runです。
本ファイルを本最適化作業の進捗の正本とし、チェックリストを実測に基づいて更新してください。
既存コードの偶然の複雑さや重複も整理してください。ただし抽象化や機能を目的化せず、YAGNI原則に従い、正確で外科的な、無駄のない、テスト可能で読みやすいコードを維持してください。
今までも行ってきたように、作業をGitHubのIssue・Sub Issueとして記録し、進捗と検証結果を定期的にIssueのコメントへ追加してください。Issue本文とコメントは日本語で作成してください。日本語の作成は`agy`コマンド経由でGemini 3.8 Flashへ依頼し、`agy`には内容を英語で伝えたうえで、Gemini側で自然な日本語へ翻訳して出力するよう明記してください。
最適化においては、闇雲にコードを書き換えて当たりはずれを見るのではなく、プロファイリングに基づき、遅い個所を、演算量が大きいのか、メモリ帯域がボトルネックなのか、同期待ちが生じているのかなど、原因の根本を明確にする姿勢を忘れないでください。
このマシン上で追加したいパッケージ等ある場合は、tmux session:rootを用いてください。また、Pythonならuv,TS/JSならbunが使えます。
公式ルール（`tasks/2. OpenFOAM HPC Task Rules.md`と2026-09-25追補）を厳守してください。
Basicは未改変v2512、分解は`hierarchical`または`scotch`のみ、`WM_*`/`FOAM_EXTRA_CXXFLAGS`を含むビルド設定、`WM_LABEL_SIZE`32/64、`caseDefinition`の`nCores`/`decompositionMethod`/`nHierarchical`と手法係数/`endTime`のみ変更可、ジョブ配置・MPI/UCX・runtime設定・SMT・parallel I/Oは自由です。
Bonusは他分解手法、`renumberMesh`オプション、v2512ソース変更、`LD_PRELOAD`/`-Wl,--wrap`、`fvSolution`のGAMG`processorAgglomerator`、unsafeな浮動小数点flagを含みます。
BonusはBasic結果を先に提出し、F3に従い同一構成の変更前baselineと1/2/4ノードのCd差±0.5%を証明し、同一マシン上の自分のBasic比で改善を示す必要があります。
精度低下、`fvSchemes`変更、F2で禁止された`fvSolution`変更、GPU、結果の捏造は全tierで禁止です。

環境の役割を固定してください。
ASPIRE-2Aを現行の採点対象とし、Gadiは停止中のため復旧後に回帰確認します。
玄界はルール上「extra information」であり採点runではありませんが、計測手法とtoolingの先行検証、およびメモリ律速の傍証に使用します。

現時点のボトルネック仮説は、メモリ帯域・レイテンシ（配列走査、一時配列、コピー、局所性）とrank間の到着時刻差（分割形状と同期）の複合です。
根拠として、ASPIREではIPCがGauss-Seidel 0.88、`residual` 0.48、`Amul` 0.60と低く、内部面数がほぼ同じrank 287/349で所要時間が約16倍・ローカルDRAM/IO由来のL1デマンドリフィルが約23倍、遅いrankは車輪・下面パッチに集中し、pre-omegaの非MPI差が約120 msに達します。
`hierarchical (16 8 4)`はノード間境界面が`multiLevel (4 2 4 16)`の11.2倍で反復時間が13.18%長い。
玄界（参考）はMemory Bound約61%、DRAM帯域約405 GB/s（bound約86%）、NUMA remoteとTLBは律速外、packed FPは約15%です。
演算器・TLB・NUMA remoteは主因ではありません。

進め方はプロファイリング駆動とし、主要因を1つずつ変えた独立commitで比較してください。
スクリーニング段階では4ノードを40反復（`iteration_by_nodes."4"=40`）で非計装runし、時間を節約して候補を絞ります。40反復は`--diagnostic`ではなく公式targetそのものとして扱い、`STATUS: VALID`・`configured_iterations=40`で記録します。採否の最終判定と採点run、1/2/4スケーリングは150反復へ戻した最終構成で取得し、発表ではスクリーニングが40反復・最終が150反復であることを明示します。改善率が「同一システムで観測したノイズ幅」と「1%」の大きい方を超え、公式判定が`VALID`でCdが許容帯域内のときのみ採用します。
profiler・instrumentationは通常benchから分離し、その所要時間を性能値に使いません。
発表が配点の70%であることを踏まえ、律速の因果、改善前後の数値、1/2/4スケーリング、来歴を証拠から再現できる形で残してください。

## 最適化チェックリスト（2026-09-27）

- [x] 変えてはならない固定要件（mesh、solver、case設定、Allrun工程、精度、禁止事項）は変更せず、`OFFICIAL_RULE.md`を正本として参照する。
- [x] ASPIRE-2Aで確立した現行基準（GNU/Cray MPICH UCX標準ビルド、1/2/4ノードのrank配置とCrayPAT/uProf計測経路、分割・toolchain・build flagの採否）を確定し、以下を既知の事実とする。
  - [x] NUMA-aware `multiLevel (4 2 4 16)`、4ノード512 rankの非計装公式150反復は3回平均2.866837216286354秒/iterationで各回`VALID`である（現行main最速構成。採点性能はBasic提出物が対象のためBonus位置づけとする）。
  - [x] 公式ケース既定`hierarchical (16 8 4)`は4ノード2回とも`VALID`で約3.245秒/iterationとなり、`multiLevel`より13.18%遅い。
  - [x] 車輪・下面パッチに接するセルへの重み3:1分割はノード間境界面を9.3%減らしたが公式2回とも遅くCdが2.595%低下したため不採用とする。
  - [x] `-march=znver3`は2.865256139422819秒/iteration（既存3回の範囲内）で改善を示さないため不採用とする。
  - [x] AOCC 5.0/AOCL 5.1.0は4ノードで約0.36%高速な後2回を含む一方、1/2ノード差と外れ値のため一貫した優位と判定せず、GNUを標準・AOCCを検証済み選択肢とする。
  - [x] `WM_LABEL_SIZE=32`はASPIRE-2Aの実行経路で既に適用済みであり、追加の改善軸ではない。
  - [x] 玄界（参考）で公式workloadのMemory Bound約61%、DRAM約405 GB/s・bound約86%、Gauss-Seidel最大トラフィック、NUMA remote/TLBが律速外であることを確認済みである。
- [ ] Basicの分割手法（`hierarchical`または`scotch`）による1/2/4ノード公式runを確保し、Bonus比較の基準にする。
  - [x] `scotch`の4ノード512 rank公式150反復（Actions 36255514227 / PBS 25570270.pbs101、run r-aaebc6de54a2abf23731ddae4fde371b）は`VALID`、5.032413983758389秒/iteration（標準偏差0.06618520537694263）、Cd 0.28404934573921931。multiLevel比+75.5%、hierarchical既定比+約55%で、scotchはノード/NUMA境界を考慮せずノード間境界面が増えるため採用しない。ASPIRE-2AのBasicはhierarchicalを基準とする。
  - [x] `nHierarchical`は編集可能なため、`(16 8 4)`以外の候補もBasic候補として比較した。`(4 8 16)`・order `zyx`（Actions 36258849614 / PBS 25570770.pbs101）は`VALID`、3.25790536361745秒/iteration、Cd 0.28264876338289940で、既定`(16 8 4)`の約3.245と+0.4%以内（ノイズ内）であり、n/orderの変更では改善しない。`(16 8 4)`・order `xyz`をBasic基準として維持する。
  - [x] Basicの`hierarchical (16 8 4)`・40反復ベースラインを確立した（Actions 36373671818、`decomposition-4n.txt=hierarchical`、3.214143072384615秒/iteration、Cd 0.43724132489600431、`VALID`、`configured_iterations=40`）。150反復の3.244826秒/iterationと整合する（差0.95%）。スクリーニングはこの40反復値を基準にする。
  - [x] 1/2/4ノードの公式step数を各5回取得した（Basic `hierarchical`、128/256/512 rank）。梗概は下記のとおりで、各runのActions ID・run dir・保存先を併記する。
    - 1ノード128 rank `(16 8 1)` 40反復、Cdは5runとも`0.43305408931961498`。s/iter: `13.53363842510256`（36387480547 / r-982ff36679e8346c8ea007858262a274）、`13.50679916082051`（36391633547 / r-232774a5996dc71ba115ea5358f731a8、クラスタ回収）、`13.54229648833333`（36396357628 / r-86078fae603c6bb9524c80412db1737a）、`13.52141208471795`（36400670569 / r-178f52120c5d345e7fb28a2eb800ba4a）、`13.49165466694872`（36400674307 / r-0c636162671dc3e3f100e4249d0d67da）。平均`13.519160` s/iter、ばらつきは約0.4%。
    - 2ノード256 rank `(16 8 2)` 80反復、Cdは5runとも`0.33732808147340321`。s/iter: `6.532428082734177`（36384019142 / r-b795a1a085e0b556485b5619056e72c5）、`6.528605927949368`（36387486409 / r-8f0704366cfe7bce5b587cb055ded5cf）、`9.554562435987341`（36391637027 / r-5944ddcec4af35e710b55828141e8fc2、クラスタ回収）、`12.47455370191139`（36396361553 / r-b894b3492e900129daeaec5a5f20cc76）、`6.508063203632912`（36400667214 / r-3aa5b13a7928e500997ed9ed0d59760c）。2ノードはスケジューラが割り当てるホスト対に強く依存し、同一シャーシ近接（`x1003c7s1b1n1`・`x1003c7s2b1n0`、`x1003c0s4b1n0`・`x1003c1s1b0n1`）で約`6.51`–`6.53`、別ラック（`x1001c2s3b1n1`・`x1001c3s1b1n1`）で`12.47`、`x1002c0`で`9.55`と分離した。中央値`6.532428`、平均`8.319643`。
    - 4ノード512 rank `(16 8 4)` 150反復、Cdは5runとも`0.27356199554825078`。s/iter: `3.247995005234901`（36089770567 / r-636ec2ca86b7a76d4be8644a7925441e）、`3.241657861402685`（36095135945 / r-b16de8bfe8e6f86700ed2c268b27eb7f）、`3.241263271429531`（36391627623 / r-20d7b99b21f4be8f8c6ac5cacfef9e61、クラスタ回収）、`3.260544584214765`（36391630516 / r-42331a4a355cf4ea5b87fc1a8ac645b6、クラスタ回収）、`3.237605580818792`（36396365266 / r-203652fca786baa9554f94780e37d450）。平均`3.245813`、標準偏差約`0.009`。
    - スケーリング: ホスト対が揃った高速標本では1→2ノードが約`2.07`倍、2→4ノードが約`2.01`倍でほぼ線形。平均値で見ると2ノードの配置依存で見かけ上`1.63`倍・`2.56`倍となるため、2ノードは配置を明記して評価する。
    - 保存先: 通常runは`/hdd_raid/samba/net_share/openfoam-artifacts/<Actions run id>/aspire2a/`（`result.txt`は`openfoam-aspire2a-occdrivaer-65m-result-*`、run bundleは`openfoam-aspire2a-v2-<run dir>/run-artifacts.tar.zst`）。VPN断でActions側の梱包・回収に失敗した4runは`/hdd_raid/samba/net_share/openfoam-artifacts/manual-recovery/issue35-basic-scaling/<Actions run id>-<run dir>.tar.zst`へ手動回収した。分析前の原データはASPIREの`/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/runs/runs/<run dir>/`。
  - [ ] 最終分割でCrayPAT/PMPIによる全rankの待ち・不均衡・message統計をE2Eで完走・再解析する（公式ルールがMPI profilingを強く推奨）。
- [x] Basic最適化（性能スコアの対象）を、source無改変・同一計算の範囲で進める。ランタイムスイッチのスクリーニングは完了し、case-default`hierarchical (16 8 4)`・512 rank・8/L3の約3.2秒/iterationを確定値とする。commsType/topoControl/nbx.tuning/pbufs.tuning/unifiedGeometricFieldはいずれも1%超の改善なし。UCXパラメータ、ホスト選定、I/O設定、追加ビルドflagは、profileに裏付けられた仮説とcontrol-plane変更またはrebuildを要するため、この段階では未実施として保留する。
  - [ ] `OptimisationSwitches`のメモリ管理（アロケータ/プール等）を有効化し、一時配列・旧fieldのchurnと局所性を改善する。
  - [x] ランク数とL3あたりプロセス数を検証した。ASPIRE-2Aは1ノード16 L3（各8物理コア）。同一448 rankで、全16 L3へ7プロセスずつ分散（B2、Actions 36286767867）は3.443525秒/iteration、14 L3へ8プロセス詰め（B1、Actions 36289009710）は3.950424秒/iterationで、**分散配置が12.8%高速**（L3溢れ仮説を支持）。ただし両者とも512 rank・8/L3×16（hierarchical `(16 8 4)`、約3.245）より遅く、**Basic最適は全コア512 rankの分散配置**で、プロセス/L3を減らすとrank数減の不利が上回る。Cdは両者一致（0.28831843092215143、同一分割）。単発runでnode分散の併存に注意。
  - [x] `commsType=scheduled`を準備工程・simpleFoam solverの両方で試験したが、準備工程では`potentialFoam`のGAMG `scale()`、solver限定でもGAMG `scale()`/`Vcycle()`でSIGFPEとなった（Actions 36311011900 / 36313378631）。結果・Cdは生成されず、現行ASPIRE-2A GNU/Cray MPICH UCXではBasic候補から除外し、既定`nonBlocking`へ戻す。
  - [x] OpenFOAMのtopology-aware collective選択（`topoControl=2`、bit2=reduce）をsimpleFoam solver限定で試した。Actions 36368984582は`decomposition-4n.txt`が`multilevel`のまま実行されており（`source/mesh/caseDefinition`で確認）、2.861892秒/iteration・Cd 0.29138860626177504はmultiLevel+topoControlの結果である。既存multiLevel 3回平均2.866837秒/iterationとの差は約-0.17%でノイズ内、**topoControlは効果なし（負の対照）**と判定する。bit16（combine）は`gAverage`/`gSum`が`mpiAllReduce`を通るため対象外であり、追加検証しない。
  - [x] ノード間processor exchangeを対象に`nbx.tuning=1`と`pbufs.tuning=1`をhierarchical 40反復で比較した。`nbx.tuning=1`（Actions 36375558400）は3.201892秒/iterationでベースライン3.214143比-0.38%、`pbufs.tuning=1`（Actions 36375610008）は3.250510で+1.13%。3runともCdは0.43724132489600431で完全一致し、交換スケジューリングは計算結果を変えないが、改善は1%閾値未満または悪化であり**不採用**。hierarchicalのノード間ペナルティは生のメッセージ量・レイテンシ由来で、NBX/PEXの管理処理では縮まない。
  - [x] `unifiedGeometricField=1`（境界fieldの単一確保へのレイアウト変更）をhierarchical 40反復で試した（Actions 36380214006）。3.249373秒/iterationでベースライン3.214143比+1.10%、Cdは0.43724132489600431で完全一致。悪化のため**不採用**。
  - [x] Basicのランタイムスイッチ（commsType/topoControl/nbx.tuning/pbufs.tuning/unifiedGeometricField）は一通り探索済みで改善なし。Basicはcase-default`hierarchical (16 8 4)`・512 rank・8/L3の約3.2秒/iterationを確定値とする。以降の最適化はBonus（multiLevel階層の調整（済・不採用）、GAMG processorAgglomerator、source変更）へ移る。
  - [ ] Cray MPICH UCXのパラメータ（collective選択等）を調整する。玄界のMPI autotune上限は約10%と推定済み。
  - [ ] ジョブ配置とホスト選定でrun間分散を制御する（ASPIREのホスト群で48%差を実測済み）。
  - [ ] `-fileHandler`/`-hostRoots`/`-ioRanks`やnode-local storageを含むI/O・filesystem設定を確認する。
  - [ ] unsafeでない追加ビルドflagを試す。
- [ ] Bonus（分割）を検討する。
  - [x] `multiLevel`の階層係数をトポロジに合わせて比較した。(4 2 4 16)は40反復で2.846727秒/iteration（Actions 36377437153、Cd 0.43422333004788705）、L3に整合する(4 2 8 8)は2.865666（Actions 36377508967、Cd 0.43954323815986718）で+0.67%遅く、**階層変更は不採用**。確立済みBonusは(4 2 4 16)の約2.85秒/iterationで、Basic hierarchical約3.21に対して約11.5%高速。
  - [ ] `structured`または`manual`分割で4ノード×8 NUMAへ厳密に対応させる。
  - [ ] `kahip`/`metis`/`ptscotch`をスクリーニングする。
  - [ ] `renumberMesh`オプション（`-dict`/`-renumber-method`/`blockSize`）を再確認する（玄界は<1%）。
  - [ ] 実測駆動の`weightField`を検討する（重み3:1はCd−2.6%で失敗したためCdを先に確認する）。
- [ ] Bonus（ソース、F3必須）を検討する。
  - [ ] `lduMatrix::upper()`が直後の代入で上書きする`lower`コピーを除去する。
  - [ ] `omegaDiv.internalFaces`の一時配列・deep copyを削減する（Stage 11で5配列処理に分散、差+16.6 ms）。
  - [ ] `residual`/`Amul`/`GaussSeidelSmoother`の一時配列・deep copyを削減する（時間上位の大カーネル）。
  - [ ] `Pstream`の通信実装を改善する。
  - [ ] `LD_PRELOAD`/`-Wl,--wrap`でアロケータまたはmemcpyを再利用する。
  - [ ] 各候補で1/2/4ノードのCd±0.5%（F3）と同一マシン上の自分のBasic比を確認する。
- [ ] Bonus（fvSolution）としてGAMG `processorAgglomerator`で圧力solveの集約・Allreduceをrank間移動する（ルール明示許可）。
- [ ] 最終構成で4ノードを複数run、1/2ノードのscaling、改善前後を取得し、律速の因果を発表用に整理する。
- [x] `hierarchical`既定採用、重み3:1分割、`-march=znver3`、AOCC常用、MPI autotune/CM renumbering（玄界で<1%）、fast-math、精度低下・GPU・結果捏造を実施しない。
- [ ] 各runでActions全job success、PBS/PJM exit 0、残留jobなし、`run-success`存在、公式parser `VALID`、1/2/4のノード数・rank数・CPUアフィニティ・NUMA配置一致、build/workload identity一致、固定artifactのarchive保存とSHA-256照合、BigQueryメトリクス、実験台帳の記録を確認する。

完了時には、ASPIRE-2Aの採点対象4ノードで公式workloadが非計装で再現可能に完走し、採用した最適化の因果と改善前後、1/2/4スケーリング、BasicとBonusの区別、F3による数値同一性の証明、および必要なprofileの来歴を証拠から確認できる状態にしてください。
