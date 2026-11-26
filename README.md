# SysML v2 QVT continuity

This repository implements a higher-level SysML v2 lifecycle with traceability
contracts:

- `develop_intent`
- `realize_architecture`
- `realize_behavior`
- `verify_satisfaction`
- `propagate_change`
- `reconcile_views`
- `baseline_thread`

The lifecycle engine, model, trace, and verification APIs are domain-neutral.
The battery thermal-control program is only a demonstration adapter. Deterministic
code generation is a caller-supplied source renderer, not a battery-specific
operation or an additional QVT lifecycle operation.

Use `LifecycleKinds` to name artifact roles for another domain or meta-model.
Use `IdentityPolicy`/`DefaultIdentityPolicy` to control stable IDs for needs,
requirements, architecture elements, tests, and baselines. Domain values belong
in artifact properties and supplied data, not in the lifecycle engine.

## Repository layout

```text
qvt/
  ContinuityRelations.qvtr       Declarative continuity invariants
  LifecycleOperational.qvto      Executable lifecycle operations
  README.md                      Adapter metamodel notes
src/sysml_v2_qvt/
  model.py                       Revisions, traces, baselines, impacts
  lifecycle.py                   Reference operation implementation
  codegen.py                     Generic behavior-to-source adapter
  example.py                     Battery thermal-control example adapter
  cli.py                         Command-line entry point
examples/
  battery_thermal.json           Complete example data
  battery_thermal_controller.py Generated-style controller
tests/
  test_lifecycle.py
  test_example.py
  test_codegen.py
```

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

**QVT-Operational** implements transaction, sequencing, revision,
supersession, reconciliation, impact, and baseline behavior.

**QVT-Core** is not authored here. It is an implementation/lowering concern,
not a useful user-facing lifecycle language for this repository.

The QVT sources reference a small adapter metamodel. They demonstrate the
contract and mapping shape; the Python implementation is the executable
reference runtime until a SysML v2 MOF adapter is connected.

## Generic lifecycle configuration

```python
from sysml_v2_qvt import Artifact, ArtifactKind, LifecycleEngine, LifecycleKinds

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

## Battery example

The example starts with `N-BATT-THERMAL`, derives `R-BATT-THERMAL`, realizes
four architectural elements and `B-BATT-THERMAL-CONTROL`, and deterministically
generates `C-BATT-THERMAL-CONTROL`.

It then creates:

- component tests for low, high, deadband, and sensor-fault behavior;
- simulated cold-start, hot-ambient, and sensor-loss scenarios;
- verification evidence for the exact requirement, behavior, and code revisions;
- a hash-addressed baseline that closes across the full thread.

Every derived artifact is revisioned. Replacing an artifact creates a
`supersedes` trace instead of rewriting history.
