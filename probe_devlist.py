import os,stat
for d in sorted(os.listdir('/dev')):
    p='/dev/'+d
    try:
        st=os.stat(p)
        m=stat.S_IFMT(st.st_mode)
    except OSError as e:
        m='ERR'+str(e.errno)
    if m in (stat.S_IFBLK, stat.S_IFCHR) or 'mmc' in d.lower() or 'emmc' in d.lower() or 'boot' in d.lower() or 'sd' in d.lower() or d in ('emmc',):
        print(p, 'mode='+oct(m) if isinstance(m,int) else m, 'rdev=', getattr(st,'st_rdev','?') if 'st' in dir() else '?')
