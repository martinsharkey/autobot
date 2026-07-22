import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

interface MemoryEntry {
    id: string;
    content: string;
    category: string;
    timestamp: number;
    importance: number;
    source: string;
}

export class MemoryStore {
    private entries: MemoryEntry[] = [];
    private filePath: string;

    constructor(context: vscode.ExtensionContext) {
        const globalDir = context.globalStorageUri.fsPath;
        fs.mkdirSync(globalDir, { recursive: true });
        this.filePath = path.join(globalDir, 'memory.json');
        this.load();
    }

    addEntry(content: string, category: string = 'experience', importance: number = 0.5, source: string = 'agent'): string {
        const entry: MemoryEntry = {
            id: `mem_${Date.now()}_${this.entries.length}`,
            content,
            category,
            timestamp: Date.now(),
            importance,
            source,
        };
        this.entries.push(entry);
        this.save();
        return entry.id;
    }

    getRecent(limit: number = 10, category?: string): MemoryEntry[] {
        let filtered = this.entries;
        if (category) {
            filtered = filtered.filter(e => e.category === category);
        }
        return filtered.slice(-limit).reverse();
    }

    getImportant(limit: number = 5): MemoryEntry[] {
        return [...this.entries]
            .sort((a, b) => b.importance - a.importance)
            .slice(0, limit);
    }

    search(query: string): MemoryEntry[] {
        const q = query.toLowerCase();
        return this.entries
            .filter(e => e.content.toLowerCase().includes(q))
            .sort((a, b) => b.importance - a.importance)
            .slice(0, 10);
    }

    getContext(): string {
        const parts: string[] = [];
        const important = this.getImportant(5);
        if (important.length > 0) {
            parts.push('Key Learnings:');
            for (const e of important) {
                parts.push(`  [${e.category}] ${e.content.slice(0, 200)}`);
            }
        }
        const recent = this.getRecent(5);
        if (recent.length > 0) {
            parts.push('Recent Context:');
            for (const e of recent) {
                parts.push(`  ${e.content.slice(0, 200)}`);
            }
        }
        return parts.join('\n');
    }

    getAll(): MemoryEntry[] {
        return [...this.entries];
    }

    clear() {
        this.entries = [];
        this.save();
    }

    private load() {
        try {
            if (fs.existsSync(this.filePath)) {
                const data = JSON.parse(fs.readFileSync(this.filePath, 'utf-8'));
                this.entries = data.entries || [];
            }
        } catch (e) {
            console.error('Memory load error:', e);
        }
    }

    private save() {
        try {
            fs.writeFileSync(this.filePath, JSON.stringify({ entries: this.entries }, null, 2), 'utf-8');
        } catch (e) {
            console.error('Memory save error:', e);
        }
    }
}
