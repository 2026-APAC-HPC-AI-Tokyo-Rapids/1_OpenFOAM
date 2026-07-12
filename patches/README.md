# OpenFOAM patches

OpenFOAM と ThirdParty source に適用するローカル差分です。CI は source 展開後に
`patches/*.patch` を名前順で全件適用します。ここに patch を追加・変更・削除した場合は、
生成済み build archive と互換でないため `[require-build]` を付けてフルビルドしてください。

| ファイル | 目的 |
| --- | --- |
| `allwmake-timestamps.patch` | `Allwmake -log` の各出力行に時刻を付与し、遅延箇所を追跡可能にする |
| `cgal-v6.1.1.patch` | OpenFOAM が参照する CGAL version を 6.1.1 に更新する |
| `icx-cpp-preprocessor.patch` | Icx 用 rule の C preprocessor を `icx -E` にする |

patch は対象の OpenFOAM version に依存します。version を上げる場合は、各 patch が正しく
適用できることと、変更後に full build が完走することを確認してください。
