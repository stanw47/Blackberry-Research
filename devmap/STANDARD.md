# devmap — Standardized Device Mapping Standard (v1.0)

A single, OS-agnostic, access-level-agnostic way to fully enumerate a mobile
device (BlackBerry or otherwise) and record everything in one machine-readable
map. Works whether you have nothing but USB, or fastboot, or an unprivileged
ADB shell, or root, or a QNX/BB10 SSH session.

The goal: **one schema, many probes, one map per device**, so any two devices
(BB10 QNX, Android, locked, unlocked, rooted, bare) can be compared directly.

## 1. Access levels (what you can do determines what you can see)

| Level | Name | Typical transport | What it unlocks |
|-------|------|-------------------|-----------------|
| L0 | `usb` | raw USB descriptors | VID/PID, interfaces, endpoints, strings |
| L1 | `fastboot` | bootloader fastboot/authboot | product, serial, vars, partition table (read-only) |
| L2 | `adb` | unprivileged shell (uid 2000) | props, /proc, /sys, packages, services, SELinux denials |
| L3 | `adb-root` / `root` | rooted shell (uid 0) | block devices, /nvram, tokens, kernel maps, write primitives |
| L4 | `qnx` | BB10 dev-mode SSH / root | QNX devctl, /dev/emmc, PPS, slog2, procmgr abilities |
| L5 | `edl` | Qualcomm EDL (9008) | raw flash, firehose — hardware/key gated |

A map records the **highest level reached** and, per data point, **which level
was required to observe it**. Missing data is not "absent"; it is "not visible
at this level".

## 2. The map schema

Top-level keys (all optional; probes fill what they can):

```jsonc
{
  "devmap_version": "1.0",
  "generated_utc": "2026-10-05T00:00:00Z",
  "provenance": {                 // how this map was obtained
    "method": "live-probe|corpus-import|manual",
    "sources": [],                // files/sessions/artifacts the data came from
    "notes": ""
  },
  "identity": {
    "serial": "", "model": "", "codename": "", "manufacturer": "",
    "os": { "family": "android|bb10-qnx", "version": "", "build": "", "patch": "" },
    "soc": { "name": "", "hwid": "" }
  },
  "access": {
    "level": "usb|fastboot|adb|adb-root|root|qnx|edl",
    "levels_seen": [],            // every level reached this session
    "capabilities": {}            // e.g. {"flash":"rw","block_rw":false,...}
  },
  "hardware": {
    "cpu": {}, "memory": {}, "storage": {},
    "peripherals": [],            // [{name, bus, addr, driver, fw, notes}]
    "security_hw": []             // [{name, detail}]
  },
  "storage_layout": {
    "emmc": { "cid": "", "name": "", "manfid": "", "date": "", "ext_csd": {} },
    "gpt": { "entries": [] },
    "partitions": [],             // [{name, size, ro, wp, verified, notes}]
    "mounts": []                  // [{dev, path, fstype, opts, verified}]
  },
  "boot": {
    "chain": [],                  // [{stage, image, load, verified_by, signed}]
    "verification": {},           // {secure_boot, root_of_trust, ecdsa/rsa, anti_rollback}
    "write_protect": {}           // {boot0, boot1, permanent, ext_csd_bytes}
  },
  "security": {
    "selinux": {},                // {mode, policy_ver, notable_denials}
    "lsm": [],                    // [selinux, pathtrust, bide, ...]
    "kernel": {},                 // {version, grsec, pax, hardening[]}
    "verified_boot": {},          // {state, dm_verity, avb}
    "write_gates": []             // human-readable gates blocking each capability
  },
  "surface": {
    "interfaces": [],             // [{name, transport, reachable_at, notes}]
    "devices": [],                // [{path, mode, owner, selinux, reachable}]
    "sockets": [],                // [{path, type, selinux, domain}]
    "services": [],               // [{name, domain, binary}]
    "packages": []                // Android only (optional)
  },
  "findings": [                   // [{id, title, component, cve, reachable, impact, status}]
  ]
}
```

## 3. Probe methodology

Probes are **layered**: each runs only if its access level is available, and
records the level it ran at. Every probe is read-only unless explicitly marked
`--allow-write`.

| Probe | Level | Collects |
|-------|-------|----------|
| `usb` | L0 | VID/PID, interfaces, endpoints, iSerial, iProduct |
| `fastboot` | L1 | `getvar all`, `oem info`, partition list, product/serial |
| `adb` | L2 | props, `/proc/cpuinfo`, `/proc/devices`, `/proc/misc`, `/sys/bus/i2c`, mounts, SELinux mode, packages, services |
| `adb-block` | L2 (DAC) | readable block devs, `/sys/block` (usually denied) |
| `adb-root` | L3 | full partition table, `/nvram`, tokens, kallsyms addresses, kernel config |
| `qnx` | L4 | `/dev/emmc/*`, devctl CID/CSD/ext_csd, PPS, slog2, procmgr abilities, autoloader info |
| `edl` | L5 | Sahara/Firehose presence, programmer signature, raw GPT |

## 4. Normalization rules

- **OS-agnostic hardware**: Android `/sys/bus/i2c/devices/*/name` and QNX PPS
  device records both normalize into `hardware.peripherals`.
- **Storage**: Android `by-name` partitions and QNX `/dev/emmc/*` both normalize
  into `storage_layout.partitions` with a common `wp`/`ro` field.
- **Security gates**: a "gate" is any mechanism that blocks a capability
  (SELinux, hardware WP, fused key, server auth). Recorded in
  `security.write_gates` with the capability it blocks.
- **Findings** use a stable `id` (`<component>-<cve-or-slug>`) so maps from
  different sessions diff cleanly.
- **Provenance**: every map states how it was made. A live probe records
  `method: live-probe`; a map reconstructed from prior dumps, notes, or
  reference material records `method: corpus-import` and lists its sources,
  so a corpus map is never mistaken for a fresh observation.

## 5. Comparison

A device can only be in one mode at a time, so a complete map is built from
per-mode probes and combined:

```
py tools/devmap.py probe  --out keyone-adb.json      # L0+L2 while booted
py tools/devmap.py probe  --out keyone-fastboot.json # L0+L1 in bootloader
py tools/devmap.py merge keyone-adb.json keyone-fastboot.json --out keyone.json
```

`merge` unions lists (interfaces, mounts, findings), fills empty fields, and
recomputes `access.level` as the highest level seen.

`devmap diff a.json b.json` reports:
- identity/build changes,
- new/removed access levels,
- security-gate changes (the important one),
- new/removed findings.

This is how you track a device across firmware updates, or compare two devices
of the same family (e.g. KEYone vs KEY2, Classic vs Passport).

## 6. Example maps

- `devmaps/keyone-bbb100-3.json` — Android 7.1.1, unprivileged ADB (L2).
- `devmaps/key2-bbf100-6.json` — LineageOS 22.2 (Android 15), unprivileged ADB (L2).
- `devmaps/classic-sqn100-1.json` — BB10 QNX, root + EDL (L4/L5), corpus-import.
- `devmaps/passport-sqw100-1.json` — BB10 QNX, root (L4), corpus-import.

These four demonstrate the same schema spanning two operating systems, three
device generations, and two very different security models.
