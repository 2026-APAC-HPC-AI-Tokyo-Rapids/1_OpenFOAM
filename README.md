# 1_OpenFOAM_HPC_Task

## OpenFOAM source mirror

The Genkai workflow builds OpenFOAM from organization-managed repositories. It
uses the following read-only bare mirrors as a shared Git object cache:

```text
/fast/pj26000080/git-mirror/
├── 3_OpenFOAM_Src.git
└── 4_OpenFOAM_ThirdParty_Src.git
```

OpenFOAM is checked out at `OpenFOAM-v2606`. The ThirdParty repository does not
have a v2606 tag, so the workflow uses its `main` branch as specified by the
source repository policy.

### One-time initialization

Run the initial download once from an SSH session on a Genkai login node. This
is intentionally not part of the GitHub Actions workflow.

```bash
install -d -m 2775 /fast/pj26000080/git-mirror

git clone --mirror \
  https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/3_OpenFOAM_Src.git \
  /fast/pj26000080/git-mirror/3_OpenFOAM_Src.git
git clone --mirror \
  https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/4_OpenFOAM_ThirdParty_Src.git \
  /fast/pj26000080/git-mirror/4_OpenFOAM_ThirdParty_Src.git

chgrp -R pj26000080 /fast/pj26000080/git-mirror
chmod -R g+rwX /fast/pj26000080/git-mirror
git -C /fast/pj26000080/git-mirror/3_OpenFOAM_Src.git \
  config core.sharedRepository group
git -C /fast/pj26000080/git-mirror/4_OpenFOAM_ThirdParty_Src.git \
  config core.sharedRepository group
```

The project group owns the directory, and setgid mode on its parent keeps new
entries in that group. Both repositories are caches only; no build job pushes
to them.

### Routine operation

Every workflow run invokes `scripts/update-source-mirrors.sh`. The script fetches
and prunes both mirrors, retries transient conflicts, and verifies the build
refs. If all fetch attempts fail but the required refs already exist, the last
complete mirror state remains usable. Builds then clone from the local mirrors,
so Git objects are not downloaded again for each build.
