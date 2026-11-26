"""Executable reference implementation of the SysML lifecycle operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol

from .model import (
    Artifact,
    ArtifactKind,
    AllocationSpec,
    Baseline,
    BehaviorModel,
    Conflict,
    ContinuityModel,
    ContinuityRepository,
    DeploymentSpec,
    ImpactPlan,
    InterfaceSpec,
    OperationSpec,
    ParameterSpec,
    PortSpec,
    Reconciliation,
    TraceKind,
    TraceLink,
    canonical_json,
    content_hash,
    kind_value,
    trace_kind_value,
)
from .relations import ContinuityRelations


def _slug(value: str) -> str:
    return "-".join(
        part
        for part in "".join(
            character if character.isalnum() else "-" for character in value.upper()
        ).split("-")
        if part
    )


@dataclass(frozen=True)
class LifecycleKinds:
    """Configurable names for lifecycle artifact roles."""

    stakeholder_need: ArtifactKind | str = ArtifactKind.STAKEHOLDER_NEED
    requirement: ArtifactKind | str = ArtifactKind.REQUIREMENT
    architectural_element: ArtifactKind | str = ArtifactKind.ARCHITECTURAL_ELEMENT
    interface: ArtifactKind | str = ArtifactKind.INTERFACE
    port: ArtifactKind | str = ArtifactKind.PORT
    connection: ArtifactKind | str = ArtifactKind.CONNECTION
    behavior_element: ArtifactKind | str = ArtifactKind.BEHAVIOR_ELEMENT
    implementation: ArtifactKind | str = ArtifactKind.IMPLEMENTATION
    allocation: ArtifactKind | str = ArtifactKind.ALLOCATION
    deployment: ArtifactKind | str = ArtifactKind.DEPLOYMENT
    component_test: ArtifactKind | str = ArtifactKind.COMPONENT_TEST
    scenario_test: ArtifactKind | str = ArtifactKind.SCENARIO_TEST
    verification_evidence: ArtifactKind | str = ArtifactKind.VERIFICATION_EVIDENCE
    verification_plan: ArtifactKind | str = ArtifactKind.VERIFICATION_PLAN


class IdentityPolicy(Protocol):
    def requirement_id(self, need: Artifact) -> str: ...

    def architecture_id(self, requirement: Artifact, element_name: str) -> str: ...

    def interface_id(self, requirement: Artifact, name: str) -> str: ...

    def port_id(self, interface: Artifact, name: str) -> str: ...

    def allocation_id(self, source: Artifact, target: Artifact) -> str: ...

    def deployment_id(self, component: Artifact, target: Artifact) -> str: ...

    def verification_plan_id(self, requirement: Artifact, behavior: Artifact) -> str: ...

    def component_test_id(
        self,
        requirement: Artifact,
        case: Mapping[str, object],
        index: int,
    ) -> str: ...

    def scenario_test_id(
        self,
        requirement: Artifact,
        scenario: Mapping[str, object],
        index: int,
    ) -> str: ...

    def baseline_id(self, requirement: Artifact, digest: str) -> str: ...


@dataclass(frozen=True)
class DefaultIdentityPolicy:
    """Stable, domain-neutral fallbacks. Callers may supply explicit IDs."""

    def requirement_id(self, need: Artifact) -> str:
        configured = need.properties.get("requirementId")
        return str(configured) if configured else need.id

    def architecture_id(self, requirement: Artifact, element_name: str) -> str:
        return f"{requirement.id}/{_slug(element_name)}"

    def interface_id(self, requirement: Artifact, name: str) -> str:
        return f"{requirement.id}/interface/{_slug(name)}"

    def port_id(self, interface: Artifact, name: str) -> str:
        return f"{interface.id}/port/{_slug(name)}"

    def allocation_id(self, source: Artifact, target: Artifact) -> str:
        return f"{source.id}/allocated-to/{target.id}"

    def deployment_id(self, component: Artifact, target: Artifact) -> str:
        return f"{component.id}/deployed-to/{target.id}"

    def verification_plan_id(self, requirement: Artifact, behavior: Artifact) -> str:
        return f"{requirement.id}/{behavior.id}/verification-plan"

    def component_test_id(
        self,
        requirement: Artifact,
        case: Mapping[str, object],
        index: int,
    ) -> str:
        return str(case.get("id", f"{requirement.id}/component-test-{index}"))

    def scenario_test_id(
        self,
        requirement: Artifact,
        scenario: Mapping[str, object],
        index: int,
    ) -> str:
        return str(scenario.get("id", f"{requirement.id}/scenario-test-{index}"))

    def baseline_id(self, requirement: Artifact, digest: str) -> str:
        return f"BL-{digest[:16]}"


class LifecycleEngine:
    def __init__(
        self,
        model: ContinuityRepository | None = None,
        *,
        identity_policy: IdentityPolicy | None = None,
        kinds: LifecycleKinds | None = None,
    ) -> None:
        self.model = model or ContinuityModel()
        self.relations = ContinuityRelations(self.model)
        self.identity_policy = identity_policy or DefaultIdentityPolicy()
        self.kinds = kinds or LifecycleKinds()

    def _execute_remote_operation(
        self,
        operation: str,
        arguments: Mapping[str, Any],
    ) -> tuple[bool, Any]:
        execute = getattr(self.model, "execute_operation", None)
        if not callable(execute):
            return False, None
        result = execute(operation, arguments)
        if isinstance(result, Mapping) and "result" in result:
            result = result["result"]
        return True, result

    def develop_intent(
        self,
        need: Artifact,
        requirement_id: str | None = None,
    ) -> Artifact:
        if kind_value(need.kind) != kind_value(self.kinds.stakeholder_need):
            raise TypeError("develop_intent requires the configured stakeholder need kind")
        handled, result = self._execute_remote_operation(
            "develop_intent",
            {
                "need": need.to_dict(),
                "requirementId": requirement_id,
            },
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote develop_intent returned an invalid artifact")
            return Artifact.from_dict(result)
        need = self.model.add_artifact(need)

        requirement_id = (
            requirement_id
            or self.identity_policy.requirement_id(need)
        )
        properties = {
            "statement": need.properties.get("statement", ""),
            "rationale": need.properties.get("rationale", ""),
            "acceptanceCriteria": need.properties.get("acceptanceCriteria", []),
            "sourceNeed": need.ref,
        }

        try:
            existing = self.model.latest(requirement_id)
        except KeyError:
            existing = None

        if existing is not None and existing.properties == properties:
            requirement = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            requirement = Artifact(
                id=requirement_id,
                kind=self.kinds.requirement,
                revision=revision,
                properties=properties,
                supersedes=supersedes,
            )
            requirement = self.model.add_artifact(requirement)

            if existing is not None:
                self.relations.supersedes(
                    existing,
                    requirement,
                    derived_by="develop_intent",
                )

        self.relations.origin(
            need,
            requirement,
            derived_by="develop_intent",
        )
        return requirement

    def realize_architecture(
        self,
        requirement: Artifact,
        element_names: Iterable[str | Mapping[str, object]],
        element_ids: Mapping[str, str] | None = None,
    ) -> tuple[Artifact, ...]:
        if kind_value(requirement.kind) != kind_value(self.kinds.requirement):
            raise TypeError("realize_architecture requires the configured requirement kind")
        element_specs = [
            dict(element) if isinstance(element, Mapping) else element
            for element in element_names
        ]
        element_names = tuple(element_specs)
        handled, result = self._execute_remote_operation(
            "realize_architecture",
            {
                "requirement": requirement.to_dict(),
                "elementNames": element_specs,
                "elementIds": dict(element_ids or {}),
            },
        )
        if handled:
            if not isinstance(result, list):
                raise TypeError("Remote realize_architecture returned invalid artifacts")
            return tuple(
                Artifact.from_dict(item)
                for item in result
                if isinstance(item, Mapping)
            )

        requirement = self.model.add_artifact(requirement)
        elements: list[Artifact] = []
        element_ids = element_ids or {}
        for element_spec in element_names:
            spec_properties: dict[str, object] = {}
            if isinstance(element_spec, Mapping):
                nested_properties = element_spec.get("properties", {})
                spec_properties = (
                    dict(nested_properties)
                    if isinstance(nested_properties, Mapping)
                    else {}
                )
                spec_properties.update(
                    {
                        key: value
                        for key, value in element_spec.items()
                        if key not in {"id", "elementId", "name", "properties"}
                    }
                )
                name = str(
                    element_spec.get(
                        "name",
                        element_spec.get("id", element_spec.get("elementId", "")),
                    )
                )
            else:
                name = element_spec
            element_id = (
                (
                    str(element_spec["id"])
                    if isinstance(element_spec, Mapping) and "id" in element_spec
                    else str(element_spec["elementId"])
                    if isinstance(element_spec, Mapping) and "elementId" in element_spec
                    else None
                )
                or element_ids.get(name)
                or self.identity_policy.architecture_id(requirement, name)
            )
            properties = {
                "name": name,
                "requirement": requirement.ref,
                **spec_properties,
            }
            try:
                existing = self.model.latest(element_id)
            except KeyError:
                existing = None

            if existing is not None and existing.properties == properties:
                element = existing
            else:
                revision = existing.revision + 1 if existing is not None else 1
                supersedes = (existing.ref,) if existing is not None else ()
                element = Artifact(
                    id=element_id,
                    kind=self.kinds.architectural_element,
                    revision=revision,
                    properties=properties,
                    supersedes=supersedes,
                )
                element = self.model.add_artifact(element)

                if existing is not None:
                    self.relations.supersedes(
                        existing,
                        element,
                        derived_by="realize_architecture",
                    )

            self.relations.realizes(
                requirement,
                element,
                derived_by="realize_architecture",
            )
            elements.append(element)
        return tuple(elements)

    def realize_behavior(
        self,
        requirement: Artifact,
        architecture: Iterable[Artifact],
        behavior_id: str,
        properties: Mapping[str, object] | BehaviorModel,
    ) -> Artifact:
        if kind_value(requirement.kind) != kind_value(self.kinds.requirement):
            raise TypeError("realize_behavior requires the configured requirement kind")
        architecture_payload = [element.to_dict() for element in architecture]
        properties_payload = (
            properties.to_properties()
            if isinstance(properties, BehaviorModel)
            else dict(properties)
        )
        handled, result = self._execute_remote_operation(
            "realize_behavior",
            {
                "requirement": requirement.to_dict(),
                "architecture": architecture_payload,
                "behaviorId": behavior_id,
                "properties": properties_payload,
            },
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote realize_behavior returned an invalid artifact")
            return Artifact.from_dict(result)
        requirement = self.model.add_artifact(requirement)
        architecture = tuple(self.model.add_artifact(element) for element in architecture)

        complete_properties = (
            properties.to_properties()
            if isinstance(properties, BehaviorModel)
            else dict(properties)
        )
        complete_properties["requirement"] = requirement.ref
        try:
            existing = self.model.latest(behavior_id)
        except KeyError:
            existing = None

        if existing is not None and existing.properties == complete_properties:
            behavior = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            behavior = Artifact(
                id=behavior_id,
                kind=self.kinds.behavior_element,
                revision=revision,
                properties=complete_properties,
                supersedes=supersedes,
            )
            behavior = self.model.add_artifact(behavior)

            if existing is not None:
                self.relations.supersedes(
                    existing,
                    behavior,
                    derived_by="realize_behavior",
                )

        for element in architecture:
            self.relations.supports(
                element,
                behavior,
                derived_by="realize_behavior",
            )
        return behavior

    def realize_interface(
        self,
        requirement: Artifact,
        architecture: Artifact,
        interface_id: str,
        interface: InterfaceSpec | Mapping[str, object] | str,
        *,
        properties: Mapping[str, object] | None = None,
    ) -> Artifact:
        if kind_value(requirement.kind) != kind_value(self.kinds.requirement):
            raise TypeError("realize_interface requires the configured requirement kind")
        interface_payload: Any
        if isinstance(interface, InterfaceSpec):
            interface_payload = interface.to_dict()
        elif isinstance(interface, Mapping):
            interface_payload = dict(interface)
        else:
            interface_payload = interface
        handled, result = self._execute_remote_operation(
            "realize_interface",
            {
                "requirement": requirement.to_dict(),
                "architecture": architecture.to_dict(),
                "interfaceId": interface_id,
                "interface": interface_payload,
                "properties": dict(properties or {}),
            },
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote realize_interface returned an invalid artifact")
            return Artifact.from_dict(result)
        requirement = self.model.add_artifact(requirement)
        architecture = self.model.add_artifact(architecture)
        if isinstance(interface, InterfaceSpec):
            spec = interface
        elif isinstance(interface, Mapping):
            spec = InterfaceSpec.from_dict(interface)
        else:
            spec = InterfaceSpec(id=interface_id, name=interface)

        complete_properties = spec.to_dict()
        complete_properties.update(properties or {})
        complete_properties["requirement"] = requirement.ref
        complete_properties["architecture"] = architecture.ref

        try:
            existing = self.model.latest(interface_id)
        except KeyError:
            existing = None
        if existing is not None and existing.properties == complete_properties:
            interface_artifact = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            interface_artifact = Artifact(
                id=interface_id,
                kind=self.kinds.interface,
                revision=revision,
                properties=complete_properties,
                supersedes=supersedes,
            )
            interface_artifact = self.model.add_artifact(interface_artifact)
            if existing is not None:
                self.relations.supersedes(
                    existing,
                    interface_artifact,
                    derived_by="realize_interface",
                )

        self.relations.realizes(
            requirement,
            interface_artifact,
            derived_by="realize_interface",
        )
        self.relations.exposes(
            architecture,
            interface_artifact,
            derived_by="realize_interface",
        )
        for port in spec.ports:
            policy_port_id = getattr(
                self.identity_policy,
                "port_id",
                lambda interface, name: f"{interface.id}/port/{_slug(name)}",
            )
            resolved_port_id = port.id or policy_port_id(interface_artifact, port.name)
            port_artifact = self.realize_port(
                interface_artifact,
                port,
                port_id=resolved_port_id,
            )
            self.relations.exposes(
                interface_artifact,
                port_artifact,
                derived_by="realize_interface",
            )
        return interface_artifact

    def realize_port(
        self,
        interface: Artifact,
        port: PortSpec | Mapping[str, object] | str,
        *,
        port_id: str | None = None,
    ) -> Artifact:
        port_payload: Any
        if isinstance(port, PortSpec):
            port_payload = port.to_dict()
        elif isinstance(port, Mapping):
            port_payload = dict(port)
        else:
            port_payload = port
        handled, result = self._execute_remote_operation(
            "realize_port",
            {
                "interface": interface.to_dict(),
                "port": port_payload,
                "portId": port_id,
            },
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote realize_port returned an invalid artifact")
            return Artifact.from_dict(result)
        interface = self.model.add_artifact(interface)
        if isinstance(port, PortSpec):
            spec = port
        elif isinstance(port, Mapping):
            spec = PortSpec.from_dict(port)
        else:
            spec = PortSpec(id=port_id or port, name=port)

        resolved_id = port_id or spec.id or spec.name
        complete_properties = spec.to_dict()
        complete_properties["interface"] = interface.ref

        try:
            existing = self.model.latest(resolved_id)
        except KeyError:
            existing = None
        if existing is not None and existing.properties == complete_properties:
            port_artifact = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            port_artifact = Artifact(
                id=resolved_id,
                kind=self.kinds.port,
                revision=revision,
                properties=complete_properties,
                supersedes=supersedes,
            )
            port_artifact = self.model.add_artifact(port_artifact)
            if existing is not None:
                self.relations.supersedes(
                    existing,
                    port_artifact,
                    derived_by="realize_port",
                )

        self.relations.exposes(
            interface,
            port_artifact,
            derived_by="realize_port",
        )
        return port_artifact

    def connect_ports(
        self,
        source_port: Artifact,
        target_port: Artifact,
        *,
        connection_id: str,
        properties: Mapping[str, object] | None = None,
    ) -> Artifact:
        handled, result = self._execute_remote_operation(
            "connect_ports",
            {
                "sourcePort": source_port.to_dict(),
                "targetPort": target_port.to_dict(),
                "connectionId": connection_id,
                "properties": dict(properties or {}),
            },
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote connect_ports returned an invalid artifact")
            return Artifact.from_dict(result)
        source_port = self.model.add_artifact(source_port)
        target_port = self.model.add_artifact(target_port)
        complete_properties = {
            "source": source_port.ref,
            "target": target_port.ref,
            **dict(properties or {}),
        }
        try:
            existing = self.model.latest(connection_id)
        except KeyError:
            existing = None
        if existing is not None and existing.properties == complete_properties:
            connection = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            connection = Artifact(
                id=connection_id,
                kind=self.kinds.connection,
                revision=revision,
                properties=complete_properties,
                supersedes=supersedes,
            )
            connection = self.model.add_artifact(connection)
            if existing is not None:
                self.relations.supersedes(
                    existing,
                    connection,
                    derived_by="connect_ports",
                )
        self.relations.connects(
            source_port,
            connection,
            derived_by="connect_ports",
        )
        self.relations.connects(
            connection,
            target_port,
            derived_by="connect_ports",
        )
        return connection

    def allocate_behavior(
        self,
        behavior: Artifact,
        target: Artifact,
        *,
        allocation_id: str | None = None,
        allocation: AllocationSpec | Mapping[str, object] | None = None,
        properties: Mapping[str, object] | None = None,
    ) -> Artifact:
        allocation_payload: Any
        if isinstance(allocation, AllocationSpec):
            allocation_payload = allocation.to_dict()
        elif isinstance(allocation, Mapping):
            allocation_payload = dict(allocation)
        else:
            allocation_payload = None
        handled, result = self._execute_remote_operation(
            "allocate_behavior",
            {
                "behavior": behavior.to_dict(),
                "target": target.to_dict(),
                "allocationId": allocation_id,
                "allocation": allocation_payload,
                "properties": dict(properties or {}),
            },
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote allocate_behavior returned an invalid artifact")
            return Artifact.from_dict(result)
        behavior = self.model.add_artifact(behavior)
        target = self.model.add_artifact(target)
        resolved_id = allocation_id
        if resolved_id is None:
            policy = getattr(
                self.identity_policy,
                "allocation_id",
                lambda source, target: f"{source.id}/allocated-to/{target.id}",
            )
            resolved_id = policy(behavior, target)
        if isinstance(allocation, AllocationSpec):
            spec = allocation
        elif isinstance(allocation, Mapping):
            spec = AllocationSpec.from_dict(allocation)
        else:
            spec = AllocationSpec(
                id=resolved_id,
                source_ref=behavior.ref,
                target_ref=target.ref,
            )
        complete_properties = spec.to_dict()
        complete_properties["sourceRef"] = behavior.ref
        complete_properties["targetRef"] = target.ref
        if properties:
            existing_properties = dict(complete_properties.get("properties", {}))
            existing_properties.update(dict(properties))
            complete_properties["properties"] = existing_properties

        try:
            existing = self.model.latest(resolved_id)
        except KeyError:
            existing = None
        if existing is not None and existing.properties == complete_properties:
            allocation_artifact = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            allocation_artifact = Artifact(
                id=resolved_id,
                kind=self.kinds.allocation,
                revision=revision,
                properties=complete_properties,
                supersedes=supersedes,
            )
            allocation_artifact = self.model.add_artifact(allocation_artifact)
            if existing is not None:
                self.relations.supersedes(
                    existing,
                    allocation_artifact,
                    derived_by="allocate_behavior",
                )
        self.relations.allocates(
            behavior,
            target,
            derived_by="allocate_behavior",
        )
        self.relations.allocates(
            allocation_artifact,
            target,
            derived_by="allocate_behavior",
        )
        return allocation_artifact

    def deploy_component(
        self,
        component: Artifact,
        target: Artifact,
        *,
        deployment_id: str | None = None,
        deployment: DeploymentSpec | Mapping[str, object] | None = None,
    ) -> Artifact:
        deployment_payload: Any
        if isinstance(deployment, DeploymentSpec):
            deployment_payload = deployment.to_dict()
        elif isinstance(deployment, Mapping):
            deployment_payload = dict(deployment)
        else:
            deployment_payload = None
        handled, result = self._execute_remote_operation(
            "deploy_component",
            {
                "component": component.to_dict(),
                "target": target.to_dict(),
                "deploymentId": deployment_id,
                "deployment": deployment_payload,
            },
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote deploy_component returned an invalid artifact")
            return Artifact.from_dict(result)
        component = self.model.add_artifact(component)
        target = self.model.add_artifact(target)
        resolved_id = deployment_id
        if resolved_id is None:
            policy = getattr(
                self.identity_policy,
                "deployment_id",
                lambda source, target: f"{source.id}/deployed-to/{target.id}",
            )
            resolved_id = policy(component, target)
        if isinstance(deployment, DeploymentSpec):
            spec = deployment
        elif isinstance(deployment, Mapping):
            spec = DeploymentSpec.from_dict(deployment)
        else:
            spec = DeploymentSpec(
                id=resolved_id,
                component_ref=component.ref,
                target_ref=target.ref,
            )
        complete_properties = spec.to_dict()
        complete_properties["componentRef"] = component.ref
        complete_properties["targetRef"] = target.ref

        try:
            existing = self.model.latest(resolved_id)
        except KeyError:
            existing = None
        if existing is not None and existing.properties == complete_properties:
            deployment_artifact = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            deployment_artifact = Artifact(
                id=resolved_id,
                kind=self.kinds.deployment,
                revision=revision,
                properties=complete_properties,
                supersedes=supersedes,
            )
            deployment_artifact = self.model.add_artifact(deployment_artifact)
            if existing is not None:
                self.relations.supersedes(
                    existing,
                    deployment_artifact,
                    derived_by="deploy_component",
                )
        self.relations.deployed_to(
            component,
            target,
            derived_by="deploy_component",
        )
        self.relations.deployed_to(
            deployment_artifact,
            target,
            derived_by="deploy_component",
        )
        return deployment_artifact

    def plan_verification(
        self,
        requirement: Artifact,
        behavior: Artifact,
        *,
        implementation: Artifact | None = None,
        plan_id: str | None = None,
        strategy: str = "",
        test_levels: Iterable[str] = (),
        environments: Iterable[str] = (),
        properties: Mapping[str, object] | None = None,
    ) -> Artifact:
        handled, result = self._execute_remote_operation(
            "plan_verification",
            {
                "requirement": requirement.to_dict(),
                "behavior": behavior.to_dict(),
                "implementation": (
                    implementation.to_dict()
                    if implementation is not None
                    else None
                ),
                "planId": plan_id,
                "strategy": strategy,
                "testLevels": list(test_levels),
                "environments": list(environments),
                "properties": dict(properties or {}),
            },
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote plan_verification returned an invalid artifact")
            return Artifact.from_dict(result)
        requirement = self.model.add_artifact(requirement)
        behavior = self.model.add_artifact(behavior)
        if implementation is not None:
            implementation = self.model.add_artifact(implementation)
        resolved_id = plan_id
        if resolved_id is None:
            policy = getattr(
                self.identity_policy,
                "verification_plan_id",
                lambda requirement, behavior: (
                    f"{requirement.id}/{behavior.id}/verification-plan"
                ),
            )
            resolved_id = policy(requirement, behavior)
        complete_properties = {
            "requirement": requirement.ref,
            "behavior": behavior.ref,
            "strategy": strategy,
            "testLevels": list(test_levels),
            "environments": list(environments),
            **dict(properties or {}),
        }
        if implementation is not None:
            complete_properties["implementation"] = implementation.ref

        try:
            existing = self.model.latest(resolved_id)
        except KeyError:
            existing = None
        if existing is not None and existing.properties == complete_properties:
            plan = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            plan = Artifact(
                id=resolved_id,
                kind=self.kinds.verification_plan,
                revision=revision,
                properties=complete_properties,
                supersedes=supersedes,
            )
            plan = self.model.add_artifact(plan)
            if existing is not None:
                self.relations.supersedes(
                    existing,
                    plan,
                    derived_by="plan_verification",
                )
        self.relations.covers(
            plan,
            requirement,
            derived_by="plan_verification",
        )
        self.relations.executes(
            plan,
            behavior,
            derived_by="plan_verification",
        )
        return plan

    def verify_satisfaction(
        self,
        requirement: Artifact,
        behavior: Artifact,
        *,
        evidence_id: str,
        result: str,
        summary: str,
        component_cases: Iterable[Mapping[str, object]],
        simulated_scenarios: Iterable[Mapping[str, object]],
        implementation: Artifact | None = None,
        verification_plan: Artifact | str | None = None,
        execution_environment: Mapping[str, object] | None = None,
    ) -> tuple[Artifact, tuple[Artifact, ...], tuple[Artifact, ...]]:
        component_cases = tuple(component_cases)
        simulated_scenarios = tuple(simulated_scenarios)
        if isinstance(verification_plan, Artifact):
            verification_plan_payload: Any = verification_plan.to_dict()
        else:
            verification_plan_payload = verification_plan
        handled, remote_result = self._execute_remote_operation(
            "verify_satisfaction",
            {
                "requirement": requirement.to_dict(),
                "behavior": behavior.to_dict(),
                "evidenceId": evidence_id,
                "result": result,
                "summary": summary,
                "componentCases": [dict(case) for case in component_cases],
                "simulatedScenarios": [dict(case) for case in simulated_scenarios],
                "implementation": (
                    implementation.to_dict()
                    if implementation is not None
                    else None
                ),
                "verificationPlan": verification_plan_payload,
                "executionEnvironment": dict(execution_environment or {}),
            },
        )
        if handled:
            if not isinstance(remote_result, Mapping):
                raise TypeError("Remote verify_satisfaction returned an invalid result")
            evidence_value = remote_result.get("evidence")
            component_value = remote_result.get("componentTests")
            scenario_value = remote_result.get("scenarioTests")
            if not isinstance(evidence_value, Mapping):
                raise TypeError("Remote verify_satisfaction omitted evidence")
            if not isinstance(component_value, list) or not isinstance(scenario_value, list):
                raise TypeError("Remote verify_satisfaction returned invalid test lists")
            return (
                Artifact.from_dict(evidence_value),
                tuple(
                    Artifact.from_dict(item)
                    for item in component_value
                    if isinstance(item, Mapping)
                ),
                tuple(
                    Artifact.from_dict(item)
                    for item in scenario_value
                    if isinstance(item, Mapping)
                ),
            )
        if kind_value(requirement.kind) != kind_value(self.kinds.requirement):
            raise TypeError("verify_satisfaction requires the configured requirement kind")
        if kind_value(behavior.kind) != kind_value(self.kinds.behavior_element):
            raise TypeError("verify_satisfaction requires the configured behavior kind")
        requirement = self.model.add_artifact(requirement)
        behavior = self.model.add_artifact(behavior)
        if implementation is not None:
            implementation = self.model.add_artifact(implementation)

        component_artifacts: list[Artifact] = []
        for index, case in enumerate(component_cases, start=1):
            case_id = self.identity_policy.component_test_id(
                requirement,
                case,
                index,
            )
            properties = dict(case)
            properties["requirement"] = requirement.ref
            properties["behavior"] = behavior.ref
            if implementation is not None:
                properties["implementation"] = implementation.ref

            try:
                existing = self.model.latest(case_id)
            except KeyError:
                existing = None
            if existing is not None and existing.properties == properties:
                test = existing
            else:
                revision = existing.revision + 1 if existing is not None else 1
                supersedes = (existing.ref,) if existing is not None else ()
                test = Artifact(
                    id=case_id,
                    kind=self.kinds.component_test,
                    revision=revision,
                    properties=properties,
                    supersedes=supersedes,
                )
                test = self.model.add_artifact(test)
                if existing is not None:
                    self.relations.supersedes(
                        existing,
                        test,
                        derived_by="verify_satisfaction",
                    )

            self.relations.covers(
                test,
                requirement,
                derived_by="verify_satisfaction",
            )
            self.relations.executes(
                test,
                behavior,
                derived_by="verify_satisfaction",
            )
            if implementation is not None:
                self.relations.executes(
                    test,
                    implementation,
                    derived_by="verify_satisfaction",
                )
            component_artifacts.append(test)

        scenario_artifacts: list[Artifact] = []
        for index, scenario in enumerate(simulated_scenarios, start=1):
            scenario_id = self.identity_policy.scenario_test_id(
                requirement,
                scenario,
                index,
            )
            properties = dict(scenario)
            properties["requirement"] = requirement.ref
            properties["behavior"] = behavior.ref
            if implementation is not None:
                properties["implementation"] = implementation.ref

            try:
                existing = self.model.latest(scenario_id)
            except KeyError:
                existing = None
            if existing is not None and existing.properties == properties:
                test = existing
            else:
                revision = existing.revision + 1 if existing is not None else 1
                supersedes = (existing.ref,) if existing is not None else ()
                test = Artifact(
                    id=scenario_id,
                    kind=self.kinds.scenario_test,
                    revision=revision,
                    properties=properties,
                    supersedes=supersedes,
                )
                test = self.model.add_artifact(test)
                if existing is not None:
                    self.relations.supersedes(
                        existing,
                        test,
                        derived_by="verify_satisfaction",
                    )

            self.relations.covers(
                test,
                requirement,
                derived_by="verify_satisfaction",
            )
            self.relations.executes(
                test,
                behavior,
                derived_by="verify_satisfaction",
            )
            if implementation is not None:
                self.relations.executes(
                    test,
                    implementation,
                    derived_by="verify_satisfaction",
                )
            scenario_artifacts.append(test)

        evidence_properties = {
            "result": result,
            "summary": summary,
            "requirement": requirement.ref,
            "behavior": behavior.ref,
            "componentTests": [test.ref for test in component_artifacts],
            "scenarioTests": [test.ref for test in scenario_artifacts],
        }
        if implementation is not None:
            evidence_properties["implementation"] = implementation.ref
        if verification_plan is not None:
            evidence_properties["verificationPlan"] = verification_plan.ref
        if execution_environment is not None:
            evidence_properties["executionEnvironment"] = dict(execution_environment)

        try:
            existing = self.model.latest(evidence_id)
        except KeyError:
            existing = None
        if existing is not None and existing.properties == evidence_properties:
            evidence = existing
        else:
            revision = existing.revision + 1 if existing is not None else 1
            supersedes = (existing.ref,) if existing is not None else ()
            evidence = Artifact(
                id=evidence_id,
                kind=self.kinds.verification_evidence,
                revision=revision,
                properties=evidence_properties,
                supersedes=supersedes,
            )
            evidence = self.model.add_artifact(evidence)
            if existing is not None:
                self.relations.supersedes(
                    existing,
                    evidence,
                    derived_by="verify_satisfaction",
                )

        self.relations.verifies(
            behavior,
            evidence,
            derived_by="verify_satisfaction",
        )
        if verification_plan is not None:
            self.relations.verifies(
                verification_plan,
                evidence,
                derived_by="verify_satisfaction",
            )
        return evidence, tuple(component_artifacts), tuple(scenario_artifacts)

    def propagate_change(self, root: Artifact) -> ImpactPlan:
        handled, result = self._execute_remote_operation(
            "propagate_change",
            {"root": root.to_dict()},
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote propagate_change returned an invalid impact plan")
            return ImpactPlan(
                root=str(result["root"]),
                impacted=tuple(str(ref) for ref in result.get("impacted", ())),
                invalidatedEvidence=tuple(
                    str(ref)
                    for ref in result.get("invalidatedEvidence", ())
                ),
                invalidatedArtifacts=tuple(
                    str(ref)
                    for ref in result.get("invalidatedArtifacts", ())
                ),
            )
        root = self.model.add_artifact(root)
        visited: set[str] = {root.ref}
        queue: list[str] = [root.ref]

        while queue:
            current = queue.pop(0)
            for link in self.model.active_traces():
                neighbor: str | None = None
                if link.source_ref == current:
                    neighbor = link.target_ref
                elif link.target_ref == current:
                    neighbor = link.source_ref
                if neighbor is not None and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        impacted: list[str] = []
        invalidated: list[str] = []
        invalidated_artifacts: list[str] = []
        for artifact_ref in sorted(visited):
            if artifact_ref == root.ref:
                continue
            try:
                artifact = self.model.get(artifact_ref)
            except KeyError:
                continue
            impacted.append(artifact_ref)
            artifact_kind = kind_value(artifact.kind)
            if artifact_kind in {
                kind_value(self.kinds.behavior_element),
                kind_value(self.kinds.interface),
                kind_value(self.kinds.port),
                kind_value(self.kinds.implementation),
                kind_value(self.kinds.allocation),
                kind_value(self.kinds.deployment),
                kind_value(self.kinds.verification_plan),
            }:
                invalidated_artifacts.append(artifact_ref)
            if kind_value(artifact.kind) == kind_value(
                self.kinds.verification_evidence
            ):
                checked_requirement = artifact.properties.get("requirement")
                if checked_requirement and checked_requirement != root.ref:
                    invalidated.append(artifact_ref)
                    invalidated_artifacts.append(artifact_ref)

        return ImpactPlan(
            root=root.ref,
            impacted=tuple(impacted),
            invalidatedEvidence=tuple(invalidated),
            invalidatedArtifacts=tuple(sorted(set(invalidated_artifacts))),
        )

    def reconcile_views(
        self,
        left: Artifact | str,
        right: Artifact | str,
    ) -> Reconciliation:
        left_payload = left.to_dict() if isinstance(left, Artifact) else left
        right_payload = right.to_dict() if isinstance(right, Artifact) else right
        handled, result = self._execute_remote_operation(
            "reconcile_views",
            {
                "left": left_payload,
                "right": right_payload,
            },
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote reconcile_views returned an invalid reconciliation")
            conflicts_value = result.get("conflicts", ())
            conflicts = tuple(
                Conflict(
                    left=str(conflict["left"]),
                    right=str(conflict["right"]),
                    reason=str(conflict["reason"]),
                )
                for conflict in conflicts_value
                if isinstance(conflict, Mapping)
            )
            return Reconciliation(
                status=str(result["status"]),
                conflicts=conflicts,
            )
        left_artifact = left if isinstance(left, Artifact) else self.model.get(left)
        right_artifact = right if isinstance(right, Artifact) else self.model.get(right)

        conflicts: list[Conflict] = []
        if left_artifact.id != right_artifact.id:
            conflicts.append(
                Conflict(
                    left=left_artifact.ref,
                    right=right_artifact.ref,
                    reason="different stable identities",
                )
            )
        elif kind_value(left_artifact.kind) != kind_value(right_artifact.kind):
            conflicts.append(
                Conflict(
                    left=left_artifact.ref,
                    right=right_artifact.ref,
                    reason="different artifact kinds",
                )
            )
        elif left_artifact.properties != right_artifact.properties:
            conflicts.append(
                Conflict(
                    left=left_artifact.ref,
                    right=right_artifact.ref,
                    reason="different semantic properties",
                )
            )

        if conflicts:
            return Reconciliation(status="conflict", conflicts=tuple(conflicts))
        return Reconciliation(status="consistent")

    def baseline_thread(self, requirement: Artifact) -> Baseline:
        handled, result = self._execute_remote_operation(
            "baseline_thread",
            {"requirement": requirement.to_dict()},
        )
        if handled:
            if not isinstance(result, Mapping):
                raise TypeError("Remote baseline_thread returned an invalid baseline")
            return Baseline.from_dict(result)
        requirement = self.model.add_artifact(requirement)
        visited: set[str] = {requirement.ref}
        queue: list[str] = [requirement.ref]

        while queue:
            current = queue.pop(0)
            for link in self.model.active_traces():
                neighbor: str | None = None
                if link.source_ref == current:
                    neighbor = link.target_ref
                elif link.target_ref == current:
                    neighbor = link.source_ref
                if neighbor is not None and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        artifact_refs = tuple(sorted(visited))
        active_links = tuple(
            sorted(
                (
                    link.key
                    for link in self.model.active_traces()
                    if link.source_ref in visited and link.target_ref in visited
                ),
                key=lambda key: canonical_json(list(key)),
            )
        )
        digest = content_hash(
            {
                "requirement": requirement.ref,
                "artifacts": list(artifact_refs),
                "traces": [list(key) for key in active_links],
            }
        )
        baseline_id = self.identity_policy.baseline_id(requirement, digest)
        baseline = Baseline(
            id=baseline_id,
            requirement_ref=requirement.ref,
            artifact_refs=artifact_refs,
            trace_keys=active_links,
            content_hash=digest,
        )
        return self.model.add_baseline(baseline)

    def check_continuity(
        self,
        requirement: Artifact,
        *,
        strict: bool = False,
    ) -> tuple[str, ...]:
        handled, result = self._execute_remote_operation(
            "check_continuity",
            {
                "requirement": requirement.to_dict(),
                "strict": strict,
            },
        )
        if handled:
            if not isinstance(result, list):
                raise TypeError("Remote check_continuity returned invalid diagnostics")
            return tuple(str(diagnostic) for diagnostic in result)
        requirement = self.model.add_artifact(requirement)
        traces = self.model.active_traces()
        diagnostics: list[str] = []

        architecture = [
            link.target_id
            for link in traces
            if trace_kind_value(link.kind) == "realizes"
            and link.source_id == requirement.id
            and link.source_revision == requirement.revision
        ]
        if not architecture:
            diagnostics.append(
                f"requirement {requirement.ref} has no architectural realization"
            )

        behavior_refs = [
            link.target_ref
            for link in traces
            if trace_kind_value(link.kind) == "supports"
            and link.source_id in architecture
        ]
        if not behavior_refs:
            diagnostics.append(
                f"requirement {requirement.ref} has no behavioral realization"
            )

        component_tests = [
            link.source_id
            for link in traces
            if trace_kind_value(link.kind) == "covers"
            and link.target_id == requirement.id
            and link.target_revision == requirement.revision
        ]
        scenario_tests = [
            artifact.id
            for artifact in self.model.latest_artifacts()
            if kind_value(artifact.kind)
            == kind_value(self.kinds.scenario_test)
            and artifact.properties.get("requirement") == requirement.ref
        ]
        if not component_tests:
            diagnostics.append(
                f"requirement {requirement.ref} has no component-level test coverage"
            )
        if not scenario_tests:
            diagnostics.append(
                f"requirement {requirement.ref} has no simulated scenario coverage"
            )

        passed_evidence = [
            artifact
            for artifact in self.model.latest_artifacts()
            if kind_value(artifact.kind)
            == kind_value(self.kinds.verification_evidence)
            and artifact.properties.get("requirement") == requirement.ref
            and artifact.properties.get("result") == "pass"
        ]
        if not passed_evidence:
            diagnostics.append(
                f"requirement {requirement.ref} has no passing verification evidence"
            )

        if strict:
            implementations = [
                link.target_ref
                for link in traces
                if trace_kind_value(link.kind) == "generates"
                and link.source_ref in behavior_refs
            ]
            if not implementations:
                diagnostics.append(
                    f"requirement {requirement.ref} has no generated implementation"
                )

            plans = [
                artifact.ref
                for artifact in self.model.latest_artifacts()
                if kind_value(artifact.kind)
                == kind_value(self.kinds.verification_plan)
                and artifact.properties.get("requirement") == requirement.ref
            ]
            if not plans:
                diagnostics.append(
                    f"requirement {requirement.ref} has no verification plan"
                )

            for behavior_ref in behavior_refs:
                try:
                    behavior = self.model.get(behavior_ref)
                except KeyError:
                    continue
                model = BehaviorModel.from_artifact(behavior)
                if not model.entry_point and not model.states and not model.actions:
                    diagnostics.append(
                        f"behavior {behavior.ref} has no executable entry point or actions"
                    )
                for call in model.function_calls:
                    if not call.function_name:
                        diagnostics.append(
                            f"behavior {behavior.ref} has a function call with no function name"
                        )
                for communication in model.communications:
                    if not communication.channel and not communication.endpoint:
                        diagnostics.append(
                            f"behavior {behavior.ref} communication "
                            f"{communication.id} has no channel or endpoint"
                        )
                for schedule in model.schedules:
                    if schedule.kind in ("cyclic", "periodic") and schedule.period_ms is None:
                        diagnostics.append(
                            f"behavior {behavior.ref} schedule "
                            f"{schedule.id} has no period"
                        )

                allocations = [
                    link
                    for link in traces
                    if trace_kind_value(link.kind) == "allocates"
                    and link.source_ref == behavior.ref
                ]
                if not allocations:
                    diagnostics.append(
                        f"behavior {behavior.ref} has no architectural allocation"
                    )

                deployments = [
                    link
                    for link in traces
                    if trace_kind_value(link.kind) == "deployed_to"
                    and link.source_ref == behavior.ref
                ]
                if not deployments:
                    diagnostics.append(
                        f"behavior {behavior.ref} has no deployment target"
                    )

        return tuple(diagnostics)
