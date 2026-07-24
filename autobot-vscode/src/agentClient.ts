import * as vscode from 'vscode';
import { spawn } from 'child_process';
import * as path from 'path';

export interface AgentMessage {
    role: 'user' | 'assistant' | 'tool' | 'system';
    content?: string;
    toolCalls?: any[];
}

export interface TaskEvent {
    type: string;
    text?: string;
    count?: number;
    max?: number;
    name?: string;
    args?: any;
}

export class AgentClient {
    private baseUrl: string;
    private apiKey: string;
    private currentTaskId: string | undefined;
    private childProcess: ReturnType<typeof spawn> | undefined;
    private onEvent: ((e: TaskEvent) => void) | undefined;
    private pendingRequests: Map<string, { resolve: (value: any) => void; reject: (reason: any) => void }> = new Map();
    private requestId: number = 0;
    private responseBuffer: string = '';

    constructor() {
        const cfg = vscode.workspace.getConfiguration('autobot');
        this.baseUrl = cfg.get<string>('gatewayUrl', 'http://127.0.0.1:8001').replace(/\/$/, '');
        this.apiKey = cfg.get<string>('gatewayApiKey', 'changeme');
    }

    private getPythonCommand(): string {
        const cfg = vscode.workspace.getConfiguration('autobot');
        const pythonPath = cfg.get<string>('pythonPath', 'python');
        return pythonPath;
    }

    private getAutobotHome(): string {
        const cfg = vscode.workspace.getConfiguration('autobot');
        const autobotHome = cfg.get<string>('autobotHome', '');
        if (autobotHome) return autobotHome;
        
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (workspaceFolder) {
            return workspaceFolder.uri.fsPath;
        }
        return vscode.env.appRoot;
    }

    async checkHealth(): Promise<boolean> {
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 5000);
            const resp = await fetch(`${this.baseUrl}/v1/health`, {
                headers: { Authorization: `Bearer ${this.apiKey}` },
                signal: controller.signal as any,
            });
            clearTimeout(timeout);
            return resp.ok;
        } catch {
            return false;
        }
    }

    async startGateway(): Promise<void> {
        const pythonCmd = this.getPythonCommand();
        const autobotHome = this.getAutobotHome();
        const mainPath = path.join(autobotHome, 'main.py');
        
        console.log(`[AUTOBOT] Starting gateway server: ${pythonCmd} ${mainPath}`);
        const gatewayProcess = spawn(pythonCmd, ['main.py'], {
            cwd: autobotHome,
            env: {
                ...process.env,
                PYTHONPATH: autobotHome,
                AUTOBOT_HOME: autobotHome,
            },
            detached: true,
            stdio: 'ignore'
        });
        gatewayProcess.unref();
        
        for (let i = 0; i < 20; i++) {
            await new Promise(r => setTimeout(r, 500));
            if (await this.checkHealth()) {
                console.log(`[AUTOBOT] Gateway server is now healthy`);
                return;
            }
        }
        console.error(`[AUTOBOT] Gateway server failed to start or respond to health check`);
    }

    async runTask(goal: string, mode: string, onEvent: (e: TaskEvent) => void): Promise<string> {
        this.onEvent = onEvent;
        const pythonCmd = this.getPythonCommand();
        const autobotHome = this.getAutobotHome();

        return new Promise((resolve, reject) => {
            try {
                const child = spawn(pythonCmd, ['-m', 'autobot.stdio_agent'], {
                    cwd: autobotHome,
                    env: {
                        ...process.env,
                        PYTHONPATH: autobotHome,
                        AUTOBOT_HOME: autobotHome,
                    },
                });

                this.childProcess = child;
                this.currentTaskId = `task_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

                let buffer = '';
                let initReceived = false;
                let completed = false;

                const finish = (err?: Error) => {
                    if (completed) return;
                    completed = true;
                    try { child.kill(); } catch {}
                    this.childProcess = undefined;
                    if (err) reject(err);
                    else resolve('');
                };

                child.stdout.on('data', (data) => {
                    buffer += data.toString();
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed) continue;
                        try {
                            const response = JSON.parse(trimmed);
                            if (!initReceived && response.id === 'init') {
                                initReceived = true;
                                const request = {
                                    id: this.currentTaskId,
                                    method: 'run',
                                    params: { goal, mode, max_loops: 50 },
                                };
                                child.stdin.write(JSON.stringify(request) + '\n');
                                onEvent({ type: 'started', text: goal });
                                continue;
                            }
                            if (response.event) {
                                onEvent(response.event);
                                continue;
                            }
                            if (response.error) {
                                onEvent({ type: 'error', text: response.error });
                                finish(new Error(response.error));
                            } else if (response.result) {
                                const result = response.result;
                                if (result.status === 'ok') {
                                    onEvent({ type: 'text', text: result.result });
                                    onEvent({ type: 'completed' });
                                    finish();
                                } else if (result.status === 'aborted') {
                                    onEvent({ type: 'error', text: result.result });
                                    finish(new Error(result.result));
                                } else {
                                    onEvent({ type: 'error', text: result.result || 'Unknown error' });
                                    finish(new Error(result.result || 'Unknown error'));
                                }
                            }
                        } catch (e) {
                            console.error('[AUTOBOT] Failed to parse response:', trimmed, e);
                        }
                    }
                });

                child.stderr.on('data', (data) => {
                    console.error('[AUTOBOT stderr]', data.toString());
                });

                child.on('exit', (code) => {
                    console.log(`[AUTOBOT] Process exited with code ${code}`);
                    if (!completed) {
                        const err = code !== 0 ? new Error(`Process exited with code ${code}`) : undefined;
                        finish(err);
                    }
                });

                child.on('error', (err) => {
                    console.error('[AUTOBOT] Process error:', err);
                    onEvent({ type: 'error', text: `Failed to start agent: ${err.message}` });
                    finish(err);
                });

                setTimeout(() => {
                    if (!completed) {
                        onEvent({ type: 'error', text: 'Task timeout (60s)' });
                        finish(new Error('Task timeout'));
                    }
                }, 60000);
            } catch (err) {
                onEvent({ type: 'error', text: `Failed to spawn agent: ${err}` });
                reject(err);
            }
        });
    }

    async stopAgent(): Promise<void> {
        if (this.childProcess) {
            this.childProcess.kill();
            this.childProcess = undefined;
        }
    }

    async getStatus(): Promise<any> {
        return { status: 'unknown' };
    }

    async chat(messages: any[]): Promise<any> {
        const lastMessage = messages[messages.length - 1];
        const goal = lastMessage?.content || '';
        
        return new Promise((resolve, reject) => {
            const child = spawn(this.getPythonCommand(), ['-m', 'autobot.stdio_agent'], {
                cwd: this.getAutobotHome(),
                env: {
                    ...process.env,
                    PYTHONPATH: this.getAutobotHome(),
                    AUTOBOT_HOME: this.getAutobotHome(),
                },
            });

            let buffer = '';
            const request = {
                id: `chat_${Date.now()}`,
                method: 'run',
                params: { goal, mode: 'coder' },
            };

            child.stdin.write(JSON.stringify(request) + '\n');

            child.stdout.on('data', (data) => {
                buffer += data.toString();
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed) continue;
                    try {
                        const response = JSON.parse(trimmed);
                        if (response.result?.status === 'ok') {
                            resolve({
                                choices: [{ message: { content: response.result.result } }]
                            });
                            child.kill();
                            return;
                        }
                    } catch (e) {}
                }
            });

            child.stderr.on('data', (data) => {
                console.error('[AUTOBOT chat stderr]', data.toString());
            });

            child.on('error', (err) => {
                reject(new Error(`Chat failed: ${err.message}`));
            });

            setTimeout(() => {
                child.kill();
                reject(new Error('Chat timeout'));
            }, 60000);
        });
    }

    async *chatStream(messages: any[]): AsyncGenerator<string, void, unknown> {
        const lastMessage = messages[messages.length - 1];
        const goal = lastMessage?.content || '';
        
        const child = spawn(this.getPythonCommand(), ['-m', 'autobot.stdio_agent'], {
            cwd: this.getAutobotHome(),
            env: {
                ...process.env,
                PYTHONPATH: this.getAutobotHome(),
                AUTOBOT_HOME: this.getAutobotHome(),
            },
        });

        const request = {
            id: `chat_${Date.now()}`,
            method: 'run',
            params: { goal, mode: 'coder' },
        };

        child.stdin.write(JSON.stringify(request) + '\n');

        let buffer = '';
        let completed = false;
        const queue: string[] = [];
        let resolveNext: (() => void) | null = null;
        let rejectNext: ((err: Error) => void) | null = null;

        child.stdout.on('data', (data) => {
            buffer += data.toString();
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;
                try {
                    const response = JSON.parse(trimmed);
                    if (response.event && response.event.type === 'text') {
                        queue.push(response.event.text);
                        if (resolveNext) {
                            resolveNext();
                            resolveNext = null;
                        }
                    }
                    if (response.result?.status === 'ok') {
                        completed = true;
                        child.kill();
                        if (resolveNext) {
                            resolveNext();
                            resolveNext = null;
                        }
                    }
                } catch (e) {}
            }
        });

        child.on('error', (err) => {
            if (rejectNext) {
                rejectNext(err);
                rejectNext = null;
            }
        });

        child.on('close', () => {
            completed = true;
            if (resolveNext) {
                resolveNext();
                resolveNext = null;
            }
        });

        while (!completed || queue.length > 0) {
            if (queue.length > 0) {
                yield queue.shift()!;
            } else {
                await new Promise<void>((resolve, reject) => {
                    resolveNext = resolve;
                    rejectNext = reject;
                });
            }
        }
    }

    async getMemory(): Promise<any> {
        const request = {
            id: `memory_${Date.now()}`,
            method: 'memory',
            params: {},
        };

        return new Promise((resolve) => {
            const child = spawn(this.getPythonCommand(), ['-m', 'autobot.stdio_agent'], {
                cwd: this.getAutobotHome(),
                env: {
                    ...process.env,
                    PYTHONPATH: this.getAutobotHome(),
                    AUTOBOT_HOME: this.getAutobotHome(),
                },
            });

            let buffer = '';
            child.stdin.write(JSON.stringify(request) + '\n');

            child.stdout.on('data', (data) => {
                buffer += data.toString();
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed) continue;
                    try {
                        const response = JSON.parse(trimmed);
                        if (response.result) {
                            resolve(response.result);
                            child.kill();
                            return;
                        }
                    } catch (e) {}
                }
            });

            child.stderr.on('data', (data) => {
                console.error('[AUTOBOT memory stderr]', data.toString());
            });

            setTimeout(() => {
                child.kill();
                resolve({ entries: [], total: 0 });
            }, 5000);
        });
    }

    async getSkills(): Promise<any> {
        return null;
    }

    dispose() {
        if (this.childProcess) {
            this.childProcess.kill();
            this.childProcess = undefined;
        }
    }
}
