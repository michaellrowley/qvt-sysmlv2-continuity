package org.github.michaellrowley.sysmlqvt.template;

import org.github.michaellrowley.sysmlqvt.text.SysMLParser;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SysMLTemplateLibraryTest {
    @Test
    void batteryTemplateContainsLifecycleArtifacts() {
        String text = new SysMLTemplateLibrary().batteryLifecycle();
        SysMLParser.ParseResult result =
            new SysMLParser().parse("battery-template", text);

        assertTrue(text.contains("stakeholder need N-BATT-THERMAL"));
        assertTrue(text.contains("behavior B-BATT-THERMAL-CONTROL"));
        assertEquals(12, result.model().allArtifacts().size());
        assertTrue(
            result.diagnostics().stream()
                .noneMatch(diagnostic -> "error".equals(diagnostic.severity()))
        );
    }

    @Test
    void genericTemplateHasNeedAndRequirement() {
        String text = new SysMLTemplateLibrary().genericNeed();

        assertTrue(text.contains("stakeholder need N-SYSTEM"));
        assertTrue(text.contains("requirement R-SYSTEM"));
        assertTrue(text.contains("behavior B-SYSTEM"));
    }
}
