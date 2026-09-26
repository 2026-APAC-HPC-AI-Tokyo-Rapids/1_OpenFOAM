# 2026 APAC HPC-AI Competition Rules

## 統合版ルール・技術仕様・Q\&A・運用ガイド

調査・更新時点: 2026-09-26 (JST)  
対象: 2026 APAC HPC-AI Competition  
主な根拠: 公式 GitHub、参加者 Slack \#social における主催者回答、HPC-AI Advisory Council の公開大会案内

重要: 本文は、2026-09-25 に公開された GitHub Addendum を最優先の現行ルールとして、従来のタスク規則、Application Notes、Slack で全参加者向けに示された質疑応答・運用情報を統合したものです。過去の Slack 回答と Addendum が異なる場合は、後から公開された Addendum を優先します。個別の口頭・DM・私的例外は根拠として扱いません。

# 0\. 本書の情報区分と読み方

# 

本書では、情報の性質を次の4種類に分けて扱います。  
• Official rule: GitHub の README / Task Rules / 2026-09-25 Addendum。競技規則として最優先します。  
• Official clarification: 主催者が \#social で全参加者向けに示した回答。GitHub と矛盾しない範囲で規則の解釈・運用を補足します。  
• Application note / example: GitHub Application Notes や reference scripts。再現済みの参考実装・推奨手順であり、Task Rules が明示しない限り特定構成を必須化するものではありません。  
• Operational note: quota、障害、VPN、cluster 状態など時点依存の情報。競技規則とは分離して読みます。

**主要章: 1 要点 / 4 共通ルール / 5 Qwen / 6 OpenFOAM / 7 Presentation / 8 Resources / 11 FAQ / 12 Checklist / 13 未確定事項 / 14–15 出典**

# 

# 1\. まず読むべき要点

• 大会全体の原則は「Make the same math faster. Don't change it.」です。同じ計算をより速くすることが課題であり、計算内容・数値的仕事量・モデル品質を変えて速く見せることは認められません。  
• 両タスクとも Basic / Bonus / Prohibited の3区分です。Basic は全チーム必須で、主催者が再実行する対象です。Bonus は、よく説明された Basic 最適化そのもの、または「同じ計算」であることをチーム自身が証明した実験的最適化です。  
• 各タスクは 50 点。現行配点は Judges 35 点（Basic 20 \+ Bonus 15）+ Performance and re-verification 15 点、すなわち 70% / 30% です。  
• Qwen は Qwen3-235B-A22B-Instruct-2507-FP8 を 2 ノード・16 GPU で Prefill/Decode 分離して処理します。公式再実行は固定 AIPerf コマンド、closed-loop、4000 input / 200 output、TTFT ≤ 3000 ms、平均 ITL ≤ 20 ms、good\_request\_fraction ≥ 0.90 です。  
• OpenFOAM は openfoam.com v2512、65M cell の occDrivAerStaticMesh、simpleFoam、double precision が固定です。1/2/4 ノードで 40/80/150 step、4 ノードの Average wall-clock time per time step が性能指標です。  
• OpenFOAM の source patch、Pstream、別 decomposition、特殊 renumbering、-ffast-math 等は一律禁止ではなく、9/25 Addendum 以降は多くが Bonus として扱えます。ただし self-proof が必須です。  
• 低精度化、計算の省略、別モデル/別ケース化、必要な検証の回避は Bonus でも禁止です。  
• 一つの interview で Qwen と OpenFOAM の両方を扱います。Presentation は 15–20 分、Q\&A は 10 分です。  
• 公開大会日程では presentation slides と code の提出は 2026-10-09 より前、interview agenda は 2026-10-16、interview は 2026-10-19 以降、最終結果は SC26（2026年11月）、award ceremony は SupercomputingAsia 2027（日本）とされています。  
• 調査時点で、提出先・アップロード手段そのものは、確認した GitHub / \#social の現行情報からは特定できませんでした。締切と提出物は確認できますが、提出チャネルは今後の公式案内を確認してください。

# 2\. 情報源と優先順位

## 2.1 現行の一次資料

最優先:  
• GitHub README Addendum (2026-09-25)  
  [https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/README.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/README.md)  
• Qwen3 AI Task Rules \+ Addendum  
  [https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/1.%20Qwen3%20AI%20Task%20Rules.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/1.%20Qwen3%20AI%20Task%20Rules.md)  
• OpenFOAM HPC Task Rules \+ Addendum  
  [https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/2.%20OpenFOAM%20HPC%20Task%20Rules.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/2.%20OpenFOAM%20HPC%20Task%20Rules.md)

運用・実装参考:  
• Qwen3 Application Notes – Firmus AI Cloud  
  [https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/3.1%20Qwen3%20Application%20Notes%20-%20Firmus%20AI%20Cloud.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/3.1%20Qwen3%20Application%20Notes%20-%20Firmus%20AI%20Cloud.md)  
• OpenFOAM Application Notes – Iris  
  [https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/4.1%20OpenFOAM%20Application%20Notes%20-%20Iris.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/4.1%20OpenFOAM%20Application%20Notes%20-%20Iris.md)

参加者向け補足:  
• Slack \#social  
  Organiser reference

公開大会案内:  
• HPC-AI Advisory Council event page  
  [https://www.hpcadvisorycouncil.com/events/2026/APAC-AI-HPC/](https://www.hpcadvisorycouncil.com/events/2026/APAC-AI-HPC/)

## 2.2 ルール衝突時の読み方

• 2026-09-25 Addendum が、以前のタスク文中の特定文を明示的に置換しています。  
• Addendum に置換対象として明記されていない旧タスク規則は引き続き有効です。  
• Slack の古い回答が Addendum より厳しい場合、現在は Addendum に従います。例: OpenFOAM source patch は当初「不可」と説明されていましたが、現行では Basic では不可、Bonus では self-proof 付きで可です。  
• Slack の運用情報（障害、資源配分、接続方法等）は時点依存です。本書では規則と運用履歴を分離しています。

# 3\. 大会日程・進行

公開大会案内および \#social で共有された日程:  
• Competition training lectures: 2026-06-08 以降  
• Competition machine access / exercise: 2026-08-03 以降  
• Presentation slides and code submission: 2026-10-09 より前  
• Presentation interview agenda announcement: 2026-10-16  
• Presentation interview: 2026-10-19 以降  
• Final result: Supercomputing Conference 2026（2026年11月）  
• Award ceremony: SupercomputingAsia 2027, Japan

補足:  
• 7月末〜8月初旬にタスク公開・training が延期され、2026-08-06 に GitHub の Competition Tasks \+ Notes が公開されたと主催者が案内しています。  
• 以後の競技仕様は GitHub に集約され、9/25 Addendum で曖昧だった許可/禁止範囲が整理されました。

# 4\. 共通ルール

## 4.1 「Same math」の定義

Qwen:  
• 同じ checkpoint: Qwen3-235B-A22B-Instruct-2507-FP8  
• target model の weight precision は FP8  
• KV は FP8 またはそれ以上  
• モデルが行う計算を省略・近似してはいけない

OpenFOAM:  
• 同じ 65M mesh  
• simpleFoam  
• fvSchemes 固定  
• fvSolution.fixedIter  
• double precision  
• 1 step あたりの数値的仕事量を維持

## 4.2 Basic

• 各タスクで必須です。  
• 主催者が build instructions / script に基づいて再構築・再実行する対象です。  
• 「再現可能・説明可能・テキストで差分が読める」ことが重要です。  
• Basic の丁寧な tuning 自体が Bonus points の対象になり得ます。実験的 source patch をしないと Bonus が取れない、という意味ではありません。

## 4.3 Bonus

Bonus には2系統あります:  
• Solid Basic tuning の評価  
• Basic の範囲外だが、同じ計算であることを self-proof した experimental work

Experimental Bonus で示すべきもの:  
1\) 何を変えたか: patch / script / flags / dictionaries をテキストで示す  
2\) なぜ same math か: judge が確認できる短い論証  
3\) Evidence: Qwen は accuracy check、OpenFOAM は所定の Cd 比較  
4\) 自分の Basic result に対する同一 platform 上での speedup

## 4.4 Prohibited

両タスクで共通して禁止:  
• 別のモデル・ケース・数値手法へ変える  
• 1 step / 1 token 当たりの必要な計算を減らす  
• 許容範囲を下回る低精度化  
• 計算や validity / boundary checks を省略する  
• 各 task で禁止された benchmark/result manipulation（計算の省略・結果の捏造等）

## 4.5 評価・配点

各タスク 50 点:  
• Basic judging: 20  
• Bonus judging: 15  
• Performance and re-verification: 15  
合計: Judges 70% / Performance & re-verification 30%

注意:  
• 異なる platform の絶対性能は直接比較しません。  
• Performance component は Basic submission を対象とします。  
• 一つの interview で両タスクを扱います。

# 5\. AI Task — Qwen3-235B-A22B PD Disaggregated Inference

## 5.1 固定 workload

Model:  
• Qwen/Qwen3-235B-A22B-Instruct-2507-FP8  
• MoE  
• served target checkpoint は公開 FP8 checkpoint そのもの

AIPerf synthetic workload:  
• corpus: Shakespeare text slices  
• ISL: 4000 tokens, stddev 0  
• OSL: 200 tokens, stddev 0  
• random seed: 2026  
• cache-bust: first\_turn\_prefix  
• temperature: 0.0  
• repetition\_penalty: 1.0  
• ignore\_eos: true  
• 12,800 dataset entries  
• closed-loop at team-declared concurrency N

Timing:  
• warmup: 60 s  
• benchmark: 120 s  
• grace: 30 s

## 5.2 Platform

選択肢:  
• Firmus AI Cloud: 2 × HGX H200 nodes, 16 GPUs total, 8 × InfiniBand NDR interconnect  
• NSCC ASPIRE 2A+: 2 × HGX H100 nodes, 16 GPUs total

Scored run:  
• 2 nodes / 16 GPUs を全て使用  
• Firmus と ASPIRE 2A+ の raw throughput は直接比較しない  
• maintenance 時は他方へ切り替えて作業継続可能

## 5.3 必須アーキテクチャ

• Prefill / Decode disaggregation は必須です。  
• 全面的な colocated deployment は task requirement を満たしません。  
• P:D split ratio は自由です。  
• Official benchmark は team gateway の OpenAI-compatible /v1/chat/completions だけを叩きます。  
• Prefill / Decode worker の内部 endpoint を benchmark client から直接叩くことは禁止です。  
• Basic では全 request が plain PD（prefill worker で prefill、decode worker で decode）である必要があります。request 単位の prefill-on-decode fallback 等は Basic ではなく Bonus 扱いです。

## 5.4 SLA と性能指標

Good request:  
• TTFT ≤ 3000 ms  
• Average ITL ≤ 20 ms  
• 両方を同時に満たす必要があります。  
• Error request も good\_request\_fraction の denominator に入ります。  
• good\_request\_fraction ≥ 0.90 が必要です。

Performance metric:  
• AIPerf の goodput は req/s  
• 競技で表記する good output token/s \= goodput × 200  
• profile\_export\_aiperf.json の goodput を用いる  
• OSL=200 が固定なので ranking order は同一です。

Qwen re-verification:  
• 再実行で good\_request\_fraction \< 0.90、または reference deployment (reference-scripts/07) を下回る場合、現行 README Addendum では performance score は reference deployment の score に設定されます。

## 5.5 Official AIPerf command

公式 scored re-run では、下記の benchmark protocol を変更してはいけません。N、HOST、MODEL はチーム環境に対応する値です。

`N=<team-declared concurrency>`  
`HOST=<gateway host:port>`  
`MODEL=<team's /v1/models id>`

`aiperf profile \`  
  `--url "http://${HOST}" \`  
  `--endpoint-type chat \`  
  `--endpoint /v1/chat/completions \`  
  `--model "${MODEL}" \`  
  `--tokenizer Qwen/Qwen3-235B-A22B-Instruct-2507 \`  
  `--streaming \`  
  `-H 'Accept: text/event-stream' \`  
  `--concurrency "${N}" \`  
  `--workers-max "${N}" \`  
  `--api-key NOT_USED \`  
  `--warmup-duration 60 \`  
  `--benchmark-duration 120 \`  
  `--benchmark-grace-period 30 \`  
  `--synthetic-input-tokens-mean 4000 \`  
  `--synthetic-input-tokens-stddev 0 \`  
  `--output-tokens-mean 200 \`  
  `--output-tokens-stddev 0 \`  
  `--extra-inputs min_tokens:200 \`  
  `--extra-inputs max_tokens:200 \`  
  `--extra-inputs ignore_eos:true \`  
  `--extra-inputs temperature:0.0 \`  
  `--extra-inputs repetition_penalty:1.0 \`  
  `--num-dataset-entries 12800 \`  
  `--random-seed 2026 \`  
  `--cache-bust first_turn_prefix \`  
  `--goodput "time_to_first_token:3000 inter_token_latency:20" \`  
  `--ui simple`

禁止:  
• official re-run で command / dataset / seed / benchmark client を変更する  
• \--request-rate 等を加えて open-loop / Poisson arrival にする

許可:  
• local exploration / sweep / presentation data 用の run では duration, warmup, seed, cache-bust 等を変えてよい  
• 短い 10–20 秒程度の exploratory run で設定差を比較してよい  
• official 120 秒 run は最終確認・公式再実行に温存することが推奨

## 5.6 Qwen Basic — 許可

Model / precision:  
• target は published FP8 checkpoint のまま  
• target weight は FP8  
• KV cache storage / transfer は FP8、FP16、BF16 が可  
• BF16 KV のみ対応する engine も参加可能だが補正なし

Lossless speculative decoding:  
• target model が全 token を verify し、official greedy setting で target-only と同じ出力を得るものは Basic で可  
• draft は EAGLE-3 head、MTP head、小型 draft model 等  
• public draft でも team-trained/fine-tuned draft でもよい  
• team-trained draft は Shakespeare corpus、AIPerf generated requests、対象モデルの同 workload prompt への回答を training data にしてはいけない  
• team-trained draft は data / scripts / settings を公開可能な形で提出  
• draft weights は FP8 以上。BF16 draft を load 時に FP8 quantize することも可  
• draft の由来、size、precision を result package で宣言

Serving:  
• serving stack は自由  
• SGLang / vLLM / TensorRT-LLM / Dynamo 組合せ等、特定 stack は必須ではない  
• stack patch も model computation を変えない範囲で可。patch をテキスト提出  
• TP / PP / EP / DP  
• P:D ratio / routing  
• scheduling  
• kernel/CUDA graph tuning  
• NCCL / IB / communication tuning  
• compute/communication overlap  
• cross-node KV transfer latency reduction  
• finer split も同じ request を同じ16 GPU・同じ SLA で処理する限り可

Warm-up:  
• engine / compiler / CUDA graph warmup は official command 前に可  
• P-D pair の KV transfer path を張るための少数の connection warm-up requests も可  
• ただし official benchmark dataset / seed を warm-up に使わない  
• official \--warmup-duration 60 自体はそのまま実行する  
• third compute node を追加せず、AIPerf client は login node で動かしてよい

## 5.7 Qwen Bonus

Basic 外の experimental serving mechanism / scheduling / kernel 等で、同じ model output を計算するもの。

必要条件:  
• Q1 accuracy check に pass  
• output が同じ理由を説明  
• patches / deployment method を提出  
• 同一 platform 上の自分の Basic に対する speedup を示す

「多少品質が落ちても speedup が大きい」は Bonus の根拠になりません。

## 5.8 Qwen Prohibited

• BF16 original を自分で FP8 target に quantize して代用する  
• distillation / requantization / pruning / model merge  
• layer / expert skipping  
• prompt pruning  
• token dropping  
• 4000 input token 全てに attend しない sparse / approximate prefill  
• KV eviction による計算省略  
• FP8 未満の served path precision  
  \- INT8  
  \- INT4  
  \- FP4  
  \- その他 FP8 未満  
• different / smaller target model  
• official request が template \+ 4000 input \+ 200 output を完全に収容できない context window  
• gateway bypass  
• open-loop 化

## 5.9 Accuracy / quality check

• 主催者が full-set accuracy check を実施  
• pass line: reference score の 99%  
• reference は official FP8 checkpoint を無変更で serving した主催者自身の run  
• model card の BF16 original の数値ではありません  
• checks は Hugging Face model card 掲載 benchmark や AIPerf checks を含むが、それらに限定されない  
• token-by-token / logits 完全一致ではなく benchmark scores を比較  
• SGLang と vLLM のわずかな出力差は、それ自体では問題ではない  
• 「dumbed down」した serving を弾くための検証です

## 5.10 Qwen submission package

必須:  
1\) Software stack build method  
   • container image \+ build files または shared storage 上の self-built setup  
   • 同じ環境を再構築できる手順  
2\) Job submission script  
   • Slurm または PBS  
   • serving stack deployment と official AIPerf invocation が同一 job 内で連続すること  
3\) Presentation slides  
4\) Optional: performance profiling data

推奨構成:  
team\_name\_qwen3pd/  
  build/  
  run/  
  results/logs/  
  analysis/profiling\_data/   (optional)  
  presentation/

## 5.11 Firmus reference deployment と実務上の注意

Application Notes の verified example:  
• 2 nodes, 8 GPUs/node  
• Node 0: 4 × Prefill workers, TP=2  
• Node 1: 2 × Decode workers, TP=4, EP=4  
• NIXL transfer  
• context-length 8192  
• mem-fraction-static 0.90  
• Prefill worker ports 30100–30103  
• Prefill bootstrap ports 9000–9003  
• Decode ports 30200–30201  
• Router port 8000  
• Decode max-running-requests 256

これは「動く starting point」であり、競技上の必須構成ではありません。Task Rules では stack / topology / parallelism は許可範囲内で変更できます。

Cold-start / NIXL:  
• /health が通るだけでは最初の実 request の KV path が確立済みとは限りません。  
• reference script 07 は concurrency を同一 job 内で ramp させます。  
• cold layout にいきなり高い closed-loop concurrency を与えると、最初の request が KVPoll.WaitingForInput のまま 300 s timeout に達する事例が報告されています。  
• 各 P-D pair を connection warm-up する運用が現行 Basic で明示許可されました。  
• 同じ症状について、SGLang/NIXL の既知問題と infrastructure 側問題の両方が確認されており、原因を一つに決めつけないことが重要です。

# 6\. HPC Task — OpenFOAM occDrivAerStaticMesh

## 6.1 固定 workload

• Application: OpenFOAM v2512, openfoam.com December 2025 release  
• Case: occDrivAerStaticMesh  
• Mesh: official coarse 65M cells  
• Solver: simpleFoam  
• Floating point: double precision  
• fvSchemes: fixed  
• fvSolution.fixedIter: fixed  
• controlDict.noWrite: fixed  
• 1 node: 40 steps  
• 2 nodes: 80 steps  
• 4 nodes: 150 steps  
• 1/2/4 node results: scaling analysis  
• Scored result: 4-node run

Official mesh reference:  
[https://zenodo.org/records/15012221](https://zenodo.org/records/15012221)

## 6.2 Platform

NCI Gadi:  
• queue: normalsr  
• Intel Xeon Platinum 8470Q Sapphire Rapids  
• scored run: 4 standard CPU nodes

NSCC ASPIRE-2A:  
• standard compute nodes  
• AMD EPYC 7713  
• scored run: 4 standard CPU nodes

• Gadi と ASPIRE-2A の absolute time は直接比較しません。  
• core/thread を全て埋める必要はありません。  
• site OpenFOAM/2512 module が推奨 starting point。  
• official v2512 を self-build することも可能です。

## 6.3 Scored preparation chain

Allrun と同じ処理を全て実行:  
1\) decomposePar \-constant  
2\) restore0Dir \-processor  
3\) renumberMesh \-constant \-overwrite \-parallel  
4\) potentialFoam \-initialiseUBCs \-parallel  
5\) applyBoundaryLayer \-ybl 0.0450244 \-parallel  
6\) simpleFoam \-parallel

必須:  
• potentialFoam を skip しない  
• applyBoundaryLayer を skip しない  
• \-ybl 0.0450244 を変えない  
• endTime は 1/2/4 node に応じて 40/80/150  
• preparation chain は複数 job に分けてもよいが、各 step は実行する

## 6.4 Performance metric

Scored number:  
• simpleFoam log の Average wall-clock time per time step  
• second step 以降から算出される値  
• lower is better  
• decompose / restore / renumber / potentialFoam / applyBoundaryLayer の preparation time は performance score に含めない

ただし preparation が非 scoring だからといって省略できるわけではありません。

ASPIRE-2A の run-to-run variability:  
• performance score に noise correction はありません。主催者の re-run が reference number になります。  
• submission / interview では final configuration の代表的な 4-node runs を job ID 付きで複数示してよく、best run を示すことも認められています。  
• machine variability を示す別の noise showcase を追加しても構いません。異常な挙動は help@nscc.sg へ報告できます。

## 6.5 OpenFOAM Basic — Source/build

• official openfoam.com v2512, unmodified source  
• site OpenFOAM/2512 module、または同じ source tree を rebuild  
• compiler / build flags は wmake/rules/\* または WM\_\*, FOAM\_EXTRA\_CXXFLAGS 等で設定可能  
• exact build script を提出  
• wmake/rules/\* を変更した場合は patch をテキスト提出  
• IEEE double precision を維持  
• WM\_LABEL\_SIZE=32 / 64 は両方可  
• WM\_PRECISION\_OPTION=DP \+ label32 は明示的に許可  
• \-ffast-math, \-Ofast 等の IEEE semantics を緩める flag は Basic ではなく Bonus

## 6.6 OpenFOAM Basic — Case / decomposition

Basic で case 側から変更可能:  
• system/include/caseDefinition  
  \- nCores  
  \- decompositionMethod \= hierarchical または scotch  
  \- nHierarchical  
• 選択 method の coefficients  
  \- hierarchicalCoeffs  
  \- scotchCoeffs  
• endTime \= 40 / 80 / 150

Basic では変更不可:  
• mesh  
• simpleFoam  
• fvSchemes  
• fvSolution.fixedIter  
• controlDict.noWrite の function objects  
• caseDefinition の physics

Function objects:  
• Basic / Bonus を問わず task-defined work の一部  
• 削除不可  
• standard output を file に redirect するのは可

## 6.7 OpenFOAM Basic — renumber / runtime / I/O

renumberMesh:  
• renumberMesh \-constant \-overwrite \-parallel をそのまま実行  
• default method  
• \-dict, \-renumber-method, \-renumber-coeffs を加えるのは Bonus

Basic runtime tuning:  
• Slurm / PBS scripts  
• ranks / node placement  
• affinity  
• SMT on/off  
• MPI parameters  
• UCX parameters  
• runtime environment variables  
• OpenFOAM runtime switches that do not alter source  
• NUMA / data locality  
• file-system tuning  
• parallel I/O

Addendum F1 で Basic として正式明記された I/O / file-system options（Slack で先行回答）:  
• \-fileHandler  
• \-hostRoots  
• \-ioRanks  
• Gadi \$PBS\_JOBFS など node-local storage の使用

## 6.8 OpenFOAM Bonus

Basic 外で、Prohibited に該当せず、same math を self-proof できるもの。

代表例:  
• decomposition:  
  \- kahip  
  \- metis  
  \- ptscotch  
  \- multiLevel  
  \- simple  
  \- structured  
  \- その他 Basic 外 method  
• method manual decomposition  
• 自作 program による decomposition / renumbering  
• renumbering:  
  \- \-dict  
  \- \-renumber-method  
  \- blockSize  
  \- zoltan  
  \- その他 alternative renumbering  
• v2512 source changes:  
  \- compiler pragmas  
  \- intrinsics  
  \- data layout  
  \- communication code / Pstream  
  \- solver internals  
• 他 OpenFOAM version / branch / fork 由来 code の移植  
  \- origin を明示  
• tree を直接編集しない code replacement:  
  \- LD\_PRELOAD  
  \- \-Wl,--wrap=  
  \- compiler plug-ins / passes  
• value-unsafe floating-point flags  
• fvSolution のうち「仕事量を変えず MPI ranks 間で work を移す」設定  
  \- 例: GAMG processorAgglomerator

重要:  
• 9/25 より前の Slack では source modification が禁止と説明された場面がありますが、現行 Addendum により source patch / Pstream 等は Bonus で明示的に許可されました。  
• Basic result を必ず別に提出します。  
• Bonus は自分の Basic と同じ machine で speedup を測定します。

## 6.9 OpenFOAM Bonus self-proof

自分の pre-change baseline を作る:  
• Bonus run と同じ decomposition method / coefficients  
• 同じ rank count  
• 同じ node count  
• Bonus change だけを外した状態

3本を別々に比較:  
• 1 node / 40 steps  
• 2 nodes / 80 steps  
• 4 nodes / 150 steps

Cd:  
• postProcessing/forceCoeffsAll/\*/coefficient.dat  
• column Cd

判定:  
• coefficient.dat が bit-identical → pass  
• そうでない場合、各 node count の最終 Cd がその baseline の ±0.5% 内 → pass  
• 40/80/150 step の時点で band 外 → same math faster とは認めない  
• 長時間回せば最後に近づく、という説明では代替できない

例外:  
• unmodified source のまま decomposition method だけを変える Bonus は、追加 pre-change baseline 不要。Basic と同様に公開 sanity check の Cd を用います。

## 6.10 OpenFOAM Prohibited

Bonus でも禁止:  
• lower floating-point precision  
  \- WM\_SP  
  \- WM\_SPDP  
  \- mixed precision  
• fvSchemes の変更  
• fvSolution の仕事量を変える変更  
  \- tolerances  
  \- maxIter  
  \- smoothers  
  \- nCellsInCoarsestLevel  
  \- relaxation factors  
  \- その他 step を安くする変更  
• mesh / physics の変更  
• required preparation chain の省略  
• function objects の削除  
• Cd / residual / timing を computation 以外の方法で生成  
• GPU acceleration  
• numerical work per step の削減

## 6.11 Cd sanity check

Basic:  
• sanity check であり scored pass/fail gate ではない  
• official ±% band は設定されていない  
• 大きく外れる場合は run が誤っている疑い  
• 目安:  
  \- 40 steps: \~0.43  
  \- 80 steps: \~0.34  
  \- 150 steps: \~0.28–0.29

公開 OHC-1 hardware values:  
40: Huawei 0.435 / Wikki 0.433 / UniBwM 0.436 / BAW 0.434  
80: Huawei 0.334 / Wikki 0.337 / UniBwM 0.345 / BAW 0.343  
150: Huawei 0.289 / Wikki 0.287 / UniBwM 0.284 / BAW 0.292

Bonus source/runtime changes:  
• 上記の公開 box ではなく、自分の pre-change baseline に対する F3 ±0.5% rule が適用されます。

## 6.12 OpenFOAM submission package

Judges が text として読める形で必要:  
1\) decomposition method / rank count / coefficients  
2\) full preparation chain \+ simpleFoam scripts/logs  
3\) 使用 v2512:  
   • site module または  
   • rebuild の WM\_\* / wmake / compiler flags  
4\) 4-node simpleFoam log  
   • Average wall-clock time per time step を含む  
5\) 4-node coefficient.dat  
6\) 1/2/4 node logs または plots  
7\) input files:  
   • decomposeParDict  
   • controlDict  
   • caseDefinition  
8\) presentation slides  
9\) Bonus を行う場合は patches / programs / self-proof evidence

提出しない:  
• mesh binary  
• processor\* directories  
• solver binaries  
• full install tree

MPI profiling / communication analysis は強く推奨されています。

# 7\. Presentation / Interview

• 1 team につき一つの interview で Qwen \+ OpenFOAM の両タスクを扱う  
• Presentation: 15–20 minutes  
• Q\&A: 10 minutes  
• Task ごとに judge score が付く  
• 重要視される点:  
  \- optimization method  
  \- measured improvement  
  \- bottleneck identification  
  \- technical understanding  
  \- innovation  
  \- reproducibility / evidence  
• 「速いが説明できない black box」は高く評価されにくい  
• 効果が出なかった experimental work でも、仮説・検証・理解が明確なら Bonus で評価され得る  
• OpenFOAM は 1/2/4 node scaling を示す  
• Qwen は SLA gate 前後、goodput、good\_request\_fraction などを定量的に示す

# 8\. Compute resources / quotas / access

## 8.1 Task-to-platform mapping

OpenFOAM:  
• Gadi または ASPIRE-2A

Qwen:  
• Firmus AI Cloud または ASPIRE-2A+

Cross-platform:  
• 絶対性能を直接比較しない  
• maintenance 時に他の許可 platform へ切り替え可能

## 8.2 Iris practice cluster

用途:  
• OpenFOAM onboarding  
• baseline work  
• non-sensitive profiling / compilation  
• decomposition / rebuild practice

特徴:  
• Intel Xeon Platinum 8280 @ 2.70 GHz × 56 cores と Slack で案内  
• non-scored  
• no-SU charging  
• shared account  
• 他 team から files/processes が見えるため、credentials、confidential work、final submission を置かない

Iris examples:  
/global/exafs/groups/rdmaworkshop/2026hpcai-openfoam/reference-scripts/

注意:  
• group tree から直接 run せず、own work directory に copy  
• Iris の ranks / queues / timings を Gadi / ASPIRE-2A のルールだと誤解しない  
• Iris time は score ではない

## 8.3 Firmus

• Qwen practice / scoring platform  
• 2 × H200 nodes  
• Slurm  
• Enroot \+ Pyxis  
• Firmus 使用自体は SU charging なしと主催者が案内  
• reference containers / models が shared storage に用意された運用例あり

## 8.4 NSCC project allocation

Slack 2026-08-11 の案内:  
• ASPIRE 2A: 30,000 CPU core hours  
• ASPIRE 2A+: 500 GPU card hours  
• project storage: 各 512 GB  
• project duration: 2026-08-01 – 2026-11-15

## 8.5 Gadi SU

初期案内（2026-08-11）:  
• 4,000 SU initial  
• \+5,000 SU first request  
• \+4,000 SU final request  
• total cap 13,000 SU

後日の更新（2026-09-13）:  
• per-team Gadi allocation は 14 KSU と主催者が案内  
• additional SU request は Slack ではなく pengzhiz@hpcadvisorycouncil.com へ email  
• requests は週1回、October は週2回集計予定

したがって、本書では 9/13 の 14 KSU 案内をより新しい運用情報として扱います。

資源節約方針:  
• Gadi / ASPIRE の national supercomputer allocation は有限  
• smoke test / basic workflow / parameter grid sweep を national systems で行わない  
• Iris / Firmus 等で方法を固め、national systems では porting / verification / final tuning に重点を置く

# 9\. NSCC access / VPN / Duo

• 各 team は NSCC account 1つ  
• Duo 2FA は1台の enrolled phone に紐付く  
• captain または designated device holder が Duo push を approve  
• teammates は各自の machine に Check Point VPN / SSH を入れられるが、接続時 approval は Duo holder が必要  
• official supported VPN client として Check Point が案内された  
• Duo onboarding mail の件名例: “Duo Security Enrollment”  
• Gadi onboarding は NSCC/VPN と別プロセス

VPN trouble:  
• home / campus / phone hotspot 等、別 network を試す  
• macOS で VPN 接続後 DNS が死ぬ事例が 9/1 に共有  
• 一時的 workaround として SSH by IP が共有された:  
  \- 10.103.72.110 → aspire2a  
  \- 10.103.72.200 → aspire2p  
• 直らない場合、account owner の email から help@nscc.sg へ問い合わせ  
• Duo portal lock が原因だった実例もあるため、no push / authentication failure 時は account status も確認

# 10\. Known operational incidents / practical notes

この節はルールではなく、\#social で共有された運用履歴です。障害は再発・解消し得るため、現在状態は各 scheduler / official channel で確認してください。

• 2026-08-11: ASPIRE 2A / 2A+ が NUS i4 Data Centre cooling issue で shutdown  
• 2026-08-18: Firmus g1/g4 drain。enroot FUSE process deadlock に関連する既知問題として説明、復旧  
• 2026-08-25: Firmus Slurm CliFilterPlugins=lua と cli\_filter.lua 未同期で srun failure。script 配布後復旧  
• 2026-08-26: Firmus /tmp / Slurm spool / ENROOT runtime/data path 容量問題。cleanup/prune 後復旧  
• 2026-09-06: Iris を含む Council clusters が down/drain、9/7 復旧  
• 2026-09-23: Firmus maintenance / Slurm controller issue。quota restriction ではないと説明、g1/g4 restart 後 queue 復旧  
• 2026-09-24〜25: Firmus g1 drain。復旧まで ASPIRE 2A+ H100 を利用可能と案内

# 11\. Frequently Asked Questions — 現行ルールに基づく短答

Q. PD disaggregation は必須ですか?  
A. はい。scored task は PD-disaggregated である必要があります。Basic では全 request が plain PD であることが必須です。request 単位の prefill-on-decode fallback 等は Bonus 扱いです。

Q. Qwen の KV cache を INT8 にできますか?  
A. できません。FP8 は可、FP16/BF16 も可。INT8/INT4/FP4 は不可です。

Q. BF16 draft model を load 時に FP8 quantize して speculative decoding に使えますか?  
A. はい。draft は FP8 以上でよく、Addendum が明示的に許可しています。target checkpoint は公式 published FP8 のままです。

Q. Speculative decoding は可能ですか?  
A. Lossless で、target が全 token を verify し、official greedy setting で target-only と同じ output を保つ場合は Basic で可です。

Q. Qwen の serving stack は SGLang 必須ですか?  
A. いいえ。stack は自由です。

Q. AIPerf は open-loop ですか?  
A. いいえ。closed-loop です。team-declared concurrency N を維持します。

Q. Goodput の単位は?  
A. AIPerf は req/s。競技表記の good output token/s は goodput × 200 です。

Q. OpenFOAM の WM\_LABEL\_SIZE=32 は可ですか?  
A. はい。floating point precision ではなく integer addressing です。

Q. OpenFOAM で SMT は使えますか?  
A. はい。Basic で可です。

Q. OpenFOAM で Pstream を patch できますか?  
A. Basic では不可、Bonus では self-proof を行えば可です。

Q. OpenFOAM source を変更できますか?  
A. Basic では unmodified v2512。Bonus では same math を self-proof すれば source changes が可能です。

Q. \-ffast-math / \-Ofast は?  
A. Basic では不可。Bonus work として self-proof が必要です。

Q. renumberMesh \-dict は?  
A. Basic では不可。Bonus では可です。

Q. \-fileHandler, \-hostRoots, \-ioRanks は?  
A. Basic で可です。filesystem / parallel I/O engineering と扱われます。

Q. OpenFOAM の preparation time は score に入りますか?  
A. いいえ。score は simpleFoam の Average wall-clock time per time step。ただし preparation chain 自体は必須です。

Q. Cd は hard gate ですか?  
A. Basic では sanity check。公式 ±% gate はありません。Bonus source/runtime changes では自分の pre-change baseline に対する ±0.5% rule があります。

Q. OpenFOAM の別 decomposition method は禁止ですか?  
A. 禁止ではありません。Basic は hierarchical/scotch、その他は Bonus です。

Q. ASPIRE-2A の OpenFOAM multi-node timing が run ごとに大きく変動する場合、補正されますか?  
A. いいえ。公式の noise correction はありません。主催者の re-run が reference number です。提出・interview では final configuration の代表的な 4-node runs を job ID 付きで示してよく、best run の提示も認められています。必要なら別途 noise showcase を追加できます。

Q. GPU で OpenFOAM を加速してよいですか?  
A. いいえ。この task は CPU-only であり GPU acceleration は全 tier で禁止です。

Q. National supercomputer で大量 sweep してよいですか?  
A. ルール違反というより資源運用上強く非推奨です。Iris/Firmus の smoke test・practice を先に行い、Gadi/ASPIRE は検証・本番 tuning に使う方針が繰り返し案内されています。

# 12\. Submission / reproducibility checklist

共通:  
□ Basic result を Qwen / OpenFOAM の両方で用意  
□ Bonus を行う場合も Basic を置き換えない  
□ 変更内容を text で提出  
□ 同じ machine/platform 上の Basic 比 speedup を示す  
□ Presentation slides を提出  
□ judge が再構築できる説明を用意

Qwen:  
□ official FP8 checkpoint  
□ 16 GPUs, 2 nodes  
□ PD disaggregation  
□ gateway /v1/chat/completions  
□ official AIPerf command  
□ good\_request\_fraction ≥ 0.90  
□ official result logs を保存し、profile\_export\_aiperf.json を含める  
□ build instructions  
□ one job submission script  
□ すべての draft について source/size/precision を宣言  
□ team-trained/fine-tuned draft の場合は training method（data/scripts/settings）も提出  
□ serving stack を patch した場合は patches を text で添付  
□ Bonus は accuracy evidence を用意

OpenFOAM:  
□ v2512  
□ 65M mesh unchanged  
□ DP  
□ required Allrun chain 全実行  
□ 1/2/4 node \= 40/80/150  
□ 4-node Average wall-clock time per time step  
□ coefficient.dat  
□ 1/2/4 scaling evidence  
□ decomposeParDict / controlDict / caseDefinition  
□ build flags / WM\_\* / patch  
□ Bonus は pre-change baseline と Cd self-proof  
□ function objects を削除していない

# 13\. 現時点で未確定・要確認の事項

## 13.1 Submission destination

2026-10-09 より前に slides/code を提出する schedule は公開されていますが、確認した GitHub root・Task Rules・\#social では、最終的な upload destination / submission portal の回答を確認できませんでした。

## 13.2 OpenFOAM “4.2 Gadi Application Notes”

現行 OpenFOAM Addendum F1 は 4.2 OpenFOAM Application Notes \- Gadi に organiser vanilla results があると記載しています。一方、2026-09-26 に取得した repository root listing には README、Qwen Rules、OpenFOAM Rules、3.1 Firmus Notes、4.1 Iris Notes の5ファイルしか確認できませんでした。ファイルが追加・移動される可能性があるため GitHub の最新状態を確認してください。

## 13.3 Application Notes と task rules の関係

Application Notes の具体的 port / topology / container / flag は verified example であり、原則として mandatory solution ではありません。Task Rules / Addendum が許す範囲で別実装を選べます。

# 14\. Slack Q\&A / announcement source index

Current rule addendum announcement:  
Organiser reference

Initial task framework — OpenFOAM:  
Organiser reference

Initial task framework — Qwen:  
Organiser reference

Judging focus / platform choice:  
Organiser reference

NSCC allocation announcement:  
Organiser reference

Earlier Gadi staged SU allocation:  
Organiser reference

Qwen closed-loop explanation:  
Organiser reference

Qwen workload / seed:  
Organiser reference

Qwen SLA gate:  
Organiser reference

Qwen PD strict requirement:  
Organiser reference

OpenFOAM I/O / label32 / Cd clarification:  
Organiser reference

Qwen good output token/s formula:  
Organiser reference

Latest Gadi 14 KSU / request process:  
Organiser reference

Qwen PD cold-start / NIXL findings:  
Organiser reference

Firmus follow-up on PD timeout:  
Organiser reference

NSCC Duo onboarding:  
Organiser reference

NSCC one-account / one-Duo-device note:  
Organiser reference

NSCC VPN DNS/network workaround:  
Organiser reference  
Organiser reference

Firmus outage fallback to ASPIRE 2A+:  
Organiser reference

Public competition schedule cited from official event page:  
Organiser reference

# 15\. GitHub source index

Repository:  
[https://github.com/hpcac/2026-APAC-HPC-AI](https://github.com/hpcac/2026-APAC-HPC-AI)

README / global Addendum:  
[https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/README.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/README.md)

Qwen Rules:  
[https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/1.%20Qwen3%20AI%20Task%20Rules.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/1.%20Qwen3%20AI%20Task%20Rules.md)

OpenFOAM Rules:  
[https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/2.%20OpenFOAM%20HPC%20Task%20Rules.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/2.%20OpenFOAM%20HPC%20Task%20Rules.md)

Qwen Firmus Application Notes:  
[https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/3.1%20Qwen3%20Application%20Notes%20-%20Firmus%20AI%20Cloud.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/3.1%20Qwen3%20Application%20Notes%20-%20Firmus%20AI%20Cloud.md)

OpenFOAM Iris Application Notes:  
[https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/4.1%20OpenFOAM%20Application%20Notes%20-%20Iris.md](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/4.1%20OpenFOAM%20Application%20Notes%20-%20Iris.md)

OpenFOAM upstream case:  
[https://develop.openfoam.com/committees/hpc/-/tree/develop/incompressible/simpleFoam/occDrivAerStaticMesh](https://develop.openfoam.com/committees/hpc/-/tree/develop/incompressible/simpleFoam/occDrivAerStaticMesh)

OHC-1:  
[https://github.com/OpenFOAM-HPC-Challenge/OHC1](https://github.com/OpenFOAM-HPC-Challenge/OHC1)

# 16\. 更新時の注意

この大会は競技中であり、ルール・Application Notes・resource allocation・cluster status は更新され得ます。  
今後更新する場合は、最低限次を再確認してください:  
• GitHub README Addendum  
• Qwen Rules の末尾 Addendum  
• OpenFOAM Rules の末尾 Addendum  
• repository root に新しい Application Notes が追加されていないか  
• Slack \#social の organizer announcement  
• submission portal / interview agenda の公式案内


