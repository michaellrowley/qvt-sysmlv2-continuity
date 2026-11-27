package org.github.michaellrowley.sysmlqvt.crud;

import java.util.List;

public record CrudResult(
    CrudOperator operator,
    boolean successful,
    CrudEntity entity,
    List<CrudEntity> entities,
    List<String> outputPaths,
    String message
) {
    public static CrudResult single(
        CrudOperator operator,
        CrudEntity entity,
        List<String> outputPaths,
        String message
    ) {
        return new CrudResult(
            operator,
            true,
            entity,
            entity == null ? List.of() : List.of(entity),
            outputPaths,
            message
        );
    }

    public static CrudResult multiple(
        CrudOperator operator,
        List<CrudEntity> entities,
        String message
    ) {
        return new CrudResult(
            operator,
            true,
            null,
            entities,
            List.of(),
            message
        );
    }

    public static CrudResult failure(CrudOperator operator, String message) {
        return new CrudResult(
            operator,
            false,
            null,
            List.of(),
            List.of(),
            message
        );
    }
}
