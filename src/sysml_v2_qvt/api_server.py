"""Small HTTP test API for the remote SysML v2 continuity adapter."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping
from urllib.parse import parse_qs, unquote, urlsplit

from .model import (
    Artifact,
    Baseline,
    BehaviorModel,
    AllocationSpec,
    DeploymentSpec,
    InterfaceSpec,
    PortSpec,
    TraceLink,
)
from .codegen import CodeGenerationSpec, generate_implementation
from .lifecycle import LifecycleEngine


class RepositoryStore:
    def __init__(self) -> None:
        self._artifacts: dict[tuple[str, int], Artifact] = {}
        self._latest: dict[str, Artifact] = {}
        self._traces: dict[tuple[Any, ...], TraceLink] = {}
        self._baselines: dict[str, Baseline] = {}

    def add_artifact(self, artifact: Artifact) -> Artifact:
        key = (artifact.id, artifact.revision)
        existing = self._artifacts.get(key)
        if existing is not None:
            return existing
        self._artifacts[key] = artifact
        current = self._latest.get(artifact.id)
        if current is None or artifact.revision >= current.revision:
            self._latest[artifact.id] = artifact
        return artifact

    def latest(self, artifact_id: str) -> Artifact:
        try:
            return self._latest[artifact_id]
        except KeyError as exc:
            raise KeyError(f"Unknown artifact: {artifact_id}") from exc

    def get(self, artifact_ref: str) -> Artifact:
        if "@" not in artifact_ref:
            return self.latest(artifact_ref)
        artifact_id, revision_text = artifact_ref.rsplit("@", 1)
        try:
            return self._artifacts[(artifact_id, int(revision_text))]
        except (KeyError, ValueError) as exc:
            raise KeyError(f"Unknown artifact revision: {artifact_ref}") from exc

    def all_artifacts(self) -> tuple[Artifact, ...]:
        return tuple(sorted(self._artifacts.values(), key=lambda item: item.ref))

    def latest_artifacts(self) -> tuple[Artifact, ...]:
        return tuple(sorted(self._latest.values(), key=lambda item: item.id))

    def add_trace(self, link: TraceLink) -> TraceLink:
        existing = self._traces.get(link.key)
        if existing is not None:
            return existing
        self._traces[link.key] = link
        return link

    def active_traces(self) -> tuple[TraceLink, ...]:
        return tuple(
            sorted(
                (link for link in self._traces.values() if link.status == "active"),
                key=lambda link: link.key,
            )
        )

    def add_baseline(self, baseline: Baseline) -> Baseline:
        self._baselines[baseline.id] = baseline
        return baseline

    def baseline(self, baseline_id: str) -> Baseline:
        try:
            return self._baselines[baseline_id]
        except KeyError as exc:
            raise KeyError(f"Unknown baseline: {baseline_id}") from exc

    def baselines(self) -> tuple[Baseline, ...]:
        return tuple(sorted(self._baselines.values(), key=lambda item: item.id))

    def materialize_trace(
        self,
        kind: Any,
        source: Artifact,
        target: Artifact,
        derived_by: str,
    ) -> TraceLink:
        link = TraceLink(
            kind=kind,
            source_id=source.id,
            source_revision=source.revision,
            target_id=target.id,
            target_revision=target.revision,
            status="active",
            derived_by=derived_by,
        )
        return self.add_trace(link)


class SysMLV2TestServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        token: str | None = None,
    ) -> None:
        self.token = token
        self.stores: dict[str, RepositoryStore] = {}
        super().__init__(server_address, SysMLV2TestHandler)

    def store(self, project_id: str) -> RepositoryStore:
        return self.stores.setdefault(project_id, RepositoryStore())


class SysMLV2TestHandler(BaseHTTPRequestHandler):
    server: SysMLV2TestServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _authorized(self) -> bool:
        token = self.server.token
        if not token:
            return True
        authorization = self.headers.get("Authorization", "")
        api_key = self.headers.get("X-API-Key", "")
        return authorization == f"Bearer {token}" or api_key == token

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._send_json(400, {"error": "Invalid JSON"})
            raise exc
        if not isinstance(value, dict):
            self._send_json(400, {"error": "JSON body must be an object"})
            raise ValueError("JSON body must be an object")
        return value

    def _route(self) -> tuple[str, list[str], str]:
        parsed = urlsplit(self.path)
        segments = [unquote(segment) for segment in parsed.path.strip("/").split("/") if segment]
        project_id = "default"
        if "projects" in segments:
            project_index = segments.index("projects")
            if project_index + 1 < len(segments):
                project_id = segments[project_index + 1]

        for resource in (
            "artifacts",
            "elements",
            "traces",
            "relationships",
            "links",
            "baselines",
            "operations",
            "health",
        ):
            if resource in segments:
                resource_index = segments.index(resource)
                remainder = segments[resource_index + 1:]
                return resource, remainder, project_id
        return "", [], project_id

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-API-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        if not self._authorized():
            self._send_json(401, {"error": "Unauthorized"})
            return

        parsed = urlsplit(self.path)
        resource, remainder, project_id = self._route()
        if resource == "health" or parsed.path.rstrip("/") == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "sysml-v2-continuity-test-api",
                },
            )
            return

        store = self.server.store(project_id)
        if resource in ("artifacts", "elements"):
            if not remainder:
                self._send_json(
                    200,
                    [artifact.to_dict() for artifact in store.all_artifacts()],
                )
                return
            if len(remainder) == 1 and remainder[0] in ("latest",):
                latest = [
                    item
                    for item in (
                        store.latest_artifacts()
                        if hasattr(store, "latest_artifacts")
                        else ()
                    )
                ]
                self._send_json(200, latest)
                return
            if len(remainder) == 2 and remainder[1] == "latest":
                try:
                    artifact = store.latest(remainder[0])
                except KeyError as exc:
                    self._send_json(404, {"error": str(exc)})
                    return
                self._send_json(200, artifact.to_dict())
                return
            if len(remainder) == 3 and remainder[1] == "revisions":
                try:
                    revision = int(remainder[2])
                    artifact = store.get(f"{remainder[0]}@{revision}")
                except (KeyError, ValueError) as exc:
                    self._send_json(404, {"error": str(exc)})
                    return
                self._send_json(200, artifact.to_dict())
                return
            if len(remainder) == 1:
                try:
                    artifact = store.get(remainder[0])
                except KeyError as exc:
                    self._send_json(404, {"error": str(exc)})
                    return
                self._send_json(200, artifact.to_dict())
                return

        if resource in ("traces", "relationships", "links"):
            query = parse_qs(urlsplit(self.path).query)
            traces = store.active_traces() if query.get("status") == ["active"] else ()
            if "status" not in query:
                traces = tuple(
                    sorted(
                        store.active_traces(),
                        key=lambda link: link.key,
                    )
                )
            self._send_json(200, [trace.to_dict() for trace in traces])
            return

        if resource == "baselines":
            if not remainder:
                self._send_json(
                    200,
                    [baseline.to_dict() for baseline in store.baselines()],
                )
                return
            try:
                baseline = store.baseline(remainder[0])
            except KeyError as exc:
                self._send_json(404, {"error": str(exc)})
                return
            self._send_json(200, baseline.to_dict())
            return

        self._send_json(404, {"error": "Not found"})

    @staticmethod
    def _serialize_result(value: Any) -> Any:
        if hasattr(value, "to_dict") and callable(value.to_dict):
            return value.to_dict()
        if isinstance(value, tuple):
            return [SysMLV2TestHandler._serialize_result(item) for item in value]
        if isinstance(value, list):
            return [SysMLV2TestHandler._serialize_result(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): SysMLV2TestHandler._serialize_result(item)
                for key, item in value.items()
            }
        return value

    @staticmethod
    def _artifact(value: Any, store: RepositoryStore) -> Artifact:
        if isinstance(value, Artifact):
            return value
        if isinstance(value, Mapping):
            return Artifact.from_dict(value)
        if isinstance(value, str):
            return store.get(value)
        raise TypeError("Expected an artifact or artifact reference")

    def _execute_operation(
        self,
        operation: str,
        arguments: Mapping[str, Any],
        store: RepositoryStore,
    ) -> Any:
        engine = LifecycleEngine(store)

        if operation == "develop_intent":
            return engine.develop_intent(
                Artifact.from_dict(arguments["need"]),
                arguments.get("requirementId"),
            )

        if operation == "realize_architecture":
            return engine.realize_architecture(
                Artifact.from_dict(arguments["requirement"]),
                tuple(arguments.get("elementNames", ())),
                dict(arguments.get("elementIds") or {}),
            )

        if operation == "realize_behavior":
            return engine.realize_behavior(
                Artifact.from_dict(arguments["requirement"]),
                tuple(
                    Artifact.from_dict(item)
                    for item in arguments.get("architecture", ())
                    if isinstance(item, Mapping)
                ),
                str(arguments["behaviorId"]),
                dict(arguments.get("properties") or {}),
            )

        if operation == "realize_interface":
            interface_value = arguments["interface"]
            interface_spec: InterfaceSpec | Mapping[str, Any] | str
            if isinstance(interface_value, Mapping):
                interface_spec = InterfaceSpec.from_dict(interface_value)
            else:
                interface_spec = str(interface_value)
            return engine.realize_interface(
                Artifact.from_dict(arguments["requirement"]),
                Artifact.from_dict(arguments["architecture"]),
                str(arguments["interfaceId"]),
                interface_spec,
                properties=dict(arguments.get("properties") or {}),
            )

        if operation == "realize_port":
            port_value = arguments["port"]
            port_spec: PortSpec | Mapping[str, Any] | str
            if isinstance(port_value, Mapping):
                port_spec = PortSpec.from_dict(port_value)
            else:
                port_spec = str(port_value)
            return engine.realize_port(
                Artifact.from_dict(arguments["interface"]),
                port_spec,
                port_id=arguments.get("portId"),
            )

        if operation == "connect_ports":
            return engine.connect_ports(
                Artifact.from_dict(arguments["sourcePort"]),
                Artifact.from_dict(arguments["targetPort"]),
                connection_id=str(arguments["connectionId"]),
                properties=dict(arguments.get("properties") or {}),
            )

        if operation == "allocate_behavior":
            allocation_value = arguments.get("allocation")
            allocation: AllocationSpec | Mapping[str, Any] | None
            if isinstance(allocation_value, Mapping):
                allocation = AllocationSpec.from_dict(allocation_value)
            else:
                allocation = None
            return engine.allocate_behavior(
                Artifact.from_dict(arguments["behavior"]),
                Artifact.from_dict(arguments["target"]),
                allocation_id=arguments.get("allocationId"),
                allocation=allocation,
                properties=dict(arguments.get("properties") or {}),
            )

        if operation == "deploy_component":
            deployment_value = arguments.get("deployment")
            deployment: DeploymentSpec | Mapping[str, Any] | None
            if isinstance(deployment_value, Mapping):
                deployment = DeploymentSpec.from_dict(deployment_value)
            else:
                deployment = None
            return engine.deploy_component(
                Artifact.from_dict(arguments["component"]),
                Artifact.from_dict(arguments["target"]),
                deployment_id=arguments.get("deploymentId"),
                deployment=deployment,
            )

        if operation == "plan_verification":
            implementation_value = arguments.get("implementation")
            implementation = (
                Artifact.from_dict(implementation_value)
                if isinstance(implementation_value, Mapping)
                else None
            )
            return engine.plan_verification(
                Artifact.from_dict(arguments["requirement"]),
                Artifact.from_dict(arguments["behavior"]),
                implementation=implementation,
                plan_id=arguments.get("planId"),
                strategy=str(arguments.get("strategy", "")),
                test_levels=tuple(arguments.get("testLevels", ())),
                environments=tuple(arguments.get("environments", ())),
                properties=dict(arguments.get("properties") or {}),
            )

        if operation == "verify_satisfaction":
            implementation_value = arguments.get("implementation")
            implementation = (
                Artifact.from_dict(implementation_value)
                if isinstance(implementation_value, Mapping)
                else None
            )
            verification_plan_value = arguments.get("verificationPlan")
            verification_plan: Artifact | str | None
            if isinstance(verification_plan_value, Mapping):
                verification_plan = Artifact.from_dict(verification_plan_value)
            elif isinstance(verification_plan_value, str):
                verification_plan = verification_plan_value
            else:
                verification_plan = None
            evidence, component_tests, scenario_tests = engine.verify_satisfaction(
                Artifact.from_dict(arguments["requirement"]),
                Artifact.from_dict(arguments["behavior"]),
                evidence_id=str(arguments["evidenceId"]),
                result=str(arguments["result"]),
                summary=str(arguments["summary"]),
                component_cases=tuple(arguments.get("componentCases", ())),
                simulated_scenarios=tuple(arguments.get("simulatedScenarios", ())),
                implementation=implementation,
                verification_plan=verification_plan,
                execution_environment=dict(arguments.get("executionEnvironment") or {}),
            )
            return {
                "evidence": evidence.to_dict(),
                "componentTests": [test.to_dict() for test in component_tests],
                "scenarioTests": [test.to_dict() for test in scenario_tests],
            }

        if operation == "propagate_change":
            plan = engine.propagate_change(
                Artifact.from_dict(arguments["root"])
            )
            return plan.to_dict()

        if operation == "reconcile_views":
            return engine.reconcile_views(
                self._artifact(arguments["left"], store),
                self._artifact(arguments["right"], store),
            ).to_dict()

        if operation == "baseline_thread":
            return engine.baseline_thread(
                Artifact.from_dict(arguments["requirement"])
            ).to_dict()

        if operation == "check_continuity":
            return list(
                engine.check_continuity(
                    Artifact.from_dict(arguments["requirement"]),
                    strict=bool(arguments.get("strict", False)),
                )
            )

        if operation == "generate_implementation":
            code_generation_value = arguments.get("codeGeneration")
            code_generation = (
                CodeGenerationSpec.from_dict(code_generation_value)
                if isinstance(code_generation_value, Mapping)
                else None
            )
            implementation, source = generate_implementation(
                store,
                Artifact.from_dict(arguments["behavior"]),
                str(arguments["implementationId"]),
                str(arguments["source"]),
                language=arguments.get("language"),
                entry_point=arguments.get("entryPoint"),
                implementation_kind=str(arguments.get("implementationKind", "implementation")),
                extra_properties=dict(arguments.get("extraProperties") or {}),
                code_generation=code_generation,
            )
            return {
                "implementation": implementation.to_dict(),
                "source": source,
            }

        raise KeyError(f"Unknown lifecycle operation: {operation}")

    def do_POST(self) -> None:
        if not self._authorized():
            self._send_json(401, {"error": "Unauthorized"})
            return
        resource, remainder, project_id = self._route()
        store = self.server.store(project_id)
        try:
            body = self._read_json()
        except (json.JSONDecodeError, ValueError):
            return

        if resource == "operations":
            operation = remainder[0] if remainder else str(body.get("operation", ""))
            arguments = body.get("arguments")
            if not isinstance(arguments, Mapping):
                arguments = {}
            try:
                result = self._execute_operation(operation, arguments, store)
            except KeyError as exc:
                self._send_json(404, {"error": str(exc)})
                return
            except (TypeError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
                return
            self._send_json(
                200,
                {
                    "operation": operation,
                    "result": self._serialize_result(result),
                },
            )
            return

        if resource in ("artifacts", "elements"):
            try:
                artifact = Artifact.from_dict(body)
            except (KeyError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            stored = store.add_artifact(artifact)
            self._send_json(200, stored.to_dict())
            return

        if resource in ("traces", "relationships", "links"):
            try:
                trace = TraceLink.from_dict(body)
            except (KeyError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            stored = store.add_trace(trace)
            self._send_json(200, stored.to_dict())
            return

        if resource == "baselines":
            try:
                baseline = Baseline.from_dict(body)
            except (KeyError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            stored = store.add_baseline(baseline)
            self._send_json(200, stored.to_dict())
            return

        self._send_json(404, {"error": "Not found"})

    do_PUT = do_POST


def create_api_server(
    host: str = "127.0.0.1",
    port: int = 0,
    *,
    token: str | None = None,
) -> SysMLV2TestServer:
    return SysMLV2TestServer((host, port), token=token)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Test API for the SysML v2 continuity adapter")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    parser.add_argument("--token", default=os.environ.get("SYSML_V2_API_TOKEN"))
    args = parser.parse_args(argv)

    server = create_api_server(args.host, args.port, token=args.token)
    print(
        json.dumps(
            {
                "status": "listening",
                "host": args.host,
                "port": server.server_address[1],
            }
        )
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
