import glob,os
interesting=[]
for p in glob.glob('/proc/[0-9]*'):
    pid=p.split('/')[2]
    try:
        cl=open(p+'/cmdline','rb').read().decode(errors='replace')
    except Exception:
        continue
    low=cl.lower()
    if any(k in low for k in ('mmc','sdcc','sdmmc','emmc','devb','disk','block','dcmd')):
        interesting.append((pid,cl))
print("=== mmc/disk driver candidates ===")
for pid,cl in interesting:
    print(pid, repr(cl[:80]))
print("=== also list kernel/process-manager-ish ===")
