# ASPIRE-2Aの運用設計

この文書のクラスタ情報は、2026年9月20日にASPIRE-2Aのログインノードで読み取り確認した結果である。旧課題の性能値や設定は現行課題へ流用しない。

## 接続

ASPIRE-2Aは直接インターネットから到達せず、Windowsジャンプホストを経由する。WSLではWindows標準OpenSSHを使うことで、`C:/Users/natty/.ssh/config`の`aspire2a`設定とWindows側の鍵・既知ホストをそのまま利用できる。

```bash
/mnt/c/Windows/System32/OpenSSH/ssh.exe -F C:/Users/natty/.ssh/config -o ForwardAgent=no -o BatchMode=yes -o ConnectTimeout=60 aspire2a
```

認証エージェント転送は不要なので明示的に無効化する。ローカルの`.env`では、このコマンドを`ASPIRE2AP_SSH_CMD`に設定する。

GitHub Actionsはhome-lab runnerから実行するため、runner側にも同等の非対話接続ラッパーが必要である。runnerの設定を確認できるまでは、workflowからの接続確認済みとは扱わない。

## 実機で確認した構成

- OSはRHEL 8系、スケジューラはPBS Proである。
- `normal`はrouting queueであり、実行queueへ直接投入しない。
- CPU compute nodeは`node_pool=ex`、1ノード128 CPU core、PBSから見えるメモリは約440 GBである。
- compute nodeは既定で共有されるため、性能計測では`place=excl`を要求する。
- `openfoam/2512`が利用でき、`simpleFoam`は`linux64GccDPInt32Opt`で構築されている。
- site moduleは`PrgEnv-gnu/8.3.3`、GCC 11.2.0、Cray MPICH 8.1.15、PALS 1.1.6をロードする。
- MPI launcherは`/opt/cray/pe/pals/1.1.6/bin/mpiexec`である。OpenMPI固有の起動optionを持ち込まない。
- PBSの`ncpus`は1ノード128であり、基準rank数は1/2/4ノードで128/256/512とする。SMTと物理coreの対応はcompute node上で再確認する。
- 1ノード128 coreは`qdev`または`q4`、2・4ノードは`q5`へroutingされる。`q4`はwalltimeが`02:00:01`以上、`qdev`は`02:00:00`以下である。
- PBSの既定メモリは実行に不足するため、各chunkに`mem=`を必ず指定する。現行ノードでは最大440 GBであり、計測ジョブは旧資料と同じく400 GBを要求候補とするが、PBS疎通ジョブで再確認する。

## 記憶領域

- homeは`/home/users/industry/ai-hpc/apacsc14`にあり、共有home filesystem上にある。
- scratchはLustreの`/scratch/users/industry/ai-hpc/apacsc14`を利用する。
- 2026年9月20日時点のscratch quotaは100 TiB、inode quotaは2億である。
- ASPIRE-2A用の正本は`/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a`以下に置き、GenkaiやGadiのbuild、case archive、cache、run directoryと共有しない。
- login nodeおよびcompute nodeの一時領域、filesystem境界、性能はPBS疎通ジョブで確認してから配置方式を決める。未確認の`PBS_JOBFS`を前提にしない。

## Projectと資源指定

PBS projectは`59000014`である。通常の計測ジョブは次の資源指定を基準とする。

```text
#PBS -P 59000014
#PBS -q normal
#PBS -l select=<nodes>:ncpus=128:mpiprocs=128:mem=400gb
#PBS -l place=excl
```

walltimeは処理別に指定する。ケース準備は性能計測ではないため、必要core数とmemoryだけを要求し、`place=excl`を付けない。

## Profile

Intel VTuneは利用できない。Cray Performance Analysis Tools 22.04.0の`perftools`、`perftools-lite`、`pat_build`、`pat_report`が利用できる。通常計測へinstrumentationを混入させず、profile入口からのみ有効化する。具体的なinstrumentation方法と成果物形式は、安価なPBSジョブでsite module版`simpleFoam`に対して動作確認してから確定する。

## 未確認事項

- home-lab runnerからの非対話接続とActions custom shell
- compute nodeのCPU topology、NUMA、SMT、hostname、`PBS_NODEFILE`、一時filesystem
- `select`、`mem=400gb`、`place=excl`、project指定を組み合わせたPBS投入とrouting先
- PALSによる1/2/4ノードのrank配置
- compute nodeからscratch、home、外部networkへの到達性
- Cray Performance Analysis Toolsによるprofile取得

これらはジョブ投入前の静的検証後、まず短時間のPBS疎通ジョブで確認する。公式ケースや高価なprofileを先に投入しない。

疎通確認には`probe-environment.pbs`を使う。投入後はjob IDを`wait-pbs-job.sh`へ渡し、終了状態とexit statusを確認してからPBS出力を保存する。ジョブ投入にはユーザーの明示許可が必要である。
