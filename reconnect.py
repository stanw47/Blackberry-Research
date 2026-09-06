import paramiko
import paramiko.transport as P
_orig = paramiko.transport.Transport.__init__
def _new(self, *a, **kw):
    kw.setdefault('server_sig_algs', False)
    return _orig(self, *a, **kw)
paramiko.transport.Transport.__init__ = _new

# First, run blackberry-connect to establish the tunnel and push a new key
import subprocess
import os

# Path to blackberry-connect
bb_connect = "~/priv-research/bbndk-tools/host_10_3_1_12/win32/x86/usr/bin/blackberry-connect"
if not os.path.exists(bb_connect):
    print("ERROR: blackberry-connect not found at", bb_connect)
    exit(1)

print("Starting blackberry-connect...")
# Run blackberry-connect in background, it will push the SSH key
result = subprocess.run([
    bb_connect, "169.254.0.1",
    "-password", "61482501",
    "-sshPublicKey", "~/Documents/blackberry-research/id_rsa.pub"
], capture_output=True, text=True, timeout=30)
print("blackberry-connect stdout:", result.stdout)
print("blackberry-connect stderr:", result.stderr)
print("Return code:", result.returncode)

# Now test SSH with the new key
import paramiko
import paramiko.transport as P
_orig = paramiko.transport.Transport.__init__
def _new(self, *a, **kw):
    kw.setdefault('server_sig_algs', False)
    return _orig(self, *a, **kw)
paramiko.transport.Transport.__init__ = _new

key = paramiko.RSAKey.from_private_key_file("~/Documents/blackberry-research/id_rsa")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(hostname="169.254.0.1", port=22, username="devuser", pkey=key,
          disabled_algorithms={'pubkeys':['rsa-sha2-512','rsa-sha2-256']}, timeout=20, allow_agent=False, look_for_keys=False)

stdin,stdout,stderr = c.exec_command("echo CONNECTED; id; uname -a", timeout=10)
print("STDOUT:", stdout.read().decode(errors='replace'))
print("STDERR:", stderr.read().decode(errors='replace'))
c.close()
