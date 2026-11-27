package org.github.michaellrowley.sysmlqvt.crud;

import java.util.LinkedHashMap;
import java.util.Map;

public record CrudEntity(
    String id,
    EntityKind kind,
    String activityId,
    String parentId,
    String name,
    String status,
    int revision,
    String createdAt,
    String updatedAt,
    Map<String, Object> properties
) {
    public CrudEntity {
        properties = properties == null
            ? new LinkedHashMap<>()
            : new LinkedHashMap<>(properties);
    }

    public String ref() {
        return id + "@" + revision;
    }

    public boolean deleted() {
        return "deleted".equalsIgnoreCase(status);
    }
}
