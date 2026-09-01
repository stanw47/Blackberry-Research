# Device eMMC dumps (Classic)

Raw dumps of the Classic's eMMC boot/secure partitions, captured via the
documented research access path.

> ⚠️ **PRIVACY / IDENTIFICATION WARNING**
>
> These images are **unique to a specific physical device**. They contain that
> device's hardware identity (`processor_id`, `usbloader_id`, `hwid`), secure
> boot state, and partition map material. Publishing them:
>
> - allows a third party to **fingerprint/identify your specific handset**;
> - exposes the exact offset of your device's `bbss.insecure` flag
>   (`boot0` offset `0x35a98`, per `parse_buildinfo.py`);
> - may leak secure-world state that is nominally device-unique.
>
> They are included **only** because the research notes reference their layout.
> If you cloned this and the dumps are yours, treat them as sensitive.

## Files

- `boot0.img` — primary boot partition (4 MiB). `bbss.insecure` at `0x35a98`.
- `boot1.img` — secondary boot partition (4 MiB).
- `nvram0.img` — NV/calibration region (contains the build-info record).
- `dmi0.img` — device-management interface partition.
- `parse_buildinfo.py` — decoder for the `RIM BlackBerry Device` build-info
  record (pulls `secure`, `hwid`, `processor_id`, `usbloader_id`, offsets).

## Usage

```
python3 parse_buildinfo.py   # run in this directory
```

This is a **research aid**. These images are not intended to be flashed back.
