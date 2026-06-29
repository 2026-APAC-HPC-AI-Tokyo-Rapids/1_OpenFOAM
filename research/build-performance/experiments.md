# 実験から得た傾向

## 並列数

| 並列数 | 中央値 |
|---:|---:|
| 30 | 19分46秒 |
| 60 | 18分21秒 |
| 90 | 20分17秒 |
| 120 | 16分26秒 |

120並列は60並列より約10%速かった。Lustre競合でSystem CPUは増えるが、I/O待ちを隠す効果が勝っている。並列度と性能は単調ではないため、160以上は別途A/Bが必要になる。

## Allwmake queue

ccache warm時の`-q`は有利ではなかった。compile自体が軽くなると、全directory走査、objectとlinkの同期点、第二passの固定費が相対的に大きくなる。

queueなしは処理構造が単純で、測定でも平均的に速かったため採用した。

## ccacheのtmpfs配置

| 方式 | 中央値 |
|---|---:|
| server既定cache | 16分26秒 |
| 毎回tmpfsへコピー | 24分26秒 |
| コピー済みtmpfs | 16分09秒 |

cache全体のコピーには約82秒かかる。コピー済みでも改善は約2%で、run間変動より小さい。ccache storage単独は主要ボトルネックではない。

## Linker

lldはIcxから起動できるが、OpenFOAM-v2412のlink ruleはGNU ld前提だった。GNU固有option、library探索、PstreamとMPIの推移的依存で失敗した。

完全対応にはlink ruleと依存順序の継続保守が必要で、現時点ではGNU ldを維持する方が合理的である。profiling上もlinkは最大の支配要因ではない。

## Profiling

- 行timestamp、`perf stat`、`time -v`に有意な遅延は見られない。
- frame-pointer方式の`perf record`もwall timeへの影響はrun間変動より小さい。
- DWARF call graphはraw dataが大きくなりすぎる。
- `pidstat`はprocess treeの追跡精度が不足し、追加情報が少なかった。

frame-pointer方式は圧縮artifactが約30MBであり、継続的な傾向監視に利用できる。
