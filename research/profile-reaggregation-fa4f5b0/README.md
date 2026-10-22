# fa4f5b0のeu-stackプロファイルの再集計（2026-10-22）

#53で取得した最終Bonus（`fa4f5b0`、4ノード512 rank、40 step、48 rankをサンプリング）のCrayPAT stack sampleを、関数別の自己時間と呼び出し経路別の包含時間に集計し直したもの。Bonus第2弾の候補を順位付けするための根拠に使う。

- 入力：Actions 37529785072の`profile-raw.tar.zst`（自宅サーバー `/mnt/net_share/openfoam-artifacts/37529785072/aspire2a/openfoam-aspire2a-v2-r-db41ebdba838b08cf28783ca3839611e/`）の`profile/raw/craypat/stack-samples/rank-*.txt`。
- 集計：`uv run -q --no-project python -I analyse.py <stack-samples-dir> summary.md`。
- 対象：time loop内のサンプル2,396本（全3,054 roundのうち、solver終了後のCrayPATの書き出し608本、読み取り失敗48本、終了処理2本を除く）。割合はすべてこの2,396本に対するもの。stack profileはMPIの割合を約1.8倍に多く見せる（#53）。

`summary.md`の内容：サンプルの分類、自己時間の上位50、`main`直下の段階別の包含時間、勾配・行列組立・GAMG・smoothSolver・kOmegaSST・function object・MPIの呼び出し経路別の包含時間、出現頻度の高いstackの上位40。
