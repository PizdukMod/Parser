import base64
import json
import os
import sys
from urllib.parse import parse_qs, unquote

import requests

SUB_URL = "https://gitverse.ru/api/repos/Pizduk/PizdukVPN/raw/branch/master/WlSubPiz.txt"

GITVERSE_API = "https://api.gitverse.ru"
OWNER = "Pizduk"
REPO = "PizdukVPN"
OUTPUT_PATH = "WLAutoPiz.txt"
BRANCH = "master"

REMARKS = "🏳PizdukVPN🤍Авто🐇Выбор🐻‍❄️"

PROBE_URL = "https://www.gstatic.com/generate_204"
PROBE_INTERVAL = "1m"

HEADER = (
    "#profile-title: PizdukVPN Автовыбор🤍\n"
    "#profile-update-interval: 6\n"
    "#announce: base64: 8J+YjtCi0LXQu9C10LPRgNCw0Lwg0LrQsNC90LDQuzogQFBpek1vZPCfmI4K4oC877iP0JXRgdC70Lgg0L3QtSDQv9C+0YDRgtC40YDRg9C10YLRgdGPINC60L7QvdGE0LjQsyDQuNGB0L/QvtC70YzQt9GD0LnRgtC1INCQ0JvQrNCi0JXQoNCd0JDQotCY0JLQndCj0K4g0YHRgdGL0LvQutGDIOKAvO+4jw==\n"
    "#profile-web-page-url: https://t.me/PizMod\n"
    "#support-url: https://t.me/Harachok\n"
)

TOKEN = os.environ["GITVERSE_TOKEN"]

def fetch_subscription():
    r = requests.get(SUB_URL, timeout=20)
    r.raise_for_status()
    raw = r.text.strip()
    try:
        decoded = base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8")
    except Exception:
        decoded = raw
    lines = [l.strip() for l in decoded.splitlines() if l.strip().startswith("vless://")]
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
        hostname, _, query = hostpart.partition("?")

        host, _, port_raw = hostname.rpartition(":")
        port = int(port_raw.split("/", 1)[0].strip())

        params = parse_qs(query)
        name = unquote(frag) if frag else host

        def q(key, default=""):
            return params.get(key, [default])[0]

        user = {"id": userinfo, "encryption": q("encryption", "none")}
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
        print("skip broken link: " + link[:60] + "... (" + str(e) + ")", file=sys.stderr)
        return None


def build_config(outbounds):
    tags = [o["tag"] for o in outbounds]
    return {
        "remarks": REMARKS,
        "log": {"loglevel": "warning"},
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
                "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
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
            "domainStrategy": "AsIs",
            "balancers": [
                {
                    "tag": "all-servers",
                    "selector": tags,
                    "strategy": {"type": "leastPing"},
                    "fallbackTag": tags[0],
                }
            ],
            "rules": [
                {"type": "field", "network": "tcp,udp", "balancerTag": "all-servers"}
            ],
        },
    }


def push_to_gitverse(content):
    url = GITVERSE_API + "/repos/" + OWNER + "/" + REPO + "/contents/" + OUTPUT_PATH
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.gitverse.object+json; version=1",
        "Content-Type": "application/json",
    }

    sha = None
    r = requests.get(url, headers=headers, params={"ref": BRANCH}, timeout=20)
    if r.status_code == 200:
        sha = r.json().get("sha")

    payload = {
        "message": "auto: update config",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    method = requests.put if sha else requests.post
    resp = method(url, headers=headers, json=payload, timeout=20)
    if not resp.ok:
        print("Gitverse response:", resp.status_code, resp.text, file=sys.stderr)
    resp.raise_for_status()
    print("pushed:", resp.status_code)


def main():
    links = fetch_subscription()
    used_tags = set()
    outbounds = []
    for l in links:
        o = parse_vless(l, used_tags)
        if o:
            outbounds.append(o)
    if not outbounds:
        print("no valid vless links parsed, aborting", file=sys.stderr)
        sys.exit(1)
    config = build_config(outbounds)
    file_content = HEADER + json.dumps(config, ensure_ascii=False, indent=2)
    push_to_gitverse(file_content)


if __name__ == "__main__":
    main()