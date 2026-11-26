# QVT sources

`LifecycleOperational.qvto` is an executable Eclipse QVT-OML transformation.
It accepts the in-memory `SYSML` and `CONTINUITY` dynamic metamodels and
revises stakeholder needs into requirements.

The Java application converts repository `.sysml` text into EMF/Ecore objects,
runs Eclipse QVT-OML, and converts the revised model back to SysML text.

`ContinuityRelations.qvtr` records the declarative continuity relation
contract. The Java `ContinuityRelations` implementation currently enforces
that contract and materializes trace links. Direct execution of
QVT-Relations by Eclipse QVTd is a separate integration step.
