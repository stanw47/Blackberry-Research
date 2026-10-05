# BlackBerry Research — Central Hub

> The **central index** for a multi-repo BlackBerry reverse-engineering
> collection: one repo per device, plus this hub for **cross-device mechanisms**,
> the **device-map standard**, shared **toolchain**, and the **master status**.
>
> New here? Read **[Start here](#start-here)** below, then jump to your device.

---

## Disclaimer

> **Research aid, not a flashing guide.** Unlocking bootloaders, editing eMMC
> boot partitions (`boot0`/`boot1`), toggling write-protect, or flashing
> firmware can **permanently brick** a device with no recovery short of
> JTAG/ISP chip-out. Everything here is for educational / defensive research on
> devices the author owns. **Proceed at your own risk.** Third-party firmware
> is not redistributed; see each repo's `firmware/FETCH.md` and [LEGAL.md](LEGAL.md).

---

## Start here

1. **Find your device** in the collection table below.
2. Open that device's repo — every device repo has the same layout
   (`README` → `notes/` → `docs/` → `devmaps/` → `recon/` → `tools/`).
3. Want the *mechanisms* that span devices? See **[cross-device/](cross-device/)**.
4. Comparing devices? Use the **[devmap standard](devmap/STANDARD.md)** and
   `toolchain/devmap.py diff a.json b.json`.

---

## The collection

| Device | Model | SoC | OS | Status | Repo |
|---|---|---|---|---|---|
| **Classic** | SQC100 (Q20) | MSM8960 | BB10/QNX | rooted (uid-0), bootable; unlock HW-gated | [Classic](https://github.com/stanw47/Blackberry-Classic-Research) |
| **Passport** | SQW100 | MSM8974AA | BB10/QNX | rooted; red-blink/non-bootable; `imggen` path mapped | [Passport](https://github.com/stanw47/Blackberry-Passport-Research) |
| **Q10** *(prototype)* | Q10 | MSM8960 | BB10/QNX | device incoming | [Q10](https://github.com/stanw47/Blackberry-Q10-Research) |
| **Priv** | STV100 | MSM8992 | Android 6 | not rooted; authboot/RTAS decoded | [Priv](https://github.com/stanw47/Blackberry-Priv-Research) |
| **KEYone** | BBB100-3 | MSM8953 | Android 7.1.1 | locked; KGSL/IOMMU kernel bug (DoS) | [KEYone](https://github.com/stanw47/Blackberry-KeyOne-Research) |
| **KEY2** | BBF100-6 | SDM660 | Android→LOS 22.2 | **unlocked + LineageOS** | [KEY2](https://github.com/stanw47/Blackberry-Key2-Research) |
| **Bold 9930** | 9930 | MSM8655 | BBOS 7.1 | recon + signing-boundary mapped | [9930](https://github.com/stanw47/Blackberry-9930-Research) |

Machine-readable index: [`devices.yml`](devices.yml) · per-device pages: [`devices/`](devices/).

---

## Headline results

- **Classic — real root achieved.** uid-0 via the `pathtrust !__root` trick;
  boot-partition write-protect is permanent, so unlock is hardware-gated.
  → [Classic repo](https://github.com/stanw47/Blackberry-Classic-Research)
- **KEY2 — unlocked and running LineageOS 22.2** via CVE-2021-1931 (`kibo`).
  → [KEY2 repo](https://github.com/stanw47/Blackberry-Key2-Research)
- **KEYone — reachable kernel bug.** CVE-2020-11261 / CVE-2023-33107-class
  KGSL/IOMMU bug reachable from unprivileged `shell` (DoS, not yet root).
  → [KEYone repo](https://github.com/stanw47/Blackberry-KeyOne-Research)
- **Priv — the authboot/RTAS gate decoded end-to-end** (why software unlock is
  impossible without BlackBerry's service). → [Priv repo](https://github.com/stanw47/Blackberry-Priv-Research)
- **BB10 — the boot write-protect wall** (`BOOT_WP[173] B_PERM_WP_EN`) explained,
  plus the `imggen` prototype-bootloader path. → cross-device below.

---

## Cross-device mechanisms

Findings that apply to **two or more** devices live here. Each links to the
device notes that prove it.

| Mechanism | Applies to | Doc |
|---|---|---|
| authboot / RTAS command gate | Priv, KEYone, (KEY2) | [cross-device/authboot-rtas.md](cross-device/authboot-rtas.md) |
| Permanent eMMC boot-partition write-protect (`bbss`) | Classic, Passport, (Priv) | [cross-device/bbss-boot-wp.md](cross-device/bbss-boot-wp.md) |
| BB10 pathtrust / `btool` / `__root` root ritual | Classic, Passport | [cross-device/bb10-root-pathtrust.md](cross-device/bb10-root-pathtrust.md) |
| Legacy LK bootloader vs modern UEFI ABL | Priv/KEYone vs KEY2 | [cross-device/lk-vs-abl.md](cross-device/lk-vs-abl.md) |
| EDL / firehose programmer situation | all Qualcomm | [cross-device/edl-firehose.md](cross-device/edl-firehose.md) |
| QNX `vtnvfs` / `/nvram` token storage | Classic, Passport, Priv | [cross-device/qnx-vtnvfs.md](cross-device/qnx-vtnvfs.md) |

---

## Device-map standard

One schema, every device and access level (L0 USB → L5 EDL), so any two devices
can be compared directly. → **[devmap/STANDARD.md](devmap/STANDARD.md)**

```
toolchain/devmap.py new|probe|diff
```

Collected maps live in [`devmaps/`](devmaps/).

---

## Shared toolchain

Tools used by 2+ devices live in [`toolchain/`](toolchain/): `devmap.py`,
`fastboot_libusb.py`, `fb_probe.py`, `lk_analyze.py`, `elf_triage.py`, and the
BB10 SSH connect recipe (`blackberry-connect` + paramiko). Device repos
reference these rather than copying.

---

## Repository layout (this hub)

| Path | Contents |
|---|---|
| `devices/` | one summary page per device (status + headline + repo link) |
| `cross-device/` | mechanisms shared by multiple devices |
| `devmap/` | the device-map **standard** |
| `devmaps/` | collected device maps (JSON) |
| `toolchain/` | shared scripts |
| `templates/` | the standard device-repo + note templates |
| `docs/` | [STANDARDS.md](docs/STANDARDS.md) (the format standard), connection guide, BB10 reference |
| `devices.yml` | machine-readable collection index |
| `STATUS.md` | master status + changelog of major updates |

---

## How the collection is maintained

- **Standard:** [`docs/STANDARDS.md`](docs/STANDARDS.md) — repo layout, README
  structure, note format, devmap schema, big-binary policy.
- **Device repos** stay **private** until a write-up is ready, then flip public.
- **This hub never deletes device work** — content is copied to the device repo;
  the hub keeps history.

---

## License

Research notes and original scripts are provided for educational purposes;
third-party code retains its own license. See [LEGAL.md](LEGAL.md).
