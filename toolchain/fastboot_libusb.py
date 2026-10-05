#!/usr/bin/env python3
"""
Minimal fastboot client over libusb/pyusb for BlackBerry KEYone (and KEY2).

Unlike Google's fastboot.exe (which needs the Android Bootloader Interface
driver), this talks to the raw USB device via libusb, so it works when the
interface is bound to WinUSB (e.g. installed with Zadig).

Usage:
    python fastboot_libusb.py                    # list matching devices
    python fastboot_libusb.py oem info
    python fastboot_libusb.py getvar all
    python fastboot_libusb.py oem device-info
    python fastboot_libusb.py reboot

Options:
    --vid 0x0FCA --pid 0x8040 --interface 0 --timeout 5000
"""
import argparse
import os
import sys
import time

# Make the known libusb DLL location available before importing usb.
for _d in (r"C:\bb10mt", os.path.dirname(os.path.abspath(__file__))):
    try:
        os.add_dll_directory(_d)
    except (AttributeError, FileNotFoundError, OSError):
        pass

try:
    import usb.core
    import usb.util
except Exception as exc:  # pragma: no cover
    print(f"[fatal] cannot import pyusb: {exc}")
    print("        install with: py -3.11 -m pip install pyusb")
    sys.exit(2)


def find_devices(vid, pid):
    return list(usb.core.find(find_all=True, idVendor=vid, idProduct=pid))


class Fastboot:
    def __init__(self, dev, interface=0, timeout=5000):
        self.dev = dev
        self.timeout = timeout
        self.interface = interface
        # Do NOT call set_configuration(); Windows already configured the device.
        self.cfg = dev.get_active_configuration()
        self.intf = self.cfg[(interface, 0)]
        self.ep_in = usb.util.find_descriptor(
            self.intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
            == usb.util.ENDPOINT_IN,
        )
        self.ep_out = usb.util.find_descriptor(
            self.intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
            == usb.util.ENDPOINT_OUT,
        )
        if self.ep_in is None or self.ep_out is None:
            raise RuntimeError("could not find bulk endpoints on interface")
        try:
            if dev.is_kernel_driver_active(interface):
                dev.detach_kernel_driver(interface)
        except (NotImplementedError, usb.core.USBError):
            pass
        usb.util.claim_interface(dev, interface)

    @property
    def endpoints(self):
        return f"IN=0x{self.ep_in.bEndpointAddress:02x} OUT=0x{self.ep_out.bEndpointAddress:02x}"

    def send(self, text):
        data = text.encode() if isinstance(text, str) else text
        self.ep_out.write(data, timeout=self.timeout)

    def read(self):
        return bytes(self.ep_in.read(4096, timeout=self.timeout))

    def collect(self, seconds=5.0):
        """Read until OKAY/FAIL or quiet timeout."""
        out = b""
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                out += self.read()
            except usb.core.USBError as exc:
                if "timeout" in str(exc).lower() or "timed out" in str(exc).lower():
                    break
                raise
            if b"OKAY" in out or b"FAIL" in out:
                break
        return out

    def command(self, text, seconds=5.0):
        self.send(text)
        return self.collect(seconds=seconds)

    def close(self):
        try:
            usb.util.release_interface(self.dev, self.interface)
        except Exception:
            pass


def show_response(raw):
    if not raw:
        print("  (no response / timeout)")
        return
    try:
        text = raw.decode("utf-8", "replace")
    except Exception:
        text = repr(raw)
    for line in text.replace("\r", "\n").split("\n"):
        if line:
            print(f"  | {line}")
    # also a compact hex view for the tail (useful when probing overflow)
    print(f"  [raw {len(raw)} bytes] {raw[:64].hex()}")


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="fastboot command, e.g. 'oem info'")
    ap.add_argument("--vid", default="0x0FCA")
    ap.add_argument("--pid", default="0x8040")
    ap.add_argument("--interface", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=5000)
    args = ap.parse_args()

    vid = int(args.vid, 0)
    pid = int(args.pid, 0)

    devices = find_devices(vid, pid)
    if not devices:
        print(f"[!] no device {vid:04x}:{pid:04x} found (in fastboot mode?)")
        sys.exit(1)

    print(f"[*] found {len(devices)} device(s) {vid:04x}:{pid:04x}")
    dev = devices[0]
    fb = Fastboot(dev, interface=args.interface, timeout=args.timeout)
    print(f"[*] claimed interface {args.interface} ({fb.endpoints})")

    cmd = " ".join(args.cmd).strip()
    if not cmd:
        # default recon sequence (read-only)
        for c in ("oem info", "oem device-info", "getvar all"):
            print(f"\n>>> {c}")
            show_response(fb.command(c))
    else:
        print(f"\n>>> {cmd}")
        show_response(fb.command(cmd))

    fb.close()


if __name__ == "__main__":
    main()
