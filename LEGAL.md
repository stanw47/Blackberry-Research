# Legal Notice

## Scope

This repository documents **independent security research** on hardware the
author legally owns. It is published for **educational and defensive security
research purposes only**.

## No permission implied

Publication of these materials does **not** grant permission to:

- Unlock, modify, or circumvent the technical protection measures on devices you
  do not own.
- Redistribute, re-host, or resell any third-party proprietary firmware included
  here for reference.
- Use any technique described here against devices or systems you are not
  authorized to test.

## Third-party proprietary material

Certain artifacts referenced by the research notes are **proprietary firmware or
binaries** owned by BlackBerry Limited, Qualcomm Incorporated, or their
respective rights holders:

- Bootloader / secure-world images (`sbl1.mbn`, `tz.mbn`, `emmc_appsboot.mbn`,
  `rpm.mbn`, `hyp.mbn`, `NON-HLOS.bin`, etc.)
- TrustZone trustlets (e.g. Widevine) and the token-service shared objects
- Full system/autoloader images

These are **copyrighted works**. They are referenced here only where strictly
necessary to document the research findings, and only for purposes of
interoperability and security analysis. All rights remain with their respective
owners. Where the author did not clearly have redistribution rights, only the
*smallest* such artifact necessary to reproduce a finding is included, and never
full operating-system images.

If you are a rights holder and believe any material here should be removed,
please open an issue or contact the repository owner and it will be removed
promptly.

## Fair use / research

Analysis notes, disassembly extracts, and original scripts are the author's own
work produced during the research and are believed to fall within customary
defensive-research / fair-use norms. Quoted strings and small excerpts from
binaries are used for identification and commentary only.

## Trademarks

All product names, logos, and brands are property of their respective owners.
Use of these names is for identification only and does not imply endorsement.
