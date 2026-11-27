package org.github.michaellrowley.sysmlqvt.crud;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class CrudRepository {
    private final Path root;
    private final Map<String, CrudEntity> entities = new LinkedHashMap<>();
    private final LifecycleActivityCatalog catalog =
        new LifecycleActivityCatalog();

    public CrudRepository(Path root) {
        this.root = root;
        loadIndex();
    }

    public LifecycleActivityCatalog catalog() {
        return catalog;
    }

    public CrudResult execute(CrudRequest request) {
        catalog.request(request.activityId());

        return switch (request.operator()) {
            case CREATE -> create(request);
            case REQUEST -> request(request);
            case UPDATE -> update(request);
            case DELETE -> delete(request);
        };
    }

    private CrudResult create(CrudRequest request) {
        if (request.id() == null || request.id().isBlank()) {
            return CrudResult.failure(
                request.operator(),
                "Create requires an entity ID."
            );
        }
        CrudEntity existing = entities.get(request.id());
        if (existing != null) {
            return CrudResult.failure(
                request.operator(),
                "Entity already exists: " + request.id()
            );
        }
        String now = Instant.now().toString();
        CrudEntity entity = new CrudEntity(
            request.id(),
            request.kind(),
            request.activityId(),
            request.parentId(),
            request.name(),
            "active",
            1,
            now,
            now,
            request.properties()
        );
        entities.put(entity.id(), entity);
        List<String> outputPaths = writeEntityAndCppUnit(entity);
        saveIndex();
        return CrudResult.single(
            request.operator(),
            entity,
            outputPaths,
            "Created " + entity.kind() + " " + entity.ref()
        );
    }

    private CrudResult request(CrudRequest request) {
        if (request.id() != null && !request.id().isBlank()) {
            CrudEntity entity = entities.get(request.id());
            if (entity == null
                || (!request.includeDeleted() && entity.deleted())) {
                return CrudResult.failure(
                    request.operator(),
                    "Unknown entity: " + request.id()
                );
            }
            return CrudResult.single(
                request.operator(),
                entity,
                List.of(),
                "Requested " + entity.ref()
            );
        }

        List<CrudEntity> result = new ArrayList<>();
        for (CrudEntity entity : entities.values()) {
            if (request.kind() != null
                && entity.kind() != request.kind()) {
                continue;
            }
            if (!request.activityId().equals(entity.activityId())) {
                continue;
            }
            if (!request.includeDeleted() && entity.deleted()) {
                continue;
            }
            result.add(entity);
        }
        result.sort(
            Comparator
                .comparing(CrudEntity::activityId)
                .thenComparing(CrudEntity::kind, (left, right) ->
                    left.name().compareTo(right.name()))
                .thenComparing(CrudEntity::id)
        );
        return CrudResult.multiple(
            request.operator(),
            List.copyOf(result),
            "Requested " + result.size() + " entities"
        );
    }

    private CrudResult update(CrudRequest request) {
        if (request.id() == null || request.id().isBlank()) {
            return CrudResult.failure(
                request.operator(),
                "Update requires an entity ID."
            );
        }
        CrudEntity existing = entities.get(request.id());
        if (existing == null) {
            return CrudResult.failure(
                request.operator(),
                "Unknown entity: " + request.id()
            );
        }
        Map<String, Object> properties =
            new LinkedHashMap<>(existing.properties());
        properties.putAll(request.properties());

        String now = Instant.now().toString();
        CrudEntity updated = new CrudEntity(
            existing.id(),
            request.kind() == null ? existing.kind() : request.kind(),
            request.activityId(),
            request.parentId() == null
                ? existing.parentId()
                : request.parentId(),
            request.name() == null ? existing.name() : request.name(),
            "active",
            existing.revision() + 1,
            existing.createdAt(),
            now,
            properties
        );
        entities.put(updated.id(), updated);
        List<String> outputPaths = writeEntityAndCppUnit(updated);
        saveIndex();
        return CrudResult.single(
            request.operator(),
            updated,
            outputPaths,
            "Updated " + updated.ref()
        );
    }

    private CrudResult delete(CrudRequest request) {
        if (request.id() == null || request.id().isBlank()) {
            return CrudResult.failure(
                request.operator(),
                "Delete requires an entity ID."
            );
        }
        CrudEntity existing = entities.get(request.id());
        if (existing == null) {
            return CrudResult.failure(
                request.operator(),
                "Unknown entity: " + request.id()
            );
        }
        CrudEntity deleted = new CrudEntity(
            existing.id(),
            existing.kind(),
            existing.activityId(),
            existing.parentId(),
            existing.name(),
            "deleted",
            existing.revision() + 1,
            existing.createdAt(),
            Instant.now().toString(),
            existing.properties()
        );
        entities.put(deleted.id(), deleted);
        List<String> outputPaths = writeEntityAndCppUnit(deleted);
        saveIndex();
        return CrudResult.single(
            request.operator(),
            deleted,
            outputPaths,
            "Deleted " + deleted.ref()
        );
    }

    private List<String> writeEntityAndCppUnit(CrudEntity entity) {
        List<String> outputs = new ArrayList<>();
        try {
            Path activityDirectory = root.resolve(
                entity.activityId()
            ).resolve(
                entity.kind().name().toLowerCase()
            );
            Files.createDirectories(activityDirectory);

            Path sysml = activityDirectory.resolve(
                safeFileName(entity.id()) + ".sysml"
            );
            Files.writeString(
                sysml,
                entitySysml(entity),
                StandardCharsets.UTF_8
            );
            outputs.add(sysml.toString());

            if (entity.kind() == EntityKind.CPP_IMPLEMENTATION
                || entity.kind() == EntityKind.ENTRYPOINT) {
                Path header = activityDirectory.resolve(
                    safeFileName(entity.id()) + ".hpp"
                );
                Path source = activityDirectory.resolve(
                    safeFileName(entity.id()) + ".cpp"
                );
                Files.writeString(
                    header,
                    cppHeader(entity),
                    StandardCharsets.UTF_8
                );
                Files.writeString(
                    source,
                    cppSource(entity),
                    StandardCharsets.UTF_8
                );
                outputs.add(header.toString());
                outputs.add(source.toString());
            }
        } catch (java.io.IOException exception) {
            throw new IllegalStateException(
                "Unable to persist CRUD entity " + entity.ref(),
                exception
            );
        }
        return outputs;
    }

    private String entitySysml(CrudEntity entity) {
        StringBuilder result = new StringBuilder();
        result.append("package '")
            .append(activityPackageName(entity.activityId()))
            .append("' {\n");
        result.append("    // ")
            .append(entity.ref())
            .append(" ")
            .append(entity.kind().name().toLowerCase())
            .append('\n');
        result.append("    ");
        result.append(entityKindSysml(entity.kind()));
        result.append(' ')
            .append(entity.id());
        result.append(" {\n");
        result.append("        revision = ")
            .append(entity.revision())
            .append(";\n");
        if (entity.parentId() != null) {
            result.append("        parent = \"")
                .append(entity.parentId())
                .append("\";\n");
        }
        if (entity.name() != null) {
            result.append("        name = \"")
                .append(entity.name())
                .append("\";\n");
        }
        result.append("        status = \"")
            .append(entity.status())
            .append("\";\n");
        result.append("    }\n");
        result.append("}\n");
        return result.toString();
    }

    private String cppHeader(CrudEntity entity) {
        String identifier = cppIdentifier(entity.id());
        String namespace = activityNamespace(entity.activityId());
        return "#pragma once\n\n"
            + "namespace sysmlv2::" + namespace + " {\n\n"
            + "class " + identifier + " {\n"
            + "public:\n"
            + "    " + identifier + "() = default;\n\n"
            + "    int run();\n"
            + "};\n\n"
            + "} // namespace sysmlv2::" + namespace + "\n";
    }

    private String cppSource(CrudEntity entity) {
        String identifier = cppIdentifier(entity.id());
        String namespace = activityNamespace(entity.activityId());
        return "#include \"" + safeFileName(entity.id()) + ".hpp\"\n\n"
            + "namespace sysmlv2::" + namespace + " {\n\n"
            + "int " + identifier + "::run() {\n"
            + "    // Implement this domain entrypoint in C++.\n"
            + "    return 0;\n"
            + "}\n\n"
            + "} // namespace sysmlv2::" + namespace + "\n";
    }

    private String entityKindSysml(EntityKind kind) {
        return switch (kind) {
            case CONOPS -> "action def";
            case CONCERN -> "concern def";
            case DOMAIN, SUBSYSTEM, COMPONENT, MODULE -> "part def";
            case REQUIREMENT -> "requirement def";
            case CONSTRAINT -> "constraint def";
            case INTERFACE -> "interface def";
            case PORT -> "port def";
            case BEHAVIOR, ENTRYPOINT -> "action def";
            case DATA_TYPE -> "attribute def";
            case CPP_IMPLEMENTATION -> "action def";
            case BUILD_TARGET, DEPLOYMENT -> "part def";
            case TEST_SUITE, TEST_CASE -> "verification def";
            case VERIFICATION_PLAN -> "verification def";
            case VERIFICATION_EVIDENCE -> "metadata def";
            case VALIDATION_SCENARIO -> "action def";
            case ALLOCATION -> "allocation def";
            case BASELINE, RELEASE -> "metadata def";
            case CHANGE_REQUEST -> "concern def";
        };
    }

    private static String safeFileName(String value) {
        StringBuilder result = new StringBuilder();
        for (char character : value.toCharArray()) {
            result.append(
                Character.isLetterOrDigit(character) || character == '-'
                    ? character
                    : '_'
            );
        }
        return result.toString();
    }

    private static String cppIdentifier(String value) {
        StringBuilder result = new StringBuilder();
        boolean capitalize = false;
        for (char character : value.toCharArray()) {
            if (!Character.isLetterOrDigit(character)) {
                capitalize = true;
            } else if (result.isEmpty()) {
                result.append(Character.toUpperCase(character));
            } else if (capitalize) {
                result.append(Character.toUpperCase(character));
                capitalize = false;
            } else {
                result.append(character);
            }
        }
        return result.isEmpty() ? "DomainEntrypoint" : result.toString();
    }

    private static String activityPackageName(String activityId) {
        return cppIdentifier(activityId);
    }

    private static String activityNamespace(String activityId) {
        return safeFileName(activityId).replace('-', '_');
    }

    private Path indexPath() {
        return root.resolve("crud-index.json");
    }

    private void loadIndex() {
        Path index = indexPath();
        if (!Files.isRegularFile(index)) {
            return;
        }
        try {
            String json = Files.readString(index, StandardCharsets.UTF_8);
            String[] records = splitJsonRecords(json);
            for (String record : records) {
                Map<String, Object> values = parseJsonObject(record);
                if (values.isEmpty()) {
                    continue;
                }
                String id = String.valueOf(values.get("id"));
                EntityKind kind = EntityKind.valueOf(
                    String.valueOf(values.get("kind"))
                );
                String activityId =
                    String.valueOf(values.get("activityId"));
                String parentId = values.containsKey("parentId")
                    ? String.valueOf(values.get("parentId"))
                    : null;
                String name = values.containsKey("name")
                    ? String.valueOf(values.get("name"))
                    : null;
                String status = String.valueOf(
                    values.getOrDefault("status", "active")
                );
                int revision = values.get("revision") instanceof Number number
                    ? number.intValue()
                    : 1;
                String createdAt = String.valueOf(
                    values.getOrDefault("createdAt", "")
                );
                String updatedAt = String.valueOf(
                    values.getOrDefault("updatedAt", "")
                );
                Map<String, Object> properties =
                    values.get("properties") instanceof Map<?, ?> map
                        ? mapCopy(map)
                        : new LinkedHashMap<>();
                entities.put(
                    id,
                    new CrudEntity(
                        id,
                        kind,
                        activityId,
                        parentId,
                        name,
                        status,
                        revision,
                        createdAt,
                        updatedAt,
                        properties
                    )
                );
            }
        } catch (IOException | RuntimeException exception) {
            throw new IllegalStateException(
                "Unable to load CRUD index " + index,
                exception
            );
        }
    }

    private void saveIndex() {
        try {
            Files.createDirectories(root);
            StringBuilder json = new StringBuilder();
            json.append("[");
            boolean first = true;
            for (CrudEntity entity : entities.values()) {
                if (!first) {
                    json.append(",");
                }
                first = false;
                json.append(indexRecord(entity));
            }
            json.append("]");
            Files.writeString(
                indexPath(),
                json.toString(),
                StandardCharsets.UTF_8
            );
        } catch (IOException exception) {
            throw new IllegalStateException(
                "Unable to save CRUD index " + indexPath(),
                exception
            );
        }
    }

    private String indexRecord(CrudEntity entity) {
        return "{"
            + jsonField("id", entity.id())
            + ",\"kind\":\"" + entity.kind().name() + "\""
            + ",\"activityId\":\"" + escapeJson(entity.activityId()) + "\""
            + ",\"parentId\":\""
            + escapeJson(entity.parentId() == null ? "" : entity.parentId())
            + "\""
            + ",\"name\":\""
            + escapeJson(entity.name() == null ? "" : entity.name())
            + "\""
            + ",\"status\":\"" + entity.status() + "\""
            + ",\"revision\":" + entity.revision()
            + ",\"createdAt\":\"" + escapeJson(entity.createdAt()) + "\""
            + ",\"updatedAt\":\"" + escapeJson(entity.updatedAt()) + "\""
            + ",\"properties\":" + jsonMap(entity.properties())
            + "}";
    }

    private static String jsonField(String key, String value) {
        return "\"" + key + "\":\"" + escapeJson(value) + "\"";
    }

    private static String jsonMap(Map<String, Object> values) {
        StringBuilder json = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : values.entrySet()) {
            if (!first) {
                json.append(",");
            }
            first = false;
            json.append("\"")
                .append(escapeJson(entry.getKey()))
                .append("\":")
                .append(jsonValue(entry.getValue()));
        }
        return json.append("}").toString();
    }

    private static String jsonValue(Object value) {
        if (value == null) {
            return "null";
        }
        if (value instanceof Number || value instanceof Boolean) {
            return String.valueOf(value);
        }
        if (value instanceof Iterable<?> iterable) {
            StringBuilder json = new StringBuilder("[");
            boolean first = true;
            for (Object item : iterable) {
                if (!first) {
                    json.append(",");
                }
                first = false;
                json.append(jsonValue(item));
            }
            return json.append("]").toString();
        }
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> values = new LinkedHashMap<>();
            map.forEach((key, item) ->
                values.put(String.valueOf(key), item)
            );
            return jsonMap(values);
        }
        return "\"" + escapeJson(String.valueOf(value)) + "\"";
    }

    private static String escapeJson(String value) {
        return value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t");
    }

    private static String[] splitJsonRecords(String json) {
        String trimmed = json.trim();
        if (trimmed.length() < 2
            || trimmed.charAt(0) != '['
            || trimmed.charAt(trimmed.length() - 1) != ']') {
            return new String[0];
        }
        String body = trimmed.substring(1, trimmed.length() - 1).trim();
        if (body.isEmpty()) {
            return new String[0];
        }
        List<String> records = new ArrayList<>();
        int depth = 0;
        boolean quoted = false;
        boolean escaped = false;
        int start = 0;
        for (int index = 0; index < body.length(); index++) {
            char character = body.charAt(index);
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
            } else if (!quoted && character == ',' && depth == 0) {
                records.add(body.substring(start, index).trim());
                start = index + 1;
            }
        }
        records.add(body.substring(start).trim());
        return records.toArray(String[]::new);
    }

    private static Map<String, Object> parseJsonObject(String json) {
        String trimmed = json.trim();
        if (trimmed.length() < 2
            || trimmed.charAt(0) != '{'
            || trimmed.charAt(trimmed.length() - 1) != '}') {
            return Map.of();
        }
        Map<String, Object> values = new LinkedHashMap<>();
        String body = trimmed.substring(1, trimmed.length() - 1);
        int index = 0;
        while (index < body.length()) {
            while (index < body.length()
                && Character.isWhitespace(body.charAt(index))) {
                index++;
            }
            if (index >= body.length()) {
                break;
            }
            if (body.charAt(index) != '"') {
                index++;
                continue;
            }
            JsonString key = readJsonString(body, index);
            index = key.next();
            while (index < body.length()
                && Character.isWhitespace(body.charAt(index))) {
                index++;
            }
            if (index >= body.length() || body.charAt(index) != ':') {
                break;
            }
            index++;
            while (index < body.length()
                && Character.isWhitespace(body.charAt(index))) {
                index++;
            }
            JsonValue value = readJsonValue(body, index);
            values.put(key.value(), value.value());
            index = value.next();
            while (index < body.length()
                && (Character.isWhitespace(body.charAt(index))
                    || body.charAt(index) == ',')) {
                index++;
            }
        }
        return values;
    }

    private record JsonString(String value, int next) {
    }

    private record JsonValue(Object value, int next) {
    }

    private static JsonString readJsonString(String json, int start) {
        StringBuilder value = new StringBuilder();
        int index = start + 1;
        boolean escaped = false;
        while (index < json.length()) {
            char character = json.charAt(index++);
            if (escaped) {
                value.append(switch (character) {
                    case '"' -> '"';
                    case '\\' -> '\\';
                    case 'n' -> '\n';
                    case 'r' -> '\r';
                    case 't' -> '\t';
                    default -> character;
                });
                escaped = false;
            } else if (character == '\\') {
                escaped = true;
            } else if (character == '"') {
                return new JsonString(value.toString(), index);
            } else {
                value.append(character);
            }
        }
        return new JsonString(value.toString(), index);
    }

    private static JsonValue readJsonValue(String json, int start) {
        char character = json.charAt(start);
        if (character == '"') {
            JsonString value = readJsonString(json, start);
            return new JsonValue(value.value(), value.next());
        }
        if (character == '{') {
            int end = findJsonObjectEnd(json, start);
            Map<String, Object> value =
                parseJsonObject(json.substring(start, end));
            return new JsonValue(value, end);
        }
        if (character == '[') {
            int end = findJsonArrayEnd(json, start);
            List<Object> value = parseJsonArray(json.substring(start, end));
            return new JsonValue(value, end);
        }
        int end = start;
        while (end < json.length()
            && json.charAt(end) != ','
            && json.charAt(end) != '}') {
            end++;
        }
        String token = json.substring(start, end).trim();
        if ("true".equals(token)) {
            return new JsonValue(Boolean.TRUE, end);
        }
        if ("false".equals(token)) {
            return new JsonValue(Boolean.FALSE, end);
        }
        if ("null".equals(token)) {
            return new JsonValue(null, end);
        }
        try {
            return new JsonValue(Double.valueOf(token), end);
        } catch (NumberFormatException ignored) {
            return new JsonValue(token, end);
        }
    }

    private static int findJsonObjectEnd(String json, int start) {
        int depth = 0;
        boolean quoted = false;
        boolean escaped = false;
        for (int index = start; index < json.length(); index++) {
            char character = json.charAt(index);
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
                    return index + 1;
                }
            }
        }
        return json.length();
    }

    private static int findJsonArrayEnd(String json, int start) {
        int depth = 0;
        boolean quoted = false;
        boolean escaped = false;
        for (int index = start; index < json.length(); index++) {
            char character = json.charAt(index);
            if (escaped) {
                escaped = false;
            } else if (character == '\\' && quoted) {
                escaped = true;
            } else if (character == '"') {
                quoted = !quoted;
            } else if (!quoted && character == '[') {
                depth++;
            } else if (!quoted && character == ']') {
                depth--;
                if (depth == 0) {
                    return index + 1;
                }
            }
        }
        return json.length();
    }

    private static List<Object> parseJsonArray(String json) {
        String trimmed = json.trim();
        if (trimmed.length() < 2) {
            return List.of();
        }
        String body = trimmed.substring(1, trimmed.length() - 1).trim();
        if (body.isEmpty()) {
            return List.of();
        }
        List<Object> result = new ArrayList<>();
        int index = 0;
        while (index < body.length()) {
            while (index < body.length()
                && (Character.isWhitespace(body.charAt(index))
                    || body.charAt(index) == ',')) {
                index++;
            }
            if (index >= body.length()) {
                break;
            }
            JsonValue value = readJsonValue(body, index);
            result.add(value.value());
            index = value.next();
        }
        return result;
    }

    private static Map<String, Object> mapCopy(Map<?, ?> map) {
        Map<String, Object> result = new LinkedHashMap<>();
        map.forEach((key, value) ->
            result.put(String.valueOf(key), value)
        );
        return result;
    }
}
