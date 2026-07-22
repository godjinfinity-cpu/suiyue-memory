from __future__ import annotations

import functools
import argparse
import ipaddress
import os
import socket
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
DEFAULT_PORT = 8000


def find_available_port(start_port: int = DEFAULT_PORT) -> int:
    port = start_port

    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
            except OSError:
                port += 1
                continue

            return port


def is_usable_private_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False

    return bool(address.version == 4 and address.is_private and not address.is_loopback and not address.is_link_local)


def get_windows_hardware_ips() -> list[str]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$items = Get-NetIPConfiguration | "
            "Where-Object { $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up' "
            "-and $_.NetAdapter.HardwareInterface -eq $true }; "
            "foreach ($item in $items) { foreach ($addr in $item.IPv4Address) { $addr.IPAddress } }"
        ),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            encoding="utf-8",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    return [
        line.strip()
        for line in completed.stdout.splitlines()
        if is_usable_private_ip(line.strip())
    ]


def get_ipconfig_ips() -> list[str]:
    try:
        completed = subprocess.run(
            ["ipconfig"],
            capture_output=True,
            check=False,
            encoding="mbcs",
            errors="ignore",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired, LookupError):
        return []

    blocks = re_split_adapters(completed.stdout)
    preferred: list[str] = []
    fallback: list[str] = []

    for heading, body in blocks:
        lower_heading = heading.lower()
        is_virtual = any(
            keyword in lower_heading
            for keyword in [
                "vethernet",
                "virtual",
                "vmware",
                "virtualbox",
                "loopback",
                "wsl",
                "docker",
                "bluetooth",
                "蓝牙",
            ]
        )
        is_preferred = any(
            keyword in lower_heading
            for keyword in ["wlan", "wi-fi", "wireless", "ethernet", "以太网", "无线局域网"]
        )

        ips = re_find_ips(body)
        if is_virtual:
            continue
        if is_preferred:
            preferred.extend(ips)
        else:
            fallback.extend(ips)

    return dedupe_ips(preferred or fallback)


def re_split_adapters(output: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.endswith(":") and not line.startswith(" ") and not line.startswith("\t"):
            if current_heading:
                blocks.append((current_heading, "\n".join(current_lines)))
            current_heading = stripped
            current_lines = []
        elif current_heading:
            current_lines.append(line)

    if current_heading:
        blocks.append((current_heading, "\n".join(current_lines)))

    return blocks


def re_find_ips(text: str) -> list[str]:
    import re

    values: list[str] = []

    for line in text.splitlines():
        if "ipv4" not in line.lower():
            continue
        values.extend(re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", line))

    return [value for value in values if is_usable_private_ip(value)]


def dedupe_ips(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def score_ip(value: str) -> int:
    if value.startswith("192.168."):
        return 0
    if value.startswith("10."):
        return 1
    if value.startswith("172."):
        return 2
    return 3


def get_lan_ip() -> str:
    ipconfig_ips = get_ipconfig_ips()
    if ipconfig_ips:
        return sorted(ipconfig_ips, key=score_ip)[0]

    hardware_ips = get_windows_hardware_ips()
    if hardware_ips:
        return sorted(hardware_ips, key=score_ip)[0]

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidate = sock.getsockname()[0]
            if is_usable_private_ip(candidate):
                return candidate
    except OSError:
        pass

    try:
        candidates = [
            info[4][0]
            for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            if is_usable_private_ip(info[4][0])
        ]
    except OSError:
        candidates = []

    if candidates:
        return sorted(set(candidates), key=score_ip)[0]

    return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="启动岁月留痕本地预览，并重建手机可扫二维码。")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="预览端口，默认 8000。")
    parser.add_argument("--host-ip", help="手动指定手机访问的电脑局域网 IP。")
    args = parser.parse_args()

    port = find_available_port(args.port)
    lan_ip = args.host_ip or get_lan_ip()
    computer_url = f"http://127.0.0.1:{port}"
    phone_url = f"http://{lan_ip}:{port}"

    os.environ["BASE_URL"] = phone_url

    from build import build_site

    build_site()

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(DOCS_DIR))

    with ThreadingHTTPServer(("0.0.0.0", port), handler) as server:
        print()
        print("岁月留痕本地预览已启动")
        print(f"电脑打开：{computer_url}")
        print(f"手机扫码/访问：{phone_url}")
        print()
        print("二维码已按“手机扫码/访问”地址重新生成。")
        print("手机和电脑需要连接同一个 Wi-Fi。")
        print("如果 Windows 防火墙弹窗，请允许 Python 访问专用网络。")
        print("请保持这个终端窗口打开。")
        print("需要关闭预览时，再回到这里按 Ctrl+C。")
        print()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n预览已关闭。")


if __name__ == "__main__":
    main()
