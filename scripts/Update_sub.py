#!/usr/bin/env python3
# PizdukVPN ❄️ — единый сборщик подписки: «ЧС» и «МИКС» в одном файле.
#
# Это ЧС-версия (отдельный файл).
#
# Как устроена проверка (раннер в США, а подписка нужна для РФ):
#   1) TCP-прозвон -> ядро (xray / sing-box) -> МЯГКАЯ проверка: прокси реально пропускает трафик.
#      Никаких «из США не открывается speedtest / youtube» — это лишь убивало рабочие из РФ конфиги.
#   2) Серверы со входом в РФ часто отсекают чужие IP, поэтому из США они «мёртвые», а с телефона живые.
#      Такие (не прошли проверку, но вход в РФ) перепроверяются с российских узлов check-host.net
#      и попадают в подписку с меткой 🔸 («достучались из РФ по TCP»).
#   3) В конец названия добавляется смайлик источника — сразу видно, откуда конфиг.

import asyncio
import base64
import datetime
import hashlib
import ipaddress
import itertools
import json
import os
import re
import shutil
import socket
import statistics
import sys
import tempfile
import time
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote

import aiohttp
import aiohttp_socks

# ============================================================
# РЕЖИМ
# ============================================================

MODE = "chs"
MIX = MODE == "mix"
TITLE = "МИКС" if MIX else "ЧС"

TARGET_COUNT = 500 if MIX else 60     # сколько проверенных взять (не считая закреплённых и 🔸); 0 = все
EARLY_STOP_MULT = 0 if MIX else 4     # остановить проверку, когда найдено TARGET*N рабочих; 0 = проверять все
SOFT_MAX = 150 if MIX else 40         # максимум 🔸-конфигов (вход в РФ, подтверждены только с российских узлов)
MAX_PER_ENDPOINT = 3 if MIX else 1    # не больше N конфигов на один ip:порт (разные uuid); 0 = без лимита
MAX_PER_EXIT_IP = 0 if MIX else 2     # не больше N на один выходной IP; 0 = без лимита
MAX_PER_SUBNET = 0 if MIX else 8      # не больше N на подсеть /24; 0 = без лимита
UPDATE_HOURS = 8 if MIX else 6

# ============================================================
# ИСТОЧНИКИ.  Формат строки:  «смайлик ссылка  # комментарий».
# Смайлик ставится в КОНЕЦ названия каждого конфига из этого источника.
# Новый источник = просто новая строка со ссылкой (смайлик подберётся сам из SEASON_POOL).
# Нерабочий источник: смотри в логе «Нерабочих по источникам» (там тот же смайлик) и удаляй строку.
# ============================================================

SOURCES_CORE = """
🎅 https://freevpn.happcluchi.workers.dev      # @freevpnhapp
🎄 https://pozor.bond/sub/aeryxvpn
🎁 https://goo.su/Xfwbx
🔔 https://sub.vlessfo.ru/vlessforu/working_configs.txt   # vlessforu
🦌 https://admin2.vspboost.ru/s/rZ7ekY                    # vsp
🧦 https://raw.githubusercontent.com/MK-l4/Q-RVVPN/refs/heads/main/Q%E2%80%A2RVVPN
🍪 https://raw.githubusercontent.com/OceaniaVPN/StekloVPN/refs/heads/main/configs/okeania_auto.txt
🥛 https://raw.githubusercontent.com/s0ulcoil/HavenVPN/refs/heads/main/Haven
🧣 https://raw.githubusercontent.com/korol5028/korol-vpn/main/Pohyu.txt
🧤 https://bit.ly/LimeVPN
🏂 https://clck.ly/3WnEfT
🛷 https://github.com/theakres/VPN/raw/main/all            # akres
"""

# Запас зимних смайликов для источников без своего (чтобы не пересекаться с ❄️⛄🧊📶🤖🔸)
SEASON_POOL = ["🎆", "🧸", "🪵", "🍫", "🥂", "🕯", "🍵", "🧑‍🎄", "🎠", "🦊", "🐻‍❄️", "⛸", "🏔", "🍰", "🥕"]


def parse_sources(text):
    rows = []
    for line in text.splitlines():
        line = line.split(" #", 1)[0].strip()
        if line.startswith("#"):
            continue
        m = re.match(r"^(?:(\S+?)\s*)?(https?://\S+)$", line)
        if m:
            rows.append([m.group(1), m.group(2)])
    return rows


def load_sources():
    rows = parse_sources(SOURCES_CORE)
    used = {e for e, _ in rows if e}
    free = iter([e for e in SEASON_POOL if e not in used])
    return [(e or next(free, "🌲"), u) for e, u in rows]


SOURCES = load_sources()
SRC_EMOJI = {u: e for e, u in SOURCES}

# ============================================================
# ЗАКРЕПЛЁННЫЕ КОНФИГИ — в начало подписки БЕЗ проверки (шапка #profile-title и т.п. тоже тут)
# ============================================================

PINNED_CONFIGS = [
    "#profile-title: PizdukVPN ЧС🏴",
    "#announce: base64: 8J+YjiDQotC10LvQtdCz0YDQsNC8INC60LDQvdCw0Ls6IEBQaXpNb2Twn5iNCvCfpbPQkNCy0YLQvtC+0LHQvdC+0LLQu9C10L3QuNC1INC60LDQttC00YvQtSA2INGH0LDRgdC+0LLwn6Sv",
    "#profile-web-page-url: t.me/PizMod",
    "#support-url: t.me/Harachok",
    "#profile-update-interval: 6",
    "vless://e75ad2eb-6c1f-45ce-8023-f5f10875df66@129.101.98.60:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=ru7e2bab87cc39.eu-cdn539.com&fp=firefox&security=reality&pbk=lews1n_fypGexd_dMofEO4Vy1ULsFeVIFa90MMY3pm4&sid=3992cc7fb9fcbe58#%F0%9F%87%B7%F0%9F%87%BA%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F",
    "vless://e75ad2eb-6c1f-45ce-8023-f5f10875df66@129.101.98.60:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=ru7e2bab87cc39.eu-cdn539.com&fp=firefox&security=reality&pbk=lews1n_fypGexd_dMofEO4Vy1ULsFeVIFa90MMY3pm4&sid=3992cc7fb9fcbe58#%F0%9F%87%B7%F0%9F%87%BA%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F%20%E2%9A%A1%20Youtube%20%F0%9F%93%BA",
    "vmess://eyJhZGQiOiJjZi4wc20uY29tIiwiYWlkIjoiMCIsImFscG4iOiIiLCJmcCI6IiIsImhvc3QiOiJ2bWVzcy5sYnc2NjYuZHBkbnMub3JnIiwiaWQiOiIwY2Y2ZDk3MC0zZjFkLTRhYWUtYTk4OS05MmE4Zjc2YWUzZGIiLCJuZXQiOiJ3cyIsInBhdGgiOiIvd3M/ZWRcdTAwM2QyMDQ4IiwicG9ydCI6IjgwIiwicHMiOiLwn4e68J+HuCDinKYg0KHQqNCQIOKcpiDwn4yAIiwic2N5IjoiYXV0byIsInNuaSI6IiIsInRscyI6IiIsInR5cGUiOiIiLCJ2IjoiMiJ9",
    "vless://fd90e601-a56c-42b8-aab7-aa02d26fcb04@app.streamru2.net:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&security=tls&sni=app.streamru2.net&fp=firefox#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20Youtube%20%F0%9F%93%BA",
    "vless://a13f3a29-56fd-4540-b7f4-848861f63ed0@199.232.249.182:443/?type=xhttp&encryption=none&flow=&host=vv1.global.ssl.fastly.net&path=%2F&mode=auto&security=tls&sni=huesos.fastly.com#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20Youtube%20%F0%9F%93%BA",
    "vless://07df3711-07a1-4649-9a61-3f16cb931d02@345739t.de19.h1clayd.click:443/?type=tcp&encryption=none&flow=&sni=345739t.de19.h1clayd.click&fp=chrome&security=reality&pbk=hFee7zTreqlv_wccK_8zxN5v23hj9u-DshByvGf-KAA&sid=23732d14a527990d#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20Youtube%20%F0%9F%93%BA",
    "vless://fd90e601-a56c-42b8-aab7-aa02d26fcb04@app.streamru13.net:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&security=tls&sni=app.streamru13.net&fp=firefox#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B",
    "vless://a13f3a29-56fd-4540-b7f4-848861f63ed0@199.232.249.182:443/?type=xhttp&encryption=none&flow=&host=vv1.global.ssl.fastly.net&path=%2F&mode=auto&security=tls&sni=huesos.fastly.com#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20",
    "vless://003ec416-45f0-462a-8030-016fe0a71703@199.232.249.182:443/?type=xhttp&encryption=none&flow=&host=v2.global.ssl.fastly.net&path=%2F&mode=auto&security=tls&sni=huesos.fastly.com#%F0%9F%87%AB%F0%9F%87%B7%20%D0%A4%D1%80%D0%B0%D0%BD%D1%86%D0%B8%D1%8F%20Youtube%20%F0%9F%93%BA",
    "vless://33b25ed8-2088-40a5-ba4f-cf04b6d3fc06@free-de1.endurancepro.space:8443/?type=xhttp&encryption=none&flow=&path=%2Fapi%2Fv1%2Fsync&mode=packet-up&sni=free-de1.endurancepro.space&fp=firefox&security=reality&pbk=vJgQ5ZSblvzGdJ1s693hIEIUGTgMJaci4_2UGR7BFVA&sid=789df6fbcf3518ea#%F0%9F%87%AA%F0%9F%87%AA%20%D0%AD%D1%81%D1%82%D0%BE%D0%BD%D0%B8%D1%8F",
    "vless://fd90e601-a56c-42b8-aab7-aa02d26fcb04@app.streamru17.net:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&security=tls&sni=app.streamru17.net&fp=firefox#%F0%9F%87%B5%F0%9F%87%B1%20%D0%9F%D0%BE%D0%BB%D1%8C%D1%88%D0%B0%20Youtube%20%F0%9F%93%BA",
    "vless://49b42507-8781-46a4-8fcc-0b404690c85d@87.242.95.170:443/?type=ws&encryption=none&flow=&host=radio-prichal.online&path=%2Fcheckout%2Fstep%2Fallo3fSMLuBu&security=tls&sni=radio-prichal.online&fp=chrome#%F0%9F%87%B5%F0%9F%87%B1%20%D0%9F%D0%BE%D0%BB%D1%8C%D1%88%D0%B0%20YT%20%F0%9F%93%BA%20AI%F0%9F%A4%96%20LTE%F0%9F%93%B6",
    # не трогай!
]

# ============================================================
# НАСТРОЙКИ
# ============================================================

# --- Зима: True — всегда, False — никогда, "auto" — с 1 ноября по 28 февраля ---
WINTER = True
SPEED_TAGS = ("❄️", "⛄", "🧊")   # быстрый (≤ GOOD_PING_MS) / нормальный (≤ 3×) / медленный
GOOD_PING_MS = 300
LTE_TAG = "📶"                    # конфиг подходит под белые списки мобильного интернета РФ
GEMINI_TAG = "🤖"                 # через конфиг открывается Gemini
SOFT_TAG = "🔸"                   # из США не проверить (вход в РФ): достучались с российских узлов по TCP
WINTER_ANNOUNCE = "❄️ Телеграм канал: @PizMod ⛄\n🎄Автообновление каждые %d часов🧊" % UPDATE_HOURS

# --- Скачивание подписок + подмена HWID (Happ / Remnawave / Marzban) ---
HWID_SPOOF = True
HWID = (os.environ.get("SUB_HWID") or "").strip() or \
    hashlib.sha256(os.environ.get("HWID_SEED", "PizMod").encode()).hexdigest()[:16]
HWID_HEADERS = {"x-hwid": HWID, "x-device-os": "Android", "x-ver-os": "14", "x-device-model": "Pixel 8"}
FETCH_TIMEOUT = 25.0
FETCH_RETRIES = 3
FETCH_UAS = ["v2rayN/6.42", "Happ/7.0.0", "Mozilla/5.0 (Windows NT 10.0; Win64;)"]

# --- Ядра ---
XRAY_BINARY = "xray"
SINGBOX_BINARY = "sing-box"        # нужна версия 1.11+ (для hy2)
CHECK_HY2 = True
CONCURRENCY = 40                   # одновременных ядер (~30-50 МБ RAM на каждое)
CORE_START_TIMEOUT = 6.0
BASE_LOCAL_PORT = 21000

# --- TCP-прозвон (hy2 — UDP, к нему не применяется) ---
TCP_TIMEOUT = 4.0                  # из США до РФ/Азии дольше, чем «у себя» — таймаут щедрый
TCP_TRIES = 2
TCP_CONCURRENCY = 300

# --- МЯГКАЯ проверка через ядро ---
PROBE_URLS = ["https://cp.cloudflare.com/generate_204", "https://www.gstatic.com/generate_204"]
PROBE_MIN_OK = 1                   # сколько из PROBE_URLS должны ответить на «шлюзе»
GATE_TRIES = 2                     # попыток шлюза на том же ядре (холодный старт, потеря пакета)
GATE_TIMEOUT = 7.0
WARM_REQUESTS = 2                  # повторные запросы по тому же соединению (рвёт ли сервер keep-alive)
WARM_MAX_FAILS = 1                 # сколько из них можно провалить
IDLE_PAUSE = 1.0
CHECK_LIMIT = 45.0                 # жёсткий лимит секунд на один конфиг целиком
MAX_PING_MS = 4000
CHECK_GEMINI = True
GEMINI_URL = "https://gemini.google.com"
GEMINI_MARKER = "45631641,null,true"   # «регион поддерживается» в HTML страницы
GEMINI_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                  "Accept-Language": "en-US,en;q=0.9", "Cookie": "SOCS=CAI"}
CHECK_SPEED = False                # True — ещё и скачать ~500 КБ (с раннера в США часто врёт, поэтому выкл.)
SPEED_URL = "https://speed.cloudflare.com/__down?bytes=500000"
SPEED_MAX_MS = 12000
SPEED_WEIGHT = 0.05

# --- Спасение «входов в РФ»: TCP с российских узлов check-host.net ---
RU_RESCUE = True
CHECK_HOST_API = "https://check-host.net"
RU_NODES_MAX = 4
RU_MIN_OK = 2                      # сколько узлов должны достучаться
RU_MAX_CHECKS = 250                # максимум конфигов на check-host за запуск
RU_CONCURRENCY = 5
RU_GEO_MAX_IPS = 700               # максимум IP, для которых узнаём страну входа (ip-api)
RU_FIRST_POLL, RU_POLL_EVERY, RU_RESULT_WAIT = 1.5, 1.0, 12.0
RU_TLDS = (".ru", ".su", ".xn--p1ai")

# --- Белые списки мобильного интернета РФ (метка 📶 и «вход в РФ») ---
LTE_LISTS_URL = "https://github.com/ancored/ru-mobile-whitelist/releases/latest/download/ru-mobile-whitelist-%s.txt"
LTE_SNI_DOMAINS = ("ya.ru", "yandex.ru", "yandex.net", "max.ru", "vk.com", "vk.ru", "vkontakte.ru",
                   "mail.ru", "ok.ru", "dzen.ru", "rutube.ru", "gosuslugi.ru", "sberbank.ru", "sber.ru",
                   "avito.ru", "ozon.ru", "wildberries.ru", "kinopoisk.ru", "2gis.ru", "userapi.com",
                   "mycdn.me", "vkuser.net")

OUTPUT_FILE = Path("output/sub.txt")
PROGRESS_EVERY = 100

PROTOCOLS = ("vless://", "vmess://", "trojan://", "ss://", "ssr://", "hysteria2://", "hy2://", "tuic://")
XRAY_SCHEMES = ("vless", "vmess", "trojan", "ss")

_my_ip = None
_info = {}                         # config -> {"ip", "cc", "city", "gem"} (выход, измерено через прокси)
_fail = Counter()                  # причина отказа -> сколько конфигов
_T0 = time.monotonic()


def elapsed():
    s = int(time.monotonic() - _T0)
    return f"{s // 60:02d}:{s % 60:02d}"


def stage(title):
    print(f"\n[⏱ {elapsed()}] {title}")


def _reject(reason):
    _fail[reason] += 1
    return None


# ============================================================
# СТРАНЫ / ГОРОДА / ЗИМА
# ============================================================

COUNTRY_NAMES = {
    "RU": "Россия", "DE": "Германия", "NL": "Нидерланды", "FI": "Финляндия", "SE": "Швеция",
    "NO": "Норвегия", "DK": "Дания", "FR": "Франция", "GB": "Британия", "UK": "Британия",
    "US": "США", "CA": "Канада", "PL": "Польша", "CZ": "Чехия", "CH": "Швейцария", "AT": "Австрия",
    "BE": "Бельгия", "IT": "Италия", "ES": "Испания", "PT": "Португалия", "IE": "Ирландия",
    "IS": "Исландия", "EE": "Эстония", "LV": "Латвия", "LT": "Литва", "UA": "Украина",
    "BY": "Беларусь", "KZ": "Казахстан", "UZ": "Узбекистан", "GE": "Грузия", "AM": "Армения",
    "AZ": "Азербайджан", "TR": "Турция", "IL": "Израиль", "AE": "ОАЭ", "JP": "Япония",
    "KR": "Юж. Корея", "CN": "Китай", "HK": "Гонконг", "SG": "Сингапур", "IN": "Индия",
    "AU": "Австралия", "BR": "Бразилия", "MX": "Мексика", "AR": "Аргентина", "CL": "Чили",
    "ZA": "ЮАР", "RO": "Румыния", "BG": "Болгария", "GR": "Греция", "HU": "Венгрия",
    "SK": "Словакия", "SI": "Словения", "HR": "Хорватия", "RS": "Сербия", "LU": "Люксембург",
    "LI": "Лихтенш.", "MT": "Мальта", "CY": "Кипр", "TH": "Таиланд", "VN": "Вьетнам",
    "ID": "Индонезия", "MY": "Малайзия", "PH": "Филиппины", "NZ": "Нов. Зеландия",
}

# Запасной словарь (ipwho и так отдаёт город по-русски; латиницу не пишем, если её нет здесь)
CITY_RU = {
    "Frankfurt am Main": "Франкфурт", "Frankfurt": "Франкфурт", "Amsterdam": "Амстердам",
    "Helsinki": "Хельсинки", "Falkenstein": "Фалькенштайн", "Nuremberg": "Нюрнберг",
    "London": "Лондон", "Paris": "Париж", "Warsaw": "Варшава", "Stockholm": "Стокгольм",
    "Vienna": "Вена", "Prague": "Прага", "Tallinn": "Таллин", "Riga": "Рига", "Vilnius": "Вильнюс",
    "Moscow": "Москва", "Saint Petersburg": "Санкт-Петербург", "New York": "Нью-Йорк",
    "Los Angeles": "Лос-Анджелес", "Tokyo": "Токио", "Istanbul": "Стамбул", "Madrid": "Мадрид",
    "Milan": "Милан", "Zurich": "Цюрих", "Dublin": "Дублин", "Almaty": "Алматы", "Kyiv": "Киев",
    "Berlin": "Берлин", "Rome": "Рим", "Oslo": "Осло", "Copenhagen": "Копенгаген",
    "Brussels": "Брюссель", "Bucharest": "Бухарест", "Sofia": "София", "Budapest": "Будапешт",
    "Chicago": "Чикаго", "Miami": "Майами", "Dallas": "Даллас", "Seattle": "Сиэтл",
    "San Jose": "Сан-Хосе", "Ashburn": "Эшберн", "Toronto": "Торонто", "Sydney": "Сидней",
    "Seoul": "Сеул", "Dubai": "Дубай", "Tel Aviv": "Тель-Авив", "Tbilisi": "Тбилиси",
}
CITY_SHORT = {"Шяуляйское городское самоуправление": "Шауляй"}
CDN_WORDS = ("cloudflare", "fastly", "akamai", "cloudfront", "gcore", "bunny")   # за CDN каскада нет
_CYRILLIC = re.compile("[А-Яа-яЁё]")


def flag(cc):
    if not cc or len(cc) != 2 or not cc.isalpha():
        return "🌐"
    return "".join(chr(ord(c) + 127397) for c in cc.upper())


def country_name(cc):
    return COUNTRY_NAMES.get(cc.upper(), cc.upper()) if cc else "Неизвестно"


def city_ru(city):
    city = str(city or "").strip()
    if not city:
        return None
    city = CITY_SHORT.get(city) or re.sub(r"^(Франкфурт)(?:-на-[А-Яа-яЁё]+|\s+am\s+Main)$", r"\1", city)
    return city if _CYRILLIC.search(city) else CITY_RU.get(city)


def geo_name(cc, city=None):
    city, country = city_ru(city), country_name(cc)
    return f"{flag(cc)} {country} — {city}" if city and city != country else f"{flag(cc)} {country}"


def winter_on():
    return WINTER if isinstance(WINTER, bool) else datetime.date.today().month in (11, 12, 1, 2)


def speed_tag(ms):
    return SPEED_TAGS[0] if ms <= GOOD_PING_MS else SPEED_TAGS[1] if ms <= GOOD_PING_MS * 3 else SPEED_TAGS[2]


def winter_header(lines):
    out = []
    for line in lines:
        if line.startswith("#profile-title:"):
            line = line.replace("🏴", "❄️").replace("🤯", "❄️")
            line = line if "❄" in line else line.rstrip() + "❄️"
        elif line.startswith("#announce:"):
            line = "#announce: base64: " + base64.b64encode(WINTER_ANNOUNCE.encode()).decode()
        out.append(line)
    return out


# ============================================================
# ПАРСИНГ ССЫЛОК (один разбор на все нужды: дубли, TCP, SNI, конфиг ядра)
# ============================================================

def b64decode_safe(value):
    if not value:
        return None
    value = value.strip().replace("-", "+").replace("_", "/")
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4)).decode("utf-8", errors="ignore")
    except Exception:
        return None


def first(p, *names):
    for n in names:
        if p.get(n) is not None:
            return p[n]
    return None


def _split_hostport(hp):
    """'h:443' -> ('h','443'); '[::1]:443' -> ('::1','443'); 'h:443,2000-3000' -> ('h','443,2000-3000')."""
    hp = hp.strip().rstrip("/")
    if hp.startswith("["):
        host, _, rest = hp[1:].partition("]")
        return host, rest.lstrip(":")
    host, sep, ports = hp.rpartition(":")
    return (host, ports) if sep else (hp, "")


def _parse_ports(ports):
    single, ranges = None, []
    for p in re.split(r"[,;]", ports or ""):
        p = p.strip()
        if p.isdigit():
            single = single or int(p)
        elif re.fullmatch(r"\d+[-:]\d+", p):
            ranges.append(p.replace("-", ":"))
    return single, ranges


@lru_cache(maxsize=None)
def parse_link(line):
    """-> {proto, host, port, user, q (параметры query), ranges, o (json vmess)} или None."""
    try:
        scheme, _, rest = line.partition("://")
        proto = {"hysteria2": "hy2"}.get(scheme.lower(), scheme.lower())
        if proto == "vmess":
            o = json.loads(b64decode_safe(rest))
            host, port, uid = str(o["add"]).strip(), int(o["port"]), str(o["id"])
            return {"proto": proto, "host": host, "port": port, "user": uid, "q": {}, "ranges": [], "o": o} \
                if host and port and uid else None
        main, _, query = rest.split("#", 1)[0].partition("?")
        q = {k.lower(): v[0] for k, v in parse_qs(query, keep_blank_values=True).items() if v}
        main = main.rstrip("/")
        if proto == "ss" and "@" not in main:                    # старый формат: всё в base64
            main = b64decode_safe(unquote(main)) or ""
        netloc = main if proto == "ss" else main.split("/", 1)[0]
        userinfo, _, hostport = netloc.rpartition("@")
        host, ports = _split_hostport(hostport)
        single, ranges = _parse_ports(ports)
        if proto == "hy2":                                       # port hopping
            _, r2 = _parse_ports(q.get("mport", ""))
            ranges += r2
            if not single and ranges:
                single = int(ranges[0].split(":")[0])
        if not (host and single):
            return None
        return {"proto": proto, "host": host, "port": single, "user": unquote(userinfo),
                "q": q, "ranges": ranges, "o": None}
    except Exception:
        return None


def host_port(line):
    L = parse_link(line)
    return (L["host"], L["port"]) if L else None


def dedupe_key(line):
    L = parse_link(line)
    return (L["proto"], L["user"], L["host"].lower(), L["port"]) if L else (line,)


def config_sni(line):
    L = parse_link(line)
    if not L:
        return ""
    src = L["o"] or L["q"]
    return str(first(src, "sni", "servername", "peer") or first(src, "host") or "").strip().lower()


def rename_config(line, name):
    L = parse_link(line)
    if L and L["proto"] == "vmess":
        o = dict(L["o"], ps=name)
        return "vmess://" + base64.b64encode(json.dumps(o, ensure_ascii=False, separators=(",", ":")).encode()).decode()
    return f"{line.split('#', 1)[0]}#{quote(name)}"


def extract_lines(raw):
    out = []
    for text in (raw, b64decode_safe(raw) if raw and "://" not in raw[:200] else None):
        for line in (text or "").splitlines():
            if line.strip().startswith(PROTOCOLS):
                out.append(line.strip())
    return list(dict.fromkeys(out))


# ============================================================
# КОНФИГ ЯДРА (xray / sing-box) ИЗ ССЫЛКИ
# ============================================================

def build_stream(net, sec, p, host):
    """p — параметры (type, path, host, servicename, mode, extra, sni, fp, alpn, pbk, sid, spx)."""
    net = str(net or "tcp").lower()
    net = {"raw": "tcp", "splithttp": "xhttp", "http": "h2"}.get(net, net)
    path, h = unquote(first(p, "path") or "/"), first(p, "host") or host
    s = {"network": net}
    if net == "ws":
        s["wsSettings"] = {"path": path, "headers": {"Host": h}}
    elif net == "grpc":
        s["grpcSettings"] = {"serviceName": unquote(first(p, "servicename") or "")}
    elif net == "httpupgrade":
        s["httpupgradeSettings"] = {"path": path, "host": h}
    elif net == "xhttp":
        xs = {"path": path, "host": h, "mode": first(p, "mode") or "auto"}
        try:
            extra = json.loads(first(p, "extra") or "null")
            if isinstance(extra, dict):
                xs["extra"] = extra
        except Exception:
            pass
        s["xhttpSettings"] = xs
    elif net == "h2":
        s["httpSettings"] = {"path": path, "host": [h]}
    sni = first(p, "sni", "servername") or host
    if sec == "reality":
        if not first(p, "pbk", "publickey"):
            return None                                           # reality без ключа не работает
        s["security"] = "reality"
        s["realitySettings"] = {"serverName": sni, "fingerprint": first(p, "fp", "fingerprint") or "chrome",
                                "publicKey": first(p, "pbk", "publickey"), "shortId": first(p, "sid", "shortid") or "",
                                "spiderX": first(p, "spx") or ""}
    elif sec == "tls":
        tls = {"serverName": sni, "allowInsecure": True}
        if first(p, "fp", "fingerprint"):
            tls["fingerprint"] = first(p, "fp", "fingerprint")
        if first(p, "alpn"):
            tls["alpn"] = [a for a in unquote(first(p, "alpn")).split(",") if a]
        s["security"], s["tlsSettings"] = "tls", tls
    else:
        s["security"] = "none"
    return s


def xray_outbound(L):
    proto, host, port, q = L["proto"], L["host"], L["port"], L["q"]
    if proto == "vmess":
        o = L["o"]
        net = str(o.get("net") or "tcp").lower()
        p = {"path": o.get("path"), "host": o.get("host"), "servicename": o.get("path"),
             "sni": o.get("sni") or o.get("host"), "alpn": o.get("alpn"), "fp": o.get("fp") or None}
        s = build_stream(net, "tls" if str(o.get("tls", "")).lower() == "tls" else "none",
                         {k: v for k, v in p.items() if v}, host)
        user = {"id": L["user"], "alterId": int(o.get("aid", 0) or 0), "security": o.get("scy") or "auto"}
        return {"protocol": "vmess", "settings": {"vnext": [{"address": host, "port": port, "users": [user]}]},
                "streamSettings": s}
    if proto in ("vless", "trojan"):
        p = dict(q)
        p.setdefault("fp", "chrome")
        s = build_stream(first(q, "type", "network", "net"), (first(q, "security") or ("tls" if proto == "trojan" else "none")).lower(), p, host)
        if s is None:
            return None
        if proto == "trojan":
            return {"protocol": "trojan", "settings": {"servers": [{"address": host, "port": port, "password": L["user"]}]},
                    "streamSettings": s}
        user = {"id": L["user"], "encryption": first(q, "encryption") or "none", "flow": first(q, "flow") or ""}
        return {"protocol": "vless", "settings": {"vnext": [{"address": host, "port": port, "users": [user]}]},
                "streamSettings": s}
    if proto == "ss":
        if "plugin" in q:                                         # obfs / v2ray-plugin xray не умеет
            return None
        creds = L["user"] if ":" in L["user"] else (b64decode_safe(L["user"]) or "")
        method, _, pw = creds.partition(":")
        if not (method and pw):
            return None
        return {"protocol": "shadowsocks", "settings": {"servers": [
            {"address": host, "port": port, "method": method.strip().lower(), "password": pw}]}}
    return None


def singbox_outbound(L):
    q = L["q"]
    if not L["user"]:
        return None
    alpn = first(q, "alpn")
    out = {"type": "hysteria2", "tag": "proxy", "server": L["host"], "server_port": L["port"], "password": L["user"],
           "tls": {"enabled": True, "server_name": first(q, "sni", "peer") or L["host"],
                   "insecure": str(first(q, "insecure", "allowinsecure") or "0").lower() in ("1", "true", "yes")
                   or bool(first(q, "pinsha256")),
                   "alpn": [a for a in unquote(alpn).split(",") if a] if alpn else ["h3"]}}
    if L["ranges"]:
        out["server_ports"] = L["ranges"]
        hop = first(q, "hop_interval", "hopinterval")
        if hop and str(hop).isdigit():
            out["hop_interval"] = f"{hop}s"
    if (first(q, "obfs") or "").lower() == "salamander":
        pw = first(q, "obfs-password", "obfs_password")
        if not pw:
            return None
        out["obfs"] = {"type": "salamander", "password": pw}
    return out


def build_core(line, port):
    """-> (бинарник, конфиг ядра с SOCKS на 127.0.0.1:port) или None."""
    L = parse_link(line)
    if not L:
        return None
    if L["proto"] == "hy2":
        ob = singbox_outbound(L)
        return (SINGBOX_BINARY, {"log": {"disabled": True}, "outbounds": [ob], "inbounds": [
            {"type": "socks", "tag": "in", "listen": "127.0.0.1", "listen_port": port}]}) if ob else None
    ob = xray_outbound(L) if L["proto"] in XRAY_SCHEMES else None
    return (XRAY_BINARY, {"log": {"loglevel": "none"}, "outbounds": [ob], "inbounds": [
        {"listen": "127.0.0.1", "port": port, "protocol": "socks", "settings": {"udp": False}}]}) if ob else None


# ============================================================
# JSON-ПОДПИСКИ (xray / sing-box, объект или массив) -> обычные ссылки
# Цепочки (dialerProxy / detour), kcp / quic и tcp с http-маскировкой не переводятся.
# ============================================================

def _one(v):
    return (v[0] if v else None) if isinstance(v, (list, tuple)) else v


def _hp(h):
    h = str(h).strip()
    return f"[{h}]" if ":" in h and not h.startswith("[") else h


def _qs(d):
    return "&".join(f"{k}={quote(str(v), safe='')}" for k, v in d.items() if v not in (None, ""))


def _xray_stream(ss):
    ss = ss or {}
    if (ss.get("sockopt") or {}).get("dialerProxy"):
        return None
    net, sec = str(ss.get("network") or "tcp").lower(), str(ss.get("security") or "none").lower()
    p = {"type": {"raw": "tcp", "splithttp": "xhttp", "http": "h2"}.get(net, net), "security": sec}
    key = {"ws": "wsSettings", "grpc": "grpcSettings", "xhttp": "xhttpSettings", "splithttp": "xhttpSettings",
           "httpupgrade": "httpupgradeSettings", "h2": "httpSettings", "http": "httpSettings"}.get(net)
    s = ss.get(key) or {} if key else {}
    if net == "tcp" or net == "raw":
        hdr = ((ss.get("tcpSettings") or ss.get("rawSettings") or {}).get("header") or {}).get("type")
        if hdr and str(hdr).lower() != "none":
            return None
    elif key is None:
        return None
    elif net == "grpc":
        p["serviceName"] = s.get("serviceName")
    else:
        p["path"] = s.get("path") or "/"
        p["host"] = _one(s.get("host")) or (s.get("headers") or {}).get("Host")
        if "xhttp" in p["type"]:
            p["mode"] = s.get("mode")
            if s.get("extra"):
                p["extra"] = json.dumps(s["extra"], ensure_ascii=False, separators=(",", ":"))
    if sec == "tls":
        t = ss.get("tlsSettings") or {}
        p.update(sni=t.get("serverName"), fp=t.get("fingerprint"), alpn=",".join(t.get("alpn") or []),
                 allowInsecure=1 if t.get("allowInsecure") else None)
    elif sec == "reality":
        r = ss.get("realitySettings") or {}
        p.update(sni=r.get("serverName"), fp=r.get("fingerprint"), pbk=r.get("publicKey") or r.get("password"),
                 sid=r.get("shortId"), spx=r.get("spiderX"))
    elif sec != "none":
        return None
    return p


def _singbox_stream(ob):
    tls, tr = ob.get("tls") or {}, ob.get("transport") or {}
    net = str(tr.get("type") or "tcp").lower()
    if net not in ("tcp", "ws", "grpc", "httpupgrade", "http"):
        return None
    p = {"type": "h2" if net == "http" else net, "security": "none"}
    if net == "grpc":
        p["serviceName"] = tr.get("service_name")
    elif net != "tcp":
        h = tr.get("headers") or {}
        p["path"] = _one(tr.get("path")) or "/"
        p["host"] = _one(tr.get("host")) or _one(h.get("Host") or h.get("host"))
    if tls.get("enabled"):
        rl = tls.get("reality") or {}
        p.update(security="reality" if rl.get("enabled") else "tls", sni=tls.get("server_name"),
                 fp=(tls.get("utls") or {}).get("fingerprint"), alpn=",".join(tls.get("alpn") or []),
                 allowInsecure=1 if tls.get("insecure") else None,
                 pbk=rl.get("public_key"), sid=rl.get("short_id"))
    return p


def _vmess_link(host, port, uid, aid, scy, p, remark):
    if p["security"] == "reality":
        return None
    o = {"v": "2", "ps": remark or "", "add": host, "port": str(port), "id": uid, "aid": str(aid or 0),
         "scy": scy or "auto", "net": p["type"], "type": "none", "host": p.get("host") or "",
         "path": (p.get("serviceName") if p["type"] == "grpc" else p.get("path")) or "",
         "tls": "tls" if p["security"] == "tls" else "", "sni": p.get("sni") or "",
         "alpn": p.get("alpn") or "", "fp": p.get("fp") or ""}
    return "vmess://" + base64.b64encode(json.dumps(o, ensure_ascii=False, separators=(",", ":")).encode()).decode()


def _ob_to_link(ob, remark):
    sb = "protocol" not in ob                                    # sing-box: поле type, плоские поля
    t = str(ob.get("type" if sb else "protocol") or "").lower()
    if ob.get("proxySettings") or ob.get("detour") or t not in (
            "vless", "vmess", "trojan", "shadowsocks", "hysteria", "hysteria2"):
        return None
    st = ob.get("settings") or {}
    node = ob if sb else (_one(st.get("vnext")) or _one(st.get("servers")) or st)
    host, port = (ob.get("server"), ob.get("server_port")) if sb else (node.get("address"), node.get("port"))
    user = node if sb else (_one(node.get("users")) or node)
    frag = f"#{quote(str(remark))}" if remark else ""
    if t in ("hysteria", "hysteria2"):
        tl = (ob.get("tls") or {}) if sb else ((ob.get("streamSettings") or {}).get("tlsSettings") or {})
        hs = (ob.get("streamSettings") or {}).get("hysteriaSettings") or {}
        pw = ob.get("password") if sb else hs.get("auth")
        if not sb and str(hs.get("version", 2)) != "2":
            return None
        ports = ob.get("server_ports")
        if not port and ports:
            port = str(_one(ports)).replace("-", ":").split(":")[0]
        if not (host and port and pw):
            return None
        q = {"sni": tl.get("server_name") or tl.get("serverName"), "alpn": ",".join(tl.get("alpn") or []),
             "insecure": 1 if (tl.get("insecure") or tl.get("allowInsecure")) else None}
        ob_obfs = ob.get("obfs") or {}
        if str(ob_obfs.get("type") or "").lower() == "salamander" and ob_obfs.get("password"):
            q.update({"obfs": "salamander", "obfs-password": ob_obfs["password"]})
        if ports:
            q["mport"] = ",".join(str(x).replace(":", "-") for x in ports)
        return f"hy2://{quote(str(pw), safe='')}@{_hp(host)}:{port}?{_qs(q)}{frag}"
    if not (host and port):
        return None
    if t == "shadowsocks":
        method, pw = node.get("method"), node.get("password")
        if ob.get("plugin") or not (method and pw):
            return None
        cred = base64.urlsafe_b64encode(f"{method}:{pw}".encode()).decode().rstrip("=")
        return f"ss://{cred}@{_hp(host)}:{port}{frag}"
    p = _singbox_stream(ob) if sb else _xray_stream(ob.get("streamSettings"))
    if p is None:
        return None
    if t == "trojan":
        pw = node.get("password")
        return f"trojan://{quote(str(pw), safe='')}@{_hp(host)}:{port}?{_qs(p)}{frag}" if pw else None
    uid = user.get("id") or user.get("uuid")
    if not uid:
        return None
    if t == "vmess":
        return _vmess_link(host, port, uid, user.get("alterId") or user.get("alter_id"), user.get("security"), p, remark)
    q = {"encryption": user.get("encryption") or "none", "flow": user.get("flow"), **p}
    return f"vless://{uid}@{_hp(host)}:{port}?{_qs(q)}{frag}"


def json_to_links(raw):
    texts = [raw or ""]
    if raw and not raw.lstrip().startswith(("{", "[")):
        dec = b64decode_safe(raw)
        if dec and dec.lstrip().startswith(("{", "[")):
            texts.append(dec)
    values = []
    for text in texts:
        try:
            values.append(json.loads(text.strip()))
            continue
        except Exception:
            pass
        for line in text.splitlines():
            if line.strip()[:1] in ("{", "["):
                try:
                    values.append(json.loads(line))
                except Exception:
                    pass
    links = []
    for val in values:
        for obj in (val if isinstance(val, list) else [val]):
            if isinstance(obj, str) and obj.startswith(PROTOCOLS):
                links.append(obj.strip())
            if not isinstance(obj, dict):
                continue
            remark = obj.get("remarks") or obj.get("remark") or obj.get("ps") or obj.get("name") or ""
            outs = obj.get("outbounds") if isinstance(obj.get("outbounds"), list) else \
                ([obj] if (obj.get("protocol") or obj.get("type")) else [])
            for ob in outs:
                try:
                    link = _ob_to_link(ob, remark) if isinstance(ob, dict) else None
                except Exception:
                    link = None
                if link:
                    links.append(link)
    return list(dict.fromkeys(links))


# ============================================================
# СКАЧИВАНИЕ ПОДПИСОК (HWID, смена User-Agent, повтор; на последней попытке — без проверки SSL)
# ============================================================

def short_name(url):
    n = re.sub(r"^https?://", "", url).split("/")[0]
    return n if len(n) <= 28 else n[:27] + "…"


async def fetch_source(session, url):
    last = None
    for attempt in range(FETCH_RETRIES):
        headers = {"User-Agent": FETCH_UAS[attempt % len(FETCH_UAS)], **(HWID_HEADERS if HWID_SPOOF else {})}
        try:
            async with session.get(url, headers=headers, allow_redirects=True,
                                   ssl=False if attempt == FETCH_RETRIES - 1 else None,
                                   timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as r:
                r.raise_for_status()
                raw = await r.text(errors="ignore")
            jl = json_to_links(raw)
            configs = list(dict.fromkeys(extract_lines(raw) + jl))
            if configs:
                print(f"[i] {SRC_EMOJI[url]} {short_name(url)}: {len(configs)}" + (f" (из JSON: {len(jl)})" if jl else ""))
                return url, configs
            last = "в ответе нет конфигов"
        except Exception as e:
            last = str(e) or type(e).__name__
        await asyncio.sleep(1.0)
    print(f"[!] {SRC_EMOJI[url]} {short_name(url)}: {str(last)[:60]}")
    return url, []


# ============================================================
# БЕЛЫЕ СПИСКИ РФ (метка 📶 и признак «вход в РФ»)
# ============================================================

_lte_sni = set(LTE_SNI_DOMAINS)
_lte_nets = {}                      # (версия, длина префикса) -> {сети как числа}


def _lte_add_net(tok):
    try:
        net = ipaddress.ip_network(tok, strict=False)
    except ValueError:
        return False
    _lte_nets.setdefault((net.version, net.prefixlen), set()).add(int(net.network_address))
    return True


def lte_ip_match(ip):
    try:
        a = ipaddress.ip_address(ip)
    except Exception:
        return False
    bits = a.max_prefixlen
    return any((int(a) & ((((1 << pl) - 1) << (bits - pl)) if pl else 0)) in nets
               for (ver, pl), nets in _lte_nets.items() if ver == a.version)


def lte_sni_match(sni):
    s = (sni or "").strip().lower().rstrip(".")
    while "." in s:
        if s in _lte_sni:
            return True
        s = s.partition(".")[2]
    return False


def is_lte(line, ip=None):
    return lte_sni_match(config_sni(line)) or bool(ip and lte_ip_match(ip))


async def load_lte_lists(session):
    async def get(kind):
        for _ in range(3):
            try:
                async with session.get(LTE_LISTS_URL % kind, headers={"User-Agent": "Mozilla/5.0"},
                                       timeout=aiohttp.ClientTimeout(total=30)) as r:
                    r.raise_for_status()
                    return await r.text(errors="ignore")
            except Exception:
                await asyncio.sleep(1.5)
        return ""
    sni_text, ip_text = await asyncio.gather(get("sni"), get("ip"))
    n_sni = n_ip = 0
    for text, is_sni in ((sni_text, True), (ip_text, False)):
        for line in text.splitlines():
            for tok in re.split(r"[\s,;]+", line.split("#", 1)[0].strip().lower()):
                tok = tok.lstrip("*.").rstrip(".") if is_sni else tok
                if not tok:
                    continue
                if _lte_add_net(tok):
                    n_ip += 1
                elif is_sni and "/" not in tok and tok not in _lte_sni:
                    _lte_sni.add(tok)
                    n_sni += 1
    print(f"[i] {LTE_TAG} белые списки: SNI +{n_sni} (всего {len(_lte_sni)}), IP/CIDR +{n_ip}"
          + ("" if sni_text and ip_text else " — часть списков не скачалась"))


# ============================================================
# DNS, TCP, ЗАПУСК ЯДРА
# ============================================================

_dns = {}


async def resolve_ip(host):
    if host not in _dns:
        try:
            ipaddress.ip_address(host)
            _dns[host] = host
        except ValueError:
            try:
                infos = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(
                    host, None, family=socket.AF_INET, type=socket.SOCK_STREAM), 5.0)
                _dns[host] = infos[0][4][0] if infos else None
            except Exception:
                _dns[host] = None
    return _dns[host]


async def tcp_ping(line):
    hp = host_port(line)
    if not hp:
        return None
    for _ in range(TCP_TRIES):
        t0 = time.monotonic()
        try:
            _, w = await asyncio.wait_for(asyncio.open_connection(*hp), TCP_TIMEOUT)
        except Exception:
            continue
        w.close()
        return (time.monotonic() - t0) * 1000
    return None


async def tcp_filter(configs):
    """-> (живые [(config, мс)], мёртвые [config])."""
    sem, alive, dead = asyncio.Semaphore(TCP_CONCURRENCY), [], []

    async def worker(c):
        async with sem:
            ms = await tcp_ping(c)
        (alive.append((c, ms)) if ms is not None else dead.append(c))

    await asyncio.gather(*(worker(c) for c in configs))
    return alive, dead


_ports = None


@asynccontextmanager
async def running_core(line):
    port = await _ports.get()
    proc = tmp = None
    try:
        spec = build_core(line, port)
        if not spec:
            yield None
            return
        fd, tmp = tempfile.mkstemp(suffix=".json", prefix="core_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(spec[1], f)
        proc = await asyncio.create_subprocess_exec(spec[0], "run", "-c", tmp, stdout=asyncio.subprocess.DEVNULL,
                                                    stderr=asyncio.subprocess.DEVNULL)
        deadline, ok = time.monotonic() + CORE_START_TIMEOUT, False
        while time.monotonic() < deadline and proc.returncode is None and not ok:
            try:
                _, w = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), 0.5)
                w.close()
                ok = True
            except Exception:
                await asyncio.sleep(0.05)
        yield port if ok else None
    finally:
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), 3)
            except Exception:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
        if tmp:
            try:
                os.remove(tmp)
            except Exception:
                pass
        await _ports.put(port)


# ============================================================
# МЯГКАЯ ПРОВЕРКА ЧЕРЕЗ ПРОКСИ
# 1) шлюз: PROBE_URLS параллельно, хватает PROBE_MIN_OK (до GATE_TRIES попыток на том же ядре);
# 2) параллельно: тёплые запросы по тому же соединению + Cloudflare trace (IP/страна) + ipwho (город по-русски);
# 3) для прошедших — Gemini. Балл = медиана пинга (+ скорость, если CHECK_SPEED).
# ============================================================

async def _get(s, url, timeout=None, min_bytes=0, headers=None):
    t0 = time.monotonic()
    kw = {"timeout": aiohttp.ClientTimeout(total=timeout)} if timeout else {}
    async with s.get(url, headers=headers, **kw) as r:
        if r.status not in (200, 204):
            raise ValueError(f"status {r.status}")
        body = await r.read()
    if (r.status == 204 and body) or len(body) < min_bytes:
        raise ValueError("подмена ответа / короткое тело")
    return (time.monotonic() - t0) * 1000


async def fetch_trace(s):
    try:
        async with s.get("https://www.cloudflare.com/cdn-cgi/trace", timeout=aiohttp.ClientTimeout(total=8)) as r:
            d = dict(l.split("=", 1) for l in (await r.text()).splitlines() if "=" in l)
        ipaddress.ip_address(d["ip"].strip())
        loc = d.get("loc", "").strip().upper()
        return d["ip"].strip(), loc if len(loc) == 2 and loc.isalpha() and loc != "XX" else ""
    except Exception:
        return None


async def fetch_geo(s):
    """(страна, город, ip) выхода — ipwho.is прямо через прокси."""
    try:
        async with s.get("https://ipwho.is/?lang=ru", timeout=aiohttp.ClientTimeout(total=8)) as r:
            d = await r.json(content_type=None)
        if d.get("success"):
            return (d.get("country_code") or "").upper(), d.get("city") or "", d.get("ip")
    except Exception:
        pass
    return None


async def check_gemini(s):
    try:
        async with s.get(GEMINI_URL, headers=GEMINI_HEADERS, timeout=aiohttp.ClientTimeout(total=12)) as r:
            return r.status == 200 and GEMINI_MARKER in await r.text(errors="ignore")
    except Exception:
        return False


async def _warm(s):
    await asyncio.sleep(IDLE_PAUSE)
    lat, fails = [], 0
    for i in range(WARM_REQUESTS):
        try:
            lat.append(await _get(s, PROBE_URLS[i % len(PROBE_URLS)]))
        except Exception:
            fails += 1
    return lat, fails


async def _probe(line, port):
    """-> (балл мс, None) или (None, причина отказа)."""
    conn = aiohttp_socks.ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
    async with aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=12)) as s:
        for _ in range(GATE_TRIES):
            res = await asyncio.gather(*(_get(s, u, GATE_TIMEOUT) for u in PROBE_URLS), return_exceptions=True)
            gate = [r for r in res if not isinstance(r, Exception)]
            if len(gate) >= PROBE_MIN_OK:
                break
            await asyncio.sleep(0.5)
        else:
            return None, "прокси не пропускает трафик"

        (warm, fails), tr, geo = await asyncio.gather(_warm(s), fetch_trace(s), fetch_geo(s))
        if fails > WARM_MAX_FAILS:
            return None, "обрывы на повторных запросах (keep-alive)"
        if tr and _my_ip and tr[0] == _my_ip:
            return None, "выходной IP совпал с моим (прокси не применился)"

        score = statistics.median(warm or gate)
        if CHECK_SPEED:
            try:
                dl = await _get(s, SPEED_URL, 15, 450_000)
            except Exception:
                return None, "скачивание не прошло"
            if dl > SPEED_MAX_MS:
                return None, "слишком медленная загрузка"
            score += dl * SPEED_WEIGHT
        if score > MAX_PING_MS:
            return None, "балл выше MAX_PING_MS"

        gem = await check_gemini(s) if CHECK_GEMINI else False
        cc = (tr[1] if tr else "") or (geo[0] if geo else "")
        _info[line] = {"ip": (tr[0] if tr else None) or (geo[2] if geo else None), "cc": cc,
                       "city": geo[1] if geo and geo[0] == cc else "", "gem": gem}
        return score, None


async def real_check(line):
    if not build_core(line, 1):
        return _reject("конфиг не разобран (парсер)")
    try:
        async with running_core(line) as port:
            if port is None:
                return _reject("ядро не поднялось")
            score, why = await asyncio.wait_for(_probe(line, port), CHECK_LIMIT)
    except Exception:
        return _reject("ошибка / таймаут проверки")
    return score if score is not None else _reject(why)


async def check_all(candidates):
    """-> (рабочие [(config, балл)], нерабочие [config], непроверенные [config] — после ранней остановки)."""
    sem, stop = asyncio.Semaphore(CONCURRENCY), asyncio.Event()
    limit = TARGET_COUNT * EARLY_STOP_MULT if TARGET_COUNT and EARLY_STOP_MULT else 0
    working, failed, skipped, done = [], [], [], 0

    async def worker(c):
        nonlocal done
        async with sem:
            if stop.is_set():
                skipped.append(c)
                return
            score = await real_check(c)
            done += 1
            if score is not None:
                working.append((c, score))
                if limit and len(working) >= limit and not stop.is_set():
                    stop.set()
                    print(f"    проверено {done}/{len(candidates)} ✓{len(working)} — хватит, стоп")
            else:
                failed.append(c)
            if done % PROGRESS_EVERY == 0:
                print(f"    [{elapsed()}] проверено {done}/{len(candidates)} ✓{len(working)}")

    await asyncio.gather(*(worker(c) for c in candidates))
    return working, failed, skipped


# ============================================================
# ГЕО ВХОДА (ip-api batch): страна и «org as» — для каскадов и для поиска входов в РФ
# ============================================================

_entry_geo = {}


async def entry_geo_batch(session, ips):
    ips = sorted({i for i in ips if i and i not in _entry_geo})
    for n, i in enumerate(range(0, len(ips), 100)):
        if n:
            await asyncio.sleep(4.5)                              # лимит ip-api: 15 batch в минуту
        for _ in range(3):
            try:
                async with session.post("http://ip-api.com/batch?fields=status,query,countryCode,org,as",
                                        json=ips[i:i + 100], timeout=aiohttp.ClientTimeout(total=20)) as r:
                    if r.status == 429:
                        await asyncio.sleep(12)
                        continue
                    if r.status != 200:
                        break
                    for d in await r.json(content_type=None):
                        if d.get("status") == "success" and d.get("countryCode"):
                            _entry_geo[d["query"]] = (d["countryCode"].upper(), f'{d.get("org", "")} {d.get("as", "")}'.lower())
                break
            except Exception:
                await asyncio.sleep(3)


# ============================================================
# СПАСЕНИЕ ВХОДОВ В РФ: TCP с российских узлов check-host.net
# Серверы в РФ нередко режут чужие IP: из США «мёртвые», с российского телефона — живые.
# Берём не прошедшие проверку конфиги, вход которых в РФ (белый список IP / .ru / страна по ip-api),
# и проверяем с российских узлов. UDP (hy2) так не проверить — их не трогаем.
# ============================================================

_ru_nodes = []
_CH = {"Accept": "application/json"}


async def ru_tcp_ok(session, hostport):
    """True/False — доступен ли host:port с российских узлов; None — не удалось узнать."""
    params = [("host", hostport)] + [("node", n) for n in _ru_nodes]
    for attempt in range(3):
        try:
            async with session.get(f"{CHECK_HOST_API}/check-tcp", params=params, headers=_CH,
                                   timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 429:
                    await asyncio.sleep(4 * (attempt + 1))
                    continue
                if r.status != 200:
                    return None
                rid = (await r.json(content_type=None)).get("request_id")
            break
        except Exception:
            await asyncio.sleep(1.5)
    else:
        return None
    if not rid:
        return None
    deadline = time.monotonic() + RU_RESULT_WAIT
    await asyncio.sleep(RU_FIRST_POLL)
    while True:
        res = {}
        try:
            async with session.get(f"{CHECK_HOST_API}/check-result/{rid}", headers=_CH,
                                   timeout=aiohttp.ClientTimeout(total=15)) as r:
                res = await r.json(content_type=None) or {}
        except Exception:
            pass
        ok = sum(1 for v in res.values() if v and isinstance(v[0], dict) and "time" in v[0] and "error" not in v[0])
        answered = sum(1 for v in res.values() if v is not None)
        total = max(len(res), len(_ru_nodes))
        need = min(RU_MIN_OK, total)
        if ok >= need:
            return True
        if answered and ok + (total - answered) < need:
            return False
        if time.monotonic() >= deadline:
            return False if answered else None
        await asyncio.sleep(RU_POLL_EVERY)


async def rescue_ru(session, dead):
    """dead — конфиги, не прошедшие TCP/проверку. Возвращает [(config, ip входа)], подтверждённые из РФ."""
    dead = [c for c in dead if host_port(c) and parse_link(c)["proto"] != "hy2"]
    await asyncio.gather(*(resolve_ip(host_port(c)[0]) for c in dead))
    ip_of = {c: _dns.get(host_port(c)[0]) for c in dead}
    dead = [c for c in dead if ip_of[c]]

    sure = [c for c in dead if lte_ip_match(ip_of[c]) or host_port(c)[0].lower().endswith(RU_TLDS)]
    sure_set = set(sure)
    rest = [c for c in dead if c not in sure_set]
    ips = list(dict.fromkeys(ip_of[c] for c in rest))[:RU_GEO_MAX_IPS]
    if ips:
        stage(f"Страна входа у {len(ips)} непрошедших серверов (ищу входы в РФ)...")
        await entry_geo_batch(session, ips)
    cands = sure + [c for c in rest if _entry_geo.get(ip_of[c], ("",))[0] == "RU"]
    cands = cands[:RU_MAX_CHECKS]
    if not cands:
        return []

    try:
        async with session.get(f"{CHECK_HOST_API}/nodes/hosts", headers=_CH, timeout=aiohttp.ClientTimeout(total=15)) as r:
            nodes = (await r.json(content_type=None)).get("nodes") or {}
        _ru_nodes[:] = sorted(n for n in nodes if str(n).lower().startswith("ru"))[:RU_NODES_MAX]
    except Exception:
        _ru_nodes[:] = []
    if not _ru_nodes:
        print("[!] check-host.net: российские узлы недоступны — входы в РФ не перепроверены")
        return []

    stage(f"Входы в РФ: {len(cands)} конфигов перепроверяю с российских узлов...")
    sem, good = asyncio.Semaphore(RU_CONCURRENCY), []

    async def one(c):
        h, p = host_port(c)
        async with sem:
            ok = await ru_tcp_ok(session, f"[{h}]:{p}" if ":" in h else f"{h}:{p}")
        if ok:
            good.append((c, ip_of[c]))

    await asyncio.gather(*(one(c) for c in cands))
    print(f"[i] Из РФ достучались: {len(good)} из {len(cands)}")
    return good


# ============================================================
# ОТБОР: лимиты на ip:порт / выходной IP / подсеть /24
# ============================================================

async def select_best(items):
    """items — [(config, балл)] по возрастанию балла."""
    await asyncio.gather(*(resolve_ip(host_port(c)[0]) for c, _ in items if host_port(c)))
    ep, ex, sub, out = Counter(), Counter(), Counter(), []
    for c, score in items:
        if TARGET_COUNT and len(out) >= TARGET_COUNT:
            break
        hp = host_port(c)
        ip = (_dns.get(hp[0]) if hp else None) or (hp[0] if hp else "")
        exit_ip = (_info.get(c) or {}).get("ip")
        net24 = ".".join(ip.split(".")[:3]) if re.fullmatch(r"\d+(\.\d+){3}", ip) else None
        if MAX_PER_ENDPOINT and hp and ep[(ip, hp[1])] >= MAX_PER_ENDPOINT:
            _reject("лимит на ip:порт")
            continue
        if MAX_PER_EXIT_IP and exit_ip and ex[exit_ip] >= MAX_PER_EXIT_IP:
            _reject("лимит на выходной IP")
            continue
        if MAX_PER_SUBNET and net24 and sub[net24] >= MAX_PER_SUBNET:
            _reject("лимит на подсеть /24")
            continue
        ep[(ip, hp[1] if hp else 0)] += 1
        if exit_ip:
            ex[exit_ip] += 1
        if net24:
            sub[net24] += 1
        out.append((c, score, ip))
    return out


# ============================================================
# MAIN
# ============================================================

async def fetch_my_ip(session):
    for url in ("https://api.ipify.org", "https://icanhazip.com"):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                ip = (await r.text()).strip()
            ipaddress.ip_address(ip)
            return ip
        except Exception:
            pass
    return None


def interleave(a, b):
    """a1, b1, a2, b2, ... — чтобы hy2 не оказались в хвосте и не отрезались ранней остановкой."""
    return [x for pair in itertools.zip_longest(a, b) for x in pair if x is not None]


def write_summary(lines):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass


def print_fail_reasons():
    if _fail:
        print("\n[i] Причины отказов:")
        for reason, n in _fail.most_common():
            print(f"    {n:>5}  {reason}")


async def main():
    global _my_ip, _ports
    try:
        sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
    except Exception:
        pass
    _ports = asyncio.Queue()
    for i in range(CONCURRENCY):
        _ports.put_nowait(BASE_LOCAL_PORT + i)

    winter = winter_on()
    print(f"[i] Режим: {TITLE} ({MODE}), источников: {len(SOURCES)}" + (", ❄️ зима" if winter else ""))
    if not shutil.which(XRAY_BINARY):
        print(f"[x] {XRAY_BINARY} не найден в PATH — проверять нечем.")
        return
    hy2_on = CHECK_HY2 and shutil.which(SINGBOX_BINARY) is not None
    if CHECK_HY2 and not hy2_on:
        print(f"[!] {SINGBOX_BINARY} не найден в PATH — hy2 проверяться не будет")

    async with aiohttp.ClientSession() as session:
        _my_ip = await fetch_my_ip(session)
        print(f"[i] Мой IP: {_my_ip or 'не определён'}")

        # ---------- 1. подписки ----------
        lte_task = asyncio.ensure_future(load_lte_lists(session))
        stage("Скачиваю подписки...")
        source_of, all_configs = {}, []
        for url, cfgs in await asyncio.gather(*(fetch_source(session, u) for _, u in SOURCES)):
            for c in cfgs:
                source_of.setdefault(dedupe_key(c), url)
                all_configs.append(c)

        # ---------- 2. дубли (закреплённые не трогаем) ----------
        pinned = [c.strip() for c in PINNED_CONFIGS if c.strip()]
        seen = {dedupe_key(c) for c in pinned if c.startswith(PROTOCOLS)}
        unique = []
        for c in all_configs:
            k = dedupe_key(c)
            if k not in seen:
                seen.add(k)
                unique.append(c)
        runnable = [c for c in unique if build_core(c, 1)]        # то, что ядро реально сможет запустить
        xray_c = [c for c in runnable if parse_link(c)["proto"] in XRAY_SCHEMES]
        hy2_c = [c for c in runnable if parse_link(c)["proto"] == "hy2"] if hy2_on else []
        print(f"[i] Скачано {len(all_configs)}, уникальных {len(unique)} (xray {len(xray_c)}, hy2 {len(hy2_c)}, "
              f"без проверки {len(unique) - len(xray_c) - len(hy2_c)})")
        if not (xray_c or hy2_c):
            print("[x] Нет конфигов для проверки.")
            return

        # ---------- 3. TCP -> ядро ----------
        stage(f"TCP: {len(xray_c)}...")
        alive, tcp_dead = await tcp_filter(xray_c)
        alive.sort(key=lambda x: x[1])
        print(f"[i] TCP ок: {len(alive)} из {len(xray_c)}")
        candidates = interleave([c for c, _ in alive], hy2_c)

        stage(f"Проверка через ядро: {len(candidates)} (hy2: {len(hy2_c)})...")
        working, failed, skipped = await check_all(candidates)
        print(f"[✓] Рабочих: {len(working)} (hy2: {sum(1 for c, _ in working if parse_link(c)['proto'] == 'hy2')})")
        working.sort(key=lambda x: x[1])

        # ---------- 4. входы в РФ, не прошедшие проверку из США ----------
        await lte_task
        soft = []
        if RU_RESCUE:
            soft = (await rescue_ru(session, tcp_dead + failed))[:SOFT_MAX]

        chosen = await select_best(working)
        print(f"[i] В подписку: {len(chosen)} проверенных + {len(soft)} {SOFT_TAG}")
        if not (chosen or soft):
            print("[x] Рабочих конфигов нет.")
            print_fail_reasons()
            return

        # ---------- 5. имена ----------
        await entry_geo_batch(session, [ip for _, _, ip in chosen])
        items, cascades, gemini_n = [], 0, 0

        def src_tag(c):
            return SRC_EMOJI.get(source_of.get(dedupe_key(c)), "")

        for c, score, ip in chosen:
            info = _info.get(c, {})
            cc, eg = info.get("cc"), _entry_geo.get(ip)
            if not cc and eg:                                   # страну выхода не узнали — берём страну входа
                cc = eg[0]
            name = geo_name(cc, info.get("city")) if cc else "🌐 Неизвестно"
            if info.get("cc") and eg and ip != info.get("ip") and eg[0] != info["cc"].upper() \
                    and not any(w in eg[1] for w in CDN_WORDS):
                name, cascades = f"{flag(eg[0])} -> {name}", cascades + 1   # каскад: вход ≠ выход
            tags = ([speed_tag(score)] if winter else []) + ([LTE_TAG] if is_lte(c, ip) else [])
            if info.get("gem"):
                tags.append(GEMINI_TAG)
                gemini_n += 1
            items.append((country_name(cc) if cc else "я_Неизвестно", 0, score,
                          rename_config(c, " ".join([name] + tags + [src_tag(c)]).strip())))

        for c, ip in soft:
            cc = _entry_geo.get(ip, ("RU",))[0]
            tags = ([LTE_TAG] if is_lte(c, ip) else []) + [SOFT_TAG]
            items.append((country_name(cc), 1, 0, rename_config(c, " ".join([geo_name(cc)] + tags + [src_tag(c)]))))

        items.sort(key=lambda x: x[:3])                         # страна -> проверенные раньше 🔸 -> балл
        renamed = [x[3] for x in items]

    # ---------- 6. сохраняем ----------
    final = (winter_header(pinned) if winter else pinned) + renamed
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(final) + "\n", encoding="utf-8")
    print(f"\n[✓] Готово за {elapsed()}: {len(final)} строк (закр. {len(pinned)} + {len(renamed)}), "
          f"каскадов {cascades}, {GEMINI_TAG} {gemini_n}\n[✓] Файл: {OUTPUT_FILE}")
    print_fail_reasons()

    # ---------- 7. нерабочие по источникам (смайлик = как в названиях конфигов) ----------
    ok_set = {c for c, _ in working} | {c for c, _ in soft}
    skipped_set, stats = set(skipped), defaultdict(lambda: [0, 0])
    for c in xray_c + hy2_c:
        if c not in skipped_set:
            s = stats[source_of.get(dedupe_key(c))]
            s[0] += 1
            s[1] += c not in ok_set
    rows = sorted(((u, t, b) for u, (t, b) in stats.items() if u and t), key=lambda r: r[2] / r[1], reverse=True)
    if rows:
        print("\n[i] Нерабочих по источникам (худшие сверху):")
        for u, t, b in rows:
            print(f"  {SRC_EMOJI.get(u, '  ')} {short_name(u)}: {b}/{t} ({b * 100 // t}%)")
        print(f"\n[!] Самый слабый: {SRC_EMOJI.get(rows[0][0], '')} {short_name(rows[0][0])}")

    write_summary([f"### PizdukVPN {TITLE} ❄️", f"- Время: **{elapsed()}**",
                   f"- В подписке: **{len(renamed)}** (проверенных {len(chosen)}, {SOFT_TAG} {len(soft)}, закреплённых {len(pinned)})",
                   f"- Каскадов: {cascades}, {GEMINI_TAG}: {gemini_n}"] +
                  [f"- {n} × {r}" for r, n in _fail.most_common(5)] +
                  [f"- {SRC_EMOJI.get(u, '')} {short_name(u)}: {b}/{t} нерабочих" for u, t, b in rows[:3]])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Остановлено.")
