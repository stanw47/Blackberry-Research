import os
paths = [
    "/apps/sys.android.gYABgKAOw1czN6neiAT72SGO.ns/native/system/xbin/btool",
    "/base/scripts/ota_info_pps.sh",
]
for p in paths:
    try:
        st = os.stat(p)
        print("== %s : uid=%d gid=%d mode=%o size=%d" % (p, st.st_uid, st.st_gid, st.st_mode & 0o7777, st.st_size))
        with open(p, "rb") as f:
            data = f.read().decode(errors="replace")
        # print lines around 25-40 and any pathtrust lines
        lines = data.splitlines()
        for i, ln in enumerate(lines, 1):
            if "pathtrust" in ln.lower() or (28 <= i <= 36):
                print("  %3d: %s" % (i, ln))
    except Exception as e:
        print("== %s : ERROR %r" % (p, e))