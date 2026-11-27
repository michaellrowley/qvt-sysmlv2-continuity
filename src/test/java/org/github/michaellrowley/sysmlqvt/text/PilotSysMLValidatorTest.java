package org.github.michaellrowley.sysmlqvt.text;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeAll;
import java.nio.file.Files;
import java.nio.file.Path;
import java.io.BufferedReader;
import java.io.InputStreamReader;

import static org.junit.jupiter.api.Assertions.assertTrue;

class PilotSysMLValidatorTest {
    private static Path pilotLibrary() {
        return Path.of(
            System.getProperty(
                "sysml.pilot.library",
                ".build/pilot/SysML-v2-Pilot-Implementation/sysml.library"
            )
        );
    }

    private static String validate(Path file) throws Exception {
        Path jar = Path.of(
            "lib/org.omg.sysml.interactive-0.64.0-SNAPSHOT-all.jar"
        ).toAbsolutePath();
        assertTrue(Files.isRegularFile(jar), "Pilot interactive jar missing: " + jar);

        Path library = pilotLibrary().toAbsolutePath();
        assertTrue(
            Files.isDirectory(library),
            "Pilot library directory missing: " + library
        );

        Process process = new ProcessBuilder(
            "java",
            "-Djava.awt.headless=true",
            "-cp",
            jar.toString(),
            "org.omg.sysml.interactive.profiler.SysMLInteractiveParsingProfiler",
            library.toString(),
            file.toString()
        ).redirectErrorStream(true).start();

        StringBuilder output = new StringBuilder();
        try (BufferedReader reader =
                 new BufferedReader(
                     new InputStreamReader(process.getInputStream())
                 )) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append('\n');
            }
        }
        process.waitFor();
        return output.toString();
    }

    @Test
    void batteryExampleHasNoPilotSyntaxOrSemanticErrors() throws Exception {
        Path example = Path.of(
            "examples/battery_lifecycle.sysml"
        ).toAbsolutePath();
        String output = validate(example);

        assertTrue(
            !output.contains("ERROR:")
                && !output.contains("Syntax error")
                && !output.contains("semantic error"),
            "Pilot validation output:\n" + output
        );
    }

    @Test
    void pilotRejectsInvalidStakeholderDialect() throws Exception {
        Path invalid = Files.createTempFile("invalid-sysml", ".sysml");
        Files.writeString(
            invalid,
            "package battery;\nstakeholder need N-BATT-THERMAL;\n"
        );
        String output = validate(invalid);

        assertTrue(
            output.contains("ERROR:")
                || output.contains("Syntax")
                || output.contains("missing EOF"),
            "Pilot should reject the custom stakeholder dialect:\n" + output
        );
    }
}
