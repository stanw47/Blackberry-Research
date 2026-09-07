import paramiko, paramiko.transport as P
_orig = paramiko.transport.Transport.__init__
def _new(self, *a, **kw):
    kw.setdefault('server_sig_algs', False)
    return _orig(self, *a, **kw)
paramiko.transport.Transport.__init__ = _new
username = "root"
key = paramiko.RSAKey.from_private_key_file("id_rsa")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect(hostname="169.254.0.1", port=22, username=username, pkey=key,
              disabled_algorithms={'pubkeys':['rsa-sha2-512','rsa-sha2-256']},
              timeout=20, allow_agent=False, look_for_keys=False)
    print("SSH CONNECTED as", username)
    i,o,e = c.exec_command("id; uname -a; echo ROOT_OK", timeout=10)
    print("OUT:", o.read().decode(errors='replace'))
    print("ERR:", e.read().decode(errors='replace'))
    c.close()
except Exception as ex:
    print("FAILED:", ex)
