# Genkai における OpenFOAM ビルドの調査記録

このディレクトリは、Genkai self-hosted runner で OpenFOAM v2412 をビルドするために行った試行と、そこから得られた運用上の結論を記録する。対象は **ビルド** だけであり、OpenFOAM のソルバ性能、MPI 実行性能、数値結果の妥当性は扱わない。

現在の目的は、最短時間の単発記録を作ることではない。再実行でき、失敗時に原因を追え、共有環境の揺らぎを区別できるビルドを保つことである。

## この調査で確立したこと

- OpenFOAM v2412 を Intel oneAPI と Intel MPI で一貫してビルドできる。
- ビルド tree は `/dev/shm` に置き、ソース archive と ccache の永続領域は runner の共有領域を使う構成が実用的である。
- ccache が warm のときは hit 率が約 99.5% まで上がる。しかし Allwmake 全体は依存関係生成、link、install、ファイル走査を続けるため、コンパイル cache だけでは時間を固定できない。
- `Allwmake -j 120`、queue なし、既定 GNU linker が現在の採用構成である。
- 同一条件でも全体時間は大きく揺れる。比較対象となる build 部分は約 14 分台から 23 分台まで観測されており、単発の wall time を最適化の根拠にしない。

構成の詳細は [current-build.md](current-build.md)、試行の記録と判断は [trial-record.md](trial-record.md)、今後の測定方法は [measurement-policy.md](measurement-policy.md) を参照する。

`research/**` だけを変更する push は、[workflow](../../.github/workflows/genkai.yml) では CI 起動の対象外である。
