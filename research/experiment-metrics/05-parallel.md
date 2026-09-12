# 並列実行条件収集モジュール

## モジュール境界

実装上の識別名は `parallel_config` とする。本モジュールは、OpenFOAMの領域分割設定辞書の内容をソルバー実行の直前に取得し、単一のバッチとして送信する。なお、MPIプロセス数およびIntel MPIの詳細設定については、全環境変数バッチ（`env.*`）側で網羅的に記録する。

## 確定メトリクス

| キー | 論理型 | 正となる取得元 | 取得方法 |
|---|---|---|---|
| `parallel.decomposition.method` | string | `system/decomposeParDict.6` | `foamDictionary` |
| `parallel.decomposition.subdomains` | int | `system/decomposeParDict.6` | `foamDictionary` |

玄界ノードグループAにおける1ノード・120ランクの実験条件では、通常以下の値が取得される。

```text
parallel.decomposition.method = scotch
parallel.decomposition.subdomains = 120
```

スクリプト側で明示的に設定するMPIパラメータは、原則として以下のみである。

```text
I_MPI_FABRICS=shm
```

`I_MPI_FABRICS`、`I_MPI_PIN`、`I_MPI_PIN_PROCESSOR_LIST`、`I_MPI_PIN_DOMAIN`、`I_MPI_PIN_CELL`、`I_MPI_PIN_ORDER`、`I_MPI_PIN_RESPECT_CPUSET` 等の各設定は、明示的設定・未設定の状態を含めて全環境変数バッチから判別する。本モジュールにおいて `parallel.*` プレフィックスの別名を作成したり、設定値の組み合わせが特定の想定プロファイルに合致するかといった推測・判定処理を行ったりはしない。

## OpenFOAM辞書からの値取得

以下のコマンドを実行して取得する。

```bash
LC_ALL=C foamDictionary -entry method -value system/decomposeParDict.6

LC_ALL=C foamDictionary -entry numberOfSubdomains -value system/decomposeParDict.6
```

各コマンドの標準出力から値を読み取り、`numberOfSubdomains` は整数値として保存する。

## 照合を行わない項目

`numberOfSubdomains`、`env.OPENFOAM_MPI_PROCS`、`env.PJM_MPI_PROC`、および実際の `mpirun -np` 引数の各値は、それぞれの取得元から得られた生の値を記録するのみとし、コレクター内部で相互の不一致を照合・検証することはしない。これらの差分や整合性の分析が必要な場合は、BigQuery側でのクエリ実行時に行う。

## 採用しない値

| 除外項目 | 除外理由 |
|---|---|
| ランク別のCPU割り当て番号一覧 | 過去の予備調査によりデフォルト配置の挙動が確認済みであり、通常実行ごとに120行展開することは不要であるため |
| メモリバインド設定 | 現在の実行構成において明示的な設定を行っていないため |
| GPU割り当て情報 | 現在の対象キューである `a-batch` はCPU専用であるため |
| ノード数、ノードあたりランク数 | PJM環境変数から一意に算出可能であり重複となるため |
| MPIファブリック種別、ピニングプロファイル | `I_MPI_*` 環境変数の記録から完全に把握できるため |
| MPI総ランク数 | `env.OPENFOAM_MPI_PROCS` としてすでに保存されているため |
| スケジューラの要求ランク数 | PJM環境変数としてすでに保存されているため |

## 参照仕様

- Intel MPI process pinning: <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-14/process-pinning.html>
- 玄界 ノードグループA ハードウェア仕様: <https://www.cc.kyushu-u.ac.jp/scp/en/system/genkai/hardware/>
