# profile53: CrayPAT stack-sample breakdown of simpleFoam (occDrivAerStaticMesh, 512 ranks, 48 sampled)

Source: `/tmp/claude-1000/-home-tomokazu-2026-APAC-HPC-AI-Tokyo-Rapids-1-OpenFOAM/ac23ae69-8bea-5ae1-b3c1-078738849dc3/scratchpad/profile53/profile/raw/craypat/stack-samples` (48 rank files: 8, 10, 11, 12, 26, 40, 41, 45, 48, 58, 72, 104, 128, 136, 143, 156, 168, 200, 217, 221, 230, 231, 232, 236, 259, 262, 264, 280, 281, 284, 285, 291, 296, 328, 351, 360, 392, 396, 398, 424, 448, 456, 478, 488, 504, 507, 509, 510)

## Sample classification

Each file holds one sample (one call stack of the main thread) per `=== round=N` header, about every 1.2 s. Classes: `inloop` = stack contains `main` and no teardown/startup frame; `teardown` = `~staticFvMesh`/exit handlers reached through `main`; `exit` = no `main` frame, stack is in `exit -> __pat_exit` (CrayPAT writing its data after the solver finished); `error` = eu-stack could not read the process (`Permission denied` / `No such file` on the final round); `startup` = any frame matching `fvMesh::fvMesh\(|polyMesh::polyMesh\(|Time::Time\(|argList::argList|::readField\(|readFields\(|decompos|turbulenceModel::New|RASModel<.*>::New|pressureReference::pressureReference|singlePhaseTransportModel::singlePhaseTransportModel|functionObjectList::read|IOobjectList::IOobjectList|createFields|fvSchemes::fvSchemes|fvSolution::fvSolution|::readMesh` (mesh/field construction, decomposition, model construction).

| class | samples |
|---|---|
| inloop | 2396 |
| exit | 608 |
| error | 48 |
| teardown | 2 |

In-loop samples: **2396** over 48 ranks (49.9 per rank); in-loop sample times span 71.8 s (epoch 1791321211.3 .. 1791321283.1). The first sample of every rank is already inside the time loop (no startup frame was ever observed), so the sampler started after initialisation; the exclusion is therefore effectively 'drop exit/teardown/error samples'.

in-loop samples per rank: 8:51, 10:51, 11:51, 12:51, 26:51, 40:50, 41:50, 45:50, 48:50, 58:51, 72:51, 104:50, 128:52, 136:52, 143:52, 156:52, 168:52, 200:52, 217:52, 221:52, 230:52, 231:52, 232:52, 236:52, 259:48, 262:48, 264:48, 280:48, 281:48, 284:48, 285:48, 291:48, 296:48, 328:48, 351:48, 360:48, 392:49, 396:49, 398:49, 424:49, 448:50, 456:49, 478:49, 488:49, 504:49, 507:49, 509:49, 510:49

Frame names below are demangled symbols with the argument list and return type removed and these abbreviations applied: `Foam::` dropped, `Vector<double>`→`vector`, `Tensor<double>`→`tensor`, `GeometricField<double,fvPatchField,volMesh>`→`volScalarField` (etc.), `outerProduct<vector,double>::type`→`vector`, `outerProduct<vector,vector>::type`→`tensor`, `kOmegaSSTBase<eddyViscosity<RASModel<IncompressibleTurbulenceModel<transportModel>>>>`→`kOmegaSSTBase<...>`. Regexes are applied to the abbreviated names; the 'matched frame strings' lists show the un-abbreviated symbol (minus arguments).

## A. Flat self (leaf-frame) time, top 50

| # | leaf frame | samples | % | cum % | MPI? |
|---|---|---|---|---|---|
| 1 | `MPIDI_Cray_shared_mem_coll_bcast` | 324 | 13.52 | 13.5 | MPI |
| 2 | `smoothSolver::solveGaussSeidelComponents` | 266 | 11.10 | 24.6 |  |
| 3 | `GaussSeidelSmoother::smooth` | 162 | 6.76 | 31.4 |  |
| 4 | `lduMatrix::Amul` | 145 | 6.05 | 37.4 |  |
| 5 | `__memmove_avx_unaligned_erms` | 102 | 4.26 | 41.7 | MPI (libc/UCX helper under MPI) |
| 6 | `syscall` | 82 | 3.42 | 45.1 | MPI (libc/UCX helper under MPI) |
| 7 | `fv::gaussGrad<double>::addLinearFaceSums` | 79 | 3.30 | 48.4 |  |
| 8 | `mlx5_poll_cq_v1` | 60 | 2.50 | 50.9 | MPI |
| 9 | `multiply` | 57 | 2.38 | 53.3 |  |
| 10 | `uct_ud_verbs_iface_progress` | 55 | 2.30 | 55.6 | MPI |
| 11 | `__memset_avx2_unaligned_erms` | 45 | 1.88 | 57.5 |  |
| 12 | `MPIDI_Cray_shared_mem_coll_tree_reduce` | 35 | 1.46 | 58.9 | MPI |
| 13 | `MPIR_Waitall_impl` | 34 | 1.42 | 60.4 | MPI |
| 14 | `process_vm_readv` | 31 | 1.29 | 61.6 | MPI (libc/UCX helper under MPI) |
| 15 | `linearUpwindV<vector>::correction` | 28 | 1.17 | 62.8 |  |
| 16 | `get_sw_cqe` | 28 | 1.17 | 64.0 | MPI |
| 17 | `surfaceInterpolationScheme<vector>::dotInterpolate<surfaceVectorField>` | 26 | 1.09 | 65.1 |  |
| 18 | `lduMatrix::residual` | 25 | 1.04 | 66.1 |  |
| 19 | `surfaceInterpolationScheme<tensor>::dotInterpolate<surfaceVectorField>` | 25 | 1.04 | 67.2 |  |
| 20 | `fv::cellLimitedGrad<vector, minmod>::calcGrad` | 24 | 1.00 | 68.2 |  |
| 21 | `fv::gaussGrad<vector>::addLinearFaceSums` | 23 | 0.96 | 69.1 |  |
| 22 | `fv::gaussGrad<double>::gradfLinear` | 21 | 0.88 | 70.0 |  |
| 23 | `pthread_spin_lock` | 21 | 0.88 | 70.9 | MPI |
| 24 | `uct_mm_iface_progress` | 20 | 0.83 | 71.7 | MPI |
| 25 | `lduInterfaceField::addToInternalField<double>` | 19 | 0.79 | 72.5 |  |
| 26 | `surfaceInterpolationScheme<double>::dotInterpolate<geometricOneField>` | 19 | 0.79 | 73.3 |  |
| 27 | `devTwoSymm` | 19 | 0.79 | 74.1 |  |
| 28 | `ucp_worker_progress` | 18 | 0.75 | 74.8 | MPI |
| 29 | `GAMGSolver::solve` | 17 | 0.71 | 75.5 |  |
| 30 | `GAMGSolver::scale` | 17 | 0.71 | 76.3 |  |
| 31 | `Field<vector>::component` | 17 | 0.71 | 77.0 |  |
| 32 | `fvc::surfaceIntegrateInternal<vector, double>` | 15 | 0.63 | 77.6 |  |
| 33 | `GAMGAgglomeration::prolongField<double>` | 14 | 0.58 | 78.2 |  |
| 34 | `fvc::surfaceIntegrate<double>` | 14 | 0.58 | 78.8 |  |
| 35 | `operator&<double>` | 13 | 0.54 | 79.3 |  |
| 36 | `UList<vector>::deepCopy` | 12 | 0.50 | 79.8 |  |
| 37 | `ucp_tag_probe_nb` | 12 | 0.50 | 80.3 | MPI |
| 38 | `dotdot<tensor, Symmtensor>` | 12 | 0.50 | 80.8 |  |
| 39 | `lduMatrix::sumA` | 12 | 0.50 | 81.3 |  |
| 40 | `fvc::surfaceIntegrate<vector>` | 11 | 0.46 | 81.8 |  |
| 41 | `processorFvPatchField<vector>::initInterfaceMatrixUpdate` | 10 | 0.42 | 82.2 |  |
| 42 | `volVectorField::GeometricField` | 10 | 0.42 | 82.6 |  |
| 43 | `gSumMag<double>` | 10 | 0.42 | 83.0 |  |
| 44 | `lduMatrix::operator-=` | 10 | 0.42 | 83.4 |  |
| 45 | `fvMatrix<vector>::H` | 9 | 0.38 | 83.8 |  |
| 46 | `lduMatrix::sumMagOffDiag` | 9 | 0.38 | 84.2 |  |
| 47 | `add<double, double, fvPatchField, volMesh>` | 9 | 0.38 | 84.6 |  |
| 48 | `lduMatrix::negSumDiag` | 9 | 0.38 | 84.9 |  |
| 49 | `Field<tensor>::operator/=` | 8 | 0.33 | 85.3 |  |
| 50 | `operator-<double, double>` | 8 | 0.33 | 85.6 |  |

Sum of MPI-marked leaf frames: 848 (35.39%). Distinct leaf frames: 189.

## C. Top-level step phases (frames directly under `main`)

`main` return address = call site inside simpleFoam's inlined loop body (UEqn.H, pEqn.H, turbulence->correct(), runTime.loop()). Sorted by address. The layout mostly follows source order, except that the compiler placed the non-orthogonal corrector loop body (fvm::laplacian / setReference / pEqn.solve / pEqn.flux, 0x42740c..0x427655) after `turbulence->correct()` (0x42739c). Phase labels are assigned per callee symbol; symbols that occur at several call sites (`fvc::grad<double>` x3, `fvc::surfaceIntegrateInternal<double>` x2, `operator-<double,double,fvPatchField,volMesh>`) are labelled per address from their position relative to unambiguous neighbours (note column) -- an inference from code layout, not from symbols.

| main ret addr | callee (frame directly under main) | samples | % | phase label | call-site note |
|---|---|---|---|---|---|
| 0x42633c | `Time::loop` | 39 | 1.63 | Time::loop (function objects) |  |
| 0x426450 | `fv::optionList::source<vector>` | 5 | 0.21 | UEqn assembly |  |
| 0x42646e | `IncompressibleTurbulenceModel<...>::divDevReff` | 111 | 4.63 | UEqn assembly |  |
| 0x4264a4 | `fvm::div<vector>` | 75 | 3.13 | UEqn assembly |  |
| 0x4264b2 | `operator+<vector>` | 3 | 0.13 | UEqn assembly |  |
| 0x426520 | `fvMatrix<vector>::operator+=` | 5 | 0.21 | UEqn assembly |  |
| 0x42654c | `operator==<vector>` | 2 | 0.08 | UEqn assembly |  |
| 0x4265a6 | `fvMatrix<vector>::relax` | 18 | 0.75 | UEqn assembly |  |
| 0x4265b5 | `fv::optionList::constrain<vector>` | 25 | 1.04 | UEqn assembly |  |
| 0x4265d1 | `fvc::grad<double>` | 27 | 1.13 | UEqn assembly | UEqn.H: solve(UEqn == -fvc::grad(p)) -- grad(p) evaluated just before solve<vector> at 0x426608 |
| 0x4265f9 | `operator==<vector>` | 11 | 0.46 | UEqn assembly |  |
| 0x426608 | `solve<vector>` | 491 | 20.49 | UEqn solve |  |
| 0x426694 | `fvMatrix<vector>::A` | 3 | 0.13 | pEqn assembly |  |
| 0x4266be | `operator/<fvPatchField, volMesh>` | 1 | 0.04 | pEqn assembly |  |
| 0x4266f0 | `fvMatrix<vector>::H` | 21 | 0.88 | pEqn assembly |  |
| 0x426702 | `operator*<vector, fvPatchField, volMesh>` | 3 | 0.13 | pEqn assembly |  |
| 0x426751 | `fvc::flux` | 4 | 0.17 | pEqn assembly |  |
| 0x4267c2 | `adjustPhi` | 3 | 0.13 | pEqn assembly |  |
| 0x426804 | `fvMatrix<vector>::H1` | 4 | 0.17 | pEqn assembly |  |
| 0x42684b | `operator/<fvPatchField, volMesh>` | 1 | 0.04 | pEqn assembly |  |
| 0x426943 | `fvc::snGrad<double>` | 48 | 2.00 | pEqn assembly |  |
| 0x42696f | `operator-<double, double, fvPatchField, volMesh>` | 1 | 0.04 | pEqn assembly | pEqn.H consistent: rAtU() - rAU (between snGrad(p) and interpolate) |
| 0x426a34 | `surfaceInterpolationScheme<double>::interpolate` | 4 | 0.17 | pEqn assembly |  |
| 0x426ace | `operator*<fvsPatchField, surfaceMesh>` | 2 | 0.08 | pEqn assembly |  |
| 0x426ae0 | `operator*<fvsPatchField, surfaceMesh>` | 2 | 0.08 | pEqn assembly |  |
| 0x426aef | `surfaceScalarField::operator+=` | 1 | 0.04 | pEqn assembly |  |
| 0x426b2e | `fvc::grad<double>` | 2 | 0.08 | pEqn assembly | pEqn.H consistent: HbyA -= (rAU - rAtU())*fvc::grad(p) (right after phiHbyA += ...) |
| 0x4270a8 | `fvc::surfaceIntegrateInternal<double>` | 1 | 0.04 | continuityErrs | continuityErrs.H: fvc::div(phi) inlined to surfaceIntegrateInternal (followed by mag/weightedAverage) |
| 0x42710e | `mag<double, volMesh>` | 1 | 0.04 | continuityErrs |  |
| 0x427148 | `DimensionedField<double, volMesh>::weightedAverage` | 3 | 0.13 | continuityErrs |  |
| 0x4271c2 | `DimensionedField<double, volMesh>::weightedAverage` | 2 | 0.08 | continuityErrs |  |
| 0x4272a3 | `fvc::grad<double>` | 7 | 0.29 | U/phi correction | pEqn.H: U = HbyA - rAtU()*fvc::grad(p) (followed by operator- at 0x4272cf) |
| 0x4272cf | `operator-<vector, vector, fvPatchField, volMesh>` | 1 | 0.04 | U/phi correction |  |
| 0x42739c | `kOmegaSSTBase<...>::correct` | 644 | 26.88 | turbulence->correct |  |
| 0x4273e7 | `fvc::surfaceIntegrateInternal<double>` | 2 | 0.08 | pEqn assembly | pEqn.H non-orth loop: fvc::div(phiHbyA) inlined to surfaceIntegrateInternal (just before fvm::laplacian at 0x42740c) |
| 0x42740c | `fvm::laplacian<double, double>` | 30 | 1.25 | pEqn assembly |  |
| 0x427485 | `volScalarField::needReference` | 25 | 1.04 | pEqn assembly |  |
| 0x4274a2 | `fvMatrix<double>::solve` | 762 | 31.80 | pEqn solve |  |
| 0x427643 | `fvMatrix<double>::flux` | 4 | 0.17 | U/phi correction |  |
| 0x427655 | `operator-<double, double, fvsPatchField, surfaceMesh>` | 2 | 0.08 | U/phi correction |  |

### Phase totals

| phase | samples | % |
|---|---|---|
| pEqn solve | 762 | 31.80 |
| turbulence->correct | 644 | 26.88 |
| UEqn solve | 491 | 20.49 |
| UEqn assembly | 282 | 11.77 |
| pEqn assembly | 157 | 6.55 |
| Time::loop (function objects) | 39 | 1.63 |
| U/phi correction | 14 | 0.58 |
| continuityErrs | 7 | 0.29 |

## B. Inclusive call-path shares

A sample counts for an item if any frame on its stack (below `main`) matches the regex. Percentages are of the 2396 in-loop samples. 'by step phase' uses the C labels.

### B1. Gauss gradient (`fv::gaussGrad<T>::calcGrad` / `gradf*`)

**B1 total gaussGrad calcGrad/gradf** regex `fv::gaussGrad<.*>::(calcGrad|gradf\w*)`: **206** samples = **8.60%**
matched frame strings (frame occurrences): `Foam::fv::gaussGrad<double>::calcGrad` (160); `Foam::fv::gaussGrad<double>::gradfLinear` (154); `Foam::fv::gaussGrad<Foam::Vector<double> >::calcGrad` (46)
by step phase: turbulence->correct 123 (5.13%), pEqn assembly 49 (2.05%), UEqn assembly 27 (1.13%), U/phi correction 7 (0.29%)

Split by nearest distinguishing caller (walk from the gaussGrad frame towards `main`, skipping grad wrappers `^(fvc::grad<|fv::gradScheme<|fv::gaussGrad<|fv::cellLimitedGrad<|tmp<|volVectorField::operator=|volTensorField::operator=|GeometricField)`; first match of correctedSnGrad::correction|fullGradCorrection / kOmegaSST / linearUpwind|ConvectionScheme|fvm::div / other non-wrapper; if `main` is reached first it is (c)). Note: the scalar laplacian's non-orthogonal correction appears as `correctedSnGrad<double>::correction -> fullGradCorrection -> fvc::grad -> gaussGrad<double>::calcGrad`.

| caller category | gradient type | samples | % |
|---|---|---|---|
| (a) correctedSnGrad::correction / fullGradCorrection | all | 84 | 3.51 |
| (a) correctedSnGrad::correction / fullGradCorrection | scalar grad (gaussGrad<double>, result vector) | 84 | 3.51 |
| (b) kOmegaSSTBase::correct | all | 86 | 3.59 |
| (b) kOmegaSSTBase::correct | vector grad (gaussGrad<vector>, result tensor) | 46 | 1.92 |
| (b) kOmegaSSTBase::correct | scalar grad (gaussGrad<double>, result vector) | 40 | 1.67 |
| (c) simpleFoam main directly (fvc::grad(p)) | all | 36 | 1.50 |
| (c) simpleFoam main directly (fvc::grad(p)) | scalar grad (gaussGrad<double>, result vector) | 36 | 1.50 |

| gradient type (template argument of gaussGrad) | samples | % |
|---|---|---|
| scalar grad (gaussGrad<double>, result vector) | 160 | 6.68 |
| vector grad (gaussGrad<vector>, result tensor) | 46 | 1.92 |

Deepest gaussGrad-related frame reached (which part of the gradient):

| innermost gaussGrad frame | samples | % |
|---|---|---|
| `fv::gaussGrad<double>::addLinearFaceSums  [leaf]` | 79 | 3.30 |
| `fv::gaussGrad<double>::gradfLinear` | 49 | 2.05 |
| `fv::gaussGrad<vector>::addLinearFaceSums  [leaf]` | 23 | 0.96 |
| `fv::gaussGrad<double>::gradfLinear  [leaf]` | 21 | 0.88 |
| `fv::gaussGrad<vector>::calcGrad` | 19 | 0.79 |
| `fv::gaussGrad<double>::correctBoundaryConditions  [leaf]` | 6 | 0.25 |
| `fv::gaussGrad<double>::addLinearFaceSums` | 5 | 0.21 |
| `fv::gaussGrad<vector>::addLinearFaceSums` | 4 | 0.17 |

**Direct children of `fv::gaussGrad<double>::calcGrad`** (regex `fv::gaussGrad<double>::calcGrad`, 160 samples = 6.68%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::gaussGrad<double>::gradfLinear` | 154 | 6.43 | 96.2 |
| `fv::gaussGrad<double>::correctBoundaryConditions` | 6 | 0.25 | 3.8 |

**Direct children of `fv::gaussGrad<vector>::calcGrad`** (regex `fv::gaussGrad<vector>::calcGrad`, 46 samples = 1.92%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::gaussGrad<vector>::addLinearFaceSums` | 27 | 1.13 | 58.7 |
| `Field<tensor>::operator/=` | 8 | 0.33 | 17.4 |
| `GeometricBoundaryField<tensor, fvPatchField, volMesh>::evaluate` | 8 | 0.33 | 17.4 |
| `volTensorField::operator=` | 3 | 0.13 | 6.5 |

**fvc::grad<vector> via cellLimitedGrad<vector,minmod>::calcGrad (grad(U), includes limiter)** regex `fv::cellLimitedGrad<vector, minmod>::calcGrad`: **100** samples = **4.17%**
matched frame strings (frame occurrences): `Foam::fv::cellLimitedGrad<Foam::Vector<double>, Foam::fv::gradientLimiters::minmod>::calcGrad` (100)
by step phase: turbulence->correct 100 (4.17%)

**Direct children of `fv::cellLimitedGrad<vector, minmod>::calcGrad`** (regex `fv::cellLimitedGrad<vector, minmod>::calcGrad`, 100 samples = 4.17%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::gaussGrad<vector>::calcGrad` | 46 | 1.92 | 46.0 |
| `<self (leaf)>` | 24 | 1.00 | 24.0 |
| `fv::gaussGrad<vector>::correctBoundaryConditions` | 13 | 0.54 | 13.0 |
| `UList<vector>::deepCopy` | 5 | 0.21 | 5.0 |
| `GeometricBoundaryField<tensor, fvPatchField, volMesh>::evaluate` | 3 | 0.13 | 3.0 |
| `fv::cellLimitedGrad<vector, minmod>::limitGradient` | 3 | 0.13 | 3.0 |
| `List<vector>::List` | 2 | 0.08 | 2.0 |
| `Field<vector>::operator-=` | 2 | 0.08 | 2.0 |
| `Field<vector>::Field` | 1 | 0.04 | 1.0 |
| `operator&<double>` | 1 | 0.04 | 1.0 |

**any fvc::grad<...> (all gradient evaluations incl. limiter)** regex `^fvc::grad<`: **176** samples = **7.35%**
matched frame strings (frame occurrences): `Foam::fvc::grad<Foam::Vector<double> >` (100); `Foam::fvc::grad<double>` (76)
by step phase: turbulence->correct 140 (5.84%), UEqn assembly 27 (1.13%), U/phi correction 7 (0.29%), pEqn assembly 2 (0.08%)

### B2. fvMatrix / lduMatrix H and H1

**fvMatrix<vector>::H()** regex `^fvMatrix<vector>::H$`: **21** samples = **0.88%**
matched frame strings (frame occurrences): `Foam::fvMatrix<Foam::Vector<double> >::H` (21)
by step phase: pEqn assembly 21 (0.88%)

**fvMatrix<...>::H1()** regex `^fvMatrix<.*>::H1$`: **4** samples = **0.17%**
matched frame strings (frame occurrences): `Foam::fvMatrix<Foam::Vector<double> >::H1` (4)
by step phase: pEqn assembly 4 (0.17%)

**lduMatrix::H<T>** regex `^lduMatrix::H<`: **6** samples = **0.25%**
matched frame strings (frame occurrences): `Foam::lduMatrix::H<Foam::Vector<double> >` (6)
by step phase: pEqn assembly 6 (0.25%)

**lduMatrix::H1** regex `^lduMatrix::H1$`: **2** samples = **0.08%**
matched frame strings (frame occurrences): `Foam::lduMatrix::H1` (2)
by step phase: pEqn assembly 2 (0.08%)

**Direct children of `fvMatrix<vector>::H`** (regex `^fvMatrix<vector>::H$`, 21 samples = 0.88%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `<self (leaf)>` | 9 | 0.38 | 42.9 |
| `lduMatrix::H<vector>` | 6 | 0.25 | 28.6 |
| `Field<vector>::operator+=` | 2 | 0.08 | 9.5 |
| `operator+<vector, vector>` | 1 | 0.04 | 4.8 |
| `GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate` | 1 | 0.04 | 4.8 |
| `operator*` | 1 | 0.04 | 4.8 |
| `__memset_avx2_unaligned_erms` | 1 | 0.04 | 4.8 |

### B3. pEqn assembly pieces

`constrainHbyA`, `constrainPressure` and `fvc::interpolate` never appear as frames in any sample (inlined into `main`; the body of fvc::interpolate shows up as `surfaceInterpolationScheme<double>::interpolate`, and fvc::div(phiHbyA) as `fvc::surfaceIntegrateInternal<double>` at call site 0x4273e7). They are reported as 0 or via those frames.

**fvc::flux** regex `^fvc::flux$`: **4** samples = **0.17%**
matched frame strings (frame occurrences): `Foam::fvc::flux` (4)
by step phase: pEqn assembly 4 (0.17%)

**fvMatrix<double>::flux (pEqn.flux())** regex `^fvMatrix<double>::flux$`: **4** samples = **0.17%**
matched frame strings (frame occurrences): `Foam::fvMatrix<double>::flux` (4)
by step phase: U/phi correction 4 (0.17%)

**constrainHbyA** regex `^constrainHbyA`: **0** samples = **0.00%**
matched frame strings (frame occurrences): 

**fvc::interpolate** regex `^fvc::interpolate`: **0** samples = **0.00%**
matched frame strings (frame occurrences): 

**surfaceInterpolationScheme<double>::interpolate (fvc::interpolate inlined caller)** regex `^surfaceInterpolationScheme<double>::interpolate`: **19** samples = **0.79%**
matched frame strings (frame occurrences): `Foam::surfaceInterpolationScheme<double>::interpolate` (19)
by step phase: pEqn assembly 8 (0.33%), turbulence->correct 7 (0.29%), UEqn assembly 4 (0.17%)

**fvc::snGrad** regex `^fvc::snGrad`: **48** samples = **2.00%**
matched frame strings (frame occurrences): `Foam::fvc::snGrad<double>` (48)
by step phase: pEqn assembly 48 (2.00%)

**fvc::div** regex `^fvc::div<`: **41** samples = **1.71%**
matched frame strings (frame occurrences): `Foam::fvc::div<Foam::Tensor<double> >` (82)
by step phase: UEqn assembly 41 (1.71%)

**adjustPhi** regex `^adjustPhi`: **3** samples = **0.13%**
matched frame strings (frame occurrences): `Foam::adjustPhi` (3)
by step phase: pEqn assembly 3 (0.13%)

**constrainPressure** regex `^constrainPressure`: **0** samples = **0.00%**
matched frame strings (frame occurrences): 

**fvm::laplacian<double,double> (pEqn operator)** regex `^fvm::laplacian<double, double>`: **128** samples = **5.34%**
matched frame strings (frame occurrences): `Foam::fvm::laplacian<double, double>` (226)
by step phase: turbulence->correct 98 (4.09%), pEqn assembly 30 (1.25%)

**volScalarField::needReference (pEqn.setReference allreduce)** regex `needReference`: **28** samples = **1.17%**
matched frame strings (frame occurrences): `Foam::GeometricField<double, Foam::fvPatchField, Foam::volMesh>::needReference` (28)
by step phase: pEqn assembly 28 (1.17%)

**fvc::div(phiHbyA) (inlined; `fvc::surfaceIntegrateInternal<double>` at main call site 0x4273e7)**: 2 samples = 0.08%

**Union of the B3 items (all call sites, including the fvm::laplacian/fvc::div inside kOmegaSST and divDevReff)**: 263 samples = 10.98%

**pEqn assembly phase total (C label, everything under main between UEqn solve and pEqn solve)**: 157 = 6.55%; its top-level callees: `fvc::snGrad<double>` 48, `fvm::laplacian<double, double>` 30, `volScalarField::needReference` 25, `fvMatrix<vector>::H` 21, `surfaceInterpolationScheme<double>::interpolate` 4, `fvc::flux` 4, `operator*<fvsPatchField, surfaceMesh>` 4, `fvMatrix<vector>::H1` 4, `adjustPhi` 3, `fvMatrix<vector>::A` 3, `operator*<vector, fvPatchField, volMesh>` 3, `fvc::surfaceIntegrateInternal<double>` 2, `fvc::grad<double>` 2, `operator/<fvPatchField, volMesh>` 2, `operator-<double, double, fvPatchField, volMesh>` 1, `surfaceScalarField::operator+=` 1

### B4. bound / fvc::average / surfaceSum

**Foam::bound** regex `^bound$`: **11** samples = **0.46%**
matched frame strings (frame occurrences): `Foam::bound` (11)
by step phase: turbulence->correct 11 (0.46%)

**fvc::average** regex `^fvc::average`: **6** samples = **0.25%**
matched frame strings (frame occurrences): `Foam::fvc::average<double>` (11)
by step phase: turbulence->correct 6 (0.25%)

**fvc::surfaceSum** regex `^fvc::surfaceSum`: **1** samples = **0.04%**
matched frame strings (frame occurrences): `Foam::fvc::surfaceSum<double>` (1)
by step phase: turbulence->correct 1 (0.04%)

### B5. GaussSeidelSmoother::smooth

**GaussSeidelSmoother::smooth (incl. scalarSmooth)** regex `GaussSeidelSmoother::(smooth|scalarSmooth)`: **275** samples = **11.48%**
matched frame strings (frame occurrences): `Foam::GaussSeidelSmoother::smooth` (387); `Foam::GaussSeidelSmoother::scalarSmooth` (163)
by step phase: pEqn solve 228 (9.52%), turbulence->correct 47 (1.96%)

Leaf frames beneath smooth (the `under MPI` column says whether an MPI/UCX frame lies between the leaf and smooth):

| leaf frame | under MPI | samples | % in-loop | % of smooth |
|---|---|---|---|---|
| `GaussSeidelSmoother::smooth` |  | 162 | 6.76 | 58.9 |
| `syscall` | yes | 36 | 1.50 | 13.1 |
| `__memmove_avx_unaligned_erms` |  | 16 | 0.67 | 5.8 |
| `MPIR_Waitall_impl` | yes | 11 | 0.46 | 4.0 |
| `uct_ud_verbs_iface_progress` | yes | 8 | 0.33 | 2.9 |
| `mlx5_poll_cq_v1` | yes | 8 | 0.33 | 2.9 |
| `get_sw_cqe` | yes | 5 | 0.21 | 1.8 |
| `pthread_spin_lock` | yes | 4 | 0.17 | 1.5 |
| `process_vm_readv` | yes | 4 | 0.17 | 1.5 |
| `lduInterfaceField::addToInternalField<double>` |  | 3 | 0.13 | 1.1 |
| `uct_mm_iface_progress` | yes | 3 | 0.13 | 1.1 |
| `ucp_tag_probe_nb` | yes | 2 | 0.08 | 0.7 |
| `__memmove_avx_unaligned_erms` | yes | 2 | 0.08 | 0.7 |
| `processorFvPatchField<double>::initInterfaceMatrixUpdate` |  | 2 | 0.08 | 0.7 |
| `ucp_worker_progress` | yes | 2 | 0.08 | 0.7 |
| `ucp_eager_only_handler` | yes | 1 | 0.04 | 0.4 |
| `__pat_track_msg_collection_enabled` | yes | 1 | 0.04 | 0.4 |
| `__pat_trsup_trace_nonblocking_send_rtsum` | yes | 1 | 0.04 | 0.4 |
| `__pat_update_msg_dest_data` | yes | 1 | 0.04 | 0.4 |
| `__pat_update_send_message_data` | yes | 1 | 0.04 | 0.4 |
| `processorGAMGInterfaceField::initInterfaceMatrixUpdate` |  | 1 | 0.04 | 0.4 |
| `pthread_spin_init` | yes | 1 | 0.04 | 0.4 |

Copy-type leaves (regex `memmove|memcpy|memset|Field<double>::operator=|UList<double>::operator=|deepCopy|::assign`) directly in OpenFOAM code beneath smooth (bPrime = source etc.): 16 samples = 0.67% in-loop = 5.8% of smooth; copy-type leaves inside MPI/UCX beneath smooth: 2; all MPI beneath smooth: 91 = 3.80% in-loop = 33.1% of smooth.

callers of those OpenFOAM copy leaves: `GaussSeidelSmoother::smooth <- GaussSeidelSmoother::smooth <- GAMGSolver::Vcycle` 8, `GaussSeidelSmoother::smooth <- GaussSeidelSmoother::smooth <- smoothSolver::solve` 4, `GaussSeidelSmoother::smooth <- GaussSeidelSmoother::scalarSmooth <- GAMGSolver::Vcycle` 4

**Direct children of `GaussSeidelSmoother::smooth (innermost smooth frame; the static smooth() overload calls the member smooth())`** (regex `GaussSeidelSmoother::smooth$`, 275 samples = 11.48%; child = frame immediately inside the innermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `<self (leaf)>` | 162 | 6.76 | 58.9 |
| `lduMatrix::updateMatrixInterfaces` | 65 | 2.71 | 23.6 |
| `lduMatrix::initMatrixInterfaces` | 32 | 1.34 | 11.6 |
| `__memmove_avx_unaligned_erms` | 16 | 0.67 | 5.8 |

**Direct children of `GaussSeidelSmoother::scalarSmooth`** (regex `GaussSeidelSmoother::scalarSmooth$`, 163 samples = 6.80%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `GaussSeidelSmoother::smooth` | 163 | 6.80 | 100.0 |

### B6. GAMG (p equation)

**GAMGSolver::solve** regex `^GAMGSolver::solve$`: **752** samples = **31.39%**
matched frame strings (frame occurrences): `Foam::GAMGSolver::solve` (752)
by step phase: pEqn solve 752 (31.39%)

**GAMGSolver::Vcycle** regex `^GAMGSolver::Vcycle$`: **640** samples = **26.71%**
matched frame strings (frame occurrences): `Foam::GAMGSolver::Vcycle` (640)
by step phase: pEqn solve 640 (26.71%)

**GAMGSolver::scale** regex `^GAMGSolver::scale$`: **228** samples = **9.52%**
matched frame strings (frame occurrences): `Foam::GAMGSolver::scale` (228)
by step phase: pEqn solve 228 (9.52%)

**GAMGSolver::solveCoarsestLevel** regex `^GAMGSolver::solveCoarsestLevel$`: **158** samples = **6.59%**
matched frame strings (frame occurrences): `Foam::GAMGSolver::solveCoarsestLevel` (158)
by step phase: pEqn solve 158 (6.59%)

**PCG::scalarSolve (coarsest-level solver)** regex `^PCG::scalarSolve$`: **157** samples = **6.55%**
matched frame strings (frame occurrences): `Foam::PCG::scalarSolve` (157)
by step phase: pEqn solve 157 (6.55%)

**GAMGAgglomeration::restrictField** regex `GAMGAgglomeration::restrictField`: **8** samples = **0.33%**
matched frame strings (frame occurrences): `Foam::GAMGAgglomeration::restrictField<double>` (8)
by step phase: pEqn solve 8 (0.33%)

**GAMGAgglomeration::prolongField** regex `GAMGAgglomeration::prolongField`: **14** samples = **0.58%**
matched frame strings (frame occurrences): `Foam::GAMGAgglomeration::prolongField<double>` (14)
by step phase: pEqn solve 14 (0.58%)

**GAMGSolver::interpolate** regex `^GAMGSolver::interpolate`: **0** samples = **0.00%**
matched frame strings (frame occurrences): 

**GAMGSolver constructor / agglomerateMatrix / New** regex `GAMGSolver::GAMGSolver|agglomerateMatrix|ConstructorToTable<GAMGSolver>`: **6** samples = **0.25%**
matched frame strings (frame occurrences): `Foam::GAMGSolver::agglomerateMatrix` (6); `Foam::GAMGSolver::GAMGSolver` (6); `Foam::lduMatrix::solver::addsymMatrixConstructorToTable<Foam::GAMGSolver>::New` (6)
by step phase: pEqn solve 6 (0.25%)

**GAMGSolver::~GAMGSolver** regex `GAMGSolver::~GAMGSolver`: **1** samples = **0.04%**
matched frame strings (frame occurrences): `Foam::GAMGSolver::~GAMGSolver` (2)
by step phase: pEqn solve 1 (0.04%)

**Direct children of `GAMGSolver::solve`** (regex `^GAMGSolver::solve$`, 752 samples = 31.39%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `GAMGSolver::Vcycle` | 640 | 26.71 | 85.1 |
| `lduMatrix::Amul` | 65 | 2.71 | 8.6 |
| `gSumMag<double>` | 27 | 1.13 | 3.6 |
| `<self (leaf)>` | 17 | 0.71 | 2.3 |
| `lduMatrix::solver::normFactor` | 2 | 0.08 | 0.3 |
| `PtrList<Field<double>>::~PtrList` | 1 | 0.04 | 0.1 |

**Direct children of `GAMGSolver::Vcycle`** (regex `^GAMGSolver::Vcycle$`, 640 samples = 26.71%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `GAMGSolver::scale` | 228 | 9.52 | 35.6 |
| `GaussSeidelSmoother::scalarSmooth` | 163 | 6.80 | 25.5 |
| `GAMGSolver::solveCoarsestLevel` | 158 | 6.59 | 24.7 |
| `GaussSeidelSmoother::smooth` | 65 | 2.71 | 10.2 |
| `GAMGAgglomeration::prolongField<double>` | 14 | 0.58 | 2.2 |
| `GAMGAgglomeration::restrictField<double>` | 8 | 0.33 | 1.2 |
| `<self (leaf)>` | 4 | 0.17 | 0.6 |

**Direct children of `GAMGSolver::scale`** (regex `^GAMGSolver::scale$`, 228 samples = 9.52%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `PstreamDetail::allReduce<void>` | 106 | 4.42 | 46.5 |
| `lduMatrix::Amul` | 105 | 4.38 | 46.1 |
| `<self (leaf)>` | 17 | 0.71 | 7.5 |

**Direct children of `GAMGSolver::solveCoarsestLevel`** (regex `^GAMGSolver::solveCoarsestLevel$`, 158 samples = 6.59%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `PCG::scalarSolve` | 157 | 6.55 | 99.4 |
| `<self (leaf)>` | 1 | 0.04 | 0.6 |

**Direct children of `PCG::scalarSolve`** (regex `^PCG::scalarSolve$`, 157 samples = 6.55%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `gSumProd<double>` | 97 | 4.05 | 61.8 |
| `lduMatrix::Amul` | 37 | 1.54 | 23.6 |
| `gSumMag<double>` | 15 | 0.63 | 9.6 |
| `lduMatrix::solver::normFactor` | 7 | 0.29 | 4.5 |
| `DICPreconditioner::precondition` | 1 | 0.04 | 0.6 |

### B7. lduMatrix kernels

**lduMatrix::Amul** regex `^lduMatrix::Amul$`: **248** samples = **10.35%**
matched frame strings (frame occurrences): `Foam::lduMatrix::Amul` (248)
by step phase: pEqn solve 207 (8.64%), turbulence->correct 31 (1.29%), UEqn solve 10 (0.42%)

**lduMatrix::residual** regex `^lduMatrix::residual$`: **28** samples = **1.17%**
matched frame strings (frame occurrences): `Foam::lduMatrix::residual` (28)
by step phase: turbulence->correct 28 (1.17%)

**lduMatrix::sumA** regex `^lduMatrix::sumA$`: **12** samples = **0.50%**
matched frame strings (frame occurrences): `Foam::lduMatrix::sumA` (12)
by step phase: turbulence->correct 6 (0.25%), UEqn solve 5 (0.21%), pEqn solve 1 (0.04%)

**lduMatrix::solver::normFactor** regex `normFactor`: **96** samples = **4.01%**
matched frame strings (frame occurrences): `Foam::lduMatrix::solver::normFactor` (96)
by step phase: turbulence->correct 61 (2.55%), UEqn solve 26 (1.09%), pEqn solve 9 (0.38%)

**lduMatrix::negSumDiag** regex `negSumDiag`: **12** samples = **0.50%**
matched frame strings (frame occurrences): `Foam::lduMatrix::negSumDiag` (12)
by step phase: turbulence->correct 7 (0.29%), UEqn assembly 3 (0.13%), pEqn assembly 2 (0.08%)

**Direct children of `lduMatrix::Amul`** (regex `^lduMatrix::Amul$`, 248 samples = 10.35%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `<self (leaf)>` | 145 | 6.05 | 58.5 |
| `lduMatrix::updateMatrixInterfaces` | 68 | 2.84 | 27.4 |
| `lduMatrix::initMatrixInterfaces` | 35 | 1.46 | 14.1 |

**Direct children of `lduMatrix::residual`** (regex `^lduMatrix::residual$`, 28 samples = 1.17%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `<self (leaf)>` | 25 | 1.04 | 89.3 |
| `lduMatrix::updateMatrixInterfaces` | 2 | 0.08 | 7.1 |
| `lduMatrix::initMatrixInterfaces` | 1 | 0.04 | 3.6 |

### B8. smoothSolver (U, k, omega)

**smoothSolver::solve** regex `^smoothSolver::solve$`: **196** samples = **8.18%**
matched frame strings (frame occurrences): `Foam::smoothSolver::solve` (196)
by step phase: turbulence->correct 196 (8.18%)

**smoothSolver::solveGaussSeidelComponents** regex `^smoothSolver::solveGaussSeidelComponents`: **455** samples = **18.99%**
matched frame strings (frame occurrences): `Foam::smoothSolver::solveGaussSeidelComponents` (455)
by step phase: UEqn solve 455 (18.99%)

**Direct children of `smoothSolver::solve`** (regex `^smoothSolver::solve$`, 196 samples = 8.18%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `lduMatrix::solver::normFactor` | 61 | 2.55 | 31.1 |
| `GaussSeidelSmoother::smooth` | 47 | 1.96 | 24.0 |
| `lduMatrix::Amul` | 31 | 1.29 | 15.8 |
| `lduMatrix::residual` | 28 | 1.17 | 14.3 |
| `gSumMag<double>` | 28 | 1.17 | 14.3 |
| `__memmove_avx_unaligned_erms` | 1 | 0.04 | 0.5 |

**Direct children of `smoothSolver::solveGaussSeidelComponents`** (regex `^smoothSolver::solveGaussSeidelComponents`, 455 samples = 18.99%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `<self (leaf)>` | 266 | 11.10 | 58.5 |
| `lduMatrix::updateMatrixInterfaces` | 58 | 2.42 | 12.7 |
| `__memmove_avx_unaligned_erms` | 46 | 1.92 | 10.1 |
| `gSumMag<double>` | 29 | 1.21 | 6.4 |
| `lduMatrix::solver::normFactor` | 26 | 1.09 | 5.7 |
| `lduMatrix::initMatrixInterfaces` | 16 | 0.67 | 3.5 |
| `lduMatrix::Amul` | 10 | 0.42 | 2.2 |
| `operator-<double, double>` | 4 | 0.17 | 0.9 |

**Direct children of `fvMatrix<vector>::solveSegregated (UEqn)`** (regex `^fvMatrix<vector>::solveSegregated$`, 491 samples = 20.49%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `smoothSolver::solveGaussSeidelComponents` | 455 | 18.99 | 92.7 |
| `Field<vector>::component` | 17 | 0.71 | 3.5 |
| `__memmove_avx_unaligned_erms` | 5 | 0.21 | 1.0 |
| `lduMatrix::updateMatrixInterfaces` | 3 | 0.13 | 0.6 |
| `<self (leaf)>` | 3 | 0.13 | 0.6 |
| `fvMatrix<vector>::addBoundarySource` | 2 | 0.08 | 0.4 |
| `UList<vector>::deepCopy` | 2 | 0.08 | 0.4 |
| `lduMatrix::initMatrixInterfaces` | 1 | 0.04 | 0.2 |
| `fvMatrix<vector>::addBoundaryDiag` | 1 | 0.04 | 0.2 |
| `GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate` | 1 | 0.04 | 0.2 |
| `FieldField<Field, vector>::component` | 1 | 0.04 | 0.2 |

**Direct children of `fvMatrix<double>::solveSegregated (p, k, omega)`** (regex `^fvMatrix<double>::solveSegregated$`, 960 samples = 40.07%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `GAMGSolver::solve` | 752 | 31.39 | 78.3 |
| `smoothSolver::solve` | 196 | 8.18 | 20.4 |
| `lduMatrix::solver::New` | 6 | 0.25 | 0.6 |
| `__memmove_avx_unaligned_erms` | 3 | 0.13 | 0.3 |
| `GeometricBoundaryField<double, fvPatchField, volMesh>::evaluate` | 2 | 0.08 | 0.2 |
| `GAMGSolver::~GAMGSolver` | 1 | 0.04 | 0.1 |

### B9. kOmegaSSTBase::correct

**kOmegaSSTBase::correct total** regex `kOmegaSSTBase<\.\.\.>::correct$`: **644** samples = **26.88%**
matched frame strings (frame occurrences): `Foam::kOmegaSSTBase<Foam::eddyViscosity<Foam::RASModel<Foam::IncompressibleTurbulenceModel<Foam::transportModel> > > >::correct` (644)
by step phase: turbulence->correct 644 (26.88%)

| sub-item (frames inside correct) | regex | samples | % in-loop | % of correct |
|---|---|---|---|---|
| F1 | `kOmegaSSTBase<\.\.\.>::F1$` | 11 | 0.46 | 1.7 |
| F2 | `kOmegaSSTBase<\.\.\.>::F2$` | 10 | 0.42 | 1.6 |
| F23 | `kOmegaSSTBase<\.\.\.>::F23$` | 9 | 0.38 | 1.4 |
| S2 | `kOmegaSSTBase<\.\.\.>::S2$` | 8 | 0.33 | 1.2 |
| GbyNu0 | `kOmegaSSTBase<\.\.\.>::GbyNu0$` | 26 | 1.09 | 4.0 |
| Pk | `kOmegaSSTBase<\.\.\.>::Pk$` | 1 | 0.04 | 0.2 |
| correctNut | `kOmegaSSTBase<\.\.\.>::correctNut$` | 13 | 0.54 | 2.0 |
| kSource/omegaSource | `kOmegaSSTBase<\.\.\.>::(kSource|omegaSource)$` | 3 | 0.13 | 0.5 |
| fvc::grad (CDkOmega: grad(k)&grad(omega), tgradU) | `^fvc::grad<` | 140 | 5.84 | 21.7 |
| fvc::grad<double> (grad(k), grad(omega)) | `^fvc::grad<double>` | 40 | 1.67 | 6.2 |
| fvc::grad<vector> (tgradU) | `^fvc::grad<vector>` | 100 | 4.17 | 15.5 |
| operator&<...> (CDkOmega dot product) | `^operator&` | 18 | 0.75 | 2.8 |
| fvm::laplacian | `^fvm::laplacian<` | 98 | 4.09 | 15.2 |
| fvm::div | `^fvm::div<` | 26 | 1.09 | 4.0 |
| fvm::Sp | `^fvm::Sp<` | 5 | 0.21 | 0.8 |
| fvm::SuSp | `^fvm::SuSp<` | 6 | 0.25 | 0.9 |
| solve<double> (k and omega solves, incl. relax? no: solve only) | `^solve<double>$` | 198 | 8.26 | 30.7 |
| fvMatrix<double>::relax | `^fvMatrix<double>::relax$` | 12 | 0.50 | 1.9 |
| bound | `^bound$` | 11 | 0.46 | 1.7 |
| fvMatrix<double>::boundaryManipulate | `boundaryManipulate` | 9 | 0.38 | 1.4 |
| fvMatrix<double>::setValues* | `setValues` | 9 | 0.38 | 1.4 |
| MPI (any MPI frame) inside correct | (any frame matching MPI regex) | 147 | 6.14 | 22.8 |

**Direct children of `kOmegaSSTBase<...>::correct`** (regex `kOmegaSSTBase<\.\.\.>::correct$`, 644 samples = 26.88%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `solve<double>` | 198 | 8.26 | 30.7 |
| `fvc::grad<vector>` | 100 | 4.17 | 15.5 |
| `fvm::laplacian<double, double>` | 98 | 4.09 | 15.2 |
| `fvc::grad<double>` | 40 | 1.67 | 6.2 |
| `operator+<double>` | 26 | 1.09 | 4.0 |
| `fvm::div<double>` | 26 | 1.09 | 4.0 |
| `kOmegaSSTBase<...>::GbyNu0` | 26 | 1.09 | 4.0 |
| `kOmegaSSTBase<...>::correctNut` | 13 | 0.54 | 2.0 |
| `operator-<double>` | 12 | 0.50 | 1.9 |
| `fvMatrix<double>::relax` | 12 | 0.50 | 1.9 |
| `bound` | 11 | 0.46 | 1.7 |
| `kOmegaSSTBase<...>::F1` | 11 | 0.46 | 1.7 |
| `fvMatrix<double>::boundaryManipulate` | 9 | 0.38 | 1.4 |
| `kOmegaSSTBase<...>::F23` | 9 | 0.38 | 1.4 |
| `kOmegaSSTBase<...>::S2` | 8 | 0.33 | 1.2 |
| `GeometricBoundaryField<double, fvPatchField, volMesh>::updateCoeffs` | 7 | 0.29 | 1.1 |
| `GeometricBoundaryField<double, fvPatchField, volMesh>::evaluate_if<GeometricBoundaryField<double, fvPatchField, volMesh>::evaluateCoupled<coupledFvPatch>(UPstream::commsTypes)::{lambda(auto:1 const&)#1}>` | 6 | 0.25 | 0.9 |
| `fvm::SuSp<double>` | 6 | 0.25 | 0.9 |
| `operator*<volMesh>` | 5 | 0.21 | 0.8 |
| `operator==<double>` | 4 | 0.17 | 0.6 |
| `operator*<double, fvPatchField, volMesh>` | 2 | 0.08 | 0.3 |
| `operator&<vector, vector, fvPatchField, volMesh>` | 2 | 0.08 | 0.3 |
| `fvm::Sp<double>` | 2 | 0.08 | 0.3 |
| `volScalarField::GeometricField` | 2 | 0.08 | 0.3 |
| `kOmegaSSTBase<...>::omegaSource` | 2 | 0.08 | 0.3 |
| `operator*<double, volMesh>` | 2 | 0.08 | 0.3 |
| `operator/<volMesh>` | 1 | 0.04 | 0.2 |
| `kOmegaSSTBase<...>::kSource` | 1 | 0.04 | 0.2 |
| `kOmegaSSTBase<...>::Pk` | 1 | 0.04 | 0.2 |
| `operator*<fvPatchField, volMesh>` | 1 | 0.04 | 0.2 |
| `fvm::ddt<double>` | 1 | 0.04 | 0.2 |

### B10. Laplacian and convection scheme assembly

**gaussLaplacianScheme<*>::fvmLaplacian (any T)** regex `gaussLaplacianScheme<.*>::fvmLaplacian$`: **152** samples = **6.34%**
matched frame strings (frame occurrences): `Foam::fv::gaussLaplacianScheme<double, double>::fvmLaplacian` (117); `Foam::fv::gaussLaplacianScheme<Foam::Vector<double>, double>::fvmLaplacian` (35)
by step phase: turbulence->correct 91 (3.80%), UEqn assembly 35 (1.46%), pEqn assembly 26 (1.09%)

**gaussLaplacianScheme<double,double>::fvmLaplacian (p, k, omega)** regex `gaussLaplacianScheme<double, double>::fvmLaplacian$`: **117** samples = **4.88%**
matched frame strings (frame occurrences): `Foam::fv::gaussLaplacianScheme<double, double>::fvmLaplacian` (117)
by step phase: turbulence->correct 91 (3.80%), pEqn assembly 26 (1.09%)

**gaussLaplacianScheme<vector,double>::fvmLaplacian (U, inside divDevReff)** regex `gaussLaplacianScheme<vector, double>::fvmLaplacian$`: **35** samples = **1.46%**
matched frame strings (frame occurrences): `Foam::fv::gaussLaplacianScheme<Foam::Vector<double>, double>::fvmLaplacian` (35)
by step phase: UEqn assembly 35 (1.46%)

**gaussLaplacianScheme<*>::fvmLaplacianUncorrected** regex `fvmLaplacianUncorrected`: **38** samples = **1.59%**
matched frame strings (frame occurrences): `Foam::fv::gaussLaplacianScheme<double, double>::fvmLaplacianUncorrected` (26); `Foam::fv::gaussLaplacianScheme<Foam::Vector<double>, double>::fvmLaplacianUncorrected` (12)
by step phase: turbulence->correct 22 (0.92%), UEqn assembly 12 (0.50%), pEqn assembly 4 (0.17%)

**gaussLaplacianScheme<*>::gammaMagSf** regex `gammaMagSf`: **0** samples = **0.00%**
matched frame strings (frame occurrences): 

**correctedSnGrad<*>::correction (non-orthogonal correction)** regex `correctedSnGrad<.*>::correction`: **124** samples = **5.18%**
matched frame strings (frame occurrences): `Foam::fv::correctedSnGrad<double>::correction` (113); `Foam::fv::correctedSnGrad<Foam::Vector<double> >::correction` (11)
by step phase: pEqn assembly 58 (2.42%), turbulence->correct 55 (2.30%), UEqn assembly 11 (0.46%)

**gaussConvectionScheme<*>::fvmDiv (any T)** regex `gaussConvectionScheme<.*>::fvmDiv`: **81** samples = **3.38%**
matched frame strings (frame occurrences): `Foam::fv::gaussConvectionScheme<Foam::Vector<double> >::fvmDiv` (68); `Foam::fv::gaussConvectionScheme<double>::fvmDiv` (13)
by step phase: UEqn assembly 68 (2.84%), turbulence->correct 13 (0.54%)

**gaussConvectionScheme<vector>::fvmDiv (U)** regex `gaussConvectionScheme<vector>::fvmDiv`: **68** samples = **2.84%**
matched frame strings (frame occurrences): `Foam::fv::gaussConvectionScheme<Foam::Vector<double> >::fvmDiv` (68)
by step phase: UEqn assembly 68 (2.84%)

**gaussConvectionScheme<double>::fvmDiv (k, omega)** regex `gaussConvectionScheme<double>::fvmDiv`: **13** samples = **0.54%**
matched frame strings (frame occurrences): `Foam::fv::gaussConvectionScheme<double>::fvmDiv` (13)
by step phase: turbulence->correct 13 (0.54%)

**boundedConvectionScheme<*>::fvmDiv (wrapper, includes fvm::Sp(-div(phi)))** regex `boundedConvectionScheme<.*>::fvmDiv`: **101** samples = **4.22%**
matched frame strings (frame occurrences): `Foam::fv::boundedConvectionScheme<Foam::Vector<double> >::fvmDiv` (75); `Foam::fv::boundedConvectionScheme<double>::fvmDiv` (26)
by step phase: UEqn assembly 75 (3.13%), turbulence->correct 26 (1.09%)

**linearUpwindV<vector>::correction** regex `linearUpwindV<vector>::correction`: **41** samples = **1.71%**
matched frame strings (frame occurrences): `Foam::linearUpwindV<Foam::Vector<double> >::correction` (41)
by step phase: UEqn assembly 41 (1.71%)

**Direct children of `gaussLaplacianScheme<double, double>::fvmLaplacian`** (regex `gaussLaplacianScheme<double, double>::fvmLaplacian$`, 117 samples = 4.88%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::correctedSnGrad<double>::correction` | 70 | 2.92 | 59.8 |
| `fv::gaussLaplacianScheme<double, double>::fvmLaplacianUncorrected` | 26 | 1.09 | 22.2 |
| `operator*<fvsPatchField, surfaceMesh>` | 8 | 0.33 | 6.8 |
| `operator*` | 5 | 0.21 | 4.3 |
| `fvc::surfaceIntegrateInternal<double, double>` | 4 | 0.17 | 3.4 |
| `fvc::surfaceIntegrateInternal<double>` | 2 | 0.08 | 1.7 |
| `Field<double>::operator-=` | 2 | 0.08 | 1.7 |

**Direct children of `gaussLaplacianScheme<vector, double>::fvmLaplacian`** (regex `gaussLaplacianScheme<vector, double>::fvmLaplacian$`, 35 samples = 1.46%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::gaussLaplacianScheme<vector, double>::fvmLaplacianUncorrected` | 12 | 0.50 | 34.3 |
| `fv::correctedSnGrad<vector>::correction` | 11 | 0.46 | 31.4 |
| `fvc::surfaceIntegrateInternal<vector, double>` | 6 | 0.25 | 17.1 |
| `operator*<fvsPatchField, surfaceMesh>` | 5 | 0.21 | 14.3 |
| `Field<vector>::operator-=` | 1 | 0.04 | 2.9 |

**Direct children of `gaussConvectionScheme<vector>::fvmDiv`** (regex `gaussConvectionScheme<vector>::fvmDiv`, 68 samples = 2.84%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `linearUpwindV<vector>::correction` | 41 | 1.71 | 60.3 |
| `fvc::surfaceIntegrateInternal<vector, double>` | 13 | 0.54 | 19.1 |
| `<self (leaf)>` | 6 | 0.25 | 8.8 |
| `fvMatrix<vector>::fvMatrix` | 2 | 0.08 | 2.9 |
| `upwind<vector>::weights` | 2 | 0.08 | 2.9 |
| `lduMatrix::lower` | 2 | 0.08 | 2.9 |
| `fvMatrix<vector>::operator+=` | 1 | 0.04 | 1.5 |
| `lduMatrix::diag` | 1 | 0.04 | 1.5 |

**Direct children of `gaussConvectionScheme<double>::fvmDiv`** (regex `gaussConvectionScheme<double>::fvmDiv`, 13 samples = 0.54%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `upwind<double>::weights` | 4 | 0.17 | 30.8 |
| `lduMatrix::lower` | 3 | 0.13 | 23.1 |
| `<self (leaf)>` | 3 | 0.13 | 23.1 |
| `lduMatrix::upper` | 2 | 0.08 | 15.4 |
| `__memmove_avx_unaligned_erms` | 1 | 0.04 | 7.7 |

**Direct children of `boundedConvectionScheme<vector>::fvmDiv`** (regex `boundedConvectionScheme<vector>::fvmDiv`, 75 samples = 3.13%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::gaussConvectionScheme<vector>::fvmDiv` | 68 | 2.84 | 90.7 |
| `fvc::surfaceIntegrateInternal<double>` | 3 | 0.13 | 4.0 |
| `fvm::Sp<vector>` | 2 | 0.08 | 2.7 |
| `fvMatrix<vector>::operator-=` | 2 | 0.08 | 2.7 |

### B11. Matrix allocation / zero fill

**memset leaf (any caller)** regex `memset`: **45** samples = **1.88%**
matched frame strings (frame occurrences): `__memset_avx2_unaligned_erms` (45)
by step phase: turbulence->correct 23 (0.96%), UEqn assembly 14 (0.58%), pEqn solve 6 (0.25%), pEqn assembly 2 (0.08%)

**lduMatrix::upper()** regex `^lduMatrix::upper$`: **16** samples = **0.67%**
matched frame strings (frame occurrences): `Foam::lduMatrix::upper` (16)
by step phase: turbulence->correct 11 (0.46%), pEqn solve 3 (0.13%), UEqn assembly 2 (0.08%)

**lduMatrix::lower()** regex `^lduMatrix::lower$`: **8** samples = **0.33%**
matched frame strings (frame occurrences): `Foam::lduMatrix::lower` (8)
by step phase: turbulence->correct 6 (0.25%), UEqn assembly 2 (0.08%)

**lduMatrix::diag()** regex `^lduMatrix::diag$`: **8** samples = **0.33%**
matched frame strings (frame occurrences): `Foam::lduMatrix::diag` (8)
by step phase: turbulence->correct 5 (0.21%), UEqn assembly 2 (0.08%), pEqn assembly 1 (0.04%)

**fvMatrix<*>::fvMatrix constructor** regex `^fvMatrix<.*>::fvMatrix$`: **22** samples = **0.92%**
matched frame strings (frame occurrences): `Foam::fvMatrix<Foam::Vector<double> >::fvMatrix` (18); `Foam::fvMatrix<double>::fvMatrix` (4)
by step phase: UEqn assembly 18 (0.75%), turbulence->correct 4 (0.17%)

**lduMatrix::lduMatrix (constructor incl. copy)** regex `^lduMatrix::lduMatrix$`: **7** samples = **0.29%**
matched frame strings (frame occurrences): `Foam::lduMatrix::lduMatrix` (7)
by step phase: UEqn assembly 7 (0.29%)

**fvMatrix<*>::~fvMatrix / lduMatrix::~lduMatrix** regex `::~(fvMatrix|lduMatrix)$`: **0** samples = **0.00%**
matched frame strings (frame occurrences): 

**malloc/free family leaf** regex `^(_int_malloc|_int_free|malloc|free|cfree|__GI___libc_malloc|malloc_consolidate|unlink_chunk|sysmalloc|__libc_malloc)`: **9** samples = **0.38%**
matched frame strings (frame occurrences): `malloc` (6); `_int_malloc` (5); `_int_free` (2); `malloc_consolidate` (1)
by step phase: turbulence->correct 4 (0.17%), UEqn assembly 2 (0.08%), pEqn solve 1 (0.04%), pEqn assembly 1 (0.04%), Time::loop (function objects) 1 (0.04%)

**Union of B11 items**: 69 = 2.88%

memset leaf by immediate caller:

| caller of memset | samples | % |
|---|---|---|
| `lduMatrix::upper` | 14 | 0.58 |
| `fvMatrix<vector>::fvMatrix` | 8 | 0.33 |
| `lduMatrix::diag` | 8 | 0.33 |
| `lduMatrix::lower` | 5 | 0.21 |
| `fvMatrix<double>::fvMatrix` | 4 | 0.17 |
| `GAMGAgglomeration::restrictField<double>` | 3 | 0.13 |
| `fvMatrix<double>::relax` | 1 | 0.04 |
| `fvMatrix<vector>::H` | 1 | 0.04 |
| `omegaWallFunctionFvPatchScalarField::omega` | 1 | 0.04 |

memmove/memcpy leaf by immediate two callers:

| callers of memmove | samples | % |
|---|---|---|
| `smoothSolver::solveGaussSeidelComponents <- fvMatrix<vector>::solveSegregated` | 46 | 1.92 |
| `GaussSeidelSmoother::smooth <- GaussSeidelSmoother::smooth` | 12 | 0.50 |
| `lduMatrix::lduMatrix <- fvMatrix<vector>::fvMatrix` | 7 | 0.29 |
| `lduMatrix::operator+= <- fvMatrix<double>::operator+=` | 6 | 0.25 |
| `fvMatrix<vector>::solveSegregated <- fvMatrix<vector>::solveSegregatedOrCoupled` | 5 | 0.21 |
| `GaussSeidelSmoother::smooth <- GaussSeidelSmoother::scalarSmooth` | 4 | 0.17 |
| `fv::gaussLaplacianScheme<double, double>::fvmLaplacianUncorrected <- fv::gaussLaplacianScheme<double, double>::fvmLaplacian` | 3 | 0.13 |
| `lduMatrix::lower <- lduMatrix::operator+=` | 3 | 0.13 |
| `fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled` | 3 | 0.13 |
| `fvMatrix<double>::operator+= <- operator+<double>` | 2 | 0.08 |
| `ucp_eager_single_pack <- uct_mm_ep_am_bcopy` | 2 | 0.08 |
| `lduMatrix::upper <- fv::gaussConvectionScheme<double>::fvmDiv` | 2 | 0.08 |
| `fvMatrix<vector>::A <- main` | 2 | 0.08 |
| `fvMatrix<double>::relax <- fvMatrix<double>::relax` | 1 | 0.04 |
| `calculatedFvPatchField<double>::clone <- GeometricBoundaryField<double, fvPatchField, volMesh>::GeometricBoundaryField` | 1 | 0.04 |
| `fvPatchField<double>::fvPatchField <- processorFvPatchField<double>::clone` | 1 | 0.04 |
| `fv::gaussConvectionScheme<double>::fvmDiv <- fv::boundedConvectionScheme<double>::fvmDiv` | 1 | 0.04 |
| `smoothSolver::solve <- fvMatrix<double>::solveSegregated` | 1 | 0.04 |

### B12. relax / solveSegregated outside the solver / boundary manipulation

**fvMatrix<*>::relax (any)** regex `^fvMatrix<.*>::relax$`: **30** samples = **1.25%**
matched frame strings (frame occurrences): `Foam::fvMatrix<Foam::Vector<double> >::relax` (36); `Foam::fvMatrix<double>::relax` (24)
by step phase: UEqn assembly 18 (0.75%), turbulence->correct 12 (0.50%)

**fvMatrix<vector>::relax (UEqn.relax)** regex `^fvMatrix<vector>::relax$`: **18** samples = **0.75%**
matched frame strings (frame occurrences): `Foam::fvMatrix<Foam::Vector<double> >::relax` (36)
by step phase: UEqn assembly 18 (0.75%)

**fvMatrix<double>::relax (k, omega, p.relax is a field relax not matrix)** regex `^fvMatrix<double>::relax$`: **12** samples = **0.50%**
matched frame strings (frame occurrences): `Foam::fvMatrix<double>::relax` (24)
by step phase: turbulence->correct 12 (0.50%)

**fvMatrix<vector>::solveSegregated**: inclusive 491 = 20.49%; **outside the lduMatrix::solver (no `^(GAMGSolver|smoothSolver|PCG|PBiCG|PBiCGStab|diagonalSolver)::(solve|scalarSolve|solveGaussSeidelComponents)$` frame)**: 36 = 1.50%
  children of solveSegregated outside the solver: `Field<vector>::component` 17, `__memmove_avx_unaligned_erms` 5, `lduMatrix::updateMatrixInterfaces` 3, `<self (leaf)>` 3, `fvMatrix<vector>::addBoundarySource` 2, `UList<vector>::deepCopy` 2, `lduMatrix::initMatrixInterfaces` 1, `fvMatrix<vector>::addBoundaryDiag` 1, `GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate` 1, `FieldField<Field, vector>::component` 1

**fvMatrix<double>::solveSegregated**: inclusive 960 = 40.07%; **outside the lduMatrix::solver (no `^(GAMGSolver|smoothSolver|PCG|PBiCG|PBiCGStab|diagonalSolver)::(solve|scalarSolve|solveGaussSeidelComponents)$` frame)**: 12 = 0.50%
  children of solveSegregated outside the solver: `lduMatrix::solver::New` 6, `__memmove_avx_unaligned_erms` 3, `GeometricBoundaryField<double, fvPatchField, volMesh>::evaluate` 2, `GAMGSolver::~GAMGSolver` 1

**fvMatrix::setValues* (setValuesFromList)** regex `setValues`: **9** samples = **0.38%**
matched frame strings (frame occurrences): `Foam::fvMatrix<double>::setValuesFromList<Foam::UList>` (9)
by step phase: turbulence->correct 9 (0.38%)

**fvMatrix::boundaryManipulate** regex `boundaryManipulate`: **9** samples = **0.38%**
matched frame strings (frame occurrences): `Foam::fvMatrix<double>::boundaryManipulate` (9)
by step phase: turbulence->correct 9 (0.38%)

**GeometricField<*>::correctBoundaryConditions** regex `::correctBoundaryConditions$`: **19** samples = **0.79%**
matched frame strings (frame occurrences): `Foam::fv::gaussGrad<Foam::Vector<double> >::correctBoundaryConditions` (13); `Foam::fv::gaussGrad<double>::correctBoundaryConditions` (6)
by step phase: turbulence->correct 14 (0.58%), UEqn assembly 3 (0.13%), pEqn assembly 2 (0.08%)

**GeometricBoundaryField<*>::evaluate (field boundary evaluation)** regex `^GeometricBoundaryField<.*>::evaluate$`: **74** samples = **3.09%**
matched frame strings (frame occurrences): `Foam::GeometricBoundaryField<Foam::Vector<double>, Foam::fvPatchField, Foam::volMesh>::evaluate` (51); `Foam::GeometricBoundaryField<double, Foam::fvPatchField, Foam::volMesh>::evaluate` (12); `Foam::GeometricBoundaryField<Foam::Tensor<double>, Foam::fvPatchField, Foam::volMesh>::evaluate` (11)
by step phase: turbulence->correct 40 (1.67%), pEqn assembly 18 (0.75%), UEqn assembly 14 (0.58%), UEqn solve 1 (0.04%), pEqn solve 1 (0.04%)

**evaluateCoupled / evaluate_if** regex `evaluateCoupled|evaluate_if`: **6** samples = **0.25%**
matched frame strings (frame occurrences): `Foam::GeometricBoundaryField<double, Foam::fvPatchField, Foam::volMesh>::evaluate_if<Foam::GeometricBoundaryField<double, Foam::fvPatchField, Foam::volMesh>::evaluateCoupled<Foam::coupledFvPatch>(Foam::UPstream::commsTypes)::{lambda(auto:1 const&)#1}>` (6)
by step phase: turbulence->correct 6 (0.25%)

**processorFvPatchField<*>::initEvaluate / evaluate** regex `processorFvPatchField<.*>::(initEvaluate|evaluate)$`: **6** samples = **0.25%**
matched frame strings (frame occurrences): `Foam::processorFvPatchField<double>::initEvaluate` (3); `Foam::processorFvPatchField<Foam::Vector<double> >::initEvaluate` (2); `Foam::processorFvPatchField<Foam::Tensor<double> >::initEvaluate` (1)
by step phase: turbulence->correct 3 (0.13%), pEqn assembly 2 (0.08%), pEqn solve 1 (0.04%)

**gaussGrad<*>::correctBoundaryConditions** regex `gaussGrad<.*>::correctBoundaryConditions`: **19** samples = **0.79%**
matched frame strings (frame occurrences): `Foam::fv::gaussGrad<Foam::Vector<double> >::correctBoundaryConditions` (13); `Foam::fv::gaussGrad<double>::correctBoundaryConditions` (6)
by step phase: turbulence->correct 14 (0.58%), UEqn assembly 3 (0.13%), pEqn assembly 2 (0.08%)

**Direct children of `GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate`** (regex `^GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate$`, 51 samples = 2.13%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `UPstream::waitRequests` | 46 | 1.92 | 90.2 |
| `extrapolatedCalculatedFvPatchField<vector>::evaluate` | 2 | 0.08 | 3.9 |
| `processorFvPatchField<vector>::initEvaluate` | 2 | 0.08 | 3.9 |
| `basicSymmetryFvPatchField<vector>::evaluate` | 1 | 0.04 | 2.0 |

### B13. continuity, fvOptions, function objects

**continuityErrs (C phase label: call sites 0x4270a8..0x4271c2 under main = fvc::div(phi) inlined to surfaceIntegrateInternal, mag, weightedAverage)**: 7 samples = 0.29%

**fv::optionList::* (fvOptions)** regex `^fv::optionList::`: **30** samples = **1.25%**
matched frame strings (frame occurrences): `Foam::fv::optionList::constrain<Foam::Vector<double> >` (25); `Foam::fv::optionList::source<Foam::Vector<double> >` (5)
by step phase: UEqn assembly 30 (1.25%)

**functionObjectList::execute subtree** regex `^functionObjectList::execute$`: **37** samples = **1.54%**
matched frame strings (frame occurrences): `Foam::functionObjectList::execute` (37)
by step phase: Time::loop (function objects) 37 (1.54%)

**Time::loop (whole, includes functionObjects + readModifiedObjects)** regex `^Time::loop$`: **39** samples = **1.63%**
matched frame strings (frame occurrences): `Foam::Time::loop` (39)
by step phase: Time::loop (function objects) 39 (1.63%)

**Time::write / regIOobject::write (field output)** regex `^(Time::write|regIOobject::write|Time::writeNow|fvMesh::write|GeometricField<.*>::write)`: **0** samples = **0.00%**
matched frame strings (frame occurrences): 

function objects by type (first `functionObjects::<type>::` frame other than timeControl, or `Probes<`):

| function object type | samples | % |
|---|---|---|
| fieldMinMax | 10 | 0.42 |
| wallShearStress | 9 | 0.38 |
| probes | 7 | 0.29 |
| forces | 5 | 0.21 |
| forceCoeffs | 3 | 0.13 |
| properties | 2 | 0.08 |
| pressure | 1 | 0.04 |

**Direct children of `Time::loop`** (regex `^Time::loop$`, 39 samples = 1.63%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `Time::run` | 39 | 1.63 | 100.0 |

### B14. MPI

**MPI total** (any frame matching `^(MPI_|PMPI_|MPIR_|MPIDI_|MPIDIG_|MPID_|MPIC_|MPIU_|MPL_|ucp_|uct_|ucs_|ucm_|mlx5_|ibv_|fi_|cxi|_pmi|PMI|get_sw_cqe|opal_|ompi_|hwloc|pthread_spin|__pat_mpi)`): **748** = **31.22%**

Caller category (walk from the outermost MPI frame towards `main`; first frame matching Allreduce regex `allReduce|reduceAnd|reduceOr|::reduce|gSum|gMax|gMin|gAverage|returnReduce|MPI_Allreduce|mpi_allgather|allGather|gatherList|listCombine|combineAllGather` or interface regex `initMatrixInterfaces|updateMatrixInterfaces|initEvaluate|::evaluate$|initInterfaceMatrixUpdate|updateInterfaceMatrix|evaluate_if|evaluateCoupled` decides):

| category | samples | % in-loop | % of MPI |
|---|---|---|---|
| Allreduce (reduce/gSum*/returnReduce/allGather) | 432 | 18.03 | 57.8 |
| interface exchange (init/updateMatrixInterfaces, initEvaluate/evaluate) | 306 | 12.77 | 40.9 |
| other | 10 | 0.42 | 1.3 |

nearest OpenFOAM caller for **Allreduce (reduce/gSum*/returnReduce/allGather)**: `PstreamDetail::allReduce<void>` 394, `UPstream::reduceAnd` 28, `UPstream::mpi_allgather` 10

nearest OpenFOAM caller for **interface exchange (init/updateMatrixInterfaces, initEvaluate/evaluate)**: `UPstream::waitRequests` 220, `UPstream::mpi_send` 46, `UPstream::mpi_receive` 25, `UPstream::finishedRequest` 15

nearest OpenFOAM caller for **other**: `UIPBstream::bufferIPCrecv` 6, `UPstream::mpi_receive` 2, `UPstream::waitRequests` 1, `UPstream::mpi_broadcast` 1

MPI entry function (outermost MPI frame):

| MPI entry | samples | % |
|---|---|---|
| `MPI_Allreduce` | 422 | 17.61 |
| `MPI_Waitall` | 221 | 9.22 |
| `MPI_Isend` | 46 | 1.92 |
| `MPI_Irecv` | 25 | 1.04 |
| `MPI_Test` | 15 | 0.63 |
| `MPI_Allgather` | 10 | 0.42 |
| `MPI_Bcast` | 7 | 0.29 |
| `MPI_Recv` | 2 | 0.08 |

MPI by step phase:

| phase | MPI samples | % in-loop | % of phase |
|---|---|---|---|
| pEqn solve | 404 | 16.86 | 53.0 |
| turbulence->correct | 147 | 6.14 | 22.8 |
| UEqn solve | 92 | 3.84 | 18.7 |
| pEqn assembly | 45 | 1.88 | 28.7 |
| UEqn assembly | 34 | 1.42 | 12.1 |
| Time::loop (function objects) | 22 | 0.92 | 56.4 |
| continuityErrs | 4 | 0.17 | 57.1 |

MPI by OpenFOAM reduction/communication primitive (first OpenFOAM frame above MPI) and its caller:

| OpenFOAM caller chain (3 frames above MPI) | samples | % |
|---|---|---|
| `PstreamDetail::allReduce<void> <- GAMGSolver::scale <- GAMGSolver::Vcycle` | 106 | 4.42 |
| `PstreamDetail::allReduce<void> <- gSumProd<double> <- PCG::scalarSolve` | 96 | 4.01 |
| `PstreamDetail::allReduce<void> <- gAverage<double> <- lduMatrix::solver::normFactor` | 68 | 2.84 |
| `UPstream::waitRequests <- lduMatrix::updateMatrixInterfaces <- lduMatrix::Amul` | 57 | 2.38 |
| `UPstream::waitRequests <- lduMatrix::updateMatrixInterfaces <- GaussSeidelSmoother::smooth` | 52 | 2.17 |
| `UPstream::waitRequests <- lduMatrix::updateMatrixInterfaces <- smoothSolver::solveGaussSeidelComponents` | 45 | 1.88 |
| `UPstream::mpi_send <- processorGAMGInterfaceField::initInterfaceMatrixUpdate <- lduMatrix::initMatrixInterfaces` | 37 | 1.54 |
| `UPstream::waitRequests <- GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate <- fv::gaussGrad<double>::gradfLinear` | 36 | 1.50 |
| `PstreamDetail::allReduce<void> <- gSumMag<double> <- smoothSolver::solve` | 28 | 1.17 |
| `UPstream::reduceAnd <- volScalarField::needReference` | 25 | 1.04 |
| `PstreamDetail::allReduce<void> <- gSumMag<double> <- GAMGSolver::solve` | 23 | 0.96 |
| `PstreamDetail::allReduce<void> <- gSumMag<double> <- smoothSolver::solveGaussSeidelComponents` | 22 | 0.92 |
| `PstreamDetail::allReduce<void> <- fv::velocityDampingConstraint::addDamping <- fv::optionList::constrain<vector>` | 21 | 0.88 |
| `UPstream::mpi_receive <- processorGAMGInterfaceField::initInterfaceMatrixUpdate <- lduMatrix::initMatrixInterfaces` | 20 | 0.83 |
| `PstreamDetail::allReduce<void> <- gSumMag<double> <- PCG::scalarSolve` | 15 | 0.63 |
| `UPstream::finishedRequest <- processorGAMGInterfaceField::updateInterfaceMatrix <- lduMatrix::updateMatrixInterfaces` | 14 | 0.58 |
| `UPstream::waitRequests <- GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate <- fvc::surfaceIntegrate<vector>` | 9 | 0.38 |
| `UPstream::mpi_allgather <- functionObjects::fieldMinMax::calcMinMaxFieldType<double> <- functionObjects::fieldMinMax::calcMinMaxFields<vector>` | 9 | 0.38 |
| `UPstream::waitRequests <- GeometricBoundaryField<double, fvPatchField, volMesh>::evaluate_if<GeometricBoundaryField<double, fvPatchField, volMesh>::evaluateCoupled<coupledFvPatch>(UPstream::commsTypes)::{lambda(auto:1 const&)#1}> <- kOmegaSSTBase<...>::correct` | 6 | 0.25 |
| `UIPBstream::bufferIPCrecv <- UIPBstream::UIPBstream <- IPBstream::IPBstream` | 6 | 0.25 |
| `UPstream::mpi_send <- processorFvPatchField<vector>::initInterfaceMatrixUpdate <- lduMatrix::initMatrixInterfaces` | 5 | 0.21 |
| `PstreamDetail::allReduce<void> <- lduMatrix::solver::normFactor <- smoothSolver::solveGaussSeidelComponents` | 4 | 0.17 |
| `PstreamDetail::allReduce<void> <- DimensionedField<double, volMesh>::weightedAverage` | 4 | 0.17 |
| `UPstream::waitRequests <- lduMatrix::updateMatrixInterfaces <- fvMatrix<vector>::solveSegregated` | 3 | 0.13 |
| `UPstream::reduceAnd <- volScalarField::needReference <- adjustPhi` | 3 | 0.13 |
| `PstreamDetail::allReduce<void> <- functionObjects::forces::calcForcesMoments <- functionObjects::forceCoeffs::execute` | 3 | 0.13 |
| `UPstream::mpi_send <- processorFvPatchField<double>::initInterfaceMatrixUpdate <- lduMatrix::initMatrixInterfaces` | 3 | 0.13 |
| `UPstream::waitRequests <- GeometricBoundaryField<tensor, fvPatchField, volMesh>::evaluate <- fv::cellLimitedGrad<vector, minmod>::calcGrad` | 3 | 0.13 |
| `UPstream::waitRequests <- GeometricBoundaryField<tensor, fvPatchField, volMesh>::evaluate <- fv::gaussGrad<vector>::calcGrad` | 3 | 0.13 |
| `UPstream::mpi_receive <- processorFvPatchField<double>::initInterfaceMatrixUpdate <- lduMatrix::initMatrixInterfaces` | 2 | 0.08 |
| `UPstream::mpi_receive <- Pstream::listGather_algorithm<double, probeModel::isNotEqOp<double>, true> <- Pstream::listReduce<double, probeModel::isNotEqOp<double>, true>` | 2 | 0.08 |
| `UPstream::waitRequests <- lduMatrix::updateMatrixInterfaces <- lduMatrix::residual` | 2 | 0.08 |
| `PstreamDetail::allReduce<void> <- min<double, fvPatchField, volMesh> <- bound` | 2 | 0.08 |
| `UPstream::mpi_receive <- processorFvPatchField<vector>::initInterfaceMatrixUpdate <- lduMatrix::initMatrixInterfaces` | 2 | 0.08 |
| `UPstream::waitRequests <- GeometricBoundaryField<double, fvPatchField, volMesh>::evaluate <- fvMatrix<vector>::A` | 1 | 0.04 |
| `UPstream::mpi_allgather <- functionObjects::fieldMinMax::calcMinMaxFieldType<double> <- functionObjects::fieldMinMax::write` | 1 | 0.04 |
| `UPstream::waitRequests <- bound <- kOmegaSSTBase<...>::correct` | 1 | 0.04 |
| `UPstream::finishedRequest <- processorFvPatchField<vector>::updateInterfaceMatrix <- lduMatrix::updateMatrixInterfaces` | 1 | 0.04 |
| `PstreamDetail::allReduce<void> <- lduMatrix::solver::normFactor <- GAMGSolver::solve` | 1 | 0.04 |
| `UPstream::mpi_send <- processorFvPatchField<double>::initEvaluate <- GeometricBoundaryField<double, fvPatchField, volMesh>::evaluate` | 1 | 0.04 |

## C (detail). Children of each phase entry frame

**Direct children of `fvMatrix<double>::solveSegregated, p equation only`** (regex `^fvMatrix<double>::solveSegregated$`, phase=pEqn solve, 762 samples = 31.80%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `GAMGSolver::solve` | 752 | 31.39 | 98.7 |
| `lduMatrix::solver::New` | 6 | 0.25 | 0.8 |
| `__memmove_avx_unaligned_erms` | 2 | 0.08 | 0.3 |
| `GAMGSolver::~GAMGSolver` | 1 | 0.04 | 0.1 |
| `GeometricBoundaryField<double, fvPatchField, volMesh>::evaluate` | 1 | 0.04 | 0.1 |

**Direct children of `fvMatrix<double>::solveSegregated, k and omega only`** (regex `^fvMatrix<double>::solveSegregated$`, phase=turbulence->correct, 198 samples = 8.26%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `smoothSolver::solve` | 196 | 8.18 | 99.0 |
| `__memmove_avx_unaligned_erms` | 1 | 0.04 | 0.5 |
| `GeometricBoundaryField<double, fvPatchField, volMesh>::evaluate` | 1 | 0.04 | 0.5 |

**Direct children of `fvMatrix<vector>::solveSegregated (UEqn)`** (regex `^fvMatrix<vector>::solveSegregated$`, phase=UEqn solve, 491 samples = 20.49%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `smoothSolver::solveGaussSeidelComponents` | 455 | 18.99 | 92.7 |
| `Field<vector>::component` | 17 | 0.71 | 3.5 |
| `__memmove_avx_unaligned_erms` | 5 | 0.21 | 1.0 |
| `lduMatrix::updateMatrixInterfaces` | 3 | 0.13 | 0.6 |
| `<self (leaf)>` | 3 | 0.13 | 0.6 |
| `fvMatrix<vector>::addBoundarySource` | 2 | 0.08 | 0.4 |
| `UList<vector>::deepCopy` | 2 | 0.08 | 0.4 |
| `lduMatrix::initMatrixInterfaces` | 1 | 0.04 | 0.2 |
| `fvMatrix<vector>::addBoundaryDiag` | 1 | 0.04 | 0.2 |
| `GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate` | 1 | 0.04 | 0.2 |
| `FieldField<Field, vector>::component` | 1 | 0.04 | 0.2 |

**Direct children of `fvm::div<vector> (UEqn convection)`** (regex `^fvm::div<vector>$`, 75 samples = 3.13%; child = frame immediately inside the outermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::boundedConvectionScheme<vector>::fvmDiv` | 75 | 3.13 | 100.0 |

**Direct children of `divDevReff -> divDevRhoReff (UEqn diffusion)`** (regex `::divDevRhoReff$`, 111 samples = 4.63%; child = frame immediately inside the innermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fvc::div<tensor>` | 41 | 1.71 | 36.9 |
| `fvm::laplacian<vector, double>` | 39 | 1.63 | 35.1 |
| `RASModel<IncompressibleTurbulenceModel<...>>::nuEff` | 10 | 0.42 | 9.0 |
| `operator*<tensor, fvPatchField, volMesh>` | 7 | 0.29 | 6.3 |
| `operator-<vector>` | 5 | 0.21 | 4.5 |
| `T<fvPatchField, volMesh>` | 3 | 0.13 | 2.7 |
| `operator-<vector, fvPatchField, volMesh>` | 3 | 0.13 | 2.7 |
| `dev2<fvPatchField, volMesh>` | 3 | 0.13 | 2.7 |

**Direct children of `fvm::laplacian<double, double> (innermost wrapper), pEqn only`** (regex `^fvm::laplacian<double, double>$`, phase=pEqn assembly, 30 samples = 1.25%; child = frame immediately inside the innermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::laplacianScheme<double, double>::fvmLaplacian` | 30 | 1.25 | 100.0 |

**Direct children of `fvm::laplacian<double, double> (innermost wrapper), k/omega only`** (regex `^fvm::laplacian<double, double>$`, phase=turbulence->correct, 98 samples = 4.09%; child = frame immediately inside the innermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::laplacianScheme<double, double>::fvmLaplacian` | 98 | 4.09 | 100.0 |

**Direct children of `fvc::snGrad<double>`** (regex `^fvc::snGrad<double>$`, 48 samples = 2.00%; child = frame immediately inside the innermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::snGradScheme<double>::snGrad` | 48 | 2.00 | 100.0 |

**Direct children of `fv::optionList::constrain<vector>`** (regex `^fv::optionList::constrain<vector>$`, 25 samples = 1.04%; child = frame immediately inside the innermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::velocityDampingConstraint::addDamping` | 25 | 1.04 | 100.0 |

**Direct children of `volScalarField::needReference`** (regex `needReference$`, 28 samples = 1.17%; child = frame immediately inside the innermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `UPstream::reduceAnd` | 28 | 1.17 | 100.0 |

**Direct children of `fvc::grad<double> (innermost), all call sites`** (regex `^fvc::grad<double>$`, 76 samples = 3.17%; child = frame immediately inside the innermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `fv::gradScheme<double>::grad` | 76 | 3.17 | 100.0 |

**Direct children of `Time::run`** (regex `^Time::run$`, 39 samples = 1.63%; child = frame immediately inside the innermost matching frame):

| child frame | samples | % in-loop | % of parent |
|---|---|---|---|
| `functionObjectList::execute` | 37 | 1.54 | 94.9 |
| `Time::readModifiedObjects` | 2 | 0.08 | 5.1 |

## Most frequent full stacks (abbreviated, leaf first), top 40

| samples | % | stack |
|---|---|---|
| 266 | 11.10 | `smoothSolver::solveGaussSeidelComponents <- fvMatrix<vector>::solveSegregated <- fvMatrix<vector>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<vector>` |
| 86 | 3.59 | `MPIDI_Cray_shared_mem_coll_bcast <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- PstreamDetail::allReduce<void> <- GAMGSolver::scale <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 79 | 3.30 | `GaussSeidelSmoother::smooth <- GaussSeidelSmoother::scalarSmooth <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 78 | 3.26 | `lduMatrix::Amul <- GAMGSolver::scale <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 74 | 3.09 | `MPIDI_Cray_shared_mem_coll_bcast <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- PstreamDetail::allReduce<void> <- gSumProd<double> <- PCG::scalarSolve <- GAMGSolver::solveCoarsestLevel <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 50 | 2.09 | `lduMatrix::Amul <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 49 | 2.05 | `GaussSeidelSmoother::smooth <- GaussSeidelSmoother::smooth <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 46 | 1.92 | `__memmove_avx_unaligned_erms <- smoothSolver::solveGaussSeidelComponents <- fvMatrix<vector>::solveSegregated <- fvMatrix<vector>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<vector>` |
| 39 | 1.63 | `MPIDI_Cray_shared_mem_coll_bcast <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- PstreamDetail::allReduce<void> <- gAverage<double> <- lduMatrix::solver::normFactor <- smoothSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<double> <- kOmegaSSTBase<...>::correct` |
| 34 | 1.42 | `GaussSeidelSmoother::smooth <- GaussSeidelSmoother::smooth <- smoothSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<double> <- kOmegaSSTBase<...>::correct` |
| 28 | 1.17 | `linearUpwindV<vector>::correction <- fv::gaussConvectionScheme<vector>::fvmDiv <- fv::boundedConvectionScheme<vector>::fvmDiv <- fvm::div<vector>` |
| 25 | 1.04 | `lduMatrix::residual <- smoothSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<double> <- kOmegaSSTBase<...>::correct` |
| 24 | 1.00 | `fv::cellLimitedGrad<vector, minmod>::calcGrad <- fv::gradScheme<vector>::grad <- fvc::grad<vector> <- kOmegaSSTBase<...>::correct` |
| 23 | 0.96 | `fv::gaussGrad<vector>::addLinearFaceSums <- fv::gaussGrad<vector>::calcGrad <- fv::cellLimitedGrad<vector, minmod>::calcGrad <- fv::gradScheme<vector>::grad <- fvc::grad<vector> <- kOmegaSSTBase<...>::correct` |
| 23 | 0.96 | `fv::gaussGrad<double>::addLinearFaceSums <- fv::gaussGrad<double>::gradfLinear <- fv::gaussGrad<double>::calcGrad <- fv::gradScheme<double>::grad <- fvc::grad<double> <- kOmegaSSTBase<...>::correct` |
| 20 | 0.83 | `fv::gaussGrad<double>::addLinearFaceSums <- fv::gaussGrad<double>::gradfLinear <- fv::gaussGrad<double>::calcGrad <- fv::gradScheme<double>::grad <- fv::correctedSnGrad<double>::fullGradCorrection <- fv::correctedSnGrad<double>::correction <- fv::gaussLaplacianScheme<double, double>::fvmLaplacian <- fv::laplacianScheme<double, double>::fvmLaplacian <- fvm::laplacian<double, double> <- fvm::laplacian<double, double> <- kOmegaSSTBase<...>::correct` |
| 19 | 0.79 | `MPIDI_Cray_shared_mem_coll_bcast <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- UPstream::reduceAnd <- volScalarField::needReference` |
| 19 | 0.79 | `MPIDI_Cray_shared_mem_coll_bcast <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- PstreamDetail::allReduce<void> <- gSumMag<double> <- smoothSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<double> <- kOmegaSSTBase<...>::correct` |
| 17 | 0.71 | `fv::gaussGrad<double>::addLinearFaceSums <- fv::gaussGrad<double>::gradfLinear <- fv::gaussGrad<double>::calcGrad <- fv::gradScheme<double>::grad <- fvc::grad<double>` |
| 17 | 0.71 | `MPIDI_Cray_shared_mem_coll_bcast <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- PstreamDetail::allReduce<void> <- gSumMag<double> <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 17 | 0.71 | `GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 17 | 0.71 | `GAMGSolver::scale <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 17 | 0.71 | `Field<vector>::component <- fvMatrix<vector>::solveSegregated <- fvMatrix<vector>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<vector>` |
| 16 | 0.67 | `MPIDI_Cray_shared_mem_coll_bcast <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- PstreamDetail::allReduce<void> <- fv::velocityDampingConstraint::addDamping <- fv::optionList::constrain<vector>` |
| 16 | 0.67 | `MPIDI_Cray_shared_mem_coll_bcast <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- PstreamDetail::allReduce<void> <- gSumMag<double> <- smoothSolver::solveGaussSeidelComponents <- fvMatrix<vector>::solveSegregated <- fvMatrix<vector>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<vector>` |
| 15 | 0.63 | `surfaceInterpolationScheme<tensor>::dotInterpolate<surfaceVectorField> <- surfaceInterpolationScheme<tensor>::dotInterpolate <- fv::gaussDivScheme<tensor>::fvcDiv <- fvc::div<tensor> <- fvc::div<tensor> <- linearViscousStress<RASModel<IncompressibleTurbulenceModel<...>>>::divDevRhoReff <- IncompressibleTurbulenceModel<...>::divDevReff` |
| 15 | 0.63 | `surfaceInterpolationScheme<vector>::dotInterpolate<surfaceVectorField> <- surfaceInterpolationScheme<vector>::dotInterpolate <- fv::correctedSnGrad<double>::fullGradCorrection <- fv::correctedSnGrad<double>::correction <- fv::gaussLaplacianScheme<double, double>::fvmLaplacian <- fv::laplacianScheme<double, double>::fvmLaplacian <- fvm::laplacian<double, double> <- fvm::laplacian<double, double> <- kOmegaSSTBase<...>::correct` |
| 14 | 0.58 | `GAMGAgglomeration::prolongField<double> <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 13 | 0.54 | `devTwoSymm <- devTwoSymm<volMesh> <- kOmegaSSTBase<...>::GbyNu0 <- kOmegaSSTBase<...>::correct` |
| 12 | 0.50 | `mlx5_poll_cq_v1 <- uct_ud_verbs_iface_progress <- ucp_worker_progress <- MPIR_Waitall_impl <- MPIR_Waitall <- PMPI_Waitall <- MPI_Waitall <- UPstream::waitRequests <- lduMatrix::updateMatrixInterfaces <- smoothSolver::solveGaussSeidelComponents <- fvMatrix<vector>::solveSegregated <- fvMatrix<vector>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<vector>` |
| 12 | 0.50 | `dotdot<tensor, Symmtensor> <- operator&&<tensor, Symmtensor, volMesh> <- kOmegaSSTBase<...>::GbyNu0 <- kOmegaSSTBase<...>::correct` |
| 12 | 0.50 | `lduInterfaceField::addToInternalField<double> <- processorFvPatchField<vector>::updateInterfaceMatrix <- lduMatrix::updateMatrixInterfaces <- smoothSolver::solveGaussSeidelComponents <- fvMatrix<vector>::solveSegregated <- fvMatrix<vector>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<vector>` |
| 11 | 0.46 | `syscall <- __pat_thread_get <- MPI_Irecv <- UPstream::mpi_receive <- processorGAMGInterfaceField::initInterfaceMatrixUpdate <- lduMatrix::initMatrixInterfaces <- GaussSeidelSmoother::smooth <- GaussSeidelSmoother::scalarSmooth <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 11 | 0.46 | `fvc::surfaceIntegrateInternal<vector, double> <- fv::gaussConvectionScheme<vector>::fvmDiv <- fv::boundedConvectionScheme<vector>::fvmDiv <- fvm::div<vector>` |
| 11 | 0.46 | `fvc::surfaceIntegrate<vector> <- fvc::surfaceIntegrate<vector> <- fv::gaussDivScheme<tensor>::fvcDiv <- fvc::div<tensor> <- fvc::div<tensor> <- linearViscousStress<RASModel<IncompressibleTurbulenceModel<...>>>::divDevRhoReff <- IncompressibleTurbulenceModel<...>::divDevReff` |
| 10 | 0.42 | `lduMatrix::Amul <- smoothSolver::solveGaussSeidelComponents <- fvMatrix<vector>::solveSegregated <- fvMatrix<vector>::solveSegregatedOrCoupled <- fvMesh::solve <- solve<vector>` |
| 10 | 0.42 | `fv::gaussGrad<double>::addLinearFaceSums <- fv::gaussGrad<double>::gradfLinear <- fv::gaussGrad<double>::calcGrad <- fv::gradScheme<double>::grad <- fv::correctedSnGrad<double>::fullGradCorrection <- fv::correctedSnGrad<double>::correction <- fv::snGradScheme<double>::snGrad <- fvc::snGrad<double>` |
| 10 | 0.42 | `MPIDI_Cray_shared_mem_coll_tree_reduce <- MPIDI_Cray_shared_mem_coll_reduce <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- PstreamDetail::allReduce<void> <- GAMGSolver::scale <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |
| 10 | 0.42 | `surfaceInterpolationScheme<tensor>::dotInterpolate<surfaceVectorField> <- surfaceInterpolationScheme<tensor>::dotInterpolate <- fv::correctedSnGrad<vector>::fullGradCorrection <- fv::correctedSnGrad<vector>::correction <- fv::gaussLaplacianScheme<vector, double>::fvmLaplacian <- fvm::laplacian<vector, double> <- linearViscousStress<RASModel<IncompressibleTurbulenceModel<...>>>::divDevRhoReff <- IncompressibleTurbulenceModel<...>::divDevReff` |
| 10 | 0.42 | `MPIDI_Cray_shared_mem_coll_bcast <- MPIR_CRAY_Allreduce <- PMPI_Allreduce <- MPI_Allreduce <- PstreamDetail::allReduce<void> <- gSumMag<double> <- PCG::scalarSolve <- GAMGSolver::solveCoarsestLevel <- GAMGSolver::Vcycle <- GAMGSolver::solve <- fvMatrix<double>::solveSegregated <- fvMatrix<double>::solveSegregatedOrCoupled <- fvMesh::solve <- fvMatrix<double>::solve` |

