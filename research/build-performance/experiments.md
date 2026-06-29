# ビルド最適化実験結果

## 並列数

各条件を2回実行した中央値。

| 並列数 | 中央値 |
|---:|---:|
| 30 | 19分46秒 |
| 60 | 18分21秒 |
| 90 | 20分17秒 |
| 120 | 16分26秒 |

120並列は60並列より約10.4%速かった。System CPUは増えるが、Lustre待ちを並列処理で隠す効果が勝った。

## ccacheのtmpfs配置

| 方式 | 中央値 | 判定 |
|---|---:|---|
| `/fast`の既定cache | 16分26秒 | 基準 |
| 毎回tmpfsへコピー | 24分26秒 | 不採用 |
| コピー済みtmpfs | 16分09秒 | 改善1.7%、誤差範囲 |

cache全体のコピーには約1分22秒かかり、コピー済みでも有意な改善はなかった。ccache storageだけがボトルネックではない。

## profiler overhead

| Run | 構成 | AllwmakeまたはBuild step |
|---:|---|---:|
| 28356014551 | profilerなし | Allwmake 13分59.64秒 |
| 28356789505 | profilerなし | Allwmake 22分07.85秒 |
| 28363430866 | `perf record`、DWARF call graph | Allwmake 13分49.00秒 |
| 28364738522 | `perf record`、frame-pointer call graph | Allwmake 14分02.80秒 |
| 28365703413 | frame-pointer profiling | Build step 14分58秒 |
| 28371443227 | 同一frame-pointer profiling、Lustre高負荷 | Allwmake 25分19.91秒 |

共有ノードの変動幅よりprofiler有無の差が小さく、有意なwall time増加は確認されなかった。DWARF call graphはrawデータ735MBで過大だったため撤去した。frame-pointer方式はrawデータ約138MB、artifact圧縮後約28MBであり、継続利用する。
