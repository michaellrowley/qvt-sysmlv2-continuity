package org.github.michaellrowley.sysmlqvt.template;

import org.github.michaellrowley.sysmlqvt.text.SysMLParser;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class SysMLTemplateLibraryTest {
    @Test
    void batteryTemplateContainsLifecycleArtifacts() {
        String text = new SysMLTemplateLibrary().batteryLifecycle();
        SysMLParser.ParseResult result =
            new SysMLParser().parse("battery-template", text);

        assertTrue(text.contains("concern def BatteryThermalSafetyConcern"));
        assertTrue(text.contains("requirement def <'BT-1'> BatteryTemperatureRequirement"));
        assertTrue(text.contains("part def ThermalController"));
        assertTrue(result.model().allArtifacts().size() >= 5);
        assertTrue(
            result.diagnostics().stream()
                .noneMatch(diagnostic -> "error".equals(diagnostic.severity()))
        );
    }

    @Test
    void genericTemplateHasNeedAndRequirement() {
        String text = new SysMLTemplateLibrary().genericNeed();

        assertTrue(text.contains("concern def SystemNeedConcern"));
        assertTrue(text.contains("requirement def <'R-SYSTEM'> SystemRequirement"));
        assertTrue(text.contains("part def System"));
    }
}
