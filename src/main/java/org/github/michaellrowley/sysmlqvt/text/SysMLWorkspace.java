package org.github.michaellrowley.sysmlqvt.text;

import org.github.michaellrowley.sysmlqvt.model.Artifact;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class SysMLWorkspace {
    private final Map<String, SysMLDocument> documents = new LinkedHashMap<>();

    public void put(String uri, String text) {
        documents.put(uri, new SysMLDocument(text));
    }

    public void remove(String uri) {
        documents.remove(uri);
    }

    public SysMLDocument document(String uri) {
        return documents.get(uri);
    }

    public Map<String, SysMLDocument> documents() {
        return documents;
    }

    public SysMLModel model() {
        SysMLModel model = new SysMLModel();
        for (SysMLDocument document : documents.values()) {
            for (Artifact artifact : document.model().allArtifacts()) {
                model.addArtifact(artifact);
            }
        }
        return model;
    }

    public List<SysMLDiagnostic> diagnostics() {
        List<SysMLDiagnostic> result = new ArrayList<>();
        for (SysMLDocument document : documents.values()) {
            result.addAll(document.diagnostics());
        }
        return result;
    }
}
