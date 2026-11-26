"""Core artifact, trace, baseline, and impact types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Iterable


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class ArtifactKind(str, Enum):
    STAKEHOLDER_NEED = "stakeholder_need"
    REQUIREMENT = "requirement"
    ARCHITECTURAL_ELEMENT = "architectural_element"
    BEHAVIOR_ELEMENT = "behavior_element"
    IMPLEMENTATION = "implementation"
    COMPONENT_TEST = "component_test"
    SCENARIO_TEST = "scenario_test"
    VERIFICATION_EVIDENCE = "verification_evidence"


class TraceKind(str, Enum):
    ORIGIN = "origin"
    REALIZES = "realizes"
    SUPPORTS = "supports"
    IMPLEMENTS = "implements"
    GENERATES = "generates"
    COVERS = "covers"
    EXECUTES = "executes"
    VERIFIES = "verifies"
    SUPERSEDES = "supersedes"


@dataclass(frozen=True)
class Artifact:
    id: str
    kind: ArtifactKind
    revision: int = 1
    properties: dict[str, Any] = field(default_factory=dict)
    supersedes: tuple[str, ...] = ()
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            digest = content_hash(
                {
                    "id": self.id,
                    "kind": self.kind.value,
                    "revision": self.revision,
                    "properties": self.properties,
                    "supersedes": list(self.supersedes),
                }
            )
            object.__setattr__(self, "content_hash", digest)

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.revision}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "revision": self.revision,
            "ref": self.ref,
            "properties": self.properties,
            "supersedes": list(self.supersedes),
            "contentHash": self.content_hash,
        }


@dataclass(frozen=True)
class TraceLink:
    kind: TraceKind
    source_id: str
    source_revision: int
    target_id: str
    target_revision: int
    status: str = "active"
    derived_by: str = ""

    @property
    def source_ref(self) -> str:
        return f"{self.source_id}@{self.source_revision}"

    @property
    def target_ref(self) -> str:
        return f"{self.target_id}@{self.target_revision}"

    @property
    def key(self) -> tuple[Any, ...]:
        return (
            self.kind.value,
            self.source_id,
            self.source_revision,
            self.target_id,
            self.target_revision,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "source": self.source_ref,
            "target": self.target_ref,
            "status": self.status,
            "derivedBy": self.derived_by,
        }


@dataclass(frozen=True)
class ImpactPlan:
    root: str
    impacted: tuple[str, ...]
    invalidatedEvidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "impacted": list(self.impacted),
            "invalidatedEvidence": list(self.invalidatedEvidence),
        }


@dataclass(frozen=True)
class Conflict:
    left: str
    right: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"left": self.left, "right": self.right, "reason": self.reason}


@dataclass(frozen=True)
class Reconciliation:
    status: str
    conflicts: tuple[Conflict, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


@dataclass(frozen=True)
class Baseline:
    id: str
    requirement_ref: str
    artifact_refs: tuple[str, ...]
    trace_keys: tuple[tuple[Any, ...], ...]
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "requirement": self.requirement_ref,
            "artifacts": list(self.artifact_refs),
            "traceKeys": [list(key) for key in self.trace_keys],
            "contentHash": self.content_hash,
        }


class ContinuityModel:
    """In-memory model repository with immutable, revisioned artifacts."""

    def __init__(self) -> None:
        self._artifacts: dict[tuple[str, int], Artifact] = {}
        self._latest: dict[str, Artifact] = {}
        self._traces: dict[tuple[Any, ...], TraceLink] = {}
        self._baselines: dict[str, Baseline] = {}

    def add_artifact(self, artifact: Artifact) -> Artifact:
        key = (artifact.id, artifact.revision)
        existing = self._artifacts.get(key)
        if existing is not None:
            return existing
        self._artifacts[key] = artifact
        current = self._latest.get(artifact.id)
        if current is None or artifact.revision >= current.revision:
            self._latest[artifact.id] = artifact
        return artifact

    def latest(self, artifact_id: str) -> Artifact:
        try:
            return self._latest[artifact_id]
        except KeyError as exc:
            raise KeyError(f"Unknown artifact: {artifact_id}") from exc

    def get(self, artifact_ref: str) -> Artifact:
        if "@" in artifact_ref:
            artifact_id, revision_text = artifact_ref.rsplit("@", 1)
            try:
                return self._artifacts[(artifact_id, int(revision_text))]
            except (KeyError, ValueError) as exc:
                raise KeyError(f"Unknown artifact revision: {artifact_ref}") from exc
        return self.latest(artifact_ref)

    def all_artifacts(self) -> tuple[Artifact, ...]:
        return tuple(sorted(self._artifacts.values(), key=lambda item: item.ref))

    def latest_artifacts(self) -> tuple[Artifact, ...]:
        return tuple(sorted(self._latest.values(), key=lambda item: item.id))

    def ensure_trace(
        self,
        kind: TraceKind,
        source: Artifact,
        target: Artifact,
        derived_by: str,
    ) -> TraceLink:
        link = TraceLink(
            kind=kind,
            source_id=source.id,
            source_revision=source.revision,
            target_id=target.id,
            target_revision=target.revision,
            status="active",
            derived_by=derived_by,
        )
        existing = self._traces.get(link.key)
        if existing is not None:
            return existing
        self._traces[link.key] = link
        return link

    def active_traces(self) -> tuple[TraceLink, ...]:
        return tuple(
            sorted(
                (link for link in self._traces.values() if link.status == "active"),
                key=lambda link: link.key,
            )
        )

    def add_baseline(self, baseline: Baseline) -> Baseline:
        self._baselines[baseline.id] = baseline
        return baseline

    def baseline(self, baseline_id: str) -> Baseline:
        return self._baselines[baseline_id]

    def baselines(self) -> tuple[Baseline, ...]:
        return tuple(sorted(self._baselines.values(), key=lambda item: item.id))
