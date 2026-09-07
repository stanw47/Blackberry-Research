import os
for p in ["/proc/boot/pathtrust",]:
    try:
        st=os.stat(p); print(p, "uid",st.st_uid,"gid",st.st_gid,"mode",oct(st.st_mode&0o7777))
        d=open(p,"rb").read().decode(errors="replace"); print("size",len(d),"head:",repr(d[:300]))
    except Exception as e:
        print(p,"ERR",repr(e))
