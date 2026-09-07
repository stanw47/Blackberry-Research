import subprocess, os
# dump sshd-related slog/console and config
for p in ["/var/log/syslog","/tmp/sshd.log","/dev/slog","/proc/boot/syslog"]:
    try:
        st=os.stat(p); print("EXIST",p,oct(st.st_mode&0o777),st.st_size)
    except Exception as e: pass
# read sshd_config fully
try:
    print("=== sshd_config ===")
    print(open("/etc/ssh/sshd_config","rt").read())
except Exception as e:
    print("cfg err",e)
for pat in ["authorized_keys2","AllowUsers","PermitRootLogin","PasswordAuth","HostKey"]:
    pass
