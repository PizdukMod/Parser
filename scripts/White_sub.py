#!/usr/bin/env python3

import asyncio
import aiohttp
import aiohttp_socks
import base64
import hashlib
import ipaddress
import json
import socket
import statistics
import tempfile
import os
import itertools
import re
import time

from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote
from collections import defaultdict, Counter


# ============================================================
# ИСТОЧНИКИ — НЕ МЕНЯТЬ
# ============================================================

SOURCES = [
    "https://freevpnhappcluchi.duckdns.org/sub/lzjrpfi55soz18q9",
    "https://gitverse.ru/api/repos/SlavaKat/FreeProxyNova/raw/branch/master/🆓ProxyNova ❯ 🗽🕊✊ Ручной выбор Обход БС (Тест)",
    "https://gitverse.ru/api/repos/gidro/white/raw/branch/master/subscription.txt",
    "https://raw.githubusercontent.com/btsk161/Freeinternet_byMygalaru.github.io/refs/heads/main/premium.txt",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/best_keys.txt",
    "https://raw.githubusercontent.com/gazeta404/rain_vpn_bs/main/bs.txt",
    "https://raw.githubusercontent.com/flaafix/AetrisVPN-white-list-lite/refs/heads/main/AetrisVPN.txt",
    "https://hub.mos.ru/akelladejavu/bunker/-/raw/main/WHITE_LIST.txt",
    "https://hub.mos.ru/rkp/sub-roskompozor/raw/main/wl",
    "https://hub.mos.ru/kfwl/auto/raw/main/wl",
    "https://gitverse.ru/api/repos/Benss/Vless/raw/branch/master/new_file",
    "https://raw.githubusercontent.com/linspisokobhod/linspisokobhod.github.io/refs/heads/main/sub/LTE.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://bobrrvpn.neocities.org/whitelist.txt",
    "https://raw.githubusercontent.com/Buffetbarko/Universal-Proxy-Config-Parser-/main/whitelist_vpn.txt",
    "https://raw.githubusercontent.com/wlunlocker/vpn-configs/main/whitelist_all.txt",
]


# ============================================================
# ЧЁРНЫЙ СПИСОК ДОМЕНОВ
# Любой конфиг, где этот домен (или его поддомен) встречается в SNI / Host / адресе
# сервера / тексте строки, выбрасывается ОТОВСЮДУ: из источников, из закреплённых
# и из итогового файла.
# ============================================================

BLOCKED_DOMAINS = ()


# ============================================================
# ЗАКРЕПЛЁННЫЕ КОНФИГИ
# Добавляются в итоговую подписку БЕЗ проверки (пинг/живость не тестируются)
# и не удаляются последующими запусками скрипта — просто впиши сюда строку(и)
# ============================================================

PINNED_CONFIGS = [
    "#profile-title: PizdukVPN БС🏳",
    "#announce:base64: 8J+UpdCi0LXQu9C10LPRgNCw0Lwg0LrQsNC90LDQuzogQFBpem1vZPCfpboK8J+lsNCQ0LLRgtC+0L7QsdC90L7QstC70LXQvdC40LUg0YDQsNC3INCyIDYg0YfQsNGB0L7QsvCfmLE=",
    "#profile-web-page-url: https://t.me/PizMod",
    "#support-url: https://t.me/Harachok",
    "#profile-update-interval: 6",
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@qq.utiltools.site:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=qq.utiltools.site&fp=qq&security=reality&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&sid=#%F0%9F%91%89%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B7%F0%9F%87%BA%20%28telegram-only%29",
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@78.159.250.214:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=qq.utiltools.site&fp=firefox&security=reality&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&sid=00000000#%F0%9F%91%89%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B7%F0%9F%87%BA%20%D1%8D%D1%82%D0%BE%202%20%28telegram-only%29",
    # "vless://uuid@host:port?...#Моё имя",
]

# ============================================================
# НАСТРОЙКИ
# ============================================================

MAX_PER_SOURCE = 1000
MIN_PER_SOURCE = 1

# --- СТРОГИЙ РЕЖИМ БС + ГАРАНТИЯ КОЛИЧЕСТВА ---
# Каждому конфигу ставится уровень доверия к «это правда БС» (tier):
#   3 = РФ-вход (IP сервера в РФ) И (SNI из WL_DOMAINS ИЛИ ASN из ASN_WL_KEYWORDS ИЛИ это каскад РФ→мир)
#   2 = только SNI из WL_DOMAINS ИЛИ только IP в РФ
#   1 = БС только по названию
# За непройденную проверку данных и за нестабильность между запусками уровень снижается на 1.
# В файл идут сначала все конфиги с tier >= STRICT_MIN_TIER. Если их меньше MIN_TOTAL —
# добираются лучшие из остальных (сверху вниз по tier, потом по пингу), пока не наберётся MIN_TOTAL.
STRICT_WL = True            # False = брать всё, что похоже на БС (tier >= 1)
STRICT_MIN_TIER = 3         # порог «основной» части подписки
MIN_TOTAL = 30              # минимум конфигов в подписке (без закреплённых)
MAX_TOTAL = 0               # максимум конфигов в подписке (0 = без ограничения)
ONLY_XRAY_PROTOCOLS = True  # True = выкинуть hysteria2/tuic/ssr (их TCP-проверка ничего не доказывает, это UDP)

# ASN сервера (поле "as" из ip-api): хостеры/операторы РФ, чьи подсети чаще попадают в БС
ASN_WL_KEYWORDS = (
    "yandex", "vkontakte", "vk.com", "mail.ru", "sber", "selectel", "timeweb",
    "rostelecom", "mts", "megafon", "beeline", "vimpelcom", "tele2", "rtcomm",
)

# --- многократная проверка ---
PROBE_COUNT = 3             # сколько запросов через прокси
PROBE_MIN_OK = 2            # сколько из них должно пройти; пинг = медиана успешных
CHECK_ATTEMPTS = 2          # повтор, если xray просто не успел стартовать (не битый конфиг)

DATA_CHECK = True           # скачать небольшой файл через прокси: рукопожатие есть, а данные идут?
DATA_URLS = (
    "https://speed.cloudflare.com/__down?bytes=65536",
    "https://httpbin.org/bytes/65536",
)
DATA_MIN_BYTES = 32768
DATA_TIMEOUT = 6.0

# --- стабильность между запусками ---
STABILITY_ENABLED = True
STABILITY_RUNS = 3          # сколько последних запусков помнить
STABILITY_MIN = 2           # сколько из них должно быть успешными (включая текущий)
                            # новые конфиги без истории считаются стабильными
STATE_FILE = Path("output/state.json")   # закоммить его вместе с sub.txt, иначе история не сохранится

# --- «медленный резерв»: если после отбора меньше MIN_TOTAL, берём рабочие, но медленнее MAX_PING_MS ---
SLOW_FILL_MAX_PING_MS = 300

# --- распределение по странам ---
MAX_PER_COUNTRY = 0       # максимум ПРЯМЫХ конфигов на одну страну в итоговом файле (0 = без ограничения)
MIN_COUNTRIES_KEEP_ALL = 0 # если стран меньше N — лимит по стране не применяется (0 = выключено)

# --- КАСКАДЫ (вход в РФ -> выход в другой стране) ---
KEEP_CASCADES = True
CASCADE_ENTRY_COUNTRIES = ("RU",)
CASCADE_LABEL = "(вход {flag} {country})"   # {flag} {country} {code}
MAX_PING_CASCADE_MS = 350
MAX_CASCADES_PER_SOURCE = 40
MAX_CASCADES_PER_COUNTRY = 15

# --- удаление дубликатов ---
DEDUPE_BY_EXIT_IP = True

# --- РЕЖИМ БЕЛЫХ СПИСКОВ (БС) ---
WHITELIST_ONLY = True        # True = оставлять только конфиги белых списков
WL_TRUST_NAME = True         # БС по названию ("БС" / "белые списки" / "whitelist") — теперь только tier 1
WL_ACCEPT_RU_IP = True       # кандидатами считаются и серверы с IP в РФ (каскады РФ→мир); сами по себе — tier 2
WL_ONLY_RU_SERVERS = False   # True = только РЕАЛЬНЫЙ ВЫХОДНОЙ IP в РФ (выбросит все каскады)

WL_DOMAINS = (
    # Яндекс
    "yandex.ru", "yandex.com", "yandex.net", "ya.ru", "yastatic.net",
    "yandexcloud.net", "dzen.ru", "kinopoisk.ru", "rutube.ru",
    # VK / Mail.ru
    "vk.com", "vk.ru", "vkontakte.ru", "userapi.com", "vkuser.net", "vk-cdn.net",
    "mail.ru", "ok.ru", "my.com", "max.ru", "rambler.ru",
    # Маркетплейсы / сервисы
    "ozon.ru", "wildberries.ru", "wb.ru", "wbbasket.ru", "avito.ru", "2gis.ru", "2gis.com", "hh.ru", "cdek.ru",
    "x5.ru", "ads.x5.ru", "okko.tv", "dobro.ru", "maxtelemost.com",
    # Банки
    "sber.ru", "sberbank.ru", "sberdevices.ru", "tbank.ru", "tinkoff.ru",
    "vtb.ru", "alfabank.ru", "gazprombank.ru",
    # Госуслуги / операторы / прочее
    "gosuslugi.ru", "mos.ru", "nalog.gov.ru", "gov.ru", "rzd.ru",
    "mts.ru", "megafon.ru", "beeline.ru", "tele2.ru",
    "ria.ru", "lenta.ru", "rbc.ru", "kommersant.ru",
    # Домены авторов БС-конфигов (работают за счёт IP). "name.*" = любая зона (.homes, .net, .xyz ...)
    "sysopnova.art", "shprcdn.*", "portshaper.com", "cdnguard.org", "dismissaltree.net",
    "guardora.pro", "tunnelgate.org", "avroraservice.online", "centermass.net",
)

SHOW_SNI_STATS = True

# слово "white" само по себе больше не считается признаком БС
WL_NAME_REGEX = re.compile(
    r"(?<!\w)(бс|белы[йхе]\w*\s*спис\w*|white\s*-?list|whitelist)(?!\w)",
    re.IGNORECASE,
)

# --- СКОРОСТЬ ПРОВЕРКИ ---
CONNECT_TIMEOUT = 1.5
FETCH_TIMEOUT = 15.0

TCP_PRECHECK = True
TCP_PRECHECK_TIMEOUT = 2.5
TCP_PRECHECK_CONCURRENCY = 300

CONCURRENCY = 40          # одновременных xray-процессов (если раннер падает по RAM — снизь до 25)
XRAY_STARTUP_MAX = 3.0    # при повторной попытке удваивается
XRAY_TEST_TIMEOUT = 6.0   # сек на ОДИН тест-запрос через прокси
GEO_TIMEOUT = 3.5
XRAY_BINARY = "xray"
TEST_URL = "https://cp.cloudflare.com/generate_204"

GEO_URLS = (
    "https://ipwho.is/",
    "http://ip-api.com/json/?fields=status,countryCode,city,query",
)
EXIT_GEO = {}  # config -> (country_code, geo_name, exit_ip)

GEO_BATCH_INTERVAL = 4.3
IP_CC = {}                 # ip сервера -> код страны ("" если не определилась)
IP_ASN = {}                # ip сервера -> строка ASN ("AS13238 YANDEX LLC")

GEO_FALLBACK_RU = (
    ("sypexgeo", "https://api.sypexgeo.net/json/{ip}"),
    ("2ip.me",   "https://api.2ip.me/geo.json?ip={ip}"),
)
GEO_FALLBACK_WEST = (
    ("ipinfo.io", "https://ipinfo.io/{ip}/json"),
    ("ipapi.co",  "https://ipapi.co/{ip}/json/"),
    ("geojs.io",  "https://get.geojs.io/v1/ip/geo/{ip}.json"),
)
GEO_FALLBACK_TIMEOUT = 6.0

MAX_PING_MS = 120         # жёсткая отсечка для ПРЯМЫХ в основной части (медленнее — только в резерв)
GOOD_PING_MS = 50

BASE_LOCAL_PORT = 21000

OUTPUT_FILE = Path("output/sub.txt")

PROTOCOLS = (
    "vless://",
    "vmess://",
    "trojan://",
    "ss://",
    "ssr://",
    "hysteria2://",
    "hy2://",
    "tuic://",
)

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
    "NZ": "Новая Зеландия", "TW": "Тайвань", "EG": "Египет",
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

FLAG_RE = re.compile("[\U0001F1E6-\U0001F1FF]{2}")


def get_country_flag(country_code):
    if not country_code or len(country_code) != 2 or not country_code.isalpha():
        return "🌐"
    country_code = country_code.upper()
    return chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)


def flag_to_code(flag):
    """🇷🇺 -> 'RU'"""
    return "".join(chr(ord(ch) - 0x1F1E6 + 65) for ch in flag)


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
# Дубль = один и тот же сервер (протокол + хост + порт + uuid/пароль).
# ============================================================

_seen_keys = set()   # серверы закреплённых конфигов (источники их не дублируют)
_seen_lines = set()  # точные повторы строк между источниками (до проверки)


def dedupe_key(line):
    if line.startswith("vmess://"):
        data = b64decode_safe(line[len("vmess://"):])
        if data:
            try:
                o = json.loads(data)
                return ("vmess", str(o.get("add")).strip().lower(), str(o.get("port")), str(o.get("id")))
            except Exception:
                pass
        return (line,)

    scheme, _, rest = line.partition("://")
    scheme = scheme.lower()
    if scheme == "hysteria2":
        scheme = "hy2"
    netloc = re.split(r"[/?#]", rest, maxsplit=1)[0]
    userinfo, _, hostport = netloc.rpartition("@")
    return (scheme, userinfo, hostport.lower())


def exact_line_key(line):
    """Ключ точного повтора: строка без названия (#...)."""
    if line.startswith("vmess://"):
        return line
    return line.split("#", 1)[0]


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
# ОПРЕДЕЛЕНИЕ КОНФИГОВ БЕЛЫХ СПИСКОВ
# ============================================================

def config_name(line):
    if line.startswith("vmess://"):
        data = b64decode_safe(line[len("vmess://"):])
        try:
            return str(json.loads(data).get("ps", ""))
        except Exception:
            return ""
    if "#" in line:
        return unquote(line.split("#", 1)[1])
    return ""


def config_domains(line):
    raw = []
    if line.startswith("vmess://"):
        data = b64decode_safe(line[len("vmess://"):])
        try:
            obj = json.loads(data)
        except Exception:
            return set()
        raw = [obj.get("sni"), obj.get("host"), obj.get("add")]
    else:
        try:
            parsed = urlparse(line)
        except Exception:
            return set()
        params = query_params(parsed)
        raw = [params.get("sni"), params.get("servername"), params.get("host"), parsed.hostname]

    result = set()
    for value in raw:
        if not value:
            continue
        for part in unquote(str(value)).split(","):
            part = part.strip().strip(".").lower()
            if part:
                result.add(part)
    return result


def is_blocked(line):
    if not BLOCKED_DOMAINS:
        return False

    low = line.lower()
    low_decoded = unquote(low)
    if line.startswith("vmess://"):
        low_decoded += " " + (b64decode_safe(line[len("vmess://"):]) or "").lower()

    for blocked in BLOCKED_DOMAINS:
        blocked = blocked.lower()
        if blocked in low or blocked in low_decoded:
            return True

    for domain in config_domains(line):
        for blocked in BLOCKED_DOMAINS:
            blocked = blocked.lower()
            if domain == blocked or domain.endswith("." + blocked):
                return True
    return False


def get_sni(line):
    if line.startswith("vmess://"):
        data = b64decode_safe(line[len("vmess://"):])
        try:
            obj = json.loads(data)
            return (obj.get("sni") or obj.get("host") or obj.get("add") or "").split(",")[0].strip().lower()
        except Exception:
            return ""
    try:
        parsed = urlparse(line)
        params = query_params(parsed)
        value = params.get("sni") or params.get("servername") or params.get("host") or parsed.hostname or ""
        return unquote(value).split(",")[0].strip().lower()
    except Exception:
        return ""


def flag_code_from_name(line):
    match = FLAG_RE.search(config_name(line))
    if not match:
        return None
    return flag_to_code(match.group(0))


def print_sni_stats(configs):
    counter = Counter(get_sni(c) or "(пусто)" for c in configs)
    print("    SNI (топ-25):")
    for sni, count in counter.most_common(25):
        mark = "✓ БС" if domain_in_whitelist(sni) else "—"
        print(f"      {count:>4}  {sni:<40} {mark}")


# ============================================================
# ГЕО ВХОДА (IP сервера) + ASN: пакетно, с кэшем и соблюдением лимита ip-api
# ============================================================

_geo_lock = asyncio.Lock()
_last_batch = 0.0


async def ensure_ip_cc(session, hosts):
    """Заполняет IP_CC и IP_ASN для хостов. Уже известные IP повторно не запрашиваются."""
    global _last_batch

    hosts = [h for h in hosts if h]
    await asyncio.gather(*(resolve_ip(h) for h in hosts))

    ips = sorted({_dns_cache.get(h) for h in hosts if _dns_cache.get(h) and _dns_cache.get(h) not in IP_CC})

    for i in range(0, len(ips), 100):
        chunk = [ip for ip in ips[i:i + 100] if ip not in IP_CC]
        if not chunk:
            continue

        async with _geo_lock:
            for _ in range(3):
                wait = GEO_BATCH_INTERVAL - (time.monotonic() - _last_batch)
                if wait > 0:
                    await asyncio.sleep(wait)
                _last_batch = time.monotonic()

                try:
                    timeout = aiohttp.ClientTimeout(total=15.0)
                    async with session.post(
                        "http://ip-api.com/batch?fields=query,countryCode,as",
                        json=chunk, timeout=timeout,
                    ) as response:
                        if response.status == 200:
                            for item in await response.json(content_type=None):
                                if item.get("query"):
                                    IP_CC[item["query"]] = (item.get("countryCode") or "").upper()
                                    IP_ASN[item["query"]] = item.get("as") or ""
                            for ip in chunk:
                                IP_CC.setdefault(ip, "")
                            break
                        if response.status == 429:
                            await asyncio.sleep(15)
                            continue
                        break
                except Exception:
                    break


def entry_cc(config):
    """Страна IP самого сервера (вход) или None."""
    hp = get_host_port(config)
    if not hp:
        return None
    ip = _dns_cache.get(hp[0])
    if not ip:
        return None
    return IP_CC.get(ip) or None


def entry_asn_ok(config):
    hp = get_host_port(config)
    if not hp:
        return False
    ip = _dns_cache.get(hp[0])
    asn = (IP_ASN.get(ip) or "").lower() if ip else ""
    return bool(asn) and any(k in asn for k in ASN_WL_KEYWORDS)


def is_cascade(config):
    if not KEEP_CASCADES:
        return False
    info = EXIT_GEO.get(config)
    if not info or not info[0]:
        return False
    ent = entry_cc(config)
    if not ent or ent.upper() == info[0].upper():
        return False
    return (not CASCADE_ENTRY_COUNTRIES) or ent.upper() in CASCADE_ENTRY_COUNTRIES


def cascade_suffix(config):
    ent = entry_cc(config)
    return CASCADE_LABEL.format(flag=get_country_flag(ent), country=get_country_name(ent), code=ent or "")


def domain_in_whitelist(domain):
    for d in WL_DOMAINS:
        if d.endswith(".*"):
            base = re.escape(d[:-2])
            if re.search(rf"(^|\.){base}\.[a-z0-9-]+$", domain):
                return True
        elif domain == d or domain.endswith("." + d):
            return True
    return False


def is_whitelist_config(line):
    """Кандидат в БС по SNI/Host/адресу или по названию (без учёта IP)."""
    if not WHITELIST_ONLY:
        return True
    if WL_TRUST_NAME and WL_NAME_REGEX.search(config_name(line)):
        return True
    return any(domain_in_whitelist(d) for d in config_domains(line))


def wl_tier(config):
    """Уровень доверия «это настоящий БС»: 3 / 2 / 1 / 0 (см. описание настроек)."""
    if not WHITELIST_ONLY:
        return 3
    dom = any(domain_in_whitelist(d) for d in config_domains(config))
    name = bool(WL_TRUST_NAME and WL_NAME_REGEX.search(config_name(config)))
    ru = entry_cc(config) == "RU"
    if ru and (dom or entry_asn_ok(config) or is_cascade(config)):
        return 3
    if dom or ru:
        return 2
    if name:
        return 1
    return 0


# ============================================================
# ИСТОРИЯ СТАБИЛЬНОСТИ (state.json)
# ============================================================

STATE = {}      # хэш сервера -> [0/1, ...] последние запуски
RESULTS = {}    # config -> прошёл проверку в этом запуске
DATA_OK = {}    # config -> прошла ли проверка передачи данных
SLOW_POOL = []  # (config, latency): рабочие, но медленнее порогов основной части
SLOW_SET = set()


def state_key(config):
    raw = "|".join(map(str, dedupe_key(config)))
    return hashlib.md5(raw.encode("utf-8", errors="ignore")).hexdigest()[:12]


def load_state():
    if not STABILITY_ENABLED:
        return
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            STATE.update({k: v for k, v in data.items() if isinstance(v, list)})
            print(f"[i] История стабильности загружена: {len(STATE)} серверов")
    except Exception:
        print("[i] История стабильности не найдена — все конфиги считаются новыми")


def is_stable(config):
    if not STABILITY_ENABLED:
        return True
    prev = STATE.get(state_key(config), [])[-(STABILITY_RUNS - 1):] if STABILITY_RUNS > 1 else []
    runs = prev + [1]  # конфиг, дошедший до отбора, в этом запуске прошёл
    need = min(STABILITY_MIN, len(runs))
    return sum(runs) >= need


def save_state():
    if not STABILITY_ENABLED or not RESULTS:
        return
    by_key = {}
    for c, ok in RESULTS.items():
        k = state_key(c)
        by_key[k] = by_key.get(k, False) or ok
    new = {k: (STATE.get(k, []) + [1 if ok else 0])[-STABILITY_RUNS:] for k, ok in by_key.items()}
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(new, separators=(",", ":")), encoding="utf-8")
        print(f"[✓] История стабильности сохранена: {len(new)} серверов -> {STATE_FILE}")
    except Exception as e:
        print(f"[!] Не удалось сохранить историю: {e}")


def eff_tier(config):
    """Итоговый уровень: tier минус штрафы за провал проверки данных и нестабильность."""
    t = wl_tier(config)
    if DATA_CHECK and not DATA_OK.get(config, True):
        t -= 1
    if not is_stable(config):
        t -= 1
    return max(t, 0)


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
# РЕАЛЬНЫЙ ВЫХОДНОЙ IP: гео через сам прокси
# ============================================================

async def fetch_exit_geo(session):
    timeout = aiohttp.ClientTimeout(total=GEO_TIMEOUT)
    for url in GEO_URLS:
        try:
            async with session.get(url, ssl=False, timeout=timeout) as r:
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


async def data_check(session):
    """True, если через прокси реально скачивается файл (а не только проходит рукопожатие)."""
    timeout = aiohttp.ClientTimeout(total=DATA_TIMEOUT)
    for url in DATA_URLS:
        try:
            async with session.get(url, ssl=False, timeout=timeout) as r:
                if r.status != 200:
                    continue
                body = await r.read()
                if len(body) >= DATA_MIN_BYTES:
                    return True
        except Exception:
            continue
    return False


# ============================================================
# TCP-ПРЕДПРОВЕРКА И ОЖИДАНИЕ ПОРТА
# ============================================================

_tcp_sem = asyncio.Semaphore(TCP_PRECHECK_CONCURRENCY)
_UDP_NET_RE = re.compile(r"(type|net)=(kcp|mkcp|quic)", re.IGNORECASE)


async def tcp_check(host, port, timeout=None):
    timeout = timeout or CONNECT_TIMEOUT
    try:
        start = time.monotonic()
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        latency_ms = (time.monotonic() - start) * 1000
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return latency_ms
    except Exception:
        return None


async def tcp_precheck(config):
    if _UDP_NET_RE.search(config):
        return True
    hp = get_host_port(config)
    if not hp:
        return True
    async with _tcp_sem:
        return await tcp_check(hp[0], hp[1], TCP_PRECHECK_TIMEOUT) is not None


async def wait_port(proc, port, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.returncode is not None:
            return False
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.close()
            return True
        except OSError:
            await asyncio.sleep(0.05)
    return False


# ============================================================
# РЕАЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ XRAY
# Возвращает (пинг_мс | None, xray_не_успел_стартовать)
# ============================================================

async def xray_real_check(line, startup_max):
    outbound = build_outbound(line)
    if not outbound:
        return None, False

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

        if not await wait_port(proc, port, startup_max):
            # процесс жив, но порт не открылся = просто медленный старт (стоит повторить);
            # процесс уже завершился = конфиг битый
            return None, proc.returncode is None

        connector = aiohttp_socks.ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
        timeout = aiohttp.ClientTimeout(total=XRAY_TEST_TIMEOUT)

        try:
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # несколько запросов подряд в одной сессии: нужно PROBE_MIN_OK успешных из PROBE_COUNT
                lats = []
                fails = 0
                for _ in range(PROBE_COUNT):
                    t0 = time.monotonic()
                    try:
                        async with session.get(TEST_URL, ssl=False) as resp:
                            if resp.status in (200, 204):
                                await resp.read()
                                lats.append((time.monotonic() - t0) * 1000)
                            else:
                                fails += 1
                    except Exception:
                        fails += 1
                    if fails > PROBE_COUNT - PROBE_MIN_OK:
                        break

                if len(lats) < PROBE_MIN_OK:
                    return None, False

                latency_ms = statistics.median(lats)

                ping_cap = max(MAX_PING_MS, MAX_PING_CASCADE_MS if KEEP_CASCADES else 0, SLOW_FILL_MAX_PING_MS)
                if latency_ms <= ping_cap:
                    geo = await fetch_exit_geo(session)
                    if geo:
                        cc, city, exit_ip = geo
                        EXIT_GEO[line] = (cc, make_geo_name(cc, city), exit_ip)
                    if DATA_CHECK:
                        DATA_OK[line] = await data_check(session)
            return latency_ms, False
        except Exception:
            return None, False

    except Exception:
        return None, False

    finally:
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except Exception:
                pass
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        await _port_pool.put(port)


# ============================================================
# ФОЛБЭК TCP-ПРОВЕРКА (hysteria2 / tuic / ssr) — только если ONLY_XRAY_PROTOCOLS = False
# ============================================================

async def fallback_check(line):
    hp = get_host_port(line)
    if not hp:
        return None
    return await tcp_check(*hp)


async def check_config(line):
    if line.startswith(XRAY_SUPPORTED):
        for attempt in range(CHECK_ATTEMPTS):
            latency, slow_start = await xray_real_check(line, XRAY_STARTUP_MAX * (1 + attempt))
            if latency is not None:
                return latency
            if not slow_start:
                return None
            await asyncio.sleep(0.3)
        return None
    return await fallback_check(line)


# ============================================================
# GEO СЕРВЕРА (фолбэк для конфигов без выходного гео)
# ============================================================

async def get_server_geo(session, host):
    try:
        try:
            ip = socket.gethostbyname(host)
        except Exception:
            ip = host

        url = f"http://ip-api.com/json/{ip}?fields=status,countryCode,city"
        timeout = aiohttp.ClientTimeout(total=5.0)

        async with session.get(url, timeout=timeout) as response:
            if response.status != 200:
                return None, None
            data = await response.json(content_type=None)
            if data.get("status") != "success":
                return None, None
            country_code = data.get("countryCode")
            geo_name = make_geo_name(country_code, data.get("city"))
            return country_code, geo_name
    except Exception:
        return None, None


def parse_geo_json(data):
    if not isinstance(data, dict):
        return None

    country = data.get("country")
    code = None
    if isinstance(country, dict):
        code = country.get("iso")
    elif isinstance(country, str) and len(country) == 2:
        code = country
    code = code or data.get("country_code") or data.get("countryCode")

    if not (isinstance(code, str) and len(code) == 2 and code.isalpha()):
        return None

    city = data.get("city")
    if isinstance(city, dict):
        city = city.get("name_ru") or city.get("name_en")
    if not isinstance(city, str):
        city = None

    return code.upper(), city


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


async def fallback_geo(session, host):
    ip = await resolve_ip(host)
    if not ip:
        return None

    timeout = aiohttp.ClientTimeout(total=GEO_FALLBACK_TIMEOUT)

    for group, services in (("RU", GEO_FALLBACK_RU), ("WEST", GEO_FALLBACK_WEST)):
        for name, template in services:
            try:
                async with session.get(template.format(ip=ip), timeout=timeout) as response:
                    if response.status != 200:
                        continue
                    data = await response.json(content_type=None)
            except Exception:
                continue

            parsed = parse_geo_json(data)
            if parsed:
                code, city = parsed
                return code, make_geo_name(code, city), f"{group}:{name}"

    return None


# ============================================================
# FETCH
# ============================================================

async def fetch(session, url):
    try:
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
        async with session.get(url, timeout=timeout, allow_redirects=True) as response:
            response.raise_for_status()
            return await response.text(errors="ignore")
    except Exception as e:
        print("[!] Ошибка источника:")
        print(f"    {url}")
        print(f"    {e}")
        return None


# ============================================================
# PROCESS SOURCE
# ============================================================

async def process_source(session, url, semaphore):
    raw = await fetch(session, url)
    if not raw:
        return []

    configs = extract_lines(raw)

    before_block = len(configs)
    configs = [c for c in configs if not is_blocked(c)]
    blocked_count = before_block - len(configs)

    skipped_proto = 0
    if ONLY_XRAY_PROTOCOLS:
        before_proto = len(configs)
        configs = [c for c in configs if c.startswith(XRAY_SUPPORTED)]
        skipped_proto = before_proto - len(configs)

    total_found = len(configs)
    by_domain = []
    by_ru_ip = []

    if SHOW_SNI_STATS and configs:
        print()
        print(f"[i] SNI источника: {url}")
        print_sni_stats(configs)

    # кандидаты в БС: по SNI/названию и (опционально) по IP в РФ. Строгость решается позже, по tier.
    if WHITELIST_ONLY:
        by_domain = [c for c in configs if is_whitelist_config(c)]
        passed = set(by_domain)
        rest = [c for c in configs if c not in passed]

        geo_src = configs if WL_ACCEPT_RU_IP else by_domain
        hosts = set()
        for c in geo_src:
            hp = get_host_port(c)
            if hp:
                hosts.add(hp[0])
        await ensure_ip_cc(session, hosts)  # нужно и для tier (РФ-вход, ASN)

        if WL_ACCEPT_RU_IP:
            by_ru_ip = [c for c in rest if entry_cc(c) == "RU"]

        configs = by_domain + by_ru_ip

    print()
    print("[i] Источник:")
    print(f"    {url}")
    if blocked_count:
        print(f"    выброшено по чёрному списку: {blocked_count}")
    if skipped_proto:
        print(f"    пропущено не-xray протоколов (hy2/tuic/ssr): {skipped_proto}")
    if WHITELIST_ONLY:
        print(f"    найдено: {total_found}, кандидатов в БС: {len(configs)} "
              f"(по SNI/названию: {len(by_domain)}, по IP в РФ: {len(by_ru_ip)})")
    else:
        print(f"    найдено: {total_found}")

    if not configs:
        return []

    # до проверки убираем только ТОЧНЫЕ повторы и серверы закреплённых.
    # Разные варианты одного сервера (другой SNI/fp) проверяются все — дубли режутся после проверки, по лучшему.
    fresh = []
    for c in configs:
        if c.startswith(PROTOCOLS) and dedupe_key(c) in _seen_keys:
            continue
        k = exact_line_key(c)
        if k in _seen_lines:
            continue
        _seen_lines.add(k)
        fresh.append(c)
    if len(fresh) != len(configs):
        print(f"    повторов убрано до проверки: {len(configs) - len(fresh)}")
    configs = fresh
    if not configs:
        return []

    async def worker(config):
        try:
            if TCP_PRECHECK and config.startswith(XRAY_SUPPORTED):
                if not await tcp_precheck(config):
                    RESULTS[config] = False
                    return None
            async with semaphore:
                latency = await check_config(config)
                RESULTS[config] = latency is not None
                if latency is not None:
                    return (config, latency)
        except Exception:
            pass
        return None

    tasks = [asyncio.create_task(worker(c)) for c in configs]
    working = []

    try:
        for task in asyncio.as_completed(tasks):
            result = await task
            if result:
                config, latency = result
                working.append((config, latency))
                mark = "🔥" if latency <= GOOD_PING_MS else ("👍" if latency <= MAX_PING_MS else "🐌")
                exit_info = EXIT_GEO.get(config)
                exit_txt = f", выход {exit_info[2]} {exit_info[1]}" if exit_info else ""
                data_txt = ""
                if DATA_CHECK and config in DATA_OK:
                    data_txt = ", данные ✓" if DATA_OK[config] else ", данные ✗"
                print(f"    [✓] {mark} рабочий, пинг {latency:.0f} мс{exit_txt}{data_txt}")
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()

    if KEEP_CASCADES and working:
        hosts = set()
        for c, _ in working:
            hp = get_host_port(c)
            if hp:
                hosts.add(hp[0])
        await ensure_ip_cc(session, hosts)

    direct = [w for w in working if not is_cascade(w[0])]
    cascades = [w for w in working if is_cascade(w[0])]

    fast_enough = [c for c in direct if c[1] <= MAX_PING_MS]

    if len(fast_enough) < MIN_PER_SOURCE and len(direct) > len(fast_enough):
        print(f"    [!] Быстрых (<{MAX_PING_MS} мс) меньше {MIN_PER_SOURCE} — добираем из более медленных")
        direct.sort(key=lambda c: c[1])
        fast_enough = direct

    fast_enough.sort(key=lambda c: c[1])
    best = fast_enough[:MAX_PER_SOURCE]

    casc_ok = sorted((c for c in cascades if c[1] <= MAX_PING_CASCADE_MS), key=lambda c: c[1])
    best_casc = casc_ok[:MAX_CASCADES_PER_SOURCE]

    # всё рабочее, но не попавшее в основную часть, идёт в «медленный резерв»
    chosen = {c for c, _ in best} | {c for c, _ in best_casc}
    slow = [(c, l) for c, l in working if c not in chosen and l <= SLOW_FILL_MAX_PING_MS]
    SLOW_POOL.extend(slow)

    print(f"    [✓] рабочих всего: {len(working)} (прямых {len(direct)}, каскадов {len(cascades)}), "
          f"отобрано: прямых {len(best)}, каскадов {len(best_casc)}, в резерв: {len(slow)}")

    if len(best) + len(best_casc) < MIN_PER_SOURCE:
        print(f"    [!] Меньше {MIN_PER_SOURCE}")

    return best + best_casc


# ============================================================
# УДАЛЕНИЕ ДУБЛЕЙ ПО РЕАЛЬНОМУ IP:ПОРТ И ПО ВЫХОДНОМУ IP
# На входе список уже отсортирован «лучшие первыми» — из группы остаётся первый.
# ============================================================

async def dedupe_by_ip(items, taken=None):
    seen = set(taken or ())

    hosts = {get_host_port(c)[0] for c, _ in items if get_host_port(c)}
    await asyncio.gather(*(resolve_ip(h) for h in hosts))

    result = []
    for config, latency in items:
        keys = []
        hp = get_host_port(config)
        if hp:
            ip = _dns_cache.get(hp[0]) or hp[0]
            keys.append((ip, hp[1]))
        if DEDUPE_BY_EXIT_IP and not is_cascade(config):
            info = EXIT_GEO.get(config)
            if info and info[2]:
                keys.append(("exit", info[2]))
        if any(k in seen for k in keys):
            continue
        seen.update(keys)
        result.append((config, latency))
    return result


# ============================================================
# ОТБОР: строгая часть + добор до MIN_TOTAL
# ============================================================

def rank_key(entry):
    config, latency = entry
    return (-eff_tier(config), config in SLOW_SET, latency)


def select_final(pool):
    """pool уже отсортирован по rank_key. Возвращает список (config, latency)."""
    min_tier = STRICT_MIN_TIER if STRICT_WL else 1

    core = [e for e in pool if e[0] not in SLOW_SET and eff_tier(e[0]) >= min_tier]
    core_ids = {e[0] for e in core}
    rest = [e for e in pool if e[0] not in core_ids]

    selected = list(core)
    filled = 0
    if len(selected) < MIN_TOTAL:
        need = MIN_TOTAL - len(selected)
        add = rest[:need]
        selected += add
        filled = len(add)

    if MAX_TOTAL:
        selected = selected[:MAX_TOTAL]

    tiers = Counter(eff_tier(e[0]) for e in selected)
    print()
    print(f"[i] Отбор: основная часть (tier >= {min_tier}): {len(core)}, добрано до минимума {MIN_TOTAL}: {filled}, "
          f"итого: {len(selected)}")
    print("    по уровням: " + ", ".join(f"tier {t}: {n}" for t, n in sorted(tiers.items(), reverse=True)))
    slow_used = sum(1 for e in selected if e[0] in SLOW_SET)
    if slow_used:
        print(f"    из них медленнее {MAX_PING_MS} мс (резерв): {slow_used}")
    if len(selected) < MIN_TOTAL:
        print(f"    [!] Рабочих БС-кандидатов всего {len(selected)} — меньше желаемых {MIN_TOTAL}")
    return selected


# ============================================================
# РАСПРЕДЕЛЕНИЕ ПО СТРАНАМ
# ============================================================

def distribute_by_country(entries):
    by_group = defaultdict(list)
    for entry in entries:
        config, _, country_code, _ = entry
        by_group[(country_code or "??", is_cascade(config))].append(entry)

    n_countries = len({k[0] for k in by_group})

    kept = []
    stats = {}

    for key in sorted(by_group, key=lambda k: len(by_group[k]), reverse=True):
        country_code, cascade = key
        group = by_group[key]
        group.sort(key=lambda e: e[1])

        limit = MAX_CASCADES_PER_COUNTRY if cascade else MAX_PER_COUNTRY
        apply_limit = limit > 0
        if not cascade and MIN_COUNTRIES_KEEP_ALL and n_countries < MIN_COUNTRIES_KEEP_ALL:
            apply_limit = False

        selected = group[:limit] if apply_limit else group
        kept.extend(selected)

        stats[key] = {
            "total": len(group),
            "kept": len(selected),
            "name": get_country_name(country_code) if country_code != "??" else "Неизвестно",
        }

    return kept, stats


def print_country_distribution(stats):
    print()
    print("[i] Распределение по странам:")
    total_kept = 0
    for (country_code, cascade), info in sorted(stats.items(), key=lambda kv: kv[1]["kept"], reverse=True):
        flag = get_country_flag(country_code) if country_code != "??" else "🌐"
        total_kept += info["kept"]
        name = info["name"] + (" (каскады)" if cascade else "")
        if info["kept"] < info["total"]:
            print(f"    {flag} {name:<28} {info['kept']:>3} / {info['total']:>3} (обрезано лимитом)")
        else:
            print(f"    {flag} {name:<28} {info['kept']:>3}")
    print(f"    {'—' * 40}")
    print(f"    Итого групп: {len(stats)}, итого конфигов: {total_kept}")


# ============================================================
# MAIN
# ============================================================

async def main():
    load_state()
    init_port_pool(CONCURRENCY)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    pinned = [c.strip() for c in PINNED_CONFIGS if c.strip() and not is_blocked(c)]
    _seen_keys.update(dedupe_key(c) for c in pinned if c.startswith(PROTOCOLS))

    all_entries = []

    print("[i] Сбор конфигов...")

    async with aiohttp.ClientSession() as session:
        tasks = [process_source(session, url, semaphore) for url in SOURCES if url.strip()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for index, result in enumerate(results, 1):
            if isinstance(result, list):
                all_entries.extend(result)
            else:
                print(f"[!] Источник #{index} завершился с ошибкой: {result}")

        # основная часть + медленный резерв (резерв нужен только если основной не хватит до MIN_TOTAL)
        main_ids = {c for c, _ in all_entries}
        slow_entries = [e for e in SLOW_POOL if e[0] not in main_ids]
        SLOW_SET.update(c for c, _ in slow_entries)
        pool = all_entries + slow_entries

        # лучшие первыми: выше tier, не из резерва, ниже пинг — их и оставит дедупликация
        pool.sort(key=rank_key)

        taken = set()
        for c in pinned:
            if not c.startswith(PROTOCOLS):
                continue
            hp = get_host_port(c)
            if hp:
                ip = await resolve_ip(hp[0])
                taken.add((ip or hp[0], hp[1]))

        before = len(pool)
        pool = await dedupe_by_ip(pool, taken)
        print()
        print(f"[i] Убрал дубли (IP:порт / выходной IP): {before - len(pool)} (осталось {len(pool)})")
        print(f"[✓] Уникальных рабочих: {len(pool)} (в основной части: {len(pool) - sum(1 for e in pool if e[0] in SLOW_SET)})")

        if not pool:
            print("[x] Рабочих конфигов нет.")
            return

        selected = select_final(pool)

        print()
        print("[i] Определяем страну и город (реальный выходной IP)...")

        geo_entries = []
        geo_cache = {}
        fallback_cache = {}

        for index, (config, latency) in enumerate(selected, 1):
            country_code, geo_name, source = None, None, "выход через прокси"

            info = EXIT_GEO.get(config)
            if info:
                country_code, geo_name, _ = info
            else:
                hp = get_host_port(config)
                host = hp[0] if hp else None

                if host:
                    if host not in geo_cache:
                        geo_cache[host] = await get_server_geo(session, host)
                    country_code, geo_name = geo_cache[host]
                    source = "ip-api.com"

                if host and not geo_name:
                    if host not in fallback_cache:
                        fallback_cache[host] = await fallback_geo(session, host)
                    result = fallback_cache[host]
                    if result:
                        country_code, geo_name, source = result

                if not geo_name:
                    flag_code = flag_code_from_name(config)
                    if flag_code:
                        country_code = flag_code
                        geo_name = make_geo_name(flag_code, None)
                        source = "флаг из названия"

            geo_entries.append((config, latency, country_code, geo_name))

            tag = f" {cascade_suffix(config)}" if is_cascade(config) else ""
            print(f"    [{index}/{len(selected)}] tier {eff_tier(config)} | {geo_name or '🌐 Неизвестно (имя не менял)'}{tag}"
                  f"  <- {source if geo_name else 'нигде не определилась'}")

    if WHITELIST_ONLY and WL_ONLY_RU_SERVERS:
        before = len(geo_entries)
        geo_entries = [e for e in geo_entries if e[2] == "RU"]
        print(f"[i] Только выход в РФ: {len(geo_entries)} из {before}")

    kept_entries, country_stats = distribute_by_country(geo_entries)

    # лимиты по странам не должны опускать подписку ниже MIN_TOTAL — возвращаем лучших из обрезанных
    if len(kept_entries) < MIN_TOTAL and len(geo_entries) > len(kept_entries):
        kept_ids = {e[0] for e in kept_entries}
        extra = [e for e in geo_entries if e[0] not in kept_ids]
        extra.sort(key=lambda e: (-eff_tier(e[0]), e[1]))
        kept_entries += extra[:MIN_TOTAL - len(kept_entries)]
        print(f"[i] Лимиты по странам вернули подписку до {len(kept_entries)} (минимум {MIN_TOTAL})")

    print_country_distribution(country_stats)

    renamed = []
    cascade_count = 0
    for config, latency, country_code, geo_name in kept_entries:
        name = geo_name
        if name and is_cascade(config):
            name = f"{name} {cascade_suffix(config)}"
            cascade_count += 1
        renamed.append(rename_config(config, name) if name else config)

    if pinned:
        print()
        print(f"[i] Добавляю закреплённых конфигов: {len(pinned)} (без проверки)")

    final_list = pinned + renamed

    before_final = len(final_list)
    final_list = [line for line in final_list if not is_blocked(line)]
    if len(final_list) != before_final:
        print(f"[i] В последний момент убрано по чёрному списку: {before_final - len(final_list)}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(final_list) + "\n", encoding="utf-8")

    save_state()

    print()
    print("[✓] Готово!")
    print(f"[✓] Сохранено: {len(final_list)} (закреплённых: {len(pinned)}, каскадов: {cascade_count})")
    print(f"[✓] Файл: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Остановлено.")
