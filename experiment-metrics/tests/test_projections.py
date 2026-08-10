from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request

from experiment_metrics.projections import (
    ProjectionBatch,
    resolve_projection_batches,
)
from experiment_metrics.registry import Registry

ROOT = Path(__file__).resolve().parents[1]


def _member(path: str, role: str, content: bytes):  # type: ignore[no-untyped-def]
    from experiment_metrics.artifact_store import ArchivedMember

    return ArchivedMember(
        path,
        len(content),
        hashlib.sha256(content).hexdigest(),
        role,
        content,
    )


def _registry() -> Registry:
    return Registry.load(ROOT / "registry/openfoam-v2.toml")


def _spec(identifier: str):  # type: ignore[no-untyped-def]
    return next(
        item
        for item in _registry().artifact_projections
        if item.identifier == identifier
    )


def _source_track_row(
    *, run_id: str = "r-" + "a" * 32, head: str = "b" * 40
) -> dict[str, object]:
    return {
        "schema_version": "source-track-projection/v1",
        "run_id": run_id,
        "run_purpose": "bench",
        "repository_identity": "apac2026-openfoam",
        "object_hash_algorithm": "sha1",
        "score_reference_commit": "c" * 40,
        "profile_base_commit": None,
        "source_head_commit": head,
        "source_track_manifest_sha256": "d" * 64,
        "source_member": "control/run-manifest.json",
        "source_sha256": "d" * 64,
    }


def test_registry_projection_machine_contract_is_exact_and_purpose_scoped() -> None:
    registry = _registry()

    assert {item.identifier for item in registry.artifact_projections} == {
        "openfoam.source_track",
        "openfoam.build_provenance",
        "openfoam.build_provision",
        "openfoam.minimal_hardware",
        "openfoam.workload_manifest",
        "openfoam.workload_member",
        "openfoam.profile_hardware",
        "openfoam.perf_counters",
        "openfoam.mpi_network",
    }
    profile_only = {
        item.identifier
        for item in registry.artifact_projections
        if item.applies_to("profile") and not item.applies_to("bench")
    }
    assert profile_only == {
        "openfoam.profile_hardware",
        "openfoam.perf_counters",
    }
    minimal = _spec("openfoam.minimal_hardware")
    assert minimal.row_schema_id == "minimal-hardware-projection/v1"
    assert minimal.row_grain == ("subject_id", "node_ordinal")
    workload_member = _spec("openfoam.workload_member")
    assert workload_member.parent_projection_id == "openfoam.workload_manifest"
    assert workload_member.parent_join_columns == ("subject_kind", "subject_id")
    assert workload_member.source_instance_grain is None


def test_projection_resolution_is_replay_idempotent_and_conflict_closed() -> None:
    spec = _spec("openfoam.source_track")
    row = _source_track_row()
    replay = ProjectionBatch(spec, '["run"]', "d" * 64, (row,))

    resolved = resolve_projection_batches((replay, replay))

    assert len(resolved.rows) == 1
    assert resolved.conflicts == ()
    assert resolved.rows[0]["_row_grain_key"] == '["r-' + "a" * 32 + '"]'
    assert set(resolved.rows[0]) == {
        "_projection_id",
        "_source_instance_key",
        "_source_instance_sha256",
        "_row_grain_key",
        "_payload_sha256",
        *row,
    }

    changed_source = ProjectionBatch(
        spec,
        '["run"]',
        "e" * 64,
        (_source_track_row(head="f" * 40),),
    )
    instance_conflict = resolve_projection_batches((replay, changed_source))
    assert instance_conflict.rows == ()
    assert [item.conflict_kind for item in instance_conflict.conflicts] == [
        "source_instance"
    ]

    same_instance_changed_payload = ProjectionBatch(
        spec,
        '["run"]',
        "d" * 64,
        (_source_track_row(head="f" * 40),),
    )
    grain_conflict = resolve_projection_batches((replay, same_instance_changed_payload))
    assert grain_conflict.rows == ()
    assert [item.conflict_kind for item in grain_conflict.conflicts] == ["row_grain"]


def test_parent_projection_has_no_manufactured_direct_lineage() -> None:
    spec = _spec("openfoam.workload_member")
    row = {
        "schema_version": "workload-member-projection/v1",
        "subject_kind": "regular_run",
        "subject_id": "r-" + "a" * 32,
        "path": "0/U",
        "content_b64": "YQ==",
    }

    batch = ProjectionBatch(spec, None, None, (row,))

    assert batch.insert_rows()[0]["_source_instance_key"] is None
    assert batch.insert_rows()[0]["_source_instance_sha256"] is None


def test_closed_source_track_workload_and_hardware_parsers_bind_lineage(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
) -> None:
    from experiment_metrics import RunManifest, init_run
    from experiment_metrics.artifact_store import (
        ArtifactMembers,
        ValidatedArtifactSet,
    )
    from experiment_metrics.projections import (
        _minimal_hardware,
        _source_track,
        _workload_manifest,
        _workload_members,
    )
    from experiment_metrics.protocol import RunProtocol
    from experiment_metrics.workload import WORKLOAD_MEMBERS

    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    manifest = RunManifest.load(manifest_path)
    artifact_set = ValidatedArtifactSet(manifest, tmp_path / "outer.json", (), ())
    protocol = RunProtocol.load(ROOT / "registry/openfoam-v2-protocol.toml", "bench")
    manifest_member = _member(
        "control/run-manifest.json", "run_manifest", manifest_path.read_bytes()
    )
    workload_rows = []
    workload_sources = []
    for index, relative in enumerate(WORKLOAD_MEMBERS):
        content = f"member-{index}\n".encode()
        workload_rows.append(
            {
                "path": relative,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
        workload_sources.append(
            _member(f"source/workload/{relative}", "workload_member", content)
        )
    workload_content = json.dumps(
        {"schema_version": "workload-manifest/v1", "members": workload_rows},
        separators=(",", ":"),
    ).encode()
    workload = _member(
        "source/workload-manifest.json", "workload_manifest", workload_content
    )
    hardware_content = json.dumps(
        {
            "schema_version": "hardware-node/v1",
            "node_ordinal": 0,
            "hostname": "node-a",
            "commands": {
                "lscpu": {
                    "argv": ["lscpu", "--json"],
                    "exit_code": 0,
                    "stderr_member": "source/hardware/lscpu-node-0.stderr.txt",
                }
            },
            "lscpu_json": {
                "lscpu": [
                    {"field": "Architecture:", "data": "x86_64"},
                    {"field": "Socket(s):", "data": "2"},
                    {"field": "Core(s) per socket:", "data": "4"},
                ]
            },
            "platform_settings": {
                "kernel_release": "6.0",
                "online_cpus": [0],
                "isolated_cpus": [],
                "nohz_full_cpus": [],
                "memory": {
                    "total_bytes": 1,
                    "hugepage_size_bytes": None,
                    "hugepages_total": None,
                },
                "numa_balancing_enabled": False,
                "boost": {"source_path": None, "raw": None, "enabled": None},
                "cpufreq_policies": [],
            },
        },
        separators=(",", ":"),
    ).encode()
    hardware = _member(
        "source/hardware/node-0.json", "minimal_hardware", hardware_content
    )
    members = ArtifactMembers(
        (manifest_member, workload, *workload_sources, hardware), ()
    )

    source = _source_track(
        _spec("openfoam.source_track"), artifact_set, members, protocol
    )
    workload_manifest = _workload_manifest(
        _spec("openfoam.workload_manifest"), artifact_set, members, protocol
    )
    workload_members = _workload_members(
        _spec("openfoam.workload_member"), artifact_set, members, protocol
    )
    minimal = _minimal_hardware(
        _spec("openfoam.minimal_hardware"), artifact_set, members, protocol
    )

    assert source.rows[0]["source_sha256"] == manifest_member.sha256
    assert workload_manifest.rows[0]["source_sha256"] == workload.sha256
    assert len(workload_members[0].rows) == 7
    assert workload_members[0].source_instance_key is None
    assert minimal[0].rows[0]["cpu_identity"]["physical_cores"] == 8
    assert "run_id" not in minimal[0].rows[0]


def test_projection_insert_identity_is_stable_across_publish_replay(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch,
) -> None:
    from experiment_metrics import RunManifest, init_run
    from experiment_metrics.artifact_store import RunPackager
    from experiment_metrics.publish import BigQueryConfig, publish_artifact_set

    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    manifest = RunManifest.load(manifest_path)
    run_dir = manifest.path.parents[1]
    (run_dir / "metrics.jsonl").write_text(
        json.dumps(
            {"run": manifest.run_id, "key": "artifact.test", "value": "a" * 64},
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    artifact = RunPackager().package(
        manifest_path,
        run_members=(("control/run-manifest.json", "run_manifest"),),
    )
    registry = _registry()
    spec = next(
        item
        for item in registry.artifact_projections
        if item.identifier == "openfoam.source_track"
    )
    row = _source_track_row(run_id=manifest.run_id)
    batch = ProjectionBatch(spec, '["run"]', "d" * 64, (row,))
    monkeypatch.setattr(
        "experiment_metrics.publish.project_artifact_set",
        lambda *args: (batch,),
    )
    requests: list[Request] = []

    def send(request: Request) -> bytes:
        requests.append(request)
        return b"{}"

    arguments = (
        manifest_path,
        artifact.manifest_path,
        BigQueryConfig("project", "dataset", "raw_table", "asia-northeast1"),
    )
    keywords = {
        "registry_path": ROOT / "registry/openfoam-v2.toml",
        "protocol_path": ROOT / "registry/openfoam-v2-protocol.toml",
        "request": send,
    }

    assert publish_artifact_set(*arguments, **keywords) == 2
    assert publish_artifact_set(*arguments, **keywords) == 2

    assert [request.full_url.rsplit("/", 2)[-2] for request in requests] == [
        "openfoam_source_tracks_base_v2",
        "raw_table",
        "openfoam_source_tracks_base_v2",
        "raw_table",
    ]
    first = json.loads(requests[0].data or b"{}")["rows"][0]
    replay = json.loads(requests[2].data or b"{}")["rows"][0]
    assert first["insertId"] == replay["insertId"]
    assert first["json"]["_source_instance_sha256"] == "d" * 64


def test_projection_rejection_prevents_raw_complete_fact_publication(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch,
) -> None:
    from experiment_metrics import RunManifest, init_run
    from experiment_metrics.artifact_store import RunPackager
    from experiment_metrics.publish import BigQueryConfig, publish_artifact_set

    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    manifest = RunManifest.load(manifest_path)
    run_dir = manifest.path.parents[1]
    (run_dir / "metrics.jsonl").write_text(
        json.dumps(
            {"run": manifest.run_id, "key": "collection_complete", "value": "true"},
            separators=(",", ":"),
        )
        + "\n"
    )
    artifact = RunPackager().package(
        manifest_path,
        run_members=(("control/run-manifest.json", "run_manifest"),),
    )
    batch = ProjectionBatch(
        _spec("openfoam.source_track"),
        '["run"]',
        "d" * 64,
        (_source_track_row(run_id=manifest.run_id),),
    )
    monkeypatch.setattr(
        "experiment_metrics.publish.project_artifact_set", lambda *args: (batch,)
    )
    requests: list[Request] = []

    def reject(request: Request) -> bytes:
        requests.append(request)
        return b'{"insertErrors":[{"index":0}]}'

    import pytest

    with pytest.raises(RuntimeError, match="rejected rows"):
        publish_artifact_set(
            manifest_path,
            artifact.manifest_path,
            BigQueryConfig("project", "dataset", "raw_table", "asia-northeast1"),
            registry_path=ROOT / "registry/openfoam-v2.toml",
            protocol_path=ROOT / "registry/openfoam-v2-protocol.toml",
            request=reject,
        )

    assert len(requests) == 1
    assert "/tables/openfoam_source_tracks_base_v2/" in requests[0].full_url
    assert "/tables/raw_table/" not in requests[0].full_url


def test_profile_hardware_and_perf_projection_require_complete_physical_axes(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
) -> None:
    from experiment_metrics import RunManifest, init_run
    from experiment_metrics.artifact_store import ArtifactMembers, ValidatedArtifactSet
    from experiment_metrics.projections import _perf, _profile_hardware
    from experiment_metrics.protocol import RunProtocol

    profile_identities = {
        **identities,
        "source_track": {
            **identities["source_track"],  # type: ignore[arg-type]
            "base_role": "profile_base",
        },
    }
    manifest_path = init_run(
        None,
        tmp_path,
        profile_identities,
        purpose="profile",
        registry_path=registry_path,
    )
    manifest = RunManifest.load(manifest_path)
    artifact_set = ValidatedArtifactSet(manifest, tmp_path / "outer.json", (), ())
    hardware = _member(
        "source/hardware/node-0.json",
        "minimal_hardware",
        json.dumps(
            {
                "schema_version": "hardware-node/v1",
                "node_ordinal": 0,
                "hostname": "node-a",
                "commands": {
                    "lscpu": {
                        "argv": ["lscpu", "--json"],
                        "exit_code": 0,
                        "stderr_member": "source/hardware/lscpu-node-0.stderr.txt",
                    }
                },
                "lscpu_json": None,
                "platform_settings": {
                    "kernel_release": None,
                    "online_cpus": None,
                    "isolated_cpus": None,
                    "nohz_full_cpus": None,
                    "memory": {
                        "total_bytes": None,
                        "hugepage_size_bytes": None,
                        "hugepages_total": None,
                    },
                    "numa_balancing_enabled": None,
                    "boost": {"source_path": None, "raw": None, "enabled": None},
                    "cpufreq_policies": None,
                },
            },
            separators=(",", ":"),
        ).encode(),
    )
    proc = _member(
        "profile/raw/hardware/node-0/proc-meminfo.txt",
        "profile",
        b"MemTotal: 200 kB\nMemAvailable: 100 kB\n",
    )
    cpulist = _member(
        "profile/raw/hardware/node-0/numa/node-0-cpulist.txt",
        "profile",
        b"0-1,2\n",
    )
    numa = _member(
        "profile/raw/hardware/node-0/numa/node-0-meminfo.txt",
        "profile",
        b"Node 0 MemTotal: 200 kB\nNode 0 MemFree: 50 kB\n",
    )
    capture_content = json.dumps(
        {
            "schema_version": "profile-hardware-capture/v1",
            "run_id": manifest.run_id,
            "node_ordinal": 0,
            "hostname": "node-a",
            "members": [
                {
                    "role": "numa_cpulist",
                    "numa_node_id": 0,
                    "path": cpulist.path,
                    "size_bytes": cpulist.size_bytes,
                    "sha256": cpulist.sha256,
                },
                {
                    "role": "numa_meminfo",
                    "numa_node_id": 0,
                    "path": numa.path,
                    "size_bytes": numa.size_bytes,
                    "sha256": numa.sha256,
                },
                {
                    "role": "proc_meminfo",
                    "numa_node_id": None,
                    "path": proc.path,
                    "size_bytes": proc.size_bytes,
                    "sha256": proc.sha256,
                },
            ],
        },
        separators=(",", ":"),
    ).encode()
    capture = _member(
        "profile/raw/hardware/node-0/capture.json", "profile", capture_content
    )
    perf_csv = _member(
        "profile/raw/perf/rank-0.csv",
        "profile",
        (
            b"1,,cycles,10,100,,\n"
            b"2,,instructions,10,100,,\n"
            b"3,,branches,10,100,,\n"
            b"4,,branch-misses,10,100,,\n"
            b"5,,cache-misses,10,100,,\n"
        ),
    )
    launch = _member(
        "profile/raw/perf/rank-0.json",
        "profile",
        json.dumps(
            {
                "schema_version": "openfoam-rank-launch/v1",
                "run_id": manifest.run_id,
                "global_rank": 0,
                "local_rank": 0,
                "local_size": 1,
                "hostname": "node-a",
                "cpu_affinity": [0],
                "numa_mems": "0",
                "argv": ["/opt/perf", "stat"],
                "environment": {"PMI_RANK": "0"},
                "output_member": perf_csv.path,
            },
            separators=(",", ":"),
        ).encode(),
    )
    members = ArtifactMembers(
        (hardware,), (capture, proc, cpulist, numa, perf_csv, launch)
    )
    protocol = RunProtocol(("solver",), 1, 1, "a-batch", "shm", "w", "a" * 64)

    hardware_rows = _profile_hardware(
        _spec("openfoam.profile_hardware"), artifact_set, members, protocol
    )
    perf_rows = _perf(_spec("openfoam.perf_counters"), artifact_set, members, protocol)

    assert [row["record_kind"] for row in hardware_rows[0].rows] == [
        "node_summary",
        "numa_node",
    ]
    assert hardware_rows[0].rows[0]["postrun_mem_available_bytes"] == 102400
    assert hardware_rows[0].rows[1]["cpulist"] == "0-2"
    assert [row["event_name"] for row in perf_rows[0].rows] == [
        "cycles",
        "instructions",
        "branches",
        "branch-misses",
        "cache-misses",
    ]
