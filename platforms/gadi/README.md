# Gadiの運用

Gadiでは、小ファイルを大量に置く処理と、長く保存する大きなファイルを分けます。

- login runnerの`/tmp`には、ソースの展開先、ビルド作業領域、ccacheの一時ファイルを置きます。
- login runnerの`/dev/shm/ccache-${USER}`には、10 GBを上限とする一次ccacheを置きます。
- `/scratch/hb15/tk7779/openfoam/gadi`には、圧縮したソース、検証済み公式mesh、ビルド成果物、共有ccache、付随記録、ケースキャッシュ、実行領域を置きます。
- 玄界の成果物やキャッシュをGadiで再利用しません。

Gadiの`/tmp`と`/dev/shm`はlogin node上の約126 GiBのtmpfsです。`/dev/shm`は`noexec`なので実行ファイルを生成するビルドには使いませんが、ccacheの保存物には使えます。ビルド終了時に`/tmp`の展開物、中間生成物、ccacheの一時ファイルを削除し、`/dev/shm`の一次ccacheはlogin nodeが保持する間だけ再利用します。実行前に`/scratch`へ展開する実行環境も一時物とし、Actionsの終了処理で削除します。

OpenFOAM runtime 1件の展開には約35,000--37,000 inodeを使い、展開物は計算と成果物回収が終わるまで必要です。2026年8月17日に3 runを同時にProvisionしたところ、`hb15`のinode hard limit 212,100へ同時に到達し、3件とも`tar: Disk quota exceeded`で失敗しました（Actions `32002206618`、`32002206644`、`32002207026`）。失敗した3展開物を削除するとinode使用量は210,900から121,823へ戻りました。Gadi workflowは`gadi-openfoam-runtime`でrun全体を直列化し、1つの展開runtimeをcleanupしてから次を開始します。この制約はGadi内だけに適用し、玄界を待たせません。

32 KiBのファイル4096個を作成した実測では、`/dev/shm`と`/tmp`が約0.08秒、`/scratch`が約5秒でした。一次ccacheを`/dev/shm`、別のlogin nodeからも使う共有ccacheを`/scratch/hb15/tk7779/openfoam/gadi/ccache`へ置きます。`~/.config/ccache/ccache.conf`で一次ccacheを`max_size = 10GB`とし、共有ccacheはビルド後に`ccache --trim-dir`で10 GBまで整理します。`max_size`は共有ccacheに適用されず、容量による整理ではinode数も保証されないため、最初の実ビルド後に共有ccacheの実ファイル数も確認します。

ビルドはlogin runnerで16並列にします。2 socket、24物理コア/socketに合わせた48並列では、公式v2512のlibrary layerをIntel `icpx`でビルドした際に複数のcompiler processが同時にkillされました（Actions run `31990408500`、2026年8月17日）。CPU数ではなく実測したmemory制約を採用し、GCC導入時にも完走実績のある16並列を使います。環境変数`OMP_NUM_THREADS=1`の影響で`nproc`は1を返すため、並列数の決定には使いません。

計算ノードから外部ネットワークへは接続できません。実行中のメトリクスは`/scratch`上のrun directoryへ記録し、PBS終了後にlogin runnerから一度だけ送信します。計算ノードへBigQueryの資格情報を環境変数で渡しません。

GitHub Actionsの実行機は、版ごとに用意した`shared/<version>/externals`を共有します。共有物の初回作成と版の切り替えは運用者が手作業で行い、ワークフローや起動スクリプトから作成・更新しません。各実行機の`bin`、認証情報、診断記録、作業領域は共有しません。

PBSの投入先は課題`hb15`の`normalsr`です。投入、待機、終了確認、資源指定はGadi用のスクリプトに置き、PJM用の処理と共通化しません。

ビルドと実行には`intel-compiler-llvm/2025.1.1`と`intel-mpi/2021.15.0`を使います。これは玄界と同じIntel C++ 2025.1.1、Intel MPI 2021.15系です。プロファイル時だけ`intel-vtune/2025.3.0`も読み込みます。

補助ツールのビルド用にGCC 16.1.0とccacheの`a89f5010f1c8edf231184b3a3a77654e12e4a288`を`~/.local`へ導入しています。玄界と同様に、`~/.local/.setenv`へ`PATH`、`LD_LIBRARY_PATH`、`MANPATH`、`PKG_CONFIG_PATH`などをまとめ、`~/.bashrc`から読み込みます。コンパイラを指定する環境変数はここで設定せず、OpenFOAMのコンパイラはIntel oneAPIのままとします。GCCの48並列ビルドはlogin nodeのメモリ不足で停止したため、GCCだけ16並列、ccacheは48並列とします。ソースと中間生成物は`/tmp`で作成して導入後に削除します。

GitHub Actions実行機の`/`は約124 MiBの読み取り専用zramで、作業領域の空き容量とは無関係です。Actionsの「Free space left: 88 MB」はこの`/`を見た警告です。実際の`_work`とOpenFOAMのデータは`/scratch/hb15`上にあります。2026年8月16日の`lquota`では、課題`hb15`の使用量は26.93 GiB / 1.00 TiB、inodeは75,868 / 202,000であり、いずれもクォータ内でした。この警告をクォータ超過と解釈しません。
