import * as https from 'https';
import * as http from 'http';
import * as vscode from 'vscode';

export interface ToolCall {
    id: string;
    type: 'function';
    function: {
        name: string;
        arguments: string;
    };
}

export interface LLMResponse {
    content: string;
    model: string;
    provider: string;
    finishReason: string;
    toolCalls?: ToolCall[];
}

export interface ChatOptions {
    signal?: AbortSignal;
    tools?: any[];
    temperature?: number;
    maxTokens?: number;
    model?: string;
}

interface ProviderDef {
    name: string;
    base_url: string;
    api_key_env: string;
    default_model: string;
    completions_path: string;
}

const PROVIDERS: ProviderDef[] = [
    { name: 'openrouter', base_url: 'https://openrouter.ai/api/v1', api_key_env: 'OPENROUTER_API_KEY', default_model: 'meta-llama/llama-3.1-8b-instruct', completions_path: 'chat/completions' },
    { name: 'groq', base_url: 'https://api.groq.com/openai/v1', api_key_env: 'GROQ_API_KEY', default_model: 'llama-3.1-8b-instant', completions_path: 'chat/completions' },
    { name: 'deepinfra', base_url: 'https://api.deepinfra.com', api_key_env: 'DEEPINFRA_API_KEY', default_model: 'meta-llama/Meta-Llama-3.1-8B-Instruct', completions_path: 'v1/openai/chat/completions' },
    { name: 'google-ai-studio', base_url: 'https://generativelanguage.googleapis.com/v1beta/openai', api_key_env: 'GOOGLE_API_KEY', default_model: 'gemini-2.5-flash', completions_path: 'chat/completions' },
    { name: 'github-models', base_url: 'https://models.github.ai/inference', api_key_env: 'GITHUB_TOKEN', default_model: 'openai/gpt-4.1-mini', completions_path: 'chat/completions' },
    { name: 'mistral', base_url: 'https://api.mistral.ai/v1', api_key_env: 'MISTRAL_API_KEY', default_model: 'mistral-small-latest', completions_path: 'chat/completions' },
    { name: 'cerebras', base_url: 'https://api.cerebras.ai/v1', api_key_env: 'CEREBRAS_API_KEY', default_model: 'llama3.1-8b', completions_path: 'chat/completions' },
    { name: 'cohere', base_url: 'https://api.cohere.ai/compatibility/v1', api_key_env: 'COHERE_API_KEY', default_model: 'command-a-03-2025', completions_path: 'chat/completions' },
    { name: 'sambanova', base_url: 'https://api.sambanova.ai/v1', api_key_env: 'SAMBANOVA_API_KEY', default_model: 'Meta-Llama-3.3-70B-Instruct', completions_path: 'chat/completions' },
    { name: 'siliconflow', base_url: 'https://api.siliconflow.com/v1', api_key_env: 'SILICONFLOW_API_KEY', default_model: 'Qwen/Qwen3-8B', completions_path: 'chat/completions' },
];

export class LLMClient {
    private activeProviders: ProviderDef[] = [];

    constructor() {
        this.activeProviders = PROVIDERS.filter(p => {
            const key = process.env[p.api_key_env];
            return key && key.length > 0;
        });

        if (this.activeProviders.length === 0) {
            console.warn('No API keys found. Tried:', PROVIDERS.map(p => p.api_key_env).join(', '));
            this.activeProviders = [...PROVIDERS];
        }

        console.log(`LLM: ${this.activeProviders.length} active providers`);
    }

    async chat(messages: any[], options?: ChatOptions): Promise<LLMResponse> {
        const errors: string[] = [];

        for (const provider of this.activeProviders) {
            const apiKey = process.env[provider.api_key_env] || '';
            try {
                const response = await this.callProvider(provider, apiKey, messages, options);
                if (response) return response;
            } catch (e: any) {
                errors.push(`${provider.name}: ${e.message}`);
                continue;
            }
        }

        throw new Error(`All providers failed.\n${errors.slice(0, 3).join('\n')}\n\nSet an API key in your .env file.`);
    }

    private callProvider(
        provider: ProviderDef,
        apiKey: string,
        messages: any[],
        options?: ChatOptions
    ): Promise<LLMResponse> {
        return new Promise((resolve, reject) => {
            if (options?.signal?.aborted) {
                reject(new DOMException('Aborted', 'AbortError'));
                return;
            }

            let baseUrl = provider.base_url.replace(/\/+$/, '');
            let completionsPath = provider.completions_path || 'chat/completions';
            let urlStr = `${baseUrl}/${completionsPath.replace(/^\//, '')}`;

            let url: URL;
            try {
                url = new URL(urlStr);
            } catch {
                reject(new Error('Invalid URL'));
                return;
            }

            const model = options?.model || provider.default_model;
            const payload: any = {
                model,
                messages,
                temperature: options?.temperature ?? 0.5,
                max_tokens: options?.maxTokens ?? 4096,
            };

            if (options?.tools && options.tools.length > 0) {
                payload.tools = options.tools;
                payload.tool_choice = 'auto';
            }

            const body = JSON.stringify(payload);
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(body).toString(),
            };

            if (provider.name === 'google-ai-studio') {
                url.searchParams.set('key', apiKey);
            } else if (provider.name === 'github-models') {
                headers['Authorization'] = `Bearer ${apiKey}`;
                headers['User-Agent'] = 'autobot-vscode/1.0';
            } else {
                headers['Authorization'] = `Bearer ${apiKey}`;
            }

            const clientModule = url.protocol === 'https:' ? https : http;

            const req = clientModule.request(
                url,
                { method: 'POST', headers, timeout: 120000 },
                (res) => {
                    let data = '';
                    res.on('data', (chunk: string) => { data += chunk; });
                    res.on('end', () => {
                        try {
                            if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
                                const parsed = JSON.parse(data);
                                const choice = parsed.choices?.[0]?.message;
                                resolve({
                                    content: choice?.content || '',
                                    model: parsed.model || model,
                                    provider: provider.name,
                                    finishReason: choice?.finish_reason || 'stop',
                                    toolCalls: choice?.tool_calls,
                                });
                            } else {
                                reject(new Error(`HTTP ${res.statusCode}: ${data.slice(0, 200)}`));
                            }
                        } catch (e: any) {
                            reject(new Error(`Parse: ${e.message}`));
                        }
                    });
                }
            );

            req.on('error', (e: Error) => reject(e));
            req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
            req.write(body);
            req.end();

            if (options?.signal) {
                options.signal.addEventListener('abort', () => {
                    req.destroy();
                    reject(new DOMException('Aborted', 'AbortError'));
                });
            }
        });
    }
}
