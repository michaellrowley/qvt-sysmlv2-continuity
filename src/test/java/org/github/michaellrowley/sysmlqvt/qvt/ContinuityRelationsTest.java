package org.github.michaellrowley.sysmlqvt.qvt;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;
import org.github.michaellrowley.sysmlqvt.model.TraceKind;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ContinuityRelationsTest {
    @Test
    void createsOriginRealizationAndVerificationTraces() {
        SysMLModel model = new SysMLModel();
        Artifact need = model.addArtifact(new Artifact(
            "N-SYSTEM",
            ArtifactKind.STAKEHOLDER_NEED,
            1,
            Map.of("requirementId", "R-SYSTEM"),
            java.util.List.of()
        ));
        Artifact requirement = model.addArtifact(new Artifact(
            "R-SYSTEM",
            ArtifactKind.REQUIREMENT,
            1,
            Map.of("statement", "Safe behavior"),
            java.util.List.of()
        ));
        Artifact architecture = model.addArtifact(new Artifact(
            "A-SYSTEM",
            ArtifactKind.ARCHITECTURAL_ELEMENT,
            1,
            Map.of("requirement", "R-SYSTEM@1"),
            java.util.List.of()
        ));
        Artifact behavior = model.addArtifact(new Artifact(
            "B-SYSTEM",
            ArtifactKind.BEHAVIOR_ELEMENT,
            1,
            Map.of("entryPoint", "main"),
            java.util.List.of()
        ));
        Artifact evidence = model.addArtifact(new Artifact(
            "E-SYSTEM",
            ArtifactKind.VERIFICATION_EVIDENCE,
            1,
            Map.of("result", "pass", "behavior", "B-SYSTEM@1"),
            java.util.List.of()
        ));

        new ContinuityRelations().enforce(model);

        assertTrue(
            model.activeTraces().stream()
                .anyMatch(trace -> trace.kind() == TraceKind.ORIGIN
                    && trace.source().equals(need.ref())
                    && trace.target().equals(requirement.ref()))
        );
        assertTrue(
            model.activeTraces().stream()
                .anyMatch(trace -> trace.kind() == TraceKind.REALIZES
                    && trace.source().equals(requirement.ref())
                    && trace.target().equals(architecture.ref()))
        );
        assertTrue(
            model.activeTraces().stream()
                .anyMatch(trace -> trace.kind() == TraceKind.VERIFIES
                    && trace.source().equals(behavior.ref())
                    && trace.target().equals(evidence.ref()))
        );
    }
}
