# 次の最適化候補

| 優先度 | 対応 | 見込み短縮 | 注意点 |
|---:|---|---:|---|
| 1 | ThirdParty成果物を単一archiveでcache | 4分40秒から5分20秒 | RPATHと再配置を検証する |
| 2 | `CCACHE_SLOPPINESS=system_headers`のA/B | 数十秒から数分 | toolchain更新時にnamespace更新が必要 |
| 3 | `CCACHE_NOSTATS=1`のA/B | 0秒から30秒 | 自動cleanupが停止する |
| 4 | 160、200、240並列のA/B | 0分から2分 | Lustre競合悪化の可能性がある |
| 5 | compiler生成dependencyへ移行 | 数十秒から1分 | wmake規則の変更が必要 |
| 6 | OpenFOAM build tree cache | 6分45秒から7分45秒 | CIで毎回buildする意味が変わる |

## Cache戦略

ThirdPartyの5分42秒を単一archiveの展開へ置き換える案が、効果と変更範囲のバランスに優れる。cache keyにはOpenFOAM、依存ライブラリ、compiler、MPI、ABI、patchのhashを含める。

ccacheは`.o`を既にcacheしているが、OpenFOAMが`wmkdepend`で別生成する`.dep`とリンク結果はcacheしない。これらを再利用するにはcompiler生成dependencyへの移行、またはbuild tree cacheが必要になる。

## ccache検証緩和

固定toolchainをnamespaceで明示したうえで`CCACHE_SLOPPINESS=system_headers`を使えば、system headerのmanifest検証を削減できる。ただしtoolchain更新時のnamespace変更を運用上必須とする。
