import base64
import json
import os
import sys
import uuid
from urllib.parse import parse_qs, unquote

import requests

# Источник подписки (vless:// ссылки). Не должен совпадать с файлом назначения.
SUB_URL = "https://github.com/PizdukMod/PizdukVPN/raw/refs/heads/main/wl"

REPO = "PizdukMod/PizdukVPN"
BRANCH = "main"
FILE_PATH = 'wl.auto'

GITHUB_API = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

REMARKS = '🏳PizdukVPN🤍Авто🐇Выбор❄️'

PROBE_URL = "https://www.gstatic.com/generate_204"
PROBE_INTERVAL = "1m"

HEADER = '#profile-title: PizdukVPN Автовыбор🤍\n#profile-update-interval: 6\n#announce: base64: 8J+YjtCi0LXQu9C10LPRgNCw0Lwg0LrQsNC90LDQuzogQFBpek1vZPCfmI4K4oC877iP0JXRgdC70Lgg0L3QtSDQv9C+0YDRgtC40YDRg9C10YLRgdGPINC60L7QvdGE0LjQsyDQuNGB0L/QvtC70YzQt9GD0LnRgtC1INCQ0JvQrNCi0JXQoNCd0JDQotCY0JLQndCj0K4g0YHRgdGL0LvQutGDIOKAvO+4jw==\n#profile-web-page-url: https://t.me/PizMod\n#support-url: https://t.me/Harachok\n'

# Токен: в workflow env: GH_TOKEN: ${{ secrets.PIZDUK_PAT }}
GH_TOKEN = os.environ.get("GH_TOKEN", "").strip()


def fetch_subscription():
    r = requests.get(SUB_URL, timeout=20)
    r.raise_for_status()
    raw = r.text.strip()

    try:
        decoded = base64.b64decode(
            raw + "=" * (-len(raw) % 4)
        ).decode("utf-8")
    except Exception:
        decoded = raw

    return [
        line.strip()
        for line in decoded.splitlines()
        if line.strip().startswith("vless://")
    ]


def slugify_tag(name, used):
    base = name.replace(" ", "_") or "node"
    tag = base
    i = 1
    while tag in used:
        i += 1
        tag = base + "_" + str(i)
    used.add(tag)
    return tag


def parse_vless(link, used_tags):
    try:
        body = link[len("vless://"):]
        left, _, frag = body.partition("#")
        userinfo, _, hostpart = left.partition("@")
        userinfo = unquote(userinfo)

        try:
            uuid.UUID(userinfo)
        except ValueError:
            print("skip invalid uuid: " + frag, file=sys.stderr)
            return None

        hostname, _, query = hostpart.partition("?")
        host, _, port_raw = hostname.rpartition(":")
        host = host.strip("[]")  # IPv6
        port = int(port_raw.split("/", 1)[0].strip())

        params = parse_qs(query)  # значения уже декодированы
        name = unquote(frag) if frag else host

        def q(key, default=""):
            return params.get(key, [default])[0]

        user = {"id": userinfo, "encryption": q("encryption", "none")}
        flow = q("flow")
        if flow:
            user["flow"] = flow

        network = q("type", "tcp")
        if network == "raw":
            network = "tcp"
        security = q("security", "none")

        outbound = {
            "tag": slugify_tag(name, used_tags),
            "protocol": "vless",
            "settings": {
                "vnext": [{"address": host, "port": port, "users": [user]}]
            },
            "streamSettings": {"network": network, "security": security},
        }
        ss = outbound["streamSettings"]

        if security == "reality":
            ss["realitySettings"] = {
                "serverName": q("sni"),
                "fingerprint": q("fp", "chrome"),
                "publicKey": q("pbk"),
                "shortId": q("sid"),
                "spiderX": q("spx", ""),
            }
        elif security == "tls":
            tls = {
                "serverName": q("sni"),
                "fingerprint": q("fp", "chrome"),
            }
            alpn_raw = q("alpn")
            if alpn_raw:
                tls["alpn"] = alpn_raw.split(",")
            ss["tlsSettings"] = tls

        if network == "grpc":
            ss["grpcSettings"] = {
                "serviceName": q("serviceName", q("path", ""))
            }
        elif network == "ws":
            host_header = q("host", "")
            ss["wsSettings"] = {
                "path": q("path", "/"),
                "headers": {"Host": host_header} if host_header else {},
            }
        elif network in ("xhttp", "splithttp"):
            xs = {"path": q("path", "/")}
            if q("host"):
                xs["host"] = q("host")
            if q("mode"):
                xs["mode"] = q("mode")
            ss["xhttpSettings"] = xs

        return outbound

    except Exception as e:
        print(
            "skip broken link: " + link[:60] + "... (" + str(e) + ")",
            file=sys.stderr,
        )
        return None


def build_config(outbounds):
    all_tags = [o["tag"] for o in outbounds]

    # Серверы "только для Телеграма" не берём в автовыбор.
    tags = [t for t in all_tags if "telegram-only" not in t] or all_tags

    return {
        "remarks": REMARKS,
        "log": {"loglevel": "warning"},
        "dns": {"servers": ["1.1.1.1", "8.8.8.8"]},
        "observatory": {
            "subjectSelector": tags,
            "probeUrl": PROBE_URL,
            "probeInterval": PROBE_INTERVAL,
            "enableConcurrency": True,
        },
        "inbounds": [
            {
                "tag": "socks-in",
                "port": 10808,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True},
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"],
                },
            },
            {
                "tag": "http-in",
                "port": 10809,
                "listen": "127.0.0.1",
                "protocol": "http",
                "settings": {},
            },
        ],
        "outbounds": outbounds + [
            {"tag": "direct", "protocol": "freedom", "settings": {}},
            {"tag": "block", "protocol": "blackhole", "settings": {}},
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "balancers": [
                {
                    "tag": "all-servers",
                    "selector": tags,
                    "strategy": {"type": "leastPing"},
                    "fallbackTag": tags[0],
                }
            ],
            "rules": [
                {
                    "type": "field",
                    "ip": ["geoip:private"],
                    "outboundTag": "direct",
                },
                {
                    "type": "field",
                    "network": "tcp,udp",
                    "balancerTag": "all-servers",
                },
            ],
        },
    }


def push_to_repo(content):
    headers = {
        "Authorization": "Bearer " + GH_TOKEN,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    sha = None
    current = None
    r = requests.get(
        GITHUB_API, headers=headers, params={"ref": BRANCH}, timeout=30
    )
    if r.status_code == 200:
        data = r.json()
        sha = data.get("sha")
        try:
            current = base64.b64decode(data.get("content", "")).decode("utf-8")
        except Exception:
            current = None
    elif r.status_code != 404:
        print("GitHub GET:", r.status_code, r.text, file=sys.stderr)
        r.raise_for_status()

    if current == content:
        print(f"[=] {FILE_PATH}: без изменений, коммит пропущен")
        return

    payload = {
        "message": f"Update {FILE_PATH}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    response = requests.put(
        GITHUB_API, headers=headers, json=payload, timeout=30
    )
    if not response.ok:
        print(
            "GitHub PUT:", response.status_code, response.text,
            file=sys.stderr,
        )
    response.raise_for_status()
    print(f"[+] GitHub: updated {FILE_PATH}")


def main():
    if not GH_TOKEN:
        print(
            "GH_TOKEN is not set (pass secrets.PIZDUK_PAT via env in workflow)",
            file=sys.stderr,
        )
        sys.exit(1)

    if SUB_URL.rstrip("/").endswith("/" + FILE_PATH):
        print(
            "WARNING: источник подписки совпадает с файлом назначения "
            f"({FILE_PATH}) - скрипт читает свой же вывод",
            file=sys.stderr,
        )

    links = fetch_subscription()
    print(f"[i] Получено VLESS-ссылок: {len(links)}")

    used_tags = set()
    outbounds = []
    for link in links:
        outbound = parse_vless(link, used_tags)
        if outbound:
            outbounds.append(outbound)

    if not outbounds:
        print("no valid vless links parsed, aborting", file=sys.stderr)
        sys.exit(1)

    config = build_config(outbounds)
    file_content = HEADER + json.dumps([config], ensure_ascii=False, indent=2)

    push_to_repo(file_content)


if __name__ == "__main__":
    main()
