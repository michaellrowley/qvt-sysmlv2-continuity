package org.github.michaellrowley.sysmlqvt;

import org.eclipse.lsp4j.jsonrpc.Launcher;
import org.eclipse.lsp4j.launch.LSPLauncher;
import org.eclipse.lsp4j.services.LanguageClient;
import org.github.michaellrowley.sysmlqvt.lsp.SysMLLanguageServer;
import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;
import org.github.michaellrowley.sysmlqvt.qvt.ContinuityRelations;
import org.github.michaellrowley.sysmlqvt.qvt.EclipseQvtEngine;
import org.github.michaellrowley.sysmlqvt.qvt.QvtResult;
import org.github.michaellrowley.sysmlqvt.template.SysMLTemplateLibrary;
import org.github.michaellrowley.sysmlqvt.text.SysMLDiagnostic;
import org.github.michaellrowley.sysmlqvt.text.SysMLParser;
import org.github.michaellrowley.sysmlqvt.text.SysMLPrinter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class Main {
    private Main() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            printUsage();
            return;
        }

        switch (args[0]) {
            case "lsp" -> runLsp();
            case "template" -> runTemplate(args);
            case "validate" -> runValidate(args);
            case "qvt" -> runQvt(args);
            case "relations" -> runRelations(args);
            case "help", "--help", "-h" -> printUsage();
            default -> {
                System.err.println("Unknown command: " + args[0]);
                printUsage();
                System.exit(2);
            }
        }
    }

    private static void runLsp() {
        SysMLLanguageServer server = new SysMLLanguageServer();
        Launcher<LanguageClient> launcher =
            LSPLauncher.createServerLauncher(
                server,
                System.in,
                System.out
            );
        server.connect(launcher.getRemoteProxy());
        launcher.startListening();
    }

    private static void runTemplate(String[] args) throws IOException {
        String name = args.length > 1 ? args[1] : "battery";
        String output = option(args, "--output");
        String text = switch (name) {
            case "battery" -> new SysMLTemplateLibrary().batteryLifecycle();
            case "generic" -> new SysMLTemplateLibrary().genericNeed();
            default -> throw new IllegalArgumentException("Unknown template: " + name);
        };

        Path outputPath = output == null
            ? Path.of(name + ".sysml")
            : Path.of(output);
        Files.createDirectories(outputPath.toAbsolutePath().getParent());
        Files.writeString(outputPath, text, StandardCharsets.UTF_8);
        System.out.println("Wrote " + outputPath.toAbsolutePath());
    }

    private static void runValidate(String[] args) throws IOException {
        String input = option(args, "--input");
        if (input == null) {
            throw new IllegalArgumentException("--input is required");
        }
        SysMLModel model = readModel(Path.of(input));
        List<SysMLDiagnostic> diagnostics = readDiagnostics(Path.of(input));

        if (diagnostics.isEmpty()) {
            System.out.println("Valid SysML continuity input: " + model.allArtifacts().size() + " artifacts");
        } else {
            for (SysMLDiagnostic diagnostic : diagnostics) {
                System.err.println(
                    diagnostic.line() + ":" + diagnostic.character() +
                        " [" + diagnostic.severity() + "] " + diagnostic.message()
                );
            }
        }

    }

    private static void runRelations(String[] args) throws IOException {
            String input = option(args, "--input");
            String mode = option(args, "--mode");
            String output = option(args, "--output");
            if (input == null) {
                throw new IllegalArgumentException("--input is required");
            }
            String resolvedMode = mode == null ? "enforce" : mode.toLowerCase();
            if (!List.of("checkonly", "enforce").contains(resolvedMode)) {
                throw new IllegalArgumentException(
                    "--mode must be checkonly or enforce"
                );
            }

            SysMLModel model = readModel(Path.of(input));
            ContinuityRelations relations = new ContinuityRelations();
            if ("checkonly".equals(resolvedMode)) {
                List<ContinuityRelations.RelationDiagnostic> diagnostics =
                    relations.checkonly(model);
                if (diagnostics.isEmpty()) {
                    System.out.println("No continuity relation diagnostics.");
                } else {
                    for (ContinuityRelations.RelationDiagnostic diagnostic
                         : diagnostics) {
                        System.err.println(
                            diagnostic.relation() + ": " +
                                diagnostic.message()
                        );
                    }
                    System.exit(1);
                }
                return;
            }

            List<?> traces = relations.enforce(model);
            if (output != null) {
                Path outputPath = Path.of(output);
                Files.createDirectories(outputPath.toAbsolutePath().getParent());
                Files.writeString(
                    outputPath,
                    new SysMLPrinter().print(model),
                    StandardCharsets.UTF_8
                );
                System.out.println("Wrote " + outputPath.toAbsolutePath());
            }
            System.out.println(
                "Continuity relations enforced: " +
                    traces.size() + " trace links materialized"
            );
    }

    private static void runQvt(String[] args) throws IOException {
        String input = option(args, "--input");
        String output = option(args, "--output");
        String transformation = option(args, "--transformation");
        if (input == null) {
            throw new IllegalArgumentException("--input is required");
        }

        Path inputPath = Path.of(input);
        SysMLModel model = readModel(inputPath);
        List<SysMLDiagnostic> diagnostics = readDiagnostics(inputPath);
        if (!diagnostics.isEmpty()) {
            for (SysMLDiagnostic diagnostic : diagnostics) {
                if ("error".equals(diagnostic.severity())) {
                    throw new IllegalArgumentException(
                        "Invalid SysML input at line " + diagnostic.line() +
                            ": " + diagnostic.message()
                    );
                }
            }
        }

        Path transformationPath = transformation == null
            ? Path.of("qvt/LifecycleOperational.qvto")
            : Path.of(transformation);
        EclipseQvtEngine engine = new EclipseQvtEngine();
        QvtResult result = engine.execute(model, transformationPath);
        if (!result.successful()) {
            for (String diagnostic : result.diagnostics()) {
                System.err.println(diagnostic);
            }
            System.exit(1);
        }

        ContinuityRelations relations = new ContinuityRelations();
        relations.enforce(model);

        Artifact requirement = first(model, ArtifactKind.REQUIREMENT);
        if (requirement != null) {
            model.baselineThread(requirement.id());
        }

        if (output != null) {
            Path outputPath = Path.of(output);
            Files.createDirectories(outputPath.toAbsolutePath().getParent());
            Files.writeString(
                outputPath,
                new SysMLPrinter().print(model),
                StandardCharsets.UTF_8
            );
            System.out.println("Wrote " + outputPath.toAbsolutePath());
        }

        System.out.println(
            "Eclipse QVTd transformation completed: " +
                model.allArtifacts().size() + " artifacts, " +
                model.activeTraces().size() + " traces"
        );
    }

    private static SysMLModel readModel(Path input) throws IOException {
        SysMLModel model = new SysMLModel();
        for (Path path : sysmlFiles(input)) {
            String text = Files.readString(path, StandardCharsets.UTF_8);
            SysMLParser.ParseResult parsed =
                new SysMLParser().parse(path.toUri().toString(), text);
            for (Artifact artifact : parsed.model().allArtifacts()) {
                model.addArtifact(artifact);
            }
        }
        return model;
    }

    private static List<SysMLDiagnostic> readDiagnostics(Path input) throws IOException {
        List<SysMLDiagnostic> result = new ArrayList<>();
        for (Path path : sysmlFiles(input)) {
            String text = Files.readString(path, StandardCharsets.UTF_8);
            SysMLParser.ParseResult parsed =
                new SysMLParser().parse(path.toUri().toString(), text);
            result.addAll(parsed.diagnostics());
        }
        return result;
    }

    private static List<Path> sysmlFiles(Path input) throws IOException {
        List<Path> result = new ArrayList<>();
        if (Files.isRegularFile(input)) {
            if (input.getFileName().toString().endsWith(".sysml")) {
                result.add(input);
            }
            return result;
        }
        if (!Files.isDirectory(input)) {
            throw new IllegalArgumentException("Input not found: " + input);
        }
        try (var paths = Files.walk(input)) {
            paths
                .filter(Files::isRegularFile)
                .filter(path -> path.getFileName().toString().endsWith(".sysml"))
                .sorted()
                .forEach(result::add);
        }
        return result;
    }

    private static Artifact first(SysMLModel model, ArtifactKind kind) {
        for (Artifact artifact : model.latestArtifacts()) {
            if (artifact.kind() == kind) {
                return artifact;
            }
        }
        return null;
    }

    private static String option(String[] args, String name) {
        for (int index = 0; index < args.length - 1; index++) {
            if (name.equals(args[index])) {
                return args[index + 1];
            }
        }
        return null;
    }

    private static void printUsage() {
        System.out.println(
            "Usage:\n" +
                "  java -jar sysml-v2-qvt-continuity.jar lsp\n" +
                "  java -jar sysml-v2-qvt-continuity.jar template battery --output battery.sysml\n" +
                "  java -jar sysml-v2-qvt-continuity.jar validate --input battery.sysml\n" +
                "  java -jar sysml-v2-qvt-continuity.jar qvt --input battery.sysml " +
                "--output lifecycle.sysml --transformation qvt/LifecycleOperational.qvto\n" +
                "  java -jar sysml-v2-qvt-continuity.jar relations --input battery.sysml " +
                "--mode checkonly\n" +
                "  java -jar sysml-v2-qvt-continuity.jar relations --input battery.sysml " +
                "--mode enforce --output relations.sysml"
        );
    }
}
