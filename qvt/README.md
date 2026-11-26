# QVT sources

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
