# ASPIRE-2Aの運用設計

この文書のクラスタ情報は、2026年9月20日から21日にASPIRE-2Aのログインノード、PBS計算ノード、およびGitHub Actionsから確認した結果である。旧課題の性能値や設定は現行課題へ流用しない。

## 接続

ローカル調査では`.env`の`ASPIRE2A_SSH_CMD`を使う。現在の設定はOpenSSHのホスト設定`aspire2a.nscc.sg`を利用する。

```bash
source .env
$ASPIRE2A_SSH_CMD hostname
```

GitHub Actionsは`/home/tomokazu/actions-runner`のself-hosted runnerに設定された`aspire2a-shell`を使う。認証、PBS投入、終了待機、成果物回収までの経路はActions run `35540131525`で完走済みである。クラスタ上のGitHub CLI認証を含むこの接続方式は意図した構成である。

## 実機で確認した構成

- OSはRHEL 8系、スケジューラはPBS Proである。
- `normal`はrouting queueであり、実行queueへ直接投入しない。
- CPU compute nodeはAMD EPYC 7713を2 socket搭載し、1ノード128 physical core、512 GiB RAMである。PBSから要求可能なメモリ上限は約440 GBである。
- compute nodeは既定で共有されるため、性能計測では`place=excl`を要求する。
- `openfoam/2512`が利用でき、`simpleFoam`は`linux64GccDPInt32Opt`で構築されている。
- site moduleは`PrgEnv-gnu/8.3.3`、GCC 11.2.0、Cray MPICH 8.1.15、PALS 1.1.6をロードする。
- MPI launcherは`/opt/cray/pe/pals/1.1.6/bin/mpiexec`であり、`mpirun`も同じ実体へのsymlinkである。OpenMPI固有の起動optionを持ち込まず、NSCCの推奨どおり`--cpu-bind depth -d 1`を指定する。現行計算ノードでは、この指定だけではOFI/UCXとも`MPI_Init`後にaffinityが全CPUへ戻ることを実測しているため、非MPIの配置記録は記録直前に`PMI_LOCAL_RANK`と同じCPUへ自己固定し、MPI processはASPIRE 2A専用interposerで`MPI_Init`/`MPI_Init_thread`の正常終了直後に固定・検証する。
- PBSの`ncpus`は1ノード128であり、基準rank数は1/2/4ノードで128/256/512とする。基準構成では1 physical coreあたり1 rankを配置する。
- 1ノード128 coreは`qdev`または`q4`、2・4ノードは`q5`へroutingされる。`q4`はwalltimeが`02:00:01`以上、`qdev`は`02:00:00`以下である。
- PBSの既定メモリは実行に不足するため、各chunkに`mem=`を必ず指定する。計測ジョブは、完走済みの基準runと同じく1ノードあたり400 GBを要求する。

## 理論上限と実測の境界

[NSCC公式FAQ](https://help.nscc.sg/aspire2a/faqs/)によると、標準計算ノードはEPYC 7713を2 socket、128 physical core搭載する。[AMD公式EPYC 7003 data sheet](https://www.amd.com/content/dam/amd/en/documents/epyc-business-docs/datasheets/amd-epyc-7003-series-product-datasheet.pdf)の7713は、1 socketあたり64 core、base 2.00 GHz、最大boost 3.675 GHz、256 MB L3、8 channel DDR4-3200、理論memory bandwidth 204.8 GB/sである。したがってASPIRE-2A標準ノードのカタログ上限は512 MB L3と409.6 GB/sである。これは全memory channelが定格で動く場合の理論値であり、OpenFOAMの到達可能な帯域や期待性能ではない。現在のHotspotsは時間sampleでありbyte数やfloating-point operation数を計測していないため、理論帯域・理論FLOPSに対する効率はまだ算出しない。その差は、公式workload上で必要なhardware counterを別条件で収集した後に評価する。

## 記憶領域

- homeは`/home/users/industry/ai-hpc/apacsc14`にあり、共有home filesystem上にある。
- scratchはLustreの`/scratch/users/industry/ai-hpc/apacsc14`を利用する。
- 2026年9月20日時点のscratch quotaは100 TiB、inode quotaは2億である。
- ASPIRE-2A用の正本は`/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a`以下に置き、GenkaiやGadiのbuild、case archive、cache、run directoryと共有しない。
- login runnerとcompute nodeの間では共有scratch上のrun directoryを境界とする。計算ノードはメトリクス断片だけを書き、終了後にlogin runnerがBigQuery送信とartifact回収を行う。ASPIRE-2A経路は`PBS_JOBFS`を前提にしない。

### Build treeとccache

計算ノードの`/dev/shm`は252 GiBのtmpfsだが`noexec`である。一方、PBSが割り当てる`${TMPDIR}`は実行可能なnode-local overlayであるため、OpenFOAMのbuild treeは`${TMPDIR}/openfoam-build`に置く。`/dev/shm`は実行ファイルを含まないccacheの一次cacheだけに使う。cache namespaceは`aspire2a-<toolchain>-<transport>`、永続file backendは`scratch`上の`build-cache/ccache/<toolchain>/<transport>`とし、compilerだけでなくMPI/ABI境界でも分離する。現行GNU/UCX構成ではそれぞれ`/dev/shm/ccache-${USER}-aspire2a-gnu-ucx`と`build-cache/ccache/gnu/ucx`であり、OFI、AOCC、他クラスタのcacheを共有しない。

site moduleにccacheがないため、公式ccache 4.13.6を`~/.local/bin/ccache`へ導入している。公式source archiveのSHA-256は`a7de667ca08cf67c3c8af9f213f6aa701a1188a2b3163fb74483858ce5e79fbb`であり、不足するxxHash 0.8.3はSHA-256 `aae608dfe8213dfd05d909a57718ef82f30722c392344583d3f39050c7f29a80`へ固定した。計算ノード上のPBS `24959663.pbs101`でRelease buildし、HTTP/Redis backend、test、文書を無効にしたfile-storage対応の最小構成である。source archive、導入script、build logおよびprovenanceは`scratch`の`tools/ccache-4.13.6`と`tools/sources`に保持する。

`~/.config/ccache/ccache.conf`は50 GB上限、圧縮、`reshare = true`だけを共通設定する。永続backendのpathはrepository側がtoolchainとtransportに応じて`CCACHE_REMOTE_STORAGE`へ設定する。PBS `24960926.pbs101`では、最初のcompile、node-local hit、一次cacheを空にした後のremote hitを順に検証している。OFI時代のGNU cacheを用いたActions `35610069144` / `35619104037`では、cold buildの1:00:11に対してwarm buildは5:27となり、異なる計算ノードから3463 remote hitsを得た。この結果は仕組みの有効性を示すが、UCX標準化後のcacheへ内容をコピーせず、UCX固有namespaceをcold状態から構築する。

## Projectと資源指定

PBS projectは`59000014`である。通常の計測ジョブは次の資源指定を基準とする。

```text
#PBS -P 59000014
#PBS -q normal
#PBS -l select=<nodes>:ncpus=128:mpiprocs=128:ompthreads=1:mem=400gb
#PBS -l place=excl
```

walltimeは処理別に指定する。ケース準備は性能計測ではないため、必要core数とmemoryだけを要求し、`place=excl`を付けない。

## Profile

ASPIRE-2AのAMD EPYC Milanに対応するAMD uProf 5.3をprofile経路の正本とする。通常計測用binaryは変更せず、共通`OpenFOAM` workflowの`profile`入口だけが`AMDuProfCLI collect --config hotspots -g --mpi`で全rankを収集する。配布scriptの`AMDuProfCLI`は引数列を`eval`で再解釈し、複数ノードOpenFOAMの`-hostRoots`と`-ioRanks`に含まれる括弧をshell構文として誤認するため使用しない。一方、PALSへ`AMDuProfCLI-bin`を直接指定すると実行ファイルがnode-localへstageされ、uProfのData/config探索が壊れる。PALSには`/usr/bin/bash`を指定し、node-localへ配備した`exec-uprof.sh`から共有領域上の`AMDuProfCLI-bin`をargv配列のまま起動する。uProf自身もtargetの括弧付き引数を再解釈するため、OpenFOAMの完全なargvはNUL区切りfileへ記録し、uProfには共有領域上の`exec-uprof-target.sh`と安全なfile pathだけを渡す。target wrapperはfileからargv配列を復元して`eval`せずsolverを起動する。計算ノード上で`report --host all --detail --cutoff 30`を実行し、全hostのCSVと同じ固定版CLIで再解析できる完全なsessionをprofile artifactとして回収する。GUIでのImport Sessionは任意の閲覧手段であり、headlessな実験経路の受入条件にはしない。

uProfはsite moduleにない。AMDのdownload pageでEULAへ同意して`AMDuProf_Linux_x64_5.3.521.tar.bz2`を取得し、次へ配置する。

```text
/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/tools/AMDuProf_Linux_x64_5.3.521.tar.bz2
```

profile workflowはAMD公表MD5 `45437d8bc0b4276a0b78e28d21de23cb`を検証し、初回だけ`tools/amduprof-5.3.521`へ展開する。EULA同意とdownloadはworkflowで自動化しない。回収したsessionは`AMDuProfCLI report --input-dir`の入力として保持し、CSV、構造化JSONおよびActions summaryを再生成可能にする。

最初は権限依存の小さいtimer-based Hotspotsを使用する。login runnerは固定版のreport構造、収集引数、MPI rank/host集計および関数時間を検証し、`profile.uprof_hotspots`としてBigQueryへ送る。検証済みraw sessionと加工済みの要約は別に保存する。IBS、PMC、system-wide、power、OS tracingは別条件のprofileとして、compute node上の権限と実測した問いに応じて追加する。一度のprofileで主要因を混ぜない。

## Cray MPICH transport

NSCCのFAQとworkshop資料が推奨する標準構成は`cray-mpich/8.1.15`とOFIである。ログインノードでは同じ`PrgEnv-gnu/8.3.3`からlibfabric 1.22.0が読み込まれる一方、PBS計算ノードではlibfabric 1.11.0.4.125が読み込まれ、計算ノードに`/opt/cray/libfabric/1.22.0`は存在しない。ビルドと実行のlink判定には計算ノード側の実体を用いる。

2ノードと4ノードの標準構成では、`renumberMesh`が`End`を出力した後の`MPI_Finalize`でSIGBUSが再現する。PBS job `24754364.pbs101`で採取したスタックは`/usr/lib64/libibverbs/libmlx5-rdmav34.so`、libfabric 1.11.0.4.125、Cray MPICH 8.1.15の`MPI_Finalize`を通り、直接の故障箇所はOFI/Mellanox verbs providerの終了処理である。64 ranks/nodeへの削減、`MPICH_SMP_SINGLE_COPY_MODE=NONE`、NSCCの2026年5月告知にある2つのsingle-copy無効化変数の同時指定でも解消しなかった。`FI_PROVIDER=sockets`は`free(): invalid pointer`となり、ログインノードのlibfabric 1.22.0を計算ノードへ持ち込む診断は終了時に停止したため、いずれも採用しない。

現在のログインノードと計算ノードでは、告知上の`MPICH_CH4_XPMEM_LMT_MSG_SIZE=NONE`と`MPICH_SMP_SINGLE_COPY_MODE=NONE`はmodule読み込み後も既定設定されない。後続のkernel更新で意図的に解除されたかは公開情報から確定できないため、リポジトリ側で推測して復元しない。サポート対象となるCray MPICH、libfabric、rdma-coreの組合せと現行の既定値はNSCCサービスデスクへ確認する。

transportはベンダーやコミュニティの所属、NICのブランドだけでは決めず、公式workloadの数値正当性と安定完走、実際のlinkとrank配置、同一条件の複数runによる性能の順で判断する。OFIは上記SIGBUSによりmulti-nodeの受入条件を満たさない一方、`craype-network-ucx`と`cray-mpich-ucx/8.1.15`を揃えたUCX構成は2/4ノードの公式workloadを完走したため、現環境の標準構成にはUCXを採用する。OFIが将来正常化した場合だけ、同一source、toolchain、rank配置、node数、workloadで複数回比較し、双方が成立すれば高速な方、一方だけ成立すれば成立する方を選ぶ。

UCX実行ではAOCL LibMをlinkするが、AOCL LibMemはpreloadしない。2ノード診断PBS `24882460.pbs101`でLibMemなしのMPI初期化・通信・終了はexit 0、LibMemありではUCX endpoint作成中に`amd_memset`からexit 139となったためである。buildと実行時にはCray MPICH UCX、`libucp`、`libucs`、`libuct`の実linkとlibfabric不在を検査する。

受入証拠はActions `35604759236` / PBS `24972410.pbs101`の2ノード256 ranksと、Actions `35617874675` / PBS `24980854.pbs101`の4ノード512 ranksである。後者は公式parserで149/150 measured iterationsを`VALID`、平均2.909178287342284秒/iteration、標準偏差0.01537712155181442、Cd 0.28404934573921931となり、全4ノードで各128 ranksがlocal rankと同じ一意なCPUへ固定された。IMB 3種は4 MiBまで完走し、4 MiB PingPongは9920.53 MB/s、Allreduceは9.23234 msだった。`gdr_copy`のbuild時v2.3とload時v2.5の不一致、および未使用の`UCX_IB_REG_METHODS`警告は残るが、正当性や完走を損なう事象としては観測されていないためsite stackの警告として追跡する。

## 検証状況

GNU 1ノードの比較可能な基準系列は、同一build-sidecarを用いたActions run `35554412747`、`35554424689`、`35556950125`である。全runが65,334,765 cells、128 ranks、39 measured iterationsを`VALID`と判定し、Cdは0.43598848994661482で一致した。平均時間は14.91809156317949〜15.171288442秒/iteration、中央値15.01955532864103秒/iteration、変動係数0.85%、max/min差1.70%である。異なるbuild-sidecarを用いた過去runの値は、この系列へ混ぜない。

AMD uProf 5.3.521の1ノードE2EはActions run `35547509496`、PBS job `24786344.pbs101`で完走した。公式結果は`VALID`で、構造化したHotspots要約、完全なraw session、BigQueryメトリクスおよびhome server上のartifactを保持している。通常計測とprofileの性能値は直接比較しない。

同runのall-host reportでは、128 rankのmodule別CPU sampleの合計は142,964.48秒である。OpenFOAMとfiniteVolume、simpleFoamなどsolver側が65,949.49秒（46.13%）、Cray MPICH、libfabric、mlx5、Pstreamなど通信側が52,512.86秒（36.73%）、vDSO、glibcおよびtoolchain runtimeが24,502.13秒（17.14%）であった。個別関数では`GaussSeidelSmoother::smooth`、`lduMatrix::residual`、`lduMatrix::Amul`に加え、Cray MPICHのshared-memory broadcast、`MPIR_Waitall_impl`、`memcpy`および`memset`が上位である。これはsolver内演算・memory accessと通信・同期の両方を改善対象にすべき証拠だが、timer-based Hotspotsだけでmemory bandwidth律速を断定しない。AOCL LibMemの効果は通常benchの同一条件で測定し、必要なら別条件のhardware counter profileで原因を絞る。

GNU/UCX基準構成の2/4ノード受入は上記Actionsで完了した。反復計測、2/4ノードuProf、UCX上のAOCC採否および改善前後の比較は、各条件を分離したcommit、Actions、PBS、公式結果およびartifactを根拠に記録する。
