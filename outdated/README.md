# 過去の実験資料

このディレクトリは、現在の GitHub Actions / Genkai workflow より前に行った Slurm 環境での
OpenFOAM 実験を保存したものです。現行 CI の入力としては使われず、スクリプト中の絶対パス、
module、OpenFOAM version は現在の環境と一致しない場合があります。

| 場所 | 内容 |
| --- | --- |
| [`build/`](build/README.md) | source 取得・Slurm build 提出用の旧 script |
| [`run/`](run/README.md) | tutorial 実行を Slurm に提出する旧 script |
| [`results/`](results/README.md) | 過去の job 出力と solver log |

再利用する場合は、パスや scheduler directive を現在の環境向けに見直してください。新しい運用は
ルート README と [`.github/workflows/genkai.yml`](../.github/workflows/genkai.yml) を正とします。
