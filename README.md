# BlackBerry Research — Central Hub

> A **multi-repo reverse-engineering collection**: one repo per BlackBerry
> device, plus this hub for cross-device mechanisms, the device-map standard,
> shared tooling, and the master status.
>
> Maintained by **[Williamson Security Solutions](https://williamsonsecuritysolutions.com)**.

---

## Disclaimer

> **Research aid, not a flashing guide.** Unlocking bootloaders, editing eMMC
> boot partitions, toggling write-protect, or flashing firmware can
> **permanently brick** a device. Everything here is for **educational /
> defensive research on devices the owner controls**. Firmware and proprietary
> blobs are **not** redistributed. **At your own risk.**

---

## The collection

| Device | Model | SoC | OS | Root | Unlock | Repo |
|---|---|---|---|---|---|---|
| **Classic** | SQC100 (Q20) | MSM8960 | BB10/QNX | ✅ uid-0 | ⛔ HW-gated | [→](https://github.com/stanw47/Blackberry-Classic-Research) |
| **Passport** | SQW100 | MSM8974AA | BB10/QNX | ✅ (bricked) | ⛔ HW-gated | [→](https://github.com/stanw47/Blackberry-Passport-Research) |
| **Q10** *(prototype)* | Q10 | MSM8960 | BB10/QNX | — | ? | [→](https://github.com/stanw47/Blackberry-Q10-Research) |
| **Priv** | STV100-1 | MSM8992 | Android 6 | ⛔ | ⛔ | [→](https://github.com/stanw47/Blackberry-Priv-Research) |
| **KEYone** | BBB100-3 (Sprint) | MSM8953 | Android 7.1.1 | ⛔ | ⛔ | [→](https://github.com/stanw47/Blackberry-KeyOne-Research) |
| **KEY2** | BBF100-6 (India/APAC, dual-SIM) | SDM660 | Android→LOS 22.2 | ✅ | ✅ | [→](https://github.com/stanw47/Blackberry-Key2-Research) |
| **Bold 9930** | 9930 (Sprint) | MSM8655 | BBOS 7.1 | ⛔ | — | [→](https://github.com/stanw47/Blackberry-9930-Research) |

Machine-readable index: [`devices.yml`](devices.yml).

---

## How to contribute

- Browse the collection and open the repo for your device.
- Found an error, an improvement, or have a device/tool to share? Visit
  **[williamsonsecuritysolutions.com](https://williamsonsecuritysolutions.com)**
  and get in touch — **suggestions and corrections are very welcome.**
- Each device repo starts with the same layout and the same README structure,
  so you learn it once.

---

## Devices at a glance

### Classic (SQC100 / Q20)
- **Device details:** MSM8960 · BB10/QNX 10.3.3.3216 · ClassicNA.
- **Current status:** rooted (real uid-0), bootable, recoverable; unlock is
  hardware-gated.
- **Achieved:** real uid-0 via `pathtrust !__root`; eMMC read without desolder;
  permanent boot-WP proven.
- **In progress:** the **A11-on-QNX runtime port** (bionic shim runs; binder +
  A11 userland next).
- **Future plans:** break the binder resmgr EPERM wall; build the A11 userland.
- **Repo:** [Classic](https://github.com/stanw47/Blackberry-Classic-Research)

### Passport (SQW100)
- **Device details:** MSM8974AA · BB10/QNX · WindermereEMEA.
- **Current status:** rooted previously; **red-blink / non-bootable** (11011).
- **Achieved:** driver forensics complete; `FS_DIRTY_ALL` shown RPMB-backed;
  `imggen` no-desolder Android path mapped.
- **In progress:** device recovery.
- **Future plans:** UART capture / chip replacement; then the no-desolder path.
- **Repo:** [Passport](https://github.com/stanw47/Blackberry-Passport-Research)

### Q10 (prototype)
- **Device details:** MSM8960 · BB10/QNX · prototype unit.
- **Current status:** **device incoming (~12 h)**; repo scaffolded.
- **Achieved:** —
- **In progress:** —
- **Future plans:** map L0→L1; test whether the engineering bootloader accepts
  unsigned images.
- **Repo:** [Q10](https://github.com/stanw47/Blackberry-Q10-Research)

### Priv (STV100-1)
- **Device details:** MSM8992 · Android 6.0.1 (AAW068) · venicena.
- **Current status:** not rooted; no public software path.
- **Achieved:** full `authboot`/RTAS + ECDSA boot gate decode; Widevine-trustlet
  underflow; factory/token stack shown dead.
- **In progress:** audit-only.
- **Future plans:** kernel 0-day, TrustZone/trustlet, or ISP/EDL (all gated).
- **Repo:** [Priv](https://github.com/stanw47/Blackberry-Priv-Research)

### KEYone (BBB100-3)
- **Device details:** MSM8953 · Android 7.1.1 (ABL766) · **Sprint, carrier-locked**.
- **Current status:** locked; no root; one reachable kernel bug (DoS).
- **Achieved:** KGSL/IOMMU bug (CVE-2020-11261 / CVE-2023-33107 class)
  reproduced from `shell`; autoloader teardown (signed firehose + symbolized
  aboot).
- **In progress:** turning the KGSL bug into kernel R/W → root.
- **Future plans:** complete the KGSL chain; or physical EDL → `devinfo` patch.
- **Repo:** [KEYone](https://github.com/stanw47/Blackberry-KeyOne-Research)

### KEY2 (BBF100-6)
- **Device details:** SDM660 · Android 8.1 → LineageOS 22.2 · **India/APAC,
  dual-SIM**.
- **Current status:** **unlocked + running LineageOS 22.2 (Android 15)**.
- **Achieved:** CVE-2021-1931 unlock (kibo); full tool RE; LineageOS port.
- **In progress:** ROM stability (SELinux/encryption, keyboard touchpad).
- **Future plans:** polish the ROM; possibly newer Android.
- **Repo:** [KEY2](https://github.com/stanw47/Blackberry-Key2-Research)

### Bold 9930
- **Device details:** MSM8655 · BBOS 7.1.0.1066 · **Sprint**.
- **Current status:** recon + signing-boundary mapped.
- **Achieved:** module dump; RRT signing wall mapped; BootROM first-contact;
  firmware + update protocol decoded.
- **In progress:** BootROM lane.
- **Future plans:** BootROM-based custom-code path.
- **Repo:** [9930](https://github.com/stanw47/Blackberry-9930-Research)

---

## Community Activity (collection-wide)

- **BB10 (Classic/Passport/Q10):** the platform is EOL, but the community keeps
  it alive — **Oleksandr (bb10.root.sx)** documented the pathtrust root and
  RAM-loader mechanics; **BBAndroids/balika011** published the `imggen`
  prototype-bootloader unlock; rooted autoloaders and **BerryCore** are widely
  shared. No custom OS exists; the Android-on-QNX port here is original work.
- **Priv:** **never rooted** (an 8-year XDA bounty unclaimed); community effort
  is audit + hardware (prototype bootloader swap).
- **KEYone:** **no public unlock/root**; the community only reaches debloat/FRP.
- **KEY2:** **the success story** — community unlock (kibo) and
  LineageOS//e/OS ports; active on XDA + postmarketOS.
- **9930:** hybrid-OS community (recombining RIM-signed modules); no root; the
  2014 bootloader class is the only door.

---

## Cross-device mechanisms

| Mechanism | Applies to | Doc |
|---|---|---|
| authboot / RTAS2 command gate | Priv, KEYone, (KEY2) | [cross-device/authboot-rtas.md](cross-device/authboot-rtas.md) |
| Permanent eMMC boot-partition write-protect (`bbss`) | Classic, Passport, Priv, KEYone | [cross-device/bbss-boot-wp.md](cross-device/bbss-boot-wp.md) |
| BB10 root ritual (`pathtrust`/`btool`/`__root`) | Classic, Passport, Q10 | [cross-device/bb10-root-pathtrust.md](cross-device/bb10-root-pathtrust.md) |
| Legacy LK `aboot` vs modern UEFI ABL | all Android | [cross-device/lk-vs-abl.md](cross-device/lk-vs-abl.md) |
| EDL / firehose | all Qualcomm | [cross-device/edl-firehose.md](cross-device/edl-firehose.md) |
| QNX `vtnvfs` / `/nvram` token storage | Classic, Passport, Priv, KEYone | [cross-device/qnx-vtnvfs.md](cross-device/qnx-vtnvfs.md) |

**Device-map standard:** [devmap/STANDARD.md](devmap/STANDARD.md) · maps in
[`devmaps/`](devmaps/) · compare with `toolchain/devmap.py diff`.

**Shared toolchain:** [`toolchain/`](toolchain/) (`devmap.py`,
`fastboot_libusb.py`, `fb_probe.py`, `lk_analyze.py`, `elf_triage.py`).

---

## Repository layout (this hub)

| Path | Contents |
|---|---|
| `README.md` | this file |
| `STATUS.md` | master status + changelog |
| `devices.yml` | machine-readable index |
| `devices/` | one summary card per device |
| `cross-device/` | mechanisms shared by multiple devices |
| `devmap/`, `devmaps/` | the device-map standard + collected maps |
| `toolchain/` | shared scripts |
| `templates/` | the standard device-repo + note templates |
| `docs/` | SSH connection guide |

---

## Citations & Acknowledgements

- **Oleksandr / bb10.root.sx** — BB10 root, pathtrust, RAM-loader research.
- **BBAndroids (balika011, imggen, passport_stage3)** — prototype-bootloader unlock.
- **BotchedRPR / kibo** and **Christopher Wade (Pen Test Partners)** — CVE-2021-1931.
- **Qualcomm** — the KGSL/IOMMU and ABL CVEs documented here.
- The **XDA / CrackBerry / postmarketOS / bb10.root.sx** communities.

---

## License

Research notes and original scripts are provided for educational purposes;
third-party code retains its own license. See [LEGAL.md](LEGAL.md).
