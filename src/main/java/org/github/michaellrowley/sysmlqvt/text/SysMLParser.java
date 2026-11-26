package org.github.michaellrowley.sysmlqvt.text;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class SysMLParser {
    public record ParseResult(SysMLModel model, List<SysMLDiagnostic> diagnostics) {
    }

    private static final Pattern PROPERTY =
        Pattern.compile(
            "(?ms)^\\s*([A-Za-z_]\\w*)\\s*=\\s*" +
                "(\\[(?:[^\\]\"]|\"(?:\\\\.|[^\"\\\\])*\")*\\]|" +
                "\"(?:\\\\.|[^\"\\\\])*\"|[^;\\r\\n]+)\\s*;",
            Pattern.MULTILINE
        );

    public ParseResult parse(String uri, String text) {
        SysMLModel model = new SysMLModel();
        List<SysMLDiagnostic> diagnostics = new ArrayList<>();
        String cleaned = stripComments(text);

        if (count(cleaned, '{') != count(cleaned, '}')) {
            diagnostics.add(new SysMLDiagnostic(
                lineForOffset(cleaned, firstBraceMismatch(cleaned)),
                0,
                "error",
                "Unbalanced braces."
            ));
        }

        Pattern declarationLine = Pattern.compile(
            "(?m)^\\s*" +
                "(stakeholder\\s+need|requirement(?:\\s+def)?|part(?:\\s+def)?|" +
                "interface(?:\\s+def)?|port(?:\\s+def)?|connection(?:\\s+def)?|" +
                "behavior(?:\\s+def)?|implementation(?:\\s+def)?|" +
                "function\\s+call|communication|schedule|" +
                "allocation(?:\\s+def)?|deployment(?:\\s+def)?|" +
                "verification\\s+plan|test\\s+component|test\\s+scenario|evidence)" +
                "\\s+([A-Za-z][A-Za-z0-9_.-]*)([^\\r\\n]*)",
            Pattern.CASE_INSENSITIVE
        );
        Matcher matcher = declarationLine.matcher(cleaned);
        int searchIndex = 0;
        while (matcher.find(searchIndex)) {
            String keyword = matcher.group(1);
            String id = matcher.group(2);
            String rest = matcher.group(3);
            Declaration declaration = declaration(keyword + " " + id + rest);
            if (declaration == null) {
                searchIndex = matcher.end();
                continue;
            }
            Map<String, Object> properties = new LinkedHashMap<>();
            if (rest.contains("{")) {
                int blockStart = cleaned.indexOf('{', matcher.start());
                int blockEnd = findMatchingBrace(cleaned, blockStart);
                if (blockStart >= 0 && blockEnd >= 0) {
                    String block = cleaned.substring(blockStart + 1, blockEnd);
                    properties = parseProperties(block);
                    searchIndex = blockEnd + 1;
                } else {
                    searchIndex = matcher.end();
                }
            } else {
                properties = parseInlineProperties(matcher.group());
                searchIndex = matcher.end();
            }

            Artifact artifact = new Artifact(
                declaration.id(),
                declaration.kind(),
                revision(properties),
                properties,
                supersedes(properties)
            );
            model.addArtifact(artifact);

            validateDeclaration(
                lineForOffset(cleaned, matcher.start()),
                declaration,
                properties,
                diagnostics
            );
        }

        return new ParseResult(model, diagnostics);
    }

    private record Declaration(ArtifactKind kind, String id) {
    }

    private Declaration declaration(String line) {
        Pattern[] patterns = {
            Pattern.compile("^stakeholder\\s+need\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^requirement(?:\\s+def)?\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^part(?:\\s+def)?\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^interface(?:\\s+def)?\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^port(?:\\s+def)?\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^connection(?:\\s+def)?\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^behavior(?:\\s+def)?\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^function\\s+call\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^communication\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^schedule\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^implementation(?:\\s+def)?\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^allocation(?:\\s+def)?\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^deployment(?:\\s+def)?\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^verification\\s+plan\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^test\\s+component\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^test\\s+scenario\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("^evidence\\s+([A-Za-z][A-Za-z0-9_.-]*)", Pattern.CASE_INSENSITIVE)
        };
        ArtifactKind[] kinds = {
            ArtifactKind.STAKEHOLDER_NEED,
            ArtifactKind.REQUIREMENT,
            ArtifactKind.ARCHITECTURAL_ELEMENT,
            ArtifactKind.INTERFACE,
            ArtifactKind.PORT,
            ArtifactKind.CONNECTION,
            ArtifactKind.BEHAVIOR_ELEMENT,
            ArtifactKind.FUNCTION_CALL,
            ArtifactKind.COMMUNICATION,
            ArtifactKind.SCHEDULE,
            ArtifactKind.IMPLEMENTATION,
            ArtifactKind.ALLOCATION,
            ArtifactKind.DEPLOYMENT,
            ArtifactKind.VERIFICATION_PLAN,
            ArtifactKind.COMPONENT_TEST,
            ArtifactKind.SCENARIO_TEST,
            ArtifactKind.VERIFICATION_EVIDENCE
        };
        for (int index = 0; index < patterns.length; index++) {
            Matcher matcher = patterns[index].matcher(line);
            if (matcher.find()) {
                String id = matcher.group(1);
                return new Declaration(kinds[index], id);
            }
        }
        return null;
    }

    private Map<String, Object> parseInlineProperties(String line) {
        Map<String, Object> properties = new LinkedHashMap<>();
        int equals = line.indexOf('=');
        if (equals < 0) {
            return properties;
        }
        String tail = line.substring(equals + 1).trim();
        properties.put("statement", parseScalar(tail));
        return properties;
    }

    private Map<String, Object> parseProperties(String block) {
        Map<String, Object> properties = new LinkedHashMap<>();
        Matcher matcher = PROPERTY.matcher(block);
        while (matcher.find()) {
            String key = matcher.group(1);
            String raw = matcher.group(2).trim();
            properties.put(key, parseValue(raw));
        }
        return properties;
    }

    private Object parseValue(String raw) {
        if (raw.startsWith("[") && raw.endsWith("]")) {
            List<Object> values = new ArrayList<>();
            String inside = raw.substring(1, raw.length() - 1).trim();
            if (!inside.isEmpty()) {
                for (String item : splitTopLevel(inside, ',')) {
                    values.add(parseScalar(item.trim()));
                }
            }
            return values;
        }
        return parseScalar(raw);
    }

    private Object parseScalar(String raw) {
        if (raw.startsWith("\"") && raw.endsWith("\"")) {
            return unquote(raw);
        }
        if ("true".equalsIgnoreCase(raw)) {
            return Boolean.TRUE;
        }
        if ("false".equalsIgnoreCase(raw)) {
            return Boolean.FALSE;
        }
        try {
            return Integer.valueOf(raw);
        } catch (NumberFormatException ignored) {
        }
        try {
            return Double.valueOf(raw);
        } catch (NumberFormatException ignored) {
        }
        return raw.replaceAll("^;+|;+$", "").trim();
    }

    private List<String> splitTopLevel(String value, char separator) {
        List<String> result = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        boolean escaped = false;
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            if (escaped) {
                current.append(character);
                escaped = false;
            } else if (character == '\\' && quoted) {
                current.append(character);
                escaped = true;
            } else if (character == '"') {
                quoted = !quoted;
                current.append(character);
            } else if (character == separator && !quoted) {
                result.add(current.toString());
                current.setLength(0);
            } else {
                current.append(character);
            }
        }
        if (!current.isEmpty()) {
            result.add(current.toString());
        }
        return result;
    }

    private String unquote(String raw) {
        String value = raw.substring(1, raw.length() - 1);
        return value
            .replace("\\\"", "\"")
            .replace("\\\\", "\\")
            .replace("\\n", "\n");
    }

    private int revision(Map<String, Object> properties) {
        Object revision = properties.get("revision");
        if (revision instanceof Number number) {
            return number.intValue();
        }
        return 1;
    }

    private List<String> supersedes(Map<String, Object> properties) {
        Object supersedes = properties.get("supersedes");
        if (supersedes instanceof List<?> list) {
            List<String> result = new ArrayList<>();
            for (Object item : list) {
                result.add(String.valueOf(item));
            }
            return result;
        }
        if (supersedes instanceof String value) {
            return List.of(value);
        }
        return List.of();
    }

    private void validateDeclaration(
        int line,
        Declaration declaration,
        Map<String, Object> properties,
        List<SysMLDiagnostic> diagnostics
    ) {
        if (declaration.kind() == ArtifactKind.STAKEHOLDER_NEED
            && !properties.containsKey("statement")) {
            diagnostics.add(new SysMLDiagnostic(
                line,
                0,
                "warning",
                "Stakeholder need should define a statement."
            ));
        }
        if (declaration.kind() == ArtifactKind.REQUIREMENT
            && !properties.containsKey("statement")) {
            diagnostics.add(new SysMLDiagnostic(
                line,
                0,
                "warning",
                "Requirement should define a statement."
            ));
        }
        if (declaration.kind() == ArtifactKind.BEHAVIOR_ELEMENT
            && !properties.containsKey("entryPoint")) {
            diagnostics.add(new SysMLDiagnostic(
                line,
                0,
                "warning",
                "Behavior should define an entryPoint."
            ));
        }
    }

    private String stripComments(String text) {
        String withoutBlock = text.replaceAll("(?s)/\\*.*?\\*/", "");
        return withoutBlock.replaceAll("(?m)//[^\\r\\n]*", "");
    }

    private int count(String text, char target) {
        int count = 0;
        for (int index = 0; index < text.length(); index++) {
            if (text.charAt(index) == target) {
                count++;
            }
        }
        return count;
    }

    private int firstBraceMismatch(String text) {
        int depth = 0;
        boolean quoted = false;
        boolean escaped = false;
        for (int index = 0; index < text.length(); index++) {
            char character = text.charAt(index);
            if (escaped) {
                escaped = false;
            } else if (character == '\\' && quoted) {
                escaped = true;
            } else if (character == '"') {
                quoted = !quoted;
            } else if (!quoted && character == '{') {
                depth++;
            } else if (!quoted && character == '}') {
                depth--;
                if (depth < 0) {
                    return index;
                }
            }
        }
        if (depth > 0) {
            for (int index = text.length() - 1; index >= 0; index--) {
                if (text.charAt(index) == '{') {
                    return index;
                }
            }
        }
        return 0;
    }

    private int lineForOffset(String text, int offset) {
        int line = 1;
        for (int index = 0; index < Math.min(offset, text.length()); index++) {
            if (text.charAt(index) == '\n') {
                line++;
            }
        }
        return line;
    }

    private int findMatchingBrace(String text, int start) {
        if (start < 0) {
            return -1;
        }
        int depth = 0;
        boolean quoted = false;
        boolean escaped = false;
        for (int index = start; index < text.length(); index++) {
            char character = text.charAt(index);
            if (escaped) {
                escaped = false;
            } else if (character == '\\' && quoted) {
                escaped = true;
            } else if (character == '"') {
                quoted = !quoted;
            } else if (!quoted && character == '{') {
                depth++;
            } else if (!quoted && character == '}') {
                depth--;
                if (depth == 0) {
                    return index;
                }
            }
        }
        return -1;
    }

    private int advanceOffset(String text, int offset, int lineLength) {
        int next = offset + lineLength + 1;
        return Math.min(next, text.length());
    }
}
