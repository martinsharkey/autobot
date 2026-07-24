import subprocess, sys, os, threading, time

proc = subprocess.Popen(
    [sys.executable, '-m', 'autobot.stdio_agent'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd='.',
    env={**os.environ, 'PYTHONPATH': '.', 'AUTOBOT_HOME': '.'}
)

print(f'Started pid {proc.pid}')

# Read init with longer timeout
result = []
def read_stdout():
    line = proc.stdout.readline()
    result.append(line)

thread = threading.Thread(target=read_stdout)
thread.daemon = True
thread.start()
thread.join(timeout=30)

if result:
    print('INIT:', result[0].strip())
else:
    print('NO INIT - killing')
    proc.kill()
    out, err = proc.communicate()
    print('STDOUT:', out[:300])
    print('STDERR:', err[:300])
