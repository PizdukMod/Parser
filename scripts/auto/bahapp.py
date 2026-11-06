import base64
import json
import os
import sys
import uuid
from urllib.parse import parse_qs, unquote

import requests

# URL исходной подписки задаётся через GitHub Actions Secret SUB_URL
SUB_URL = "https://Gist.github.com/PizdukMod/0270547cabecdd08527e2645f3b3672c/raw/3d6edd8c419cec45c61f8653ffa6150816981af9/sub",

GIST_ID = "40450c65ccdf39c6556cebf93c8353a5"
GIST_FILENAME = "BaHapp"
GIST_API = f"https://api.github.com/gists/{GIST_ID}"

REMARKS = "😍@PizMod🏴PizdukVPN👀Авто😎выбор"

PROBE_URL = "https://www.gstatic.com/generate_204"
PROBE_INTERVAL = "1m"

HEADER = ""

GH_TOKEN = os.environ["PIZDUK_PAT"]


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

    lines = [
        line.strip()
        for line in decoded.splitlines()
        if line.strip().startswith("vless://")
    ]

    return lines


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
        port = int(port_raw.split("/", 1)[0].strip())

        params = parse_qs(query)
        name = unquote(frag) if frag else host

        def q(key, default=""):
            return params.get(key, [default])[0]

        user = {
            "id": userinfo,
            "encryption": q("encryption", "none")
        }

        flow = q("flow")
        if flow:
            user["flow"] = flow

        outbound = {
            "tag": slugify_tag(name, used_tags),
            "protocol": "vless",
            "settings": {
                "vnext": [
                    {
                        "address": host,
                        "port": port,
                        "users": [user],
                    }
                ]
            },
            "streamSettings": {
                "network": q("type", "tcp"),
                "security": q("security", "none"),
            },
        }

        if outbound["streamSettings"]["network"] == "raw":
            outbound["streamSettings"]["network"] = "tcp"

        network = outbound["streamSettings"]["network"]
        security = outbound["streamSettings"]["security"]

        if security == "reality":
            outbound["streamSettings"]["realitySettings"] = {
                "serverName": q("sni"),
                "fingerprint": q("fp", "chrome"),
                "publicKey": q("pbk"),
                "shortId": q("sid"),
                "spiderX": unquote(q("spx", "")),
            }

        elif security == "tls":
            tls = {
                "serverName": q("sni"),
                "fingerprint": q("fp", "chrome"),
            }

            alpn_raw = q("alpn")
            if alpn_raw:
                tls["alpn"] = unquote(alpn_raw).split(",")

            outbound["streamSettings"]["tlsSettings"] = tls

        if network == "grpc":
            outbound["streamSettings"]["grpcSettings"] = {
                "serviceName": q("serviceName", q("path", ""))
            }

        elif network == "ws":
            host_header = q("host", "")

            outbound["streamSettings"]["wsSettings"] = {
                "path": q("path", "/"),
                "headers": {"Host": host_header} if host_header else {},
            }

        return outbound

    except Exception as e:
        print(
            "skip broken link: " + link[:60] + "... (" + str(e) + ")",
            file=sys.stderr,
        )
        return None


def build_config(outbounds):
    all_tags = [outbound["tag"] for outbound in outbounds]

    # Серверы "только для Телеграма" не берём в автовыбор.
    tags = [
        tag for tag in all_tags
        if "telegram-only" not in tag
    ] or all_tags

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
                "settings": {
                    "auth": "noauth",
                    "udp": True
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
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
            {
                "tag": "direct",
                "protocol": "freedom",
                "settings": {}
            },
            {
                "tag": "block",
                "protocol": "blackhole",
                "settings": {}
            },
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
                    "outboundTag": "direct"
                },
                {
                    "type": "field",
                    "network": "tcp,udp",
                    "balancerTag": "all-servers"
                },
            ],
        },
    }


def push_to_gist(content):
    headers = {
        "Authorization": "Bearer " + GH_TOKEN,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = {
        "files": {
            GIST_FILENAME: {
                "content": content,
            }
        }
    }

    response = requests.patch(
        GIST_API,
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        print(
            "GitHub Gist response:",
            response.status_code,
            response.text,
            file=sys.stderr,
        )

    response.raise_for_status()
    print(f"[+] GitHub Gist: updated {GIST_FILENAME}")


def main():
    links = fetch_subscription()
    print(f"[i] Получено VLESS-ссылок: {len(links)}")

    used_tags = set()
    outbounds = []

    for link in links:
        outbound = parse_vless(link, used_tags)
        if outbound:
            outbounds.append(outbound)

    if not outbounds:
        print(
            "no valid vless links parsed, aborting",
            file=sys.stderr
        )
        sys.exit(1)

    config = build_config(outbounds)

    file_content = HEADER + json.dumps(
        [config],
        ensure_ascii=False,
        indent=2
    )

    push_to_gist(file_content)


if __name__ == "__main__":
    main()
