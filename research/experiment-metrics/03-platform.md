# 実行環境収集モジュール

## モジュール境界

実装上の識別名は `platform` とする。本モジュールは、計算処理の開始前に計算ノード上の同一PythonプロセスからOS、CPU、メモリ、および全環境変数の情報を取得し、単一のバッチとしてBigQueryへ送信する。現行の対象は、九州大学「玄界」ノードグループAにおける1ノードCPU実行である。

情報の取得は、PJM環境変数の確定、環境モジュールのロード（`module load`）、OpenFOAMの`etc/bashrc`読み込み、MPI設定、および認証設定がすべて完了した後、メッシュ生成処理を開始する直前のタイミングで実施する。これ以降、実行条件となる環境構成を変更してはならない。また、構成情報の収集処理をソルバーと並行して実行させることはせず、送信完了を確認した後に前処理工程を開始する。

## 確定メトリクス

| キー | 論理型 | 正となる取得元 | 取得方法 |
|---|---|---|---|
| `system.cluster` | string | コレクター定数 | クラスタ識別用の環境変数が存在しない場合のみ `"genkai"` |
| `system.os.id` | string | `/etc/os-release` | `platform.freedesktop_os_release()["ID"]` |
| `system.os.version_id` | string | `/etc/os-release` | 同APIの `VERSION_ID` |
| `system.kernel.release` | string | カーネル | `os.uname().release` |
| `system.architecture` | string | カーネル | アーキテクチャを示す環境変数が存在しない場合のみ `os.uname().machine` |
| `system.node.hostname` | string | カーネル | ホスト名を示す環境変数が存在しない場合のみ `socket.gethostname()` |
| `hardware.cpu.model` | string | `lscpu --json` | `Model name:` に対応する `data` フィールド |
| `hardware.cpu.socket_count` | int | `lscpu --json` | `Socket(s):` フィールド |
| `hardware.cpu.cores_per_socket` | int | `lscpu --json` | `Core(s) per socket:` フィールド |
| `hardware.cpu.threads_per_core` | int | `lscpu --json` | `Thread(s) per core:` フィールド |
| `hardware.cpu.available_logical_count` | int | プロセスアフィニティ | `len(os.sched_getaffinity(0))` |
| `hardware.memory.total_bytes` | int | `/proc/meminfo` | `MemTotal` のKiB値 × 1024 |
| `env.<environment_name>` | string | プロセス環境変数 | 後述の規則に従って全変数を収集 |

`WM_PROJECT_VERSION`、`WM_OPTIONS`、`LOADEDMODULES` などの環境変数も、それぞれ `env.WM_PROJECT_VERSION`、`env.WM_OPTIONS`、`env.LOADEDMODULES` として保存する。これらを `software.*` として二重に複製したり、`LOADEDMODULES` を分解して派生行を作成したりはしない。また、`PXMYCLST` 等が存在する場合はクラスタ名を、`HOSTNAME` またはPJMの同等変数が存在する場合はホスト名を、`HOSTTYPE` または `WM_ARCH` が存在する場合はアーキテクチャを `system.*` へ重複して複製しない。該当する環境変数が実際に存在しない場合に限り、上表のフォールバックメトリクスを送信する。

## `lscpu --json` の解釈規則

以下のコマンドを実行する。

```bash
LC_ALL=C lscpu --json
```

標準出力をJSONパーサーで解析し、最上位の `lscpu` 配列に含まれる各オブジェクトについて、`field` の末尾コロンを1つ除去した文字列をキーとし、`data` を値とする。必要なフィールドはキー名で直接抽出し、出力の表示位置や空白幅には依存しない。

玄界ノードグループAの公称諸元は Intel Xeon Platinum 8490H、60コア × 2ソケット、主記憶 512 GiB であるが、公称値を静的に埋め込むのではなく、実ノードから動的に取得した値を記録する。

## `/proc/meminfo` の解釈規則

`MemTotal:` で始まる行を検索し、ASCII空白で3つのトークンに分割する。

```text
MemTotal: <unsigned integer> kB
```

Linuxのカーネルインターフェースにおいて、この `kB` 単位は 1024 バイトとして扱う。なお、`MemAvailable` や実行時の空きメモリ量（free memory）は他ジョブの影響等で変動し、実行の再現条件を示す静的構成値ではないため収集対象外とする。

## 全環境変数の保存規則

`os.environb` が利用可能なLinux環境では、文字列デコードを行う前のバイト列ベースで環境変数名と値を列挙する。許可リスト、拒否リスト、およびシークレット情報のフィルタリングは一切介在させない。空文字列の値や改行コードを含む値も欠落なく保持する。

環境変数名とメトリクスキーの対応関係は以下の通りとする。

| 条件 | メトリクスキー |
|---|---|
| 名前がASCII `[A-Za-z][A-Za-z0-9_]*` に合致する場合 | 大小文字をそのまま保持した `env.<name>` |
| それ以外（特殊文字等を含む場合） | 変数名のバイト列を小文字の16進数（hex）文字列化した `env.encoded.<hex>` |

値が正常なUTF-8バイト列であれば、デコードした文字列をそのまま `value` に格納する。UTF-8として無効なバイト列が含まれる場合は、バイト列全体をRFC 4648標準のBase64（改行なし、`=`パディングあり）でエンコードし、キー名を `env.bytes.<name-token>` とする。これにより、BigQueryの `STRING` 型制約を厳密に遵守しながら、あらゆる環境変数を欠落なく可逆的に保存できる。

## 取得失敗時の扱い

- `lscpu --json` や `/proc/meminfo` から目的の値を読み取れない場合は、該当キーの値を空文字として送信する。
- 静的な公称構成を代入したり、人間向けの標準 `lscpu` 出力の解析へフォールバックしたりはしない。
- 取得コマンドの標準エラー出力はメトリクス値には含めず、コレクターの警告ログとして記録する。

## 採用しない値

| 除外項目 | 除外理由 |
|---|---|
| OSの `PRETTY_NAME` | `ID` と `VERSION_ID` の組み合わせで十分に比較可能であるため |
| CPU動作周波数 | ターボブーストや動的負荷によって常時変動し、実行レベルの静的構成値にならないため |
| 空きメモリ量（free/available memory） | 当該実験の外部要因による瞬間的な負荷を表すに過ぎないため |
| GPU情報 | 現在の対象である `a-batch` はCPU専用キューであり対象外であるため |
| `software.openfoam.*`、`software.module.*` | 一次情報である環境変数そのものが保存されるため重複を避けるため |
| ホスト名・アーキテクチャの無条件な複製 | 同等の環境変数が存在する環境では二重記録となるため |

## 参照仕様

- Python `platform.freedesktop_os_release`: <https://docs.python.org/3/library/platform.html#platform.freedesktop_os_release>
- util-linux `lscpu`: <https://man7.org/linux/man-pages/man1/lscpu.1.html>
- Linux `/proc/meminfo`: <https://docs.kernel.org/filesystems/proc.html>
- 玄界 ハードウェア諸元: <https://www.cc.kyushu-u.ac.jp/scp/en/system/genkai/hardware/>
