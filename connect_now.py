import paramiko
import paramiko.transport as P
_orig = paramiko.transport.Transport.__init__
def _new(self, *a, **kw):
    kw.setdefault('server_sig_algs', False)
    return _orig(self, *a, **kw)
paramiko.transport.Transport.__init__ = _new

key = paramiko.RSAKey.from_private_key_file("/home/stanw47/Documents/blackberry-research/id_rsa")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(hostname="169.254.0.1", port=22, username="devuser", pkey=key,
              disabled_algorithms={'pubkeys':['rsa-sha2-512','rsa-sha2-256']}, timeout=20, allow_agent=False, look_for_keys=False)
    print("SSH CONNECTED!")
    stdin,stdout,stderr = c.exec_command("echo CONNECTED; id; uname -a", timeout=10)
    print(stdout.read().decode(errors='replace'))
    c.close()
except Exception as e:
    print("FAILED:", e)
