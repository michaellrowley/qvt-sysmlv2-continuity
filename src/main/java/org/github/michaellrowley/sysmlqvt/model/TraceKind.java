package org.github.michaellrowley.sysmlqvt.model;

public enum TraceKind {
    ORIGIN("origin"),
    REALIZES("realizes"),
    SUPPORTS("supports"),
    EXPOSES("exposes"),
    CONNECTS("connects"),
    ALLOCATES("allocates"),
    DEPLOYED_TO("deployed_to"),
    IMPLEMENTS("implements"),
    GENERATES("generates"),
    COVERS("covers"),
    EXECUTES("executes"),
    VERIFIES("verifies"),
    SUPERSEDES("supersedes");

    private final String text;

    TraceKind(String text) {
        this.text = text;
    }

    public String text() {
        return text;
    }

    public static TraceKind fromText(String value) {
        for (TraceKind kind : values()) {
            if (kind.text.equals(value)) {
                return kind;
            }
        }
        throw new IllegalArgumentException("Unknown trace kind: " + value);
    }
}
