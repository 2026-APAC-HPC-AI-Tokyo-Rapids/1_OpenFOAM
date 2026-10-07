# Tokyo Rapids with RIKEN OpenFOAM 提出物ガイド

本ディレクトリは競技提出物の準備用ディレクトリです。内容が空の結果ファイルや辞書ファイルのプレースホルダー、およびGitHub Actionsの実行経路と一致しない過去の検証用スクリプトは削除して整理されています。実際の提出にあたっては、選定した実実行（run）の成果物、およびその実行コミットにおけるスクリプトから以下の内容を揃えます。

公式の性能評価指標は、2ステップ目以降の`Average wall-clock time per time step`（秒単位、小さいほど高速）です。採点対象はGadi（`normalsr`）またはASPIRE-2Aの4ノード環境であり、玄界での計測結果は参考資料として明記します。1ノード、2ノード、4ノード環境においてそれぞれ40、80、150反復を実行し、同一クラスタ・同一ビルド・同一最適化条件による通常ベンチマークからスケーリング性能を示します。なお、プロファイル計測の所要時間はベンチマーク結果に混入させません。

| 提出項目 | 実実行における正本データ |
| --- | --- |
| ビルド手順・`WM_*`・コンパイラ/MPI構成 | 各実行の`control/build-sidecar.json`、`control/build-raw/`、および実行コミットのビルドスクリプト |
| 全準備工程とMPI設定 | 実行コミットの共通`run-openfoam.sh`・`prepare-openfoam-case.sh`、クラスタ別バッチスクリプト（PJM/PBS）、`logs/`および各ステージの引数（argv） |
| 実際に使用した入力ファイル群 | `source/mesh/decomposeParDict`、`controlDict`、`caseDefinition`（公式の固定入力は`source/workload/`） |
| ソルバーログ・公式判定結果 | `logs/solver.log`、`results/result.txt` |
| 抗力係数（$C_d$） | `results/coefficient.dat`（取得元パスは`results/coefficient-source.json`に記録。$C_d$に対する独自の合否判定基準は設けない） |
| スケーリングデータ | 選定した1/2/4ノードの実行結果から再生成したテキスト表（コミットハッシュ、GitHub Actions実行、生成果物への参照を含む） |
| プロファイル解析結果 | 選定したプロファイル実行におけるホットスポット一覧と収集ステータス（通常ベンチマークとは区別して提示） |

成果物の保存先は、自宅サーバー（home-lab）の`/hdd_raid/samba/net_share/openfoam-artifacts/<Actions run id>/<cluster>/`です。固定成果物である`artifact-manifest.json`および`run-artifacts.tar.zst`から必要なテキストデータを抽出します。なお、メッシュデータ本体、`processor*`ディレクトリ、実行バイナリ、完全なインストールツリー、VTuneのバイナリ結果は提出物に含めません。

選定した3つの固定成果物ディレクトリを指定してスケーリング表を再生成し、未作成の出力先ディレクトリへテキストを保存します（URLおよびディレクトリパスは、実際に選定した実行のものに置き換えてください）。

```bash
uv run --project experiment-metrics python -m experiment_metrics.scaling --run URL1 ARTIFACT_DIR1 --run URL2 ARTIFACT_DIR2 --run URL4 ARTIFACT_DIR4 --output-dir submission/openfoam
```

スクリプトを実行すると、`scaling.txt`および`{1,2,4}node/<run_id>/`が出力されます。ここには各実行のログ、結果、実使用入力、ビルドおよび実行の来歴情報（provenance）が含まれます。このツールは、同一コミット・同一クラスタ・同一ビルド・同一ワークロードによる通常ベンチマークのみを受け付け、ノード数に依存する反復回数、ランク数、既定の輸送特性（transport）の差分を表中に明示します。ASPIRE-2AのBonus（multiLevel）では、ノード数ごとに宣言した`domains`（1ノード`(2 4 16)`、2ノード`(2 2 4 16)`、4ノード`(4 2 4 16)`）だけを入力の差分として認め、表の分割欄に実際の`domains`を表示します。なお、ステップ間の標準偏差を複数回実行間の測定ばらつきとして解釈しないよう注意してください。提出する実行スクリプトは表に記載されたコミットから取得し、`scripts/`、対象の`platforms/<cluster>/`、`.github/workflows/`のテキストを添付します。

最終審査のプレゼンテーションはQwenとOpenFOAMを合わせた単一の発表スライドで構成し、発表15〜20分、質疑応答10分で実施されます。OpenFOAMタスクは50点で、2026-09-25の追補（`tasks/README.md`のR4）により、審査が35点（Basic 20点＋Bonus 15点）、Basicの4ノード性能と主催者の再実行が15点です。メッシュ分割手法、ランク数、各種係数の選定理由、最適化の意図、同一条件における複数回実行の改善度合いと測定ばらつき、ならびに1/2/4ノードのスケーリング特性について説明します。公式ルールの詳細は[ルール対応表](../research/official-rules.md)を参照してください。

以下に公式の推奨ディレクトリ配置例を示します（ジョブスケジューラのスクリプト拡張子は使用クラスタに合わせて調整します）。

```
submission/
  ├── README.txt                  # 使用した環境モジュール、および再ビルド手順の記録（再ビルドを実施した場合）
  ├── build/
  │   └── build.sh                # 再ビルド用スクリプト（再ビルドを実施した場合のみ）
  ├── run/
  │   ├── 1node.sbatch            # simpleFoam単体ではなく全準備工程を含む実行スクリプト
  │   ├── 2node.sbatch
  │   └── 4node.sbatch
  ├── dicts/
  │   ├── caseDefinition
  │   ├── decomposeParDict
  │   └── controlDict
  ├── results/
  │   ├── 1node/                  # decomposeParを含む各種テキストログ
  │   ├── 2node/
  │   └── 4node/
  │       ├── simpleFoam.log
  │       └── coefficient.dat     # postProcessing/forceCoeffsAllから取得したCd
  ├── scaling/
  └── analysis/                   # プロファイル解析の考察（任意）
```
