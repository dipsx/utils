#!/usr/bin/env python3
"""Proxmox MCP Server — удалённое выполнение команд и управление Proxmox через MCP (SSE)."""

import asyncio
import os
import shlex
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

EXEC_MODE = os.getenv("EXEC_MODE", "local")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")

mcp = FastMCP(
    "Proxmox MCP Server",
    description="Удалённое выполнение команд и управление Proxmox VE",
)

# ---------------------------------------------------------------------------
# SSH helper
# ---------------------------------------------------------------------------

def _get_ssh_client():
    """Создаёт и возвращает SSH-клиент на основе env-переменных."""
    import paramiko

    host = os.environ["SSH_HOST"]
    port = int(os.getenv("SSH_PORT", "22"))
    user = os.getenv("SSH_USER", "root")
    key_path = os.getenv("SSH_KEY_PATH")
    password = os.getenv("SSH_PASSWORD")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {"hostname": host, "port": port, "username": user}
    if key_path:
        connect_kwargs["key_filename"] = str(Path(key_path).expanduser())
    elif password:
        connect_kwargs["password"] = password

    client.connect(**connect_kwargs)
    return client


def _exec_ssh(command: str, timeout: int = 30) -> dict:
    """Выполняет команду через SSH."""
    client = _get_ssh_client()
    try:
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return {
            "stdout": stdout.read().decode(errors="replace"),
            "stderr": stderr.read().decode(errors="replace"),
            "exit_code": exit_code,
        }
    finally:
        client.close()


def _exec_local(command: str, timeout: int = 30) -> dict:
    """Выполняет команду локально."""
    result = subprocess.run(
        command, shell=True, capture_output=True, timeout=timeout, text=True
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def exec_command(command: str, timeout: int = 30) -> dict:
    """Выполнить shell-команду на Proxmox-сервере.

    Args:
        command: Shell-команда для выполнения
        timeout: Таймаут в секундах (по умолчанию 30)

    Returns:
        dict с полями stdout, stderr, exit_code
    """
    if EXEC_MODE == "ssh":
        return _exec_ssh(command, timeout=timeout)
    return _exec_local(command, timeout=timeout)


@mcp.tool()
def list_vms() -> dict:
    """Получить список всех VM и контейнеров на Proxmox (через qm/pct)."""
    qm = exec_command("qm list 2>/dev/null || true")
    pct = exec_command("pct list 2>/dev/null || true")
    return {"qemu_vms": qm["stdout"], "lxc_containers": pct["stdout"]}


@mcp.tool()
def vm_status(vmid: str) -> dict:
    """Получить статус VM или контейнера по VMID.

    Args:
        vmid: ID виртуальной машины или контейнера
    """
    qm = exec_command(f"qm status {shlex.quote(vmid)} 2>/dev/null")
    if qm["exit_code"] == 0:
        config = exec_command(f"qm config {shlex.quote(vmid)}")
        return {"type": "qemu", "status": qm["stdout"].strip(), "config": config["stdout"]}

    pct = exec_command(f"pct status {shlex.quote(vmid)} 2>/dev/null")
    if pct["exit_code"] == 0:
        config = exec_command(f"pct config {shlex.quote(vmid)}")
        return {"type": "lxc", "status": pct["stdout"].strip(), "config": config["stdout"]}

    return {"error": f"VM/CT {vmid} not found"}


@mcp.tool()
def vm_action(vmid: str, action: str) -> dict:
    """Выполнить действие с VM/контейнером: start, stop, restart, shutdown.

    Args:
        vmid: ID виртуальной машины или контейнера
        action: Действие (start, stop, restart, shutdown)
    """
    allowed = {"start", "stop", "restart", "shutdown"}
    if action not in allowed:
        return {"error": f"Action must be one of: {', '.join(allowed)}"}

    safe_vmid = shlex.quote(vmid)

    # Определяем тип (qemu или lxc)
    qm_check = exec_command(f"qm status {safe_vmid} 2>/dev/null")
    if qm_check["exit_code"] == 0:
        cmd = f"qm {action} {safe_vmid}"
    else:
        cmd = f"pct {action} {safe_vmid}"

    return exec_command(cmd, timeout=60)


@mcp.tool()
def node_status() -> dict:
    """Получить статус ноды Proxmox (CPU, RAM, диск, uptime)."""
    commands = {
        "hostname": "hostname",
        "uptime": "uptime",
        "cpu": "nproc",
        "memory": "free -h",
        "disk": "df -h /",
        "pve_version": "pveversion 2>/dev/null || echo 'N/A'",
    }
    result = {}
    for key, cmd in commands.items():
        out = exec_command(cmd)
        result[key] = out["stdout"].strip()
    return result


@mcp.tool()
def read_file(path: str) -> dict:
    """Прочитать содержимое файла на Proxmox-сервере.

    Args:
        path: Абсолютный путь к файлу
    """
    return exec_command(f"cat {shlex.quote(path)}")


@mcp.tool()
def write_file(path: str, content: str) -> dict:
    """Записать содержимое в файл на Proxmox-сервере.

    Args:
        path: Абсолютный путь к файлу
        content: Содержимое для записи
    """
    safe_path = shlex.quote(path)
    safe_content = shlex.quote(content)
    return exec_command(f"printf %s {safe_content} > {safe_path}")


@mcp.tool()
def service_action(service: str, action: str) -> dict:
    """Управление systemd-сервисами на Proxmox.

    Args:
        service: Имя сервиса
        action: Действие (status, start, stop, restart, enable, disable)
    """
    allowed = {"status", "start", "stop", "restart", "enable", "disable"}
    if action not in allowed:
        return {"error": f"Action must be one of: {', '.join(allowed)}"}

    return exec_command(f"systemctl {shlex.quote(action)} {shlex.quote(service)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8090"))

    print(f"Starting Proxmox MCP Server on {host}:{port} (mode: {EXEC_MODE})")
    mcp.run(transport="sse")
