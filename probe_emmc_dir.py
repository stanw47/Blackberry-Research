import os
for base in ('/dev/emmc','/dev/emmc/boot0','/dev/emmc/boot1'):
    try:
        print(base, '->', os.listdir(base) if os.path.isdir(base) else '(not dir)')
    except OSError as e:
        print(base, 'ERR', e)
