import pytest

from sysml_v2_qvt.codegen import CodeGenerationSpec, generate_implementation
from sysml_v2_qvt.lifecycle import LifecycleEngine, LifecycleKinds
from sysml_v2_qvt.model import (
    Artifact,
    ArtifactKind,
    BehaviorModel,
    CommunicationSpec,
    FunctionCallSpec,
    InterfaceSpec,
    OperationSpec,
    ParameterSpec,
    PortSpec,
    ScheduleSpec,
    TraceKind,
)
from sysml_v2_qvt.relations import ContinuityRelations


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
    requirement = engine.develop_intent(need, "R-BATT")
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
    old_requirement = engine.develop_intent(old_need, "R-BATT")
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
    new_requirement = engine.develop_intent(changed_need, "R-BATT")
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
    assert old_evidence.ref in plan.invalidatedArtifacts


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
    requirement = engine.develop_intent(need, "R-X")
    first = engine.baseline_thread(requirement)
    second = engine.baseline_thread(requirement)

    assert first.id == second.id
    assert first.content_hash == second.content_hash


def test_lifecycle_accepts_custom_domain_artifact_kinds():
    engine = LifecycleEngine(
        kinds=LifecycleKinds(
            stakeholder_need="goal",
            requirement="outcome",
            architectural_element="solution",
            behavior_element="workflow",
            implementation="code_artifact",
            component_test="unit_check",
            scenario_test="scenario_check",
            verification_evidence="proof",
        )
    )

    goal = engine.model.add_artifact(
        Artifact(
            id="GOAL-1",
            kind="goal",
            properties={
                "statement": "Complete the operation.",
                "rationale": "Operational need.",
                "acceptanceCriteria": ["The operation completes."],
            },
        )
    )
    outcome = engine.develop_intent(goal, "OUTCOME-1")
    solution = engine.realize_architecture(outcome, ["Coordinator"])
    workflow = engine.realize_behavior(
        outcome,
        solution,
        "WORKFLOW-1",
        {"steps": ["prepare", "execute"]},
    )
    evidence, component_tests, scenario_tests = engine.verify_satisfaction(
        outcome,
        workflow,
        evidence_id="PROOF-1",
        result="pass",
        summary="Checks passed.",
        component_cases=[{"id": "UNIT-1", "result": "pass"}],
        simulated_scenarios=[{"id": "SCENARIO-1", "result": "pass"}],
    )

    assert outcome.kind == "outcome"
    assert solution[0].kind == "solution"
    assert workflow.kind == "workflow"
    assert component_tests[0].kind == "unit_check"
    assert scenario_tests[0].kind == "scenario_check"
    assert evidence.kind == "proof"
    assert engine.check_continuity(outcome) == ()


def test_lifecycle_accepts_custom_identity_policy():
    class NamespacedIdentityPolicy:
        def requirement_id(self, need):
            return f"OUTCOME/{need.id}"

        def architecture_id(self, requirement, element_name):
            return f"SOLUTION/{requirement.id}/{element_name}"

        def component_test_id(self, requirement, case, index):
            return str(case.get("id", f"{requirement.id}/UNIT/{index}"))

        def scenario_test_id(self, requirement, scenario, index):
            return str(scenario.get("id", f"{requirement.id}/SCENARIO/{index}"))

        def baseline_id(self, requirement, digest):
            return f"SNAPSHOT-{digest[:12]}"

    engine = LifecycleEngine(identity_policy=NamespacedIdentityPolicy())
    need = engine.model.add_artifact(
        Artifact(
            id="GOAL-7",
            kind=ArtifactKind.STAKEHOLDER_NEED,
            properties={"statement": "Operate safely."},
        )
    )

    outcome = engine.develop_intent(need)
    architecture = engine.realize_architecture(outcome, ["SafetyCore"])
    baseline = engine.baseline_thread(outcome)

    assert outcome.id == "OUTCOME/GOAL-7"
    assert architecture[0].id == "SOLUTION/OUTCOME/GOAL-7/SafetyCore"
    assert baseline.id.startswith("SNAPSHOT-")


def test_continuity_relations_materialize_trace_links():
    from sysml_v2_qvt.model import ContinuityModel

    model = ContinuityModel()
    relations = ContinuityRelations(model)
    old_need = model.add_artifact(
        Artifact(
            id="N-SYSTEM",
            kind=ArtifactKind.STAKEHOLDER_NEED,
            revision=1,
        )
    )
    requirement = model.add_artifact(
        Artifact(
            id="R-SYSTEM",
            kind=ArtifactKind.REQUIREMENT,
            revision=1,
        )
    )
    replacement = model.add_artifact(
        Artifact(
            id="R-SYSTEM",
            kind=ArtifactKind.REQUIREMENT,
            revision=2,
            supersedes=("R-SYSTEM@1",),
        )
    )

    origin = relations.origin(
        old_need,
        requirement,
        derived_by="develop_intent",
    )
    supersession = relations.supersedes(
        requirement,
        replacement,
        derived_by="develop_intent",
    )

    assert origin.kind is TraceKind.ORIGIN
    assert supersession.kind is TraceKind.SUPERSEDES
    assert origin.source_ref == "N-SYSTEM@1"
    assert origin.target_ref == "R-SYSTEM@1"
    assert supersession.source_ref == "R-SYSTEM@1"
    assert supersession.target_ref == "R-SYSTEM@2"


def test_full_system_behavior_is_traceable_and_executable():
    engine = LifecycleEngine()
    need = engine.model.add_artifact(
        Artifact(
            id="N-SYSTEM",
            kind=ArtifactKind.STAKEHOLDER_NEED,
            properties={
                "statement": "Process commands and publish a status cyclically.",
                "rationale": "Distributed control.",
                "acceptanceCriteria": ["Status is published each cycle."],
            },
        )
    )
    requirement = engine.develop_intent(need, "R-SYSTEM")
    architecture = engine.realize_architecture(
        requirement,
        [{"id": "A-CONTROLLER", "name": "Controller"}],
    )
    controller = architecture[0]

    interface = engine.realize_interface(
        requirement,
        controller,
        "IF-CONTROLLER",
        InterfaceSpec(
            id="IF-CONTROLLER",
            name="ControllerInterface",
            protocol="CAN",
            operations=(
                OperationSpec(
                    id="OP-RUN",
                    name="run",
                    parameters=(
                        ParameterSpec(
                            name="command",
                            type_name="Command",
                            direction="in",
                        ),
                    ),
                    results=(
                        ParameterSpec(
                            name="status",
                            type_name="Status",
                            direction="out",
                        ),
                    ),
                ),
            ),
            ports=(
                PortSpec(
                    id="P-CONTROLLER-IN",
                    name="command_in",
                    direction="in",
                    interface_id="IF-CONTROLLER",
                ),
                PortSpec(
                    id="P-CONTROLLER-OUT",
                    name="status_out",
                    direction="out",
                    interface_id="IF-CONTROLLER",
                ),
            ),
        ),
    )

    behavior_model = BehaviorModel(
        kind="state_machine",
        entry_point="run",
        initial_state="RUNNING",
        states=("RUNNING", "FAULT"),
        function_calls=(
            FunctionCallSpec(
                id="CALL-RUN",
                function_name="run",
                target="Controller",
                synchronous=True,
                timeout_ms=20,
            ),
        ),
        communications=(
            CommunicationSpec(
                id="COMM-STATUS",
                kind="publish",
                direction="out",
                channel="system.status",
                protocol="DDS",
                payload_type="Status",
                qos={"periodMs": 10},
                timeout_ms=5,
            ),
        ),
        schedules=(
            ScheduleSpec(
                id="SCH-RUN",
                kind="cyclic",
                period_ms=10,
                deadline_ms=10,
                wcet_ms=2,
                priority=40,
                entry_point="run",
            ),
        ),
    )
    behavior = engine.realize_behavior(
        requirement,
        architecture,
        "B-CONTROLLER",
        behavior_model,
    )
    allocation = engine.allocate_behavior(
        behavior,
        controller,
        properties={"partition": "control"},
    )
    deployment = engine.deploy_component(
        behavior,
        controller,
        deployment={
            "environment": "real-time-node",
            "runtime": "RTOS",
            "resources": {"cpuMsPerPeriod": 2},
        },
    )

    implementation, source = generate_implementation(
        engine.model,
        behavior,
        "C-CONTROLLER",
        "int run(void) { publish_status(); return 0; }",
        code_generation=CodeGenerationSpec(
            target_language="C",
            target_platform="RTOS",
            entry_point="run",
            build_system="CMake",
        ),
    )
    plan = engine.plan_verification(
        requirement,
        behavior,
        implementation=implementation,
        strategy="component-and-integration",
        test_levels=["component", "integration"],
        environments=["simulator", "HIL"],
    )
    evidence, _, _ = engine.verify_satisfaction(
        requirement,
        behavior,
        evidence_id="E-SYSTEM",
        result="pass",
        summary="All execution contracts passed.",
        component_cases=[{"id": "TC-C-RUN"}],
        simulated_scenarios=[{"id": "TC-S-RUN"}],
        implementation=implementation,
        verification_plan=plan,
        execution_environment={"kind": "HIL", "target": "RTOS"},
    )

    assert interface.kind is ArtifactKind.INTERFACE
    assert allocation.kind is ArtifactKind.ALLOCATION
    assert deployment.kind is ArtifactKind.DEPLOYMENT
    assert plan.kind is ArtifactKind.VERIFICATION_PLAN
    assert evidence.properties["verificationPlan"] == plan.ref
    assert implementation.properties["behaviorModel"]["functionCalls"][0]["functionName"] == "run"
    assert implementation.properties["codeGeneration"]["targetLanguage"] == "C"
    assert source == "int run(void) { publish_status(); return 0; }"
    assert engine.check_continuity(requirement, strict=True) == ()
