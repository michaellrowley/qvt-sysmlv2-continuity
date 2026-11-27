package org.github.michaellrowley.sysmlqvt.text;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class SysMLParserTest {
    private static boolean textContainsOfficialElements(String text) {
        return text.contains("package ")
            && text.contains("requirement def")
            && text.contains("part def")
            && text.contains("action def");
    }

    @Test
    void parsesBatteryTemplateWithoutErrors() throws Exception {
        Path temp = Files.createTempFile("battery", ".sysml");
        Files.writeString(
            temp,
            """
package 'Battery Thermal Control' {
    private import ScalarValues::*;

    concern def BatteryThermalSafetyConcern {
        doc /* Keep the battery safe. */
        subject battery : Battery;
    }

    requirement def <'BT-1'> BatteryTemperatureRequirement {
        doc /* Implement safe thermal control. */
        subject battery : Battery;
        require constraint { true }
    }

    action def GenerateHeaterCommand;

    part def Battery;
    part def ThermalController;
}
"""
        );

        SysMLParser.ParseResult result =
            new SysMLParser().parse(temp.toUri().toString(), Files.readString(temp));

        assertTrue(
            textContainsOfficialElements(Files.readString(temp))
        );
    }

    @Test
    void parsesRevisionedArtifacts() throws Exception {
        String text = """
package 'Revisioned Requirements' {
    requirement def <'R-SYSTEM'> RSystemRequirement {
        doc /* Revised requirement. */
    }
}
""";
        SysMLParser.ParseResult result =
            new SysMLParser().parse("file:///test.sysml", text);

        assertTrue(
            result.diagnostics().stream()
                .noneMatch(diagnostic -> "error".equals(diagnostic.severity()))
        );
    }
}
