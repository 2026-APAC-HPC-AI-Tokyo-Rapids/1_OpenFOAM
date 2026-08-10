from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class KeySpec:
    pattern: str
    owner: str
    logical_type: str
    required_for: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProducerSpec:
    identifier: str
    required_for: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProducerContractSpec:
    identifier: str
    owner_scope: str
    applicable_run_variants: frozenset[str]
    activation_kind: str
    activation_reference: str | None
    instance_axes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceSpec:
    identifier: str
    producer_id: str
    source_role: str
    storage: str
    schema_id: str
    required_when_applicable: bool
    path_tokens: tuple[str, ...]
    path_template: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class FactSpec:
    identifier: str
    key_pattern: str
    source_id: str
    schema_id: str
    logical_type: str
    unit: str
    cardinality: str
    capture_id: str
    validator_id: str
    reducer_id: str


@dataclass(frozen=True, slots=True)
class ArtifactProjectionSpec:
    identifier: str
    relation_id: str
    source_artifact_id: str
    source_schema_id: str
    row_schema_id: str
    publisher_id: str
    transform_id: str


@dataclass(frozen=True, slots=True)
class ContractSpec:
    schema_version: str
    repository_id: str


@dataclass(frozen=True, slots=True)
class ArtifactRoleSpec:
    filenames: tuple[tuple[str, str], ...]
    run_bundle_source_roles: tuple[str, ...]

    def filename(self, role: str) -> str:
        matches = [value for name, value in self.filenames if name == role]
        if len(matches) != 1:
            raise ValueError(f"unknown outer artifact role: {role}")
        return matches[0]


@dataclass(frozen=True, slots=True)
class Registry:
    schema_version: str
    keys: tuple[KeySpec, ...]
    producers: tuple[ProducerSpec, ...]
    producer_contracts: tuple[ProducerContractSpec, ...] = ()
    sources: tuple[SourceSpec, ...] = ()
    facts: tuple[FactSpec, ...] = ()
    artifact_projections: tuple[ArtifactProjectionSpec, ...] = ()
    contract: ContractSpec | None = None
    artifact_roles: ArtifactRoleSpec | None = None

    @classmethod
    def load(cls, path: Path) -> Registry:
        with path.open("rb") as stream:
            document = tomllib.load(stream)
        root = document.get("registry")
        if not isinstance(root, dict) or not isinstance(
            root.get("schema_version"), str
        ):
            raise ValueError("registry.schema_version is required")
        keys = tuple(_key_spec(item) for item in document.get("keys", []))
        producers = tuple(
            _producer_spec(item) for item in document.get("producers", [])
        )
        if not keys or not producers:
            raise ValueError("registry must declare keys and producers")
        if len({item.identifier for item in producers}) != len(producers):
            raise ValueError("registry producer IDs must be unique")
        producer_contracts = tuple(
            _producer_contract_spec(item) for item in document.get("producer", [])
        )
        sources = tuple(_source_spec(item) for item in document.get("source", []))
        facts = tuple(_fact_spec(item) for item in document.get("fact", []))
        projections = tuple(
            _artifact_projection_spec(item)
            for item in document.get("artifact_projection", [])
        )
        contract = _contract_spec(document.get("contract"))
        artifact_roles = _artifact_role_spec(document.get("artifact_roles"))
        if sources or facts or projections:
            if contract is None or artifact_roles is None:
                raise ValueError(
                    "canonical registry requires contract and artifact roles"
                )
            _validate_contract_graph(
                producers,
                producer_contracts,
                keys,
                sources,
                facts,
                projections,
                artifact_roles,
            )
        return cls(
            root["schema_version"],
            keys,
            producers,
            producer_contracts,
            sources,
            facts,
            projections,
            contract,
            artifact_roles,
        )

    def spec_for(self, key: str) -> KeySpec:
        matches = [item for item in self.keys if fnmatch.fnmatchcase(key, item.pattern)]
        if len(matches) != 1:
            raise ValueError(f"key {key!r} has {len(matches)} registry matches")
        return matches[0]

    def producer(self, identifier: str) -> ProducerSpec:
        matches = [item for item in self.producers if item.identifier == identifier]
        if len(matches) != 1:
            raise ValueError(f"unknown producer: {identifier}")
        return matches[0]

    def required_producers(self, purpose: str) -> frozenset[str]:
        return frozenset(
            item.identifier for item in self.producers if purpose in item.required_for
        )

    def required_keys(
        self, purpose: str, *, expected_pstream_ranks: int
    ) -> frozenset[str]:
        """Expand every required pattern, rejecting undeclared axis semantics."""

        required: set[str] = set()
        for item in self.keys:
            if purpose not in item.required_for:
                continue
            if "*" not in item.pattern:
                required.add(item.pattern)
            elif item.pattern in _PSTREAM_RANK_PATTERNS:
                required.update(
                    item.pattern.replace("*", str(rank))
                    for rank in range(expected_pstream_ranks)
                )
            else:
                raise ValueError(
                    f"required wildcard has no protocol axis expansion: {item.pattern}"
                )
        return frozenset(required)

    def required_literal_sources(
        self, purpose: str, *, storages: frozenset[str]
    ) -> tuple[tuple[str, str], ...]:
        """Return required source paths whose instance axes need no expansion."""

        producers = {item.identifier: item for item in self.producer_contracts}
        selected: list[tuple[str, str]] = []
        for source in self.sources:
            producer = producers[source.producer_id]
            if (
                source.required_when_applicable
                and source.storage in storages
                and purpose in producer.applicable_run_variants
                and not source.path_tokens
            ):
                selected.append(
                    (
                        source.identifier,
                        "".join(value for _, value in source.path_template),
                    )
                )
        return tuple(sorted(selected, key=lambda item: item[0].encode()))


def _key_spec(item: object) -> KeySpec:
    if not isinstance(item, dict):
        raise ValueError("registry keys must be objects")
    pattern = item.get("pattern")
    owner = item.get("owner")
    logical_type = item.get("logical_type")
    required_for = _purposes(item.get("required_for"))
    if not all(
        isinstance(value, str) and value for value in (pattern, owner, logical_type)
    ):
        raise ValueError("registry key pattern, owner, and logical_type are required")
    return KeySpec(pattern, owner, logical_type, required_for)


def _producer_spec(item: object) -> ProducerSpec:
    if not isinstance(item, dict):
        raise ValueError("registry producers must be objects")
    identifier = item.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("registry producer id is required")
    return ProducerSpec(identifier, _purposes(item.get("required_for")))


def _producer_contract_spec(item: object) -> ProducerContractSpec:
    if not isinstance(item, dict) or set(item) != {
        "id",
        "owner_scope",
        "applicable_run_variants",
        "activation",
        "instances",
    }:
        raise ValueError("contract producer must contain exactly its v1 fields")
    identifier = item["id"]
    variants = item["applicable_run_variants"]
    activation = item["activation"]
    instances = item["instances"]
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("contract producer ID is required")
    if item["owner_scope"] != "run":
        raise ValueError("v1 runtime producer owner scope must be run")
    if (
        not isinstance(variants, list)
        or not variants
        or not set(variants).issubset({"bench", "profile"})
    ):
        raise ValueError("contract producer variants are invalid")
    if not isinstance(activation, dict):
        raise ValueError("contract producer activation is invalid")
    activation_kind = activation.get("kind")
    if activation_kind == "always":
        if set(activation) != {"kind"}:
            raise ValueError("always activation is not closed")
        activation_reference = None
    elif activation_kind == "bundle_component":
        if set(activation) != {"kind", "component_id"} or not isinstance(
            activation.get("component_id"), str
        ):
            raise ValueError("bundle component activation is not closed")
        activation_reference = activation["component_id"]
    else:
        raise ValueError("contract producer activation is invalid")
    if not isinstance(instances, dict):
        raise ValueError("contract producer instances are invalid")
    instance_kind = instances.get("kind")
    if instance_kind == "singleton":
        if set(instances) != {"kind"}:
            raise ValueError("singleton producer instances are not closed")
        axes: list[str] = []
    elif instance_kind == "cartesian":
        if set(instances) != {"kind", "axes"}:
            raise ValueError("cartesian producer instances are not closed")
        axes = instances.get("axes")
    else:
        raise ValueError("contract producer instances are invalid")
    allowed_axes = {"node_ordinal", "global_rank", "stage_name", "invocation_id"}
    if (
        not isinstance(axes, list)
        or not axes
        or not all(isinstance(axis, str) for axis in axes)
        or axes != sorted(set(axes), key=str.encode)
        or not set(axes).issubset(allowed_axes)
    ) and instance_kind == "cartesian":
        raise ValueError("contract producer axes are invalid")
    return ProducerContractSpec(
        identifier,
        item["owner_scope"],
        frozenset(variants),
        activation_kind,
        activation_reference,
        tuple(axes),
    )


def _source_spec(item: object) -> SourceSpec:
    if not isinstance(item, dict):
        raise ValueError("contract sources must be objects")
    required = {
        "id",
        "producer_id",
        "source_role",
        "storage",
        "path_template",
        "schema_id",
        "required_when_applicable",
    }
    if set(item) != required:
        raise ValueError("contract source must contain exactly its v1 fields")
    values = [
        item[name] for name in required - {"path_template", "required_when_applicable"}
    ]
    if not all(isinstance(value, str) and value for value in values):
        raise ValueError("contract source string fields are required")
    if item["storage"] not in {"fact_fragment", "run_bundle", "profile_raw"}:
        raise ValueError("contract source storage is invalid")
    if not isinstance(item["required_when_applicable"], bool):
        raise ValueError("contract source requiredness must be boolean")
    path_template = _path_template(item["path_template"])
    path_tokens = tuple(value for kind, value in path_template if kind == "token")
    return SourceSpec(
        item["id"],
        item["producer_id"],
        item["source_role"],
        item["storage"],
        item["schema_id"],
        item["required_when_applicable"],
        path_tokens,
        path_template,
    )


def _contract_spec(item: object) -> ContractSpec | None:
    if item is None:
        return None
    if not isinstance(item, dict) or set(item) != {
        "schema_version",
        "repository_id",
    }:
        raise ValueError("contract header must be a closed v1 object")
    if (
        item["schema_version"] != "openfoam-observation-contract/v1"
        or item["repository_id"] != "apac2026-openfoam"
    ):
        raise ValueError("unsupported contract identity")
    return ContractSpec(item["schema_version"], item["repository_id"])


def _artifact_role_spec(item: object) -> ArtifactRoleSpec | None:
    if item is None:
        return None
    required = {
        "run_bundle",
        "metrics",
        "profile_raw",
        "artifact_manifest",
        "run_bundle_source_roles",
    }
    if not isinstance(item, dict) or set(item) != required:
        raise ValueError("artifact roles must be a closed v1 object")
    expected = {
        "run_bundle": "run-artifacts.tar.zst",
        "metrics": "metrics.jsonl",
        "profile_raw": "profile-raw.tar.zst",
        "artifact_manifest": "artifact-manifest.json",
    }
    if any(item[name] != value for name, value in expected.items()):
        raise ValueError("artifact role filename mapping is invalid")
    roles = item["run_bundle_source_roles"]
    if (
        not isinstance(roles, list)
        or not roles
        or not all(isinstance(role, str) and role for role in roles)
        or roles != sorted(set(roles), key=str.encode)
    ):
        raise ValueError("run bundle source roles must be byte-sorted and unique")
    return ArtifactRoleSpec(tuple(expected.items()), tuple(roles))


def _fact_spec(item: object) -> FactSpec:
    if not isinstance(item, dict):
        raise ValueError("contract facts must be objects")
    required = {
        "id",
        "key_pattern",
        "source_id",
        "schema_id",
        "logical_type",
        "unit",
        "cardinality",
        "capture_id",
        "validator_id",
        "reducer_id",
    }
    allowed = required | {"duplication_justification"}
    if frozenset(item) not in {frozenset(required), frozenset(allowed)}:
        raise ValueError("contract fact must contain exactly its v1 fields")
    if not all(isinstance(item[name], str) and item[name] for name in required):
        raise ValueError("contract fact string fields are required")
    return FactSpec(
        item["id"],
        item["key_pattern"],
        item["source_id"],
        item["schema_id"],
        item["logical_type"],
        item["unit"],
        item["cardinality"],
        item["capture_id"],
        item["validator_id"],
        item["reducer_id"],
    )


def _artifact_projection_spec(item: object) -> ArtifactProjectionSpec:
    if not isinstance(item, dict):
        raise ValueError("artifact projections must be objects")
    required = {
        "id",
        "base_table_id",
        "relation_id",
        "conflict_relation_id",
        "source_artifact_id",
        "source_schema_id",
        "row_schema_id",
        "row_grain",
        "subject_scopes",
        "publisher_id",
        "transform_id",
        "conflict_rule",
        "duplication_justification",
    }
    optional = {
        "source_member_field",
        "source_sha256_field",
        "source_instance_grain",
        "source_instance_sha256_field",
        "parent_projection_id",
        "parent_join_columns",
    }
    if not required.issubset(item) or set(item) - required - optional:
        raise ValueError("artifact projection has invalid v1 fields")
    for name in required - {"row_grain", "subject_scopes"}:
        if not isinstance(item[name], str) or not item[name]:
            raise ValueError("artifact projection string fields are required")
    if not isinstance(item["row_grain"], list) or not item["row_grain"]:
        raise ValueError("artifact projection row grain is required")
    if not isinstance(item["subject_scopes"], list) or not item["subject_scopes"]:
        raise ValueError("artifact projection subject scope is required")
    return ArtifactProjectionSpec(
        item["id"],
        item["relation_id"],
        item["source_artifact_id"],
        item["source_schema_id"],
        item["row_schema_id"],
        item["publisher_id"],
        item["transform_id"],
    )


def _path_template(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("source path template must be nonempty")
    segments: list[tuple[str, str]] = []
    previous_literal = False
    allowed_tokens = {"node_ordinal", "global_rank", "stage_name", "invocation_id"}
    for segment in value:
        if not isinstance(segment, dict) or set(segment) not in (
            {"literal"},
            {"token"},
        ):
            raise ValueError("source path template segment is invalid")
        token = next(iter(segment.values()))
        if not isinstance(token, str) or not token:
            raise ValueError("source path template segment must be nonempty")
        is_literal = "literal" in segment
        if is_literal and previous_literal:
            raise ValueError("adjacent source path literals must be combined")
        if not is_literal:
            if token not in allowed_tokens:
                raise ValueError("source path template token is invalid")
        segments.append(("literal" if is_literal else "token", token))
        previous_literal = is_literal
    return tuple(segments)


def _validate_contract_graph(
    producers: tuple[ProducerSpec, ...],
    producer_contracts: tuple[ProducerContractSpec, ...],
    keys: tuple[KeySpec, ...],
    sources: tuple[SourceSpec, ...],
    facts: tuple[FactSpec, ...],
    projections: tuple[ArtifactProjectionSpec, ...],
    artifact_roles: ArtifactRoleSpec,
) -> None:
    producer_ids = {item.identifier for item in producers}
    contract_producer_ids = {item.identifier for item in producer_contracts}
    if len(contract_producer_ids) != len(producer_contracts):
        raise ValueError("contract producer IDs must be unique")
    if not producer_ids.issubset(contract_producer_ids):
        raise ValueError("runtime producers are absent from the canonical graph")
    if len({item.identifier for item in sources}) != len(sources):
        raise ValueError("contract source IDs must be unique")
    if any(item.producer_id not in contract_producer_ids for item in sources):
        raise ValueError("contract source references an unknown producer")
    producer_by_id = {item.identifier: item for item in producer_contracts}
    for source in sources:
        if not set(source.path_tokens).issubset(
            producer_by_id[source.producer_id].instance_axes
        ):
            raise ValueError("source path token is absent from its producer axes")
    fragment_producers = [
        item.producer_id for item in sources if item.storage == "fact_fragment"
    ]
    if len(fragment_producers) != len(set(fragment_producers)):
        raise ValueError("a producer may own at most one fact fragment source")
    run_roles = [item.source_role for item in sources if item.storage == "run_bundle"]
    if len(run_roles) != len(set(run_roles)):
        raise ValueError("run bundle source roles must resolve to one registry source")
    if not set(run_roles).issubset(artifact_roles.run_bundle_source_roles):
        raise ValueError("run bundle source uses an undeclared artifact role")
    source_ids = {item.identifier for item in sources}
    if len({item.identifier for item in facts}) != len(facts):
        raise ValueError("contract fact IDs must be unique")
    if any(item.source_id not in source_ids for item in facts):
        raise ValueError("contract fact references an unknown source")
    fact_by_pattern = {item.key_pattern: item for item in facts}
    if len(fact_by_pattern) != len(facts):
        raise ValueError("canonical fact key patterns must be unique")
    source_by_id = {item.identifier: item for item in sources}
    for key in keys:
        fact = fact_by_pattern.get(key.pattern)
        if fact is None:
            raise ValueError(f"runtime key has no canonical fact entry: {key.pattern}")
        if source_by_id[fact.source_id].producer_id != key.owner:
            raise ValueError(
                f"runtime key owner differs from canonical fact: {key.pattern}"
            )
        if fact.logical_type != key.logical_type:
            raise ValueError(
                f"runtime key type differs from canonical fact: {key.pattern}"
            )
    if len({item.identifier for item in projections}) != len(projections):
        raise ValueError("artifact projection IDs must be unique")
    if any(item.source_artifact_id not in source_ids for item in projections):
        raise ValueError("artifact projection references an unknown source")


def _purposes(value: object) -> frozenset[str]:
    if not isinstance(value, list) or not all(
        item in {"bench", "profile"} for item in value
    ):
        raise ValueError("registry required_for must contain bench and/or profile")
    return frozenset(value)


_PSTREAM_RANK_PATTERNS = frozenset(
    {
        "solver.pstream.startup_applied.rank.*",
        "solver.pstream.runtime_current.rank.*",
        "solver.pstream.change_events.rank.*",
    }
)
