#!/usr/bin/env bash
# setup-gnome-rdp.sh
# Fedora 43 GNOME Remote Desktop (RDP) — headless/unattended setup
# Requires: Fedora 41+ (GNOME 46+), run as the target user with sudo access
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
RDP_USER="${RDP_USER:-${USER}}"
RDP_PASS="${RDP_PASS:-}"
CERT_DIR="${HOME}/.local/share/gnome-remote-desktop"
CERT_KEY="${CERT_DIR}/rdp-tls.key"
CERT_CRT="${CERT_DIR}/rdp-tls.crt"
# ─────────────────────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── Checks ────────────────────────────────────────────────────────────────────
[[ "${EUID}" -eq 0 ]] && error "Do not run as root. Run as your regular user."

if ! grep -q 'ID=fedora' /etc/os-release 2>/dev/null; then
    warn "This script is designed for Fedora. Proceeding anyway..."
fi

GNOME_VER=$(gnome-shell --version 2>/dev/null | grep -oP '\d+' | head -1 || echo "0")
if [[ "${GNOME_VER}" -lt 46 ]]; then
    error "GNOME ${GNOME_VER} detected. Headless RDP requires GNOME 46+ (Fedora 41+)."
fi
info "GNOME ${GNOME_VER} detected — headless RDP supported."

# ── Password ──────────────────────────────────────────────────────────────────
if [[ -z "${RDP_PASS}" ]]; then
    echo -n "Enter RDP password for user '${RDP_USER}': "
    read -rs RDP_PASS
    echo
    [[ -z "${RDP_PASS}" ]] && error "Password cannot be empty."
fi

# ── Install ───────────────────────────────────────────────────────────────────
info "Installing gnome-remote-desktop..."
sudo dnf install -y gnome-remote-desktop

# ── TLS Certificate ───────────────────────────────────────────────────────────
info "Generating self-signed TLS certificate..."
mkdir -p "${CERT_DIR}"
chmod 700 "${CERT_DIR}"

openssl req -newkey rsa:4096 -nodes \
    -keyout "${CERT_KEY}" \
    -x509 -days 3650 \
    -out "${CERT_CRT}" \
    -subj "/CN=gnome-remote-desktop/O=LocalRDP" \
    -addext "subjectAltName=IP:127.0.0.1" \
    2>/dev/null

chmod 600 "${CERT_KEY}" "${CERT_CRT}"
info "Certificate written to ${CERT_DIR}"

# ── Configure via grdctl ──────────────────────────────────────────────────────
info "Configuring gnome-remote-desktop..."

# User-session mode (Desktop Sharing — attach to running session)
grdctl rdp set-tls-key  "${CERT_KEY}"
grdctl rdp set-tls-cert "${CERT_CRT}"
grdctl rdp set-credentials "${RDP_USER}" "${RDP_PASS}"
grdctl rdp enable

# System-wide mode (Remote Login — headless, new session)
sudo grdctl --system rdp set-tls-key  "${CERT_KEY}"
sudo grdctl --system rdp set-tls-cert "${CERT_CRT}"
sudo grdctl --system rdp set-credentials "${RDP_USER}" "${RDP_PASS}"
sudo grdctl --system rdp enable

# ── Systemd service ───────────────────────────────────────────────────────────
info "Enabling gnome-remote-desktop systemd service..."

# User-session service
systemctl --user enable --now gnome-remote-desktop.service

# System-wide service (for headless/Remote Login)
sudo systemctl enable --now gnome-remote-desktop.service

# ── Firewall ──────────────────────────────────────────────────────────────────
info "Opening firewall port 3389/tcp..."
if command -v firewall-cmd &>/dev/null; then
    sudo firewall-cmd --permanent --add-port=3389/tcp
    sudo firewall-cmd --reload
else
    warn "firewall-cmd not found — skipping firewall rule. Open port 3389 manually."
fi

# ── SELinux ───────────────────────────────────────────────────────────────────
# Fedora 41+ ships an SELinux policy for gnome-remote-desktop — nothing to do.
info "SELinux: Fedora 43 ships gnome-remote-desktop policy — no manual steps needed."

# ── Done ──────────────────────────────────────────────────────────────────────
LOCAL_IP=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' || echo "<your-ip>")

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} GNOME RDP setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Host IP : ${LOCAL_IP}"
echo "  Port    : 3389"
echo "  User    : ${RDP_USER}"
echo ""
echo "  Connect:"
echo "    Linux  → remmina rdp://${LOCAL_IP}"
echo "    Windows→ mstsc /v:${LOCAL_IP}"
echo ""
echo "  For remote access over internet → use Tailscale:"
echo "    curl -fsSL https://tailscale.com/install.sh | sh"
echo "    sudo tailscale up"
echo ""
warn "TLS cert is self-signed — clients will show a cert warning on first connect. Accept it."
