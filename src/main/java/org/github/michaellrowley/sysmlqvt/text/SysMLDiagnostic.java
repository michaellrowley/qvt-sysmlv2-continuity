package org.github.michaellrowley.sysmlqvt.text;

public record SysMLDiagnostic(
    int line,
    int character,
    String severity,
    String message
) {
}
