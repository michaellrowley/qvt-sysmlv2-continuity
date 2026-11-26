"""HTTP adapter for a remotely hosted SysML v2 continuity repository."""

from __future__ import annotations

import json
import ssl
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .model import (
    Artifact,
    Baseline,
    TraceKind,
    TraceLink,
)


class SysMLV2ApiError(RuntimeError):
    """Raised when a hosted SysML v2 API cannot complete a request."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        response: str = "",
        method: str = "",
        url: str = "",
    ) -> None:
        super().__init__(message)
        self.status = status
        self.response = response
        self.method = method
        self.url = url


RemoteApiError = SysMLV2ApiError
SysMLV2APIError = SysMLV2ApiError


class SysMLV2ApiModel:
    """Continuity repository backed by an HTTP API hosted by a SysML v2 service."""

    def __init__(
        self,
        base_url: str,
        *,
        project_id: str | None = None,
        token: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
        headers: Mapping[str, str] | None = None,
        verify_ssl: bool = True,
        api_prefix: str = "/api/v1",
        artifacts_path: str = "/artifacts",
        traces_path: str = "/traces",
        baselines_path: str = "/baselines",
        operations_path: str = "/operations",
        health_path: str = "/health",
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.token = token
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.api_prefix = api_prefix.strip("/")
        self.artifacts_path = artifacts_path
        self.traces_path = traces_path
        self.baselines_path = baselines_path
        self.operations_path = operations_path
        self.health_path = health_path
        self.headers = dict(headers or {})

    def _api_prefix(self) -> str:
        prefix = self.base_url
        if self.api_prefix:
            prefix = f"{prefix}/{self.api_prefix}"
        if self.project_id:
            prefix = f"{prefix}/projects/{quote(self.project_id, safe='')}"
        return prefix

    def _resolve(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if path.startswith("/"):
            if path == self.health_path:
                return f"{self.base_url}{path}"
            return f"{self._api_prefix()}{path}"
        return f"{self._api_prefix()}/{path}"

    def _headers(self) -> dict[str, str]:
        headers = dict(self.headers)
        headers.setdefault("Accept", "application/json")
        if self.token:
            headers.setdefault("Authorization", f"Bearer {self.token}")
        if self.api_key:
            headers.setdefault("X-API-Key", self.api_key)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        query: Mapping[str, Any] | None = None,
    ) -> Any:
        url = self._resolve(path)
        if query:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(query)}"

        body = None
        headers = self._headers()
        if payload is not None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=body, headers=headers, method=method)

        try:
            context = ssl.create_default_context()
            if not self.verify_ssl:
                context = ssl._create_unverified_context()
            with urlopen(request, timeout=self.timeout, context=context) as response:
                raw = response.read()
        except HTTPError as exc:
            raw = exc.read()
            response_text = raw.decode("utf-8", errors="replace")
            try:
                detail = json.loads(response_text).get("error", response_text)
            except (json.JSONDecodeError, AttributeError):
                detail = response_text or exc.reason
            raise SysMLV2ApiError(
                f"{method} {url} returned HTTP {exc.code}: {detail}",
                status=exc.code,
                response=response_text,
                method=method,
                url=url,
            ) from exc
        except (URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise SysMLV2ApiError(
                f"{method} {url} failed: {reason}",
                method=method,
                url=url,
            ) from exc

        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SysMLV2ApiError(
                f"{method} {url} returned invalid JSON",
                response=raw.decode("utf-8", errors="replace"),
                method=method,
                url=url,
            ) from exc

    @staticmethod
    def _unwrap(payload: Any, *keys: str) -> Any:
        if isinstance(payload, Mapping):
            for key in keys:
                if key in payload:
                    return payload[key]
        return payload

    def _artifact_from_response(self, payload: Any) -> Artifact:
        value = self._unwrap(payload, "artifact")
        if not isinstance(value, Mapping):
            raise SysMLV2ApiError("API returned an invalid artifact response")
        return Artifact.from_dict(value)

    def _trace_from_response(self, payload: Any) -> TraceLink:
        value = self._unwrap(payload, "trace", "link")
        if not isinstance(value, Mapping):
            raise SysMLV2ApiError("API returned an invalid trace response")
        return TraceLink.from_dict(value)

    def _baseline_from_response(self, payload: Any) -> Baseline:
        value = self._unwrap(payload, "baseline")
        if not isinstance(value, Mapping):
            raise SysMLV2ApiError("API returned an invalid baseline response")
        return Baseline.from_dict(value)

    def _artifacts_collection(self, payload: Any) -> tuple[Artifact, ...]:
        value = self._unwrap(payload, "artifacts", "elements", "items")
        if not isinstance(value, list):
            raise SysMLV2ApiError("API returned an invalid artifact collection")
        return tuple(
            Artifact.from_dict(item)
            for item in value
            if isinstance(item, Mapping)
        )

    def _traces_collection(self, payload: Any) -> tuple[TraceLink, ...]:
        value = self._unwrap(payload, "traces", "relationships", "links", "items")
        if not isinstance(value, list):
            raise SysMLV2ApiError("API returned an invalid trace collection")
        return tuple(
            TraceLink.from_dict(item)
            for item in value
            if isinstance(item, Mapping)
        )

    def _baselines_collection(self, payload: Any) -> tuple[Baseline, ...]:
        value = self._unwrap(payload, "baselines", "items")
        if not isinstance(value, list):
            raise SysMLV2ApiError("API returned an invalid baseline collection")
        return tuple(
            Baseline.from_dict(item)
            for item in value
            if isinstance(item, Mapping)
        )

    def health(self) -> Any:
        return self._request("GET", self.health_path)

    def execute_operation(
        self,
        operation: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> Any:
        """Execute a lifecycle operation in the hosted SysML v2 service."""

        payload = self._request(
            "POST",
            f"{self.operations_path}/{quote(operation, safe='_')}",
            {"operation": operation, "arguments": dict(arguments or {})},
        )
        if isinstance(payload, Mapping):
            if "error" in payload:
                raise SysMLV2ApiError(
                    f"Remote lifecycle operation {operation} failed: {payload['error']}"
                )
            if "result" in payload:
                return payload["result"]
        return payload

    def add_artifact(self, artifact: Artifact) -> Artifact:
        payload = self._request("POST", self.artifacts_path, artifact.to_dict())
        return self._artifact_from_response(payload)

    def latest(self, artifact_id: str) -> Artifact:
        try:
            payload = self._request(
                "GET",
                f"{self.artifacts_path}/{quote(artifact_id, safe='')}/latest",
            )
            return self._artifact_from_response(payload)
        except SysMLV2ApiError as exc:
            if exc.status != 404:
                raise

        artifacts = self.all_artifacts()
        matches = [artifact for artifact in artifacts if artifact.id == artifact_id]
        if not matches:
            raise KeyError(f"Unknown artifact: {artifact_id}")
        return max(matches, key=lambda artifact: artifact.revision)

    def get(self, artifact_ref: str) -> Artifact:
        if "@" not in artifact_ref:
            return self.latest(artifact_ref)

        artifact_id, revision_text = artifact_ref.rsplit("@", 1)
        try:
            revision = int(revision_text)
        except ValueError as exc:
            raise KeyError(f"Unknown artifact revision: {artifact_ref}") from exc
        payload = self._request(
            "GET",
            (
                f"{self.artifacts_path}/{quote(artifact_id, safe='')}"
                f"/revisions/{revision}"
            ),
        )
        return self._artifact_from_response(payload)

    def all_artifacts(self) -> tuple[Artifact, ...]:
        payload = self._request("GET", self.artifacts_path)
        return self._artifacts_collection(payload)

    def latest_artifacts(self) -> tuple[Artifact, ...]:
        latest: dict[str, Artifact] = {}
        for artifact in self.all_artifacts():
            current = latest.get(artifact.id)
            if current is None or artifact.revision >= current.revision:
                latest[artifact.id] = artifact
        return tuple(sorted(latest.values(), key=lambda item: item.id))

    def materialize_trace(
        self,
        kind: TraceKind | str,
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
        payload = self._request("POST", self.traces_path, link.to_dict())
        return self._trace_from_response(payload)

    def active_traces(self) -> tuple[TraceLink, ...]:
        payload = self._request(
            "GET",
            self.traces_path,
            query={"status": "active"},
        )
        return tuple(
            sorted(
                (
                    link
                    for link in self._traces_collection(payload)
                    if link.status == "active"
                ),
                key=lambda link: link.key,
            )
        )

    def add_baseline(self, baseline: Baseline) -> Baseline:
        payload = self._request("POST", self.baselines_path, baseline.to_dict())
        return self._baseline_from_response(payload)

    def baseline(self, baseline_id: str) -> Baseline:
        payload = self._request(
            "GET",
            f"{self.baselines_path}/{quote(baseline_id, safe='')}",
        )
        return self._baseline_from_response(payload)

    def baselines(self) -> tuple[Baseline, ...]:
        payload = self._request("GET", self.baselines_path)
        return tuple(
            sorted(
                self._baselines_collection(payload),
                key=lambda item: item.id,
            )
        )


RemoteContinuityModel = SysMLV2ApiModel
HostedSysMLV2Model = SysMLV2ApiModel
