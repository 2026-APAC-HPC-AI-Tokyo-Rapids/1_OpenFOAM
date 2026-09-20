# OpenFOAM実験でBigQueryへ収集する情報

## 結論

コンテストの正式な性能値は、`simpleFoam`が出力する2ステップ目以降の`Average wall-clock time per time step`とする。小さいほど良い。

[OHC-1論文](https://arxiv.org/html/2603.27565v1)は、time-to-solution、前処理時間、time per iteration、エネルギー、FVOPS、並列効率、空力係数を分析している。FVOPSは次式で定義される。

```text
FVOPS = cells * measured_iterations / measured_wall_time
```

現行課題ではセル数が固定され、公式時間が`average_seconds_per_iteration`として得られるため、診断用FVOPSは次のようにBigQuery上で算出できる。

```text
FVOPS = cells / average_seconds_per_iteration
```

したがってFVOPSを別の生データとして保存しない。公式値、セル数、反復数、ノード数を保存し、FVOPSやFVOPS/nodeはクエリで導出する。

## すべての通常runで収集する情報

既存の`run / key / value`テーブルとキー体系を維持する。次の情報が、ASPIRE-2Aの通常runにおける必須収集対象である。

| 分類 | BigQueryへ保存する情報 | 主な既存キー |
| --- | --- | --- |
| 実行の識別 | run ID、bench/profile、Git commit、Actions run、計装バージョン | `run.identity.*`, `source.track.head_commit` |
| 課題の識別 | OpenFOAM v2512、公式ケースcommit、65M mesh、固定入力の識別 | `workload.manifest` |
| ビルドと実行物 | site moduleまたは独自ビルド、コンパイラ、MPI、実行バイナリ、launcherの実効バージョン | `build.provenance`, `build.provision` |
| PBS要求と実績 | queue、project、nodes、ranks、memory、walltime、job ID、終了状態、実使用時間・CPU時間・最大メモリ | `scheduler.request`, `scheduler.accounting` |
| ハードウェア | CPU型番、socket/core/thread構成、cache、総メモリ、NUMA、kernel、周波数・boost設定 | `hardware.minimal.node.*` |
| MPI配置 | global/local rank、hostname、CPU affinity、NUMA memory affinity、launcher引数、MPI環境 | `parallel.rank_placement`, `env.*` |
| 領域分割 | method、subdomain数、rank別セル数、rank間境界面数、processor patch数 | `mesh.partition.*` |
| メッシュ | cells、faces、internal faces、points | `mesh.topology` |
| 工程別時間 | case preparation、renumberMesh、potentialFoam、applyBoundaryLayer、solver、全pipeline | `perf.stage.*.wall_time_sec`, `perf.pipeline.wall_time_sec` |
| ソルバー経過 | ステップごとのExecutionTime/ClockTime、圧力solverの残差と反復数、終了マーカー | `solver.step_timings`, `solver.pressure_solves`, `solver.log_markers` |
| 公式結果 | VALID、平均秒/step、ステップ間標準偏差、計測反復数、nodes/ranks/cells | `result.official` |
| 空力健全性 | 最終stepと最終$C_d$、元の`coefficient.dat` | `result.aero_sanity` |

ステップ間標準偏差と、同一条件を複数回実行したときのrun間ばらつきは別物である。run間の分布は、同じ条件の複数runをBigQueryで集計して求める。

## 追加する情報

### 空力係数の時系列

論文は$C_d$だけでなく、$C_l$と$C_s$の平均・分散も数値的な一貫性の確認に使用している。現行コンテストの公式sanity checkは最終$C_d$なので、その判定方法は変えない。一方、`coefficient.dat`に存在する以下の列は、順序付き配列として1キーに保存する。

```text
result.aero_coefficients = [{step, Cd, Cl, Cs, CmPitch}, ...]
```

存在しない列は追加しない。完全な`coefficient.dat`もartifactへ残す。現行課題は40/80/150ステップと短いため、論文の長時間収束run向け`meanCalc`閾値を公式合否判定として適用しない。

### profileの要約

profile runでは、ASPIRE-2Aで実際に利用可能なツールから次を取得する。

- 全rankのMPI時間比率、MPI待機時間、負荷不均衡
- 上位MPI関数と呼出回数・時間
- 代表rankの上位計算関数
- 取得可能ならメモリ帯域、cache miss、実行周波数

ツール固有の全出力はartifactへ保存し、BigQueryには比較に使う小さな構造化要約だけを`profile.*`として送る。profile値を通常benchの性能値に混ぜない。

### エネルギー

論文ではenergy-to-solutionとenergy per iterationを重要指標としている。ただしTDPからの推定には不確実性がある。ASPIRE-2Aでスケジューラまたは電力計測APIから実測値を取得できる場合だけ、次を保存する。

```text
energy.observation = {joules, scope, started_at, finished_at, source}
```

`scope`は`solver`または`job`を必須とし、前処理を含むjob全体の値をsolver energyとして扱わない。実測手段がなければ保存せず、TDP推定値を実測値として登録しない。

## BigQueryで導出し、生データとして重複保存しない値

| 導出値 | 計算方法・注意 |
| --- | --- |
| 公式計測区間の総時間 | `average_seconds_per_iteration * measured_iterations` |
| FVOPS | `cells / average_seconds_per_iteration` |
| FVOPS/node | `FVOPS / nodes` |
| cells/rank | `cells / ranks` |
| cells/physical core | hardwareと配置から求めた使用physical core数で割る |
| rank別セル不均衡 | `mesh.partition.observed`のrank別セル数から算出する |
| ノード間境界面数 | rank配置とrank間interfaceを結合して算出する |
| run間の中央値・範囲・変動率 | 同一commit、build、条件の複数bench runから算出する |
| energy/iteration | `scope=solver`の実測joulesを反復数で割る |
| FVOPS/energy | 同じsolver計測区間のFVOPSとenergyだけを使用する |

論文のstrong scalingとparallel efficiencyは、同一計算量のrun同士を比較している。現行コンテストの公式1/2/4ノードrunは40/80/150ステップで総計算量が異なるため、そのまま論文のstrong-scaling式へ入れない。平均秒/stepによるノード数別比較はできるが、「公式scaling系列」または「per-step scaling」と明記する。

## artifactだけに保存する情報

次はBigQueryへ全文を複製せず、artifactを正本とする。

- solver、PBS、準備工程の完全なテキストログ
- `coefficient.dat`、実使用入力辞書、ジョブスクリプト
- profilerの生データと詳細レポート
- 大きなメッシュ、`processor*`、OpenFOAMインストールツリー

BigQueryには比較・検索に必要な構造化値と、artifactへたどるためのrun IDを保存する。

## 実装順序

1. 既存キーをASPIRE-2Aの通常runで欠損なく収集する。
2. `result.aero_coefficients`を追加する。
3. ASPIRE-2Aで利用できるprofileツールを確認してから`profile.*`要約を決める。
4. 信頼できる実測エネルギー源が確認できた場合だけ`energy.observation`を追加する。

新しい派生値専用キーやクラスタ固有の別名キーは作らない。
