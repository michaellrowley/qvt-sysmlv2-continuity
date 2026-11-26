package org.github.michaellrowley.sysmlqvt.qvt;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.ArtifactKind;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;
import org.github.michaellrowley.sysmlqvt.model.TraceKind;
import org.github.michaellrowley.sysmlqvt.model.TraceLink;

import java.util.ArrayList;
import java.util.List;

public final class ContinuityRelations {
    public List<TraceLink> enforce(SysMLModel model) {
        List<TraceLink> created = new ArrayList<>();

        for (Artifact artifact : model.allArtifacts()) {
            for (String superseded : artifact.supersedes()) {
                try {
                    Artifact previous = model.get(superseded);
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.SUPERSEDES,
                        previous.ref(),
                        artifact.ref(),
                        "active",
                        "qvtr.ArtifactSupersession"
                    )));
                } catch (IllegalArgumentException ignored) {
                }
            }
        }

        for (Artifact need : artifactsOfKind(model, ArtifactKind.STAKEHOLDER_NEED)) {
            Object requirementId = need.properties().get("requirementId");
            if (requirementId == null) {
                continue;
            }
            try {
                Artifact requirement = model.latest(String.valueOf(requirementId));
                created.add(model.addTrace(new TraceLink(
                    TraceKind.ORIGIN,
                    need.ref(),
                    requirement.ref(),
                    "active",
                    "qvtr.StakeholderNeedToRequirement"
                )));
            } catch (IllegalArgumentException ignored) {
            }
        }

        for (Artifact requirement : artifactsOfKind(model, ArtifactKind.REQUIREMENT)) {
            for (Artifact architecture : artifactsOfKind(model, ArtifactKind.ARCHITECTURAL_ELEMENT)) {
                Object architectureRequirement = architecture.properties().get("requirement");
                if (architectureRequirement != null
                    && !architectureRequirement.toString().startsWith(requirement.id() + "@")) {
                    continue;
                }
                created.add(model.addTrace(new TraceLink(
                    TraceKind.REALIZES,
                    requirement.ref(),
                    architecture.ref(),
                    "active",
                    "qvtr.RequirementToArchitecture"
                )));
            }
        }

        for (Artifact architecture : artifactsOfKind(model, ArtifactKind.ARCHITECTURAL_ELEMENT)) {
            for (Artifact behavior : artifactsOfKind(model, ArtifactKind.BEHAVIOR_ELEMENT)) {
                created.add(model.addTrace(new TraceLink(
                    TraceKind.SUPPORTS,
                    architecture.ref(),
                    behavior.ref(),
                    "active",
                    "qvtr.ArchitectureToBehavior"
                )));
            }
        }

        for (Artifact behavior : artifactsOfKind(model, ArtifactKind.BEHAVIOR_ELEMENT)) {
            for (Artifact implementation : artifactsOfKind(model, ArtifactKind.IMPLEMENTATION)) {
                Object sourceBehavior = implementation.properties().get("sourceBehavior");
                if (sourceBehavior != null
                    && !sourceBehavior.toString().startsWith(behavior.id())) {
                    continue;
                }
                created.add(model.addTrace(new TraceLink(
                    TraceKind.GENERATES,
                    behavior.ref(),
                    implementation.ref(),
                    "active",
                    "qvtr.BehaviorToImplementation"
                )));
                created.add(model.addTrace(new TraceLink(
                    TraceKind.IMPLEMENTS,
                    implementation.ref(),
                    behavior.ref(),
                    "active",
                    "qvtr.BehaviorToImplementation"
                )));
            }

            for (Artifact allocation : artifactsOfKind(model, ArtifactKind.ALLOCATION)) {
                Object sourceRef = allocation.properties().get("sourceRef");
                if (sourceRef != null && sourceRef.toString().startsWith(behavior.id())) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.ALLOCATES,
                        behavior.ref(),
                        allocation.ref(),
                        "active",
                        "qvtr.Allocation"
                    )));
                }
            }

            for (Artifact deployment : artifactsOfKind(model, ArtifactKind.DEPLOYMENT)) {
                Object componentRef = deployment.properties().get("componentRef");
                if (componentRef != null && componentRef.toString().startsWith(behavior.id())) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.DEPLOYED_TO,
                        behavior.ref(),
                        deployment.ref(),
                        "active",
                        "qvtr.Deployment"
                    )));
                }
            }
        }

        for (Artifact requirement : artifactsOfKind(model, ArtifactKind.REQUIREMENT)) {
            for (Artifact test : artifactsOfKind(model, ArtifactKind.COMPONENT_TEST)) {
                created.add(model.addTrace(new TraceLink(
                    TraceKind.COVERS,
                    test.ref(),
                    requirement.ref(),
                    "active",
                    "qvtr.TestToRequirement"
                )));
            }
            for (Artifact test : artifactsOfKind(model, ArtifactKind.SCENARIO_TEST)) {
                created.add(model.addTrace(new TraceLink(
                    TraceKind.COVERS,
                    test.ref(),
                    requirement.ref(),
                    "active",
                    "qvtr.TestToRequirement"
                )));
            }
            for (Artifact plan : artifactsOfKind(model, ArtifactKind.VERIFICATION_PLAN)) {
                Object planRequirement = plan.properties().get("requirement");
                if (planRequirement != null
                    && planRequirement.toString().startsWith(requirement.id() + "@")) {
                    created.add(model.addTrace(new TraceLink(
                        TraceKind.COVERS,
                        plan.ref(),
                        requirement.ref(),
                        "active",
                        "qvtr.VerificationPlan"
                    )));
                }
            }
        }

        for (Artifact evidence : artifactsOfKind(model, ArtifactKind.VERIFICATION_EVIDENCE)) {
            if ("pass".equalsIgnoreCase(String.valueOf(evidence.properties().get("result")))) {
                for (Artifact behavior : artifactsOfKind(model, ArtifactKind.BEHAVIOR_ELEMENT)) {
                    Object evidenceBehavior = evidence.properties().get("behavior");
                    if (evidenceBehavior != null
                        && evidenceBehavior.toString().startsWith(behavior.id())) {
                        created.add(model.addTrace(new TraceLink(
                            TraceKind.VERIFIES,
                            behavior.ref(),
                            evidence.ref(),
                            "active",
                            "qvtr.VerificationEvidence"
                        )));
                    }
                }
            }
        }

        return created;
    }

    private List<Artifact> artifactsOfKind(SysMLModel model, ArtifactKind kind) {
        List<Artifact> result = new ArrayList<>();
        for (Artifact artifact : model.latestArtifacts()) {
            if (artifact.kind() == kind) {
                result.add(artifact);
            }
        }
        return result;
    }
}
