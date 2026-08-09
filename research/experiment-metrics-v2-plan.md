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

本projectは実験用であり、mission-criticalな送達systemではない。正常終了するrunで取得対象が最初から
実装されていないことは許さないが、極稀なcollector、node、転送failureを救うための多段retry、fallback source、
field別reason registry、耐久journalは作らない。値のsource、取得時点、schemaは厳密にする一方、取得できなかった
値はconsumerで`NULL`、run全体は単一の`collection_complete=false`で十分とする。失敗runは保存できたlogを残し、
必要なら人が再実行する。このsimple failure modelは以降の節にある個別の旧reason表現より優先する。
厳密さは実装時のcontract testに寄せ、実行時は各sourceを一度取得しterminal後に一度finalizeするだけにする。
同じ値を複数validatorで囲むruntime safeguardは追加しない。

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

### 調査根拠

現行fileに加え、`0c26b1e`（BigQuery収集導入）、`56c1a2e`（commandを一metric化）、`8c67f1f`/`b7e69c2`
（full output保持とhome archive）、`fa9d49a`（scoreからperfを除外）、`335a10d`（bench/profile分離）までの
関連commit列を確認した。過去のCodex threadで確定した「欠測はNULLだけ」「OpenFOAM移管を基準」「稀な失敗は
許容」は本書の決定状態へ要約し、会話本文やcommit messageをrun metricへ複製しない。

## raw relationの契約

raw tableは現在の三列を維持する。

```text
run    STRING NOT NULL
key    STRING NOT NULL
value  STRING NOT NULL
```

`run`は一childの全producerが共有するglobally uniqueでimmutableなIDである。各submission subjectにはjob投入前に
OS CSPRNGの16 byteを32文字のlowercase hexで表す128-bit `subject_nonce`を一つ生成する。regularでは
`submission_subject_id=run_id`、qualificationではglobally uniqueなallocation IDをsubject IDとし、二child run IDも
それぞれ独立なCSPRNG 16 byteからopaqueに作る。allocation IDとarmはmanifest fieldだけが所有し、child IDへencodeしない。
manual経路でも同じsubject/child規則を使う。
`pjsub`返却後にしか分からないPJM job IDはrun/allocation IDへ
含めず、submission resultとjob-entryのjob IDをquery時に照合して結ぶ。初期run manifestを書き換えない。
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
- collectorは成功時にfragmentを閉じ、失敗時はnonzeroで終わる。別のcollection status、原因、error count、
  started/final耐久journalは作らない。finalizerはimmutable contractのvariant applicabilityとbundle selectionから
  expected fragment/fileを一回導出し、存在と照合して`collection_complete`を一度導出する。回収できた
  source/logは不完全runでも収録する。

`run.metrics_contract`は、emitterとviewの非互換schemaを識別するための小さな運用索引として
意図的に保存する。既存keyの意味、unit、JSON shapeは変更せず、非互換変更は新contract
または新keyにする。

各keyまたはkey patternは、owner、logical type、unit、cardinality、source、scope、
取得時点、required/optionalを一つのGit管理registryで定義する。動的keyの
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
registryの`duplication_justification`へ理由と検証式を書く。

全環境変数の保存は、取り漏らしのないforensic比較という要件に基づく明示的な非最小例外
である。個別env値を別namespaceへ再掲せず、標準Sheetでは比較関連projectionだけを出す。

## raw metrics exportと送達

v2は任意のcrash境界から一件も失わず再開できることを目的にしない。release gateは、成功した各run
variantの正常pathでcontractが要求する設定、性能値、raw log、PJM accounting、profile runのprofile rawが
Artifactへ収録され、finalizerで確認できることである。失敗・中断runは完成済みfileだけを残し、partial recordの
復旧処理は作らない。supervisorがterminal後のfinalizerまで到達した失敗runは、そこで存在する完成済みlog/sourceと
`collection_complete=false`を通常の一artifact setへpackageする。finalizer前のcrashまたはpackage自体の失敗だけは
完成artifactを作らず、qualification setではchildの`artifact_manifest=null`だけにする。原因fieldは追加しない。

`metrics.jsonl`はBigQuery fact tableと同じ`run/key/value`を持つrun単位のraw exportである。artifact projectionは
subject artifact setからPublisherが別relationへ送る。別event
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
  -> merge済みfragmentを削除し、log/source/resultのrun bundleとartifact-manifest.jsonを作成
  -> run bundle、merged JSONL、artifact manifestをGitHub Artifactへupload
  -> upload成功後にGenkai runtimeを削除可能
  -> archive jobがhome RAIDへscpし、runnerがBigQueryへ送信
```

- 一つのJSON objectを一lineで書き、producer終了時にflush/closeする。各lineやdirectoryごとの`fsync`は
  要求せず、必要なら一定間隔のbuffer flushを使う。
- expected producer/file集合はimmutable contractのvariant applicability、protocol、bundle selectionからjob投入前に一回導出する。manifestへ再掲しない。scheduler
  accountingとobserved placementは、その期待集合が実際に成立したかを後から検証するsourceである。
- mergeはrun ID、JSON、owner、expected node、一意性を検査し、欠損や異値競合を隠さない。
- BigQuery `insertId`はbest-effortの補助にすぎない。logical viewが完全一致rowをdeduplicate
  し、異値競合を隔離する。
- replayは同じrowを全件送ってよい。送信成功後もarchiveのJSONLを変更しない。publish失敗時はhomeまたは
  GitHub ArtifactのJSONLからworkflowを手動再実行する。
- upload失敗はattempt failureとする。upload成功後はruntimeを削除してよく、home転送のSCPが
  失敗した時だけGitHub Artifactを残す。

artifact identityの自己参照を避ける。全fragmentを一度mergeして`metrics.jsonl`を確定した後、log/source/resultから
run bundleを作り、bundle、metrics sidecar、profile raw tarのrole/size/hashを`artifact-manifest.json`へ保存する。
outer filenameはroleから固定導出し、manifestへ複写しない。
fragmentはmerged JSONLの完全な部分集合なのでartifactへ保存しない。
bundle hashやmetrics sidecar自身のhashをmetricへ戻して再mergeしない。publishはremote archive verificationを前提にせず、
同じattemptのlocal/GitHub artifactを入力にできる。

計算nodeではBigQueryへ接続しない。したがって送信用credentialをPJM processへ渡す必要も
ない。各snapshotはそのscopeに実在する環境をfilterなしで保存し、機密値も例外扱いしない。

## 最小の実装境界

対象programへ計測システムの都合を持ち込まないため、責務を次の六境界へ固定する。

1. domain probe/parserは`Fact(key, logical_value)`だけを返すpure functionとする。run ID、文字列化、
   filesystem、BigQueryを知らない。
2. `recording.py`の`Recorder`だけがpersist済みrun manifest、registry、canonical encoder、factのbuffered
   append/flush、data fragmentのcompletionを所有する。別のcollector status fileは作らない。
3. `StageRunner`だけがspawnするactual argv、monotonic timer、signal、child wait statusを所有し、
   観測したfactを`Recorder`へ渡す。
4. runner側`merge`がexpected producer、run ID、owner、一意性、required key、fragment完了を検証し、
   archive対象のmerged JSONLを作る。
5. `ArtifactStore/RunPackager`がrun bundle/artifact manifestの作成と検証を所有する。GitHub Artifact uploadと
   home移管はworkflowが担当し、汎用reconciler、quarantine service、delivery ledgerは作らない。
6. runner側`publish`だけがBigQuery credentialと、一attempt一送信・同じJSONLを入力にした手動workflow
   再実行を所有する。collector、solver、PJM
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
欠損時の扱いは[観測マップ](./experiment-metrics-v2-observation-map.md)、field-level shapeは
[contract schema handoff](./experiment-metrics-v2-contract-schemas.md)に置く。最初の実装sliceでこれらを
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
次の値はregular bench/profileではGitだけから実行事実を復元できないためraw metricとして残す。

- `experiment.block_id`
- `experiment.block_order`
- `experiment.replicate_index`
- `experiment.pair_id`: 欠損・置換後もA/B対応を推測しないprotocol割当ID
- `experiment.planned_replicate_group_id`: submit前に割り当てる非NULL arm/group ID
- `experiment.planned_comparison_set_id`: submit前に割り当てる非NULL比較集合ID

qualification childはblock ID/order/replicate indexを複写せず、順にallocation ID、parent/setのordered-child offset、
protocol pair array offsetからviewで導出する。pair ID、planned comparison set、must-match/treatment tupleだけをchildへbindする。

探索比較の既定は各条件5 attemptとし、記述統計だけに使う。同じ時間block内でA/Bを
事前乱数化し、順序を均衡させる。5 attemptや有効run 3件を、equivalence、non-inferiority、
release gateの根拠へ流用しない。意思決定を伴うprotocolは、estimand、margin、想定効果、
分散、alpha、powerからplanned attempt数を事前dimensioningする。invalid/failed runを遅かった
という理由で除外・置換せず、最大attempt数と置換規則も事前にcommitする。

比較次元はGit管理SQLで次へ分類する。

- 一致必須: 実caseから観測したworkload identity、purpose別のsource/build semantic identity、run-time MPI execution identity、resource lane、precision、
  正規化したplacement/affinity policy、instrumentation mode
- 意図的に変えるtreatment: 対象commit、cluster、node type等
- nuisance: hostname、開始日時、queue待ち、個別node identity
- outcome: score、各stage時間、resource値

protocol commitはtreatmentにするkey集合と一致必須key集合を事前宣言し、runner manifestがexact policyと
`dimension_policy_hash`をsealする。contractはdimensionごとのallowed classだけを制約し、protocolごとに
変わり得るclassを固定しない。viewは次の二つを導出し、fingerprint自体はrawへ保存しない。hash入力は
contract ID/hash、protocol commit/hash、dimension policy hash、dimension name、logical type、canonical
valueのsorted tupleである。required dimensionがmissing/conflictingならfingerprintを作らずNULLにする。

- `observed_replicate_fingerprint`: 実観測した一致必須条件とtreatment値を含むnullable検証結果。
- `observed_comparison_set_fingerprint`: 実観測値から宣言済みtreatment次元だけを除いたnullable検証結果。

attempted countのgroupにはnullableなobserved fingerprintを使わない。pre-run protocol assignmentが必ず
非NULLのplanned group/set IDをsealし、failed/invalid runもそこへ残す。eligible countだけが、実観測
fingerprintとplanned policyの一致を要求する。
`namespace={contract_id,contract_hash,protocol_id,protocol_hash,dimension_policy_hash}`とする。
`planned_replicate_group_id`は`SHA-256(JCS({namespace,purpose,must_match,treatment}))`、
`planned_comparison_set_id`は`SHA-256(JCS({namespace,purpose,must_match}))`で生成する。
dimension arrayはplanned-treatmentと同じcanonical entry/name byte順とし、arm/pair/block/order/replicateをcomparison-set
hashへ入れない。qualification armはprotocol指定treatmentとしてtreatment ID/paired contrastには使う。
`group-1`等の任意labelは表示属性にすぎない。

commit、artifact、cluster等がtreatmentならcomparison set内では差を許すが、replicate groupは
必ず分離する。nuisanceとoutcomeはどちらにも含めない。競技提出用bestと、環境比較用の全点、
median、MAD、ratio、不確実性を分ける。

上記は通常の性能比較policyである。計測擾乱専用protocolだけは、`instrumentation_mode`、
score bundle、qualified source diff、reference/final build semanticだけをtreatmentへ
再分類する。これを行わずにon/offを同じcomparison setへ入れたり、通常比較でmode差を許したりしない。
通常benchのenvironment比較では、各run自身が記録したsource、build semantic、runtime MPI semantic、score bundle、
control-plane blobsを通常のcomparison policyで扱う。D-001の一回限りの受入結果をmust-match dimensionへ加えない。

## OpenFOAMで保存する原始事実

### run、stage、allocation

- `run.started_at`、`run.finished_at`、`run.elapsed_sec`
- `run.exit_code`。`run_outcome`は0=`succeeded`、非0=`failed`、欠損=`NULL`としてviewで一度導出する
- `run.stage.<name>.launch`: `StageRunner`がspawnしたprofiler/mpirunを含むexact outer `argv`、`cwd`、
  `stderr_mode`のcanonical JSON object。solver専用のargv subset keyは作らない
- 各`perf.stage.<name>.wall_time_sec`と`run.stage.<name>.termination`。terminationはexit、signal、
  spawn errorを区別するJSON objectで、shellの`128+signal`へ潰さない
- `perf.pipeline.wall_time_sec`: regular bench/profileだけ、blockMesh spawn直前からsolver wait直後まで。mesh audit、hash、
  archiveを含めない。二caseを二solver前に準備するqualification childでは非適用でNULL
- `scheduler.request`: runner submit boundaryのlane、PJM script identity、exact `pjsub` argv
- `scheduler.accounting`: 固定した`pjstat --history -S --choose ... --data --delimiter "\t"`の結果
- regular runだけ、submission resultの`scheduler.submit_job_id`とjob-entryの
  `scheduler.job_entry_job_id`を別sourceのscalar indexとして保存し、equalityはviewで導出する。binding booleanは作らない
- minimal hardwareはregular runごと、qualification allocationはarm 1前に一度だけ、各allocated nodeで
  `LC_ALL=C lscpu --json`とcontract列挙のproc/sysfs settingを読む。raw node artifactはlscpu JSON/settingsだけ、
  `openfoam_minimal_hardware_raw_v2`はCPU identity、hostname、kernel、CPU sets、memory/hugepage、NUMA balancing、
  boost、cpufreq policyをsubject/node grainで持つ。各consensusはview派生で、child Factへ複写しない
- profileだけ、minimal hardwareに含まれないNUMA配置とpost-run memoryのraw artifactを追加する。
  これを第二のcompound raw factへまとめず、publisherのsource-linked projectionからconsumer列を作る。benchではNULL

regularのrun lifecycleはPJM entryからcompute回収終了まで、qualificationは各child orchestration開始直前から
そのchildのsource/log回収終了までを個別に取る。allocation-wideのPJM entry/accounting/terminalは親projectionだけが
所有し、child lifecycleへ複写しない。started/finishedはUTC wall clock、elapsedは同じsupervisor境界の
monotonic clockで取得するため、
wall-clock jumpとtimestamp精度の影響を受けず厳密な派生関係ではない間だけ残す。同一scope、clock、
precisionへ統一した時点でelapsedまたはtimestamp pairの一方をview派生へ移す。

### build provenance

build sidecar manifestに次を固定する。

- buildを定義した`1_OpenFOAM` commit
- OpenFOAMとThirdPartyのresolved commit
- compiler、MPI、toolchain、compile flags
- precision、label size。original build workflow/run/attemptはsidecarでなくoperational build rowだけが所有する
- build archive、`icoFoam` binary、ELF `DT_NEEDED`、build時のMPI version

provision後に初めて分かる実配置binaryの`realpath`/SHA-256と`ldd`/resolved `libmpi`はbuild sidecarへ
後書きせず、runの`control/build-provision-validation.json`へ置く。

meshの正常pathを実装可能にするため、probe sourceは
`experiment-metrics/native/mesh-facts/{mesh-facts.C,Make/files,Make/options}`へ固定する。build workflowは実験対象と
同じOpenFOAMへlinkしてbuild artifactの`bin/mesh-facts`へ収録し、provisionは
`<runtime>/provisions/<build-sidecar-sha256>/bin/mesh-facts`へ配置する。完全なpartition検査も
`experiment-metrics/native/partition-audit/{partition-audit.C,Make/files,Make/options}`のnative utilityへ固定し、同じbuild/provisionの
`bin/partition-audit`へ収録する。`capture-hardware`はtracked Python sourceの
blob identityをbuild provenanceに置き、entrypointは同じper-build provisionの`bin/capture-hardware`へsource bytesを
そのままinstallしてbyte hashもbuild semanticへ一度含める。
`icoFoam`、`blockMesh`、`decomposePar`、`checkMesh`、`mesh-facts`、`partition-audit`、`capture-hardware`、profileだけのsystem `perf`の
resolved realpath/hashをbuild-provision validationへ一度記録し、stageは裸のcommand名でなく
そのabsolute pathを起動する。MPI launcherもresolved realpath/hashとそのabsolute pathでの`--version`を同recordへ一度記録し、
solver/hardwareの全MPI launchはそのabsolute pathを使う。probe出力は`cells/faces/points/internal_faces`だけのclosed JSON objectである。

raw tableは比較groupとartifact到達に必要なcommit、manifest identity、artifact URIだけを
索引化する。archive hashはbuild時に一度計算し、各benchmark runで再計算しない。
build scriptがarchiveとhash付きsidecarを書き終えて成功した後だけcacheへ公開する。consumerはsidecar存在と
archive hash一致の組だけをreuseし、任意のcrash境界から二fileを復旧するtransactionは作らない。
Publisherはbuild sidecarとrole付きtoolchain rawをbuild-grain `openfoam_build_provenance_raw_v2`、runのprovision
validationを`openfoam_build_provisions_raw_v2`へ一度だけ投影する。Runsのprecision/build artifact/compiler/MPIは
前者をbuild manifest SHA-256で、実resolved executable/libmpiは後者をrun IDでjoinし、scalar Factへ再掲しない。

### actual workload

solverが読む実caseについて、exact 7 memberをsetup後・`blockMesh`前に`source/workload/`へcopyし、同じbytesから
manifestを作る。regularとqualificationの各childが、自身のsolver caseを一度所有する。OFF/ONは別case directoryなので、
parentの一回観測で代表させない。Publisherはmanifest rowとmemberのexact content bytesを別projectionへ転記するため、Sheet/agentはhashだけで
なく境界条件、solver control、mesh設定を直接比較できる。member contentを個別raw keyへ再掲しない。
protocolは`workload_id`とexact 7 member manifestのexpected identityをGit-managed dimensionとして持つ。
`workload_match`はactual manifest projectionとのequalityだけで、片側欠損/conflictはNULL、expected値をrawへ複写しない。

### mesh、partition、配置

- `mesh.topology`: cells、faces、points、internal facesのJSON object
- `mesh.partition.requested`: 実使用dictの`source_sha256/subdomains/method`だけのJSON object
- `mesh.partition.observed`: `source/mesh/partition-observed.json`のJSON object。serial mesh五file identity、rank別cell数、
  rank順のprocessor mesh五file/addressing四file SHA-256、rank pair順のprocessor-interface face数を持つ。min/max/mean/imbalanceは
  rank別cell数の完全な部分集合なのでviewで導出しrawへ保存しない
- `solver.runtime_header`: solver logのbuild、arch、Exec、nProcs、Hostsを一つのJSON object
- `solver.pstream.startup_applied.rank.<rank>`: `UPstream::init()`が実際に適用したstartup state
- `solver.pstream.runtime_current.rank.<rank>`: `Time`構築とcase override後、time loop前のcurrent state
- `solver.pstream.change_events.rank.<rank>`: runtime中にcontrol再読込で変わった場合だけの順序付きrecord
- `parallel.rank_placement`: rank、hostname、local rank、CPU affinity、NUMA affinityのJSON配列

placement reducerはfilename/global rank/run ID、global rankの`0..requested_ranks-1`集合、
`0 <= local_rank < local_size`、hostname内のlocal size consensusと連続local rank集合をexact検査する。

`solver.runtime_header`、scheduler request/accounting、launcher placementは取得源の異なる独立観測で
あり、互いのprojectionとして削除しない。requested値の別名は作らない。

1 nodeはPJM supervisorが`<provision>/bin/capture-hardware --mode minimal --subject-kind <regular_run|qualification_allocation>
--subject-id <run|allocation> --output-root <subject>/source/hardware --node-ordinal 0`を実行する。multi-node laneはarm/timed solver外で
一度だけ、検査済みabsolute `mpirun -np <lane.nodes> -ppn 1`の後ろへ同prefixと`--node-ordinal-from-env PMI_RANK`を置く。
各lane canary自身で`PMI_RANK`の存在と期待連続集合を確認できたrunだけをconformance eligibleにし、probeは代替rank
sourceを探索しない。各processはshared runtimeの
`source/hardware/node-<node-ordinal>.json`へ書き、identityとplatform settingsを含むfull `hardware-node/v1`を持つ。
`commands`はargv/exit_code/stderr、`lscpu`はstdoutからparseしたraw JSON objectである。さらにkernel release、
CPU/node online/isolated/nohz_full、memory total/hugepage、NUMA balancing、boost、cpufreq policy別driver/governor/
min/maxを同じ軽量probeへ入れる。post-runでordinal、hostname、
expected node数を照合する。別daemonや常駐collectorは置かない。

profile post-runもtimed solver外で同じone-shot形を使い、
`<resolved-mpirun> -np <lane.nodes> -ppn 1 <provision>/bin/capture-hardware --mode profile-postrun
--subject-kind regular_run --subject-id <run> --output-root <run>/profile/raw/hardware --node-ordinal-from-env PMI_RANK`
へ固定する。`capture-hardware`は公開CLI use caseにせず`collect`から呼ぶinternal probeとする。minimal hardwareのnode recordを
正本とし、CPU identity consensusを別rawへ複写しない。profileのfull topologyは
`profile/raw/hardware/node-<ordinal>/`に`/proc/meminfo`、NUMA別
`cpulist`/`meminfo`、capture resultだけを置く。profile captureはhostnameも一度持ち、別one-shot launchのordinalだけを
信用せずminimal hardwareの`(node_ordinal,hostname)`とexact照合する。meminfoのkBはbytesへ変換し、cpulistはkernel listとして
canonicalizeする。

partition identityはserial mesh/order、実processor mesh、partition membership、rank順・local index順を保った
cell/face/point/boundary addressingを分ける。global cellが全rankでちょうど一回、serial owner/neighbourから決まる
unsplit faceは一回・split faceはpeer両側に符号反対で二回・boundary faceは一回、local face vertex cycleはpoint mapping後の
serial faceと向き込みで一致、point unionはserial point集合一致、processor/nonprocessor boundary mapping、rank集合の連続性を
native `partition-audit`で検査する。
`partition-observed.json`は`schema_version/serial_mesh/subdomains/interfaces`の固定objectとし、`subdomains`はrank昇順、
`interfaces`は`(lower_rank,upper_rank)`昇順にする。interfaceのauthoritative sourceは
`processor<rank>/constant/polyMesh/boundary`のprocessor patchにある`myProcNo/neighbProcNo/nFaces`とする。
`partition-audit`は同じOpenFOAMへlinkし、`polyMesh`、`labelIOList`、`processorPolyPatch` APIでASCII/binary、label幅、
endiannessをOpenFOAM自身に解釈させ、signed `faceProcAddressing`の符号を保持する。interfaceは小さいrankを`lower_rank`、
大きいrankを`upper_rank`にcanonicalizeし、両processor patchがexactly onceかつ同じ`nFaces`を報告する時だけ一件にreduceする。
regularはsolver終了後に一caseへ一回、qualificationはarm 2終了後にOFF/ONの各caseへ一回ずつ実行し、arm間には走らせず、
別parserやfallbackを持たない。各実行はserial meshを一度読み、processor
directoryをrank順に一つずつ処理し、global membershipはbitset、peer照合はmapped face ID集合で保持する。64M-cell canaryで
peak RSSをnode memoryの25%以下と確認する。
mesh/addressingのpathはcase rootからのrelative POSIX path、hashはheaderを含む実file byte全体のSHA-256とする。source
file全体をrun artifactへ複写しないため、各locatorは`locator_kind=runtime_relative_ephemeral`、relative path、
size、file-byte hashを持ち、artifact memberとは呼ばない。hashは消去前runtime sourceのidentity、summaryはquery
利用性のためであり、一方から他方を導出できないので正当な併存とする。complete `checkMesh` outputは
`logs/checkMesh.log`へ残す。
`decomposeParDict`は`decomposePar` spawn直前に実argvが参照するfile bytesを
`source/mesh/decomposeParDict`へcopyし、同じbytesからrequested recordを作る。mesh topologyは
`mesh-facts -case <case> -fileHandler uncollated -constant`、complete logは
`LC_ALL=C checkMesh -case <case> -fileHandler uncollated -constant`で取得する。
大容量mesh scan、`checkMesh`、partition hashはregularではsolver終了後、qualificationでは必ずarm 2終了後に両child caseへ各一回実施し、
scored solverのcacheを乱さない。generated `decomposeParDict`と各stage logはartifactへ残す。

初版は同じrun/allocation内のinline post-run scanだけを実装する。standalone audit jobはmanifest、CLI、join契約を
増やす割に初版の取得値を増やさないためscope外とする。

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

hookのsinkは`OPENFOAM_METRICS_PSTREAM_DIR=<runtime>/runs/<run>/domain/pstream`一つだけである。bundleはこのabsolute sinkと
validated run IDをそれぞれ`OPENFOAM_METRICS_PSTREAM_DIR`/`OPENFOAM_METRICS_RUN_ID`へ結ぶclosed environment bindingを持つ。
supervisorが`mpirun`前にこのabsolute directoryを一度作り、rank hookはdirectoryを作らず自身のfileをopenする。
各rankは`UPstream::myProcNo()`確定後に`rank-<rank>.jsonl`をline-buffered appendし、正常終了時にflush/closeする。
write失敗でsolverを止めず、fallback sinkや再送queueも作らない。その場合は値がNULL、requiredなrunでは
`collection_complete=false`になる。

`parallel.rank_placement`は別の`mpirun`で測らない。同じrank processのwrapperが`PMI_RANK`、
`MPI_LOCALRANKID`、`MPI_LOCALNRANKS`、`gethostname()`、`os.sched_getaffinity(0)`、
`/proc/self/status`の`Mems_allowed_list`を記録してから`exec icoFoam`する。各lane canary自身でrank envの存在と
期待集合を確認し、欠損時の代替sourceは持たない。reducerはglobal rank昇順のcanonical arrayを作る。

### solver logの完全record

- `solver.step_timings`: 公式`ExecutionTime` regex match一件につき一要素を作り、直前の
  simulation time、同じtiming行のExecutionTime/ClockTimeの原lexemeとnullable parsed numericを
  持つ順序付きJSON配列。
  simulation timeまたは同一行のClockTimeがなければ、そのfieldだけを`null`にする。
- `solver.pressure_solves`: `Solving for p`一件につき一要素を作り、initial residual、final
  residual、iterationsと各数値の原lexemeを持つ順序付きJSON配列。iterationsは公式の行末regexに一致しなければ
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
- `run_outcome`: supervisor/pipeline exit codeだけから導出する成否。scheduler成否はscheduler列が別に所有する

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
`score_comparison_eligible`は`run_purpose=bench`と通常のresult/source/placement gateだけから導出し、
D-001 decisionをrunごとにjoinして判定しない。`qualification_arm_eligible`は、実装時に一度だけ行う
`run_purpose=qualification`の受入試験runから導出する。
`qualification_pair_eligible`はrun列やraw factへ複写せず、両arm、parent allocation binding、common-source一致を
joinしたpair grainで一度だけ導出する。
profile/qualificationは公式FVOPSを算出・表示してもscore stats、best、rankingへ入れない。

MPI teardown後の非zero exitでもsolver workloadがofficial validになり得る。原始結果は必ず
収集し、official validityとrun outcomeを混同しない。`official_log_valid=true`でもscoreを算出不能なら
scoreはNULLにする。field別原因分類はしない。

## lane scopeと計測擾乱

D-003は「収集系を初版からmulti-node対応にし、Genkai 1/2/4 nodeを実機conformance対象にする」で確定した。
node数やrank数をcollectorへhard-codeせず、`experiments/lanes/openfoam-genkai-n<nodes>-r<ranks>.toml`が
node/rank/resource group/transport policyを一度所有する。required producerはcontractのvariant applicability、
instrumentation modeはprotocol/bundle selectionだけが所有する。runnerはlaneから
expected node ordinal/rank集合とexact `pjsub`/`mpirun` argvを展開し、PJM script identityとともにmanifestへsealする。
初版canaryは総rank数を120に固定したbalanced配置
`n1-r120`（120 rank/node、`I_MPI_FABRICS=shm`）、`n2-r120`（60 rank/node、`I_MPI_FABRICS=shm:ofi`）、
`n4-r120`（30 rank/node、`I_MPI_FABRICS=shm:ofi`）を使う。いずれも`a-batch`、Scotch 120 subdomainで、launcherは
`mpirun -np 120 -ppn <120/nodes>`へ固定する。1-nodeは現行64M workloadで実証済み、2-nodeは旧workloadで基盤だけ実証済み、
4-nodeは未実証なので、後二者に性能期待値を仮置きせず各一回の通常canaryで取得成否を確認する。失敗時の自動retryや
代替laneは作らない。canary後のrank sweepは同じschemaの別laneとして追加し、値を既存laneへ上書きしない。各runで次を照合する。

```text
claimed lane == requested nodes == allocated nodes
             == distinct solver hosts == distinct placement hosts
```

rank ID、header nProcs、Hosts合計、placement件数、hostごとのrank数=`ranks/nodes`も一致させる。multi-node laneで
`I_MPI_FABRICS=shm`のようなnode内限定transportを拒否する。

scored solver直前にはBigQuery通信、profiler、MPI debug、`checkMesh`、大容量hashを実行しない。
同一runに必須なのはrank、hostname、local rank、affinityとenvironment deltaの最小recordだけで、
各rank wrapperが自分専用のsidecarへ一度書いてからsolverをexecする。collector daemonやdurable ACKは
使わない。full topology dumpやverbose diagnosticsはaudit modeへ分ける。最小probeも
probeあり/なしの反復A/Bで事前閾値を超えるなら、そのrunはofficial-validでもscore-comparison-ineligible
とし、別audit runのplacementを元runへ移植しない。

`instrumentation_bundle_hash`は、score pathで有効なhook、probe、rank別source schema、sample interval、sink、
buffer、wrapper executable hash、observation contract version、env capture scope、source path allowlistを
列挙したcanonical manifestのcontent hashである。`lightweight`等の
labelだけでは同一視しない。D-001はcollector実装時に一度だけ行い、合格するまでは最小probeを含むrunを
score-runへ昇格させない。一度合格した後は、その結果を実装の受入結果として固定し、lane、環境、run、
commitまたはbundleごとの再qualificationは行わない。
このhashはpurpose/arm/run ID/absolute runtime rootを含まないsemantic identityで、sinkとargvはrelative templateにする。
qualification ONは受入対象のbundle bytesを参照する。合格後のbenchは通常contractで選んだbundleを使い、
D-001 evidenceとの継続的なbyte照合は行わない。実argv/sinkは各run sourceで観測する。

## bench/profile trackの分離

重いprofilerを挟むrunと公式性能を測るrunは、protocolだけでなくsource trackも分離する。

- `bench`: score、環境比較、qualificationの基点。profiler、polling、verbose traceを入れず、D-001合格後は
  bench用の最小収集bundleを通常contractとして決め打ちする。
- `profile`: `bench`のexact commitへprofile専用overlayを載せる診断track。値は原因探索に使うが、
  score、replicate統計、環境ランキングへ混ぜない。
- `qualification`: unmodified `bench`と最終score bundleを直接比較する専用protocol。profile trackの
  結果で非擾乱を代用しない。

ユーザー判断により、benchでprofile専用metricを取得できないことは許容する。contractの各family/consumer列は
`applicable_run_variants`（`bench`、`profile`、`qualification:off`、`qualification:on`の集合）だけを持つ。
expected producer graphはrun variantごとに作る。非適用でもcollector failureでもconsumer値は`NULL`だけとし、
field別status、欠損用placeholder、reasonを作らない。required sourceの有無はrun-level
`collection_complete`を一度導出するだけである。

| family | bench | profile | benchで取らない時の意味 |
|---|---|---|---|
| source/build/workload、exact argv/cwd、runner/submit/job-shell env、scheduler、termination、公式solver log/FVOPS、minimal hardware identity | required | required | 欠損ならbench不適格 |
| solver-rank env、rank/local-rank/affinity、Pstream rank別source JSONL | D-001通過bundleだけrequired | required | 未採用bundleならbench protocol自体から除外 |
| workload exact member copy/hash | setup後・blockMesh前required | required | target timer外で各solver caseから取得 |
| mesh/partitionの重いidentity scan | pair/run終了後required | required | target timer外で取得 |
| perf counter、sampling profiler、call stack、verbose MPI/Pstream trace、full topology dump | not expected | protocol指定時required | Runsでは`NULL` |

benchで取得しないprofile専用familyはexpected producer graphから外し、raw key、status、placeholderを作らず、
typed/Sheet値だけを`NULL`にする。benchの`collection_complete`分母へ含めない。bench/profileそれぞれでrequiredと
宣言したfamilyのcollector failureはrun-level `collection_complete=false`にするが、原因分類はしない。
profile値を同じprofile baseのbench runへ移植しない。

qualificationは同じpurpose内でもarmごとにgraphが異なるため、expected graphを
subject manifest top-levelの`(run_purpose, qualification_arm)`で解決する。armはplanned-treatment tupleへ複写せず、
protocol指定のtreatment ID/paired contrastにだけ反映する。

- `qualification/OFF`: 両arm共通のsource/build/workload、argv、runner/job-shell env、scheduler、termination、
  公式log/result、外側timerだけをrequiredにする。
- `qualification/ON`: OFFのcommon familyに加え、D-001対象のexact minimal score bundleだけをrequiredにする。

両armともprofile-only列はNULLだけを返す。OFFでON専用列も同じくNULLだけとする。D-001合格後のbenchは
profile-only producer IDを含まないbench用bundleを通常contractから選ぶ。qualification evidenceやdecision contextを
各benchへbindせず、D-001をrun eligibilityや環境比較dimensionにしない。

Git運用はlong-livedな相互mergeではなく、`bench -> profile`を基本方向にする。profile側はbenchの更新を
merge/rebaseして追従する。profileで見つけた最適化はprofile hookを含まない独立commitとしてbenchへ実装し、
その後benchからprofileへ取り込む。profile branch全体をbenchへmergeしない。必要なら二つのworktreeを使う。
branch名はmoving labelなのでidentityにせず、run manifestは次のcanonical source-track recordをsealする。

```text
{schema_version="source-track/v1", object_hash_algorithm,
 base_role="score_reference"|"profile_base", base_commit, head_commit}
```

bench/qualificationはscore reference、profileはprofile baseを選ぶ。run purpose、qualification arm、repository IDはsubject
manifest top-levelが所有し、nested recordへ複写しない。

`source_track_manifest_hash = SHA-256(canonical source-track record)`をsource-track projectionのidentityにする。hashをrecord自身へ入れて
再帰させない。全v2 benchはscore bundleを使い、score referenceがbench headのancestorであることを要求する。
D-001の初回判定が終わるまではbenchをaudit-onlyにする。合格後はこの制限を固定解除する。profileではprofile baseがprofile headのancestor、qualification OFFではhead=score referenceを要求する。
qualification ONではscore referenceがsource headのancestorである。このvariantだけがbase→headの
canonical tree diff v2を計算し、decoded path集合をscore bundleの`source_paths`へexact一致させる。
protocolの`control_plane_files`はbase/headとparentの実行checkoutで同じblob OIDを要求する。同時にbuild sidecarの
`commits[commit_role="build_definition"]` OIDをqualification ON source headに一致させ、profile-only overlay、profiler flag、
workload変更やcontrol-plane実装変更をdiffに含めない。algorithm/version、base/head、canonical entriesは
`control/source-track-diff.json`へ一度sealする。entriesのJCS SHA-256は採否decisionのcross-run join anchorへ一度だけ置き、
source artifactへhash/一致booleanを複写しない。

build生産時はclean checkoutのHEAD/treeをsidecar `build_definition` OIDと検査する。bench/profile/qualificationでは、
そのOIDをrunのsource-track headとも一致させる。D-001合格後も通常のsource/build provenance検査だけを行い、
qualification時のbuild semantic、score bundle、control-plane blobまたはsource diffを各benchへ再照合しない。
submodule pointer、file mode、symlink、LFS object
identityもqualification diff検証対象にする。全variantのhead/base commitはremote reachableでなければ投入しない。
base/headから決定的に計算できるdiff hashはrawへ重複保存しない。

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
artifact projectionの`*_raw_v2`もdaily ingestion-time partitionとし、subject/runおよび各row grainの先頭fieldで
clusterする。値のidentityやcomparisonにpartition時刻を使わない。

Git管理SQLは次の非二乗relationを作る。

| object | row grain | 役割 |
|---|---|---|
| `raw_distinct` | unique `(run,key,value)` | replayで生じた完全一致rowだけをdeduplicate |
| `run_key_singletons` | `(run,key)` | distinct valueが一つだけのtyped pivot入力。異値keyを通さない |
| `run_key_conflicts` | `(run,key,value)` | 異値が二つ以上あるkeyの各distinct valueを一行ずつ保持し、値を選ばない |
| `openfoam_run_fact_pivot_v2` | one row per run | conflict-free Fact refだけをtyped固定列へpivot |
| `openfoam_run_facts_v2` | one row per run | fact pivotへconflict-free projection refとGit-managed dimension refをconsumer bindingどおりjoinした最終Runs relation |
| `openfoam_run_commits_v2` | `(run,repository,commit_role,object_hash_algorithm,commit)` | source-trackとbuild manifestからalgorithm付きfull object IDを導出し、Git subject/body/URLをjoin |
| `openfoam_run_sources_v2` | `(run,consumer_column)` | 実在する値だけについてauthoritative raw key/artifact member/projection IDとtransform IDを示すlineage。欠損placeholderは作らない |
| `openfoam_source_tracks_raw_v2` | `(run)` | compact source track、base/reference/head commit、record/source hashを一度だけ保持 |
| `openfoam_build_provenance_raw_v2` | `(source_sha256)` | precision、label bits、compile flags、exact compiler/MPI/readelf output、build archive identityとpath順のexecutable/OpenFOAM shared-library runtime closureを一度だけ保持。source SHA-256がbuild-sidecar identity |
| `openfoam_build_provisions_raw_v2` | `(run)` | provision後のresolved executable/libmpi path/hashとldd exact contentをrun別に保持 |
| `openfoam_minimal_hardware_raw_v2` | `(subject_kind,subject_id,node_ordinal)` | regular runまたはqualification allocationのnormalized CPU identity/settingsとsource member/hashを一度だけ保持 |
| `openfoam_workload_manifests_raw_v2` | `(subject_kind,subject_id)` | workload identity、source member/hashを一度だけ保持 |
| `openfoam_workload_members_raw_v2` | `(subject_kind,subject_id,path)` | pathとexact content bytesを保持。manifest identityはparent join、size/hashはview派生 |
| `openfoam_profile_hardware_raw_v2` | `(run,node_ordinal,record_kind,numa_node_id)` | profile hardware artifactのnode summary/NUMA nodeをqueryableに転記。source member/hashを保持 |
| `openfoam_perf_counters_v2` | `(run,global_rank,event_name)` | profile run × expected rank × fixed five event skeletonへrank別`perf-stat/v1`をLEFT JOINし、counter/coverage値をqueryableにする。別base copyは作らない |
| `openfoam_rank_placements_v2` | `(run,global_rank)` | Fact `parallel.rank_placement`のordered arrayをglobal rank、hostname、local rank/size、CPU affinity、NUMA memsへlosslessに展開する唯一のlong consumer。別raw copyは作らない |
| `openfoam_qualification_allocations_raw_v2` | `(allocation_id)` | parent artifactのscheduler、decoded env、二job IDとfull bundle member arrayを保持。hardwareはallocation subject、workloadはchild subjectのrelationへ分離 |
| `openfoam_qualification_allocations_v2` | `(allocation_id)` | parent manifest/artifactからnamespace、ordered child IDs、binding、scheduler request/accounting/terminal、minimal hardware stage、observed control-plane hash、job-entry envを一度だけ投影。同じ`(namespace,pair_id)`が複数なら全候補をconflictへ出しskeleton joinへ0行を返す |
| `openfoam_instrumentation_decisions_v2` | `(decision_id,decision_sha256)` | 実装時に一度だけ行ったD-001受入試験のclosed記録。通常benchからjoinしない |
| `openfoam_instrumentation_decision_context_v2` | `(decision_id,decision_sha256)` | 一回限りの受入試験を確認するため、decision namespaceからqualification protocolへjoinしたevidence view。通常runのdimensionではない |
| `openfoam_comparison_dimensions_v2` | `(run,dimension)` | `must_match/treatment/nuisance/outcome`とcanonical value |
| `openfoam_qualification_estimand_points_v2` | `(contract_hash,protocol_hash,dimension_policy_hash,planned_comparison_set_id,pair_id,arm,estimand_id)` | protocol schedule基底のplanned skeleton。allocation/run/valueはnullable payloadとしてLEFT JOIN |
| `openfoam_replicate_points_v2` | `(run,estimand_id)` | 実bench runを直接基底にし、protocol、group/treatment、attempt/order/value、eligibleを全点表示 |
| `openfoam_replicate_stats_v2` | `(contract_hash,protocol_hash,dimension_policy_hash,planned_replicate_group_id,estimand_id)` | bench attempted全件とobserved一致済みeligible n、median、MAD、CV。bestとは別 |
| `openfoam_paired_points_v2` | `(analysis_purpose,contract_hash,protocol_hash,dimension_policy_hash,planned_comparison_set_id,pair_id,estimand_id,baseline_treatment_id,candidate_treatment_id)` | bench通常比較またはqualificationのprotocol指定pair。profileは行を出さない |
| `openfoam_paired_comparisons_v2` | `(analysis_purpose,contract_hash,protocol_hash,dimension_policy_hash,planned_comparison_set_id,estimand_id,baseline_treatment_id,candidate_treatment_id,estimator_id)` | ratio方向、pair数、interval、decision。未決定基準はNULL |
| `openfoam_env_facts_v2` | `(run,scope_kind,scope_instance,escaped_name)` | common/deltaから復元したfull snapshotのbyte-exact valueと由来 |
| `openfoam_run_diff_v2(left_run,right_run)` | table function、一declared dimension一行 | 二runのvalue/equality/class。片側欠損はNULL |
| `openfoam_env_diff_v2(left_run,right_run)` | table function、一scope/name一行 | full outer joinしたnullable左右値と、両値がある時だけのequality |
| `openfoam_archive_attempts_v2` | `(github_run_id,github_run_attempt)` | workflowが書くupload/SCP/publish outcomeと時刻、GitHub Artifact保持有無、home空き容量 |
| `openfoam_sheet_status_v2` | one row | SQL/contract identity、query時刻、latest publish/archive、未移管Artifact数、home空き容量、run-level collection incomplete件数 |

environmentの`scope_kind`はcontract enum `job_entry|host_exec_rank`、`scope_instance`はnullable node/global rank等を
field名付きcanonical JSONにしたinjective IDで、Sheetにはtyped scope列も出す。display hostnameだけをjoin keyに
しない。`escaped_name`はbyte nameの単射表現であり、同名でもscopeが違えば別rowである。

archive workflowは一attempt一rowのoperational recordだけを残す。hash chain、delivery FSM、receipt storeは
作らない。Data Statusはこのtableの`MAX`時刻と最新attempt、GitHub artifact inventory、home `df` snapshotを
表示する。scientific factへdelivery状態を複写しない。

artifact sourceが科学的正本で、artifact由来の`*_raw_v2`はSheet/agentから値をqueryできるようpublisherが
contract-declared row schemaへ一度projectionする保存境界である。direct projectionはsource member/hash、child projectionは
明示したparent projection/joinを持ち、別のmetric aliasやaggregateを作らない。
それ以外の上表は独立した保存メトリクス集合ではなくlogical query interfaceである。
各projectionのphysical append tableはreplay rowを許し、一source instanceを一load jobでappendする。logical
`*_raw_v2` relationは全列完全一致を一件へdedupeする。同じsource-instance grainに異なるsource hashがあれば
そのinstance全rowを、同じdeclared row grainに異なるpayloadがあればその全variantを`*_conflicts_v2`へ残し、
consumer入力から外す。
相互に列が重なるprojectionも別のraw producerやscheduled copyを作らない。lineageはcontractに定義した
consumer columnのordered source refsへ直接展開し、欠損用rowやreason rowを生成しない。publish後のprojection
conflictは該当consumerをNULLにするだけで、finalizerが確定したraw `collection_complete`を上書きしない。

`openfoam-v2.toml`にはraw contractと同じcommitで`[[consumer.run_column]]`を置く。各固定列は
`name,type,unit,source_refs,scope_cardinality,reducer_id,conflict_rule,transform_id,applicable_run_variants,
dimension_name,allowed_classes`を宣言する。`source_refs`はordered tagged listで、各entryに
`kind=fact|projection|dimension`、ID、必要なら`json_path`とvariant別`bindings`を持たせ、異種sourceを一つのreducerへ
渡す順序も閉じる。projection bindingはrun-keyedの`run_id -> run_id`、regular subject-keyedの
`run_id -> subject_id`、child-owned workloadの`run_id -> qualification_child subject_id`、qualification childから
parent-owned sourceへの`block_id -> qualification_allocation subject_id|allocation_id`、buildの
`artifact.build_manifest_sha256 -> source_sha256`を明示する。
`dimension`はGit管理のclosed `contract|protocol` relation、projectionはconflict-free
logical relationを入力にし、archiveをSQLから直接読まない。
dimension bindingはcontractならfact pivotの`(contract_id,contract_hash)`からdimensionの
`(contract_id,contract_sha256)`へ、protocolなら
`(contract_id,contract_hash,protocol_id,protocol_hash,dimension_policy_hash)`から
`(contract_id,contract_sha256,protocol_id,protocol_sha256,dimension_policy_hash)`へexact joinする。
branch、latest、IDだけへのfallbackは作らない。
instrumentation decision contextは一回限りのD-001 reportだけが読み、run manifestや通常benchのdimensionへjoinしない。
sourceが欠損または当該variantで非適用ならRuns列を`NULL`にする。複数sourceを使う
派生列はordered source listを持つ。生成SQL、Sources lineage、Sheet headerだけが
これを読み、手書きpivotを許さない。contract testは各consumer列についてexactly one column definition、
sourceの存在、type/transform、variant applicabilityを検査する。これにより列名からraw key patternまたはartifact/
Git dimensionへ機械的に一意に遡れる。

同じcontract/protocolに`[[consumer.estimand]]`を置き、`estimand_id`、source/transform、logical type、unit、
改善方向、eligibility rule ID、許すstatistic/estimator/interval、`applicable_run_variants`を固定する。
comparison dimensionとestimandはsource列のapplicabilityを継承する。当該variantで
NULLとなる列をdimension/estimand、observed fingerprint、config diff expected gridへ
入れない。point viewはprofile runを展開せず、bench/qualification runとそのpurposeにapplicableなestimandの
直積だけを展開する。source欠損は行を落とさずNULL valueにする。protocolは一次・二次
estimandとdecision対象を事前指定し、view実装者が結果を見て選ばない。

全run pairのdiffを通常viewとしてmaterializeしない。agent/SQL利用者とConnected Sheetsは二つのcell
parameterを持つcustom query `SELECT * FROM dataset.openfoam_run_diff_v2(@LEFT_RUN,@RIGHT_RUN)`、同env diffを
直接呼ぶ。NULL、同一、存在しないrunの指定はquery errorまたはzero rowとし、selection/status sentinelを
生成しない。valid config diffは左右contract/protocolのdeclared dimension gridのunionから始め、左右のdefinition
hash、logical type/unit/transform、policy classとnullableな左右値を表示する。互換な両値が実在する時だけ
equalityを計算し、それ以外はNULLにする。

env diffは復元済みfull snapshotをscope/nameでfull outer joinし、nullableな左右byte値だけを返す。両値が
実在する時だけequalityを計算し、片側snapshot欠損・非適用を表すstatus/sentinel rowは作らない。UI filter/
pivotだけで二run制約を実現しない。Sheetのfilterなしでfull environment extractを作らない。値はユーザー
指示どおり内部利用者へmask/redactせず表示するが、Sheetとdatasetの共有先を
同じ内部ACLへ限定する。

`openfoam_run_facts_v2`は少なくとも次の固定列を持つ。ここで挙げる名前をcontractのconsumer projectionへ
個別登録し、概念名だけの列を作らない。aggregate統計をrun rowへ複写せず、replicate viewを別tabにする。

| group | columns |
|---|---|
| identity/protocol | `run_id`、`contract_id`、`contract_hash`、`protocol_id`、`protocol_hash`、`dimension_policy_hash`、`planned_replicate_group_id`、`planned_comparison_set_id`、`planned_attempts`、`max_attempts`、`stopping_rule_id`、`block_id`、`block_order`、`pair_id`、`replicate_index`、`lane_id`、`run_purpose`、`qualification_arm`、`instrumentation_mode`、`instrumentation_bundle_hash`、`started_at`、`finished_at`。qualificationでは`block_id=allocation ID`を唯一のparent join keyにする。D-001 decision ID/hashは通常run列に置かない |
| source/artifact | `source_track_head_commit`、`score_reference_commit`、`profile_base_commit`、`source_track_manifest_hash`、`openfoam_commit`、`thirdparty_commit`、`build_manifest_sha256`、qualification childだけallocation projectionからjoinする`qualification_parent_archive_hash`。bundle hashはartifact dimension、URIはworkflow operational joinが所有しraw metricへ戻さない。role別commit metadataは`openfoam_run_commits_v2`だけに置く |
| quality | `collection_complete`、`official_log_valid`、`score_comparison_eligible`、`qualification_arm_eligible`。欠損原因やreason codeは列にしない |
| termination | `run_outcome`、`run_exit_code`、`solver_termination_kind`、`solver_exit_code`、`solver_signal`、`scheduler_terminal_state`、`scheduler_exit_code` |
| workload/build | `workload_id`、`workload_manifest_identity`、`workload_match`、`precision`、`build_artifact_sha256`、`compiler_identity`、build時`mpi_identity`、run時`mpi_execution_identity` |
| topology/placement | `requested_nodes`、`requested_ranks`、`allocated_nodes`、`solver_host_count`、`solver_nprocs`、`placement_host_count`、`placement_rank_count`、`resource_group`、`transport_policy`、`effective_transport`、`transport_valid`、`effective_file_handler`、`placement_affinity_signature`。validated placementが存在すればrank集合は必ず正しいため`placement_rank_set_valid`を作らずeligibilityがfact存在を直接要求する。`solver_host_rank_sum`はvalidated runtime headerの`solver_nprocs`と常に同じなので列にしない。現行`pjstat`が返さない`allocated_ranks`も作らない |
| hardware | bench coreの`cpu_model_consensus`、`kernel_release_consensus`、`physical_cores_per_node_consensus`、`numa_nodes_per_node_consensus`、`memory_total_bytes_consensus`、`cpu_governor_consensus`、`cpu_frequency_max_hz_consensus`、`cpu_boost_enabled_consensus`、`numa_balancing_consensus`と、profile-onlyの`numa_cpu_layout_identity`、`postrun_memory_available_bytes_min`。profile-only列はbenchでNULL |
| mesh | `mesh_cells`、`mesh_faces`、`mesh_points`、`mesh_internal_faces`、`requested_partition_identity`、`observed_partition_identity`。`partition_valid`はvalidated observed factの存在からTRUE/NULLしか作れないstatus duplicateなので列にせず、eligibilityがconflict-free requested/observed sourceとexpected subdomain一致を直接要求する |
| Pstream | `pstream_change_event_count`、`float_transfer`、`default_comms_type`、`pstream_buffers_algorithm`、`using_node_comms`、`node_comms_control`、`node_comms_min`、`topology_control`、`configured_mpi_buffer_value`、`environment_mpi_buffer_bytes_applied`、`attached_mpi_buffer_bytes`、`nprocs_simple_sum`、`nprocs_nonblocking_exchange`、`tuning_nbx`、`n_poll_proc_interfaces`、`max_comms_size`。startup/runtime consensus objectはこれらscalarの完全な投影、unchangedは`change_event_count=0`から完全導出なので列にしない。rank欠損時は該当valueをNULLにする |
| outcome | `official_fvops_trim_m`、`official_trim_sec`、`solver_outer_wall_sec`、`block_mesh_wall_sec`、`decompose_par_wall_sec`、`pipeline_end_to_end_wall_sec` |

profile counterはwide Runsへ5×rank列を増やさず、logical `openfoam_perf_counters_v2`だけで表示する。列は
`run_id/global_rank/event_name/raw_count_lexeme/count/unit/running_ns/percent_running/enabled_ns`に固定する。
profile runのlaneから`0..requested_ranks-1`、contractから
`cycles|instructions|branches|branch-misses|cache-misses`の記載順を展開し、conflict-free
`profile.perf_stat.rank.<rank>`のarrayをoffset/event一致でLEFT JOINする。record欠損時はevent skeletonを残して観測列を
すべてNULLにし、reason/status列は作らない。`enabled_ns`だけは`running_ns/(percent_running/100)`をquery時に導出し、
percentageが0/NULLならNULLにする。parsed Factと同じpayloadを別raw tableへ保存しない。

`placement_affinity_signature`はhostnameや物理CPU番号を直接hashせず、rank/local-rank順のCPU-set
cardinality、rank間overlap、NUMA binding、pinning shapeをcanonical JSONにした実値である。
eligibilityはこの実値をprotocol planned-value policyが所有する`placement_affinity_policy` must-match dimensionへ
直接照合する。完全導出できる`placement_policy_valid`列は作らず、異なる二つのvalid policyを同一視しない。
rank別のfull CPU set/hostはsource artifactに残す。

Fact ref列だけは`run_key_singletons`を入力にしてcontract typeから`SAFE_CAST`/JSON validationする。projection refは
各conflict-free logical relation、dimension refはGit-managed relationをconsumer bindingでjoinする。missing、conflict、
cast-invalid、非適用はいずれも最終wide列をNULLにし、原因列は増やさない。複数値を`MAX`、
`ANY_VALUE`等で隠さず、finalizerが見るraw Fact conflictだけ`collection_complete=false`にする。
commit metadataはGitから`openfoam_run_commits_v2`へrole付きでjoinし、commit messageをrun metricやRunsの
曖昧な単数列へ複製しない。

qualification parentはprogram runではないので`run/key/value`へ擬似runとして入れない。publisherが
`allocation-artifacts.tar.zst`をparseしてallocation-grain base table
`openfoam_qualification_allocations_raw_v2`へ投入し、その上の`openfoam_qualification_allocations_v2`が
allocation ID一意性とchild referenceを検査して投影する。standalone parent summary JSONは作らない。qualification childの
Runs/paired viewはqualification childの`block_id`でjoinし、同じscheduler request/accounting/terminalを二childの
raw keyへ複写しない。Environmentは同じjoinからparent job-entry snapshotをdecodeし、Hardwareはsubject
kind/IDを使ってparent-owned projectionをjoinする。Workloadは各childの`run_id -> qualification_child subject_id`、
regular runは自身のrun subject projectionを使う。

`openfoam_replicate_points_v2`はbench pointを実run基底で表し、failed/invalidも削除せずNULL値で全件残す。
`openfoam_qualification_estimand_points_v2`はqualification pointを
基底にせず、qualification protocolのexact pair schedule × two arms × applicable estimandsをplanned skeletonとし、
allocation projectionをnamespace/pair IDで、そのordered childをarmで、child Fact/estimand valueをrun IDで順にLEFT JOINする。
未投入pairはallocation/childがNULL、未起動childはrun/valueがNULLのまま行を保持する。replicate pointsはprotocol、planned/max attempt、stopping
rule、planned group/set ID、pair/block ID、estimand ID、nullable observed fingerprintを持つ。statsはplanned
groupでattempted nを数え、事前protocolのeligible ruleとobserved fingerprint一致を満たす点だけをeligible nへ
数える。treatment IDは宣言した全treatment dimensionのname/type/canonical value sorted tupleのhashで、
canonical JSONを表示属性にする。logical allocation viewは同じ`(namespace,pair_id)`を0-or-1 rowに制限し、複数allocationは
全候補をconflictへ出してskeletonへjoinしない。paired pointsはbenchではreplicate points、qualificationでは上記planned skeletonから
`analysis_purpose=score|qualification`を持ち、protocolが割り当てたpair IDだけを対応付け、欠損・置換後に
block/orderから推測しない。scoreは`score_comparison_eligible`、qualificationは
両armの`qualification_arm_eligible`、parent binding、common-source equalityからpair grainで導出した
`qualification_pair_eligible`だけを使い、purposeを跨いでpairにしない。paired comparisonはbaseline/candidateを順序付きで保持しratioを
`candidate / baseline`と定義し、planned/attempted/eligible pair count、median、MAD、protocolが明示した場合だけの
interval、decisionを併記する。これらはpoint rowとversioned protocolからquery時に導出し、rawへaggregateの
第二正本を作らない。estimator/intervalはprotocolが事前指定した方法だけを使い、
`instrumentation_overhead_decision`は一回限りのD-001 reportにだけ表示し、通常runや通常比較へ複写しない。
D-001 screenだけは、既知のarm/result不成立をeligible filterで消して残存pairだけを採用する選択バイアスを避けるため、
`qualification_pair_eligible`をpre-filterに使わない。planned skeletonからquery-onlyの共通evaluable集合`E`を直接作り、
取得済みgateのfalseを保持する。
breakingなcolumn/type/meaning変更は
既存v2 viewを書き換えずv3 objectを作る。

Connected Sheetsは次のtabだけをversioned consumer objectへ接続する。

1. `Runs`: one run/rowの固定列。JSON展開なしでquality、config、一次結果、artifactへ到達する。
2. `Replicates`: point viewとstats/comparison viewを別tableとして全点とrobust statisticsを示す。競技bestを同じ列で置換しない。
3. `Sources`: 選択runで実在する各表示列について、raw key、source、artifact member、transformを示す。
4. `Config Diff`: 左右run cell parameterからtable functionを直接呼ぶ。
5. `Environment`: 左右run cell parameterからscope-aware diffを直接呼び、full byte-exact envをmask/redactせず比較する。
6. `Rank Placement`: 選択runの`openfoam_rank_placements_v2`をglobal rank grainでlosslessに表示する。
7. `Profile Counters`: 選択profile runの`openfoam_perf_counters_v2`をrank/event grainで表示する。benchには非適用のplaceholder行を作らない。
8. `Data Status`: contract/SQL identity、各query時刻、latest publish/archive、未移管Artifact数、home空き容量を表示する。

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

## D-001: 実装時に一度だけ行うbench側計測の非擾乱確認

### 調査結果

profilerをprofile trackへ分離しても、benchに残すconfig hook、rank sidecar、Pstream source writeにも負荷はある。
したがって「profile branchを使った」こと自体を非擾乱の証明にはしない。一方、profile専用のperf/profiler、
polling、verbose traceはscore bundleへ含めず、このgateの対象をbenchで本当に有効にする最小bundleへ限定する。

公式baseline logの`ExecutionTime[last] - ExecutionTime[first]`を同じ式で再計算すると、独立job間のtrim時間は
次のように揺れる。これはinstrumentation on/offのpaired分散ではないためsample-size計算へ直接使えないが、
全laneを個別にqualificationする根拠はないため、実装受入には代表lane一つだけを使う。

| cluster | 1 node CV | 2 node CV | 4 node CV | run数 |
|---|---:|---:|---:|---|
| Gadi | 0.68% | 0.16% | 0.72% | 3 / 3 / 8 |
| ASPIRE-2A | 1.99% | 7.45% | 4.47% | 3 / 8 / 8 |
| Iris | 0.39% | 0.46% | 0.38% | 2 / 2 / 2 |

再計算sourceは[`tasks/baseline_logs`](../tasks/baseline_logs/README.md)である。初版ではこの分散からsample sizeを
再計算せず、固定5 pairの簡素screenとしてのみ使う。

### 確定した簡素な判定

D-001はメトリクス収集処理を実装した時点の受入試験として一度だけ実施する。初回が`reject`または
`inconclusive`なら実装を直してから再度試験してよいが、最初の`adopt`を得た時点で完了とする。その後の
通常benchでは判定を決め打ちし、定期実行、lane別実行、環境変更時の再実行、commit/bundle/runtime変更を契機とする
再qualificationは行わない。D-001の結果は実装時の確認記録であり、個々のbench runのeligibility条件ではない。

初版はOpenFOAM collector実装に対して一度だけ、実証済みの代表lane `n1-r120`で固定5 pairを事前commitし、
同一allocation内でOFF/ONを隣接実行する。順序は
exact `[OFF→ON, ON→OFF, OFF→ON, ON→OFF, OFF→ON]`とする。pilot、sample-size再計算、TOST、sequential stopping、replacement slot、別response
canaryは作らない。稀な失敗pairは欠測として残し、自動再投入しない。3 pair未満しか評価可能でなければ単に未決定とする。
評価可能pair集合は二metricで共通の一集合`E`をquery時に一度だけ導出する。planned pairに両child、parent binding、namespace、
各arm gateを評価するためのapplicable source、mesh/decomposition/workloadとinstrumentation対象外runtimeのidentity値、
正有限な両performance値、result-equivalenceを評価するsourceがすべて存在するpairだけを`E`へ入れる。
ここで必要なのは証拠の存在であり、`qualification_arm_eligible`、identity equality、official validityまたは
result equivalenceのtruth値ではない。取得済み証拠からfalseを導出できるpairは`E`に残して後段のreject材料にし、
証拠自体が欠けるpairだけを欠測にする。metric別集合、pair別reason/status、persistする`d001_pair_evaluable` booleanは作らない。

判定対象はqualificationのexact contract/protocol/policy namespaceが所有する`lane_id`、score reference source object、
workload identity、reference/score bundle path/SHA-256、control-plane file blob集合、exact 5-pair scheduleと、
post-runで得るqualified source diff SHA-256、reference/final build-semantic pairである。final head commitは無関係な変更を
含み得るためdecision identityにしない。
build-semantic hashはbuild projectionのprecision/labels/flags、OpenFOAM/ThirdParty source、toolchain、runtime closureから
導出し、build-definition commit/sidecar lineageは除く。toolchain等は個別のrun比較dimensionとして見えるため、
全archive hashはpackage integrityにだけ使う。lane/reference/workload/bundles/control-plane files/5 pair scheduleはpre-buildのexact protocol relationが
一度所有する。runtime closureで初めて決まるreference/final build-semantic pairはpost-qualificationのevidenceなので、
採否recordは`decision_id`、qualification namespace、`adopt|reject|inconclusive`をGit管理し、adopt/rejectだけ
qualified source diff SHA-256、observed build pair、評価可能childで一値のobserved runtime MPI semantic SHA-256を持つ。
inconclusiveは一値のevidenceを捏造せずそれらをabsentにする。
この採否recordは一度だけ行った実装受入試験の記録として残す。合格後は変更検知による自動再openや再判定を行わず、
通常benchからこのrecordへのbindingも要求しない。

OFF/ONは次だけを変える。

- `OFF`: unmodified bench solverと両arm共通の外側timer/log保存。
- `ON`: release予定binaryとbenchで有効にする最小hook/rank source bundle。

各pairは独立case directoryを使うが、同じallocation、tracked lane/MPI executable/resource/transport policy、mesh、
decomposition、workloadを使う。ONにだけ必要なbundle宣言済みwrapper、sink binding、patch以外のlauncher設定は
同じにする。OFFでは計測しないactual mapping/cpuset一致を判定条件にしない。
初版は全stageのexact argvで`-fileHandler uncollated`を固定し、runtime headerのactual handlerも一致させる。
両caseのsetup、workload capture、blockMesh、decomposeParはarm 1のscored solver前に完了する。
二つのscored solver間にbuild/copy/mesh preparation/checkMesh/archiveを挟まない。片armが失敗しても保存できたlogを
残し、そのpairの値をNULLにするだけで別allocationのrunと再pairしない。

判定は評価可能pairについて次を人間とagentが同じSheetで直接確認する。

- 公式FVOPS比 `FVOPS_ON / FVOPS_OFF` のmedian
- solver outer wall比 `wall_ON / wall_OFF` のmedian
- official validity、mesh/workload identity、pressure residual/iteration trajectoryの一致
- ONで必要なsource fileが正常pathでは揃うこと

exact qualification protocolの`qualification_target.screen`が次を一度だけ所有する。decision record、
raw row、child manifestへ閾値やeligible数を複写しない。
closed `protocol/v1`ではscreenをqualification時required、bench/profile時absentとし、decision contextはprotocolからjoinして露出する。

```text
criterion_id: const "median-pair-ratio-screen/v1"
minimum_evaluable_pairs: const 3
require_both_arm_orders: const true
pair_set: const "common-evaluable-pairs"
median: {kind:const "continuous", even:const "mean-middle-two"}
criteria:
  - {response_id:const "official_fvops_trim_m", ratio:const "on/off",
     lower_bound_inclusive:const 0.99}
  - {response_id:const "solver_outer_wall_sec", ratio:const "on/off",
     upper_bound_inclusive:const 1.01}
result_equivalence_policy_id: const "openfoam-official-validity-pressure-trajectory/v1"
```

両`response_id`は同じcontractの既存`consumer.estimand.estimand_id`を参照し、screen専用generic metricを増やさない。
ratioとmedianはBigQueryの通常の数値演算で計算し、偶数個なら中央二値の算術平均を使う。Sheetの表示丸め前の値を
0.99/1.01と比較すれば十分とし、専用の数値型や境界補正は実装しない。

`openfoam-official-validity-pressure-trajectory/v1`のevidence presentは、両armについてofficial marker、
pressure-solve全array、そこからofficial validityを評価する全sourceが存在することを意味する。result equivalenceは両armの
`official_log_valid=true`かつofficial-marker objectがexact一致し、pressure-solve arrayがlog順のまま
simulation time、initial/final residual、iterationのlexemeとparse値をexact一致する時だけtrueである。
mesh/workload/decomposition identityはこのpolicyへ重ねず`E`のpreconditionで比較する。evidence-presentとequivalenceの
nullable truth値はquery時に別々に導出し、第三のraw equality booleanを保存しない。同じexpected workloadへの各arm一致から
actual同士の一致は導出できるため、そのequalityも保存しない。

確定規則は、まず同じ`E`について`|E| >= 3`、両arm orderを一件以上含むこと、pair内および`E`全体の
比較identityとpost-run semantic identityが一値に定まることをpreconditionとする。どれかが不成立なら、他gateの値にかかわらず
`inconclusive`である。precondition成立後、BigQueryで得た未表示丸めのratio medianについて
`median(FVOPS_ON / FVOPS_OFF) >= 0.99`、`median(wall_ON / wall_OFF) <= 1.01`、全pairのresult
equivalenceと各arm gateがtrueなら`adopt`、いずれかがfalseなら`reject`とする。これはformalな非擾乱証明ではなく、
実験projectで明らかな計測負荷をbenchへ持ち込まないためのscreenである。5 pairの個々の値とmedianを表示し、個々のratioへ
1% gateを掛けない。CI、power、MAD、closed reason enumはgateにせず、retry/replacementも作らない。

D-001をまだ実行していない間はbenchをaudit-onlyにする。最初の`adopt`後は実装受入済みとして固定し、
通常benchへoverhead decision列を持たせたり、runごとにdecisionを再評価したりしない。profile runはscore比較へ混ぜない。

## 決定事項と再open条件

D-003は2026-08-09にユーザー回答「基本的にはマルチノード対応型の収集」で確定した。質問はGenkai 1 nodeだけを
初版canaryにするか、1/2/4 nodeをv2対象にするか、推奨は前者、採用回答は後者である。affected fields/viewsは
lane resolved object、scheduler request、producer node/rank axes、placement/host consensus、profile rank source、
score/qualification eligibilityである。reopen triggerは対象clusterのnode modelまたはscheduler/MPI placement意味が変わり、
同じlane schemaでnode/rank集合を表せなくなった時だけとする。

実装上は1/2/4 nodeで同じcollector graphを使い、node/rank数だけをlaneから展開する。未実証2/4-nodeの値を
成功扱いせず、通常canaryの実観測をそのまま保存する。専用collector、fallback discovery、再投入枠は追加しない。

D-001はcollector実装時に一度だけ、固定5 pair、最低3評価可能pair、FVOPS低下1%以内、solver outer wall増加1%以内の
簡素screenを行うことで確定した。最初の`adopt`後は結果を決め打ちし、reopen triggerは設けない。

## 決定状態

| 状態 | 決定 |
|---|---|
| 確定 | raw relationは`run/key/value`の三列、compound valueはcanonical JSON |
| 確定 | 定義した各process scopeの環境変数は機密値を含めfilterせずbyte-exactに全件保存 |
| 確定 | native object/structured sourceを優先し、log regexはfixture付きの最終手段 |
| 確定 | compute側はlocal raw fileだけ、finalize/publishはrunner、Artifact upload/home移管はworkflowが担当 |
| 確定 | complete recordのsubsetであるfirst/last/count/average等をrawへ重複保存しない |
| 確定 | bench/profileを分離し、取得できなかった値とprofile専用familyは値だけNULL、原因/status/欠損用recordなしとする。run-level statusは`collection_complete`だけ |
| 確定 | 実験用途として多段retry、fallback source、field別reason registry、formalな大規模qualification campaignは作らない |
| 確定 | artifact移管は現行OpenFOAMのGitHub Artifact -> Tailscale/SSH -> home RAIDを基準とし、Qwenへも同じ経路を移植する |
| 確定 | home artifactは自動expireせず、容量が実際に問題になった時だけ手動整理する。専用quarantineは作らない |
| 確定 | D-003: collectorはlane-driven multi-node対応とし、Genkai 1/2/4 nodeを初版実機conformance対象にする。初版canaryは総120 ranksのbalanced 1/2/4-node lane |
| 確定 | D-001: collector実装時に代表`n1-r120` laneで一度だけ、固定5 pair、最低3評価可能pair、FVOPS低下1%以内かつsolver outer wall増加1%以内の簡素screen。最初のadopt後は決め打ち |

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
collect_once(manifest_path, runtime_dir, producer_id, probe) -> Path
submit_subject(subject_manifest_path, runtime_dir, lane_adapter, pjsub_argv) -> SubmissionOutcome
run_stage(stage_name, argv, *, cwd, stderr_mode, recorder) -> Termination
finalize_subject(subject_manifest_path, runtime_dir) -> tuple[FinalizeOutcome, ...]
publish_subject(subject_manifest_path, artifact_set_path, destination) -> PublishOutcome
```

`Recorder.open`はpersist済みmanifestとregistryをread-onlyで検証し、runを生成・推測しない。
`LogicalValue`はstring、bytes、bool、int、finite float、Decimal、UTC timestamp、またはJSON treeに
限定する。top-level `None`は禁止し、bytes/Decimal/timestampとcompound JSONのencodingはregistryの
logical typeが決める。
`append_many`だけがlogical valueをcanonical stringへ変換し、一行ずつ`run/key/value`へbuffered writeする。
`seal`はflush/closeしてtemporary fragmentをrenameする。semantic ownerはprobe外側のsupervisorまたは
`StageRunner`である。正常終了時にexpected fragmentが存在することを
finalizerが検査し、途中crashから全eventを救うための逐次syncは行わない。
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
`stage_runner.py`、`finalize_subject`は`artifact_store.py`、`publish_subject`は`publish.py`が
所有する。`cli.py`はargument parseとhandler dispatchだけを行い、manifest生成、scheduler subprocess、
probe lifecycleを実装しない。
`publish_subject`はregularなら一runのmetrics/projection、qualificationならset manifestを入口にparent projectionと
ordered二childの`metrics.jsonl`/applicable projectionを一callで送る。childだけを別callしてparent joinを欠かさない。

`collect_once`はfragment pathをstdoutへ返し、成否はprocess exitだけで表す。`SubmissionOutcome`は
`submitted|failed`とnullable job IDを持つ。曖昧submitを自動探索・復旧するstate machineは
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
| `.github/workflows/genkai.yml` | pre-submit manifest、submission/job-entry取得、terminal後finalize/archive/publishを所有 |

実装fileは計画済みの`domain.py`、`recording.py`、`submission.py`、`stage_runner.py`、`merge.py`、
`artifact_store.py`、`publish.py`とdomain別probe/parserに限定する。`manager`、`service`、汎用event
bus、DI frameworkは追加しない。`submission.py`は一回のscheduler submitと結果保存を隠す深いmoduleであり、
collectorやpublisherをimportしない。OpenFOAM固有adapterは`rank_wrapper.py`だけにする。same-rank wrapperは
検証済みglobal/local rank、local size、placement、env deltaをrank別source fileへ書いてsolverを`exec`する。

第二段階のOpenFOAM hookは
まずprofile purposeだけで有効にする。D-001を通したexact bundleだけbench expected graphへ追加できる。hookが
startup/runtime/change source recordをrank別`domain/pstream/rank-<rank>.jsonl`へbuffered appendする。
ACK待ちや逐次syncをせず、write failureをsolver exit/numericsへ伝播させない。terminal後のreducerがexpected
rankとsentinelを検査し、欠損値をNULL、runの`collection_complete=false`にする。timing影響はG9で判定する。

機械可読正本は`experiment-metrics/contracts/openfoam-v2.toml`一fileにする。producer entryがowner scopeとapplicable variant、
source entryがpath/schema/requiredness、fact entryがkey/type/unit/source/reducerを各一度所有する。lane/protocolはこのcontractに
定義済みのproducer IDからexpected graphを選ぶ。runtime manifestにはcontract IDとcontent hashを
sealし、raw tableにはroutingに必要なcontract IDだけを索引化する。観測マップの表はこのTOMLから
生成し、手書きproseだけを別に保つ。したがってregistryとMarkdown表の二つを正本にしない。

各`[[fact]]`のcanonical field listは
`id,key_pattern,source_id,schema_id,logical_type,unit,cardinality,capture_id,validator_id,reducer_id,
duplication_justification?`だけとし、producer/owner/applicability/requirednessをsource→producer joinから複写しない。
各`[[artifact_projection]]`は
`id,base_table_id,relation_id,conflict_relation_id,source_artifact_id,source_schema_id,row_schema_id,row_grain,
subject_scopes,publisher_id,transform_id,conflict_rule,source_member_field?,source_sha256_field?,
source_instance_grain?,source_instance_sha256_field?,parent_projection_id?,parent_join_columns?,duplication_justification`だけを持つ。
`subject_scopes`はrun variant付きrun ownerと、variantを持たないqualification-allocation/build ownerのtagged arrayである。

### CLIと設定境界

CLIは次の六orchestration use caseだけを持つ。behaviorを環境変数で切り替えず、manifestとruntimeは
明示引数、比較条件はGit管理protocol、BigQuery宛先はrunner側のGit管理設定から読む。

```text
init-subject   regular runまたはqualification parent+二childのmanifestを作成
submit         exact pjsub argvを一度実行し、stdout/stderrと取得できたjob IDを保存
collect        compute producerを一度実行し、成功時だけ完成data fragmentを残す
stage          target argvをspawnしterminationと時間を記録
finalize       terminal後にsubjectを検証し、expected artifactとmetrics.jsonlを作成
publish        regular artifact set、またはparent+ordered二childを含むqualification setを一callでBigQueryへ送達
```

`init-subject`以外は`--subject-manifest`を必須にし、compute内部の`collect`/`stage`だけはparentが指定した
`--run-manifest`を必須にする。`EXPERIMENT_METRICS_RUN`、PID、PJM IDからsubject/runを再構成しない。
`collect`と`stage`はBigQuery設定やcredentialをimportしない。`finalize`と`publish`を分けることで、
送信障害を理由にcomputeやarchiveを再実行しない。

`submit`はexact argv、subject ID、stdout/stderr、subprocess outcome、取得できたjob IDを通常fileへ保存する。
応答を確定できないrunner crashはそのattemptを失敗とし、自動nonce検索、recovery receipt、blind resubmitは
実装しない。PJM側はrun/allocation IDと`PJM_JOBID`をjob-entry fileへ書き、terminal後にrunner側job IDと照合する。
PJM batch stdout/stderrはsubmission requestでregularなら`<runtime>/runs/<run>/logs/pjm-job.log`、qualificationなら
`<runtime>/allocations/<allocation>/logs/pjm-job.log`を直接指定する。これはsupervisor/orchestration messageだけにし、StageRunnerの
child stdout/stderrは各stage/solver logだけへ書き`tee`しない。submit command自身のstdoutは
`control/submission.stdout`が所有する。job ID parserは現行fixtureの
`^Job ([0-9]+) submitted\.$`に固定する。terminal captureは実行した`pjwait` argv/stdout/stderr/exitと時刻を
`scheduler-terminal.json`へ一度保存する。`pjstat-version.txt`にはcanaryで確認したversion表示commandとraw outputを残す。

`rank-wrapper`は上記六use caseへ数えないOpenFOAM固有internal entrypointである。
`scripts/run-openfoam.pjm`とsolver argvだけが呼び、一般利用者向け設定面にはしない。allocationのnode、
affinity、mesh/hardware auditはPJM scriptが終了する前にfileへ書く。runnerの`finalize`はallocationへ
再接続せず、terminal accountingと既存log/source/artifactのpure parser/reducer
だけを実行する。

### runtimeとarchive layout

runとsubmission subjectを分け、run側は次の固定layoutにする。任意file探索や「最後に見つかったJSON」を禁止する。
実行物は共有`<runtime>/bin`へ置かず、`<runtime>/provisions/<build-sidecar-sha256>/bin/`のimmutable
per-build directoryをrun manifestが参照する。

```text
<runtime>/runs/<run>/
  control/run-manifest.json                 # pre-submit immutable
  control/contract.toml                     # regularだけ。qualificationはparentが一度所有
  control/protocol.toml                     # regularだけ。qualificationはparentが一度所有
  control/source-track-diff.json            # qualification ONだけ: diff algorithm/base/head/entries
  control/instrumentation-bundle.json        # 実際に選択したcomponent/launch設定
  control/build-sidecar.json                # resolved source/toolchain/binary identity
  control/build-provision-validation.json   # provision後binary/ldd/libmpi identity
  control/submission-request.json
  control/submission.stdout
  control/submission.stderr
  control/submission-result.json            # raw subprocess outcome when available
  control/job-entry.json                     # PJM側のrun IDとPJM_JOBID
  metrics/fragments/<producer>.tmp           # write中
  metrics/fragments/<producer>.jsonl         # 正常close後のrename先。merge成功後削除
  domain/pstream/rank-<rank>.jsonl
  source/workload-manifest.json
  source/workload/0/{U,p}
  source/workload/constant/transportProperties
  source/workload/system/{controlDict,fvSchemes,fvSolution,blockMeshDict}
  source/hardware/node-<node-ordinal>.json
  source/mesh/mesh-topology.json
  source/mesh/partition-observed.json
  source/mesh/decomposeParDict
  source/env/job-entry.snapshot
  source/env/host-exec.snapshot
  source/env/rank-<rank>.delta.json
  source/placement/rank-<rank>.json
  source/scheduler/pjstat.stdout
  source/scheduler/pjstat.stderr
  source/scheduler/pjstat-version.txt
  profile/raw/...                            # profileだけ。OPENFOAM_PROFILE_DIRの実体
  profile/raw/hardware/node-<ordinal>/...    # profileだけの追加sysfs/proc raw
  logs/pjm-job.log
  logs/log.icoFoam                           # solver combined log
  logs/<preparation-stage>.stdout
  logs/<preparation-stage>.stderr
  logs/checkMesh.log
  control/scheduler-terminal.json
  merge/metrics.jsonl
  archive-staging/run-artifacts.tar.zst
  archive-staging/bundle.manifest.json
  archive-staging/artifact-manifest.json
  archive-staging/profile-raw.tar.zst        # profileだけ
```

regular runだけが上記`control/submission-*`、job-entry、`control/scheduler-terminal.json`を所有する。
qualification childではそれらを作らず、代わりに
child manifest自身のallocation ID、parent manifest hash、top-level qualification arm、
pair IDを使う。block/order/replicateは親とprotocolのarray offsetから導出し、別parent-ref fileは作らない。
qualification parentは次の固定layoutを所有する。

```text
  <runtime>/allocations/<allocation>/
  control/qualification-allocation-manifest.json
  control/contract.toml
  control/protocol.toml
  control/submission-request.json
  control/submission.stdout
  control/submission.stderr
  control/submission-result.json
  control/job-entry.json                           # allocation ID/job ID/ordered child IDs
  control/minimal-hardware-stage.json              # parent one-shot launch/termination
  source/env/job-entry.snapshot                    # NUL区切りbyte-exact parent source
  source/scheduler/pjstat.stdout
  source/scheduler/pjstat.stderr
  source/scheduler/pjstat-version.txt
  source/hardware/node-<node-ordinal>.json
  logs/pjm-job.log
  control/scheduler-terminal.json
  archive-staging/allocation-artifacts.tar.zst
  archive-staging/qualification-set-manifest.json
```

qualification parent sourceはcontract/protocolを含む上記`control/`、`source/`、`logs/`を
`allocation-artifacts.tar.zst`へ一度収録し、
`logs/pjm-job.log`をrequired memberとするがrun metricsは持たない。各childはparent manifest hashだけを参照する。
qualification child tarへcontract/protocol bytesを複写せず、child manifestのID/hashからparent copyへjoinする。
同じworkflow artifact/home directoryでは、外側`qualification-set-manifest.json`に従い
`qualification/<allocation>/allocation/`と`qualification/<allocation>/runs/<child>/`へ分ける。これによりparentと
二childの同名fileを衝突なく一setとして移管し、publisherがparent sourceをallocation-grain raw tableへ投入できる。

runごとのarchive対象は次の三fileを基本にする。

```text
run-artifacts.tar.zst   # 下記expected control/source/domain/log/result
metrics.jsonl           # 最終raw sidecar
artifact-manifest.json  # outer file role、size、SHA-256。filenameはroleから導出
```

bundle memberはrun variant別のmanifest駆動exact allowlistとする。regularは`control/`のmanifest、contract、
protocol、submission raw stdout/stderr、実在するsubmission result、job-entry、scheduler-terminal、PJM accounting raw/version、
PJM batch logを含む。regularはworkload manifest/memberとminimal hardwareも含む。全program runはbuild sidecar、
mesh/partition summary、該当するenvironment/placement、solver combined log、preparation/checkMesh logをexpected fileとして列挙する。
公式結果はsolver logからviewで一度だけ導出する。qualification childはparent-owned contract/protocol、job-entry env、hardware、
scheduler/accounting/PJM batch logを含めない一方、自身の実caseから取ったworkload manifest/memberは含める。
いずれも`domain/`、`source/`、`logs/`、自己を除くmember path/hash/sizeを持つ
`archive-staging/bundle.manifest.json`を作り、tar rootの`bundle.manifest.json`として含める。最終
`metrics.jsonl`とartifact manifest、merge元fragmentはbundle内へ重複収録しない。

`run-artifacts.tar.zst`はmanifestで列挙したmemberを収録し、作成後の実byte列をhashする。再実行時にtar headerや
compressor versionまで同一にして同じbundle hashを再現することは要求しない。同一run attemptでは既に作った
bundleをそのまま転送し直す。
最終`metrics.jsonl`は完全一致rowを一件へし、異値conflictは全rowを残したまま`(run,key,value)`の
UTF-8 byte順にsortする。各lineはobject member順`run`,`key`,`value`、空白なし、UTF-8、LF終端へ固定する。

manifestは通常のtemporary writeとrenameで完成させる。基本三fileとprofile attachmentをGitHub Artifactへ
uploadできた時点でGenkai runtimeはcleanupしてよい。archive jobはそれらをhomeの
`<github-run-id>/attempt-<attempt>/`へ`scp`し、SCPが成功した時だけGitHub Artifactを削除する。現行OpenFOAM
移管と同じくremote再読取checksum、transaction、reconciler、別delivery storeは実装しない。

BigQuery publishはhomeへ保存したsubject artifact setまたは同じGitHub Artifactから再実行できればよい。
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
`<runtime>/runs/<run>/profile/raw`へ固定し、rank別`perf/rank-<global-rank>.csv`とprofile-only hardware rawだけを
`profile-raw.tar.zst`へ収録する。`perf --version`はbuild-provision validationが一度所有し、profile tarへ複写しない。
exact launch recordとsolver logはrun bundleが所有するためprofile tarへ重複させない。MPI rank executableはhash済みwrapperとし、
wrapperは`PMI_RANK`を検証してrank別pathをrenderし、各rankで
`<resolved-perf> stat --no-big-num -x, -o <profile>/perf/rank-<global-rank>.csv -e cycles,instructions,branches,branch-misses,cache-misses --
<resolved-icoFoam> <solver-subargv...>`をshellなしで一回起動する。各CSVは五eventを記載順にexactly one row持ち、unsupported rowも
残してcountだけNULLにする。perf失敗時にsolverだけを再実行しない。benchではprofile artifactや欠損用recordを作らず、
対応consumer値は`NULL`だけである。
build archiveは現行Genkai cacheを使い、runにはbuild sidecarの
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
run manifest -> submit result/job-entry -> compute log/source/ephemeral fragments
             -> terminal accounting -> post-run validation -> run artifact + metrics.jsonl
             -> GitHub Artifact upload -> runtime cleanup -> home SCP -> BigQuery publish

qualification:
allocation manifest -> submit result/job-entry -> child OFF source/log/metrics
                                           \-> child ON source/log/metrics
                    -> terminal accounting -> one qualification artifact set
```

- finalizerはvariant別expected file、producer、rankとrequired keyを一度検査する。正常終了runで
  欠けていれば`collection_complete=false`とする。失敗・timeout runの`.tmp`は手元に診断用として残り得るが
  artifact/merge入力にせず、partial line recoveryや欠損の空文字/zero補完はしない。
- 同一run/keyの異値は両方を保持し、conflictとしてpublishしてcomparisonから隔離する。
- foreign run、unknown key、owner違反、canonical encoding違反はfragmentをmetrics sidecarへ混ぜない。
  専用quarantine状態や二次保存経路は作らない。
- process timeout、signal、spawn errorでもrunnerはscheduler terminal後にpost-run parserとfinalizeを
  実行できる範囲でraw log/sourceをartifactへ含める。任意のcrash境界から完全再開できることは要求しない。
- cleanupはGitHub Artifact upload成功後に許す。publish失敗はhomeまたはGitHub Artifactの
  同じsubject artifact setから手動再送し、computeを再実行しない。

### gateを証明するtest

| gate | 必須test/fixture | 証明すること |
|---|---|---|
| G0 依存境界 | `test_dependency_boundaries.py`、CLI subprocess import trace | domain/probe/recording/collect/stageのtransitive importにpublisher、credential、networkがない |
| G1 値契約 | `test_domain.py`、RFC 8785/decimal/env byte fixture | 空、zero、欠損、非有限拒否、単射escape、canonical byte |
| G2 submit/join | `test_submission.py`、regular/qualificationのsuccess/reject/mismatch fixture | exact argv/stdout/stderr/job ID保存、submission resultとjob-entryからallocation/job/ordered child joinを導出 |
| G3 local file | `test_recording.py`、正常終了・program failure fixture | buffered writerのclose/rename、完成fragmentだけがmerge入力になり、merge後fragmentと失敗tmpをartifactへ入れないこと |
| G4 ownership/merge | `test_merge.py`、variant別producer graph fixture | owner一意性、exact dedupe、異値conflict、required欠損、qualification parentのjob env/minimal hardwareを二childへjoinしてraw複写しない。欠損・非適用のconsumer値はNULL、required欠損時だけrun-level `collection_complete=false` |
| G5 process観測 | `test_stage_runner.py` | actual argv/cwd、combined log、process-group signal forwarding、exit/signal/spawn error、monotonic境界 |
| G6 archive/送達 | workflow integration fixture | happy pathで全expected artifactがhomeにあり、upload失敗はattempt failure、SCP失敗ではGitHub Artifactが残る。homeのartifact setをBigQueryへ再送できる |
| G7 OpenFOAM意味 | `test_observation_contract.py`、baseline log/mesh/Pstream/rank/source-diff fixture、64M-cell canary | contract source/時点/owner、観測済み変更0件の`[]`、rank欠損時NULL、qualification ONの差分がinstrumentation patchだけ、native partition完全検査とRSS上限、profile rank別exact five perf eventであること |
| G8 consumer contract | contract生成SQL fixture、variant別BigQuery golden rows、Sheet parameter/refresh smoke test | 全列lineage、profile attemptのscore統計除外、非適用・欠損列がNULL、pair-grain eligibility、同bundleでbase/workload/toolchainだけ変えたbench拒否、失敗attempt残存、protocol分離、estimand、definition非互換・片側env欠損TVF、freshness/size |
| G9 非擾乱 | collector実装時に一度だけ行うD-001のunmodified OFF/final ON固定5 pair | 二metric共通E、両arm order、continuous median、inclusive 0.99/1.01境界、数値結果一致を使いadopt/reject/inconclusiveを再現し、最初のadopt後は再実行しないこと |

`test_observation_contract.py`はcontractのschemaとowner/source/capture/applicability/validatorの完全性を検査し、
生成した観測マップ表がcommit済み表とbyte一致することを検査する。これが「この値はどこから取るか」
を、一つの正本から人間向け表と実行時validationの双方へ機械的に保証する。

### release単位

移行はkeyごとに二重化せず、run contract単位で行う。

1. legacyの出力、shell evaluator、baseline logをgolden fixtureとして凍結する。
2. pre-submit manifest、local metrics export、OpenFOAM native probe、complete solver record、Pstream/placement
   sidecarを一つのv2 fixtureと最初のv2 runで通す。
3. benchへ必要な最小subsetだけを、collector実装時に代表`n1-r120` laneで一度D-001へ掛ける。意味・数値同等性・
   非擾乱screenがadoptになったらbenchへ追加し、他laneや以後の変更では再実行しない。
4. v2 viewとSheetを切り替え、legacy-only consumerがゼロになってから旧senderとsubset keyを削除する。

rollbackはlaneのprotocol contractを直前版へ戻して新しいrunを投入する。既存runのmanifestやrowを
書き換えず、一run内でlegacy producerとv2 producerを混在させない。

## 実装順序

1. 現行key、producer、consumer、artifact保存先をinventory化し、key registry、expected producer
   graph、`run.metrics_contract`を作る。contractなしはlegacy、run内のproducer contract混在はinvalid、
   v2 viewはexact contractだけを読む。
2. clean checkout、remote到達性、build sidecar manifest、manual provenance gateを作る。
3. BigQuery credentialをrunnerだけへ移したうえで、現行metric集合のまま`Fact`、`Recorder`、
   JSONL export、runner merge/publish、workflow artifact upload/home移管を導入する。
4. ingestion-time partition/`run,key` clusterのraw table、distinct/singleton/conflict、Sources lineage、
   archive attempt/status、exact-contract run/dimension/point/stats/paired view、二run table
   functionをconsumer column contractから生成しfixtureを通す。
5. cavity3Dのactual workload manifest、complete solver record、mesh、provenanceをlegacy collectorと並行追加する。意味が
   変わる既存keyをv2で再利用しない。
6. canonical official evaluatorを作り、旧shell validityと全baseline golden logを照合する。
7. D-003で確定したlane、同一rank wrapper sidecar、二段階Pstream/partition auditを追加し、最終
   instrumentationを含む全対象laneでbaselineと比較適格性を再検証する。各laneでunmodified OFFと
   exact final ONを同一mesh/partition/rankで対にし、pressure residual/iteration軌跡と公式markersの
   lexeme一致を数値同等性ゲートにする。
8. Connected SheetsのRuns/Replicates/Sources/Config Diff/Environment/Rank Placement/Profile Counters/Data Statusをbounded consumerへ
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
- profile runの全raw attachmentをhome pathから読め、bench archiveにはprofile pathも欠損用
  recordもなく、対応Sheet列がNULLだけになる。
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
- 各run/Sources/Sheet列がcontract raw keyまたはGit/artifact dimensionへ一意に遡れ、cast失敗や異値競合を
  aggregateが隠さない。
- 二run diffがcell parameter付きtable functionで計算され、NULL/同一/不存在runを拒否し、全run pairを
  materializeせず、full envをparameterなしでSheetへextractしない。
- config definition/policy非互換または片側env snapshot欠損では、左右値/equalityをNULLにする。
- Data Statusが各objectのquery時刻、最新publish、未移管Artifact数、archive job最終成功時刻、home空き容量、
  SQL/contract identity、conflict/run-level collection incomplete件数を表示し、
  scheduled refreshのowner変更・停止とresult-size超過をsmoke testで検出できる。
- Sheets利用者がJSON展開なしでcommit、妥当性、一次結果、反復統計、artifactへ到達できる。
