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
- MPI launcherは`/opt/cray/pe/pals/1.1.6/bin/mpiexec`である。OpenMPI固有の起動optionを持ち込まない。
- PBSの`ncpus`は1ノード128であり、基準rank数は1/2/4ノードで128/256/512とする。基準構成では1 physical coreあたり1 rankを配置する。
- 1ノード128 coreは`qdev`または`q4`、2・4ノードは`q5`へroutingされる。`q4`はwalltimeが`02:00:01`以上、`qdev`は`02:00:00`以下である。
- PBSの既定メモリは実行に不足するため、各chunkに`mem=`を必ず指定する。計測ジョブは、完走済みの基準runと同じく1ノードあたり400 GBを要求する。

## 記憶領域

- homeは`/home/users/industry/ai-hpc/apacsc14`にあり、共有home filesystem上にある。
- scratchはLustreの`/scratch/users/industry/ai-hpc/apacsc14`を利用する。
- 2026年9月20日時点のscratch quotaは100 TiB、inode quotaは2億である。
- ASPIRE-2A用の正本は`/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a`以下に置き、GenkaiやGadiのbuild、case archive、cache、run directoryと共有しない。
- login runnerとcompute nodeの間では共有scratch上のrun directoryを境界とする。計算ノードはメトリクス断片だけを書き、終了後にlogin runnerがBigQuery送信とartifact回収を行う。ASPIRE-2A経路は`PBS_JOBFS`を前提にしない。

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

ASPIRE-2AのAMD EPYC Milanに対応するAMD uProf 5.3をprofile経路の正本とする。通常計測用binaryは変更せず、共通`OpenFOAM` workflowの`profile`入口だけが`AMDuProfCLI collect --config hotspots -g --mpi`で全rankを収集する。PALSがuProfのlauncher scriptだけをnode-local領域へstageしないよう、各rankでは`/usr/bin/bash`へ共有領域上のscriptを絶対パスで渡す。計算ノード上で`report --host all --detail --cutoff 30`を実行し、CSVとGUIへimportできる完全なsessionをprofile artifactとして回収する。

uProfはsite moduleにない。AMDのdownload pageでEULAへ同意して`AMDuProf_Linux_x64_5.3.521.tar.bz2`を取得し、次へ配置する。

```text
/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/tools/AMDuProf_Linux_x64_5.3.521.tar.bz2
```

profile workflowはAMD公表MD5 `45437d8bc0b4276a0b78e28d21de23cb`を検証し、初回だけ`tools/amduprof-5.3.521`へ展開する。EULA同意とdownloadはworkflowで自動化しない。Windows版uProf GUIの`Import Session`で回収したsessionを開ける。

最初は権限依存の小さいtimer-based Hotspotsを使用する。login runnerは固定版のreport構造、収集引数、MPI rank/host集計および関数時間を検証し、`profile.uprof_hotspots`としてBigQueryへ送る。検証済みraw sessionと加工済みの要約は別に保存する。IBS、PMC、system-wide、power、OS tracingは別条件のprofileとして、compute node上の権限と実測した問いに応じて追加する。一度のprofileで主要因を混ぜない。

## 検証状況

GNU基準構成の1ノードE2E経路はActions run `35540131525`、PBS job `24720304.pbs101`で完走した。公式parserは65,334,765 cells、128 ranks、39 measured iterationsを`VALID`と判定し、平均13.36250805274359秒/iterationを報告した。1/2/4ノードの反復計測、uProf、AOCCの採否および改善前後の比較は、各runのActions、PBS、公式結果およびartifactを根拠に別途記録する。
