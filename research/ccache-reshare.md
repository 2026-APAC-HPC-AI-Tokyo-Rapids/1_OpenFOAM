# ccache一次キャッシュの後送

## 結論

ビルドを行わず、login nodeの一次キャッシュからfile backendの共有キャッシュへ未登録entryを送れる。`scripts/reshare-file-ccache.py`はccacheの一次キャッシュを走査し、自己完結したentryだけを共有キャッシュの配置へ原子的に追加する。既存entryは上書きせず、一次キャッシュも削除しない。

通常ビルドへは組み込まない。ccacheはmissから得たentryを既に一次・共有の両方へ書くため、正常時の後送は重複走査になる。共有側の一時障害や、共有設定前に作られた一次キャッシュを回収するときに手動で使う。

## 根拠

両クラスタで使用しているccacheは公式リポジトリの`a89f5010f1c8edf231184b3a3a77654e12e4a288`である。この版の`reshare=true`は、コンパイル要求が一次キャッシュへhitしたとき、そのentryを共有先へ書く設定である。全entryを後送するCLIではない。

file backendへ保存する値は一次キャッシュentryと同じバイト列だが、配置が異なる。40桁のキーを`012345...`とすると、現在の一次キャッシュは`0/1/2345...`、file backendは`01/2345...`に置く。そのためディレクトリ全体のコピーは使えない。一次キャッシュにある`stats`、`CACHEDIR.TAG`、一時ファイルも共有先へ送ってはならない。

ccacheは共有先へ書く前にentry headerの`self_contained`を確認する。後送プログラムも同じ条件を使う。file backendを有効にしたビルドではraw file方式が使われないため、今回確認したGadiの3,574 entryと玄界の24,384 entryはすべて自己完結していた。両クラスタとも、今回の正常ビルドで作られたentryは全件すでに共有側に存在した。

## 実行方法

一次キャッシュはnode-localな`/dev/shm`にあるため、そのキャッシュを持つlogin nodeごとに実行する。

Gadi:

```bash
uv run --script scripts/reshare-file-ccache.py "/dev/shm/ccache-${USER}" "/scratch/hb15/${USER}/openfoam/gadi/ccache"
ccache --trim-dir "/scratch/hb15/${USER}/openfoam/gadi/ccache" --trim-max-size 10GB
```

玄界:

```bash
uv run --script scripts/reshare-file-ccache.py "/dev/shm/ccache-${USER}" /fast/pj26000080/ccache_cache_dir
```

コピーせず件数だけ調べる場合は`--dry-run`を付ける。プログラムは共有キャッシュの容量整理を行わない。Gadiの10 GB制限のような保存方針は、後送後にccache自身の`--trim-dir`で適用する。
