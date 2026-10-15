#!/usr/bin/env python3

import asyncio
import aiohttp
import aiohttp_socks
import base64
import json
import socket
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
# Добавляются в итоговую подписку БЕЗ проверки (пинг/живость не тестируются)
# и не удаляются последующими запусками скрипта — просто впиши сюда строку(и)
# ============================================================

PINNED_CONFIGS = [
    "#profile-title: PizdukVPN БС🏳",
    "#announce:base64: 8J+UpdCi0LXQu9C10LPRgNCw0Lwg0LrQsNC90LDQuzogQFBpem1vZPCfpboK8J+lsNCQ0LLRgtC+0L7QsdC90L7QstC70LXQvdC40LUg0YDQsNC3INCyIDYg0YfQsNGB0L7QsvCfmLE=",
    "#profile-web-page-url: https://t.me/PizMod",
    "#support-url: https://t.me/Harachok",
    "#profile-update-interval: 6",
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@qq.utiltools.site:443?security=reality&encryption=none&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&headerType=none&fp=qq&type=tcp&flow=xtls-rprx-vision&sni=qq.utiltools.site#%F0%9F%91%89%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B7%F0%9F%87%BA ",
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@qq.utiltools.site:443?security=reality&encryption=none&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&headerType=none&fp=qq&type=tcp&flow=xtls-rprx-vision&sni=qq.utiltools.site#%F0%9F%91%89%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B7%F0%9F%87%BA%20%D1%8D%D1%82%D0%BE%202",
    "vless://6b134aff-450b-4a5f-8d1b-dac67ceb11d0@msc1.serverslocal.ru:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=msc1.serverslocal.ru&fp=firefox&security=reality&pbk=qPh1iuwpELosLWTxOXyfCiMghs_sjSzCOGbkiF0gdkk&sid=f7e66e308136e1a1#%F0%9F%87%B7%F0%9F%87%BA%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F%F0%9F%8F%B3",
    "vless://adc11f30-e4cb-4985-bf5e-f9ded69c019f@90.156.218.163:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=eh.vk.ru&fp=qq&security=reality&pbk=fNfokzklCF4l_c8k8PciOCjm5ecNoF_sNLjEtaO-xzI&sid=db04ce8bdb8900f1#%E2%9A%A1%20%F0%9F%87%B7%F0%9F%87%BA%20%E2%98%AD%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F%20%7C%20%D0%91%D0%B5%D0%BB%D1%8B%D0%B9%20IP%20%E2%98%AD%20%F0%9F%87%B7%F0%9F%87%BA%20%E2%9A%A1",
    "vless://03ca8c3f-e777-45b5-a1b1-592094ca99ee@79.174.92.222:443/?type=grpc&encryption=none&flow=&sni=m.vk.com&security=reality&pbk=_PYBo3dyZRpGC44vADqcmlBCSeAVh1X8l3mulghVsTI&sid=a1b2c3d4#%F0%9F%87%B7%F0%9F%87%BA%20%E2%98%80%EF%B8%8F%E2%9C%88%EF%B8%8F%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F%F0%9F%8F%B3%EF%B8%8F%F0%9F%94%90",
    "vless://2c634977-584e-4e1f-b501-1b70c77a6743@185.141.227.180:2053/?type=xhttp&encryption=none&flow=&host=dismissaltree.net&path=%2Fapi%2Fv1%2Fupload&mode=auto&extra=%7B%0A%20%20%22xPaddingBytes%22%3A%20%220%22%2C%0A%20%20%22scMaxEachPostBytes%22%3A%20%221000000%22%2C%0A%20%20%22scMinPostsIntervalMs%22%3A%20%2230%22%2C%0A%20%20%22scMaxBufferedPosts%22%3A%200%2C%0A%20%20%22scStreamUpServerSecs%22%3A%20%220%22%2C%0A%20%20%22uplinkChunkSize%22%3A%20%220%22%2C%0A%20%20%22serverMaxHeaderBytes%22%3A%200%2C%0A%20%20%22sessionIDLength%22%3A%20%220%22%2C%0A%20%20%22xmux%22%3A%20%7B%0A%20%20%20%20%22maxConcurrency%22%3A%20%220%22%2C%0A%20%20%20%20%22maxConnections%22%3A%20%220%22%2C%0A%20%20%20%20%22cMaxReuseTimes%22%3A%20%220%22%2C%0A%20%20%20%20%22hMaxRequestTimes%22%3A%20%220%22%2C%0A%20%20%20%20%22hMaxReusableSecs%22%3A%20%220%22%2C%0A%20%20%20%20%22hKeepAlivePeriod%22%3A%200%0A%20%20%7D%2C%0A%20%20%22host%22%3A%20%22%22%2C%0A%20%20%22path%22%3A%20%22%22%2C%0A%20%20%22mode%22%3A%20%22%22%0A%7D&security=tls&sni=dismissaltree.net#%F0%9F%87%AB%F0%9F%87%AE%D0%A4%D0%B8%D0%BD%D0%BB%D1%8F%D0%BD%D0%B4%D0%B8%D1%8F%F0%9F%A4%8D%F0%9F%A4%8D",
    "vless://2c634977-584e-4e1f-b501-1b70c77a6743@185.141.227.180:2053/?type=xhttp&encryption=none&flow=&host=dismissaltree.net&path=%2Fapi%2Fv1%2Fupload&mode=auto&extra=%7B%0A%20%20%22xPaddingBytes%22%3A%20%220%22%2C%0A%20%20%22scMaxEachPostBytes%22%3A%20%221000000%22%2C%0A%20%20%22scMinPostsIntervalMs%22%3A%20%2230%22%2C%0A%20%20%22scMaxBufferedPosts%22%3A%200%2C%0A%20%20%22scStreamUpServerSecs%22%3A%20%220%22%2C%0A%20%20%22uplinkChunkSize%22%3A%20%220%22%2C%0A%20%20%22serverMaxHeaderBytes%22%3A%200%2C%0A%20%20%22sessionIDLength%22%3A%20%220%22%2C%0A%20%20%22xmux%22%3A%20%7B%0A%20%20%20%20%22maxConcurrency%22%3A%20%220%22%2C%0A%20%20%20%20%22maxConnections%22%3A%20%220%22%2C%0A%20%20%20%20%22cMaxReuseTimes%22%3A%20%220%22%2C%0A%20%20%20%20%22hMaxRequestTimes%22%3A%20%220%22%2C%0A%20%20%20%20%22hMaxReusableSecs%22%3A%20%220%22%2C%0A%20%20%20%20%22hKeepAlivePeriod%22%3A%200%0A%20%20%7D%2C%0A%20%20%22host%22%3A%20%22%22%2C%0A%20%20%22path%22%3A%20%22%22%2C%0A%20%20%22mode%22%3A%20%22%22%0A%7D&security=tls&sni=dismissaltree.net#%F0%9F%87%BA%F0%9F%87%B8%20%D0%A1%D0%A8%D0%90%20%F0%9F%A4%8D",
    # "vless://uuid@host:port?...#Моё имя",
]

# ============================================================
# НАСТРОЙКИ
# ============================================================

MAX_PER_SOURCE = 40
MIN_PER_SOURCE = 1

# --- распределение по странам ---
MAX_PER_COUNTRY = 15       # максимум конфигов на одну страну в итоговом файле (0 = без ограничения)
MIN_COUNTRIES_KEEP_ALL = 0 # если стран меньше N — лимит по стране не применяется (0 = выключено)

# --- РЕЖИМ БЕЛЫХ СПИСКОВ (БС) ---
WHITELIST_ONLY = True        # True = оставлять только конфиги белых списков
WL_TRUST_NAME = True         # считать БС-конфигом, если в названии есть "БС" / "белые списки" / "whitelist"
WL_ACCEPT_RU_IP = True       # считать БС-конфигом и тот, чей сервер по geo находится в РФ (каскады РФ→мир, SNI может быть любым)
WL_ONLY_RU_SERVERS = False   # True = оставлять только конфиги, у которых РЕАЛЬНЫЙ ВЫХОДНОЙ IP в РФ.
                             # Для каскадов РФ→мир выход не в РФ, поэтому обычно держи False

# Конфиг считается БС, если его SNI / Host / адрес сервера входит в один из этих доменов
# (включая поддомены). Список белых списков меняется — дополняй под себя.
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

SHOW_SNI_STATS = True        # печатать в лог топ SNI каждого источника (видно, что добавить в WL_DOMAINS)

WL_NAME_REGEX = re.compile(
    r"(?<!\w)(бс|белы[йхе]\w*\s*спис\w*|white\s*-?list|whitelist|white)(?!\w)",
    re.IGNORECASE,
)

CONNECT_TIMEOUT = 1.5     # для фолбэк-протоколов (hysteria2/tuic)
FETCH_TIMEOUT = 15.0

CONCURRENCY = 15          # одновременных xray-процессов (осторожно с RAM раннера)
XRAY_STARTUP_WAIT = 1.2   # сек, дать xray время подняться
XRAY_TEST_TIMEOUT = 8.0   # сек на сессию через прокси (тест-запрос + запрос гео)
XRAY_BINARY = "xray"      # должен быть в PATH (см. workflow)
TEST_URL = "https://cp.cloudflare.com/generate_204"

# --- реальная проверка выходного IP: гео запрашивается ЧЕРЕЗ сам прокси ---
GEO_URLS = (
    "https://ipwho.is/",
    "http://ip-api.com/json/?fields=status,countryCode,city,query",
)
EXIT_GEO = {}  # config -> (country_code, geo_name, exit_ip)

MAX_PING_MS = 120         # жёсткая отсечка — медленнее не берём вообще
GOOD_PING_MS = 50         # ориентир "хорошего" пинга, используется только в логах

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

# протоколы, для которых умеем строить реальный xray-конфиг
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
# HOST / PORT (для geo и фолбэк-проверки)
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
    """Название конфига (то, что после # или поле ps у vmess)."""
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
    """Все домены, по которым фильтр может опознать конфиг: SNI, Host, адрес сервера."""
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


def get_sni(line):
    """SNI конфига (или Host / адрес сервера, если SNI не задан)."""
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


def print_sni_stats(configs):
    counter = Counter(get_sni(c) or "(пусто)" for c in configs)
    print("    SNI (топ-25):")
    for sni, count in counter.most_common(25):
        mark = "✓ БС" if domain_in_whitelist(sni) else "—"
        print(f"      {count:>4}  {sni:<40} {mark}")


_geo_lock = asyncio.Lock()


async def find_ru_hosts(session, hosts):
    """Возвращает множество хостов, чей IP по geo находится в РФ (пакетный запрос к ip-api.com)."""
    loop = asyncio.get_running_loop()
    ip_of = {}

    async def resolve(host):
        try:
            infos = await loop.getaddrinfo(host, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
            ip_of[host] = infos[0][4][0]
        except Exception:
            pass

    await asyncio.gather(*(resolve(h) for h in hosts))

    ips = sorted(set(ip_of.values()))
    ru_ips = set()

    async with _geo_lock:  # лимит ip-api: 15 пакетных запросов в минуту
        for i in range(0, len(ips), 100):
            chunk = ips[i:i + 100]
            try:
                timeout = aiohttp.ClientTimeout(total=15.0)
                async with session.post(
                    "http://ip-api.com/batch?fields=query,countryCode",
                    json=chunk, timeout=timeout,
                ) as response:
                    if response.status == 200:
                        for item in await response.json(content_type=None):
                            if item.get("countryCode") == "RU":
                                ru_ips.add(item.get("query"))
            except Exception:
                pass
            if i + 100 < len(ips):
                await asyncio.sleep(4.5)

    return {host for host, ip in ip_of.items() if ip in ru_ips}


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
    """True, если конфиг похож на конфиг белых списков (БС)."""
    if not WHITELIST_ONLY:
        return True
    if WL_TRUST_NAME and WL_NAME_REGEX.search(config_name(line)):
        return True
    return any(domain_in_whitelist(d) for d in config_domains(line))


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
# РЕАЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ XRAY
# ============================================================

async def xray_real_check(line):
    outbound = build_outbound(line)
    if not outbound:
        return False

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

        try:
            start = time.monotonic()
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(TEST_URL, ssl=False) as resp:
                    if resp.status not in (200, 204):
                        return None
                    await resp.read()
                latency_ms = (time.monotonic() - start) * 1000

                # реальный выходной IP / страна / город — запрос идёт через прокси
                geo = await fetch_exit_geo(session)
                if geo:
                    cc, city, exit_ip = geo
                    EXIT_GEO[line] = (cc, make_geo_name(cc, city), exit_ip)
            return latency_ms
        except Exception:
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
# ФОЛБЭК TCP-ПРОВЕРКА (hysteria2 / tuic / ssr)
# ============================================================

async def tcp_check(host, port):
    try:
        start = time.monotonic()
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT)
        latency_ms = (time.monotonic() - start) * 1000
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return latency_ms
    except Exception:
        return None


async def fallback_check(line):
    hp = get_host_port(line)
    if not hp:
        return None
    return await tcp_check(*hp)


# ============================================================
# ОБЩАЯ ПРОВЕРКА КОНФИГА — возвращает пинг в мс или None
# ============================================================

async def check_config(line):
    if line.startswith(XRAY_SUPPORTED):
        return await xray_real_check(line)
    return await fallback_check(line)


# ============================================================
# GEO СЕРВЕРА (фолбэк для протоколов без xray: hysteria/tuic/ssr)
# ============================================================

async def get_server_geo(session, host):
    """Возвращает (country_code, geo_name) или (None, None)."""
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
    total_found = len(configs)
    by_domain = []
    by_ru_ip = []

    if SHOW_SNI_STATS and configs:
        print()
        print(f"[i] SNI источника: {url}")
        print_sni_stats(configs)

    # отсекаем всё, что не относится к белым спискам, ДО проверки (экономит время и RAM)
    if WHITELIST_ONLY:
        by_domain = [c for c in configs if is_whitelist_config(c)]
        passed = set(by_domain)
        rest = [c for c in configs if c not in passed]

        if WL_ACCEPT_RU_IP and rest:
            hosts = set()
            for c in rest:
                hp = get_host_port(c)
                if hp:
                    hosts.add(hp[0])
            ru_hosts = await find_ru_hosts(session, hosts)
            for c in rest:
                hp = get_host_port(c)
                if hp and hp[0] in ru_hosts:
                    by_ru_ip.append(c)

        configs = by_domain + by_ru_ip

    print()
    print("[i] Источник:")
    print(f"    {url}")
    if WHITELIST_ONLY:
        print(f"    найдено: {total_found}, из них белых списков: {len(configs)} "
              f"(по SNI/названию: {len(by_domain)}, по IP в РФ: {len(by_ru_ip)})")
    else:
        print(f"    найдено: {total_found}")

    if not configs:
        return []

    async def worker(config):
        async with semaphore:
            try:
                latency = await check_config(config)
                if latency is not None:
                    return (config, latency)
            except Exception:
                pass
        return None

    tasks = [asyncio.create_task(worker(c)) for c in configs]
    working = []  # список (config, latency_ms)

    try:
        for task in asyncio.as_completed(tasks):
            result = await task
            if result:
                config, latency = result
                working.append((config, latency))
                mark = "🔥" if latency <= GOOD_PING_MS else ("👍" if latency <= MAX_PING_MS else "🐌")
                exit_info = EXIT_GEO.get(config)
                exit_txt = f", выход {exit_info[2]} {exit_info[1]}" if exit_info else ""
                print(f"    [✓] {mark} рабочий, пинг {latency:.0f} мс{exit_txt}")
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()

    # отбрасываем слишком медленные
    fast_enough = [c for c in working if c[1] <= MAX_PING_MS]

    if len(fast_enough) < MIN_PER_SOURCE and len(working) > len(fast_enough):
        print(f"    [!] Быстрых (<{MAX_PING_MS} мс) меньше {MIN_PER_SOURCE} — добираем из более медленных")
        working.sort(key=lambda c: c[1])
        fast_enough = working

    fast_enough.sort(key=lambda c: c[1])
    best = fast_enough[:MAX_PER_SOURCE]

    print(f"    [✓] рабочих всего: {len(working)}, отобрано лучших по пингу: {len(best)}")

    if len(best) < MIN_PER_SOURCE:
        print(f"    [!] Меньше {MIN_PER_SOURCE}")

    return best  # список (config, latency)


# ============================================================
# РАСПРЕДЕЛЕНИЕ ПО СТРАНАМ
# ============================================================

def distribute_by_country(entries):
    """
    entries: список (config, latency, country_code, geo_name)
    Возвращает (kept, stats): лимит MAX_PER_COUNTRY на страну, лучшие по пингу первыми.
    """
    by_country = defaultdict(list)
    for entry in entries:
        _, _, country_code, _ = entry
        key = country_code or "??"
        by_country[key].append(entry)

    apply_limit = MAX_PER_COUNTRY > 0
    if MIN_COUNTRIES_KEEP_ALL and len(by_country) < MIN_COUNTRIES_KEEP_ALL:
        apply_limit = False

    kept = []
    stats = {}

    for country_code in sorted(by_country, key=lambda c: len(by_country[c]), reverse=True):
        group = by_country[country_code]
        group.sort(key=lambda e: e[1])  # по латентности, лучшие первые

        selected = group[:MAX_PER_COUNTRY] if apply_limit else group
        kept.extend(selected)

        example_name = get_country_name(country_code) if country_code != "??" else "Неизвестно"
        stats[country_code] = {
            "total": len(group),
            "kept": len(selected),
            "name": example_name,
        }

    return kept, stats


def print_country_distribution(stats):
    print()
    print("[i] Распределение по странам:")
    total_kept = 0
    for country_code, info in sorted(stats.items(), key=lambda kv: kv[1]["kept"], reverse=True):
        flag = get_country_flag(country_code) if country_code != "??" else "🌐"
        total_kept += info["kept"]
        if info["kept"] < info["total"]:
            print(f"    {flag} {info['name']:<20} {info['kept']:>3} / {info['total']:>3} (обрезано лимитом)")
        else:
            print(f"    {flag} {info['name']:<20} {info['kept']:>3}")
    print(f"    {'—' * 40}")
    print(f"    Итого стран: {len(stats)}, итого конфигов: {total_kept}")


# ============================================================
# MAIN
# ============================================================

async def main():
    init_port_pool(CONCURRENCY)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    all_entries = []  # (config, latency)

    print("[i] Сбор конфигов...")

    async with aiohttp.ClientSession() as session:
        tasks = [process_source(session, url, semaphore) for url in SOURCES if url.strip()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for index, result in enumerate(results, 1):
            if isinstance(result, list):
                all_entries.extend(result)
            else:
                print(f"[!] Источник #{index} завершился с ошибкой: {result}")

        seen = set()
        unique_entries = []
        for config, latency in all_entries:
            if config in seen:
                continue
            seen.add(config)
            unique_entries.append((config, latency))
        all_entries = unique_entries

        print()
        print(f"[✓] Уникальных рабочих: {len(all_entries)}")

        if not all_entries:
            print("[x] Рабочих конфигов нет.")
            return

        print()
        print("[i] Определяем страну и город (реальный выходной IP)...")

        geo_entries = []  # (config, latency, country_code, geo_name)
        geo_cache = {}

        for index, (config, latency) in enumerate(all_entries, 1):
            info = EXIT_GEO.get(config)
            if info:
                country_code, geo_name, _ = info
            else:  # hysteria/tuic/ssr или гео через прокси не ответило — по адресу сервера
                hp = get_host_port(config)
                if not hp:
                    continue
                host = hp[0]
                if host not in geo_cache:
                    geo_cache[host] = await get_server_geo(session, host)
                country_code, geo_name = geo_cache[host]
            geo_entries.append((config, latency, country_code, geo_name))

            print(f"    [{index}/{len(all_entries)}] {geo_name or '🌐 Неизвестно'}")

    if WHITELIST_ONLY and WL_ONLY_RU_SERVERS:
        before = len(geo_entries)
        geo_entries = [e for e in geo_entries if e[2] == "RU"]
        print(f"[i] Только выход в РФ: {len(geo_entries)} из {before}")

    # --- распределение по странам с ограничением MAX_PER_COUNTRY ---
    kept_entries, country_stats = distribute_by_country(geo_entries)
    print_country_distribution(country_stats)

    # переименовываем конфиги согласно гео (после отбора, чтобы не тратить время зря)
    renamed = []
    for config, latency, country_code, geo_name in kept_entries:
        renamed_config = rename_config(config, geo_name) if geo_name else config
        renamed.append(renamed_config)

    # закреплённые конфиги — без проверки, всегда в начале списка
    pinned = [c.strip() for c in PINNED_CONFIGS if c.strip()]
    if pinned:
        print()
        print(f"[i] Добавляю закреплённых конфигов: {len(pinned)} (без проверки)")

    final_list = pinned + renamed

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(final_list) + "\n", encoding="utf-8")

    print()
    print("[✓] Готово!")
    print(f"[✓] Сохранено: {len(final_list)} (из них закреплённых: {len(pinned)})")
    print(f"[✓] Файл: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Остановлено.")