# Workflows

## `genkai.yml`

Genkai 上で OpenFOAM v2606 を提供し、`motorBike` tutorial を smoke test する workflow
です。処理は三つの job に分かれます。

| Job | 役割 |
| --- | --- |
| `build` | source archive の取得、patch 適用、Allwmake、成果物の保存または再利用 |
| `provision` | build archive から source を除いた実行用 tree を作成 |
| `run` | PJM job として並列メッシュ生成・`simpleFoam` を実行し、結果を圧縮 |

push では先頭コミットメッセージに `[require-build]` がある場合だけ `build` job が
フルビルドを行います。それ以外は第一親の履歴から利用可能な成功アーカイブを探します。
手動実行では `require_build` 入力で選択します。

workflow の共有パス、依存 version、並列度は YAML の `env` に集約しています。変更時は
archive の互換性を確認し、原則として `[require-build]` を付けた commit で検証してください。
