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
採否は非計装の公式150反復を複数run取得して判定し、改善率が「同一システムで観測したノイズ幅」と「1%」の大きい方を超え、公式判定が`VALID`でCdが許容帯域内のときのみ採用します。
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
  - [ ] 1ノード40反復・2ノード80反復も同条件で取得する。
  - [ ] 最終分割でCrayPAT/PMPIによる全rankの待ち・不均衡・message統計をE2Eで完走・再解析する（公式ルールがMPI profilingを強く推奨）。
- [ ] Basic最適化（性能スコアの対象）を、source無改変・同一計算の範囲で進める。
  - [ ] `OptimisationSwitches`のメモリ管理（アロケータ/プール等）を有効化し、一時配列・旧fieldのchurnと局所性を改善する。
  - [x] ランク数とL3あたりプロセス数を検証した。ASPIRE-2Aは1ノード16 L3（各8物理コア）。同一448 rankで、全16 L3へ7プロセスずつ分散（B2、Actions 36286767867）は3.443525秒/iteration、14 L3へ8プロセス詰め（B1、Actions 36289009710）は3.950424秒/iterationで、**分散配置が12.8%高速**（L3溢れ仮説を支持）。ただし両者とも512 rank・8/L3×16（hierarchical `(16 8 4)`、約3.245）より遅く、**Basic最適は全コア512 rankの分散配置**で、プロセス/L3を減らすとrank数減の不利が上回る。Cdは両者一致（0.28831843092215143、同一分割）。単発runでnode分散の併存に注意。
  - [x] `commsType=scheduled`を準備工程・simpleFoam solverの両方で試験したが、準備工程では`potentialFoam`のGAMG `scale()`、solver限定でもGAMG `scale()`/`Vcycle()`でSIGFPEとなった（Actions 36311011900 / 36313378631）。結果・Cdは生成されず、現行ASPIRE-2A GNU/Cray MPICH UCXではBasic候補から除外し、既定`nonBlocking`へ戻す。
  - [ ] Cray MPICH UCXのパラメータ（collective選択等）を調整する。玄界のMPI autotune上限は約10%と推定済み。
  - [ ] ジョブ配置とホスト選定でrun間分散を制御する（ASPIREのホスト群で48%差を実測済み）。
  - [ ] `-fileHandler`/`-hostRoots`/`-ioRanks`やnode-local storageを含むI/O・filesystem設定を確認する。
  - [ ] unsafeでない追加ビルドflagを試す。
- [ ] Bonus（分割）を検討する。
  - [ ] `multiLevel`の階層係数をトポロジに合わせて調整する（例 `(4 8 2 8)` 等）。
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
