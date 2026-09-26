<div align="center">

<img src="https://raw.githubusercontent.com/admonstrator/glinet-firmware-overview/main/images/robbenlogo-glinet-small.webp" width="300" alt="GL.iNet Firmware Overview Logo" style="border-radius: 10px; margin: 20px 0;">

## GL.iNet Firmware Overview

**Automated dashboard and flat-file API for GL.iNet firmware tracking!**

[![Stars](https://img.shields.io/github/stars/admonstrator/glinet-firmware-overview?style=for-the-badge)](https://github.com/admonstrator/glinet-firmware-overview/stargazers)
[![License](https://img.shields.io/github/license/admonstrator/glinet-firmware-overview?style=for-the-badge)](LICENSE)
[![Dashboard](https://img.shields.io/badge/Live-Dashboard-blue?style=for-the-badge&logo=google-chrome)](https://firmware.gl-i.net/)

---

## 💖 Support the Project

If you find this tool helpful, consider supporting its development:

[![GitHub Sponsors](https://img.shields.io/badge/GitHub-Sponsors-EA4AAA?style=for-the-badge&logo=github)](https://github.com/sponsors/admonstrator) [![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/admon) [![Ko-fi](https://img.shields.io/badge/Ko--fi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/admon) [![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/aaronviehl)

</div>

---

## 📖 About

This project is an automated dashboard and flat-file API provider for GL.iNet firmware versions. It tracks the latest firmware releases (RELEASE, BETA, SNAPSHOT, TESTING, etc.) for all GL.iNet router, IOT, and KVM models.

Created by [Admon](https://forum.gl-inet.com/u/admon/) for the GL.iNet community.

> 🎖️ **Community Maintained** – Part of the [GL.iNet Toolbox](https://github.com/Admonstrator/glinet-toolbox) project  
> ⚠️ **Independent Project** – Not officially affiliated with GL.iNet or Tailscale

---

## ✨ Features

- 🚀 **Automated Tracking** – Daily updates for all GL.iNet models (Routers, IoT, KVM)
- 🔍 **Link Validation** – Every download link is verified with a `HEAD` request, retried on temporary failures. An unreachable link never changes which version is listed; it is flagged instead, and the newest older build that still downloads is offered as a second link
- 🩺 **Status Page** – [`/status.html`](https://firmware.gl-i.net/status.html) lists every download that could not be reached, with the reason, the number of attempts and the latest reachable build
- 📁 **Flat-File API** – Simple, machine-readable directory structure for easy integration
- 🪶 **Works Without JavaScript** – The official firmware page needs JavaScript; this one is plain HTML with no external assets, about 15 KB compressed, readable on slow connections and with scripts blocked
- 📊 **Categorized Dashboard** – One table per device type, filter by type without JavaScript, search as a small progressive enhancement, dark mode
- 🔗 **Device Deep Links** – Every model has its own page at `/<model>/` that can be linked directly
- 🆕 **Recently Released** – Builds from the last 14 days at the top of the dashboard and as text at `/new`
- 🕰️ **Last Update per Device** – How long ago each device got its newest build
- 📰 **Atom Feeds** – [`/feed.xml`](https://firmware.gl-i.net/feed.xml) for all devices, `/<model>/feed.xml` for one device
- 📖 **API & Terminal Docs** – [`/docs/`](https://firmware.gl-i.net/docs/) explains the menu, the text pages, the flat-file API and the feeds

---

## 🎛️ API Usage

This project serves as a machine-readable API. You can access version information directly:

| Endpoint | Description |
|----------|-------------|
| `/api/all.json` | Consolidated JSON of all tracked models and versions |
| `/api/status.json` | Build report: unreachable downloads with reason and attempt count, models the API returned no data for |
| `/api/<model>/branches` | Text file listing available firmware stages for a model |
| `/api/models` | Tab-separated: model code, type, name, release version |
| `/api/<model>/stages` | Tab-separated: stage, version, date, download URL, MD5, link state, fallback version, fallback URL |
| `/api/<model>/<stage>/version` | Returns only the version string (e.g., `4.5.0`) |
| `/api/<model>/<stage>/url` | Returns the direct download URL for the firmware |
| `/api/<model>/<stage>/date` | Returns the release date |
| `/api/<model>/<stage>/hash` | Returns the MD5 hash (if available) |
| `/api/<model>/<stage>/changelog` | Returns the latest changelog as plain text (TXT) |

`/api/all.json` includes `changelog` as path reference (e.g. `/api/ax1800/release/changelog`) instead of inline changelog content. Each entry also carries `link_ok`, which is `false` when the download link did not respond during the last build; the per-stage summary at `/api/<model>/<stage>/` shows the same as a `link:` line. When a link is down and an older build still downloads, the entry gains `latest_reachable` (`version`, `release_time`, `download`) and the summary a matching `latest_reachable:` line. The reported `version` is always the newest one GL.iNet publishes, whether or not its download responds.

**Example:**
`curl -s https://firmware.gl-i.net/api/ax1800/release/version`


### 🖥️ Plain text in the terminal

`curl` gets plain text instead of HTML: Cloudflare rewrites requests from `curl`, `wget`, HTTPie or any client sending `Accept: text/plain` to the text twin of each page (`/index.txt`, `/<model>/index.txt`, ...), which can also be fetched directly. The pages form a small menu, each one ends with the commands for the next step:

```
curl https://firmware.gl-i.net/                  menu
curl https://firmware.gl-i.net/routers           one category (also: iot, kvm, all)
curl https://firmware.gl-i.net/new               builds from the last 14 days
curl https://firmware.gl-i.net/mt3000            one device
curl https://firmware.gl-i.net/mt3000/release    one build with its changelog
```

There is also an interactive menu that runs on anything with a POSIX shell, including BusyBox on the router itself:

```
curl -s https://firmware.gl-i.net/cli | sh       # or:  wget -qO- https://firmware.gl-i.net/cli | sh
```

It browses categories and devices, searches by name, shows changelogs and downloads a build into the current directory (with MD5 check where GL.iNet publishes one). The script is [`cli.sh`](cli.sh) in this repository. Scripts that want to avoid JSON can use the tab-separated index files `/api/models` and `/api/<model>/stages`.

The full reference is on the site at [`/docs/`](https://firmware.gl-i.net/docs/) (also as text: `curl https://firmware.gl-i.net/docs`). The Cloudflare setup is described in [`cloudflare/README.md`](cloudflare/README.md).

### 📰 Feeds

- `https://firmware.gl-i.net/feed.xml`: the newest 50 builds across all devices, without snapshots
- `https://firmware.gl-i.net/<model>/feed.xml`: every stage of one device, e.g. [`/mt3000/feed.xml`](https://firmware.gl-i.net/mt3000/feed.xml)

---

## 🔗 Device Pages

Every tracked model has its own small page that can be linked directly, e.g. in forum posts:

`https://firmware.gl-i.net/<model>/`

**Example:** [https://firmware.gl-i.net/mt3000/](https://firmware.gl-i.net/mt3000/)

Each page lists all verified firmware stages of the model with version, release date, download link and changelog, when the device was last updated, its feed and the terminal commands for that model. The model names in the dashboard link to these pages as well.

---

## 🧪 Development

The generator is `generate_page.py`; the page renderers live in `sitelib/`. Tests need only Python:

```
python3 -m unittest discover -s tests              # unit tests plus an offline build of the whole site
python3 tests/build_offline.py --out /tmp/site     # render the fixture site to look at it
python3 tests/check_site.py /tmp/site --no-external-assets
```

---

## 💡 Getting Help

Need assistance or have questions?

- 💬 [Join the discussion on GL.iNet Forum](https://forum.gl-inet.com/) – Community support

---

## ⚠️ Disclaimer

This project is provided **as-is** without any warranty. Use it at your own risk.
It is an independent community project and is not affiliated with GL.iNet.

---

<div align="center">

## 🧰 Part of the GL.iNet Toolbox

This project is part of a comprehensive collection of tools for GL.iNet routers.

**Explore more tools and utilities:**

[![GL.iNet Toolbox](https://img.shields.io/badge/🧰_GL.iNet_Toolbox-Explore_All_Tools-blue?style=for-the-badge)](https://github.com/admonstrator/glinet-toolbox)

*Discover AdGuard Home Updater, Tailscale Updater, and more community-driven projects!*

</div>

---

<div align="center">

**Made with ❤️ by [Admon](https://github.com/admonstrator) for the GL.iNet Community**

⭐ If you find this useful, please star the repository!

</div>
