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

`run`は一childの全producerが共有するglobally uniqueでimmutableなIDである。各submission subjectにはjob投入前に
OS CSPRNGの16 byteを32文字のlowercase hexで表す128-bit `subject_nonce`を一つ生成する。regularでは
`submission_subject_id=run_id`、qualificationではglobally uniqueなallocation IDをsubject IDとし、二child run IDは
allocation ID、arm ordinal、各child用CSPRNG nonceから別々に固定する。manual経路でも同じsubject/child規則を使う。
`pjsub`返却後にしか分からないPJM job IDはrun/allocation IDへ
含めず、immutableなsubmission bindingと`scheduler.job_id`で結ぶ。初期run manifestを書き換えない。
run IDとallocation IDはUTF-8で`^[a-z0-9][a-z0-9._-]{0,199}$`を満たすよう生成し、同じ値を安全なruntime path
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
- supervisorは各collector callのstatus/error countを一つの`collection-status.json`へまとめる。個別の
  started/final耐久journalは作らない。post-run validatorはstatusとvariant別expected fragment/keyを照合する。
  status file自体がない中断runはincompleteであり、残ったsource/logだけをbest effortで回収する。

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

## raw metrics exportと送達

v2は任意のcrash境界から一件も失わず再開できることを目的にしない。release gateは、成功した各run
variantの正常pathでcontractが要求する設定、性能値、raw log、PJM accounting、profile runのprofile rawが
Artifactへ収録され、post-run validatorで確認できることである。失敗・中断runの部分回収はbest effortとし、
取得不足なら比較不適格として再実行する。

`metrics.jsonl`はBigQueryと同じ`run/key/value`を持つrun単位のraw exportである。別event
envelope、型別value列、ack queueは作らない。

target programの薄いhookが出すversion付きdomain recordは、local adapterへの入力または
diagnostic/source logであって第二の送達queueではない。単発factはadapterがregistryで検証して
metric fragmentへ書く。反復eventを最終的に一arrayへするfamilyはline-buffered domain JSONLへ書き、stage終了時に
flushする。terminal後のpure reducerが一度だけFactへ変換する。稀なprocess/node failureで末尾が欠ける
ことは許容し、正常終了したのにexpected recordが毎回欠ける実装をreleaseしない。registryはsource
JSONLとmetric fragmentのどちらを正本にするかfamilyごとに固定する。

```text
compute producer
  -> logical producer別のmetrics fragmentへappendしstage終了時にflush
  -> 完了fragmentをtemporary fileからrename
  -> runnerが全fragmentとexpected fileを一度検証してmetrics.jsonlへmerge
  -> log/source/fragmentのrun bundleとartifact-manifest.jsonを作成
  -> run bundle、merged JSONL、artifact manifestをGitHub Artifactへupload
  -> upload成功後にGenkai runtimeを削除可能
  -> archive jobがhome RAIDへscpし、runnerがBigQueryへ送信
```

- 一つのJSON objectを一lineで書き、producer終了時にflush/closeする。各lineやdirectoryごとの`fsync`は
  要求せず、必要なら一定間隔のbuffer flushを使う。
- expected producer集合はGit管理protocolとrun manifestからjob投入前に固定する。scheduler
  accountingとobserved placementは、その期待集合が実際に成立したかを後から検証するsourceである。
- mergeはrun ID、JSON、owner、expected node、一意性を検査し、欠損や異値競合を隠さない。
- BigQuery `insertId`はbest-effortの補助にすぎない。logical viewが完全一致rowをdeduplicate
  し、異値競合を隔離する。
- replayは同じrowを全件送ってよい。送信成功後もarchiveのJSONLを変更しない。publish失敗時はhomeまたは
  GitHub ArtifactのJSONLからworkflowを手動再実行する。
- upload失敗はattempt failureとする。upload成功後はruntimeを削除してよく、home転送のSCPが
  失敗した時だけGitHub Artifactを残す。

artifact identityの自己参照を避ける。全fragmentを一度mergeして`metrics.jsonl`を確定した後、log/source/fragmentから
run bundleを作り、bundle、metrics sidecar、profile raw tarのpath/size/hashを`artifact-manifest.json`へ保存する。
bundle hashやmetrics sidecar自身のhashをmetricへ戻して再mergeしない。publishはremote archive verificationを前提にせず、
同じattemptのlocal/GitHub artifactを入力にできる。

計算nodeではBigQueryへ接続しない。したがって送信用credentialをPJM processへ渡す必要も
ない。各snapshotはそのscopeに実在する環境をfilterなしで保存し、機密値も例外扱いしない。

## 最小の実装境界

対象programへ計測システムの都合を持ち込まないため、責務を次の六境界へ固定する。

1. domain probe/parserは`Fact(key, logical_value)`だけを返すpure functionとする。run ID、文字列化、
   filesystem、BigQueryを知らない。
2. `recording.py`の`Recorder`だけがpersist済みrun manifest、registry、canonical encoder、factのbuffered
   append/flush、data fragmentのcompletionを所有する。supervisorはcollector結果を一つの
   `collection-status.json`へまとめる。
3. `StageRunner`だけがspawnするactual argv、monotonic timer、signal、child wait statusを所有し、
   観測したfactを`Recorder`へ渡す。
4. runner側`merge`がexpected producer、run ID、owner、一意性、required key、fragment完了を検証し、
   archive対象のmerged JSONLを作る。
5. `ArtifactStore/RunPackager`がrun bundle/artifact manifestの作成と検証を所有する。GitHub Artifact uploadと
   home移管はworkflowが担当し、汎用reconciler、quarantine service、delivery ledgerは作らない。
6. runner側`publish`だけがBigQuery credential、retry、replayを所有する。collector、solver、PJM
   processはBigQuery、artifact upload、HTTP/cloud client等の外部メトリクス送達networkを使わない。
   solver本来のMPI communicationとnode-local observation IPCはこの禁止対象ではない。

OpenFOAM本体へ必要なhookは、version付きlocal structured eventを定義済み境界でだけ書く薄いadapterとする。
metrics packageやBigQuery clientをlinkせず、送達、再試行、key展開を知らない。実装上は
`domain.py`、`recording.py`、`submission.py`、`stage_runner.py`、`merge.py`、`artifact_store.py`、`publish.py`とdomain別
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
- `experiment.pair_id`: 欠損・置換後もA/B対応を推測しないprotocol割当ID
- `experiment.planned_replicate_group_id`: submit前に割り当てる非NULL arm/group ID
- `experiment.planned_comparison_set_id`: submit前に割り当てる非NULL比較集合ID

探索比較の既定は各条件5 attemptとし、記述統計だけに使う。同じ時間block内でA/Bを
事前乱数化し、順序を均衡させる。5 attemptや有効run 3件を、equivalence、non-inferiority、
release gateの根拠へ流用しない。意思決定を伴うprotocolは、estimand、margin、想定効果、
分散、alpha、powerからplanned attempt数を事前dimensioningする。invalid/failed runを遅かった
という理由で除外・置換せず、最大attempt数と置換規則も事前にcommitする。

比較次元はGit管理SQLで次へ分類する。

- 一致必須: 実caseから観測したworkload identity、source/build artifact、resource lane、precision、
  正規化したplacement/affinity policy、instrumentation mode
- 意図的に変えるtreatment: 対象commit、cluster、node type等
- nuisance: hostname、開始日時、queue待ち、個別node identity
- outcome: score、各stage時間、resource値

protocol commitはtreatmentにするkey集合と一致必須key集合を事前宣言し、runner manifestがexact policyと
`dimension_policy_hash`をsealする。contractはdimensionごとのallowed classだけを制約し、protocolごとに
変わり得るclassを固定しない。viewは次の二つを導出し、fingerprint自体はrawへ保存しない。hash入力は
contract ID/hash、protocol commit/hash、dimension policy hash、dimension name、logical type、canonical
valueのsorted tupleである。required dimensionがmissing/conflictingならfingerprintを作らずreasonを返す。

- `observed_replicate_fingerprint`: 実観測した一致必須条件とtreatment値を含むnullable検証結果。
- `observed_comparison_set_fingerprint`: 実観測値から宣言済みtreatment次元だけを除いたnullable検証結果。

attempted countのgroupにはnullableなobserved fingerprintを使わない。pre-run protocol assignmentが必ず
非NULLのplanned group/set IDをsealし、failed/invalid runもそこへ残す。eligible countだけが、実観測
fingerprintとplanned policyの一致を要求する。
`planned_replicate_group_id`はcontract hash、protocol hash、dimension policy hash、planned must-matchと
planned treatment dimensionのcanonical tupleから生成する。`planned_comparison_set_id`は同じnamespaceで
宣言treatmentだけを除いたplanned tupleから生成する。`group-1`等の任意labelは表示属性にすぎない。

commit、artifact、cluster等がtreatmentならcomparison set内では差を許すが、replicate groupは
必ず分離する。nuisanceとoutcomeはどちらにも含めない。競技提出用bestと、環境比較用の全点、
median、MAD、ratio、不確実性を分ける。

上記は通常の性能比較policyである。計測擾乱専用protocolだけは、`instrumentation_mode`、
`instrumentation_bundle_hash`、およびinstrumentation patchだけが異なるbuild artifactをtreatmentへ
再分類する。これを行わずにon/offを同じcomparison setへ入れたり、通常比較でmode差を許したりしない。

## OpenFOAMで保存する原始事実

### run、stage、allocation

- `run.started_at`、`run.finished_at`、`run.elapsed_sec`
- `run.outcome`、`run.exit_code`
- `run.launch_argv`: `StageRunner`がspawnしたprofiler/mpirunを含むexact outer argvのcanonical JSON配列
- 各`perf.stage.<name>.wall_time_sec`と`run.stage.<name>.termination`。terminationはexit、signal、
  spawn errorを区別するJSON objectで、shellの`128+signal`へ潰さない
- `scheduler.request`: runner submit boundaryのlane、PJM script identity、exact `pjsub` argv
- `scheduler.accounting`: 固定した`pjstat --history -S --choose ... --data --delimiter`の結果
- `hardware.identity_min`: regularはrunごと、qualificationはallocation内でarm 1前に一度だけ、各allocated nodeで
  `LC_ALL=C lscpu --json`を実行する。node別rawを保存し、`Architecture`、`Vendor ID`、`CPU family`、`Model`、
  `Stepping`、`Model name`とhostnameを固定fieldのaggregateへ変換する。resource classはlane/requestを参照し、
  qualification childはparent sourceをjoinしてrawへ複写しない
- `hardware.topology_full`: profileで取るNUMA、CPU topology、memory詳細。bench consumerは理由なしのNULL

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
build scriptがarchiveとhash付きsidecarを書き終えて成功した後だけcacheへ公開する。consumerはsidecar存在と
archive hash一致の組だけをreuseし、任意のcrash境界から二fileを復旧するtransactionは作らない。

### mesh、partition、配置

- `mesh.topology`: cells、faces、points、internal facesのJSON object
- `mesh.partition.requested`: 実使用dictのmethod、subdomains、renumbering等のJSON object
- `mesh.partition.observed`: `source/mesh/partition-observed.json`のJSON object。global cell数、rank別cell数、
  min/max/mean/imbalance、rank順のcell/face addressing SHA-256、rank pair順のprocessor-interface face数を持つ
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
`partition-observed.json`は`schema_version/global/subdomains/interfaces`の固定objectとし、`subdomains`はrank昇順、
`interfaces`は`(owner_rank,neighbor_rank)`昇順にする。source addressing全体をrun artifactへ複写せず、path、size、
content hashと上記summaryを保存し、complete `checkMesh` outputを`logs/checkMesh.log`へ残す。
大容量mesh scan、`checkMesh`、partition hashはregularではsolver終了後または別audit job、qualificationでは
必ずarm 2終了後に実施し、
scored solverのcacheを乱さない。generated `decomposeParDict`と各stage logはartifactへ残す。

同じallocation内のinline post-run auditだけが元runへfactを追加できる。別audit jobは別run IDで
`audit.subject_artifact_identity`によりjoinし、immutable mesh/build artifactから得られるfactだけを
移送可能とする。placement、hardware、runtime stateを元runへ移植せず、元runのraw exportへ追記しない。

startup recordはcommunicator構築時のnode communicator control/threshold、実際のnode communication、topology control、
configured MPI bufferとclamp/attach後のbuffer byteを持つ。runtime-current recordはcaseの
`OptimisationSwitches`適用後の`floatTransfer`、`nProcsSimpleSum`、exchange/tuning、`commsType`、
polling、`maxCommsSize`に加え、current `nodeCommsControl`、`nodeCommsMin`、`topologyControl`、
`usingNodeComms`を持つ。全rankが出し、viewはexpected全rankの存在と一致を検証する。
`runTimeModifiable`による再読込で値が変わればrank別append-only domain event logへ残す。runnerは
terminal後にcomplete lineとproducer event countを検証し、期待rankごとに一つのordered
`solver.pstream.change_events.rank.<rank>` arrayを必ず一度だけmetric fragmentへ出す。`[]`は観測済み変更0件、
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
- `score_comparison_eligible`: benchの科学的な環境比較へ使えるか
- `qualification_arm_eligible`: D-001の一childとしてcommon sourceとarm固有required familyが妥当か。profileではNULL
- `run_outcome`: pipelineとschedulerの運用上の成否

公式FVOPSの分子は観測cell数ではなく常に`64,000,000 * 4`である。分母は
`ExecutionTime[last] - ExecutionTime[first]`とし、ClockTimeやlauncher wallへ置換しない。
meshが不正ならcomparison対象外にするが、公式式の分子を観測cell数へ変更しない。
baseline ratioはcluster identityが公表baselineとexact matchする時だけ作る。Gadiでは
`9.778M FVOPS`、ASPIRE-2Aでは`5.717M FVOPS`を使うが、Genkai runへ流用せず、承認済みGenkai
baselineがprotocolにない限りratioをNULLにする。

`score_comparison_eligible`はofficial validに加え、次を要求する。

- meshが64,000,000 cells、192,480,000 faces、64,481,201 points
- ExecutionTimeは有限かつ狭義単調、ClockTimeは整数秒の同値を許して有限かつ単調非減少、
  ExecutionTime trimは正
- requested、allocated、solver Hosts、placement hostsがlaneと一致
- DP、許可されたworkload、`floatTransfer=false`
- build provenance、required collector、artifactがcomplete
- score runはdirect modeで、比較run同士のinstrumentation modeが一致

`run_purpose`はplanned/observed双方の必須比較次元で、planned group/set IDのhash入力にも必ず含める。
`score_comparison_eligible`は`run_purpose=bench`かつexact D-001 qualification tupleがadopt済みの場合だけ
trueになり、`qualification_arm_eligible`は`run_purpose=qualification`の一runだけから導出する。
`qualification_pair_eligible`はrun列やraw factへ複写せず、両arm、parent allocation binding、common-source一致を
joinしたpair grainで一度だけ導出する。
profile/qualificationは公式FVOPSを算出・表示してもscore stats、best、rankingへ入れない。

MPI teardown後の非zero exitでもsolver workloadがofficial validになり得る。原始結果は必ず
収集し、official validityとrun outcomeを混同しない。非単調、ClockTime異常、trim非正は
comparison reasonであり、canonical official evaluatorが定めない限りofficial invalid reasonへ
混ぜない。`official_log_valid=true`でもscoreを算出不能ならscoreはNULLと別reasonにする。

## lane scopeと計測擾乱

D-003未回答中は、現行scriptで実証済みの1 node条件だけを`experiments/lanes/openfoam-genkai-1.toml`の
canary lane候補とする。D-003でGenkai 2/4 nodeも今回のscopeに含めるなら、実測でresource group、rank数、
transport、walltimeを確定してから別laneを追加する。推奨どおり競技clusterを後続scopeにする場合は、対象cluster
確定後にcluster固有の1/2/4 node contractを作り、Genkai laneと同一視しない。各lane fileはnode/rank/resource
group/transport policy、required producer、instrumentation modeを持ち、runnerがexact `pjsub` argvとPJM script
identityへ解決してmanifestへsealする。各runで次を照合する。

```text
claimed lane == requested nodes == allocated nodes
             == distinct solver hosts == distinct placement hosts
```

rank ID、header nProcs、Hosts合計、placement件数も一致させる。multi-node laneで
`I_MPI_FABRICS=shm`のようなnode内限定transportを拒否する。

scored solver直前にはBigQuery通信、profiler、MPI debug、`checkMesh`、大容量hashを実行しない。
同一runに必須なのはrank、hostname、local rank、affinityとenvironment deltaの最小recordだけで、
各rank wrapperが自分専用のsidecarへ一度書いてからsolverをexecする。collector daemonやdurable ACKは
使わない。full topology dumpやverbose diagnosticsはaudit modeへ分ける。最小probeも
probeあり/なしの反復A/Bで事前閾値を超えるなら、そのrunはofficial-validでもscore-comparison-ineligible
とし、別audit runのplacementを元runへ移植しない。

`instrumentation_bundle_hash`は、score pathで有効なhook、probe、rank別source schema、sample interval、sink、
buffer、wrapper executable hash、observation contract version、env capture scope、build
patch identityを列挙したcanonical manifestのcontent hashである。`lightweight`等の
labelだけでは同一視しない。D-001が未回答、またはそのexact bundle/laneのqualificationが未通過なら、
最小probeを含むinstrumented runはすべてaudit-onlyとし、自動的にscore-runへ昇格させない。

## bench/profile trackの分離

重いprofilerを挟むrunと公式性能を測るrunは、protocolだけでなくsource trackも分離する。

- `bench`: score、環境比較、qualificationの基点。profiler、polling、verbose traceを入れず、対象pathの
  観測はqualification済みscore bundleだけにする。
- `profile`: `bench`のexact commitへprofile専用overlayを載せる診断track。値は原因探索に使うが、
  score、replicate統計、環境ランキングへ混ぜない。
- `qualification`: unmodified `bench`と最終score bundleを直接比較する専用protocol。profile trackの
  結果で非擾乱を代用しない。

ユーザー判断により、benchでprofile専用metricを取得できないことは許容する。contractの各family/consumer列は
`applicable_run_variants`（`bench`、`profile`、`qualification:off`、`qualification:on`の集合）、
`missing_policy_when_applicable=reasoned_missing`、
`projection_policy_when_inapplicable=silent_null`を別fieldとして持つ。expected producer graphは
run variantごとに作る。同じ列でもapplicable variantでcollectorが失敗した時は通常どおり
status/Evidence/reasonを生成し、非適用variantではRuns projectionを`NULL`にするだけでraw key、family status、
Evidence行、理由を生成しない。

| family | bench | profile | benchで取らない時の意味 |
|---|---|---|---|
| source/build/workload、exact argv/cwd、runner/submit/job-shell env、scheduler、termination、公式solver log/FVOPS、minimal hardware identity | required | required | 欠損ならbench不適格 |
| solver-rank env、rank/local-rank/affinity、Pstream rank別source JSONL | D-001通過bundleだけrequired | required | 未採用bundleならbench protocol自体から除外 |
| mesh/partition/workloadの重いidentity scan | pair/run終了後required | required | target timer外で取得 |
| perf counter、sampling profiler、call stack、verbose MPI/Pstream trace、full topology dump | not expected | protocol指定時required | Runsでは`NULL` |

benchで取得しないprofile専用familyはexpected producer graphから外し、raw key、family status、Evidence行、
NULL理由、reason codeを一切作らず、typed/Sheet値だけを`NULL`にする。benchの`score_comparison_eligible`や
completeness分母へ含めない。反対にbench/profileそれぞれでrequiredと宣言したfamilyのcollector failureは
run全体の通常の品質判定として扱う。profile値を同じprofile baseのbench runへ移植しない。

qualificationは同じpurpose内でもarmごとにgraphが異なるため、expected graphを
`(run_purpose, qualification_arm)`で解決する。`qualification_arm`はplanned treatment tupleの一fieldである。

- `qualification/OFF`: 両arm共通のsource/build/workload、argv、runner/job-shell env、scheduler、termination、
  公式log/result、外側timerだけをrequiredにする。
- `qualification/ON`: OFFのcommon familyに加え、D-001対象のexact minimal score bundleだけをrequiredにする。

両armともprofile-only列は非適用variantなので`silent_null`でNULLだけを返す。OFFでON専用列も同じく
NULLだけとし、理由/status/Evidenceを作らない。最終benchは、実`instrumentation_bundle_hash`がadopt済み
D-001 decision内の`instrumentation_bundle_hash`と一致し、現在runから再構成したqualification tuple全体が
decision内の`qualified_candidate_tuple`と一致し、profile-only producer IDを一つも含まない時だけそのbundleを選べる。
decision identityはdecision record全体のcanonical hashであり、bundle hashとは比較しない。

Git運用はlong-livedな相互mergeではなく、`bench -> profile`を基本方向にする。profile側はbenchの更新を
merge/rebaseして追従する。profileで見つけた最適化はprofile hookを含まない独立commitとしてbenchへ実装し、
その後benchからprofileへ取り込む。profile branch全体をbenchへmergeしない。必要なら二つのworktreeを使う。
branch名はmoving labelなのでidentityにせず、run manifestは次のtagged-union canonical source-track recordをsealする。

```text
bench:
  {run_purpose, repository_identity, score_reference_commit, bench_head_commit}
profile:
  {run_purpose, repository_identity, profile_base_commit, profile_head_commit}
qualification:
  {run_purpose, qualification_arm, repository_identity,
   score_reference_commit, source_head_commit}
```

`source_track_manifest_hash = SHA-256(canonical source-track record)`をindexにする。hashをrecord自身へ入れて
再帰させない。benchでは無計測bundleならreference=head、採用済みscore bundleならscore referenceがbench headの
ancestor、profileではprofile baseがprofile headのancestor、qualification OFFではhead=score referenceを要求する。
qualification ONではscore referenceがsource headのancestorであり、bench/qualification ONのbaseからheadへ
manifest/build validation時に計算したcanonical tree diffがproposed build manifestとinstrumentation bundleの
`instrumentation_patch_identity`へexact一致し、profile-only overlay、profiler flag、workload変更を含まないことを
required gateにする。algorithm/version、base/head、expected patch identity、pass/failをcontent-addressedな
`control/source-track-validation.json`へsealし、query時にGit treeを再取得しない。clean checkoutのHEAD/treeと
proposed buildのsource head/treeがrecordと一致することを検査し、
submodule pointer、file mode、symlink、LFS object identityもtree/diff検証対象にする。全variantのhead/base commitは
remote reachableまたは耐久source archive済みでなければ投入しない。base/headから決定的に計算できるdiff hashは
rawへ重複保存しない。

`source_track_head_commit`、`score_reference_commit`、`profile_base_commit`等のconsumer列はこのrecordから導出し、同じcommit tupleを別raw keyへ
複写しない。profile runはprofile baseが同じでもinstrumentation bundle、build artifact、argv、environmentを
独立に保存し、「profileで速かった」をbenchの性能値へ読み替えない。

## BigQuery viewとスプレッドシート

logical schemaを増やさず、raw tableはdaily ingestion-time partition、cluster順`run,key`で作り、
`require_partition_filter=false`とする。`_PARTITIONTIME`はUTC delivery partition bucketであってrun時刻にも
exact publish時刻にもならず、replayで変わり、streaming write-optimized storageでは一時的にNULLにも
なり得るためcomparison/freshness factへ使わない。project中はpartition expirationを設定しない。
recent publish確認だけ`(_PARTITIONDATE >= ... OR _PARTITIONTIME IS NULL)`を使い、run lookupは
cluster filterを使う。semanticなdedupe/conflict/comparisonは正しさのため全partitionを対象にする。

Git管理SQLは次の非二乗relationを作る。

| object | row grain | 役割 |
|---|---|---|
| `raw_distinct` | unique `(run,key,value)` | 完全一致retryだけをdeduplicate |
| `run_key_singletons` | `(run,key)` | distinct valueが一つだけのtyped pivot入力。異値keyを通さない |
| `run_key_conflicts` | `(run,key,value)` | 異値が二つ以上あるkeyの各distinct valueを一行ずつ保持し、値を選ばない |
| `openfoam_run_reason_items_v2` | `(run,reason_item_id)` | class/code/subject/canonical detail JSONを持つ全理由の唯一のlong relation |
| `openfoam_run_facts_v2` | one row per run | conflict-free factだけをtyped固定列へpivot |
| `openfoam_run_commits_v2` | `(run,repository,commit_role,commit)` | source-trackとbuild manifestからrole付きcommitを導出し、Git subject/body/URLをjoin |
| `openfoam_run_evidence_items_v2` | `(run,family,evidence_item_id)` | producer/capture/scope/raw key/artifact member/valueごとの決定的evidence |
| `openfoam_run_family_status_v2` | `(run,family)` | evidence itemsからexpected/observed/status/reasonを集約 |
| `openfoam_qualification_allocations_v2` | `(allocation_id)` | parent evidence artifactからordered child IDs、binding、scheduler request/accounting/terminal、job-entry env locator/status、minimal hardware consensus/reasonを一度だけ投影 |
| `openfoam_comparison_dimensions_v2` | `(run,dimension)` | `must_match/treatment/nuisance/outcome`とcanonical value |
| `openfoam_estimand_points_v2` | `(analysis_purpose,run,estimand_id)` | bench/qualificationのpurpose-awareな基底point。profileは行を出さない |
| `openfoam_replicate_points_v2` | `(run,estimand_id)` | `estimand_points`のscoreだけを取り、benchのprotocol、group/treatment、attempt/order/value、eligible/reasonsを全点表示 |
| `openfoam_replicate_stats_v2` | `(contract_hash,protocol_hash,dimension_policy_hash,planned_replicate_group_id,estimand_id)` | bench attempted全件とobserved一致済みeligible n、median、MAD、CV。bestとは別 |
| `openfoam_paired_points_v2` | `(analysis_purpose,contract_hash,protocol_hash,dimension_policy_hash,planned_comparison_set_id,pair_id,estimand_id,baseline_treatment_id,candidate_treatment_id)` | bench通常比較またはqualificationのprotocol指定pair。profileは行を出さない |
| `openfoam_paired_comparisons_v2` | `(analysis_purpose,contract_hash,protocol_hash,dimension_policy_hash,planned_comparison_set_id,estimand_id,baseline_treatment_id,candidate_treatment_id,estimator_id)` | ratio方向、pair数、interval、decision、reason。未決定基準はNULL |
| `openfoam_env_facts_v2` | `(run,scope_kind,scope_instance,escaped_name)` | common/deltaから復元したfull snapshotのbyte-exact valueと由来 |
| `openfoam_run_diff_v2(left_run,right_run)` | table function、一expected dimensionまたはsentinel一行 | 二runのvalue/equality/class/blocking reason |
| `openfoam_env_diff_v2(left_run,right_run)` | table function、一scope/nameまたはsentinel一行 | full outer diffのadded/removed/changed/sameと左右値 |
| `openfoam_archive_attempts_v2` | `(github_run_id,github_run_attempt)` | workflowが書くupload/SCP/publish outcomeと時刻、GitHub Artifact保持有無、home空き容量 |
| `openfoam_sheet_status_v2` | one row | SQL/contract identity、query時刻、latest publish/archive、未移管Artifact数、home空き容量、issue件数 |

environmentの`scope_kind`はcontract enum `job_entry|host_exec_rank`、`scope_instance`はnullable node/global rank等を
field名付きcanonical JSONにしたinjective IDで、Sheetにはtyped scope列も出す。display hostnameだけをjoin keyに
しない。`escaped_name`はbyte nameの単射表現であり、同名でもscopeが違えば別rowである。

archive workflowは一attempt一rowのoperational recordだけを残す。hash chain、delivery FSM、receipt storeは
作らない。Data Statusはこのtableの`MAX`時刻と最新attempt、GitHub artifact inventory、home `df` snapshotを
表示する。scientific factやprofile missing reasonへdelivery状態を複写しない。
family statusはevidence itemのaggregateであって同じgrainのsubsetではない。別の保存表やproducerを作らず、
run facts/statusのmissing/incomplete countも同じaggregateを使う。
`reason_item_id`はreason class/code、`subject_kind=raw_key|consumer_column|family|contract|dimension|evaluator`、
subject ID、nullable raw key、`detail_sha256`から決定的に作る。`detail_json`はexpected/actual、evaluator、
source locator等を持つcanonical typed JSONで、hashだけで内容を捨てない。blocking booleanも持つ。

上表は独立した保存メトリクス集合ではなく、rawを唯一の正本とするlogical query interfaceである。
相互に列が重なるprojectionも別のraw producerやscheduled copyを作らない。非NULL`expected_locator`は
contract field/key patternまたはartifact fieldとexpected scope instanceを一意に表す。`source_instance_id`は
contract hash、expected locator、producer、capture、expected scope instanceだけから作る観測非依存IDである。
`evidence_item_id`はsource instance ID、evidence kind、nullable concrete raw keyまたはartifact content
identity/member、nullable value hashまたはmissing sentinelから決定的に作る。mirror URIは表示locatorであり
IDへ入れない。contractの
expected rank/source graphからmissing instanceも行として展開し、artifact-only証拠はraw keyをNULLにする。
同一source instanceの異値はvalue hashごとに別itemとしstatusをconflictingにするが、familyのexpected/
observed countはdistinct source instance IDを数えて水増ししない。全valueは`run_key_conflicts`へ戻せる。

`openfoam-v2.toml`にはraw contractと同じcommitで`[[consumer.run_column]]`を置く。各固定列は少なくとも
`name/type/unit/source_family/raw_pattern|artifact_field/scope_cardinality/json_path/reducer/
conflict_rule/transform_id/applicable_run_variants/missing_policy_when_applicable/
projection_policy_when_inapplicable/dimension_name/allowed_classes`を宣言する。
applicable variantの`reasoned_missing`列だけ`null_reason`を必須にする。`silent_null`はsource種別でなく
当該run variantで非適用と宣言されたRuns列へ作用し、RunsをNULLにするだけでraw key、family status、Evidence、
reason item/codeを生成せず、NULL reason検査からも外す。複数sourceを使う
派生列はordered source listを持つ。生成SQL、Evidence lineage、Sheet headerだけが
これを読み、手書きpivotを許さない。contract testは各consumer列についてexactly one column definition、
sourceの存在、type/transform、variant applicability、applicable missing policy、inapplicable projection policyを検査する。これにより列名からraw key patternまたはartifact/
Git dimensionへ機械的に一意に遡れる。

同じcontract/protocolに`[[consumer.estimand]]`を置き、`estimand_id`、source/transform、logical type、unit、
改善方向、eligibility rule ID、許すstatistic/estimator/interval、`applicable_run_variants`を固定する。
comparison dimensionとestimandはsource列のapplicabilityと二つのmissing/projection policyを継承する。当該variantで
silent NULLとなる列をdimension/estimand、observed fingerprint、completeness count、config diff expected gridへ
入れない。point viewはprofile runを展開せず、bench/qualification runとそのpurposeにapplicableなestimandの
直積だけを展開する。applicable source欠損は行を落とさずNULL value+reasonにする。protocolは一次・二次
estimandとdecision対象を事前指定し、view実装者が結果を見て選ばない。

全run pairのdiffを通常viewとしてmaterializeしない。agent/SQL利用者とConnected Sheetsは二つのcell
parameterを持つcustom query `SELECT * FROM dataset.openfoam_run_diff_v2(@LEFT_RUN,@RIGHT_RUN)`、同env diffを
直接呼ぶ。table functionはNULL、同一、存在しないrunを`selection_status`で拒否し、full outer joinで
片側欠損を落とさない。invalid selectionはzero rowにせず、`row_kind=selection_error`のsentinelを必ず一行
返す。valid config diffは左右contract/protocolのdeclared dimension gridのunionから始め、左右のdefinition
hash、logical type/unit/transform、policy classを表示する。definition/policy互換性を別判定し、互換な行だけ
equalityを計算する。非互換、片側undeclared、観測missingも固有`value_status`で残す。

env diffは左右manifestのexpected scope gridとscope-level family statusを先にjoinする。同scopeの両snapshotが
completeな場合だけvariableを`added/removed/changed/same`とし、片側collector/snapshot欠損は
`unknown_left|unknown_right|unknown_both`、片側でscope非該当なら`not_expected_left|not_expected_right`の
scope sentinelを返す。absence、未観測、非該当を混同しない。UI filter/
pivotだけで二run制約を実現しない。Sheetのfilterなしでfull environment extractを作らない。値はユーザー
指示どおり内部利用者へmask/redactせず表示するが、Sheetとdatasetの共有先を
同じ内部ACLへ限定する。

`openfoam_run_facts_v2`は少なくとも次の固定列を持つ。ここで挙げる名前をcontractのconsumer projectionへ
個別登録し、概念名だけの列を作らない。aggregate統計をrun rowへ複写せず、replicate viewを別tabにする。

| group | columns |
|---|---|
| identity/protocol | `run_id`、`contract_id`、`contract_hash`、`protocol_id`、`protocol_hash`、`dimension_policy_hash`、`planned_replicate_group_id`、`planned_comparison_set_id`、`planned_attempts`、`max_attempts`、`stopping_rule_id`、`block_id`、`block_order`、`pair_id`、`replicate_index`、`lane_id`、`run_purpose`、`qualification_arm`、`instrumentation_mode`、`instrumentation_bundle_hash`、`instrumentation_qualification_decision_hash`、`instrumentation_qualification_status`、`started_at`、`finished_at`。qualificationでは`block_id=allocation_id`なので別列を作らない |
| source/artifact | `source_track_head_commit`、`score_reference_commit`、`profile_base_commit`、`source_track_manifest_hash`、`openfoam_commit`、`thirdparty_commit`、`build_manifest_sha256`、`qualification_parent_archive_hash`、`bundle_uri`、`bundle_hash`、`solver_log_member`。role別commit metadataは`openfoam_run_commits_v2`だけに置き、別のfull log URIは保存しない |
| quality | `required_families_complete`、`missing_family_count`、`incomplete_family_count`、`conflicting_key_count`、`cast_failure_count`、sorted `reason_codes`、`official_log_valid`、`official_score_status`、`score_comparison_eligible`、`qualification_arm_eligible` |
| termination | `run_outcome`、`run_exit_code`、`solver_termination_kind`、`solver_exit_code`、`solver_signal`、`scheduler_terminal_state`、`scheduler_exit_code` |
| workload/build | `workload_id`、`workload_manifest_identity`、`workload_match`、`precision`、`build_artifact_sha256`、`compiler_identity`、`mpi_identity` |
| topology/placement | `requested_nodes`、`requested_ranks`、`allocated_nodes`、`allocated_ranks`、`solver_host_count`、`solver_nprocs`、`solver_host_rank_sum`、`placement_host_count`、`placement_rank_count`、`placement_rank_set_valid`、`resource_group`、`transport_policy`、`effective_transport`、`transport_valid`、`placement_affinity_signature`、`placement_policy_valid` |
| hardware | bench coreの`cpu_model_consensus`、`hardware_identity_min_reason_codes`と、profile-onlyの`physical_cores_per_node_consensus`、`numa_nodes_per_node_consensus`、`memory_bytes_per_node_consensus`、`hardware_topology_full_reason_codes`。profile-only列はbenchで理由なしのNULL |
| mesh | `mesh_cells`、`mesh_faces`、`mesh_points`、`mesh_internal_faces`、`requested_partition_identity`、`observed_partition_identity`、`partition_valid` |
| Pstream | `pstream_startup_all_ranks_present`、`pstream_startup_consensus`、`pstream_runtime_all_ranks_present`、`pstream_runtime_consensus`、`pstream_change_event_count`、`pstream_unchanged`、`float_transfer`、`default_comms_type`、`pstream_buffers_algorithm`、`using_node_comms`、`node_comms_control`、`node_comms_min`、`topology_control`、`configured_mpi_buffer_bytes`、`attached_mpi_buffer_bytes`、`nprocs_simple_sum`、`nprocs_nonblocking_exchange`、`tuning_nbx`、`n_poll_proc_interfaces`、`max_comms_size` |
| outcome | `official_fvops`、`official_trim_sec`、`solver_outer_wall_sec`、`block_mesh_wall_sec`、`decompose_par_wall_sec`、`pipeline_end_to_end_wall_sec` |

`placement_affinity_signature`はhostnameや物理CPU番号を直接hashせず、rank/local-rank順のCPU-set
cardinality、rank間overlap、NUMA binding、pinning shapeをcanonical JSONにした実値である。
`placement_policy_valid`はその実値とlane要求の照合結果であり、異なる二つのvalid policyを同一視しない。
rank別のfull CPU set/hostはEvidenceに残す。

applicableなtyped columnは`run_key_singletons`だけを入力にしてcontract typeから`SAFE_CAST`/JSON validationし、cast
失敗をNULLと`run_reason_items`へ出す。複数値を`MAX`、`ANY_VALUE`等で隠さず、conflict keyはwide列をNULL、
runをpurposeに対応するcomparison-ineligibleにする。applicable列のmissing/conflict/cast-invalidを同じNULLだけへ潰さない。
当該variantで`silent_null`となる列はこの処理へ入れない。reason itemsは
fact issue、family status、official score status、comparison evaluator、protocol/dimension validatorを
UNIONする。Sheet用`reason_codes`はこのrelationだけをlexicographic sortして`;`区切りSTRINGへ投影し、code
自体に`;`を禁止する。applicableなeligibilityがfalseでblocking reasonが0件のrunをcontract testで拒否する。
commit metadataはGitから`openfoam_run_commits_v2`へrole付きでjoinし、commit messageをrun metricやRunsの
曖昧な単数列へ複製しない。

qualification parentはprogram runではないので`run/key/value`へ擬似runとして入れない。runnerがparent
`allocation-evidence.json`を同じqualification artifact setへ書き、`openfoam_qualification_allocations_v2`が
allocation ID一意性とchild referenceを検査して投影する。qualification childの
Runs/paired viewはqualification childの`block_id`でjoinし、同じscheduler request/accounting/terminalを二childの
raw keyへ複写しない。Environmentは同じjoinからparent job-entry snapshotをdecodeし、Runsはminimal hardwareと
reasonをjoinする。regular runのscheduler/env/hardware factは従来どおり自身のrawへ置く。

`openfoam_estimand_points_v2`はbenchとqualificationの基底pointを`analysis_purpose`付きで表し、profileには
行を出さない。replicate pointsはそのscore subsetとしてbenchのfailed/invalidも削除せずreason付きで全件残し、protocol、planned/max attempt、stopping
rule、planned group/set ID、pair/block ID、estimand ID、nullable observed fingerprintを持つ。statsはplanned
groupでattempted nを数え、事前protocolのeligible ruleとobserved fingerprint一致を満たす点だけをeligible nへ
数える。treatment IDは宣言した全treatment dimensionのname/type/canonical value sorted tupleのhashで、
canonical JSONを表示属性にする。paired pointsはestimand pointsから
`analysis_purpose=score|qualification`を持ち、protocolが割り当てたpair IDだけを対応付け、欠損・置換後に
block/orderから推測しない。scoreは`score_comparison_eligible`、qualificationは
両armの`qualification_arm_eligible`、parent binding、common-source equalityからpair grainで導出した
`qualification_pair_eligible`だけを使い、purposeを跨いでpairにしない。paired comparisonはbaseline/candidateを順序付きで保持しratioを
`candidate / baseline`と定義し、planned/attempted/eligible pair count、interval method/level、decision
criterion ID、equivalence bounds、alpha、target power、pilot evidence identity、estimate/CI、decision
class/reasonを併記する。これらはpoint rowとversioned protocolからquery時に導出し、rawへaggregateの
第二正本を作らない。estimator/intervalはprotocolが事前指定した方法だけを使い、
`instrumentation_overhead_decision`は現在未決定のcriterionを確定するまでNULLにする。暫定式を埋めない。
breakingなcolumn/type/meaning変更は
既存v2 viewを書き換えずv3 objectを作る。

Connected Sheetsは次のtabだけをversioned consumer objectへ接続する。

1. `Runs`: one run/rowの固定列。JSON展開なしでquality、config、一次結果、artifactへ到達する。
2. `Replicates`: point viewとstats/comparison viewを別tableとして全点とrobust statisticsを示す。競技bestを同じ列で置換しない。
3. `Evidence`: 選択runのfamily/evidence itemごとに、scope、raw key、値hash、source、artifact member、欠損理由を示す。
4. `Config Diff`: 左右run cell parameterからtable functionを直接呼ぶ。
5. `Environment`: 左右run cell parameterからscope-aware diffを直接呼び、full byte-exact envをmask/redactせず比較する。
6. `Data Status`: contract/SQL identity、各query時刻、latest publish/archive、未移管Artifact数、home空き容量、issue件数を表示する。

Connected Sheetsは自動同期されないため、deployment checklistにrefresh ownerとscheduleを記録する。
各Connected object自身のqueryで
`query_generated_at`を出し、Data StatusのSheet-local rangeが各tabのtimestamp cellを参照する。BigQueryの
status queryが他objectのrefresh時刻を知るとはみなさない。preview/extract/pivotは事前filter後の
row数とresult byteを検査し、保守的な内部budget（pivot 80,000 result/8 MB未満、extract 400,000 row/
8 MB未満かつ4 million cells以下）を超えたらscope単位に決定的分割する。`LIMIT`で先頭だけを
表示しない。
標準tabへraw tableやunbounded env relationを直接接続しない。

consumer relationはまずlogical viewとtable functionだけで実装し、同じprojectionのscheduled tableを
先回りして複製しない。実測したrefresh latency/bytesが運用budgetを超えた場合だけ、rawから完全再生成
できるcache tableを別contractで導入する。

この物理設計はBigQueryの[ingestion-time partitioning](https://docs.cloud.google.com/bigquery/docs/partitioned-tables)、
[STRING clustering](https://cloud.google.com/bigquery/docs/creating-clustered-tables)、consumer運用は
[Connected Sheetsのrefreshとresult制約](https://support.google.com/docs/answer/9703214)、
[cell parameter付きcustom query](https://support.google.com/docs/answer/9703000)を前提にする。

## D-001: bench側計測の非擾乱qualification

### 調査結果

profilerをprofile trackへ分離しても、benchに残すconfig hook、rank sidecar、Pstream source writeにも負荷はある。
したがって「profile branchを使った」こと自体を非擾乱の証明にはしない。一方、profile専用のperf/profiler、
polling、verbose traceはscore bundleへ含めず、このgateの対象をbenchで本当に有効にする最小bundleへ限定する。

公式baseline logの`ExecutionTime[last] - ExecutionTime[first]`を同じ式で再計算すると、独立job間のtrim時間は
次のように揺れる。これはinstrumentation on/offのpaired分散ではないためsample-size計算へ直接使えないが、
全lane共通の固定5 pairに根拠がないことは示す。

| cluster | 1 node CV | 2 node CV | 4 node CV | run数 |
|---|---:|---:|---:|---|
| Gadi | 0.68% | 0.16% | 0.72% | 3 / 3 / 8 |
| ASPIRE-2A | 1.99% | 7.45% | 4.47% | 3 / 8 / 8 |
| Iris | 0.39% | 0.46% | 0.38% | 2 / 2 / 2 |

再計算sourceは[`tasks/baseline_logs`](../tasks/baseline_logs/README.md)である。paired-tの90% CIを5 pairで
ratioの約±1%へ収めるには、平均差が0でも観測paired log-ratio SDが約1.04%未満でなければならない。
よって5 pairはscreen/pilotにはなっても、未知分散のformal qualificationにはならない。

### 推奨option R（ユーザー回答待ち）

判定単位は次のtupleとし、どれか一つでも変わればdecisionを再openする。branch名や最新commitは使わない。

```text
(repo, lane_id, score_reference_commit, reference_build_manifest,
 proposed_build_manifest, protocol_hash, workload_manifest_identity,
 instrumentation_bundle_hash, toolchain/mpi identity)
```

採用時のGit管理immutable decision recordは`decision_id`、`decision=adopt|reject`、`qualification_protocol_hash`、reference tuple、
`qualified_candidate_tuple`（repo/lane/source-track head/base、proposed build、workload、bundle、toolchain/MPI）と
判定evidenceを持つ。通常bench manifestは`instrumentation_qualification_decision_hash`をsealし、自身の通常
protocol hashをqualification protocolへ一致させるのではなく、実runから再構成したcandidate fieldsをdecision内の
`qualified_candidate_tuple`へ一致させる。source、build、workload、toolchain、MPI、bundleのどれかが変われば
decisionを再openする。同じbundle hashのまま他fieldだけ変えたrunを採用しない。runnerはsubmit前にdecision
canonical bytes/hash、`decision=adopt`、candidate一致を検証し、参照したrecordを
`control/instrumentation-qualification-decision.json`へimmutable copyする。Runsは
`instrumentation_qualification_decision_hash`と
`instrumentation_qualification_status=not_required|pending|adopted|rejected|invalid`を持つ。無計測benchは
`not_required`、未回答中のinstrumented benchはhash NULLかつ`pending`でscore不適格、adoptedだけがscore候補である。

専用comparison policyでだけinstrumentation/build variantをtreatmentにする。primary armは次である。

- `OFF`: unmodified bench solverと、両arm共通の外側timer/log保存だけ。
- `ON`: release予定binaryと、bench score runで有効にするhook、rank別source fileをすべて含む最終bundle。

同一binaryのdisabled/enabled比較はactive costの原因分解には使えるが、compiled hookの配置効果を消すため
release gateを代用しない。必要時は`unmodified / final-build-disabled / final-build-enabled`をprofile診断で
比較し、採用判定は常にunmodified OFF対final ONを直接見る。

各laneで、まずconfirmatoryへ混ぜない8 planned pilot pair slotを事前commitする。一pairの二armだけを同じ
allocationで隣接実行し、pair間は別allocationにしてallocationを統計上の独立単位にする。`allocation_id`と
`pair_id`は一対一であり、一allocationに0または2以上のpairが属した場合は全pairをprotocol-invalidとして
attempted pointだけを保持し、estimate/SD/CIへ入れない。effective N、mean、SDは一つのeligible pairを持つ
distinct allocationだけから計算する。二つのarmは独立case directoryを
使うが、同じnode、rank mapping、cpuset、transport、mesh、既存decompositionを使い、間にbuild/copy/
decompose/checkMesh/full audit/archiveを挟まない。commit済みseedで4 slotをOFF→ON、4 slotをON→OFFへ割り当てる。

submission subjectを`regular_run(run_id)`と
`qualification_allocation(allocation_id,pair_id,ordered_child_run_ids)`のtagged unionにする。
qualificationでは通常run manifestの親にimmutable qualification-allocation manifestを一つ置き、
`qualification_allocation_id/scheduler submission-binding identity/pair_id/ordered child run IDs/OFF-ON assignment/
common lane-node-rank-binding policy`を最初のarm開始前にsealする。submission bindingとjob-entry fileは
allocation IDとordered child run IDsを所有し、各child runは独立したsource/build/argv/timer/log/metricsを
持つ。各childはparent manifest hash、job ID、arm ordinalをimmutable parent refで参照し、scheduler request/
accounting/terminalを複写しない。各childの`block_id=qualification_allocation_id`とする。

両case/buildと全common inputはarm 1前に準備し、qualificationではheavy mesh/partition/hardware auditとarchiveを
arm 2終了後だけに行う。child solver outer timer終了とmetrics fileのcloseを分け、arm間にはbuild/copy/decompose/
checkMesh/full audit/archiveを一切挟まない。scheduler terminal後、`finalize` commandはparent binding/entry/terminalと
両childを一度検証し、parent evidenceと二childのsource/log/metricsを同じworkflow artifact setへまとめる。
arm間crash、一方だけ未起動、一方だけmetrics未完成でも回収できたsourceをbest effortで残し、
pairをineligibleにして別allocationのrunと再pairしない。

全8 planned slot終了後、eligible subsetからpaired log差のSDの片側80%上限を求める。eligible=8になるまで
追加せず、推奨option Rの`minimum_eligible_allocations=8`を下回れば`pilot_insufficient`とする。不足時は結果を
見てreplacementを足さず、原因修正後に新しい固定pilot protocolを事前commitする。同じlaneについて事前登録済みの過去paired SDがあれば
その大きい方を`sigma_plan`にする。次のunknown-variance paired TOSTでpower 80%以上となる最小の偶数Nを
求め、confirmatory protocolへ一度だけcommitする。planning上の真値は0.3% slowdown、最小Nは10 pair、
推奨campaign上限は32 pairとする。必要Nが上限を超えたlaneはmarginを緩めず`criterion_infeasible`である。
pilot、sample-size code/version、入力、出力、乱数seed identityをartifactとして保存する。

primary estimandは各eligible pairの正の公式scoreについて

```text
d_i = ln(FVOPS_ON_i / FVOPS_OFF_i)
estimate = exp(mean(d_i))
CI90 = exp(mean(d) +/- t(0.95, N - 1) * sd(d) / sqrt(N))
```

とする。候補marginはratio scaleのexact `[0.99, 1.01]`、各片側alphaは0.05である。
`official_trim_sec`はFVOPSと固定分子のもとで単調な代数的再表現なので、独立したgateとして重複させない。
FVOPSが含まないsolver起動・終了周辺の負荷は、非冗長な`solver_outer_wall_sec`について
`wall_OFF / wall_ON`を同じ方法・marginでco-gateにする。両方が通ることを要求するintersection-union gateであり、
各CIを「同時90% CI」とは呼ばない。

各complete pairでは性能値より先に適格性と数値同等性を判定する。両arm共通で、allocation/node set、
mesh/decomposition/workload byte、exact launcher/binding policy、rank数、OpenFOAM Hosts/runtime header、
公式marker、time-step/pressure solve順、solver名、residual lexeme、iteration countを一致させ、timing lexemeは
除く。OFFへrank wrapperを足して「観測一致」を作らず、actual affinity/Pstreamは同一allocationとsealed
launcher/binding policyで制御する。ONだけはfinal bundleのrank placement/env、Pstream startup/runtime/change、
expected rank/sentinel completenessとexpected configの一致を要求する。OFFのON専用consumer列は理由なしのNULLである。
protocolが最終fieldを書き出す場合はpayload hashも一致させる。
ON側だけのrequired event/source欠損、数値差、crashは`qualification_pair_eligible=false`かつ計測bundleのreliability failureであり、遅い値と
同様にpairを捨てない。treatment activation前の外部scheduler/node failureだけ、事前確保したreplacement
slotへ両armを新しいpair IDで再投入できる。一方のsolver開始後に片armを別runと再pairしない。

固定Nの全planned slotが終了するまでCIを判定に使わず、通常CIを見て追加・pass時停止・outlier削除をしない。
最終classは次のclosed enumとする。

- `adopt`: distinct eligible allocation数=N、全pairの意味/reliability gate、FVOPSとouter-wall TOST、当該laneの全条件を通過。
- `perturbing`: 数値差、instrumentation-attributable failure、またはCIが許容域から明確に分離。
- `inconclusive`: CIが境界を跨ぐ、eligible pair不足、または必要Nがcampaign上限超過。

異なるlaneをpoolしない。複数laneへ一括enableするなら全対象laneで`adopt`、lane別enableならpassしたlaneだけを
score用途へ許す。全attempt/pair pointはraw sourceから残すが、log-ratio、SD、ratio、CI、decisionは
protocolとpoint viewから導出し、rawへ保存しない。

これはTOSTでalpha 0.05と90% CI内包が対応するという[equivalence testingの原理](https://doi.org/10.1177/1948550617697177)、
software benchmarkではvariance levelをpilotでdimensioningすべきという
[Kalibera/Jones](https://doi.org/10.1145/2491894.2464160)、通常CIの反復peekを避けるべきという
[optional-stoppingの知見](https://www.kdd.org/kdd2017/papers/view/peeking-at-ab-tests-why-it-matters-and-what-to-do-about-it)
に基づく。

代替は、(A) 5 pairを一度だけ解析する低cost screen、(B) slowdownだけを禁じるratio下側95% bound > 0.99の
non-inferiority、(C) alpha-spendingを事前設計したsequential equivalenceである。非擾乱を目的とするため
推奨は双方向のoption Rである。ユーザー回答までは`instrumentation_overhead_decision=NULL`、benchの
instrumented runはaudit-only、profile runは常にaudit-onlyとする。

## 未決定事項と質問protocol

[Grill with Docs](https://github.com/mattpocock/skills/blob/main/docs/engineering/grill-with-docs.md)の進め方を
採用し、文書から調べられる事実を先に閉じた後、結果を変える未決定事項だけを一回に一問聞く。各回答は
`decision_id/question/recommended option/alternatives/user answer/decided_at/affected contract fields and
views/reopen trigger`をGit管理decision recordへ残す。未回答を推奨値で埋めず、依存するviewのdecisionはNULL、
release gateは未通過のままにする。

コード監査で、D-001より上流にlane scope D-003が残っていることが分かった。現行
`scripts/run-openfoam.pjm`が実証するGenkai条件は1 node、120 ranks、`a-batch`、
`I_MPI_FABRICS=shm`だけであり、64M cavity3DのGenkai 2/4 node設定はコードやrun recordから一意に
決められない。OpenFOAM内の依存順は次とする。

1. D-003: Genkai 1/2/4 nodeを今回のv2 scopeにするか、Genkai 1 nodeをcanaryに限定して競技clusterの
   1/2/4 laneは対象cluster確定後に別contractとして追加するか。推奨は後者。
2. D-001: D-003で確定した各score laneに許すinstrumentation overhead criterion。

プロジェクト全体の質問順は`D-003 -> D-004（Qwen初版profiler） -> D-001`とする。D-004はOpenFOAMの
contractをblockしないが、両repository共通のD-001を最後に一度だけ扱うため、その前に閉じる。

D-003が未回答の間、未実証の`openfoam-genkai-{2,4}.toml`を作ったことにせず、1/2/4 nodeを完了条件や
D-001 campaign対象として数えない。

## 決定状態

| 状態 | 決定 |
|---|---|
| 確定 | raw relationは`run/key/value`の三列、compound valueはcanonical JSON |
| 確定 | 定義した各process scopeの環境変数は機密値を含めfilterせずbyte-exactに全件保存 |
| 確定 | native object/structured sourceを優先し、log regexはfixture付きの最終手段 |
| 確定 | compute側はlocal raw fileだけ、finalize/publishはrunner、Artifact upload/home移管はworkflowが担当 |
| 確定 | complete recordのsubsetであるfirst/last/count/average等をrawへ重複保存しない |
| 確定 | bench/profileを分離し、profile専用familyはbenchで値だけNULL、原因/status/Evidenceなしとする。profile runはscore比較へ混ぜない |
| 確定 | artifact移管は現行OpenFOAMのGitHub Artifact -> Tailscale/SSH -> home RAIDを基準とし、Qwenへも同じ経路を移植する |
| 確定 | home artifactは自動expireせず、容量が実際に問題になった時だけ手動整理する。専用quarantineは作らない |
| 未決定 | D-003: OpenFOAM v2のlane scope。推奨は現行Genkai 1 nodeをcanaryとし、競技cluster 1/2/4は対象確定後に別contract化 |
| 未決定 | score runへ許すinstrumentation overheadの統計的上限 |

## 実装ハンドオフ

### 公開面とfile境界

実装者が新しい抽象を増やさないよう、package内部の依存方向を次に固定する。

```text
OpenFOAM hook -> version付きsource record -> rank別JSONL
                                             -> pure reducer ----\
I/O probe ------> structured source value ---> pure parser ------+-> Fact -> Recorder
StageRunner -----------------------------------------------------/

runner: single merge -> ArtifactStore/RunPackager -> publish
```

hookはmetric keyや`Fact`を知らず、`run/rank/sequence/kind/version`を持つsource recordだけを書く。
startup/runtime各recordをrank観測のsentinelとし、両方が揃ってchange recordが0件の時だけreducerが
change array `[]`を作る。rank別source JSONL自体がない時は`[]`を作らない。

公開するdomain型はimmutableな`Fact`と`Termination`だけにする。`Fact`はrun ID、owner、encoded
stringを持たず、`Termination`は`exit`、`signal`、`spawn_error`をunionとして表す。最低限のcall
surfaceは次で足りる。

```python
Fact(key: str, logical_value: LogicalValue)
init_subject(kind, protocol_path, contract_path, runtime_root, identities) -> SubjectManifestPath
Recorder.open(manifest_path, registry_path, producer_id, runtime_dir)
Recorder.append_many(facts)
Recorder.seal()
collect_once(manifest_path, runtime_dir, producer_id, probe) -> CollectorOutcome
submit_subject(subject_manifest_path, runtime_dir, lane_adapter, pjsub_argv) -> SubmissionOutcome
run_stage(stage_name, argv, *, cwd, stderr_mode, recorder) -> Termination
finalize_subject(subject_manifest_path, runtime_dir) -> tuple[FinalizeOutcome, ...]
publish_run(metrics_jsonl_path, destination) -> PublishOutcome
```

`Recorder.open`はpersist済みmanifestとregistryをread-onlyで検証し、runを生成・推測しない。
`LogicalValue`はstring、bytes、bool、int、finite float、Decimal、UTC timestamp、またはJSON treeに
限定する。top-level `None`は禁止し、bytes/Decimal/timestampとcompound JSONのencodingはregistryの
logical typeが決める。
`append_many`だけがlogical valueをcanonical stringへ変換し、一行ずつ`run/key/value`へbuffered writeする。
`seal`はflush/closeしてtemporary fragmentをrenameする。semantic ownerはprobe外側のsupervisorまたは
`StageRunner`である。正常終了時にexpected fragmentが存在することを
post-run validatorが検査し、途中crashから全eventを救うための逐次syncは行わない。
registry loading、canonical encoding、manifest validationは
`recording.py`のprivate collaboratorとし、それぞれを薄いpublic moduleへ分割しない。

`stderr_mode`は`separate`または`stdout`のclosed enumとし、solverは現行公式logとのparityを保つため
`stdout`へcombined logを作る。log pathはstage nameとruntimeから内部導出し、signalはchild process
groupへforwardしてraw wait statusを保存する。`finalize_subject`は唯一のrunner orchestratorであり、
post-run validation、metrics merge、bundle/artifact manifest作成を順に行う。別のpublic `merge_run`と
二重にorchestrationしない。

`FinalizeOutcome`はbundle/metrics path、hash、sizeとcompletenessを返す。`PublishOutcome`はdestination、
attempt、outcomeを返し、workflow logへ残す。内部`MergeReport`はinput manifest hash、row counts、conflicts、
completeness、output hashを持つ。制御状態を再構成するためのreceipt DAGは作らない。

`init_subject`と`collect_once`は`recording.py`、`submit_subject`は`submission.py`、`run_stage`は
`stage_runner.py`、`finalize_subject`は`artifact_store.py`、`publish_run`は`publish.py`が
所有する。`cli.py`はargument parseとhandler dispatchだけを行い、manifest生成、scheduler subprocess、
probe lifecycleを実装しない。

use-case outcomeも小さなclosed schemaにする。`CollectorOutcome`は`status/error_count/fragment_path/complete`、
`SubmissionOutcome`は`submitted|failed`とnullable job IDを持つ。曖昧submitを自動探索・復旧するstate machineは
作らず、そのworkflow attemptを失敗として人が再実行する。

現行fileからの移行先は次の通りとする。

| 現行 | 移行後の責務 |
|---|---|
| `model.py` | `domain.py`の`Fact`へ置換。`None`/非有限値を空文字へ変える処理を廃止 |
| `context.py` | run生成を廃止し、`recording.py`経由でimmutable manifestを読むだけにする |
| `sender.py`、`credentials.py` | compute packageのcall pathから外し、runner-only `publish.py`へ移す |
| `cli.py` | 下記use caseを配線するcomposition rootだけにする |
| `collectors/`、`readers/` | I/O probeとpure parserを分け、どちらも最後は`Fact`列を返す |
| `command.py`と現行`_stage` | `stage_runner.py`へ集約し、exact argv、同一clock、raw wait statusを一度だけ所有 |
| `prepare.py`、assets、`prepare-case` | canary中はlegacy互換として凍結。v2 cutover時にcase preparation scriptへ移しmetrics packageから外す |
| `scripts/run-openfoam.pjm` | manifest/runtime pathを明示してcompute collectorとstageだけを呼ぶ |
| `.github/workflows/genkai.yml` | pre-submit manifest、submission binding、terminal後finalize/archive/publishを所有 |

実装fileは計画済みの`domain.py`、`recording.py`、`submission.py`、`stage_runner.py`、`merge.py`、
`artifact_store.py`、`publish.py`とdomain別probe/parserに限定する。`manager`、`service`、汎用event
bus、DI frameworkは追加しない。`submission.py`は一回のscheduler submitと結果保存を隠す深いmoduleであり、
collectorやpublisherをimportしない。OpenFOAM固有adapterは`rank_wrapper.py`だけにする。same-rank wrapperは
検証済みglobal/local rank、local size、placement、env deltaをrank別source fileへ書いてsolverを`exec`する。

第二段階のOpenFOAM hookは
まずprofile purposeだけで有効にする。D-001を通したexact bundleだけbench expected graphへ追加できる。hookが
startup/runtime/change source recordをrank別`domain/pstream/rank-<rank>.jsonl`へbuffered appendする。
ACK待ちや逐次syncをせず、write failureをsolver exit/numericsへ伝播させない。terminal後のreducerがexpected
rankとsentinelを検査し、欠損runをconfiguration incompleteにする。timing影響はG9で判定する。

機械可読正本は`experiment-metrics/contracts/openfoam-v2.toml`一fileにする。contract ID、producer
定義、key pattern、owner、logical type、unit、cardinality、source、scope、capture、required、
missing、validation、正当な重複のjustificationを同じentryに置く。lane/protocolはこのcontractに
定義済みのproducer IDからexpected graphを選ぶ。runtime manifestにはcontract IDとcontent hashを
sealし、raw tableにはroutingに必要なcontract IDだけを索引化する。観測マップの表はこのTOMLから
生成し、手書きproseだけを別に保つ。したがってregistryとMarkdown表の二つを正本にしない。

### CLIと設定境界

CLIは次の六orchestration use caseだけを持つ。behaviorを環境変数で切り替えず、manifestとruntimeは
明示引数、比較条件はGit管理protocol、BigQuery宛先はrunner側のGit管理設定から読む。

```text
init-subject   regular runまたはqualification parent+二childのmanifestを作成
submit         exact pjsub argvを一度実行し、stdout/stderrと取得できたjob IDを保存
collect        compute producerを一度実行しdata fragmentとcollection statusへ記録
stage          target argvをspawnしterminationと時間を記録
finalize       terminal後にsubjectを検証し、expected artifactとmetrics.jsonlを作成
publish        metrics.jsonlをBigQueryへ送達
```

`init-subject`以外は`--subject-manifest`を必須にし、compute内部の`collect`/`stage`だけはparentが指定した
`--run-manifest`を必須にする。`EXPERIMENT_METRICS_RUN`、PID、PJM IDからsubject/runを再構成しない。
`collect`と`stage`はBigQuery設定やcredentialをimportしない。`finalize`と`publish`を分けることで、
送信障害を理由にcomputeやarchiveを再実行しない。

`submit`はexact argv、subject ID、stdout/stderr、subprocess outcome、取得できたjob IDを通常fileへ保存する。
応答を確定できないrunner crashはそのattemptを失敗とし、自動nonce検索、recovery receipt、blind resubmitは
実装しない。PJM側はrun/allocation IDと`PJM_JOBID`をjob-entry fileへ書き、terminal後にrunner側job IDと照合する。

`rank-wrapper`は上記六use caseへ数えないOpenFOAM固有internal entrypointである。
`scripts/run-openfoam.pjm`とsolver argvだけが呼び、一般利用者向け設定面にはしない。allocationのnode、
affinity、mesh/hardware auditはPJM scriptが終了する前にfileへ書く。runnerの`finalize`はallocationへ
再接続せず、terminal accountingと既存log/source/artifactのpure parser/reducer
だけを実行する。

### runtimeとarchive layout

runとsubmission subjectを分け、run側は次の固定layoutにする。任意file探索や「最後に見つかったJSON」を禁止する。

```text
<runtime>/runs/<run>/
  control/run-manifest.json                 # pre-submit immutable
  control/contract.toml                     # 実使用contractのimmutable copy
  control/protocol.toml                     # 実使用protocol/laneのimmutable copy
  control/source-track-validation.json      # diff algorithm/base/head/patch/pass
  control/build-sidecar.json                # resolved source/toolchain/binary identity
  control/instrumentation-qualification-decision.json # decisionを参照するbenchだけ
  control/submission-request.json
  control/submission.stdout
  control/submission.stderr
  control/submission-result.json            # raw subprocess outcome when available
  control/submission-failed.json            # explicit rejectionの場合だけ
  control/submission-binding.json           # 取得できたjob IDとのbinding
  control/job-entry.json                     # PJM側のrun IDとPJM_JOBID
  control/collection-status.json
  metrics/fragments/<producer>.tmp           # write中
  metrics/fragments/<producer>.jsonl         # 正常close後のrename先
  domain/pstream/rank-<rank>.jsonl
  source/workload-manifest.json
  source/hardware/identity-min.json
  source/hardware/node-<node>.lscpu.json
  source/mesh/mesh-topology.json
  source/mesh/partition-observed.json
  source/env/job-entry.snapshot
  source/env/host-exec.snapshot
  source/env/rank-<rank>.delta.json
  source/placement/rank-<rank>.json
  source/scheduler/pjstat.stdout
  source/scheduler/pjstat.stderr
  source/scheduler/pjstat-version.txt
  profile/raw/...                            # profileだけ。OPENFOAM_PROFILE_DIRの実体
  logs/pjm-job.log
  logs/log.icoFoam                           # solver combined log
  logs/<preparation-stage>.stdout
  logs/<preparation-stage>.stderr
  logs/checkMesh.log
  results/result.txt                         # canonical official evaluator output
  control/scheduler-terminal.json
  merge/collection-validation.json
  merge/metrics.jsonl
  archive-staging/run-artifacts.tar.zst
  archive-staging/artifact-manifest.json
  archive-staging/profile-raw.tar.zst        # profileだけ
```

regular runだけが上記`control/submission-*`、binding、job-entry、`control/scheduler-terminal.json`を所有する。
qualification childではそれらを作らず、代わりに
`control/qualification-parent-ref.json`（allocation ID、parent manifest hash、job ID、arm ordinal）を置く。
qualification parentは次の固定layoutを所有する。

```text
<runtime>/allocations/<allocation>/
  control/qualification-allocation-manifest.json
  control/protocol.toml
  control/child-source-validation-index.json # child source validationsのcontent-addressed index
  control/submission-request.json
  control/submission.stdout
  control/submission.stderr
  control/submission-result.json | submission-failed.json
  control/submission-binding.json
  control/job-entry.json                           # allocation ID/job ID/ordered child IDs
  source/env/job-entry.snapshot                    # NUL区切りbyte-exact parent source
  source/scheduler/pjstat.stdout
  source/scheduler/pjstat.stderr
  source/scheduler/pjstat-version.txt
  source/hardware/identity-min.json
  source/hardware/node-<node>.lscpu.json
  logs/pjm-job.log
  control/collection-status.json
  control/scheduler-terminal.json
  archive-staging/allocation-evidence.tar.zst
```

parent evidenceは上記`control/`、`source/`、`logs/`を一つに収録し、`logs/pjm-job.log`をrequired memberとするが、
run metricsは持たない。各childはparent manifest
hashだけを参照し、parent、二child、該当するprofile attachmentを同じworkflow artifact setへまとめる。

runごとのarchive対象は次の三fileを基本にする。

```text
run-artifacts.tar.zst   # 下記expected source/log/fragment
metrics.jsonl           # 最終raw sidecar
artifact-manifest.json  # file path、size、SHA-256、contract
```

bundle memberはrun variant別のmanifest駆動exact allowlistとする。regularは`control/`のmanifest、contract、
protocol、submission raw stdout/stderr、実在するresult/failed outcome、binding、job-entry、scheduler-terminalを
含む。さらに全runでbuild sidecar、workload manifest、minimal hardware、mesh/partition summary、該当する
environment/placement、PJM accounting raw/version、PJM batch log、solver combined log、preparation/checkMesh log、
official resultをexpected fileとして列挙する。qualification childは
parent-owned memberを含めず、`qualification-parent-ref.json`だけを含む。
いずれも`control/collection-status.json`、expected producerの完成および残っていれば途中fragment、
`domain/`、`source/`、`logs/`、`merge/collection-validation.json`、自己を除くmember path/hash/sizeを持つ
`bundle.manifest.json`を含める。最終`metrics.jsonl`とartifact manifestはbundle内へ重複収録しない。

`run-artifacts.tar.zst`はmanifestで列挙したmemberを収録し、作成後の実byte列をhashする。再実行時にtar headerや
compressor versionまで同一にして同じbundle hashを再現することは要求しない。同一run attemptでは既に作った
bundleをそのまま転送し直す。
最終`metrics.jsonl`は完全一致rowを一件へし、異値conflictは全rowを残したまま`(run,key,value)`の
UTF-8 byte順にsortする。各lineはobject member順`run`,`key`,`value`、空白なし、UTF-8、LF終端へ固定する。

manifestは通常のtemporary writeとrenameで完成させる。基本三fileとprofile attachmentをGitHub Artifactへ
uploadできた時点でGenkai runtimeはcleanupしてよい。archive jobはそれらをhomeの
`<github-run-id>/attempt-<attempt>/`へ`scp`し、SCPが成功した時だけGitHub Artifactを削除する。現行OpenFOAM
移管と同じくremote再読取checksum、transaction、reconciler、別delivery storeは実装しない。

BigQuery publishはhomeへ保存した`metrics.jsonl`または同じGitHub Artifactから再実行できればよい。
invalidなrunも通常のrun/attempt directoryへraw artifactを残し、comparison viewから除外する。物理的な
quarantine systemは作らない。通信・archive失敗はworkflow failureとして扱い、少数のarchive job状態だけを
Data Statusへ投影する。

### OpenFOAM移管系を基準にした実験用archive候補 D-002

基準経路は現行OpenFOAMの`actions/upload-artifact`、GitHub-hosted archive job、Tailscale/SSH、
`/hdd_raid/samba/net_share/openfoam-artifacts`、成功後のGitHub Artifact削除である。Qwenはこの経路を持たない
移植先とする。これは実験用projectであり、極稀な転送failureやrun lossまで多重に防ぐことを目的にしない。
通常pathで取得対象が初めから保存されない欠陥を防ぎ、失敗したrunは不完全として再実行できればよい。

2026-08-09のread-only実測ではhome領域は127 workflow run、約9.0 GB、最大runは約803 MBで、
`/hdd_raid`には約2.83 TBの空きがある。現時点で複雑なquota/reservation機構を正当化する容量逼迫はない。
一方、`scripts/run-openfoam.pjm`はprofile rawを`~/openfoam-profile`へ置き、Artifactにはlocationだけを残す。
これはprofile runで取得すべき値がarchiveへ全く入らない通常pathの欠陥なので、最優先で直す。

推奨option Rは現行経路をそのまま使う。

```text
run -> exact bundle manifestと、profileならprofile raw tarをGitHub Artifactへupload
    -> 現行どおりhome RAIDのrun/attempt directoryへscp
    -> SCP commandが成功した時だけ、そのworkflow runのGitHub Artifactを削除
```

SCPが失敗すればarchive jobをfailureにし、GitHub Artifactを残す。job rerunで再転送できる。
remote再読取checksum、temporary transaction、`renameat2`、directory fsync、forced-command receiver、reservation
ledger、quota pool、全命令境界のcrash recovery、独立backupをrelease条件にしない。runtimeは現行どおり
Artifact upload成功後にcleanupしてよく、uploadとGitHub側保持が同時に壊れる稀なcaseは許容する。

OpenFOAMの初版profile protocolは現行実装にある`perf-stat`へ固定する。`OPENFOAM_PROFILE_DIR`を
`<runtime>/runs/<run>/profile/raw`へ固定し、perf stat raw、tool version、exact profiler argv、solver logを
`profile-raw.tar.zst`へ
収録する。benchではprofile artifact、placeholder、absence recordを作らず、対応consumer値は
原因/status/Evidenceなしの`NULL`だけである。build archiveは現行Genkai cacheを使い、runにはbuild sidecarの
source commitとcontent hashを記録する。同じbuild byteをhomeへ再複写することはD-002の必須要件にしない。

推奨retentionはhome RAID上のrun artifactを自動expireせず、容量が実際に問題になった時だけ人が整理する
単純なpolicyである。専用quarantine databaseやledgerを作らず、invalidなartifactもrun/attempt別directoryへ
残す。Data Statusにはarchive jobの最終成功時刻、未移管Artifact数、home空き容量だけを表示し、run raw keyや
profile欠損理由へ複写しない。

完全replayはhomeのrun artifact tree、qualification parent artifact、Git管理contract/protocol/decision/SQLを
入力に空datasetを再構築できることを意味する。転送の各中間状態を永久保存することは意味しない。

### 状態と失敗規則

runnerは`pjsub`のstdout/stderrと取得できたjob IDを保存する。PJM supervisorはentry直後にsubject ID、
`PJM_JOBID`、qualificationならordered child IDsを`job-entry.json`へ書く。terminal後に両者を照合し、
片方が欠けるattemptや不一致はcomparison不適格にする。稀なrunner crashからsubmit状態を自動復旧しない。

runの処理状態は次の単純なfile flowで追う。

```text
regular:
run manifest -> submit result/job-entry -> compute log/source/fragments
             -> terminal accounting -> post-run validation -> run artifact + metrics.jsonl
             -> GitHub Artifact upload -> runtime cleanup -> home SCP -> BigQuery publish

qualification:
allocation manifest -> submit result/job-entry -> child OFF source/log/metrics
                                           \-> child ON source/log/metrics
                    -> terminal accounting -> one qualification artifact set
```

- post-run validatorはvariant別expected file、producer、rankとrequired keyを一度検査する。正常終了runで
  欠けていればcollection failureとする。失敗・timeout runの途中fileは読めるcomplete JSON lineだけを
  best effortで回収し、欠損を空文字やzeroで補わない。
- 同一run/keyの異値は両方を保持し、conflictとしてpublishしてcomparisonから隔離する。
- foreign run、unknown key、owner違反、canonical encoding違反は入力をbundleへ保全するが、信頼できる
  metrics sidecarへ混ぜない。専用quarantine状態は作らない。
- process timeout、signal、spawn errorでもrunnerはscheduler terminal後にpost-run parserとfinalizeを
  実行できる範囲でraw log/sourceをartifactへ含める。任意のcrash境界から完全再開できることは要求しない。
- cleanupはGitHub Artifact upload成功後に許す。publish失敗はhomeまたはGitHub Artifactの
  `metrics.jsonl`から手動再送し、computeを再実行しない。

### gateを証明するtest

| gate | 必須test/fixture | 証明すること |
|---|---|---|
| G0 依存境界 | `test_dependency_boundaries.py`、CLI subprocess import trace | domain/probe/recording/collect/stageのtransitive importにpublisher、credential、networkがない |
| G1 値契約 | `test_domain.py`、RFC 8785/decimal/env byte fixture | 空、zero、欠損、非有限拒否、単射escape、canonical byte |
| G2 submit/binding | `test_submission.py`、regular/qualificationのsuccess/reject/mismatch fixture | exact argv/stdout/stderr/job ID保存、allocation/job/ordered child join、不一致の比較除外 |
| G3 local file | `test_recording.py`、正常終了・program failure・truncated JSON fixture | buffered writerのclose/rename、expected file検査、読めるcomplete lineのbest-effort回収 |
| G4 ownership/merge | `test_merge.py`、variant別producer graph fixture | owner一意性、exact dedupe、異値conflict、required欠損、qualification parentのjob env/minimal hardwareを二childへjoinしてraw複写しない。profileでprofile-only collector失敗はreasonあり、benchの同列とqualification OFFのON専用列は理由なしNULL、qualification ONの同collector失敗はreasonあり |
| G5 process観測 | `test_stage_runner.py` | actual argv/cwd、combined log、process-group signal forwarding、exit/signal/spawn error、monotonic境界 |
| G6 archive/送達 | workflow integration fixture | happy pathで全expected artifactがhomeにあり、upload失敗はattempt failure、SCP失敗ではGitHub Artifactが残る。homeのJSONLをBigQueryへ再送できる |
| G7 OpenFOAM意味 | `test_observation_contract.py`、baseline log/mesh/Pstream/rank/source-diff fixture | contract source/時点/owner、sentinel/`[]`、rank欠損、PJM timeout best-effort回収、qualification ONの差分がinstrumentation patchだけであること |
| G8 consumer contract | contract生成SQL fixture、variant別BigQuery golden rows、Sheet parameter/refresh smoke test | 全列lineage、profile attemptのscore統計除外、非適用列がreason/EvidenceなしのNULL、pair-grain eligibility、同bundleでbase/workload/toolchainだけ変えたbench拒否、失敗attempt残存、protocol分離、estimand、definition非互換・片側env欠損TVF、freshness/size |
| G9 非擾乱 | D-001のlane別unmodified OFF/final ON paired run | 数値同等性、bundle reliability、事前dimensioningしたoverhead採用基準を同時に満たすこと |

`test_observation_contract.py`はcontractのschemaとowner/source/capture/absenceの完全性を検査し、
生成した観測マップ表がcommit済み表とbyte一致することを検査する。これが「この値はどこから取るか」
を、一つの正本から人間向け表と実行時validationの双方へ機械的に保証する。

### release単位

移行はkeyごとに二重化せず、run contract単位で行う。

1. legacyの出力、shell evaluator、baseline logをgolden fixtureとして凍結する。
2. 専用canary protocolだけでpre-submit manifestとlocal metrics exportを導入し、legacy runの送信経路は触らない。
3. canaryでrunner finalize/archive/publishの正常系と代表的なmissing-file failureを通す。
4. OpenFOAM固有のnative probe、complete solver record、Pstream/placement sidecarをprofile purposeへ追加する。
5. benchへ必要な最小subsetだけD-001へ掛け、D-003で確定した各score laneで意味・数値同等性・非擾乱gateを通したbundleだけbenchへ追加する。
6. v2 viewとSheetを切り替え、legacy-only consumerがゼロになってから旧senderとsubset keyを削除する。

rollbackはlaneのprotocol contractを直前版へ戻して新しいrunを投入する。既存runのmanifestやrowを
書き換えず、一run内でlegacy producerとv2 producerを混在させない。

## 実装順序

1. 現行key、producer、consumer、artifact保存先をinventory化し、key registry、expected producer
   graph、`run.metrics_contract`を作る。contractなしはlegacy、run内のproducer contract混在はinvalid、
   v2 viewはexact contractだけを読む。
2. clean checkout、remote到達性、build sidecar manifest、manual provenance gateを作る。
3. BigQuery credentialをrunnerだけへ移したうえで、現行metric集合のまま`Fact`、`Recorder`、
   JSONL export、runner merge/publish、workflow artifact upload/home移管を導入する。
4. ingestion-time partition/`run,key` clusterのraw table、distinct/singleton/conflict/reason items、evidence
   item/family status、archive attempt/status、exact-contract run/dimension/point/stats/paired view、二run table
   functionをconsumer column contractから生成しfixtureを通す。
5. cavity3Dのactual workload manifest、complete solver record、mesh、provenanceをlegacy collectorと並行追加する。意味が
   変わる既存keyをv2で再利用しない。
6. canonical official evaluatorを作り、旧shell validityと全baseline golden logを照合する。
7. D-003で確定したlane、同一rank wrapper sidecar、二段階Pstream/partition auditを追加し、最終
   instrumentationを含む全対象laneでbaselineと比較適格性を再検証する。各laneでunmodified OFFと
   exact final ONを同一mesh/partition/rankで対にし、pressure residual/iteration軌跡と公式markersの
   lexeme一致を数値同等性ゲートにする。
8. Connected SheetsのRuns/Replicates/Evidence/Config Diff/Environment/Data Statusをbounded consumerへ
   切り替え、freshness/result-size smoke testを通す。旧key consumerがなくなってから派生・部分集合keyの
   新規生成を止める。
9. homeのrun artifact tree、qualification parent artifact、Git管理source/contract/protocol/decision/SQLから
   空datasetを再構築し、raw row集合と主要view/Sheetの結果を照合してから旧viewを廃止する。

冗長keyの停止をview作成より先に行わない。

## 完了条件

- 性能に影響する変更がすべてremote到達可能なcommitにあり、commit bodyから仮説が分かる。
- 新規buildとreuseの両方でsource/build commit、toolchain、binary identityを追跡できる。
- 正当な空文字、未観測、collector失敗、collector未到達、真のゼロをfixtureで区別できる。
- canonical JSONがprocessやobject挿入順に依存せず同じbyte列になる。
- 各key patternのownerが一意で、distinct後のrun/key conflictがゼロである。
- BigQuery停止時もhomeまたはGitHub ArtifactのJSONLから同じlogical row集合を再送できる。
- 成功・失敗・timeout runのexpected log/JSONLをGitHub Artifactへuploadし、upload成功後はruntimeを削除できる。
- OpenFOAM基準移管でSCPが失敗した時はGitHub Artifactを削除せず、archive jobを再実行できる。
- profile runの全raw attachmentをhome pathから読め、bench archiveにはprofile pathもabsence
  recordもなく、対応Sheet列が原因なしNULLだけになる。
- 全baseline golden logでofficial validityとFVOPSが`parse_result.sh`に一致する。
- truncated、NaN/Inf、step/solve/iteration/mesh/rank/trim異常を理由別に判定できる。
- `solver.step_timings`と`solver.pressure_solves`から派生値を一意に計算でき、subset keyがない。
- ExecutionTime、ClockTime、launcher wallの異なるscopeが保存される。
- D-003で確定した各laneでrequested、allocated、solver Hosts、placementが一致する。
- setup後の実case workload memberがprotocol manifestと一致し、1 byte差をcomparison不適格にできる。
- bench/profileが分離され、profile-only列はbenchで理由なしのNULLになり、bench bundleの計測影響はD-001内である。
- unmodified OFFとexact final ONの同一条件でpressure solve軌跡と公式markersが一致し、数値結果を
  hookが変えていない。
- 同一protocolの反復がpair ID、実行順、blockを含め復元でき、全estimand点、median、MADがSheetに表示される。
- treatment値を含む同一条件だけが同じreplicate groupへ入り、宣言したtreatment差だけが同じ
  comparison set内で許される。
- required dimensionが欠けたfailed/invalid runもpre-run planned groupのattempted nへ一度だけ入り、NULL
  fingerprint groupへ脱落・混入しない。
- 別protocolが同じhuman group labelを使ってもcontract/protocol/policy namespaceにより統計が混ざらない。
- 各run/evidence/Sheet列がcontract raw keyまたはGit/artifact dimensionへ一意に遡れ、cast失敗や異値競合を
  aggregateが隠さない。
- 二run diffがcell parameter付きtable functionで計算され、NULL/同一/不存在runを拒否し、全run pairを
  materializeせず、full envをparameterなしでSheetへextractしない。
- config definition/policy非互換をequality NULLで表示し、片側env snapshot欠損をadded/removedでなく
  unknownとして表示する。
- Data Statusが各objectのquery時刻、最新publish、未移管Artifact数、archive job最終成功時刻、home空き容量、
  SQL/contract identity、conflict/incomplete件数を表示し、
  scheduled refreshのowner変更・停止とresult-size超過をsmoke testで検出できる。
- Sheets利用者がJSON展開なしでcommit、妥当性、一次結果、反復統計、artifactへ到達できる。
