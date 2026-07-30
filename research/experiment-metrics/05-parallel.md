# 並列実行条件収集モジュール

## モジュール境界

実装名は `parallel_config` とする。OpenFOAMの領域分割辞書をsolver開始直前に
1バッチで送る。MPI process数とIntel MPI設定は全環境変数バッチだけに保存する。

## 確定メトリクス

| キー | 論理型 | 正となる取得元 | 取得方法 |
|---|---|---|---|
| `parallel.decomposition.method` | string | `system/decomposeParDict.6` | `foamDictionary` |
| `parallel.decomposition.subdomains` | int | `system/decomposeParDict.6` | `foamDictionary` |

現在の1-node/120-rank実験では、通常は次の値が取得される。

```text
parallel.decomposition.method = scotch
parallel.decomposition.subdomains = 120
```

明示するMPI設定は次だけである。

```text
I_MPI_FABRICS=shm
```

`I_MPI_FABRICS`、`I_MPI_PIN`、`I_MPI_PIN_PROCESSOR_LIST`、
`I_MPI_PIN_DOMAIN`、`I_MPI_PIN_CELL`、`I_MPI_PIN_ORDER`、
`I_MPI_PIN_RESPECT_CPUSET`は設定済み・未設定の状態を含めて全環境変数バッチから判断する。
`parallel.*`の別名は作らず、値の組合せが想定profileに一致するかも判定しない。

## OpenFOAM辞書の取得

```bash
LC_ALL=C foamDictionary \
  -entry method \
  -value \
  system/decomposeParDict.6

LC_ALL=C foamDictionary \
  -entry numberOfSubdomains \
  -value \
  system/decomposeParDict.6
```

各commandのstdoutから値を読み、`numberOfSubdomains`は整数として保存する。

## 照合しない値

`numberOfSubdomains`、`env.OPENFOAM_MPI_PROCS`、`env.PJM_MPI_PROC`、
実際の`mpirun -np`引数はそれぞれの取得元の値として保存するだけで、
collector内では相互に照合しない。違いを調べたい場合はBigQuery側で行う。

## 採用しない値

| 値 | 理由 |
|---|---|
| rankごとのCPU番号 | 既存調査でdefault配置を確認済みで、通常runごとの120行は不要 |
| memory binding | 現在の実行で明示設定しない |
| GPU割当 | 現在のa-batchはCPU-only |
| node数、node当たりrank数 | PJM環境変数から得られるため重複する |
| MPI fabric、pinning profile | `I_MPI_*`環境変数の保存内容から判断できる |
| MPI rank数 | `env.OPENFOAM_MPI_PROCS`として保存する |
| schedulerの要求rank数 | PJM環境変数として保存する |

## 参照仕様

- Intel MPI process pinning:
  <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-14/process-pinning.html>
- Genkai node group A:
  <https://www.cc.kyushu-u.ac.jp/scp/en/system/genkai/hardware/>
