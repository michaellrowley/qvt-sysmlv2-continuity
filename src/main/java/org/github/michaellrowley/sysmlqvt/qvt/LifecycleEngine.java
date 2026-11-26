package org.github.michaellrowley.sysmlqvt.qvt;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.Baseline;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;
import org.github.michaellrowley.sysmlqvt.model.TraceKind;
import org.github.michaellrowley.sysmlqvt.model.TraceLink;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;

public final class LifecycleEngine {
    public record ImpactPlan(
        String root,
        List<String> impacted,
        List<String> invalidatedEvidence,
        List<String> invalidatedArtifacts
    ) {
    }

    public record Conflict(String left, String right, String reason) {
    }

    public record Reconciliation(String status, List<Conflict> conflicts) {
    }

    private final SysMLModel model;
    private final ContinuityRelations relations;

    public LifecycleEngine(SysMLModel model) {
        this.model = model;
        this.relations = new ContinuityRelations();
    }

    public Artifact markSuperseded(Artifact oldElement, Artifact newElement) {
        return model.addArtifact(new Artifact(
            newElement.id(),
            newElement.kind(),
            newElement.revision(),
            newElement.properties(),
            mergeSupersedes(newElement.supersedes(), oldElement.ref())
        ));
    }

    public Artifact developIntent(Artifact need, String requirementId) {
        String resolvedId = requirementId;
        if (resolvedId == null || resolvedId.isBlank()) {
            Object configured = need.properties().get("requirementId");
            resolvedId = configured == null ? need.id() : String.valueOf(configured);
        }

        Map<String, Object> properties = new LinkedHashMap<>();
        properties.put("statement", need.properties().getOrDefault("statement", ""));
        properties.put("rationale", need.properties().getOrDefault("rationale", ""));
        properties.put(
            "acceptanceCriteria",
            need.properties().getOrDefault("acceptanceCriteria", List.of())
        );
        properties.put("sourceNeed", need.ref());

        Artifact requirement = ensureArtifact(
            resolvedId,
            ArtifactKind.REQUIREMENT,
            properties,
            "develop_intent"
        );
        model.addTrace(new TraceLink(
            TraceKind.ORIGIN,
            need.ref(),
            requirement.ref(),
            "active",
            "develop_intent"
        ));
        return requirement;
    }

    public List<Artifact> realizeArchitecture(
        Artifact requirement,
        List<?> elementSpecs,
        Map<String, String> elementIds
    ) {
        List<Artifact> elements = new ArrayList<>();
        for (Object value : elementSpecs) {
            Map<String, Object> specProperties = new LinkedHashMap<>();
            String name;
            String id = null;

            if (value instanceof Map<?, ?> spec) {
                Object nested = spec.get("properties");
                if (nested instanceof Map<?, ?> nestedProperties) {
                    nestedProperties.forEach(
                        (key, item) -> specProperties.put(String.valueOf(key), item)
                    );
                }
                spec.forEach((key, item) -> {
                    String keyText = String.valueOf(key);
                    if (!List.of("id", "elementId", "name", "properties").contains(keyText)) {
                        specProperties.put(keyText, item);
                    }
                });
                Object nameValue = spec.containsKey("name")
                    ? spec.get("name")
                    : spec.containsKey("id")
                        ? spec.get("id")
                        : spec.get("elementId");
                name = nameValue == null ? "" : String.valueOf(nameValue);
                if (spec.containsKey("id")) {
                    id = String.valueOf(spec.get("id"));
                } else if (spec.containsKey("elementId")) {
                    id = String.valueOf(spec.get("elementId"));
                }
            } else {
                name = String.valueOf(value);
            }

            if (id == null && elementIds != null) {
                id = elementIds.get(name);
            }
            if (id == null || id.isBlank()) {
                id = requirement.id() + "/" + slug(name);
            }

            Map<String, Object> properties = new LinkedHashMap<>();
            properties.put("name", name);
            properties.put("requirement", requirement.ref());
            properties.putAll(specProperties);

            Artifact element = ensureArtifact(
                id,
                ArtifactKind.ARCHITECTURAL_ELEMENT,
                properties,
                "realize_architecture"
            );
            model.addTrace(new TraceLink(
                TraceKind.REALIZES,
                requirement.ref(),
                element.ref(),
                "active",
                "realize_architecture"
            ));
            elements.add(element);
        }
        return elements;
    }

    public Artifact realizeInterface(
        Artifact requirement,
        Artifact architecture,
        String interfaceId,
        Map<String, Object> interfaceSpec
    ) {
        Map<String, Object> properties = new LinkedHashMap<>(interfaceSpec);
        properties.put("requirement", requirement.ref());
        properties.put("architecture", architecture.ref());

        Artifact interfaceArtifact = ensureArtifact(
            interfaceId,
            ArtifactKind.INTERFACE,
            properties,
            "realize_interface"
        );
        model.addTrace(new TraceLink(
            TraceKind.REALIZES,
            requirement.ref(),
            interfaceArtifact.ref(),
            "active",
            "realize_interface"
        ));
        model.addTrace(new TraceLink(
            TraceKind.EXPOSES,
            architecture.ref(),
            interfaceArtifact.ref(),
            "active",
            "realize_interface"
        ));
        return interfaceArtifact;
    }

    public Artifact realizePort(
        Artifact interfaceArtifact,
        Map<String, Object> portSpec,
        String portId
    ) {
        String resolvedId = portId;
        if (resolvedId == null || resolvedId.isBlank()) {
            Object id = portSpec.get("id");
            resolvedId = id == null ? String.valueOf(portSpec.getOrDefault("name", "")) : String.valueOf(id);
        }
        Map<String, Object> properties = new LinkedHashMap<>(portSpec);
        properties.put("interface", interfaceArtifact.ref());

        Artifact port = ensureArtifact(
            resolvedId,
            ArtifactKind.PORT,
            properties,
            "realize_port"
        );
        model.addTrace(new TraceLink(
            TraceKind.EXPOSES,
            interfaceArtifact.ref(),
            port.ref(),
            "active",
            "realize_port"
        ));
        return port;
    }

    public Artifact connectPorts(
        Artifact source,
        Artifact target,
        String connectionId,
        Map<String, Object> connectionSpec
    ) {
        Map<String, Object> properties = new LinkedHashMap<>(connectionSpec);
        properties.put("source", source.ref());
        properties.put("target", target.ref());

        Artifact connection = ensureArtifact(
            connectionId,
            ArtifactKind.CONNECTION,
            properties,
            "connect_ports"
        );
        model.addTrace(new TraceLink(
            TraceKind.CONNECTS,
            source.ref(),
            connection.ref(),
            "active",
            "connect_ports"
        ));
        model.addTrace(new TraceLink(
            TraceKind.CONNECTS,
            connection.ref(),
            target.ref(),
            "active",
            "connect_ports"
        ));
        return connection;
    }

    public Artifact realizeBehavior(
        Artifact requirement,
        List<Artifact> architecture,
        String behaviorId,
        Map<String, Object> properties
    ) {
        Map<String, Object> complete = new LinkedHashMap<>(properties);
        complete.put("requirement", requirement.ref());

        Artifact behavior = ensureArtifact(
            behaviorId,
            ArtifactKind.BEHAVIOR_ELEMENT,
            complete,
            "realize_behavior"
        );
        for (Artifact element : architecture) {
            model.addTrace(new TraceLink(
                TraceKind.SUPPORTS,
                element.ref(),
                behavior.ref(),
                "active",
                "realize_behavior"
            ));
        }
        return behavior;
    }

    public Artifact configureFunctionCall(
        Artifact behavior,
        Map<String, Object> spec
    ) {
        String id = String.valueOf(spec.getOrDefault("id", behavior.id() + "/call"));
        Map<String, Object> properties = new LinkedHashMap<>(spec);
        properties.put("behavior", behavior.ref());

        Artifact call = ensureArtifact(
            id,
            ArtifactKind.FUNCTION_CALL,
            properties,
            "configure_function_call"
        );
        model.addTrace(new TraceLink(
            TraceKind.CALLS,
            behavior.ref(),
            call.ref(),
            "active",
            "configure_function_call"
        ));
        return call;
    }

    public Artifact configureCommunication(
        Artifact behavior,
        Map<String, Object> spec
    ) {
        String id = String.valueOf(spec.getOrDefault("id", behavior.id() + "/communication"));
        Map<String, Object> properties = new LinkedHashMap<>(spec);
        properties.put("behavior", behavior.ref());

        Artifact communication = ensureArtifact(
            id,
            ArtifactKind.COMMUNICATION,
            properties,
            "configure_communication"
        );
        String direction = String.valueOf(spec.getOrDefault("direction", ""));
        TraceKind traceKind = "in".equalsIgnoreCase(direction)
            ? TraceKind.SUBSCRIBES
            : "out".equalsIgnoreCase(direction)
                ? TraceKind.PUBLISHES
                : TraceKind.CONNECTS;
        model.addTrace(new TraceLink(
            traceKind,
            behavior.ref(),
            communication.ref(),
            "active",
            "configure_communication"
        ));
        return communication;
    }

    public Artifact configureSchedule(
        Artifact behavior,
        Map<String, Object> spec
    ) {
        String id = String.valueOf(spec.getOrDefault("id", behavior.id() + "/schedule"));
        Map<String, Object> properties = new LinkedHashMap<>(spec);
        properties.put("behavior", behavior.ref());

        Artifact schedule = ensureArtifact(
            id,
            ArtifactKind.SCHEDULE,
            properties,
            "configure_schedule"
        );
        model.addTrace(new TraceLink(
            TraceKind.SCHEDULES,
            behavior.ref(),
            schedule.ref(),
            "active",
            "configure_schedule"
        ));
        return schedule;
    }

    public Artifact allocateBehavior(
        Artifact behavior,
        Artifact target,
        String allocationId,
        Map<String, Object> allocationSpec
    ) {
        String resolvedId = allocationId;
        if (resolvedId == null || resolvedId.isBlank()) {
            resolvedId = behavior.id() + "/allocated-to/" + target.id();
        }
        Map<String, Object> properties = new LinkedHashMap<>(allocationSpec);
        properties.put("sourceRef", behavior.ref());
        properties.put("targetRef", target.ref());

        Artifact allocation = ensureArtifact(
            resolvedId,
            ArtifactKind.ALLOCATION,
            properties,
            "allocate_behavior"
        );
        model.addTrace(new TraceLink(
            TraceKind.ALLOCATES,
            behavior.ref(),
            target.ref(),
            "active",
            "allocate_behavior"
        ));
        model.addTrace(new TraceLink(
            TraceKind.ALLOCATES,
            allocation.ref(),
            target.ref(),
            "active",
            "allocate_behavior"
        ));
        return allocation;
    }

    public Artifact deployComponent(
        Artifact component,
        Artifact target,
        String deploymentId,
        Map<String, Object> deploymentSpec
    ) {
        String resolvedId = deploymentId;
        if (resolvedId == null || resolvedId.isBlank()) {
            resolvedId = component.id() + "/deployed-to/" + target.id();
        }
        Map<String, Object> properties = new LinkedHashMap<>(deploymentSpec);
        properties.put("componentRef", component.ref());
        properties.put("targetRef", target.ref());

        Artifact deployment = ensureArtifact(
            resolvedId,
            ArtifactKind.DEPLOYMENT,
            properties,
            "deploy_component"
        );
        model.addTrace(new TraceLink(
            TraceKind.DEPLOYED_TO,
            component.ref(),
            target.ref(),
            "active",
            "deploy_component"
        ));
        model.addTrace(new TraceLink(
            TraceKind.DEPLOYED_TO,
            deployment.ref(),
            target.ref(),
            "active",
            "deploy_component"
        ));
        return deployment;
    }

    public Artifact generateImplementation(
        Artifact behavior,
        String implementationId,
        Map<String, Object> codeGeneration
    ) {
        Map<String, Object> properties = new LinkedHashMap<>();
        properties.put("sourceBehavior", behavior.ref());
        properties.put("sourceHash", behavior.contentHash());
        properties.put("language", codeGeneration.getOrDefault("targetLanguage", ""));
        properties.put("targetPlatform", codeGeneration.getOrDefault("targetPlatform", ""));
        properties.put("entryPoint", codeGeneration.getOrDefault("entryPoint", ""));
        properties.put("buildSystem", codeGeneration.getOrDefault("buildSystem", ""));
        properties.put("sourceFormat", codeGeneration.getOrDefault("sourceFormat", ""));
        properties.put("behaviorModel", behavior.properties());
        properties.put("codeGeneration", codeGeneration);

        Artifact implementation = ensureArtifact(
            implementationId,
            ArtifactKind.IMPLEMENTATION,
            properties,
            "generate_implementation"
        );
        model.addTrace(new TraceLink(
            TraceKind.GENERATES,
            behavior.ref(),
            implementation.ref(),
            "active",
            "generate_implementation"
        ));
        model.addTrace(new TraceLink(
            TraceKind.IMPLEMENTS,
            implementation.ref(),
            behavior.ref(),
            "active",
            "generate_implementation"
        ));
        return implementation;
    }

    public Artifact planVerification(
        Artifact requirement,
        Artifact behavior,
        Artifact implementation,
        String planId,
        Map<String, Object> planSpec
    ) {
        Map<String, Object> properties = new LinkedHashMap<>(planSpec);
        properties.put("requirement", requirement.ref());
        properties.put("behavior", behavior.ref());
        if (implementation != null) {
            properties.put("implementation", implementation.ref());
        }

        Artifact plan = ensureArtifact(
            planId,
            ArtifactKind.VERIFICATION_PLAN,
            properties,
            "plan_verification"
        );
        model.addTrace(new TraceLink(
            TraceKind.COVERS,
            plan.ref(),
            requirement.ref(),
            "active",
            "plan_verification"
        ));
        model.addTrace(new TraceLink(
            TraceKind.EXECUTES,
            plan.ref(),
            behavior.ref(),
            "active",
            "plan_verification"
        ));
        return plan;
    }

    public Artifact verifySatisfaction(
        Artifact requirement,
        Artifact behavior,
        Artifact implementation,
        Artifact plan,
        String evidenceId,
        String result,
        String summary,
        List<Map<String, Object>> componentCases,
        List<Map<String, Object>> simulatedScenarios,
        Map<String, Object> executionEnvironment
    ) {
        for (Map<String, Object> caseSpec : componentCases) {
            configureTest(
                ArtifactKind.COMPONENT_TEST,
                requirement,
                behavior,
                implementation,
                caseSpec
            );
        }
        for (Map<String, Object> scenarioSpec : simulatedScenarios) {
            configureTest(
                ArtifactKind.SCENARIO_TEST,
                requirement,
                behavior,
                implementation,
                scenarioSpec
            );
        }

        Map<String, Object> evidenceProperties = new LinkedHashMap<>();
        evidenceProperties.put("result", result);
        evidenceProperties.put("summary", summary);
        evidenceProperties.put("requirement", requirement.ref());
        evidenceProperties.put("behavior", behavior.ref());
        if (implementation != null) {
            evidenceProperties.put("implementation", implementation.ref());
        }
        if (plan != null) {
            evidenceProperties.put("verificationPlan", plan.ref());
        }
        evidenceProperties.put("executionEnvironment", executionEnvironment);

        Artifact evidence = ensureArtifact(
            evidenceId,
            ArtifactKind.VERIFICATION_EVIDENCE,
            evidenceProperties,
            "verify_satisfaction"
        );
        model.addTrace(new TraceLink(
            TraceKind.VERIFIES,
            behavior.ref(),
            evidence.ref(),
            "active",
            "verify_satisfaction"
        ));
        if (plan != null) {
            model.addTrace(new TraceLink(
                TraceKind.VERIFIES,
                plan.ref(),
                evidence.ref(),
                "active",
                "verify_satisfaction"
            ));
        }
        return evidence;
    }

    private Artifact configureTest(
        ArtifactKind kind,
        Artifact requirement,
        Artifact behavior,
        Artifact implementation,
        Map<String, Object> spec
    ) {
        String id = String.valueOf(spec.getOrDefault(
            "id",
            kind == ArtifactKind.COMPONENT_TEST
                ? requirement.id() + "/component-test"
                : requirement.id() + "/scenario-test"
        ));
        Map<String, Object> properties = new LinkedHashMap<>(spec);
        properties.put("requirement", requirement.ref());
        properties.put("behavior", behavior.ref());
        if (implementation != null) {
            properties.put("implementation", implementation.ref());
        }

        Artifact test = ensureArtifact(
            id,
            kind,
            properties,
            "verify_satisfaction"
        );
        model.addTrace(new TraceLink(
            TraceKind.COVERS,
            test.ref(),
            requirement.ref(),
            "active",
            "verify_satisfaction"
        ));
        model.addTrace(new TraceLink(
            TraceKind.EXECUTES,
            test.ref(),
            behavior.ref(),
            "active",
            "verify_satisfaction"
        ));
        if (implementation != null) {
            model.addTrace(new TraceLink(
                TraceKind.EXECUTES,
                test.ref(),
                implementation.ref(),
                "active",
                "verify_satisfaction"
            ));
        }
        return test;
    }

    public ImpactPlan propagateChange(Artifact root) {
        Set<String> visited = new LinkedHashSet<>();
        Queue<String> queue = new ArrayDeque<>();
        visited.add(root.ref());
        queue.add(root.ref());

        while (!queue.isEmpty()) {
            String current = queue.remove();
            for (TraceLink trace : model.activeTraces()) {
                String neighbor = null;
                if (trace.source().equals(current)) {
                    neighbor = trace.target();
                } else if (trace.target().equals(current)) {
                    neighbor = trace.source();
                }
                if (neighbor != null && visited.add(neighbor)) {
                    queue.add(neighbor);
                }
            }
        }

        List<String> impacted = new ArrayList<>();
        List<String> invalidatedEvidence = new ArrayList<>();
        List<String> invalidatedArtifacts = new ArrayList<>();
        for (String ref : visited) {
            if (ref.equals(root.ref())) {
                continue;
            }
            impacted.add(ref);
            try {
                Artifact artifact = model.get(ref);
                if (List.of(
                    ArtifactKind.BEHAVIOR_ELEMENT,
                    ArtifactKind.INTERFACE,
                    ArtifactKind.PORT,
                    ArtifactKind.IMPLEMENTATION,
                    ArtifactKind.ALLOCATION,
                    ArtifactKind.DEPLOYMENT,
                    ArtifactKind.VERIFICATION_PLAN
                ).contains(artifact.kind())) {
                    invalidatedArtifacts.add(ref);
                }
                if (artifact.kind() == ArtifactKind.VERIFICATION_EVIDENCE) {
                    invalidatedEvidence.add(ref);
                    invalidatedArtifacts.add(ref);
                }
            } catch (IllegalArgumentException ignored) {
            }
        }
        return new ImpactPlan(
            root.ref(),
            impacted,
            invalidatedEvidence,
            invalidatedArtifacts
        );
    }

    public Reconciliation reconcileViews(Artifact left, Artifact right) {
        List<Conflict> conflicts = new ArrayList<>();
        if (!left.id().equals(right.id())) {
            conflicts.add(new Conflict(
                left.ref(),
                right.ref(),
                "different stable identities"
            ));
        } else if (left.kind() != right.kind()) {
            conflicts.add(new Conflict(
                left.ref(),
                right.ref(),
                "different artifact kinds"
            ));
        } else if (!left.properties().equals(right.properties())) {
            conflicts.add(new Conflict(
                left.ref(),
                right.ref(),
                "different semantic properties"
            ));
        }
        return conflicts.isEmpty()
            ? new Reconciliation("consistent", List.of())
            : new Reconciliation("conflict", conflicts);
    }

    public Baseline baselineThread(Artifact requirement) {
        return model.baselineThread(requirement.id());
    }

    public List<String> checkContinuity(Artifact requirement, boolean strict) {
        List<String> diagnostics = new ArrayList<>();
        List<Artifact> architecture = new ArrayList<>();
        for (TraceLink trace : model.activeTraces()) {
            if (trace.kind() == TraceKind.REALIZES
                && trace.source().equals(requirement.ref())) {
                try {
                    architecture.add(model.get(trace.target()));
                } catch (IllegalArgumentException ignored) {
                }
            }
        }
        if (architecture.isEmpty()) {
            diagnostics.add(
                "requirement " + requirement.ref() +
                    " has no architectural realization"
            );
        }

        boolean behavior = false;
        for (Artifact element : architecture) {
            for (TraceLink trace : model.activeTraces()) {
                if (trace.kind() == TraceKind.SUPPORTS
                    && trace.source().equals(element.ref())) {
                    behavior = true;
                    break;
                }
            }
        }
        if (!behavior) {
            diagnostics.add(
                "requirement " + requirement.ref() +
                    " has no behavioral realization"
            );
        }

        boolean componentCoverage = false;
        boolean scenarioCoverage = false;
        boolean passingEvidence = false;
        for (TraceLink trace : model.activeTraces()) {
            if (trace.kind() == TraceKind.COVERS
                && trace.target().equals(requirement.ref())) {
                try {
                    Artifact test = model.get(trace.source());
                    if (test.kind() == ArtifactKind.COMPONENT_TEST) {
                        componentCoverage = true;
                    }
                    if (test.kind() == ArtifactKind.SCENARIO_TEST) {
                        scenarioCoverage = true;
                    }
                } catch (IllegalArgumentException ignored) {
                }
            }
        }
        for (Artifact artifact : model.latestArtifacts()) {
            if (artifact.kind() == ArtifactKind.VERIFICATION_EVIDENCE
                && requirement.ref().equals(artifact.properties().get("requirement"))
                && "pass".equalsIgnoreCase(
                    String.valueOf(artifact.properties().get("result"))
                )) {
                passingEvidence = true;
            }
        }
        if (!componentCoverage) {
            diagnostics.add(
                "requirement " + requirement.ref() +
                    " has no component-level test coverage"
            );
        }
        if (!scenarioCoverage) {
            diagnostics.add(
                "requirement " + requirement.ref() +
                    " has no simulated scenario coverage"
            );
        }
        if (!passingEvidence) {
            diagnostics.add(
                "requirement " + requirement.ref() +
                    " has no passing verification evidence"
            );
        }

        if (strict) {
            boolean implementation = false;
            boolean allocation = false;
            boolean deployment = false;
            boolean plan = false;
            for (Artifact artifact : model.latestArtifacts()) {
                if (artifact.kind() == ArtifactKind.IMPLEMENTATION) {
                    implementation = true;
                }
                if (artifact.kind() == ArtifactKind.ALLOCATION) {
                    allocation = true;
                }
                if (artifact.kind() == ArtifactKind.DEPLOYMENT) {
                    deployment = true;
                }
                if (artifact.kind() == ArtifactKind.VERIFICATION_PLAN
                    && requirement.ref().equals(artifact.properties().get("requirement"))) {
                    plan = true;
                }
            }
            if (!implementation) {
                diagnostics.add(
                    "requirement " + requirement.ref() +
                        " has no generated implementation"
                );
            }
            if (!allocation) {
                diagnostics.add(
                    "requirement " + requirement.ref() +
                        " has no architectural allocation"
                );
            }
            if (!deployment) {
                diagnostics.add(
                    "requirement " + requirement.ref() +
                        " has no deployment target"
                );
            }
            if (!plan) {
                diagnostics.add(
                    "requirement " + requirement.ref() +
                        " has no verification plan"
                );
            }
        }
        return diagnostics;
    }

    public void synchronizeOperationalScope() {
        List<Artifact> needs = artifactsOfKind(ArtifactKind.STAKEHOLDER_NEED);
        for (Artifact need : needs) {
            developIntent(need, null);
        }

        List<Artifact> requirements = artifactsOfKind(ArtifactKind.REQUIREMENT);
        if (requirements.isEmpty()) {
            relations.enforce(model);
            return;
        }
        Artifact requirement = requirements.get(requirements.size() - 1);

        List<Artifact> existingArchitecture =
            artifactsOfKind(ArtifactKind.ARCHITECTURAL_ELEMENT);
        List<Artifact> architecture = new ArrayList<>();
        List<Object> architectureSpecs = new ArrayList<>();
        for (Artifact element : existingArchitecture) {
            Map<String, Object> spec = new LinkedHashMap<>();
            spec.put(
                "name",
                element.properties().getOrDefault("name", element.id())
            );
            spec.put("id", element.id());
            spec.putAll(element.properties());
            spec.put("id", element.id());
            architectureSpecs.add(spec);
        }
        if (!architectureSpecs.isEmpty()) {
            architecture = realizeArchitecture(
                requirement,
                architectureSpecs,
                Map.of()
            );
        }

        Artifact firstArchitecture =
            architecture.isEmpty() ? null : architecture.get(0);

        for (Artifact interfaceArtifact :
             artifactsOfKind(ArtifactKind.INTERFACE)) {
            if (firstArchitecture != null) {
                realizeInterface(
                    requirement,
                    firstArchitecture,
                    interfaceArtifact.id(),
                    mapCopy(interfaceArtifact.properties())
                );
            }
        }

        for (Artifact port : artifactsOfKind(ArtifactKind.PORT)) {
            Artifact owner = firstInterface();
            if (owner != null) {
                realizePort(owner, mapCopy(port.properties()), port.id());
            }
        }

        for (Artifact connection :
             artifactsOfKind(ArtifactKind.CONNECTION)) {
            String sourceRef = String.valueOf(
                connection.properties().getOrDefault("source", "")
            );
            String targetRef = String.valueOf(
                connection.properties().getOrDefault("target", "")
            );
            Artifact source = artifactForRef(sourceRef);
            Artifact target = artifactForRef(targetRef);
            if (source != null && target != null) {
                connectPorts(
                    source,
                    target,
                    connection.id(),
                    mapCopy(connection.properties())
                );
            }
        }

        for (Artifact behavior :
             artifactsOfKind(ArtifactKind.BEHAVIOR_ELEMENT)) {
            realizeBehavior(
                requirement,
                architecture,
                behavior.id(),
                mapCopy(behavior.properties())
            );

            for (Object callValue :
                 listValue(behavior.properties(), "functionCalls")) {
                if (callValue instanceof Map<?, ?> call) {
                    configureFunctionCall(
                        behavior,
                        mapCopy(call)
                    );
                }
            }
            for (Object communicationValue :
                 listValue(behavior.properties(), "communications")) {
                if (communicationValue instanceof Map<?, ?> communication) {
                    configureCommunication(
                        behavior,
                        mapCopy(communication)
                    );
                }
            }
            for (Object scheduleValue :
                 listValue(behavior.properties(), "schedules")) {
                if (scheduleValue instanceof Map<?, ?> schedule) {
                    configureSchedule(
                        behavior,
                        mapCopy(schedule)
                    );
                }
            }
        }

        for (Artifact allocation :
             artifactsOfKind(ArtifactKind.ALLOCATION)) {
            Artifact behavior = artifactForRef(
                String.valueOf(
                    allocation.properties().getOrDefault("sourceRef", "")
                )
            );
            Artifact target = artifactForRef(
                String.valueOf(
                    allocation.properties().getOrDefault("targetRef", "")
                )
            );
            if (behavior != null && target != null) {
                allocateBehavior(
                    behavior,
                    target,
                    allocation.id(),
                    mapCopy(allocation.properties())
                );
            }
        }

        for (Artifact deployment :
             artifactsOfKind(ArtifactKind.DEPLOYMENT)) {
            Artifact component = artifactForRef(
                String.valueOf(
                    deployment.properties().getOrDefault("componentRef", "")
                )
            );
            Artifact target = artifactForRef(
                String.valueOf(
                    deployment.properties().getOrDefault("targetRef", "")
                )
            );
            if (component != null && target != null) {
                deployComponent(
                    component,
                    target,
                    deployment.id(),
                    mapCopy(deployment.properties())
                );
            }
        }

        for (Artifact implementation :
             artifactsOfKind(ArtifactKind.IMPLEMENTATION)) {
            Artifact behavior = artifactForRef(
                String.valueOf(
                    implementation.properties().getOrDefault("sourceBehavior", "")
                )
            );
            if (behavior != null) {
                Object codeGeneration =
                    implementation.properties().get("codeGeneration");
                Map<String, Object> codeGenerationMap =
                    codeGeneration instanceof Map<?, ?> map
                        ? mapCopy(map)
                        : Map.of(
                            "targetLanguage",
                            implementation.properties().getOrDefault("language", ""),
                            "targetPlatform",
                            implementation.properties().getOrDefault("targetPlatform", ""),
                            "entryPoint",
                            implementation.properties().getOrDefault("entryPoint", "")
                        );
                generateImplementation(
                    behavior,
                    implementation.id(),
                    codeGenerationMap
                );
            }
        }

        for (Artifact behavior :
             artifactsOfKind(ArtifactKind.BEHAVIOR_ELEMENT)) {
            for (Artifact plan :
                 artifactsOfKind(ArtifactKind.VERIFICATION_PLAN)) {
                Artifact implementation = firstImplementation();
                planVerification(
                    requirement,
                    behavior,
                    implementation,
                    plan.id(),
                    mapCopy(plan.properties())
                );
            }
        }

        for (Artifact evidence :
             artifactsOfKind(ArtifactKind.VERIFICATION_EVIDENCE)) {
            Artifact behavior = artifactForRef(
                String.valueOf(
                    evidence.properties().getOrDefault("behavior", "")
                )
            );
            if (behavior == null) {
                behavior = firstBehavior();
            }
            Artifact implementation = firstImplementation();
            Artifact plan = firstPlan();
            if (behavior != null) {
                List<Map<String, Object>> componentCases = new ArrayList<>();
                List<Map<String, Object>> scenarioCases = new ArrayList<>();
                for (Artifact test :
                     artifactsOfKind(ArtifactKind.COMPONENT_TEST)) {
                    componentCases.add(mapCopy(test.properties()));
                }
                for (Artifact test :
                     artifactsOfKind(ArtifactKind.SCENARIO_TEST)) {
                    scenarioCases.add(mapCopy(test.properties()));
                }
                verifySatisfaction(
                    requirement,
                    behavior,
                    implementation,
                    plan,
                    evidence.id(),
                    String.valueOf(evidence.properties().getOrDefault("result", "pass")),
                    String.valueOf(evidence.properties().getOrDefault("summary", "")),
                    componentCases,
                    scenarioCases,
                    mapOfExecutionEnvironment(
                        evidence.properties().get("executionEnvironment")
                    )
                );
            }
        }

        relations.enforce(model);
        baselineThread(requirement);
    }

    private List<Artifact> artifactsOfKind(ArtifactKind kind) {
        List<Artifact> result = new ArrayList<>();
        for (Artifact artifact : model.latestArtifacts()) {
            if (artifact.kind() == kind) {
                result.add(artifact);
            }
        }
        return result;
    }

    private Artifact artifactForRef(String ref) {
        if (ref == null || ref.isBlank()) {
            return null;
        }
        try {
            return model.get(ref);
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private Artifact firstInterface() {
        List<Artifact> interfaces = artifactsOfKind(ArtifactKind.INTERFACE);
        return interfaces.isEmpty() ? null : interfaces.get(0);
    }

    private Artifact firstBehavior() {
        List<Artifact> behaviors =
            artifactsOfKind(ArtifactKind.BEHAVIOR_ELEMENT);
        return behaviors.isEmpty() ? null : behaviors.get(0);
    }

    private Artifact firstImplementation() {
        List<Artifact> implementations =
            artifactsOfKind(ArtifactKind.IMPLEMENTATION);
        return implementations.isEmpty() ? null : implementations.get(0);
    }

    private Artifact firstPlan() {
        List<Artifact> plans =
            artifactsOfKind(ArtifactKind.VERIFICATION_PLAN);
        return plans.isEmpty() ? null : plans.get(0);
    }

    private List<?> listValue(
        Map<String, Object> properties,
        String key
    ) {
        Object value = properties.get(key);
        return value instanceof List<?> list ? list : List.of();
    }

    private Map<String, Object> mapCopy(Map<?, ?> source) {
        Map<String, Object> result = new LinkedHashMap<>();
        source.forEach((key, value) ->
            result.put(String.valueOf(key), value)
        );
        return result;
    }

    private Map<String, Object> mapOfExecutionEnvironment(Object value) {
        return value instanceof Map<?, ?> map
            ? mapCopy(map)
            : Map.of();
    }

    private Artifact ensureArtifact(
        String id,
        ArtifactKind kind,
        Map<String, Object> properties,
        String derivedBy
    ) {
        Artifact existing = null;
        try {
            existing = model.latest(id);
        } catch (IllegalArgumentException ignored) {
        }

        if (existing != null && existing.properties().equals(properties)) {
            return existing;
        }
        int revision = existing == null ? 1 : existing.revision() + 1;
        List<String> supersedes = existing == null
            ? List.of()
            : List.of(existing.ref());
        Artifact replacement = new Artifact(
            id,
            kind,
            revision,
            properties,
            supersedes
        );
        replacement = model.addArtifact(replacement);
        if (existing != null) {
            model.addTrace(new TraceLink(
                TraceKind.SUPERSEDES,
                existing.ref(),
                replacement.ref(),
                "active",
                derivedBy
            ));
        }
        return replacement;
    }

    private static List<String> mergeSupersedes(
        List<String> existingSupersedes,
        String supersededRef
    ) {
        if (existingSupersedes.contains(supersededRef)) {
            return existingSupersedes;
        }
        List<String> result = new ArrayList<>(existingSupersedes);
        result.add(supersededRef);
        return result;
    }

    private static String slug(String value) {
        StringBuilder result = new StringBuilder();
        boolean separator = false;
        for (char character : value.toUpperCase().toCharArray()) {
            if (Character.isLetterOrDigit(character)) {
                if (separator && !result.isEmpty()) {
                    result.append('-');
                }
                result.append(character);
                separator = false;
            } else {
                separator = true;
            }
        }
        return result.toString();
    }
}
