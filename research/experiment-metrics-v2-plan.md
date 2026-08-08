# 実験メトリクス再設計計画

## 目的

メトリクスは、ログやGitを置き換えるための記録ではない。次の四つの問いに、
BigQueryとスプレッドシートから短く答えるための索引である。

1. どのGit管理下の条件で実行したか。
2. Gitの外で、実行時にどの条件が選ばれたか。
3. 計算は妥当で、どれだけ速かったか。
4. 比較不能または要調査と判断すべき欠損がないか。

変更内容と変更理由の正本はGit、実行の詳細の正本はログ、run間比較の正本は
BigQuery viewとする。この責務を混ぜない。

## 正本

| 情報 | 正本 | メトリクスの役割 |
|---|---|---|
| script、設定、patch | 実行repositoryのcommit | repositoryとcommitを指す |
| 仮説、変更理由、期待する効果 | commit messageのbody | 保存しない |
| OpenFOAM、ThirdPartyの変更 | 各source repositoryのcommit | build provenanceからcommitを指す |
| stdout、stderr、solver出力 | run artifactのlog | 比較に必要な観測値だけを索引化する |
| 実行時の環境変数 | 計算processから取得した値 | Gitから復元できないため全件保存する |
| build済みbinary/archive | immutable artifact | build commitと必要ならcontent hashを指す |
| score、speedup、平均、順位 | BigQuery view | raw tableへ保存しない |

Git管理された通常ファイルには、個別のSHA-256メトリクスを付けない。commitとpathで
内容が一意になるためである。hashは、Git外のbinaryの同一性や転送後の冪等性を
保証する場合に限定する。

## Gitによる実験条件の管理

- 性能、計算量、配置、build、collectorの挙動を変える変更は、job投入前にcommitする。
- benchmarkはcleanなtreeからだけ投入する。dirty treeを説明するためのdiff metricは
  作らない。
- 一つのcommitは一つの説明可能な変更単位にする。複数ファイルの変更が一つの仮説を
  実現するなら、同じcommitでよい。
- subjectは変更の要約、空行後のbodyは変更理由、仮説、予想する影響、確認方法を書く。
- 同じ条件の反復測定ではcommitを増やさない。同じcommitから複数runを作る。
- workflow dispatch inputはbuildの強制など運用上の選択だけに使う。性能条件を可変inputへ
  逃がさず、scriptまたは設定としてcommitする。
- 過去のbuild artifactを再利用した場合、現在の実行commitとは別に、そのartifactを
  作った実行repository、OpenFOAM source、ThirdParty sourceのcommitを記録する。

commit messageの形は次を基準とする。

```text
Select the Scotch decomposition backend

The previous decomposition produced a large cell imbalance. Use Scotch because
the hypothesis is that lower partition imbalance reduces the steady-state PCG
time enough to exceed the measured run-to-run noise. Verify the generated
partition sizes and compare repeated FVOPS_trim values against the parent commit.
```

この文章を`experiment.hypothesis`や`run.note`として複製しない。runからcommitへ
たどればよい。

## 保存形式

raw tableは現在の三列を維持する。

```text
run    STRING NOT NULL
key    STRING NOT NULL
value  STRING NOT NULL
```

値が自然に一つのscalarならそのscalarを文字列化する。順序付きの複数値は、添字付きkeyへ
分解せずcompact canonical JSONの一つのvalueにする。Pythonの`str(list)`は使わない。

collectorはBigQueryへ送る同じrowを、先にrun artifact内の`metrics.jsonl`へappendする。
BigQuery送信失敗時はこのfileから再送する。別のevent envelope、別schemaのspool、
型別value列は作らない。

```text
collect
  -> metrics.jsonlへappend
  -> 同じrun/key/valueをBigQueryへ送信
  -> logとmetrics.jsonlをrun artifactとして保存
```

複数nodeで収集する場合はnodeごとの一時JSONLを作り、終了時に一つへmergeする。
keyにnode番号を含め、同じ`(run, key)`を複数producerが所有しない。

## 重複を避ける規則

候補メトリクスAが次のいずれかなら保存しない。

1. Git commitとpathだけから復元できる。
2. 既存メトリクスBだけから決定的に計算できる。
3. 同じsource、scope、取得時点で、Aの集合がBの完全な部分集合である。
4. raw logの診断にしか使わず、runの選別、比較、group化には使わない。

該当する値はBigQuery viewで導出する。完全な集合と、その一部を検索しやすくするための
抜粋をraw tableへ同時に置かない。

ただし、見た目が似ていても意味が異なる値は残す。

- requested node数とschedulerが報告したallocated node数
- Gitで指定したcommandとsolver logが報告したactual rank/host配置
- job全体のwall timeとicoFoamのExecutionTime
- 現在の実行commitと、再利用binaryを作ったbuild commit

この判定をcollector単位でも行う。例えば全環境変数を保存する`environment` collectorが
あれば、`GITHUB_SHA`、`WM_*`、`I_MPI_*`を別collectorで別名保存しない。

## OpenFOAMで保存する最小の事実

### 実行と外部条件

- `run.started_at`
- `run.elapsed_sec`
- `run.exit_code`
- `run.command`
- `env.*`: job processの全環境変数
- `scheduler.*`: PJM終了後に得るactual accounting
- `hardware.node.<rank>.*`: 環境変数から分からないCPU、NUMA、memory、hostname、
  cpuset、frequency/governor、huge page状態
- `artifact.openfoam.*`: build commit、OpenFOAM commit、ThirdParty commit、archive ID、
  binary archiveのcontent hash

`run.finished_at`は`started_at + elapsed`で必要十分ならviewで導出する。
`run.outcome`はexit codeとscheduler stateからviewで導出する。

### 計算時間

- `perf.stage.block_mesh.wall_time_sec`
- `perf.stage.decompose_par.wall_time_sec`
- `perf.stage.ico_foam.wall_time_sec`

stageの合計を別metricとして保存しない。job全体の時間はstage外の処理を含むため、
`scheduler.elapsed_sec`とは意味が異なる。

### 競技結果の原始観測値

- `mesh.cell_count`
- `solver.execution_time_sec`: 5個のcumulative ExecutionTimeを一つのJSON配列で保存
- `solver.pressure_iterations`: 10回のiteration数を一つのJSON配列で保存
- `solver.end_count`
- `solver.nan_or_inf_count`
- `solver.rank_count`
- `solver.host_rank_counts`: hostごとのrank数を一つのJSON objectで保存
- `parallel.rank_placement`: host、rank、CPU affinity、NUMA nodeの対応を一つのJSON配列で保存

次はraw tableへ保存せずviewで計算する。

- step count、pressure solve count
- trim time、seconds per step、`FVOPS_trim`
- validityとinvalid reason
- node count、host rank合計、rank per node
- baseline差、speedup、反復runのmedian、MAD、CV

配列全体を保存した上で、そのfirst、last、count、meanを別keyへ複製しない。

### Git外で変わり得る実効値

OpenFOAM辞書をjob中に生成する場合、そのfile自体をartifact logへ残す。BigQueryには、
commitと環境変数から一意に復元できない実効値だけを置く。Git管理された
`controlDict`、`fvSolution`、`fvSchemes`の個別値やhashは保存しない。

MPIやOpenFOAMが自動選択したtransport、binding、Pstream設定がlogに明示され、
Gitと環境変数だけから一意に決まらない場合は、actual値として保存する。requested値の
別名は作らない。

## BigQuery viewとスプレッドシート

raw tableは事実だけを持つ。workload別viewが次を行う。

1. `env.GITHUB_REPOSITORY`と`env.GITHUB_SHA`からcommit URLを作る。
2. JSON配列からstep数、first/last、trim timeを求める。
3. cell数、step数、iteration列、終了状態からvalidityを求める。
4. valid runだけについて`FVOPS_trim`を求める。
5. 実行commit、build artifact、node数など同じ比較条件で反復runをgroup化する。
6. bestとは別にcount、median、MAD、CVを表示する。

commit messageはmetricへコピーしない。人間はcommit URL、エージェントは`git show`から
変更と仮説を読む。

## 実装順序

1. benchmark jobがclean treeから投入されることを確認するgateを追加する。
2. OpenFOAM build manifestへ実行repository、OpenFOAM、ThirdPartyの正確なcommitと
   archive content hashを記録する。
3. senderを`metrics.jsonl`への先行appendと再送に対応させる。
4. collector間のkey集合が交差しないことをtestする。
5. motorBike用result collectorを削除し、cavity3Dの原始観測値へ置き換える。
6. 使用されていないcase、mesh、result、artifact呼び出しを現行workflowに合わせて
   削除または接続し、collectorとworkflowの契約を一つにする。
7. raw tableに保存中の派生値、Git管理値のhash、環境変数の別名を廃止する。
8. OpenFOAM比較viewを作り、公式`parse_result.sh`と同じscoreとvalidityになることを
   golden logで確認する。
9. 同一commitを複数回実行し、反復runが一つの比較groupになることを確認する。
10. BigQuery送信を意図的に失敗させ、保存したJSONLから同じrowを再送できることを
    確認する。

## 完了条件

- 性能に影響する変更がすべてcommitされ、benchmark runがcommitを指している。
- commit bodyだけを読めば、変更理由と仮説が分かる。
- Git外のbuild artifactはsource/build commitと必要なcontent hashで一意になる。
- full logと`metrics.jsonl`が成功・失敗runの両方で保存される。
- collectorが所有するkey集合に重複がない。
- raw metricから別のraw metricだけで導出できる値が残っていない。
- 必須keyの欠損をviewで検出でき、空値とrun失敗を混同しない。
- viewのscoreとvalidityが公式parserに一致する。
- 同じcommitの反復と異なるcommitの変更がSheets上で明確に対照できる。
