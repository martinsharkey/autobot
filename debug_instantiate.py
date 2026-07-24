import sys, os, time
sys.path.insert(0, '.')
os.environ['PYTHONPATH'] = '.'
os.environ['AUTOBOT_HOME'] = '.'

print("Importing Config...")
from autobot.config import Config
print("Instantiating Config...")
config = Config()

print("Importing AgentRuntime...")
from autobot.runtime import AgentRuntime
print("Instantiating AgentRuntime...")
rt = AgentRuntime.shared()

print("Importing NotificationClient...")
from autobot.notifications import NotificationClient
print("Instantiating NotificationClient...")
nc = NotificationClient()

print("Importing RemoteCommandProtocol...")
from autobot.remote_commands import RemoteCommandProtocol
print("Instantiating RemoteCommandProtocol...")
rc = RemoteCommandProtocol()

print("All done!")
