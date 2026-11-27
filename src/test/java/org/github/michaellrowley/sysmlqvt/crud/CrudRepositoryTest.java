package org.github.michaellrowley.sysmlqvt.crud;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CrudRepositoryTest {
    @TempDir
    Path tempDir;

    @Test
    void createsSystemDomainAndSubsystemThenCppEntrypoint() throws Exception {
        CrudRepository repository =
            new CrudRepository(tempDir.resolve("workspace"));

        CrudResult domain = repository.execute(new CrudRequest(
            CrudOperator.CREATE,
            "system-domain",
            EntityKind.DOMAIN,
            "DOMAIN-BMS",
            null,
            "Battery Management System",
            Map.of("mission", "Manage battery safety"),
            false
        ));
        CrudResult subsystem = repository.execute(new CrudRequest(
            CrudOperator.CREATE,
            "system-architecture",
            EntityKind.SUBSYSTEM,
            "SUB-THERMAL",
            "DOMAIN-BMS",
            "Battery Thermal Control",
            Map.of("domain", "DOMAIN-BMS"),
            false
        ));
        CrudResult requirement = repository.execute(new CrudRequest(
            CrudOperator.CREATE,
            "system-requirements",
            EntityKind.REQUIREMENT,
            "REQ-TEMP-RANGE",
            "SUB-THERMAL",
            "Temperature range",
            Map.of(
                "statement",
                "Keep battery temperature between 20 C and 30 C.",
                "verificationMethod",
                "test"
            ),
            false
        ));
        CrudResult entrypoint = repository.execute(new CrudRequest(
            CrudOperator.CREATE,
            "software-implementation",
            EntityKind.CPP_IMPLEMENTATION,
            "CPP-GENERATE-HEATER-COMMAND",
            "SUB-THERMAL",
            "Generate heater command",
            Map.of(
                "language", "C++",
                "languageStandard", "C++20",
                "header", "generate_heater_command.hpp",
                "source", "generate_heater_command.cpp",
                "signature",
                "HeaterCommand generate_heater_command(double temperatureC, bool sensorValid)"
            ),
            false
        ));

        assertTrue(domain.successful());
        assertTrue(subsystem.successful());
        assertTrue(requirement.successful());
        assertTrue(entrypoint.successful());
        List<String> cppPaths = entrypoint.outputPaths();
        assertEquals(3, cppPaths.size());
        assertTrue(Files.exists(Path.of(cppPaths.get(0))));
        assertTrue(Files.exists(Path.of(cppPaths.get(1))));
        assertTrue(Files.exists(Path.of(cppPaths.get(2))));

        String header = Files.readString(Path.of(cppPaths.get(1)));
        String source = Files.readString(Path.of(cppPaths.get(2)));
        assertTrue(header.contains("class"));
        assertTrue(header.contains("int run"));
        assertTrue(source.contains("#include"));
        assertTrue(source.contains("domain entrypoint"));
    }

    @Test
    void requestsUpdatesAndDeletesEntities() {
        CrudRepository repository =
            new CrudRepository(tempDir.resolve("workspace"));
        repository.execute(new CrudRequest(
            CrudOperator.CREATE,
            "system-domain",
            EntityKind.DOMAIN,
            "DOMAIN-FLIGHT",
            null,
            "Flight Domain",
            Map.of("mission", "Navigation"),
            false
        ));

        CrudResult requested = repository.execute(new CrudRequest(
            CrudOperator.REQUEST,
            "system-domain",
            EntityKind.DOMAIN,
            "DOMAIN-FLIGHT",
            null,
            null,
            Map.of(),
            false
        ));
        assertEquals(1, requested.entities().size());

        CrudResult updated = repository.execute(new CrudRequest(
            CrudOperator.UPDATE,
            "system-domain",
            EntityKind.DOMAIN,
            "DOMAIN-FLIGHT",
            null,
            "Flight and Navigation Domain",
            Map.of("mission", "Navigation and flight safety"),
            false
        ));
        assertEquals("Flight and Navigation Domain", updated.entity().name());
        assertEquals(2, updated.entity().revision());

        CrudResult deleted = repository.execute(new CrudRequest(
            CrudOperator.DELETE,
            "system-domain",
            EntityKind.DOMAIN,
            "DOMAIN-FLIGHT",
            null,
            null,
            Map.of(),
            false
        ));
        assertTrue(deleted.entity().deleted());
        assertEquals(3, deleted.entity().revision());

        CrudResult withoutDeleted = repository.execute(new CrudRequest(
            CrudOperator.REQUEST,
            "system-domain",
            EntityKind.DOMAIN,
            null,
            null,
            null,
            Map.of(),
            false
        ));
        assertFalse(
            withoutDeleted.entities().stream()
                .anyMatch(entity -> entity.deleted())
        );
    }
}
