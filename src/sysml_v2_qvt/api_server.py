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
    TraceLink,
)


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

        for resource in ("artifacts", "elements", "traces", "relationships", "links", "baselines", "health"):
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
