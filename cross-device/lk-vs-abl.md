# Legacy LK bootloader vs modern UEFI ABL

**Applies to:** the whole Android-BlackBerry line. This single architectural
split explains why the **KEY2 can be unlocked** but the **Priv/KEYone cannot**.

---

## Two bootloader generations

```
Legacy lane (LK / aboot):     Priv (MSM8992)  ──  KEYone (MSM8953)
Modern lane (UEFI ABL):       KEY2 (SDM660)   ──  KEY2 LE
```

| | Legacy lane | Modern lane |
|---|---|---|
| Bootloader | Qualcomm **LK** (`emmc_appsboot.mbn`) | UEFI **ABL** (`abl.elf`) |
| `getvar kernel` | `lk` | — |
| Unlock gate | authboot + bbss WP | authboot + bbss WP |
| Known bypass | **none** | **CVE-2021-1931** (ABL fastboot bug) |
| Community result | no unlock | **unlocked + LineageOS** (kibo) |

## Why the KEY2 fell

CVE-2021-1931 is a bug in Qualcomm's **ABL/fastboot** that BlackBerry/TCL never
patched on the SDM660 KEY2. The `kibo` tool (BotchedRPR) uses it for a permanent
unlock, then a modified boot image is needed because BlackBerry forces
FACTORY_MODE restrictions. This is **specific to the modern ABL stack**.

## Why the Priv/KEYone did not

- They use the **older LK `aboot`**, whose fastboot is the `authboot` fork
  (see [authboot-rtas.md](authboot-rtas.md)) — the CVE-2021-1931 path does not
  apply.
- The KEYone LK was audited for the classic LK bypasses (CVE-2013-2598,
  CVE-2014-0973); BlackBerry's build does not expose them.

## Evidence

- KEYone: `kernel:lk`, `authboot_api_ver:2.0`, `bootmode:PRODUCT_MODE` (live
  `fastboot getvar all`); `emmc_appsboot.mbn` symbolized analysis.
- KEY2: `kibo` + CVE-2021-1931, LineageOS 22.2 running.
- Priv: same LK/authboot design as KEYone.
