package org.github.michaellrowley.sysmlqvt.model;

import java.util.List;

public record Baseline(
    String id,
    String requirementRef,
    List<String> artifactRefs,
    List<String> traceKeys,
    String contentHash
) {
}
