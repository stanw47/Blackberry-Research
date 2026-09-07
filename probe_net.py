import subprocess
for c in [["netstat","-an"],["pidin","-f"]]:
    try:
        out=subprocess.run(c,capture_output=True,text=True).stdout
        for l in out.splitlines():
            if "22" in l or "sshd" in l.lower():
                print(l)
    except Exception as e:
        print(c,"ERR",e)
