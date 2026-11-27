package org.github.michaellrowley.sysmlqvt.crud;

import java.util.LinkedHashMap;
import java.util.Map;

public record CrudRequest(
    CrudOperator operator,
    String activityId,
    EntityKind kind,
    String id,
    String parentId,
    String name,
    Map<String, Object> properties,
    boolean includeDeleted
) {
    public CrudRequest {
        properties = properties == null
            ? new LinkedHashMap<>()
            : new LinkedHashMap<>(properties);
    }
}
