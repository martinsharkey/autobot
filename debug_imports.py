import sys, os, time

sys.path.insert(0, '.')
os.environ['PYTHONPATH'] = '.'
os.environ['AUTOBOT_HOME'] = '.'

imports = [
    ('autobot.llm', 'LLMClient'),
    ('autobot.memory', 'MemoryStore'),
    ('autobot.tools', 'ToolRegistry'),
    ('autobot.mcp.bridge', 'MCPBridge'),
    ('autobot.safety', 'SafetyPolicy'),
    ('autobot.governance', 'GovernanceModule'),
    ('autobot.trading.mt5_connector', 'MT5Connector'),
    ('autobot.trading.risk_manager', 'RiskManager'),
    ('autobot.subagent', 'SubAgentSpawner'),
    ('autobot.evolution', 'GapAnalysisEngine'),
    ('autobot.overnight', 'OvernightLearner'),
    ('autobot.plugins.interface', 'PluginRegistry'),
    ('autobot.windows_compat', 'ensure_windows_compat'),
    ('autobot.context_sanitizer', 'sanitize_context_files'),
    ('autobot.delegation', 'HierarchicalDelegator'),
]

for mod_name, attr in imports:
    print(f'Testing {mod_name}...', end='', flush=True)
    start = time.time()
    try:
        mod = __import__(mod_name, fromlist=[attr])
        getattr(mod, attr)
        elapsed = time.time() - start
        print(f' OK ({elapsed:.2f}s)')
    except Exception as e:
        elapsed = time.time() - start
        print(f' ERROR ({elapsed:.2f}s): {e}')
    sys.stdout.flush()

print('Done')
