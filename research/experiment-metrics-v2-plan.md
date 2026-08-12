# 実験メトリクス再設計計画（旧merge/projection設計資料）

> この文書は当初計画の履歴資料である。実装済みの直接送信keyと非収集項目は
> `research/experiment-metrics-v2-key-catalog.md` を正本とする。

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

`run`は全producerが共有するglobally uniqueでimmutableなIDである。job投入前に
OS CSPRNGの16 byteを32文字のlowercase hexで表す128-bit `subject_nonce`を一つ生成し、
`submission_subject_id=run_id`とする。`pjsub`返却後にしか分からないPJM job IDはrun IDへ
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
  started/final耐久journalは作らない。finalizerはpurpose applicabilityとbundle selectionから
  expected fragment/fileを一回導出し、存在と照合して`collection_complete`を一度導出する。回収できた
  source/logは不完全runでも収録する。

contract/protocolのIDやhashはmetricへ保存しない。既存keyの意味、unit、JSON shapeを変える場合は
新keyにし、細かい仕様はソースと文書を正本にする。

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
完成artifactを作らない。原因fieldは追加しない。

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

- `source/env/job-entry.snapshot`: PJM entry直後のraw provenance artifact。factへは投影しない
- `env.*`: `mpirun`直前のsupervisor environmentをUTF-8平文で投影する
- rank固有environmentは収集しない。rank/node情報はplacement、scheduler、hardwareが所有する

raw snapshotの名前と値はbyte-exactに取得する。factのnameは`[A-Za-z0-9_]`だけをそのまま使い、
それ以外は`~HH`の大文字hexでescapeする。valueはUTF-8を検証してエンコードせず保存する。これにより通常文字列の
曖昧性を作らない。rank deltaは追加・変更値と削除nameを持ち、commonとの和がfull snapshotに
一致しなければならない。snapshot間で同じ値が重複してもscopeが異なる独立観測である。標準の
二run差分はGit管理された比較関連keyだけを表示し、全env差分は別viewでdecodeして提供する。

## 実験データの独立性

一回のjobを一つのrun IDで記録し、各runは他のrunから独立した実験データとして扱う。
block、実行順、replicate index、pair ID、group/set ID、planned attempt、stopping ruleなど、
反復・ペア実行を管理するfield、metric key、manifest fieldは作らない。

OpenFOAMの実際のsource、workload、個別実行設定、配置、結果、時刻、artifact identityは各run自身が記録する。
複数runの比較や統計が必要な場合は、保存済みの個別keyを利用者がその都度選んでqueryする。
事前grouping、pairing、fingerprint、attempted count、median/MADなどの反復統計をv2の標準viewやSheetsへ持たせない。


## OpenFOAMで保存する原始事実

### run、stage、allocation

- `run.started_at`、`run.finished_at`、`run.elapsed_sec`
- `run.exit_code`。`run_outcome`は0=`succeeded`、非0=`failed`、欠損=`NULL`としてviewで一度導出する
- `run.stage.<name>.launch`: `StageRunner`がspawnしたprofiler/mpirunを含むexact outer `argv`、`cwd`、
  `stderr_mode`のcanonical JSON object。solver専用のargv subset keyは作らない
- 各`perf.stage.<name>.wall_time_sec`と`run.stage.<name>.termination`。terminationはexit、signal、
  spawn errorを区別するJSON objectで、shellの`128+signal`へ潰さない
- `perf.pipeline.wall_time_sec`: bench/profileでblockMesh spawn直前からsolver wait直後まで。mesh audit、hash、archiveを含めない
- `scheduler.request`: runner submit boundaryの個別実行設定、PJM script identity、exact `pjsub` argv
- `scheduler.accounting`: 固定した`pjstat --history -S --choose ... --data --delimiter "\t"`の結果
- regular runだけ、submission resultの`scheduler.submit_job_id`とjob-entryの
  `scheduler.job_entry_job_id`を別sourceのscalar indexとして保存し、equalityはviewで導出する。binding booleanは作らない
- minimal hardwareはrunごとに各allocated nodeで
  `LC_ALL=C lscpu --json`とcontract列挙のproc/sysfs settingを読む。raw node artifactはlscpu JSON/settingsだけ、
  `openfoam_minimal_hardware_raw_v2`はCPU identity、hostname、kernel、CPU sets、memory/hugepage、NUMA balancing、
  boost、cpufreq policyをsubject/node grainで持つ。各consensusはview派生で、child Factへ複写しない
- profileだけ、minimal hardwareに含まれないNUMA配置とpost-run memoryのraw artifactを追加する。
  これを第二のcompound raw factへまとめず、publisherのsource-linked projectionからconsumer列を作る。benchではNULL

run lifecycleはPJM entryからcompute回収終了までとする。started/finishedはUTC wall clock、elapsedは同じsupervisor境界の
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

raw tableはartifact到達とrun自身の再現に必要なcommit、manifest identity、artifact URIだけを
索引化する。archive hashはbuild時に一度計算し、各benchmark runで再計算しない。
build scriptがarchiveとhash付きsidecarを書き終えて成功した後だけcacheへ公開する。consumerはsidecar存在と
archive hash一致の組だけをreuseし、任意のcrash境界から二fileを復旧するtransactionは作らない。
Publisherはbuild sidecarとrole付きtoolchain rawをbuild-grain `openfoam_build_provenance_raw_v2`、runのprovision
validationを`openfoam_build_provisions_raw_v2`へ一度だけ投影する。Runsのprecision/build artifact/compiler/MPIは
前者をbuild manifest SHA-256で、実resolved executable/libmpiは後者をrun IDでjoinし、scalar Factへ再掲しない。

### MPI通信計測

bench/profileのsolver本処理が成功した場合に限り、同じallocation、MPI process数、transport環境を維持したまま
`network_imb_mpi1` stageを本処理後に一度実行する。cluster固有launcherは後続のジョブ組込みが完全なargvを組み立て、
共通capture runnerはそのargvを変更せず起動する。初版のIMB subcommandは次に固定する。

```text
IMB-MPI1 -npmin <solverと同じMPI process数> -msglog 0:22 -iter 1000 -time 1 \
  -iter_policy dynamic PingPong Sendrecv Allreduce
```

0 byteおよび1 byteから4 MiBまでの2冪を対象とし、IMB stdout/stderr、完全なargvを
`source/network/imb-mpi1/`へ保存する。parserは保存済みtextだけを入力とするpure functionで、警告を無視しつつ、
completeなPingPong、Sendrecv、Allreduce sectionからIMB自身が出したprocess count、message size、iterations、
time、bandwidthだけを復元する。独自平均、単位換算による別帯域、代表値、最大値をraw metricへ追加しない。

固定幅factsは`network.imb_mpi1.*`の実行設定と`software.imb_mpi1.version`、stage termination/wall timeだけである。
可変長結果は`mpi_network_results_v2`へ
`(run_id,benchmark,process_count,message_bytes)` grainで投影し、columnsは
`run_id,benchmark,process_count,message_bytes,iterations,time_min_us,time_avg_us,time_max_us,
bandwidth_mbytes_per_sec,source_member`とする。benchmarkに存在しないtime列またはAllreduceのbandwidthはNULLにする。

solverが失敗したrunではstageを起動しない。通信stageの非zero exit、signal、spawn error、timeout、truncated/parse不能出力は
solver成功を覆さないが、terminationを保存してrunの`collection_complete=false`とする。不完全sourceから結果rowは作らず、
retryしない。solver wall timeと既存`perf.pipeline.wall_time_sec`は通信時間を含めず、PJM entryから回収終了までの
`run.elapsed_sec`だけが通信時間を含む。
ASPIRE 2A/2A+、Gadi、玄界のlauncher、module、host mapping、Singularity、walltime、PJM/PBS/workflow編集は後続作業とする。

### actual workload

solverが読む実caseについて、exact 7 memberをsetup後・`blockMesh`前に`source/workload/`へcopyし、同じbytesから
manifestを作る。各runが自身のsolver caseを一度所有する。Publisherはmanifest rowとmemberのexact content bytesを別projectionへ転記するため、Sheet/agentはhashだけで
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

1 nodeはPJM supervisorが`<provision>/bin/capture-hardware --mode minimal --subject-kind regular_run
--subject-id <run> --output-root <run>/source/hardware --node-ordinal 0`を実行する。multi-node設定はtimed solver外で
一度だけ、検査済みabsolute `mpirun -np <protocol.nodes> -ppn 1`の後ろへ同prefixと`--node-ordinal-from-env PMI_RANK`を置く。
各設定のcanary自身で`PMI_RANK`の存在と期待連続集合を確認できたrunだけをconformance eligibleにし、probeは代替rank
sourceを探索しない。各processはshared runtimeの
`source/hardware/node-<node-ordinal>.json`へ書き、identityとplatform settingsを含むfull `hardware-node/v1`を持つ。
`commands`はargv/exit_code/stderr、`lscpu`はstdoutからparseしたraw JSON objectである。さらにkernel release、
CPU/node online/isolated/nohz_full、memory total/hugepage、NUMA balancing、boost、cpufreq policy別driver/governor/
min/maxを同じ軽量probeへ入れる。post-runでordinal、hostname、
expected node数を照合する。別daemonや常駐collectorは置かない。

profile post-runもtimed solver外で同じone-shot形を使い、
`<resolved-mpirun> -np <protocol.nodes> -ppn 1 <provision>/bin/capture-hardware --mode profile-postrun
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
solver終了後に一caseへ一回実行し、
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
大容量mesh scan、`checkMesh`、partition hashはsolver終了後に一回実施し、
scored solverのcacheを乱さない。generated `decomposeParDict`と各stage logはartifactへ残す。

初版は同じrun内のinline post-run scanだけを実装する。standalone audit jobはmanifest、CLI、join契約を
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
`/proc/self/status`の`Mems_allowed_list`を記録してから`exec icoFoam`する。各設定のcanary自身でrank envの存在と
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
- requested、allocated、solver Hosts、placement hostsがprotocolの個別設定と一致
- DP、許可されたworkload、`floatTransfer=false`
- build provenance、required collector、artifactがcomplete
- score runはdirect modeで、比較run同士のinstrumentation modeが一致

`run_purpose`は各run自身の用途として保存するが、group/set IDは作らない。
`score_comparison_eligible`は`run_purpose=bench`と通常のresult/source/placement gateだけから導出し、
profileは公式FVOPSを算出・表示してもscore stats、best、rankingへ入れない。

MPI teardown後の非zero exitでもsolver workloadがofficial validになり得る。原始結果は必ず
収集し、official validityとrun outcomeを混同しない。`official_log_valid=true`でもscoreを算出不能なら
scoreはNULLにする。field別原因分類はしない。

## 個別実行設定と計測擾乱

D-003は「収集系を初版からmulti-node対応にし、Genkai 1/2/4 nodeを実機conformance対象にする」で確定した。
node数やrank数をcollectorへhard-codeせず、protocolが`nodes`、`ranks`、`resource_group`、`transport_policy`を
独立fieldとして一度所有する。required producerはcontractのvariant applicability、
instrumentation modeはprotocol/bundle selectionだけが所有する。runnerはこれらの個別fieldから
expected node ordinal/rank集合とexact `pjsub`/`mpirun` argvを展開し、PJM script identityとともにmanifestへsealする。
初版canaryは総rank数を120に固定したbalanced配置
`n1-r120`（120 rank/node、`I_MPI_FABRICS=shm`）、`n2-r120`（60 rank/node、`I_MPI_FABRICS=shm:ofi`）、
`n4-r120`（30 rank/node、`I_MPI_FABRICS=shm:ofi`）を使う。いずれも`a-batch`、Scotch 120 subdomainで、launcherは
`mpirun -np 120 -ppn <120/nodes>`へ固定する。1-nodeは現行64M workloadで実証済み、2-nodeは旧workloadで基盤だけ実証済み、
4-nodeは未実証なので、後二者に性能期待値を仮置きせず各一回の通常canaryで取得成否を確認する。失敗時の自動retryや
代替設定は作らない。canary後のrank sweepは同じschemaで個別値を変え、既存runを上書きしない。
実行設定を束ねるID/object/専用manifestは作らない。各runで次を照合する。

```text
protocol.nodes == requested nodes == allocated nodes
               == distinct solver hosts == distinct placement hosts
protocol.ranks == requested ranks == solver nProcs == placement record count
```

rank ID、header nProcs、Hosts合計、placement件数、hostごとのrank数=`ranks/nodes`も一致させる。multi-node設定で
`I_MPI_FABRICS=shm`のようなnode内限定transportを拒否する。

scored solver直前にはBigQuery通信、profiler、MPI debug、`checkMesh`、大容量hashを実行しない。
同一runに必須なのはrank、hostname、local rank、affinityとenvironment deltaの最小recordだけで、
各rank wrapperが自分専用のsidecarへ一度書いてからsolverをexecする。collector daemonやdurable ACKは
使わない。full topology dumpやverbose diagnosticsはaudit modeへ分ける。最小probeの影響はcollector実装中に
計測なし／ありで一時確認し、結果を破棄する。通常runのeligibilityや反復管理情報にはしない。

`instrumentation_bundle_hash`は、score pathで有効なhook、probe、rank別source schema、sample interval、sink、
buffer、wrapper executable hash、observation contract version、env capture scope、source path allowlistを
列挙したcanonical manifestのcontent hashである。`lightweight`等の
labelだけでは同一視しない。collector実装中に一度だけ非擾乱を確認し、確認後は通常benchで同じbundleを使う。
このhashはpurpose/arm/run ID/absolute runtime rootを含まないsemantic identityで、sinkとargvはrelative templateにする。
開発時確認の出力は保存せず、通常benchはcontractで選んだbundleを使う。実argv/sinkは各run sourceで観測する。

## bench/profile trackの分離

永続化するrun purposeは`bench`と`profile`だけである。

- `bench`: scoreと環境比較。profiler、polling、verbose traceを含めない。
- `profile`: score比較から分離し、perf counter、追加hardware、verbose diagnosticsを持つ。

contractのproducerは`applicable_run_variants=["bench","profile"]`のsubsetだけを持つ。
profile-only sourceはbenchで起動せず、固定幅consumerは理由なしのNULLを返す。
開発時の非擾乱確認はrun variantではなく、出力を保存しない一時的な確認作業である。

benchはscore reference、profileはprofile baseをsource trackに使う。全runでclean checkout、
remote reachable、build sidecar、control-plane blobを通常のprovenance規則で検証する。
## BigQuery viewとスプレッドシート

BigQueryにはbench/profileのrun、source、artifact projectionだけを公開する。開発時の非擾乱確認や
その判定を表すtable/viewは作らない。

主なlogical relationは次である。

| relation | grain | role |
|---|---|---|
| `openfoam_run_facts_v2` | `(run_id)` | Runsの固定幅consumer |
| `openfoam_run_points_v2` | `(run_id,estimand_id)` | benchの比較点 |
| `openfoam_rank_placements_v2` | `(run_id,global_rank)` | rank配置 |
| `openfoam_perf_counters_v2` | `(run_id,global_rank,event_name)` | profile-only counter |
| `mpi_network_results_v2` | `(run_id,benchmark,process_count,message_bytes)` | IMBのmessage size別実効MPI通信結果 |
| source/build/workload/hardware relations | source固有grain | lineageと詳細値 |

`openfoam_run_facts_v2`は少なくとも次の列群を持つ。

| group | columns |
|---|---|
| identity | `run_id`、purpose、instrumentation identity、開始終了時刻。反復・ペア管理情報とcontract/protocol ID・hashは持たない |
| execution configuration | `nodes`、`ranks`、`resource_group`、`transport_policy`を独立列 |
| quality | `collection_complete`、`official_log_valid`、`score_comparison_eligible` |
| topology | requested/allocated/observed node・rank数、effective transport/file handler、affinity signature |
| workload/build | workload identity、precision、build/MPI identity |
| outcome | FVOPS、trim、solver/stage/pipeline wall time |
| hardware | CPU/kernel/memory/settings consensusとprofile-only列 |

Connected Sheetsの既存tab設計は維持する。通信結果の表は全実装完了後に設計し、現段階では
`mpi_network_results_v2`を将来の`MPI Network` tabの入力候補とすることだけを固定する。JSON展開やsummary列は要求しない。
固定幅source欠損はNULL、long relationは実在rowだけを返す。
## 開発時の非擾乱確認

experiment-metrics-v2の実装中に、計測なし／ありを同条件で実行し、FVOPSとsolver outer wallが
実用上遅くなっていないことを確認する。この比較は開発作業の一時チェックであり、確認後は出力を破棄する。

v2には専用run purpose、OFF/ON arm、allocation、pair、manifest、artifact、Fact、metric key、
BigQuery relation、Sheets tab、eligibility、Git管理decision recordを作らない。通常benchは確認済みの
instrumentation bundleを直接使用し、開発時チェックの結果をrunへjoinしない。
## 決定事項と再open条件

D-003は2026-08-09にユーザー回答「基本的にはマルチノード対応型の収集」で確定した。質問はGenkai 1 nodeだけを
初版canaryにするか、1/2/4 nodeをv2対象にするか、推奨は前者、採用回答は後者である。2026-08-10の追加回答により、
実行設定を束ねる抽象は不採用とし、各値をprotocolの独立fieldおよびSheetsの独立列として扱う。affected fields/viewsは
protocolの個別実行設定、scheduler request、producer node/rank axes、placement/host consensus、profile rank source、
score eligibilityである。reopen triggerは対象clusterのnode modelまたはscheduler/MPI placement意味が変わり、
同じ個別fieldでnode/rank集合を表せなくなった時だけとする。

実装上は1/2/4 nodeで同じcollector graphを使い、node/rank数をprotocolの個別fieldから展開する。未実証2/4-nodeの値を
成功扱いせず、通常canaryの実観測をそのまま保存する。専用collector、fallback discovery、再投入枠は追加しない。

非擾乱確認はcollector実装中にだけ行い、完了後は結果を保存しない。

## 決定状態

| 状態 | 決定 |
|---|---|
| 確定 | raw relationは`run/key/value`の三列、compound valueはcanonical JSON |
| 確定 | 定義した各process scopeの環境変数は機密値を含めfilterせずbyte-exactに全件保存 |
| 確定 | native object/structured sourceを優先し、log regexはfixture付きの最終手段 |
| 確定 | compute側はlocal raw fileだけ、finalize/publishはrunner、Artifact upload/home移管はworkflowが担当 |
| 確定 | complete recordのsubsetであるfirst/last/count/average等をrawへ重複保存しない |
| 確定 | bench/profileを分離し、取得できなかった値とprofile専用familyは値だけNULL、原因/status/欠損用recordなしとする。run-level statusは`collection_complete`だけ |
| 確定 | 実験用途として多段retry、fallback source、field別reason registryを作らない |
| 確定 | artifact移管は現行OpenFOAMのGitHub Artifact -> Tailscale/SSH -> home RAIDを基準とし、Qwenへも同じ経路を移植する |
| 確定 | home artifactは自動expireせず、容量が実際に問題になった時だけ手動整理する。専用quarantineは作らない |
| 確定 | D-003: collectorはmulti-node対応とし、Genkai 1/2/4 nodeを初版実機conformance対象にする。nodes/ranks/resource/transportは独立field・独立列とし、設定を束ねるID/object/manifestは作らない |
| 確定 | 非擾乱確認はcollector実装中にだけ行い、結果・専用run・metric・artifact・decision recordを保存しない |

## 実装ハンドオフ

公開面はbench/profileの通常runだけを扱う。

```python
Fact(key: str, logical_value: LogicalValue)
init_run(settings_path, runtime_root, identities) -> RunManifestPath
Recorder.open(manifest_path, registry_path, producer_id, runtime_dir)
collect_once(manifest_path, runtime_dir, producer_id, probe) -> Path
submit_run(manifest_path, runtime_dir, execution_fields, pjsub_argv) -> SubmissionOutcome
run_stage(stage_name, argv, *, cwd, stderr_mode, recorder) -> Termination
capture_network_stage(stage_name, argv, *, cwd, artifact_dir, recorder) -> Termination
finalize_run(manifest_path, runtime_dir) -> FinalizeOutcome
publish_run(manifest_path, artifact_set_path, destination) -> PublishOutcome
```

CLIのpurposeは`bench|profile`だけとし、非擾乱確認を通常runとして表すoption/subcommandを
追加しない。owner scopeはrun/build、source storageはfact fragment/run bundle/profile rawだけである。

runtime layoutは`runs/<run-id>/`の下に`control/`、`domain/`、`source/`、`logs/`、
`profile/raw/`、`archive-staging/`を持つ。artifact setは`run-artifacts.tar.zst`、
`metrics.jsonl`、profileだけの`profile-raw.tar.zst`、`artifact-manifest.json`で閉じる。
開発時の非擾乱確認用fileやdirectoryはこのlayoutへ入れない。

network rawは`source/network/imb-mpi1/`の下にargv/stdout/stderrを置く。

test gateはmanifest、submission/job ID、environment、merge、artifact、OpenFOAM意味、profile、再構築に加え、
IMBの0 byte、科学表記、欠損列、複数process-count section、警告混在、truncated outputをbench/profile fixtureで検証する。
raw artifactから同じ`mpi_network_results_v2` row集合を再構築できること、失敗・timeout・部分出力では0 rowかつ
terminationと`collection_complete=false`だけになることも検証する。catalog/schema testはnetwork namespaceに
`lane`、`qualification*`、`block_id`、`block_order`、`replicate_index`、`pair_id`、`ib_*_bw`、`ib_*_lat`、
contract/protocol ID・hashがないことを保証する。Connected Sheetsの詳細testは表設計時へ延期する。非擾乱確認は実装者がその場で
実行・確認し、fixture、golden decision、publish対象にはしない。
### release単位

移行はkeyごとに二重化せず、v2 run単位で行う。

1. legacyの出力、shell evaluator、baseline logをgolden fixtureとして凍結する。
2. pre-submit manifest、local metrics export、OpenFOAM native probe、complete solver record、Pstream/placement
   sidecarを一つのv2 fixtureと最初のv2 runで通す。
3. benchへ必要な最小subsetだけを、collector実装時に代表設定`nodes=1, ranks=120`で計測なし／あり比較へ掛ける。
   意味・数値同等性・非擾乱をその場で確認したら結果を破棄し、確認済みcollectorをbenchへ追加する。
4. v2 viewとSheetを切り替え、legacy-only consumerがゼロになってから旧senderとsubset keyを削除する。

rollbackは実行設定と実装を直前版へ戻して新しいrunを投入する。既存runのmanifestやrowを
書き換えず、一run内でlegacy producerとv2 producerを混在させない。

## 実装順序

1. 現行key、producer、consumer、artifact保存先をinventory化し、key registryとexpected producer graphを作る。
2. clean checkout、remote到達性、build sidecar manifest、manual provenance gateを作る。
3. BigQuery credentialをrunnerだけへ移したうえで、現行metric集合のまま`Fact`、`Recorder`、
   JSONL export、runner merge/publish、workflow artifact upload/home移管を導入する。
4. ingestion-time partition/`run,key` clusterのraw table、distinct/singleton/conflict、Sources lineage、
   archive attempt/status、run/point view、二run table
   functionをkey catalogから生成しfixtureを通す。
5. cavity3Dのactual workload manifest、complete solver record、mesh、provenanceをlegacy collectorと並行追加する。意味が
   変わる既存keyをv2で再利用しない。
6. canonical official evaluatorを作り、旧shell validityと全baseline golden logを照合する。
7. D-003で確定した個別実行設定、同一rank wrapper sidecar、二段階Pstream/partition auditを追加する。
   collector実装中は代表設定で計測なし／ありを同一mesh/partition/rankにして比較し、pressure
   residual/iteration軌跡と公式markersのlexeme一致、性能非劣化を確認したら結果を破棄する。
8. 共通network capture、IMB pure parser、固定幅factsと`mpi_network_results_v2` projectionを実装し、raw artifactからの
   round-tripと失敗時0-row規則をfixtureで通す。cluster固有ジョブへの組込みは行わない。
9. Connected SheetsのRuns/Sources/Config Diff/Environment/Rank Placement/Profile Counters/Data Statusをbounded consumerへ
   切り替え、freshness/result-size smoke testを通す。旧key consumerがなくなってから派生・部分集合keyの
   新規生成を止める。
10. homeのrun artifact tree、Git管理source/SQLから
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
- D-003で確定した各設定値でrequested、allocated、solver Hosts、placementが一致する。
- setup後の実case workload memberがprotocol manifestと一致し、1 byte差をcomparison不適格にできる。
- bench/profileが分離され、profile-only列はbenchで理由なしのNULLになる。collector実装中の一時比較で
  bench bundleによる実用上の性能低下がないことを確認し、その比較結果は保存されない。
- unmodified OFFとexact final ONの同一条件でpressure solve軌跡と公式markersが一致し、数値結果を
  hookが変えていない。
- 各runが他runのblock/order/pair/groupに依存せず、単独でsource、設定、結果、artifactを復元できる。
- 各run/Sources/Sheet列がmetric keyまたはGit/artifact dimensionへ一意に遡れ、cast失敗や異値競合を
  aggregateが隠さない。
- 二run diffがcell parameter付きtable functionで計算され、NULL/同一/不存在runを拒否し、全run pairを
  materializeせず、full envをparameterなしでSheetへextractしない。
- config definition/policy非互換または片側env snapshot欠損では、左右値/equalityをNULLにする。
- Data Statusが各objectのquery時刻、最新publish、未移管Artifact数、archive job最終成功時刻、home空き容量、
  SQL revision、conflict/run-level collection incomplete件数を表示し、
  scheduled refreshのowner変更・停止とresult-size超過をsmoke testで検出できる。
- Sheets利用者がJSON展開なしでcommit、妥当性、一次結果、artifactへ到達できる。
- completeなIMB rawからmessage size別rowをlosslessに再構築でき、通信stage失敗がsolver成功を変更しない。
