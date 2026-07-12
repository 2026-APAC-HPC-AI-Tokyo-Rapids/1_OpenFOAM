# 調査資料

現在の OpenFOAM CI のビルド性能に関する設計判断と計測記録です。実行性能や CFD 結果の
妥当性を評価する資料ではありません。

[`build-performance/`](build-performance/README.md) には、現在のビルド構成、比較実験の
方針、過去の試行から得た判断をまとめています。workflow や patch、ccache、並列度を変更する
前に、特に `measurement-policy.md` を確認してください。
