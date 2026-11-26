from pathlib import Path

from sysml_v2_qvt.example import (
    generate_battery_controller_source,
    run_battery_example,
)
from sysml_v2_qvt.model import Artifact, ArtifactKind


def test_battery_controller_adapter_matches_example_source():
    behavior = Artifact(
        id="B-BATT",
        kind=ArtifactKind.BEHAVIOR_ELEMENT,
        properties={"heatBelowC": 24.0, "offAboveC": 26.0},
    )

    source = generate_battery_controller_source(behavior)
    example_path = Path(__file__).parents[1] / "examples" / "battery_thermal_controller.py"

    assert "HEAT_BELOW_C = 24.0" in source
    assert "OFF_ABOVE_C = 26.0" in source
    assert source.strip() == example_path.read_text(encoding="utf-8").strip()


def test_battery_example_is_complete_and_passes():
    result = run_battery_example()

    assert result["requirement"]["ref"] == "R-BATT-THERMAL@1"
    assert result["passed"] is True
    assert result["diagnostics"] == []
    assert result["evidence"]["properties"]["result"] == "pass"
    assert len(result["architecture"]) == 4
    assert len(result["componentTests"]) == 4
    assert len(result["scenarioTests"]) == 3
    assert result["behavior"]["properties"]["functionCalls"][0]["functionName"] == "generate_heater_command"
    assert result["behavior"]["properties"]["communications"][0]["channel"] == "battery.temperature"
    assert result["behavior"]["properties"]["schedules"][0]["periodMs"] == 100
    assert result["allocation"]["kind"] == "allocation"
    assert result["deployment"]["kind"] == "deployment"
    assert result["verificationPlan"]["kind"] == "verification_plan"
    assert result["implementation"]["properties"]["codeGeneration"]["targetLanguage"] == "Python"
    assert result["baseline"]["id"].startswith("BL-")


def test_custom_example_json_flow(tmp_path):
    from sysml_v2_qvt.example import load_battery_example

    data = load_battery_example("examples/battery_thermal.json")
    result = run_battery_example(data)

    assert result["passed"] is True
    assert result["baseline"]["requirement"] == "R-BATT-THERMAL@1"
