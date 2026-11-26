package org.github.michaellrowley.sysmlqvt.qvt;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

class EclipseQvtEngineTest {
    @TempDir
    Path tempDir;

    @Test
    void executesValidQVToTransformation() throws Exception {
        Path transformation = tempDir.resolve("Lifecycle.qvto");
        Files.writeString(
            transformation,
            """
modeltype SYSML uses sysml('urn:sysml:v2:lite');
modeltype CONTINUITY uses continuity('urn:qvt:continuity');

transformation Lifecycle(
  inout sysml : SYSML,
  inout continuity : CONTINUITY
);

main() {
  sysml.objects()[StakeholderNeed]->forEach(need) {
    need.map developIntent();
  };
}

mapping StakeholderNeed::developIntent() : Requirement {
  id := self.requirementId;
  revision := self.revision + 1;
  statement := self.statement;
  rationale := self.rationale;
  acceptanceCriteria := self.acceptanceCriteria;
  sourceNeedId := self.id;
  kind := 'requirement';
  properties := self.properties;
}
"""
        );

        SysMLModel model = new SysMLModel();
        model.addArtifact(new Artifact(
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

        QvtResult result =
            new EclipseQvtEngine().execute(model, transformation);

        assertTrue(result.successful(), result.diagnostics().toString());
        assertEquals("R-SYSTEM", model.latest("R-SYSTEM").id());
    }
}
