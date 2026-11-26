package org.github.michaellrowley.sysmlqvt.qvt;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.Baseline;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;
import org.github.michaellrowley.sysmlqvt.model.TraceKind;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LifecycleEngineTest {
    @Test
    void executesFullOperationalScope() {
        SysMLModel model = new SysMLModel();
        LifecycleEngine engine = new LifecycleEngine(model);

        Artifact need = model.addArtifact(new Artifact(
            "N-SYSTEM",
            ArtifactKind.STAKEHOLDER_NEED,
            1,
            Map.of(
                "requirementId", "R-SYSTEM",
                "statement", "Create a safe system.",
                "rationale", "Safety.",
                "acceptanceCriteria", List.of("Pass verification.")
            ),
            List.of()
        ));
        Artifact requirement = engine.developIntent(need, "R-SYSTEM");

        List<Artifact> architecture = engine.realizeArchitecture(
            requirement,
            List.of(
                Map.of("id", "A-CONTROLLER", "name", "Controller"),
                Map.of("id", "A-SENSOR", "name", "Sensor")
            ),
            Map.of()
        );
        Artifact interfaceArtifact = engine.realizeInterface(
            requirement,
            architecture.get(0),
            "IF-CONTROLLER",
            Map.of("name", "ControllerInterface", "protocol", "CAN")
        );
        Artifact sourcePort = engine.realizePort(
            interfaceArtifact,
            Map.of("id", "P-IN", "name", "command_in", "direction", "in"),
            "P-IN"
        );
        Artifact targetPort = engine.realizePort(
            interfaceArtifact,
            Map.of("id", "P-OUT", "name", "status_out", "direction", "out"),
            "P-OUT"
        );
        engine.connectPorts(
            sourcePort,
            targetPort,
            "CON-CONTROLLER",
            Map.of("transport", "CAN")
        );

        Artifact behavior = engine.realizeBehavior(
            requirement,
            architecture,
            "B-CONTROLLER",
            Map.of(
                "kind", "state_machine",
                "entryPoint", "run",
                "states", List.of("RUNNING", "FAULT")
            )
        );
        engine.configureFunctionCall(
            behavior,
            Map.of("id", "CALL-RUN", "functionName", "run")
        );
        engine.configureCommunication(
            behavior,
            Map.of(
                "id", "COMM-STATUS",
                "direction", "out",
                "channel", "system.status"
            )
        );
        engine.configureSchedule(
            behavior,
            Map.of("id", "SCH-RUN", "kind", "cyclic", "periodMs", 10)
        );
        Artifact allocation = engine.allocateBehavior(
            behavior,
            architecture.get(0),
            "AL-CONTROLLER",
            Map.of("kind", "behavior")
        );
        Artifact deployment = engine.deployComponent(
            behavior,
            architecture.get(0),
            "DP-CONTROLLER",
            Map.of("environment", "RTOS", "runtime", "embedded")
        );
        Artifact implementation = engine.generateImplementation(
            behavior,
            "C-CONTROLLER",
            Map.of(
                "targetLanguage", "C",
                "targetPlatform", "RTOS",
                "entryPoint", "run"
            )
        );
        Artifact plan = engine.planVerification(
            requirement,
            behavior,
            implementation,
            "VP-CONTROLLER",
            Map.of(
                "strategy", "component-and-scenario",
                "testLevels", List.of("component", "scenario"),
                "environments", List.of("HIL")
            )
        );
        Artifact evidence = engine.verifySatisfaction(
            requirement,
            behavior,
            implementation,
            plan,
            "E-CONTROLLER",
            "pass",
            "All verification passed.",
            List.of(Map.of("id", "TC-C-RUN", "purpose", "Run component")),
            List.of(Map.of("id", "TC-S-RUN", "purpose", "Run scenario")),
            Map.of("kind", "HIL", "target", "RTOS")
        );

        LifecycleEngine.ImpactPlan impact =
            engine.propagateChange(requirement);
        LifecycleEngine.Reconciliation reconciliation =
            engine.reconcileViews(requirement, requirement);
        Baseline baseline = engine.baselineThread(requirement);
        List<String> diagnostics =
            engine.checkContinuity(requirement, true);

        assertEquals("consistent", reconciliation.status());
        assertEquals(requirement.ref(), impact.root());
        assertTrue(baseline.artifactRefs().contains(requirement.ref()));
        assertTrue(diagnostics.isEmpty());
        assertTrue(model.latestArtifacts().stream()
            .anyMatch(artifact -> artifact.kind() == ArtifactKind.ALLOCATION
                && artifact.id().equals(allocation.id())));
        assertTrue(model.latestArtifacts().stream()
            .anyMatch(artifact -> artifact.kind() == ArtifactKind.DEPLOYMENT
                && artifact.id().equals(deployment.id())));
        assertTrue(model.latestArtifacts().stream()
            .anyMatch(artifact -> artifact.kind() == ArtifactKind.IMPLEMENTATION
                && artifact.id().equals(implementation.id())));
        assertTrue(model.latestArtifacts().stream()
            .anyMatch(artifact -> artifact.kind() == ArtifactKind.VERIFICATION_EVIDENCE
                && artifact.id().equals(evidence.id())));

        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.ORIGIN));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.REALIZES));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.EXPOSES));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.CONNECTS));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.CALLS));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.PUBLISHES));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.SCHEDULES));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.ALLOCATES));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.DEPLOYED_TO));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.GENERATES));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.COVERS));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.EXECUTES));
        assertTrue(model.activeTraces().stream()
            .anyMatch(trace -> trace.kind() == TraceKind.VERIFIES));
    }
}
