# 設計上の知見

## Workflowを単純に保つ

現在のworkflowはsource取得、tmpfs準備、展開とpatch、build、artifact、cleanupへ責務を分割している。実行時にしか決まらない値を除き、設定はjobの`env:`へ集約する。

効果が測定誤差内の仕組みは残さない。build symlink、独自`CCACHE_DIR`、archive temporary path、download関数などは、標準機能で代替できたため撤去した。

## Sourceとpatchを宣言的に扱う

- URLは直接記述し、version部分だけを環境変数にする。
- `wget --no-clobber`で共有archiveを再利用する。
- `patches/*.patch`を全件適用し、workflowへfile名を列挙しない。
- patchの追加と削除はGitの差分だけで管理する。

## tmpfsとccacheの役割を分ける

`/dev/shm`はsource、dependency、object、link output、ccache temporary fileへ使う。永続ccache storageはserver設定を尊重する。

毎回変わるbuild pathは`CCACHE_BASEDIR`で正規化できるため、固定pathへのsymlinkは不要である。cache storageとtemporary directoryは別の問題として扱う。

## ログと失敗検出を両立する

Allwmakeの大量stdoutはfileへ保存し、artifactとして取得する。consoleには失敗時のerror要約だけを出す。

`-log`内部の`tee`で終了statusを失わないよう、`bash -o pipefail`を使う。計測結果もbuild logと同じartifactへまとめる。

## A/Bは一要因ずつ行う

queue、linker、parallelism、cache placementを同時に変更すると原因を特定できない。共有nodeでは時間変動も大きいため、反復、逆順実行、User/System CPUの比較を併用する。

wall timeだけでなく、次を判断材料にする。

- User/System CPU
- context switch
- page fault
- 工程別時間
- ccache hit率
- profiler自身のoverheadとartifact size
