import * as vscode from 'vscode';

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
    private eventSource: EventSource | undefined;
    private onEvent: ((e: TaskEvent) => void) | undefined;
    private reconnectTimer: NodeJS.Timeout | undefined;

    constructor() {
        const cfg = vscode.workspace.getConfiguration('autobot');
        this.baseUrl = cfg.get<string>('gatewayUrl', 'http://127.0.0.1:8001').replace(/\/$/, '');
        this.apiKey = cfg.get<string>('gatewayApiKey', 'changeme');
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

    async runTask(goal: string, mode: string, onEvent: (e: TaskEvent) => void): Promise<string> {
        this.onEvent = onEvent;
        const resp = await fetch(`${this.baseUrl}/v1/agent/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.apiKey}`,
            },
            body: JSON.stringify({ goal, mode, max_loops: 50, stream: true }),
        });
        if (!resp.ok) {
            const text = await resp.text();
            throw new Error(`Agent run failed: ${resp.status} ${text}`);
        }
        const reader = resp.body?.getReader();
        if (!reader) {
            throw new Error('Streaming not supported');
        }
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || !trimmed.startsWith('data: ')) continue;
                const data = trimmed.slice(6).trim();
                if (data === '[DONE]') {
                    onEvent({ type: 'completed' });
                    return Promise.resolve('');
                }
                try {
                    const chunk = JSON.parse(data);
                    const eventType = chunk.type || 'text';
                    onEvent({
                        type: eventType,
                        text: chunk.text,
                        name: chunk.name,
                        args: chunk.args,
                        count: chunk.count,
                        max: chunk.max,
                    });
                } catch {}
            }
        }
        return Promise.resolve('');
    }

    async stopAgent(): Promise<void> {
        try {
            await fetch(`${this.baseUrl}/v1/agent/stop`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${this.apiKey}` },
            });
        } catch {}
    }

    async getStatus(): Promise<any> {
        try {
            const resp = await fetch(`${this.baseUrl}/v1/agent/status`, {
                headers: { Authorization: `Bearer ${this.apiKey}` },
            });
            if (resp.ok) return await resp.json() as any;
        } catch {}
        return null;
    }

    async chat(messages: any[]): Promise<any> {
        const resp = await fetch(`${this.baseUrl}/v1/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${this.apiKey}`,
            },
            body: JSON.stringify({ model: 'gateway', messages }),
        });
        if (!resp.ok) throw new Error(`Chat failed: ${resp.status}`);
        return await resp.json() as any;
    }

    async *chatStream(messages: any[]): AsyncGenerator<string, void, unknown> {
        const resp = await fetch(`${this.baseUrl}/v1/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${this.apiKey}`,
            },
            body: JSON.stringify({ model: 'gateway', messages }),
        });
        if (!resp.ok) throw new Error(`Stream failed: ${resp.status}`);
        const reader = resp.body?.getReader();
        if (!reader) return;
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || !trimmed.startsWith('data: ')) continue;
                const data = trimmed.slice(6).trim();
                if (data === '[DONE]') return;
                try {
                    const chunk = JSON.parse(data);
                    const delta = (chunk as any).choices?.[0]?.delta?.content || '';
                    if (delta) yield delta;
                } catch {}
            }
        }
    }

    async getMemory(): Promise<any> {
        try {
            const resp = await fetch(`${this.baseUrl}/v1/memory`, {
                headers: { Authorization: `Bearer ${this.apiKey}` },
            });
            if (resp.ok) return await resp.json() as any;
        } catch {}
        return null;
    }

    async getSkills(): Promise<any> {
        try {
            const resp = await fetch(`${this.baseUrl}/v1/skills`, {
                headers: { Authorization: `Bearer ${this.apiKey}` },
            });
            if (resp.ok) return await resp.json() as any;
        } catch {}
        return null;
    }

    dispose() {
        this.currentTaskId = undefined;
    }
}
