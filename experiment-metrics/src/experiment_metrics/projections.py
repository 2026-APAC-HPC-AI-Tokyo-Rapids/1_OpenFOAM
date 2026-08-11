from __future__ import annotations

import base64
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .artifact_store import ArchivedMember, ArtifactMembers, ValidatedArtifactSet
from .build_provenance import validate_build_sidecar
from .fact import canonical_json
from .imb import parse_imb_mpi1, validate_imb_results
from .manifest import SHA256
from .postrun import _cpu_identity, _hardware
from .profile_perf import parse_perf_csv, project_perf_record
from .protocol import RunProtocol
from .provision import validate_provision_document
from .reducers import network_projection_rows
from .registry import ArtifactProjectionSpec, Registry
from .workload import WORKLOAD_MEMBERS

_REGISTRY_PROJECTION_IDS = frozenset(
    {
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
)
_PERF_PATH = re.compile(r"^profile/raw/perf/rank-([0-9]+)\.csv$")
_RANK_LAUNCH_PATH = re.compile(r"^profile/raw/perf/rank-([0-9]+)\.json$")
_HARDWARE_PATH = re.compile(r"^source/hardware/node-([0-9]+)\.json$")
_PROFILE_CAPTURE = re.compile(r"^profile/raw/hardware/node-([0-9]+)/capture\.json$")
_PROFILE_MEMBER_ROLES = ("capture", "proc_meminfo", "numa_cpulist", "numa_meminfo")
_PROFILE_CAPTURE_MEMBER_ROLES = frozenset(_PROFILE_MEMBER_ROLES[1:])
_WORKLOAD_SET = frozenset(WORKLOAD_MEMBERS)
_UINT_MAX = (1 << 64) - 1


@dataclass(frozen=True, slots=True)
class ProjectionBatch:
    spec: ArtifactProjectionSpec
    source_instance_key: str | None
    source_instance_sha256: str | None
    rows: tuple[dict[str, object], ...]

    def __post_init__(self) -> None:
        if not self.rows:
            raise ValueError(f"empty artifact projection: {self.spec.identifier}")
        if self.spec.parent_projection_id is None:
            if not self.source_instance_key or not self.source_instance_sha256:
                raise ValueError("direct projection requires source instance identity")
            _sha256(self.source_instance_sha256)
        elif (
            self.source_instance_key is not None
            or self.source_instance_sha256 is not None
        ):
            raise ValueError("parent projection cannot manufacture source identity")
        for row in self.rows:
            _closed_projection_row(self.spec, row)

    def insert_rows(self) -> tuple[dict[str, object], ...]:
        result: list[dict[str, object]] = []
        for payload in self.rows:
            payload_json = canonical_json(_json_value(payload))
            grain = [payload[name] for name in self.spec.row_grain]
            envelope: dict[str, object] = {
                "_projection_id": self.spec.identifier,
                "_source_instance_key": self.source_instance_key,
                "_source_instance_sha256": self.source_instance_sha256,
                "_row_grain_key": canonical_json(_json_value(grain)),
                "_payload_sha256": hashlib.sha256(payload_json.encode()).hexdigest(),
                **_json_value(payload),
            }
            result.append(envelope)
        return tuple(result)


@dataclass(frozen=True, slots=True)
class ProjectionConflict:
    projection_id: str
    conflict_kind: str
    grain_key: str
    rows: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class ProjectionResolution:
    rows: tuple[dict[str, object], ...]
    conflicts: tuple[ProjectionConflict, ...]


def resolve_projection_batches(
    batches: tuple[ProjectionBatch, ...],
) -> ProjectionResolution:
    """Apply the v1 instance-conflict, exact-dedupe, then grain-conflict rules."""

    if not batches:
        return ProjectionResolution((), ())
    projection_id = batches[0].spec.identifier
    if any(batch.spec.identifier != projection_id for batch in batches):
        raise ValueError("projection resolution cannot mix registry entries")
    excluded: set[int] = set()
    conflicts: list[ProjectionConflict] = []
    by_instance: dict[str, list[int]] = defaultdict(list)
    for index, batch in enumerate(batches):
        if batch.source_instance_key is not None:
            by_instance[batch.source_instance_key].append(index)
    for key, indexes in sorted(by_instance.items()):
        hashes = {batches[index].source_instance_sha256 for index in indexes}
        if len(hashes) > 1:
            excluded.update(indexes)
            rows = tuple(
                row for index in indexes for row in batches[index].insert_rows()
            )
            conflicts.append(
                ProjectionConflict(projection_id, "source_instance", key, rows)
            )

    unique: dict[str, dict[str, object]] = {}
    for index, batch in enumerate(batches):
        if index in excluded:
            continue
        for row in batch.insert_rows():
            unique.setdefault(canonical_json(_json_value(row)), row)
    by_grain: dict[str, list[dict[str, object]]] = defaultdict(list)
    for identity in sorted(unique):
        row = unique[identity]
        by_grain[str(row["_row_grain_key"])].append(row)
    accepted: list[dict[str, object]] = []
    for grain, rows in sorted(by_grain.items()):
        payloads = {str(row["_payload_sha256"]) for row in rows}
        if len(payloads) == 1:
            accepted.append(rows[0])
        else:
            conflicts.append(
                ProjectionConflict(projection_id, "row_grain", grain, tuple(rows))
            )
    return ProjectionResolution(tuple(accepted), tuple(conflicts))


def project_artifact_set(
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    registry: Registry,
    protocol: RunProtocol,
) -> tuple[ProjectionBatch, ...]:
    """Parse all and only purpose-applicable registry projections."""

    by_id = {item.identifier: item for item in registry.artifact_projections}
    if frozenset(by_id) != _REGISTRY_PROJECTION_IDS:
        raise ValueError("publisher projection implementation differs from registry")
    manifest = artifact_set.manifest
    if protocol.ranks <= 0 or protocol.nodes <= 0:
        raise ValueError("projection protocol axes are invalid")
    factories = {
        "openfoam.source_track": _source_track,
        "openfoam.build_provenance": _build_provenance,
        "openfoam.build_provision": _build_provision,
        "openfoam.minimal_hardware": _minimal_hardware,
        "openfoam.workload_manifest": _workload_manifest,
        "openfoam.workload_member": _workload_members,
        "openfoam.profile_hardware": _profile_hardware,
        "openfoam.perf_counters": _perf,
        "openfoam.mpi_network": _mpi_network,
    }
    batches: list[ProjectionBatch] = []
    for identifier, spec in by_id.items():
        if not spec.applies_to(manifest.purpose):
            continue
        made = factories[identifier](spec, artifact_set, members, protocol)
        batches.extend(made if isinstance(made, tuple) else (made,))
    return tuple(batches)


def _source_track(
    spec: ArtifactProjectionSpec,
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    protocol: RunProtocol,
) -> ProjectionBatch:
    del protocol
    manifest = artifact_set.manifest
    source = members.run("control/run-manifest.json", role="run_manifest")
    if source.content != manifest.path.read_bytes():
        raise ValueError("archived subject manifest differs from publisher manifest")
    track = manifest.source_track
    base = str(track["base_commit"])
    row = {
        "schema_version": "source-track-projection/v1",
        "run_id": manifest.run_id,
        "run_purpose": manifest.purpose,
        "repository_identity": manifest.repository_id,
        "object_hash_algorithm": track["object_hash_algorithm"],
        "score_reference_commit": base if manifest.purpose == "bench" else None,
        "profile_base_commit": base if manifest.purpose == "profile" else None,
        "source_head_commit": track["head_commit"],
        "source_track_manifest_sha256": source.sha256,
        "source_member": source.path,
        "source_sha256": source.sha256,
    }
    return _batch(spec, row, artifact_set.manifest.run_id)


def _build_provenance(
    spec: ArtifactProjectionSpec,
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    protocol: RunProtocol,
) -> ProjectionBatch:
    del artifact_set, protocol
    source = members.run("control/build-sidecar.json", role="build_sidecar")
    document = _json_object(source.content, "build sidecar")
    validate_build_sidecar(document)
    observations: list[dict[str, object]] = []
    for command in document["toolchain_commands"]:
        assert isinstance(command, dict)
        stdout = _referenced_run_member(members, command["stdout"])
        stderr = _referenced_run_member(members, command["stderr"])
        observations.append(
            {
                "role": command["role"],
                "outcome": command["outcome"],
                "stdout_member": stdout.path,
                "stdout_b64": _b64(stdout.content),
                "stderr_member": stderr.path,
                "stderr_b64": _b64(stderr.content),
            }
        )
    archive = document["build_archive"]
    assert isinstance(archive, dict)
    row = {
        "schema_version": "build-provenance-projection/v1",
        "precision": document["precision"],
        "label_bits": document["label_bits"],
        "compile_flags": document["compile_flags"],
        "commits": document["source_commits"],
        "build_archive_sha256": archive["sha256"],
        "toolchain_observations": observations,
        "runtime_objects": document["runtime_objects"],
        "source_member": source.path,
        "source_sha256": source.sha256,
    }
    return _batch(spec, row, source.sha256)


def _build_provision(
    spec: ArtifactProjectionSpec,
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    protocol: RunProtocol,
) -> ProjectionBatch:
    del protocol
    manifest = artifact_set.manifest
    source = members.run(
        "control/build-provision-validation.json", role="build_provision_validation"
    )
    document = _json_object(source.content, "build provision validation")
    validate_provision_document(document, purpose=manifest.purpose)
    build_sidecar = members.run("control/build-sidecar.json", role="build_sidecar")
    if document["build_sidecar_sha256"] != build_sidecar.sha256:
        raise ValueError("provision validation refers to a different build sidecar")
    ldd_sources = []
    for item in document["ldd_raw"]:
        assert isinstance(item, dict)
        raw = _referenced_run_member(members, item["source"])
        ldd_sources.append(
            {
                "role": item["role"],
                "source_member": raw.path,
                "content_b64": _b64(raw.content),
            }
        )
    launcher = _version_projection(document["launcher_version"], members)
    profiler = (
        _version_projection(document["profiler_version"], members)
        if manifest.purpose == "profile"
        else {
            "argv": None,
            "outcome": None,
            "stdout_member": None,
            "stdout_b64": None,
            "stderr_member": None,
            "stderr_b64": None,
        }
    )
    libmpi = document["resolved_libmpi"]
    assert isinstance(libmpi, dict)
    row = {
        "schema_version": "build-provision-projection/v1",
        "run_id": manifest.run_id,
        "build_sidecar_sha256": document["build_sidecar_sha256"],
        "executables": document["executables"],
        "ldd_sources": ldd_sources,
        "launcher_version": launcher,
        "profiler_version": profiler,
        "resolved_libmpi_path": libmpi["path"],
        "resolved_libmpi_sha256": libmpi["sha256"],
        "source_member": source.path,
        "source_sha256": source.sha256,
    }
    return _batch(spec, row, manifest.run_id)


def _minimal_hardware(
    spec: ArtifactProjectionSpec,
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    protocol: RunProtocol,
) -> tuple[ProjectionBatch, ...]:
    manifest = artifact_set.manifest
    sources = members.run_by_role("minimal_hardware")
    if len(sources) != protocol.nodes:
        raise ValueError("minimal hardware source count differs from protocol nodes")
    batches = []
    ordinals: set[int] = set()
    for source in sources:
        match = _HARDWARE_PATH.fullmatch(source.path)
        if match is None:
            raise ValueError("minimal hardware source path is invalid")
        document = _json_object(source.content, "minimal hardware")
        _hardware(document)
        ordinal = int(match[1])
        if document["node_ordinal"] != ordinal:
            raise ValueError("minimal hardware ordinal differs from source path")
        ordinals.add(ordinal)
        row = {
            "schema_version": "minimal-hardware-projection/v1",
            "subject_kind": "regular_run",
            "subject_id": manifest.run_id,
            "run_id": manifest.run_id,
            "node_ordinal": ordinal,
            "hostname": document["hostname"],
            "cpu_identity": _cpu_identity(document["lscpu_json"]),
            "platform_settings": document["platform_settings"],
            "source_member": source.path,
            "source_sha256": source.sha256,
        }
        # run_id is physical lineage context, not part of the logical row schema.
        batch = _batch(spec, row, manifest.run_id, logical_extras={"run_id"})
        batches.append(batch)
    if ordinals != set(range(protocol.nodes)):
        raise ValueError("minimal hardware node ordinal set is incomplete")
    return tuple(batches)


def _workload_manifest(
    spec: ArtifactProjectionSpec,
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    protocol: RunProtocol,
) -> ProjectionBatch:
    del protocol
    manifest = artifact_set.manifest
    source = members.run("source/workload-manifest.json", role="workload_manifest")
    document = _workload_document(source.content)
    identity = hashlib.sha256(canonical_json(document["members"]).encode()).hexdigest()
    row = {
        "schema_version": "workload-manifest-projection/v1",
        "subject_kind": "regular_run",
        "subject_id": manifest.run_id,
        "workload_identity": identity,
        "source_member": source.path,
        "source_sha256": source.sha256,
    }
    return _batch(spec, row, manifest.run_id)


def _workload_members(
    spec: ArtifactProjectionSpec,
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    protocol: RunProtocol,
) -> tuple[ProjectionBatch, ...]:
    del protocol
    manifest = artifact_set.manifest
    source = members.run("source/workload-manifest.json", role="workload_manifest")
    document = _workload_document(source.content)
    rows: list[dict[str, object]] = []
    for declared in document["members"]:
        relative = declared["path"]
        raw = members.run(f"source/workload/{relative}", role="workload_member")
        if raw.size_bytes != declared["size_bytes"] or raw.sha256 != declared["sha256"]:
            raise ValueError(f"workload member differs from manifest: {relative}")
        rows.append(
            {
                "schema_version": "workload-member-projection/v1",
                "subject_kind": "regular_run",
                "subject_id": manifest.run_id,
                "path": relative,
                "content_b64": _b64(raw.content),
            }
        )
    return (ProjectionBatch(spec, None, None, tuple(rows)),)


def _profile_hardware(
    spec: ArtifactProjectionSpec,
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    protocol: RunProtocol,
) -> tuple[ProjectionBatch, ...]:
    manifest = artifact_set.manifest
    captures = [
        member
        for member in members.profile_raw
        if _PROFILE_CAPTURE.fullmatch(member.path)
    ]
    if len(captures) != protocol.nodes:
        raise ValueError("profile hardware capture count differs from protocol nodes")
    minimal = {
        int(_HARDWARE_PATH.fullmatch(item.path)[1]): _json_object(
            item.content, "minimal hardware"
        )
        for item in members.run_by_role("minimal_hardware")
        if _HARDWARE_PATH.fullmatch(item.path)
    }
    batches: list[ProjectionBatch] = []
    ordinals: set[int] = set()
    for capture in sorted(captures, key=lambda item: item.path.encode()):
        document = _profile_capture_document(capture.content, manifest.run_id)
        ordinal = document["node_ordinal"]
        assert isinstance(ordinal, int)
        match = _PROFILE_CAPTURE.fullmatch(capture.path)
        assert match is not None
        if int(match[1]) != ordinal:
            raise ValueError("profile hardware ordinal differs from capture path")
        if ordinal in ordinals:
            raise ValueError("duplicate profile hardware node ordinal")
        ordinals.add(ordinal)
        minimal_source = minimal.get(ordinal)
        if minimal_source is None or minimal_source["hostname"] != document["hostname"]:
            raise ValueError("profile and minimal hardware node identities differ")
        capture_lineage = {
            "role": "capture",
            "path": capture.path,
            "sha256": capture.sha256,
        }
        declared = document["members"]
        proc_declared = [item for item in declared if item["role"] == "proc_meminfo"]
        if len(proc_declared) != 1:
            raise ValueError("profile hardware needs one proc meminfo source")
        proc = _profile_source(members, proc_declared[0])
        postrun = _mem_available(proc.content)
        rows: list[dict[str, object]] = [
            {
                "schema_version": "profile-hardware-projection/v1",
                "run_id": manifest.run_id,
                "node_ordinal": ordinal,
                "hostname": document["hostname"],
                "record_kind": "node_summary",
                "numa_node_id": None,
                "postrun_mem_available_bytes": postrun,
                "cpulist": None,
                "mem_total_bytes": None,
                "mem_free_bytes": None,
                "source_members": [
                    capture_lineage,
                    {"role": "proc_meminfo", "path": proc.path, "sha256": proc.sha256},
                ],
            }
        ]
        node_ids = sorted(
            {
                item["numa_node_id"]
                for item in declared
                if item["role"] in {"numa_cpulist", "numa_meminfo"}
            }
        )
        for node_id in node_ids:
            pair = [item for item in declared if item["numa_node_id"] == node_id]
            if [item["role"] for item in pair] != ["numa_cpulist", "numa_meminfo"]:
                raise ValueError("profile NUMA source roles are incomplete")
            cpulist = _profile_source(members, pair[0])
            meminfo = _profile_source(members, pair[1])
            mem_total, mem_free = _numa_meminfo(meminfo.content, node_id)
            rows.append(
                {
                    "schema_version": "profile-hardware-projection/v1",
                    "run_id": manifest.run_id,
                    "node_ordinal": ordinal,
                    "hostname": document["hostname"],
                    "record_kind": "numa_node",
                    "numa_node_id": node_id,
                    "postrun_mem_available_bytes": None,
                    "cpulist": _canonical_cpu_list(cpulist.content),
                    "mem_total_bytes": mem_total,
                    "mem_free_bytes": mem_free,
                    "source_members": [
                        capture_lineage,
                        {
                            "role": "numa_cpulist",
                            "path": cpulist.path,
                            "sha256": cpulist.sha256,
                        },
                        {
                            "role": "numa_meminfo",
                            "path": meminfo.path,
                            "sha256": meminfo.sha256,
                        },
                    ],
                }
            )
        batches.append(_batch(spec, rows, manifest.run_id))
    if ordinals != set(range(protocol.nodes)):
        raise ValueError("profile hardware node ordinal set is incomplete")
    return tuple(batches)


def _perf(
    spec: ArtifactProjectionSpec,
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    protocol: RunProtocol,
) -> tuple[ProjectionBatch, ...]:
    run_id = artifact_set.manifest.run_id
    sources: dict[int, ArchivedMember] = {}
    launches: dict[int, ArchivedMember] = {}
    for member in members.profile_raw:
        match = _PERF_PATH.fullmatch(member.path)
        if match is not None:
            rank = int(match[1])
            if rank in sources:
                raise ValueError("duplicate profile perf rank")
            sources[rank] = member
        launch_match = _RANK_LAUNCH_PATH.fullmatch(member.path)
        if launch_match is not None:
            rank = int(launch_match[1])
            if rank in launches:
                raise ValueError("duplicate profile rank launch source")
            launches[rank] = member
    if set(sources) != set(range(protocol.ranks)):
        raise ValueError("profile perf rank source set is incomplete")
    if set(launches) != set(range(protocol.ranks)):
        raise ValueError("profile rank launch source set is incomplete")
    batches = []
    for rank, source in sorted(sources.items()):
        _rank_launch_document(launches[rank].content, run_id, rank, source.path)
        record = parse_perf_csv(
            source.content.decode("utf-8"),
            run_id=run_id,
            global_rank=rank,
            source_member=source.path,
            source_sha256=source.sha256,
        )
        rows = []
        for projected in project_perf_record(record):
            item = projected.item
            rows.append(
                _json_value(
                    {
                        "schema_version": "perf-counter-projection/v1",
                        "run_id": run_id,
                        "global_rank": rank,
                        "event_name": item.event_name,
                        "raw_count_lexeme": item.raw_count_lexeme,
                        "count": item.count,
                        "unit": item.unit,
                        "running_ns_lexeme": item.running_ns_lexeme,
                        "running_ns": item.running_ns,
                        "percent_running_lexeme": item.percent_running_lexeme,
                        "percent_running": item.percent_running,
                        "metric_value_lexeme": item.metric_value_lexeme,
                        "metric_unit": item.metric_unit,
                        "source_member": source.path,
                        "source_sha256": source.sha256,
                    }
                )
            )
        batches.append(_batch(spec, rows, run_id))
    return tuple(batches)


def _mpi_network(
    spec: ArtifactProjectionSpec,
    artifact_set: ValidatedArtifactSet,
    members: ArtifactMembers,
    protocol: RunProtocol,
) -> ProjectionBatch:
    run_id = artifact_set.manifest.run_id
    stdout = members.run("source/network/imb-mpi1/stdout.txt", role="imb_mpi1_stdout")
    members.run("source/network/imb-mpi1/stderr.txt", role="imb_mpi1_stderr")
    argv_source = members.run("source/network/imb-mpi1/argv.json", role="imb_mpi1_argv")
    argv_document = _json_object(argv_source.content, "IMB argv")
    _validate_imb_argv(argv_document, protocol)
    results = parse_imb_mpi1(stdout.content.decode("utf-8", errors="strict"))
    validate_imb_results(results, protocol.ranks)
    rows = network_projection_rows(run_id, results, stdout.path)
    return _batch(spec, list(rows), run_id, source_sha256=stdout.sha256)


def _batch(
    spec: ArtifactProjectionSpec,
    rows: dict[str, object] | list[dict[str, object]],
    run_id: str,
    *,
    source_sha256: str | None = None,
    logical_extras: set[str] | None = None,
) -> ProjectionBatch:
    values = [rows] if isinstance(rows, dict) else rows
    normalized: list[dict[str, object]] = []
    instance_keys: set[str] = set()
    for value in values:
        item = dict(value)
        extras = logical_extras or set()
        instance_context = {"run_id": run_id, **item}
        if "source_member" not in instance_context and isinstance(
            item.get("source_members"), list
        ):
            capture_members = [
                member
                for member in item["source_members"]
                if isinstance(member, dict) and member.get("role") == "capture"
            ]
            if len(capture_members) == 1:
                instance_context["source_member"] = capture_members[0].get("path")
        instance_parts = [
            instance_context[name] for name in spec.source_instance_grain or ()
        ]
        instance_keys.add(canonical_json(_json_value(instance_parts)))
        if extras:
            for name in extras:
                item.pop(name, None)
        normalized.append(item)
    if len(instance_keys) != 1:
        raise ValueError("projection batch crosses source-instance grain")
    instance_key = instance_keys.pop()
    digest = source_sha256 or _lineage_sha(spec, normalized[0])
    return ProjectionBatch(spec, instance_key, digest, tuple(normalized))


def _lineage_sha(spec: ArtifactProjectionSpec, row: dict[str, object]) -> str:
    field = spec.source_instance_sha256_field
    if field == "source_sha256":
        value = row.get("source_sha256")
    elif field == "source_members.capture.sha256":
        matches = [
            item["sha256"]
            for item in row.get("source_members", [])
            if isinstance(item, dict) and item.get("role") == "capture"
        ]
        value = matches[0] if len(matches) == 1 else None
    else:
        value = None
    if not isinstance(value, str):
        raise ValueError(f"cannot resolve projection lineage SHA: {field}")
    _sha256(value)
    return value


def _closed_projection_row(
    spec: ArtifactProjectionSpec, row: dict[str, object]
) -> None:
    expected = _ROW_FIELDS.get(spec.row_schema_id)
    if expected is None or set(row) != expected:
        raise ValueError(f"{spec.row_schema_id} row is not closed: {sorted(set(row))}")
    if row.get("schema_version", spec.row_schema_id) != spec.row_schema_id:
        raise ValueError("projection row schema version differs from registry")
    if any(name not in row for name in spec.row_grain):
        raise ValueError("projection row is missing its registry grain")


_ROW_FIELDS = {
    "source-track-projection/v1": {
        "schema_version",
        "run_id",
        "run_purpose",
        "repository_identity",
        "object_hash_algorithm",
        "score_reference_commit",
        "profile_base_commit",
        "source_head_commit",
        "source_track_manifest_sha256",
        "source_member",
        "source_sha256",
    },
    "build-provenance-projection/v1": {
        "schema_version",
        "precision",
        "label_bits",
        "compile_flags",
        "commits",
        "build_archive_sha256",
        "toolchain_observations",
        "runtime_objects",
        "source_member",
        "source_sha256",
    },
    "build-provision-projection/v1": {
        "schema_version",
        "run_id",
        "build_sidecar_sha256",
        "executables",
        "ldd_sources",
        "launcher_version",
        "profiler_version",
        "resolved_libmpi_path",
        "resolved_libmpi_sha256",
        "source_member",
        "source_sha256",
    },
    "minimal-hardware-projection/v1": {
        "schema_version",
        "subject_kind",
        "subject_id",
        "node_ordinal",
        "hostname",
        "cpu_identity",
        "platform_settings",
        "source_member",
        "source_sha256",
    },
    "workload-manifest-projection/v1": {
        "schema_version",
        "subject_kind",
        "subject_id",
        "workload_identity",
        "source_member",
        "source_sha256",
    },
    "workload-member-projection/v1": {
        "schema_version",
        "subject_kind",
        "subject_id",
        "path",
        "content_b64",
    },
    "profile-hardware-projection/v1": {
        "schema_version",
        "run_id",
        "node_ordinal",
        "hostname",
        "record_kind",
        "numa_node_id",
        "postrun_mem_available_bytes",
        "cpulist",
        "mem_total_bytes",
        "mem_free_bytes",
        "source_members",
    },
    "perf-counter-projection/v1": {
        "schema_version",
        "run_id",
        "global_rank",
        "event_name",
        "raw_count_lexeme",
        "count",
        "unit",
        "running_ns_lexeme",
        "running_ns",
        "percent_running_lexeme",
        "percent_running",
        "metric_value_lexeme",
        "metric_unit",
        "source_member",
        "source_sha256",
    },
    "mpi-network-result/v2": {
        "run_id",
        "benchmark",
        "process_count",
        "message_bytes",
        "iterations",
        "time_min_us",
        "time_avg_us",
        "time_max_us",
        "bandwidth_mbytes_per_sec",
        "source_member",
    },
}


def _referenced_run_member(
    members: ArtifactMembers, declaration: object
) -> ArchivedMember:
    if not isinstance(declaration, dict) or set(declaration) != {
        "path",
        "size_bytes",
        "sha256",
    }:
        raise ValueError("referenced source member is not closed")
    member = members.run(str(declaration["path"]))
    if (
        member.size_bytes != declaration["size_bytes"]
        or member.sha256 != declaration["sha256"]
    ):
        raise ValueError(f"referenced source identity mismatch: {member.path}")
    return member


def _version_projection(value: object, members: ArtifactMembers) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("version observation is invalid")
    stdout = _referenced_run_member(members, value["stdout"])
    stderr = _referenced_run_member(members, value["stderr"])
    return {
        "argv": value["argv"],
        "outcome": value["outcome"],
        "stdout_member": stdout.path,
        "stdout_b64": _b64(stdout.content),
        "stderr_member": stderr.path,
        "stderr_b64": _b64(stderr.content),
    }


def _workload_document(content: bytes) -> dict[str, Any]:
    document = _json_object(content, "workload manifest")
    if (
        set(document) != {"schema_version", "members"}
        or document["schema_version"] != "workload-manifest/v1"
    ):
        raise ValueError("workload manifest is not a closed v1 object")
    rows = document["members"]
    if not isinstance(rows, list) or [
        item.get("path") if isinstance(item, dict) else None for item in rows
    ] != list(WORKLOAD_MEMBERS):
        raise ValueError("workload manifest has the wrong member set/order")
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "size_bytes", "sha256"}:
            raise ValueError("workload manifest member is not closed")
        _uint(row["size_bytes"])
        _sha256(row["sha256"])
    return document


def _profile_capture_document(content: bytes, run_id: str) -> dict[str, Any]:
    document = _json_object(content, "profile hardware capture")
    if (
        set(document)
        != {"schema_version", "run_id", "node_ordinal", "hostname", "members"}
        or document["schema_version"] != "profile-hardware-capture/v1"
        or document["run_id"] != run_id
    ):
        raise ValueError("profile hardware capture is not a bound closed v1 object")
    _uint(document["node_ordinal"])
    if not isinstance(document["hostname"], str) or not document["hostname"]:
        raise ValueError("profile hardware hostname is invalid")
    raw_members = document["members"]
    if not isinstance(raw_members, list):
        raise ValueError("profile hardware source members are invalid")
    keys = []
    for item in raw_members:
        if (
            not isinstance(item, dict)
            or set(item) != {"role", "numa_node_id", "path", "size_bytes", "sha256"}
            or item["role"] not in _PROFILE_CAPTURE_MEMBER_ROLES
        ):
            raise ValueError("profile hardware member is not closed")
        if item["role"] == "proc_meminfo":
            if item["numa_node_id"] is not None:
                raise ValueError("proc meminfo must have null NUMA node")
        else:
            _uint(item["numa_node_id"])
        _uint(item["size_bytes"])
        _sha256(item["sha256"])
        keys.append(
            (
                item["role"].encode(),
                -1 if item["numa_node_id"] is None else item["numa_node_id"],
                item["path"].encode(),
            )
        )
    if keys != sorted(set(keys)):
        raise ValueError("profile hardware members are not canonical")
    return document


def _profile_source(
    members: ArtifactMembers, declaration: dict[str, Any]
) -> ArchivedMember:
    source = members.profile(declaration["path"])
    if (
        source.size_bytes != declaration["size_bytes"]
        or source.sha256 != declaration["sha256"]
    ):
        raise ValueError(f"profile hardware source identity mismatch: {source.path}")
    return source


def _rank_launch_document(
    content: bytes, run_id: str, rank: int, output_member: str
) -> None:
    document = _json_object(content, "profile rank launch")
    fields = {
        "schema_version",
        "run_id",
        "global_rank",
        "local_rank",
        "local_size",
        "hostname",
        "cpu_affinity",
        "numa_mems",
        "argv",
        "environment",
        "output_member",
    }
    if (
        set(document) != fields
        or document["schema_version"] != "openfoam-rank-launch/v1"
        or document["run_id"] != run_id
        or document["global_rank"] != rank
        or document["output_member"] != output_member
    ):
        raise ValueError("profile rank launch is not a bound closed v1 object")
    local_rank = _uint(document["local_rank"])
    local_size = _uint(document["local_size"])
    if local_size == 0 or local_rank >= local_size:
        raise ValueError("profile rank launch local axes are invalid")
    if not isinstance(document["hostname"], str) or not document["hostname"]:
        raise ValueError("profile rank launch hostname is invalid")
    affinity = document["cpu_affinity"]
    if (
        not isinstance(affinity, list)
        or affinity != sorted(set(affinity))
        or any(isinstance(item, bool) or not isinstance(item, int) for item in affinity)
    ):
        raise ValueError("profile rank launch affinity is invalid")
    if not isinstance(document["argv"], list) or not all(
        isinstance(item, str) and item for item in document["argv"]
    ):
        raise ValueError("profile rank launch argv is invalid")
    if not isinstance(document["environment"], dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in document["environment"].items()
    ):
        raise ValueError("profile rank launch environment is invalid")


def _mem_available(content: bytes) -> int:
    matches = re.findall(
        rb"(?m)^MemAvailable:[ \t]+([0-9]+)[ \t]+kB$", content.decode("ascii").encode()
    )
    if len(matches) != 1:
        raise ValueError("profile meminfo requires one MemAvailable kB value")
    return _kb(int(matches[0]))


def _numa_meminfo(content: bytes, node_id: int) -> tuple[int, int]:
    text = content.decode("ascii")
    matches = re.findall(
        r"(?m)^Node ([0-9]+) (MemTotal|MemFree):[ \t]+([0-9]+)[ \t]+kB$", text
    )
    if (
        len(matches) != 2
        or {kind for _, kind, _ in matches} != {"MemTotal", "MemFree"}
        or {int(node) for node, _, _ in matches} != {node_id}
    ):
        raise ValueError("profile NUMA meminfo is incomplete or foreign")
    values = {kind: _kb(int(value)) for _, kind, value in matches}
    return values["MemTotal"], values["MemFree"]


def _canonical_cpu_list(content: bytes) -> str:
    text = content.decode("ascii").strip()
    if not text:
        return ""
    cpus: set[int] = set()
    for token in text.split(","):
        match = re.fullmatch(r"([0-9]+)(?:-([0-9]+))?", token)
        if match is None:
            raise ValueError("profile CPU list has invalid grammar")
        start, end = int(match[1]), int(match[2] or match[1])
        if end < start:
            raise ValueError("profile CPU range is reversed")
        cpus.update(range(start, end + 1))
    ordered = sorted(cpus)
    ranges: list[str] = []
    start = previous = ordered[0]
    for cpu in ordered[1:]:
        if cpu == previous + 1:
            previous = cpu
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = cpu
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(ranges)


def _validate_imb_argv(document: dict[str, Any], protocol: RunProtocol) -> None:
    if (
        set(document) != {"schema_version", "argv"}
        or document["schema_version"] != "argv/v1"
        or not isinstance(document["argv"], list)
    ):
        raise ValueError("IMB argv is not a closed argv/v1 object")
    argv = document["argv"]
    if (
        len(argv) != 19
        or not all(isinstance(item, str) and item for item in argv)
        or not argv[0].startswith("/")
        or not argv[5].startswith("/")
    ):
        raise ValueError("IMB argv does not have the closed command shape")
    expected = [
        "-np",
        str(protocol.ranks),
        "-ppn",
        str(protocol.ranks_per_node),
        argv[5],
        "-npmin",
        str(protocol.ranks),
        "-msglog",
        "0:22",
        "-iter",
        "1000",
        "-time",
        "1",
        "-iter_policy",
        "dynamic",
        "PingPong",
        "Sendrecv",
        "Allreduce",
    ]
    if argv[1:] != expected:
        raise ValueError("IMB argv differs from the protocol command")


def _json_object(content: bytes, label: str) -> dict[str, Any]:
    def closed(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} has duplicate key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(content, object_pairs_hook=closed)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid {label}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _json_value(value: object) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _b64(content: bytes) -> str:
    return base64.b64encode(content).decode("ascii")


def _uint(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= _UINT_MAX
    ):
        raise ValueError("unsigned integer is invalid")
    return value


def _sha256(value: object) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise ValueError("SHA-256 is invalid")
    return value


def _kb(value: int) -> int:
    result = value * 1024
    if result > _UINT_MAX:
        raise ValueError("byte count overflows uint64")
    return result
