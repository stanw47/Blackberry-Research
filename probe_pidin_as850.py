import os,glob
# find /proc/<pid> dirs and aspace nodes; try opening via devctl-less read
pids=[p for p in glob.glob('/proc/[0-9]*') if os.path.isdir(p)]
print("proc count", len(pids))
# list a few with names via /proc/pid/cmdline if allowed
import time
for p in sorted(pids, key=lambda x:-int(x.split('/')[2]))[:6]:
    try:
        cl=open(p+'/cmdline','rb').read().decode(errors='replace')
    except Exception as e:
        cl='ERR:'+str(e)
    print(p, repr(cl[:50]))
    try:
        asz=open(p+'/as','rb').read(8)
        print("   as read OK:", asz.hex())
    except Exception as e:
        print("   as:", e)
