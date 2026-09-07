import os
# check writability of candidate trusted dirs by current (uid850) and note perms
for d in ["/base","/base/bin","/bin","/usr/bin","/proc/boot","/apps","/tmp"]:
    try:
        st=os.stat(d)
        w=os.access(d, os.W_OK)
        print("%-12s uid=%d gid=%d mode=%s writable_by_me=%s" % (d, st.st_uid, st.st_gid, oct(st.st_mode&0o7777), w))
    except Exception as e:
        print(d, "ERR", repr(e))
# size of python interpreter + its dir tree
p="/accounts/1000/shared/misc/berrycore/lib/python3_ntoarmv7-qnx-static/tools/python3/python3.11"
try:
    print("python bin size:", os.path.getsize(p), "exists:", os.path.exists(p))
except Exception as e:
    print("python err", repr(e))
