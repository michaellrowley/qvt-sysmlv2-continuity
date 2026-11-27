package org.github.michaellrowley.sysmlqvt.crud;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class LifecycleActivityCatalog {
    private static final Set<CrudOperator> ALL_OPERATORS =
        Set.of(CrudOperator.CREATE, CrudOperator.REQUEST,
            CrudOperator.UPDATE, CrudOperator.DELETE);

    private final Map<String, LifecycleActivity> activities =
        new LinkedHashMap<>();

    public LifecycleActivityCatalog() {
        register(
            "stakeholder-needs",
            "Stakeholder Needs",
            EngineeringDiscipline.SYSTEMS,
            VLifecyclePhase.STAKEHOLDER_NEEDS,
            "Capture stakeholders, concerns, and source needs.",
            Set.of(EntityKind.CONCERN, EntityKind.CHANGE_REQUEST)
        );
        register(
            "concept-of-operations",
            "Concept of Operations",
            EngineeringDiscipline.SYSTEMS,
            VLifecyclePhase.CONCEPT,
            "Define operational context, actors, missions, and scenarios.",
            Set.of(EntityKind.CONOPS, EntityKind.VALIDATION_SCENARIO)
        );
        register(
            "system-domain",
            "System Domain",
            EngineeringDiscipline.SYSTEMS,
            VLifecyclePhase.SYSTEM_ARCHITECTURE,
            "Create and manage the top-level system domain.",
            Set.of(EntityKind.DOMAIN)
        );
        register(
            "system-requirements",
            "System Requirements",
            EngineeringDiscipline.SYSTEMS,
            VLifecyclePhase.REQUIREMENTS,
            "Create, review, revise, and retire system requirements.",
            Set.of(EntityKind.REQUIREMENT, EntityKind.CONSTRAINT)
        );
        register(
            "system-architecture",
            "System Architecture",
            EngineeringDiscipline.SYSTEMS,
            VLifecyclePhase.SYSTEM_ARCHITECTURE,
            "Define system domains, subsystems, interfaces, ports, and allocations.",
            Set.of(EntityKind.DOMAIN, EntityKind.SUBSYSTEM, EntityKind.COMPONENT,
                EntityKind.INTERFACE, EntityKind.PORT, EntityKind.ALLOCATION)
        );
        register(
            "subsystem-requirements",
            "Subsystem Requirements",
            EngineeringDiscipline.SYSTEMS,
            VLifecyclePhase.SUBSYSTEM_DESIGN,
            "Flow system requirements into subsystem requirements.",
            Set.of(EntityKind.REQUIREMENT, EntityKind.ALLOCATION)
        );
        register(
            "subsystem-detailed-design",
            "Subsystem Detailed Design",
            EngineeringDiscipline.SYSTEMS,
            VLifecyclePhase.SUBSYSTEM_DESIGN,
            "Design subsystem behavior, data, interfaces, and internal structure.",
            Set.of(EntityKind.SUBSYSTEM, EntityKind.BEHAVIOR,
                EntityKind.DATA_TYPE, EntityKind.INTERFACE)
        );
        register(
            "software-requirements",
            "Software Requirements",
            EngineeringDiscipline.SOFTWARE,
            VLifecyclePhase.REQUIREMENTS,
            "Define software behaviors, interfaces, and constraints.",
            Set.of(EntityKind.REQUIREMENT, EntityKind.CONSTRAINT,
                EntityKind.INTERFACE)
        );
        register(
            "software-architecture",
            "Software Architecture",
            EngineeringDiscipline.SOFTWARE,
            VLifecyclePhase.SUBSYSTEM_DESIGN,
            "Define software modules, packages, domains, and dependencies.",
            Set.of(EntityKind.MODULE, EntityKind.DOMAIN,
                EntityKind.INTERFACE, EntityKind.PORT)
        );
        register(
            "software-detailed-design",
            "Software Detailed Design",
            EngineeringDiscipline.SOFTWARE,
            VLifecyclePhase.SUBSYSTEM_DESIGN,
            "Define classes, functions, data types, and entrypoints.",
            Set.of(EntityKind.BEHAVIOR, EntityKind.ENTRYPOINT,
                EntityKind.DATA_TYPE)
        );
        register(
            "software-implementation",
            "Software Implementation",
            EngineeringDiscipline.SOFTWARE,
            VLifecyclePhase.IMPLEMENTATION,
            "Implement domain behavior at C++ entrypoints.",
            Set.of(EntityKind.CPP_IMPLEMENTATION, EntityKind.ENTRYPOINT,
                EntityKind.BUILD_TARGET)
        );
        register(
            "component-verification",
            "Component Verification",
            EngineeringDiscipline.CROSS_DISCIPLINE,
            VLifecyclePhase.VERIFICATION,
            "Create and run unit/component test suites.",
            Set.of(EntityKind.TEST_SUITE, EntityKind.TEST_CASE,
                EntityKind.VERIFICATION_EVIDENCE)
        );
        register(
            "subsystem-integration",
            "Subsystem Integration",
            EngineeringDiscipline.CROSS_DISCIPLINE,
            VLifecyclePhase.INTEGRATION,
            "Integrate and allocate subsystem components.",
            Set.of(EntityKind.SUBSYSTEM, EntityKind.COMPONENT,
                EntityKind.ALLOCATION)
        );
        register(
            "system-integration",
            "System Integration",
            EngineeringDiscipline.SYSTEMS,
            VLifecyclePhase.INTEGRATION,
            "Integrate subsystems into deployable system configurations.",
            Set.of(EntityKind.DOMAIN, EntityKind.SUBSYSTEM,
                EntityKind.DEPLOYMENT)
        );
        register(
            "system-verification",
            "System Verification",
            EngineeringDiscipline.CROSS_DISCIPLINE,
            VLifecyclePhase.VERIFICATION,
            "Verify requirements using plans, cases, and evidence.",
            Set.of(EntityKind.VERIFICATION_PLAN,
                EntityKind.TEST_CASE, EntityKind.VERIFICATION_EVIDENCE)
        );
        register(
            "system-validation",
            "System Validation",
            EngineeringDiscipline.SYSTEMS,
            VLifecyclePhase.VALIDATION,
            "Validate operational need fulfillment using operational scenarios.",
            Set.of(EntityKind.VALIDATION_SCENARIO,
                EntityKind.VERIFICATION_EVIDENCE)
        );
        register(
            "release",
            "Release",
            EngineeringDiscipline.CROSS_DISCIPLINE,
            VLifecyclePhase.OPERATIONS,
            "Create and manage deployable releases and baselines.",
            Set.of(EntityKind.BUILD_TARGET, EntityKind.RELEASE,
                EntityKind.BASELINE, EntityKind.DEPLOYMENT)
        );
        register(
            "operations-maintenance",
            "Operations and Maintenance",
            EngineeringDiscipline.CROSS_DISCIPLINE,
            VLifecyclePhase.OPERATIONS,
            "Operate, monitor, change, and maintain deployed systems.",
            Set.of(EntityKind.CHANGE_REQUEST, EntityKind.DEPLOYMENT,
                EntityKind.RELEASE)
        );
    }

    private void register(
        String id,
        String name,
        EngineeringDiscipline discipline,
        VLifecyclePhase phase,
        String description,
        Set<EntityKind> entityKinds
    ) {
        activities.put(
            id,
            new LifecycleActivity(
                id,
                name,
                discipline,
                phase,
                description,
                entityKinds,
                ALL_OPERATORS
            )
        );
    }

    public List<LifecycleActivity> all() {
        return List.copyOf(activities.values());
    }

    public LifecycleActivity request(String id) {
        LifecycleActivity activity = activities.get(id);
        if (activity == null) {
            throw new IllegalArgumentException("Unknown lifecycle activity: " + id);
        }
        return activity;
    }
}
