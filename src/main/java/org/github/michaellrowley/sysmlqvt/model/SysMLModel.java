package org.github.michaellrowley.sysmlqvt.model;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class SysMLModel {
    private final Map<String, Artifact> latest = new LinkedHashMap<>();
    private final Map<String, Artifact> revisions = new LinkedHashMap<>();
    private final Map<String, TraceLink> traces = new LinkedHashMap<>();
    private final Map<String, Baseline> baselines = new LinkedHashMap<>();

    public Artifact addArtifact(Artifact artifact) {
        String revisionKey = artifact.ref();
        Artifact existing = revisions.putIfAbsent(revisionKey, artifact);
        Artifact stored = existing == null ? artifact : existing;
        Artifact current = latest.get(artifact.id());
        if (current == null || artifact.revision() >= current.revision()) {
            latest.put(artifact.id(), stored);
        }
        return stored;
    }

    public Artifact latest(String id) {
        Artifact artifact = latest.get(id);
        if (artifact == null) {
            throw new IllegalArgumentException("Unknown artifact: " + id);
        }
        return artifact;
    }

    public Artifact get(String ref) {
        if (ref.contains("@")) {
            Artifact artifact = revisions.get(ref);
            if (artifact == null) {
                throw new IllegalArgumentException("Unknown artifact revision: " + ref);
            }
            return artifact;
        }
        return latest(ref);
    }

    public Collection<Artifact> latestArtifacts() {
        return latest.values();
    }

    public Collection<Artifact> allArtifacts() {
        return revisions.values();
    }

    public TraceLink addTrace(TraceLink trace) {
        return traces.computeIfAbsent(trace.key(), key -> trace);
    }

    public Collection<TraceLink> activeTraces() {
        List<TraceLink> active = new ArrayList<>();
        for (TraceLink trace : traces.values()) {
            if ("active".equals(trace.status())) {
                active.add(trace);
            }
        }
        return active;
    }

    public Baseline addBaseline(Baseline baseline) {
        baselines.put(baseline.id(), baseline);
        return baseline;
    }

    public Baseline baseline(String id) {
        Baseline baseline = baselines.get(id);
        if (baseline == null) {
            throw new IllegalArgumentException("Unknown baseline: " + id);
        }
        return baseline;
    }

    public Collection<Baseline> baselines() {
        return baselines.values();
    }

    public Baseline baselineThread(String requirementId) {
        Artifact requirement = latest(requirementId);
        Set<String> visited = new LinkedHashSet<>();
        List<String> queue = new ArrayList<>();
        visited.add(requirement.ref());
        queue.add(requirement.ref());

        for (int index = 0; index < queue.size(); index++) {
            String current = queue.get(index);
            for (TraceLink trace : activeTraces()) {
                String neighbor = null;
                if (trace.source().equals(current)) {
                    neighbor = trace.target();
                } else if (trace.target().equals(current)) {
                    neighbor = trace.source();
                }
                if (neighbor != null && visited.add(neighbor)) {
                    queue.add(neighbor);
                }
            }
        }

        List<String> artifactRefs = new ArrayList<>(visited);
        artifactRefs.sort(String::compareTo);
        List<String> traceKeys = new ArrayList<>();
        for (TraceLink trace : activeTraces()) {
            if (visited.contains(trace.source()) && visited.contains(trace.target())) {
                traceKeys.add(trace.key());
            }
        }
        traceKeys.sort(String::compareTo);

        String digest = sha256(requirement.ref() + "|" + artifactRefs + "|" + traceKeys);
        String id = "BL-" + digest.substring(0, 16);
        Baseline baseline = new Baseline(
            id,
            requirement.ref(),
            artifactRefs,
            traceKeys,
            digest
        );
        return addBaseline(baseline);
    }

    private static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder();
            for (byte item : bytes) {
                hex.append(String.format("%02x", item));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }
}
