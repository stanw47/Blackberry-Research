# Device eMMC dumps (Passport / Windermere)

Raw dumps of the Passport's eMMC boot/secure partitions, captured live via
SSH+root on a windermereemea device (OS 10.3.3.x branch) using the documented
research access path (`g_Disk_Drivers` + `__root` + `dd` on block nodes).

> ⚠️ **PRIVACY / IDENTIFICATION WARNING**
>
> These images are **unique to a specific physical device**. They contain that
> device's hardware identity (`processor_id`, `usbloader_id`, `hwid`), secure
> boot state, and partition map material. Publishing them:
>
> - allows a third party to **fingerprint/identify your specific handset**;
> - exposes the exact SBL1 binary and its build-info format strings;
> - may leak secure-world state that is nominally device-unique.
>
> They are included **only** because the research notes reference their layout.
> If you cloned this and the dumps are yours, treat them as sensitive.

## Files

| File | Size | Description |
|------|------|-------------|
| `bb0_full.bin` | 4 MiB | Full `boot0` partition — contains **SBL1** (1 MiB nonzero). EFI PART at 0x200, "BootROM" GPT entry (LBA 34–511). SBL1 strings: "Build info", "Loading SBL image", "SBL1 decompression failed", "Jump to SBL1", "Preload images build info", "DDR training occurred, must reset". ELF magic at 0x4f9e8, 0x56e41, 0x757e9. |
| `bb1_full.bin` | 4 MiB | Full `boot1` partition — **blank** (all zeros, ~4 KiB noise). No SBL/ABOOT present. |
| `bb0_head.bin` | 64 KiB | First 64 KiB of `boot0` (GPT header + SBL1 header). |
| `bb1_head.bin` | 64 KiB | First 64 KiB of `boot1` (all zeros). |
| `os0_8M.bin` | 8 MiB | First 8 MiB of `os0` — QNX v1.2b boot loader at 0x0; IFS startup code ~0x25c594 ("STACK USAGE", "board_smp_start"), $OS table at 0x386d10, SFI markers at 0x25deb1/0x7b6f04, BB10 marker at 0x2c7126. |
| `os0_head.bin` | 64 KiB | First 64 KiB of `os0` (QNX boot loader). |
| `u0_sb.bin` | 256 KiB | First 256 KiB of `user0` (root filesystem, QNX6FS). |
| `o0_meta.bin` | 256 KiB | Second 256 KiB of `os0` (metadata region). |

## Hashes (SHA256)

```
bb0_full.bin  75108c669a25444ed852ca087997788845976e23c7da2a413b42ba77349b34bd
bb1_full.bin  bb9f8df61474d25e71fa00722318cd387396ca1736605e1248821cc0de3d3af8
```

## Capture Method

All reads performed via `__root` wrapper on a live rooted Passport:

```sh
# boot0 / boot1 full
dd if=/dev/emmc/boot0 of=/tmp/bb0_full.bin bs=512 count=8192
dd if=/dev/emmc/boot1 of=/tmp/bb1_full.bin bs=512 count=8192

# os0 first 8 MiB
dd if=/dev/emmc/os0 of=/tmp/os0_8M.bin bs=1048576 count=8

# heads
dd if=/dev/emmc/boot0 of=/tmp/bb0_head.bin bs=512 count=128
dd if=/dev/emmc/boot1 of=/tmp/bb1_head.bin bs=512 count=128
dd if=/dev/emmc/os0   of=/tmp/os0_head.bin   bs=512 count=128
dd if=/dev/emmc/user0 of=/tmp/u0_sb.bin     bs=262144 count=2
dd if=/dev/emmc/os0   of=/tmp/o0_meta.bin   bs=262144 count=2
```

Files pulled via SFTP (`/tmp/opencode/sftp.py`).

## Key Findings from These Dumps

- **`boot0` = SBL1** (1 MiB), not a standard EFI/GPT partition table. The "EFI PART" signature is a minimal decoy; the real content is the SBL1 preloader with build-info format strings.
- **`boot1` is empty** — no ABOOT/LK present. On this unit, the SBL1 chain loads directly from boot0.
- **`os0` = QNX IFS** (boot loader + startup). The OS partition is rcfs-mounted at `/base`.
- **`user0` = root filesystem** (QNX6FS, mounted at `/`).
- **CID is live-read** — identical 16-byte CID on boot0/boot1/user0 (`00 91 b2 63 55 93 00 34 45 47 32 33 30 00 01 11`); no 16-byte CID cache in RAM.
- **EXT_CSD is NOT cached** — no 512-byte ext_csd copy found in any writable region (heap1/2, module data, anon spans). Live read via `DCMD_MMCSD_CARD_REGISTER` returns the current state.

## Related Notes

- `notes/session19-driver-gate-decode-and-passport-dumps.md` — full session log including driver gate 0xf182 decode, WP handler 0x108d0 decode, per-node ext model, CID live-read, ext_csd no-cache finding, and these dumps.

---

This is a **research aid**. These images are not intended to be flashed back.