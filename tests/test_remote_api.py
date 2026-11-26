from threading import Thread

import pytest

from sysml_v2_qvt.api_server import create_api_server
from sysml_v2_qvt.example import run_battery_example
from sysml_v2_qvt.model import (
    Artifact,
    ArtifactKind,
    Baseline,
    TraceKind,
)
from sysml_v2_qvt.remote import (
    SysMLV2ApiError,
    SysMLV2ApiModel,
)


@pytest.fixture
def remote_api():
    server = create_api_server("127.0.0.1", 0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    model = SysMLV2ApiModel(f"http://{host}:{port}")
    try:
        yield model
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_remote_api_stores_revisioned_artifacts(remote_api):
    first = remote_api.add_artifact(
        Artifact(
            id="R-SYSTEM",
            kind=ArtifactKind.REQUIREMENT,
            revision=1,
            properties={"statement": "Initial requirement"},
        )
    )
    second = remote_api.add_artifact(
        Artifact(
            id="R-SYSTEM",
            kind=ArtifactKind.REQUIREMENT,
            revision=2,
            properties={"statement": "Revised requirement"},
            supersedes=(first.ref,),
        )
    )

    assert remote_api.latest("R-SYSTEM").ref == second.ref
    assert remote_api.get("R-SYSTEM@1").properties["statement"] == "Initial requirement"
    assert remote_api.latest_artifacts()[0].ref == "R-SYSTEM@2"
    assert [artifact.ref for artifact in remote_api.all_artifacts()] == [
        "R-SYSTEM@1",
        "R-SYSTEM@2",
    ]


def test_remote_api_stores_traces_and_baselines(remote_api):
    need = remote_api.add_artifact(
        Artifact(
            id="N-SYSTEM",
            kind=ArtifactKind.STAKEHOLDER_NEED,
        )
    )
    requirement = remote_api.add_artifact(
        Artifact(
            id="R-SYSTEM",
            kind=ArtifactKind.REQUIREMENT,
        )
    )
    trace = remote_api.materialize_trace(
        TraceKind.ORIGIN,
        need,
        requirement,
        "test",
    )
    baseline = remote_api.add_baseline(
        Baseline(
            id="BL-SYSTEM",
            requirement_ref=requirement.ref,
            artifact_refs=(need.ref, requirement.ref),
            trace_keys=(trace.key,),
            content_hash="abc",
        )
    )

    assert remote_api.active_traces()[0].source_ref == "N-SYSTEM@1"
    assert remote_api.baseline("BL-SYSTEM").id == baseline.id
    assert remote_api.baselines()[0].requirement_ref == "R-SYSTEM@1"


def test_remote_api_runs_full_battery_lifecycle(remote_api):
    result = run_battery_example(model=remote_api)

    assert result["passed"] is True
    assert result["diagnostics"] == []
    assert remote_api.latest("R-BATT-THERMAL").ref == "R-BATT-THERMAL@1"
    assert remote_api.baseline(result["baseline"]["id"]).id == result["baseline"]["id"]
    assert remote_api.active_traces()


def test_remote_api_supports_project_scope_and_bearer_auth():
    server = create_api_server("127.0.0.1", 0, token="test-secret")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    try:
        unauthorized = SysMLV2ApiModel(base_url, project_id="P-SAFE")
        with pytest.raises(SysMLV2ApiError) as exc:
            unauthorized.health()
        assert exc.value.status == 401

        authorized = SysMLV2ApiModel(
            base_url,
            project_id="P-SAFE",
            token="test-secret",
        )
        assert authorized.health()["status"] == "ok"
        artifact = authorized.add_artifact(
            Artifact(id="N-PROJECT", kind=ArtifactKind.STAKEHOLDER_NEED)
        )
        assert authorized.latest("N-PROJECT").ref == artifact.ref
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
