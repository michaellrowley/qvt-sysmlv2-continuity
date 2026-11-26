"""Deterministic code derivation from SysML v2 behavior artifacts."""

from __future__ import annotations

from .model import Artifact, ArtifactKind, ContinuityModel, TraceKind, content_hash


def generate_controller_source(behavior: Artifact) -> str:
    """Render a small controller implementation from behavior properties."""
    heat_below = float(behavior.properties["heatBelowC"])
    off_above = float(behavior.properties["offAboveC"])
    return f'''HEAT_BELOW_C = {heat_below:.1f}
OFF_ABOVE_C = {off_above:.1f}
SAFE_OFF = "SAFE_OFF"


def generate_heater_command(
    temperature_c: float,
    sensor_valid: bool = True,
    current_state: str = "HOLD",
) -> str:
    if not sensor_valid:
        return SAFE_OFF
    if temperature_c < HEAT_BELOW_C:
        return "HEAT"
    if temperature_c > OFF_ABOVE_C:
        return "OFF"
    return current_state
'''


def generate_implementation(
    model: ContinuityModel,
    behavior: Artifact,
    implementation_id: str,
) -> tuple[Artifact, str]:
    behavior = model.add_artifact(behavior)
    source = generate_controller_source(behavior)
    digest = content_hash(source)
    properties = {
        "language": "Python",
        "sourceBehavior": behavior.ref,
        "sourceHash": behavior.content_hash,
        "contentHash": digest,
        "entryPoint": "generate_heater_command",
    }

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
            kind=ArtifactKind.IMPLEMENTATION,
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
    return implementation, source
