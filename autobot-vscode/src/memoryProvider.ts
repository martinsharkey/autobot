import * as vscode from 'vscode';
import { AgentClient } from './agentClient';

export class MemoryProvider implements vscode.TreeDataProvider<MemoryItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<MemoryItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    private entries: any[] = [];

    constructor(private client: AgentClient) {}

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    async load() {
        this.entries = [];
        const data = await this.client.getMemory();
        if (data?.entries) {
            this.entries = data.entries.slice(0, 50);
        }
        this.refresh();
    }

    getTreeItem(element: MemoryItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: MemoryItem): MemoryItem[] {
        if (!element) {
            const cats = new Map<string, number>();
            for (const e of this.entries) {
                cats.set(e.category, (cats.get(e.category) || 0) + 1);
            }
            const items: MemoryItem[] = [];
            for (const [cat, count] of cats) {
                items.push(new MemoryItem(cat, vscode.TreeItemCollapsibleState.Collapsed, `${cat} (${count})`));
            }
            items.push(new MemoryItem('stats', vscode.TreeItemCollapsibleState.None, `stats: ${this.entries.length} entries`));
            return items;
        }
        if (element.id === 'stats') return [];
        return this.entries
            .filter(e => e.category === element.id)
            .slice(0, 20)
            .map(e => new MemoryItem(
                e.id,
                vscode.TreeItemCollapsibleState.None,
                (e.content || '').slice(0, 80),
                undefined,
                undefined,
                `Importance: ${e.importance}\n${e.content}`
            ));
    }
}

class MemoryItem extends vscode.TreeItem {
    constructor(
        public readonly id: string,
        collapsibleState: vscode.TreeItemCollapsibleState,
        label: string,
        tooltip?: string,
        description?: string,
        public readonly fullDescription?: string
    ) {
        super(label, collapsibleState);
        if (fullDescription) this.tooltip = fullDescription;
        if (description) this.description = description;
    }
}
