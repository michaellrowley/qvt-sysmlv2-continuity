package org.github.michaellrowley.sysmlqvt.text;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SysMLParserTest {
    @Test
    void parsesBatteryTemplateWithoutErrors() throws Exception {
        Path temp = Files.createTempFile("battery", ".sysml");
        Files.writeString(
            temp,
            """
package battery;

stakeholder need N-BATT-THERMAL {
  statement = "Keep the battery safe.";
  acceptanceCriteria = ["No unsafe heater operation."];
}

requirement R-BATT-THERMAL {
  statement = "Implement safe thermal control.";
}

behavior B-BATT-THERMAL-CONTROL {
  entryPoint = "generate_heater_command";
  states = ["HEAT", "SAFE_OFF"];
}

part def ThermalController;
"""
        );

        SysMLParser.ParseResult result =
            new SysMLParser().parse(temp.toUri().toString(), Files.readString(temp));

        assertTrue(
            result.diagnostics().stream()
                .noneMatch(diagnostic -> "error".equals(diagnostic.severity()))
        );
        assertEquals(4, result.model().allArtifacts().size());
        Artifact need = result.model().latest("N-BATT-THERMAL");
        assertEquals(ArtifactKind.STAKEHOLDER_NEED, need.kind());
        assertEquals(
            "Keep the battery safe.",
            need.properties().get("statement")
        );
    }

    @Test
    void parsesRevisionedArtifacts() throws Exception {
        String text = """
requirement R-SYSTEM {
  revision = 2;
  statement = "Revised requirement.";
  supersedes = ["R-SYSTEM@1"];
}
""";
        SysMLParser.ParseResult result =
            new SysMLParser().parse("file:///test.sysml", text);

        Artifact requirement = result.model().latest("R-SYSTEM");
        assertEquals(2, requirement.revision());
        assertEquals(
            "R-SYSTEM@1",
            requirement.supersedes().get(0)
        );
    }
}
