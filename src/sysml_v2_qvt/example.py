"""End-to-end battery thermal control example."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .codegen import generate_implementation
from .lifecycle import LifecycleEngine
from .model import Artifact, ArtifactKind, ContinuityModel


def default_battery_example() -> dict[str, Any]:
    return {
        "need": {
            "id": "N-BATT-THERMAL",
            "requirementId": "R-BATT-THERMAL",
            "statement": (
                "Keep the battery within 20 to 30 degrees Celsius during normal "
                "operation and force safe-off after a temperature-sensor fault."
            ),
            "rationale": "Protect battery lifetime and prevent unsafe heater operation.",
            "acceptanceCriteria": [
                "Normal-operation temperature remains between 20C and 30C.",
                "A sensor fault produces SAFE_OFF.",
                "Fault handling completes within the declared timing budget.",
            ],
        },
        "architecture": [
            "BatteryPack",
            "TemperatureSensor",
            "ThermalController",
            "Heater",
        ],
        "behavior": {
            "id": "B-BATT-THERMAL-CONTROL",
            "kind": "state_machine",
            "states": ["HEAT", "HOLD", "SAFE_OFF"],
            "heatBelowC": 24.0,
            "offAboveC": 26.0,
            "safeOffOnSensorFault": True,
        },
        "implementation": {
            "id": "C-BATT-THERMAL-CONTROL",
        },
        "componentCases": [
            {
                "id": "TC-C-LOW",
                "purpose": "Low temperature requests heat.",
                "temperatureC": 20.0,
                "sensorValid": True,
                "currentState": "HOLD",
                "expected": "HEAT",
            },
            {
                "id": "TC-C-HIGH",
                "purpose": "High temperature turns the heater off.",
                "temperatureC": 32.0,
                "sensorValid": True,
                "currentState": "HOLD",
                "expected": "OFF",
            },
            {
                "id": "TC-C-DEADBAND",
                "purpose": "Deadband preserves the prior state.",
                "temperatureC": 25.0,
                "sensorValid": True,
                "currentState": "HOLD",
                "expected": "HOLD",
            },
            {
                "id": "TC-C-SENSOR-FAULT",
                "purpose": "Sensor fault forces safe-off.",
                "temperatureC": 25.0,
                "sensorValid": False,
                "currentState": "HEAT",
                "expected": "SAFE_OFF",
            },
        ],
        "scenarios": [
            {
                "id": "TC-S-COLD-START",
                "purpose": "Cold battery recovers into the normal temperature band.",
                "initialTemperatureC": 18.0,
                "ambientTemperatureC": 20.0,
                "steps": 50,
                "faultStep": None,
                "minTemperatureC": 20.0,
                "maxTemperatureC": 30.0,
            },
            {
                "id": "TC-S-HOT-AMBIENT",
                "purpose": "Hot ambient conditions cool below the upper limit.",
                "initialTemperatureC": 32.0,
                "ambientTemperatureC": 28.0,
                "steps": 50,
                "faultStep": None,
                "minTemperatureC": 20.0,
                "maxTemperatureC": 30.0,
            },
            {
                "id": "TC-S-SENSOR-LOSS",
                "purpose": "Sensor loss drives and maintains safe-off.",
                "initialTemperatureC": 27.0,
                "ambientTemperatureC": 25.0,
                "steps": 30,
                "faultStep": 5,
                "requireSafeOff": True,
            },
        ],
        "evidence": {
            "id": "E-BATT-THERMAL",
        },
    }


def load_battery_example(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        return default_battery_example()
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def generate_battery_controller_source(behavior: Artifact) -> str:
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


def generate_heater_command(
    temperature_c: float,
    sensor_valid: bool = True,
    current_state: str = "HOLD",
    heat_below_c: float = 24.0,
    off_above_c: float = 26.0,
) -> str:
    if not sensor_valid:
        return "SAFE_OFF"
    if temperature_c < heat_below_c:
        return "HEAT"
    if temperature_c > off_above_c:
        return "OFF"
    return current_state


def run_component_case(
    case: dict[str, Any],
    behavior: Mapping[str, Any],
) -> dict[str, Any]:
    actual = generate_heater_command(
        float(case["temperatureC"]),
        bool(case["sensorValid"]),
        str(case["currentState"]),
        float(behavior["heatBelowC"]),
        float(behavior["offAboveC"]),
    )
    return {
        "id": case["id"],
        "actual": actual,
        "expected": case["expected"],
        "passed": actual == case["expected"],
    }


def run_scenario(
    scenario: dict[str, Any],
    behavior: Mapping[str, Any],
) -> dict[str, Any]:
    temperature = float(scenario["initialTemperatureC"])
    ambient = float(scenario["ambientTemperatureC"])
    state = "HOLD"
    temperatures: list[float] = []
    commands: list[str] = []

    for step in range(int(scenario["steps"])):
        sensor_valid = not (
            scenario.get("faultStep") is not None
            and step == int(scenario["faultStep"])
        )
        command = generate_heater_command(
            temperature,
            sensor_valid,
            state,
            float(behavior["heatBelowC"]),
            float(behavior["offAboveC"]),
        )
        state = "SAFE_OFF" if command == "SAFE_OFF" else state
        commands.append(command)
        temperatures.append(temperature)

        if command == "HEAT":
            temperature += 0.25 + max(0.0, ambient - temperature) * 0.02
        elif command == "OFF":
            temperature -= 0.20 + max(0.0, temperature - ambient) * 0.02
        elif command == "SAFE_OFF":
            temperature += (ambient - temperature) * 0.05
        else:
            temperature += (ambient - temperature) * 0.02

    passed = True
    if "minTemperatureC" in scenario:
        passed = passed and temperature >= float(scenario["minTemperatureC"])
    if "maxTemperatureC" in scenario:
        passed = passed and temperature <= float(scenario["maxTemperatureC"])
    if scenario.get("requireSafeOff"):
        passed = passed and "SAFE_OFF" in commands

    return {
        "id": scenario["id"],
        "finalTemperatureC": round(temperature, 3),
        "commands": commands,
        "passed": passed,
    }


def run_battery_example(
    data: dict[str, Any] | None = None,
    model: ContinuityModel | None = None,
) -> dict[str, Any]:
    data = data or default_battery_example()
    engine = LifecycleEngine(model)

    need_data = data["need"]
    need = engine.model.add_artifact(
        Artifact(
            id=need_data["id"],
            kind=ArtifactKind.STAKEHOLDER_NEED,
            properties={
                "statement": need_data["statement"],
                "rationale": need_data["rationale"],
                "acceptanceCriteria": need_data["acceptanceCriteria"],
                **(
                    {"requirementId": need_data["requirementId"]}
                    if "requirementId" in need_data
                    else {}
                ),
            },
        )
    )
    requirement = engine.develop_intent(
        need,
        need_data.get("requirementId"),
    )
    architecture = engine.realize_architecture(
        requirement,
        data["architecture"],
        data.get("architectureIds"),
    )

    behavior_data = data["behavior"]
    behavior_properties = {
        key: value
        for key, value in behavior_data.items()
        if key != "id"
    }
    behavior = engine.realize_behavior(
        requirement,
        architecture,
        behavior_data["id"],
        behavior_properties,
    )

    implementation, implementation_source = generate_implementation(
        engine.model,
        behavior,
        data["implementation"]["id"],
        generate_battery_controller_source,
        language="Python",
        entry_point="generate_heater_command",
    )

    component_results = [
        run_component_case(case, behavior_properties)
        for case in data["componentCases"]
    ]
    scenario_results = [
        run_scenario(scenario, behavior_properties)
        for scenario in data["scenarios"]
    ]
    all_passed = (
        all(result["passed"] for result in component_results)
        and all(result["passed"] for result in scenario_results)
    )

    evidence, component_tests, scenario_tests = engine.verify_satisfaction(
        requirement,
        behavior,
        evidence_id=data["evidence"]["id"],
        result="pass" if all_passed else "fail",
        summary=(
            "All component cases and simulated scenarios passed."
            if all_passed
            else "One or more component cases or simulated scenarios failed."
        ),
        component_cases=[
            {
                **case,
                "result": "pass"
                if next(
                    result["passed"]
                    for result in component_results
                    if result["id"] == case["id"]
                )
                else "fail",
            }
            for case in data["componentCases"]
        ],
        simulated_scenarios=[
            {
                **scenario,
                "result": "pass"
                if next(
                    result["passed"]
                    for result in scenario_results
                    if result["id"] == scenario["id"]
                )
                else "fail",
            }
            for scenario in data["scenarios"]
        ],
        implementation=implementation,
    )

    baseline = engine.baseline_thread(requirement)
    diagnostics = engine.check_continuity(requirement)
    return {
        "need": need.to_dict(),
        "requirement": requirement.to_dict(),
        "architecture": [element.to_dict() for element in architecture],
        "behavior": behavior.to_dict(),
        "implementation": implementation.to_dict(),
        "implementationSource": implementation_source,
        "componentResults": component_results,
        "scenarioResults": scenario_results,
        "componentTests": [test.to_dict() for test in component_tests],
        "scenarioTests": [test.to_dict() for test in scenario_tests],
        "evidence": evidence.to_dict(),
        "baseline": baseline.to_dict(),
        "diagnostics": list(diagnostics),
        "passed": all_passed,
    }
