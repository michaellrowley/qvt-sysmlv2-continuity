"""End-to-end battery thermal control example."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .codegen import CodeGenerationSpec, generate_implementation
from .lifecycle import LifecycleEngine
from .model import (
    Artifact,
    ArtifactKind,
    BehaviorModel,
    ContinuityModel,
)


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
            "entryPoint": "generate_heater_command",
            "initialState": "HOLD",
            "states": ["HEAT", "HOLD", "SAFE_OFF"],
            "heatBelowC": 24.0,
            "offAboveC": 26.0,
            "safeOffOnSensorFault": True,
            "parameters": [
                {
                    "name": "temperatureC",
                    "typeName": "float",
                    "direction": "in",
                    "required": True,
                },
                {
                    "name": "sensorValid",
                    "typeName": "bool",
                    "direction": "in",
                    "default": True,
                },
                {
                    "name": "currentState",
                    "typeName": "str",
                    "direction": "in",
                    "default": "HOLD",
                },
            ],
            "variables": [
                {
                    "name": "heaterCommand",
                    "typeName": "str",
                    "initialValue": "HOLD",
                    "mutable": True,
                }
            ],
            "results": [
                {
                    "name": "heaterCommand",
                    "typeName": "str",
                    "direction": "out",
                }
            ],
            "operations": [
                {
                    "id": "OP-GENERATE-HEATER-COMMAND",
                    "name": "generate_heater_command",
                    "kind": "function",
                    "parameters": [
                        {
                            "name": "temperatureC",
                            "typeName": "float",
                            "direction": "in",
                        },
                        {
                            "name": "sensorValid",
                            "typeName": "bool",
                            "direction": "in",
                            "default": True,
                        },
                    ],
                    "results": [
                        {
                            "name": "heaterCommand",
                            "typeName": "str",
                            "direction": "out",
                        }
                    ],
                    "asynchronous": False,
                }
            ],
            "functionCalls": [
                {
                    "id": "CALL-GENERATE-HEATER-COMMAND",
                    "functionName": "generate_heater_command",
                    "target": "ThermalController",
                    "synchronous": True,
                    "timeoutMs": 10,
                    "arguments": [
                        {"name": "temperatureC", "expression": "sensorTemperatureC"},
                        {"name": "sensorValid", "expression": "sensorValid"},
                        {"name": "currentState", "expression": "heaterState"},
                    ],
                    "returnBinding": "heaterCommand",
                }
            ],
            "communications": [
                {
                    "id": "COMM-TEMPERATURE-SENSOR",
                    "kind": "subscription",
                    "direction": "in",
                    "channel": "battery.temperature",
                    "protocol": "CAN",
                    "payloadType": "TemperatureReading",
                    "qos": {
                        "periodMs": 100,
                        "reliability": "best_effort",
                    },
                    "timeoutMs": 50,
                    "reliable": True,
                },
                {
                    "id": "COMM-HEATER-COMMAND",
                    "kind": "command",
                    "direction": "out",
                    "channel": "heater.command",
                    "protocol": "CAN",
                    "payloadType": "HeaterCommand",
                    "qos": {
                        "priority": 7,
                        "reliability": "eventual",
                    },
                    "timeoutMs": 10,
                    "reliable": True,
                }
            ],
            "schedules": [
                {
                    "id": "SCH-THERMAL-CONTROL",
                    "kind": "cyclic",
                    "periodMs": 100,
                    "startOffsetMs": 0,
                    "deadlineMs": 100,
                    "wcetMs": 5,
                    "priority": 50,
                    "jitterMs": 1,
                    "entryPoint": "generate_heater_command",
                }
            ],
            "transitions": [
                {
                    "id": "TRANS-SENSOR-FAULT",
                    "source": "HOLD",
                    "target": "SAFE_OFF",
                    "trigger": "SensorFault",
                    "guard": "not sensorValid",
                    "actions": [
                        {
                            "kind": "send",
                            "target": "heater.command",
                            "arguments": [
                                {"name": "command", "value": "SAFE_OFF"}
                            ],
                        }
                    ],
                },
                {
                    "id": "TRANS-LOW-TEMPERATURE",
                    "source": "HOLD",
                    "target": "HEAT",
                    "trigger": "TemperatureSample",
                    "guard": "temperatureC < heatBelowC",
                    "actions": [
                        {
                            "kind": "call",
                            "target": "generate_heater_command",
                            "returnBinding": "heaterCommand",
                        }
                    ],
                },
            ],
            "concurrency": "cyclic",
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
        "change": {
            "statement": (
                "Keep the battery within 18 to 32 degrees Celsius during "
                "normal operation and force safe-off after a sensor fault."
            ),
            "rationale": "Updated operating-temperature envelope.",
            "acceptanceCriteria": [
                "Normal-operation temperature remains between 18C and 32C.",
                "A sensor fault produces SAFE_OFF.",
            ],
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
    behavior_properties = BehaviorModel.from_dict(
        behavior_properties
    ).to_properties()
    behavior = engine.realize_behavior(
        requirement,
        architecture,
        behavior_data["id"],
        behavior_properties,
    )
    thermal_controller = next(
        element
        for element in architecture
        if element.properties.get("name") == "ThermalController"
    )
    allocation = engine.allocate_behavior(
        behavior,
        thermal_controller,
        properties={
            "scheduler": "cyclic",
        },
    )
    deployment = engine.deploy_component(
        behavior,
        thermal_controller,
        deployment={
            "environment": "battery-controller-node",
            "runtime": "bare-metal",
            "resources": {
                "cpuMsPerPeriod": 5,
                "memoryBytes": 4096,
            },
        },
    )

    implementation, implementation_source = generate_implementation(
        engine.model,
        behavior,
        data["implementation"]["id"],
        generate_battery_controller_source,
        language="Python",
        entry_point="generate_heater_command",
        code_generation=CodeGenerationSpec(
            target_language="Python",
            target_platform="embedded",
            entry_point="generate_heater_command",
            module_name="battery_thermal_controller",
            build_system="none",
            source_format="python",
        ),
    )
    verification_plan = engine.plan_verification(
        requirement,
        behavior,
        implementation=implementation,
        strategy="requirements-driven component and scenario verification",
        test_levels=["component", "simulation"],
        environments=["python-simulator", "hardware-in-loop"],
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
        verification_plan=verification_plan,
        execution_environment={
            "kind": "python-simulator",
            "target": "generic",
        },
    )

    baseline = engine.baseline_thread(requirement)
    diagnostics = engine.check_continuity(requirement, strict=True)
    return {
        "need": need.to_dict(),
        "requirement": requirement.to_dict(),
        "architecture": [element.to_dict() for element in architecture],
        "behavior": behavior.to_dict(),
        "allocation": allocation.to_dict(),
        "deployment": deployment.to_dict(),
        "implementation": implementation.to_dict(),
        "implementationSource": implementation_source,
        "verificationPlan": verification_plan.to_dict(),
        "componentResults": component_results,
        "scenarioResults": scenario_results,
        "componentTests": [test.to_dict() for test in component_tests],
        "scenarioTests": [test.to_dict() for test in scenario_tests],
        "evidence": evidence.to_dict(),
        "baseline": baseline.to_dict(),
        "diagnostics": list(diagnostics),
        "passed": all_passed,
    }
