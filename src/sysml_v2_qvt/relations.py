"""Executable implementation of declarative continuity relations."""

from __future__ import annotations

from .model import (
    Artifact,
    ContinuityModel,
    TraceKind,
    TraceLink,
)


class ContinuityRelations:
    """Enforce trace relations against the executable continuity model."""

    def __init__(self, model: ContinuityModel) -> None:
        self.model = model

    def enforce(
        self,
        kind: TraceKind | str,
        source: Artifact,
        target: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        source = self.model.add_artifact(source)
        target = self.model.add_artifact(target)
        return self.model.materialize_trace(
            kind,
            source,
            target,
            derived_by,
        )

    def supersedes(
        self,
        old: Artifact,
        replacement: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.SUPERSEDES,
            old,
            replacement,
            derived_by=derived_by,
        )

    def origin(
        self,
        need: Artifact,
        requirement: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.ORIGIN,
            need,
            requirement,
            derived_by=derived_by,
        )

    def realizes(
        self,
        requirement: Artifact,
        target: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.REALIZES,
            requirement,
            target,
            derived_by=derived_by,
        )

    def exposes(
        self,
        source: Artifact,
        target: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.EXPOSES,
            source,
            target,
            derived_by=derived_by,
        )

    def connects(
        self,
        source: Artifact,
        target: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.CONNECTS,
            source,
            target,
            derived_by=derived_by,
        )

    def supports(
        self,
        architecture: Artifact,
        behavior: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.SUPPORTS,
            architecture,
            behavior,
            derived_by=derived_by,
        )

    def calls(
        self,
        behavior: Artifact,
        call: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.CALLS,
            behavior,
            call,
            derived_by=derived_by,
        )

    def schedules(
        self,
        behavior: Artifact,
        schedule: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.SCHEDULES,
            behavior,
            schedule,
            derived_by=derived_by,
        )

    def allocates(
        self,
        source: Artifact,
        target: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.ALLOCATES,
            source,
            target,
            derived_by=derived_by,
        )

    def deployed_to(
        self,
        component: Artifact,
        target: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.DEPLOYED_TO,
            component,
            target,
            derived_by=derived_by,
        )

    def generates(
        self,
        behavior: Artifact,
        implementation: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.GENERATES,
            behavior,
            implementation,
            derived_by=derived_by,
        )

    def implements(
        self,
        implementation: Artifact,
        behavior: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.IMPLEMENTS,
            implementation,
            behavior,
            derived_by=derived_by,
        )

    def covers(
        self,
        source: Artifact,
        requirement: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.COVERS,
            source,
            requirement,
            derived_by=derived_by,
        )

    def executes(
        self,
        source: Artifact,
        target: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.EXECUTES,
            source,
            target,
            derived_by=derived_by,
        )

    def verifies(
        self,
        source: Artifact,
        evidence: Artifact,
        *,
        derived_by: str,
    ) -> TraceLink:
        return self.enforce(
            TraceKind.VERIFIES,
            source,
            evidence,
            derived_by=derived_by,
        )
