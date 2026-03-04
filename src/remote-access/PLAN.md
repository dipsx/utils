# Remote Access Setup — Fedora 43 GNOME RDP

## Stack

| Component | Tool |
|---|---|
| Protocol | RDP (built-in `gnome-remote-desktop`) |
| Display server | Wayland (native support) |
| Config CLI | `grdctl` |
| VPN layer | Tailscale (recommended) |
| Client | Remmina (Linux) / mstsc (Windows) / Microsoft Remote Desktop (macOS) |

---

## Modes

### Mode A — Desktop Sharing (attach to existing session)
- Connects to an **already running** GNOME session
- Useful when someone is logged in at the machine
- Configure via: Settings → System → Remote Desktop → Desktop Sharing

### Mode B — Remote Login / Headless (recommended)
- Creates a **new session** without physical login
- Truly unattended, works headless
- Supported since GNOME 46 (Fedora 41+), F43 ships GNOME 47 ✅
- Configure via: `grdctl --system` or Settings → Remote Login

---

## Setup

```bash
./setup-gnome-rdp.sh
```

The script will:
1. Install `gnome-remote-desktop`
2. Generate self-signed TLS certificate
3. Configure credentials via `grdctl`
4. Enable and start the systemd service
5. Open firewall port 3389

---

## Network

### LAN
Connect directly to the machine's local IP on port `3389`.

### WAN / Internet (recommended: Tailscale)
```bash
# On the Fedora 43 host
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Then connect via Tailscale IP — no port forwarding needed
```

---

## Client Connection

| OS | Client | Notes |
|---|---|---|
| Linux | Remmina | Select RDP, enter IP:3389 |
| Windows | `mstsc` (built-in) | Run → mstsc → enter IP |
| macOS | Microsoft Remote Desktop | Free on App Store |
| Browser | Apache Guacamole | Self-hosted, HTML5 |

---

## Ports

| Port | Protocol | Purpose |
|---|---|---|
| 3389 | TCP | RDP |
