# 実験メトリクス再設計計画（旧merge/projection設計資料）

> この文書は当初計画の履歴資料である。実装済みの送信keyと非収集項目は
> `research/experiment-metrics-v2-key-catalog.md` を正本とする。
> 本文のcavity3D・FVOPS・5ステップ評価は旧課題の履歴であり、現行scoreではない。現行のoccDrivAerStaticMeshは平均wall-clock秒/stepで評価する。[現行ルール対応表](official-rules.md)を参照。

## 目的

メトリクスは、Gitやログを複製する保管庫ではない。BigQueryやスプレッドシートから
次の問いへ簡潔に答えるための索引である。

1. どのGit管理下の条件で実行したか。
2. Git管理外で、実行時にどの条件が選ばれたか。
3. 計算は公式規則上妥当で、科学的な比較にも耐えうるか。
4. 何を一次指標として、どれだけ高速であったか。
5. 比較不能または要調査と判断すべき欠損や競合がないか。

変更内容と変更理由の正本はGit、実行詳細の正本はrun artifact、raw factの索引は
BigQuery、比較規則の正本はGit管理下のSQLおよびテストとする。BigQuery viewはその
デプロイ済み実体であり、暗黙の手編集は行わない。

本プロジェクトは実験用途であり、ミッションクリティカルな高信頼送達システムではない。正常終了するrunで取得対象が最初から
未実装である事態は許容しないが、ごく稀に生じるcollector、ノード、転送の障害を救済するための多段リトライ、フォールバックソース、
フィールド別reasonレジストリ、永続ジャーナルは設けない。値のソース、取得時点、スキーマは厳格に定義する一方、取得できなかった
値はコンシューマ側で`NULL`とし、run全体は単一の`collection_complete=false`フラグで十分とする。失敗したrunは保存できたログを残し、
必要に応じて人間が再実行する。この単純な障害モデル（simple failure model）は、以降の節にある個別の旧reason表現より優先する。
厳密さは実装時のコントラクトテストに寄せ、実行時は各ソースを一度取得しターミナル終了後に一度ファイナライズするのみとする。
同一の値を複数のバリデータで囲い込むようなランタイムセーフガードは追加しない。

## 正本とidentity

| 情報 | 正本 | raw metricの役割 |
|---|---|---|
| スクリプト、設定、パッチ | 実行リポジトリのcommit | リポジトリとfull commitを指す |
| 仮説、変更理由、期待する効果 | commit messageのbody | 保存しない |
| OpenFOAM、ThirdPartyソース | 各ソースリポジトリのcommit | ビルドプロベナンスを索引化する |
| stdout、stderr、ソルバー出力 | run artifactのログ | 比較に必要な原始観測のみを索引化する |
| 実行時の環境変数 | スコープごとのbyte-exactスナップショット | 全件保存する |
| ビルド済みバイナリ/アーカイブ | 不変のartifact | オリジナルのビルドとコンテンツidentityを指す |
| スコア、高速化率、中央値、順位 | Git管理されたview SQL | raw tableへは保存しない |

次の3点を混同してはならない。

- source identity: リポジトリURLと解決済みのfull commit
- binary identity: artifact IDとビルド時に一度計算するコンテンツハッシュ
- reproducibility: ツールチェーン、依存関係、ビルド環境、全ソースcommitを含むマニフェスト

Git管理下の通常ファイルには個別のSHA-256メトリクスを付与しない。commitとパスによって内容が一意に
確定するためである。ハッシュ値の算出はGit管理外artifactの同一性検証、バイナリ転送、マニフェストの冪等性確認に
限定し、スコア計測対象ソルバーの実行直前には大容量ファイルのハッシュ計算を行わない。

## Gitによる実験条件の管理

- 性能、計算量、プロセス配置、ビルド、collectorの挙動に影響を与える変更は、ジョブ投入前に必ずcommitする。
- GitHub Actionsでのチェックアウト直後、プロビジョニング前にクリーンなワーキングツリーとfull commitを検証する。
- ベンチマークに使用するcommitはリモートから到達可能であるか、永続アーカイブに保存済みでなければ
  ならない。プロベナンスの追跡できない手動runは投入しない。
- 1つのcommitは1つの説明可能な変更単位とする。複数のファイルが同一の仮説を実現する場合は
  同一commitとしてよい。
- コミットメッセージのsubjectは変更の要約とし、空行を挟んだbodyに変更理由、仮説、期待される影響、検証方法を記述する。
- 同一条件での反復測定ではcommitを増やさず、同一commitから複数のrunを生成する。
- 性能条件をworkflow dispatchのinputへ逃がさず、Git追跡下のスクリプトまたは設定ファイルに記述する。
- 既存artifactを再利用したrunでは、現在の実行commitとは別にオリジナルビルドのcommitおよびソース
  commitを記録する。ハードリンク先の新しいrun番号をビルドidentityとしてはならない。

コミットメッセージの例を示す。

```text
Select the Scotch decomposition backend

The previous decomposition produced a large cell imbalance. Use Scotch because
the hypothesis is that lower partition imbalance reduces the steady-state PCG
time enough to exceed the measured run-to-run noise. Verify the partition and
compare repeated FVOPS_trim values against the parent commit.
```

この記述内容を`experiment.hypothesis`や`run.note`へ複製してはならない。人間およびエージェントは
runのcommitから直接読み取るものとする。

### 調査根拠

現行ファイルに加え、`0c26b1e`（BigQuery収集導入）、`56c1a2e`（コマンドの単一メトリクス化）、`8c67f1f`/`b7e69c2`
（完全出力の保持とホームアーカイブ）、`fa9d49a`（スコアからperfを除外）、`335a10d`（bench/profile分離）までの
関連commit履歴を確認した。過去のCodexスレッドで確定した「欠測値はNULLのみ」「OpenFOAM側への移管を基準」「稀な失敗は
許容」という方針は本設計書の決定事項へ要約して反映し、会話本文やコミットメッセージをrunメトリクスへ重複記録しない。

## raw relationの契約

raw tableは現在の3列構成を維持する。

```text
run    STRING NOT NULL
key    STRING NOT NULL
value  STRING NOT NULL
```

`run`は全プロデューサが共有するグローバルに一意かつ不変（immutable）なIDである。ジョブ投入前に
OSのCSPRNGから得た16バイトを32文字の小文字16進数で表す128ビットの`subject_nonce`を生成し、
`submission_subject_id=run_id`とする。`pjsub`返却後にしか判明しないPJMジョブIDはrun IDに
含めず、投入結果とjob-entryのジョブIDをクエリ時に照合して結合する。初期runマニフェストを書き換えてはならない。
run IDおよびアロケーションIDはUTF-8で`^[a-z0-9][a-z0-9._-]{0,199}$`を満たすよう生成し、安全な実行時パス
コンポーネントとしてそのまま利用する。任意のリポジトリ名やユーザー入力をエスケープなしで連結してはならない。
raw relationは次の関数従属性（functional dependency）を満たす。

```text
(run, key) -> value
```

- 完全一致する`(run, key, value)`の再送は、論理上の単一レコードとして扱う。
- 同一の`(run, key)`に異なる値（distinct value）が複数存在する場合は値を選択せず`conflicting`とみなし、そのrunを
  比較対象から除外する。
- 既存runの値を事後的に訂正してはならない。訂正を伴う測定は新規runとして記録する。
- 行の不在は未観測を表し、`value=""`は実際に観測された空文字列、`"0"`は真のゼロを表す。
- 取得不能や非該当をプレースホルダーの空文字列で表してはならない。
- collectorは正常終了時にフラグメントを閉じ、失敗時は非ゼロ終了コードで終了する。別個の収集ステータス、原因、エラーカウント、
  開始/終了の永続ジャーナルは設けない。ファイナライザは用途の適用性（purpose applicability）とバンドル選択から
  期待されるフラグメント/ファイルを1回導出し、存在確認と照合して`collection_complete`を1回導出する。回収できた
  ソースやログは不完全なrunであっても収録する。

コントラクトやプロトコルのID・ハッシュはメトリクスへ保存しない。既存keyの意味、単位、JSON構造を変更する場合は
新しいkeyを定義し、詳細な仕様はソースコードおよび文書を正本とする。

各keyまたはkeyパターンは、オーナー、論理型、単位、カーディナリティ、ソース、スコープ、
取得時点、必須/任意（required/optional）をGit管理下の単一レジストリで定義する。動的keyの
コンポーネントエスケープは単射とし、追加・マージ時にも所有権と衝突を検証する。

## scalarとcanonical JSON

本質的に単一のスカラー値であるものは、そのスカラーをSTRINGへ変換して格納する。順序や対応関係を持つ
複合値は、添字付きの複数keyへ分解せず、単一のcanonical JSON値として格納する。

canonical JSONはRFC 8785（JSON Canonicalization Scheme: JCS）に準拠する。配列の順序を保持し、
重複したオブジェクトキー、NaN、Infinityを禁止する。RFC 8785の表現可能範囲を超える整数や高精度を
必要とする十進数はJSON numberとせず、レジストリで型を規定した標準十進数文字列（canonical decimal string）とする。

スカラーエンコーダの規則も以下に固定する。

- ブール値は`true`/`false`、整数は符号付き十進最短表現とし、先頭の`+`や余分なゼロ、`-0`を許容しない。
- 浮動小数点数は有限なIEEE 754値のRFC 8785準拠シリアライズとし、NaN/Infinityを許容しない。
- タイムスタンプはUTCに正規化した`YYYY-MM-DDTHH:MM:SS[.fraction]Z`形式とし、小数秒の末尾ゼロは省略する。
- 時間の単位は秒、データ量はバイトとする。文字列はUTF-8で保持する。
- JSONの`null`は、レジストリで明義された「観測済みの複合レコード内におけるフィールド欠損」にのみ用い、
  key全体の取得失敗や非該当には用いない。

これにより、同一の論理値はプロセスやプログラミング言語に依存せず、常に同一のバイト列となる。

Pythonの`str(list)`による文字列表現は使用しない。論理型や単位はvalueの文字列から推測せず、keyレジストリを
正本とする。

## 重複を排除する規則

あるメトリクス候補Aを削除できるのは、残存するraw factおよび不変なGit/artifactのidentityのみから、
同一のセマンティクス、ソース、スコープ、取得時点、単位、精度において、Aのkeyの帰属とvalueを
常に一意かつ可逆的に復元でき、かつ比較用viewの利便性も損なわれない場合に限られる。

単に値が等しい、名前が類似している、あるいはログ中に存在するということだけを理由に削除してはならない。要求値（requested）と
実効値（effective）、計画値（planned）と観測値（observed）、スケジューラ値とソルバーヘッダー値、異なるクロックでの計測時間はそれぞれ独立した事実である。
公式プロデューサとの照合、スキーマルーティング、保存層をまたぐマニフェスト索引など、正当な理由による重複については、
レジストリの`duplication_justification`にその理由と検証式を明記する。

全環境変数の保存は、取りこぼしのないフォレンジックな比較を実現するための明示的な非最小化例外
である。個別の環境変数値を別名前空間へ重複して掲示せず、標準のスプレッドシートでは比較に必要な射影（projection）のみを表示する。

## raw metricsのエクスポートと送達

v2は任意のクラッシュ境界から1件の欠損もなく復旧・再開することを目的としない。リリース判定基準（release gate）は、成功した各run
バリアントの正常パスにおいて、コントラクトが要求する設定、性能値、rawログ、PJMアカウンティング、およびprofile runのprofile rawが
Artifactへ収録され、ファイナライザで確認できることである。失敗・中断したrunは完成済みのファイルのみを残し、不完全なレコードの部分的
復旧処理は設けない。スーパーバイザが終了後のファイナライザまで到達した失敗runは、その時点で存在する完成済みログ/ソースと
`collection_complete=false`を通常の1つのartifactセットとしてパッケージ化する。ファイナライザ到達前のクラッシュ、またはパッケージ化自体の失敗時のみ
完成artifactを作成しない。個別原因を示すフィールドは追加しない。

`metrics.jsonl`はBigQueryファクトテーブルと同一の`run/key/value`を持つrun単位のrawエクスポートである。artifactの射影は
対象artifactセットからPublisherが別リレーションへ送信する。別個のイベント
エンベロープ、型別のvalue列、ACKキューなどは設けない。

対象プログラムに組み込む薄いフックが出力するバージョン付きドメインレコードは、ローカルアダプタへの入力または
診断/ソースログであり、第二の送達キューではない。単発のfactはアダプタがレジストリに従って検証し、
メトリクスフラグメントへ書き出す。反復イベントを最終的に1つの配列へと集約する系統は、行バッファリングされたドメインJSONLへ追記し、ステージ終了時に
flushする。終了後に純粋関数的なリデューサ（pure reducer）が1回だけFactへ変換する。ごく稀なプロセス/ノード障害により末尾が欠損する
事態は許容するが、正常終了したにもかかわらず期待されるレコードが毎回欠損するような実装はリリースを認めない。レジストリはソース
JSONLとメトリクスフラグメントのどちらを正本とするかを系統ごとに固定する。

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

- 1つのJSONオブジェクトを1行で書き出し、プロデューサ終了時にflush/closeする。各行やディレクトリごとの`fsync`は
  要求せず、必要に応じて一定間隔のバッファflushを用いる。
- 期待されるプロデューサ/ファイルの集合は、不変コントラクトのバリアント適用性、プロトコル、バンドル選択からジョブ投入前に1回導出する。マニフェストへ再掲してはならない。スケジューラ
  アカウンティングと観測されたプロセス配置は、その期待集合が実際に成立したかを事後検証するための情報源である。
- マージ処理ではrun ID、JSON形式、オーナー、期待ノード、一意性を検証し、欠損や値の衝突を隠蔽しない。
- BigQueryの`insertId`はベストエフォートの補助手段にすぎない。論理view側で完全一致レコードの重複を排除
  し、値の競合を隔離する。
- 再送（replay）時は同一行を全件再送信してよい。送信成功後もアーカイブのJSONLを変更してはならない。送信に失敗した場合は、ホームまたは
  GitHub ArtifactのJSONLを元に手動でワークフローを再実行する。
- アップロードの失敗は試行の失敗（attempt failure）として扱う。アップロード成功後は実行時ディレクトリを削除してよく、ホーム転送のSCPが
  失敗した場合のみGitHub Artifactを保持する。

artifact identityの自己参照を避ける。全フラグメントを一度マージして`metrics.jsonl`を確定させた後、ログ/ソース/結果から
runバンドルを生成し、バンドル、メトリクスサイドカー、profile raw tarの役割/サイズ/ハッシュを`artifact-manifest.json`へ保存する。
外部ファイル名は役割から一意に決定し、マニフェストへ重複記録しない。
フラグメントはマージ済みJSONLの完全な部分集合であるため、個別artifactとしては保存しない。
バンドルハッシュやメトリクスサイドカー自身のハッシュをメトリクスへ書き戻して再マージしてはならない。送信処理はリモートアーカイブの検証を前提とせず、
同一試行のローカルまたはGitHub Artifactを入力として実行できる。

計算ノードからはBigQueryへ直接接続しない。したがって送信用クレデンシャルをPJMプロセスへ渡す必要も
ない。各スナップショットはそのスコープに実在する環境をフィルタリングせずに保存し、機密情報も例外扱いしない。

## 最小の実装境界

計測対象プログラムに計測システムの都合を持ち込まないため、責務を次の6つの境界に明確に分離する。

1. ドメインプローブ/パーサーは`Fact(key, logical_value)`のみを返す純粋関数（pure function）とする。run ID、文字列化、
   ファイルシステム、BigQueryの知識を持たない。
2. `recording.py`の`Recorder`のみが、永続化されたrunマニフェスト、レジストリ、canonicalエンコーダ、factのバッファリングされた
   追加/flush、データフラグメントの完了状態を管理・所有する。別個のcollectorステータスファイルは作成しない。
3. `StageRunner`のみが、実際にspawnするargv、モノトニックタイマー、シグナル、子プロセスのwaitステータスを管理し、
   観測されたfactを`Recorder`へ渡す。
4. ランナー側の`merge`が期待されるプロデューサ、run ID、オーナー、一意性、必須key、フラグメント完了を検証し、
   アーカイブ対象となるマージ済みJSONLを生成する。
5. `ArtifactStore/RunPackager`がrunバンドルおよびartifactマニフェストの作成と検証を担う。GitHub Artifactのアップロードと
   ホーム環境への移管はワークフローが担当し、汎用のリコンサイラ、隔離サービス、送達元帳などは設けない。
6. ランナー側の`publish`のみがBigQueryクレデンシャルを保持し、1試行1送信、同一JSONLを入力とした手動ワークフローの
   再実行を担当する。collector、ソルバー、PJM
   プロセスはBigQuery、artifactアップロード、HTTP/クラウドクライアント等の外部メトリクス送達ネットワークを利用しない。
   ソルバー本来のMPI通信やノード内IPCは本禁止事項の対象外である。

OpenFOAM本体に必要なフックは、定義された境界でのみバージョン付きローカル構造化イベントを出力する薄いアダプタとする。
メトリクスパッケージやBigQueryクライアントをリンクせず、送達、再試行、key展開の責務を持たせない。実装上は
`domain.py`、`recording.py`、`submission.py`、`stage_runner.py`、`merge.py`、`artifact_store.py`、`publish.py`とドメイン別
プローブ/パーサーの間に明確なモジュール境界を設け、CLIはその合成ルート（composition root）に限定する。

OpenFOAM用とQwen用を直ちに第三の共通パッケージへ統合しない。まずは同一のコントラクトと適合性テスト用
フィクスチャを両リポジトリで満たし、インターフェースが安定した段階で、canonicalエンコーダ、レジストリバリデータ、
マージバリデータのみを抽出する。ドメイン固有のcollectorやパイプライン固有の障害処理は共通化しない。

実装開始前の設計正本として、各factの権威あるソース、プロデューサ、取得時点、raw key/artifact、検証規則、
欠損時の扱いは[観測マップ](./experiment-metrics-v2-observation-map.md)に、フィールドレベルの構造は
[contract schema handoff](./experiment-metrics-v2-contract-schemas.md)に規定する。最初の実装スライスでこれらを
単一の機械可読コントラクトへ移行し、以後は観測マップの表をコントラクトから自動生成する。ソースと取得時点を
コントラクト上で特定できない候補は追加しない。

## 環境スナップショット

同一名称の環境変数であっても、取得時点やプロセスが異なれば意味が異なるため、以下を厳格に分離する。

- `source/env/job-entry.snapshot`: PJMエントリ直後のrawプロベナンスartifact。factへは投影しない
- `env.*`: `mpirun`直前のスーパーバイザ環境変数をUTF-8平文で投影する
- rank固有の環境変数は収集しない。rank/ノードに関する情報はプロセス配置（placement）、スケジューラ、ハードウェア情報が担う

rawスナップショットの変数名と値はbyte-exactに取得する。factのキー名は`[A-Za-z0-9_]`のみをそのまま使用し、
それ以外の文字は`~HH`形式の大文字16進数でエスケープする。値はUTF-8であることを検証し、過剰なエンコードを行わずにそのまま保存する。これにより通常文字列における
曖昧性を排除する。rank差分（rank delta）は追加・変更された値および削除された変数名を保持し、共通環境変数との和が完全なスナップショットと
一致しなければならない。スナップショット間で同一の値が重複しても、スコープが異なる独立した観測として扱う。標準的な
2つのrunの差分比較ではGit管理された比較関連keyのみを表示し、全環境変数の差分は別viewでデコードして提供する。

## 実験データの独立性

1回のジョブを1つのrun IDで記録し、各runは他のすべてのrunから独立した実験データとして扱う。
実験ブロック、実行順序、反復インデックス（replicate index）、ペアID、グループ/セットID、計画試行回数、停止規則（stopping rule）など、
反復実行やペア実行を管理するためのフィールド、メトリクスkey、マニフェストフィールドは設けない。

OpenFOAMの実際のソースコード、ワークロード、個別実行設定、配置、計算結果、タイムスタンプ、artifact identityは、各run自身が記録する。
複数runの比較や統計処理が必要な場合は、保存済みの個別keyを利用者が目的に応じて選択しクエリを実行する。
事前グルーピング、ペアリング、フィンガープリント、試行回数、中央値/中央絶対偏差（MAD）などの反復統計量を、v2の標準viewやスプレッドシートに保持させない。


## OpenFOAMで保存する原始事実

### run、stage、allocation

- `run.started_at`、`run.finished_at`、`run.elapsed_sec`
- `run.exit_code`。`run_outcome`は0=`succeeded`、非0=`failed`、欠損=`NULL`としてview側で1回導出する
- `run.stage.<name>.launch`: `StageRunner`がspawnしたプロファイラ/`mpirun`を含む正確な外部`argv`、`cwd`、`stderr_mode`のcanonical JSONオブジェクト。ソルバー専用のargvサブセットkeyは設けない
- 各`perf.stage.<name>.wall_time_sec`と`run.stage.<name>.termination`。terminationはexit、signal、spawn errorを区別するJSONオブジェクトとし、シェルの`128+signal`へ縮退させない
- `perf.pipeline.wall_time_sec`: bench/profileにおいて`blockMesh`のspawn直前からソルバーのwait直後までを計測する。メッシュ監査、ハッシュ計算、アーカイブ処理時間は含めない
- `scheduler.request`: ランナー側の投入境界における個別実行設定、PJMスクリプトidentity、正確な`pjsub`のargv
- `scheduler.accounting`: 固定した`pjstat --history -S --choose ... --data --delimiter "\t"`の実行結果
- 通常のrun（regular run）のみ、投入結果の`scheduler.submit_job_id`とジョブエントリの`scheduler.job_entry_job_id`を別個のソースに由来するスカラー索引として保存し、両者の一致性はview側で導出する。結合用の真偽値フラグは設けない
- minimal hardwareはrunごとに各割り当てノードで`LC_ALL=C lscpu --json`およびコントラクト列挙のproc/sysfs設定を読み取る。rawノードartifactはlscpu JSON/settingsのみとし、`openfoam_minimal_hardware_raw_v2`はCPU identity、ホスト名、カーネル、CPU sets、メモリ/HugePage、NUMA balancing、ブースト、cpufreqポリシーをsubject/node粒度で保持する。各コンセンサスはview側で導出し、下位Factへ複写しない
- profile runのみ、minimal hardwareに含まれないNUMA配置と実行後メモリ（post-run memory）のraw artifactを追加する。これを第2の複合raw factへ集約せず、Publisherのソース連動型射影からコンシューマ列を構成する。bench runではNULLとする

runのライフサイクルはPJMエントリから計算ノード側の回収終了までとする。started/finishedはUTCウォールクロック、elapsedは同一スーパーバイザ境界のモノトニッククロックで取得するため、ウォールクロックのジャンプやタイムスタンプ精度の影響を受けず、厳密な派生関係にはない期間のみ両者を併存させる。同一スコープ・クロック・精度へ統一された時点で、elapsedまたはtimestampペアのいずれか一方をview側の派生項目へ移行する。

### build provenance（ビルドプロベナンス）

build sidecarマニフェストには以下を固定する。

- ビルドを定義した`1_OpenFOAM`のcommit
- OpenFOAMおよびThirdPartyの解決済みcommit
- コンパイラ、MPI、ツールチェーン、コンパイルフラグ
- 精度（precision）、ラベルサイズ（label size）。オリジナルのビルドワークフロー/run/試行はsidecarではなく運用側のbuild行のみが保持する
- ビルドアーカイブ、`icoFoam`バイナリ、ELF `DT_NEEDED`、ビルド時のMPIバージョン

プロビジョニング後に初めて判明する実配置バイナリの`realpath`/SHA-256および`ldd`/解決済み`libmpi`はbuild sidecarへ追記せず、run側の`control/build-provision-validation.json`に記録する。

メッシュの正常パスを確実に実装するため、プローブソースは`experiment-metrics/native/mesh-facts/{mesh-facts.C,Make/files,Make/options}`へ固定する。ビルドワークフローは実験対象と同一のOpenFOAMへリンクしてビルドartifactの`bin/mesh-facts`へ収録し、プロビジョニング時に`<runtime>/provisions/<build-sidecar-sha256>/bin/mesh-facts`へ配置する。完全なパーティション検査も`experiment-metrics/native/partition-audit/{partition-audit.C,Make/files,Make/options}`のネイティブユーティリティへ固定し、同一ビルド/プロビジョニングの`bin/partition-audit`へ収録する。`capture-hardware`はGit追跡下のPythonソースを同一のビルド別プロビジョニング先`bin/capture-hardware`へインストールし、実行可能ファイルのハッシュ値をビルドのセマンティクスへ一度含める。
`icoFoam`、`blockMesh`、`decomposePar`、`checkMesh`、`mesh-facts`、`partition-audit`、`capture-hardware`、およびprofile時のみ使用するシステム`perf`について、解決済みrealpathとハッシュをbuild-provision validationへ一度記録し、各ステージは単純なコマンド名ではなくその絶対パスを指定して起動する。MPIランチャーも解決済みrealpath/ハッシュおよびその絶対パスによる`--version`出力を同レコードへ一度記録し、ソルバーおよびハードウェアプローブの全MPI起動はその絶対パスを用いる。プローブ出力は`cells/faces/points/internal_faces`のみで閉じたJSONオブジェクトとする。

raw tableはartifactへの到達およびrun自身の再現に必要なcommit、マニフェストidentity、artifact URIのみを索引化する。アーカイブのハッシュはビルド時に一度計算し、ベンチマークrunのたびに再計算しない。ビルドスクリプトがアーカイブとハッシュ付きsidecarの書き込みを完了して正常終了した後のみキャッシュへ公開する。コンシューマ側はsidecarの存在とアーカイブハッシュの一致が確認された組のみを再利用し、任意のクラッシュ境界から2つのファイルを復旧するようなトランザクション処理は作らない。Publisherはbuild sidecarと役割付きツールチェーンrawをビルド粒度の`openfoam_build_provenance_raw_v2`へ、runのプロビジョニング検証を`openfoam_build_provisions_raw_v2`へ一度だけ投影する。Runsテーブルの精度/ビルドartifact/コンパイラ/MPIは前者をビルドマニフェストのSHA-256で、実際に解決された実行ファイル/`libmpi`は後者をrun IDで結合し、スカラーFactへ重複して掲示しない。

### MPI通信計測

bench/profileにおいてソルバーの本処理が成功した場合に限り、同一のアロケーション、MPIプロセス数、トランスポート環境を維持したまま、本処理終了後に`network_imb_mpi1`ステージを一度だけ実行する。クラスタ固有のランチャーは後続のジョブ組み込み側で完全なargvを組み立て、共通のキャプチャランナーはそのargvを改変せずに起動する。初版のIMBサブコマンドは以下に固定する。

```text
IMB-MPI1 -npmin <solverと同じMPI process数> -msglog 0:22 -iter 1000 -time 1 -iter_policy dynamic PingPong Sendrecv Allreduce
```

0バイトおよび1バイトから4 MiBまでの2の冪乗サイズを対象とし、IMBの標準出力/標準エラー出力、完全なargvを`source/network/imb-mpi1/`へ保存する。パーサーは保存済みテキストのみを入力とする純粋関数であり、警告メッセージを無視しつつ、完全なPingPong、Sendrecv、AllreduceセクションからIMB自身が出力したプロセス数、メッセージサイズ、反復回数、時間、帯域幅のみを復元する。独自算出した平均値、単位換算による別名帯域、代表値、最大値などをrawメトリクスへ追加しない。

固定幅factsは`network.imb_mpi1.*`の実行設定、`software.imb_mpi1.version`、ステージのterminationおよび所要時間（wall time）のみである。可変長の結果データは`mpi_network_results_v2`へ`(run_id, benchmark, process_count, message_bytes)`粒度で投影し、列構成は`run_id, benchmark, process_count, message_bytes, iterations, time_min_us, time_avg_us, time_max_us, bandwidth_mbytes_per_sec, source_member`とする。当該ベンチマークに存在しない時間列、またはAllreduceにおける帯域幅はNULLとする。

ソルバーが失敗したrunでは本ステージを起動しない。通信ステージの非ゼロ終了コード、シグナル終了、spawnエラー、タイムアウト、出力の切り捨てやパース失敗はソルバー自体の成功判定を覆さないが、terminationを記録してrunの`collection_complete=false`とする。不完全なソースから結果レコードは生成せず、リトライも行わない。ソルバーのwall timeおよび既存の`perf.pipeline.wall_time_sec`には通信時間を含めず、PJMエントリから回収終了までの`run.elapsed_sec`のみが通信時間を含む。
ASPIRE 2A/2A+、Gadi、玄界におけるランチャー、モジュール、ホストマッピング、Singularity、walltime、PJM/PBS/ワークフローの修正は後続の個別作業とする。

### actual workload（実際のワークロード）

ソルバーが読み込む実際のケースについて、セットアップ完了後かつ`blockMesh`実行前に、厳密に7つの構成ファイルを`source/workload/`へコピーし、その同一バイト列からマニフェストを生成する。各runが自身のソルバーケースを一度所有する。Publisherはマニフェスト行と各構成要素の正確なコンテンツバイト列を別個の射影へ転記するため、スプレッドシートやエージェントはハッシュ値だけでなく境界条件、ソルバー制御設定、メッシュ設定を直接比較できる。構成ファイルの内容を個別のraw keyへ重複記録しない。プロトコルは`workload_id`と7構成要素マニフェストの期待されるidentityをGit管理下の次元として保持する。`workload_match`は実際の構成要素射影との完全一致のみを判定し、片側の欠損や競合時はNULLとし、期待値をrawへ複写しない。

### mesh、partition、配置

- `mesh.topology`: cells、faces、points、internal facesのJSONオブジェクト
- `mesh.partition.requested`: 実際に使用された辞書の`source_sha256/subdomains/method`のみからなるJSONオブジェクト
- `mesh.partition.observed`: `source/mesh/partition-observed.json`のJSONオブジェクト。シリアルメッシュ5ファイルのidentity、rank別セル数、rank順のプロセッサメッシュ5ファイル/アドレッシング4ファイルのSHA-256、rankペア順のプロセッサ間境界（processor-interface）面数を保持する。最小・最大・平均・不均衡度はrank別セル数の完全な部分集合であるためview側で導出し、rawへは保存しない
- `solver.runtime_header`: ソルバーログのbuild、arch、Exec、nProcs、Hostsをまとめた単一のJSONオブジェクト
- `solver.pstream.startup_applied.rank.<rank>`: `UPstream::init()`が実際に適用した起動時状態（startup state）
- `solver.pstream.runtime_current.rank.<rank>`: `Time`のインスタンス生成およびcase override適用後、タイムループ開始前の現在状態（current state）
- `solver.pstream.change_events.rank.<rank>`: 実行中に制御設定の再読み込みにより変更が生じた場合のみ記録される順序付きレコード
- `parallel.rank_placement`: rank、ホスト名、ローカルrank、CPU affinity、NUMA affinityのJSON配列

配置リデューサ（placement reducer）は、ファイル名/グローバルrank/run ID、グローバルrankが`0..requested_ranks-1`の完全集合をなすこと、`0 <= local_rank < local_size`であること、同一ホスト名内でのローカルサイズの合意および連続したローカルrank集合を厳密に検証する。

`solver.runtime_header`、スケジューラ要求/アカウンティング、ランチャー配置情報はそれぞれ取得元が異なる独立した観測値であり、互いの射影とみなして削除してはならない。要求値に対する別名は設けない。

1ノード構成では、PJMスーパーバイザが`<provision>/bin/capture-hardware --mode minimal --subject-kind regular_run --subject-id <run> --output-root <run>/source/hardware --node-ordinal 0`を実行する。マルチノード構成では、時間計測対象ソルバーの外側で1度だけ、検証済み絶対パスの`mpirun -np <protocol.nodes> -ppn 1`の後続に同様のプレフィックスと`--node-ordinal-from-env PMI_RANK`を指定して実行する。各設定のcanaryテスト自体で`PMI_RANK`の存在と期待される連続集合が確認できたrunのみを適合性評価の対象（conformance eligible）とし、プローブ側で代替のrank情報源を探索することはない。各プロセスは共有実行時領域の`source/hardware/node-<node-ordinal>.json`へ書き出し、identityとプラットフォーム設定を含む完全な`hardware-node/v1`レコードを保持する。`commands`はargv/exit_code/stderr、`lscpu`は標準出力からパースしたraw JSONオブジェクトである。さらにカーネルリリース、CPU/ノードのonline/isolated/nohz_full状態、総メモリ/HugePage、NUMA balancing、ブースト、cpufreqポリシー別のdriver/governor/min/maxを同一の軽量プローブで収集する。実行後に序数（ordinal）、ホスト名、期待ノード数を照合する。別個のデーモンや常駐型collectorは設けない。

profile runの実行後処理も時間計測対象ソルバーの外側で同様のワンショット形式を用い、`<resolved-mpirun> -np <protocol.nodes> -ppn 1 <provision>/bin/capture-hardware --mode profile-postrun --subject-kind regular_run --subject-id <run> --output-root <run>/profile/raw/hardware --node-ordinal-from-env PMI_RANK`に固定する。`capture-hardware`は公開CLIコマンドとせず、`collect`から呼び出される内部プローブとする。minimal hardwareのノードレコードを正本とし、CPU identityの合意情報を別個のrawへ複写しない。profile runの完全なトポロジー情報は`profile/raw/hardware/node-<ordinal>/`に`/proc/meminfo`、NUMA別の`cpulist`/`meminfo`、およびキャプチャ結果のみを配置する。profileのキャプチャ処理はホスト名も一度取得し、別起動のワンショット実行の序数のみを過信せず、minimal hardwareの`(node_ordinal, hostname)`と厳密に照合する。meminfoのkB値はバイトへ変換し、cpulistはカーネルリスト形式として正規化する。

パーティションidentityは、シリアルメッシュおよびその順序、実際のプロセッサメッシュ、パーティション所属関係、rank順およびローカルインデックス順を保持したセル/面/点/境界のアドレッシング情報を厳密に分離する。グローバルセルが全rankにわたって正確に1回現れること、シリアルメッシュのowner/neighbourから決定される未分割面（unsplit face）は1回・分割面（split face）は対向する双方に符号反対で計2回・境界面（boundary face）は1回現れること、ローカル面の頂点巡回順が点マッピング後のシリアル面と向きを含めて一致すること、点の総和集合がシリアル点集合と一致すること、プロセッサ間境界および外部境界のマッピング、rank集合の連続性をネイティブの`partition-audit`によって検証する。
`partition-observed.json`は`schema_version/serial_mesh/subdomains/interfaces`からなる固定オブジェクトとし、`subdomains`はrank昇順、`interfaces`は`(lower_rank, upper_rank)`昇順で整列する。interfaceの権威ある情報源は、各プロセッサ領域の`processor<rank>/constant/polyMesh/boundary`内にあるプロセッサパッチの`myProcNo/neighbProcNo/nFaces`とする。`partition-audit`は同一のOpenFOAMへリンクし、`polyMesh`、`labelIOList`、`processorPolyPatch`の各APIを利用してASCII/バイナリ形式、ラベル幅、エンディアンをOpenFOAM自身に解釈させ、符号付き`faceProcAddressing`の正負符号を保持する。interfaceは小さいrankを`lower_rank`、大きいrankを`upper_rank`として正規化し、双方のプロセッサパッチが過不足なく一致し、かつ同一の`nFaces`を報告した場合にのみ1件へ集約する。ソルバー終了後に1ケースにつき1回実行し、別個のパーサーやフォールバック手段は持たない。各実行はシリアルメッシュを一度読み込み、プロセッサディレクトリをrank順に1つずつ処理し、グローバル所属関係をビットセットで、対向照合をマップ済み面ID集合で保持する。64MセルcanaryにおいてピークRSSがノードメモリの25%以下に収まることを検証する。
メッシュおよびアドレッシングのパスはケースルートからの相対POSIXパスとし、ハッシュ値はヘッダーを含む実ファイル全体のバイト列に対するSHA-256とする。ソースファイル全体をrun artifactへ複製しないため、各ロケータは`locator_kind=runtime_relative_ephemeral`、相対パス、ファイルサイズ、ファイルバイトのハッシュ値を保持し、artifact memberとは呼ばない。ハッシュ値は消去前の実行時ソースのidentityを保証し、要約情報はクエリの利便性を高めるためのものであり、一方から他方を導出することはできないため、両者の併存は正当である。完全な`checkMesh`の出力は`logs/checkMesh.log`へ保存する。
`decomposeParDict`は、`decomposePar`のspawn直前に実際のargvが参照するファイルバイト列を`source/mesh/decomposeParDict`へコピーし、同一のバイト列から要求レコード（requested record）を生成する。メッシュトポロジーは`mesh-facts -case <case> -fileHandler uncollated -constant`、完全なログは`LC_ALL=C checkMesh -case <case> -fileHandler uncollated -constant`で取得する。大容量メッシュのスキャン、`checkMesh`、パーティションハッシュの計算はソルバー終了後に1回だけ実施し、スコア計測対象ソルバーのキャッシュ状態を乱さない。生成された`decomposeParDict`および各ステージのログはartifactへ保存する。

初版では同一run内のインライン実行後スキャンのみを実装する。独立した監査ジョブ（standalone audit job）は、マニフェスト、CLI、結合契約を複雑化させる割に初版での取得情報を増やさないため、スコープ外とする。

startupレコードは、コミュニケータ構築時のノード内通信制御/閾値、実際のノード間通信、トポロジー制御、設定されたMPIバッファおよびクランプ/アタッチ後のバッファバイト数を保持する。runtime-currentレコードは、ケース側の`OptimisationSwitches`適用後における`floatTransfer`、`nProcsSimpleSum`、exchange/tuning設定、`commsType`、polling、`maxCommsSize`に加え、現在の`nodeCommsControl`、`nodeCommsMin`、`topologyControl`、`usingNodeComms`を保持する。全rankがこれを出力し、view側で期待される全rankの存在と設定値の一致を検証する。`runTimeModifiable`による再読み込みで値が変更された場合は、rank別の追記専用（append-only）ドメインイベントログへ記録する。ランナーはターミナル終了後に完全な行数とプロデューサのイベント数を検証し、期待される各rankごとに1つの順序付き`solver.pstream.change_events.rank.<rank>`配列を必ず一度だけメトリクスフラグメントへ出力する。`[]`は変更が0件観測されたことを示し、key自体の不在はリデューサまたはフックの失敗を表す。スコア計測プロトコルにおいて実行中に設定変更が検出されたrunは、比較不適格とする。未確認の値をデフォルト値から推測して補完せず、`null`とする。

フックの出力先（sink）は`OPENFOAM_METRICS_PSTREAM_DIR=<runtime>/runs/<run>/domain/pstream`の単一ディレクトリに限定する。バンドルはこの絶対パス指定のsinkと検証済みrun IDをそれぞれ`OPENFOAM_METRICS_PSTREAM_DIR`/`OPENFOAM_METRICS_RUN_ID`環境変数へ結合する閉じたバインディングを持つ。スーパーバイザが`mpirun`実行前にこの絶対パスディレクトリを1回作成し、各rankのフックはディレクトリ作成を行わずに自身のファイルを直接オープンする。各rankは`UPstream::myProcNo()`の確定後に`rank-<rank>.jsonl`へ行バッファリングで追記し、正常終了時にflush/closeする。書き込み失敗を理由にソルバーを異常終了させてはならず、フォールバック先や再送キューも設けない。その場合、値はNULLとなり、必須項目に指定されているrunでは`collection_complete=false`となる。

`parallel.rank_placement`は別の`mpirun`ジョブで計測してはならない。同一のrankプロセスを起動するラッパーが`PMI_RANK`、`MPI_LOCALRANKID`、`MPI_LOCALNRANKS`、`gethostname()`、`os.sched_getaffinity(0)`、`/proc/self/status`内の`Mems_allowed_list`を記録した後に、`exec icoFoam`を実行する。各設定のcanaryテスト自体でrank環境変数の存在と期待集合を確認し、欠損時の代替情報源は設けない。リデューサはグローバルrank昇順のcanonical配列を生成する。

### solver logの完全な記録

- `solver.step_timings`: 公式の`ExecutionTime`正規表現にマッチした行ごとに1要素を生成し、直前のシミュレーション時刻、同一タイミング行のExecutionTime/ClockTimeの生の字句（lexeme）およびパース後の数値（nullable）を保持する順序付きJSON配列。シミュレーション時刻または同一行のClockTimeが存在しない場合は、該当フィールドのみを`null`とする
- `solver.pressure_solves`: `Solving for p`にマッチした行ごとに1要素を生成し、初期残差（initial residual）、最終残差（final residual）、反復回数（iterations）、および各数値の生の字句を保持する順序付きJSON配列。反復回数が公式の行末正規表現に合致しない場合は`null`とする
- `solver.log_markers`: Endカウント、NaN/Infカウント、ログに記録されたセル数（nCells）からなるJSONオブジェクト

失敗したrunでは、0件から期待件数未満の配列をそのまま保存し、欠落した要素を空の期待値で補完してはならない。同一レコードのフィールドを初回値、最終値、カウント、反復配列として別keyへ重複保存しない。

圧力方程式の残差は、ソースコード変更時に未変更ビルドと同一のパーティション・rank構成下で計算の収束軌跡を比較検証するために保持する。反復回数のみの配列は本完全レコードの部分集合であるため、別個に保存しない。

## 公式判定と比較適格性

公式判定関数と科学的比較関数は別モジュール、別フィクスチャとして実装する。v2への完全移行前に、現行のシェル固有の正規表現、BADNUMによる行数判定、ホスト名欠損の許容、不正ログであってもexit 0を返す仕様などの判定セマンティクスを忠実に再現した標準評価器（canonical evaluator）を作成し、`tasks/parse_result.sh`をその薄いCLIラッパーとする。数値パース、トリム計算、4桁丸めの規則は固定ロケールおよび十進数演算規則へ一本化し、公開されている全ベースラインログのgolden判定を再確立する。旧AWKの中間丸め挙動を暗黙のうちにSQLで模倣してはならない。

view側では以下の指標を明確に分離する。

- `official_log_valid`: `tasks/parse_result.sh`と完全に一致するログ妥当性判定
- `official_fvops_trim_m`: 公式算定式に基づくスコア
- `score_comparison_eligible`: bench runが科学的な環境比較に適格であるかどうかの判定
- `run_outcome`: スーパーバイザおよびパイプラインの終了コードのみから導出される成否。スケジューラ側の成否はスケジューラ列が独立して保持する

公式FVOPSの分子は観測されたセル数ではなく、常に固定値の`64,000,000 * 4`である。分母は`ExecutionTime[last] - ExecutionTime[first]`とし、ClockTimeやランチャーの経過時間で代替してはならない。メッシュが不正な場合は比較対象外とするが、公式式の分子を観測セル数へ変更してはならない。ベースライン比（baseline ratio）は、クラスタidentityが公表ベースラインと完全一致する場合にのみ算出する。Gadiでは`9.778M FVOPS`、ASPIRE-2Aでは`5.717M FVOPS`を用いるが、これを玄界（Genkai）のrunへ流用してはならず、承認済みの玄界ベースラインがプロトコルに規定されない限り比率はNULLとする。

`score_comparison_eligible`は、official validであることに加え、以下を満たすことを要求する。

- メッシュが64,000,000セル、192,480,000面、64,481,201点であること
- ExecutionTimeが有限かつ狭義単調増加であり、ClockTimeが整数秒の同値を許容したうえで有限かつ単調非減少であり、ExecutionTimeのトリム値が正であること
- 要求ノード/プロセス数、割り当てノード/プロセス数、ソルバーのHosts、配置されたホスト群がプロトコルの個別設定と完全一致すること
- 倍精度（DP）、許可されたワークロード、および`floatTransfer=false`であること
- ビルドプロベナンス、必須collector、成果物artifactがすべて完全（complete）であること
- スコア計測runがdirectモードであり、比較対象のrun同士で計測モード（instrumentation mode）が一致していること

`run_purpose`は各run自身の用途として記録するが、グループIDやセットIDは設けない。`score_comparison_eligible`は`run_purpose=bench`および通常の結果/ソース/配置ゲートのみから導出され、profile runは公式FVOPSが算出・表示される場合であっても、スコア統計、ベスト記録、ランキングの集計対象には含めない。

MPI終了処理（teardown）時の非ゼロ終了コードであっても、ソルバーの計算ワークロード自体は公式妥当（official valid）を満たしうる。原始観測結果は必ず収集し、公式判定の妥当性とrun全体の成否を混同してはならない。`official_log_valid=true`であってもスコアの算出が不可能な場合はスコアをNULLとする。フィールド別の原因分類は行わない。

## 個別実行設定と計測擾乱

D-003は「収集系を初版からマルチノード対応とし、玄界（Genkai）の1/2/4ノードを実機適合性評価（conformance）の対象とする」方針で確定した。
ノード数やプロセス数（rank数）をcollector側へハードコードせず、プロトコルが`nodes`、`ranks`、`resource_group`、`transport_policy`を
独立したフィールドとして一度保持する。要求されるプロデューサはコントラクトのバリアント適用性（variant applicability）が、
計測モード（instrumentation mode）はプロトコルおよびバンドル選択のみが管理する。ランナーはこれらの個別フィールドから
期待されるノード序数/rank集合、および正確な`pjsub`/`mpirun`のargvを展開し、PJMスクリプトidentityとともにマニフェストへ封印（seal）する。
初版のcanaryテストは総rank数を120に固定した均等配置構成
`n1-r120`（120 rank/node、`I_MPI_FABRICS=shm`）、`n2-r120`（60 rank/node、`I_MPI_FABRICS=shm:ofi`）、
`n4-r120`（30 rank/node、`I_MPI_FABRICS=shm:ofi`）を用いる。いずれも`a-batch`キュー、Scotchによる120領域分割（subdomain）とし、ランチャーは
`mpirun -np 120 -ppn <120/nodes>`に固定する。1ノード構成は現行の64Mワークロードで実証済み、2ノード構成は旧ワークロードで基盤動作のみ実証済み、
4ノード構成は未実証であるため、後者2つには過度な性能期待値を仮定せず、各1回の通常canary実行によって取得の成否を確認する。失敗時の自動リトライや
代替設定への切り替えは行わない。canary完了後のrank sweepは同一スキーマ内で個別設定値を変更して実施し、既存のrunを上書きしない。
実行設定を包括的に束ねるID、オブジェクト、専用マニフェストは作成しない。各runにおいて以下の完全一致を照合する。

```text
protocol.nodes == requested nodes == allocated nodes
               == distinct solver hosts == distinct placement hosts
protocol.ranks == requested ranks == solver nProcs == placement record count
```

rank ID、ヘッダーのnProcs、Hostsの合計、配置レコード件数、およびホストあたりのプロセス数（`ranks/nodes`）も完全に一致させる。マルチノード構成において
`I_MPI_FABRICS=shm`のようなノード内通信限定のトランスポート設定は拒否する。

スコア計測対象ソルバーの実行直前には、BigQuery通信、プロファイラ起動、MPIデバッグ出力、`checkMesh`、大容量ハッシュ計算を実行しない。
同一runにおいて最低限必須となるのは、rank、ホスト名、ローカルrank、CPU affinity、および環境変数の差分最小レコードのみであり、
各rankのラッパーが自身専用のsidecarファイルへ一度書き出してから、ソルバープロセスを`exec`する。collectorデーモンや永続ACKプロトコルは
用いない。完全なトポロジーダンプや詳細診断はauditモードへ分離する。最小プローブによるオーバーヘッドの影響は、collector実装段階において
計測なし/ありの比較により一時的に確認し、確認完了後にその測定結果は破棄する。通常runの適格性判定や反復管理情報には組み込まない。

`instrumentation_bundle_hash`は、スコア計測パスで有効化されるフック、プローブ、rank別ソーススキーマ、サンプリング間隔、sink、
バッファ、ラッパーパス、観測コントラクトバージョン、環境変数キャプチャスコープ、ソースパスのallowlistを
列挙したcanonicalマニフェストのコンテンツハッシュである。`lightweight`等の
ラベルのみで同一視してはならない。collector実装中に一度だけ非擾乱（性能オーバーヘッドが実質的にないこと）を確認し、確認後は通常のbench runで同一のバンドルを使用する。
このハッシュは用途（purpose）、arm、run ID、絶対実行時ルートを含まないセマンティックidentityであり、sinkおよびargvは相対テンプレートとして定義する。
開発時の確認出力は保存せず、通常のbench runはコントラクトで選定されたバンドルを使用する。実際のargvやsinkは各runのソース情報として観測する。

## bench/profile trackの分離

永続化するrunの用途（purpose）は`bench`および`profile`の2種類のみとする。

- `bench`: スコア計測および環境間比較。プロファイラ、ポーリング、冗長なトレースは一切含めない。
- `profile`: スコア比較から完全に分離し、ハードウェア性能カウンタ（perf counter）、追加のハードウェア情報、詳細な診断情報を収集する。

コントラクトのプロデューサは`applicable_run_variants=["bench", "profile"]`の部分集合のみを保持する。
profile専用のソースはbench runでは起動せず、固定幅のコンシューマは理由なしのNULLを返す。
開発時の非擾乱確認は独立したrunバリアントではなく、出力を保存しない一時的な確認作業にすぎない。

bench runはscore reference、profile runはprofile baseをソース追跡に用いる。すべてのrunにおいてクリーンなチェックアウト、
リモート到達性、ビルドsidecar、コントロールプレーンのバイナリオブジェクトを通常のプロベナンス規則に従って検証する。

## BigQuery viewとスプレッドシート

BigQueryにはbench/profileのrun、ソース、および成果物の射影（artifact projection）のみを公開する。開発時の非擾乱確認や
その判定結果を表すテーブルやviewは作成しない。

主な論理リレーション（logical relation）は以下の通りである。

| relation | grain | role |
|---|---|---|
| `openfoam_run_facts_v2` | `(run_id)` | Runsの固定幅コンシューマ |
| `openfoam_run_points_v2` | `(run_id,estimand_id)` | bench runの比較評価点 |
| `openfoam_rank_placements_v2` | `(run_id,global_rank)` | rank配置情報 |
| `openfoam_perf_counters_v2` | `(run_id,global_rank,event_name)` | profile専用性能カウンタ |
| `mpi_network_results_v2` | `(run_id,benchmark,process_count,message_bytes)` | IMBのメッセージサイズ別実効MPI通信結果 |
| source/build/workload/hardware relations | ソース固有grain | リネージおよび詳細値 |

`openfoam_run_facts_v2`は少なくとも以下の列グループを持つ。

| group | columns |
|---|---|
| identity | `run_id`、purpose、計測identity、開始・終了時刻。反復・ペア管理情報およびコントラクト/プロトコルのID・ハッシュは持たない |
| execution configuration | `nodes`、`ranks`、`resource_group`、`transport_policy`を独立列として保持 |
| quality | `collection_complete`、`official_log_valid`、`score_comparison_eligible` |
| topology | 要求/割り当て/観測ノード数およびrank数、実効トランスポート/ファイルハンドラ、affinityシグネチャ |
| workload/build | ワークロードidentity、計算精度、ビルド/MPI identity |
| outcome | FVOPS、トリム値、ソルバー/ステージ/パイプラインの経過時間（wall time） |
| hardware | CPU/カーネル/メモリ/各種設定のコンセンサス値、およびprofile専用列 |

Connected Sheetsの既存タブ設計は維持する。通信計測結果のシート表示は全機能の実装完了後に設計するものとし、現段階では
`mpi_network_results_v2`を将来の`MPI Network`タブへの入力候補として位置付けることのみを確定とする。不必要なJSON展開や要約列の追加は要求しない。
固定幅ソースの欠損値はNULLとし、縦持ち（long relation）リレーションは実在するレコードのみを返す。

## 開発時の非擾乱確認

experiment-metrics-v2の実装段階において、計測なし/ありの同条件実行を行い、FVOPSおよびソルバー外部のwall-clock時間が
実用上劣化していないことを確認する。この比較は開発時の一時的な品質検証であり、確認完了後は出力を破棄する。

v2には、非擾乱確認専用のrun purpose、OFF/ONの比較アーム、アロケーション、ペア、マニフェスト、artifact、Fact、メトリクスkey、
BigQueryリレーション、Sheetsタブ、適格性判定、Git管理の決定記録（decision record）は作成しない。通常のbench runは確認済みの
計測バンドルを直接利用し、開発時チェックの結果をrunへ結合（join）しない。

## 決定事項と再オープン条件

D-003は2026-08-09にユーザー回答「基本的にはマルチノード対応型の収集」をもって確定した。検討内容は、玄界の1ノード構成のみを
初版canaryとするか、1/2/4ノード構成をv2対象に含めるかであり、推奨案は前者、採択された決定は後者である。2026-08-10の追加決定により、
実行設定を包括的に束ねる抽象構造は不採用とし、各設定値をプロトコルの独立フィールドおよびスプレッドシートの独立列として扱うこととした。影響を受けるフィールド/viewは、
プロトコルの個別実行設定、スケジューラ要求、プロデューサのnode/rank軸、配置/ホストのコンセンサス、profileのrankソース、
スコア比較適格性判定である。再オープンの契機（reopen trigger）は、対象クラスタのノードモデルまたはスケジューラ/MPI配置セマンティクスが変更され、
同一の個別フィールドによってnode/rank集合を表現できなくなった場合のみとする。

実装上は1/2/4ノード構成で同一のcollectorグラフを用い、node/rank数をプロトコルの個別フィールドから動的に展開する。未実証の2/4ノード構成の数値を
安易に成功扱いとせず、通常canaryにおける実際の観測結果をそのまま記録する。専用collector、フォールバック探索、再投入用の特別枠などは設けない。

非擾乱確認はcollector実装中にのみ実施し、完了後は結果を保存しない。

## 決定状態

| 状態 | 決定 |
|---|---|
| 確定 | raw relationは`run/key/value`の3列構成とし、複合値はcanonical JSONを用いる |
| 確定 | 定義された各プロセススコープの環境変数は、機密情報を含めフィルタリングせずbyte-exactに全件保存する |
| 確定 | ネイティブオブジェクト/構造化ソースを優先し、ログの正規表現パースはフィクスチャを伴う最終手段とする |
| 確定 | 計算ノード側はローカルrawファイルの出力のみを担当し、ファイナライズ/BigQuery送信はランナー、Artifactアップロード/ホーム移管はワークフローが担当する |
| 確定 | 完全なレコードの部分集合にすぎない初回値/最終値/カウント/平均値などをrawへ重複保存しない |
| 確定 | benchとprofileを明確に分離し、取得できなかった値およびprofile専用系統は値のみNULLとし、原因/ステータス/欠損専用レコードは設けない。runレベルのステータスは`collection_complete`のみとする |
| 確定 | 実験用途のシステムとして、多段リトライ、フォールバックソース、フィールド別reasonレジストリは作成しない |
| 確定 | 固定v2成果物の移管は現行OpenFOAMの「GitHub Artifact -> ホームラボランナー -> ホームRAID」を基準とし、Qwenリポジトリへも同様の経路を適用する。OpenFOAMのVTune完全結果およびParaViewケースは固定artifactへ重複格納せず、ホームラボランナーがクラスタから直接取得する |
| 確定 | ホーム環境のartifactは自動失効（expire）させず、ストレージ容量が実際に逼迫した場合にのみ手動で整理する。専用の隔離領域（quarantine）は設けない |
| 確定 | D-003: collectorはマルチノード対応とし、玄界の1/2/4ノード構成を初版実機適合性評価の対象とする。nodes/ranks/resource/transportは独立フィールド・独立列とし、設定を束ねる包括的ID/オブジェクト/マニフェストは設けない |
| 確定 | 非擾乱確認はcollector実装中にのみ実施し、その結果・専用run・メトリクス・artifact・決定記録は一切保存しない |

## 実装ハンドオフ

公開インターフェースはbench/profileの通常runのみを対象とする。

```python
Fact(key: str, logical_value: LogicalValue)
init_run(settings_path, runtime_root, identities) -> RunManifestPath
Recorder.open(manifest_path, producer_id, runtime_dir)
collect_once(manifest_path, runtime_dir, producer_id, probe) -> Path
submit_run(manifest_path, runtime_dir, execution_fields, pjsub_argv) -> SubmissionOutcome
run_stage(stage_name, argv, *, cwd, stderr_mode, recorder) -> Termination
capture_network_stage(stage_name, argv, *, cwd, artifact_dir, recorder) -> Termination
finalize_run(manifest_path, runtime_dir) -> FinalizeOutcome
publish_run(manifest_path, artifact_set_path, destination) -> PublishOutcome
```

CLIのpurposeオプションは`bench|profile`のみとし、非擾乱確認を通常runとして指定するようなオプションやサブコマンドは
追加しない。オーナーのスコープはrunおよびbuildとし、ソースストレージはfact fragment、run bundle、profile rawのみとする。

実行時レイアウトは`runs/<run-id>/`配下に`control/`、`domain/`、`source/`、`logs/`、
`profile/raw/`、`archive-staging/`を配置する。成果物セット（artifact set）は`run-artifacts.tar.zst`、
`metrics.jsonl`、profile時のみ生成される`profile-raw.tar.zst`、および`artifact-manifest.json`で完結させる。
開発時の一時的な非擾乱確認用のファイルやディレクトリを本レイアウトへ混入させてはならない。

ネットワークrawデータは`source/network/imb-mpi1/`配下にargv、stdout、stderrを配置する。

テストゲートでは、マニフェスト、投入/ジョブID、環境変数、マージ、artifact、OpenFOAMセマンティクス、profile、再構築の検証に加え、
IMBにおける0バイトメッセージ、指数表記（科学表記）、欠損列、複数プロセス数セクション、警告混在、出力の途中切断をbench/profile用フィクスチャで検証する。
raw artifactから同一の`mpi_network_results_v2`行集合を過不足なく再構築できること、および失敗・タイムアウト・部分的出力時には0レコードとなり、
termination情報と`collection_complete=false`のみが記録されることを検証する。カタログ/スキーマテストでは、network名前空間に
`lane`、`qualification*`、`block_id`、`block_order`、`replicate_index`、`pair_id`、`ib_*_bw`、`ib_*_lat`、
コントラクト/プロトコルIDやハッシュ値が含まれていないことを保証する。Connected Sheetsの詳細テストは表レイアウト設計時まで延期する。非擾乱確認は実装者がその場で
実行・検証し、フィクスチャ、goldenデータ、送信対象には含めない。

### リリース単位

システム移行はkeyごとの部分的な二重化を行わず、v2のrun単位で段階的に実施する。

1. レガシー出力、シェル評価器、ベースラインログをgoldenフィクスチャとして凍結する。
2. 投入前マニフェスト、ローカルメトリクスエクスポート、OpenFOAMネイティブプローブ、完全なソルバーログレコード、Pstream/配置
   sidecarを単一のv2フィクスチャおよび最初のv2 runで検証・通過させる。
3. bench runに必要な最小サブセットのみを、collector実装段階において代表設定`nodes=1, ranks=120`で計測なし/ありの比較に供する。
   意味的・数値的な等価性および非擾乱性をその場で確認した後に測定結果を破棄し、検証済みcollectorをbenchパイプラインへ組み込む。
4. v2 viewおよびスプレッドシートを切り替え、レガシー専用コンシューマが完全にゼロになったことを確認した後に、旧送信処理およびサブセットkeyを削除する。

ロールバック時は、実行設定および実装を直前のバージョンへ戻して新規runを投入する。既存runのマニフェストやレコードを
事後修正してはならず、1つのrun内でレガシープロデューサとv2プロデューサを混在させてはならない。

## 実装順序

1. 現行key、プロデューサ、コンシューマ、成果物保存先をインベントリ化し、keyレジストリおよび期待されるプロデューサグラフを作成する。
2. クリーンなチェックアウト検証、リモート到達性確認、ビルドsidecarマニフェスト、手動プロベナンスゲートを構築する。
3. BigQueryクレデンシャルをランナー側のみへ集約したうえで、現行メトリクス集合のまま`Fact`、`Recorder`、
   JSONLエクスポート、ランナー側マージ/送信、ワークフロー成果物アップロード/ホーム移管を導入する。
4. データ取り込み時間パーティションおよび`(run, key)`クラスタリングを持つraw table、重複排除/単一値/衝突検出、Sourcesリネージ、
   アーカイブ試行/ステータス、run/point view、2つのrunの差分テーブル関数をkeyカタログから自動生成し、フィクスチャテストを通過させる。
5. cavity3Dの実際のワークロードマニフェスト、完全なソルバーレコード、メッシュ情報、プロベナンスをレガシーcollectorと並行して追加する。意味が
   変化する既存keyをv2で再利用してはならない。
6. 標準公式評価器を実装し、旧シェルスクリプトの判定妥当性および全ベースラインgoldenログとの照合を行う。
7. D-003で確定した個別実行設定、同一rankラッパーsidecar、二段階Pstream/パーティション監査機能を追加する。
   collector実装中は代表設定において同一メッシュ・パーティション・rank構成下で計測なし/ありを比較し、圧力残差/反復軌跡および
   公式マーカーの字句完全一致、性能非劣化を確認したうえで結果を破棄する。
8. 共通ネットワークキャプチャ、IMB純粋関数パーサー、固定幅facts、および`mpi_network_results_v2`射影を実装し、raw artifactからの
   可逆再構築と失敗時の0行規則をフィクスチャで検証する。クラスタ固有ジョブへの組み込みはこの段階では行わない。
9. Connected SheetsのRuns/Sources/Config Diff/Environment/Rank Placement/Profile Counters/Data Status各タブを制限付きコンシューマへ
   切り替え、鮮度および結果サイズに関するスモークテストを通過させる。旧keyコンシューマの不在を確認後、派生・部分集合keyの
   新規生成を停止する。
10. ホーム環境のrun artifactツリーおよびGit管理下のソース/SQLから
    空のデータセットを再構築し、rawレコード集合と主要view/スプレッドシートの結果を照合した後に、旧viewを正式に廃止する。

冗長keyの廃止をviewの作成および動作確認より先行させてはならない。

## 完了条件

- 性能に影響を与えるすべての変更がリモート到達可能なcommitに存在し、コミットメッセージ本文から仮説が明瞭に読み取れること。
- 新規ビルドと再利用の双方において、ソース/ビルドcommit、ツールチェーン、バイナリidentityが完全に追跡可能であること。
- 正当な空文字列、未観測、collector失敗、collector未到達、真のゼロがフィクスチャ上で明確に区別できること。
- canonical JSONがプロセス環境やオブジェクトのキー挿入順に依存せず、常に同一のバイト列を生成すること。
- 各keyパターンのオーナーが一意に定まり、重複排除後の`(run, key)`競合がゼロであること。
- BigQueryの障害時にも、ホーム環境またはGitHub ArtifactのJSONLから同一の論理レコード集合を完全に再送できること。
- 成功・失敗・タイムアウトしたrunの期待されるログおよびJSONLがGitHub Artifactへ確実にアップロードされ、アップロード完了後に実行時環境を安全に削除できること。
- OpenFOAM固定成果物のSCP転送が失敗した場合はGitHub Artifactを保持し、アーカイブジョブを安全に再実行できること。VTune完全結果の直接取得または検証が失敗した際はクラスタ上の原本を削除しないこと。
- profile runの全raw添付ファイルがホーム環境のパスから参照可能であり、benchアーカイブにはprofileパスも欠損用
  レコードも存在せず、対応するスプレッドシート列がNULLのみとなること。
- 公開されている全ベースラインgoldenログにおいて、公式妥当性判定およびFVOPS算出結果が`parse_result.sh`と完全に一致すること。
- 出力途中切断、NaN/Infの発生、ステップ/残差計算/反復回数/メッシュ/rank/トリム処理の異常が原因別に正確に判定できること。
- `solver.step_timings`および`solver.pressure_solves`から派生値を一意に算出でき、不要なサブセットkeyが存在しないこと。
- ExecutionTime、ClockTime、ランチャーの経過時間という異なるスコープの時間がそれぞれ厳密に保存されていること。
- D-003で確定した各設定値において、要求値、割り当て値、ソルバーのHosts、プロセス配置が完全に一致すること。
- セットアップ完了後の実際のケースワークロード構成要素がプロトコルのマニフェストと完全に一致し、1バイトの差異であっても比較不適格と判定できること。
- benchとprofileが厳格に分離され、profile専用列はbench runにおいて理由明記なしのNULLとなること。collector実装段階の一時比較によって
  benchバンドルによる実用上の性能低下が生じないことを確認し、その一時的な比較結果が永続保存されていないこと。
- 未変更（OFF）と最終版計測（ON）の同一条件下において、圧力残差の収束軌跡および公式マーカーが完全に一致し、計測用フックが計算の数値結果に影響を与えていないこと。
- 各runが他runのブロック、実行順、ペア、グループ設定に依存せず、単独でソース情報、設定、結果、artifactを完全に復元できること。
- 各run、Sources、スプレッドシート列がメトリクスkeyまたはGit/artifactの次元へ一意に遡及でき、型変換エラーや値の競合が集約処理によって隠蔽されないこと。
- 2つのrunの差分比較がセルパラメータ付きテーブル関数によって計算され、NULL、同一run同士、存在しないrunの入力を拒絶し、全runペアの事前実体化を行わず、完全な環境変数ダンプをパラメータ指定なしでスプレッドシートへ展開しないこと。
- 設定定義やポリシーの非互換、または片側の環境スナップショット欠損時には、左右の比較値および等価性判定を適切にNULLとすること。
- Data Statusシートにおいて、各オブジェクトのクエリ時刻、最新送信時刻、未移管Artifact数、アーカイブジョブ最終成功時刻、ホームストレージ空き容量、
  SQLリビジョン、競合件数、runレベルの収集不完全件数が正しく表示され、スケジュール更新のオーナー変更・停止やクエリ結果サイズ超過をスモークテストで検知できること。
- スプレッドシート利用者が複雑なJSON展開を行うことなく、commit、妥当性判定、一次結果、成果物artifactへ容易に到達できること。
- 完全なIMB rawデータからメッセージサイズ別のレコード集合を可逆的かつ損失なく再構築でき、通信ステージの失敗がソルバー本処理の成功判定を改変しないこと。
