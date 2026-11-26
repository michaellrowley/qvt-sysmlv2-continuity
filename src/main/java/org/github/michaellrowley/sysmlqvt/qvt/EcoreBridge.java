package org.github.michaellrowley.sysmlqvt.qvt;

import org.eclipse.emf.common.util.EList;
import org.eclipse.emf.ecore.EAttribute;
import org.eclipse.emf.ecore.EClass;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class EcoreBridge {
    private final EPackage sysml;
    private final EPackage continuity;

    public EcoreBridge() {
        sysml = EcoreMetamodel.sysmlPackage();
        continuity = EcoreMetamodel.continuityPackage();
    }

    public List<EObject> sysmlObjects(ResourceSet resourceSet, SysMLModel model) {
        resourceSet.getPackageRegistry().put(EcoreMetamodel.SYSML_NS, sysml);
        resourceSet.getPackageRegistry().put(EcoreMetamodel.CONTINUITY_NS, continuity);

        List<EObject> objects = new ArrayList<>();
        for (Artifact artifact : model.allArtifacts()) {
            objects.add(toEObject(artifact));
        }
        return objects;
    }

    public List<EObject> continuityObjects(ResourceSet resourceSet) {
        resourceSet.getPackageRegistry().put(EcoreMetamodel.SYSML_NS, sysml);
        resourceSet.getPackageRegistry().put(EcoreMetamodel.CONTINUITY_NS, continuity);
        return new ArrayList<>();
    }

    public EObject toEObject(Artifact artifact) {
        EClass clazz = EcoreMetamodel.classFor(sysml, className(artifact.kind()));
        if (clazz == null) {
            clazz = EcoreMetamodel.classFor(sysml, "LifecycleElement");
        }
        EObject object = org.eclipse.emf.ecore.EcoreFactory.eINSTANCE.create(clazz);

        set(object, "id", artifact.id());
        set(object, "revision", artifact.revision());
        set(object, "kind", artifact.kind().text());
        set(object, "properties", new LinkedHashMap<>(artifact.properties()));
        set(object, "supersedes", artifact.supersedes());

        Map<String, Object> properties = artifact.properties();
        switch (artifact.kind()) {
            case STAKEHOLDER_NEED -> {
                set(object, "statement", string(properties, "statement"));
                set(object, "rationale", string(properties, "rationale"));
                set(object, "acceptanceCriteria", list(properties, "acceptanceCriteria"));
                set(object, "requirementId", string(properties, "requirementId"));
            }
            case REQUIREMENT -> {
                set(object, "statement", string(properties, "statement"));
                set(object, "rationale", string(properties, "rationale"));
                set(object, "acceptanceCriteria", list(properties, "acceptanceCriteria"));
                set(object, "sourceNeedId", refId(string(properties, "sourceNeed")));
            }
            case ARCHITECTURAL_ELEMENT -> {
                set(object, "name", string(properties, "name"));
                set(object, "requirementId", refId(string(properties, "requirement")));
            }
            case INTERFACE -> {
                set(object, "name", string(properties, "name"));
                set(object, "protocol", string(properties, "protocol"));
                set(object, "operations", properties.get("operations"));
                set(object, "ports", properties.get("ports"));
            }
            case PORT -> {
                set(object, "name", string(properties, "name"));
                set(object, "direction", string(properties, "direction"));
                set(object, "kind", string(properties, "kind"));
                set(object, "interfaceId", refId(string(properties, "interface")));
                set(object, "protocol", string(properties, "protocol"));
                set(object, "binding", properties.get("binding"));
            }
            case CONNECTION -> {
                set(object, "sourcePortId", refId(string(properties, "source")));
                set(object, "targetPortId", refId(string(properties, "target")));
                set(object, "transport", string(properties, "transport"));
                set(object, "qos", properties.get("qos"));
            }
            case BEHAVIOR_ELEMENT -> {
                set(object, "behaviorKind", string(properties, "kind"));
                set(object, "entryPoint", string(properties, "entryPoint"));
                set(object, "initialState", string(properties, "initialState"));
                set(object, "states", list(properties, "states"));
                set(object, "parameters", properties.get("parameters"));
                set(object, "variables", properties.get("variables"));
                set(object, "results", properties.get("results"));
                set(object, "operations", properties.get("operations"));
                set(object, "functionCalls", properties.get("functionCalls"));
                set(object, "communications", properties.get("communications"));
                set(object, "schedules", properties.get("schedules"));
                set(object, "transitions", properties.get("transitions"));
                set(object, "actions", properties.get("actions"));
                set(object, "concurrency", string(properties, "concurrency"));
            }
            case FUNCTION_CALL -> {
                set(object, "functionName", string(properties, "functionName"));
                set(object, "target", string(properties, "target"));
                set(object, "arguments", properties.get("arguments"));
                set(object, "returnBinding", string(properties, "returnBinding"));
                set(object, "synchronous", properties.get("synchronous"));
                set(object, "timeoutMs", properties.get("timeoutMs"));
            }
            case COMMUNICATION -> {
                set(object, "communicationKind", string(properties, "kind"));
                set(object, "direction", string(properties, "direction"));
                set(object, "channel", string(properties, "channel"));
                set(object, "endpoint", string(properties, "endpoint"));
                set(object, "protocol", string(properties, "protocol"));
                set(object, "payloadType", string(properties, "payloadType"));
                set(object, "qos", properties.get("qos"));
                set(object, "timeoutMs", properties.get("timeoutMs"));
                set(object, "reliable", properties.get("reliable"));
            }
            case SCHEDULE -> {
                set(object, "scheduleKind", string(properties, "kind"));
                set(object, "periodMs", properties.get("periodMs"));
                set(object, "deadlineMs", properties.get("deadlineMs"));
                set(object, "wcetMs", properties.get("wcetMs"));
                set(object, "priority", properties.get("priority"));
                set(object, "jitterMs", properties.get("jitterMs"));
                set(object, "entryPoint", string(properties, "entryPoint"));
            }
            case ALLOCATION -> {
                set(object, "sourceRef", string(properties, "sourceRef"));
                set(object, "targetRef", string(properties, "targetRef"));
            }
            case DEPLOYMENT -> {
                set(object, "componentRef", string(properties, "componentRef"));
                set(object, "targetRef", string(properties, "targetRef"));
                set(object, "environment", string(properties, "environment"));
                set(object, "runtime", string(properties, "runtime"));
                set(object, "resources", properties.get("resources"));
            }
            case IMPLEMENTATION -> {
                set(object, "sourceBehavior", refId(string(properties, "sourceBehavior")));
                set(object, "sourceBehaviorRevision", refRevision(string(properties, "sourceBehavior")));
                set(object, "language", string(properties, "language"));
                set(object, "targetPlatform", string(properties, "targetPlatform"));
                set(object, "entryPoint", string(properties, "entryPoint"));
                set(object, "buildSystem", string(properties, "buildSystem"));
                set(object, "sourceFormat", string(properties, "sourceFormat"));
                set(object, "behaviorModel", properties.get("behaviorModel"));
                set(object, "codeGeneration", properties.get("codeGeneration"));
            }
            case VERIFICATION_PLAN -> {
                set(object, "requirementRef", string(properties, "requirement"));
                set(object, "behaviorRef", string(properties, "behavior"));
                set(object, "implementationRef", string(properties, "implementation"));
                set(object, "strategy", string(properties, "strategy"));
                set(object, "testLevels", list(properties, "testLevels"));
                set(object, "environments", list(properties, "environments"));
            }
            case COMPONENT_TEST, SCENARIO_TEST -> {
                set(object, "purpose", string(properties, "purpose"));
                set(object, "result", string(properties, "result"));
                set(object, "requirementId", refId(string(properties, "requirement")));
                set(object, "requirementRevision", refRevision(string(properties, "requirement")));
                set(object, "behaviorId", refId(string(properties, "behavior")));
                set(object, "behaviorRevision", refRevision(string(properties, "behavior")));
                set(object, "implementationId", refId(string(properties, "implementation")));
                set(object, "implementationRevision", refRevision(string(properties, "implementation")));
                set(object, "executionEnvironment", properties.get("executionEnvironment"));
            }
            case VERIFICATION_EVIDENCE -> {
                set(object, "requirementRef", string(properties, "requirement"));
                set(object, "behaviorRef", string(properties, "behavior"));
                set(object, "implementationRef", string(properties, "implementation"));
                set(object, "verificationPlan", string(properties, "verificationPlan"));
                set(object, "result", string(properties, "result"));
                set(object, "summary", string(properties, "summary"));
                set(object, "executionEnvironment", properties.get("executionEnvironment"));
            }
        }
        return object;
    }

    public void mergeFrom(
        SysMLModel model,
        List<EObject> sysmlObjects
    ) {
        for (EObject object : sysmlObjects) {
            Artifact artifact = fromEObject(object);
            if (artifact != null) {
                model.addArtifact(artifact);
            }
        }
    }

    public Artifact fromEObject(EObject object) {
        Object id = get(object, "id");
        if (id == null) {
            return null;
        }
        Object revisionValue = get(object, "revision");
        int revision = revisionValue instanceof Number number ? number.intValue() : 1;
        Object kindValue = get(object, "kind");
        ArtifactKind kind;
        if (kindValue instanceof String text) {
            try {
                kind = ArtifactKind.fromText(text);
            } catch (IllegalArgumentException ignored) {
                kind = kindForClass(object.eClass().getName());
            }
        } else {
            kind = kindForClass(object.eClass().getName());
        }

        Map<String, Object> properties = new LinkedHashMap<>();
        Object propertiesValue = get(object, "properties");
        if (propertiesValue instanceof Map<?, ?> map) {
            map.forEach((key, value) -> properties.put(String.valueOf(key), value));
        }

        properties.putIfAbsent("statement", get(object, "statement"));
        properties.putIfAbsent("rationale", get(object, "rationale"));
        properties.putIfAbsent("requirementId", get(object, "requirementId"));
        properties.putIfAbsent("name", get(object, "name"));
        properties.putIfAbsent("entryPoint", get(object, "entryPoint"));
        properties.putIfAbsent("functionName", get(object, "functionName"));
        properties.putIfAbsent("target", get(object, "target"));
        properties.putIfAbsent("channel", get(object, "channel"));
        properties.putIfAbsent("protocol", get(object, "protocol"));
        properties.putIfAbsent("periodMs", get(object, "periodMs"));

        Object supersedesValue = get(object, "supersedes");
        List<String> supersedes = new ArrayList<>();
        if (supersedesValue instanceof List<?> list) {
            for (Object item : list) {
                supersedes.add(String.valueOf(item));
            }
        }

        return new Artifact(
            String.valueOf(id),
            kind,
            revision,
            properties,
            supersedes
        );
    }

    private ArtifactKind kindForClass(String className) {
        return switch (className) {
            case "StakeholderNeed" -> ArtifactKind.STAKEHOLDER_NEED;
            case "Requirement" -> ArtifactKind.REQUIREMENT;
            case "ArchitecturalElement" -> ArtifactKind.ARCHITECTURAL_ELEMENT;
            case "Interface" -> ArtifactKind.INTERFACE;
            case "Port" -> ArtifactKind.PORT;
            case "Connection" -> ArtifactKind.CONNECTION;
            case "BehaviorElement" -> ArtifactKind.BEHAVIOR_ELEMENT;
            case "Allocation" -> ArtifactKind.ALLOCATION;
            case "Deployment" -> ArtifactKind.DEPLOYMENT;
            case "Implementation" -> ArtifactKind.IMPLEMENTATION;
            case "VerificationPlan" -> ArtifactKind.VERIFICATION_PLAN;
            case "TestCase" -> ArtifactKind.COMPONENT_TEST;
            case "VerificationEvidence" -> ArtifactKind.VERIFICATION_EVIDENCE;
            case "FunctionCall" -> ArtifactKind.FUNCTION_CALL;
            case "Communication" -> ArtifactKind.COMMUNICATION;
            case "Schedule" -> ArtifactKind.SCHEDULE;
            default -> ArtifactKind.REQUIREMENT;
        };
    }

    private String className(ArtifactKind kind) {
        return switch (kind) {
            case STAKEHOLDER_NEED -> "StakeholderNeed";
            case REQUIREMENT -> "Requirement";
            case ARCHITECTURAL_ELEMENT -> "LifecycleElement";
            case INTERFACE -> "LifecycleElement";
            case PORT -> "LifecycleElement";
            case CONNECTION -> "LifecycleElement";
            case BEHAVIOR_ELEMENT -> "BehaviorElement";
            case ALLOCATION -> "LifecycleElement";
            case DEPLOYMENT -> "LifecycleElement";
            case IMPLEMENTATION -> "LifecycleElement";
            case VERIFICATION_PLAN -> "LifecycleElement";
            case COMPONENT_TEST, SCENARIO_TEST -> "LifecycleElement";
            case VERIFICATION_EVIDENCE -> "LifecycleElement";
            case FUNCTION_CALL -> "FunctionCall";
            case COMMUNICATION -> "Communication";
            case SCHEDULE -> "Schedule";
        };
    }

    private void set(EObject object, String feature, Object value) {
        if (value == null) {
            return;
        }
        try {
            EAttribute attribute = (EAttribute) object.eClass().getEStructuralFeature(feature);
            if (attribute == null) {
                return;
            }
            if (attribute.isMany() && value instanceof List<?> list) {
                @SuppressWarnings("unchecked")
                EList<Object> target = (EList<Object>) object.eGet(attribute);
                target.clear();
                target.addAll(list);
            } else if (attribute.isMany() && value instanceof String string) {
                @SuppressWarnings("unchecked")
                EList<Object> target = (EList<Object>) object.eGet(attribute);
                target.clear();
                target.add(string);
            } else {
                object.eSet(attribute, value);
            }
        } catch (RuntimeException ignored) {
        }
    }

    private Object get(EObject object, String feature) {
        var structural = object.eClass().getEStructuralFeature(feature);
        if (structural == null) {
            return null;
        }
        return object.eGet(structural);
    }

    private String string(Map<String, Object> properties, String key) {
        Object value = properties.get(key);
        return value == null ? "" : String.valueOf(value);
    }

    private List<String> list(Map<String, Object> properties, String key) {
        Object value = properties.get(key);
        if (value instanceof List<?> list) {
            List<String> result = new ArrayList<>();
            for (Object item : list) {
                result.add(String.valueOf(item));
            }
            return result;
        }
        return new ArrayList<>();
    }

    private String refId(String ref) {
        if (ref == null) {
            return "";
        }
        int at = ref.lastIndexOf('@');
        return at < 0 ? ref : ref.substring(0, at);
    }

    private int refRevision(String ref) {
        if (ref == null) {
            return 1;
        }
        int at = ref.lastIndexOf('@');
        if (at < 0) {
            return 1;
        }
        try {
            return Integer.parseInt(ref.substring(at + 1));
        } catch (NumberFormatException ignored) {
            return 1;
        }
    }
}
