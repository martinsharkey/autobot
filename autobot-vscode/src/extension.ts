import * as vscode from 'vscode';
import { AutobotAgent } from './agent';
import { ChatPanel } from './chatPanel';
import { MemoryProvider } from './memoryProvider';
import { Config } from './config';

let agent: AutobotAgent | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('AUTOBOT: Activating extension...');

    // Initialize configuration
    Config.initialize();

    // Initialize the agent
    agent = new AutobotAgent(context);

    // Register the chat webview panel
    const chatPanel = new ChatPanel(context, agent);

    // Register memory tree view
    const memoryProvider = new MemoryProvider(agent);
    vscode.window.registerTreeDataProvider('autobot.memory', memoryProvider);

    // ── Register all commands ──

    const commands = [
        vscode.commands.registerCommand('autobot.startChat', () => {
            chatPanel.show();
        }),

        vscode.commands.registerCommand('autobot.runTask', async () => {
            const goal = await vscode.window.showInputBox({
                prompt: 'What should AUTOBOT do?',
                placeHolder: 'e.g., Build a REST API for a todo app',
                ignoreFocusOut: true,
            });
            if (goal && goal.trim()) {
                chatPanel.show();
                chatPanel.sendMessage(goal);
                await agent?.runTask(goal, (chunk) => chatPanel.appendChunk(chunk));
            }
        }),

        vscode.commands.registerCommand('autobot.switchMode', async () => {
            const modes = [
                { label: '$(book) Architect', description: 'Design systems, plan architecture', slug: 'architect' },
                { label: '$(code) Coder', description: 'Write, edit, debug code', slug: 'coder' },
                { label: '$(search) Reflector', description: 'Analyze, reflect, extract insights', slug: 'reflector' },
                { label: '$(lightbulb) Learner', description: 'Research, experiment, learn', slug: 'learner' },
                { label: '$(sync) Evolver', description: 'Self-improvement, optimization', slug: 'evolver' },
            ];
            const picked = await vscode.window.showQuickPick(modes, {
                title: 'Switch AUTOBOT Mode',
                placeHolder: 'Select a mode...',
            });
            if (picked) {
                agent?.switchMode(picked.slug);
                vscode.window.showInformationMessage(`AUTOBOT switched to ${picked.label} mode`);
            }
        }),

        vscode.commands.registerCommand('autobot.showMemory', () => {
            memoryProvider.refresh();
            vscode.commands.executeCommand('workbench.view.extension.autobot-sidebar');
        }),

        vscode.commands.registerCommand('autobot.explainCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selection = editor.selection;
            const text = editor.document.getText(selection);
            if (!text) {
                vscode.window.showWarningMessage('Select code first');
                return;
            }
            chatPanel.show();
            chatPanel.sendMessage(`Explain this code:\n\`\`\`\n${text}\n\`\`\``);
            await agent?.runTask(`Explain this code in detail:\n${text}`, 
                (chunk) => chatPanel.appendChunk(chunk));
        }),

        vscode.commands.registerCommand('autobot.refactorCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selection = editor.selection;
            const text = editor.document.getText(selection);
            if (!text) {
                vscode.window.showWarningMessage('Select code first');
                return;
            }
            chatPanel.show();
            chatPanel.sendMessage(`Refactor this code:\n\`\`\`\n${text}\n\`\`\``);
            await agent?.runTask(`Refactor and improve this code:\n${text}`,
                (chunk) => chatPanel.appendChunk(chunk));
        }),

        vscode.commands.registerCommand('autobot.generateTests', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const filePath = editor.document.uri.fsPath;
            const content = editor.document.getText();
            chatPanel.show();
            chatPanel.sendMessage(`Generating tests for ${filePath}...`);
            await agent?.runTask(
                `Generate comprehensive unit tests for the code in ${filePath}:\n${content.slice(0, 8000)}`,
                (chunk) => chatPanel.appendChunk(chunk));
        }),

        vscode.commands.registerCommand('autobot.stop', () => {
            agent?.stop();
            vscode.window.showInformationMessage('AUTOBOT stopped');
        }),
    ];

    context.subscriptions.push(...commands);

    // Show welcome message
    vscode.window.showInformationMessage('AUTOBOT ready! Press Ctrl+Alt+A to start chatting.');

    console.log('AUTOBOT: Extension activated.');
}

export function deactivate() {
    agent?.dispose();
    console.log('AUTOBOT: Deactivated.');
}
