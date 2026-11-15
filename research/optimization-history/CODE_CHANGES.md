# OpenFOAM：コードの変更から実測結果まで

対象は2026年10月8日までに調査した履歴。ここでは「何を最適化したか」に加え、**どの関数の、どのループ・配列・通信を変えたか**を追う。性能値の比較条件と原記録は[概要](README.md)、[実験台帳](EXPERIMENTS.md)に対応する。コード原本は[固定コミット別の索引](code-diffs/README.md)から全文を読める。

以下は対象コミットのGit objectから取得したコードである。0001〜0004は最終Bonusの`fa4f5b04`が保持するパッチを保存した。導入コミットと最終修正版を区別する。短縮したコードには「要約」と付記した。

## 変更の位置関係

| 段階 | 呼び出し位置・変更対象 | 減らす処理 | 実装を読む章 |
| --- | --- | --- | --- |
| MPI起動 | `exec-local-numa.sh` / `keep-rank-affinity.sh` | remote NUMAアクセスにつながる配置の崩れ | [1](#of-1) |
| ケース準備 | `prepare-openfoam-case.sh` / `decomposeParDict` | ノードを跨ぐprocessor面 | [2](#of-2) |
| 反復解法 | `smoothSolver::scalarSolve` / `GAMGSolver::solve` | 残差の一時場・コピー・余分な走査 | [3](#of-3) |
| Uの3成分solve | `fvMatrix::solveSegregated` → `solveGaussSeidelComponents` | 共通LDU配列の3回読み | [4](#of-4) |
| 方程式組立 | `surfaceIntegrateInternal` / `gaussConvectionScheme::fvmDiv` | 不要な出力境界評価・係数の再走査 | [5](#of-5) |
| 勾配・補正項 | `gaussGrad` / 二引数`surfaceIntegrateInternal` | 補間面場・積の一時面場 | [6](#of-6) |
| 旧cavityのPCG | `DICPreconditioner::precondition` / `PCG::scalarSolve` | scatter先の繰返し更新・残差再読込み | [8](#of-8) |

<a id="of-1"></a>
## 1. CPU固定とメモリ配置は別のコードで直した

NUMAメモリ固定とCPU affinityの再固定を適用した。外部CPU固定だけの3.5488/3.4098/3.4629秒に対し、NUMAラッパー＋keeperは2.9191/2.9123/2.9189秒。比較条件：異なる時期の配置診断。保存済み最終bundleのrank配置は[監査JSON](final-bundle-audit.json)にある。各snapshotでrankの固定を確認した。初期メモリ配置と計算中のCPU配置を揃えたことが短縮の原因と考えられる。

導入`5abefc1c`。[起動・keeperの実差分](code-diffs/rank-binding.diff)。変更前は`LD_PRELOAD`のMPI affinity interposerを使っていた。変更後はrankの起動ラッパーと、node上の別プロセスによる再固定に分けた。

`platforms/aspire2a/exec-local-numa.sh`の実処理は次の一行である。

```bash
exec numactl --membind="$(( PMI_LOCAL_RANK / 16 ))" "$@"
```

この環境の16 core/NUMAという対応を使い、MPI初期化より前にrankのメモリポリシーを設定する。CPU affinityだけを後から戻しても、初期割当て済みページの所在は直らないため、この処理が必要だった。

`keep-rank-affinity.sh`は`simpleFoam`のPIDを探し、`/proc/<pid>/environ`の`PMI_LOCAL_RANK`と`/proc/<pid>/status`の`Cpus_allowed_list`を比較する。不一致なら次を実行する。

```bash
taskset -pc "${local_rank_of[${pid}]}" "${pid}"
```

keeper自身はCPU 255へ置く。起動後60秒までは0.1秒、以降は2秒間隔で確認する。solverを起動するPBS側でkeeperを開始し、solver終了後にkill/waitする。旧interposerのビルド・配布も削除された。

<a id="of-2"></a>
## 2. multiLevelで分割をnode・socket・NUMA・coreに対応させた

multiLevel分割を適用した。パッチなしで2.918057→2.873231秒、約1.54%短縮。ノード間面は337,324→208,092。後続のソースパッチの数値一致は、**同じmultiLevelのパッチなし版**との比較で確認した。通信する面の配置をハードウェア階層へ対応させたことが改善の原因と考えられる。

統合`e2730db0`。[統合差分](code-diffs/multilevel.diff)、[ケース準備スクリプト原文](code-diffs/prepare-openfoam-case.sh.txt)。`platforms/aspire2a/decomposition-{1,2,4}n.txt`の選択を`multilevel`にし、準備時に階層の積とMPI rank数が一致することを検査する。4ノードで生成する設定の要約は次の形になる。

```foam
method multiLevel;
multiLevelCoeffs
{
    method scotch;
    domains (4 2 4 16);
}
```

node→socket→NUMA→coreの階層を分割へ反映し、1ノードは`(2 4 16)`、2ノードは`(2 2 4 16)`にする。`prepare-openfoam-case.sh`は`method`と`domains`をcase cacheのidentityにも含める。ここを変えないと、新設定なのに古い分割済みケースを再利用する危険がある。

<a id="of-3"></a>
## 3. 0001：残差を返すAPIから、既存領域へ書くAPIへ

残差のin-place計算とGAMGの減算融合を適用した。同じmultiLevelで2.873231→2.775911秒、約3.39%短縮した。一時fieldの確保・コピーと残差の再走査を減らしたことが効いたと考えられる。比較は二箇所の変更を同時に適用した構成。残差の`gSumMag`、normFactor、収束判定、反復回数を維持した。

導入`d3681045`。[0001全文](code-diffs/0001-drop-redundant-solver-copies.patch)。対象は`src/OpenFOAM/matrices/lduMatrix/solvers/`下の`smoothSolver/smoothSolver.C`と`GAMG/GAMGSolverSolve.C`。

`smoothSolver::scalarSolve`の変更を引数省略で要約すると、次の差分になる。

```diff
- residual = matrix_.residual(psi, source, interfaceBouCoeffs_, interfaces_, cmpt);
+ matrix_.residual(residual, psi, source, interfaceBouCoeffs_, interfaces_, cmpt);
```

前者は戻り値の一時fieldを確保し、`Field::operator=(const tmp<Field>&)`で既存`residual`へコピーする。後者は出力先を第一引数に渡すoverloadで、同じ残差計算を既存領域に直接書く。対象fixedIter条件ではUの3成分×15回とk/omega各8回、合計61回/stepの確保・cell fieldコピーを取り除く。

GAMG側の実差分は短い。

```diff
- finestResidual = tsource();
- finestResidual -= Apsi;
+ subtract(finestResidual, tsource(), Apsi);
```

以前はsource全体をコピーしてから、もう一度残差fieldを読み書きして引いていた。変更後は`source[cell] - Apsi[cell]`を一回の走査で出力する。圧力の12 V-cycleで繰り返す箇所である。

<a id="of-4"></a>
## 4. 0002：Uの成分別solveから共有行列の走査へ

Uの3成分の平滑化・残差計算を融合した。対照各3runで2.781302→2.717522秒、約2.29%短縮した。非対角係数とaddressingの読込みを3成分で共有したことが効いたと考えられる。導入前profileではU solveが全体の14.0%を占めていた。各成分内のface順を保ち、独立な成分の処理を交互に実行する。psi・source・diagは成分ごとに読み書きする。

導入`81fb7e5c`。[0002全文](code-diffs/0002-smooth-vector-components-together.patch)。主な変更は三つある。

| ファイル | 追加・変更した関数 | 役割 |
| --- | --- | --- |
| `src/finiteVolume/fvMatrices/fvMatrix/fvMatrixSolve.C` | `fvMatrix<Type>::solveSegregated` | 成分ごとのdiag/source/interfaceを準備して新経路を呼ぶ |
| `src/OpenFOAM/matrices/lduMatrix/solvers/smoothSolver/smoothSolver.H` | `solveGaussSeidelComponents`宣言 | 3成分をまとめる入口 |
| 同ディレクトリの`smoothSolver.C` | `gaussSeidelSweep<N>`、`internalResidual<N>`、上記入口 | 共通係数・addressingの読込みを共有 |

従来はUxの全反復→Uyの全反復→Uzの全反復という成分別のsolveだった。Uの非対角係数`lower/upper`とaddressingは共通なので、新しいsweepは一つの係数を読み、その場で3成分へ使う。以下は追加コードの実抜粋。

```cpp
for (label facei=fStart; facei<fEnd; facei++)
{
    const scalar a = upperPtr[facei];
    const label j = uPtr[facei];
    for (int k=0; k<N; k++)
    {
        psii[k] -= a*psiPtr[k][j];
    }
}
```

`diagPtr[k]`は成分別である。境界による対角補正まで共有化すると別の方程式になるので、`solveSegregated`内で`saveDiag`を成分ごとにコピーして`addBoundaryDiag(..., cmpt)`を適用する。source、境界係数、初期残差、normFactorも成分別に保つ。

新経路の条件は`Type == vector`、`solveScalar == scalar`、全成分valid、solverが`smoothSolver`、smootherが`GaussSeidel`、`nSweeps > 0`。他の型・解法には既存の成分ループを残す。

処理順は「各成分のinterface更新→全成分の内部sweep→全成分の内部残差→各成分のinterface寄与→各成分のnorm/収束判定」。interfaceのバッファは共有されるため、成分間の通信を重ねて走らせない。`active[0] && active[1] && active[2]`の間だけ`<3>`を使い、先に収束した成分が出たら残りは`<1>`で処理する。成分ごとに元の収束条件で終了する。

<a id="of-5"></a>
## 5. 0003：捨てる出力境界を作らず、係数を一回で組み立てる

内部cell値を直接返すAPIと、対流係数を一回の面ループで作る処理を適用した。各3runで2.708041→2.672486秒、約1.31%短縮した。不要な出力境界の評価と、lower→upper→diagの配列再読込みを減らしたことが効いたと考えられる。

導入`20d285b4`。[0003全文](code-diffs/0003-skip-discarded-boundary-updates.patch)。新関数は`src/finiteVolume/finiteVolume/fvc/fvcSurfaceIntegrate.{H,C}`の`surfaceIntegrateInternal`。戻り値を境界を持つ`GeometricField`から、内部cell値だけの`DimensionedField<Type, volMesh>`にする。

内部では従来の`surfaceIntegrate(tvf.ref().field(), ssf)`を呼び、入力faceの境界寄与を加算する。消費側が使う内部cell値を直接返すことで、出力vol fieldの境界の構築・評価を省いた。

| 呼び出し元 | 変更前 | 変更後・使用先 |
| --- | --- | --- |
| `simpleFoam/pEqn.H` | `fvc::div(phiHbyA)` | `fvc::surfaceIntegrateInternal(phiHbyA)`を圧力方程式右辺へ |
| `kOmegaSSTBase::correct` | `fvc::div(fvc::absolute(phi,U))` | 内部場`divU`を直接生成 |
| `continuityErrs.H` | `volScalarField contErr(...)` | `volScalarField::Internal`で体積加重平均 |
| `boundedConvectionScheme::fvmDiv` | `fvm::Sp(fvc::surfaceIntegrate(faceFlux),vf)` | 内部値だけを`Sp`へ渡す |
| `gaussLaplacianScheme` | `fvc::div(... )().primitiveField()` | `surfaceIntegrateInternal(... )().field()`でsourceを補正 |

もう一つの変更は`gaussConvectionScheme::fvmDiv`の係数生成である。

```cpp
// 変更前の実コード
fvm.lower() = -weights.primitiveField()*faceFlux.primitiveField();
fvm.upper() = fvm.lower() + faceFlux.primitiveField();
fvm.negSumDiag();
```

変更後の面ループ内部は次の実コードになる。

```cpp
const scalar lowerf = -w[facei]*phi[facei];
const scalar upperf = lowerf + phi[facei];
lower[facei] = lowerf;
upper[facei] = upperf;
diag[l[facei]] -= lowerf;
diag[u[facei]] -= upperf;
```

<a id="of-6"></a>
## 6. 0004：面場を実体化せず、その場で補間・乗算して加算する

線形補間と勾配の面加算、積とsurface integrationを融合した。修正版の各3runは2.674771→2.599353秒、2.82%短縮。1/2/4ノードの同じ分割のパッチなし版と最終パッチ版で`coefficient.dat`全体のバイト一致を独立照合した。照合対象は保存済みCdファイル全体。一時面場の確保・書込み・読込みを省いたことが短縮の原因と考えられる。

導入`80b5da59`、ビルド修正`fa4f5b04`。[最終0004全文](code-diffs/0004-fuse-gauss-gradient-and-product-integrate.patch)。

`src/finiteVolume/finiteVolume/gradSchemes/gaussGrad/gaussGrad.C`の旧経路は`gradf(tinterpScheme_().interpolate(vsf), name)`である。最初に補間したsurface field全体を作り、その面場を勾配の積分ループで読み直していた。新経路はlinear補間の場合だけ`gradfLinear`→`addLinearFaceSums`へ進む。

```cpp
const Type ssf =
    lambda[facei]*(vfi[owner[facei]] - vfi[neighbour[facei]])
  + vfi[neighbour[facei]];
const GradType Sfssf = Sf[facei]*ssf;
igGrad[owner[facei]] += Sfssf;
igGrad[neighbour[facei]] -= Sfssf;
```

これは実抜粋で、補間の式を代数的に展開し直していない。線形補間以外は従来経路へ戻す。coupled境界では`patchNeighbourField()`と`patchInternalField()`を`lerp`してから境界faceを加算し、非coupled境界は元の境界値を使う。体積除算と`correctBoundaryConditions()`も残る。

二つ目は`fvcSurfaceIntegrate.C`の二引数overload。0003で残っていた積の一時場を消す。

```diff
  fvc::surfaceIntegrateInternal
  (
-     faceFlux*tinterpScheme_().correction(vf)
+     faceFlux,
+     tinterpScheme_().correction(vf)
  );
```

新関数では`abf = ia[facei]*ib[facei]`をownerへ加算、neighbourから減算し、境界面も積を加算した後に`mesh.Vsc()`で割る。積の結果をface数分保存しない。Laplacianではflux correctionを後で保存・使用する経路まで一律に削除せず、該当する式の経路を置換している。

初版は非依存型`surfaceScalarField` / `fvsPatchScalarField`をテンプレート定義内で使ったため、完全な定義がまだ見えていない`PoissonPatchDistMethod.C`の翻訳単位で失敗した。修正版は`template<class Type, class GType>`にし、`GeometricField<GType,...>` / `fvsPatchField<GType>` / `Field<GType>`へ置換した。[失敗後の修正差分](code-diffs/gradient-build-fix.diff)。呼び出し時の`GType`はscalarで、積の算術は変えていない。限られた翻訳単位のコンパイル成功では依存ヘッダーの問題を取り切れなかった例である。

## 7. パッチをbuild inputと成果物の識別に組み込んだ

[0001導入時のビルド差分](code-diffs/patch-build.diff)で、`scripts/build-openfoam.sh`に`patches/openfoam/*.patch`の適用処理を追加し、`scripts/build-inputs-match.sh`のbuild input判定にも同ディレクトリを追加した。番号順に0001→0002→0003→0004を適用する。0004は0003が追加した関数を拡張する。

patch変更時にbuild archiveを更新し、sidecarの`build_definition`、生成した共有ライブラリのhash、case cache identityで測定対象を識別するようにした。[最終bundle監査](final-bundle-audit.json)はその対応を記録する。

<a id="of-8"></a>
## 8. 旧cavity：DIC cell gatherとPCG norm融合

DICのcell gatherとPCGの残差・L1和の融合を適用した。単独候補はそれぞれ8.1490 M FVOPS、統合2run平均8.4573 M。基準5run中央値7.9900 Mに対し+5.85%。比較条件：統合版2run平均と基準5run中央値。詳細は[旧統合実験](../dic-pcg-combined-experiment.md)。出力cellへの繰返し書込みと残差の再読込みを減らしたことが改善要因と考えられる。

対象は旧課題のv2606/icoFoam。ソースrepoは`3_OpenFOAM_Src`、統合は`7d59c05ec`。

### DIC：faceごとのscatterをcellごとの局所変数へ

導入`8ad5ef43f`。[実差分](code-diffs/dic-cell-gather.diff)。対象は`src/OpenFOAM/matrices/lduMatrix/preconditioners/DICPreconditioner/DICPreconditioner.C`の`precondition`。

旧forwardは、初期値を全cellへ書いてから、各faceで次の更新をしていた。

```cpp
wAPtr[uPtr[face]] -= rDPtr[uPtr[face]]*upperPtr[face]*wAPtr[lPtr[face]];
```

新forwardはcellを昇順に回し、`solveScalar w = rDPtr[cell]*rAPtr[cell]`を作る。そのcellへ入る面を`losortStartPtr[cell]`から`losortStartPtr[cell+1]`まで集め、同じ式の寄与を`w`へ引き、最後に一度だけ`wAPtr[cell] = w`とする。backwardはcell降順、`ownerStartPtr`の面範囲も逆順で回す。

狙いは不連続な出力先をfaceごとにread-modify-writeする交通の削減。三角依存を壊さないcell順と、同じ出力cellに対する元のface順を保持する必要がある。代償として`losort/losortStart/ownerStart`のaddressingを生成する。

### PCG：更新した残差をその場でL1和へ

導入`270d7da3a`。[実差分](code-diffs/pcg-residual-norm.diff)。`PCG::scalarSolve`でpsiとrAを更新する既存cell loopに次を加えた。

```cpp
rAPtr[cell] -= alpha*wAPtr[cell];
residualSum += mag(rAPtr[cell]);
```

loop後の`gSumMag(rA, comm)`を`Foam::reduce(residualSum, sumOp<solveScalar>(), UPstream::msgType(), comm)`へ変える。ローカルのrA再走査を省き、MPIのglobal reductionには計算済みの和を渡す。normFactorによる除算と収束判定は残る。

## 9. コードを変えたが採用しなかった例

### 対称AmulのCSR化：条件一行で、キャッシュ生成も有効になる

ソース`e59ba5827`、`lduMatrix/lduMatrix/lduMatrixATmul.C`の`Amul`。[差分](code-diffs/amul-csr.diff)。

```diff
- if (hasLowerCSR())
+ if (symmetric() || hasLowerCSR())
```

対称行列は通常upperのみを保持し、lower CSR cacheを持たないため旧条件ではface scatterへ進む。新条件は既存のcell gather経路へ入り、`lowerCSR()`が初回にupper係数をlosort順へコピーする。以後はcacheを再利用できるが、面当たりscalar一個とaddressingの追加、初回生成が必要になる。1ノード1.5803 M FVOPSとなり不採用。CSR係数とaddressingの追加に伴うメモリ負荷が、gather化の利得を上回った可能性がある。DIC/PCG統合からは除外した。

### GAMG masterCoarsest：一行の設定が集約先を変える

利用側`cc72e444`。[差分](code-diffs/master-coarsest.diff)。`benchmark/occDrivAerStaticMesh/system/fvSolution.fixedIter`の圧力solverへ次を追加した。

```foam
processorAgglomerator masterCoarsest;
```

粗レベルをmasterへ集約する経路を選ぶ。粗系の並列通信を減らす狙いに対し、集約・戻しとmasterのsolveが必要になる。40反復で3.373321秒、基準比+4.95%となり見送り。masterの直列solveとgather/scatter待ちが増えたことが原因と考えられる。後日のper-NUMA/per-node段階集約案は未完了。

他の不採用設定（compiler flags、scotch tleaf、重み付き分割、通信backend）と履歴上の判断は[実験台帳](EXPERIMENTS.md)に残している。原本索引には主要実装の差分を収録した。
