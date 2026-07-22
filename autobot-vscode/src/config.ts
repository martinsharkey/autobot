import * as vscode from 'vscode';

export class Config {
    static gatewayUrl: string = 'http://127.0.0.1:8000/v1';
    static gatewayApiKey: string = 'changeme';
    static defaultMode: string = 'coder';
    static maxTurns: number = 50;
    static temperature: number = 0.5;
    static autoImprove: boolean = true;
    static autoReflect: boolean = true;

    static initialize() {
        const cfg = vscode.workspace.getConfiguration('autobot');
        this.gatewayUrl = cfg.get<string>('gatewayUrl', this.gatewayUrl);
        this.gatewayApiKey = cfg.get<string>('gatewayApiKey', this.gatewayApiKey);
        this.defaultMode = cfg.get<string>('defaultMode', this.defaultMode);
        this.maxTurns = cfg.get<number>('maxTurns', this.maxTurns);
        this.temperature = cfg.get<number>('temperature', this.temperature);
        this.autoImprove = cfg.get<boolean>('autoImprove', this.autoImprove);
        this.autoReflect = cfg.get<boolean>('autoReflect', this.autoReflect);

        // Listen for config changes
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('autobot')) {
                this.initialize();
            }
        });
    }
}

export type AgentMode = 'architect' | 'coder' | 'reflector' | 'learner' | 'evolver';

export interface ToolGroup {
    read: boolean;
    edit: boolean;
    command: boolean;
    mcp: boolean;
}

export const AGENT_MODES: Record<AgentMode, { name: string; role: string; groups: ToolGroup }> = {
    architect: {
        name: 'Architect',
        role: 'You are AUTOBOT in Architect mode. Design systems, plan architecture, analyze requirements. Focus on reading and planning.',
        groups: { read: true, edit: false, command: false, mcp: true },
    },
    coder: {
        name: 'Coder',
        role: 'You are AUTOBOT in Code mode. Write, edit, and debug code. Implement features and fix bugs.',
        groups: { read: true, edit: true, command: true, mcp: true },
    },
    reflector: {
        name: 'Reflector',
        role: 'You are AUTOBOT in Reflect mode. Analyze past actions, extract learnings, identify improvements. Read-only.',
        groups: { read: true, edit: false, command: false, mcp: false },
    },
    learner: {
        name: 'Learner',
        role: 'You are AUTOBOT in Learn mode. Research new topics, extract patterns, build skills, expand knowledge.',
        groups: { read: true, edit: true, command: true, mcp: true },
    },
    evolver: {
        name: 'Evolver',
        role: 'You are AUTOBOT in Evolve mode. Self-improvement, code rewriting, optimization, capability enhancement.',
        groups: { read: true, edit: true, command: true, mcp: true },
    },
};
