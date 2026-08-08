# 実験メトリクス再設計計画

## 目的

メトリクスは、Gitやlogを複製する保管庫ではない。BigQueryとスプレッドシートから
次の問いへ短く答えるための索引である。

1. どのGit管理下の条件で実行したか。
2. Git外で、実行時にどの条件が選ばれたか。
3. 計算は公式規則上妥当で、科学的な比較にも使えるか。
4. 何を一次指標として、どれだけ速かったか。
5. 比較不能または要調査と判断すべき欠損や競合がないか。

変更内容と変更理由の正本はGit、実行詳細の正本はrun artifact、raw factの索引は
BigQuery、比較規則の正本はGit管理されたSQLとtestとする。BigQuery viewはその
deploy済み実体であり、暗黙に手編集しない。

## 正本とidentity

| 情報 | 正本 | raw metricの役割 |
|---|---|---|
| script、設定、patch | 実行repositoryのcommit | repositoryとfull commitを指す |
| 仮説、変更理由、期待する効果 | commit messageのbody | 保存しない |
| OpenFOAM、ThirdParty source | 各source repositoryのcommit | build provenanceを索引化する |
| stdout、stderr、solver出力 | run artifactのlog | 比較に必要な原始観測だけを索引化する |
| 実行時の環境変数 | scopeごとのbyte-exact snapshot | 全件保存する |
| build済みbinary/archive | immutable artifact | original buildとcontent identityを指す |
| score、speedup、median、順位 | Git管理されたview SQL | raw tableへ保存しない |

次の三つを混同しない。

- source identity: repository URLとresolved full commit
- binary identity: artifact IDとbuild時に一度計算するcontent hash
- reproducibility: toolchain、dependency、build環境、全source commitを含むmanifest

Git管理された通常fileには個別SHA-256 metricを付けない。commitとpathで内容が一意に
なるためである。hashはGit外artifactの同一性、binary転送、manifestの冪等性確認に
限定し、scored solver直前には大容量fileをhashしない。

## Gitによる実験条件の管理

- 性能、計算量、配置、build、collectorの挙動を変える変更はjob投入前にcommitする。
- Actions checkout直後、provision前にclean treeとfull commitを検証する。
- benchmarkに使うcommitはremoteから到達可能、または耐久archiveに保存済みでなければ
  ならない。provenanceのないmanual runは投入しない。
- 一つのcommitは一つの説明可能な変更単位にする。複数fileが同じ仮説を実現する場合は
  同じcommitでよい。
- subjectは変更の要約、空行後のbodyは変更理由、仮説、期待する影響、確認方法を書く。
- 同じ条件の反復ではcommitを増やさず、同じcommitから複数runを作る。
- 性能条件をworkflow dispatch inputへ逃がさず、tracked scriptまたは設定に置く。
- artifactを再利用したrunは、現在の実行commitとは別にoriginal build commitとsource
  commitsを記録する。hardlink先の新しいrun numberをbuild identityにしない。

commit messageの例を示す。

```text
Select the Scotch decomposition backend

The previous decomposition produced a large cell imbalance. Use Scotch because
the hypothesis is that lower partition imbalance reduces the steady-state PCG
time enough to exceed the measured run-to-run noise. Verify the partition and
compare repeated FVOPS_trim values against the parent commit.
```

この文章を`experiment.hypothesis`や`run.note`へ複製しない。人間とエージェントは
runのcommitから読む。

## raw relationの契約

raw tableは現在の三列を維持する。

```text
run    STRING NOT NULL
key    STRING NOT NULL
value  STRING NOT NULL
```

`run`は全producerが共有するglobally uniqueでimmutableなIDである。Actions経路ではjob投入前に
repository、Actions run ID、attemptと各submissionで必須の128-bit random nonceから固定する。nonceは
OS CSPRNGの16 byteを32文字のlowercase hexで表す。manual経路では
clusterを含むUUIDをjob投入前に生成する。`pjsub`返却後にしか分からないPJM job IDはrun IDへ
含めず、immutableなsubmission bindingと`scheduler.job_id`で結ぶ。初期run manifestを書き換えない。
run IDはUTF-8で`^[a-z0-9][a-z0-9._-]{0,199}$`を満たすよう生成し、同じ値を安全なruntime path
componentとして使う。任意のrepository名やuser入力を未escapeで連結しない。
raw relationは次のfunctional dependencyを満たす。

```text
(run, key) -> value
```

- 完全一致する`(run,key,value)`の再送は、論理上の一rowとして扱う。
- 同じ`(run,key)`に複数のdistinct valueがあれば値を選ばず`conflicting`とし、runを
  比較から除外する。
- 既存runの値を訂正しない。訂正測定は新しいrunとして残す。
- row不在は未観測、`value=""`は実際に観測した空文字、`"0"`は真のゼロを表す。
- 取得不能や非該当をplaceholder空文字にしない。
- collector lifecycle keyはsupervisorだけが所有する。collector data fragmentとは独立した
  `lifecycle/<producer>.jsonl`へ、呼出し前に`collector.<name>.started`を耐久appendし、呼出しから
  戻った後にstatusとerror countを持つ`collector.<name>.final`を一度だけappendする。どちらのkeyも
  更新しない。lifecycle journalはatomic sealを要求せず、mergeはvalidなcomplete JSON lineを必ず
  回収し、末尾のpartial lineだけを破棄して`fragment_complete=false`をrunner fragmentへ記録する。
- startedなしは未到達、startedあり/finalなしは中断、finalのfailedは処理済み失敗とする。
  finalがあってもrequired keyがなければ別理由のincompleteとし、viewで混同しない。

`run.metrics_contract`は、emitterとviewの非互換schemaを識別するための小さな運用索引として
意図的に保存する。既存keyの意味、unit、JSON shapeは変更せず、非互換変更は新contract
または新keyにする。

各keyまたはkey patternは、owner、logical type、unit、cardinality、source、scope、
取得時点、required/optional、欠損規則を一つのGit管理registryで定義する。動的keyの
component escapeは単射にし、append/merge時にもownershipと衝突を検査する。

## scalarとcanonical JSON

自然に一つのscalarである値は、そのscalarをSTRINGへ変換する。順序や対応関係を持つ
複数値は、添字付きkeyへ分解せず一つのcanonical JSON valueにする。

canonical JSONはRFC 8785 JSON Canonicalization Schemeに固定する。array順序を保持し、
duplicate object key、NaN、Infinityを禁止する。RFC 8785の表現可能範囲を超える整数や精度を
必要とするdecimalはJSON numberにせず、registryで型を定めたcanonical decimal stringにする。

scalar encoderも次に固定する。

- boolは`true`/`false`、intは符号付き十進最短表現とし、leading `+`/zeroと`-0`を許さない。
- floatは有限IEEE 754値のRFC 8785 number serializationとし、NaN/Infinityを許さない。
- timestampはUTCへ正規化した`YYYY-MM-DDTHH:MM:SS[.fraction]Z`とし、小数秒の末尾zeroを除く。
- 時間のunitは秒、data量はbyteとする。stringはUTF-8で保持する。
- JSON `null`はregistryが定義する「観測済みcompound record内のfield欠損」にだけ使い、
  key全体の取得失敗や非該当には使わない。

これにより同じlogical valueはprocessやlanguageにかかわらず同じbyte列になる。

Pythonの`str(list)`は使用しない。logical typeとunitはvalueから推測せずkey registryを
正本にする。

## 重複を避ける規則

候補Aを削除できるのは、残存するraw factとimmutableなGit/artifact identityだけから、
同じsemantic、source、scope、取得時点、unit、精度で、Aのkey membershipとvalueを
常に一意かつ損失なく復元でき、comparison viewの利用性も失わない場合だけである。

単に値が等しい、名前が似る、またはlogに存在するだけでは削除しない。requestedと
effective、plannedとobserved、schedulerとsolver header、別clockの時間は独立事実である。
公式producerとの照合、schema routing、保存層をまたぐmanifest索引などの正当な重複は、
registryの`justification`へ理由と検証式を書く。

全環境変数の保存は、取り漏らしのないforensic比較という要件に基づく明示的な非最小例外
である。個別env値を別namespaceへ再掲せず、標準Sheetでは比較関連projectionだけを出す。

## write-ahead logと送達

`metrics.jsonl`はBigQueryと同じ`run/key/value`を持つwrite-ahead logである。別event
envelope、型別value列、ack queueは作らない。

target programの薄いhookが出すversion付きdomain recordは、local adapterへの入力または
diagnostic/source logであって第二の送達queueではない。単発factはadapterが直ちにregistryで検証して
WAL化する。反復eventを最終的に一arrayへするfamilyは、fsync済みappend-only domain journalを
artifactとして残し、terminal後のpure reducerが一度だけFactへ変換する。registryはどちらか一方を
familyごとに固定し、BigQueryへの耐久送達の正本は`run/key/value` WALだけにする。

```text
compute producer
  -> logical producer別のmetrics fragmentへ耐久append
  -> 完了fragmentをatomic rename
  -> runnerが全fragmentを検証し、log/fragmentのrun bundleを作成
  -> bundle identityをfinalizer fragmentへappendして最終merge
  -> run bundleとmerged JSONL sidecarをarchiveしchecksum/manifestで検証
  -> runnerがBigQueryへ全行をat-least-once送信またはreplay待ちに登録
  -> archive検証後にruntimeを削除
```

- 一つの完全なJSON lineを`O_APPEND`またはlock下で書き、flush/fsync後に完了とする。
- expected producer集合はGit管理protocolとrun manifestからjob投入前に固定する。scheduler
  accountingとobserved placementは、その期待集合が実際に成立したかを後から検証するsourceである。
- mergeはrun ID、JSON、owner、expected node、一意性を検査し、欠損や異値競合を隠さない。
- BigQuery `insertId`はbest-effortの補助にすぎない。logical viewが完全一致rowをdeduplicate
  し、異値競合を隔離する。
- replayは常に同じrowを全件送ってよい。送信成功後もJSONLをtruncateしない。
- archive/upload失敗時はruntimeを`archive-retry-pending`とし、後続reconcilerが回収する。
- publish失敗時は検証済みarchiveをreplay pendingにし、raw JSONLから再送する。
- remote checksumとmanifest確認前に唯一のlocal copyやGitHub artifactを削除しない。

artifact identityの自己参照を避ける。まずlogとproducer fragmentからrun bundleを作ってhashし、
そのdeterministic URI、bundle hash、manifest identityをrunner finalizer fragmentへappendする。
その後に最終mergeした`metrics.jsonl`をbundleとは別のsidecarとして同じarchive prefixへ保存する。
bundleとsidecarの両方をremoteで検証してからpublish/cleanupする。metrics sidecar自身のhashを
sidecar内のmetricにはしない。

計算nodeではBigQueryへ接続しない。したがって送信用credentialをPJM processへ渡す必要も
ない。各snapshotはそのscopeに実在する環境をfilterなしで保存し、機密値も例外扱いしない。

## 最小の実装境界

対象programへ計測システムの都合を持ち込まないため、責務を次の六境界へ固定する。

1. domain probe/parserは`Fact(key, logical_value)`だけを返すpure functionとする。run ID、文字列化、
   filesystem、BigQueryを知らない。
2. `journal.py`の`Recorder`と`LifecycleJournal`だけがpersist済みrun manifest、registry、canonical
   encoder、fact/lifecycleのappend/fsync、data fragmentのatomic completionを所有する。probeは
   `Recorder`、その外側のsupervisorは`LifecycleJournal`だけを見る。
3. `StageRunner`だけがspawnするactual argv、monotonic timer、signal、child wait statusを所有し、
   観測したfactを`Recorder`へ渡す。
4. runner側`merge`がexpected producer、run ID、owner、一意性、required key、fragment完了を検証し、
   archive対象のmerged JSONLを作る。
5. `ArtifactStore/RunFinalizer`がrun bundle/outer manifestのfsync、seal、put/remote verify、quarantine、reconcileを
   所有する。delivery receiptはrun WALへ戻さず外側のdelivery ledgerへappendする。
6. runner側`publish`だけがBigQuery credential、retry、replayを所有する。collector、solver、PJM
   processはBigQuery、artifact upload、HTTP/cloud client等の外部メトリクス送達networkを使わない。
   solver本来のMPI communicationとnode-local observation IPCはこの禁止対象ではない。

OpenFOAM本体へ必要なhookは、version付きlocal structured eventを定義済み境界でだけ書く薄いadapterとする。
metrics packageやBigQuery clientをlinkせず、送達、再試行、key展開を知らない。実装上は
`domain.py`、`journal.py`、`submission.py`、`stage_runner.py`、`merge.py`、`artifact_store.py`、`publish.py`とdomain別
probe/parserを深いmodule境界にし、CLIはそのcomposition rootに限定する。

OpenFOAM用とQwen用を直ちに第三の共通packageへ統合しない。まず同じcontractとconformance
fixtureを両repositoryで満たし、interfaceが安定してから、canonical encoder、registry validator、
merge validatorだけを抽出する。domain collectorやpipeline固有の失敗処理は共通化しない。

実装開始前の設計正本として、各factの権威source、producer、取得時点、raw key/artifact、validation、
欠損時の扱いは[観測マップ](./experiment-metrics-v2-observation-map.md)に置く。最初の実装sliceでこれらを
一つの機械可読contractへ移し、以後は観測マップの表をcontractから生成する。sourceと取得時点を
contractへ特定できない候補は追加しない。

## 環境snapshot

同じ名前でも時点とprocessが違えば意味が異なるため、次を分ける。

- `env.job_entry.*`: PJM entry直後、module操作やunsetより前の全環境
- `env.host_exec.common.*`: `mpirun`直前のsupervisor full environment
- `env.host_exec.rank.<rank>.delta.*`と`removed_names`: 同じrank wrapperのexec環境とcommonの
  byte-exact差分。両者から各rankの全環境をlosslessに復元する

名前と値はbyte-exactに取得する。nameの各byteは`[A-Za-z0-9_]`だけをそのまま使い、それ以外は
`~HH`の大文字hexでescapeするため単射になる。valueはUTF-8可否にかかわらず全件をRFC 4648の
padding付きBase64にし、registryで`bytes/base64`と宣言する。これにより通常文字列とBase64の
曖昧性を作らない。rank deltaは追加・変更値と削除nameを持ち、commonとの和がfull snapshotに
一致しなければならない。snapshot間で同じ値が重複してもscopeが異なる独立観測である。標準の
二run差分はGit管理された比較関連keyだけを表示し、全env差分は別viewでdecodeして提供する。

## 実験protocolと比較条件

「速い」の一次estimandを公式trimmed FVOPSとする。二次estimandは`StageRunner`が観測する
solver outer-launch wall time、blockMesh/decomposeParを含むend-to-end timeとする。個々の
icoFoam rank process wallと呼ばない。結果を見て指標を
選び直さない。

実験protocol、予定試行数、停止規則、A/B順序はGitへcommitする。実行時に割り当てられた
次の値はGitだけから実行事実を復元できないためraw metricとして残す。

- `experiment.block_id`
- `experiment.block_order`
- `experiment.replicate_index`

既定は各条件5 attemptとし、同じ時間block内でA/Bを交互または事前乱数化順に投入する。
有効runが3未満なら環境差を確定しない。invalid/failed runを遅かったという理由で除外・
置換せず、最大attempt数と置換規則も事前にcommitする。

比較次元はGit管理SQLで次へ分類する。

- 一致必須: workload、source/build artifact、resource lane、precision、instrumentation mode
- 意図的に変えるtreatment: 対象commit、cluster、node type等
- nuisance: hostname、開始日時、queue待ち、個別node identity
- outcome: score、各stage時間、resource値

protocol commitはtreatmentにするkey集合と一致必須key集合を事前宣言する。viewは次の二つを
導出し、fingerprint自体はrawへ保存しない。

- `replicate_fingerprint`: 一致必須条件とtreatment値を含み、同一条件の反復統計に使う。
- `comparison_set_fingerprint`: 宣言済みtreatment次元だけを除き、A/B ratioの候補を束ねる。

commit、artifact、cluster等がtreatmentならcomparison set内では差を許すが、replicate groupは
必ず分離する。nuisanceとoutcomeはどちらにも含めない。競技提出用bestと、環境比較用の全点、
median、MAD、ratio、不確実性を分ける。

## OpenFOAMで保存する原始事実

### run、stage、allocation

- `run.started_at`、`run.finished_at`、`run.elapsed_sec`
- `run.outcome`、`run.exit_code`
- `run.launch_argv`: `StageRunner`がspawnしたprofiler/mpirunを含むexact outer argvのcanonical JSON配列
- 各`perf.stage.<name>.wall_time_sec`と`run.stage.<name>.termination`。terminationはexit、signal、
  spawn errorを区別するJSON objectで、shellの`128+signal`へ潰さない
- `scheduler.request`: runner submit boundaryのlane、PJM script identity、exact `pjsub` argv
- `scheduler.accounting`: 固定した`pjstat --history -S --choose ... --data --delimiter`の結果
- `hardware.nodes`: hostnameごとのhost-invariantなCPU、NUMA、memory等のJSON配列

started/finishedはUTC wall clock、elapsedは同じsupervisor境界のmonotonic clockで取得するため、
wall-clock jumpとtimestamp精度の影響を受けず厳密な派生関係ではない間だけ残す。同一scope、clock、
precisionへ統一した時点でelapsedまたはtimestamp pairの一方をview派生へ移す。

### build provenance

build sidecar manifestに次を固定する。

- buildを定義した`1_OpenFOAM` commit
- OpenFOAMとThirdPartyのresolved commit
- compiler、MPI、toolchain、compile flags
- precision、label size、original build workflow/run
- build archive、`icoFoam` binary、ELF `DT_NEEDED`、build/provision時に解決した`libmpi`の
  path/content identity、MPI version

raw tableは比較groupとartifact到達に必要なcommit、manifest identity、artifact URIだけを
索引化する。archive hashはbuild時に一度計算し、各benchmark runで再計算しない。
archiveとsidecarは二file同時にatomicにはならないため、version directoryへarchiveをrenameし、
hashを含むsidecarを最後にcommit markerとしてatomic renameする。consumerはsidecar存在とarchive
hash一致の組だけをreuseする。

### mesh、partition、配置

- `mesh.topology`: cells、faces、points、internal facesのJSON object
- `mesh.partition.requested`: 実使用dictのmethod、subdomains、renumbering等のJSON object
- `mesh.partition.observed`: partition balance、processor interface、ordering identities等のJSON object
- `solver.runtime_header`: solver logのbuild、arch、nProcs、Hostsを一つのJSON object
- `solver.pstream.startup_applied.rank.<rank>`: `UPstream::init()`が実際に適用したstartup state
- `solver.pstream.runtime_current.rank.<rank>`: `Time`構築とcase override後、time loop前のcurrent state
- `solver.pstream.change_events.rank.<rank>`: runtime中にcontrol再読込で変わった場合だけの順序付きrecord
- `parallel.rank_placement`: rank、hostname、local rank、CPU affinity、NUMA affinityのJSON配列

`solver.runtime_header`、scheduler request/accounting、launcher placementは取得源の異なる独立観測で
あり、互いのprojectionとして削除しない。requested値の別名は作らない。

partition identityはserial mesh/order、partition membership、rank順・local index順を保った
`cellProcAddressing`、必要なsigned `faceProcAddressing`を分ける。headerだけを除外し、global cellが
全rankでちょうど一回、rank集合が連続であることを検査する。
大容量mesh scan、`checkMesh`、partition hashはsolver終了後または別audit jobで実施し、
scored solverのcacheを乱さない。generated `decomposeParDict`と各stage logはartifactへ残す。

同じallocation内のinline post-run auditだけが元runへfactを追加できる。別audit jobは別run IDで
`audit.subject_artifact_identity`によりjoinし、immutable mesh/build artifactから得られるfactだけを
移送可能とする。placement、hardware、runtime stateを元runへ移植せず、sealed WALへ追記しない。

startup recordはcommunicator構築時のnode communicator control/threshold、実際のnode communication、topology control、
configured MPI bufferとclamp/attach後のbuffer byteを持つ。runtime-current recordはcaseの
`OptimisationSwitches`適用後の`floatTransfer`、`nProcsSimpleSum`、exchange/tuning、`commsType`、
polling、`maxCommsSize`に加え、current `nodeCommsControl`、`nodeCommsMin`、`topologyControl`、
`usingNodeComms`を持つ。全rankが出し、viewはexpected全rankの存在と一致を検証する。
`runTimeModifiable`による再読込で値が変わればrank別append-only domain event logへ残す。runnerは
terminal後にcomplete lineとproducer event countを検証し、期待rankごとに一つのordered
`solver.pstream.change_events.rank.<rank>` arrayを必ず一度だけWALへ出す。`[]`は観測済み変更0件、
key不在はreducer/hook失敗を表す。score protocolで変更があった
runはcomparison不適格にする。未確認値をdefaultから推測せず`null`にする。

`parallel.rank_placement`は別の`mpirun`で測らない。同じrank processのwrapperがaffinity等を
記録してから`exec icoFoam`し、solverを実行したrankそのものの配置を証明する。

### solver logの完全record

- `solver.step_timings`: 公式`ExecutionTime` regex match一件につき一要素を作り、直前の
  simulation time、同じtiming行のExecutionTime/ClockTimeの原lexemeとnullable parsed numericを
  持つ順序付きJSON配列。
  simulation timeまたは同一行のClockTimeがなければ、そのfieldだけを`null`にする。
- `solver.pressure_solves`: `Solving for p`一件につき一要素を作り、initial residual、final
  residual、iterationsを持つ順序付きJSON配列。iterationsは公式の行末regexに一致しなければ
  `null`にする。
- `solver.log_markers`: End count、NaN/Inf count、log-reported nCellsのJSON object

失敗runでは0件から期待件数未満の配列をそのまま保存し、欠けた要素を空の期待値で補わない。
同じrecordのfieldをfirst、last、count、iteration配列として別keyへ再保存しない。

pressure solveの残差は、source変更時に未変更buildと同じpartition/rankで軌跡を比較するために
残す。iterationだけの配列はこのcomplete recordの部分集合なので保存しない。

## 公式判定と比較適格性

公式判定関数と科学比較関数を別module、別fixtureにする。v2 cutover前に、現在のshell固有の
regex、BADNUMのline count、missing host許容、invalidでもexit 0というvalidity semanticsを保つ
canonical evaluatorを作り、`tasks/parse_result.sh`をその薄いCLIにする。数値parse、trim計算、
4桁丸めは固定locale/decimal規則へ一本化し、全公表baseline logを再golden化する。旧AWKの中間丸めを
暗黙にSQLで模倣しない。

viewは次を分離する。

- `official_log_valid`: `tasks/parse_result.sh`と完全に同じlog判定
- `official_fvops_trim_m`: 公式式によるscore
- `comparison_eligible`: 科学的な環境比較へ使えるか
- `run_outcome`: pipelineとschedulerの運用上の成否

公式FVOPSの分子は観測cell数ではなく常に`64,000,000 * 4`である。分母は
`ExecutionTime[last] - ExecutionTime[first]`とし、ClockTimeやlauncher wallへ置換しない。
meshが不正ならcomparison対象外にするが、公式式の分子を観測cell数へ変更しない。
baseline ratioはcluster identityが公表baselineとexact matchする時だけ作る。Gadiでは
`9.778M FVOPS`、ASPIRE-2Aでは`5.717M FVOPS`を使うが、Genkai runへ流用せず、承認済みGenkai
baselineがprotocolにない限りratioをNULLにする。

`comparison_eligible`はofficial validに加え、次を要求する。

- meshが64,000,000 cells、192,480,000 faces、64,481,201 points
- ExecutionTimeは有限かつ狭義単調、ClockTimeは整数秒の同値を許して有限かつ単調非減少、
  ExecutionTime trimは正
- requested、allocated、solver Hosts、placement hostsがlaneと一致
- DP、許可されたworkload、`floatTransfer=false`
- build provenance、required collector、artifactがcomplete
- score runはdirect modeで、比較run同士のinstrumentation modeが一致

MPI teardown後の非zero exitでもsolver workloadがofficial validになり得る。原始結果は必ず
収集し、official validityとrun outcomeを混同しない。非単調、ClockTime異常、trim非正は
comparison reasonであり、canonical official evaluatorが定めない限りofficial invalid reasonへ
混ぜない。`official_log_valid=true`でもscoreを算出不能ならscoreはNULLと別reasonにする。

## 1/2/4 node laneと計測擾乱

1/2/4 node条件を`experiments/lanes/openfoam-genkai-{1,2,4}.toml`の別laneとして定義する。
各fileはnode/rank/resource group/transport policy、required producer、instrumentation modeを持ち、
runnerがexact `pjsub` argvとPJM script identityへ解決してmanifestへsealする。各runで次を照合する。

```text
claimed lane == requested nodes == allocated nodes
             == distinct solver hosts == distinct placement hosts
```

rank ID、header nProcs、Hosts合計、placement件数も一致させる。2/4 node laneで
`I_MPI_FABRICS=shm`のようなnode内限定transportを拒否する。

scored solver直前にはBigQuery通信、profiler、MPI debug、`checkMesh`、大容量hashを実行しない。
同一runに必須なのはrank、hostname、local rank、affinityとenvironment deltaの最小recordだけで、
rankはnode-local collectorへ送り、collectorがnodeごと一つのshared durable sidecarへfsyncしてから
ACKする。full topology dumpやverbose diagnosticsはaudit modeへ分ける。最小probeも
probeあり/なしの反復A/Bで事前閾値を超えるなら、そのrunはofficial-validでもcomparison-ineligible
とし、別audit runのplacementを元runへ移植しない。

## BigQuery viewとスプレッドシート

Git管理SQLは次の順でviewを作る。

1. `raw_distinct`: 完全一致rowをdeduplicate
2. `run_key_conflicts`: 同じrun/keyの異値を隔離
3. `run_completeness`: contract、collector、parse、artifact欠損を理由別に表示
4. `openfoam_run_facts_v2`: 固定列のrun比較表
5. `openfoam_run_diff_v2`: 二run間の比較関連差分
6. `openfoam_env_diff_v2`: 全環境変数差分

Gitから生成するcommit dimensionをjoinし、subject、body、commit URLを表示できるようにする。
commit messageをrun metricへ複製しない。Connected Sheetsはraw tableではなくversioned consumer
viewだけを見る。

標準Sheetは少なくともrun、時刻、outcome、completeness、commit、artifact/log link、lane、
build/mesh/placement、official validity、comparison eligibility、FVOPS、stage時間、反復数、
median、MAD、CV、baseline ratioを固定列で表示する。full env差分は別tabにする。

## 決定状態

| 状態 | 決定 |
|---|---|
| 確定 | raw relationは`run/key/value`の三列、compound valueはcanonical JSON |
| 確定 | 定義した各process scopeの環境変数は機密値を含めfilterせずbyte-exactに全件保存 |
| 確定 | native object/structured sourceを優先し、log regexはfixture付きの最終手段 |
| 確定 | compute側はlocal WALだけ、archive/verify/publish/replayはrunner側 |
| 確定 | complete recordのsubsetであるfirst/last/count/average等をrawへ重複保存しない |
| 未決定 | score runへ許すinstrumentation overheadの統計的上限 |
| 未決定 | durable archiveの最終保存先、retention期間、quarantineの容量上限 |

## 実装ハンドオフ

### 公開面とfile境界

実装者が新しい抽象を増やさないよう、package内部の依存方向を次に固定する。

```text
OpenFOAM hook -> version付きsource record -> durable rank journal
                                             -> pure reducer ----\
I/O probe ------> structured source value ---> pure parser ------+-> Fact -> Recorder
StageRunner -----------------------------------------------------/

runner: merge -> ArtifactStore/RunFinalizer -> publish
```

hookはmetric keyや`Fact`を知らず、`run/rank/sequence/kind/version`を持つsource recordだけを書く。
startup/runtime各recordをrank観測のsentinelとし、両方が揃ってchange recordが0件の時だけreducerが
change array `[]`を作る。journal自体がない時は`[]`を作らない。

公開するdomain型はimmutableな`Fact`と`Termination`だけにする。`Fact`はrun ID、owner、encoded
stringを持たず、`Termination`は`exit`、`signal`、`spawn_error`をunionとして表す。最低限のcall
surfaceは次で足りる。

```python
Fact(key: str, logical_value: LogicalValue)
init_run(protocol_path, contract_path, runtime_root, identity) -> ManifestPath
Recorder.open(manifest_path, registry_path, producer_id, runtime_dir)
Recorder.append_many(facts)
Recorder.seal()
LifecycleJournal.open(manifest_path, producer_id, runtime_dir)
LifecycleJournal.append_started()
LifecycleJournal.append_final(status, error_count)
collect_once(manifest_path, runtime_dir, producer_id, probe) -> CollectorOutcome
submit_run(manifest_path, runtime_dir, lane_adapter, pjsub_argv) -> SubmissionOutcome
run_stage(stage_name, argv, *, cwd, stderr_mode, recorder, lifecycle) -> Termination
finalize_run(manifest_path, runtime_dir, archive_target) -> ArchiveReceipt
publish_run(archive_receipt_path, destination) -> PublishReceipt
reconcile_run(manifest_path, runtime_dir, archive_target, delivery_store) -> ReconcileOutcome
```

`Recorder.open`はpersist済みmanifestとregistryをread-onlyで検証し、runを生成・推測しない。
`LogicalValue`はstring、bytes、bool、int、finite float、Decimal、UTC timestamp、またはJSON treeに
限定する。top-level `None`は禁止し、bytes/Decimal/timestampとcompound JSONのencodingはregistryの
logical typeが決める。
`append_many`だけがlogical valueをcanonical stringへ変換し、一行ずつ`run/key/value`へfsyncする。
`seal`だけがdata fragmentをatomic renameして親directoryもfsyncする。`LifecycleJournal`はcanonical
append/fsyncだけを行い、semantic ownerはprobe外側のsupervisorまたは`StageRunner`である。data
fragmentのappend/sealが失敗しても`append_final`を試せる構造にし、lifecycleはsealを待たず回収する。
registry loading、canonical encoding、manifest validationは
`journal.py`のprivate collaboratorとし、それぞれを薄いpublic moduleへ分割しない。

`stderr_mode`は`separate`または`stdout`のclosed enumとし、solverは現行公式logとのparityを保つため
`stdout`へcombined logを作る。log pathはstage nameとruntimeから内部導出し、signalはchild process
groupへforwardしてraw wait statusを保存する。`finalize_run`は唯一のrunner orchestratorであり、
privateなpre-bundle merge、bundle作成/検証、finalizer fact、final merge、metrics sidecar検証を順に
行う。別のpublic `merge_run`と二重にorchestrationしない。

`ArchiveReceipt`はmemory上だけの値ではなく`receipts/archive-verified.json`へsealする。最低限
`schema/run/contract/bundle URI/hash/size/metrics URI/hash/size/target/attempt/started_at/finished_at/outcome/error`を持つ。`PublishReceipt`は
`schema/run/contract/metrics hash/destination/attempt/outcome/response digest`、内部`MergeReport`は
`schema/run/contract/input manifest hash/row counts/conflicts/completeness/output hash`を持ち、いずれも
process再起動後にfileから再構成できる。

`init_run`と`collect_once`は`journal.py`、`submit_run`は`submission.py`、`run_stage`は
`stage_runner.py`、`finalize_run`と`reconcile_run`は`artifact_store.py`、`publish_run`は`publish.py`が
所有する。`cli.py`はargument parseとhandler dispatchだけを行い、manifest生成、scheduler subprocess、
probe lifecycle、quarantine探索を実装しない。

use-case outcomeもclosed schemaにする。`CollectorOutcome`は`status/error_count/fragment_path/complete`、
`SubmissionOutcome`は`bound|failed|unknown|recovered`、receipt path、nullable job ID、`ReconcileOutcome`はreason class、
input receipt、実行action、output receiptを持つ。これらはraw metricではなく、対応するimmutable evidenceを
指すcontrol-plane return valueである。

現行fileからの移行先は次の通りとする。

| 現行 | 移行後の責務 |
|---|---|
| `model.py` | `domain.py`の`Fact`へ置換。`None`/非有限値を空文字へ変える処理を廃止 |
| `context.py` | run生成を廃止し、`journal.py`経由でimmutable manifestを読むだけにする |
| `sender.py`、`credentials.py` | compute packageのcall pathから外し、runner-only `publish.py`へ移す |
| `cli.py` | 下記use caseを配線するcomposition rootだけにする |
| `collectors/`、`readers/` | I/O probeとpure parserを分け、どちらも最後は`Fact`列を返す |
| `command.py`と現行`_stage` | `stage_runner.py`へ集約し、exact argv、同一clock、raw wait statusを一度だけ所有 |
| `prepare.py`、assets、`prepare-case` | canary中はlegacy互換として凍結。v2 cutover時にcase preparation scriptへ移しmetrics packageから外す |
| `scripts/run-openfoam.pjm` | manifest/runtime pathを明示してcompute collectorとstageだけを呼ぶ |
| `.github/workflows/genkai.yml` | pre-submit manifest、submission binding、terminal後finalize/archive/publishを所有 |

実装fileは計画済みの`domain.py`、`journal.py`、`submission.py`、`stage_runner.py`、`merge.py`、
`artifact_store.py`、`publish.py`とdomain別probe/parserに限定する。`manager`、`service`、汎用event
bus、DI frameworkは追加しない。`submission.py`はintent、scheduler adapter、曖昧結果照合を隠す一つの
深いmoduleであり、collectorやpublisherをimportしない。OpenFOAM固有adapterとしてだけ`rank_wrapper.py`と
`node_collector.py`を許可する。PJM supervisorはallocated nodeごとにcollectorを一つ起動し、same-rank
wrapperは第一段階で検証済みglobal/local rank、local size、placement、env deltaだけをnode-local IPCへ
送る。collectorはshared runtimeのplacement fragmentをfsync、rename、親directory fsyncした後だけstartup
ACKする。ACKはbounded timeoutとし、expected collector ready/ACKがない時はsolverを開始せず
configuration failureにする。

wrapperはstartup ACK後、collector IPC FDを継承させてsolverを`exec`する。第二段階ではOpenFOAM hookが
startup/runtime/change source recordを同じFDへ送り、collectorだけが
`domain/pstream/rank-<rank>.jsonl`へcomplete lineをappend/fsyncしてdurable ACKを返す。hookはboundedにACKを
待つが、write/ACK失敗を数値pathやsolver exit codeへ伝播させず、runをconfiguration incompleteにする。
collectorはsolver process group終了とIPC drainまで存続してからjournalをsealする。timing影響はG8で
判定する。

機械可読正本は`experiment-metrics/contracts/openfoam-v2.toml`一fileにする。contract ID、producer
定義、key pattern、owner、logical type、unit、cardinality、source、scope、capture、required、
missing、validation、正当な重複のjustificationを同じentryに置く。lane/protocolはこのcontractに
定義済みのproducer IDからexpected graphを選ぶ。runtime manifestにはcontract IDとcontent hashを
sealし、raw tableにはroutingに必要なcontract IDだけを索引化する。観測マップの表はこのTOMLから
生成し、手書きproseだけを別に保つ。したがってregistryとMarkdown表の二つを正本にしない。

### CLIと設定境界

CLIは次の七orchestration use caseだけを持つ。behaviorを環境変数で切り替えず、manifest、runtime、archiveは
明示引数、比較条件はGit管理protocol、BigQuery宛先はrunner側のGit管理設定から読む。

```text
init-run       runnerがnonce、protocol、expected producerをrun-manifest.jsonへseal
submit         intentをsealしてexact pjsub argvを実行し、result/bindingを耐久化
collect        compute producerを一度実行しlifecycle/data fragmentへ記録
stage          target argvをspawnしterminationと時間を記録
finalize       terminal後にdurable sourceを回収/reduceし、merge、archive、remote verifyまで実行
publish        verify済みarchiveのmetrics sidecarだけをBigQueryへ送達
reconcile      invalid監査、archive-retry、replay-pendingをreason別に冪等処理
```

`init-run`以外は`--manifest`を必須にし、`EXPERIMENT_METRICS_RUN`、PID、PJM IDからrunを再構成しない。
`collect`と`stage`はBigQuery設定やcredentialをimportしない。`finalize`と`publish`を分けることで、
送信障害を理由にcomputeやarchiveを再実行しない。

`submit`は`pjsub`前にexact argvとrun nonceを`submission-intent.json`へfsyncし、stdout/stderrを耐久fileへ
直接redirectする。nonceはlane adapterが保証するscheduler検索可能なjob name/comment/request fieldにも
入れる。明示rejectは`submission-failed.json`、成功はresultとbindingをsealする。応答を確定できない
crashではblind retryせず、nonceでscheduler/accountingを検索する。exact 1 jobだけをbinding化し、0件で
検索完了または複数件、検索不能なら`submission-unknown.json`をsealして人手確認まで停止する。後に
exact 1 jobへ解決した場合もunknownを消さず、`submission-recovery.json`とbindingを追加sealする。この
検索fieldと照合commandを提供できないlaneはunattended v2 submitをreleaseしない。

`node-collector`と`rank-wrapper`は上記七use caseへ数えないOpenFOAM固有internal entrypointである。
`scripts/run-openfoam.pjm`とsolver argvだけが呼び、一般利用者向け設定面にはしない。allocationのnode、
affinity、mesh/hardware auditはPJM scriptが終了する前に耐久化する。runnerの`finalize`はallocationへ
再接続してcollectorを再実行せず、terminal accountingと既存log/journal/artifactのpure parser/reducer
だけを実行する。

### runtimeとarchive layout

一runのruntimeは次の固定layoutにする。任意file探索や「最後に見つかったJSON」を禁止する。

```text
<runtime>/<run>/
  control/run-manifest.json                 # pre-submit immutable
  control/contract.toml                     # 実使用contractのimmutable copy
  control/protocol.toml                     # 実使用protocol/laneのimmutable copy
  control/submission-intent.json
  control/submission.stdout
  control/submission.stderr
  control/submission-result.json            # raw subprocess outcome when available
  control/submission-failed.json            # explicit rejectionの場合だけ
  control/submission-unknown.json           # ambiguous outcomeの場合だけ
  control/submission-recovery.json          # ambiguous outcomeを後で解決した場合だけ
  control/submission-binding.json           # post-submit immutable
  control/job-entry-receipt.json            # PJM側がbindingを待たずにseal
  metrics/lifecycle/<producer>.jsonl         # partial末尾も回収
  metrics/fragments/<producer>.partial       # append中
  metrics/fragments/<producer>.jsonl         # seal済みrename先
  metrics/fragments/runner-finalizer.partial
  metrics/fragments/runner-finalizer.jsonl
  domain/pstream/rank-<rank>.jsonl
  source/placement/node-<node>.jsonl
  logs/<stage>.stdout
  logs/<stage>.stderr
  receipts/scheduler-terminal.json
  receipts/archive-verified.json
  merge/metrics.pre-finalizer.jsonl
  merge/pre-bundle-report.json
  merge/metrics.jsonl
  archive-staging/bundle.tar.zst
  archive-staging/bundle.outer.json
  archive-staging/metrics.outer.json
```

archiveは次の四objectを同じrun prefixへ置く。

```text
bundle.tar.zst       # 下記exact allowlistの事故証拠とsource
bundle.outer.json    # bundleのhash、size、manifest identity
metrics.jsonl        # bundle identityを含む最終raw sidecar
metrics.outer.json   # metrics sidecarのhash、size、contract
```

`bundle.outer.json`はbundle外、`metrics.outer.json`はmetrics外に置くため自己参照しない。remoteで
四objectの存在、hash、sizeを再読取検証して初めてarchive済みとする。

bundle memberはmanifest駆動のexact allowlistとし、`control/`のmanifest、contract、protocol、submission
intent、raw stdout/stderr、実在するresult/failed/unknown/recovery outcome、binding、job-entry receipt、
pre-bundle expected producerの`metrics/lifecycle/`、sealedおよびpartial producer fragment、
`domain/`、`source/`、`logs/`、scheduler-terminal receipt、`merge/pre-bundle-report.json`、自己を除く
member path/hash/sizeを持つ`bundle.manifest.json`を含める。最終`metrics.jsonl`、outer manifest、
archive/delivery receipt、`runner-finalizer` fragment/lifecycle、一時`metrics.pre-finalizer.jsonl`は含めない。
producer fragmentとはpre-bundle mergeが消費したcompute/runner source fragmentの固定集合を指す。
これによりcleanup後もrun identity、
expected graph、partial failure、replay根拠を失わず、finalizer factとのhash cycleも作らない。

runner finalizerはcollector lifecycle keyを作らず、そのstarted/outcome/errorは外側の
`archive-verified`または`archive-retry-pending` receiptだけを正本にする。これによりbundle seal後に
bundle memberが増えない。

`bundle.tar.zst`はpathをbyte順に並べ、tar headerのuid/gid/owner/mtime/modeとzstd parameterを固定して
決定的に作る。保存が必要な元metadataはbundle manifestの値として記録する。同じ入力集合のretryが
同じbundle byte/hashになることをfixtureで保証し、compressor versionもouter manifestへ残す。
最終`metrics.jsonl`は完全一致rowを一件へし、異値conflictは全rowを残したまま`(run,key,value)`の
UTF-8 byte順にsortする。各lineはobject member順`run`,`key`,`value`、空白なし、UTF-8、LF終端へ固定する。

localのmanifest、report、outer、receiptはすべて同directoryの`.partial`へwrite/fsyncし、no-replace
rename後に親directoryをfsyncする。remote四objectは`put-if-absent`とし、既存objectはremote bytes/hash/
sizeがexact一致する時だけ成功扱いにする。異値objectをoverwriteせずcollision quarantineへ送る。

BigQuery attemptはrun archiveとは別namespaceのdurable append-only delivery storeへ
`archive-verified`、`publish-attempt`、`succeeded`、`replay-pending`をimmutable receiptとして保存する。
local `archive-verified.json`はこのreceiptのstaging copyであり、durable copyの確認前にcleanupしない。
runner workspaceはstagingにすぎず正本にしない。invalid inputは`invalid-quarantine`、通信・archive障害は
`archive-retry-pending`に分け、reason classをreceiptへ持たせる。durable delivery/quarantine backend、
retention、容量上限が確定していない間はproduction cutoverのrelease blockerとし、そこへ退避できない
runのruntimeをcleanupしたりworkflowを成功扱いしたりしない。

### 状態と失敗規則

`pjsub`成功応答とjob開始には順序保証がない。PJM supervisorはsubmission bindingを待たず、entry直後に
manifest run IDと自身の`PJM_JOBID`を`job-entry-receipt.json`へO_EXCL相当でsealしてcomputeを続ける。
runnerは`pjsub`返却後または曖昧応答の照合後にbindingをsealし、terminal後のmergeが両receiptの
run/job IDを照合する。bindingをjob entryの前提条件にしない。

mutableな`status.json`は作らず、次のimmutable evidence DAGから状態を導出する。

```text
run-manifest -> submission-intent -> submit outcome -> submission-binding
                         |                    \-> failed/unknown -> optional recovery/binding
                         +-> job-entry -> compute lifecycle/source/fragments ---\
submission-binding -> scheduler-terminal ---------------------+-> post-terminal reducers
                                                              -> pre-bundle merge
                                                              -> bundle verify
                                                              -> finalizer fragment/final merge
                                                              -> metrics verify/archive receipt
                                                              -> durable delivery receipt
```

- lifecycle、metric `.partial`、Pstream/domain journalの各validatorはcomplete JSON lineのvalid prefixを
  回収し、末尾の不完全lineだけを破棄する。partialからfactを回収してもfragment completenessはtrueに
  戻さない。required key欠損、expected producer欠損は、回収できたvalid factを保持して
  completeness reasonを付ける。空文字やzeroで補わない。
- 同一run/keyの異値は両方を保持し、conflictとしてpublishしてcomparisonから隔離する。
- foreign run、unknown key、owner違反、canonical encoding違反は入力をbundleへ保全するが、信頼できる
  metrics sidecarを作らず`invalid-quarantine`へ送る。
- process timeout、signal、spawn errorでもrunnerはscheduler terminal後にpost-run parserとfinalizeを
  実行する。再実行は既存receiptを検証し、同じbyte列なら成功、異なれば競合として止める。
- terminal後にもsubmission bindingとjob-entry receiptの片方が欠ける、またはjob IDが異なるrunは、
  compute結果をbundleへ保全するがpublishせずtracking failureとして`invalid-quarantine`へ送る。
- cleanupはverified archive receiptの後だけ許し、publish失敗は`replay-pending`であってcompute失敗に
  戻さない。

### gateを証明するtest

| gate | 必須test/fixture | 証明すること |
|---|---|---|
| G0 依存境界 | `test_dependency_boundaries.py`、CLI subprocess import trace | domain/probe/journal/collect/stageのtransitive importにpublisher、credential、networkがない |
| G1 値契約 | `test_domain.py`、RFC 8785/decimal/env byte fixture | 空、zero、欠損、非有限拒否、単射escape、canonical byte |
| G2 submit/binding | `test_submission.py`、binding前job-entry/crash fixture | intent先行、曖昧成功でblind retryなし、0/1/複数job照合、entry/binding join |
| G3 local durability | `test_journal.py`、全journalの各byte crash matrix | lifecycle/metric partial/Pstream valid prefix、seal/no-replace/directory fsyncの冪等性 |
| G4 ownership/merge | `test_merge.py`、全producer graph fixture | owner一意性、exact dedupe、異値conflict、required欠損 |
| G5 process観測 | `test_stage_runner.py` | actual argv/cwd、combined log、process-group signal forwarding、exit/signal/spawn error、monotonic境界 |
| G6 archive/送達 | `test_artifact_store.py`、`test_publish.py`、各PUT/verify/BQ accept直後crash matrix | exact bundle allowlist、deterministic bundle、put-if-absent、receipt再開、remote verify前cleanup禁止、二重replay同値 |
| G7 OpenFOAM意味 | `test_observation_contract.py`、baseline log/mesh/Pstream/rank ACK fixture | contract source/時点/owner、sentinel/`[]`、rank欠損、ACK timeout、PJM timeout salvage |
| G8 非擾乱 | lane別hook on/off paired run | 数値同等性と、未決定のoverhead採用基準を同時に満たすこと |

`test_observation_contract.py`はcontractのschemaとowner/source/capture/absenceの完全性を検査し、
生成した観測マップ表がcommit済み表とbyte一致することを検査する。これが「この値はどこから取るか」
を、一つの正本から人間向け表と実行時validationの双方へ機械的に保証する。

### release単位

移行はkeyごとに二重化せず、run contract単位で行う。

1. legacyの出力、shell evaluator、baseline logをgolden fixtureとして凍結する。
2. 専用canary protocolだけでpre-submit manifestとlocal WALを導入し、legacy runの送信経路は触らない。
3. canaryでrunner finalize/archive/publish/reconcileとfault injectionを通す。
4. OpenFOAM固有のnative probe、complete solver record、Pstream/placement sidecarをv2へ追加する。
5. 全laneで意味・数値同等性・非擾乱gateを通してから、run単位でv2を既定にする。
6. v2 viewとSheetを切り替え、legacy-only consumerがゼロになってから旧senderとsubset keyを削除する。

rollbackはlaneのprotocol contractを直前版へ戻して新しいrunを投入する。既存runのmanifestやrowを
書き換えず、一run内でlegacy producerとv2 producerを混在させない。

## 実装順序

1. 現行key、producer、consumer、artifact保存先をinventory化し、key registry、expected producer
   graph、`run.metrics_contract`を作る。contractなしはlegacy、run内のproducer contract混在はinvalid、
   v2 viewはexact contractだけを読む。
2. clean checkout、remote到達性、build sidecar manifest、manual provenance gateを作る。
3. BigQuery credentialをrunnerだけへ移したうえで、現行metric集合のまま`Fact`、`Recorder`、
   JSONL WAL、runner merge/publish、archive/reconcilerを導入する。
4. `raw_distinct`、conflict、completeness、exact-contract v2 comparison viewを旧collectorと
   並行して作る。
5. cavity3Dのcomplete solver record、mesh、provenanceをlegacy collectorと並行追加する。意味が
   変わる既存keyをv2で再利用しない。
6. canonical official evaluatorを作り、旧shell validityと全baseline golden logを照合する。
7. 1/2/4 node lane、同一rank wrapper sidecar、二段階Pstream/partition auditを追加し、最終
   instrumentationを含む全laneでbaselineと比較適格性を再検証する。各laneでunmodified buildと
   hook-only buildを同一mesh/partition/rankで対にし、pressure residual/iteration軌跡と公式markersの
   lexeme一致を数値同等性ゲートにする。
8. Connected Sheetsをv2 viewへ切り替え、旧key consumerがなくなってから派生・部分集合keyの
   新規生成を止める。
9. retention期間後もarchive済みJSONLだけから空tableへ完全replayできることを確認して旧viewを
   廃止する。

冗長keyの停止をview作成より先に行わない。

## 完了条件

- 性能に影響する変更がすべてremote到達可能なcommitにあり、commit bodyから仮説が分かる。
- 新規buildとreuseの両方でsource/build commit、toolchain、binary identityを追跡できる。
- 正当な空文字、未観測、collector失敗、collector未到達、真のゼロをfixtureで区別できる。
- canonical JSONがprocessやobject挿入順に依存せず同じbyte列になる。
- 各key patternのownerが一意で、distinct後のrun/key conflictがゼロである。
- BigQuery停止、append直後crash、部分fragment、二重replay後もJSONLとlogical row集合が一致する。
- upload失敗時にruntimeが消えず、成功・失敗・timeout runのlogとJSONLを回収できる。
- 全baseline golden logでofficial validityとFVOPSが`parse_result.sh`に一致する。
- truncated、NaN/Inf、step/solve/iteration/mesh/rank/trim異常を理由別に判定できる。
- `solver.step_timings`と`solver.pressure_solves`から派生値を一意に計算でき、subset keyがない。
- ExecutionTime、ClockTime、launcher wallの異なるscopeが保存される。
- 1/2/4 laneでrequested、allocated、solver Hosts、placementが一致する。
- direct/profileやplacement probeの計測影響が事前閾値内、またはscore runから分離される。
- unmodified buildとhook-only buildの同一条件でpressure solve軌跡と公式markersが一致し、数値結果を
  hookが変えていない。
- 同一protocolの反復が実行順とblockを含め復元でき、全点、median、MADがSheetに表示される。
- treatment値を含む同一条件だけが同じreplicate groupへ入り、宣言したtreatment差だけが同じ
  comparison set内で許される。
- Sheets利用者がJSON展開なしでcommit、妥当性、一次結果、反復統計、artifactへ到達できる。
