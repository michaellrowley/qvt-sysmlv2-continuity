# Legacy QVT sources

QVT is retained for compatibility and executable lifecycle lower-level
implementation. The primary interface is CRUD:

```text
Create  -> new domain/subsystem/requirement/behavior/implementation/test
Request -> retrieve entity or activity-set revisions
Update  -> revision replacement and supersession
Delete  -> preserve history while marking the entity deleted
```

The legacy V-lifecycle operation model is retained as a compatibility
transformation, but the primary model interface is CRUD:

| Operator | Legacy lifecycle effect |
|---|---|
| Create | Create a domain, subsystem, requirement, interface, behavior, implementation, test, or baseline. |
| Request | Read/retrieve an entity or activity set. |
| Update | Create a new revision and supersede the prior version. |
| Delete | Mark the entity deleted while retaining its history. |

`LifecycleOperational.qvto` is an executable Eclipse QVT-OML transformation
with the former operational scope:

- `markSuperseded`
- `developIntent`
- `realizeArchitecture`
- `realizeInterface`
- `realizePort`
- `connectPorts`
- `realizeBehavior`
- `configureFunctionCall`
- `configureCommunication`
- `configureSchedule`
- `allocateBehavior`
- `deployComponent`
- `generateImplementation`
- `planVerification`
- `verifySatisfaction`
- `propagateChange`
- `reconcileViews`
- `baselineThread`
- `checkContinuity`

The Java application converts repository `.sysml` text into EMF/Ecore objects,
runs Eclipse QVT-OML, and converts the revised model back to SysML text.

`ContinuityRelations.qvtr` records the full declarative continuity relation
contract. It covers:

- artifact supersession;
- stakeholder need to requirement origin;
- requirement realization by architecture;
- architecture interface and port exposure;
- port-to-port connections;
- architecture support of behavior;
- behavior function calls;
- behavior communication;
- behavior scheduling;
- behavior allocation;
- component deployment;
- behavior implementation;
- verification-plan evidence;
- test coverage and execution.

The Java `ContinuityRelations` implementation enforces this complete scope,
supports `checkonly` diagnostics and `enforce` trace materialization, and
materializes active links. Direct execution of the `.qvtr` file by a QVT
Relations engine remains a separate integration.

## End-to-end lifecycle sequence

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant TXT as .sysml text
    participant PILOT as Pilot parser
    participant BRIDGE as EMF/Ecore bridge
    participant QVT as Eclipse QVT-Operational
    participant LIFE as Lifecycle engine
    participant REL as QVT-Relations contract
    participant VERIFY as Verification environment

    Operator->>TXT: Edit need and lifecycle artifacts
    Operator->>PILOT: Validate syntax and semantics
    PILOT-->>Operator: Syntax and semantic result
    Operator->>BRIDGE: Run qvt
    BRIDGE->>BRIDGE: Convert text to EObjects
    BRIDGE->>QVT: Execute LifecycleOperational.qvto
    QVT-->>BRIDGE: Revised model
    BRIDGE->>LIFE: Synchronize complete lifecycle
    LIFE->>LIFE: Intent and architecture realization
    LIFE->>LIFE: Interfaces, ports, connections, behavior
    LIFE->>LIFE: Calls, communication, schedule
    LIFE->>LIFE: Allocation and deployment
    LIFE->>LIFE: Implementation and verification planning
    LIFE->>REL: checkonly or enforce
    REL-->>Operator: Diagnostics or active TraceLinks
    LIFE->>VERIFY: Verify satisfaction
    VERIFY-->>LIFE: Test and scenario evidence
    LIFE->>REL: Enforce verification relations
    LIFE-->>Operator: Reconciliation, baseline, continuity diagnostics

    opt Change propagation
        Operator->>LIFE: Revise artifact
        LIFE->>LIFE: Re-run lifecycle operations
        LIFE->>LIFE: propagateChange
        LIFE-->>Operator: ImpactPlan
        LIFE->>LIFE: Reconcile and baseline revised thread
    end
```
