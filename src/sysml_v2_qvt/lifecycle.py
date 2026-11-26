"""Executable reference implementation of the SysML lifecycle operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from .model import (
    Artifact,
    ArtifactKind,
    Baseline,
    Conflict,
    ContinuityModel,
    ImpactPlan,
    Reconciliation,
    TraceKind,
    TraceLink,
    canonical_json,
    content_hash,
    kind_value,
    trace_kind_value,
)


def _slug(value: str) -> str:
    return "-".join(
        part
        for part in "".join(
            character if character.isalnum() else "-" for character in value.upper()
        ).split("-")
        if part
    )


@dataclass(frozen=True)
class LifecycleKinds:
    """Configurable names for lifecycle artifact roles."""

    stakeholder_need: ArtifactKind | str = ArtifactKind.STAKEHOLDER_NEED
    requirement: ArtifactKind | str = ArtifactKind.REQUIREMENT
    architectural_element: ArtifactKind | str = ArtifactKind.ARCHITECTURAL_ELEMENT
    behavior_element: ArtifactKind | str = ArtifactKind.BEHAVIOR_ELEMENT
    implementation: ArtifactKind | str = ArtifactKind.IMPLEMENTATION
    component_test: ArtifactKind | str = ArtifactKind.COMPONENT_TEST
    scenario_test: ArtifactKind | str = ArtifactKind.SCENARIO_TEST
    verification_evidence: ArtifactKind | str = ArtifactKind.VERIFICATION_EVIDENCE


class IdentityPolicy(Protocol):
    def requirement_id(self, need: Artifact) -> str: ...

    def architecture_id(self, requirement: Artifact, element_name: str) -> str: ...

    def component_test_id(
        self,
        requirement: Artifact,
        case: Mapping[str, object],
        index: int,
    ) -> str: ...

    def scenario_test_id(
        self,
        requirement: Artifact,
        scenario: Mapping[str, object],
        index: int,
    ) -> str: ...

    def baseline_id(self, requirement: Artifact, digest: str) -> str: ...


@dataclass(frozen=True)
class DefaultIdentityPolicy:
    """Stable, domain-neutral fallbacks. Callers may supply explicit IDs."""

    def requirement_id(self, need: Artifact) -> str:
        configured = need.properties.get("requirementId")
        return str(configured) if configured else need.id

    def architecture_id(self, requirement: Artifact, element_name: str) -> str:
        return f"{requirement.id}/{_slug(element_name)}"

    def component_test_id(
        self,
        requirement: Artifact,
        case: Mapping[str, object],
        index: int,
    ) -> str:
        return str(case.get("id", f"{requirement.id}/component-test-{index}"))

    def scenario_test_id(
        self,
        requirement: Artifact,
        scenario: Mapping[str, object],
        index: int,
    ) -> str:
        return str(scenario.get("id", f"{requirement.id}/scenario-test-{index}"))

    def baseline_id(self, requirement: Artifact, digest: str) -> str:
        return f"BL-{digest[:16]}"


class LifecycleEngine:
    def __init__(
        self,
        model: ContinuityModel | None = None,
        *,
        identity_policy: IdentityPolicy | None = None,
        kinds: LifecycleKinds | None = None,
    ) -> None:
        self.model = model or ContinuityModel()
        self.identity_policy = identity_policy or DefaultIdentityPolicy()
        self.kinds = kinds or LifecycleKinds()

    def develop_intent(
        self,
        need: Artifact,
        requirement_id: str | None = None,
    ) -> Artifact:
        if kind_value(need.kind) != kind_value(self.kinds.stakeholder_need):
            raise TypeError("develop_intent requires the configured stakeholder need kind")
        need = self.model.add_artifact(need)

        requirement_id = (
            requirement_id
            or self.identity_policy.requirement_id(need)
        )
        properties = {
            "statement": need.properties.get("statement", ""),
            "rationale": need.properties.get("rationale", ""),
            "acceptanceCriteria": need.properties.get("acceptanceCriteria", []),
            "sourceNeed": need.ref,
        }

        try:
            existing = self.model.latest(requirement_id)
        except KeyError:
            existing = None

        if existing is not None and existing.properties == properties:
            requirement = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            requirement = Artifact(
                id=requirement_id,
                kind=self.kinds.requirement,
                revision=revision,
                properties=properties,
                supersedes=supersedes,
            )
            requirement = self.model.add_artifact(requirement)

            if existing is not None:
                self.model.ensure_trace(
                    TraceKind.SUPERSEDES,
                    existing,
                    requirement,
                    "develop_intent",
                )

        self.model.ensure_trace(
            TraceKind.ORIGIN,
            need,
            requirement,
            "develop_intent",
        )
        return requirement

    def realize_architecture(
        self,
        requirement: Artifact,
        element_names: Iterable[str],
        element_ids: Mapping[str, str] | None = None,
    ) -> tuple[Artifact, ...]:
        if kind_value(requirement.kind) != kind_value(self.kinds.requirement):
            raise TypeError("realize_architecture requires the configured requirement kind")

        requirement = self.model.add_artifact(requirement)
        elements: list[Artifact] = []
        element_ids = element_ids or {}
        for name in element_names:
            element_id = (
                element_ids.get(name)
                or self.identity_policy.architecture_id(requirement, name)
            )
            properties = {
                "name": name,
                "requirement": requirement.ref,
            }
            try:
                existing = self.model.latest(element_id)
            except KeyError:
                existing = None

            if existing is not None and existing.properties == properties:
                element = existing
            else:
                revision = existing.revision + 1 if existing is not None else 1
                supersedes = (existing.ref,) if existing is not None else ()
                element = Artifact(
                    id=element_id,
                    kind=self.kinds.architectural_element,
                    revision=revision,
                    properties=properties,
                    supersedes=supersedes,
                )
                element = self.model.add_artifact(element)

                if existing is not None:
                    self.model.ensure_trace(
                        TraceKind.SUPERSEDES,
                        existing,
                        element,
                        "realize_architecture",
                    )

            self.model.ensure_trace(
                TraceKind.REALIZES,
                requirement,
                element,
                "realize_architecture",
            )
            elements.append(element)
        return tuple(elements)

    def realize_behavior(
        self,
        requirement: Artifact,
        architecture: Iterable[Artifact],
        behavior_id: str,
        properties: Mapping[str, object],
    ) -> Artifact:
        if kind_value(requirement.kind) != kind_value(self.kinds.requirement):
            raise TypeError("realize_behavior requires the configured requirement kind")
        requirement = self.model.add_artifact(requirement)
        architecture = tuple(self.model.add_artifact(element) for element in architecture)

        complete_properties = dict(properties)
        complete_properties["requirement"] = requirement.ref
        try:
            existing = self.model.latest(behavior_id)
        except KeyError:
            existing = None

        if existing is not None and existing.properties == complete_properties:
            behavior = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            behavior = Artifact(
                id=behavior_id,
                kind=self.kinds.behavior_element,
                revision=revision,
                properties=complete_properties,
                supersedes=supersedes,
            )
            behavior = self.model.add_artifact(behavior)

            if existing is not None:
                self.model.ensure_trace(
                    TraceKind.SUPERSEDES,
                    existing,
                    behavior,
                    "realize_behavior",
                )

        for element in architecture:
            self.model.ensure_trace(
                TraceKind.SUPPORTS,
                element,
                behavior,
                "realize_behavior",
            )
        return behavior

    def verify_satisfaction(
        self,
        requirement: Artifact,
        behavior: Artifact,
        *,
        evidence_id: str,
        result: str,
        summary: str,
        component_cases: Iterable[Mapping[str, object]],
        simulated_scenarios: Iterable[Mapping[str, object]],
        implementation: Artifact | None = None,
    ) -> tuple[Artifact, tuple[Artifact, ...], tuple[Artifact, ...]]:
        if kind_value(requirement.kind) != kind_value(self.kinds.requirement):
            raise TypeError("verify_satisfaction requires the configured requirement kind")
        if kind_value(behavior.kind) != kind_value(self.kinds.behavior_element):
            raise TypeError("verify_satisfaction requires the configured behavior kind")
        requirement = self.model.add_artifact(requirement)
        behavior = self.model.add_artifact(behavior)
        if implementation is not None:
            implementation = self.model.add_artifact(implementation)

        component_artifacts: list[Artifact] = []
        for index, case in enumerate(component_cases, start=1):
            case_id = self.identity_policy.component_test_id(
                requirement,
                case,
                index,
            )
            properties = dict(case)
            properties["requirement"] = requirement.ref
            properties["behavior"] = behavior.ref
            if implementation is not None:
                properties["implementation"] = implementation.ref

            try:
                existing = self.model.latest(case_id)
            except KeyError:
                existing = None
            if existing is not None and existing.properties == properties:
                test = existing
            else:
                revision = existing.revision + 1 if existing is not None else 1
                supersedes = (existing.ref,) if existing is not None else ()
                test = Artifact(
                    id=case_id,
                    kind=self.kinds.component_test,
                    revision=revision,
                    properties=properties,
                    supersedes=supersedes,
                )
                test = self.model.add_artifact(test)
                if existing is not None:
                    self.model.ensure_trace(
                        TraceKind.SUPERSEDES,
                        existing,
                        test,
                        "verify_satisfaction",
                    )

            self.model.ensure_trace(
                TraceKind.COVERS,
                test,
                requirement,
                "verify_satisfaction",
            )
            self.model.ensure_trace(
                TraceKind.EXECUTES,
                test,
                behavior,
                "verify_satisfaction",
            )
            if implementation is not None:
                self.model.ensure_trace(
                    TraceKind.EXECUTES,
                    test,
                    implementation,
                    "verify_satisfaction",
                )
            component_artifacts.append(test)

        scenario_artifacts: list[Artifact] = []
        for index, scenario in enumerate(simulated_scenarios, start=1):
            scenario_id = self.identity_policy.scenario_test_id(
                requirement,
                scenario,
                index,
            )
            properties = dict(scenario)
            properties["requirement"] = requirement.ref
            properties["behavior"] = behavior.ref
            if implementation is not None:
                properties["implementation"] = implementation.ref

            try:
                existing = self.model.latest(scenario_id)
            except KeyError:
                existing = None
            if existing is not None and existing.properties == properties:
                test = existing
            else:
                revision = existing.revision + 1 if existing is not None else 1
                supersedes = (existing.ref,) if existing is not None else ()
                test = Artifact(
                    id=scenario_id,
                    kind=self.kinds.scenario_test,
                    revision=revision,
                    properties=properties,
                    supersedes=supersedes,
                )
                test = self.model.add_artifact(test)
                if existing is not None:
                    self.model.ensure_trace(
                        TraceKind.SUPERSEDES,
                        existing,
                        test,
                        "verify_satisfaction",
                    )

            self.model.ensure_trace(
                TraceKind.COVERS,
                test,
                requirement,
                "verify_satisfaction",
            )
            self.model.ensure_trace(
                TraceKind.EXECUTES,
                test,
                behavior,
                "verify_satisfaction",
            )
            if implementation is not None:
                self.model.ensure_trace(
                    TraceKind.EXECUTES,
                    test,
                    implementation,
                    "verify_satisfaction",
                )
            scenario_artifacts.append(test)

        evidence_properties = {
            "result": result,
            "summary": summary,
            "requirement": requirement.ref,
            "behavior": behavior.ref,
            "componentTests": [test.ref for test in component_artifacts],
            "scenarioTests": [test.ref for test in scenario_artifacts],
        }
        if implementation is not None:
            evidence_properties["implementation"] = implementation.ref

        try:
            existing = self.model.latest(evidence_id)
        except KeyError:
            existing = None
        if existing is not None and existing.properties == evidence_properties:
            evidence = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            evidence = Artifact(
                id=evidence_id,
                kind=self.kinds.verification_evidence,
                revision=revision,
                properties=evidence_properties,
                supersedes=supersedes,
            )
            evidence = self.model.add_artifact(evidence)
            if existing is not None:
                self.model.ensure_trace(
                    TraceKind.SUPERSEDES,
                    existing,
                    evidence,
                    "verify_satisfaction",
                )

        self.model.ensure_trace(
            TraceKind.VERIFIES,
            behavior,
            evidence,
            "verify_satisfaction",
        )
        return evidence, tuple(component_artifacts), tuple(scenario_artifacts)

    def propagate_change(self, root: Artifact) -> ImpactPlan:
        root = self.model.add_artifact(root)
        visited: set[str] = {root.ref}
        queue: list[str] = [root.ref]

        while queue:
            current = queue.pop(0)
            for link in self.model.active_traces():
                neighbor: str | None = None
                if link.source_ref == current:
                    neighbor = link.target_ref
                elif link.target_ref == current:
                    neighbor = link.source_ref
                if neighbor is not None and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        impacted: list[str] = []
        invalidated: list[str] = []
        for artifact_ref in sorted(visited):
            if artifact_ref == root.ref:
                continue
            try:
                artifact = self.model.get(artifact_ref)
            except KeyError:
                continue
            impacted.append(artifact_ref)
            if kind_value(artifact.kind) == kind_value(
                self.kinds.verification_evidence
            ):
                checked_requirement = artifact.properties.get("requirement")
                if checked_requirement and checked_requirement != root.ref:
                    invalidated.append(artifact_ref)

        return ImpactPlan(
            root=root.ref,
            impacted=tuple(impacted),
            invalidatedEvidence=tuple(invalidated),
        )

    def reconcile_views(
        self,
        left: Artifact | str,
        right: Artifact | str,
    ) -> Reconciliation:
        left_artifact = left if isinstance(left, Artifact) else self.model.get(left)
        right_artifact = right if isinstance(right, Artifact) else self.model.get(right)

        conflicts: list[Conflict] = []
        if left_artifact.id != right_artifact.id:
            conflicts.append(
                Conflict(
                    left=left_artifact.ref,
                    right=right_artifact.ref,
                    reason="different stable identities",
                )
            )
        elif kind_value(left_artifact.kind) != kind_value(right_artifact.kind):
            conflicts.append(
                Conflict(
                    left=left_artifact.ref,
                    right=right_artifact.ref,
                    reason="different artifact kinds",
                )
            )
        elif left_artifact.properties != right_artifact.properties:
            conflicts.append(
                Conflict(
                    left=left_artifact.ref,
                    right=right_artifact.ref,
                    reason="different semantic properties",
                )
            )

        if conflicts:
            return Reconciliation(status="conflict", conflicts=tuple(conflicts))
        return Reconciliation(status="consistent")

    def baseline_thread(self, requirement: Artifact) -> Baseline:
        requirement = self.model.add_artifact(requirement)
        visited: set[str] = {requirement.ref}
        queue: list[str] = [requirement.ref]

        while queue:
            current = queue.pop(0)
            for link in self.model.active_traces():
                neighbor: str | None = None
                if link.source_ref == current:
                    neighbor = link.target_ref
                elif link.target_ref == current:
                    neighbor = link.source_ref
                if neighbor is not None and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        artifact_refs = tuple(sorted(visited))
        active_links = tuple(
            sorted(
                (
                    link.key
                    for link in self.model.active_traces()
                    if link.source_ref in visited and link.target_ref in visited
                ),
                key=lambda key: canonical_json(list(key)),
            )
        )
        digest = content_hash(
            {
                "requirement": requirement.ref,
                "artifacts": list(artifact_refs),
                "traces": [list(key) for key in active_links],
            }
        )
        baseline_id = self.identity_policy.baseline_id(requirement, digest)
        baseline = Baseline(
            id=baseline_id,
            requirement_ref=requirement.ref,
            artifact_refs=artifact_refs,
            trace_keys=active_links,
            content_hash=digest,
        )
        return self.model.add_baseline(baseline)

    def check_continuity(self, requirement: Artifact) -> tuple[str, ...]:
        requirement = self.model.add_artifact(requirement)
        traces = self.model.active_traces()
        diagnostics: list[str] = []

        architecture = [
            link.target_id
            for link in traces
            if trace_kind_value(link.kind) == "realizes"
            and link.source_id == requirement.id
            and link.source_revision == requirement.revision
        ]
        if not architecture:
            diagnostics.append(
                f"requirement {requirement.ref} has no architectural realization"
            )

        behavior_refs = [
            link.target_ref
            for link in traces
            if trace_kind_value(link.kind) == "supports"
            and link.source_id in architecture
        ]
        if not behavior_refs:
            diagnostics.append(
                f"requirement {requirement.ref} has no behavioral realization"
            )

        component_tests = [
            link.source_id
            for link in traces
            if trace_kind_value(link.kind) == "covers"
            and link.target_id == requirement.id
            and link.target_revision == requirement.revision
        ]
        scenario_tests = [
            artifact.id
            for artifact in self.model.latest_artifacts()
            if kind_value(artifact.kind)
            == kind_value(self.kinds.scenario_test)
            and artifact.properties.get("requirement") == requirement.ref
        ]
        if not component_tests:
            diagnostics.append(
                f"requirement {requirement.ref} has no component-level test coverage"
            )
        if not scenario_tests:
            diagnostics.append(
                f"requirement {requirement.ref} has no simulated scenario coverage"
            )

        passed_evidence = [
            artifact
            for artifact in self.model.latest_artifacts()
            if kind_value(artifact.kind)
            == kind_value(self.kinds.verification_evidence)
            and artifact.properties.get("requirement") == requirement.ref
            and artifact.properties.get("result") == "pass"
        ]
        if not passed_evidence:
            diagnostics.append(
                f"requirement {requirement.ref} has no passing verification evidence"
            )

        return tuple(diagnostics)
