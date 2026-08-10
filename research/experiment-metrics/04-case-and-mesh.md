# ケース・メッシュ収集モジュール

## モジュール境界

実装を`case_config`と`mesh`の2 collectorに分ける。

- `case_config`は、有効な辞書編集がすべて終わった後、meshing開始前に送る。
- `mesh`は、`snappyHexMesh`と`topoSet`の完了後、solver開始前に送る。
- hash計算、`foamDictionary`、`checkMesh`を共通utilityとして再利用する。

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
| `case.freestream_velocity_m_per_sec` | list string | `0.orig/include/initialConditions` | `foamDictionary`のvector出力をlist化して`str(list)` |
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
| `case.input_manifest.sha256` | string | effective input tree | 下記canonical manifest hash |
| `case.control_dict.sha256` | string | effective file | SHA-256 |
| `case.fv_schemes.sha256` | string | effective file | SHA-256 |
| `case.fv_solution.sha256` | string | effective file | SHA-256 |
| `case.decompose_par_dict.sha256` | string | effective file | SHA-256 |
| `case.force_coefficients.sha256` | string | `system/forceCoeffs` | SHA-256 |
| `case.solver_info.sha256` | string | `system/solverInfo` | SHA-256 |
| `case.metrics_functions.sha256` | string | `system/metricsFunctions` | SHA-256 |
| `case.geometry.motorbike_obj_gz.sha256` | string | `constant/triSurface/motorBike.obj.gz` | SHA-256 |

辞書値はOpenFOAM自身に解釈させる。例えば`endTime`は次で取得する。

```bash
LC_ALL=C foamDictionary \
  -entry endTime \
  -value \
  system/controlDict
```

各commandのstdoutから値を読み、辞書をcollector独自の文法で解析しない。

入れ子の値は例えば次で取得する。

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

OpenFOAM vectorは共通の`openfoam_vector` parserで3要素のlistへ変換する。そのlistは
要素別のメトリクスへ展開せず、`str(list)`による1つのSTRING valueとして送る。

SHA-256はPython `hashlib.sha256`でファイルを固定長chunkずつ読み、他のファイルを
作らずに計算する。hash対象は変更後のeffective fileであり、元tutorialのファイル
ではない。

### Input manifest hash

meshing開始前の`0.orig/`、`constant/`、`system/`以下にあるregular fileを対象とする。
相対pathのUTF-8 byte順にsortし、各ファイルについて次を1つのSHA-256へ入力する。

```text
<UTF-8 relative path><NUL><lowercase file SHA-256><LF>
```

symlink、socket、deviceなどregular file以外はhash対象に含めない。
この時点では生成済みmeshやresultは存在しない。したがってmanifestは、編集済み辞書、
初期条件、物性、geometry、function object設定をまとめて識別しつつ、各値を
`value`へ詰め込まない単一のdigestとなる。

## メッシュの確定メトリクス

| キー | 論理型 | 正となる取得元 | 取得方法 |
|---|---|---|---|
| `mesh.partitioned.sha256` | string | 全processorの`constant/polyMesh` | 下記canonical manifest hash |
| `mesh.point_count` | int | `checkMesh` | `points:`行 |
| `mesh.face_count` | int | `checkMesh` | `faces:`行 |
| `mesh.cell_count` | int | `checkMesh` | `cells:`行 |
| `mesh.patch_count` | int | `checkMesh` | `boundary patches:`行 |
| `mesh.region_count` | int | `checkMesh` | `Number of regions:`行 |
| `mesh.quality.max_aspect_ratio` | float | `checkMesh` | `Max aspect ratio =`行 |
| `mesh.quality.max_skewness` | float | `checkMesh` | `Max skewness =`行 |
| `mesh.quality.max_non_orthogonality_deg` | float | `checkMesh` | `Mesh non-orthogonality Max:`行 |
| `mesh.quality.min_cell_volume_m3` | float | `checkMesh` | `Min volume =`行 |
| `mesh.quality.valid` | bool | `checkMesh` | return codeと最終判定 |

### Partitioned mesh hash

case directoryから、次のbasenameを持つregular fileだけを対象にする。

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

`processor<number>/constant/polyMesh/<basename>`という相対pathでbyte順にsortする。
各ファイルについて、次のbyte列を1つのSHA-256へ順に入力する。

```text
<UTF-8 relative path><NUL><lowercase file SHA-256><LF>
```

processor directory番号とpartition内容を含むため、rank数や分割が変わればhashも
変わる。これは物理的に同一な未分割meshの識別子ではなく、そのrunが実際に
solverへ渡したpartitioned meshの厳密な識別子である。

### `checkMesh`の実行

```bash
LC_ALL=C mpirun -np "${OPENFOAM_MPI_PROCS}" \
  checkMesh \
  -parallel \
  -constant \
  -allTopology \
  -allGeometry \
  -decomposeParDict system/decomposeParDict.6
```

stdoutはファイルへ保存せず、pipeから1行ずつ読む。v2606にはJSON等の構造化出力が
ないため、ここだけを人間向けテキスト解析の例外とする。

parserはOpenFOAM v2606の次の英語labelを探す。

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

各label直後の最初の整数またはfloatを読む。boundary patch数もlabel直後の
global countを使う。行末の`OK.`、平均値、local range、句読点などは照合しない。
最後のsummaryに`Mesh OK.`があれば`mesh.quality.valid=true`、
`Failed`があれば`false`とする。command失敗や見つからない項目は空文字で送る。

## 失敗時の扱い

取得できた値を送る。case hashや一部のmesh情報を収集できなくても、それだけを理由に
solverを止めない。`mesh.quality.valid=false`のときに実験を続行するかは既存workflowの
判断であり、メトリクスcollectorは値を記録するだけとする。

## 採用しない値

| 値 | 理由 |
|---|---|
| root側`constant/polyMesh`のhash | parallel snappyHexMesh後の実メッシュではない |
| processor別cell数 | load balanceは必要になった時に別モジュールで扱う |
| hashへmtime、owner、permissionを含める |計算入力の内容ではない |

## 参照仕様

- OpenFOAM command-line interface:
  <https://doc.openfoam.com/2306/fundamentals/command-line/>
- OpenFOAM v2606 `postProcess`:
  <https://doc.openfoam.com/2606/tools/post-processing/utilities/postProcess/>
