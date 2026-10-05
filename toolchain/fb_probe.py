#!/usr/bin/env python3
"""
Robust fastboot-over-libusb probe for BlackBerry KEYone / KEY2.

Handles: device reset, command terminators, generous timeouts, raw hex dumps.
Useful for figuring out exactly how the BlackBerry bootloader expects commands,
and later for the CVE-2021-1931 overflow work.

Examples:
    # list
    py -3.11 fb_probe.py
    # reset the USB device, then send 'oem info' + NUL, watch the reply
    py -3.11 fb_probe.py --reset --term nul "oem info"
    # try getvar without a terminator
    py -3.11 fb_probe.py --term none "getvar:all"
    # send arbitrary bytes
    py -3.11 fb_probe.py --raw 6f656d20696e666f
"""
import argparse
import os
import sys
import time

for _d in (r"C:\bb10mt", os.path.dirname(os.path.abspath(__file__))):
    try:
        os.add_dll_directory(_d)
    except (AttributeError, FileNotFoundError, OSError):
        pass

try:
    import usb.core
    import usb.util
except Exception as exc:
    print(f"[fatal] cannot import pyusb: {exc}")
    sys.exit(2)

TERMS = {"none": b"", "nul": b"\x00", "lf": b"\n", "crlf": b"\r\n", "space": b" "}


def find(vid, pid):
    return list(usb.core.find(find_all=True, idVendor=vid, idProduct=pid))


def open_claim(vid, pid, interface, max_tries=10):
    for _ in range(max_tries):
        devs = find(vid, pid)
        if devs:
            dev = devs[0]
            try:
                cfg = dev.get_active_configuration()
                intf = cfg[(interface, 0)]
                ep_in = usb.util.find_descriptor(
                    intf,
                    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
                    == usb.util.ENDPOINT_IN,
                )
                ep_out = usb.util.find_descriptor(
                    intf,
                    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
                    == usb.util.ENDPOINT_OUT,
                )
                try:
                    if dev.is_kernel_driver_active(interface):
                        dev.detach_kernel_driver(interface)
                except (NotImplementedError, usb.core.USBError):
                    pass
                usb.util.claim_interface(dev, interface)
                return dev, ep_in, ep_out
            except usb.core.USBError as exc:
                print(f"[warn] open/claim attempt failed: {exc}")
        time.sleep(0.5)
    return None, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    ap.add_argument("--vid", default="0x0FCA")
    ap.add_argument("--pid", default="0x8040")
    ap.add_argument("--interface", type=int, default=0)
    ap.add_argument("--term", choices=list(TERMS), default="none")
    ap.add_argument("--raw", help="raw hex bytes to send instead of a command")
    ap.add_argument("--reset", action="store_true", help="USB reset before opening")
    ap.add_argument("--write-timeout", type=int, default=3000)
    ap.add_argument("--read-timeout", type=int, default=3000)
    ap.add_argument("--total-read", type=float, default=8.0)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    vid = int(args.vid, 0)
    pid = int(args.pid, 0)

    devs = find(vid, pid)
    print(f"[*] {len(devs)} device(s) {vid:04x}:{pid:04x}")
    if args.list or not devs:
        for d in devs:
            eps = []
            try:
                cfg = d.get_active_configuration()
                for i in cfg:
                    for ep in i:
                        eps.append(f"if{i.bInterfaceNumber} ep0x{ep.bEndpointAddress:02x}")
            except Exception as e:
                eps = [f"(desc err {e})"]
            print(f"    bus={d.bus} addr={d.address} sn={d.serial_number} {' '.join(eps)}")
        return

    if args.reset:
        try:
            devs[0].reset()
            print("[*] USB reset issued; waiting for re-enumeration")
            time.sleep(3)
        except Exception as exc:
            print(f"[warn] reset failed: {exc}")

    dev, ep_in, ep_out = open_claim(vid, pid, args.interface)
    if dev is None:
        print("[!] could not open/claim device")
        sys.exit(1)
    print(f"[*] claimed interface {args.interface} IN=0x{ep_in.bEndpointAddress:02x} OUT=0x{ep_out.bEndpointAddress:02x}")

    # Build payload
    if args.raw:
        payload = bytes.fromhex(args.raw)
        label = f"raw:{args.raw}"
    else:
        cmd = " ".join(args.cmd).strip()
        payload = cmd.encode() + TERMS[args.term]
        label = repr(cmd) + f" term={args.term}"

    print(f">>> send {label} ({len(payload)} bytes): {payload.hex()}")
    try:
        ep_out.write(payload, timeout=args.write_timeout)
        print("[*] OUT write OK")
    except usb.core.USBError as exc:
        print(f"[!] OUT write failed: {exc}")
        sys.exit(1)

    # Read
    out = b""
    deadline = time.time() + args.total_read
    while time.time() < deadline:
        try:
            chunk = bytes(ep_in.read(4096, timeout=args.read_timeout))
            if chunk:
                out += chunk
                print(f"[<] {len(chunk)} bytes: {chunk!r}")
            if b"OKAY" in out or b"FAIL" in out:
                break
        except usb.core.USBError as exc:
            msg = str(exc).lower()
            if "timeout" in msg or "timed out" in msg:
                continue
            print(f"[!] IN read error: {exc}")
            break

    print(f"[=] total {len(out)} bytes")
    if out:
        print(f"    text: {out.decode('utf-8','replace')!r}")
        print(f"    hex : {out.hex()}")
    else:
        print("    (no data)")


if __name__ == "__main__":
    main()
