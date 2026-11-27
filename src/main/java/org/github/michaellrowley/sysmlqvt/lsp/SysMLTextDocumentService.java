package org.github.michaellrowley.sysmlqvt.lsp;

import org.eclipse.lsp4j.CodeAction;
import org.eclipse.lsp4j.CodeActionKind;
import org.eclipse.lsp4j.CodeActionParams;
import org.eclipse.lsp4j.CompletionItem;
import org.eclipse.lsp4j.CompletionItemKind;
import org.eclipse.lsp4j.CompletionParams;
import org.eclipse.lsp4j.DiagnosticSeverity;
import org.eclipse.lsp4j.DidChangeTextDocumentParams;
import org.eclipse.lsp4j.DidCloseTextDocumentParams;
import org.eclipse.lsp4j.DidOpenTextDocumentParams;
import org.eclipse.lsp4j.DidSaveTextDocumentParams;
import org.eclipse.lsp4j.Hover;
import org.eclipse.lsp4j.HoverParams;
import org.eclipse.lsp4j.MarkupContent;
import org.eclipse.lsp4j.MarkupKind;
import org.eclipse.lsp4j.Position;
import org.eclipse.lsp4j.PublishDiagnosticsParams;
import org.eclipse.lsp4j.Range;
import org.eclipse.lsp4j.TextDocumentContentChangeEvent;
import org.eclipse.lsp4j.TextEdit;
import org.eclipse.lsp4j.WorkspaceEdit;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.eclipse.lsp4j.services.LanguageClient;
import org.eclipse.lsp4j.services.TextDocumentService;
import org.github.michaellrowley.sysmlqvt.template.SysMLTemplateLibrary;
import org.github.michaellrowley.sysmlqvt.text.SysMLDiagnostic;
import org.github.michaellrowley.sysmlqvt.text.SysMLDocument;
import org.github.michaellrowley.sysmlqvt.text.SysMLWorkspace;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public final class SysMLTextDocumentService implements TextDocumentService {
    private final SysMLWorkspace workspace;
    private volatile LanguageClient client;

    public SysMLTextDocumentService(SysMLWorkspace workspace) {
        this.workspace = workspace;
    }

    public void setClient(LanguageClient client) {
        this.client = client;
    }

    @Override
    public void didOpen(DidOpenTextDocumentParams params) {
        String uri = params.getTextDocument().getUri();
        workspace.put(uri, params.getTextDocument().getText());
        publish(uri);
    }

    @Override
    public void didChange(DidChangeTextDocumentParams params) {
        String uri = params.getTextDocument().getUri();
        String text = "";
        for (TextDocumentContentChangeEvent change : params.getContentChanges()) {
            text = change.getText();
        }
        workspace.put(uri, text);
        publish(uri);
    }

    @Override
    public void didClose(DidCloseTextDocumentParams params) {
        String uri = params.getTextDocument().getUri();
        workspace.remove(uri);
        if (client != null) {
            client.publishDiagnostics(new PublishDiagnosticsParams(uri, List.of()));
        }
    }

    @Override
    public void didSave(DidSaveTextDocumentParams params) {
        publish(params.getTextDocument().getUri());
    }

    @Override
    public CompletableFuture<Either<List<CompletionItem>, org.eclipse.lsp4j.CompletionList>> completion(
        CompletionParams params
    ) {
        List<CompletionItem> items = new ArrayList<>();
        for (String keyword : List.of(
            "package",
            "concern def",
            "requirement def",
            "part def",
            "interface",
            "interface def",
            "port",
            "port def",
            "connection",
            "action def",
            "state def",
            "allocation",
            "verification def"
        )) {
            CompletionItem item = new CompletionItem(keyword);
            item.setKind(CompletionItemKind.Keyword);
            item.setDetail("SysML continuity template keyword");
            items.add(item);
        }
        return CompletableFuture.completedFuture(Either.forLeft(items));
    }

    @Override
    public CompletableFuture<Hover> hover(HoverParams params) {
        String uri = params.getTextDocument().getUri();
        SysMLDocument document = workspace.document(uri);
        if (document == null) {
            return CompletableFuture.completedFuture(new Hover(List.of()));
        }

        Position position = params.getPosition();
        String word = wordAt(document.text(), position.getLine(), position.getCharacter());
        MarkupContent content = new MarkupContent(
            MarkupKind.MARKDOWN,
            word.isEmpty()
                ? "SysML v2 continuity source"
                : "```\n" + word + "\n```"
        );
        return CompletableFuture.completedFuture(new Hover(
            content,
            new Range(
                new Position(position.getLine(), position.getCharacter()),
                new Position(position.getLine(), position.getCharacter())
            )
        ));
    }

    @Override
    public CompletableFuture<List<Either<org.eclipse.lsp4j.Command, CodeAction>>> codeAction(
        CodeActionParams params
    ) {
        String uri = params.getTextDocument().getUri();
        SysMLTemplateLibrary templates = new SysMLTemplateLibrary();

        CodeAction battery = new CodeAction("Insert battery lifecycle template");
        battery.setKind(CodeActionKind.RefactorRewrite);
        battery.setEdit(templateEdit(uri, templates.batteryLifecycle()));

        CodeAction generic = new CodeAction("Insert generic lifecycle template");
        generic.setKind(CodeActionKind.RefactorRewrite);
        generic.setEdit(templateEdit(uri, templates.genericNeed()));

        List<Either<org.eclipse.lsp4j.Command, CodeAction>> actions = List.of(
            Either.forRight(battery),
            Either.forRight(generic)
        );
        return CompletableFuture.completedFuture(actions);
    }

    private WorkspaceEdit templateEdit(String uri, String template) {
        TextEdit edit = new TextEdit(
            new Range(
                new Position(0, 0),
                new Position(0, 0)
            ),
            template
        );
        Map<String, List<TextEdit>> changes = new LinkedHashMap<>();
        changes.put(uri, List.of(edit));
        return new WorkspaceEdit(changes);
    }

    private void publish(String uri) {
        if (client == null) {
            return;
        }
        SysMLDocument document = workspace.document(uri);
        if (document == null) {
            return;
        }
        List<org.eclipse.lsp4j.Diagnostic> diagnostics = new ArrayList<>();
        for (SysMLDiagnostic diagnostic : document.diagnostics()) {
            DiagnosticSeverity severity =
                "error".equals(diagnostic.severity())
                    ? DiagnosticSeverity.Error
                    : DiagnosticSeverity.Warning;
            org.eclipse.lsp4j.Diagnostic item = new org.eclipse.lsp4j.Diagnostic(
                new Range(
                    new Position(Math.max(0, diagnostic.line() - 1), diagnostic.character()),
                    new Position(Math.max(0, diagnostic.line() - 1), diagnostic.character())
                ),
                diagnostic.message(),
                severity,
                "sysml-continuity"
            );
            diagnostics.add(item);
        }
        client.publishDiagnostics(new PublishDiagnosticsParams(uri, diagnostics));
    }

    private String wordAt(String text, int line, int character) {
        String[] lines = text.split("\\R", -1);
        if (line < 0 || line >= lines.length) {
            return "";
        }
        String lineText = lines[line];
        int start = Math.min(character, lineText.length());
        int end = start;
        while (start > 0
            && Character.isLetterOrDigit(lineText.charAt(start - 1))) {
            start--;
        }
        while (end < lineText.length()
            && Character.isLetterOrDigit(lineText.charAt(end))) {
            end++;
        }
        if (start == end) {
            return "";
        }
        return lineText.substring(start, end);
    }
}
