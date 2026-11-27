package org.github.michaellrowley.sysmlqvt.crud;

import java.util.Set;

public record LifecycleActivity(
    String id,
    String name,
    EngineeringDiscipline discipline,
    VLifecyclePhase phase,
    String description,
    Set<EntityKind> entityKinds,
    Set<CrudOperator> operators
) {
}
