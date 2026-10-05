# BlackBerry Research — Standards & Conventions (v1.0)

> One collection, many repos. This document defines the **single standard** every
> device repo and the central hub follow, so the work is consistent, readable to
> newcomers, and usable by researchers.

---

## 0. The collection model

```
Blackberry-Research            ← HUB: cross-device mechanisms, master index, shared tooling
├── Blackberry-<Device>-Research   ← one repo per device
├── Blackberry-<Device>-Research
└── ...
```

- The **hub** holds only things that apply to **2+ devices**: shared mechanisms,
  the device-map standard, shared toolchain, the master index, and status.
- Each **device repo** holds everything specific to that device.
- Repos are **private while in progress**, flipped **public** when a write-up is ready.
- Nothing is deleted to make this work: content is **copied** into its device repo,
  and the hub keeps history. (Git history in the old repo preserves everything.)

Naming: `Blackberry-<Device>-Research` (hyphens, exact device name). The hub is
`Blackberry-Research`.

---

## 1. Device repo layout (the standard)

```
Blackberry-<Device>-Research/
├── README.md          # the front door (structure in §2)
├── SUMMARY.md         # ~10-line machine-aggregatable summary (hub reads this)
├── notes/             # chronological session notes  (NN-slug.md, §4)
├── docs/              # polished write-ups & guides (no dates in names)
├── devmaps/           # device maps, schema v1.0 (hub's devmap standard)
├── recon/             # raw captures: props, partitions, logs, kallsyms, policy
├── tools/             # device-specific scripts (device_<verb>.py)
├── firmware/          # NOT committed — FETCH.md with URLs + SHA256 (see §5)
└── .gitignore
```

Optional when large: `exploit/`, `kernel/`, `abl/`, `edl/`, `specimens/`.

---

## 2. README structure (device repos — copy this skeleton)

Every device README follows the same section order so readers learn one layout:

```
# BlackBerry <Device> (<model>) — Research

> One-line description. Part of the [Blackberry-Research](<hub url>) collection.

## Disclaimer            ← safety warning (flashing can brick)
## Status                ← the one table everyone wants (see §3)
## TL;DR                 ← 3–6 bullet key findings, plain language
## Key findings          ← numbered, stable, each links to a note
## How to connect        ← the access ritual for this device
## Repository layout     ← what's in each folder
## Related repos         ← hub + sibling devices
## References            ← public sources (not re-hosted)
## License
```

Rules:
- **Status table first** after the disclaimer — readers scan it before anything.
- Key findings are **numbered and stable** (never renumber; append).
- Every claim links to a `notes/` or `docs/` file.
- No giant code blocks in the README; link out.

### §3 The standard Status table

```markdown
| Field | Value |
|---|---|
| Device / model | BlackBerry <name> (<model>) |
| SoC | e.g. MSM8960 / MSM8953 |
| OS / build | e.g. BB10 10.3.3.3216 / Android 7.1.1 ABL766 |
| Bootloader | locked / unlocked / prototype |
| Root | none / uid-0 / partial |
| Access levels | L0 usb, L1 fastboot, L2 adb, L3 root, L4 qnx, L5 edl |
| Status | one line: what works, what's blocked |
```

---

## 4. Notes standard

- Filename: `NN-slug.md` (zero-padded, e.g. `07-classic-real-root.md`).
- Every note starts with a fixed header block:

```markdown
# Session NN — Short Title

- **Date:** YYYY-MM-DD
- **Device:** <device> (<model>)
- **Access level:** L0..L5
- **Status:** finding | negative | map | in-progress

## TL;DR
One paragraph a newcomer can read.

## What we did
## Findings
## Artifacts      ← files produced, with paths
## Next
```

- **Negative results are first-class.** Record what *failed* and *why* — it saves
  the next researcher.
- Never edit old notes to "fix" history; add a new note.

---

## 5. Big binaries — never in git

GitHub rejects files > 100 MB and the repo bloats. Rules:

- Firmware/autoloaders/ISOs/dumps are **not committed**.
- Each device repo has `firmware/FETCH.md` with: filename, source URL,
  **SHA-256**, size, and where to place it.
- Reference binaries that are re-downloadable (e.g. AOSP `ref/`) are gitignored
  with a fetch note.
- Small, essential, license-clean artifacts (e.g. a patched `btool`, a device
  map) may be committed — keep each < 5 MB.

The hub `.gitignore` enforces the global patterns; device repos extend it.

---

## 6. Device maps (devmap)

- One JSON per device (or per access level), in `devmaps/`.
- Schema is defined in the hub: [`devmap/STANDARD.md`](../devmap/STANDARD.md).
- Access levels L0–L5: `usb → fastboot → adb → adb-root/root → qnx → edl`.
- Compare any two with the hub tool: `py toolchain/devmap.py diff a.json b.json`.

---

## 7. Shared toolchain

Anything used by 2+ devices lives in the **hub** under `toolchain/` and is
referenced (not copied) by device repos: `blackberry-connect`, the paramiko SSH
recipe, `edl`, `imggen`, `devmap.py`, autoloader extraction, fastboot-libusb.

---

## 8. Readability rules (for amateurs *and* researchers)

- Define a term the first time it's used; link the glossary.
- Lead with the **status**, then the **plain-language TL;DR**, then the detail.
- Use tables for facts, prose for reasoning.
- Every "blocked" statement says **why** and **what would unblock it**.
- Cross-link aggressively: hub ↔ device, note ↔ note, finding ↔ artifact.
- English, present tense, no hype.
