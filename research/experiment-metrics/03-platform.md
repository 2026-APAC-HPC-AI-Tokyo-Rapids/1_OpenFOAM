# 実行環境収集モジュール

## モジュール境界

実装名は `platform` とする。計算開始前に、計算ノード上の同じPythonプロセスから
OS、CPU、メモリ、全環境変数を取得し、1バッチで送る。
現在の対象はGenkai node group Aの1ノードCPU実行である。

PJM変数の確定、`module load`、OpenFOAM bashrc、MPI設定、認証設定をすべて終えた後、
meshingの前に取得する。それ以降は実行条件となる環境を変更しない。構成取得をsolverと
同時に走らせず、送信完了後に前処理を開始する。

## 確定メトリクス

| キー | 論理型 | 正となる取得元 | 取得方法 |
|---|---|---|---|
| `system.cluster` | string | collector定数 | cluster識別用環境変数がない場合だけ`"genkai"` |
| `system.os.id` | string | `/etc/os-release` | `platform.freedesktop_os_release()["ID"]` |
| `system.os.version_id` | string | `/etc/os-release` | 同APIの`VERSION_ID` |
| `system.kernel.release` | string | kernel | `os.uname().release` |
| `system.architecture` | string | kernel | architectureを表す環境変数がない場合だけ`os.uname().machine` |
| `system.node.0.hostname` | string | kernel | hostnameを表す環境変数がない場合だけ`socket.gethostname()` |
| `hardware.cpu.model` | string | `lscpu --json` | `Model name:`の`data` |
| `hardware.cpu.socket_count` | int | `lscpu --json` | `Socket(s):` |
| `hardware.cpu.cores_per_socket` | int | `lscpu --json` | `Core(s) per socket:` |
| `hardware.cpu.threads_per_core` | int | `lscpu --json` | `Thread(s) per core:` |
| `hardware.cpu.available_logical_count` | int | process affinity | `len(os.sched_getaffinity(0))` |
| `hardware.memory.total_bytes` | int | `/proc/meminfo` | `MemTotal`のKiB値×1024 |
| `env.<environment_name>` | string | process environment | 下記規則ですべて取得 |

`WM_PROJECT_VERSION`、`WM_OPTIONS`、`LOADEDMODULES`などもそれぞれ
`env.WM_PROJECT_VERSION`、`env.WM_OPTIONS`、`env.LOADEDMODULES`として保存する。
これらを`software.*`へ複製したり、`LOADEDMODULES`を分割した派生行を作ったりしない。
`PXMYCLST`等が存在すればclusterを、`HOSTNAME`またはPJMの同等変数が存在すれば
hostnameを、`HOSTTYPE`または`WM_ARCH`が存在すればarchitectureを`system.*`へ
複製しない。該当する環境変数が実際にない場合だけ、上表のfallbackメトリクスを送る。

## `lscpu --json` の読み方

次を実行する。

```bash
LC_ALL=C lscpu --json
```

標準出力をJSON parserで読み、top-level `lscpu` 配列の各objectについて
`field`末尾のコロンを1つ除いた文字列をキー、`data`を値とする。必要なfieldを
名前で選ぶ。表示位置や空白へ依存しない。

Genkai node group Aの公称構成はIntel Xeon Platinum 8490H、60 cores×2 sockets、
512 GiBであるが、公称値をメトリクスとして埋め込まず、実ノードの値を取得する。

## `/proc/meminfo` の読み方

`MemTotal:`で始まる行を探し、ASCII空白で3 tokenへ分ける。

```text
MemTotal: <unsigned integer> kB
```

Linuxのこのinterfaceにおける`kB`は1024 bytesとして扱う。`MemAvailable`や
実行時free memoryは他ジョブ等の影響を受け、runの再現条件ではないため収集しない。

## 全環境変数の規則

`os.environb`が利用できるLinuxでは、文字列へdecodeする前の名前と値を列挙する。
許可リスト、拒否リスト、秘密情報フィルタを一切設けない。空の値、改行を含む値も
省略しない。

名前とキーの対応は次とする。

| 条件 | キー |
|---|---|
| 名前がASCII `[A-Za-z][A-Za-z0-9_]*` | 大小文字を保った `env.<name>` |
| それ以外 | 名前のbyte列を小文字hex化した `env.encoded.<hex>` |

値が正しいUTF-8ならdecodeした文字列をそのまま`value`へ入れる。UTF-8でない場合は
byte列をRFC 4648 standard Base64（改行なし、`=`paddingあり）でencodeし、
キーを`env.bytes.<name-token>`とする。これによりBigQueryの
`STRING`制約を守りながら、全変数を欠落なく可逆に保存できる。

## 取得できない場合

- `lscpu --json`や`/proc/meminfo`から目的の値を読めなければ、そのキーを空文字で送る。
- 公称構成を代入したり、人間向け`lscpu`出力へfallbackしたりしない。
- 取得コマンドのstderrはメトリクスへ入れず、収集警告として扱う。

## 採用しない値

| 値 | 理由 |
|---|---|
| OSの`PRETTY_NAME` | `ID`と`VERSION_ID`で比較可能 |
| CPU周波数 | turboと負荷で変動し、今回のrun-level構成値にならない |
| free/available memory | 実験外の瞬間的な負荷を表す |
| GPU情報 | 現在の`a-batch`はCPU-onlyであり対象外 |
| `software.openfoam.*`、`software.module.*` | 対応する環境変数が一次情報であり重複する |
| hostname、architectureの無条件な複製 | 対応する環境変数があるrunでは重複する |

## 参照仕様

- Python `platform.freedesktop_os_release`:
  <https://docs.python.org/3/library/platform.html#platform.freedesktop_os_release>
- util-linux `lscpu`: <https://man7.org/linux/man-pages/man1/lscpu.1.html>
- Linux `/proc/meminfo`: <https://docs.kernel.org/filesystems/proc.html>
- Genkai hardware:
  <https://www.cc.kyushu-u.ac.jp/scp/en/system/genkai/hardware/>
