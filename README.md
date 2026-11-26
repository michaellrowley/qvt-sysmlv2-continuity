# SysML v2 QVT continuity

This repository provides a domain-neutral SysML v2 lifecycle with revisioned
artifacts and traceability contracts.

The lifecycle covers:

- intent and architecture realization;
- interfaces, ports, connections, function calls, communications, and scheduling;
- executable behavior realization and implementation generation;
- allocation, deployment, verification planning, and evidence;
- change propagation, view reconciliation, continuity checks, and baselines.

The battery thermal-control program is a demonstration adapter. Deterministic
code generation is a caller-supplied source renderer; it is not a battery-specific
QVT lifecycle operation.

Use `LifecycleKinds` to name artifact roles for another domain or meta-model.
Use `IdentityPolicy`/`DefaultIdentityPolicy` to control stable IDs for needs,
requirements, architecture elements, tests, and baselines. Domain values belong
in artifact properties and supplied data, not in the lifecycle engine.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m pytest -q
.venv/bin/python -m sysml_v2_qvt.cli battery
```

Run a custom example data file:

```bash
.venv/bin/python -m sysml_v2_qvt.cli battery --data examples/battery_thermal.json
```

Show the change-impact shape:

```bash
.venv/bin/python -m sysml_v2_qvt.cli impact
```

## QVT roles

**QVT-Relations** declares continuity invariants. It can be used in
`checkonly` mode to report broken relations and in constrained `enforce` mode
where the relation has a clear authoritative side.

**QVT-Operational** executes lifecycle transactions: it creates and revises
artifacts, marks supersession, sequences realization and verification,
reconciles views, propagates impact, and snapshots baselines. It does not
create `TraceLink` objects.

Trace links are owned by `ContinuityRelations`: QVT-Relations declares their
invariants, and a relation pass materializes the corresponding active links
after operational transactions.

**QVT-Core** is not authored here. It is an implementation/lowering concern,
not a useful user-facing lifecycle language for this repository.

The QVT sources reference a small adapter metamodel. They demonstrate the
contract and mapping shape; the Python implementation is the executable
reference runtime until a SysML v2 MOF adapter is connected.

## End-to-end lifecycle sequence

The operational flow below uses the QVT-Operational entry points and closes
through verification, reconciliation, baselining, and change propagation.

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant QR as QVT-Relations
    participant QL as QVT-Operational
    participant SYS as SYSML model
    participant CT as Continuity model
    participant CG as Code generator
    participant V as Verification environment

    Operator->>QL: main()
    QL->>SYS: Find StakeholderNeed objects

    loop Each stakeholder need
        SYS-->>QL: StakeholderNeed
        QL->>SYS: developIntent(need)
        opt Existing requirement
            QL->>SYS: markSuperseded(oldRequirement, newRequirement)
        end

        QL->>SYS: realizeArchitecture(requirement, elementSpecs)
        loop Each architecture element
            opt Existing element
                QL->>SYS: markSuperseded(oldElement, newElement)
            end
        end

        opt Interface and port realization
            QL->>SYS: realizeInterface(requirement, architecture, interfaceSpec)

            loop Each port
                QL->>SYS: realizePort(interface, portSpec)
            end
        end

        opt Port connection
            QL->>SYS: connectPorts(sourcePort, targetPort, connectionSpec)
        end

        QL->>SYS: realizeBehavior(requirement, architecture, behaviorSpec)
        opt Existing behavior
            QL->>SYS: markSuperseded(oldBehavior, newBehavior)
        end

        opt Function call
            QL->>SYS: configureFunctionCall(behavior, callSpec)
        end

        opt Communication
            QL->>SYS: configureCommunication(behavior, communicationSpec)
        end

        opt Schedule
            QL->>SYS: configureSchedule(behavior, scheduleSpec)
        end

        opt Allocation
            QL->>SYS: allocateBehavior(behavior, target, allocationSpec)
        end

        opt Deployment
            QL->>SYS: deployComponent(behavior, target, deploymentSpec)
        end

        QL->>CG: generateImplementation(behavior, codeGenerationSpec)
        CG->>SYS: Create or revise Implementation
        CG-->>QL: Implementation

        QL->>SYS: planVerification(requirement, behavior, implementation, planSpec)

        QL->>QR: enforceContinuityRelations(updatedThread)
        QR->>SYS: Match SYSML artifacts and revisions
        QR->>CT: Materialize active TraceLink objects
        QR-->>QL: Relation diagnostics

        alt Broken relation
            Operator->>QL: checkonly / enforce
            QL-->>Operator: Resolve or report relation
        end

        QL->>V: verifySatisfaction(requirement, behavior, tests, plan, environment)
        loop Component tests and scenarios
            V->>SYS: Produce test result
        end
        V-->>QL: VerificationEvidence

        QL->>QR: enforceVerificationRelations(evidence)
        QR->>CT: Materialize coverage and verification TraceLinks

        Operator->>QL: reconcileViews(left, right)
        QL->>SYS: Compare identity, kind, and properties
        QL-->>Operator: Reconciliation

        QL->>CT: baselineThread(requirement)
        CT-->>Operator: Hash-addressed Baseline

        QL->>CT: checkContinuity(requirement, strict=true)
        alt Passing lifecycle
            CT-->>Operator: No diagnostics
        else Missing or failing continuity
            CT-->>Operator: Diagnostics
        end
    end

    opt Change propagation
        Operator->>SYS: Revise need or lifecycle artifact
        SYS-->>QL: New revision

        QL->>SYS: developIntent(changedNeed)
        QL->>SYS: realizeArchitecture(revisedRequirement, revisedSpecs)
        QL->>SYS: realizeInterface / realizePort / connectPorts
        QL->>SYS: realizeBehavior(revisedRequirement, revisedArchitecture, revisedSpecs)
        QL->>SYS: configureFunctionCall / Communication / Schedule
        QL->>SYS: allocateBehavior / deployComponent
        QL->>CG: generateImplementation(revisedBehavior, revisedCodeGeneration)
        QL->>SYS: planVerification(revisedRequirement, revisedBehavior, revisedImplementation)
        QL->>QR: enforceContinuityRelations(revisedThread)
        QR->>CT: Revise active TraceLink objects
        QL->>V: verifySatisfaction(revisedThread)
        QL->>QR: enforceVerificationRelations(revisedEvidence)
        QR->>CT: Revise coverage and verification TraceLinks

        QL->>QL: propagateChange(changedArtifact)
        QL->>CT: Traverse active traces bidirectionally
        CT-->>QL: ImpactPlan
        QL-->>Operator: Impacted and invalidated artifacts

        Operator->>QL: reconcileViews(oldView, revisedView)
        QL->>CT: baselineThread(revisedRequirement)
        QL->>CT: checkContinuity(revisedRequirement, strict=true)
    end
```

The main operation sequence is:
`main` → `developIntent` → `realizeArchitecture` → interface/port and behavioral realization
→ allocation/deployment → `generateImplementation` → `planVerification`
→ Relations enforcement → `verifySatisfaction` → Relations enforcement
→ `reconcileViews` → `baselineThread`
→ `checkContinuity`; changed artifacts loop back through this sequence via
`propagateChange`.

## Generic lifecycle configuration

```python
from sysml_v2_qvt import Artifact, LifecycleEngine, LifecycleKinds

kinds = LifecycleKinds(
    stakeholder_need="goal",
    requirement="outcome",
    architectural_element="solution",
    behavior_element="workflow",
    verification_evidence="proof",
)
engine = LifecycleEngine(kinds=kinds)

goal = Artifact(
    id="GOAL-1",
    kind="goal",
    properties={"statement": "Complete the operation."},
)
outcome = engine.develop_intent(goal, "OUTCOME-1")
```

`generate_implementation()` accepts the source text or a renderer callback,
plus language and entry-point metadata. It never interprets domain properties:
that belongs to the selected renderer.

In the Python reference runtime, `LifecycleEngine` performs operational
transactions and `ContinuityRelations` materializes trace links for the
corresponding QVT-Relations invariants.

## Executable behavior contracts

Behavior models can describe:

- typed parameters, variables, and results;
- operations and provided/required interfaces;
- synchronous or asynchronous function calls and return bindings;
- subscriptions, publishes, commands, RPC, QoS, channels, endpoints, and timeouts;
- cyclic, periodic, one-shot, event-driven, or custom schedules;
- state transitions, guards, priorities, and actions;
- architecture allocations and runtime deployments;
- code-generation targets, entry points, build systems, dependencies, and flags;
- verification plans and execution environments.

Use `BehaviorModel`, `InterfaceSpec`, `PortSpec`, `FunctionCallSpec`,
`CommunicationSpec`, `ScheduleSpec`, `AllocationSpec`, `DeploymentSpec`, and
`CodeGenerationSpec` for typed values. Arbitrary domain metadata remains available
through each descriptor's `properties` mapping.

## Battery example

The example starts with `N-BATT-THERMAL`, derives `R-BATT-THERMAL`, realizes
four architectural elements and `B-BATT-THERMAL-CONTROL`, and deterministically
generates `C-BATT-THERMAL-CONTROL`.

It then creates:

- a structured behavior model with function calls, communications, transitions,
  and a cyclic schedule;
- allocation and deployment artifacts for the controller;
- a verification plan with component, simulation, and execution-environment coverage;
- component tests for low, high, deadband, and sensor-fault behavior;
- simulated cold-start, hot-ambient, and sensor-loss scenarios;
- verification evidence for the exact requirement, behavior, and code revisions;
- a hash-addressed baseline that closes across the full thread.

Every derived artifact is revisioned. Replacing an artifact creates a
`supersedes` trace instead of rewriting history.
