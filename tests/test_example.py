from sysml_v2_qvt.example import run_battery_example


def test_battery_example_is_complete_and_passes():
    result = run_battery_example()

    assert result["requirement"]["ref"] == "R-BATT-THERMAL@1"
    assert result["passed"] is True
    assert result["diagnostics"] == []
    assert result["evidence"]["properties"]["result"] == "pass"
    assert len(result["architecture"]) == 4
    assert len(result["componentTests"]) == 4
    assert len(result["scenarioTests"]) == 3
    assert "BL-BATT-THERMAL-1-" in result["baseline"]["id"]


def test_custom_example_json_flow(tmp_path):
    from sysml_v2_qvt.example import load_battery_example

    data = load_battery_example("examples/battery_thermal.json")
    result = run_battery_example(data)

    assert result["passed"] is True
    assert result["baseline"]["requirement"] == "R-BATT-THERMAL@1"
