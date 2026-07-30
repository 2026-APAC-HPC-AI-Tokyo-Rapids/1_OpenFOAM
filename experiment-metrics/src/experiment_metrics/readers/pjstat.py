from __future__ import annotations

from ..command import run

FIELDS = [
    "jid",
    "st",
    "sdt",
    "elp",
    "ec",
    "sn",
    "pc",
    "nnumu",
    "mmszu",
    "uctmut",
    "sctmut",
]


def read(job_id: str) -> dict[str, str]:
    result = run(
        [
            "pjstat",
            "--history",
            "-S",
            "--choose",
            ",".join(FIELDS),
            "--data",
            "--delimiter",
            "\t",
            job_id,
        ]
    )
    if result.returncode != 0:
        return {}
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return {}
    data = lines[-1].split("\t")
    if data and data[0] == "":
        data = data[1:]
    return dict(zip(FIELDS, data))
