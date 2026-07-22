import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { Config, AgentMode, AGENT_MODES, ToolGroup } from './config';
import { LLMClient, LLMResponse } from './llm';
import { ToolSystem } from './tools';
import { MemoryStore } from './memory';
import { HermesPrompt } from './hermesPrompt';

export type StreamCallback = (chunk: string) => void;

export class AutobotAgent {
    private llm: LLMClient;
    private tools: ToolSystem;
    private memory: MemoryStore;
    private mode: AgentMode;
    private running: boolean = false;
    private abortController: AbortController | null = null;

    constructor(private ctx: vscode.ExtensionContext) {
        this.mode = Config.defaultMode as AgentMode;
        this.llm = new LLMClient();
        this.tools = new ToolSystem();
        this.memory = new MemoryStore(this.ctx);

        console.log(`AUTOBOT Agent initialized [mode: ${this.mode}]`);
    }

    async runTask(goal: string, onChunk: StreamCallback): Promise<void> {
        if (this.running) {
            vscode.window.showWarningMessage('AUTOBOT is already running a task. Stop it first.');
            return;
        }

        this.running = true;
        this.abortController = new AbortController();
        const signal = this.abortController.signal;

        try {
            onChunk(`## Running: ${goal}\n\n`);

            // Phase 1: Plan
            onChunk('### Phase 1: Planning\n\n');
            const plan = await this.generatePlan(goal, signal);

            // Phase 2-4: Execute loop
            for (let i = 0; i < Math.min(plan.length, Config.maxTurns); i++) {
                if (signal.aborted) break;

                const step = plan[i];
                onChunk(`### Step ${i + 1}: ${step}\n\n`);

                // Execute using LLM with tool calls
                const response = await this.executeStep(step, signal);

                if (response.content) {
                    onChunk(response.content + '\n\n');
                }

                // Auto-reflect
                if (Config.autoReflect) {
                    const reflection = await this.reflect(goal, signal);
                    if (reflection) {
                        onChunk(`> Reflection: ${reflection.slice(0, 200)}...\n\n`);
                    }
                }
            }

            onChunk('### Task Complete\n\n');
            this.memory.addEntry(`Completed task: ${goal}`, 'accomplishment', 0.8);

        } catch (err: any) {
            if (err.name === 'AbortError') {
                onChunk('*Task cancelled*\n\n');
            } else {
                onChunk(`*Error: ${err.message}*\n\n`);
                console.error('AUTOBOT Error:', err);
            }
        } finally {
            this.running = false;
            this.abortController = null;
        }
    }

    private async generatePlan(goal: string, signal: AbortSignal): Promise<string[]> {
        const modeInfo = AGENT_MODES[this.mode];
        const systemPrompt = HermesPrompt.build(this.mode, modeInfo.role, this.memory.getContext());

        const messages = [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: `Create a step-by-step plan (3-8 steps) for:\n\n${goal}\n\nConsider:\n- Current mode: ${this.mode}\n- Available: read=${modeInfo.groups.read}, edit=${modeInfo.groups.edit}, command=${modeInfo.groups.command}\n\nOutput numbered steps.` }
        ];

        const response = await this.llm.chat(messages, { signal });
        return this.parsePlan(response.content);
    }

    private async executeStep(step: string, signal: AbortSignal): Promise<LLMResponse> {
        const modeInfo = AGENT_MODES[this.mode];
        const systemPrompt = HermesPrompt.build(this.mode, modeInfo.role, this.memory.getContext());

        const messages = [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: step }
        ];

        const response = await this.llm.chat(messages, {
            signal,
            tools: this.tools.getDefinitions(this.mode),
            temperature: Config.temperature,
        });

        // Execute any tool calls the LLM requested
        if (response.toolCalls && response.toolCalls.length > 0) {
            for (const tc of response.toolCalls) {
                try {
                    const args = typeof tc.function.arguments === 'string'
                        ? JSON.parse(tc.function.arguments)
                        : tc.function.arguments;
                    
                    const result = await this.tools.execute(tc.function.name, args, this.mode);
                    
                    // Store tool result in memory
                    this.memory.addEntry(
                        `Tool: ${tc.function.name} -> ${result.success ? 'OK' : 'Error: ' + (result.error || '')}`,
                        'tool_use',
                        0.4
                    );
                } catch (err: any) {
                    console.error(`Tool ${tc.function.name} failed:`, err);
                }
            }
        }

        return response;
    }

    private async reflect(goal: string, signal: AbortSignal): Promise<string> {
        const recent = this.memory.getRecent(5).map(e => `- ${e.content}`).join('\n');
        if (!recent) return '';

        const messages = [
            { role: 'system', content: 'Analyze recent actions and extract insights.' },
            { role: 'user', content: `Goal: ${goal}\n\nRecent actions:\n${recent}\n\nWhat patterns emerge? What should change?` }
        ];

        const response = await this.llm.chat(messages, { signal, temperature: 0.3 });
        const reflection = response.content.slice(0, 500);
        this.memory.addEntry(reflection, 'reflection', 0.7);
        return reflection;
    }

    private parsePlan(content: string): string[] {
        const steps: string[] = [];
        for (const line of content.split('\n')) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            
            let cleaned: string | null = null;
            if (/^\d+[\.\)]/.test(trimmed)) {
                cleaned = trimmed.replace(/^\d+[\.\)]\s*/, '');
            } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                cleaned = trimmed.slice(2);
            }

            if (cleaned && cleaned.length > 10) {
                steps.push(cleaned);
            }
        }
        return steps.length > 0 ? steps : [content.trim()];
    }

    switchMode(mode: string) {
        if (mode in AGENT_MODES) {
            this.mode = mode as AgentMode;
            vscode.commands.executeCommand('setContext', 'autobotMode', mode);
        }
    }

    getMode(): AgentMode { return this.mode; }

    getMemory(): MemoryStore { return this.memory; }

    getToolSystem(): ToolSystem { return this.tools; }

    stop(): void {
        this.abortController?.abort();
        this.running = false;
    }

    isRunning(): boolean { return this.running; }

    dispose(): void {
        this.stop();
    }
}
