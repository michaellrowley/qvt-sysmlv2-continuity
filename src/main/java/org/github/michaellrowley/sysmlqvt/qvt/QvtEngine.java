package org.github.michaellrowley.sysmlqvt.qvt;

import org.github.michaellrowley.sysmlqvt.model.SysMLModel;

import java.nio.file.Path;

public interface QvtEngine {
    QvtResult execute(SysMLModel model, Path transformation);
}
