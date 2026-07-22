import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { AutobotAgent } from './agent';

export class ChatPanel {
    private panel: vscode.WebviewPanel | undefined;
    private disposables: vscode.Disposable[] = [];
    private htmlContent: string;

    constructor(
        private context: vscode.ExtensionContext,
        private agent: AutobotAgent
    ) {
        const htmlPath = path.join(context.extensionPath, 'src', 'chatPanel.html');
        this.htmlContent = fs.readFileSync(htmlPath, 'utf-8');
    }

    show() {
        if (this.panel) {
            this.panel.reveal(vscode.ViewColumn.Beside);
            return;
        }

        this.panel = vscode.window.createWebviewPanel(
            'autobot.chat',
            'AUTOBOT Chat',
            vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );

        this.panel.webview.html = this.htmlContent;

        this.panel.onDidDispose(() => {
            this.panel = undefined;
            for (const d of this.disposables) {
                d.dispose();
            }
            this.disposables = [];
        }, null, this.disposables);

        this.panel.webview.onDidReceiveMessage(
            async (message: { command: string; text?: string }) => {
                switch (message.command) {
                    case 'sendMessage':
                        if (message.text && message.text.trim()) {
                            await this.agent.runTask(message.text, (chunk: string) => {
                                this.appendChunk(chunk);
                            });
                        }
                        break;
                    case 'stop':
                        this.agent.stop();
                        break;
                }
            },
            null,
            this.disposables
        );
    }

    sendMessage(text: string) {
        this.panel?.webview.postMessage({ command: 'addUserMessage', text });
    }

    appendChunk(chunk: string) {
        this.panel?.webview.postMessage({ command: 'appendChunk', text: chunk });
    }
}
