# 次の検証候補

| 優先度 | 対応 | 見込み短縮 | 判断理由 |
|---:|---|---:|---|
| 1 | ThirdParty成果物を単一archiveでcache | 4分から5分 | 小fileのbuildとinstallをまとめて省略できる |
| 2 | `CCACHE_SLOPPINESS=system_headers`のA/B | 数十秒から数分 | 固定toolchain headerのLustre検証を減らせる可能性がある |
| 3 | `CCACHE_NOSTATS=1`のA/B | 0秒から30秒 | cache統計のmetadata更新を削減できる |
| 4 | 160、200、240並列のA/B | 0分から2分 | I/O待ちをさらに隠せる可能性がある |
| 5 | compiler生成dependencyへ移行 | 数十秒から1分 | `wmkdepend`起動と独立走査を削減できる |
| 6 | OpenFOAM build tree cache | 6分から8分 | dependency、object、link結果を再利用できる |

ThirdParty archive cacheが、効果、正しさ、workflowの複雑さのバランスに最も優れる。cache keyにはOpenFOAM、依存library、compiler、MPI、ABI、patchのhashを含め、RPATHと再配置可能性を検証する必要がある。
