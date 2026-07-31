# 1_OpenFOAM_HPC_Task

## OpenFOAM source mirror

The Genkai workflow builds OpenFOAM from organization-managed repositories. It
uses the following read-only bare mirrors as a shared Git object cache:

```text
/fast/pj26000080/git-mirror/
├── 3_OpenFOAM_Src.git
└── 4_OpenFOAM_ThirdParty_Src.git
```

OpenFOAM is checked out from the organization-managed `master` branch, whose
current release line is v2606. The ThirdParty repository does not have a v2606
tag, so the workflow uses its `main` branch as specified by the source
repository policy.

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

Each source repository updates its own bare mirror from a serialized GitHub
Actions workflow after a push. This repository treats both mirrors as read-only
and only clones from them when a new build is required, so Git objects are not
downloaded again for each build.

The ThirdParty Git repository does not contain unpacked dependency sources. Its
`download-v2606-sources.sh` script retrieves the required archives through the
existing shared source cache and expands them into the build tree. The workflow
does not copy `sources/` from the monolithic ThirdParty release archive.
