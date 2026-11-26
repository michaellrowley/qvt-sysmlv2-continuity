package org.github.michaellrowley.sysmlqvt.model;

public enum ArtifactKind {
    STAKEHOLDER_NEED("stakeholder_need"),
    REQUIREMENT("requirement"),
    ARCHITECTURAL_ELEMENT("architectural_element"),
    INTERFACE("interface"),
    PORT("port"),
    CONNECTION("connection"),
    BEHAVIOR_ELEMENT("behavior_element"),
    IMPLEMENTATION("implementation"),
    ALLOCATION("allocation"),
    DEPLOYMENT("deployment"),
    COMPONENT_TEST("component_test"),
    SCENARIO_TEST("scenario_test"),
    VERIFICATION_EVIDENCE("verification_evidence"),
    VERIFICATION_PLAN("verification_plan");

    private final String text;

    ArtifactKind(String text) {
        this.text = text;
    }

    public String text() {
        return text;
    }

    public static ArtifactKind fromText(String value) {
        for (ArtifactKind kind : values()) {
            if (kind.text.equals(value)) {
                return kind;
            }
        }
        throw new IllegalArgumentException("Unknown artifact kind: " + value);
    }
}
