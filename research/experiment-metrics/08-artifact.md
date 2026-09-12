# 数値検証サマリー成果物モジュール

## モジュール境界

実装上の識別名は `numerical_summary` とする。本モジュールは、BigQueryを参照できない環境であっても、数値精度の異常が発生していないかを即座に確認できるよう、単一の小さなMarkdown形式の検証サマリー成果物を生成する。

ケースアーカイブ（case archive）、ParaView可視化データ、ソルバーの完全なログファイル、およびプロファイラ出力については、既存のワークフローが必要に応じて保存を制御するが、本メトリクス収集モジュールの管轄外とする。巨大な出力ファイルを網羅的に列挙した `artifact.result.*` 系統のメトリクス群は作成しない。

## 成果物の固定仕様

成果物の論理識別名は `numerical_summary`、ファイル名は `numerical-summary.md` に固定する。GitHub Actions環境では、既存の以下のログアーカイブ成果物内に他のログファイル群とともに格納する。

```text
openfoam-run-log-<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT>
```

実行ID（Run ID）および実行試行回数（Attempt）は全環境変数バッチから取得可能であるため、成果物アーカイブ名を別の個別メトリクスとして重複記録することはしない。

サマリー文書内のセクション構成および見出しの順序は以下のように固定する。

```text
# Numerical validation summary
## Run status
## Case and mesh identity
## Aerodynamic coefficients
## Boundary flux
## Wake probes
## Final field ranges
## Continuity
## Final linear-solver state
```

記載する値は、[ソルバー状態・数値結果モジュール](07-solver-and-result.md)および[ケース・メッシュモジュール](04-case-and-mesh.md)が取得したスカラー値を、同一のキー名および単位を用いて1行ずつ記録する。配列構造やJSON形式への集約は行わない。また、ベースラインとの差分、合否判定（pass/fail）、許容閾値の記載は行わない。実行失敗時（failed run）は、取得完了している項目、`run.outcome`、およびステージの終了コードを記載し、取得できなかった項目についてはBigQueryと同様に空文字として出力する。

ファイル形式はUTF-8エンコーディング、LF改行、末尾改行ありとし、各データ行のフォーマットは以下のように統一する。

```text
- `<key>`: `<canonical scalar value>`
```

文書の冒頭には、同一のフォーマットでBigQueryの生データテーブル（raw table）における `run` 識別子を記載する。各セクション内ではキーのバイト順序に従って昇順ソートし、Markdown生成時刻等の動的な追加情報は付与しない。

## 確定メトリクス

```text
artifact.numerical_summary.path
artifact.numerical_summary.sha256
artifact.numerical_summary.size_bytes
```

各メトリクスの値は以下のように定義される。

```text
artifact.numerical_summary.path = "numerical-summary.md"
artifact.numerical_summary.sha256 = "<lowercase SHA-256>"
artifact.numerical_summary.size_bytes = "<unsigned decimal bytes>"
```

本成果物には `numerical_summary` という一意の論理名が定義されているため、数値インデックスを用いたサブプロパティや汎用的な `artifact.result.0.*` のような命名は採用しない。

## 生成・取得・送信の順序

1. 各結果コレクターが、取得したデータバッチを先行してBigQueryへ送信する。
2. 同一プロセス内で取得済みのスカラー値群をサマリー生成処理（summary writer）へ渡す。
3. 最終出力先パスへ `numerical-summary.md` を直接作成し、明示的にflushおよびcloseを実行する。
4. `os.stat()` からファイルサイズ（`st_size`）を取得し、Pythonの `hashlib.sha256` によりファイル内容のSHA-256ハッシュを計算する。
5. 上記3つの成果物メトリクスをメモリ上の単一バッチとして直ちにBigQueryへ送信する。
6. GitHub Actionsワークフローが、本ファイルをActionsの成果物としてアップロードする。

別名の一時作業ファイル、送信用テンポラリファイル、スプール領域、キュー等は介在させない。`numerical-summary.md` 自体は永続的に保持すべき正規の成果物であり、転送用の一時ファイルではない。ハッシュ計算中に内容が書き換わることを防ぐため、ファイルclose後はアップロード完了に至るまで変更を加えない。

## 失敗時の扱い

- サマリー生成処理は、パイプラインの成否（成功・失敗）にかかわらず、パイプライン監視処理の終了処理（finalization）において必ず試行する。
- サマリー生成が万一失敗した場合であっても、すでに送信済みのBigQueryメトリクスを取り消す（ロールバックする）ことはしない。
- サマリー生成自体の失敗によって、OpenFOAM実験全体の成否判定を変更することはない。
- ソルバーが異常終了した実行であっても、終了処理が実行可能な状態であれば部分的なサマリー（partial summary）を作成する。

## 採用しない値

| 除外項目 | 除外理由 |
|---|---|
| `artifact.actions_url` | リポジトリ名および `GITHUB_RUN_ID` から後から一意に導出可能であるため |
| GitHub Actions成果物名 | 記録済みの環境変数から一意に決定可能であるため |
| ケースおよび結果アーカイブ全体のハッシュ値 | 数値精度の健全性確認にはデータサイズが大きすぎ、数値サマリーで目的を十分に達成できるため |
| ディレクトリ全体のハッシュ値 | 対象範囲の境界やメタデータの微小差が曖昧になり、本モジュールのスコープを超えるため |
| `artifact.result.*` | 記録対象が単一の数値サマリーファイルに確定しているため |
