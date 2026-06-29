# OpenFOAMビルド性能調査

## 結論

OpenFOAM-v2412のウォームビルドは、コンパイル計算よりもLustre上のpage faultとmetadata lockに強く制約されている。
ccache hit率は約99.5%だが、短命プロセスによるファイル走査、依存生成、コピー、installが残り、120並列時にはkernelのspin lock待ちが支配的になる。

重い`perf record`は調査後に撤去した。オーバーヘッドが確認されなかった次の軽量計測はCIに残している。

- Allwmake出力の秒単位タイムスタンプ
- 5秒間隔の`perf stat -d`
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

ThirdPartyの内訳は次の通り。時刻付きログの各見出し間から算出した概算値である。

| ThirdParty工程 | 時間 |
|---|---:|
| Scotch / PT-Scotch | 1分36秒 |
| METIS | 15秒 |
| Boost | 1分21秒 |
| CGAL install | 2秒 |
| FFTW | 1分29秒 |
| ADIOS2 | 57秒 |

## Resource usage

同じrunの`time -v`結果を使用した。

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

System CPUは全子プロセスの累計であり、wall timeとの直接比較値ではない。それでもuser CPUの約34倍あり、kernel側の待機とmetadata処理が大きいことを示す。

## perf結果

低頻度call graphを取得したRun [28363430866](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/28363430866)とRun [28364738522](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/28364738522)では、次のLustre client処理が確認された。

- `native_queued_spin_lock_slowpath`
- `ll_fault`
- `ll_cl_add` / `ll_cl_remove`
- `ll_inode_permission`
- `ldlm_*`
- `ptlrpc_*`

9Hz、call graphなしで取得したRun [28362137687](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/28362137687)では、spin lock中のprocess名は次の比率だった。

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

## 実験結果

### 並列数

各条件を2回実行した中央値。

| 並列数 | 中央値 |
|---:|---:|
| 30 | 19分46秒 |
| 60 | 18分21秒 |
| 90 | 20分17秒 |
| 120 | 16分26秒 |

120並列は60並列より約10.4%速かった。System CPUは増えるが、Lustre待ちを並列処理で隠す効果が勝った。

### ccacheのtmpfs配置

| 方式 | 中央値 | 判定 |
|---|---:|---|
| `/fast`の既定cache | 16分26秒 | 基準 |
| 毎回tmpfsへコピー | 24分26秒 | 不採用 |
| コピー済みtmpfs | 16分09秒 | 改善1.7%、誤差範囲 |

cache全体のコピーには約1分22秒かかり、コピー済みでも有意な改善はなかった。ccache storageだけがボトルネックではない。

### profiler overhead

| Run | 構成 | AllwmakeまたはBuild step |
|---:|---|---:|
| 28356014551 | profilerなし | Allwmake 13分59.64秒 |
| 28356789505 | profilerなし | Allwmake 22分07.85秒 |
| 28363430866 | `perf record`、DWARF call graph | Allwmake 13分49.00秒 |
| 28364738522 | `perf record`、frame-pointer call graph | Allwmake 14分02.80秒 |
| 28365703413 | 最終profiling構成 | Build step 14分58秒 |

共有ノードの変動幅よりprofiler有無の差が小さく、有意なwall time増加は確認されなかった。ただしDWARF call graphはrawデータ735MB、frame-pointer方式でも約138MBを生成したため、継続利用には重いと判断して`perf record`を撤去した。

## 推奨する次の検証

| 優先度 | 対応 | 見込み短縮 | 注意点 |
|---:|---|---:|---|
| 1 | ThirdParty成果物を単一archiveでcache | 4分40秒から5分20秒 | RPATHと再配置を検証する |
| 2 | `CCACHE_SLOPPINESS=system_headers`のA/B | 数十秒から数分 | toolchain更新時にnamespace更新が必要 |
| 3 | `CCACHE_NOSTATS=1`のA/B | 0秒から30秒 | 自動cleanupが停止する |
| 4 | 160、200、240並列のA/B | 0分から2分 | Lustre競合悪化の可能性がある |
| 5 | compiler生成dependencyへ移行 | 数十秒から1分 | wmake規則の変更が必要 |
| 6 | OpenFOAM build tree cache | 6分45秒から7分45秒 | CIで毎回buildする意味が変わる |

## 注意事項

- genkai0001は共有ノードであり、wall timeのrun間変動が大きい。
- perf比率はサンプリング結果であり、絶対的なCPU使用率ではない。
- `time -v`のfile system inputs/outputsはrusage counterであり、byte数ではない。
- ccache hit率約99.5%は個別build統計から算出した。
- profilingのraw artifactはGitHub Actions側の保持期限に従い削除される。
