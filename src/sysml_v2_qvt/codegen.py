"""Deterministic code derivation from SysML v2 behavior artifacts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .model import (
    Artifact,
    ArtifactKind,
    BehaviorModel,
    ContinuityModel,
    TraceKind,
    content_hash,
)


SourceProvider = Callable[[Artifact], str] | str


@dataclass(frozen=True)
class CodeGenerationSpec:
    target_language: str
    target_platform: str = ""
    entry_point: str = ""
    module_name: str = ""
    build_system: str = ""
    source_format: str = ""
    dependencies: tuple[str, ...] = ()
    compiler_flags: tuple[str, ...] = ()
    optimization: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CodeGenerationSpec":
        dependencies = value.get("dependencies", ())
        compiler_flags = value.get("compilerFlags", value.get("compiler_flags", ()))
        dependencies = dependencies or ()
        compiler_flags = compiler_flags or ()
        if isinstance(dependencies, str):
            dependencies = (dependencies,)
        if isinstance(compiler_flags, str):
            compiler_flags = (compiler_flags,)
        return cls(
            target_language=str(
                value.get("targetLanguage", value.get("language", ""))
            ),
            target_platform=str(value.get("targetPlatform", value.get("platform", ""))),
            entry_point=str(value.get("entryPoint", value.get("entry_point", ""))),
            module_name=str(value.get("moduleName", value.get("module", ""))),
            build_system=str(value.get("buildSystem", value.get("build_system", ""))),
            source_format=str(value.get("sourceFormat", value.get("source_format", ""))),
            dependencies=tuple(str(item) for item in dependencies),
            compiler_flags=tuple(str(item) for item in compiler_flags),
            optimization=str(value.get("optimization", "")),
            properties=dict(value.get("properties") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "targetLanguage": self.target_language,
            "targetPlatform": self.target_platform,
            "entryPoint": self.entry_point,
            "moduleName": self.module_name,
            "buildSystem": self.build_system,
            "sourceFormat": self.source_format,
            "dependencies": list(self.dependencies),
            "compilerFlags": list(self.compiler_flags),
            "optimization": self.optimization,
            "properties": dict(self.properties),
        }


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
    code_generation: CodeGenerationSpec | Mapping[str, Any] | None = None,
) -> tuple[Artifact, str]:
    behavior = model.add_artifact(behavior)
    source_text = source(behavior) if callable(source) else source
    digest = content_hash(source_text)
    spec = (
        CodeGenerationSpec.from_dict(code_generation)
        if isinstance(code_generation, Mapping)
        else code_generation
    )
    behavior_model = BehaviorModel.from_artifact(behavior)
    properties = {
        "sourceBehavior": behavior.ref,
        "sourceHash": behavior.content_hash,
        "contentHash": digest,
        "behaviorModel": behavior_model.to_dict(),
    }
    effective_language = language
    effective_entry_point = entry_point
    if spec is not None:
        effective_language = effective_language or spec.target_language or None
        effective_entry_point = effective_entry_point or spec.entry_point or behavior_model.entry_point or None
        properties["codeGeneration"] = spec.to_dict()
    if effective_language is not None:
        properties["language"] = effective_language
    if effective_entry_point is not None:
        properties["entryPoint"] = effective_entry_point
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
