package org.github.michaellrowley.sysmlqvt.qvt;

import org.github.michaellrowley.sysmlqvt.model.SysMLModel;

import java.util.List;

public record QvtResult(
    SysMLModel model,
    boolean successful,
    List<String> diagnostics
) {
}
