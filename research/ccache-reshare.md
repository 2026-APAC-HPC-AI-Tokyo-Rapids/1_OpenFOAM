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

## ウォームビルドでの性能差

2026-08-16にActions run [`31948680575`](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/31948680575)で比較した。各クラスタで同じlogin runnerを占有し、最初の`reshare=false`をウォームアップとして除外した。その後は`false, true, true, false, false, true`の順で実行した。各試行は新しいビルドツリーを使い、一次ccacheだけを同じ`/dev/shm/ccache-${USER}`から再利用した。

全測定試行は1,789 cacheable call、1,785 local hit、4 missで一致した。`remote_storage_write`は`false`が8、`true`が3,574であり、`true`ではローカルヒットの共有先への書き戻しが実際に発生している。

| クラスタ | `reshare` | ビルド本体3回（秒） | 中央値（秒） | builder全体中央値（秒） |
|---|---|---:|---:|---:|
| Gadi | `false` | 249.630, 245.759, 251.784 | 249.630 | 259.578 |
| Gadi | `true` | 244.304, 267.312, 248.953 | 248.953 | 259.633 |
| 玄界 | `false` | 299.140, 304.140, 300.497 | 300.497 | 350.584 |
| 玄界 | `true` | 319.579, 311.158, 298.461 | 311.158 | 364.854 |

Gadiではビルド本体の中央値が0.677秒短く、builder全体では0.055秒長い。いずれも0.3%未満であり、`true`の試行内変動より小さいため性能差は検出できない。

玄界では`true`によりビルド本体の中央値が10.661秒、3.55%長く、builder全体の中央値が14.270秒、4.07%長かった。`true`の範囲は298.461秒から319.579秒で`false`の範囲と重なり、3回だけで一般的な遅延率を確定はできないが、通常ビルドで`reshare=true`を有効にする理由はない。共有キャッシュの回収が必要な場合は、通常ビルドへ書き戻しを加えず、前節の後送プログラムを明示的に実行する。
