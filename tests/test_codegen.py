from pathlib import Path

from sysml_v2_qvt.codegen import generate_controller_source, generate_implementation
from sysml_v2_qvt.model import Artifact, ArtifactKind, ContinuityModel, TraceKind


def test_generated_controller_matches_example_source():
    behavior = Artifact(
        id="B-BATT",
        kind=ArtifactKind.BEHAVIOR_ELEMENT,
        properties={"heatBelowC": 24.0, "offAboveC": 26.0},
    )

    source = generate_controller_source(behavior)
    example_path = Path(__file__).parents[1] / "examples" / "battery_thermal_controller.py"

    assert "HEAT_BELOW_C = 24.0" in source
    assert "OFF_ABOVE_C = 26.0" in source
    assert source.strip() == example_path.read_text(encoding="utf-8").strip()


def test_codegen_records_trace_to_behavior():
    model = ContinuityModel()
    behavior = model.add_artifact(
        Artifact(
            id="B-BATT",
            kind=ArtifactKind.BEHAVIOR_ELEMENT,
            properties={"heatBelowC": 24.0, "offAboveC": 26.0},
        )
    )

    implementation, _ = generate_implementation(
        model,
        behavior,
        "C-BATT",
    )

    assert implementation.kind is ArtifactKind.IMPLEMENTATION
    assert implementation.properties["sourceBehavior"] == "B-BATT@1"
    assert any(
        trace.kind is TraceKind.GENERATES
        and trace.source_ref == behavior.ref
        and trace.target_ref == implementation.ref
        for trace in model.active_traces()
    )
