import os
p="/base/bin/__root"
st=os.stat(p); print("uid",st.st_uid,"gid",st.st_gid,"mode",oct(st.st_mode&0o7777),"size",st.st_size)
d=open(p,"rb").read()
print("magic:", d[:16].hex())
print("ascii head:", repr(d[:160]))
# search for strings
import re
for m in re.finditer(rb'[ -~]{4,}', d):
    s=m.group().decode(errors='replace')
    print("  str:", s)
