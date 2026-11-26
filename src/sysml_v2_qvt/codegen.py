"""Deterministic code derivation from SysML v2 behavior artifacts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .model import Artifact, ArtifactKind, ContinuityModel, TraceKind, content_hash


SourceProvider = Callable[[Artifact], str] | str


def generate_implementation(
    model: ContinuityModel,
    behavior: Artifact,
    implementation_id: str,
    source: SourceProvider,
    *,
    language: str | None = None,
    entry_point: str | None = None,
    implementation_kind: ArtifactKind | str = ArtifactKind.IMPLEMENTATION,
    extra_properties: Mapping[str, Any] | None = None,
) -> tuple[Artifact, str]:
    behavior = model.add_artifact(behavior)
    source_text = source(behavior) if callable(source) else source
    digest = content_hash(source_text)
    properties = {
        "sourceBehavior": behavior.ref,
        "sourceHash": behavior.content_hash,
        "contentHash": digest,
    }
    if language is not None:
        properties["language"] = language
    if entry_point is not None:
        properties["entryPoint"] = entry_point
    if extra_properties:
        properties.update(extra_properties)

    try:
        existing = model.latest(implementation_id)
    except KeyError:
        existing = None

    if existing is not None and existing.properties == properties:
        implementation = existing
    else:
        revision = existing.revision + 1 if existing is not None else 1
        supersedes = (existing.ref,) if existing is not None else ()
        implementation = Artifact(
            id=implementation_id,
            kind=implementation_kind,
            revision=revision,
            properties=properties,
            supersedes=supersedes,
        )
        implementation = model.add_artifact(implementation)
        if existing is not None:
            model.ensure_trace(
                TraceKind.SUPERSEDES,
                existing,
                implementation,
                "deterministic_codegen",
            )

    model.ensure_trace(
        TraceKind.GENERATES,
        behavior,
        implementation,
        "deterministic_codegen",
    )
    model.ensure_trace(
        TraceKind.IMPLEMENTS,
        implementation,
        behavior,
        "deterministic_codegen",
    )
    return implementation, source_text
