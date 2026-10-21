#!/usr/bin/env python3

import asyncio
import aiohttp
import aiohttp_socks
import base64
import json
import socket
import statistics
import tempfile
import os
import itertools
import time

from pathlib import Path
from urllib.parse import urlparse, parse_qs, parse_qsl, unquote, quote
from collections import defaultdict


# ============================================================
# ИСТОЧНИКИ — НЕ МЕНЯТЬ (только добавлять)
# ============================================================

SOURCES = [
    # --- из первой версии ---
    "https://freevpnhappcluchi.duckdns.org/sub/3qjxa0px9dqfd01q",
    "https://gitverse.ru/api/repos/soulcoil/Haven/raw/branch/master/Haven",
    "https://botpost.vpnruss1.ru/sub/ba63f7f9-84c0-49ac-b0ff-87acee16484a",
    "https://raw.githubusercontent.com/gooseteam-hackers/freevpn-cracks/refs/heads/main/subscription_auto.txt",
    "https://quorteam.vspboost.ru/1oRtg1/QuorVPN",
    "https://raw.githubusercontent.com/ImSketch1337/vless-/refs/heads/main/BLWLservers.txt",
    # --- добавлено из второй версии ---
    "https://gidroksi.fun/black-list",
    "https://sub.clearq.workers.dev/sub/clearqsite?id=Colab_VPN",
    "https://gist.githubusercontent.com/flexter151-rgb/de6108267d7a17ce217961b2b2e3accc/raw/b677202742aab271b311af8b808f6860dfc8fe99/gistfile1.txt",
    "https://github.com/Remiuc0ff/ya-nikogo-ne-ubival/raw/refs/heads/Remiuc0ff-patch-1/Owner-@remiuc",
    # Белые списки:
    "https://gitverse.ru/api/repos/SlavaKat/FreeProxyNova/raw/branch/master/🆓ProxyNova ❯ 🗽🕊✊ Ручной выбор Обход БС (Тест)",
    "https://gitverse.ru/api/repos/gidro/white/raw/branch/master/subscription.txt",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/best_keys.txt",
    "https://warp-gen.cyb-portal.org/CP-032",
    "https://raw.githubusercontent.com/flaafix/AetrisVPN-white-list-lite/refs/heads/main/AetrisVPN.txt",
    "https://hub.mos.ru/akelladejavu/bunker/-/raw/main/WHITE_LIST.txt",
    "https://gitverse.ru/api/repos/Benss/Vless/raw/branch/master/new_file",
    "https://raw.githubusercontent.com/linspisokobhod/linspisokobhod.github.io/refs/heads/main/sub/LTE.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
]


# ============================================================
# ЗАКРЕПЛЁННЫЕ КОНФИГИ
# Добавляются в начало итоговой подписки БЕЗ проверки
# и не удаляются последующими запусками скрипта — просто впиши сюда строку(и)
# ============================================================

PINNED_CONFIGS = [
    "#profile-title: PizDukVPN Миксер🤯",
    "#announce: base64: 8J+UpdCi0LXQu9C10LPRgNCw0Lwg0LrQsNC90LDQuzogQFBpem1vZPCfpboK8J+lsNCQ0LLRgtC+0L7QsdC90L7QstC70LXQvdC40LUg0YDQsNC3INCyIDYg0YfQsNGB0L7QsvCfmLE=",
    "#profile-web-page-url: https://t.me/PizMod",
    "#support-url: https://t.me/Harachok",
    "#profile-update-interval: 4",
    #типо пропуск ок,чисто для меня
]


# ============================================================
# НАСТРОЙКИ
# ============================================================

TARGET_COUNT = 130          # сколько конфигов взять в итоге (не считая закреплённых)
EARLY_STOP_MULT = 3        # остановить xray-проверку, когда найдено TARGET_COUNT * N рабочих
                           # (из них берутся лучшие по пингу). 0 = проверять все

MAX_PER_COUNTRY = 15       # максимум конфигов на одну страну (0 = без ограничения)

MAX_PING_MS = 3000         # отсечка совсем медленных (РЕАЛЬНЫЙ пинг через прокси)
GOOD_PING_MS = 300         # только для значков в логе

# --- реальный пинг ---
PING_SAMPLES = 3           # сколько замеров после прогрева; берётся медиана
                           # (прогревочный запрос с TLS-рукопожатием в пинг не входит)

# --- реальный выходной IP: гео запрашивается ЧЕРЕЗ сам прокси ---
GEO_URLS = (
    "https://ipwho.is/",
    "http://ip-api.com/json/?fields=status,countryCode,city,query",
)
EXIT_GEO = {}              # config -> (country_code, geo_name, exit_ip)

MAX_TCP_PING_MS = 1700     # TCP-пинг выше этого (или нет ответа) — в xray не идёт
TCP_CONCURRENCY = 200      # одновременных TCP-проверок

FETCH_TIMEOUT = 20.0

CONCURRENCY = 15           # одновременных xray-процессов (осторожно с RAM раннера)
XRAY_STARTUP_WAIT = 1.2    # сек, дать xray подняться
XRAY_TEST_TIMEOUT = 12.0   # сек на всю сессию через прокси (прогрев + замеры + гео)
XRAY_BINARY = "xray"       # должен быть в PATH (см. workflow)
TEST_URLS = [
    "https://cp.cloudflare.com/generate_204",
    "https://www.gstatic.com/generate_204",
]

GEO_DELAY = 1.4            # ip-api.com бесплатно (только для фолбэка по адресу сервера)
PROGRESS_EVERY = 50        # как часто писать прогресс xray-проверки (раз в N конфигов)
BASE_LOCAL_PORT = 21000

OUTPUT_FILE = Path("output/sub.txt")

PROTOCOLS = (
    "vless://", "vmess://", "trojan://", "ss://",
    "ssr://", "hysteria2://", "hy2://", "tuic://",
)

# Только эти протоколы можно реально проверить через xray.
# hy2/tuic/ssr (UDP) по TCP-коннекту проверить нельзя — в итог не попадают.
XRAY_SUPPORTED = ("vless://", "vmess://", "trojan://", "ss://")


# ============================================================
# НАЗВАНИЯ СТРАН
# ============================================================

COUNTRY_NAMES = {
    "RU": "Россия", "DE": "Германия", "NL": "Нидерланды", "FI": "Финляндия",
    "SE": "Швеция", "NO": "Норвегия", "DK": "Дания", "FR": "Франция",
    "GB": "Великобритания", "UK": "Великобритания", "US": "США", "CA": "Канада",
    "PL": "Польша", "CZ": "Чехия", "CH": "Швейцария", "AT": "Австрия",
    "BE": "Бельгия", "IT": "Италия", "ES": "Испания", "PT": "Португалия",
    "IE": "Ирландия", "IS": "Исландия", "EE": "Эстония", "LV": "Латвия",
    "LT": "Литва", "UA": "Украина", "BY": "Беларусь", "KZ": "Казахстан",
    "UZ": "Узбекистан", "GE": "Грузия", "AM": "Армения", "AZ": "Азербайджан",
    "TR": "Турция", "IL": "Израиль", "AE": "ОАЭ", "JP": "Япония",
    "KR": "Южная Корея", "CN": "Китай", "HK": "Гонконг", "SG": "Сингапур",
    "IN": "Индия", "AU": "Австралия", "BR": "Бразилия", "MX": "Мексика",
    "AR": "Аргентина", "CL": "Чили", "ZA": "ЮАР", "RO": "Румыния",
    "BG": "Болгария", "GR": "Греция", "HU": "Венгрия", "SK": "Словакия",
    "SI": "Словения", "HR": "Хорватия", "RS": "Сербия", "LU": "Люксембург",
    "LI": "Лихтенштейн", "MT": "Мальта", "CY": "Кипр", "TH": "Таиланд",
    "VN": "Вьетнам", "ID": "Индонезия", "MY": "Малайзия", "PH": "Филиппины",
    "NZ": "Новая Зеландия",
}


# ============================================================
# BASE64
# ============================================================

def b64decode_safe(value):
    if not value:
        return None
    value = value.strip()
    value = value.replace("-", "+").replace("_", "/")
    value += "=" * (-len(value) % 4)
    try:
        return base64.b64decode(value, validate=False).decode("utf-8", errors="ignore")
    except Exception:
        return None


# ============================================================
# ФЛАГ / НАЗВАНИЕ СТРАНЫ
# ============================================================

def get_country_flag(country_code):
    if not country_code or len(country_code) != 2 or not country_code.isalpha():
        return "🌐"
    country_code = country_code.upper()
    return chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)


def get_country_name(country_code):
    if not country_code:
        return "Неизвестная страна"
    return COUNTRY_NAMES.get(country_code.upper(), country_code.upper())


def make_geo_name(country_code, city):
    flag = get_country_flag(country_code)
    country = get_country_name(country_code)
    if city:
        city = str(city).strip()
        if city:
            return f"{flag} {country} — {city}"
    return f"{flag} {country}"


# ============================================================
# ПЕРЕИМЕНОВАНИЕ
# ============================================================

def rename_config(line, new_name):
    if line.startswith("vmess://"):
        decoded = b64decode_safe(line[len("vmess://"):])
        if decoded:
            try:
                obj = json.loads(decoded)
                obj["ps"] = new_name
                encoded = base64.b64encode(
                    json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                ).decode("utf-8")
                return "vmess://" + encoded
            except Exception:
                pass
        return line

    base_line = line.split("#", 1)[0]
    return f"{base_line}#{quote(new_name)}"


# ============================================================
# ИЗВЛЕЧЕНИЕ КОНФИГОВ
# ============================================================

def extract_lines(raw):
    if not raw:
        return []
    candidates = [raw]
    decoded = b64decode_safe(raw)
    if decoded and "://" in decoded:
        candidates.append(decoded)

    result = []
    for text in candidates:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(PROTOCOLS):
                result.append(line)
    return list(dict.fromkeys(result))


# ============================================================
# КЛЮЧ ДЛЯ УДАЛЕНИЯ ДУБЛИКАТОВ
# Два конфига с разным названием (#...), но одним сервером — дубли.
# ============================================================

def dedupe_key(line):
    """Ключ дубликата: протокол + сервер + порт + учётные данные + параметры.
    Название (#...), порядок параметров и пустые параметры не влияют."""
    line = line.strip()

    if line.startswith("vmess://"):
        data = b64decode_safe(line[len("vmess://"):])
        if data:
            try:
                o = json.loads(data)
                return ("vmess", str(o.get("add")).strip().lower(), str(o.get("port")),
                        str(o.get("id")).strip().lower(), o.get("net") or "tcp",
                        o.get("path") or "", (o.get("host") or "").lower(),
                        o.get("tls") or "", (o.get("sni") or "").lower())
            except Exception:
                pass
        return ("raw", line)

    try:
        parsed = urlparse(line.split("#", 1)[0])
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").lower()
        port = parsed.port
        user = unquote(parsed.username or "")
        pw = unquote(parsed.password or "")

        # ss://BASE64@host:port и ss://method:pass@host:port — одно и то же
        if scheme == "ss" and not pw:
            dec = b64decode_safe(user)
            if dec and ":" in dec:
                user, pw = dec.split(":", 1)

        if scheme in ("vless", "vmess"):
            user = user.lower()

        params = tuple(sorted(
            (k.lower(), v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if v != ""
        ))
        if not host:
            return ("raw", line.split("#", 1)[0].lower())
        return (scheme, user, pw, host, port, params)
    except Exception:
        return ("raw", line.split("#", 1)[0].lower())


# ============================================================
# HOST / PORT
# ============================================================

def get_host_port(line):
    if line.startswith("vmess://"):
        data = b64decode_safe(line[len("vmess://"):])
        if not data:
            return None
        try:
            obj = json.loads(data)
            host = obj.get("add")
            port = int(obj.get("port"))
            if host and port:
                return host, port
        except Exception:
            return None
        return None

    try:
        parsed = urlparse(line)
        if parsed.hostname and parsed.port:
            return parsed.hostname, parsed.port
    except Exception:
        pass
    return None


def query_params(parsed):
    result = {}
    for key, values in parse_qs(parsed.query, keep_blank_values=True).items():
        if values:
            result[key.lower()] = values[0]
    return result


def first(params, *names):
    for name in names:
        value = params.get(name.lower())
        if value is not None:
            return value
    return None


# ============================================================
# ПОСТРОЕНИЕ XRAY-КОНФИГА ИЗ URI
# ============================================================

def build_stream_settings(params, default_host):
    network = (first(params, "type", "network", "net") or "tcp").lower()
    security = (first(params, "security") or "none").lower()
    stream = {"network": network}

    if network == "ws":
        stream["wsSettings"] = {
            "path": unquote(first(params, "path") or "/"),
            "headers": {"Host": first(params, "host") or default_host},
        }
    elif network == "grpc":
        stream["grpcSettings"] = {
            "serviceName": first(params, "servicename") or "",
        }
    elif network in ("xhttp", "http", "h2"):
        stream["network"] = "xhttp" if network == "xhttp" else "h2"
        path = unquote(first(params, "path") or "/")
        host = first(params, "host") or default_host
        if stream["network"] == "xhttp":
            stream["xhttpSettings"] = {"path": path, "host": host, "mode": first(params, "mode") or "auto"}
        else:
            stream["httpSettings"] = {"path": path, "host": [host]}

    if security == "reality":
        stream["security"] = "reality"
        stream["realitySettings"] = {
            "serverName": first(params, "sni", "servername") or default_host,
            "fingerprint": first(params, "fp", "fingerprint") or "chrome",
            "publicKey": first(params, "pbk", "publickey"),
            "shortId": first(params, "sid", "shortid") or "",
            "spiderX": first(params, "spx") or "",
        }
    elif security == "tls":
        stream["security"] = "tls"
        stream["tlsSettings"] = {
            "serverName": first(params, "sni", "servername") or default_host,
            "allowInsecure": True,
            "fingerprint": first(params, "fp", "fingerprint") or "chrome",
        }
    else:
        stream["security"] = "none"

    return stream


def parse_vless(line):
    try:
        parsed = urlparse(line)
        uuid, host, port = parsed.username, parsed.hostname, parsed.port
        if not (uuid and host and port):
            return None
        params = query_params(parsed)
        return {
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": host,
                    "port": port,
                    "users": [{
                        "id": uuid,
                        "encryption": first(params, "encryption") or "none",
                        "flow": first(params, "flow") or "",
                    }],
                }]
            },
            "streamSettings": build_stream_settings(params, host),
        }
    except Exception:
        return None


def parse_trojan(line):
    try:
        parsed = urlparse(line)
        password, host, port = parsed.username, parsed.hostname, parsed.port
        if not (password and host and port):
            return None
        params = query_params(parsed)
        return {
            "protocol": "trojan",
            "settings": {"servers": [{"address": host, "port": port, "password": password}]},
            "streamSettings": build_stream_settings(params, host),
        }
    except Exception:
        return None


def parse_ss(line):
    try:
        body = line[len("ss://"):]
        userinfo_part, _, rest = body.partition("@")
        if not rest:
            return None
        hostport_part = rest.split("#", 1)[0].split("?", 1)[0]
        host, _, port_s = hostport_part.partition(":")
        port = int(port_s) if port_s.isdigit() else None
        if not (host and port):
            return None

        decoded = b64decode_safe(unquote(userinfo_part))
        creds = decoded if (decoded and ":" in decoded) else unquote(userinfo_part)
        if ":" not in creds:
            return None
        method, password = creds.split(":", 1)

        return {
            "protocol": "shadowsocks",
            "settings": {"servers": [{"address": host, "port": port, "method": method, "password": password}]},
        }
    except Exception:
        return None


def parse_vmess(line):
    try:
        data = b64decode_safe(line[len("vmess://"):])
        if not data:
            return None
        obj = json.loads(data)
        host, port, uuid = obj.get("add"), int(obj.get("port")), obj.get("id")
        if not (host and port and uuid):
            return None

        network = str(obj.get("net", "tcp")).lower()
        stream = {"network": network}

        if network == "ws":
            stream["wsSettings"] = {"path": obj.get("path", "/"), "headers": {"Host": obj.get("host", "") or host}}
        elif network == "grpc":
            stream["grpcSettings"] = {"serviceName": obj.get("path", "")}

        if str(obj.get("tls", "")).lower() == "tls":
            stream["security"] = "tls"
            stream["tlsSettings"] = {
                "serverName": obj.get("sni") or obj.get("host") or host,
                "allowInsecure": True,
            }
        else:
            stream["security"] = "none"

        return {
            "protocol": "vmess",
            "settings": {
                "vnext": [{
                    "address": host,
                    "port": port,
                    "users": [{
                        "id": uuid,
                        "alterId": int(obj.get("aid", 0) or 0),
                        "security": obj.get("scy", "auto"),
                    }],
                }]
            },
            "streamSettings": stream,
        }
    except Exception:
        return None


def build_outbound(line):
    if line.startswith("vless://"):
        return parse_vless(line)
    if line.startswith("vmess://"):
        return parse_vmess(line)
    if line.startswith("trojan://"):
        return parse_trojan(line)
    if line.startswith("ss://"):
        return parse_ss(line)
    return None


# ============================================================
# ПУЛ ЛОКАЛЬНЫХ ПОРТОВ
# ============================================================

_port_counter = itertools.count(BASE_LOCAL_PORT)
_port_pool = asyncio.Queue()


def init_port_pool(n):
    for _ in range(n):
        _port_pool.put_nowait(next(_port_counter))


# ============================================================
# БЫСТРАЯ TCP-ПРОВЕРКА (до xray)
# ============================================================

async def tcp_ping(line):
    """Возвращает время TCP-подключения в мс или None."""
    hp = get_host_port(line)
    if not hp:
        return None
    host, port = hp
    start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=MAX_TCP_PING_MS / 1000,
        )
    except Exception:
        return None
    ms = (time.monotonic() - start) * 1000
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass
    return ms


async def tcp_filter(candidates):
    """Оставляет только отвечающие по TCP. Возвращает список (config, tcp_ms)."""
    semaphore = asyncio.Semaphore(TCP_CONCURRENCY)
    alive = []

    async def worker(config):
        async with semaphore:
            ms = await tcp_ping(config)
            if ms is not None and ms <= MAX_TCP_PING_MS:
                alive.append((config, ms))

    await asyncio.gather(*(worker(c) for c in candidates))
    return alive


# ============================================================
# РЕАЛЬНЫЙ ВЫХОДНОЙ IP: гео через сам прокси
# ============================================================

async def fetch_exit_geo(session):
    """Запрашивает гео через прокси-сессию. Возвращает (country_code, city, exit_ip) или None."""
    for url in GEO_URLS:
        try:
            async with session.get(url, ssl=False) as r:
                if r.status != 200:
                    continue
                d = await r.json(content_type=None)
                if d.get("success") is True or d.get("status") == "success":
                    cc = d.get("country_code") or d.get("countryCode")
                    if cc:
                        return cc, d.get("city"), d.get("ip") or d.get("query")
        except Exception:
            continue
    return None


# ============================================================
# РЕАЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ XRAY — возвращает пинг (мс) или None
#
# Пинг считается честно:
#   1) прогревочный запрос (SOCKS-коннект + TLS-рукопожатие) — НЕ входит в пинг;
#   2) PING_SAMPLES замеров по уже открытому соединению;
#   3) берётся медиана — единичные всплески не портят результат.
# Затем через ту же сессию определяется реальный выходной IP и страна.
# ============================================================

async def xray_real_check(line):
    outbound = build_outbound(line)
    if not outbound:
        return None

    port = await _port_pool.get()
    proc = None
    tmp_path = None

    try:
        xray_config = {
            "log": {"loglevel": "none"},
            "inbounds": [{
                "listen": "127.0.0.1",
                "port": port,
                "protocol": "socks",
                "settings": {"udp": False},
            }],
            "outbounds": [outbound],
        }

        fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="xr_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(xray_config, f)

        proc = await asyncio.create_subprocess_exec(
            XRAY_BINARY, "run", "-c", tmp_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        await asyncio.sleep(XRAY_STARTUP_WAIT)

        if proc.returncode is not None:
            return None  # xray сразу упал — конфиг битый

        connector = aiohttp_socks.ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
        timeout = aiohttp.ClientTimeout(total=XRAY_TEST_TIMEOUT)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # пробуем по очереди тестовые URL — хватает одного рабочего
            for url in TEST_URLS:
                try:
                    # 1) прогрев — не считается
                    async with session.get(url, ssl=False) as resp:
                        if resp.status not in (200, 204):
                            continue
                        await resp.read()

                    # 2) замеры по прогретому соединению
                    samples = []
                    try:
                        for _ in range(PING_SAMPLES):
                            start = time.monotonic()
                            async with session.get(url, ssl=False) as resp:
                                if resp.status not in (200, 204):
                                    break
                                await resp.read()
                            samples.append((time.monotonic() - start) * 1000)
                    except Exception:
                        pass  # если часть замеров прошла — используем их

                    if not samples:
                        continue

                    # 3) реальный выходной IP / страна / город (через тот же прокси)
                    geo = await fetch_exit_geo(session)
                    if geo:
                        cc, city, exit_ip = geo
                        EXIT_GEO[line] = (cc, make_geo_name(cc, city), exit_ip)

                    return statistics.median(samples)
                except Exception:
                    continue
        return None

    except Exception:
        return None

    finally:
        if proc is not None and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        await _port_pool.put(port)


# ============================================================
# GEO СЕРВЕРА (фолбэк, если гео через прокси не ответило)
# ============================================================

async def get_server_geo(session, host):
    """Возвращает (country_code, geo_name) или (None, None)."""
    try:
        try:
            ip = socket.gethostbyname(host)
        except Exception:
            ip = host

        url = f"http://ip-api.com/json/{ip}?fields=status,countryCode,city"
        timeout = aiohttp.ClientTimeout(total=8.0)

        for _ in range(2):
            async with session.get(url, timeout=timeout) as response:
                if response.status == 429:  # лимит — ждём и пробуем ещё раз
                    await asyncio.sleep(5)
                    continue
                if response.status != 200:
                    return None, None
                data = await response.json(content_type=None)
                if data.get("status") != "success":
                    return None, None
                country_code = data.get("countryCode")
                return country_code, make_geo_name(country_code, data.get("city"))
        return None, None
    except Exception:
        return None, None


# ============================================================
# СКАЧИВАНИЕ ПОДПИСОК
# ============================================================

def short_name(url):
    """Короткое имя источника для лога (только домен)."""
    name = urlparse(url).netloc or url
    return name if len(name) <= 28 else name[:27] + "…"


async def fetch(session, url):
    try:
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
        async with session.get(url, timeout=timeout, allow_redirects=True) as response:
            response.raise_for_status()
            return await response.text(errors="ignore")
    except Exception as e:
        print(f"[!] {short_name(url)}: {str(e)[:60]}")
        return None


async def fetch_source(session, url):
    raw = await fetch(session, url)
    configs = extract_lines(raw) if raw else []
    print(f"[i] {short_name(url)}: {len(configs)}")
    return url, configs


# ============================================================
# ПРОВЕРКА ВСЕХ КАНДИДАТОВ
# ============================================================

async def check_all(candidates):
    """Проверяет конфиги через xray.
    Возвращает (working, failed): working — список (config, latency_ms),
    failed — список реально проверенных, но нерабочих конфигов."""
    semaphore = asyncio.Semaphore(CONCURRENCY)
    working = []
    failed = []
    stop_at = TARGET_COUNT * EARLY_STOP_MULT if EARLY_STOP_MULT else None
    stop_event = asyncio.Event()
    done = 0
    total = len(candidates)

    async def worker(config):
        nonlocal done
        async with semaphore:
            if stop_event.is_set():
                return  # после ранней остановки не проверяем и не считаем нерабочим
            try:
                latency = await xray_real_check(config)
            except Exception:
                latency = None
            done += 1
            if latency is not None and latency <= MAX_PING_MS:
                working.append((config, latency))
                if stop_at and len(working) >= stop_at and not stop_event.is_set():
                    stop_event.set()
                    print(f"    xray {done}/{total} ✓{len(working)} — хватит, стоп")
                    return
            else:
                failed.append(config)
            if done % PROGRESS_EVERY == 0:
                print(f"    xray {done}/{total} ✓{len(working)}")

    await asyncio.gather(*(worker(c) for c in candidates))
    return working, failed


# ============================================================
# MAIN
# ============================================================

async def main():
    init_port_pool(CONCURRENCY)

    # ---------- 1. скачиваем ВСЕ подписки ----------
    print("[i] Скачиваю подписки...")
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(fetch_source(session, u) for u in SOURCES),
                                       return_exceptions=True)

        all_configs = []
        source_of = {}  # ключ конфига -> url источника (первого, где он встретился)
        for i, r in enumerate(results, 1):
            if isinstance(r, tuple):
                url, cfgs = r
                for c in cfgs:
                    source_of.setdefault(dedupe_key(c), url)
                all_configs.extend(cfgs)
            else:
                print(f"[!] Источник #{i}: ошибка {str(r)[:60]}")

        print(f"[i] Всего скачано: {len(all_configs)}")

        # ---------- 2. удаляем дубликаты (до проверки — экономит время) ----------
        # закреплённые никогда не удаляются; из подписок убираются только те,
        # что уже есть среди закреплённых или повторяются внутри подписок
        pinned = [c.strip() for c in PINNED_CONFIGS if c.strip()]
        seen = {dedupe_key(c) for c in pinned if "://" in c}

        unique = []
        for c in all_configs:
            k = dedupe_key(c)
            if k in seen:
                continue
            seen.add(k)
            unique.append(c)

        print(f"[i] После удаления дубликатов: {len(unique)}")

        # проверяем только то, что реально можно проверить через xray
        candidates = [c for c in unique if c.startswith(XRAY_SUPPORTED)]
        skipped = len(unique) - len(candidates)
        if skipped:
            print(f"[i] Без проверки (hy2/tuic/ssr) — пропущено: {skipped}")

        if not candidates:
            print("[x] Нет конфигов для проверки.")
            return

        # статистика по источникам: url -> [проверено, нерабочих]
        stats = {}

        def count(config, ok):
            s = stats.setdefault(source_of.get(dedupe_key(config)), [0, 0])
            s[0] += 1
            if not ok:
                s[1] += 1

        # ---------- 3. быстрая TCP-проверка ----------
        print(f"\n[i] TCP: проверяю {len(candidates)}...")
        alive = await tcp_filter(candidates)
        alive_set = {c for c, _ in alive}
        for c in candidates:
            if c not in alive_set:
                count(c, False)
        print(f"[i] TCP ок: {len(alive)} из {len(candidates)}")

        if not alive:
            print("[x] Ни один сервер не ответил по TCP.")
            return

        # самые быстрые по TCP проверяем в xray первыми
        alive.sort(key=lambda x: x[1])
        candidates = [c for c, _ in alive]

        # ---------- 3.1 реальная проверка через xray (пинг + выходной IP) ----------
        print(f"\n[i] xray: проверяю {len(candidates)}...")
        working, failed = await check_all(candidates)
        for c, _ in working:
            count(c, True)
        for c in failed:
            count(c, False)
        print(f"[✓] Рабочих: {len(working)}")

        if not working:
            print("[x] Рабочих конфигов нет.")
            return

        # ---------- 4. отбор лучших по реальному пингу + лимит на страну ----------
        working.sort(key=lambda x: x[1])

        print("\n[i] Определяю страны (по реальному выходному IP) и отбираю лучшие...")
        geo_cache = {}
        per_country = defaultdict(int)
        items = []  # (country_key, latency, renamed_line)

        for config, latency in working:
            if len(items) >= TARGET_COUNT:
                break

            info = EXIT_GEO.get(config)
            if info:
                code, name, _ = info
            else:  # гео через прокси не ответило — по адресу сервера
                code, name = None, None
                hp = get_host_port(config)
                if hp:
                    host = hp[0]
                    if host not in geo_cache:
                        geo_cache[host] = await get_server_geo(session, host)
                        await asyncio.sleep(GEO_DELAY)
                    code, name = geo_cache[host]

            limit_key = code or "??"
            if MAX_PER_COUNTRY and per_country[limit_key] >= MAX_PER_COUNTRY:
                continue
            per_country[limit_key] += 1

            final_name = name or "🌐 Неизвестно"
            country_key = get_country_name(code) if code else "я_Неизвестно"  # неизвестные — в конец
            items.append((country_key, latency, rename_config(config, final_name)))

            if len(items) % 10 == 0:
                print(f"    отобрано {len(items)}/{TARGET_COUNT}")

        print(f"[i] Отобрано: {len(items)} (стран: {len(per_country)})")

        # группируем по стране, внутри страны — по пингу
        items.sort(key=lambda x: (x[0], x[1]))
        renamed = [line for _, _, line in items]

    # ---------- 5. сохраняем ----------
    final_list = pinned + renamed

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(final_list) + "\n", encoding="utf-8")

    print()
    print(f"[✓] Готово: {len(final_list)} (закр. {len(pinned)} + {len(renamed)})")
    print(f"[✓] Файл: {OUTPUT_FILE}")

    print("\n[i] Распределение по странам:")
    for code, n in sorted(per_country.items(), key=lambda kv: kv[1], reverse=True):
        flag = get_country_flag(code) if code != "??" else "🌐"
        name = get_country_name(code) if code != "??" else "Неизвестно"
        print(f"    {flag} {name:<20} {n:>3}")

    # ---------- 6. где больше всего нерабочих ----------
    rows = [(url, tested, bad) for url, (tested, bad) in stats.items() if url and tested]
    if rows:
        rows.sort(key=lambda r: r[2], reverse=True)
        print("\n[i] Нерабочих по источникам:")
        for n, (url, tested, bad) in enumerate(rows):
            icon = "🥴" if n == 0 else "  "
            print(f"{icon} {short_name(url)}: {bad}/{tested} ({bad * 100 // tested}%)")
        top_url, top_tested, top_bad = rows[0]
        print(f"\n[!] Больше всего нерабочих: {short_name(top_url)} ({top_bad} из {top_tested})")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Остановлено.")
