package org.github.michaellrowley.sysmlqvt.model;

public record TraceLink(
    TraceKind kind,
    String source,
    String target,
    String status,
    String derivedBy
) {
    public TraceLink {
        status = status == null ? "active" : status;
        derivedBy = derivedBy == null ? "" : derivedBy;
    }

    public String key() {
        return kind.text() + "|" + source + "|" + target + "|" + status;
    }
}
