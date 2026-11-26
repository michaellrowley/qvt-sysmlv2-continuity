import pytest

from sysml_v2_qvt.lifecycle import LifecycleEngine
from sysml_v2_qvt.model import Artifact, ArtifactKind, TraceKind


def test_full_lifecycle_enforces_trace_contract():
    engine = LifecycleEngine()
    need = Artifact(
        id="N-BATT",
        kind=ArtifactKind.STAKEHOLDER_NEED,
        properties={
            "statement": "Keep temperature in range.",
            "rationale": "Safety.",
            "acceptanceCriteria": ["Temperature in range."],
        },
    )
    requirement = engine.develop_intent(need)
    architecture = engine.realize_architecture(
        requirement,
        ["ThermalController", "TemperatureSensor", "Heater"],
    )
    behavior = engine.realize_behavior(
        requirement,
        architecture,
        "B-THERMAL",
        {
            "states": ["HEAT", "HOLD", "SAFE_OFF"],
            "heatBelowC": 24.0,
            "offAboveC": 26.0,
        },
    )
    evidence, component_tests, scenarios = engine.verify_satisfaction(
        requirement,
        behavior,
        evidence_id="E-THERMAL",
        result="pass",
        summary="All verification passed.",
        component_cases=[
            {
                "id": "TC-C-LOW",
                "purpose": "Low temperature",
                "temperatureC": 20,
                "expected": "HEAT",
            }
        ],
        simulated_scenarios=[
            {
                "id": "TC-S-COLD",
                "purpose": "Cold start",
                "initialTemperatureC": 18,
                "result": "pass",
            }
        ],
    )
    baseline = engine.baseline_thread(requirement)

    assert requirement.ref == "R-BATT@1"
    assert len(architecture) == 3
    assert len(component_tests) == 1
    assert len(scenarios) == 1
    assert evidence.properties["result"] == "pass"
    assert baseline.requirement_ref == requirement.ref
    assert requirement.ref in baseline.artifact_refs
    assert engine.check_continuity(requirement) == ()

    traces = engine.model.active_traces()
    assert any(
        trace.kind is TraceKind.ORIGIN
        and trace.source_ref == need.ref
        and trace.target_ref == requirement.ref
        for trace in traces
    )
    assert any(
        trace.kind is TraceKind.VERIFIES
        and trace.target_ref == evidence.ref
        for trace in traces
    )


def test_requirement_revision_propagates_and_invalidates_evidence():
    engine = LifecycleEngine()
    old_need = Artifact(
        id="N-BATT",
        kind=ArtifactKind.STAKEHOLDER_NEED,
        revision=1,
        properties={
            "statement": "Keep temperature between 20C and 30C.",
            "rationale": "Safety.",
            "acceptanceCriteria": ["In range."],
        },
    )
    old_requirement = engine.develop_intent(old_need)
    old_architecture = engine.realize_architecture(
        old_requirement,
        ["ThermalController", "Heater"],
    )
    old_behavior = engine.realize_behavior(
        old_requirement,
        old_architecture,
        "B-THERMAL",
        {"heatBelowC": 24.0, "offAboveC": 26.0},
    )
    old_evidence, _, _ = engine.verify_satisfaction(
        old_requirement,
        old_behavior,
        evidence_id="E-THERMAL",
        result="pass",
        summary="Old evidence.",
        component_cases=[{"id": "TC-C-LOW"}],
        simulated_scenarios=[{"id": "TC-S-COLD"}],
    )

    changed_need = Artifact(
        id="N-BATT",
        kind=ArtifactKind.STAKEHOLDER_NEED,
        revision=2,
        properties={
            "statement": "Keep temperature between 18C and 32C.",
            "rationale": "Updated envelope.",
            "acceptanceCriteria": ["Updated range."],
        },
    )
    new_requirement = engine.develop_intent(changed_need)
    new_architecture = engine.realize_architecture(
        new_requirement,
        ["ThermalController", "Heater"],
    )
    engine.realize_behavior(
        new_requirement,
        new_architecture,
        "B-THERMAL",
        {"heatBelowC": 24.0, "offAboveC": 26.0},
    )

    plan = engine.propagate_change(new_requirement)
    assert plan.root == new_requirement.ref
    assert old_evidence.ref in plan.invalidatedEvidence
    assert old_requirement.ref in plan.impacted


def test_reconcile_views_reports_semantic_conflicts():
    engine = LifecycleEngine()
    left = engine.model.add_artifact(
        Artifact(
            id="R-BATT",
            kind=ArtifactKind.REQUIREMENT,
            properties={"statement": "Temperature between 20C and 30C."},
        )
    )
    right = Artifact(
        id="R-BATT",
        kind=ArtifactKind.REQUIREMENT,
        revision=2,
        properties={"statement": "Temperature between 18C and 32C."},
    )

    reconciliation = engine.reconcile_views(left, right)

    assert reconciliation.status == "conflict"
    assert reconciliation.conflicts
    assert "semantic properties" in reconciliation.conflicts[0].reason


def test_baseline_is_repeatable():
    engine = LifecycleEngine()
    need = engine.model.add_artifact(
        Artifact(
            id="N-X",
            kind=ArtifactKind.STAKEHOLDER_NEED,
            properties={"statement": "Test baseline."},
        )
    )
    requirement = engine.develop_intent(need)
    first = engine.baseline_thread(requirement)
    second = engine.baseline_thread(requirement)

    assert first.id == second.id
    assert first.content_hash == second.content_hash
