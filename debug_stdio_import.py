import subprocess, sys, os

proc = subprocess.Popen(
    [sys.executable, '-c', 'import sys; print("PYTHON OK"); import autobot.stdio_agent'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd='.',
    env={**os.environ, 'PYTHONPATH': '.', 'AUTOBOT_HOME': '.'}
)
try:
    out, err = proc.communicate(timeout=10)
    print('OUT:', out[:300])
    print('ERR:', err[:300])
    print('RC:', proc.returncode)
except subprocess.TimeoutExpired:
    proc.kill()
    out, err = proc.communicate()
    print('TIMEOUT - OUT:', out[:300])
    print('TIMEOUT - ERR:', err[:300])
