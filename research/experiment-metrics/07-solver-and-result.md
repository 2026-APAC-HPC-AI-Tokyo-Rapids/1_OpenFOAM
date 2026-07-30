# ソルバー状態・数値結果収集モジュール

## 目的とモジュール境界

実装を次のcollectorへ分ける。

| collector | 取得対象 | 呼び出し時点 |
|---|---|---|
| `solver_status` | 完了状態、最終linear solver情報、continuity | `simpleFoam`終了直後 |
| `aero_result` | 空力係数の末尾100 iteration統計 | `simpleFoam`終了直後 |
| `field_result` | final field範囲、boundary flux、固定probe | `simpleFoam`終了直後 |

各collectorは対応するOpenFOAM function objectの表形式出力を読み、直ちに1バッチで
送る。solver log本文は解析しない。これらは解が数学的に同一であることの証明ではなく、
比較対象run間の数値精度異常を高い感度で検出するための物理的・数値的fingerprintである。

主指標は空力係数、流量収支、後流速度・圧力である。field範囲、continuity、
linear solver残差は異常原因を切り分ける補助指標とする。

## Function objectの確定設定

v2606 motorBike tutorialにある`forceCoeffs1`と`solverInfo1`を利用し、追加設定は
`system/metricsFunctions`へ置いて`controlDict.functions`からincludeする。
全`.dat`出力には`writePrecision 17`を指定する。

### 既存objectへ加える設定

`forceCoeffs1`は必要列を固定する。

```text
coefficients    (Cd Cl CmPitch);
writePrecision  17;
writeControl    timeStep;
writeInterval   1;
```

`solverInfo1`は`fields (U p)`を維持し、次を加える。

```text
writePrecision  17;
executeControl  timeStep;
executeInterval 1;
```

### `system/metricsFunctions`

```text
continuityErrorMetrics
{
    type            continuityError;
    libs            (fieldFunctionObjects);
    phi             phi;
    writePrecision  17;
    writeControl    timeStep;
    writeInterval   1;
}

velocityRangeMetrics
{
    type            fieldMinMax;
    libs            (fieldFunctionObjects);
    fields          (U);
    mode            magnitude;
    internal        true;
    location        false;
    writePrecision  17;
    writeControl    writeTime;
    writeInterval   1;
}

scalarRangeMetrics
{
    type            fieldMinMax;
    libs            (fieldFunctionObjects);
    fields          (p k omega);
    mode            component;
    internal        true;
    location        false;
    writePrecision  17;
    writeControl    writeTime;
    writeInterval   1;
}

inletFluxMetrics
{
    type            surfaceFieldValue;
    libs            (fieldFunctionObjects);
    regionType      patch;
    name            inlet;
    operation       sum;
    fields          (phi);
    writeFields     false;
    writePrecision  17;
    writeControl    writeTime;
    writeInterval   1;
}

outletFluxMetrics
{
    type            surfaceFieldValue;
    libs            (fieldFunctionObjects);
    regionType      patch;
    name            outlet;
    operation       sum;
    fields          (phi);
    writeFields     false;
    writePrecision  17;
    writeControl    writeTime;
    writeInterval   1;
}

wakeProbeMetrics
{
    type                probes;
    libs                (sampling);
    fields              (U p);
    probeLocations
    (
        (3 0 0.75)
        (3 0 1.25)
        (5 0 0.75)
    );
    fixedLocations      true;
    includeOutOfBounds  false;
    interpolationScheme cellPoint;
    writeControl        writeTime;
    writeInterval       1;
}
```

probe番号と論理名は次に固定する。

| 番号 | 論理名 | 座標 `(x y z)` m |
|---:|---|---|
| 0 | `wake_near` | `(3 0 0.75)` |
| 1 | `wake_upper` | `(3 0 1.25)` |
| 2 | `wake_far` | `(5 0 0.75)` |

`controlDict.writeInterval`は現在`3000`であり、final-only objectはfinal writeだけを
出力する。probe出力精度はOpenFOAMのglobal stream precisionに従うため、
`controlDict.writePrecision`も`17`へ設定し、`case.write_precision`として記録する。

## 確定メトリクス

### 完了状態

| キー | 論理型 | 取得方法 |
|---|---|---|
| `solver.completed` | bool | `simpleFoam` stage return codeが0か |
| `solver.final_simulation_time` | float | `solverInfo.dat`の最大`Time` |

### 最終linear solver状態

`solverInfo1`の最終行から取得する。

```text
solver.linear.u.0.initial_residual
solver.linear.u.0.final_residual
solver.linear.u.0.iterations
solver.linear.u.1.initial_residual
solver.linear.u.1.final_residual
solver.linear.u.1.iterations
solver.linear.u.2.initial_residual
solver.linear.u.2.final_residual
solver.linear.u.2.iterations
solver.linear.u.converged

solver.linear.p.initial_residual
solver.linear.p.final_residual
solver.linear.p.iterations
solver.linear.p.converged
```

v2606の列名は`Ux_initial`, `Ux_final`, `Ux_iters`から`Uz_iters`、
`U_converged`、`p_initial`, `p_final`, `p_iters`, `p_converged`である。
OpenFOAM列の`x`, `y`, `z`をそれぞれ数字sub-propertyの`0`, `1`, `2`へ対応付ける。
vector fieldのconverged列はcomponent別ではなくfield全体に1つだけである。
residualをfloat、iterationsをint、convergedの`0`または`1`をboolへ変換する。
solver名文字列は比較用物理量ではないため保存しない。

### Continuity

`continuityError.dat`の最終行の`Local`, `Global`, `Cumulative`から取得する。

```text
solver.continuity.final.local
solver.continuity.final.global
solver.continuity.cumulative
```

いずれもOpenFOAMが計算した無次元値を符号を変えずに保存する。

### 空力係数

`coefficient.dat`の末尾から最大100 data行をwindowとし、`Cd`, `Cl`, `CmPitch`の
それぞれについて次を保存する。

```text
result.aero.tail.window_size
result.aero.<coefficient>.tail.final
result.aero.<coefficient>.tail.min
result.aero.<coefficient>.tail.max
result.aero.<coefficient>.tail.mean
result.aero.<coefficient>.tail.population_stddev
```

`<coefficient>`は`cd`, `cl`, `cm_pitch`である。window sizeには実際に読んだ行数、
meanは算術平均、標準偏差は分母`N`の母標準偏差とする。全値は無次元である。
meanは`math.fsum(values) / N`、標準偏差はそのmeanを用いた
`sqrt(math.fsum((x - mean)**2 for x in values) / N)`の2-pass計算に固定する。
100行未満でも存在する行を使う。時刻順や`case.end_time`との一致は照合しない。

### Final field範囲

```text
result.field.u_magnitude.final.min_m_per_sec
result.field.u_magnitude.final.max_m_per_sec
result.field.kinematic_pressure.final.min_m2_per_sec2
result.field.kinematic_pressure.final.max_m2_per_sec2
result.field.k.final.min_m2_per_sec2
result.field.k.final.max_m2_per_sec2
result.field.omega.final.min_per_sec
result.field.omega.final.max_per_sec
```

速度はvectorのmagnitude、`p/k/omega`は符号を保つcomponent modeである。
いずれもinternal fieldだけを対象にする。incompressible solverの
`p`はkinematic pressureであり、Paへ換算しない。

### Final boundary flux

```text
result.flux.inlet.final_m3_per_sec
result.flux.outlet.final_m3_per_sec
```

`sum(phi)`の符号を保つ。inletを正へ反転しない。収支誤差は保存値ではなく、
BigQuery上で次を計算する。

```text
abs(inlet + outlet) / max(abs(inlet), abs(outlet))
```

### Final wake probes

各`<probe_name>`について4つのスカラーへ展開する。

```text
result.probe.<probe_name>.u.final_m_per_sec.0
result.probe.<probe_name>.u.final_m_per_sec.1
result.probe.<probe_name>.u.final_m_per_sec.2
result.probe.<probe_name>.kinematic_pressure.final_m2_per_sec2
```

対象名は`wake_near`, `wake_upper`, `wake_far`である。probe番号0、1、2をこの順で
論理名へ対応付け、取得できたfinal valueを読む。header座標との再照合は行わない。
U vectorの`x`, `y`, `z`成分を数字sub-propertyの`0`, `1`, `2`へ展開する。

## 出力ファイルとparser契約

start timeが0の現在のcaseでは、入力pathを次に固定する。

| object | path |
|---|---|
| `forceCoeffs1` | `postProcessing/forceCoeffs1/0/coefficient.dat` |
| `solverInfo1` | `postProcessing/solverInfo1/0/solverInfo.dat` |
| `continuityErrorMetrics` | `postProcessing/continuityErrorMetrics/0/continuityError.dat` |
| `velocityRangeMetrics` | `postProcessing/velocityRangeMetrics/0/fieldMinMax.dat` |
| `scalarRangeMetrics` | `postProcessing/scalarRangeMetrics/0/fieldMinMax.dat` |
| `inletFluxMetrics` | `postProcessing/inletFluxMetrics/0/surfaceFieldValue.dat` |
| `outletFluxMetrics` | `postProcessing/outletFluxMetrics/0/surfaceFieldValue.dat` |
| `wakeProbeMetrics` | `postProcessing/wakeProbeMetrics/0/U`, `.../p` |

basenameの探索や最新directoryの推測はしない。`case.start_time`が0以外のprofileを
将来追加する場合だけ、そのcanonicalなOpenFOAM time nameをpathへ使う。

各表では次のheader名の列を読む。他の列は無視し、目的の列がなければそのメトリクスを
空文字で送る。

| file | 必要なheader |
|---|---|
| `coefficient.dat` | `Time`, `Cd`, `Cl`, `CmPitch` |
| `solverInfo.dat` | `Time`, `Ux_initial`, `Ux_final`, `Ux_iters`, `Uy_initial`, `Uy_final`, `Uy_iters`, `Uz_initial`, `Uz_final`, `Uz_iters`, `U_converged`, `p_initial`, `p_final`, `p_iters`, `p_converged` |
| `continuityError.dat` | `Time`, `Local`, `Global`, `Cumulative` |
| velocity `fieldMinMax.dat` | `Time`, `min(mag(U))`, `max(mag(U))` |
| scalar `fieldMinMax.dat` | `Time`, `min(p)`, `max(p)`, `min(k)`, `max(k)`, `min(omega)`, `max(omega)` |
| inlet/outlet `surfaceFieldValue.dat` | `Time`, `sum(phi)` |
| probe `U`, `p` | `Time`, `0`, `1`, `2` |

共通`openfoam_table` parserは次の読み方とする。

1. UTF-8をstrict decodeし、空行を無視する。
2. comment marker `#`を列間で繰り返すv2606出力もtokenとして扱い、markerを除いた
   先頭列が`Time`のcolumn headerを使う。
3. data行をOpenFOAM token grammarで読む。scalar、word、括弧付き3-vectorだけを許す。
4. 必要列をheader名で選ぶ。
5. final値には最後のdata行を使う。
6. tail parserは最後の最大100行だけをメモリに保持する。

これはcolumn header付き表のtoken parserであり、正規表現は使わない。
probeだけは1 field 1 fileの公式形式に合わせ、`Time`に続くprobe順の値を同じ
tokenizerで読む。`# Not Found`のprobeはその地点のキーを空文字で送る。

## 比較方法

比較時には必要に応じて`case.input_manifest.sha256`と`mesh.partitioned.sha256`で
同条件runを絞り込める。空力係数のmean/final、flux収支、3点のwake値を主比較し、
field範囲とcontinuity、残差を補助比較する。この比較はcollectorでは行わない。

許容差はデータ収集仕様へ固定しない。同一build・同一条件の反復runから自然変動幅を
求めた上で、物理量ごとにBigQuery/Sheets側で絶対差・相対差の閾値を定める。
単にsolverが終了したことやresidualが小さいことだけを、精度不変の根拠にはしない。

## 失敗時の扱い

- `solver.completed`はstage終了直後に必ず送る。
- `simpleFoam`失敗時も、読める出力があれば取得できた値を送る。
- 欠けた列や出力はそのメトリクスを空文字で送り、OpenFOAM実験の成否は変更しない。
- baselineとの差は計算nodeで判定せず、BigQuery/Sheetsで比較する。

## 採用しない値

| 値 | 理由 |
|---|---|
| iterationごとの残差・係数 | BigQueryのrun-level対象外 |
| warning/fatal/bounding件数 | solver logの曖昧な解析になる |
| `solver.converged` | 固定3000 iterationに全体収束の定義がない |
| `validation.passed` | baselineと物理量別許容差に依存する派生値 |
| pressureのPa値 | incompressible `p`はkinematic pressure |
| field全体のhash | 無害な丸め差に過敏で、物理的な差の尺度にならない |

## 参照仕様

- v2606 `forceCoeffs`:
  <https://doc.openfoam.com/2606/tools/post-processing/function-objects/forces/forceCoeffs/>
- v2606 `solverInfo`:
  <https://doc.openfoam.com/2606/tools/post-processing/function-objects/utilities/solverInfo/>
- v2606 `continuityError`:
  <https://doc.openfoam.com/2606/tools/post-processing/function-objects/field/continuityError/>
- v2606 `fieldMinMax`:
  <https://doc.openfoam.com/2606/tools/post-processing/function-objects/field/fieldMinMax/>
- v2606 `surfaceFieldValue`:
  <https://doc.openfoam.com/2606/tools/post-processing/function-objects/field/surfaceFieldValue/>
- v2606 `probes`:
  <https://doc.openfoam.com/2606/tools/post-processing/function-objects/sampling/probes/>
- OpenFOAM v2606 source tag:
  <https://gitlab.com/openfoam/core/openfoam/-/tree/OpenFOAM-v2606>
