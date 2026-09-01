# Bootloader images

These are **prototype / research bootloader images** produced by the open-source
`imggen` toolchain (`tools/imggen/`), used in the bootloader-unlock research.
They are the *output* of the research, not stock BlackBerry factory firmware.

- `bbss.mbn` — prototype secondary bootloader (SBL). Contains the
  "insecure device; ignoring SBL auth failure!" string documented in the notes.
- `aboot.mbn`, `sbl1.mbn`, `sbl1r.mbn`, `stage1/2/3.mbn`, `rpm.mbn`, `tz.mbn`,
  `sdi.mbn` — generated boot-chain images from the imggen build.
- `boot_gpt_secure.bin` / `boot_gpt_insecure.bin` — GPT layouts for secure vs
  insecure (`bbss.insecure`) state.
- `*.img` — small partition templates (`blog`, `boardid`, `nvuser`, `perm`,
  `prdid`) emitted by the build.
- `user_gpt.bin` — user-area GPT.

These reference Qualcomm/BlackBerry boot-chain *structure* and are provided only
as research artifacts under the terms in [../LEGAL.md](../LEGAL.md). They are
**not intended to be flashed**; doing so can brick a device (see
[../SECURITY.md](../SECURITY.md)).

## Not included

- Stock BlackBerry autoloader firmware and full system images are **not**
  re-hosted here (copyright + multi-GB size; see [../LEGAL.md](../LEGAL.md)).
- Device-specific eMMC dumps (`boot0.img`, `nvram0.img`, etc.) are **not**
  included because they contain personally identifying device keys/serials.
