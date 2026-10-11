# KEYone factory-mode + Priv mux: Linux host runbook

The Windows host is blocked by a WinUSB exclusivity wedge (the BlackBerry
Device Manager stack holds the KEYone's auth interface; err 5 on every
open, survives reboots/replugs). On Linux the auth/mux interfaces are plain
libusb devices - no wedge, no manager. This runbook covers both lanes.

## 0. Host prep (Debian-family)

```bash
sudo apt install -y android-sdk-platform-tools libusb-1.0-0 python3-pip
pip3 install pyusb
# udev rule for the BlackBerry devices (unplug/replug after):
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="0fca", MODE="0666"' | sudo tee /etc/udev/rules.d/90-bb.rules
sudo udevadm control --reload
```

The fastboot binary also ships in the autoloaders
(`host/linux-x86/bin/fastboot`, AAW068/ABL766 zips) if the distro package
isn't available.

## 1. KEYone factory-mode lane (the primary goal)

Prereqs: KEYone in fastboot mode (Power+VolDown from off).

```
(a) tools/auth_oracle.py   - listens on 0FCA:8040 intf 1 (the auth
     interface), answers the device's has-permission requests with YES:
       DEV -> PC {0xbba78701, 0x1012, tool_name} -> PC replies {.., 0x1013, 1}
       DEV -> PC {0xbba78701, 0x1014, code}      -> PC replies {.., 0x1015, 1}
(b) in parallel: fastboot -s <serial> oem set-factory-mode
```

Expected: the device prints "Attempting to switch mode to FACTORY MODE...",
`set_bootmode(0,0)` runs (from PRODUCT mode: "Skipping Factory transistion
wipe" - no wipe), boot count = 100, RPMB write, auto-reboot.
Verify: `fastboot getvar bootmode` -> FACTORY_MODE (or the boot count).

If the device doesn't answer the oracle's handshake: run
`tools/auth_flow.py handshake` first to confirm the raw channel (the
0x2000/0x2001 exchange), then the oracle.

## 2. Priv mux lane (the canary ladder)

Prereqs: Priv in fastboot (Power+VolDown; PID 0fca:8030). The mux interface
= intf 1 ("mux", ff/01/ff). On Linux it's a plain bulk interface - the
RimUsb.sys wall from Windows doesn't exist.

The aboot-side expectations (session 5/6):
- control packet: {op u8, chan u8, ?, param u8, len u16, cmd u16, payload}
- OPEN_REQUEST (inner cmd 1): payload = hex-ASCII channel name (0x14 bytes);
  channels: AUTHBOOT/NVSIG/DBGSIG/DDT/STP -venice{apac,att,emea,vzw,na,sprint}
- version clamp: [r6+6] in 3..8 accepted
- the device NAKs opens from the 2017-era client (missing tool registration;
  "bbauthtool: Tool name not found. Caller should do rtas_init again")

The empirical goal: drive the mux (raw bulk) through tool registration +
OPEN(NVSIG-venicena) + challenge, then send the oversized ASN.1 nv_sig
response (session 5: sb in 181..253) -> canary oracle. LCG candidates if
the TZ RNG fails: 0x11, 0x3284A, ... (state*0x3039+0x11, BSS-zero seed).

## 3. Portability notes

- tools/auth_oracle.py and tools/auth_flow.py already use pyusb/libusb; on
  Linux the `os.add_dll_directory` calls are no-ops and the default system
  libusb is used.
- tools/auth_winusb.py is Windows-only (WinUSB ctypes) - not needed here.
- The pcauthtool/authboot Windows exes are not needed: the fastboot command
  alone drives the device; the oracle answers the auth channel.

## 4. Status when this was written (2026-10-12)

- KEYone: permission protocol fully decoded (device trusts the tool's
  0x1015 answer); factory transition = wipe-free from PRODUCT mode; the
  only blocker on Windows = the err-5 wedge. On Linux this is expected to
  go through on the first attempt.
- Priv: mux dispatcher decoded (session 6); canary = SCM random w/
  unseeded LCG fallback (deterministic if the 2016 TZ lacks the RNG svc);
  nv_sig response overflow @0xf953e68 (canary-gated).
