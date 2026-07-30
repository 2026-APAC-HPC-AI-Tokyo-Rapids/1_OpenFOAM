# 数値検証サマリー成果物モジュール

## モジュール境界

実装名は`numerical_summary`とする。BigQueryだけを見られない場合にも、数値精度の
異常がないかを1ファイルで確認できる小さなMarkdown成果物を作る。

case archive、ParaView data、solver全文log、profiler出力は既存workflowが必要に応じて
保存するが、このメトリクスmoduleの対象外とする。巨大な成果物を列挙した
`artifact.result.*`群は作らない。

## 成果物の固定仕様

論理名は`numerical_summary`、ファイル名は`numerical-summary.md`に固定する。
GitHub Actionsでは既存の次のartifactへlogsと一緒に格納する。

```text
openfoam-run-log-<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT>
```

run IDとattemptは全環境変数バッチから得られるため、artifact名を別メトリクスへ
複製しない。

サマリーのsectionと項目順は次に固定する。

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

値は[ソルバー状態・数値結果モジュール](07-solver-and-result.md)と
[ケース・メッシュモジュール](04-case-and-mesh.md)が取得したスカラーを、
同じキー名と単位で1行ずつ記す。配列やJSONへまとめない。baseline差、pass/fail、
許容差は書かない。失敗runでは取得済み項目と`run.outcome`、stage exit codeを記し、
取得失敗項目はBigQueryと同じく空文字にする。

UTF-8、LF改行、末尾改行ありとし、各値の行は次の形式に固定する。

```text
- `<key>`: `<canonical scalar value>`
```

冒頭に同じ形式でraw tableの`run`名も記す。section内ではキーのbyte順に並べ、
Markdown生成時刻のような新しい値は加えない。

## 確定メトリクス

```text
artifact.numerical_summary.path
artifact.numerical_summary.sha256
artifact.numerical_summary.size_bytes
```

値はそれぞれ次とする。

```text
artifact.numerical_summary.path = "numerical-summary.md"
artifact.numerical_summary.sha256 = "<lowercase SHA-256>"
artifact.numerical_summary.size_bytes = "<unsigned decimal bytes>"
```

成果物には固有の論理名`numerical_summary`があるため、数字のsub-propertyや
汎用的な`artifact.result.0.*`を使わない。

## 生成・取得・送信順序

1. 各result collectorは取得したバッチを先にBigQueryへ送る。
2. 同じプロセス内で取得済みのスカラーをsummary writerへ渡す。
3. `numerical-summary.md`を最終pathへ直接作成し、flush、closeする。
4. `os.stat()`の`st_size`と、Python `hashlib.sha256`による内容hashを取得する。
5. 上記3つのartifactメトリクスをメモリ上の1バッチとして直ちに送る。
6. workflowがこのファイルをActions artifactへuploadする。

別名の作業ファイル、送信用一時ファイル、spool、queueは作らない。
`numerical-summary.md`自体はユーザーが要求した永続成果物であり、transport用の
一時ファイルではない。hash中に更新されないよう、close後はupload完了まで変更しない。

## 失敗時の扱い

- summary生成は成功・失敗にかかわらずpipeline supervisorのfinalizationで試みる。
- summaryを生成できなくても、既に送信済みのBigQueryメトリクスを巻き戻さない。
- summary生成に失敗してもOpenFOAM実験の成否は変更しない。
- solver失敗runでも、finalizationが実行できればpartial summaryを作る。

## 採用しない値

| 値 | 理由 |
|---|---|
| `artifact.actions_url` | repositoryと`GITHUB_RUN_ID`から後で作れる |
| Actions artifact名 | 保存済み環境変数から決定できる |
| case/result archiveのhash | 物理的精度の確認には大きすぎ、数値サマリーで目的を満たす |
| directory hash | 対象範囲とmetadata差が曖昧になり、このmoduleでは不要 |
| `artifact.result.*` | 固有の対象が数値サマリー1つに確定している |
