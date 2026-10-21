#!/usr/bin/env python3

import asyncio
import aiohttp
import aiohttp_socks
import base64
import ipaddress
import json
import re
import shutil
import socket
import tempfile
import os
import itertools
import time

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote


# ============================================================
# ИСТОЧНИКИ — НЕ МЕНЯТЬ
# ============================================================

SOURCES = [
    "https://freevpnhappcluchi.duckdns.org/sub/cwolxcvx5lmoe59v",
    "https://quorteam.vspboost.ru/1oRtg1/QuorVPN",
    "https://gidroksi.fun/black-list",
    "https://raw.githubusercontent.com/gazeta404/rain_vpn_sub/main/subscribe.txt",
    "https://pozor.bond/sub/85seabksu3tv",
    "https://raw.githubusercontent.com/gooseteam-hackers/freevpn-cracks/refs/heads/main/subscription_auto.txt",
    "https://bobrrvpn.neocities.org/blacklist.txt",
    "https://github.com/Remiuc0ff/vpn-hiddifycode/raw/refs/heads/main/allhiddifyvpn",
]


# ============================================================
# ЗАКРЕПЛЁННЫЕ КОНФИГИ — добавляются в начало БЕЗ проверки
# ============================================================

PINNED_CONFIGS = [
    "#profile-title: PizDukVPN ЧС🏴",
    "#announce: base64: 8J+UpdCi0LXQu9C10LPRgNCw0Lwg0LrQsNC90LDQuzogQFBpem1vZPCfpboK8J+lsNCQ0LLRgtC+0L7QsdC90L7QstC70LXQvdC40LUg0YDQsNC3INCyIDYg0YfQsNGB0L7QsvCfmLE=",
    "#profile-web-page-url: https://t.me/PizMod",
    "#support-url: https://t.me/Harachok",
    "#profile-update-interval: 6",
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@qq.utiltools.site:443?security=reality&encryption=none&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&headerType=none&fp=qq&type=tcp&flow=xtls-rprx-vision&sni=qq.utiltools.site#%F0%9F%91%89%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B7%F0%9F%87%BA%20%28telegram-only%29",
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@78.159.250.214:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=qq.utiltools.site&fp=firefox&security=reality&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&sid=00000000#%F0%9F%91%89%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B7%F0%9F%87%BA%20%D1%8D%D1%82%D0%BE%202%20%28telegram-only%29",
    "vless://5d7e07ba-f460-4638-af79-bbcde67fcb6b@rus1.justnable.xyz:8443/?type=xhttp&encryption=none&flow=&path=%2Fxh&mode=auto&sni=www.asus.com&fp=firefox&security=reality&pbk=xlXuN8KDdbqGEsaj1m2D8NUnR5d2oeo5TT71RSMmfxY&sid=#%F0%9F%87%B7%F0%9F%87%BA%20%D0%9E%2C%20%D1%83%D1%80%D0%B0%2C%20%D0%B5%D1%81%D1%82%D1%8C%20%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%BD%D0%B5%D1%82%20%F0%9F%8C%90",
    "vless://95a608b6-bff1-4e10-bb61-0a39f221bb7d@fitindoor.net:2053/?type=xhttp&encryption=none&flow=&host=fitindoor.net&path=%2Fapi%2Fv1%2Fupload&mode=auto&security=tls&sni=fitindoor.net&alpn=h2%2Chttp%2F1.1&fp=firefox#%F0%9F%87%B7%F0%9F%87%BA%20%E0%BC%BA%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F%20%E0%BC%BB%20%F0%9F%93%B6",
    "vless://95a608b6-bff1-4e10-bb61-0a39f221bb7d@randomquaint.net:2053/?type=xhttp&encryption=none&flow=&host=randomquaint.net&path=%2Fapi%2Fv1%2Fupload&mode=auto&security=tls&sni=randomquaint.net&alpn=h2%2Chttp%2F1.1&fp=firefox#%F0%9F%87%B7%F0%9F%87%BA%20%E0%BC%BA%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F%20%E0%BC%BB%20%F0%9F%9B%B0",
    "vless://068c73f5-c2fc-4579-96be-6e37cfcf58ed@193.233.220.203:8443/?type=xhttp&encryption=none&flow=&path=%2Fxhttp&mode=auto&sni=cdn-us.cahmes.space&fp=firefox&security=reality&pbk=KZejN2d1cwCrITHNxFYQVZ4rpMTZzHgJd9p30MZm_3k&sid=6bd33a75ebc0f26e#%F0%9F%87%BA%F0%9F%87%B8%20%D0%A1%D0%A8%D0%90%20%F0%9F%9F%A2Steam",
    "vless://068c73f5-c2fc-4579-96be-6e37cfcf58ed@us-05.avroraservice.online:8443/?type=xhttp&encryption=none&flow=&path=%2Fxhttp&mode=stream-one&sni=cdn-us.cahmes.space&fp=chrome&security=reality&pbk=KZejN2d1cwCrITHNxFYQVZ4rpMTZzHgJd9p30MZm_3k&sid=6bd33a75ebc0f26e#%F0%9F%87%BA%F0%9F%87%B8%20%E0%BC%BA%20%D0%A1%D0%A8%D0%90%20%E0%BC%BB%20%F0%9F%97%BD",
    "vmess://eyJhZGQiOiJjZi4wc20uY29tIiwiYWlkIjoiMCIsImFscG4iOiIiLCJmcCI6IiIsImhvc3QiOiJ2bWVzcy5sYnc2NjYuZHBkbnMub3JnIiwiaWQiOiIwY2Y2ZDk3MC0zZjFkLTRhYWUtYTk4OS05MmE4Zjc2YWUzZGIiLCJuZXQiOiJ3cyIsInBhdGgiOiIvd3M/ZWRcdTAwM2QyMDQ4IiwicG9ydCI6IjgwIiwicHMiOiLwn4e68J+HuCDinKYg0KHQqNCQIOKcpiDwn4yAIiwic2N5IjoiYXV0byIsInNuaSI6IiIsInRscyI6IiIsInR5cGUiOiIiLCJ2IjoiMiJ9",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTprMWRCT21PQjRvcWk3VW1wMzdhMWJR@82.38.31.212:8080#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20YT%E2%9C%85",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTprMWRCT21PQjRvcWk3VW1wMzdhMWJR@82.38.31.178:8080#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTprMWRCT21PQjRvcWk3VW1wMzdhMWJR@82.38.31.180:8080#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTprMWRCT21PQjRvcWk3VW1wMzdhMWJR@82.38.31.220:8080#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTprMWRCT21PQjRvcWk3VW1wMzdhMWJR@82.38.31.204:8080#%E2%9C%A6%20%F0%9F%87%B3%F0%9F%87%B1%20%E2%9C%A7%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%E2%9C%A7%20%F0%9F%87%B3%F0%9F%87%B1%20%E2%9C%A6",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTprMWRCT21PQjRvcWk3VW1wMzdhMWJR@82.38.31.195:8080#%E2%9F%A1%20%F0%9F%87%B3%F0%9F%87%B1%20%E2%9C%A6%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%E2%9C%A6%20%F0%9F%87%B3%F0%9F%87%B1%20%E2%9F%A1",
    "ss://YWVzLTEyOC1nY206MzY1M2E4ZTdkNDk1NmI1MjNlMThkYjQ3ZTc0OWFmMzA@62.210.26.134:12571#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpvWklvQTY5UTh5aGNRVjhrYTNQYTNB@82.38.31.54:8080#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20ss",
    "vless://b24ad12f-f6ce-4f0b-a264-d58a76104026@84.32.52.14:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=nl1.spidermanshopping.com&fp=firefox&security=reality&pbk=jIq_COD-tIXTvgDn-TslFGtB_a8HVgUOOIlUByv8fkg&sid=8718c58d3d51db59#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B",
    "hy2://p7Q76LzlnS4hIzr1W3staBOnUe_WwSkR@130.49.161.70:443/?hop_interval=10&sni=hy2.aspidnet.xyz&obfs=salamander&obfs-password=rG07s3COMIEvdnQipRyWzx_H_2xygNC3#🇳🇱 Нидерланды",
    "vless://3679bafc-b71b-4129-a196-33dfc92898a6@demw.verymad.net:27439/?type=tcp&encryption=none&flow=&sni=www.vk.com&fp=firefox&security=reality&pbk=Re0aWbYgk775QZ2eiIzh9fwPANq8HfLlrp9vbTC8vXQ&sid=60e64f9f8724c0#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%232",
    "vmess://eyJhZGQiOiJkZS1kMjFlNTZjMTNjLnNoYW1hbmFwcC5vbmxpbmUiLCJhaWQiOiIwIiwiYWxwbiI6IiIsImZwIjoiIiwiaG9zdCI6ImRlLWQyMWU1NmMxM2Muc2hhbWFuYXBwLm9ubGluZTozMzc0NCIsImlkIjoiYjNhMTEwNjgtMWE3ZS00NjQzLTg1ZGUtN2M4MmNjZTQ2OTQzIiwibmV0Ijoid3MiLCJwYXRoIjoiL1NoYW1hblZNRVNTMjAyNiIsInBvcnQiOiIzMzc0NCIsInBzIjoi8J+HqfCfh6og0JPQtdGA0LzQsNC90LjRjyIsInNjeSI6ImF1dG8iLCJzbmkiOiIiLCJ0bHMiOiIiLCJ0eXBlIjoiIiwidiI6IjIifQ==",
    "vless://07104d25-afc5-4b3b-a871-c729c57de047@2.27.248.195:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=ded.remnahoysry.ru&fp=firefox&security=reality&pbk=Abp__UEbRjj_fRvYa_u-B-I8XoHVUkGmc1ofMBMqHT4&sid=#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F",
    "vless://2f35965a-9a9b-45fd-ba32-987296dfb6be@150.40.126.18:443/?type=grpc&encryption=none&flow=&serviceName=node.v2.ObjectService&sni=rs1.univesalsrv.com&fp=chrome&security=reality&pbk=upIzyaSbVz2ZK6KfGtXmPl_-sCwn8XLDyFDH5CsL9iY&sid=ed0cd5cc2e26e6e7#%F0%9F%87%B7%F0%9F%87%B8%20%EA%A7%81%20%D0%A1%D0%B5%D1%80%D0%B1%D0%B8%D1%8F%20%EA%A7%82%20%E2%9A%A1",
    "vless://2f35965a-9a9b-45fd-ba32-987296dfb6be@150.40.126.19:443/?type=grpc&encryption=none&flow=&serviceName=media.v1.ObjectService&sni=rs2.univesalsrv.com&fp=firefox&security=reality&pbk=tL16MVY08r-7YDXb1_gxuBBWInpSFp97ZLJ_ax3R2iE&sid=1469af2040b7c323#%F0%9F%87%B7%F0%9F%87%B8%20%EA%A7%81%20%D0%A1%D0%B5%D1%80%D0%B1%D0%B8%D1%8F%20%EA%A7%82%20%F0%9F%8C%BF",
    "vless://2f35965a-9a9b-45fd-ba32-987296dfb6be@rs1.univesalsrv.com:443/?type=grpc&encryption=none&flow=&serviceName=node.v2.ObjectService&sni=rs1.univesalsrv.com&fp=firefox&security=reality&pbk=upIzyaSbVz2ZK6KfGtXmPl_-sCwn8XLDyFDH5CsL9iY&sid=ed0cd5cc2e26e6e7#%F0%9F%87%B7%F0%9F%87%B8%20%D0%A1%D0%B5%D1%80%D0%B1%D0%B8%D1%8F",
    "vless://2f35965a-9a9b-45fd-ba32-987296dfb6be@150.40.126.22:443/?type=grpc&encryption=none&flow=&serviceName=media.v1.StreamService&sni=rs4.univesalsrv.com&fp=firefox&security=reality&pbk=sXsJ4ET-50TYqlhKZf03nPQr2JIy1F0D4m6lOsI0cAs&sid=861ac7d66953e55f#%F0%9F%87%B7%F0%9F%87%B8%20%EA%A7%81%20%D0%A1%D0%B5%D1%80%D0%B1%D0%B8%D1%8F%20%EA%A7%82%20%F0%9F%94%A5",
    "vless://fe551942-d6e5-4361-ae5c-1f2e9077cd79@83.219.97.18:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=fi5.silalink.sbs&security=reality&pbk=32XFmS-ifqooBFY89KNP3ZrqgSBOd3vel9GlNinL6yw&sid=03#%F0%9F%87%AB%F0%9F%87%AE%20%D0%A4%D0%B8%D0%BD%D0%BB%D1%8F%D0%BD%D0%B4%D0%B8%D1%8F",
    "vless://fe551942-d6e5-4361-ae5c-1f2e9077cd79@83.219.97.18:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=fi5.silalink.sbs&fp=safari&security=reality&pbk=32XFmS-ifqooBFY89KNP3ZrqgSBOd3vel9GlNinL6yw&sid=03#%F0%9F%87%AB%F0%9F%87%AE%20%D0%A4%D0%B8%D0%BD%D0%BB%D1%8F%D0%BD%D0%B4%D0%B8%D1%8F",
    "ss://YWVzLTI1Ni1nY206WlJwZ2FCZUd4dEVOSVhndmhwa1pCS3o5R25XUlMyZFljeDlPK2EyaXdOND0@202.50.253.72:19999#%F0%9F%87%AE%F0%9F%87%B9%20%D0%98%D1%82%D0%B0%D0%BB%D0%B8%D1%8F",
    "vless://2f35965a-9a9b-45fd-ba32-987296dfb6be@bg3.univesalsrv.com:443/?type=grpc&encryption=none&flow=&serviceName=home.v1.ApiService&sni=bg3.univesalsrv.com&fp=firefox&security=reality&pbk=XBfCioniAKXgKYBUVnvBXu80AIaIa4SpAB3w8qeF7Gk&sid=1be1bd931c98c84a#%F0%9F%87%A7%F0%9F%87%AC%20%D0%91%D0%BE%D0%BB%D0%B3%D0%B0%D1%80%D0%B8%D1%8F",
    "vless://2f35965a-9a9b-45fd-ba32-987296dfb6be@bg2.univesalsrv.com:443/?type=grpc&encryption=none&flow=&serviceName=api.v2.PushService&fp=chrome&security=reality&pbk=0f0dh_FUju5cHgQcIwUjHvxQb9aIZ00p0kZRHeE7Ey4&sid=501ab3325b77e1ca#%F0%9F%87%A7%F0%9F%87%AC%20%EA%A7%81%20%D0%91%D0%BE%D0%BB%D0%B3%D0%B0%D1%80%D0%B8%D1%8F%20%EA%A7%82%20%F0%9F%8C%B9",
    "vmess://eyJhZGQiOiJldTMuOTk4OTk4LmJlc3QiLCJhaWQiOiIwIiwiYWxwbiI6IiIsImZwIjoiIiwiaG9zdCI6InNlcnZlcjQwLjk5NjYzMzgueHl6IiwiaWQiOiI1NTA0ZWFhOC0xMzk1LTQwMmYtOGUwZS03NWVjZDc2MmU2MjciLCJuZXQiOiJ3cyIsInBhdGgiOiIvYWlhaWFpIiwicG9ydCI6IjQ0MyIsInBzIjoi8J+HqvCfh6og6qeBINCt0YHRgtC+0L3QuNGPIOqngiDwn4y/Iiwic2N5IjoiYXV0byIsInNuaSI6InNlcnZlcjQwLjk5NjYzMzgueHl6IiwidGxzIjoidGxzIiwidHlwZSI6IiIsInYiOiIyIn0=",
    "vless://019fbe0f-2d9f-4b89-9f81-e1e36129892a@77.110.105.122:443/?type=raw&encryption=none&flow=xtls-rprx-vision&sni=co-es.speedtec.ru&fp=random&security=reality&pbk=EBISh6QAVskJ_nvet-Qio9jS2yqxe9de6GMScYlbjhI&sid=226509f017e4c36d#%F0%9F%87%AA%F0%9F%87%AA%20%D0%AD%D1%81%D1%82%D0%BE%D0%BD%D0%B8%D1%8F",
    "vless://c6cfcc53-9271-4ef7-88c5-5141621c8db1@31.59.216.141:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=193.23.216.239.cdn-one.org&fp=firefox&security=reality&pbk=7zsU1U-30jh-qqfmqZukMfoqHB75ksKFA5aQFi8LGW4&sid=70b4ca#%F0%9F%87%AB%F0%9F%87%B7%20%D0%A2%D0%BE%D1%80%D1%82%D0%B8%D0%BA%20FR",
    #пропуск (не удалять!) . - , получается хуйня такая
]


# ============================================================
# НАСТРОЙКИ
# ============================================================

TARGET_COUNT = 60          # сколько конфигов взять в итоге (не считая закреплённых)
EARLY_STOP_MULT = 3        # остановить проверку, когда найдено TARGET_COUNT * N рабочих
                           # (из них берутся лучшие по пингу). 0 = проверять все

MAX_PING_MS = 3000         # отсечка совсем медленных (пинг через прокси)
GOOD_PING_MS = 300         # только для значков в логе

MAX_TCP_PING_MS = 1700     # TCP-пинг выше этого (или нет ответа) — в xray не идёт
TCP_CONCURRENCY = 200      # одновременных TCP-проверок

# --- Скачивание подписок ---
FETCH_TIMEOUT = 20.0
FETCH_RETRIES = 3          # сколько раз пробовать каждый источник
FETCH_HEADERS_LIST = [     # User-Agent меняется от попытки к попытке
    {"User-Agent": "v2rayN/6.42"},
    {"User-Agent": "Happ/1.0"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
]

CONCURRENCY = 15           # одновременных xray/sing-box процессов
XRAY_STARTUP_TIMEOUT = 6.0 # сек: максимум ждём, пока ядро откроет локальный порт
XRAY_TEST_TIMEOUT = 8.0    # сек на ОДИН тестовый запрос через прокси
XRAY_BINARY = "xray"       # должен быть в PATH

# --- Hy2 (проверяется через sing-box, т.к. это UDP/QUIC) ---
CHECK_HY2 = True           # False — не проверять hy2 вообще
SINGBOX_BINARY = "sing-box"  # должен быть в PATH (нужна версия 1.11+)

TEST_URLS = [
    "https://cp.cloudflare.com/generate_204",
    "https://www.gstatic.com/generate_204",
]

# Строгая проверка: КАЖДЫЙ тестовый URL должен ответить в КАЖДОМ раунде.
# Первый раунд — «холодный» (рукопожатие), последний — «тёплый», по нему считается пинг.
CHECK_ROUNDS = 3

# --- Защита от «соединение закрыто» и тайм-аутов ---
IDLE_PAUSE = 2.0            # пауза перед повторным запросом по тому же соединению
BURST_PARALLEL = 8          # параллельных запросов на новых соединениях
BURST_MAX_FAILS = 0         # сколько из них можно провалить

DOWNLOAD_URLS = [           # достаточно, чтобы прошёл ХОТЯ БЫ ОДИН
    "https://speed.cloudflare.com/__down?bytes=1000000",
    "https://proof.ovh.net/files/1Mb.dat",
]
DOWNLOAD_BYTES = 1_000_000
DOWNLOAD_TIMEOUT = 15.0
REQUIRE_DOWNLOAD = True     # False — если раннер не достаёт до DOWNLOAD_URLS

# --- Реальная проверка выходного IP ---
# Через каждый прокси спрашиваем у IP-эхо сервиса, какой у нас IP.
IP_ECHO_URLS = [
    "https://api.ipify.org",
    "https://icanhazip.com",
    "https://ifconfig.me/ip",
]
REQUIRE_EXIT_IP = True      # не получили выходной IP или он = нашему → конфиг нерабочий
DEDUPE_BY_EXIT_IP = True    # дубли по реальному выходному IP

# Повторная проверка лучших кандидатов отдельным запуском ядра:
# отсекает «мигающие» серверы, которые прошли проверку случайно.
CONFIRM_BEST = True
CONFIRM_SPARE = 10         # сколько лишних кандидатов брать с запасом на выбывших

GEO_DELAY = 0.3            # пауза между гео-запросами
PROGRESS_EVERY = 50        # как часто писать прогресс проверки (раз в N конфигов)
BASE_LOCAL_PORT = 21000

OUTPUT_FILE = Path("output/sub.txt")

PROTOCOLS = (
    "vless://", "vmess://", "trojan://", "ss://",
    "ssr://", "hysteria2://", "hy2://", "tuic://",
)

# Через xray проверяются эти протоколы.
XRAY_SUPPORTED = ("vless://", "vmess://", "trojan://", "ss://")

# Hy2 — через sing-box (UDP, TCP-пинг к нему неприменим).
HY2_SCHEMES = ("hy2://", "hysteria2://")

# Наш реальный IP (без прокси) и выходные IP конфигов
_my_ip = None
_exit_ip = {}               # config -> выходной IP


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
# Дубль = один и тот же сервер (протокол + хост + порт + uuid/пароль).
# Название (#...) и мелкие параметры (fp, sni, sid, flow...) на ключ не влияют:
# на одном порту всё равно работает один конфиг.
# ============================================================

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
        scheme = "hy2"  # hy2:// и hysteria2:// — один и тот же протокол
    netloc = re.split(r"[/?#]", rest, maxsplit=1)[0]
    userinfo, _, hostport = netloc.rpartition("@")
    return (scheme, userinfo, hostport.lower())


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
# HY2: разбор URI
# hy2://auth@host:port/?sni=...&insecure=1&obfs=salamander&obfs-password=...&mport=...#name
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
            insecure = True  # закрепление сертификата здесь не проверяем

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
# DNS (асинхронно, с кэшем) — нужен для удаления дублей по IP и для гео
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
    # "raw" (так называет клиент) = обычный tcp; "splithttp" = старое имя xhttp
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
            # старый формат: всё целиком в base64
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
    """Выбирает ядро и строит его конфиг с SOCKS-входом на 127.0.0.1:port.
    Возвращает (бинарник, конфиг) или None, если конфиг не разобрать."""
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
# БЫСТРАЯ TCP-ПРОВЕРКА (до xray; к hy2 не применяется — он на UDP)
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
# ОЖИДАНИЕ ЛОКАЛЬНОГО ПОРТА ЯДРА
# (вместо слепого sleep: не даём ложных «не работает» при нагрузке
#  и точно знаем, что запрос идёт именно в наше ядро)
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
# Отдаёт локальный SOCKS-порт или None, если ядро не поднялось /
# конфиг не разобрался. По выходу всё гасит и освобождает порт.
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
# ОПРЕДЕЛЕНИЕ IP ЧЕРЕЗ IP-ЭХО СЕРВИСЫ
# Без прокси — наш реальный IP; через прокси — выходной IP конфига.
# ============================================================

async def fetch_ip(session, timeout=8.0):
    t = aiohttp.ClientTimeout(total=timeout)
    for url in IP_ECHO_URLS:
        try:
            async with session.get(url, timeout=t) as resp:
                if resp.status != 200:
                    continue
                text = (await resp.text()).strip()
            ipaddress.ip_address(text)  # убедимся, что это именно IP
            return text
        except Exception:
            continue
    return None


# ============================================================
# ОДИН ТЕСТОВЫЙ ЗАПРОС: бросает исключение при любой ошибке
# (статус не 200/204, обрыв, тайм-аут, слишком короткое тело)
# Возвращает время в мс.
# ============================================================

async def _fetch_ok(session, url, min_bytes=0, timeout=None):
    start = time.monotonic()
    kw = {"timeout": aiohttp.ClientTimeout(total=timeout)} if timeout else {}
    async with session.get(url, **kw) as resp:
        if resp.status not in (200, 204):
            raise ValueError(f"status {resp.status}")
        body = await resp.read()
    if len(body) < min_bytes:
        raise ValueError("short body")
    return (time.monotonic() - start) * 1000


# ============================================================
# РЕАЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ ЯДРО (xray / sing-box) — возвращает пинг (мс) или None
# Строго: все тестовые URL должны ответить во всех раундах,
# HTTPS-сертификаты проверяются (подменённый/«дырявый» прокси не проходит).
# Дальше:
#   1) пауза и повторный запрос по тому же соединению (keep-alive);
#   2) реальный выходной IP: определяется и не совпадает с нашим;
#   3) параллельный залп на новых соединениях;
#   4) скачивание ~1 МБ (обрывы посреди передачи, слишком медленные).
# Одинаково для vless / vmess / trojan / ss / hy2.
# ============================================================

async def _probe(line, port):
    connector = aiohttp_socks.ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
    timeout = aiohttp.ClientTimeout(total=XRAY_TEST_TIMEOUT)

    latencies = []
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for rnd in range(CHECK_ROUNDS):
            last_round = rnd == CHECK_ROUNDS - 1
            for url in TEST_URLS:
                ms = await _fetch_ok(session, url)   # ssl-проверка ВКЛЮЧЕНА
                if last_round:
                    latencies.append(ms)

        # пауза + повтор по тому же соединению (рвёт ли сервер keep-alive)
        await asyncio.sleep(IDLE_PAUSE)
        for url in TEST_URLS:
            await _fetch_ok(session, url)

        # реальная проверка выходного IP
        exit_ip = await fetch_ip(session, XRAY_TEST_TIMEOUT)
        if REQUIRE_EXIT_IP and (not exit_ip or (_my_ip and exit_ip == _my_ip)):
            return None
        if exit_ip:
            _exit_ip[line] = exit_ip

    # параллельный залп на НОВЫХ соединениях + загрузка файла
    conn2 = aiohttp_socks.ProxyConnector.from_url(
        f"socks5://127.0.0.1:{port}", force_close=True
    )
    async with aiohttp.ClientSession(connector=conn2, timeout=timeout) as s2:
        urls = [TEST_URLS[i % len(TEST_URLS)] for i in range(BURST_PARALLEL)]
        res = await asyncio.gather(*(_fetch_ok(s2, u) for u in urls),
                                   return_exceptions=True)
        if sum(isinstance(r, Exception) for r in res) > BURST_MAX_FAILS:
            return None

        if DOWNLOAD_URLS:
            dl_ok = False
            for url in DOWNLOAD_URLS:
                try:
                    await _fetch_ok(s2, url, DOWNLOAD_BYTES * 0.9, DOWNLOAD_TIMEOUT)
                    dl_ok = True
                    break
                except Exception:
                    continue
            if REQUIRE_DOWNLOAD and not dl_ok:
                return None

    if not latencies:
        return None
    return sum(latencies) / len(latencies)


async def real_check(line):
    try:
        async with running_core(line) as port:
            if port is None:
                return None
            return await _probe(line, port)
    except Exception:
        return None


# ============================================================
# GEO: консенсус нескольких сервисов
# ip="" -> сначала узнаём выходной IP через прокси, затем страну по нему
# ============================================================

GEO_PROVIDERS = [
    ("ipinfo", "https://ipinfo.io/{ip}/json"),
    ("ipwho",  "https://ipwho.is/{ip}"),
    ("geojs",  "https://get.geojs.io/v1/ip/geo/{ip}.json"),
    ("dbip",   "https://api.db-ip.com/v2/free/{ip}"),
    ("ipapico","https://ipapi.co/{ip}/json/"),
    ("ipapi",  "http://ip-api.com/json/{ip}?fields=status,countryCode,city"),
    ("sypex",  "https://api.sypexgeo.net/json/{ip}"),
]

GEO_MIN_AGREE = 2              # минимум сервисов, согласных по стране
GEO_USE_SERVER_FALLBACK = False  # гео по IP сервера часто врёт — выключено


def parse_geo(kind, data):
    try:
        if kind == "sypex":
            cc = (data.get("country") or {}).get("iso")
            c = data.get("city") or {}
            city = c.get("name_ru") or c.get("name_en")
        elif kind == "ipwho":
            if not data.get("success"):
                return None, None
            cc, city = data.get("country_code"), data.get("city")
        elif kind == "ipapi":
            if data.get("status") != "success":
                return None, None
            cc, city = data.get("countryCode"), data.get("city")
        elif kind == "ipinfo":
            cc, city = data.get("country"), data.get("city")
        elif kind == "geojs":
            cc, city = data.get("country_code"), data.get("city")
        elif kind == "ipapico":
            if data.get("error"):
                return None, None
            cc, city = data.get("country_code"), data.get("city")
        elif kind == "dbip":
            cc, city = data.get("countryCode"), data.get("city")
        else:
            return None, None
        if cc and len(cc) == 2 and cc.isalpha():
            return cc.upper(), city
    except Exception:
        pass
    return None, None


async def _geo_provider(session, idx, kind, tpl, ip):
    try:
        timeout = aiohttp.ClientTimeout(total=8.0)
        async with session.get(tpl.format(ip=ip), timeout=timeout) as resp:
            if resp.status != 200:
                return idx, None, None
            data = await resp.json(content_type=None)
        code, city = parse_geo(kind, data)
        return idx, code, city
    except Exception:
        return idx, None, None


async def geo_lookup(session, ip=""):
    """Страна по КОНСЕНСУСУ нескольких сервисов. Возвращает (code, geo_name)."""
    # через прокси сначала узнаём реальный выходной IP, потом спрашиваем про него
    if not ip:
        ip = await fetch_ip(session)
        if not ip:
            return None, None

    results = await asyncio.gather(*(
        _geo_provider(session, i, k, t, ip)
        for i, (k, t) in enumerate(GEO_PROVIDERS)
    ))

    votes = {}  # code -> [(priority, city)]
    for idx, code, city in results:
        if code:
            votes.setdefault(code, []).append((idx, city))
    if not votes:
        return None, None

    responded = sum(len(v) for v in votes.values())
    best = max(votes, key=lambda c: (len(votes[c]), -min(i for i, _ in votes[c])))
    agree = len(votes[best])

    # если ответили ≥2 сервиса, но двое не согласились — не верим никому
    if responded >= GEO_MIN_AGREE and agree < GEO_MIN_AGREE:
        return None, None

    city = next((c for _, c in sorted(votes[best], key=lambda x: x[0]) if c), None)
    return best, make_geo_name(best, city)


async def get_server_geo(session, ip):
    if not ip or not GEO_USE_SERVER_FALLBACK:
        return None, None
    return await geo_lookup(session, ip)


async def exit_geo(line):
    """Страна по РЕАЛЬНОМУ выходному IP: поднимаем ядро и спрашиваем гео через прокси."""
    try:
        async with running_core(line) as port:
            if port is None:
                return None, None
            connector = aiohttp_socks.ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
            async with aiohttp.ClientSession(connector=connector) as s:
                return await geo_lookup(s)
    except Exception:
        return None, None


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
        # последняя попытка — без проверки SSL
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
    """Проверяет конфиги через xray / sing-box.
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
                failed.append(config)
            if done % PROGRESS_EVERY == 0:
                print(f"    проверено {done}/{total} ✓{len(working)}")

    await asyncio.gather(*(worker(c) for c in candidates))
    return working, failed


# ============================================================
# УДАЛЕНИЕ ДУБЛЕЙ ПО РЕАЛЬНОМУ IP:ПОРТ И ПО ВЫХОДНОМУ IP
# Разные домены/названия на один и тот же ip:порт — это один сервер.
# Конфиги с одинаковым выходным IP — тоже считаем дублями.
# Из группы остаётся самый быстрый.
# ============================================================

async def dedupe_by_ip(items, taken=None):
    """items: список (config, latency), уже отсортированный по пингу.
    taken: множество (ip, port), которые уже заняты (закреплённые)."""
    seen = set(taken or ())

    hosts = {get_host_port(c)[0] for c, _ in items if get_host_port(c)}
    await asyncio.gather(*(resolve_ip(h) for h in hosts))

    result = []
    for config, latency in items:
        hp = get_host_port(config)
        if not hp:
            result.append((config, latency))
            continue
        ip = _dns_cache.get(hp[0]) or hp[0]
        keys = [(ip, hp[1])]
        if DEDUPE_BY_EXIT_IP and config in _exit_ip:
            keys.append(("exit", _exit_ip[config]))
        if any(k in seen for k in keys):
            continue
        seen.update(keys)
        result.append((config, latency))
    return result


# ============================================================
# ПОВТОРНАЯ ПРОВЕРКА ЛУЧШИХ
# Берём кандидатов по порядку пинга и проверяем второй раз отдельным ядром.
# Остаются только те, кто прошёл оба раза. Идём, пока не наберём TARGET_COUNT.
# ============================================================

async def confirm_best(items):
    confirmed = []
    idx = 0
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def worker(config, first_latency):
        async with semaphore:
            try:
                latency = await real_check(config)
            except Exception:
                latency = None
        if latency is not None and latency <= MAX_PING_MS:
            confirmed.append((config, (first_latency + latency) / 2))

    while idx < len(items) and len(confirmed) < TARGET_COUNT:
        need = TARGET_COUNT - len(confirmed)
        chunk = items[idx: idx + need + CONFIRM_SPARE]
        idx += len(chunk)
        await asyncio.gather(*(worker(c, l) for c, l in chunk))
        print(f"    подтверждено {len(confirmed)}/{TARGET_COUNT} (просмотрено {idx}/{len(items)})")

    confirmed.sort(key=lambda x: x[1])
    return confirmed


def interleave(a, b):
    """Чередует два списка: a1, b1, a2, b2, ... (чтобы hy2 не оказался
    в хвосте и не отрезался ранней остановкой)."""
    return [x for pair in itertools.zip_longest(a, b) for x in pair if x is not None]


# ============================================================
# MAIN
# ============================================================

async def main():
    global _my_ip

    init_port_pool(CONCURRENCY)

    hy2_enabled = CHECK_HY2 and shutil.which(SINGBOX_BINARY) is not None
    if CHECK_HY2 and not hy2_enabled:
        print(f"[!] {SINGBOX_BINARY} не найден в PATH — hy2 проверяться не будет")

    # ---------- 1. скачиваем ВСЕ подписки ----------
    async with aiohttp.ClientSession() as session:
        # наш реальный IP (без прокси) — для проверки утечки
        try:
            _my_ip = await asyncio.wait_for(fetch_ip(session), 20)
        except Exception:
            _my_ip = None
        print(f"[i] Мой IP: {_my_ip or 'не определён (проверка совпадения с моим IP отключена)'}")

        print("[i] Скачиваю подписки...")
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
        seen = {dedupe_key(c) for c in pinned if c.startswith(PROTOCOLS)}

        unique = []
        for c in all_configs:
            k = dedupe_key(c)
            if k in seen:
                continue
            seen.add(k)
            unique.append(c)

        print(f"[i] После удаления дубликатов: {len(unique)}")

        # что проверяем: vless/vmess/trojan/ss через xray, hy2 через sing-box
        xray_cands = [c for c in unique if c.startswith(XRAY_SUPPORTED)]
        hy2_cands = [c for c in unique if c.startswith(HY2_SCHEMES)] if hy2_enabled else []
        skipped = len(unique) - len(xray_cands) - len(hy2_cands)
        if skipped:
            what = "tuic/ssr" if hy2_enabled else "hy2/tuic/ssr"
            print(f"[i] Без проверки ({what}): {skipped}")

        if not xray_cands and not hy2_cands:
            print("[x] Нет конфигов для проверки.")
            return

        # статистика по источникам: url -> [проверено, нерабочих]
        stats = {}

        def count(config, ok):
            s = stats.setdefault(source_of.get(dedupe_key(config)), [0, 0])
            s[0] += 1
            if not ok:
                s[1] += 1

        # ---------- 3. быстрая TCP-проверка (только не-hy2) ----------
        alive = []
        if xray_cands:
            print(f"\n[i] TCP: проверяю {len(xray_cands)}...")
            alive = await tcp_filter(xray_cands)
            alive_set = {c for c, _ in alive}
            for c in xray_cands:
                if c not in alive_set:
                    count(c, False)
            print(f"[i] TCP ок: {len(alive)} из {len(xray_cands)}")

        # самые быстрые по TCP проверяем первыми
        alive.sort(key=lambda x: x[1])
        tcp_ok = [c for c, _ in alive]

        if hy2_cands:
            print(f"[i] Hy2 (UDP, без TCP-проверки): {len(hy2_cands)}")

        candidates = interleave(tcp_ok, hy2_cands)
        if not candidates:
            print("[x] Ни один сервер не ответил по TCP.")
            return

        # ---------- 3.1 реальная проверка (+ выходной IP) ----------
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
            return

        # ---------- 4. лучшие по пингу, без дублей, с повторной проверкой ----------
        working.sort(key=lambda x: x[1])

        # IP:порт закреплённых тоже считаем занятыми
        taken = set()
        for c in pinned:
            if not c.startswith(PROTOCOLS):
                continue
            hp = get_host_port(c)
            if hp:
                ip = await resolve_ip(hp[0])
                taken.add((ip or hp[0], hp[1]))

        before = len(working)
        working = await dedupe_by_ip(working, taken)
        print(f"[i] Убрал дубли (IP:порт / выходной IP): {before - len(working)} (осталось {len(working)})")

        if CONFIRM_BEST:
            print("\n[i] Повторная проверка лучших...")
            best = await confirm_best(working)
        else:
            best = working
        best = best[:TARGET_COUNT]
        print(f"[i] Беру лучших по пингу: {len(best)}")

        if not best:
            print("[x] После повторной проверки рабочих не осталось.")
            return

        # ---------- 5. страна/город по реальному выходному IP + переименование ----------
        print("\n[i] Определяю страны (по выходному IP)...")
        geo_sem = asyncio.Semaphore(CONCURRENCY)
        geo_done = 0

        async def geo_one(config):
            nonlocal geo_done
            async with geo_sem:
                code, name = None, None
                # 1) гео по уже известному выходному IP (без запуска ядра)
                exit_ip = _exit_ip.get(config)
                if exit_ip:
                    code, name = await geo_lookup(session, exit_ip)
                # 2) через ядро, если выходной IP неизвестен/не определился
                if not code:
                    code, name = await exit_geo(config)
                # 3) запасной путь: гео по IP сервера (по умолчанию выключен)
                if not code:
                    hp = get_host_port(config)
                    if hp:
                        ip = await resolve_ip(hp[0])
                        code, name = await get_server_geo(session, ip)
                await asyncio.sleep(GEO_DELAY)
                geo_done += 1
                if geo_done % 10 == 0 or geo_done == len(best):
                    print(f"    гео {geo_done}/{len(best)}")
                return code, name

        geos = await asyncio.gather(*(geo_one(c) for c, _ in best))

        items = []  # (country_name, latency, renamed_line)
        for (config, latency), (code, name) in zip(best, geos):
            final_name = name or "🌐 Неизвестно"
            country_key = get_country_name(code) if code else "я_Неизвестно"  # неизвестные — в конец
            items.append((country_key, latency, rename_config(config, final_name)))

        # группируем по стране, внутри страны — по пингу
        items.sort(key=lambda x: (x[0], x[1]))
        renamed = [line for _, _, line in items]

    # ---------- 6. сохраняем ----------
    final_list = pinned + renamed

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(final_list) + "\n", encoding="utf-8")

    print()
    print(f"[✓] Готово: {len(final_list)} (закр. {len(pinned)} + {len(renamed)})")
    print(f"[✓] Файл: {OUTPUT_FILE}")

    # ---------- 7. где больше всего нерабочих ----------
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