package org.github.michaellrowley.sysmlqvt.qvt;

import org.eclipse.emf.common.util.Diagnostic;
import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.resource.impl.ResourceSetImpl;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;
import org.eclipse.m2m.qvt.oml.BasicModelExtent;
import org.eclipse.m2m.qvt.oml.ExecutionContextImpl;
import org.eclipse.m2m.qvt.oml.ExecutionDiagnostic;
import org.eclipse.m2m.qvt.oml.ModelExtent;
import org.eclipse.m2m.qvt.oml.TransformationExecutor;
import org.github.michaellrowley.sysmlqvt.model.SysMLModel;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class EclipseQvtEngine implements QvtEngine {
    private final EcoreBridge bridge = new EcoreBridge();

    @Override
    public QvtResult execute(SysMLModel model, Path transformation) {
        List<String> diagnostics = new ArrayList<>();
        if (!transformation.toFile().isFile()) {
            diagnostics.add("QVTo transformation not found: " + transformation);
            return new QvtResult(model, false, diagnostics);
        }

        try {
            ResourceSet resourceSet = new ResourceSetImpl();
            resourceSet.getResourceFactoryRegistry()
                .getExtensionToFactoryMap()
                .put("xmi", new XMIResourceFactoryImpl());
            resourceSet.getPackageRegistry()
                .put(EcoreMetamodel.SYSML_NS, EcoreMetamodel.sysmlPackage());
            resourceSet.getPackageRegistry()
                .put(EcoreMetamodel.CONTINUITY_NS, EcoreMetamodel.continuityPackage());

            List<EObject> sysmlObjects =
                bridge.sysmlObjects(resourceSet, model);
            List<EObject> continuityObjects =
                bridge.continuityObjects(resourceSet);
            ModelExtent sysmlExtent = new BasicModelExtent(sysmlObjects);
            ModelExtent continuityExtent = new BasicModelExtent(continuityObjects);

            URI transformationUri =
                URI.createFileURI(transformation.toAbsolutePath().toFile().getAbsolutePath());
            TransformationExecutor executor = new TransformationExecutor(transformationUri);

            org.eclipse.emf.common.util.Diagnostic loadDiagnostic =
                executor.loadTransformation();
            if (loadDiagnostic.getSeverity() >= Diagnostic.ERROR) {
                diagnostics.add("Eclipse QVTd load failed: " + loadDiagnostic.getMessage());
                for (Diagnostic child : loadDiagnostic.getChildren()) {
                    diagnostics.add("  " + child.getMessage());
                }
                executor.cleanup();
                return new QvtResult(model, false, diagnostics);
            }

            ExecutionContextImpl context = new ExecutionContextImpl();
            context.setConfigProperty("keepModeling", true);

            ExecutionDiagnostic result = executor.execute(
                context,
                new ModelExtent[]{sysmlExtent, continuityExtent}
            );

            boolean successful = result.getSeverity() == Diagnostic.OK;
            if (!successful) {
                diagnostics.add(
                    "Eclipse QVTd failed: " + result.getMessage()
                );
                for (Diagnostic child : result.getChildren()) {
                    diagnostics.add("  " + child.getMessage());
                }
            } else {
                bridge.mergeFrom(model, sysmlExtent.getContents());
                new LifecycleEngine(model).synchronizeOperationalScope();
            }

            return new QvtResult(model, successful, diagnostics);
        } catch (RuntimeException | LinkageError exception) {
            diagnostics.add(
                "Eclipse QVTd could not execute " + transformation +
                    ": " + exception.getMessage()
            );
            return new QvtResult(model, false, diagnostics);
        }
    }

}
