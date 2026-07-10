# 次の変更をどう測るか

## 変更前に固定するもの

性能比較では、少なくとも次を固定または記録する。

- workflow の commit SHA と patch の内容
- OpenFOAM、ADIOS2、CGAL、oneAPI、MPI の version
- `OPENFOAM_BUILD_PARALLELISM`、queue、linker、ccache の設定
- run の開始時刻、job / step 時間、成功・失敗
- `ccache --show-stats` の hit 率と call 数

測る対象は一度に一つだけ変える。例えば並列度を変える run では、ccache の配置や linker を同時に変えない。

## 最低限の実験手順

1. 基準構成を少なくとも 2 回実行し、ばらつきを先に見る。
2. 変更構成を同じ回数だけ実行する。
3. 可能なら基準・変更・基準・変更の順に交互実行し、時間帯の偏りを減らす。
4. Actions の `Build OpenFOAM` 時間と artifact の `allwmake.log` を比較する。
5. ccache hit 率や miss 数が変わっていれば、wall time と独立の要因として記録する。
6. 成功したかだけでなく、生成 archive と log が期待どおり残ることを確認する。

中央値と最小・最大を併記する。最小値だけを採用根拠にしない。

## 次に検討する候補

優先順位は「短縮できそうか」だけでなく、正しさと保守負担を含めて決める。

| 候補 | 期待 | 注意点 |
|---|---|---|
| ThirdParty の成果物を version / compiler / patch hash で archive cache 化 | full build の固定費を大きく省ける可能性 | ABI、RPATH、再配置可能性の検証が必要 |
| 160 以上の並列度 | I/O 待ちを隠せる可能性 | shared runner では悪化もあり得る。複数回比較が必須 |
| `CCACHE_SLOPPINESS=system_headers` | header 検証を減らせる可能性 | cache 正確性の影響を明示して、専用の A/B とする |
| `CCACHE_NOSTATS=1` | stats 更新を減らせる可能性 | 観測性を失うため、通常運用に入れる前に効果を確認する |
| OpenFOAM build tree の再利用 | dependency / object / link を省ける可能性 | invalidation 条件が複雑で、誤った再利用を避ける設計が必要 |

逆に、ccache 全体を run ごとに tmpfs へコピーする案と、lld を常用する案は、現時点では再試行の優先度を下げる。前者はコピーコスト、後者は full build の互換性が判断を覆すほど改善されない限り、現行構成を複雑にするためである。

## 調査の範囲外

このディレクトリでは、以下を性能結論として扱わない。

- OpenFOAM solver の実行時間やスケーリング
- MPI 通信性能、ノード間性能、GPU 利用
- 計算結果の物理的・数値的な正しさ
- Genkai 全体の混雑状況の断定

最後の項目は特に重要である。Actions のログだけでは共有システム全体の負荷を直接観測できない。build が遅い場合は、まず workflow 内の工程と cache 状態を確認し、それでも説明できない遅延を「共有環境による変動の可能性」として記録する。
