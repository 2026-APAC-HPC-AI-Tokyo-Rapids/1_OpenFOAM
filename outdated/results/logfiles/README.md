# 旧 case のログ

過去の OpenFOAM case 実行で出力された工程別ログと、比較に用いた `controlDict` の控えです。

| 種別 | 内容 |
| --- | --- |
| `10_*.log` ～ `50_*.log` | `decomposePar`、mesh 操作、`potentialFoam`、`simpleFoam` の順の実行ログ |
| `Allrun` | 当時の case 実行手順 |
| `controlDict*` | 出力の有無などを比較するための設定ファイル |

これらは再現性を保証するケース一式ではなく、診断用の記録です。現在の CI は OpenFOAM に付属する
`motorBike` tutorial を別の runtime tree 上で実行します。
