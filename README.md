# BlackBerry Research — Central Hub

> The **index and shared-knowledge base** for a multi-repo BlackBerry
> reverse-engineering collection. One repo per device; this hub holds only what
> applies to **two or more** devices: the cross-device mechanisms, the device-map
> standard, the shared toolchain, and the master status.

---

## Read this first

> **Research aid, not a flashing guide.** Unlocking bootloaders, editing eMMC
> boot partitions (`boot0`/`boot1`), toggling hardware write-protect, or
> flashing firmware can **permanently brick** a device with no recovery short of
> JTAG/ISP chip-out. Everything here is for **educational / defensive research
> on devices the author owns**. Firmware and proprietary blobs are **not**
> redistributed — each device repo has a `firmware/FETCH.md`. See
> [LEGAL.md](LEGAL.md). **Proceed at your own risk.**

**New here?** → [How to use this collection](#how-to-use-this-collection).

---

## The collection

| Device | Model | SoC | OS | Root | Unlock | Status | Repo |
|---|---|---|---|---|---|---|---|
| **Classic** | SQC100 (Q20) | MSM8960 | BB10/QNX | ✅ uid-0 | ⛔ HW-gated | rooted, bootable; A11-on-QNX port | [Classic](https://github.com/stanw47/Blackberry-Classic-Research) |
| **Passport** | SQW100 | MSM8974AA | BB10/QNX | ✅ (bricked) | ⛔ HW-gated | red-blink; `imggen` path mapped | [Passport](https://github.com/stanw47/Blackberry-Passport-Research) |
| **Q10** *(prototype)* | Q10 | MSM8960 | BB10/QNX | — | ? | device incoming | [Q10](https://github.com/stanw47/Blackberry-Q10-Research) |
| **Priv** | STV100 | MSM8992 | Android 6 | ⛔ | ⛔ | authboot/RTAS decoded | [Priv](https://github.com/stanw47/Blackberry-Priv-Research) |
| **KEYone** | BBB100-3 | MSM8953 | Android 7.1.1 | ⛔ | ⛔ | reachable KGSL/IOMMU bug (DoS) | [KEYone](https://github.com/stanw47/Blackberry-KeyOne-Research) |
| **KEY2** | BBF100-6 | SDM660 | Android→LOS 22.2 | ✅ | ✅ | **unlocked + LineageOS** | [KEY2](https://github.com/stanw47/Blackberry-Key2-Research) |
| **Bold 9930** | 9930 | MSM8655 | BBOS 7.1 | ⛔ | — | signing boundary mapped | [9930](https://github.com/stanw47/Blackberry-9930-Research) |

Machine-readable index: [`devices.yml`](devices.yml). Per-device cards: [`devices/`](devices/).

---

## How to use this collection

1. **Pick your device** from the table above and open its repo. Every device repo
   uses the same layout, so you learn it once:
   ```
   README.md   ← start here (status, TL;DR, key findings)
   SUMMARY.md  ← 10-line machine summary
   notes/      ← chronological session notes (the research trail)
   docs/       ← polished write-ups and guides
   devmaps/    ← machine-readable device map(s)
   recon/      ← raw captures (props, partitions, logs, dumps)
   tools/      ← device-specific scripts
   firmware/   ← NOT committed (fetch instructions + SHA-256)
   ```
2. **Want the underlying mechanisms?** See [Cross-device mechanisms](#cross-device-mechanisms).
3. **Comparing devices?** Use the [device-map standard](devmap/STANDARD.md) and
   `toolchain/devmap.py diff a.json b.json`.
4. **Reading a session note?** Each starts with a fixed header
   (date · device · access level · status) and a plain-language TL;DR.

---

## Headline results

- **KEY2 — unlocked and running LineageOS 22.2 (Android 15).** The only modern
  BlackBerry cracked: a UEFI-ABL buffer overflow (CVE-2021-1931) + the `kibo`
  payload. → [KEY2 repo](https://github.com/stanw47/Blackberry-Key2-Research)
- **Classic — real root (uid-0).** The BB10 `pathtrust` / `btool` / `__root`
  ritual; boot-partition write-protect is permanent, so unlock is hardware-gated.
  → [Classic repo](https://github.com/stanw47/Blackberry-Classic-Research)
- **KEYone — a reachable kernel bug.** CVE-2020-11261 / CVE-2023-33107-class
  KGSL/IOMMU range-validation flaw, reachable from unprivileged `shell` (a
  denial-of-service; not yet root). → [KEYone repo](https://github.com/stanw47/Blackberry-KeyOne-Research)
- **Priv — the whole boot gate decoded.** `authboot`/RTAS2 command authorization
  + ECDSA boot-image verification explain why no software unlock exists; plus a
  Widevine-trustlet underflow. → [Priv repo](https://github.com/stanw47/Blackberry-Priv-Research)
- **Passport — the no-desolder Android path.** MSM8974AA is the exact `imggen`
  target; the recovery from its red-blink state is the open task.
  → [Passport repo](https://github.com/stanw47/Blackberry-Passport-Research)

---

## Cross-device mechanisms

Durable findings that span devices. Each links to the device notes that prove it.

| Mechanism | Applies to | Doc |
|---|---|---|
| **authboot / RTAS2 command gate** — why software unlock is impossible | Priv, KEYone, (KEY2) | [cross-device/authboot-rtas.md](cross-device/authboot-rtas.md) |
| **Permanent eMMC boot-partition write-protect** (`bbss` / `B_PERM_WP_EN`) | Classic, Passport, Priv, KEYone | [cross-device/bbss-boot-wp.md](cross-device/bbss-boot-wp.md) |
| **BB10 root ritual** — `pathtrust` / `btool` / `__root` | Classic, Passport, Q10 | [cross-device/bb10-root-pathtrust.md](cross-device/bb10-root-pathtrust.md) |
| **Legacy LK `aboot` vs modern UEFI ABL** — why KEY2 ≠ KEYone | all Android | [cross-device/lk-vs-abl.md](cross-device/lk-vs-abl.md) |
| **EDL / firehose** — the universal bypass (physical entry + signed programmer) | all Qualcomm | [cross-device/edl-firehose.md](cross-device/edl-firehose.md) |
| **QNX `vtnvfs` / `/nvram` token storage** | Classic, Passport, Priv, KEYone | [cross-device/qnx-vtnvfs.md](cross-device/qnx-vtnvfs.md) |

---

## Device-map standard (`devmap`)

One schema, every device and every access level, so any two devices can be
compared directly:

```
L0 usb → L1 fastboot/authboot → L2 adb → L3 root → L4 qnx → L5 edl
```

- Schema + rules: **[devmap/STANDARD.md](devmap/STANDARD.md)**
- Collected maps: [`devmaps/`](devmaps/)
- Compare: `python3 toolchain/devmap.py diff devmaps/a.json devmaps/b.json`

---

## Shared toolchain

Tools used by 2+ devices (device repos reference these rather than copy them):

| Tool | Purpose |
|---|---|
| `toolchain/devmap.py` | create / probe / diff device maps |
| `toolchain/fastboot_libusb.py` | drive BlackBerry fastboot (`0FCA:8040`) over libusb |
| `toolchain/fb_probe.py` | robust fastboot-over-libusb probe |
| `toolchain/lk_analyze.py` | LK (`emmc_appsboot.mbn`) MBN/ELF analyzer |
| `toolchain/elf_triage.py` | ELF triage (exports + interesting strings) |

The BB10 Dev-Mode **SSH connect recipe** (fresh 4096-bit key + `blackberry-connect`
tunnel + paramiko with QNX algorithm fixes) is documented in
[docs/ssh-connection-linux.md](docs/ssh-connection-linux.md).

---

## Repository layout (this hub)

| Path | Contents |
|---|---|
| `README.md` | this file |
| `STATUS.md` | master status + changelog of major updates |
| `devices.yml` | machine-readable collection index |
| `devices/` | one summary card per device |
| `cross-device/` | mechanisms shared by multiple devices |
| `devmap/` | the device-map standard |
| `devmaps/` | collected device maps (JSON) |
| `toolchain/` | shared scripts |
| `templates/` | the standard device-repo + note templates |
| `docs/` | SSH connection guide |
| `LEGAL.md`, `SECURITY.md` | legal / disclosure notes |

---

## How the collection is maintained

- **Format:** the per-device layout and README/note structure are defined by the
  [`templates/`](templates/). Device repos follow them so the collection stays
  consistent and readable.
- **Visibility:** device repos start **private** and are flipped **public** once
  a write-up is ready.
- **No data loss:** device work is copied into its repo; nothing is deleted to
  reorganize.
- **Big binaries never enter git:** firmware/autoloaders/dumps live outside the
  repo (or in `firmware/` fetch notes) with SHA-256.

---

## License

Research notes and original scripts are provided for educational purposes;
third-party code retains its own license. See [LEGAL.md](LEGAL.md).
