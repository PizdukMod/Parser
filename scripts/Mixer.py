#!/usr/bin/env python3

import asyncio
import aiohttp
import aiohttp_socks
import base64
import datetime
import ipaddress
import json
import re
import shutil
import socket
import statistics
import tempfile
import os
import itertools
import time

from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse, parse_qs, parse_qsl, unquote, quote


# ============================================================
# ИСТОЧНИКИ — НЕ МЕНЯТЬ (только добавлять)
# ============================================================

SOURCES = [
    # Большие
    "https://freevpn.happcluchi.workers.dev",
    "https://quorteam.vspboost.ru/1oRtg1/QuorVPN",
    "https://pozor.bond/sub/free-sub-forza-obxod",
    # РКП
    "https://gidroksi.fun/black-list",
    "https://hub.mos.ru/rkp/sub-roskompozor/raw/main/bl",
    # Кота
    "https://hub.mos.ru/akelladejavu/bunker/-/raw/main/BLACK_LIST.txt",
    "https://hub.mos.ru/akelladejavu/bunker/-/raw/main/BEST_LIST.txt",
    # Mifa
    "https://mifa.world/sage",
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
# НАСТРОЙКИ  (режим «МНОГО КОНФИГОВ», но проверка усилена)
# ============================================================

TARGET_COUNT = 1500        # сколько конфигов взять в итоге (не считая закреплённых); 0 = без лимита
EARLY_STOP_MULT = 0        # 0 = проверять ВСЕ (ранней остановки нет)

MAX_PER_COUNTRY = 0        # 0 = без ограничения на страну

MAX_PING_MS = 5000         # отсечка по итоговому баллу (пинг + вклад скорости)
GOOD_PING_MS = 300         # «быстрый» сервер (🎃 в названии); ≤3× — 👻, дальше — 🦇

# --- Хеллоуин ---
# True — всегда, False — никогда, "auto" — только с 25 октября по 2 ноября
# Авто-режим ВЫКЛЮЧЕН: переименование включено всегда.
HALLOWEEN = auto

# --- реальный пинг ---
CHECK_ROUNDS = 3           # раундов по всем TEST_URLS; 1-й «холодный», остальные считаются в пинг

# --- гео выходного IP: страна — Cloudflare trace (через сам прокси), город — ipwho/ip-api ---
GEO_URLS = (
    "https://ipwho.is/?lang=ru",
    "http://ip-api.com/json/?fields=status,countryCode,city,query&lang=ru",
)
EXIT_GEO = {}              # config -> (country_code, geo_name, exit_ip)

MAX_TCP_PING_MS = 2500     # TCP-пинг выше этого (или нет ответа) — в ядро не идёт
TCP_CONCURRENCY = 300      # одновременных TCP-проверок

# --- Скачивание подписок ---
FETCH_TIMEOUT = 25.0
FETCH_RETRIES = 3
FETCH_HEADERS_LIST = [     # User-Agent меняется от попытки к попытке
    {"User-Agent": "v2rayN/6.42"},
    {"User-Agent": "Happ/7.0.0"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64;)"},
]

CONCURRENCY = 40           # одновременных процессов ядра (осторожно с RAM раннера: ~30-50 МБ на процесс)
XRAY_STARTUP_TIMEOUT = 6.0 # сек: максимум ждём, пока ядро откроет локальный порт
XRAY_TEST_TIMEOUT = 12.0   # сек на сессию / один запрос через прокси
XRAY_BINARY = "xray"       # должен быть в PATH (см. workflow)

# --- Hy2 (проверяется через sing-box, т.к. это UDP/QUIC) ---
CHECK_HY2 = True           # False — не проверять hy2 вообще
SINGBOX_BINARY = "sing-box"  # нужна версия 1.11+; если не найден — hy2 просто пропускается

TEST_URLS = [
    "https://cp.cloudflare.com/generate_204",
    "https://www.gstatic.com/generate_204",
]

# --- Усиленная проверка (каждый пункт можно ослабить/отключить) ---
IDLE_PAUSE = 2.0            # пауза перед повторным запросом по тому же соединению (keep-alive)
BURST_PARALLEL = 6          # параллельных запросов на новых соединениях
BURST_MAX_FAILS = 1         # сколько из них можно провалить

DOWNLOAD_URLS = [           # достаточно, чтобы прошёл ХОТЯ БЫ ОДИН
    "https://speed.cloudflare.com/__down?bytes=1000000",
    "https://proof.ovh.net/files/1Mb.dat",
]
DOWNLOAD_BYTES = 1_000_000
DOWNLOAD_TIMEOUT = 15.0
REQUIRE_DOWNLOAD = True     # False — если раннер не достаёт до DOWNLOAD_URLS
DOWNLOAD_MAX_MS = 10000     # 1 МБ дольше этого — слишком медленно
SPEED_WEIGHT = 0.05         # вклад времени загрузки/отдачи в итоговый балл

UPLOAD_URL = "https://speed.cloudflare.com/__up"
UPLOAD_BYTES = 256 * 1024
UPLOAD_TIMEOUT = 15.0
UPLOAD_MAX_MS = 8000
REQUIRE_UPLOAD = True       # ловит «полусломанные» туннели (вниз идёт, вверх нет)

# Доступ к заблокированным сайтам. В миксере есть белые списки, которые
# их не открывают, поэтому по умолчанию 0 (выкл). Для чистой ЧС-подписки поставь 2.
BLOCKED_URLS = [
    "https://www.youtube.com/generate_204",
    "https://www.tiktok.com/",
    "https://api.telegram.org/",
]
MIN_BLOCKED_OK = 0

MAX_JITTER = 3.0            # макс/мин пинг в тёплых раундах (+100 мс запаса)
REQUIRE_STABLE_EXIT_IP = True   # выходной IP не должен «плавать» между запросами

# Реальный выходной IP: IP-эхо сервисы + Cloudflare trace (страна и подтверждение IP)
IP_ECHO_URLS = [
    "https://api.ipify.org",
    "https://icanhazip.com",
    "https://ifconfig.me/ip",
]
CF_TRACE_URL = "https://www.cloudflare.com/cdn-cgi/trace"
REQUIRE_EXIT_IP = True      # не получили выходной IP (ни от эха, ни от trace) или он = нашему → нерабочий
REQUIRE_EXIT_COUNTRY = False  # True — отбрасывать конфиги, у которых не определилась страна выхода

# Выходы в этих странах отбрасываются. Пример: {"RU", "BY"}. Пусто = не фильтровать.
EXCLUDE_EXIT_COUNTRIES = set()

# Дубли ДО проверки: домен и его IP, одинаковые uuid/пароль/транспорт = один конфиг.
DEDUPE_RESOLVED = True

# Дубли ПОСЛЕ проверки (лучшие по баллу остаются). Режим «много конфигов»: всё выкл./мягко.
DEDUPE_BY_IP_PORT = False   # True — один конфиг на ip:порт (жёстко, режет много)
DEDUPE_BY_EXIT_IP = False   # True — один конфиг на выходной IP (= MAX_PER_EXIT_IP = 1)
MAX_PER_ENDPOINT = 3        # не больше N конфигов на один ip:порт (разные uuid); 0 = без лимита
MAX_PER_EXIT_IP = 0         # не больше N на один выходной IP; 0 = без лимита
MAX_PER_SUBNET24 = 0        # не больше N на одну подсеть /24 (IPv4); 0 = без лимита

# Повторная проверка лучших отдельным запуском ядра: отсекает «мигающие» серверы
CONFIRM_BEST = True
CONFIRM_SPARE = 20          # лишние кандидаты с запасом на выбывших
CONFIRM_CONCURRENCY = 20

PROGRESS_EVERY = 100       # как часто писать прогресс (раз в N конфигов)
BASE_LOCAL_PORT = 21000

# Каскады: вход и выход в разных странах -> в конце названия «{флаг входа}Каскад»
DETECT_CASCADE = True

OUTPUT_FILE = Path("output/sub.txt")

PROTOCOLS = (
    "vless://", "vmess://", "trojan://", "ss://",
    "ssr://", "hysteria2://", "hy2://", "tuic://",
)

XRAY_SUPPORTED = ("vless://", "vmess://", "trojan://", "ss://")
HY2_SCHEMES = ("hy2://", "hysteria2://")

_my_ip = None
_exit_ip = {}               # config -> выходной IP
_fail = Counter()           # причина отказа -> сколько конфигов


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
# ХЕЛЛОУИН
# Имя конфига: «{флаг} Страна — Город {тег} [{флаг входа}Каскад]»
# Флаг остаётся первым (клиенты берут из него значок), тег скорости — в конце:
#   🎃 быстрый (≤ GOOD_PING_MS), 👻 нормальный (≤ 3×), 🦇 медленный.
# ============================================================

HALLOWEEN_ANNOUNCE = "🎃 Телеграм канал: @PizMod 👻\n🦇Автообновление раз в 6 часов🕷"


def halloween_on():
    if HALLOWEEN is True:
        return True
    if HALLOWEEN is False:
        return False
    t = datetime.date.today()  # "auto"
    return (t.month == 10 and t.day >= 25) or (t.month == 11 and t.day <= 2)


def spooky_tag(score):
    if score <= GOOD_PING_MS:
        return "🎃"
    if score <= GOOD_PING_MS * 3:
        return "👻"
    return "🦇"


def halloween_header(lines):
    """Подменяет заголовок подписки (название и анонс) на хеллоуинские."""
    out = []
    for line in lines:
        if line.startswith("#profile-title:"):
            title = line.replace("🤯", "🎃")
            if "🎃" not in title:
                title = title.rstrip() + "🎃"
            out.append(title)
        elif line.startswith("#announce:"):
            enc = base64.b64encode(HALLOWEEN_ANNOUNCE.encode("utf-8")).decode("ascii")
            out.append(f"#announce: base64: {enc}")
        else:
            out.append(line)
    return out


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
        if scheme == "hysteria2":
            scheme = "hy2"  # один и тот же протокол
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
# РАЗБОР host:port (с поддержкой IPv6 и списков портов)
# ============================================================

def _split_hostport(hostport):
    """'host:443' -> ('host', '443'); '[::1]:443' -> ('::1', '443');
    'host:443,20000-30000' -> ('host', '443,20000-30000')."""
    hostport = hostport.strip().rstrip("/")
    if hostport.startswith("["):
        host, _, rest = hostport[1:].partition("]")
        return host, rest.lstrip(":")
    if ":" not in hostport:
        return hostport, ""
    host, _, ports = hostport.rpartition(":")
    return host, ports


def _parse_ports(ports):
    """Возвращает (основной_порт | None, [диапазоны 'a:b'])."""
    single, ranges = None, []
    for p in re.split(r"[,;]", ports or ""):
        p = p.strip()
        if not p:
            continue
        if p.isdigit():
            if single is None:
                single = int(p)
        elif re.fullmatch(r"\d+[-:]\d+", p):
            a, b = re.split(r"[-:]", p)
            ranges.append(f"{a}:{b}")
    return single, ranges


# ============================================================
# HY2: разбор URI (для sing-box)
# ============================================================

def split_hy2(line):
    """Возвращает (auth, host, ports_str, params) или None."""
    try:
        body = line.split("://", 1)[1].split("#", 1)[0]
        main, _, query = body.partition("?")
        netloc = main.split("/", 1)[0]
        userinfo, _, hostport = netloc.rpartition("@")
        host, ports = _split_hostport(hostport)
        if not host:
            return None
        params = {k.lower(): v[0]
                  for k, v in parse_qs(query, keep_blank_values=True).items() if v}
        return unquote(userinfo), host, ports, params
    except Exception:
        return None


def parse_hy2(line):
    """Outbound для sing-box или None."""
    try:
        parts = split_hy2(line)
        if not parts:
            return None
        auth, host, ports, params = parts

        single, ranges = _parse_ports(ports)
        mport = first(params, "mport")
        if mport:
            s2, r2 = _parse_ports(mport)
            ranges += r2
            single = single or s2
        if not single and ranges:
            single = int(ranges[0].split(":")[0])
        if not (auth and host and single):
            return None

        sni = first(params, "sni", "peer") or host
        insecure = str(first(params, "insecure", "allowinsecure") or "0").lower() in ("1", "true", "yes")
        if first(params, "pinsha256"):
            insecure = True

        alpn = first(params, "alpn")
        tls = {
            "enabled": True,
            "server_name": sni,
            "insecure": insecure,
            "alpn": [a for a in unquote(alpn).split(",") if a] if alpn else ["h3"],
        }

        outbound = {
            "type": "hysteria2",
            "tag": "proxy",
            "server": host,
            "server_port": single,
            "password": auth,
            "tls": tls,
        }

        if ranges:  # port hopping
            outbound["server_ports"] = ranges
            hop = first(params, "hop_interval", "hopinterval")
            if hop and str(hop).isdigit():
                outbound["hop_interval"] = f"{hop}s"

        if (first(params, "obfs") or "").lower() == "salamander":
            obfs_pw = first(params, "obfs-password", "obfs_password")
            if not obfs_pw:
                return None
            outbound["obfs"] = {"type": "salamander", "password": obfs_pw}

        return outbound
    except Exception:
        return None


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

    if line.startswith(HY2_SCHEMES):
        parts = split_hy2(line)
        if not parts:
            return None
        _, host, ports, params = parts
        single, ranges = _parse_ports(ports)
        if not single:
            _, r2 = _parse_ports(first(params, "mport") or "")
            if r2:
                single = int(r2[0].split(":")[0])
        return (host, single) if (host and single) else None

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
# DNS (асинхронно, с кэшем)
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
# ============================================================

def build_stream_settings(params, default_host, default_security="none"):
    network = (first(params, "type", "network", "net") or "tcp").lower()
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
    """Shadowsocks (SIP002, без base64, старый формат, IPv6). SS с plugin пропускаем."""
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


def build_core_config(line, port):
    """Выбирает ядро и строит конфиг с SOCKS-входом на 127.0.0.1:port.
    Возвращает (бинарник, конфиг) или None."""
    if line.startswith(HY2_SCHEMES):
        outbound = parse_hy2(line)
        if not outbound:
            return None
        return SINGBOX_BINARY, {
            "log": {"disabled": True},
            "inbounds": [{
                "type": "socks", "tag": "in",
                "listen": "127.0.0.1", "listen_port": port,
            }],
            "outbounds": [outbound],
        }

    outbound = build_outbound(line)
    if not outbound:
        return None
    return XRAY_BINARY, {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "listen": "127.0.0.1",
            "port": port,
            "protocol": "socks",
            "settings": {"udp": False},
        }],
        "outbounds": [outbound],
    }


# ============================================================
# ПУЛ ЛОКАЛЬНЫХ ПОРТОВ
# ============================================================

_port_counter = itertools.count(BASE_LOCAL_PORT)
_port_pool = asyncio.Queue()


def init_port_pool(n):
    for _ in range(n):
        _port_pool.put_nowait(next(_port_counter))


# ============================================================
# БЫСТРАЯ TCP-ПРОВЕРКА (до ядра; к hy2 не применяется — он на UDP)
# ============================================================

async def tcp_ping(line):
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
# ОЖИДАНИЕ ЛОКАЛЬНОГО ПОРТА ЯДРА
# ============================================================

async def wait_local_port(proc, port, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.returncode is not None:
            return False  # ядро упало — конфиг битый
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
# ЗАПУСК ЯДРА (xray или sing-box) ДЛЯ ОДНОГО КОНФИГА
# ============================================================

@asynccontextmanager
async def running_core(line):
    port = await _port_pool.get()
    proc = None
    tmp_path = None
    try:
        spec = build_core_config(line, port)
        if not spec:
            yield None
            return
        binary, cfg = spec

        fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="core_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        proc = await asyncio.create_subprocess_exec(
            binary, "run", "-c", tmp_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        ok = await wait_local_port(proc, port, XRAY_STARTUP_TIMEOUT)
        yield port if ok else None
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
# IP / TRACE / ГЕО ЧЕРЕЗ ПРОКСИ
# ============================================================

async def fetch_ip(session, timeout=8.0):
    t = aiohttp.ClientTimeout(total=timeout)
    for url in IP_ECHO_URLS:
        try:
            async with session.get(url, timeout=t) as resp:
                if resp.status != 200:
                    continue
                text = (await resp.text()).strip()
            ipaddress.ip_address(text)
            return text
        except Exception:
            continue
    return None


async def fetch_trace(session, timeout=8.0):
    """Cloudflare trace: (ip, страна) или None."""
    try:
        t = aiohttp.ClientTimeout(total=timeout)
        async with session.get(CF_TRACE_URL, timeout=t) as resp:
            if resp.status != 200:
                return None
            text = await resp.text()
        d = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
        ip = (d.get("ip") or "").strip()
        ipaddress.ip_address(ip)
        loc = (d.get("loc") or "").strip().upper()
        if not (len(loc) == 2 and loc.isalpha()) or loc == "XX":
            loc = ""
        return ip, loc
    except Exception:
        return None


async def fetch_exit_geo(session):
    """Гео через прокси-сессию: (country_code, city, ip) или None."""
    for url in GEO_URLS:
        try:
            async with session.get(url, ssl=False,
                                   timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status != 200:
                    continue
                d = await r.json(content_type=None)
                if d.get("success") is True or d.get("status") == "success":
                    cc = d.get("country_code") or d.get("countryCode")
                    if cc:
                        return cc.upper(), d.get("city"), d.get("ip") or d.get("query")
        except Exception:
            continue
    return None


def _same_family_diff(a, b):
    """True, если оба — IP одной версии и они РАЗНЫЕ."""
    try:
        ia, ib = ipaddress.ip_address(a), ipaddress.ip_address(b)
    except Exception:
        return False
    return ia.version == ib.version and ia != ib


# ============================================================
# ОДИН ТЕСТОВЫЙ ЗАПРОС: бросает исключение при любой ошибке
# ============================================================

async def _fetch_ok(session, url, min_bytes=0, timeout=None, ok_status=(200, 204)):
    start = time.monotonic()
    kw = {"timeout": aiohttp.ClientTimeout(total=timeout)} if timeout else {}
    async with session.get(url, **kw) as resp:
        if resp.status not in ok_status:
            raise ValueError(f"status {resp.status}")
        body = await resp.read()
    if resp.status == 204 and body:
        raise ValueError("204 с телом (подмена ответа)")
    if len(body) < min_bytes:
        raise ValueError("short body")
    return (time.monotonic() - start) * 1000


def _reject(reason):
    _fail[reason] += 1
    return None


# ============================================================
# РЕАЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ ЯДРО (xray / sing-box) — возвращает балл (мс) или None
# От дешёвых проверок к дорогим:
#   1) все тестовые URL во всех раундах, SSL проверяется, 204 без тела;
#   2) пауза и повтор по тому же соединению (keep-alive);
#   3) выходной IP (эхо + Cloudflare trace должны совпадать), страна выхода, город;
#   4) заблокированные сайты (если MIN_BLOCKED_OK > 0);
#   5) параллельный залп на новых соединениях;
#   6) скачивание ~1 МБ и отдача (upload);
#   7) выходной IP не «плавает», разброс пинга небольшой.
# Балл = медиана пинга в тёплых раундах + вклад времени загрузки и отдачи.
# ============================================================

async def _probe(line, port):
    connector = aiohttp_socks.ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
    timeout = aiohttp.ClientTimeout(total=XRAY_TEST_TIMEOUT)

    latencies = []
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for rnd in range(CHECK_ROUNDS):
                for url in TEST_URLS:
                    ms = await _fetch_ok(session, url)   # ssl-проверка ВКЛЮЧЕНА
                    if rnd > 0:
                        latencies.append(ms)

            await asyncio.sleep(IDLE_PAUSE)
            for url in TEST_URLS:
                await _fetch_ok(session, url)
    except Exception:
        return _reject("тестовые URL / keep-alive")

    connector_b = aiohttp_socks.ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
    exit_ip = None
    code = None
    async with aiohttp.ClientSession(connector=connector_b, timeout=timeout) as session:
        echo_ip = await fetch_ip(session, XRAY_TEST_TIMEOUT)
        tr = await fetch_trace(session, XRAY_TEST_TIMEOUT)
        t_ip, t_loc = tr if tr else (None, "")

        exit_ip = echo_ip or t_ip
        if REQUIRE_EXIT_IP and (not exit_ip or (_my_ip and exit_ip == _my_ip)):
            return _reject("нет выходного IP / совпал с моим")
        if REQUIRE_STABLE_EXIT_IP and echo_ip and t_ip and _same_family_diff(echo_ip, t_ip):
            return _reject("выходной IP «плавает»")

        if t_loc:
            if t_loc in EXCLUDE_EXIT_COUNTRIES:
                return _reject("выход в исключённой стране")
            code = t_loc

        # город (и страна, если trace не ответил) — через ту же прокси-сессию
        geo = await fetch_exit_geo(session)
        city = None
        if geo:
            g_cc, g_city, g_ip = geo
            if not code:
                code = g_cc
                if code in EXCLUDE_EXIT_COUNTRIES:
                    return _reject("выход в исключённой стране")
            if g_cc == code:
                city = g_city  # город берём, только если страна совпала
            exit_ip = exit_ip or g_ip

        if REQUIRE_EXIT_COUNTRY and not code:
            return _reject("страна выхода не определена")

        if exit_ip:
            _exit_ip[line] = exit_ip
        if code:
            EXIT_GEO[line] = (code, make_geo_name(code, city), exit_ip)

        if BLOCKED_URLS and MIN_BLOCKED_OK:
            res_b = await asyncio.gather(
                *(_fetch_ok(session, u, timeout=10, ok_status=range(200, 400))
                  for u in BLOCKED_URLS),
                return_exceptions=True,
            )
            if sum(not isinstance(r, Exception) for r in res_b) < MIN_BLOCKED_OK:
                return _reject("заблокированные сайты недоступны")

    dl_ms = None
    up_ms = None
    conn2 = aiohttp_socks.ProxyConnector.from_url(
        f"socks5://127.0.0.1:{port}", force_close=True
    )
    async with aiohttp.ClientSession(connector=conn2, timeout=timeout) as s2:
        urls = [TEST_URLS[i % len(TEST_URLS)] for i in range(BURST_PARALLEL)]
        res = await asyncio.gather(*(_fetch_ok(s2, u) for u in urls),
                                   return_exceptions=True)
        if sum(isinstance(r, Exception) for r in res) > BURST_MAX_FAILS:
            return _reject("параллельные запросы (залп)")

        if DOWNLOAD_URLS:
            for url in DOWNLOAD_URLS:
                try:
                    dl_ms = await _fetch_ok(s2, url, DOWNLOAD_BYTES * 0.9, DOWNLOAD_TIMEOUT)
                    break
                except Exception:
                    continue
            if REQUIRE_DOWNLOAD and dl_ms is None:
                return _reject("скачивание не прошло")
            if REQUIRE_DOWNLOAD and dl_ms > DOWNLOAD_MAX_MS:
                return _reject("слишком медленная загрузка")

        if UPLOAD_URL:
            try:
                start = time.monotonic()
                async with s2.post(
                    UPLOAD_URL, data=b"0" * UPLOAD_BYTES,
                    timeout=aiohttp.ClientTimeout(total=UPLOAD_TIMEOUT),
                ) as r:
                    await r.read()
                    if r.status in (200, 204):
                        up_ms = (time.monotonic() - start) * 1000
            except Exception:
                up_ms = None
            if REQUIRE_UPLOAD and (up_ms is None or up_ms > UPLOAD_MAX_MS):
                return _reject("отдача (upload) не прошла / медленная")

        if REQUIRE_STABLE_EXIT_IP and exit_ip:
            ip2 = await fetch_ip(s2, XRAY_TEST_TIMEOUT)
            if ip2 and _same_family_diff(exit_ip, ip2):
                return _reject("выходной IP «плавает»")

    if not latencies:
        return _reject("нет замеров пинга")
    if max(latencies) > MAX_JITTER * min(latencies) + 100:
        return _reject("нестабильный пинг (джиттер)")
    return statistics.median(latencies) + ((dl_ms or 0) + (up_ms or 0)) * SPEED_WEIGHT


async def real_check(line):
    try:
        async with running_core(line) as port:
            if port is None:
                return _reject("ядро не запустилось / конфиг не разобран")
            return await _probe(line, port)
    except Exception:
        return _reject("прочая ошибка")


# ============================================================
# ГЕО ВХОДА (сервера из конфига) — пачками по 100 IP через ip-api.com/batch
# Нужно для каскадов и как запасная страна, если гео через прокси не ответило.
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
# СКАЧИВАНИЕ ПОДПИСОК
# ============================================================

def short_name(url):
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
    """Возвращает (working, failed): working — [(config, score_ms)], failed — нерабочие."""
    semaphore = asyncio.Semaphore(CONCURRENCY)
    working = []
    failed = []
    stop_at = TARGET_COUNT * EARLY_STOP_MULT if (EARLY_STOP_MULT and TARGET_COUNT) else None
    stop_event = asyncio.Event()
    done = 0
    total = len(candidates)

    async def worker(config):
        nonlocal done
        async with semaphore:
            if stop_event.is_set():
                return
            try:
                latency = await real_check(config)
            except Exception:
                latency = None
            done += 1
            if latency is not None and latency <= MAX_PING_MS:
                working.append((config, latency))
                if stop_at and len(working) >= stop_at and not stop_event.is_set():
                    stop_event.set()
                    print(f"    проверено {done}/{total} ✓{len(working)} — хватит, стоп")
                    return
            else:
                if latency is not None:
                    _reject("итоговый балл выше MAX_PING_MS")
                failed.append(config)
            if done % PROGRESS_EVERY == 0:
                print(f"    проверено {done}/{total} ✓{len(working)}")

    await asyncio.gather(*(worker(c) for c in candidates))
    return working, failed


# ============================================================
# ДУБЛИ ПО РЕАЛЬНОМУ IP:ПОРТ / ВЫХОДНОМУ IP (по флагам, по умолчанию выкл.)
# ============================================================

async def dedupe_by_ip(items):
    if not (DEDUPE_BY_IP_PORT or DEDUPE_BY_EXIT_IP):
        return items

    seen = set()
    hosts = {get_host_port(c)[0] for c, _ in items if get_host_port(c)}
    await asyncio.gather(*(resolve_ip(h) for h in hosts))

    result = []
    for config, latency in items:
        keys = []
        hp = get_host_port(config)
        if DEDUPE_BY_IP_PORT and hp:
            keys.append(((_dns_cache.get(hp[0]) or hp[0]), hp[1]))
        if DEDUPE_BY_EXIT_IP and config in _exit_ip:
            keys.append(("exit", _exit_ip[config]))
        if any(k in seen for k in keys):
            continue
        seen.update(keys)
        result.append((config, latency))
    return result


# ============================================================
# ПОВТОРНАЯ ПРОВЕРКА ЛУЧШИХ (отдельным запуском ядра)
# ============================================================

async def confirm_best(items, want):
    confirmed = []
    idx = 0
    semaphore = asyncio.Semaphore(CONFIRM_CONCURRENCY)

    async def worker(config, first_latency):
        async with semaphore:
            try:
                latency = await real_check(config)
            except Exception:
                latency = None
        if latency is not None and latency <= MAX_PING_MS:
            confirmed.append((config, (first_latency + latency) / 2))

    while idx < len(items) and len(confirmed) < want:
        need = want - len(confirmed)
        chunk = items[idx: idx + need + CONFIRM_SPARE]
        idx += len(chunk)
        await asyncio.gather(*(worker(c, l) for c, l in chunk))
        print(f"    подтверждено {len(confirmed)}/{want} (просмотрено {idx}/{len(items)})")

    confirmed.sort(key=lambda x: x[1])
    return confirmed


def interleave(a, b):
    """Чередует два списка: a1, b1, a2, b2, ..."""
    return [x for pair in itertools.zip_longest(a, b) for x in pair if x is not None]


# ============================================================
# MAIN
# ============================================================

async def main():
    global _my_ip

    init_port_pool(CONCURRENCY)

    spooky = halloween_on()
    if spooky:
        print("[i] 🎃 Хеллоуин-режим: названия с тегами скорости")

    hy2_enabled = CHECK_HY2 and shutil.which(SINGBOX_BINARY) is not None
    if CHECK_HY2 and not hy2_enabled:
        print(f"[!] {SINGBOX_BINARY} не найден в PATH — hy2 проверяться не будет")

    async with aiohttp.ClientSession() as session:
        # наш реальный IP (без прокси) — для проверки утечки
        try:
            _my_ip = await asyncio.wait_for(fetch_ip(session), 20)
        except Exception:
            _my_ip = None
        print(f"[i] Мой IP: {_my_ip or 'не определён (проверка совпадения с моим IP отключена)'}")

        # ---------- 1. скачиваем ВСЕ подписки ----------
        print("[i] Скачиваю подписки...")
        results = await asyncio.gather(*(fetch_source(session, u) for u in SOURCES),
                                       return_exceptions=True)

        all_configs = []
        source_of = {}
        for i, r in enumerate(results, 1):
            if isinstance(r, tuple):
                url, cfgs = r
                for c in cfgs:
                    source_of.setdefault(dedupe_key(c), url)
                all_configs.extend(cfgs)
            else:
                print(f"[!] Источник #{i}: ошибка {str(r)[:60]}")

        print(f"[i] Всего скачано: {len(all_configs)}")

        # ---------- 2. удаляем дубликаты ----------
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

        xray_cands = [c for c in unique if c.startswith(XRAY_SUPPORTED)]
        hy2_cands = [c for c in unique if c.startswith(HY2_SCHEMES)] if hy2_enabled else []
        skipped = len(unique) - len(xray_cands) - len(hy2_cands)
        if skipped:
            what = "tuic/ssr" if hy2_enabled else "hy2/tuic/ssr"
            print(f"[i] Без проверки ({what}): {skipped}")

        if not xray_cands and not hy2_cands:
            print("[x] Нет конфигов для проверки.")
            return

        stats = {}

        def count(config, ok):
            s = stats.setdefault(source_of.get(dedupe_key(config)), [0, 0])
            s[0] += 1
            if not ok:
                s[1] += 1

        # ---------- 3. быстрая TCP-проверка (кроме hy2) ----------
        alive = []
        if xray_cands:
            print(f"\n[i] TCP: проверяю {len(xray_cands)}...")
            alive = await tcp_filter(xray_cands)
            alive_set = {c for c, _ in alive}
            for c in xray_cands:
                if c not in alive_set:
                    count(c, False)
            print(f"[i] TCP ок: {len(alive)} из {len(xray_cands)}")

        alive.sort(key=lambda x: x[1])
        tcp_ok = [c for c, _ in alive]

        if hy2_cands:
            print(f"[i] Hy2 (UDP, без TCP-проверки): {len(hy2_cands)}")

        candidates = interleave(tcp_ok, hy2_cands)
        if not candidates:
            print("[x] Ни один сервер не ответил по TCP.")
            return

        # ---------- 3.1 реальная проверка ----------
        print(f"\n[i] Реальная проверка: {len(candidates)} "
              f"(xray: {len(tcp_ok)}, hy2: {len(hy2_cands)})...")
        working, failed = await check_all(candidates)
        for c, _ in working:
            count(c, True)
        for c in failed:
            count(c, False)
        hy2_ok = sum(1 for c, _ in working if c.startswith(HY2_SCHEMES))
        print(f"[✓] Рабочих: {len(working)} (из них hy2: {hy2_ok})")

        if not working:
            print("[x] Рабочих конфигов нет.")
            if _fail:
                print("\n[i] Причины отказов:")
                for reason, n in _fail.most_common():
                    print(f"    {n:>5}  {reason}")
            return

        # ---------- 4. по баллу, (опц.) без дублей, повторная проверка ----------
        working.sort(key=lambda x: x[1])

        before = len(working)
        working = await dedupe_by_ip(working)
        if before != len(working):
            print(f"[i] Убрал дубли: {before - len(working)} (осталось {len(working)})")

        if CONFIRM_BEST:
            want = (TARGET_COUNT * (2 if MAX_PER_COUNTRY else 1)) if TARGET_COUNT else len(working)
            print("\n[i] Повторная проверка лучших...")
            selected = await confirm_best(working, want)
        else:
            selected = working
        if TARGET_COUNT and not MAX_PER_COUNTRY:
            selected = selected[:TARGET_COUNT]
        print(f"[i] После повторной проверки: {len(selected)}")

        if not selected:
            print("[x] После повторной проверки рабочих не осталось.")
            return

        # ---------- 5. гео ВХОДА: для каскадов и как запасная страна ----------
        entry_ip = {}
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
        items = []
        cascades = 0

        for config, latency in selected:
            if TARGET_COUNT and len(items) >= TARGET_COUNT:
                break

            info = EXIT_GEO.get(config)
            exit_ip = None
            if info:
                code, name, exit_ip = info
            else:
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

            if spooky:
                final_name += f" {spooky_tag(latency)}"

            # каскад: страна входа ≠ страна выхода (и вход не за CDN)
            if DETECT_CASCADE and info:
                ip = entry_ip.get(config)
                eg = entry_geo.get(ip)
                if eg and ip != exit_ip and eg[0] != code \
                        and not any(w in eg[1] for w in CDN_WORDS):
                    final_name += f" {get_country_flag(eg[0])}Каскад"
                    cascades += 1

            country_key = get_country_name(code) if code else "я_Неизвестно"
            items.append((country_key, latency, rename_config(config, final_name)))

            if len(items) % 100 == 0:
                print(f"    отобрано {len(items)}/{TARGET_COUNT or '∞'}")

        print(f"[i] Отобрано: {len(items)} (стран: {len(per_country)}, каскадов: {cascades})")

        items.sort(key=lambda x: (x[0], x[1]))
        renamed = [line for _, _, line in items]

    # ---------- 6. сохраняем ----------
    header = halloween_header(pinned) if spooky else pinned
    final_list = header + renamed

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

    # ---------- 7. почему отсеивались ----------
    if _fail:
        print("\n[i] Причины отказов (подсказка, какой порог ослабить):")
        for reason, n in _fail.most_common():
            print(f"    {n:>5}  {reason}")

    # ---------- 8. где больше всего нерабочих ----------
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
