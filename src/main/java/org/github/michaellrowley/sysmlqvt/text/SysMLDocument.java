package org.github.michaellrowley.sysmlqvt.text;

import org.github.michaellrowley.sysmlqvt.model.SysMLModel;

import java.util.ArrayList;
import java.util.List;

public final class SysMLDocument {
    private String text;
    private SysMLModel model;
    private List<SysMLDiagnostic> diagnostics;

    public SysMLDocument(String text) {
        update(text);
    }

    public synchronized void update(String newText) {
        text = newText == null ? "" : newText;
        SysMLParser.ParseResult result =
            new SysMLParser().parse("", text);
        model = result.model();
        diagnostics = new ArrayList<>(result.diagnostics());
    }

    public String text() {
        return text;
    }

    public SysMLModel model() {
        return model;
    }

    public List<SysMLDiagnostic> diagnostics() {
        return diagnostics;
    }
}
