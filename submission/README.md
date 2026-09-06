# Tokyo Rapids with RIKEN OpenFOAM SUBMISSION

このディレクトリは提出準備用です。空の結果・辞書プレースホルダーと、Actions経路に一致しない練習用スクリプトは削除しました。提出時は選択したrunの成果物と、そのcommitのスクリプトから下記の内容を揃えます。

公式性能指標は2ステップ目以降の`Average wall-clock time per time step`（秒、小さいほど高速）。採点対象はGadi `normalsr` またはASPIRE-2Aの4ノードで、玄界の結果は参考資料と明記します。1/2/4ノードで40/80/150ステップを実行し、同cluster・build・最適化条件の通常benchからscalingを示します。profileの時間をbenchへ混ぜません。

| 提出内容 | 実runの正本 |
| --- | --- |
| build手順・WM_*・compiler/MPI | runの`control/build-sidecar.json`、`control/build-raw/`、実行commitのbuildスクリプト |
| 全準備工程とMPI設定 | 実行commitの共通`run-openfoam.sh`・`prepare-openfoam-case.sh`、クラスタ別PJM/PBS、`logs/`とstage argv |
| 実使用入力 | `source/mesh/decomposeParDict`、`controlDict`、`caseDefinition`。公式固定入力は`source/workload/` |
| solverログ・公式結果 | `logs/solver.log`、`results/result.txt` |
| Cd | `results/coefficient.dat`、元pathは`results/coefficient-source.json`。Cdに独自の合否閾値を設定しない |
| scaling | 選択した1/2/4ノードrunから再生成するテキスト表。commitとActions・raw成果物への参照を含める |
| profile解析 | 選択したprofile runのhotspotsと収集状態。benchとは区別する |

保存先はhome-labの`/hdd_raid/samba/net_share/openfoam-artifacts/<Actions run id>/<cluster>/`です。固定artifactの`artifact-manifest.json`と`run-artifacts.tar.zst`から必要なテキストを取得します。メッシュ、`processor*`、実行バイナリ、完全install tree、VTuneバイナリ結果は提出物へ含めません。

固定artifact directoryを3件指定して表を再生成し、未作成の出力先へテキストを保存します（URL・directoryは選択した実runに置き換えます）。

```bash
uv run --project experiment-metrics python -m experiment_metrics.scaling --run URL1 ARTIFACT_DIR1 --run URL2 ARTIFACT_DIR2 --run URL4 ARTIFACT_DIR4 --output-dir submission/openfoam
```

出力は`scaling.txt`と`{1,2,4}node/<run_id>/`です。各runのlogs、results、実使用入力、build/run provenanceを含みます。同commit・cluster・build・workloadの通常benchだけを受け付け、ノード依存の反復数・rank数・既定transport差は表で明示します。step間標準偏差をrun間の測定ばらつきとして解釈しないでください。実行スクリプトは表にあるcommitから取得し、`scripts/`、対象`platforms/<cluster>/`、`.github/workflows/`のテキストを添えます。

面接はQwenとOpenFOAMを合わせた1つの発表資料で、15〜20分の発表と10分の質疑です。OpenFOAMの評価は発表60%、性能40%。分割方法・rank数・係数、最適化の理由、同条件の複数runによる改善とばらつき、1/2/4ノードのscalingを説明します。公式ルールは[対応表](../research/official-rules.md)から辿れます。

以下は公式の推奨配置例です（scheduler拡張子は使用クラスタに合わせます）。

```
submission/
  ├── README.txt                  # including loaded site modules, or how you rebuilt if you did
  ├── build/
  │   └── build.sh                # only if you rebuilt
  ├── run/
  │   ├── 1node.sbatch            # full prep chain, not only simpleFoam
  │   ├── 2node.sbatch
  │   └── 4node.sbatch
  ├── dicts/
  │   ├── caseDefinition
  │   ├── decomposeParDict
  │   └── controlDict
  ├── results/
  │   ├── 1node/                  # text logs, including decomposePar
  │   ├── 2node/
  │   └── 4node/
  │       ├── simpleFoam.log
  │       └── coefficient.dat     # Cd; copy from postProcessing/forceCoeffsAll
  ├── scaling/
  └── analysis/                   # optional profiling write-up
```
