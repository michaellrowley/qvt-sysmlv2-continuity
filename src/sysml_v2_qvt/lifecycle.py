"""Executable reference implementation of the SysML lifecycle operations."""

from __future__ import annotations

from typing import Iterable, Mapping

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
)


def _slug(value: str) -> str:
    return "-".join(
        part
        for part in "".join(
            character if character.isalnum() else "-" for character in value.upper()
        ).split("-")
        if part
    )


class LifecycleEngine:
    def __init__(self, model: ContinuityModel | None = None) -> None:
        self.model = model or ContinuityModel()

    def develop_intent(self, need: Artifact) -> Artifact:
        if need.kind is not ArtifactKind.STAKEHOLDER_NEED:
            raise TypeError("develop_intent requires a stakeholder_need")
        need = self.model.add_artifact(need)

        requirement_id = f"R-{need.id.removeprefix('N-')}"
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
                kind=ArtifactKind.REQUIREMENT,
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
    ) -> tuple[Artifact, ...]:
        if requirement.kind is not ArtifactKind.REQUIREMENT:
            raise TypeError("realize_architecture requires a requirement")

        requirement = self.model.add_artifact(requirement)
        elements: list[Artifact] = []
        for name in element_names:
            element_id = f"A-{_slug(requirement.id)}-{_slug(name)}"
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
                    kind=ArtifactKind.ARCHITECTURAL_ELEMENT,
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
                kind=ArtifactKind.BEHAVIOR_ELEMENT,
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
        requirement = self.model.add_artifact(requirement)
        behavior = self.model.add_artifact(behavior)
        if implementation is not None:
            implementation = self.model.add_artifact(implementation)

        component_artifacts: list[Artifact] = []
        for index, case in enumerate(component_cases, start=1):
            case_id = str(case.get("id", f"TC-C-{index}"))
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
                    kind=ArtifactKind.COMPONENT_TEST,
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
            scenario_id = str(scenario.get("id", f"TC-S-{index}"))
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
                    kind=ArtifactKind.SCENARIO_TEST,
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
                kind=ArtifactKind.VERIFICATION_EVIDENCE,
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
            if artifact.kind is ArtifactKind.VERIFICATION_EVIDENCE:
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
        elif left_artifact.kind is not right_artifact.kind:
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
        requirement_stem = requirement.id.removeprefix("R-")
        baseline_id = (
            f"BL-{requirement_stem}-{requirement.revision}-{digest[:8]}"
        )
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
            if link.kind is TraceKind.REALIZES
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
            if link.kind is TraceKind.SUPPORTS
            and link.source_id in architecture
        ]
        if not behavior_refs:
            diagnostics.append(
                f"requirement {requirement.ref} has no behavioral realization"
            )

        component_tests = [
            link.source_id
            for link in traces
            if link.kind is TraceKind.COVERS
            and link.target_id == requirement.id
            and link.target_revision == requirement.revision
        ]
        scenario_tests = [
            artifact.id
            for artifact in self.model.latest_artifacts()
            if artifact.kind is ArtifactKind.SCENARIO_TEST
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
            if artifact.kind is ArtifactKind.VERIFICATION_EVIDENCE
            and artifact.properties.get("requirement") == requirement.ref
            and artifact.properties.get("result") == "pass"
        ]
        if not passed_evidence:
            diagnostics.append(
                f"requirement {requirement.ref} has no passing verification evidence"
            )

        return tuple(diagnostics)
