# QVT sources

`ContinuityRelations.qvtr` declares the consistency relations. It is the
constraint/invariant layer:

- stakeholder need to requirement;
- requirement to architecture;
- architecture to behavior;
- behavior to deterministic implementation;
- test to requirement and behavior;
- behavior to passing verification evidence.

`LifecycleOperational.qvto` is the execution layer. It creates revisions,
adds supersession links, ensures trace links, verifies the full thread, computes
impact, reconciles views, and snapshots baselines.

The source files target a small adapter metamodel named `SYSML` and a
continuity metamodel named `CONTINUITY`. Their type names are intentionally
explicit:

- `SYSML::StakeholderNeed`
- `SYSML::Requirement`
- `SYSML::ArchitecturalElement`
- `SYSML::BehaviorElement`
- `SYSML::Implementation`
- `SYSML::TestCase`
- `SYSML::VerificationEvidence`
- `CONTINUITY::TraceLink`
- `CONTINUITY::ImpactPlan`
- `CONTINUITY::Reconciliation`
- `CONTINUITY::Baseline`

Stable identity, revision, and `properties` fields are part of the adapter
contract. These sources are reference implementations, not a claim that the
types are literal SysML v2 metaclass names.

The example mappings use explicit source/target identities and properties rather
than domain-specific ID prefixes. Domains can provide their own identity
fields, artifact-role names, and code-generation adapters.

The executable behavior contract includes typed parameters and variables,
provided and required operations, function calls, communication subscriptions,
publishes and commands, cyclic or event schedules, state transitions, and
behavior actions. Interfaces, ports, connections, allocations, deployments,
code-generation specifications, verification plans, execution environments,
and implementation trace links are first-class contract elements rather than
battery-specific properties.
