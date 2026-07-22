import * as vscode from 'vscode';
import { AutobotAgent } from './agent';

export class MemoryProvider implements vscode.TreeDataProvider<MemoryItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<MemoryItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    constructor(private agent: AutobotAgent) {}

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: MemoryItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: MemoryItem): MemoryItem[] {
        const memory = this.agent.getMemory();
        
        if (!element) {
            // Root level - show categories
            const all = memory.getAll();
            const categories = new Set(all.map(e => e.category));
            const items: MemoryItem[] = [];
            
            for (const cat of categories) {
                const count = all.filter(e => e.category === cat).length;
                items.push(new MemoryItem(
                    cat,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    `$(book) ${cat} (${count})`
                ));
            }
            
            items.push(new MemoryItem(
                'stats',
                vscode.TreeItemCollapsibleState.None,
                `$(graph) ${all.length} total entries`
            ));
            
            return items;
        }

        if (element.id === 'stats') return [];

        // Show entries for this category
        return memory.getAll()
            .filter(e => e.category === element.id)
            .slice(0, 20)
            .map(e => {
                const item = new MemoryItem(
                    e.id,
                    vscode.TreeItemCollapsibleState.None,
                    e.content.slice(0, 80) + (e.content.length > 80 ? '...' : '')
                );
                item.tooltip = `[${e.category}] ${e.content}\n\nImportance: ${e.importance}\nSource: ${e.source}\nTime: ${new Date(e.timestamp).toLocaleString()}`;
                item.description = `\u2605 ${e.importance.toFixed(1)}`;
                item.contextValue = 'memoryEntry';
                return item;
            });
    }
}

class MemoryItem extends vscode.TreeItem {
    constructor(
        public id: string,
        collapsibleState: vscode.TreeItemCollapsibleState,
        label: string
    ) {
        super(label, collapsibleState);
        this.id = id;
    }
}
