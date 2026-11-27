package org.github.michaellrowley.sysmlqvt.qvt;

import org.eclipse.emf.ecore.EAttribute;
import org.eclipse.emf.ecore.EClass;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EReference;
import org.eclipse.emf.ecore.EcoreFactory;
import org.eclipse.emf.ecore.EcorePackage;

public final class EcoreMetamodel {
    public static final String SYSML_NS = "urn:sysml:v2:lite";
    public static final String CONTINUITY_NS = "urn:qvt:continuity";

    private EcoreMetamodel() {
    }

    public static EPackage sysmlPackage() {
        EPackage existing = EPackage.Registry.INSTANCE.getEPackage(SYSML_NS);
        if (existing != null) {
            return existing;
        }

        EPackage pkg = EcoreFactory.eINSTANCE.createEPackage();
        pkg.setName("SYSML");
        pkg.setNsPrefix("sysml");
        pkg.setNsURI(SYSML_NS);

        EClass lifecycle = class_(pkg, "LifecycleElement");
        string(lifecycle, "id");
        integer(lifecycle, "revision");
        string(lifecycle, "kind");
        javaObject(lifecycle, "properties");
        stringList(lifecycle, "supersedes");

        EClass need = class_(pkg, "StakeholderNeed");
        need.getESuperTypes().add(lifecycle);
        string(need, "statement");
        string(need, "rationale");
        stringList(need, "acceptanceCriteria");
        string(need, "requirementId");

        EClass requirement = class_(pkg, "Requirement");
        requirement.getESuperTypes().add(lifecycle);
        string(requirement, "statement");
        string(requirement, "rationale");
        stringList(requirement, "acceptanceCriteria");
        string(requirement, "sourceNeedId");

        EClass architecture = class_(pkg, "ArchitecturalElement");
        architecture.getESuperTypes().add(lifecycle);
        string(architecture, "name");
        string(architecture, "requirementId");
        integer(architecture, "requirementRevision");

        EClass iface = class_(pkg, "Interface");
        iface.getESuperTypes().add(lifecycle);
        string(iface, "name");
        string(iface, "protocol");
        javaObject(iface, "operations");
        javaObject(iface, "ports");

        EClass port = class_(pkg, "Port");
        port.getESuperTypes().add(lifecycle);
        string(port, "name");
        string(port, "direction");
        string(port, "kind");
        string(port, "interfaceId");
        string(port, "protocol");
        javaObject(port, "binding");

        EClass connection = class_(pkg, "Connection");
        connection.getESuperTypes().add(lifecycle);
        string(connection, "sourcePortId");
        string(connection, "targetPortId");
        string(connection, "transport");
        javaObject(connection, "qos");

        EClass behavior = class_(pkg, "BehaviorElement");
        behavior.getESuperTypes().add(lifecycle);
        string(behavior, "behaviorKind");
        string(behavior, "entryPoint");
        string(behavior, "initialState");
        stringList(behavior, "states");
        javaObject(behavior, "parameters");
        javaObject(behavior, "variables");
        javaObject(behavior, "results");
        javaObject(behavior, "operations");
        javaObject(behavior, "functionCalls");
        javaObject(behavior, "communications");
        javaObject(behavior, "schedules");
        javaObject(behavior, "transitions");
        javaObject(behavior, "actions");
        string(behavior, "concurrency");

        EClass functionCall = class_(pkg, "FunctionCall");
        functionCall.getESuperTypes().add(lifecycle);
        string(functionCall, "functionName");
        string(functionCall, "target");
        javaObject(functionCall, "arguments");
        string(functionCall, "returnBinding");
        bool(functionCall, "synchronous");
        integer(functionCall, "timeoutMs");

        EClass communication = class_(pkg, "Communication");
        communication.getESuperTypes().add(lifecycle);
        string(communication, "communicationKind");
        string(communication, "direction");
        string(communication, "channel");
        string(communication, "endpoint");
        string(communication, "protocol");
        string(communication, "payloadType");
        javaObject(communication, "qos");
        integer(communication, "timeoutMs");
        bool(communication, "reliable");

        EClass schedule = class_(pkg, "Schedule");
        schedule.getESuperTypes().add(lifecycle);
        string(schedule, "scheduleKind");
        integer(schedule, "periodMs");
        integer(schedule, "deadlineMs");
        integer(schedule, "wcetMs");
        integer(schedule, "priority");
        integer(schedule, "jitterMs");
        string(schedule, "entryPoint");

        EClass allocation = class_(pkg, "Allocation");
        allocation.getESuperTypes().add(lifecycle);
        string(allocation, "sourceRef");
        string(allocation, "targetRef");

        EClass deployment = class_(pkg, "Deployment");
        deployment.getESuperTypes().add(lifecycle);
        string(deployment, "componentRef");
        string(deployment, "targetRef");
        string(deployment, "environment");
        string(deployment, "runtime");
        javaObject(deployment, "resources");

        EClass implementation = class_(pkg, "Implementation");
        implementation.getESuperTypes().add(lifecycle);
        string(implementation, "sourceBehavior");
        integer(implementation, "sourceBehaviorRevision");
        string(implementation, "language");
        string(implementation, "targetPlatform");
        string(implementation, "entryPoint");
        string(implementation, "buildSystem");
        string(implementation, "sourceFormat");
        javaObject(implementation, "behaviorModel");
        javaObject(implementation, "codeGeneration");

        EClass plan = class_(pkg, "VerificationPlan");
        plan.getESuperTypes().add(lifecycle);
        string(plan, "requirementRef");
        string(plan, "behaviorRef");
        string(plan, "implementationRef");
        string(plan, "strategy");
        stringList(plan, "testLevels");
        stringList(plan, "environments");

        EClass testCase = class_(pkg, "TestCase");
        testCase.getESuperTypes().add(lifecycle);
        string(testCase, "purpose");
        string(testCase, "result");
        string(testCase, "requirementId");
        integer(testCase, "requirementRevision");
        string(testCase, "behaviorId");
        integer(testCase, "behaviorRevision");
        string(testCase, "implementationId");
        integer(testCase, "implementationRevision");
        javaObject(testCase, "executionEnvironment");

        EClass evidence = class_(pkg, "VerificationEvidence");
        evidence.getESuperTypes().add(lifecycle);
        string(evidence, "requirementRef");
        string(evidence, "behaviorRef");
        string(evidence, "implementationRef");
        string(evidence, "verificationPlan");
        string(evidence, "result");
        string(evidence, "summary");
        javaObject(evidence, "executionEnvironment");

        EClass architectureSpec = class_(pkg, "ArchitectureElementSpec");
        string(architectureSpec, "id");
        string(architectureSpec, "name");
        javaObject(architectureSpec, "properties");

        EClass interfaceSpec = class_(pkg, "InterfaceSpec");
        string(interfaceSpec, "id");
        string(interfaceSpec, "name");
        string(interfaceSpec, "kind");
        string(interfaceSpec, "protocol");
        javaObject(interfaceSpec, "operations");
        javaObject(interfaceSpec, "ports");
        javaObject(interfaceSpec, "properties");

        EClass portSpec = class_(pkg, "PortSpec");
        string(portSpec, "id");
        string(portSpec, "name");
        string(portSpec, "direction");
        string(portSpec, "kind");
        string(portSpec, "interfaceId");
        string(portSpec, "protocol");
        javaObject(portSpec, "binding");
        javaObject(portSpec, "properties");

        EClass connectionSpec = class_(pkg, "ConnectionSpec");
        string(connectionSpec, "id");
        string(connectionSpec, "transport");
        javaObject(connectionSpec, "qos");
        javaObject(connectionSpec, "properties");

        EClass functionCallSpec = class_(pkg, "FunctionCallSpec");
        string(functionCallSpec, "id");
        string(functionCallSpec, "functionName");
        string(functionCallSpec, "target");
        javaObject(functionCallSpec, "arguments");
        string(functionCallSpec, "returnBinding");
        bool(functionCallSpec, "synchronous");
        integer(functionCallSpec, "timeoutMs");
        string(functionCallSpec, "precondition");
        string(functionCallSpec, "postcondition");
        javaObject(functionCallSpec, "properties");

        EClass communicationSpec = class_(pkg, "CommunicationSpec");
        string(communicationSpec, "id");
        string(communicationSpec, "kind");
        string(communicationSpec, "direction");
        string(communicationSpec, "channel");
        string(communicationSpec, "endpoint");
        string(communicationSpec, "protocol");
        string(communicationSpec, "operation");
        string(communicationSpec, "payloadType");
        javaObject(communicationSpec, "payloadMapping");
        javaObject(communicationSpec, "qos");
        integer(communicationSpec, "timeoutMs");
        bool(communicationSpec, "reliable");
        javaObject(communicationSpec, "properties");

        EClass scheduleSpec = class_(pkg, "ScheduleSpec");
        string(scheduleSpec, "id");
        string(scheduleSpec, "kind");
        integer(scheduleSpec, "periodMs");
        integer(scheduleSpec, "startOffsetMs");
        integer(scheduleSpec, "deadlineMs");
        integer(scheduleSpec, "wcetMs");
        integer(scheduleSpec, "priority");
        integer(scheduleSpec, "jitterMs");
        string(scheduleSpec, "entryPoint");
        string(scheduleSpec, "trigger");
        javaObject(scheduleSpec, "properties");

        EClass allocationSpec = class_(pkg, "AllocationSpec");
        string(allocationSpec, "id");
        string(allocationSpec, "kind");
        javaObject(allocationSpec, "properties");

        EClass deploymentSpec = class_(pkg, "DeploymentSpec");
        string(deploymentSpec, "id");
        string(deploymentSpec, "environment");
        string(deploymentSpec, "runtime");
        javaObject(deploymentSpec, "resources");
        javaObject(deploymentSpec, "properties");

        EClass behaviorProperties = class_(pkg, "BehaviorProperties");
        string(behaviorProperties, "kind");
        string(behaviorProperties, "entryPoint");
        string(behaviorProperties, "initialState");
        stringList(behaviorProperties, "states");
        javaObject(behaviorProperties, "parameters");
        javaObject(behaviorProperties, "variables");
        javaObject(behaviorProperties, "results");
        javaObject(behaviorProperties, "operations");
        javaObject(behaviorProperties, "functionCalls");
        javaObject(behaviorProperties, "communications");
        javaObject(behaviorProperties, "schedules");
        javaObject(behaviorProperties, "transitions");
        javaObject(behaviorProperties, "actions");
        string(behaviorProperties, "concurrency");

        EClass codeGenerationSpec = class_(pkg, "CodeGenerationSpec");
        string(codeGenerationSpec, "targetLanguage");
        string(codeGenerationSpec, "targetPlatform");
        string(codeGenerationSpec, "entryPoint");
        string(codeGenerationSpec, "buildSystem");
        string(codeGenerationSpec, "sourceFormat");
        javaObject(codeGenerationSpec, "properties");

        EClass verificationPlanSpec = class_(pkg, "VerificationPlanSpec");
        string(verificationPlanSpec, "id");
        string(verificationPlanSpec, "strategy");
        stringList(verificationPlanSpec, "testLevels");
        stringList(verificationPlanSpec, "environments");
        javaObject(verificationPlanSpec, "properties");

        EClass executionEnvironment = class_(pkg, "ExecutionEnvironment");
        string(executionEnvironment, "kind");
        string(executionEnvironment, "target");
        javaObject(executionEnvironment, "properties");

        EPackage.Registry.INSTANCE.put(SYSML_NS, pkg);
        EPackage.Registry.INSTANCE.put("SYSML", pkg);
        EPackage.Registry.INSTANCE.put("sysml", pkg);
        return pkg;
    }

    public static EPackage continuityPackage() {
        EPackage existing = EPackage.Registry.INSTANCE.getEPackage(CONTINUITY_NS);
        if (existing != null) {
            return existing;
        }

        EPackage pkg = EcoreFactory.eINSTANCE.createEPackage();
        pkg.setName("CONTINUITY");
        pkg.setNsPrefix("continuity");
        pkg.setNsURI(CONTINUITY_NS);

        EClass trace = class_(pkg, "TraceLink");
        string(trace, "kind");
        string(trace, "sourceId");
        integer(trace, "sourceRevision");
        string(trace, "targetId");
        integer(trace, "targetRevision");
        string(trace, "status");
        string(trace, "derivedBy");

        EClass impact = class_(pkg, "ImpactPlan");
        string(impact, "root");
        stringList(impact, "impacted");
        stringList(impact, "invalidatedEvidence");
        stringList(impact, "invalidatedArtifacts");

        EClass reconciliation = class_(pkg, "Reconciliation");
        string(reconciliation, "status");
        stringList(reconciliation, "conflicts");

        EClass baseline = class_(pkg, "Baseline");
        string(baseline, "id");
        string(baseline, "requirement");
        stringList(baseline, "artifacts");
        stringList(baseline, "traceKeys");
        string(baseline, "contentHash");

        EPackage.Registry.INSTANCE.put(CONTINUITY_NS, pkg);
        EPackage.Registry.INSTANCE.put("CONTINUITY", pkg);
        EPackage.Registry.INSTANCE.put("continuity", pkg);
        return pkg;
    }

    private static EClass class_(EPackage pkg, String name) {
        EClass clazz = EcoreFactory.eINSTANCE.createEClass();
        clazz.setName(name);
        pkg.getEClassifiers().add(clazz);
        return clazz;
    }

    private static EAttribute string(EClass clazz, String name) {
        return attribute(clazz, name, EcorePackage.Literals.ESTRING, 1, 1);
    }

    private static EAttribute integer(EClass clazz, String name) {
        return attribute(clazz, name, EcorePackage.Literals.EINT, 1, 1);
    }

    private static EAttribute bool(EClass clazz, String name) {
        return attribute(clazz, name, EcorePackage.Literals.EBOOLEAN, 1, 1);
    }

    private static EAttribute javaObject(EClass clazz, String name) {
        return attribute(clazz, name, EcorePackage.Literals.EJAVA_OBJECT, 1, 1);
    }

    private static EAttribute stringList(EClass clazz, String name) {
        return attribute(clazz, name, EcorePackage.Literals.ESTRING, 0, -1);
    }

    private static EAttribute attribute(
        EClass clazz,
        String name,
        org.eclipse.emf.ecore.EDataType type,
        int lower,
        int upper
    ) {
        EAttribute attribute = EcoreFactory.eINSTANCE.createEAttribute();
        attribute.setName(name);
        attribute.setEType(type);
        attribute.setLowerBound(lower);
        attribute.setUpperBound(upper);
        clazz.getEStructuralFeatures().add(attribute);
        return attribute;
    }

    public static EClass classFor(EPackage pkg, String name) {
        return (EClass) pkg.getEClassifier(name);
    }
}
