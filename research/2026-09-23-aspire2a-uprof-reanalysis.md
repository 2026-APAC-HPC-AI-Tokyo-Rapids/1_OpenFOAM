# ASPIRE 2A AMD uProf rawセッションの再解析（2026-09-23）

## 対象と手順

- 公式`occDrivAerStaticMesh-65M`、OpenFOAM.com v2512、`simpleFoam`、4ノード512 MPI rank、150反復の別々のprofile実行を用いた。`assess`は[Actions 35737087579](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/35737087579)、`data_access`は[Actions 35740961947](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/35740961947)。公式parserはそれぞれ`STATUS: VALID`、149/150計測反復と判定した。双方の実行が使用したビルドアーカイブは同一inodeかつSHA-256 `f76fb0a924c25562ab0bd345f0bfffcf3dad7d78f1099b88fef81cc8cb453f4e`である。
- 元のprofile archiveはhome-labの`/hdd_raid/samba/net_share/openfoam-artifacts/{35737087579,35740961947}/aspire2a/*/profile-raw.tar.zst`に保存されている。32 rank（各ノードでlocal rank 0、16、…、112）の独立uProf 5.3.521.0セッションをASPIRE login nodeへ一時展開し、各セッションを`AMDuProfCLI report --input-dir <session> --host <host> --detail --cutoff 0 --show-event-count`で再生成した。新しいsolverジョブは実行していない。
- 元の`--cutoff 30`報告では、`data_access`の各rankで全process推定サイクルの41.9～49.5%しか`FUNCTION SUMMARY`に載っていなかった。再生成した全行報告では32 rankすべて100%となった。3関数について元報告が保持していた推定サイクルは、全行報告比でGauss–Seidel 82.4%、`residual` 82.1%、`Amul` 67.4%だった。
- `BINARY FILE NOT FOUND`で表示された`libOpenFOAM.so!0x...`を、その実行に使ったビルドの`libOpenFOAM.so`の`nm -D -C -S --defined-only`から得た関数の開始アドレスとサイズに照合した。対象は`GaussSeidelSmoother::smooth`の2 overload、`lduMatrix::residual`の2 overload、`lduMatrix::Amul`の1関数である。下表は対応する命令位置の推定イベント数を、各run内の32 rankで合算した値である。
- IPCは`RETIRED_INST / CYCLES_NOT_IN_HALT`、分岐ミス率は`RETIRED_BR_INST_MISP / RETIRED_BR_INST`、需要補充頻度は6種類の`L1_DEMAND_DC_REFILLS_*`合計を`L1_DC_ACCESSES_ALL`で割って算出した。イベント数は異なるsampling間隔から復元された推定値であり、実測時間や厳密な全命令カウントではない。

## 関数別の再解析結果

| 関数 | `assess`サイクル比 | `data_access`サイクル比 | IPC（`assess` / `data_access`） | `assess`分岐ミス率 |
|---|---:|---:|---:|---:|
| `GaussSeidelSmoother::smooth` | 14.93% | 14.62% | 0.877 / 0.885 | 6.08% |
| `lduMatrix::residual` | 10.96% | 10.96% | 0.482 / 0.476 | 0.01% |
| `lduMatrix::Amul` | 6.00% | 5.92% | 0.595 / 0.596 | 0.02% |

サイクル比は32個の対象rankの推定サイクル合計を分母とする。MPIの待機を含むsolver全体のwall時間比や、全512 rankの比率ではない。`data_access`のrank別サイクル比の範囲は、上から順に13.63～17.70%、9.82～12.20%、5.12～6.79%。Gauss–Seidelの分岐ミス率はrank別中央値6.05%、範囲2.84～8.33%で、推定ミス数は32 rank合計約183.7億件（計測間隔50万からの復元、約36,735サンプル）である。他2関数の分岐ミスイベントはそれぞれ約12、20サンプルのみなので、細かな率は評価しない。

| 関数 | L1アクセス1000件当たり需要補充 | 補充元：同一coreのL2 | 補充元：local DRAM/IO | L2 DTLBミス／L1アクセス100万件 |
|---|---:|---:|---:|---:|
| `GaussSeidelSmoother::smooth` | 5.74 | 95.04% | 0.87% | 110 |
| `lduMatrix::residual` | 6.11 | 84.10% | 13.46% | 203 |
| `lduMatrix::Amul` | 7.99 | 79.26% | 14.32% | 192 |

補充元の割合は`data_access`で得た6種類の`L1_DEMAND_DC_REFILLS_*`推定数の合計を分母とする。全メモリアクセス中の割合や実DRAM転送量ではない。local DRAM由来の割合は、全32 rankで`residual`と`Amul`がGauss–Seidelより高い。ただしGauss–Seidelの当該イベントはrank当たり最低5サンプル程度で、個々のrankの細かな値は不安定である。ハードウェアprefetchによるDRAM転送は、この需要補充元の表だけでは評価できない。

元ビルドの逆アセンブルとイベント位置を照合すると、`residual`のface更新ループは関数内推定サイクルの約69%、`Amul`では約75%を占めた。一方、local DRAM由来の需要補充イベントは、それぞれ約91%、93%が連続配列を読む対角ループの命令位置付近に帰属した。`Amul`の採取点には`hasLowerCSR()`の`else`側にあるfaceベース更新ループが含まれる。Gauss–Seidelは行ごとの参照・更新ループに推定サイクルのほぼ全てが集中する。イベントの命令位置にはsampling skidがあり、特定のload命令が原因だと断定するためのIBS精度はない。

## 判断と残る情報

2つの独立したPMC runで3関数の順位、サイクル比、IPCは近い。Gauss–Seidelは最も大きな対象で、行ごとの不規則参照と分岐が調査候補になる。`residual`と`Amul`では、サイクルを多く消費するface更新と、DRAM由来の需要補充が集中する対角ループを分けて検討する。サイクル比だけからsolverの短縮率は見積もれない。

保存済みセッションにはIBSによる個別load latency、uncoreによる実DRAM帯域、計算フェーズのrank別wall時刻がない。したがってASPIREでのDRAM帯域飽和や、後のPMPI時系列で見つかった`normFactor`到着遅れの局所原因は、この再解析だけでは判定できない。今回のPMCは旧`(4 128)`分割で採取し、PMPI時系列は後のNUMA-aware`(4 2 4 16)`分割なので、rank 208を含む同一番号の挙動も直接対応付けない。
