# 複数クラスタの実装判断

## 実行の入口

通常計測は`.github/workflows/openfoam.yml`を入口とする。pushでは`[cluster:genkai]`と`[cluster:gadi]`を個別に調べ、複数指定を認める。指定がなければクラスタ上のジョブを起動しない。ノード数は`[nodes:1]`、`[nodes:2]`、`[nodes:4]`で指定し、省略時は1とする。

手動実行は実行先、ノード数、通常計測かプロファイルかを入力欄から受け取る。コミットメッセージは読まない。プロファイルも同じ入口から起動し、同時に選んだ各クラスタへ同じ実行モードを渡す。

`[require-build]`はpush時だけ有効である。手動実行と`[require-build]`のないpushは、対象commitからfirst-parentを1 commitずつ親方向へ辿り、最初に見つかった同じクラスタの利用可能な成果物を使う。Actions全体をworkflow実行日時順には探索しない。利用できるものがなければビルドする。

## 共通部分と固有部分

`scripts/build-openfoam-task.sh`、`scripts/prepare-openfoam-case.sh`、`scripts/run-openfoam.sh`は計算処理を共通化する。クラスタ別ワークフローは、ビルド選択、再利用またはビルド、配備、ケース準備、実行、成果物保管という同じ形にする。ビルドはどちらもlogin runnerで行う。ジョブ投入スクリプト、資源指定、モジュール設定はクラスタごとに持ち、PJMとPBSを一つの投入処理へ統合しない。

実行先の追加では、既存ワークフローへ大きな条件分岐を加えず、実行先固有の再利用可能ワークフローと`platforms/<cluster>/`を追加する。

## 記憶領域と再利用

玄界は短命なビルド領域と一次ccacheをlogin nodeの`/dev/shm`、ソースの鏡像と共有ccacheを`/fast`、圧縮成果物を共有領域へ置く。Gadiは`/dev/shm`が`noexec`なので短命なビルド領域をlogin nodeの`/tmp`へ置き、一次ccacheだけを`/dev/shm`へ置く。圧縮したソースと成果物、共有ccache、ケースキャッシュ、実行領域、回収記録は`/scratch`へ置く。展開したビルド領域とccacheの一時ファイルはActionsの終了処理で削除する。Gadiの実行環境はBuild archive SHA-256ごとの共有runtime cacheとして保持し、run固有のsymlinkだけを削除する。

ビルド成果物、ソース圧縮ファイル、ケースキャッシュはクラスタごとに独立させる。ケースキャッシュは並列数と領域分割条件も識別する。異なるコンパイラ、MPI、ABIの成果物を共有しない。

両クラスタとも、計算ノード上ではメトリクス断片をrun directoryへ閉じる。スケジューラの終了を確認してterminal情報を記録した後、login runnerが全断片を一度だけBigQueryへ送る。BigQueryの資格情報は計算ジョブの環境へ渡さない。GitHub artifactも同じlogin runnerからアップロードする。

## 同時実行

実行機のラベルと同時実行制御名にはクラスタ名を含める。ビルドとケース生成はクラスタ内で必要な範囲だけ直列化し、玄界とGadiを相互に待たせない。Gadiでは、展開runtime 3件がinode hard limitへ同時に到達した実測に基づき、Build archive SHA-256ごとの読み取り専用runtimeを共有する。初回populationだけをGadi内のfilesystem lockで直列化し、Provision、計算、回収そのものには同時実行制御を置かない。

## 内容の識別

コピー元とコピー先を比較するための固定SHAは持たない。スケジューラへ渡したファイルなど、実際に使ったものを記録する。ビルド圧縮ファイル、外部から取得したソース、ケースキャッシュ、最終成果物のように処理や記憶領域の境界を越えるものは、内容を識別して取り違えを防ぐ。

## 本番確認

以下のrunはIssue #18移行前のcavity3D系経路を確認した履歴であり、v2512 `occDrivAerStaticMesh`の完了証跡には用いない。

1ノードの新規ビルド確認はActions run `31940403739`で行った。両クラスタとも選択、login nodeでのビルド、配備、ケース準備、計算、公式判定、成果物保管まで成功した。公式判定は玄界が`FVOPS_trim=1.8101M`、Gadiが`FVOPS_trim=1.7903M`で、どちらも`STATUS: VALID`だった。

`[require-build]`のないpushによる再利用確認はrun `31942772973`で行った。両クラスタともBuildが`Skipped`、Reuseが成功し、その後の全処理も成功した。公式判定は玄界が`FVOPS_trim=1.8073M`、Gadiが`FVOPS_trim=1.7922M`で、どちらも`STATUS: VALID`だった。

手動実行によるプロファイル確認はrun `31943260640`で行った。入力で両クラスタ、1ノード、hotspots、rank 0を指定し、コミットメッセージに依存せず両方の既存ビルドを再利用した。玄界はPJM `6504040`、GadiはPBS `176404848.gadi-pbs`で完走した。両方とも公式判定が`STATUS: VALID`、VTuneの対象処理とVTune自身の終了値が0で、hotspots要約、profile生データ、固定成果物、公式結果、home serverへの保管まで成功した。

2ノードと4ノードは資源対応を単体試験で確認し、必要な実験時に実計算を行う。プロファイル値は通常計測との性能比較には使わない。

両クラスタともIntel C++ 2025.1.1とIntel MPI 2021.15を基準とする。Gadiは`intel-compiler-llvm/2025.1.1`と`intel-mpi/2021.15.0`、課題`hb15`、投入先`normalsr`を使う。玄界は`intel/2025.1.3`と`impi`、投入先`a-batch`を使う。login nodeの物理コア数と実測したメモリ上限に合わせ、ビルド並列数はGadiが16、玄界が120である。玄界のIcx用Make preprocessorは、compute nodeでも`cc1`を解決できるgcc-toolset-11の`cpp`へ固定する。Gadiのノード内通信は`shm`、ノード間通信は`shm:ofi`とする。これらを変える場合は新規ビルドを行い、変更理由をコミット本文へ記録する。

## Gadiの空き容量警告

GadiのActionsに出る空き88 MBの警告は`hb15`の容量やinode制限ではない。runner 2.336.0は作業ディレクトリから`Directory.GetDirectoryRoot`で得た`/`に対して空き容量を調べる。Gadi login nodeの`/`は124 MBのzramで、実測した空き92,430,336 bytesが警告の88 MiBと一致した。

runnerの`_work`は空き約4.7 PiBの`/scratch/hb15`、ビルド領域の`/tmp`は空き約122 GiBのtmpfs、一次ccacheの`/dev/shm`は空き約126 GiBのtmpfsにある。`hb15`の利用者クォータも容量27.19 GiB / 1 TiB、inode 80,018 / 202,000で超過していなかった。警告を避けるための処理を各workflowへ加えず、runner側の監視対象が修正または設定可能になった場合にrunner管理として扱う。

Gadiのソース取得は、実行機に設定済みの`gh`認証を読み取り専用で使う。現在のリポジトリへ発行される`GITHUB_TOKEN`では、組織内の非公開ソースリポジトリを読めないためである。組織共通の専用資格情報を用意した場合は、この依存を置き換える。
