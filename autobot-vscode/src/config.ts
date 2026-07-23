import * as vscode from 'vscode';

export class Config {
    static gatewayUrl: string = 'http://127.0.0.1:8000';
    static gatewayApiKey: string = 'changeme';
    static defaultMode: string = 'coder';
    static maxLoops: number = 50;
    static autoStartGateway: boolean = true;

    static initialize(context: vscode.ExtensionContext) {
        const cfg = vscode.workspace.getConfiguration('autobot');
        this.gatewayUrl = cfg.get<string>('gatewayUrl', this.gatewayUrl);
        this.gatewayApiKey = cfg.get<string>('gatewayApiKey', this.gatewayApiKey);
        this.defaultMode = cfg.get<string>('defaultMode', this.defaultMode);
        this.maxLoops = cfg.get<number>('maxLoops', this.maxLoops);
        this.autoStartGateway = cfg.get<boolean>('autoStartGateway', this.autoStartGateway);

        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('autobot')) this.initialize(context);
        });
    }
}
