import os
for base in ["/etc/ssh","/var/chroot/sshd/etc/ssh","/var/chroot/sshd"]:
    try:
        for p in [base+"/authorized_keys2", base+"/sshd_config"]:
            if os.path.exists(p):
                st=os.stat(p)
                print("EXIST", p, "uid",st.st_uid,"gid",st.st_gid,"mode",oct(st.st_mode&0o777))
                d=open(p,"rt").read(errors='replace')
                if "authorized" in d.lower():
                    print("   cfg:", d)
    except Exception as e:
        print(base,"ERR",repr(e))
# list /var/chroot if exists
for p in ["/var/chroot","/var/chroot/sshd","/var/chroot/sshd/etc"]:
    try:
        print("LIST", p, os.listdir(p))
    except Exception as e:
        print("LIST", p, "ERR", repr(e))
