from sysml_v2_qvt.codegen import CodeGenerationSpec, generate_implementation
from sysml_v2_qvt.model import Artifact, ContinuityModel, TraceKind


def test_generic_codegen_records_properties_and_trace():
    model = ContinuityModel()
    behavior = model.add_artifact(
        Artifact(
            id="B-SYSTEM",
            kind="process",
            properties={"entry": "start", "exit": "finish"},
        )
    )

    def render(process: Artifact) -> str:
        return f"run(start={process.properties['entry']}, exit={process.properties['exit']})"

    implementation, source = generate_implementation(
        model,
        behavior,
        "C-SYSTEM",
        render,
        language="DSL",
        entry_point="run",
        implementation_kind="code_artifact",
        code_generation=CodeGenerationSpec(
            target_language="DSL",
            target_platform="runtime",
            entry_point="run",
            module_name="system",
            dependencies=("core",),
            compiler_flags=("-O2",),
        ),
    )

    assert implementation.kind == "code_artifact"
    assert implementation.properties["sourceBehavior"] == "B-SYSTEM@1"
    assert implementation.properties["language"] == "DSL"
    assert implementation.properties["entryPoint"] == "run"
    assert implementation.properties["behaviorModel"]["kind"] == "state_machine"
    assert implementation.properties["codeGeneration"]["targetPlatform"] == "runtime"
    assert implementation.properties["codeGeneration"]["dependencies"] == ["core"]
    assert source == "run(start=start, exit=finish)"
    assert any(
        trace.kind is TraceKind.GENERATES
        and trace.source_ref == behavior.ref
        and trace.target_ref == implementation.ref
        for trace in model.active_traces()
    )
