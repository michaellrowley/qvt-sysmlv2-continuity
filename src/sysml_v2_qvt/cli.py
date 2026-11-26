"""Command-line entry point for the reference lifecycle."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .codegen import CodeGenerationSpec
from .example import (
    generate_battery_controller_source,
    load_battery_example,
    run_battery_example,
)
from .model import Artifact, ArtifactKind, BehaviorModel
from .remote import SysMLV2ApiModel


def add_api_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--api-url",
        help="Hosted SysML v2 continuity API base URL",
    )
    parser.add_argument(
        "--api-project",
        help="Remote API project identifier",
    )
    parser.add_argument(
        "--api-token",
        default=None,
        help="Bearer or API-key token (defaults to SYSML_V2_API_TOKEN)",
    )


def build_repository(args: argparse.Namespace):
    api_url = getattr(args, "api_url", None)
    if not api_url:
        return None
    token = getattr(args, "api_token", None) or os.environ.get("SYSML_V2_API_TOKEN")
    return SysMLV2ApiModel(
        api_url,
        project_id=getattr(args, "api_project", None),
        token=token,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sysml-qvt-continuity",
        description="SysML v2 continuity and lifecycle reference",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    battery = subparsers.add_parser(
        "battery",
        help="Run the battery thermal-control end-to-end example",
    )
    battery.add_argument("--data", type=Path, help="Optional example JSON file")
    add_api_options(battery)

    impact = subparsers.add_parser(
        "impact",
        help="Show an example requirement-change impact plan",
    )
    impact.add_argument("--data", type=Path, help="Optional example JSON file")
    add_api_options(impact)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data = load_battery_example(args.data) if hasattr(args, "data") and args.data else None
    model = build_repository(args)

    if args.command == "battery":
        result = run_battery_example(data, model)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] and not result["diagnostics"] else 1

    if args.command == "impact":
        from .lifecycle import LifecycleEngine
        from .codegen import generate_implementation

        example_data = data or load_battery_example()
        engine = LifecycleEngine(model)
        baseline_result = run_battery_example(example_data, engine.model)
        change_data = example_data.get("change", {})

        changed_need = Artifact(
            id=example_data["need"]["id"],
            kind=ArtifactKind.STAKEHOLDER_NEED,
            revision=2,
            properties={
                **(
                    {"requirementId": example_data["need"]["requirementId"]}
                    if "requirementId" in example_data["need"]
                    else {}
                ),
                "statement": (
                    change_data.get(
                        "statement",
                        example_data["need"]["statement"],
                    )
                ),
                "rationale": change_data.get(
                    "rationale",
                    example_data["need"]["rationale"],
                ),
                "acceptanceCriteria": change_data.get(
                    "acceptanceCriteria",
                    example_data["need"]["acceptanceCriteria"],
                ),
            },
        )
        engine.model.add_artifact(changed_need)
        revised_requirement = engine.develop_intent(
            changed_need,
            example_data["need"].get("requirementId"),
        )
        revised_architecture = engine.realize_architecture(
            revised_requirement,
            example_data["architecture"],
            example_data.get("architectureIds"),
        )
        revised_behavior = engine.realize_behavior(
            revised_requirement,
            revised_architecture,
            example_data["behavior"]["id"],
            BehaviorModel.from_dict(
                {
                    key: value
                    for key, value in example_data["behavior"].items()
                    if key != "id"
                }
            ),
        )
        generate_implementation(
            engine.model,
            revised_behavior,
            example_data["implementation"]["id"],
            generate_battery_controller_source,
            language="Python",
            entry_point="generate_heater_command",
            code_generation=CodeGenerationSpec(
                target_language="Python",
                target_platform="embedded",
                entry_point="generate_heater_command",
                module_name="battery_thermal_controller",
            ),
        )
        thermal_controller = next(
            element
            for element in revised_architecture
            if element.properties.get("name") == "ThermalController"
        )
        engine.allocate_behavior(revised_behavior, thermal_controller)
        engine.deploy_component(revised_behavior, thermal_controller)
        engine.plan_verification(
            revised_requirement,
            revised_behavior,
            implementation=engine.model.latest(
                example_data["implementation"]["id"]
            ),
            strategy="impact-propagation verification",
            test_levels=["component", "simulation"],
            environments=["python-simulator", "HIL"],
        )

        plan = engine.propagate_change(revised_requirement)
        print(
            json.dumps(
                {
                    "exampleBaseline": baseline_result["baseline"]["id"],
                    "revisedRequirement": revised_requirement.ref,
                    "impact": plan.to_dict(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
