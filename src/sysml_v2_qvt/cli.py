"""Command-line entry point for the reference lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .example import load_battery_example, run_battery_example
from .model import Artifact, ArtifactKind


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

    impact = subparsers.add_parser(
        "impact",
        help="Show an example requirement-change impact plan",
    )
    impact.add_argument("--data", type=Path, help="Optional example JSON file")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data = load_battery_example(args.data) if hasattr(args, "data") and args.data else None

    if args.command == "battery":
        result = run_battery_example(data)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] and not result["diagnostics"] else 1

    if args.command == "impact":
        from .lifecycle import LifecycleEngine
        from .codegen import generate_implementation

        example_data = data or load_battery_example()
        engine = LifecycleEngine()
        baseline_result = run_battery_example(example_data, engine.model)

        changed_need = Artifact(
            id="N-BATT-THERMAL",
            kind=ArtifactKind.STAKEHOLDER_NEED,
            revision=2,
            properties={
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
        )
        engine.model.add_artifact(changed_need)
        revised_requirement = engine.develop_intent(changed_need)
        revised_architecture = engine.realize_architecture(
            revised_requirement,
            example_data["architecture"],
        )
        revised_behavior = engine.realize_behavior(
            revised_requirement,
            revised_architecture,
            example_data["behavior"]["id"],
            {
                key: value
                for key, value in example_data["behavior"].items()
                if key != "id"
            },
        )
        generate_implementation(
            engine.model,
            revised_behavior,
            example_data["implementation"]["id"],
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
