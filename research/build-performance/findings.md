# ビルド性能の傾向

## 支配要因

ウォームビルドはコンパイル計算より、Lustre上のpage faultとmetadata操作に制約されている。

- ccache hit率が約99.5%でも、依存生成、link、install、file scanは残る。
- System CPUはUser CPUを大幅に上回る。
- `open`、`stat`、inode lookup、Lustre lock待ちがperfで観測される。
- `sh`、`cp`、`sed`、`mkdir`、`wmkdepend`などの短命processが無視できない。

実コンパイルをcacheしても、build system自体が行う大量の小file操作はcacheされない。これがccache warm後の主要コストになる。

## 工程別の傾向

代表的な14分程度のbuildでは、時間配分は概ね次の通りだった。

| 工程 | 時間の目安 |
|---|---:|
| ThirdParty | 5分から6分 |
| OpenFOAM libraries | 5分から6分 |
| OpenFOAM applications | 2分前後 |
| modules | 1分未満 |

ThirdPartyではScotch、Boost、FFTW、ADIOS2が主な時間を占める。OpenFOAM側ではlibrary buildが最も長く、依存生成とlinkの固定費が残る。

## 実行時間の変動

同じsource、同じccache hit状況、同じprofiling設定でも、Allwmakeは14分台から25分台まで変動した。

遅いrunでは次の傾向があった。

- User CPUは通常runとほぼ同じ。
- System CPUが2倍以上へ増加する。
- Voluntary context switchが桁違いに増える。
- ThirdPartyとapplicationsが同時に遅くなる。
- perfではLustreのdirectory lookupとdistributed lock待ちが増える。

したがって単一packageやprofilerの問題ではなく、共有Lustre metadata負荷の時間変動と考えられる。単発runだけで高速化を判定してはいけない。

## tmpfsの効果範囲

sourceとbuild outputを`/dev/shm`へ置くことには効果がある。ただし次のpathは引き続きLustre上にある。

- ccache storage
- Intel oneAPI toolchain
- GCC standard headers
- moduleやuser環境の一部

tmpfs化は参照先そのものを変更した処理にしか効かない。build directoryだけをtmpfs化しても、toolchainとcacheのmetadata accessは残る。
