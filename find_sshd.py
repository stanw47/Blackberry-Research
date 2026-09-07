import glob,os
hits=[]
for p in glob.glob('/proc/[0-9]*'):
    pid=p.split('/')[2]
    try:
        cl=open(p+'/cmdline','rb').read().decode(errors='replace')
    except Exception:
        continue
    if 'sshd' in cl.lower() or 'ssh' in cl.lower() or 'scp' in cl.lower() or 'sftp' in cl.lower():
        hits.append((pid,cl))
for pid,cl in hits:
    print(pid, repr(cl[:90]))
print("TOTAL", len(hits))
