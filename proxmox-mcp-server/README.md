# Proxmox MCP Server

MCP-сервер для удалённого управления Proxmox VE из Claude Code.

## Возможности

- `exec_command` — выполнить произвольную shell-команду
- `list_vms` — список VM и LXC-контейнеров
- `vm_status` — статус и конфигурация VM/CT
- `vm_action` — start/stop/restart/shutdown VM/CT
- `node_status` — информация о ноде (CPU, RAM, диск)
- `read_file` / `write_file` — чтение/запись файлов
- `service_action` — управление systemd-сервисами

## Быстрый старт

### 1. Установка

```bash
cd proxmox-mcp-server
pip install -r requirements.txt
cp .env.example .env
```

### 2. Настройка .env

**Если сервер запущен прямо на Proxmox:**
```
EXEC_MODE=local
```

**Если сервер запущен на другой машине в сети:**
```
EXEC_MODE=ssh
SSH_HOST=192.168.1.100
SSH_USER=root
SSH_KEY_PATH=~/.ssh/id_rsa
```

### 3. Запуск

```bash
python server.py
```

Или через Docker:
```bash
docker compose up -d
```

### 4. Подключение к Claude Code

В `~/.claude/settings.json` (или в настройках проекта `.claude/settings.json`):

```json
{
  "mcpServers": {
    "proxmox": {
      "type": "sse",
      "url": "http://<your-tailscale-ip>:8090/sse"
    }
  }
}
```

## Доступ через Tailscale Funnel

```bash
tailscale funnel 8090
```

Тогда URL для Claude Code будет:
```
https://<your-machine>.ts.net/sse
```

## Безопасность

- Сервер даёт полный доступ к shell — запускайте только в доверенной сети
- Используйте `AUTH_TOKEN` в .env для базовой защиты
- Tailscale Funnel обеспечивает шифрование и аутентификацию на уровне сети
