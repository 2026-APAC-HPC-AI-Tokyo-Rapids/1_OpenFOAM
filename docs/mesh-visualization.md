# ASPIRE-2Aの分割済みメッシュ回収

Actionsの **ASPIRE-2A mesh archive recovery** をmainから手動実行する。既存のhome-lab runner、home-lab-shell、aspire2a-shellを使い、BasicとBonusの4ノード512分割のケースアーカイブを個別のjobで回収する。runner側のVPN・SSH接続が有効であることが必要。ビルドやPBS投入は行わず、ASPIRE側のファイルを変更・削除しない。

| 対象 | 参照run | 分割 | cache_identity |
| --- | --- | --- | --- |
| Basic | 37206922099 | scotch | 98bcec2d9fc050ec941ae41d29d4d21855a42b63bfd64a532e61d2db92679634 |
| Bonus | 37217223164 | multiLevel (4 2 4 16) | b036b1f77a6c7485437b963d7653fc594460e8dd1983a1f5c7edc647cfc1f63c |

ASPIRE上の保存先は`/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/case-archives/<cache_identity>/`。回収時はREADY、アーカイブmanifest、ケースmanifestから対象を確認し、zstdの整合性を検査する。取得したアーカイブのSHA-256・容量・参照run・回収commitは`recovery.json`へ記録する。転送や検証に失敗したjobは失敗し、未完了の回収先だけを削除する。成功した他方のjobやASPIRE原本は保持する。

回収先はhome-labの`/hdd_raid/samba/net_share/openfoam-artifacts/<回収Actions ID>/aspire2a/mesh-{basic,bonus}/`。公開サーバーでは`https://mizuha-dev.com/files/openfoam-artifacts/<回収Actions ID>/aspire2a/mesh-{basic,bonus}/`から取得する。大容量アーカイブはGitHub artifactへ重複アップロードしない。成功済みjobの再実行では同じ保存先を上書きしないため、必要な場合は失敗jobだけを再実行する。

## ParaViewでの表示

それぞれ別の空ディレクトリへ`case.tar.zst`を展開し、ケース直下に空の`.foam`ファイルを作る。

```bash
mkdir basic-case
tar --zstd -xf case.tar.zst -C basic-case
touch basic-case/occDrivAerStaticMesh.foam
```

ParaViewで`.foam`を開き、Case TypeをDecomposed Case、Skip Zero Timeをオフにして読む。最初は場の配列を選ばず、必要なメッシュ領域だけを読む。BasicとBonusは同じカメラ・断面・表示範囲で比較する。ケースアーカイブは分割直後のメッシュと初期場であり、計算後の圧力・流速・後流の表示には使わない。
