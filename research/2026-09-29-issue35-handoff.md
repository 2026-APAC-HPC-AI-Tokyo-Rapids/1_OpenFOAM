# Issue #35 OpenFOAM 最適化作業 引き継ぎ書（2026-09-29）

本書は、公式OpenFOAM HPC課題 `occDrivAerStaticMesh` の最適化作業（GitHub Issue #35）を別の担当者が継続するための引き継ぎ資料である。進捗の正本は `TASK_2a_optimization.md`、ルールの正本は `OFFICIAL_RULE.md`（`tasks/2. OpenFOAM HPC Task Rules.md` + 2026-09-25追補）、実行履歴は Issue #35 と GitHub Actions、raw出力は自宅サーバーの artifact 保管先にある。

## 1. 目的と採点条件

- 対象: `occDrivAerStaticMesh`（65,334,765セル、`simpleFoam`、kOmegaSST、OpenFOAM.com v2512）。
- 評価指標: `simpleFoam` ログの `Average wall-clock time per time step`（2ステップ目以降、小さいほど良い）。4ノードが採点run、1/2/4ノードはスケーリング確認。
- 採点runの反復数: 1/2/4ノードで 40/80/150。
- 環境の役割: ASPIRE-2A（AMD EPYC 7713、標準compute node）が現行の採点対象。Gadi（Intel Xeon Platinum 8470Q）は停止中のため復旧後に回帰確認。玄界はルール上「extra information」で採点対象外、計測手法・toolingの先行検証に使用。
- Basic/Bonus: Basic=未改変v2512・`hierarchical`/`scotch`。Bonus=他分解、`renumberMesh`オプション、**v2512ソース変更**、`LD_PRELOAD`/`-Wl,--wrap`、GAMG `processorAgglomerator`、unsafe FP flag等（`OFFICIAL_RULE.md` §6.8）。Bonusは同一マシン上の自分のBasic比でspeedupを示す。
- **ソース変更Bonusの自己証明（F3, §6.9）**: Bonus runと同じ分解手法・係数で、Bonus変更だけを外した pre-change baseline を1/2/4ノード40/80/150で取得し、Cd差±0.5%を証明する。分解手法だけを変えるBonusは追加pre-change baseline不要（§6.9 line 577）。
- 禁止（全tier）: 精度低下、`fvSchemes`変更、F2で禁止の`fvSolution`変更、GPU、結果捏造。

## 2. リポジトリとブランチの現状

- 作業ツリーの現在ブランチ: `experiment/issue35-gamg-procagg`（tip `2798902`）。
- 主要ブランチの tip:
  - `experiment/issue35-gamg-procagg` … `2798902`（Phase 4のGAMG `masterCoarsest` 実験。`benchmark/occDrivAerStaticMesh/system/fvSolution.fixedIter` に `processorAgglomerator masterCoarsest;`、`benchmark/workload.json` の `case.identity_sha256` を `e2a3b605...` に更新済み）
  - `experiment/issue35-basic-optimization` … `fd6f618`（`decomposition-4n.txt=hierarchical` に戻した状態。40反復ポリシー有効）
  - `main`（Basic確立を含む）
- **要対応**: 40反復スクリーニングポリシーが両実験ブランチで有効。最終採点runの前に150反復へ戻す（§7）。
- 未コミットの正本: `TASK_2a_optimization.md`（コミットしない運用）。

## 3. 確定済みの事実（数値）

### Basic（未改変v2512、`hierarchical (16 8 4)`、512 rank、8/L3）
- 4ノード150反復: 5run平均 **3.245813 s/iter**（標準偏差約0.009）、Cd `0.27356199554825078`。
- 40反復スクリーニング基準: **3.214143 s/iter**（Actions 36373671818、Cd `0.43724132489600431`、`configured_iterations=40`）。
- 1ノード128 rank `(16 8 1)` 40反復: 平均 **13.519160 s/iter**、Cd `0.43305408931961498`。
- 2ノード256 rank `(16 8 2)` 80反復: 中央値 **6.532428**、平均 8.319643。**スケジューラのホスト対依存が支配的**（近接`x1003*`≒6.51–6.53、別ラック`x1001*`=12.47、`x1002c0`=9.55）。
- スケーリング: ホスト対一致の高速標本で1→2≒2.07倍、2→4≒2.01倍（ほぼ線形）。
- Cdは分解依存（GAMG coarseningがdecomposition依存、未収束150反復で数%差）。case入力は全run同一。

### Bonus（現行最良、`multiLevel (4 2 4 16)`、512 rank）
- 4ノード150反復: 3回平均 **2.866837 s/iter**、Basic比約 **11.5%高速**。40反復では 2.846727 s/iter（Actions 36377437153、Cd `0.43422333004788705`）。
- `hierarchical` は `multiLevel` より約13.18%遅い。

### 不採用の確定事項
- `-march=znver3`: 2.865256 s/iter（既存3回の範囲内、改善なし）。
- `nHierarchical (4 8 16)` order `zyx`: 3.257905（既定`(16 8 4)`の+0.4%以内、ノイズ内）。
- 重み3:1分割: ノード間境界面-9.3%だがCdが2.595%低下し遅い。
- ランタイムスイッチ（`commsType=scheduled`, `topoControl=2`, `nbx.tuning=1`, `pbufs.tuning=1`, `unifiedGeometricField=1`）: いずれも1%超の改善なし、または悪化。
- `multiLevel`階層 `(4 2 8 8)`: `(4 2 4 16)`比+0.67%遅い。
- AOCC/AOCL: 一貫した優位と判定せず（GNUが標準）。
- `WM_LABEL_SIZE=32`, `WM_PRECISION_OPTION=DP` は既に適用済みで追加の改善軸ではない。
- Basicのランク数検証: 448 rankは512 rankより遅い（全コア512 rankが最良）。

### Phase 2（分解手法 kahip/metis/ptscotch）: 実行不可で結論
- 候補コミット `805943e`(kahip)/`74010ee`(metis)/`f0ae3d4`(ptscotch) は全滅。kahipは `FOAM FATAL ERROR: Attempted to use <kahip> without the kahipDecomp library loaded.`。
- ビルド調査: **scotchのみ実体**（`libscotchDecomp.so`）、`lib/dummy/lib{metis,kahip,ptscotch,scotch}Decomp.so` はスタブ。`scripts/build-openfoam-task.sh` は `makeSCOTCH -no-mpi` のみ。ThirdPartyソースは `/app/apps/openfoam/2512/ThirdParty-v2512/sources/` にあり `makeMETIS`/`makeKAHIP` で追加ビルド可能だが本課題では実施しない。
- 記録: Issue #35 コメント `5886244761`。`decomposition-4n.txt` は `hierarchical` へ戻し（`fd6f618`）。

### Phase 4（GAMG `processorAgglomerator masterCoarsest`）: 不採用で結論
- 結果: **3.373321 s/iter（40反復baseline 3.214143比 +4.95%）**、Cd `0.43746620632609945`、VALID（Actions 36539722079 / `r-cd53b5945c8a8fb47fc489582e1d5362`）。
- 機序: `processorAgglomerator`未設定時は `procAgglomeratorPtr_` がnullで最粗も512 rank並列。`masterCoarsest`は`nMasters`/`nProcessorsPerMaster`未指定だと`nProcessorsPerMaster_=0`（`masterCoarsestGAMGProcAgglomeration.C:57-65`）→`procAgglomMap=Zero`で全rankを**master 0の1 rankへ集約**（同:152）。`coarsestLevelCorr`は`PCG/DIC`の`minIter=maxIter=35`固定反復で、集約後の粗系（数千〜約1万セル）を1 rankが直列に35反復処理し、残り511 rankが待機。これがV-cycle 12回×毎SIMPLEステップで蓄積。gather/scatterの集団通信も加算。
- 結論: 未設定（完全並列の粗solve）が最良。`eager`/`procFaces`/`nMasters`も集約方向のため見込み薄。
- 記録: Issue #35 コメント `5887433063`。

## 4. ボトルネックの実測根拠（`research/2026-09-26-openfoam-task-execution.md`）

- 40反復のPMPI診断で **rank当たり63,194回の`MPI_Allreduce`**（約1,580回/step、計装実行の値）。
- `smoothSolver.residual` 区間の中央値 **410 ms/rank/step**、`Amul` 累積 **249 ms/step**（面ループ149.7 + interface更新42.0）。
- Stage 8: 内部面数がほぼ同じ rank 287/349（380,575対380,801）で `omega`内部面係数ループが **20.688対1.318 ms**、DRAM/IO由来のL1需要補充が190,645対8,209回 → **メモリアクセス局所性が支配的**。
- Stage 11: `omegaDiv.internalFaces` の遅速群差 **+16.626 ms**、5配列操作に分散。
- L1需要補充: GaussSeidelの95%がローカルL2、`residual` 13.46%・`Amul` 14.32%がDRAM/IO。
- 旧CrayPAT(150反復): rank間送信2.8515 TB、うちノード間は **203.9 GB（7.15%）**。ノード間通信はlatency-bound。
- IPC: Gauss-Seidel 0.88、`residual` 0.48、`Amul` 0.60（低い）。

## 5. ビルドとソース改変の適用機構

- 現状、ソースは `OPENFOAM_SOURCE_OID`（`3_OpenFOAM_Src`）からtarballで取得し `platforms/aspire2a/build-environment.sh:47` の `prepare_build_sources` で展開。**ソース改変の適用機構は未実装**。
- AGENTSの「source mirrorは読み取り専用」に従い、**本リポジトリが所有するパッチをビルド時に当てる**方式を推奨。
  - 新規 `platforms/aspire2a/source-patches/*.patch` を `prepare_build_sources` で `patch -p1` 適用。
  - `scripts/build-inputs-match.sh:19` の `build_inputs` にパッチを追加 → 変更で必ず新規ビルド。
  - `cluster_compile_flags` に `OPENFOAM_SOURCE_PATCH_IDENTITY=<sha>` を追加して来歴記録（`scripts/source-tree-identity.sh` が展開後ツリー全体をハッシュ）。
- `scripts/build-openfoam.sh` は `WM_LABEL_SIZE=32 WM_PRECISION_OPTION=DP WM_COMPILE_OPTION=Opt`、`build_tuning_flags=`（空）。`WM_PRECISION_OPTION=SPDP` は `scalar=float`/`solveScalar=double` で **保存精度がfloat化**するため禁止（精度低下）。

## 6. Phase 3（ソース変更）候補カタログ

優先度順。各候補は1パッチ/1コミットで管理し、4ノード40反復でスクリーニング→有望ならF3へ。

**M1. 固定反復時の収束ノルム／残差再計算の除去（最有力・数値不変）**
- `solvers/smoothSolver/smoothSolver.C`: ループ内 `matrix_.residual(...)`（全面パス）＋ `gSumMag`（Allreduce）を毎反復。`tolerance=relTol=0` ではpsiに寄与しない。最終反復のみ計算にすると **U15+k8+omega8=31面パス＋31 Allreduce/step**を削減。
- `solvers/PCG/PCG.C:190-192`: `finalResidual = gSumMag(rA)` を毎反復（35回）。psiは`wArA`/`wApA`のみに依存。
- `solvers/GAMG/GAMGSolverSolve.C:138-147`: 各反復の `Amul`＋`gSumMag` も収束判定専用。
- `normFactor`（`lduMatrixSolver.C`: `sumA`面パス＋`gAverage`＋依存する`gSum`の2 Allreduce）も固定反復では報告専用。
- psiはbitwise同一。ログ残差は最終値のみになる。リスク: 低。

**M2. omega/k方程式の組立で一時配列とパスを融合**
- `finiteVolume/convectionSchemes/gaussConvectionScheme/gaussConvectionScheme.C:84-113`: `tweights`＋`fvm += fvc::surfaceIntegrate(faceFlux*correction(vf))` がsurface場＋vol場の一時を作り複数回全面走査。
- `interpolation/surfaceInterpolation/schemes/linearUpwind/linearUpwindV.C:44-90`: `tsfCorr` を確保。
- `TurbulenceModels/turbulenceModels/Base/kOmegaSST/kOmegaSSTBase.C`（omega式は570付近）: `divU`/`grad(U)`/`S2`/`GbyNu0`/`G`/`CDkOmega`(grad 2本)/`F1`/`F23` の一時場。
- `correction`面値を直接 `fvm.upper()/lower()/diag` へ加算し中間場を消す。FP加算順は変わる。リスク: 中（Cd）。

**M3. 反復ソルバ間のスクラッチ再利用**
- `PCG.C:87-101`（pA/wA/rA）、`GAMGSolverSolve.C:52-69`（Apsi/finestCorrection/finestResidual/coarse fields）を毎solve確保・解放。mesh単位の再利用バッファへ。リスク: 低。

**M4. GaussSeidel の `bPrime = source` コピー削減**
- `smoothers/GaussSeidel/GaussSeidelSmoother.C`: 各sweepでnCellsコピー（約1MB/rank）。リスク: 低、効果: 小。

**C2. 粗レベルPCGのpipelined化（`PPCG`/`PPCR`）**
- `lduMatrix/solvers/PPCG`。反復あたりallreduce 2→1。`coarsestLevelCorr`の変更（設定）またはsolver internals。リスク: 中（収束挙動）。

**N1. THP/NUMA（環境・`LD_PRELOAD`/`--wrap`、ソース不改変）**
- 大配列へ `madvise(MADV_HUGEPAGE)` でTLBミス削減。`numactl --localalloc` と自動NUMAバランス無効化。M1と独立に重畳可。リスク: 低。

### Phase 3のprior art（旧課題・重要）
旧 `cavity3D-64M`（icoFoam/v2606、FVOPS指標）では以下を検証済み。**メカニズムは参考になるが数値を流用しない**。
- `DIC cell-gather`（`DICPreconditioner::precondition` をセル単位gatherへ）と `PCG residual-loop fusion`（`PCG::scalarSolve` の残差L1集計を更新ループへ融合）を統合したビルドは4ノードで **+5.85%**（8.4573 vs ベースライン中央値7.9900 M FVOPS）、単独版は各+1.99%。旧ソース `master` へマージ（`7d59c05ec`）。→ M1/M3の方向性を裏付ける。
- 対称 `Amul` のCSR化はベースライン比 **-7.1%** で棄却。
- 関連ブランチ: `experiment/dic-cell-gather`, `experiment/pcg-loop-fusion`, `experiment/dic-pcg-combined`, `experiment/amul-csr`。文書: `research/dic-pcg-combined-experiment.md`。
- `experiment/issue33-omega-allocation` は Issue #33 で omega の一時配列分離を**計装**したもの（プロファイル目的）。
- `experiment/issue33-znver3` は `-march=znver3` 検証（§3で不採用確定）。

## 7. 未決事項と次のアクション

1. **Phase 3の第1候補を決めて実装する**。推奨順は M1 → N1 → M2 → M3/C2。M1は通信（Allreduce）とメモリ（面パス）を同時に削減し数値不変で最も安全。
2. **ソース改変の適用機構（§5）を実装**する。`experiment/issue35-basic-optimization`（`fd6f618`）から新ブランチ（例 `experiment/issue35-source-*`）を切る。現ブランチ `experiment/issue35-gamg-procagg` は GAMG変更を含むため流用しない。
3. **F3のpre-change baseline**を確定する。Bonus基盤を `multiLevel (4 2 4 16)` に置くか `hierarchical` に置くかを決める（§6.9は同一分解を要求）。pre-change baselineは変更を外した同一ビルド。
4. **40反復スクリーニング**（4ノード）→ 有望なら **1/2/4ノード×150反復＋F3**。
5. **最終採点run前に40反復ポリシーを150へ戻す**: `benchmark/workload.json` `iteration_by_nodes."4"`、`benchmark/parse_result.sh`、`experiment-metrics/src/experiment_metrics/workload.py`（`{"1":40,"2":80,"4":40}`）、および tests。
6. Phase 2で追加した kahip/metis/ptscotch ハーネス対応（`scripts/prepare-openfoam-case.sh` `--decomposition-method`、`run-openfoam.sh`、PBS、workflow validation、preset `aspire2a-{kahip,metis,ptscotch}-4n-512r`）は**未使用の一般性**。AGENTSに従い、不要なら撤去する。
7. 実験ブランチの棚卸し（`experiment/issue35-gamg-procagg` は結論済みのため削除候補）。

## 8. 運用・コマンド・保存先

- テスト/静的検査: `uv run --project experiment-metrics pytest -q experiment-metrics/tests tests`、`uv run --project experiment-metrics ruff check experiment-metrics`、`bash -n`、`actionlint .github/workflows/aspire2a.yml`。Pythonは`uv`、パッケージは `tmux session:root`。
- ワークフロー: `openfoam.yml` → `aspire2a.yml`。pushトリガは `on.push`（branchフィルタなし）、`paths-ignore: research/**, **/*.md`。commitメッセージの `[cluster:aspire2a]`/`[nodes:N]`/`[profile]`/`[require-build]` で制御。手動実行は `workflow_dispatch`（`node_count`入力）。
- 進捗コメントは日本語（`agy -p "<English + translate instruction>"` → `gh issue comment 35 --body-file`）。
- 成果物: 通常runは `/hdd_raid/samba/net_share/openfoam-artifacts/<Actions run id>/aspire2a/`（`result.txt`は `openfoam-aspire2a-occdrivaer-65m-result-*`、bundleは `openfoam-aspire2a-v2-<run dir>/run-artifacts.tar.zst`）。VPN断で梱包失敗したrunは `/hdd_raid/samba/net_share/openfoam-artifacts/manual-recovery/issue35-basic-scaling/<Actions run id>-<run dir>.tar.zst`。原データはASPIRE `/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/runs/runs/<run dir>/`。
- SSH: `.env` の `ASPIRE2A_SSH_CMD="ssh -T aspire2a.nscc.sg"`、`HOME_LAB_SSH_CMD="ssh -T tomokazu@100.85.119.7"`。
- VPNは日次認証情報更新で一時断・再接続する（今回2回発生）。SSH断で provision/回収が `Connection closed by UNKNOWN port 65535` 等で失敗するが、復旧後の再実行で成功する。

## 9. Issue #35 の主要コメント

- `5885458107`: Basic 1/2/4ノード5回キャンペーンの記録。
- `5886244761`: Phase 2（kahip/metis/ptscotch スタブ）結論。
- `5887433063`: Phase 4（GAMG `processorAgglomerator masterCoarsest`）結果と機序。

## 10. 注意・リスク

- **精度・数値同一性**: ソース変更はCd±0.5%（F3）が必須。FP加算順を変える変更（M2）は40反復でCdを先に確認する。
- **40反復ポリシーの戻し忘れ**: 最終採点runは150反復で取得すること。
- **`workload.json` の `case.identity_sha256`**: caseファイル（`fvSolution`等）を変更した場合は再計算・更新が必要。原値は `17225076d34fc3a1594e441f55493927c89c18c0ff09d9070c7a13605a9f0f8b`（gamgブランチでは `e2a3b605c5d1ab99f1493c0597bdbace82779f2b3281547e7e5d4f372fa487aa`）。
- **source mirrorは読み取り専用**: `3_OpenFOAM_Src` を更新せず、パッチは本リポジトリ所有でビルド時適用。
- **高価なrunの前に安価な検証**: 構文検査、単体テスト、`bash -n`、`actionlint`を先に行う。
- **AGENTSの順守**: push、Actions手動起動、PJM/PBS投入はユーザーの明示的許可があるまで行わない。`git add -A` を使わない。`TASK_2a.md` はコミットしない。
