#!/usr/bin/env python3
"""
devmap.py - standardized, OS-agnostic, access-level-agnostic device mapping.

Produces one machine-readable JSON map per device (see docs/devmap/STANDARD.md).
Works across Android and BB10/QNX, at whatever access level is available
(USB -> fastboot -> adb -> root -> qnx -> edl).

Usage:
  py devmap.py probe  [--serial S] [--out FILE]     # auto-detect + full probe
  py devmap.py usb     [--out FILE]                 # L0 only
  py devmap.py fastboot[--out FILE]                 # L1 only
  py devmap.py adb     [--serial S] [--out FILE]    # L2 only
  py devmap.py merge A.json B.json ... [--out FILE] # combine mode maps
  py devmap.py diff A.json B.json

Read-only by default. No writes to the device.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

def _tool(env_name, default):
    p = os.environ.get(env_name, default)
    if os.path.isdir(p):
        p = os.path.join(p, os.path.basename(default))
    return p


ADB = _tool("ADB", r"C:\platform-tools\adb.exe")
FASTBOOT = _tool("FASTBOOT", r"C:\platform-tools\fastboot.exe")

DLL_DIR = r"C:\bb10mt"
if os.path.isdir(DLL_DIR):
    try:
        os.add_dll_directory(DLL_DIR)
    except (AttributeError, OSError):
        pass


# ----------------------------------------------------------------------------
# process helpers
# ----------------------------------------------------------------------------
def run(cmd, timeout=25):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except Exception as exc:
        return f"<error: {exc}>"


def sh(serial, cmd, timeout=25):
    c = [ADB]
    if serial:
        c += ["-s", serial]
    c += ["shell", cmd]
    return run(c, timeout)


# ----------------------------------------------------------------------------
# L0 - USB
# ----------------------------------------------------------------------------
BB_PIDS = {
    0x8030: "fastboot (BB boot mode)",
    0x8031: "intermediate/bootloader",
    0x8032: "Android composite",
    0x803A: "charge-only",
    0x8040: "fastboot (KEY2/KEYone)",
    0x8041: "MTP composite",
    0x8042: "ADB composite",
    0x8001: "loader/reload OS",
    0x8014: "mass storage",
    0x8017: "device/tether",
}


def probe_usb():
    out = {"interfaces": [], "notes": []}
    try:
        import usb.core
        import usb.util
        try:
            import libusb_package
            usb.core.USBError  # noqa
            backend = libusb_package.get_libusb1_backend()
            if backend is not None:
                usb.core.find(find_all=True, idVendor=0x0FCA, backend=backend)
        except Exception:
            pass
    except Exception as exc:
        out["notes"].append(f"pyusb unavailable: {exc}")
        return out
    devs = None
    try:
        import libusb_package
        backend = libusb_package.get_libusb1_backend()
        devs = usb.core.find(find_all=True, idVendor=0x0FCA, backend=backend)
    except Exception:
        try:
            devs = usb.core.find(find_all=True, idVendor=0x0FCA)
        except Exception as exc:
            out["notes"].append(f"usb find failed: {exc}")
            return out
    for dev in devs:
        pid = dev.idProduct
        entry = {
            "vid": "0x0fca",
            "pid": f"0x{pid:04x}",
            "name": BB_PIDS.get(pid, "unknown"),
            "bus": dev.bus,
            "address": dev.address,
            "ifaces": [],
        }
        try:
            entry["serial"] = dev.serial_number
        except Exception:
            pass
        try:
            cfg = dev.get_active_configuration()
            for intf in cfg:
                entry["ifaces"].append({
                    "num": intf.bInterfaceNumber,
                    "class": f"0x{intf.bInterfaceClass:02x}",
                    "subclass": f"0x{intf.bInterfaceSubClass:02x}",
                    "protocol": f"0x{intf.bInterfaceProtocol:02x}",
                    "endpoints": [f"0x{ep.bEndpointAddress:02x}" for ep in intf],
                })
        except Exception:
            pass
        out["interfaces"].append(entry)
    return out


# ----------------------------------------------------------------------------
# L1 - fastboot
# ----------------------------------------------------------------------------
def probe_fastboot(serial):
    out = {}
    c = [FASTBOOT]
    if serial:
        c += ["-s", serial]
    txt = run(c + ["getvar", "all"])
    if "FAILED" in txt and "unknown" in txt.lower():
        out["getvar_all"] = txt[:2000]
    else:
        kv = {}
        for line in txt.splitlines():
            m = re.match(r"\(bootloader\)\s*(\S+):\s*(.*)", line.strip())
            if m:
                kv[m.group(1)] = m.group(2)
        out["getvar"] = kv
    for name in ("product", "serialno", "secure", "unlocked", "variant"):
        out.setdefault("vars", {})[name] = run(c + ["getvar", name]).strip().splitlines()[-1] if run(c + ["getvar", name]).strip() else ""
    info = run(c + ["oem", "info"])
    if "FAILED" not in info:
        out["oem_info_raw"] = info[:4000]
        parsed = {}
        for line in info.splitlines():
            line = line.strip()
            for prefix in ("(bootloader)", "INFO"):
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
            if ":" in line and not line.startswith("Finished"):
                k, _, v = line.partition(":")
                if k.strip():
                    parsed[k.strip()] = v.strip()
        out["oem_info"] = parsed
    return out


# ----------------------------------------------------------------------------
# L2 - adb (unprivileged)
# ----------------------------------------------------------------------------
def parse_getprop(txt):
    props = {}
    for line in txt.splitlines():
        m = re.match(r"\[([^\]]+)\]:\s*\[(.*)\]", line.strip())
        if m:
            props[m.group(1)] = m.group(2)
    return props


DEVICE_CANDIDATES = [
    "/dev/binder", "/dev/hwbinder", "/dev/vndbinder", "/dev/ashmem",
    "/dev/kgsl-3d0", "/dev/kgsl-3d1", "/dev/ion", "/dev/dri/renderD128",
    "/dev/qseecom", "/dev/tee0", "/dev/teepriv0", "/dev/adsprpc-smd",
    "/dev/smd7", "/dev/smem_log", "/dev/pathtrust", "/dev/nvram",
    "/dev/block/bootdevice/by-name", "/dev/block/bootdevice",
    "/dev/block/mmcblk0", "/dev/block/mmcblk0boot0", "/dev/block/mmcblk0boot1",
    "/dev/ttyHSL0", "/dev/diag", "/dev/radio0", "/dev/watchdog",
    "/dev/random", "/dev/urandom", "/dev/zero", "/dev/null",
    "/dev/emmc/boot0", "/dev/emmc/boot1", "/dev/emmc/rpmb0",
    "/dev/emmc/nvram0", "/dev/emmc/dmi0", "/dev/emmc/os0", "/dev/emmc/os1",
    "/dev/emmc/uda0", "/dev/emmc/user0", "/dev/emmc/cal_work0",
    "/dev/emmc/radio0", "/dev/emmc/sd0",
    "/proc/boot/pathtrust", "/proc/boot/hold_boot",
]


def probe_devices(serial):
    paths = " ".join(DEVICE_CANDIDATES)
    txt = sh(serial, f"for p in {paths}; do stat -c '%n %a %U %G' $p 2>/dev/null; done")
    out = []
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            out.append({
                "path": parts[0],
                "mode": parts[1],
                "owner": f"{parts[2]}:{parts[3]}",
                "selinux": "",
                "reachable": "present",
            })
    return out


def probe_adb(serial):
    out = {}
    out["getprop"] = parse_getprop(sh(serial, "getprop"))
    out["cpuinfo"] = sh(serial, "cat /proc/cpuinfo")
    out["proc_devices"] = sh(serial, "cat /proc/devices")
    out["misc"] = sh(serial, "cat /proc/misc")
    out["mounts"] = sh(serial, "cat /proc/mounts")
    out["selinux"] = sh(serial, "getenforce").strip()
    out["id"] = sh(serial, "id").strip()
    out["i2c"] = sh(serial, "for d in /sys/bus/i2c/devices/*/name; do echo \"$d: $(cat $d 2>/dev/null)\"; done")
    out["devices"] = probe_devices(serial)
    out["block"] = sh(serial, "ls -la /dev/block/bootdevice/by-name/ 2>&1")
    out["services"] = sh(serial, "service list 2>/dev/null")
    out["packages"] = sh(serial, "pm list packages 2>/dev/null")
    out["denials"] = sh(serial, "dmesg 2>/dev/null | grep -i 'avc: denied' | tail -40")
    out["kernel"] = sh(serial, "uname -a").strip()
    out["sockets"] = sh(serial, "cat /proc/net/unix 2>/dev/null")
    out["modules"] = sh(serial, "cat /proc/modules 2>/dev/null")
    return out


# ----------------------------------------------------------------------------
# normalization into the standard schema
# ----------------------------------------------------------------------------
def normalize(usb, fb, adb, level):
    m = {
        "devmap_version": "1.0",
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "provenance": {
            "method": "live-probe",
            "sources": [l for l, v in (("usb", usb), ("fastboot", fb), ("adb", adb)) if v],
            "notes": "",
        },
        "identity": {},
        "access": {"level": level, "levels_seen": [level], "capabilities": {}},
        "hardware": {"peripherals": [], "security_hw": []},
        "storage_layout": {"partitions": [], "mounts": []},
        "boot": {},
        "security": {},
        "surface": {"interfaces": [], "devices": [], "sockets": [], "services": []},
        "findings": [],
    }
    props = (adb or {}).get("getprop", {})
    oem = (fb or {}).get("oem_info", {})

    m["identity"] = {
        "serial": props.get("ro.serialno") or oem.get("BSN") or "",
        "model": props.get("ro.product.model") or oem.get("Product") or "",
        "codename": props.get("ro.product.device", ""),
        "manufacturer": props.get("ro.product.manufacturer", ""),
        "os": {
            "family": "android" if props.get("ro.build.version.release") else "unknown",
            "version": props.get("ro.build.version.release", ""),
            "build": props.get("ro.build.display.id") or oem.get("Build", ""),
            "patch": props.get("ro.build.version.security_patch", ""),
        },
        "soc": {"name": props.get("ro.board.platform") or props.get("ro.hardware", ""), "hwid": ""},
    }

    if adb:
        m["access"]["capabilities"] = {
            "shell_uid": (adb.get("id", "").split()[0] if adb.get("id") else ""),
            "selinux": adb.get("selinux", ""),
            "block_rw": "<error" not in adb.get("block", "Permission denied") and "Permission denied" not in adb.get("block", "Permission denied"),
            "packages": "<error" not in adb.get("packages", "") and bool(adb.get("packages", "").strip()),
        }
        # peripherals from i2c names
        for line in adb.get("i2c", "").splitlines():
            mm = re.match(r"(/sys/bus/i2c/devices/[\w-]+)/name:\s*(\S+)", line)
            if mm:
                m["hardware"]["peripherals"].append({"bus": "i2c", "path": mm.group(1), "name": mm.group(2)})
        # device nodes
        m["surface"]["devices"] = adb.get("devices", [])
        # mounts
        for line in adb.get("mounts", "").splitlines():
            parts = line.split()
            if len(parts) >= 4:
                m["storage_layout"]["mounts"].append({
                    "dev": parts[0], "path": parts[1], "fstype": parts[2], "opts": parts[3]})
        # sockets
        for line in adb.get("sockets", "").splitlines():
            parts = line.split()
            if parts and parts[-1].startswith("/"):
                m["surface"]["sockets"].append({"path": parts[-1]})
        # services
        for line in adb.get("services", "").splitlines():
            parts = line.split(":", 1)
            if len(parts) == 2:
                m["surface"]["services"].append({"name": parts[1].strip()})
        m["security"]["selinux"] = {"mode": adb.get("selinux", ""), "notable_denials": adb.get("denials", "").count("avc: denied")}
        m["security"]["kernel"] = {"uname": adb.get("kernel", "")}
        m["boot"]["verification"] = {
            "verified_boot_state": props.get("ro.boot.verifiedbootstate", ""),
            "flash_locked": props.get("ro.boot.flash.locked", ""),
            "dm_verity": props.get("ro.boot.veritymode", ""),
        }

    if fb:
        m["boot"]["oem_info"] = fb.get("oem_info", {})
        m["boot"]["write_protect"] = {
            "wp_type": oem.get("WP Type", ""),
            "insecure": oem.get("Insecure", ""),
        }
        if fb.get("getvar"):
            m["surface"]["fastboot_vars"] = fb["getvar"]

    if usb:
        for i in usb.get("interfaces", []):
            m["surface"]["interfaces"].append({
                "vid": i.get("vid"), "pid": i.get("pid"), "name": i.get("name"),
                "ifaces": i.get("ifaces", []), "reachable_at": "usb"})

    return m


# ----------------------------------------------------------------------------
# merge
# ----------------------------------------------------------------------------
LEVEL_ORDER = ["usb", "fastboot", "adb", "adb-root", "root", "qnx", "edl"]


def deep_merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = deep_merge(a[k], v) if k in a else v
        return out
    if isinstance(a, list) and isinstance(b, list):
        seen = {json.dumps(x, sort_keys=True) for x in a}
        return a + [x for x in b if json.dumps(x, sort_keys=True) not in seen]
    if a in (None, "", [], {}):
        return b
    return a


def cmd_merge(paths, out_path):
    m = {}
    for p in paths:
        m = deep_merge(m, json.load(open(p, encoding="utf-8")))
    seen = m.get("access", {}).get("levels_seen", [])
    if seen:
        m["access"]["level"] = max(
            seen, key=lambda l: LEVEL_ORDER.index(l) if l in LEVEL_ORDER else -1)
    m["generated_utc"] = datetime.datetime.utcnow().isoformat() + "Z"
    m.setdefault("provenance", {})["method"] = "live-probe (merged)"
    m["provenance"]["notes"] = "merged from: " + ", ".join(os.path.basename(p) for p in paths)
    return m


# ----------------------------------------------------------------------------
# diff
# ----------------------------------------------------------------------------
def cmd_diff(a_path, b_path):
    a = json.load(open(a_path, encoding="utf-8"))
    b = json.load(open(b_path, encoding="utf-8"))
    def flat(d, p=""):
        out = {}
        if isinstance(d, dict):
            for k, v in d.items():
                out.update(flat(v, f"{p}.{k}" if p else k))
        elif isinstance(d, list):
            out[p] = json.dumps(d, sort_keys=True)
        else:
            out[p] = d
        return out
    fa, fb = flat(a), flat(b)
    keys = sorted(set(fa) | set(fb))
    print(f"{'KEY':<60} {'A':<28} {'B':<28}")
    for k in keys:
        va, vb = fa.get(k, "<missing>"), fb.get(k, "<missing>")
        if va != vb:
            sa, sb = str(va)[:27], str(vb)[:27]
            print(f"{k:<60} {sa:<28} {sb:<28}")


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def first_device(txt, state):
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == state:
            return parts[0]
    return None


def cmd_probe(args):
    level = "usb"
    usb = probe_usb()
    fb = None
    adb = None

    serial = args.serial
    adb_serial = first_device(run([ADB, "devices"]), "device")
    fb_serial = first_device(run([FASTBOOT, "devices"]), "fastboot")
    if adb_serial:
        adb = probe_adb(serial or adb_serial)
        level = "adb"
    elif fb_serial:
        fb = probe_fastboot(serial or fb_serial)
        level = "fastboot"
    else:
        if args.serial:
            fb = probe_fastboot(serial)

    m = normalize(usb, fb, adb, level)
    m["access"]["levels_seen"] = [l for l, v in (("usb", usb), ("fastboot", fb), ("adb", adb)) if v]
    return m


def main():
    ap = argparse.ArgumentParser(description="standardized device mapping")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("probe", "usb", "fastboot", "adb"):
        s = sub.add_parser(name)
        s.add_argument("--serial")
        s.add_argument("--out")
    d = sub.add_parser("diff")
    d.add_argument("a")
    d.add_argument("b")
    g = sub.add_parser("merge")
    g.add_argument("maps", nargs="+")
    g.add_argument("--out")
    args = ap.parse_args()

    if args.cmd == "diff":
        cmd_diff(args.a, args.b)
        return 0

    if args.cmd == "merge":
        m = cmd_merge(args.maps, args.out)
    elif args.cmd == "probe":
        m = cmd_probe(args)
    elif args.cmd == "usb":
        m = normalize(probe_usb(), None, None, "usb")
    elif args.cmd == "fastboot":
        m = normalize(None, probe_fastboot(args.serial), None, "fastboot")
    elif args.cmd == "adb":
        m = normalize(None, None, probe_adb(args.serial), "adb")

    txt = json.dumps(m, indent=2, sort_keys=True)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(txt)
        print(f"wrote {args.out} ({len(txt)} bytes)")
    else:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
