package org.github.michaellrowley.sysmlqvt.text;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;
import org.github.michaellrowley.sysmlqvt.model.TraceLink;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

public final class SysMLPrinter {
    public String print(SysMLModel model) {
        StringBuilder text = new StringBuilder();
        text.append("package qvttest;\n\n");

        List<Artifact> artifacts = new ArrayList<>(model.latestArtifacts());
        artifacts.sort(Comparator.comparingInt(this::kindOrder).thenComparing(Artifact::id));
        for (Artifact artifact : artifacts) {
            appendArtifact(text, artifact);
        }

        if (!model.activeTraces().isEmpty()) {
            text.append("\n// Continuity trace links\n");
            List<TraceLink> traces = new ArrayList<>(model.activeTraces());
            traces.sort(
                Comparator
                    .comparing((TraceLink trace) -> trace.kind().text())
                    .thenComparing(TraceLink::source)
                    .thenComparing(TraceLink::target)
            );
            for (TraceLink trace : traces) {
                text.append("trace ")
                    .append(trace.kind().text())
                    .append(" ")
                    .append(trace.source())
                    .append(" ")
                    .append(trace.target())
                    .append(";\n");
            }
        }
        return text.toString();
    }

    private int kindOrder(Artifact artifact) {
        return switch (artifact.kind()) {
            case STAKEHOLDER_NEED -> 1;
            case REQUIREMENT -> 2;
            case ARCHITECTURAL_ELEMENT -> 3;
            case INTERFACE -> 4;
            case PORT -> 5;
            case CONNECTION -> 6;
            case BEHAVIOR_ELEMENT -> 7;
            case FUNCTION_CALL -> 8;
            case COMMUNICATION -> 9;
            case SCHEDULE -> 10;
            case ALLOCATION -> 11;
            case DEPLOYMENT -> 12;
            case IMPLEMENTATION -> 13;
            case VERIFICATION_PLAN -> 14;
            case COMPONENT_TEST -> 15;
            case SCENARIO_TEST -> 16;
            case VERIFICATION_EVIDENCE -> 17;
        };
    }

    private void appendArtifact(StringBuilder text, Artifact artifact) {
        switch (artifact.kind()) {
            case STAKEHOLDER_NEED -> appendBlock(
                text,
                "stakeholder need ",
                artifact,
                List.of("statement", "rationale", "acceptanceCriteria", "requirementId")
            );
            case REQUIREMENT -> appendBlock(
                text,
                "requirement ",
                artifact,
                List.of("statement", "rationale", "acceptanceCriteria", "sourceNeed")
            );
            case ARCHITECTURAL_ELEMENT -> {
                text.append("part def ")
                    .append(artifact.id())
                    .append(";\n");
                appendPropertiesComment(text, artifact.properties());
            }
            case INTERFACE -> appendBlock(
                text,
                "interface ",
                artifact,
                List.of("name", "kind", "protocol", "operations", "ports")
            );
            case PORT -> appendBlock(
                text,
                "port ",
                artifact,
                List.of("name", "direction", "kind", "interfaceId", "protocol")
            );
            case CONNECTION -> appendBlock(
                text,
                "connection ",
                artifact,
                List.of("source", "target", "transport")
            );
            case BEHAVIOR_ELEMENT -> appendBlock(
                text,
                "behavior ",
                artifact,
                List.of(
                    "requirement",
                    "kind",
                    "entryPoint",
                    "initialState",
                    "states",
                    "heatBelowC",
                    "offAboveC",
                    "safeOffOnSensorFault"
                )
            );
            case FUNCTION_CALL -> appendBlock(
                text,
                "function call ",
                artifact,
                List.of("behavior", "functionName", "target", "arguments", "returnBinding")
            );
            case COMMUNICATION -> appendBlock(
                text,
                "communication ",
                artifact,
                List.of("behavior", "kind", "direction", "channel", "protocol", "payloadType")
            );
            case SCHEDULE -> appendBlock(
                text,
                "schedule ",
                artifact,
                List.of("behavior", "kind", "periodMs", "deadlineMs", "wcetMs", "priority")
            );
            case IMPLEMENTATION -> appendBlock(
                text,
                "implementation ",
                artifact,
                List.of("sourceBehavior", "language", "entryPoint", "targetPlatform")
            );
            case ALLOCATION -> appendBlock(
                text,
                "allocation ",
                artifact,
                List.of("sourceRef", "targetRef", "properties")
            );
            case DEPLOYMENT -> appendBlock(
                text,
                "deployment ",
                artifact,
                List.of("componentRef", "targetRef", "environment", "runtime")
            );
            case VERIFICATION_PLAN -> appendBlock(
                text,
                "verification plan ",
                artifact,
                List.of("requirement", "behavior", "implementation", "strategy")
            );
            case COMPONENT_TEST -> appendBlock(
                text,
                "test component ",
                artifact,
                List.of("purpose", "temperatureC", "sensorValid", "expected")
            );
            case SCENARIO_TEST -> appendBlock(
                text,
                "test scenario ",
                artifact,
                List.of("purpose", "initialTemperatureC", "ambientTemperatureC", "steps")
            );
            case VERIFICATION_EVIDENCE -> appendBlock(
                text,
                "evidence ",
                artifact,
                List.of("result", "summary", "requirement", "behavior")
            );
        }
        text.append("\n");
    }

    private void appendBlock(
        StringBuilder text,
        String keyword,
        Artifact artifact,
        List<String> keys
    ) {
        text.append(keyword).append(artifact.id()).append(" {\n");
        text.append("  revision = ").append(artifact.revision()).append(";\n");
        for (String key : keys) {
            if (artifact.properties().containsKey(key)) {
                text.append("  ")
                    .append(key)
                    .append(" = ")
                    .append(formatValue(artifact.properties().get(key)))
                    .append(";\n");
            }
        }
        text.append("}");
    }

    private void appendPropertiesComment(
        StringBuilder text,
        Map<String, Object> properties
    ) {
        if (!properties.isEmpty()) {
            text.append("// properties: ").append(properties).append("\n");
        }
    }

    private String formatValue(Object value) {
        if (value instanceof String string) {
            return "\"" +
                string
                    .replace("\\", "\\\\")
                    .replace("\"", "\\\"")
                    .replace("\n", "\\n") +
                "\"";
        }
        if (value instanceof List<?> list) {
            StringBuilder result = new StringBuilder("[");
            for (int index = 0; index < list.size(); index++) {
                if (index > 0) {
                    result.append(", ");
                }
                result.append(formatValue(list.get(index)));
            }
            return result.append("]").toString();
        }
        if (value instanceof Map<?, ?> map) {
            StringBuilder result = new StringBuilder("{");
            boolean first = true;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (!first) {
                    result.append(", ");
                }
                first = false;
                result.append(entry.getKey()).append(": ").append(formatValue(entry.getValue()));
            }
            return result.append("}").toString();
        }
        return String.valueOf(value);
    }
}
