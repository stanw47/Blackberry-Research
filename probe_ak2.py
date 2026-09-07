d=open("/etc/ssh/authorized_keys2","rt").read()
lines=[l for l in d.splitlines() if l.strip() and l.strip().startswith("ssh-rsa")]
print("key lines:", len(lines))
for l in lines:
    print("  ends:", l.rsplit(" ",1)[-1], "| start:", l[:18])
