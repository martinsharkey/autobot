import * as vscode from 'vscode';
import { AgentClient, TaskEvent } from './agentClient';
import { Config } from './config';

export class ChatPanel implements vscode.WebviewViewProvider {
    private view: vscode.WebviewView | undefined;
    private disposables: vscode.Disposable[] = [];
    private client: AgentClient;
    private currentMode: string = 'coder';
    private running: boolean = false;

    constructor(private context: vscode.ExtensionContext, client: AgentClient) {
        this.client = client;
        this.currentMode = Config.defaultMode;
    }

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this.view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.context.extensionUri]
        };

        webviewView.webview.html = getHtml(webviewView.webview, this.currentMode);

        webviewView.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'sendMessage':
                    if (msg.text?.trim()) await this.runTask(msg.text.trim());
                    break;
                case 'stop':
                    await this.client.stopAgent();
                    this.appendSystem('Task stopped by user');
                    break;
                case 'ping':
                    this.view?.webview.postMessage({ command: 'pong' });
                    break;
            }
        }, null, this.disposables);

        webviewView.onDidDispose(() => {
            this.view = undefined;
            this.disposables.forEach(d => d.dispose());
            this.disposables = [];
        }, null, this.disposables);
    }

    show() {
        vscode.commands.executeCommand('workbench.view.extension.autobot-sidebar');
        if (this.view) {
            this.view.show(true);
        }
    }

    async runTask(goal: string) {
        if (this.running) {
            vscode.window.showWarningMessage('AUTOBOT is already running');
            return;
        }
        this.running = true;
        this.appendUser(goal);
        this.appendSystem(`*Running in ${this.currentMode} mode...*`);

        try {
            await this.client.runTask(goal, this.currentMode, (event: TaskEvent) => {
                switch (event.type) {
                    case 'started':
                        this.appendSystem(`*Task started: ${event.text}*`);
                        break;
                    case 'loop':
                        this.appendSystem(`*Loop ${event.count} / ${event.max}*`);
                        vscode.commands.executeCommand('autobot.refreshMemory');
                        break;
                    case 'tool_call':
                        this.appendTool(event.name || 'unknown', event.args || {});
                        break;
                    case 'text':
                        if (event.text) this.appendAssistant(event.text);
                        break;
                    case 'reflection':
                        this.appendSystem(`*Reflection: ${(event.text || '').slice(0, 200)}*`);
                        break;
                    case 'error':
                        this.appendSystem(`*Error: ${event.text}*`);
                        vscode.window.showErrorMessage(`AUTOBOT: ${event.text}`);
                        break;
                    case 'completed':
                        this.appendSystem(`*Task completed*`);
                        vscode.commands.executeCommand('autobot.refreshMemory');
                        break;
                    default:
                        if (event.text) this.appendSystem(`*${event.text}*`);
                }
            });
        } catch (err: any) {
            this.appendSystem(`*Error: ${err?.message || err}*`);
            vscode.window.showErrorMessage(`AUTOBOT failed: ${err?.message || err}`);
        } finally {
            this.running = false;
        }
    }

    setMode(mode: string) {
        this.currentMode = mode;
        this.view?.webview.postMessage({ command: 'setMode', mode });
    }

    appendUser(text: string) {
        this.view?.webview.postMessage({ command: 'appendUser', text });
    }
    appendAssistant(text: string) {
        this.view?.webview.postMessage({ command: 'appendAssistant', text });
    }
    appendSystem(text: string) {
        this.view?.webview.postMessage({ command: 'appendSystem', text });
    }
    appendTool(name: string, args: any) {
        this.view?.webview.postMessage({ command: 'appendTool', name, args });
    }

    sendMessage(text: string) {
        this.view?.webview.postMessage({ command: 'addUserMessage', text });
    }

    dispose() {
        this.running = false;
    }
}

function getHtml(webview: vscode.Webview, mode: string): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUTOBOT</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: var(--vscode-font-family); background: var(--vscode-editor-background); color: var(--vscode-editor-foreground); display: flex; flex-direction: column; height: 100vh; }
  header { padding: 10px 16px; border-bottom: 1px solid var(--vscode-panel-border); display: flex; align-items: center; gap: 10px; }
  header .mode { font-size: 11px; background: var(--vscode-badge-background); color: var(--vscode-badge-foreground); padding: 2px 8px; border-radius: 10px; }
  #output { flex: 1; overflow-y: auto; padding: 16px; }
  .msg { margin-bottom: 12px; padding: 8px 12px; border-radius: 6px; line-height: 1.5; font-size: 13px; }
  .msg.user { background: var(--vscode-input-background); border-left: 3px solid var(--vscode-textLink-foreground); }
  .msg.assistant { background: var(--vscode-editor-inactiveSelectionBackground); }
  .msg.system { color: var(--vscode-descriptionForeground); font-style: italic; font-size: 12px; }
  .msg.tool { background: var(--vscode-textBlockQuote-background); border-left: 3px solid var(--vscode-textLink-foreground); font-family: var(--vscode-editor-font-family); font-size: 12px; }
  .tool-name { font-weight: bold; color: var(--vscode-textLink-foreground); }
  .tool-args { color: var(--vscode-descriptionForeground); }
  pre { background: var(--vscode-textCodeBlock-background); padding: 8px; border-radius: 4px; overflow-x: auto; }
  code { font-family: var(--vscode-editor-font-family); font-size: 12px; }
  #input-area { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--vscode-panel-border); }
  input { flex: 1; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); padding: 8px 12px; border-radius: 4px; outline: none; }
  button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .status-bar { padding: 4px 16px; font-size: 11px; background: var(--vscode-statusBar-background); color: var(--vscode-statusBar-foreground); display: flex; justify-content: space-between; }
</style>
</head>
<body>
  <header>
    <strong>AUTOBOT</strong>
    <span class="mode" id="mode-badge">${mode}</span>
    <span style="flex:1"></span>
    <button id="stop-btn" title="Stop">Stop</button>
  </header>
  <div id="output"></div>
  <div id="input-area">
    <input id="goal-input" placeholder="What should AUTOBOT do?" autofocus />
    <button id="send-btn">Run</button>
  </div>
  <div class="status-bar">
    <span id="status">Ready</span>
    <span id="task-id"></span>
  </div>
<script>
  const vscode = acquireVsCodeApi();
  const output = document.getElementById('output');
  const input = document.getElementById('goal-input');
  const sendBtn = document.getElementById('send-btn');
  const stopBtn = document.getElementById('stop-btn');
  const status = document.getElementById('status');
  const taskIdEl = document.getElementById('task-id');
  const modeBadge = document.getElementById('mode-badge');

  function scroll() { output.scrollTop = output.scrollHeight; }
  function append(type, html) {
    const div = document.createElement('div');
    div.className = 'msg ' + type;
    div.innerHTML = html;
    output.appendChild(div);
    scroll();
  }
  append('system', 'AUTOBOT ready. Ask anything or use commands from the palette.');

  window.addEventListener('message', e => {
    const m = e.data;
    if (!m) return;
    switch (m.command) {
      case 'appendUser': append('user', escapeHtml(m.text)); break;
      case 'appendAssistant': append('assistant', formatMarkdown(m.text)); break;
      case 'appendSystem': append('system', escapeHtml(m.text)); break;
      case 'appendTool': append('tool', '<span class="tool-name">' + escapeHtml(m.name) + '</span><pre class="tool-args">' + escapeHtml(JSON.stringify(m.args, null, 2)) + '</pre>'); break;
      case 'setMode': modeBadge.textContent = m.mode; break;
    }
  });

  function send() {
    const text = input.value.trim(); if (!text) return;
    vscode.postMessage({ command: 'sendMessage', text });
    input.value = '';
    input.disabled = true; sendBtn.disabled = true;
    status.textContent = 'Running...';
  }
  sendBtn.addEventListener('click', send);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
  stopBtn.addEventListener('click', () => { vscode.postMessage({ command: 'stop' }); status.textContent = 'Stopping...'; });

  function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function formatMarkdown(s) {
    let t = escapeHtml(s);
    t = t.replace(/\`\`\`([\\s\\S]*?)\`\`\`/g, '<pre><code>$1</code></pre>');
    t = t.replace(/\`([^\`]+)\`/g, '<code>$1</code>');
    t = t.replace(/\\*\\*([^*]+)\\*\\*/g, '<b>$1</b>');
    t = t.replace(/\\n/g, '<br>');
    return t;
  }
</script>
</body>
</html>`;
}