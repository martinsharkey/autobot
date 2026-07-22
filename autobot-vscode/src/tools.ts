import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';
import { AgentMode, AGENT_MODES } from './config';

interface ToolResult {
    success: boolean;
    result?: string;
    error?: string;
}

interface ToolDef {
    name: string;
    description: string;
    parameters: any;
    handler: (...args: any[]) => Promise<ToolResult>;
    group: string;
}

export class ToolSystem {
    private tools: Map<string, ToolDef> = new Map();

    constructor() {
        this.registerCoreTools();
    }

    getDefinitions(mode: AgentMode): any[] {
        const modeConf = AGENT_MODES[mode];
        const allowed = new Set<string>();
        for (const [group, enabled] of Object.entries(modeConf.groups)) {
            if (enabled) allowed.add(group);
        }

        return Array.from(this.tools.values())
            .filter(t => allowed.has(t.group))
            .map(t => ({
                type: 'function',
                function: {
                    name: t.name,
                    description: t.description,
                    parameters: t.parameters,
                },
            }));
    }

    async execute(name: string, args: any, mode: AgentMode): Promise<ToolResult> {
        const tool = this.tools.get(name);
        if (!tool) return { success: false, error: `Unknown tool: ${name}` };

        const modeConf = AGENT_MODES[mode];
        if (!(modeConf.groups as any)[tool.group]) {
            return { success: false, error: `Tool '${name}' not allowed in ${mode} mode` };
        }

        try {
            return await tool.handler(args);
        } catch (e: any) {
            return { success: false, error: e.message };
        }
    }

    private register(name: string, description: string, parameters: any, handler: (...args: any[]) => Promise<ToolResult>, group: string) {
        this.tools.set(name, { name, description, parameters, handler, group });
    }

    private registerCoreTools() {
        // ── Read tools ──
        this.register('read_file', 'Read the contents of a file',
            { type: 'object', properties: { path: { type: 'string' } }, required: ['path'] },
            async (args) => {
                const filePath = path.resolve(args.path);
                if (!fs.existsSync(filePath)) return { success: false, error: 'File not found' };
                const stat = fs.statSync(filePath);
                if (stat.isDirectory()) return { success: false, error: 'Is a directory' };
                if (stat.size > 500000) return { success: false, error: 'File too large (>500KB)' };
                const content = fs.readFileSync(filePath, 'utf-8');
                return { success: true, result: content };
            }, 'read');

        this.register('search_files', 'Search for files by glob pattern',
            { type: 'object', properties: { pattern: { type: 'string' } }, required: ['pattern'] },
            async (args) => {
                const workspaceFolders = vscode.workspace.workspaceFolders;
                if (!workspaceFolders) return { success: false, error: 'No workspace open' };
                const root = workspaceFolders[0].uri.fsPath;
                const glob = new vscode.RelativePattern(root, args.pattern);
                const files = await vscode.workspace.findFiles(glob, undefined, 200);
                return { success: true, result: files.map(f => f.fsPath).join('\n') };
            }, 'read');

        this.register('grep_search', 'Search file contents using regex',
            { type: 'object', properties: { pattern: { type: 'string' }, path: { type: 'string' } }, required: ['pattern'] },
            async (args) => {
                const workspaceFolders = vscode.workspace.workspaceFolders;
                if (!workspaceFolders) return { success: false, error: 'No workspace open' };
                try {
                    const root = workspaceFolders[0].uri.fsPath;
                    const grepPath = args.path ? path.resolve(root, args.path) : root;
                    const cmd = `grep -rn "${args.pattern}" "${grepPath}" --include="*.py" --include="*.ts" --include="*.js" --include="*.tsx" --include="*.json" --include="*.yaml" --include="*.md" 2>/dev/null | head -100`;
                    const result = execSync(cmd, { cwd: root, timeout: 15000 }).toString();
                    return { success: true, result: result || 'No matches' };
                } catch (e: any) {
                    return { success: false, error: e.message };
                }
            }, 'read');

        this.register('list_files', 'List files in a directory',
            { type: 'object', properties: { path: { type: 'string' }, recursive: { type: 'boolean' } }, required: ['path'] },
            async (args) => {
                const dirPath = path.resolve(args.path);
                if (!fs.existsSync(dirPath)) return { success: false, error: 'Directory not found' };
                if (args.recursive) {
                    const entries: string[] = [];
                    const walkDir = (dir: string, prefix: string = '') => {
                        const items = fs.readdirSync(dir, { withFileTypes: true });
                        for (const item of items) {
                            entries.push(prefix + item.name);
                            if (item.isDirectory()) walkDir(path.join(dir, item.name), prefix + item.name + '/');
                        }
                    };
                    walkDir(dirPath);
                    return { success: true, result: entries.slice(0, 200).join('\n') };
                }
                const items = fs.readdirSync(dirPath);
                return { success: true, result: items.join('\n') };
            }, 'read');

        // ── Edit tools ──
        this.register('write_to_file', 'Write content to a file (creates/overwrites)',
            { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' } }, required: ['path', 'content'] },
            async (args) => {
                const filePath = path.resolve(args.path);
                fs.mkdirSync(path.dirname(filePath), { recursive: true });
                fs.writeFileSync(filePath, args.content, 'utf-8');
                return { success: true, result: `Wrote ${args.content.length} chars to ${args.path}` };
            }, 'edit');

        this.register('edit_file', 'Find and replace text in a file',
            { type: 'object', properties: { path: { type: 'string' }, old_string: { type: 'string' }, new_string: { type: 'string' } }, required: ['path', 'old_string', 'new_string'] },
            async (args) => {
                const filePath = path.resolve(args.path);
                if (!fs.existsSync(filePath)) return { success: false, error: 'File not found' };
                let content = fs.readFileSync(filePath, 'utf-8');
                if (!content.includes(args.old_string)) return { success: false, error: 'String not found' };
                content = content.replace(args.old_string, args.new_string);
                fs.writeFileSync(filePath, content, 'utf-8');
                return { success: true, result: `Edited ${args.path}` };
            }, 'edit');

        // ── Command tools ──
        this.register('execute_command', 'Run a shell command',
            { type: 'object', properties: { command: { type: 'string' }, timeout: { type: 'number' } }, required: ['command'] },
            async (args) => {
                const workspaceFolders = vscode.workspace.workspaceFolders;
                const cwd = workspaceFolders ? workspaceFolders[0].uri.fsPath : process.cwd();
                try {
                    const result = execSync(args.command, {
                        cwd,
                        timeout: (args.timeout || 30) * 1000,
                        maxBuffer: 1024 * 1024,
                    }).toString();
                    return { success: true, result: result.slice(-10000) || '(no output)' };
                } catch (e: any) {
                    return { success: true, result: e.stdout?.toString().slice(-5000) || e.message };
                }
            }, 'command');

        // ── Learning/Memory tools ──
        this.register('think', 'Think step by step (no side effects)',
            { type: 'object', properties: { thought: { type: 'string' } }, required: ['thought'] },
            async (args) => ({ success: true, result: `Thinking: ${args.thought.slice(0, 200)}...` }), 'read');

        this.register('attempt_completion', 'Signal that the task is complete',
            { type: 'object', properties: { result: { type: 'string' } }, required: ['result'] },
            async (args) => ({ success: true, result: `Task complete: ${args.result}` }), 'read');

        this.register('ask_question', 'Ask the user a question',
            { type: 'object', properties: { question: { type: 'string' } }, required: ['question'] },
            async (args) => {
                const answer = await vscode.window.showInputBox({
                    prompt: args.question,
                    ignoreFocusOut: true,
                });
                return { success: true, result: answer || '(no answer)' };
            }, 'read');

        this.register('open_file', 'Open a file in the editor',
            { type: 'object', properties: { path: { type: 'string' } }, required: ['path'] },
            async (args) => {
                const filePath = path.resolve(args.path);
                const doc = await vscode.workspace.openTextDocument(filePath);
                await vscode.window.showTextDocument(doc);
                return { success: true, result: `Opened ${args.path}` };
            }, 'read');
    }
}
