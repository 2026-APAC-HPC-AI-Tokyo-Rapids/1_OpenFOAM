# OpenFOAMビルド性能調査

OpenFOAM-v2412のgenkai向けビルドについて、工程時間、resource usage、Lustre競合、最適化実験を記録する。

- [調査結果](findings.md)
- [実験結果](experiments.md)
- [設計変更の履歴](design-history.md)
- [今後の検証候補](recommendations.md)
- [測定値](measurements.tsv)

`research/`だけを変更したpushでは、OpenFOAMのCIを起動しない。
