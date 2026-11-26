"""Core artifact, trace, baseline, and impact types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class ArtifactKind(str, Enum):
    STAKEHOLDER_NEED = "stakeholder_need"
    REQUIREMENT = "requirement"
    ARCHITECTURAL_ELEMENT = "architectural_element"
    INTERFACE = "interface"
    PORT = "port"
    CONNECTION = "connection"
    BEHAVIOR_ELEMENT = "behavior_element"
    IMPLEMENTATION = "implementation"
    ALLOCATION = "allocation"
    DEPLOYMENT = "deployment"
    COMPONENT_TEST = "component_test"
    SCENARIO_TEST = "scenario_test"
    VERIFICATION_EVIDENCE = "verification_evidence"
    VERIFICATION_PLAN = "verification_plan"


class TraceKind(str, Enum):
    ORIGIN = "origin"
    REALIZES = "realizes"
    SUPPORTS = "supports"
    EXPOSES = "exposes"
    REQUIRES = "requires"
    PROVIDES = "provides"
    CONNECTS = "connects"
    ALLOCATES = "allocates"
    DEPLOYED_TO = "deployed_to"
    IMPLEMENTS = "implements"
    GENERATES = "generates"
    CALLS = "calls"
    PUBLISHES = "publishes"
    SUBSCRIBES = "subscribes"
    RECEIVES = "receives"
    SCHEDULES = "schedules"
    COVERS = "covers"
    EXECUTES = "executes"
    VERIFIES = "verifies"
    SUPERSEDES = "supersedes"


def kind_value(kind: ArtifactKind | str) -> str:
    return kind.value if isinstance(kind, ArtifactKind) else str(kind)


def trace_kind_value(kind: TraceKind | str) -> str:
    return kind.value if isinstance(kind, TraceKind) else str(kind)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_items(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return tuple(item if isinstance(item, Mapping) else {"value": item} for item in value)
    if isinstance(value, Mapping):
        return (value,)
    return ()


def _optional_int(value: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in value and value[key] is not None:
            return int(value[key])
    return None


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    type_name: str = "Any"
    direction: str = "in"
    default: Any = None
    required: bool = True
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ParameterSpec":
        return cls(
            name=str(value.get("name", value.get("id", ""))),
            type_name=str(value.get("typeName", value.get("type", "Any"))),
            direction=str(value.get("direction", "in")),
            default=value.get("default"),
            required=bool(value.get("required", True)),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "typeName": self.type_name,
            "direction": self.direction,
            "default": self.default,
            "required": self.required,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class VariableSpec:
    name: str
    type_name: str = "Any"
    initial_value: Any = None
    mutable: bool = True
    scope: str = "local"
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VariableSpec":
        return cls(
            name=str(value.get("name", value.get("id", ""))),
            type_name=str(value.get("typeName", value.get("type", "Any"))),
            initial_value=value.get("initialValue", value.get("initial", None)),
            mutable=bool(value.get("mutable", True)),
            scope=str(value.get("scope", "local")),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "typeName": self.type_name,
            "initialValue": self.initial_value,
            "mutable": self.mutable,
            "scope": self.scope,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class OperationSpec:
    id: str
    name: str
    kind: str = "function"
    parameters: tuple[ParameterSpec, ...] = ()
    results: tuple[ParameterSpec, ...] = ()
    asynchronous: bool = False
    timeout_ms: int | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OperationSpec":
        name = str(value.get("name", value.get("id", "")))
        parameters = tuple(
            item if isinstance(item, ParameterSpec) else ParameterSpec.from_dict(_mapping(item))
            for item in value.get("parameters", ())
            if isinstance(item, (ParameterSpec, Mapping))
        )
        results = tuple(
            item if isinstance(item, ParameterSpec) else ParameterSpec.from_dict(_mapping(item))
            for item in value.get("results", value.get("returns", ()))
            if isinstance(item, (ParameterSpec, Mapping))
        )
        return cls(
            id=str(value.get("id", name)),
            name=name,
            kind=str(value.get("kind", "function")),
            parameters=parameters,
            results=results,
            asynchronous=bool(value.get("asynchronous", value.get("async", False))),
            timeout_ms=_optional_int(value, "timeoutMs", "timeout_ms"),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "results": [result.to_dict() for result in self.results],
            "asynchronous": self.asynchronous,
            "timeoutMs": self.timeout_ms,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class PortSpec:
    id: str
    name: str
    direction: str = "bidirectional"
    kind: str = "interface"
    interface_id: str = ""
    protocol: str = ""
    binding: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PortSpec":
        name = str(value.get("name", value.get("id", "")))
        return cls(
            id=str(value.get("id", name)),
            name=name,
            direction=str(value.get("direction", "bidirectional")),
            kind=str(value.get("kind", "interface")),
            interface_id=str(value.get("interfaceId", value.get("interface", ""))),
            protocol=str(value.get("protocol", "")),
            binding=dict(_mapping(value.get("binding"))),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "direction": self.direction,
            "kind": self.kind,
            "interfaceId": self.interface_id,
            "protocol": self.protocol,
            "binding": dict(self.binding),
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class InterfaceSpec:
    id: str
    name: str
    kind: str = "interface"
    protocol: str = ""
    operations: tuple[OperationSpec, ...] = ()
    ports: tuple[PortSpec, ...] = ()
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InterfaceSpec":
        name = str(value.get("name", value.get("id", "")))
        operations = tuple(
            item if isinstance(item, OperationSpec) else OperationSpec.from_dict(_mapping(item))
            for item in value.get("operations", ())
            if isinstance(item, (OperationSpec, Mapping))
        )
        ports = tuple(
            item if isinstance(item, PortSpec) else PortSpec.from_dict(_mapping(item))
            for item in value.get("ports", ())
            if isinstance(item, (PortSpec, Mapping))
        )
        return cls(
            id=str(value.get("id", name)),
            name=name,
            kind=str(value.get("kind", "interface")),
            protocol=str(value.get("protocol", "")),
            operations=operations,
            ports=ports,
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "protocol": self.protocol,
            "operations": [operation.to_dict() for operation in self.operations],
            "ports": [port.to_dict() for port in self.ports],
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class ArgumentBinding:
    name: str
    value: Any = None
    expression: str = ""
    by_reference: bool = False
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArgumentBinding":
        return cls(
            name=str(value.get("name", value.get("id", ""))),
            value=value.get("value"),
            expression=str(value.get("expression", "")),
            by_reference=bool(value.get("byReference", value.get("by_reference", False))),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "expression": self.expression,
            "byReference": self.by_reference,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class FunctionCallSpec:
    id: str
    function_name: str
    target: str = ""
    arguments: tuple[ArgumentBinding, ...] = ()
    return_binding: str = ""
    synchronous: bool = True
    timeout_ms: int | None = None
    precondition: str = ""
    postcondition: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FunctionCallSpec":
        function_name = str(
            value.get("functionName", value.get("function", value.get("name", "")))
        )
        arguments = tuple(
            item if isinstance(item, ArgumentBinding) else ArgumentBinding.from_dict(_mapping(item))
            for item in value.get("arguments", ())
            if isinstance(item, (ArgumentBinding, Mapping))
        )
        return cls(
            id=str(value.get("id", function_name)),
            function_name=function_name,
            target=str(value.get("target", value.get("callee", ""))),
            arguments=arguments,
            return_binding=str(
                value.get("returnBinding", value.get("return", value.get("result", "")))
            ),
            synchronous=bool(value.get("synchronous", not value.get("asynchronous", False))),
            timeout_ms=_optional_int(value, "timeoutMs", "timeout_ms"),
            precondition=str(value.get("precondition", "")),
            postcondition=str(value.get("postcondition", "")),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "functionName": self.function_name,
            "target": self.target,
            "arguments": [argument.to_dict() for argument in self.arguments],
            "returnBinding": self.return_binding,
            "synchronous": self.synchronous,
            "timeoutMs": self.timeout_ms,
            "precondition": self.precondition,
            "postcondition": self.postcondition,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class CommunicationSpec:
    id: str
    kind: str
    direction: str = "out"
    channel: str = ""
    endpoint: str = ""
    protocol: str = ""
    operation: str = ""
    payload_type: str = ""
    payload_mapping: dict[str, Any] = field(default_factory=dict)
    qos: dict[str, Any] = field(default_factory=dict)
    timeout_ms: int | None = None
    reliable: bool = True
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CommunicationSpec":
        return cls(
            id=str(value.get("id", value.get("channel", value.get("topic", "")))),
            kind=str(value.get("kind", "event")),
            direction=str(value.get("direction", "out")),
            channel=str(value.get("channel", value.get("topic", ""))),
            endpoint=str(value.get("endpoint", "")),
            protocol=str(value.get("protocol", "")),
            operation=str(value.get("operation", "")),
            payload_type=str(value.get("payloadType", value.get("payload", ""))),
            payload_mapping=dict(_mapping(value.get("payloadMapping"))),
            qos=dict(_mapping(value.get("qos"))),
            timeout_ms=_optional_int(value, "timeoutMs", "timeout_ms"),
            reliable=bool(value.get("reliable", True)),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "direction": self.direction,
            "channel": self.channel,
            "endpoint": self.endpoint,
            "protocol": self.protocol,
            "operation": self.operation,
            "payloadType": self.payload_type,
            "payloadMapping": dict(self.payload_mapping),
            "qos": dict(self.qos),
            "timeoutMs": self.timeout_ms,
            "reliable": self.reliable,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class ScheduleSpec:
    id: str
    kind: str = "cyclic"
    period_ms: int | None = None
    start_offset_ms: int = 0
    deadline_ms: int | None = None
    wcet_ms: int | None = None
    priority: int | None = None
    jitter_ms: int = 0
    entry_point: str = ""
    trigger: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScheduleSpec":
        return cls(
            id=str(value.get("id", value.get("entryPoint", "schedule"))),
            kind=str(value.get("kind", "cyclic")),
            period_ms=_optional_int(value, "periodMs", "period_ms"),
            start_offset_ms=_optional_int(
                value,
                "startOffsetMs",
                "start_offset_ms",
            ) or 0,
            deadline_ms=_optional_int(value, "deadlineMs", "deadline_ms"),
            wcet_ms=_optional_int(value, "wcetMs", "wcet_ms"),
            priority=_optional_int(value, "priority"),
            jitter_ms=_optional_int(value, "jitterMs", "jitter_ms") or 0,
            entry_point=str(value.get("entryPoint", value.get("entry_point", ""))),
            trigger=str(value.get("trigger", "")),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "periodMs": self.period_ms,
            "startOffsetMs": self.start_offset_ms,
            "deadlineMs": self.deadline_ms,
            "wcetMs": self.wcet_ms,
            "priority": self.priority,
            "jitterMs": self.jitter_ms,
            "entryPoint": self.entry_point,
            "trigger": self.trigger,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class BehaviorAction:
    kind: str
    target: str = ""
    arguments: tuple[ArgumentBinding, ...] = ()
    return_binding: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BehaviorAction":
        arguments = tuple(
            item if isinstance(item, ArgumentBinding) else ArgumentBinding.from_dict(_mapping(item))
            for item in value.get("arguments", ())
            if isinstance(item, (ArgumentBinding, Mapping))
        )
        return cls(
            kind=str(value.get("kind", "custom")),
            target=str(value.get("target", "")),
            arguments=arguments,
            return_binding=str(value.get("returnBinding", value.get("return", ""))),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "target": self.target,
            "arguments": [argument.to_dict() for argument in self.arguments],
            "returnBinding": self.return_binding,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class BehaviorTransition:
    id: str
    source: str
    target: str
    trigger: str = ""
    guard: str = ""
    actions: tuple[BehaviorAction, ...] = ()
    priority: int | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BehaviorTransition":
        actions = tuple(
            item if isinstance(item, BehaviorAction) else BehaviorAction.from_dict(_mapping(item))
            for item in value.get("actions", ())
            if isinstance(item, (BehaviorAction, Mapping))
        )
        return cls(
            id=str(value.get("id", f"{value.get('source', '')}->{value.get('target', '')}")),
            source=str(value.get("source", value.get("from", ""))),
            target=str(value.get("target", value.get("to", ""))),
            trigger=str(value.get("trigger", "")),
            guard=str(value.get("guard", value.get("condition", ""))),
            actions=actions,
            priority=_optional_int(value, "priority"),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "trigger": self.trigger,
            "guard": self.guard,
            "actions": [action.to_dict() for action in self.actions],
            "priority": self.priority,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class BehaviorModel:
    kind: str = "state_machine"
    entry_point: str = ""
    initial_state: str = ""
    states: tuple[str, ...] = ()
    parameters: tuple[ParameterSpec, ...] = ()
    variables: tuple[VariableSpec, ...] = ()
    results: tuple[ParameterSpec, ...] = ()
    operations: tuple[OperationSpec, ...] = ()
    function_calls: tuple[FunctionCallSpec, ...] = ()
    communications: tuple[CommunicationSpec, ...] = ()
    schedules: tuple[ScheduleSpec, ...] = ()
    transitions: tuple[BehaviorTransition, ...] = ()
    actions: tuple[BehaviorAction, ...] = ()
    concurrency: str = "sequential"
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BehaviorModel":
        known_keys = {
            "kind",
            "behaviorKind",
            "entryPoint",
            "entry_point",
            "initialState",
            "initial_state",
            "states",
            "parameters",
            "inputs",
            "variables",
            "locals",
            "results",
            "outputs",
            "operations",
            "functionCalls",
            "function_calls",
            "calls",
            "communications",
            "comms",
            "messages",
            "schedules",
            "cyclicSchedules",
            "transitions",
            "actions",
            "concurrency",
            "properties",
        }
        parameters = tuple(
            item if isinstance(item, ParameterSpec) else ParameterSpec.from_dict(_mapping(item))
            for item in value.get("parameters", value.get("inputs", ()))
            if isinstance(item, (ParameterSpec, Mapping))
        )
        variables = tuple(
            item if isinstance(item, VariableSpec) else VariableSpec.from_dict(_mapping(item))
            for item in value.get("variables", value.get("locals", ()))
            if isinstance(item, (VariableSpec, Mapping))
        )
        results = tuple(
            item if isinstance(item, ParameterSpec) else ParameterSpec.from_dict(_mapping(item))
            for item in value.get("results", value.get("outputs", ()))
            if isinstance(item, (ParameterSpec, Mapping))
        )
        operations = tuple(
            item if isinstance(item, OperationSpec) else OperationSpec.from_dict(_mapping(item))
            for item in value.get("operations", ())
            if isinstance(item, (OperationSpec, Mapping))
        )
        function_calls = tuple(
            item if isinstance(item, FunctionCallSpec) else FunctionCallSpec.from_dict(_mapping(item))
            for item in value.get(
                "functionCalls",
                value.get("function_calls", value.get("calls", ())),
            )
            if isinstance(item, (FunctionCallSpec, Mapping))
        )
        communications = tuple(
            item if isinstance(item, CommunicationSpec) else CommunicationSpec.from_dict(_mapping(item))
            for item in value.get(
                "communications",
                value.get("comms", value.get("messages", ())),
            )
            if isinstance(item, (CommunicationSpec, Mapping))
        )
        schedules = tuple(
            item if isinstance(item, ScheduleSpec) else ScheduleSpec.from_dict(_mapping(item))
            for item in value.get(
                "schedules",
                value.get("cyclicSchedules", ()),
            )
            if isinstance(item, (ScheduleSpec, Mapping))
        )
        transitions = tuple(
            item if isinstance(item, BehaviorTransition) else BehaviorTransition.from_dict(_mapping(item))
            for item in value.get("transitions", ())
            if isinstance(item, (BehaviorTransition, Mapping))
        )
        actions = tuple(
            item if isinstance(item, BehaviorAction) else BehaviorAction.from_dict(_mapping(item))
            for item in value.get("actions", ())
            if isinstance(item, (BehaviorAction, Mapping))
        )
        extra_properties = {
            key: item
            for key, item in value.items()
            if key not in known_keys
        }
        extra_properties.update(dict(_mapping(value.get("properties"))))
        return cls(
            kind=str(value.get("kind", value.get("behaviorKind", "state_machine"))),
            entry_point=str(value.get("entryPoint", value.get("entry_point", ""))),
            initial_state=str(value.get("initialState", value.get("initial_state", ""))),
            states=tuple(str(state) for state in value.get("states", ())),
            parameters=parameters,
            variables=variables,
            results=results,
            operations=operations,
            function_calls=function_calls,
            communications=communications,
            schedules=schedules,
            transitions=transitions,
            actions=actions,
            concurrency=str(value.get("concurrency", "sequential")),
            properties=extra_properties,
        )

    @classmethod
    def from_artifact(cls, artifact: "Artifact") -> "BehaviorModel":
        return cls.from_dict(artifact.properties)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "entryPoint": self.entry_point,
            "initialState": self.initial_state,
            "states": list(self.states),
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "variables": [variable.to_dict() for variable in self.variables],
            "results": [result.to_dict() for result in self.results],
            "operations": [operation.to_dict() for operation in self.operations],
            "functionCalls": [call.to_dict() for call in self.function_calls],
            "communications": [
                communication.to_dict()
                for communication in self.communications
            ],
            "schedules": [schedule.to_dict() for schedule in self.schedules],
            "transitions": [
                transition.to_dict()
                for transition in self.transitions
            ],
            "actions": [action.to_dict() for action in self.actions],
            "concurrency": self.concurrency,
            "properties": dict(self.properties),
        }

    def to_properties(self) -> dict[str, Any]:
        properties = dict(self.properties)
        properties.update(self.to_dict())
        properties.pop("properties", None)
        return properties


@dataclass(frozen=True)
class AllocationSpec:
    id: str
    source_ref: str
    target_ref: str
    kind: str = "allocation"
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AllocationSpec":
        return cls(
            id=str(value.get("id", "")),
            source_ref=str(value.get("sourceRef", value.get("source", ""))),
            target_ref=str(value.get("targetRef", value.get("target", ""))),
            kind=str(value.get("kind", "allocation")),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sourceRef": self.source_ref,
            "targetRef": self.target_ref,
            "kind": self.kind,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class DeploymentSpec:
    id: str
    component_ref: str
    target_ref: str
    environment: str = ""
    runtime: str = ""
    resources: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DeploymentSpec":
        return cls(
            id=str(value.get("id", "")),
            component_ref=str(value.get("componentRef", value.get("component", ""))),
            target_ref=str(value.get("targetRef", value.get("target", ""))),
            environment=str(value.get("environment", "")),
            runtime=str(value.get("runtime", "")),
            resources=dict(_mapping(value.get("resources"))),
            properties=dict(_mapping(value.get("properties"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "componentRef": self.component_ref,
            "targetRef": self.target_ref,
            "environment": self.environment,
            "runtime": self.runtime,
            "resources": dict(self.resources),
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class Artifact:
    id: str
    kind: ArtifactKind | str
    revision: int = 1
    properties: dict[str, Any] = field(default_factory=dict)
    supersedes: tuple[str, ...] = ()
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            digest = content_hash(
                {
                    "id": self.id,
                    "kind": kind_value(self.kind),
                    "revision": self.revision,
                    "properties": self.properties,
                    "supersedes": list(self.supersedes),
                }
            )
            object.__setattr__(self, "content_hash", digest)

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.revision}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": kind_value(self.kind),
            "revision": self.revision,
            "ref": self.ref,
            "properties": self.properties,
            "supersedes": list(self.supersedes),
            "contentHash": self.content_hash,
        }


@dataclass(frozen=True)
class TraceLink:
    kind: TraceKind | str
    source_id: str
    source_revision: int
    target_id: str
    target_revision: int
    status: str = "active"
    derived_by: str = ""

    @property
    def source_ref(self) -> str:
        return f"{self.source_id}@{self.source_revision}"

    @property
    def target_ref(self) -> str:
        return f"{self.target_id}@{self.target_revision}"

    @property
    def key(self) -> tuple[Any, ...]:
        return (
            trace_kind_value(self.kind),
            self.source_id,
            self.source_revision,
            self.target_id,
            self.target_revision,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": trace_kind_value(self.kind),
            "source": self.source_ref,
            "target": self.target_ref,
            "status": self.status,
            "derivedBy": self.derived_by,
        }


@dataclass(frozen=True)
class ImpactPlan:
    root: str
    impacted: tuple[str, ...]
    invalidatedEvidence: tuple[str, ...]
    invalidatedArtifacts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "impacted": list(self.impacted),
            "invalidatedEvidence": list(self.invalidatedEvidence),
            "invalidatedArtifacts": list(self.invalidatedArtifacts),
        }


@dataclass(frozen=True)
class Conflict:
    left: str
    right: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"left": self.left, "right": self.right, "reason": self.reason}


@dataclass(frozen=True)
class Reconciliation:
    status: str
    conflicts: tuple[Conflict, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


@dataclass(frozen=True)
class Baseline:
    id: str
    requirement_ref: str
    artifact_refs: tuple[str, ...]
    trace_keys: tuple[tuple[Any, ...], ...]
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "requirement": self.requirement_ref,
            "artifacts": list(self.artifact_refs),
            "traceKeys": [list(key) for key in self.trace_keys],
            "contentHash": self.content_hash,
        }


class ContinuityModel:
    """In-memory model repository with immutable, revisioned artifacts."""

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
        if "@" in artifact_ref:
            artifact_id, revision_text = artifact_ref.rsplit("@", 1)
            try:
                return self._artifacts[(artifact_id, int(revision_text))]
            except (KeyError, ValueError) as exc:
                raise KeyError(f"Unknown artifact revision: {artifact_ref}") from exc
        return self.latest(artifact_ref)

    def all_artifacts(self) -> tuple[Artifact, ...]:
        return tuple(sorted(self._artifacts.values(), key=lambda item: item.ref))

    def latest_artifacts(self) -> tuple[Artifact, ...]:
        return tuple(sorted(self._latest.values(), key=lambda item: item.id))

    def ensure_trace(
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
        return self._baselines[baseline_id]

    def baselines(self) -> tuple[Baseline, ...]:
        return tuple(sorted(self._baselines.values(), key=lambda item: item.id))
