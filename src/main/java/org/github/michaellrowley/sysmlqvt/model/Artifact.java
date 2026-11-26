package org.github.michaellrowley.sysmlqvt.model;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public final class Artifact {
    private final String id;
    private final ArtifactKind kind;
    private final int revision;
    private final Map<String, Object> properties;
    private final List<String> supersedes;
    private final String contentHash;

    public Artifact(
        String id,
        ArtifactKind kind,
        int revision,
        Map<String, Object> properties,
        List<String> supersedes
    ) {
        this.id = id;
        this.kind = kind;
        this.revision = revision;
        this.properties = Collections.unmodifiableMap(
            new LinkedHashMap<>(properties == null ? Map.of() : properties)
        );
        this.supersedes = Collections.unmodifiableList(
            new ArrayList<>(supersedes == null ? List.of() : supersedes)
        );
        this.contentHash = sha256(
            id + "|" + kind.text() + "|" + revision + "|" +
                canonical(properties) + "|" + this.supersedes
        );
    }

    public String id() {
        return id;
    }

    public ArtifactKind kind() {
        return kind;
    }

    public int revision() {
        return revision;
    }

    public Map<String, Object> properties() {
        return properties;
    }

    public List<String> supersedes() {
        return supersedes;
    }

    public String contentHash() {
        return contentHash;
    }

    public String ref() {
        return id + "@" + revision;
    }

    private static String canonical(Map<String, Object> value) {
        TreeMap<String, Object> sorted = new TreeMap<>(value == null ? Map.of() : value);
        StringBuilder result = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : sorted.entrySet()) {
            if (!first) {
                result.append(",");
            }
            first = false;
            result.append(entry.getKey()).append("=");
            result.append(canonicalValue(entry.getValue()));
        }
        return result.append("}").toString();
    }

    private static String canonicalValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            TreeMap<String, Object> sorted = new TreeMap<>();
            map.forEach((key, item) -> sorted.put(String.valueOf(key), item));
            return canonical(sorted);
        }
        if (value instanceof Iterable<?> iterable) {
            StringBuilder result = new StringBuilder("[");
            boolean first = true;
            for (Object item : iterable) {
                if (!first) {
                    result.append(",");
                }
                first = false;
                result.append(canonicalValue(item));
            }
            return result.append("]").toString();
        }
        return String.valueOf(value);
    }

    private static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder();
            for (byte item : bytes) {
                hex.append(String.format("%02x", item));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    public static Artifact revision(
        String id,
        ArtifactKind kind,
        int revision,
        Map<String, Object> properties,
        String supersededRef
    ) {
        List<String> supersedes = supersededRef == null
            ? List.of()
            : List.of(supersededRef);
        return new Artifact(id, kind, revision, properties, supersedes);
    }
}
