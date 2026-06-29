# 調査結果

## 結論

OpenFOAM-v2412のウォームビルドは、コンパイル計算よりもLustre上のpage faultとmetadata lockに強く制約されている。ccache hit率は約99.5%だが、短命プロセスによるファイル走査、依存生成、コピー、installが残り、120並列時にはkernelのspin lock待ちが支配的になる。

735MBのrawデータを生成したDWARF call graph方式は撤去した。実行時間への有意な影響がなく、artifactも約28MBだったframe-pointer方式はCIに残している。

- Allwmake出力の秒単位タイムスタンプ
- 5秒間隔の`perf stat -d`
- 1Hz、frame-pointer call graphの`perf record`
- `/usr/bin/time -v`によるprocess tree全体のresource usage

## 測定環境

| 項目 | 構成 |
|---|---|
| OpenFOAM | v2412 |
| Compiler | Intel oneAPI Icx 2025.1.1 |
| MPI | Intel MPI 2021.15 |
| ABI | DP / Int64 |
| 並列数 | 120 |
| Build directory | `/dev/shm`上の`mktemp`ディレクトリ |
| ccache | `/fast/pj26000080/ccache_cache_dir`、最大50GB |
| Linker | GNU ld |

## 工程時間

Run [28364738522](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/28364738522)のAllwmake実時間は14分02.80秒だった。

| 工程 | 時間 |
|---|---:|
| ThirdParty | 5分42秒 |
| OpenFOAM libraries | 5分30秒 |
| OpenFOAM applications | 1分54秒 |
| OpenFOAM modules | 53秒 |

ThirdPartyの内訳は時刻付きログの各見出し間から算出した概算値である。

| ThirdParty工程 | 時間 |
|---|---:|
| Scotch / PT-Scotch | 1分36秒 |
| METIS | 15秒 |
| Boost | 1分21秒 |
| CGAL install | 2秒 |
| FFTW | 1分29秒 |
| ADIOS2 | 57秒 |

## Resource usage

| 指標 | 値 |
|---|---:|
| User CPU | 689.88秒 |
| System CPU | 23,165.86秒 |
| Wall clock | 842.80秒 |
| 平均CPU使用率 | 2,830% |
| Major page faults | 6,904 |
| Minor page faults | 64,078,620 |
| Voluntary context switches | 1,020,672 |
| Involuntary context switches | 1,442,116 |
| File system inputs | 1,020,216 |
| File system outputs | 167,320 |

System CPUは全子プロセスの累計である。user CPUの約34倍あり、kernel側の待機とmetadata処理が大きい。

## perf結果

Run [28363430866](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/28363430866)とRun [28364738522](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/28364738522)では、次のLustre client処理が確認された。

- `native_queued_spin_lock_slowpath`
- `ll_fault`
- `ll_cl_add` / `ll_cl_remove`
- `ll_inode_permission`
- `ldlm_*`
- `ptlrpc_*`

Run [28362137687](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/28362137687)では、spin lock中のprocess名は次の比率だった。

| Process | Samples |
|---|---:|
| `sh` | 35.06% |
| `cp` | 20.20% |
| `sed` | 11.76% |
| `mkdir` | 5.01% |
| `ccache` | 4.25% |
| `wmkdepend` | 3.78% |
| `makeTargetDir` | 3.26% |
| `clang` | 2.34% |

実コンパイルだけではなく、shell、コピー、依存生成、ディレクトリ操作の総量がLustre metadata競合を引き起こしている。

## 注意事項

- genkai0001は共有ノードであり、wall timeのrun間変動が大きい。
- perf比率はサンプリング結果であり、絶対的なCPU使用率ではない。
- `time -v`のfile system inputs/outputsはrusage counterであり、byte数ではない。
- ccache hit率約99.5%は個別build統計から算出した。
