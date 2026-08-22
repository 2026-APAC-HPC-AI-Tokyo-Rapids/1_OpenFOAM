# OpenFOAM motorBikeの実行性能調査

> 過去の記録: この調査はIssue #18の移行前に行った。現在の課題は`benchmark/workload.json`で固定したv2512の`occDrivAerStaticMesh`であり、以下のmotorBikeの結果とは比較できない。

## 目的

この文書は、玄界上でOpenFOAM v2606の`simpleFoam`を使ったmotorBike試験について、実行時プロファイルと起動設定の調整結果を記録する。改善対象はMPI配置、MPIとOpenFOAMの実行時設定、プロファイラの起動設定に限定し、OpenFOAMのソース自体は変更しない。

過去のAPSとVTuneの完全な結果はGitHubの成果物とは別に保存している。2026年8月23日以降のVTuneとParaView完全結果は、自宅サーバーのActions run単位の成果物ツリーを正本とする。旧`openfoam-vtune`配下は過去runの履歴として保持する。

```text
~/openfoam-profile/<github-run-id>-<pjm-job-id>/
```

新しいprofile runの大容量成果物は次の場所へ保存する。

```text
/hdd_raid/samba/net_share/openfoam-artifacts/<github-run-id>/<cluster>/openfoam-<cluster>-v2-<run-id>/large-output/vtune/vtune-result.tar.zst
/hdd_raid/samba/net_share/openfoam-artifacts/<github-run-id>/<cluster>/openfoam-<cluster>-v2-<run-id>/large-output/paraview/paraview-case.tar.zst
```

共有プロファイル領域と実行ごとのディレクトリの権限は`2770`である。この記録を作成した時点で、プロファイル全体は約3.0 GiBを使用していた。

## 試験条件

- OpenFOAM v2606、`simpleFoam`、Intel oneAPI 2025.1.3、Intel MPI 2021.15。
- 現在の既定値は玄界のCPUノード1台、MPI 120ランクである。以下の初期の拡張性調査とプロファイルでは最大2ノードを使用した。
- 各ノードは60物理コアのソケット2基、計120物理コア、240論理CPUを備える。
- APSが報告したノード間接続装置はConnectX-7。
- 領域分割はScotch。
- 計算の`endTime=3000`で、`Time=3000`に結果を1回書き出す。
- 最終メッシュは356,630セル、1,116,860面、408,877点。
- 240 MPIランクに対してメッシュが非常に小さい。
  - 240ランク: 1ランクあたり約1,486セル。
  - 120ランク: 1ランクあたり約2,972セル。
  - 60ランク: 1ランクあたり約5,944セル。

メッシュはActionsの実行ごとに再生成した。ソルバー比較では同じケースと計算時間を使ったが、共有HPCシステムに通常生じる実行間の揺らぎを考慮して経過時間を解釈する必要がある。

## 1ノード120ランクでのMPI調整

現在の運用条件は1ノード120 MPIランク、物理コアあたり1ランクである。Intel MPI 2021.15は、このジョブを自動的に共有メモリ通信だけへ切り替えなかった。基準条件の診断ログでは、全ランクが1ノード上にあっても`mlx` libfabric提供機能が選ばれていた。`scripts/run-openfoam.pjm`で次を明示すると、不要な提供機能を避けられる。

```bash
export I_MPI_FABRICS=shm
```

各設定は別々のコミットとして変更・プッシュしたため、表の各行は独立したActions実行とPJMジョブである。「起動全体」にはソルバーだけでなくMPIの初期化と終了も含む。

| 実行 | MPI設定 | ソルバー時間 | 起動全体 | 結果 |
| --- | --- | ---: | ---: | --- |
| #141 | Intel MPI既定値 | 111 s | 120.81 s | 基準条件。診断出力で`mlx`を選択 |
| #142 | `I_MPI_FABRICS=shm` | **101 s** | **104.45 s** | 共有メモリ通信だけを使った試行で最速 |
| #143 | `I_MPI_PIN_DOMAIN=core`、`I_MPI_PIN_ORDER=scatter` | 105 s | 114.60 s | 実効CPU一覧は既定値と同じ |
| #144 | `I_MPI_PIN_DOMAIN=core`、`I_MPI_PIN_ORDER=compact` | 106 s | 115.96 s | 実効CPU一覧は既定値と同じ |
| #145 | `I_MPI_ADJUST_ALLREDUCE=1`（再帰的倍加） | 未完了 | 未完了 | PJMの25分上限までにTime=943までしか到達しなかった |
| #146 | `I_MPI_ADJUST_ALLREDUCE=9`（Knomial） | 112 s | 120.21 s | 自動選択より遅い |
| #147 | `I_MPI_ADJUST_ALLREDUCE=11`（共有メモリ向けKnomial） | 106 s | 116.53 s | 通信方式を共有メモリだけには限定しない |
| #148 | Intel MPI集合通信の自動調整 | 107 s | 115.93 s | 調整負荷と結果が共有メモリだけの条件より悪い |
| #149 | `I_MPI_FABRICS=shm`の再試行 | 107 s | 109.30 s | 通常の実行間変動を含めても効果を確認 |
| #150 | 共有メモリ通信とKnomial Allreduce | 103 s | 105.43 s | 共有メモリ通信だけの条件との差は雑音範囲で、追加指定の根拠はない |
| #151 | 共有メモリ通信専用のソルバー設定、診断無効 | **101 s** | **103.46 s** | ソルバーの検証に成功 |
| #152 | すべてのMPI処理へ共有メモリ通信を適用 | **101 s** | **104.06 s** | 最終的な一連処理の検証に成功 |

基準条件ではランク0--119を論理CPU 0--119へ固定していた。明示的な`core`固定でも同じ一覧になったため、配置順序による小さな時間差は配置の違いではなく雑音である。有効だった改善は固定方法ではなく通信方式の選択である。

#152では、共有メモリ設定をすべてのMPI前処理より前へ移したことで、Actionsのログ追跡区間が基準条件#141の201秒から165秒へ短縮した。設定を`simpleFoam`だけへ適用した以前の試行は、同じ区間に185--189秒かかった。この配置により、主ソルバーだけでなく`snappyHexMesh`、`topoSet`、`potentialFoam`も改善した。

このジョブではAllreduce方式を一律に固定すると逆効果になる。OpenFOAMは異なるメッセージ容量と状況でAllreduceを呼ぶため、Intel MPIの容量別自動選択を維持するべきである。特に再帰的倍加は不適切で、PJMの上限時間内に完了しなかった。最終設定は`I_MPI_FABRICS=shm`だけを指定し、プロセス固定、集合通信方式、自動調整は既定値のままとした。

## ソルバー時間の結果

「ソルバー時間」はOpenFOAMが最後に出力する`ClockTime`である。「起動全体」は`mpirun`を`/usr/bin/time`で囲んだ値であり、MPIの初期化と終了も含む。APSやVTuneを使った計測実行は直接比較から除外した。

| 実行 | ノード数 | MPIランク数 | 設定 | ソルバー時間 | 起動全体 | 結果 |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| #117 | 1 | 120 | 既定値 | 107 s | - | 以前の試験による基準値 |
| #122 | 2 | 240 | 既定値 | 105 s | 127.04 s | ランク数も倍にすると2ノードの効果はほぼない |
| #123 | 2 | 240 | `allcores:map=scatter` | 104 s | 125.71 s | 約1秒短縮したが通常の雑音範囲 |
| #124 | 2 | 240 | `allcores:map=bunch` | 107 s | 128.53 s | 既定値より遅い |
| #125 | 2 | 120 | 既定値、各ノード60ランク | **56 s** | **63.31 s** | 完了したランク数比較で最良 |
| #126 | 2 | 60 | 既定値、各ノード30ランク | 76 s | 79.55 s | 計算並列度が不足 |
| #129 | 2 | 240 | `topoControl=16` | 107 s | 127.30 s | OpenFOAMの階層型縮約が遅い |
| #130 | 2 | 240 | `nPollProcInterfaces=-1` | 114 s | 136.04 s | 完了済みインターフェースの即時処理は約9%遅い |
| #131 | 2 | 240 | Intel MPI集合通信の自動調整 | 103 s | 128.89 s | 約2秒短縮したが効果は小さい |
| #134 | 2 | 120 | Intel MPI集合通信の自動調整 | 58 s | 64.33 s | 120ランクの既定値より遅い |
| #135 | 2 | 90 | 既定値 | 68 s | 73.72 s | 計算並列度が不足 |
| #136 | 2 | 150 | 既定値 | 55 s | 65.31 s | ソルバーは120ランクに近いが起動負荷が高い |
| #137 | 2 | 180 | 既定値 | 57 s | 71.72 s | 通信負荷が増えている |
| #138 | 2 | 135 | 既定値 | 54 s | 64.88 s | ソルバーは速いが開始から終了までは120ランクより遅い |
| #139 | 2 | 165 | 既定値 | 53 s | 68.10 s | ソルバーは速いがMPI負荷が大きい |
| #140 | 2 | 120 | 最終的な既定値の検証 | 56 s | 63.31 s | #125を正確に再現 |

主要な結果は固定方法の微調整ではない。2ノードジョブを240ランクから合計120ランクへ減らすと、ソルバー時間が105秒から56秒へ約47%短縮した。さらに60ランクへ減らすと76秒へ増えた。165ランク程度まではソルバーだけの時間を少し短縮できるが、MPIの初期化と終了がそれ以上に増える。120ランクは測定した起動全体が最短で、PJMの一連処理時間も同率最短だったため、運用上の最良な既定値である。

PJM全体に近い範囲を測るActionsのログ追跡処理は、240ランクで272秒、120ランクで133秒、60ランクで133秒、90ランクで138秒、135と150ランクで154秒、165ランクで171秒、180ランクで177秒だった。60ランクが開始から終了まで120ランクと同時間なのは、ソルバーが遅い一方で起動と前処理が軽いためである。120ランクはジョブ全体の時間を増やさず、ソルバーの処理量を大きくできる。

## APSによる240ランク低速化の分析

全ランクをAPSで計測した実行は#119（240ランク）と#133（120ランク）である。生データは次にある。

```text
~/openfoam-profile/30005026547-6264943/  # 240ランク
~/openfoam-profile/30007072403-6265018/  # 120ランク
```

| APSの指標 | 240ランク | 120ランク |
| --- | ---: | ---: |
| 計測対象の経過時間 | 179.02 s | 86.62 s |
| 平均MPI時間 | 151.27 s（84.50%） | 51.80 s（59.86%） |
| MPI不均衡 | 44.30 s（24.75%） | 15.57 s（18.00%） |
| `MPI_Allreduce`平均 | 56.04 s | 18.42 s |
| `MPI_Waitall`平均 | 59.06 s | 12.38 s |
| 双方向のノード間転送量 | 289,023.6 MB | 105,093.1 MB |
| 平均DRAM帯域 | 20.66 GB/s | 29.98 GB/s |
| DRAM帯域律速 | 14.20% | 46.80% |
| 倍精度ベクトル化率 | 23.55% | 20.20% |

APSは240ランクのアプリケーションをMPI律速と判定した。全ランク合計の関数統計はおよそ次のとおりである。

- `MPI_Allreduce`が2億1,060万回。
- `MPI_Waitall`が1億8,930万回。
- `MPI_Isend`が22億2,000万回。
- 2ノード間で289 GBを転送。

120ランクでは1対1通信の呼び出し回数がほぼ半減し、ノード間通信量は約64%減少した。MPI時間の合計はそれ以上に大きく減った。MPI負荷を減らした後は、DRAM帯域が意味のある二次的な制約になる。

120ランクの全ランク合計値はおよそ次のとおりである。

- `MPI_Allreduce`が9,600万回。
- `MPI_Waitall`が9,960万回。
- `MPI_Isend`が11億3,000万回。
- 2ノード間で105 GBを転送。

ランク0は典型的ではない。240ランクのAPS実行では、ランク0のMPI比率が約51%なのに対し、大半のランクは約83--87%をMPIに費やした。このためランク0はOpenFOAM本体の計算上のホットスポットを探すVTune対象として有用だが、ほかのランクは主に通信と負荷不均衡の費用を示す。

APSは、ノードごとの統計情報が一つ欠けているとして警告を出した。240ランク実行ではランク4と195、120ランク実行でも同様に2件の記録が欠けた。APSは正しい通信集団の大きさを認識し、上位の結果も一貫していたが、合計呼び出し回数はわずかに過小評価されているものとして扱う。

## VTuneホットスポット

改善後の配置で最も有用なプロファイルは#132で、2ノード120ランクのランク0をVTune Hotspotsで計測した。

```text
~/openfoam-profile/30007051832-6265016/hotspots.<host>/
```

VTuneが測定した選択ランクの経過時間は62.06秒、CPU時間は59.26秒だった。主なホットスポットは次のとおりである。

| 関数 | モジュール | CPU時間 | 割合 |
| --- | --- | ---: | ---: |
| `PMPI_Allreduce` | Intel MPI | 11.36 s | 19.2% |
| `PMPI_Waitall` | Intel MPI | 5.57 s | 9.4% |
| `Foam::GaussSeidelSmoother::smooth` | `libOpenFOAM` | 3.54 s | 6.0% |
| `ucp_worker_progress` | UCX | 2.84 s | 4.8% |
| `internal_Isend` | Intel MPI | 2.25 s | 3.8% |
| `cellLimitedGrad<...>::calcGrad` | `libfiniteVolume` | 1.40 s | 2.4% |
| `Foam::lduMatrix::residual` | `libOpenFOAM` | 1.11 s | 1.9% |
| `Foam::lduMatrix::Amul` | `libOpenFOAM` | 0.89 s | 1.5% |
| `linearUpwindV<...>::correction` | `libfiniteVolume` | 0.78 s | 1.3% |
| `Foam::fv::gaussGrad<double>::gradf` | `libfiniteVolume` | 0.75 s | 1.3% |

240ランクのランク0ではMPIの比率がさらに大きく、`PMPI_Allreduce`が21.9%、`PMPI_Waitall`が11.3%、`internal_Isend`が8.3%だった。ランク数を減らすと3つとも低下し、行列平滑化と勾配計算が相対的に目立つようになった。

HPC Characterizationの結果もAPSと同様に、倍精度演算のベクトル化率が約20--23%と低いことを示した。ただし浮動小数点演算は全uOpsの一部にすぎず、240ランクの実行はメモリ帯域上限に達していない。そのため、ソースレベルのベクトル化を最初の改善対象にはしない。一方、120ランクではAPSがDRAM帯域負荷の増加を示しており、MPIを減らした次にメモリ局所性が制約となる可能性が高い。

## 実行時設定の指針

1. 1ノードに限定する場合はMPI 120ランクで`I_MPI_FABRICS=shm`を指定する。指定しない場合、計測したIntel MPI 2021.15は`mlx` libfabric提供機能を選択した。以前の制約なし比較では合計120ランクの2ノードがさらに速かったが、現在の1ノード条件の範囲外である。
2. 反復測定で安定したscatterの優位性が出ない限り、Intel MPIの既定のプロセス配置を使う。`scatter`の改善は約1秒だけで、`bunch`は遅かった。
3. OpenFOAMの`topoControl=0`を維持する。Intel MPIがトポロジーを考慮した集合通信を行っており、OpenFOAMの3段階階層型縮約を強制すると遅くなった。
4. `nPollProcInterfaces=0`を維持する。`-1`で完了済みインターフェースを即時処理すると、この課題は約9%遅くなった。
5. Intel MPIの自動調整は、適切なランク数を決めた後だけ試す。性能の悪い240ランク配置は約2秒改善したが、120ランク配置は56秒から58秒へ悪化した。調整ファイルは構成依存であり、ノード数、ノードあたりランク数、通信方式、MPI版が同じ場合だけ再利用する。
6. 新しいケースでは、1ランクあたりセル数を基準にランク数を振り、APSでMPI時間と不均衡を定量化する。その後、APSで計算時間が最も大きいランクを特定してVTuneを実行する。
7. VTuneの完全な結果はプロファイル終了後に自宅サーバーがクラスタから直接取得する。圧縮結果を検証して自宅側へ確定した後だけクラスタ原本を削除し、検証済みのテキストやCSV要約はプロファイル成果物と計測値経路へ公開する。
8. 将来ソース変更が許可された場合は、Gauss-Seidel平滑化、制限付き勾配計算、`lduMatrix`の残差と積、非常に高頻度の大域縮約を調査する。現在の作業ではこれらの算法を変更しない。

Intelは、`I_MPI_STATS`または`aps`によるAPS、`mpirun -gtool`による特定MPIランクのプロファイル、`I_MPI_PIN_PROCESSOR_LIST`によるプロセス固定、`I_MPI_TUNING_MODE=auto`による集合通信の自動調整を次の資料で説明している。

- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-15/communication-fabrics-control.html>
- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-16/other-environment-variables.html>
- <https://www.intel.com/content/www/us/en/docs/vtune-profiler/cookbook/2024-0/profiling-mpi-applications.html>
- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-12/environment-variables-for-process-pinning.html>
- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-11/autotuning.html>

## プロファイル実装

プッシュ起動は常に通常計測とし、外部プロファイラを付けずにソルバーを起動する。手動実行では`bench`または`profile`を選ぶ。プロファイル実行はソースやビルド成果物を変更せず、`profile_rank`入力で選択したMPIランク（既定値は0）へ一定時間だけVTuneのホットスポット収集を接続する。ランク0は計算上のホットスポット発見に引き続き有用だが、APSがランク0を非典型と示しているため、代表的な通信の結論には内部ランクやノード境界ランクの追加計測が必要である。

VTuneの完全な結果とParaView用の最終分割ケースは一時的にクラスタのprofile rootへ生成し、自宅サーバーがSSHで直接取得する。ParaView用データは全`processor*`と`occDrivAerStaticMesh.foam`を単一の`paraview-case.tar.zst`にまとめる。自宅側で可読性、サイズ、SHA-256を検証し、Actions runの固定v2成果物ディレクトリ配下へ確定した後だけクラスタ原本を削除する。検証済みレポート、収集状態、JSON形式の事実、上限付きActions要約は、プロファイル成果物とexperiment-metricsの記録に残す。VTune実行ファイルの識別情報と版は、ビルド配備の観測情報で一度だけ管理する。
