package org.github.michaellrowley.sysmlqvt.lsp;

import org.eclipse.lsp4j.CompletionOptions;
import org.eclipse.lsp4j.InitializeParams;
import org.eclipse.lsp4j.InitializeResult;
import org.eclipse.lsp4j.ServerCapabilities;
import org.eclipse.lsp4j.TextDocumentSyncKind;
import org.eclipse.lsp4j.services.LanguageClient;
import org.eclipse.lsp4j.services.LanguageClientAware;
import org.eclipse.lsp4j.services.LanguageServer;
import org.eclipse.lsp4j.services.TextDocumentService;
import org.eclipse.lsp4j.services.WorkspaceService;
import org.github.michaellrowley.sysmlqvt.text.SysMLWorkspace;

import java.util.List;
import java.util.concurrent.CompletableFuture;

public final class SysMLLanguageServer
    implements LanguageServer, LanguageClientAware {

    private final SysMLWorkspace workspace = new SysMLWorkspace();
    private final SysMLTextDocumentService textService =
        new SysMLTextDocumentService(workspace);
    private final SysMLWorkspaceService workspaceService =
        new SysMLWorkspaceService();
    private volatile boolean shutdown;

    @Override
    public CompletableFuture<InitializeResult> initialize(InitializeParams params) {
        ServerCapabilities capabilities = new ServerCapabilities();
        capabilities.setTextDocumentSync(TextDocumentSyncKind.Full);
        capabilities.setCompletionProvider(new CompletionOptions(false, List.of()));
        capabilities.setHoverProvider(true);
        capabilities.setCodeActionProvider(true);
        return CompletableFuture.completedFuture(
            new InitializeResult(capabilities)
        );
    }

    @Override
    public CompletableFuture<Object> shutdown() {
        shutdown = true;
        return CompletableFuture.completedFuture(null);
    }

    @Override
    public void exit() {
        if (!shutdown) {
            System.exit(1);
        }
        System.exit(0);
    }

    @Override
    public TextDocumentService getTextDocumentService() {
        return textService;
    }

    @Override
    public WorkspaceService getWorkspaceService() {
        return workspaceService;
    }

    @Override
    public void connect(LanguageClient client) {
        textService.setClient(client);
    }
}
