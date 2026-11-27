package org.github.michaellrowley.sysmlqvt.qvt;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;
import org.github.michaellrowley.sysmlqvt.model.TraceKind;
import org.github.michaellrowley.sysmlqvt.model.TraceLink;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class ContinuityRelations {
    public record RelationDiagnostic(String relation, String message) {
    }

    public List<RelationDiagnostic> checkonly(SysMLModel model) {
        List<RelationDiagnostic> diagnostics = new ArrayList<>();

        for (Artifact artifact : model.allArtifacts()) {
            for (String superseded : artifact.supersedes()) {
                if (!containsRef(model, superseded)) {
                    diagnostics.add(new RelationDiagnostic(
                        "ArtifactSupersession",
                        "Missing superseded artifact " + superseded
                    ));
                }
            }
        }

        for (Artifact need : artifactsOfKind(model, ArtifactKind.STAKEHOLDER_NEED)) {
            Artifact requirement = requirementForNeed(model, need);
            if (requirement == null) {
                diagnostics.add(new RelationDiagnostic(
                    "StakeholderNeedToRequirement",
                    "Need " + need.ref() + " has no requirement"
                ));
            }
        }

        for (Artifact requirement : artifactsOfKind(model, ArtifactKind.REQUIREMENT)) {
            boolean realization = false;
            for (Artifact architecture : artifactsOfKind(model, ArtifactKind.ARCHITECTURAL_ELEMENT)) {
                Object requirementRef = architecture.properties().get("requirement");
                if (requirementRef == null
                    || requirementRef.toString().startsWith(requirement.id() + "@")) {
                    realization = true;
                    break;
                }
            }
            if (!realization) {
                diagnostics.add(new RelationDiagnostic(
                    "RequirementToArchitecture",
                    "Requirement " + requirement.ref() +
                        " has no architectural realization"
                ));
            }
        }

        for (Artifact interfaceArtifact : artifactsOfKind(model, ArtifactKind.INTERFACE)) {
            Object architectureRef = interfaceArtifact.properties().get("architecture");
            if (architectureRef == null || !containsRef(model, String.valueOf(architectureRef))) {
                diagnostics.add(new RelationDiagnostic(
                    "ArchitectureToInterfaceAndPort",
                    "Interface " + interfaceArtifact.ref() +
                        " has no architecture exposure"
                ));
            }
            boolean port = false;
            for (Artifact portArtifact : artifactsOfKind(model, ArtifactKind.PORT)) {
                Object interfaceRef = portArtifact.properties().get("interface");
                if (interfaceRef != null
                    && interfaceRef.toString().startsWith(interfaceArtifact.id() + "@")) {
                    port = true;
                    break;
                }
            }
            if (!port) {
                diagnostics.add(new RelationDiagnostic(
                    "ArchitectureToInterfaceAndPort",
                    "Interface " + interfaceArtifact.ref() + " has no exposed port"
                ));
            }
        }

        for (Artifact behavior : artifactsOfKind(model, ArtifactKind.BEHAVIOR_ELEMENT)) {
            boolean functionCallCovered = false;
            for (Artifact call : artifactsOfKind(model, ArtifactKind.FUNCTION_CALL)) {
                Object callBehavior = call.properties().get("behavior");
                if (callBehavior != null
                    && callBehavior.toString().startsWith(behavior.id() + "@")) {
                    functionCallCovered = true;
                    break;
                }
            }
            if (!functionCallCovered
                && behaviorPropertiesContain(model, behavior, "functionCalls")) {
                diagnostics.add(new RelationDiagnostic(
                    "BehaviorFunctionCall",
                    "Behavior " + behavior.ref() +
                        " has function calls without call traces"
                ));
            }

            boolean communicationCovered = false;
            for (Artifact communication :
                 artifactsOfKind(model, ArtifactKind.COMMUNICATION)) {
                Object communicationBehavior =
                    communication.properties().get("behavior");
                if (communicationBehavior != null
                    && communicationBehavior.toString().startsWith(behavior.id() + "@")) {
                    communicationCovered = true;
                    break;
                }
            }
            if (!communicationCovered
                && behaviorPropertiesContain(model, behavior, "communications")) {
                diagnostics.add(new RelationDiagnostic(
                    "BehaviorCommunication",
                    "Behavior " + behavior.ref() +
                        " has communications without communication traces"
                ));
            }

            boolean scheduleCovered = false;
            for (Artifact schedule :
                 artifactsOfKind(model, ArtifactKind.SCHEDULE)) {
                Object scheduleBehavior = schedule.properties().get("behavior");
                if (scheduleBehavior != null
                    && scheduleBehavior.toString().startsWith(behavior.id() + "@")) {
                    scheduleCovered = true;
                    break;
                }
            }
            if (!scheduleCovered
                && behaviorPropertiesContain(model, behavior, "schedules")) {
                diagnostics.add(new RelationDiagnostic(
                    "BehaviorSchedule",
                    "Behavior " + behavior.ref() +
                        " has schedules without schedule traces"
                ));
            }
            if (!hasAllocation(model, behavior.ref())) {
                diagnostics.add(new RelationDiagnostic(
                    "BehaviorToAllocation",
                    "Behavior " + behavior.ref() +
                        " has no allocation"
                ));
            }
            if (!hasImplementation(model, behavior.ref())) {
                diagnostics.add(new RelationDiagnostic(
                    "BehaviorToImplementation",
                    "Behavior " + behavior.ref() +
                        " has no generated implementation"
                ));
            }
        }

        for (Artifact plan : artifactsOfKind(model, ArtifactKind.VERIFICATION_PLAN)) {
            Artifact requirement = requirementForRef(
                model,
                String.valueOf(plan.properties().get("requirement"))
            );
            if (requirement == null) {
                diagnostics.add(new RelationDiagnostic(
                    "VerificationPlanToEvidence",
                    "Verification plan " + plan.ref() +
                        " has no linked requirement"
                ));
            }
        }

        for (Artifact test : artifactsOfKind(model, ArtifactKind.COMPONENT_TEST)) {
            if (!test.properties().containsKey("requirement")
                || !test.properties().containsKey("behavior")) {
                diagnostics.add(new RelationDiagnostic(
                    "TestToRequirementAndBehavior",
                    "Component test " + test.ref() +
                        " is missing requirement or behavior coverage"
                ));
            }
        }
        for (Artifact test : artifactsOfKind(model, ArtifactKind.SCENARIO_TEST)) {
            if (!test.properties().containsKey("requirement")
                || !test.properties().containsKey("behavior")) {
                diagnostics.add(new RelationDiagnostic(
                    "TestToRequirementAndBehavior",
                    "Scenario test " + test.ref() +
                        " is missing requirement or behavior coverage"
                ));
            }
        }

        for (Artifact evidence : artifactsOfKind(model, ArtifactKind.VERIFICATION_EVIDENCE)) {
            if (!"pass".equalsIgnoreCase(
                String.valueOf(evidence.properties().get("result"))
            )) {
                diagnostics.add(new RelationDiagnostic(
                    "VerificationPlanToEvidence",
                    "Evidence " + evidence.ref() + " is not passing"
                ));
            }
        }
        return diagnostics;
    }

    public List<TraceLink> enforce(SysMLModel model) {
        List<TraceLink> created = new ArrayList<>();

        for (Artifact artifact : model.allArtifacts()) {
            for (String superseded : artifact.supersedes()) {
                try {
                    Artifact previous = model.get(superseded);
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.SUPERSEDES,
                        previous.ref(),
                        artifact.ref(),
                        "active",
                        "qvtr.ArtifactSupersession"
                    )));
                } catch (IllegalArgumentException ignored) {
                }
            }
        }

        for (Artifact need : artifactsOfKind(model, ArtifactKind.STAKEHOLDER_NEED)) {
            Artifact requirement = requirementForNeed(model, need);
            if (requirement != null) {
                created.add(model.addTrace(new TraceLink(
                    TraceKind.ORIGIN,
                    need.ref(),
                    requirement.ref(),
                    "active",
                    "qvtr.StakeholderNeedToRequirement"
                )));
            }
        }

        for (Artifact requirement : artifactsOfKind(model, ArtifactKind.REQUIREMENT)) {
            for (Artifact architecture : artifactsOfKind(model, ArtifactKind.ARCHITECTURAL_ELEMENT)) {
                Object architectureRequirement = architecture.properties().get("requirement");
                if (architectureRequirement == null
                    || architectureRequirement.toString().startsWith(requirement.id() + "@")) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.REALIZES,
                        requirement.ref(),
                        architecture.ref(),
                        "active",
                        "qvtr.RequirementToArchitecture"
                    )));
                }
            }
        }

        for (Artifact architecture : artifactsOfKind(model, ArtifactKind.ARCHITECTURAL_ELEMENT)) {
            for (Artifact interfaceArtifact :
                 artifactsOfKind(model, ArtifactKind.INTERFACE)) {
                Object architectureRef =
                    interfaceArtifact.properties().get("architecture");
                if (architectureRef == null
                    || architectureRef.toString().startsWith(architecture.id() + "@")) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.EXPOSES,
                        architecture.ref(),
                        interfaceArtifact.ref(),
                        "active",
                        "qvtr.ArchitectureToInterfaceAndPort"
                    )));
                }
            }
            for (Artifact behavior : artifactsOfKind(model, ArtifactKind.BEHAVIOR_ELEMENT)) {
                created.add(model.addTrace(new TraceLink(
                    TraceKind.SUPPORTS,
                    architecture.ref(),
                    behavior.ref(),
                    "active",
                    "qvtr.ArchitectureToBehavior"
                )));
            }
        }

        for (Artifact interfaceArtifact :
             artifactsOfKind(model, ArtifactKind.INTERFACE)) {
            for (Artifact port : artifactsOfKind(model, ArtifactKind.PORT)) {
                Object interfaceRef = port.properties().get("interface");
                if (interfaceRef == null
                    || interfaceRef.toString().startsWith(interfaceArtifact.id() + "@")) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.EXPOSES,
                        interfaceArtifact.ref(),
                        port.ref(),
                        "active",
                        "qvtr.ArchitectureToInterfaceAndPort"
                    )));
                }
            }
        }

        for (Artifact connection : artifactsOfKind(model, ArtifactKind.CONNECTION)) {
            Object source = connection.properties().get("source");
            Object target = connection.properties().get("target");
            if (source != null) {
                created.add(model.addTrace(new TraceLink(
                    TraceKind.CONNECTS,
                    String.valueOf(source),
                    connection.ref(),
                    "active",
                    "qvtr.PortToPortConnection"
                )));
            }
            if (target != null) {
                created.add(model.addTrace(new TraceLink(
                    TraceKind.CONNECTS,
                    connection.ref(),
                    String.valueOf(target),
                    "active",
                    "qvtr.PortToPortConnection"
                )));
            }
        }

        for (Artifact behavior : artifactsOfKind(model, ArtifactKind.BEHAVIOR_ELEMENT)) {
            Object functionCalls = behavior.properties().get("functionCalls");
            if (functionCalls instanceof List<?> calls) {
                for (Object callValue : calls) {
                    if (callValue instanceof Map<?, ?> call) {
                        String id = mapString(
                            call,
                            "id",
                            behavior.id() + "/call"
                        );
                        created.add(materializeNested(
                            model,
                            ArtifactKind.FUNCTION_CALL,
                            id,
                            call,
                            extraMap("behavior", behavior.ref()),
                            TraceKind.CALLS,
                            behavior,
                            "qvtr.BehaviorFunctionCall",
                            created
                        ));
                    }
                }
            }

            for (Artifact call : artifactsOfKind(model, ArtifactKind.FUNCTION_CALL)) {
                Object callBehavior = call.properties().get("behavior");
                if (callBehavior != null
                    && callBehavior.toString().startsWith(behavior.id() + "@")) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.CALLS,
                        behavior.ref(),
                        call.ref(),
                        "active",
                        "qvtr.BehaviorFunctionCall"
                    )));
                }
            }

            Object communications = behavior.properties().get("communications");
            if (communications instanceof List<?> communicationList) {
                for (Object communicationValue : communicationList) {
                    if (communicationValue instanceof Map<?, ?> communication) {
                        String id = mapString(
                            communication,
                            "id",
                            behavior.id() + "/communication"
                        );
                        String direction =
                            mapString(communication, "direction", "");
                        TraceKind kind = "in".equalsIgnoreCase(direction)
                            ? TraceKind.SUBSCRIBES
                            : "out".equalsIgnoreCase(direction)
                                ? TraceKind.PUBLISHES
                                : TraceKind.CONNECTS;
                        created.add(materializeNested(
                            model,
                            ArtifactKind.COMMUNICATION,
                            id,
                            communication,
                            extraMap("behavior", behavior.ref()),
                            kind,
                            behavior,
                            "qvtr.BehaviorCommunication",
                            created
                        ));
                    }
                }
            }

            Object schedules = behavior.properties().get("schedules");
            if (schedules instanceof List<?> scheduleList) {
                for (Object scheduleValue : scheduleList) {
                    if (scheduleValue instanceof Map<?, ?> schedule) {
                        String id = mapString(
                            schedule,
                            "id",
                            behavior.id() + "/schedule"
                        );
                        created.add(materializeNested(
                            model,
                            ArtifactKind.SCHEDULE,
                            id,
                            schedule,
                            extraMap("behavior", behavior.ref()),
                            TraceKind.SCHEDULES,
                            behavior,
                            "qvtr.BehaviorSchedule",
                            created
                        ));
                    }
                }
            }

            for (Artifact allocation : artifactsOfKind(model, ArtifactKind.ALLOCATION)) {
                Object sourceRef = allocation.properties().get("sourceRef");
                Object targetRef = allocation.properties().get("targetRef");
                if (sourceRef != null
                    && sourceRef.toString().startsWith(behavior.id() + "@")) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.ALLOCATES,
                        behavior.ref(),
                        targetArtifactRef(model, targetRef),
                        "active",
                        "qvtr.BehaviorToAllocation"
                    )));
                }
            }

            for (Artifact implementation :
                 artifactsOfKind(model, ArtifactKind.IMPLEMENTATION)) {
                Object sourceBehavior = implementation.properties().get("sourceBehavior");
                if (sourceBehavior == null
                    || sourceBehavior.toString().startsWith(behavior.id() + "@")) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.GENERATES,
                        behavior.ref(),
                        implementation.ref(),
                        "active",
                        "qvtr.BehaviorToImplementation"
                    )));
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.IMPLEMENTS,
                        implementation.ref(),
                        behavior.ref(),
                        "active",
                        "qvtr.BehaviorToImplementation"
                    )));
                }
            }

            for (Artifact communication :
                 artifactsOfKind(model, ArtifactKind.COMMUNICATION)) {
                Object communicationBehavior =
                    communication.properties().get("behavior");
                if (communicationBehavior != null
                    && communicationBehavior.toString().startsWith(behavior.id() + "@")) {
                    String direction =
                        String.valueOf(communication.properties().getOrDefault("direction", ""));
                    TraceKind kind = "in".equalsIgnoreCase(direction)
                        ? TraceKind.SUBSCRIBES
                        : "out".equalsIgnoreCase(direction)
                            ? TraceKind.PUBLISHES
                            : TraceKind.CONNECTS;
                    created.add(model.addTrace(new TraceLink(
                        kind,
                        behavior.ref(),
                        communication.ref(),
                        "active",
                        "qvtr.BehaviorCommunication"
                    )));
                }
            }
        }

        for (Artifact deployment : artifactsOfKind(model, ArtifactKind.DEPLOYMENT)) {
            Object componentRef = deployment.properties().get("componentRef");
            Object targetRef = deployment.properties().get("targetRef");
            if (componentRef != null) {
                created.add(model.addTrace(new TraceLink(
                    TraceKind.DEPLOYED_TO,
                    targetArtifactRef(model, componentRef),
                    targetArtifactRef(model, targetRef),
                    "active",
                    "qvtr.ComponentToDeployment"
                )));
            }
        }

        for (Artifact requirement : artifactsOfKind(model, ArtifactKind.REQUIREMENT)) {
            for (Artifact plan :
                 artifactsOfKind(model, ArtifactKind.VERIFICATION_PLAN)) {
                Object requirementRef = plan.properties().get("requirement");
                if (requirementRef != null
                    && requirementRef.toString().startsWith(requirement.id() + "@")) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.COVERS,
                        plan.ref(),
                        requirement.ref(),
                        "active",
                        "qvtr.VerificationPlanToEvidence"
                    )));
                }
            }
            for (Artifact test : artifactsOfKind(model, ArtifactKind.COMPONENT_TEST)) {
                addTestTraces(model, test, requirement, created);
            }
            for (Artifact test : artifactsOfKind(model, ArtifactKind.SCENARIO_TEST)) {
                addTestTraces(model, test, requirement, created);
            }
        }

        for (Artifact evidence : artifactsOfKind(model, ArtifactKind.VERIFICATION_EVIDENCE)) {
            if (!"pass".equalsIgnoreCase(
                String.valueOf(evidence.properties().get("result"))
            )) {
                continue;
            }
            for (Artifact behavior : artifactsOfKind(model, ArtifactKind.BEHAVIOR_ELEMENT)) {
                Object behaviorRef = evidence.properties().get("behavior");
                if (behaviorRef != null
                    && behaviorRef.toString().startsWith(behavior.id() + "@")) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.VERIFIES,
                        behavior.ref(),
                        evidence.ref(),
                        "active",
                        "qvtr.VerificationPlanToEvidence"
                    )));
                }
            }
            Object planRef = evidence.properties().get("verificationPlan");
            if (planRef != null) {
                try {
                    Artifact plan = model.get(String.valueOf(planRef));
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.VERIFIES,
                        plan.ref(),
                        evidence.ref(),
                        "active",
                        "qvtr.VerificationPlanToEvidence"
                    )));
                } catch (IllegalArgumentException ignored) {
                }
            }
        }
        return created;
    }

    private TraceLink materializeNested(
        SysMLModel model,
        ArtifactKind kind,
        String id,
        Map<?, ?> spec,
        Map<String, Object> extra,
        TraceKind traceKind,
        Artifact behavior,
        String relationName,
        List<TraceLink> created
    ) {
        Map<String, Object> properties = new LinkedHashMap<>();
        spec.forEach((key, value) ->
            properties.put(String.valueOf(key), value)
        );
        properties.putAll(extra);
        Artifact nested = model.addArtifact(new Artifact(
            id,
            kind,
            1,
            properties,
            List.of()
        ));
        TraceLink trace = model.addTrace(new TraceLink(
            traceKind,
            behavior.ref(),
            nested.ref(),
            "active",
            relationName
        ));
        return trace;
    }

    private void addTestTraces(
        SysMLModel model,
        Artifact test,
        Artifact requirement,
        List<TraceLink> created
    ) {
        Object testRequirement = test.properties().get("requirement");
        if (testRequirement == null
            || !testRequirement.toString().startsWith(requirement.id() + "@")) {
            return;
        }
        created.add(model.addTrace(new TraceLink(
            TraceKind.COVERS,
            test.ref(),
            requirement.ref(),
            "active",
            "qvtr.TestToRequirementAndBehavior"
        )));
        Object behaviorRef = test.properties().get("behavior");
        if (behaviorRef != null) {
            created.add(model.addTrace(new TraceLink(
                TraceKind.EXECUTES,
                test.ref(),
                String.valueOf(behaviorRef),
                "active",
                "qvtr.TestToRequirementAndBehavior"
            )));
        }
        Object implementationRef = test.properties().get("implementation");
        if (implementationRef != null) {
            created.add(model.addTrace(new TraceLink(
                TraceKind.EXECUTES,
                test.ref(),
                String.valueOf(implementationRef),
                "active",
                "qvtr.TestToRequirementAndBehavior"
            )));
        }
    }

    private Artifact requirementForNeed(SysMLModel model, Artifact need) {
        Object configured = need.properties().get("requirementId");
        if (configured == null) {
            return null;
        }
        try {
            return model.latest(String.valueOf(configured));
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private Artifact requirementForRef(SysMLModel model, String ref) {
        if (ref == null || "null".equals(ref) || ref.isBlank()) {
            return null;
        }
        try {
            return model.get(ref);
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private boolean containsRef(SysMLModel model, String ref) {
        try {
            model.get(ref);
            return true;
        } catch (IllegalArgumentException ignored) {
            return false;
        }
    }

    private boolean behaviorPropertiesContain(
        SysMLModel model,
        Artifact behavior,
        String key
    ) {
        Object value = behavior.properties().get(key);
        return value instanceof List<?> list && !list.isEmpty();
    }

    private boolean hasTrace(
        SysMLModel model,
        TraceKind kind,
        String source,
        String target
    ) {
        for (TraceLink trace : model.activeTraces()) {
            if (trace.kind() == kind
                && trace.source().equals(source)
                && (target == null || trace.target().equals(target))) {
                return true;
            }
        }
        return false;
    }

    private boolean hasAllocation(SysMLModel model, String behaviorRef) {
        for (TraceLink trace : model.activeTraces()) {
            if (trace.kind() == TraceKind.ALLOCATES
                && trace.source().equals(behaviorRef)) {
                return true;
            }
        }
        for (Artifact allocation :
             artifactsOfKind(model, ArtifactKind.ALLOCATION)) {
            Object source = allocation.properties().get("sourceRef");
            if (source != null && source.toString().startsWith(
                behaviorRef.substring(0, behaviorRef.indexOf('@'))
            )) {
                return true;
            }
        }
        return false;
    }

    private boolean hasImplementation(SysMLModel model, String behaviorRef) {
        for (TraceLink trace : model.activeTraces()) {
            if (trace.kind() == TraceKind.GENERATES
                && trace.source().equals(behaviorRef)) {
                return true;
            }
        }
        for (Artifact implementation :
             artifactsOfKind(model, ArtifactKind.IMPLEMENTATION)) {
            Object source = implementation.properties().get("sourceBehavior");
            if (source != null
                && source.toString().startsWith(
                    behaviorRef.substring(0, behaviorRef.indexOf('@'))
                )) {
                return true;
            }
        }
        return false;
    }

    private String targetArtifactRef(SysMLModel model, Object ref) {
        if (ref == null) {
            return "";
        }
        String text = String.valueOf(ref);
        if (text.contains("@")) {
            return text;
        }
        try {
            return model.latest(text).ref();
        } catch (IllegalArgumentException ignored) {
            return text;
        }
    }

    private String mapString(
        Map<?, ?> map,
        String key,
        String fallback
    ) {
        Object value = map.get(key);
        return value == null ? fallback : String.valueOf(value);
    }

    private Map<String, Object> extraMap(String key, String value) {
        Map<String, Object> result = new java.util.LinkedHashMap<>();
        result.put(key, value);
        return result;
    }

    private List<Artifact> artifactsOfKind(
        SysMLModel model,
        ArtifactKind kind
    ) {
        List<Artifact> result = new ArrayList<>();
        for (Artifact artifact : model.latestArtifacts()) {
            if (artifact.kind() == kind) {
                result.add(artifact);
            }
        }
        return result;
    }
}
