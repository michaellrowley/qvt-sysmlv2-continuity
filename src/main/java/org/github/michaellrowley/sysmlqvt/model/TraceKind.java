package org.github.michaellrowley.sysmlqvt.model;

public enum TraceKind {
    ORIGIN("origin"),
    REALIZES("realizes"),
    SUPPORTS("supports"),
    EXPOSES("exposes"),
    REQUIRES("requires"),
    PROVIDES("provides"),
    CONNECTS("connects"),
    ALLOCATES("allocates"),
    DEPLOYED_TO("deployed_to"),
    IMPLEMENTS("implements"),
    GENERATES("generates"),
    CALLS("calls"),
    PUBLISHES("publishes"),
    SUBSCRIBES("subscribes"),
    RECEIVES("receives"),
    SCHEDULES("schedules"),
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
