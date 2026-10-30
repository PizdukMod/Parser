#!/usr/bin/env python3

import asyncio
import aiohttp
import aiohttp_socks
import base64
import ipaddress
import json
import re
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
    "https://freevpnhappcluchi.duckdns.org/sub/lzjrpfi55soz18q9",
    "https://gitverse.ru/api/repos/soulcoil/Haven/raw/branch/master/Haven",
    "https://quorteam.vspboost.ru/1oRtg1/QuorVPN",
    "https://raw.githubusercontent.com/gazeta404/rain_vpn_sub/main/subscribe.txt",
    # --- добавлено из второй версии ---
    "https://gidroksi.fun/black-list",
    # Белые списки:
    "https://hub.mos.ru/akelladejavu/bunker/-/raw/main/BLWL_MIX.txt",
    # --- добавлено для объёма (из скрипта ЧС; ненужное можно удалить) ---
    "https://raw.githubusercontent.com/ImSketch1337/vless-/refs/heads/main/BLWLservers.txt",
    "https://raw.githubusercontent.com/flaafix/AetrisVPN-black-list/refs/heads/main/configs.txt",
    "https://raw.githubusercontent.com/Buffetbarko/Universal-Proxy-Config-Parser-/main/blacklist_vpn.txt",
    "https://mifa.world/onix",
]


# ============================================================
# ЗАКРЕПЛЁННЫЕ КОНФИГИ
# Добавляются в начало итоговой подписки БЕЗ проверки
# и не удаляются последующими запусками скрипта — просто впиши сюда строку(и)
# ============================================================

PINNED_CONFIGS = [
    "#profile-title: PizdukVPN Миксер🤯",
    "#announce: base64: 8J+UpdCi0LXQu9C10LPRgNCw0Lwg0LrQsNC90LDQuzogQFBpem1vZPCfpboK8J+lsNCQ0LLRgtC+0L7QsdC90L7QstC70LXQvdC40LUg0YDQsNC3INCyIDYg0YfQsNGB0L7QsvCfmLE=",
    "#profile-web-page-url: t.me/PizMod",
    "#support-url: t.me/Harachok",
    "#profile-update-interval: 8",
    #типо пропуск ок,чисто для меня
]


# ============================================================
# НАСТРОЙКИ  (режим «МНОГО КОНФИГОВ»: проверки мягкие, отбор широкий)
# ============================================================

TARGET_COUNT = 1500        # сколько конфигов взять в итоге (не считая закреплённых)
EARLY_STOP_MULT = 0        # 0 = проверять ВСЕ (ранней остановки нет)

MAX_PER_COUNTRY = 0        # 0 = без ограничения на страну

MAX_PING_MS = 5000         # отсечка совсем медленных (РЕАЛЬНЫЙ пинг через прокси)
GOOD_PING_MS = 300         # только для значков в логе

# --- реальный пинг ---
PING_SAMPLES = 3           # замеров после прогрева; берётся медиана

# --- реальный выходной IP: гео запрашивается ЧЕРЕЗ сам прокси (город по-русски) ---
GEO_URLS = (
    "https://ipwho.is/?lang=ru",
    "http://ip-api.com/json/?fields=status,countryCode,city,query&lang=ru",
)
EXIT_GEO = {}              # config -> (country_code, geo_name, exit_ip)

MAX_TCP_PING_MS = 2500     # TCP-пинг выше этого (или нет ответа) — в xray не идёт
TCP_CONCURRENCY = 300      # одновременных TCP-проверок

# --- Скачивание подписок ---
FETCH_TIMEOUT = 25.0
FETCH_RETRIES = 3
FETCH_HEADERS_LIST = [     # User-Agent меняется от попытки к попытке
    {"User-Agent": "v2rayN/6.42"},
    {"User-Agent": "Happ/7.0.0"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64;)"},
]

CONCURRENCY = 40           # одновременных xray-процессов (осторожно с RAM раннера: ~30-50 МБ на процесс)
XRAY_STARTUP_TIMEOUT = 6.0 # сек: максимум ждём, пока xray откроет локальный порт
XRAY_TEST_TIMEOUT = 15.0   # сек на всю сессию через прокси (прогрев + замеры + гео)
XRAY_BINARY = "xray"       # должен быть в PATH (см. workflow)
TEST_URLS = [
    "https://cp.cloudflare.com/generate_204",
    "https://www.gstatic.com/generate_204",
]

PROGRESS_EVERY = 100       # как часто писать прогресс xray-проверки (раз в N конфигов)
BASE_LOCAL_PORT = 21000

# Каскады: вход и выход в разных странах -> в конце названия «{флаг входа}Каскад»
DETECT_CASCADE = True

OUTPUT_FILE = Path("output/sub.txt")

PROTOCOLS = (
    "vless://", "vmess://", "trojan://", "ss://",
    "ssr://", "hysteria2://", "hy2://", "tuic://",
)

# Только эти протоколы можно реально проверить через xray.
# hy2/tuic/ssr (UDP) по TCP-коннекту проверить нельзя — в итог не попадают.
XRAY_SUPPORTED = ("vless://", "vmess://", "trojan://", "ss://")


# ============================================================
# НАЗВАНИЯ СТРАН И ГОРОДОВ
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

# Длинные названия сокращаем
COUNTRY_NAMES.update({
    "GB": "Британия", "UK": "Британия", "KR": "Юж. Корея",
    "NZ": "Нов. Зеландия", "LI": "Лихтенш.",
})

# Запасной словарь, если сервис вернул город не по-русски
CITY_RU = {
    "Frankfurt am Main": "Франкфурт", "Frankfurt": "Франкфурт", "Amsterdam": "Амстердам",
    "Helsinki": "Хельсинки", "Falkenstein": "Фалькенштайн", "Nuremberg": "Нюрнберг",
    "London": "Лондон", "Paris": "Париж", "Warsaw": "Варшава", "Stockholm": "Стокгольм",
    "Vienna": "Вена", "Prague": "Прага", "Tallinn": "Таллин", "Riga": "Рига",
    "Vilnius": "Вильнюс", "Moscow": "Москва", "Saint Petersburg": "Санкт-Петербург",
    "St Petersburg": "Санкт-Петербург", "New York": "Нью-Йорк", "Los Angeles": "Лос-Анджелес",
    "Tokyo": "Токио", "Istanbul": "Стамбул", "Madrid": "Мадрид", "Milan": "Милан",
    "Zurich": "Цюрих", "Dublin": "Дублин", "Almaty": "Алматы", "Kyiv": "Киев",
    "Berlin": "Берлин", "Rome": "Рим", "Oslo": "Осло", "Copenhagen": "Копенгаген",
    "Brussels": "Брюссель", "Lisbon": "Лиссабон", "Bucharest": "Бухарест",
    "Sofia": "София", "Budapest": "Будапешт", "Belgrade": "Белград", "Athens": "Афины",
    "Tbilisi": "Тбилиси", "Yerevan": "Ереван", "Baku": "Баку", "Dubai": "Дубай",
    "Tel Aviv": "Тель-Авив", "Chicago": "Чикаго", "Miami": "Майами", "Dallas": "Даллас",
    "Seattle": "Сиэтл", "San Jose": "Сан-Хосе", "Ashburn": "Эшберн", "Toronto": "Торонто",
    "Montreal": "Монреаль", "Sydney": "Сидней", "Seoul": "Сеул", "Osaka": "Осака",
    "Mumbai": "Мумбаи", "Sao Paulo": "Сан-Паулу", "Johannesburg": "Йоханнесбург",
}

_CYRILLIC = re.compile("[А-Яа-яЁё]")

# Серверы за этими CDN не считаем каскадом (страна «входа» там ничего не значит)
CDN_WORDS = ("cloudflare", "fastly", "akamai", "cloudfront", "gcore", "bunny")


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
# ФЛАГ / НАЗВАНИЕ СТРАНЫ / ГОРОД
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


def city_ru(city):
    """Город по-русски: уже русский — как есть, иначе словарь, иначе None."""
    if not city:
        return None
    city = str(city).strip()
    if not city:
        return None
    if _CYRILLIC.search(city):
        return city
    return CITY_RU.get(city)


def make_geo_name(country_code, city):
    flag = get_country_flag(country_code)
    country = get_country_name(country_code)
    city = city_ru(city)
    if city and city != country:
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
# РАЗБОР host:port (с поддержкой IPv6)
# ============================================================

def _split_hostport(hostport):
    """'host:443' -> ('host', '443'); '[::1]:443' -> ('::1', '443')."""
    hostport = hostport.strip().rstrip("/")
    if hostport.startswith("["):
        host, _, rest = hostport[1:].partition("]")
        return host, rest.lstrip(":")
    if ":" not in hostport:
        return hostport, ""
    host, _, ports = hostport.rpartition(":")
    return host, ports


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

    if line.startswith("ss://"):
        ob = parse_ss(line)
        if ob:
            srv = ob["settings"]["servers"][0]
            return srv["address"], srv["port"]
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
# DNS (асинхронно, с кэшем) — нужен для определения входа каскада
# ============================================================

_dns_cache = {}


async def resolve_ip(host):
    if host in _dns_cache:
        return _dns_cache[host]
    ip = None
    try:
        ipaddress.ip_address(host)
        ip = host
    except ValueError:
        try:
            loop = asyncio.get_running_loop()
            infos = await asyncio.wait_for(
                loop.getaddrinfo(host, None, family=socket.AF_INET, type=socket.SOCK_STREAM),
                timeout=5.0,
            )
            if infos:
                ip = infos[0][4][0]
        except Exception:
            ip = None
    _dns_cache[host] = ip
    return ip


# ============================================================
# ПОСТРОЕНИЕ XRAY-КОНФИГА ИЗ URI
# (разбор максимально терпимый — чтобы потерять как можно меньше конфигов)
# ============================================================

def build_stream_settings(params, default_host, default_security="none"):
    network = (first(params, "type", "network", "net") or "tcp").lower()
    # "raw" = обычный tcp; "splithttp" = старое имя xhttp
    if network in ("raw", ""):
        network = "tcp"
    if network == "splithttp":
        network = "xhttp"
    security = (first(params, "security") or default_security).lower()
    stream = {"network": network}

    if network == "ws":
        stream["wsSettings"] = {
            "path": unquote(first(params, "path") or "/"),
            "headers": {"Host": first(params, "host") or default_host},
        }
    elif network == "grpc":
        stream["grpcSettings"] = {
            "serviceName": unquote(first(params, "servicename") or ""),
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
        pbk = first(params, "pbk", "publickey")
        if not pbk:
            return None  # reality без публичного ключа работать не может
        stream["security"] = "reality"
        stream["realitySettings"] = {
            "serverName": first(params, "sni", "servername") or default_host,
            "fingerprint": first(params, "fp", "fingerprint") or "chrome",
            "publicKey": pbk,
            "shortId": first(params, "sid", "shortid") or "",
            "spiderX": first(params, "spx") or "",
        }
    elif security == "tls":
        tls = {
            "serverName": first(params, "sni", "servername") or default_host,
            "allowInsecure": True,
            "fingerprint": first(params, "fp", "fingerprint") or "chrome",
        }
        alpn = first(params, "alpn")
        if alpn:
            tls["alpn"] = [a for a in unquote(alpn).split(",") if a]
        stream["security"] = "tls"
        stream["tlsSettings"] = tls
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
        stream = build_stream_settings(params, host)
        if stream is None:
            return None
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
            "streamSettings": stream,
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
        # у trojan по умолчанию TLS
        stream = build_stream_settings(params, host, default_security="tls")
        if stream is None:
            return None
        return {
            "protocol": "trojan",
            "settings": {"servers": [{"address": host, "port": port, "password": unquote(password)}]},
            "streamSettings": stream,
        }
    except Exception:
        return None


def parse_ss(line):
    """Shadowsocks. Понимает:
      ss://BASE64(method:password)@host:port#name        (SIP002)
      ss://method:password@host:port#name                (без base64, в т.ч. SS-2022)
      ss://BASE64(method:password@host:port)#name        (старый формат)
      IPv6-хосты [::1]:port.
    SS с plugin (obfs/v2ray-plugin) xray не умеет — такие пропускаем."""
    try:
        body = line[len("ss://"):].split("#", 1)[0]
        main, _, query = body.partition("?")
        if "plugin=" in query.lower():
            return None
        main = main.rstrip("/")

        if "@" not in main:
            decoded = b64decode_safe(unquote(main))
            if not decoded or "@" not in decoded:
                return None
            main = decoded

        userinfo, _, hostport = main.rpartition("@")
        host, ports = _split_hostport(hostport)
        port = int(ports) if ports.isdigit() else None
        if not (host and port):
            return None

        plain = unquote(userinfo)
        creds = plain if ":" in plain else b64decode_safe(plain)
        if not creds or ":" not in creds:
            return None
        method, password = creds.split(":", 1)
        method = method.strip().lower()
        if not method or not password:
            return None

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
        if network in ("raw", ""):
            network = "tcp"
        stream = {"network": network}

        if network == "ws":
            stream["wsSettings"] = {"path": obj.get("path", "/"), "headers": {"Host": obj.get("host", "") or host}}
        elif network == "grpc":
            stream["grpcSettings"] = {"serviceName": obj.get("path", "")}

        if str(obj.get("tls", "")).lower() == "tls":
            tls = {
                "serverName": obj.get("sni") or obj.get("host") or host,
                "allowInsecure": True,
            }
            alpn = obj.get("alpn")
            if alpn:
                tls["alpn"] = [a for a in str(alpn).split(",") if a]
            stream["security"] = "tls"
            stream["tlsSettings"] = tls
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
# ОЖИДАНИЕ ЛОКАЛЬНОГО ПОРТА XRAY (вместо слепого sleep:
# быстрее и без ложных «не работает» при высокой нагрузке)
# ============================================================

async def wait_local_port(proc, port, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.returncode is not None:
            return False  # xray упал — конфиг битый
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port), timeout=0.5
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            await asyncio.sleep(0.1)
    return False


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
# Проверка мягкая (как и раньше): хватает одного рабочего тестового URL.
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

        if not await wait_local_port(proc, port, XRAY_STARTUP_TIMEOUT):
            return None

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
                        EXIT_GEO[line] = (cc.upper(), make_geo_name(cc, city), exit_ip)

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
                    await proc.wait()
                except Exception:
                    pass
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        await _port_pool.put(port)


# ============================================================
# ГЕО ВХОДА (сервера из конфига) — пачками по 100 IP через ip-api.com/batch
# Нужно для каскадов и как запасная страна, если гео через прокси не ответило.
# Бесплатный лимит ~15 запросов/мин -> пауза между пачками.
# ============================================================

async def entry_geo_batch(session, ips):
    """ip -> (country_code, 'org as' в нижнем регистре)."""
    result = {}
    ips = sorted(set(ips))
    for i in range(0, len(ips), 100):
        chunk = ips[i:i + 100]
        for _ in range(3):
            try:
                async with session.post(
                    "http://ip-api.com/batch?fields=status,query,countryCode,org,as",
                    json=chunk,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as r:
                    if r.status == 429:
                        await asyncio.sleep(12)
                        continue
                    if r.status != 200:
                        break
                    data = await r.json(content_type=None)
                for d in data:
                    if d.get("status") == "success" and d.get("countryCode"):
                        result[d["query"]] = (
                            d["countryCode"].upper(),
                            f'{d.get("org", "")} {d.get("as", "")}'.lower(),
                        )
                break
            except Exception:
                await asyncio.sleep(3)
        await asyncio.sleep(4.5)
    return result


# ============================================================
# СКАЧИВАНИЕ ПОДПИСОК (с повторами, разными User-Agent и запасным
# вариантом без проверки SSL на последней попытке)
# ============================================================

def short_name(url):
    """Короткое имя источника для лога (только домен)."""
    name = urlparse(url).netloc or url
    return name if len(name) <= 28 else name[:27] + "…"


async def fetch(session, url):
    timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
    last_err = None
    for attempt in range(FETCH_RETRIES):
        headers = FETCH_HEADERS_LIST[attempt % len(FETCH_HEADERS_LIST)]
        ssl_opt = False if attempt == FETCH_RETRIES - 1 else None
        try:
            async with session.get(url, headers=headers, timeout=timeout,
                                   allow_redirects=True, ssl=ssl_opt) as response:
                response.raise_for_status()
                return await response.text(errors="ignore")
        except Exception as e:
            last_err = e
            await asyncio.sleep(1.5)
    err = str(last_err) or type(last_err).__name__
    print(f"[!] {short_name(url)}: {err[:60]}")
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

        # ---------- 4. отбор по реальному пингу (+ необязательный лимит на страну) ----------
        working.sort(key=lambda x: x[1])
        selected = working if not TARGET_COUNT else working[:TARGET_COUNT * 2]

        # гео ВХОДА: нужно для каскадов и как запасная страна
        entry_ip = {}   # config -> ip сервера из конфига
        need_entry = [c for c, _ in selected if DETECT_CASCADE or c not in EXIT_GEO]
        hosts = {get_host_port(c)[0] for c in need_entry if get_host_port(c)}
        await asyncio.gather(*(resolve_ip(h) for h in hosts))
        for c in need_entry:
            hp = get_host_port(c)
            if hp and _dns_cache.get(hp[0]):
                entry_ip[c] = _dns_cache[hp[0]]

        entry_geo = {}
        if entry_ip:
            print(f"\n[i] Гео входа (для каскадов): {len(set(entry_ip.values()))} IP...")
            entry_geo = await entry_geo_batch(session, entry_ip.values())

        print("\n[i] Определяю страны (по реальному выходному IP) и отбираю...")
        per_country = defaultdict(int)
        items = []      # (country_key, latency, renamed_line)
        cascades = 0

        for config, latency in selected:
            if TARGET_COUNT and len(items) >= TARGET_COUNT:
                break

            info = EXIT_GEO.get(config)
            exit_ip = None
            if info:
                code, name, exit_ip = info
            else:  # гео через прокси не ответило — по стране входа
                code = None
                eg = entry_geo.get(entry_ip.get(config))
                if eg:
                    code = eg[0]
                name = make_geo_name(code, None) if code else None

            limit_key = code or "??"
            if MAX_PER_COUNTRY and per_country[limit_key] >= MAX_PER_COUNTRY:
                continue
            per_country[limit_key] += 1

            final_name = name or "🌐 Неизвестно"

            # каскад: страна входа ≠ страна выхода (и вход не за CDN)
            if DETECT_CASCADE and info:
                ip = entry_ip.get(config)
                eg = entry_geo.get(ip)
                if eg and ip != exit_ip and eg[0] != code \
                        and not any(w in eg[1] for w in CDN_WORDS):
                    final_name += f" {get_country_flag(eg[0])}Каскад"
                    cascades += 1

            country_key = get_country_name(code) if code else "я_Неизвестно"  # неизвестные — в конец
            items.append((country_key, latency, rename_config(config, final_name)))

            if len(items) % 100 == 0:
                print(f"    отобрано {len(items)}/{TARGET_COUNT or '∞'}")

        print(f"[i] Отобрано: {len(items)} (стран: {len(per_country)}, каскадов: {cascades})")

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
        print(f"    {flag} {name:<20} {n:>4}")

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
