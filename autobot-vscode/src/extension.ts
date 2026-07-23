import * as vscode from 'vscode';
import { AgentClient } from './agentClient';
import { ChatPanel } from './chatPanel';
import { MemoryProvider } from './memoryProvider';
import { Config } from './config';

let client: AgentClient | undefined;
let chatPanel: ChatPanel | undefined;
let memoryProvider: MemoryProvider | undefined;
let statusBarItem: vscode.StatusBarItem | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('AUTOBOT v2.0 activating...');
    Config.initialize(context);
    client = new AgentClient();
    chatPanel = new ChatPanel(context, client);
    memoryProvider = new MemoryProvider(client);

    vscode.window.registerTreeDataProvider('autobot.memory', memoryProvider);

    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.text = '$(rocket) AUTOBOT';
    statusBarItem.command = 'autobot.startChat';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    const commands = [
        vscode.commands.registerCommand('autobot.startChat', () => chatPanel?.show()),
        vscode.commands.registerCommand('autobot.runTask', async () => {
            const goal = await vscode.window.showInputBox({
                prompt: 'What should AUTOBOT do autonomously?',
                placeHolder: 'e.g., Build a REST API for a todo app with tests',
                ignoreFocusOut: true,
            });
            if (goal && goal.trim()) {
                chatPanel?.show();
                await chatPanel?.runTask(goal);
            }
        }),
        vscode.commands.registerCommand('autobot.stopAgent', async () => {
            await client?.stopAgent();
            vscode.window.showInformationMessage('AUTOBOT stopped');
        }),
        vscode.commands.registerCommand('autobot.switchMode', async () => {
            const modes = [
                { label: '$(book) Architect', description: 'Design systems, plan architecture', slug: 'architect' },
                { label: '$(code) Coder', description: 'Write, edit, debug code', slug: 'coder' },
                { label: '$(search) Reflector', description: 'Analyze, reflect, extract insights', slug: 'reflector' },
                { label: '$(lightbulb) Learner', description: 'Research, experiment, learn', slug: 'learner' },
                { label: '$(sync) Evolver', description: 'Self-improvement, optimization', slug: 'evolver' },
            ];
            const picked = await vscode.window.showQuickPick(modes, { title: 'Switch AUTOBOT Mode' });
            if (picked) {
                chatPanel?.setMode(picked.slug);
                vscode.window.showInformationMessage(`AUTOBOT: ${picked.label}`);
            }
        }),
        vscode.commands.registerCommand('autobot.showMemory', () => {
            memoryProvider?.refresh();
            vscode.commands.executeCommand('workbench.view.extension.autobot-sidebar');
        }),
        vscode.commands.registerCommand('autobot.explainCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const text = editor.document.getText(editor.selection) || editor.document.getText();
            chatPanel?.show();
            await chatPanel?.runTask(`Explain this code in detail:\n\`\`\`\n${text.slice(0, 12000)}\n\`\`\``);
        }),
        vscode.commands.registerCommand('autobot.refactorCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const text = editor.document.getText(editor.selection) || editor.document.getText();
            chatPanel?.show();
            await chatPanel?.runTask(`Refactor and improve this code:\n\`\`\`\n${text.slice(0, 12000)}\n\`\`\``);
        }),
        vscode.commands.registerCommand('autobot.generateTests', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const text = editor.document.getText();
            chatPanel?.show();
            await chatPanel?.runTask(`Generate comprehensive unit tests for:\n\`\`\`\n${text.slice(0, 12000)}\n\`\`\``);
        }),
    ];

    context.subscriptions.push(...commands);
    vscode.window.showInformationMessage('AUTOBOT ready. Press Ctrl+Alt+A to start.');
    console.log('AUTOBOT activated');
}

export function deactivate() {
    client?.dispose();
    chatPanel?.dispose();
    statusBarItem?.dispose();
    console.log('AUTOBOT deactivated');
}
