<div align="center">

<img src="https://raw.githubusercontent.com/admonstrator/glinet-firmware-overview/main/images/robbenlogo-glinet-small.webp" width="300" alt="GL.iNet Firmware Overview Logo" style="border-radius: 10px; margin: 20px 0;">

## GL.iNet Firmware Overview

**Automated dashboard and flat-file API for GL.iNet firmware tracking!**

[![Stars](https://img.shields.io/github/stars/admonstrator/glinet-firmware-overview?style=for-the-badge)](https://github.com/admonstrator/glinet-firmware-overview/stargazers)
[![License](https://img.shields.io/github/license/admonstrator/glinet-firmware-overview?style=for-the-badge)](LICENSE)
[![Dashboard](https://img.shields.io/badge/Live-Dashboard-blue?style=for-the-badge&logo=google-chrome)](https://admonstrator.github.io/glinet-firmware-overview/)

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
- 🔍 **Link Validation** – Automatically verifies that firmware download links are active
- 📁 **Flat-File API** – Simple, machine-readable directory structure for easy integration
- 📊 **Categorized Dashboard** – Clean UI grouped by device type with search functionality
- ⚡ **Last Updated Badges** – Track exactly when the data was last verified

---

## 🎛️ API Usage

This project serves as a machine-readable API. You can access version information directly:

| Endpoint | Description |
|----------|-------------|
| `/api/all.json` | Consolidated JSON of all tracked models and versions |
| `/api/<model>/branches` | Text file listing available firmware stages for a model |
| `/api/<model>/<stage>/version` | Returns only the version string (e.g., `4.5.0`) |
| `/api/<model>/<stage>/url` | Returns the direct download URL for the firmware |
| `/api/<model>/<stage>/date` | Returns the release date |
| `/api/<model>/<stage>/hash` | Returns the MD5 hash (if available) |
| `/api/<model>/<stage>/changelog` | Returns the latest changelog as plain text (TXT) |

`/api/all.json` includes `changelog` as path reference (e.g. `/api/ax1800/release/changelog`) instead of inline changelog content.

**Example:**
`curl -s https://glinet-firmware.admon.me/api/ax1800/release/version`

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

<div align="center">

_Last updated: 2026-07-03_

</div>
