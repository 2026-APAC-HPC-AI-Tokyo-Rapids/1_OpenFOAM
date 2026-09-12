# ケース・メッシュ収集モジュール

## モジュール境界

本モジュールの実装は、`case_config` と `mesh` の2つのコレクターに分離する。

- `case_config`: 有効な辞書編集がすべて完了した後、メッシュ生成処理を開始する直前のタイミングで送信する。
- `mesh`: `snappyHexMesh` および `topoSet` が完了した後、ソルバー実行を開始する直前のタイミングで送信する。
- ハッシュ計算、`foamDictionary` の呼び出し、および `checkMesh` の実行処理は共通ユーティリティとして再利用する。

## ケース設定の確定メトリクス

| キー | 論理型 | 正となる取得元 | 取得方法 |
|---|---|---|---|
| `case.name` | string | 実験設定 | `"motorBike"` |
| `case.application` | string | `system/controlDict` | `foamDictionary` |
| `case.start_time` | float | `system/controlDict` | `foamDictionary` |
| `case.end_time` | float | `system/controlDict` | `foamDictionary` |
| `case.delta_t` | float | `system/controlDict` | `foamDictionary` |
| `case.write_interval` | int | `system/controlDict` | `foamDictionary` |
| `case.write_precision` | int | `system/controlDict` | `foamDictionary` |
| `case.freestream_velocity_m_per_sec` | list string | `0.orig/include/initialConditions` | `foamDictionary` のベクトル出力をリスト化し `str(list)` で格納 |
| `case.initial.kinematic_pressure_m2_per_sec2` | float | `0.orig/include/initialConditions` | `foamDictionary` |
| `case.initial.turbulent_kinetic_energy_m2_per_sec2` | float | 同上 | `foamDictionary` |
| `case.initial.specific_dissipation_rate_per_sec` | float | 同上 | `foamDictionary` |
| `case.transport.model` | string | `constant/transportProperties` | `foamDictionary` |
| `case.transport.kinematic_viscosity_m2_per_sec` | float | 同上 | `foamDictionary` |
| `case.turbulence.simulation_type` | string | `constant/turbulenceProperties` | `foamDictionary` |
| `case.turbulence.ras_model` | string | 同上 | `foamDictionary` |
| `case.force_coefficients.reference_velocity_m_per_sec` | float | `system/forceCoeffs` | `foamDictionary` |
| `case.force_coefficients.reference_length_m` | float | `system/forceCoeffs` | `foamDictionary` |
| `case.force_coefficients.reference_area_m2` | float | `system/forceCoeffs` | `foamDictionary` |
| `case.force_coefficients.reference_density_kg_per_m3` | float | `system/forceCoeffs` | `foamDictionary` |
| `case.input_manifest.sha256` | string | 実使用入力ツリー | 後述の正規化マニフェストハッシュ |
| `case.control_dict.sha256` | string | 実使用ファイル | SHA-256 |
| `case.fv_schemes.sha256` | string | 実使用ファイル | SHA-256 |
| `case.fv_solution.sha256` | string | 実使用ファイル | SHA-256 |
| `case.decompose_par_dict.sha256` | string | 実使用ファイル | SHA-256 |
| `case.force_coefficients.sha256` | string | `system/forceCoeffs` | SHA-256 |
| `case.solver_info.sha256` | string | `system/solverInfo` | SHA-256 |
| `case.metrics_functions.sha256` | string | `system/metricsFunctions` | SHA-256 |
| `case.geometry.motorbike_obj_gz.sha256` | string | `constant/triSurface/motorBike.obj.gz` | SHA-256 |

辞書ファイル内の値は、OpenFOAM自身のツールに解釈させる。たとえば `endTime` は以下のコマンドで取得する。

```bash
LC_ALL=C foamDictionary -entry endTime -value system/controlDict
```

各コマンドの標準出力から値を読み取り、コレクター独自で辞書ファイルの独自構文解析を行うことは避ける。

ネストされた辞書エントリは、たとえば以下のように取得する。

```bash
LC_ALL=C foamDictionary -entry forceCoeffs1/magUInf -value system/forceCoeffs
LC_ALL=C foamDictionary -entry forceCoeffs1/lRef    -value system/forceCoeffs
LC_ALL=C foamDictionary -entry forceCoeffs1/Aref    -value system/forceCoeffs
LC_ALL=C foamDictionary -entry forceCoeffs1/rhoInf  -value system/forceCoeffs
LC_ALL=C foamDictionary -entry flowVelocity -value 0.orig/include/initialConditions
LC_ALL=C foamDictionary -entry pressure -value 0.orig/include/initialConditions
LC_ALL=C foamDictionary -entry turbulentKE -value 0.orig/include/initialConditions
LC_ALL=C foamDictionary -entry turbulentOmega -value 0.orig/include/initialConditions
LC_ALL=C foamDictionary -entry transportModel -value constant/transportProperties
LC_ALL=C foamDictionary -entry nu -value constant/transportProperties
LC_ALL=C foamDictionary -entry simulationType -value constant/turbulenceProperties
LC_ALL=C foamDictionary -entry RAS/RASModel -value constant/turbulenceProperties
```

OpenFOAMの3次元ベクトルは、共通の `openfoam_vector` パーサーにより3要素のリストへ変換する。このリストは要素ごとの個別メトリクスには展開せず、`str(list)` による単一の文字列（STRING）として送信する。

SHA-256ハッシュは、Pythonの `hashlib.sha256` を用いてファイルを固定長チャンク単位で読み込み、一時ファイル等を作成せずにメモリ上で直接計算する。ハッシュの対象は、前処理適用後の実使用ファイル（effective file）であり、配布時のチュートリアル原典ファイルではない。

### 入力マニフェストハッシュの算出規則

メッシュ生成開始前の `0.orig/`、`constant/`、`system/` 配下に存在する通常ファイル（regular file）を対象とする。相対パスのUTF-8バイト順でソートし、各ファイルについて以下のバイト列を単一のSHA-256コンテキストへ順次入力する。

```text
<UTF-8 relative path><NUL><lowercase file SHA-256><LF>
```

シンボリックリンク、ソケット、デバイスファイル等の特殊ファイルはハッシュ対象に含めない。この時点では生成済みメッシュや計算結果は存在しない。したがって本マニフェストは、編集済み辞書群、初期条件、物性値、ジオメトリ、およびfunction object設定を包括的に一意識別しつつ、個別値をテーブルへ過剰に展開させない単一のダイジェスト値となる。

## メッシュの確定メトリクス

| キー | 論理型 | 正となる取得元 | 取得方法 |
|---|---|---|---|
| `mesh.partitioned.sha256` | string | 全processorディレクトリの `constant/polyMesh` | 後述の正規化マニフェストハッシュ |
| `mesh.point_count` | int | `checkMesh` | `points:` 行 |
| `mesh.face_count` | int | `checkMesh` | `faces:` 行 |
| `mesh.cell_count` | int | `checkMesh` | `cells:` 行 |
| `mesh.patch_count` | int | `checkMesh` | `boundary patches:` 行 |
| `mesh.region_count` | int | `checkMesh` | `Number of regions:` 行 |
| `mesh.quality.max_aspect_ratio` | float | `checkMesh` | `Max aspect ratio =` 行 |
| `mesh.quality.max_skewness` | float | `checkMesh` | `Max skewness =` 行 |
| `mesh.quality.max_non_orthogonality_deg` | float | `checkMesh` | `Mesh non-orthogonality Max:` 行 |
| `mesh.quality.min_cell_volume_m3` | float | `checkMesh` | `Min volume =` 行 |
| `mesh.quality.valid` | bool | `checkMesh` | コマンド終了コードと最終サマリー判定 |

### 領域分割済みメッシュハッシュの算出規則

ケースディレクトリから、以下のベース名を持つ通常ファイルのみを対象とする。

```text
boundary
cellZones
faceZones
faces
neighbour
owner
pointZones
points
```

`processor<number>/constant/polyMesh/<basename>` という相対パスのバイト順序でソートする。各ファイルについて、以下のバイト列を単一のSHA-256コンテキストへ順次入力する。

```text
<UTF-8 relative path><NUL><lowercase file SHA-256><LF>
```

processorディレクトリ番号と分割内容が含まれるため、ランク数や分割手法が異なればハッシュ値も変化する。これは物理的に同一な単一メッシュの識別子ではなく、当該実行においてソルバーへ実際に渡された領域分割済みメッシュ（partitioned mesh）の厳密な識別子である。

### `checkMesh` の実行と出力解析

```bash
LC_ALL=C mpirun -np "${OPENFOAM_MPI_PROCS}" checkMesh -parallel -constant -allTopology -allGeometry -decomposeParDict system/decomposeParDict.6
```

標準出力はディスクへ保存せず、パイプから1行ずつ読み取る。OpenFOAM v2606にはJSON等の構造化出力オプションが存在しないため、ここでのみ人間向けテキスト出力の解析を例外的に認める。

パーサーは、OpenFOAM v2606が出力する以下の英語ラベルを検索する。

```text
    points:
    faces:
    cells:
    boundary patches:
    Number of regions:
    Max aspect ratio =
    Mesh non-orthogonality Max:
    Max skewness =
    Min volume =
```

各ラベル直後に出現する最初の整数または浮動小数点数を読み取る。境界パッチ数（boundary patches）についてもラベル直後のグローバル総数を使用する。行末の `OK.`、平均値、ローカル範囲、句読点などは照合しない。最終サマリーに `Mesh OK.` が含まれていれば `mesh.quality.valid=true`、`Failed` が含まれていれば `false` と判定する。コマンド実行の失敗や該当項目が存在しない場合は、対象キーを空文字として送信する。

## 失敗時の扱い

取得できた値のみを送信する。ケースハッシュや一部のメッシュ情報が収集できなかったことのみを理由としてソルバー実行を停止させてはならない。`mesh.quality.valid=false` の場合に実験を継続するか否かはワークフロー側の制御判断であり、メトリクスコレクターは状態を正確に記録することに専念する。

## 採用しない値

| 除外項目 | 除外理由 |
|---|---|
| ルートディレクトリ側の `constant/polyMesh` ハッシュ | 並列 `snappyHexMesh` 実行後の実メッシュを反映しないため |
| プロセッサ別のセル数内訳 | ロードバランス検証が必要になった段階で別モジュールとして扱うため |
| ハッシュへの更新時刻（mtime）、所有者、パーミッションの包含 | 計算入力の内容そのものを識別する目的から外れるため |

## 参照仕様

- OpenFOAM コマンドラインインターフェース: <https://doc.openfoam.com/2306/fundamentals/command-line/>
- OpenFOAM v2606 `postProcess`: <https://doc.openfoam.com/2606/tools/post-processing/utilities/postProcess/>
