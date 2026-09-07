import os,re
d=open("/accounts/1000/shared/misc/berrycore/pidin_root.txt","rt",errors="replace").read()
for line in d.splitlines():
    if re.search(r'sdmmc|emmc|mmc|msmsdcc|devb', line, re.I):
        print(line[:160])
