# BlackBerry <DEVICE> (<MODEL>) — Research

> <ONE-LINE DESCRIPTION>
>
> Part of the **[Blackberry-Research](https://github.com/stanw47/Blackberry-Research)**
> collection. See the hub for cross-device mechanisms and the shared
> [devmap standard](https://github.com/stanw47/Blackberry-Research/blob/main/devmap/STANDARD.md).

---

## Disclaimer

> **Research aid, not a flashing guide.** Modifying bootloaders, eMMC boot
> partitions (`boot0`/`boot1`), or firmware can **permanently brick** a device
> with no recovery short of JTAG/ISP chip-out. Everything here is for
> educational / defensive research on devices the author owns. Proceed at your
> own risk.

---

## Status

| Field | Value |
|---|---|
| Device / model | BlackBerry <DEVICE> (<MODEL>) |
| SoC | <SoC> |
| OS / build | <OS / build> |
| Bootloader | <locked / unlocked / prototype> |
| Root | <none / uid-0 / partial> |
| Access levels | <L0..L5 reached> |
| Status | <one-line: what works, what's blocked> |

**Current state:** <2–3 sentences>.

---

## TL;DR

- <key finding 1>
- <key finding 2>
- <key finding 3>

---

## Key findings

*Numbered, stable — never renumber; append new findings. Each links to detail.*

1. **<title>** — <one line>. → [`notes/NN-slug.md`](notes/NN-slug.md)
2. **<title>** — <one line>. → [`docs/<doc>.md`](docs/<doc>.md)

---

## How to connect

<The access ritual for this device: transport, auth, tooling. Link the hub
toolchain where shared.>

---

## Repository layout

| Path | Contents |
|---|---|
| `notes/` | chronological session notes |
| `docs/` | polished write-ups & guides |
| `devmaps/` | device maps (schema v1.0) |
| `recon/` | raw captures (props, partitions, logs) |
| `tools/` | device-specific scripts |
| `firmware/` | **not committed** — see `firmware/FETCH.md` |

---

## Related repos

- **Hub:** [Blackberry-Research](https://github.com/stanw47/Blackberry-Research)
- <sibling device repos>

---

## References

| Source | URL | Relevance |
|---|---|---|
| <name> | <url> | <why> |

---

## License

Research notes and original scripts are provided for educational purposes;
third-party code retains its own license.
