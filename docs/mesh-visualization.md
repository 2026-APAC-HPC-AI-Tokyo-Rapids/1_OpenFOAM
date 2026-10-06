# ASPIRE-2Aの分割済みメッシュ回収

## 現在の回収状況

[回収Actions 37420126890](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/37420126890)でBonusは回収・zstd整合性検査に成功した。[Bonusのアーカイブ](https://mizuha-dev.com/files/openfoam-artifacts/37420126890/aspire2a/mesh-bonus/case.tar.zst)は8,661,745,718 bytesで、同じディレクトリの[recovery.json](https://mizuha-dev.com/files/openfoam-artifacts/37420126890/aspire2a/mesh-bonus/recovery.json)に来歴がある。

Basicは未回収。最初の試行は転送中のSSH応答タイムアウト、attempt 2は接続開始時のタイムアウトで失敗した。[読み取り接続診断](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/37446743081)でも約100秒で接続がタイムアウトした。接続復旧後のattempt 3は転送が再開したが、遅いためユーザー指示で停止し、`mesh-basic.incoming-3/case.tar.zst`の192,101,888 bytesを保持した。現在のworkflowはこの途中ファイルへrsyncで追記する。診断用workflowは削除済み。

## 回収方法

Actionsの **ASPIRE-2A mesh archive recovery** をmainから手動実行する。現在は未回収のBasicだけを対象とし、既存のhome-lab runner、home-lab-shell、aspire2a-shellを使う。rsyncのappend転送は、同じ変更されない原本から取得した途中ファイルを前提とする。途中ファイルを編集・置換しないこと。SSH接続の標準出力と両端のrsyncの利用可否は[機能確認run](https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM/actions/runs/37464223127)で確認済み。runner側のVPN・SSH接続が必要。ビルドやPBS投入は行わず、ASPIRE側のファイルを変更・削除しない。

| 対象 | 参照run | 分割 | cache_identity |
| --- | --- | --- | --- |
| Basic | 37206922099 | scotch | 98bcec2d9fc050ec941ae41d29d4d21855a42b63bfd64a532e61d2db92679634 |
| Bonus | 37217223164 | multiLevel (4 2 4 16) | b036b1f77a6c7485437b963d7653fc594460e8dd1983a1f5c7edc647cfc1f63c |

ASPIRE上の保存先は`/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/case-archives/<cache_identity>/`。保持済みのREADY、アーカイブmanifest、ケースmanifestから対象を確認する。転送が完了したら容量とzstdの整合性を検査し、実際のSHA-256・容量・参照run・回収commit・再開位置を`recovery.json`へ記録する。転送失敗や時間上限による終了では途中ファイルを保持する。次回は古いrunの再実行ではなく、mainの現在のworkflowを手動実行し、その時点の容量から続行する。同じ途中ファイルへ同時に書き込まないよう、Basic回収のjobを同時実行制御で制限する。

回収先はhome-labの`/hdd_raid/samba/net_share/openfoam-artifacts/37420126890/aspire2a/mesh-{basic,bonus}/`。公開サーバーでは`https://mizuha-dev.com/files/openfoam-artifacts/37420126890/aspire2a/mesh-{basic,bonus}/`から取得する。途中ファイルは同じ親ディレクトリの`mesh-basic.incoming-3/`に固定し、成功後に`mesh-basic/`へ切り替える。新しいActionsの実行IDとcommitは`recovery.json`に記録する。大容量アーカイブはGitHub artifactへ重複アップロードしない。公開済みのBasicは上書きせず、Bonusも保持する。

## ParaViewでの表示

それぞれ別の空ディレクトリへ`case.tar.zst`を展開し、ケース直下に空の`.foam`ファイルを作る。

```bash
mkdir basic-case
tar --zstd -xf case.tar.zst -C basic-case
touch basic-case/occDrivAerStaticMesh.foam
```

ParaViewで`.foam`を開き、Case TypeをDecomposed Case、Skip Zero Timeをオフにして読む。最初は場の配列を選ばず、必要なメッシュ領域だけを読む。BasicとBonusは同じカメラ・断面・表示範囲で比較する。ケースアーカイブは分割直後のメッシュと初期場であり、計算後の圧力・流速・後流の表示には使わない。
