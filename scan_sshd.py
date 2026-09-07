import glob
for p in glob.glob('/proc/[0-9]*'):
    try:
        cl=open(p+'/cmdline','rb').read().decode(errors='replace')
        if 'sshd' in cl:
            print(p.split('/')[2], repr(cl[:80]))
    except Exception as e:
        pass
print('scan done')
