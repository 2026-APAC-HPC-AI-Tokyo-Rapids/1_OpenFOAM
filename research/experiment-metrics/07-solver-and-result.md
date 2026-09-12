# ソルバー状態・数値結果収集モジュール

> [!NOTE]
> 本ドキュメントは旧v2606 motorBike課題を対象とした設計資料である。本文中に記載されている追加のfunction objectや末尾100反復の統計収集は現行の公式課題には適用しない。現行のv2512 occDrivAerStaticMesh課題では固定された公式入力を維持し、平均ステップ時間および最終ステップの抗力係数（$C_d$）を記録する。[現行キーカタログ](../experiment-metrics-v2-key-catalog.md)を参照のこと。

## 目的とモジュール境界

本モジュールの実装は、以下の3つのコレクターに分離する。

| コレクター | 取得対象 | 呼び出し時点 |
|---|---|---|
| `solver_status` | ソルバー完了状態、最終反復の線形ソルバー情報、連続の式誤差（continuity） | `simpleFoam` 終了直後 |
| `aero_result` | 空力係数の末尾100反復における統計値 | `simpleFoam` 終了直後 |
| `field_result` | 最終フィールドの値範囲、境界フラックス収支、固定プローブ観測値 | `simpleFoam` 終了直後 |

各コレクターは、対応するOpenFOAM function objectの表形式出力を読み取り、直ちに単一のバッチとして送信する。ソルバーログ（`simpleFoam.log`）本文の構文解析は行わない。これらの収集項目は解が数学的に完全一致することを証明するものではなく、比較対象とする実行間で数値精度上の異常が発生していないかを高感度に検知するための物理的・数値的フィンガープリント（指紋）として機能する。

主要な評価指標は空力係数、質量流量収支、後流の速度および圧力である。フィールドの値範囲、連続の式誤差、線形ソルバーの残差情報は、異常発生時の原因切り分けを行うための補助指標として位置付ける。

## Function objectの確定設定

v2606 motorBikeチュートリアルに標準で含まれる `forceCoeffs1` および `solverInfo1` を活用し、追加の設定は `system/metricsFunctions` に配置して `controlDict.functions` からincludeする。出力されるすべての `.dat` ファイルに対しては `writePrecision 17` を明示的に指定する。

### 既存のfunction objectに対する追加設定

`forceCoeffs1` については必要な出力列を固定する。

```text
coefficients    (Cd Cl CmPitch);
writePrecision  17;
writeControl    timeStep;
writeInterval   1;
```

`solverInfo1` は対象フィールド設定 `fields (U p)` を維持し、以下を追加する。

```text
writePrecision  17;
executeControl  timeStep;
executeInterval 1;
```

### `system/metricsFunctions` の定義内容

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

プローブ番号と論理名の対応は以下のように固定する。

| プローブ番号 | 論理識別名 | 空間座標 `(x y z)` [m] |
|---:|---|---|
| 0 | `wake_near` | `(3 0 0.75)` |
| 1 | `wake_upper` | `(3 0 1.25)` |
| 2 | `wake_far` | `(5 0 0.75)` |

現在 `controlDict.writeInterval` は `3000` に設定されており、`writeTime` 制御のオブジェクトは最終書き出し時のみ出力される。プローブ出力の精度はOpenFOAMのグローバルなストリーム精度に依存するため、`controlDict.writePrecision` も `17` に統一し、`case.write_precision` として記録する。

## 確定メトリクス

### 完了ステータス

| キー | 論理型 | 取得方法 |
|---|---|---|
| `solver.completed` | bool | `simpleFoam` ステージの終了コードが0か否か |
| `solver.final_simulation_time` | float | `solverInfo.dat` 内の最大 `Time` 値 |

### 最終反復の線形ソルバー状態

`solverInfo1` の最終行から取得する。

```text
solver.linear.u.initial_residual
solver.linear.u.final_residual
solver.linear.u.iterations
solver.linear.u.converged

solver.linear.p.initial_residual
solver.linear.p.final_residual
solver.linear.p.iterations
solver.linear.p.converged
```

v2606におけるヘッダー列名は `Ux_initial`、`Ux_final`、`Ux_iters` から `Uz_iters`、`U_converged`、`p_initial`、`p_final`、`p_iters`、`p_converged` である。速度ベクトル $U$ の残差および反復回数は $x, y, z$ 成分の順にリスト化し、それぞれ `str(list)` により単一の文字列（STRING）として保存する。成分ごとの個別キー展開は行わない。ベクトルフィールドの `converged` 列はフィールド全体に対して1列のみ出力されるため、`0` または `1` をブール値へ変換して記録する。なお、ソルバー名文字列は比較対象の物理量ではないため保存しない。

### 連続の式誤差（Continuity）

`continuityError.dat` の最終行に出力される `Local`、`Global`、`Cumulative` の各列から取得する。

```text
solver.continuity.final.local
solver.continuity.final.global
solver.continuity.cumulative
```

いずれもOpenFOAMが算出した無次元値を符号を保持したまま保存する。

### 空力係数統計

`coefficient.dat` の末尾から最大100行のデータ行をウィンドウとして抽出し、`Cd`、`Cl`、`CmPitch` のそれぞれについて以下のメトリクスを算出・記録する。

```text
result.aero.tail.window_size
result.aero.<coefficient>.tail.final
result.aero.<coefficient>.tail.min
result.aero.<coefficient>.tail.max
result.aero.<coefficient>.tail.mean
result.aero.<coefficient>.tail.population_stddev
```

ここで `<coefficient>` は `cd`、`cl`、`cm_pitch` のいずれかである。`window_size` には実際に読み込んだデータ行数、`mean` には算術平均、`population_stddev` には分母を $N$ とする母標準偏差を記録する。すべての値は無次元量である。平均値は `math.fsum(values) / N`、標準偏差はその平均値を用いた `sqrt(math.fsum((x - mean)**2 for x in values) / N)` の2パスアルゴリズムで厳密に算出する。データが100行未満の場合でも存在する全行を用いて計算する。なお、タイムスタンプの順序性や `case.end_time` との一致検証は行わない。

### 最終フィールド値範囲

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

速度はベクトルの大きさ（magnitude）、$p, k, \omega$ は符号を保持するコンポーネントモード（component mode）で取得する。いずれも内部メッシュ（internal field）のみを対象とする。非圧縮性ソルバーにおける圧力 $p$ は動圧（kinematic pressure: $\mathrm{m^2/s^2}$）であり、パスカル（$\mathrm{Pa}$）への単位換算は行わない。

### 最終境界フラックス収支

```text
result.flux.inlet.final_m3_per_sec
result.flux.outlet.final_m3_per_sec
```

`sum(phi)` の符号をそのまま保持する（流入を正に反転する等の操作は行わない）。収支誤差の比率はメトリクスとして直接保存せず、BigQuery上で以下の式により導出する。

```text
abs(inlet + outlet) / max(abs(inlet), abs(outlet))
```

### 最終後流プローブ観測値

各 `<probe_name>` について、速度ベクトル $U$ を単一のリスト表現文字列、動圧 $p$ をスカラー文字列として記録する。

```text
result.probe.<probe_name>.u.final_m_per_sec
result.probe.<probe_name>.kinematic_pressure.final_m2_per_sec2
```

対象プローブ名は `wake_near`、`wake_upper`、`wake_far` である。プローブ番号0、1、2をこの順序で論理名に対応付け、取得された最終時刻の値を抽出する。ヘッダーに記載された空間座標との再照合は行わない。速度ベクトルの $x, y, z$ 成分はこの順序のリストとし、`str(list)` により単一の文字列として格納する。

## 出力ファイルパスとパーサー仕様

開始時刻が0である現行ケース構成において、入力ファイルパスは以下のように固定する。

| オブジェクト名 | ファイルパス |
|---|---|
| `forceCoeffs1` | `postProcessing/forceCoeffs1/0/coefficient.dat` |
| `solverInfo1` | `postProcessing/solverInfo1/0/solverInfo.dat` |
| `continuityErrorMetrics` | `postProcessing/continuityErrorMetrics/0/continuityError.dat` |
| `velocityRangeMetrics` | `postProcessing/velocityRangeMetrics/0/fieldMinMax.dat` |
| `scalarRangeMetrics` | `postProcessing/scalarRangeMetrics/0/fieldMinMax.dat` |
| `inletFluxMetrics` | `postProcessing/inletFluxMetrics/0/surfaceFieldValue.dat` |
| `outletFluxMetrics` | `postProcessing/outletFluxMetrics/0/surfaceFieldValue.dat` |
| `wakeProbeMetrics` | `postProcessing/wakeProbeMetrics/0/U`, `.../p` |

ベース名の動的探索や最新時刻ディレクトリの推測処理は行わない。開始時刻が0以外のプロファイルを将来追加する場合に限り、その公式なOpenFOAM時刻ディレクトリ名をパスに用いる。

各テーブルファイルからは以下のヘッダー列を読み取る。その他の列は無視し、目的の列が存在しない場合は該当メトリクスを空文字として送信する。

| ファイル名 | 読み取るべきヘッダー列名 |
|---|---|
| `coefficient.dat` | `Time`, `Cd`, `Cl`, `CmPitch` |
| `solverInfo.dat` | `Time`, `Ux_initial`, `Ux_final`, `Ux_iters`, `Uy_initial`, `Uy_final`, `Uy_iters`, `Uz_initial`, `Uz_final`, `Uz_iters`, `U_converged`, `p_initial`, `p_final`, `p_iters`, `p_converged` |
| `continuityError.dat` | `Time`, `Local`, `Global`, `Cumulative` |
| 速度 `fieldMinMax.dat` | `Time`, `min(mag(U))`, `max(mag(U))` |
| スカラー `fieldMinMax.dat` | `Time`, `min(p)`, `max(p)`, `min(k)`, `max(k)`, `min(omega)`, `max(omega)` |
| 流入・流出 `surfaceFieldValue.dat` | `Time`, `sum(phi)` |
| プローブ `U`, `p` | `Time`, `0`, `1`, `2` |

共通テーブルパーサー（`openfoam_table`）は以下の規則に従ってファイルを読み込む。

1. UTF-8バイト列を厳密にデコードし、空行を無視する。
2. 列ヘッダー行においてコメントマーカー `#` が列間に繰り返されるOpenFOAMの出力仕様に対応し、マーカーを除いた先頭列が `Time` である行を列ヘッダー行として認識する。
3. データ行をOpenFOAMの字句規則に従ってトークン分割する。スカラー値、単語（word）、および括弧で囲まれた3成分ベクトルのみを許容する。
4. 必要な列をヘッダー名との完全一致により抽出する。
5. 最終値にはファイルの末尾データ行を採用する。
6. 末尾データ抽出処理（tail parser）は、直近の最大100行のみをメモリ上に保持して処理する。

本処理は列ヘッダー付きテーブル専用のトークンパーサーであり、脆弱な正規表現パターンマッチングには依存しない。プローブデータについては、1フィールド1ファイルの公式形式に準拠し、`Time` に続くプローブ番号順の値を同一の字句解析器で処理する。`# Not Found` と記録されているプローブ位置については、該当キーの値を空文字として送信する。

## 比較検証方針

結果を比較する際は、必要に応じて `case.input_manifest.sha256` および `mesh.partitioned.sha256` を用いて完全に同一条件下での実行を抽出する。空力係数の平均値および最終値、質量流量収支、3箇所の後流プローブ値を主要な比較対象とし、フィールド値範囲、連続の式誤差、線形ソルバー残差を補助的な比較対象とする。なお、この比較評価処理自体はコレクター内部では行わない。

許容誤差の閾値はデータ収集仕様内には固定化しない。同一ビルド・同一条件下での複数回実行から自然な数値変動幅を算定した上で、物理量ごとにBigQueryやスプレッドシート側で絶対誤差および相対誤差の判定閾値を設定する。単にソルバーが正常終了したことや残差が小さいことのみをもって、「数値精度が変化していない」と安易に判断してはならない。

## 失敗時の扱い

- `solver.completed` はステージ終了直後に必ず送信する。
- `simpleFoam` が異常終了した場合であっても、読み取り可能な出力ファイルが存在すれば取得できた値を送信する。
- 欠落した列や存在しないファイルについては該当メトリクスを空文字として送信し、OpenFOAM実験自体の成否判定は変更しない。
- ベースラインとの差分検証は計算ノード上では実施せず、BigQueryや分析環境側で実施する。

## 採用しない値

| 除外項目 | 除外理由 |
|---|---|
| 反復ステップごとの全残差および空力係数 | BigQueryに蓄積する実行レベル（run-level）のデータ粒度を超えるため |
| 警告、致命的エラー、バウンディングの発生件数 | ソルバーログの曖昧なテキスト解析に依存することを避けるため |
| `solver.converged` | 固定反復（3000反復等）の実行において全体収束の普遍的定義が存在しないため |
| `validation.passed` | ベースラインデータと物理量ごとの許容閾値に依存する派生的な判定値であるため |
| 圧力のパスカル（Pa）換算値 | 非圧縮性ソルバーにおいて圧力 $p$ は動圧（$\mathrm{m^2/s^2}$）として扱われるため |
| フィールド全体のバイナリハッシュ | 物理的に無害な微小丸め誤差に過敏に反応し、物理的な差異の尺度として機能しないため |

## 参照仕様

- OpenFOAM v2606 `forceCoeffs`: <https://doc.openfoam.com/2606/tools/post-processing/function-objects/forces/forceCoeffs/>
- OpenFOAM v2606 `solverInfo`: <https://doc.openfoam.com/2606/tools/post-processing/function-objects/utilities/solverInfo/>
- OpenFOAM v2606 `continuityError`: <https://doc.openfoam.com/2606/tools/post-processing/function-objects/field/continuityError/>
- OpenFOAM v2606 `fieldMinMax`: <https://doc.openfoam.com/2606/tools/post-processing/function-objects/field/fieldMinMax/>
- OpenFOAM v2606 `surfaceFieldValue`: <https://doc.openfoam.com/2606/tools/post-processing/function-objects/field/surfaceFieldValue/>
- OpenFOAM v2606 `probes`: <https://doc.openfoam.com/2606/tools/post-processing/function-objects/sampling/probes/>
- OpenFOAM v2606 ソースコードタグ: <https://gitlab.com/openfoam/core/openfoam/-/tree/OpenFOAM-v2606>
