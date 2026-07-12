# GitHub 設定

このディレクトリには、リポジトリの自動実行設定を置きます。現在は
[`workflows/genkai.yml`](workflows/genkai.yml) のみを管理しています。

workflow は self-hosted Genkai runner を前提とします。GitHub-hosted runner では、
必要な module、共有ビルドアーカイブ、PJM がないため動作しません。

push でのビルド有無は最新コミットメッセージで決まります。`[require-build]` を含めると
フルビルドし、含めなければ過去の成功アーカイブを再利用します。
