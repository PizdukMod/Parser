#!/usr/bin/env python3
# PizdukVPN «ЧС» ❄️ — сбор, проверка и публикация подписки (output/sub.txt)

import asyncio
import aiohttp
import aiohttp_socks
import base64
import datetime
import hashlib
import ipaddress
import json
import re
import shutil
import socket
import statistics
import sys
import tempfile
import os
import itertools
import time

from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote


# ============================================================
# ИСТОЧНИКИ — НЕ МЕНЯТЬ
# ============================================================

SOURCES = [
    "https://freevpn.happcluchi.workers.dev", #@freevpnhapp
    "https://cat-wife.halyavusvpnus.workers.dev/",
    "https://mifa.world/visa", #mifa
    "https://sub.vlessfo.ru/vlessforu/working_configs.txt", #vlessforu
    "https://admin2.vspboost.ru/s/rZ7ekY", #vsp
    "https://pozor.bond/sub/google-vpn",
    "https://pozor.bond/sub/ry2627uz9cp7", #Лёха иногда вырубает серваки
    "https://vpn.voidgram.xyz/burmalda", #burmalda
    "https://pozor.bond/sub/9xnb9v67465y", #от улитки
    "https://v2hub.link/sub/pdsdrvg_qWhwRRhSeUpdN9Bn7qGG2AIuIi319E-QFUs",
    "https://raw.githubusercontent.com/KoT-ANTIDOT/bunker-subscriptions/refs/heads/main/Black_List.txt",
    "https://codeberg.org/telegram-alt_vpn_obxod/obxod_white-black_list/raw/branch/main/subs.txt",
    "https://is.wepogp.gay/bypass-hwid-lock-3z5O6BFAaJQzGlamvtSo?payload=LoWcw85kRd%2BHRAuaIWWTGaHlqIHCzpm8J09GWd0zeNMb%2BUDgv4dboD2VwU438QTP4MnqUeC52Cr1%2BwMypBkx2AeCuIdXZCocuSDn6up0bvCVvvd5lEzyRfjFZUCiUuH5",
    "https://is.wepogp.gay/bypass-hwid-lock-3z5O6BFAaJQzGlamvtSo?payload=LoWcw85kRd%2BHRAuaIWWTGaHlqIHCzpm8J09GWd0zeNMb%2BUDgv4dboD2VwU438QTP4MnqUeC52Cr1%2BwMypBkx2PeUWfpWpdOUvOeNWrBgAX98qiT06gURdNejXhujIa0P",
]


# ============================================================
# ЗАКРЕПЛЁННЫЕ КОНФИГИ — добавляются в начало БЕЗ проверки
# ============================================================

PINNED_CONFIGS = [
    "#profile-title: PizdukVPN ЧС🏴",
    "#announce: base64: 8J+YjiDQotC10LvQtdCz0YDQsNC8INC60LDQvdCw0Ls6IEBQaXpNb2Twn5iNCvCfpbPQkNCy0YLQvtC+0LHQvdC+0LLQu9C10L3QuNC1INC60LDQttC00YvQtSA2INGH0LDRgdC+0LLwn6Sv",
    "#profile-web-page-url: t.me/PizMod",
    "#support-url: t.me/Harachok",
    "#profile-update-interval: 6",
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@qq.utiltools.site:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=qq.utiltools.site&fp=chrome&security=reality&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&sid=#%F0%9F%95%B8%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B3%F0%9F%87%B1%20%28telegram-only%29%F0%9F%8E%83",
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@78.159.250.107:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=qq.utiltools.site&fp=safari&security=reality&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&sid=#%F0%9F%95%B8%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B3%F0%9F%87%B1%20%C2%B2%20%28telegram-only%29%F0%9F%8E%83",
    "vless://c8c2ddff-825a-46c3-bbdd-4a101de468a7@188.130.209.212:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=thumbs.mycdn-io.ru&fp=firefox&security=reality&pbk=6vubZmkLVtaiFF8JyGFy7XSy2pc7ywN4P625QLKw8wc&sid=11979c0c9b2da371#%F0%9F%87%B7%F0%9F%87%BA%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F",
    "vmess://eyJhZGQiOiJjZi4wc20uY29tIiwiYWlkIjoiMCIsImFscG4iOiIiLCJmcCI6IiIsImhvc3QiOiJ2bWVzcy5sYnc2NjYuZHBkbnMub3JnIiwiaWQiOiIwY2Y2ZDk3MC0zZjFkLTRhYWUtYTk4OS05MmE4Zjc2YWUzZGIiLCJuZXQiOiJ3cyIsInBhdGgiOiIvd3M/ZWRcdTAwM2QyMDQ4IiwicG9ydCI6IjgwIiwicHMiOiLwn4e68J+HuCDinKYg0KHQqNCQIOKcpiDwn4yAIiwic2N5IjoiYXV0byIsInNuaSI6IiIsInRscyI6IiIsInR5cGUiOiIiLCJ2IjoiMiJ9",
    "vmess://eyJhZGQiOiIxNzIuNjcuMTg3LjE0NSIsImFpZCI6IjAiLCJhbHBuIjoiIiwiZnAiOiIiLCJob3N0Ijoidm1lc3MubGJ3NjY2LmRwZG5zLm9yZyIsImlkIjoiMGNmNmQ5NzAtM2YxZC00YWFlLWE5ODktOTJhOGY3NmFlM2RiIiwibmV0Ijoid3MiLCJwYXRoIjoiL3dzP2VkXHUwMDNkMjA0OCIsInBvcnQiOiI4MCIsInBzIjoi8J+HuvCfh7gg0KHQqNCQIiwic2N5IjoiYXV0byIsInNuaSI6IiIsInRscyI6IiIsInR5cGUiOiIiLCJ2IjoiMiJ9",
    "vless://33f3c1ee-f026-4f3f-bed3-8c7c01de8a96@user.betust.net:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=user.betust.net&fp=firefox&security=reality&pbk=TXP6hQVE4PdXDEdDk2k_5_f92jcOKZ15Fuw14jCJTQg&sid=c1064ddb#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%E2%9A%A1%20Gemini%20%F0%9F%A4%96",
    "vless://50a87e21-f0e2-4b53-a787-91adfe748f63@hollandlanzerotte.xyz:443/?type=raw&encryption=none&flow=xtls-rprx-vision&sni=hollandlanzerotte.xyz&fp=qq&security=reality&pbk=EEL-yDPBfol_fiEEM8Pd0zue7SSz5MtZlXEePVak2jc&sid=#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%F0%9F%90%8C%20Gemini%20%F0%9F%A4%96",
    "vless://95d0e214-eab0-4701-93ed-fea4f1b56062@main.jarbook.net:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=main.jarbook.net&fp=firefox&security=reality&pbk=gJoMHh97teLxW92Z_3DI8qdSulqBlb9sW6mthYPEEBk&sid=d889ac17#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%D0%AE%D1%82%D1%83%D0%B1%20%F0%9F%93%BA",
    "vless://95d0e214-eab0-4701-93ed-fea4f1b56062@prime.jarbook.net:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=prime.jarbook.net&fp=firefox&security=reality&pbk=oAX7soFKfN3xURgCD26trmjeF-e-eEjW3pBVXuuvW0k&sid=77a8c8c8#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%E2%9A%A1%20YouTube%20%F0%9F%93%BA",
    "vless://3f5e89d5-591f-4ac9-b071-b05680b573c3@50.7.178.197:8443/?type=grpc&encryption=none&flow=&serviceName=connect-fr&security=tls&sni=fr2.gacvpn.site#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%E2%9A%A1%20YT%20%F0%9F%93%BA",
    "vless://3f5e89d5-591f-4ac9-b071-b05680b573c3@nl4.gacvpn.site:443/?type=ws&encryption=none&flow=&path=%2Fstatic%2Fjs%2Fvendor.cc1645b6.js%3Fed%3D2048&security=tls&sni=nl4.gacvpn.site#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%E2%9A%A1%20YT%20%F0%9F%93%BA",
    "vless://804334e2-04ca-434c-8311-3ccee8218175@123466.ru:33664/?type=tcp&encryption=mlkem768x25519plus.native.0rtt.dYzoy51qawu9f3ACOG44G0aOaTyj0hd6m7aRgUwQMFE&flow=#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%E2%9A%A1%20YouTube%20%F0%9F%93%BA",
    "vmess://eyJhZGQiOiIxMjM0NjYucnUiLCJhaWQiOiIwIiwiYWxwbiI6IiIsImZwIjoiIiwiaG9zdCI6IjEyMzQ2Ni5ydSIsImlkIjoiODA0MzM0ZTItMDRjYS00MzRjLTgzMTEtM2NjZWU4MjE4MTc1IiwibmV0Ijoid3MiLCJwYXRoIjoiLyIsInBvcnQiOiIyODA1NCIsInBzIjoi8J+Hs/Cfh7Eg0J3QuNC00LXRgNC70LDQvdC00Ysg4pqhIFlvdVR1YmUg8J+TuiIsInNjeSI6ImF1dG8iLCJzbmkiOiIiLCJ0bHMiOiIiLCJ0eXBlIjoiIiwidiI6IjIifQ==",
    "vmess://eyJhZGQiOiIxMjM0NjYucnUiLCJhaWQiOiIwIiwiYWxwbiI6IiIsImZwIjoiIiwiaG9zdCI6IjEyMzQ2Ni5ydSIsImlkIjoiODA0MzM0ZTItMDRjYS00MzRjLTgzMTEtM2NjZWU4MjE4MTc1IiwibmV0IjoiaHR0cHVwZ3JhZGUiLCJwYXRoIjoiLyIsInBvcnQiOiIzMjY5NCIsInBzIjoi8J+Hs/Cfh7Eg0J3QuNC00LXRgNC70LDQvdC00Ysg4pqhIFlvdVR1YmUg8J+TuiIsInNjeSI6ImF1dG8iLCJzbmkiOiIiLCJ0bHMiOiIiLCJ0eXBlIjoiIiwidiI6IjIifQ==", #🇳🇱 Нидерланды
    "vless://50a87e21-f0e2-4b53-a787-91adfe748f63@swedenafteraventura.space:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=swedenafteraventura.space&fp=chrome&security=reality&pbk=TyuIIquHoesD9YwMQJHda0YZ3Hy9Dh123dQ00iGK0QY&sid=#%F0%9F%87%B8%F0%9F%87%AA%20%E2%9A%A1%20%D0%A8%D0%B2%D0%B5%D1%86%D0%B8%D1%8F%20%E2%9A%A1%20YT%20%F0%9F%93%BA%20AI%F0%9F%A4%96",
    "vless://dd5bed0b-ee77-481b-9f2c-250a632ddd9f@get.jarbook.net:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=get.jarbook.net&fp=firefox&security=reality&pbk=BIy6H-jndn24Ukyw83ML8LDB1HL8WLJmfCADEy8lzVs&sid=c6f97313#%F0%9F%87%B8%F0%9F%87%AA%20%D0%A8%D0%B2%D0%B5%D1%86%D0%B8%D1%8F",
    "vless://dd5bed0b-ee77-481b-9f2c-250a632ddd9f@185.189.45.195:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=get.jarbook.net&fp=firefox&security=reality&pbk=BIy6H-jndn24Ukyw83ML8LDB1HL8WLJmfCADEy8lzVs&sid=c6f97313#%F0%9F%87%B8%F0%9F%87%AA%20%D0%A8%D0%B2%D0%B5%D1%86%D0%B8%D1%8F%20%E2%9A%A1",
    "vless://67cd3349-f789-4cbb-8b91-4b6b1654ce7c@151.101.36.235:443/?type=xhttp&encryption=none&flow=&host=ovd13.global.ssl.fastly.net&path=%2F&mode=auto&extra=%7B%0A%20%20%22xPaddingBytes%22%3A%20%22100-1000%22%2C%0A%20%20%22scMaxEachPostBytes%22%3A%20%22500000%22%2C%0A%20%20%22scMinPostsIntervalMs%22%3A%20%2260%22%2C%0A%20%20%22noGRPCHeader%22%3A%20true%2C%0A%20%20%22xmux%22%3A%20%7B%0A%20%20%20%20%22maxConnections%22%3A%20%2216%22%2C%0A%20%20%20%20%22cMaxReuseTimes%22%3A%20%220%22%2C%0A%20%20%20%20%22hMaxRequestTimes%22%3A%20%22600-900%22%2C%0A%20%20%20%20%22hMaxReusableSecs%22%3A%20%221800-3000%22%2C%0A%20%20%20%20%22hKeepAlivePeriod%22%3A%200%0A%20%20%7D%2C%0A%20%20%22scMaxConcurrentPosts%22%3A%20100%0A%7D&security=tls&sni=accounts.fastly.com&alpn=h3&fp=chrome#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%E2%9A%A1%20Gemini%20%F0%9F%A4%96",
    "vless://0000be2c-fb3a-5bce-a7d7-2105d461915b@188.72.103.4:443/?type=xhttp&encryption=none&flow=&host=cdnapiv2.tronglob5.net&path=%2Fcontent%2Fcatalog%2Fitems%2F&mode=packet-up&extra=%7B%0A%20%20%22headers%22%3A%20%7B%0A%20%20%20%20%22User-Agent%22%3A%20%22Mozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F120.0.0.0%20Safari%2F537.36%22%0A%20%20%7D%2C%0A%20%20%22xPaddingBytes%22%3A%20%2264-768%22%2C%0A%20%20%22scMaxEachPostBytes%22%3A%20%2216384%22%2C%0A%20%20%22scMinPostsIntervalMs%22%3A%20%2210%22%2C%0A%20%20%22noGRPCHeader%22%3A%20true%2C%0A%20%20%22noSSEHeader%22%3A%20true%2C%0A%20%20%22scMaxBufferedPosts%22%3A%20128%2C%0A%20%20%22uplinkDataPlacement%22%3A%20%22header%22%2C%0A%20%20%22uplinkDataKey%22%3A%20%22X-Media-Token%22%2C%0A%20%20%22uplinkChunkSize%22%3A%20%227500%22%2C%0A%20%20%22uplinkHTTPMethod%22%3A%20%22GET%22%2C%0A%20%20%22seqPlacement%22%3A%20%22cookie%22%2C%0A%20%20%22seqKey%22%3A%20%22part%22%2C%0A%20%20%22xPaddingObfsMode%22%3A%20true%2C%0A%20%20%22xPaddingKey%22%3A%20%22cs%22%2C%0A%20%20%22xPaddingHeader%22%3A%20%22X-Cache-Status%22%2C%0A%20%20%22xPaddingPlacement%22%3A%20%22queryInHeader%22%2C%0A%20%20%22xPaddingMethod%22%3A%20%22tokenish%22%2C%0A%20%20%22serverMaxHeaderBytes%22%3A%2065535%2C%0A%20%20%22sessionPlacement%22%3A%20%22cookie%22%2C%0A%20%20%22sessionKey%22%3A%20%22view_id%22%2C%0A%20%20%22sessionIDPlacement%22%3A%20%22cookie%22%2C%0A%20%20%22sessionIDKey%22%3A%20%22view_id%22%2C%0A%20%20%22sessionIDTable%22%3A%20%22Base62%22%2C%0A%20%20%22sessionIDLength%22%3A%20%2216-32%22%2C%0A%20%20%22xmux%22%3A%20%7B%0A%20%20%20%20%22maxConcurrency%22%3A%20%2216-32%22%2C%0A%20%20%20%20%22maxConnections%22%3A%20%220%22%2C%0A%20%20%20%20%22cMaxReuseTimes%22%3A%20%22100%22%0A%20%20%7D%2C%0A%20%20%22mode%22%3A%20%22packet-up%22%2C%0A%20%20%22path%22%3A%20%22%2Fcontent%2Fcatalog%2Fitems%2F%22%0A%7D&security=tls&sni=cdnapiv2.tronglob5.net&alpn=h2%2Chttp%2F1.1&fp=edge#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%E2%9A%A1%20YT%20%F0%9F%93%BA%20AI%F0%9F%A4%96",
    "vless://18669c97-4d3e-03e9-a94e-b250e7aac408@201.24.113.19:8443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=ya.ru&fp=firefox&security=reality&pbk=DulhUFMYzxIsucjtPONJQMszzyi9V6bqQ9WI3GjGFAY&sid=abc123#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%E2%9A%A1%20YouTube%20%F0%9F%93%BA",
    "vless://18669c97-4d3e-03e9-a94e-b250e7aac408@72.56.11.15:8443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=ya.ru&fp=firefox&security=reality&pbk=DulhUFMYzxIsucjtPONJQMszzyi9V6bqQ9WI3GjGFAY&sid=abc123#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%E2%9A%A1%20YouTube%20%F0%9F%93%BA",
    "vless://4cabcd59-a405-4c00-96f5-03507e1e28fa@cadrin.wtf:443/?type=grpc&encryption=none&flow=&serviceName=cache.sync.v1&security=tls&sni=cadrin.wtf&fp=chrome#%F0%9F%87%B7%F0%9F%87%BA%20-%3E%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%F0%9F%90%8C%20YouTube%20%F0%9F%93%BA",
    "vless://4cabcd59-a405-4c00-96f5-03507e1e28fa@torvani.cyou:443/?type=ws&encryption=none&flow=&host=torvani.cyou&path=%2Fapi%2Fboards%2Flive&security=tls&sni=torvani.cyou&fp=chrome#%F0%9F%87%B7%F0%9F%87%BA%20-%3E%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%F0%9F%90%8C%20YouTube%20%F0%9F%93%BA",
    "vless://3f5e89d5-591f-4ac9-b071-b05680b573c3@138.124.242.46:8443/?type=grpc&encryption=none&flow=&serviceName=connect-pl&security=tls&sni=pl2-edge.gacvpn.site#%F0%9F%87%B5%F0%9F%87%B1%20%D0%9F%D0%BE%D0%BB%D1%8C%D1%88%D0%B0%20YouTube%20%F0%9F%93%BA",
    "vless://67cd3349-f789-4cbb-8b91-4b6b1654ce7c@151.101.36.2:443/?type=xhttp&encryption=none&flow=&host=oh4.global.ssl.fastly.net&path=%2F&mode=auto&extra=%7B%0A%20%20%22xPaddingBytes%22%3A%20%22100-1000%22%2C%0A%20%20%22scMaxEachPostBytes%22%3A%20%22500000%22%2C%0A%20%20%22scMinPostsIntervalMs%22%3A%20%2260%22%2C%0A%20%20%22noGRPCHeader%22%3A%20true%2C%0A%20%20%22xmux%22%3A%20%7B%0A%20%20%20%20%22maxConnections%22%3A%20%2216%22%2C%0A%20%20%20%20%22cMaxReuseTimes%22%3A%20%220%22%2C%0A%20%20%20%20%22hMaxRequestTimes%22%3A%20%22600-900%22%2C%0A%20%20%20%20%22hMaxReusableSecs%22%3A%20%221800-3000%22%2C%0A%20%20%20%20%22hKeepAlivePeriod%22%3A%200%0A%20%20%7D%2C%0A%20%20%22scMaxConcurrentPosts%22%3A%20100%0A%7D&security=tls&sni=accounts.fastly.com&alpn=h3&fp=chrome#%F0%9F%87%AB%F0%9F%87%B7%20%D0%A4%D1%80%D0%B0%D0%BD%D1%86%D0%B8%D1%8F%20YT%20%F0%9F%93%BA%20AI%F0%9F%A4%96",
    #пропуск (не удалять!) . - , получается хуйня такая
]


# ============================================================
# НАСТРОЙКИ
# ============================================================

TARGET_COUNT = 60          # сколько конфигов взять в итоге (не считая закреплённых)
EARLY_STOP_MULT = 4        # остановить проверку, когда найдено TARGET_COUNT * N рабочих
                           # (запас нужен: часть отсеется проверкой «из РФ»). 0 = проверять все (было 5)

MAX_PING_MS = 3000         # отсечка совсем медленных (итоговый балл: пинг + вклад скорости)
GOOD_PING_MS = 300         # «быстрый» сервер (❄️ в названии); ≤3× — ⛄, дальше — 🧊

MAX_TCP_PING_MS = 1700     # TCP-пинг выше этого (или нет ответа) — в ядро не идёт
TCP_CONCURRENCY = 300      # одновременных TCP-проверок (было 200)

# --- Зима ---
# True — всегда, False — никогда, "auto" — только с 1 ноября по 28 февраля
WINTER = True
WINTER_FAST = "❄️"         # быстрый (≤ GOOD_PING_MS)
WINTER_MID = "⛄"           # нормальный (≤ 3×)
WINTER_SLOW = "🧊"         # медленный

# --- Подмена HWID (подписки с привязкой к устройству: Happ / Remnawave / Marzban и т.п.) ---
# HWID один и тот же при каждом запуске (берётся из seed) — чтобы не плодить «новые устройства»
# и не упираться в лимит устройств на подписке. Одинаковый seed в МИКС и ЧС = одно «устройство».
HWID_SPOOF = True
HWID_SEED = os.environ.get("HWID_SEED", "PizMod")
HWID_FIXED = os.environ.get("SUB_HWID", "")   # если задан — используется как есть
HWID_OS = "Android"
HWID_OS_VER = "14"
HWID_MODEL = "Pixel 8"

# --- Gemini: если через конфиг открывается Gemini — в конец названия добавляется 🤖 ---
GEMINI_CHECK = True
GEMINI_URL = "https://gemini.google.com"
GEMINI_MARKERS = ("45631641,null,true",)   # маркер «регион поддерживается» в HTML страницы
GEMINI_TIMEOUT = 12.0
GEMINI_TAG = "🤖"
GEMINI_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "SOCS=CAI",      # без окна согласия для EU-выходов
}

# --- Скачивание подписок ---
FETCH_TIMEOUT = 20.0
FETCH_RETRIES = 3          # сколько раз пробовать каждый источник
FETCH_HEADERS_LIST = [     # User-Agent меняется от попытки к попытке
    {"User-Agent": "v2rayN/6.42"},
    {"User-Agent": "Happ/7.0.0"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64;)"},
]

CONCURRENCY = 40           # одновременных xray/sing-box процессов (было 15; ~30-50 МБ RAM на процесс)
XRAY_STARTUP_TIMEOUT = 6.0 # сек: максимум ждём, пока ядро откроет локальный порт
XRAY_TEST_TIMEOUT = 10.0   # сек на ОДИН тестовый запрос через прокси
XRAY_BINARY = "xray"       # должен быть в PATH

# --- Hy2 (проверяется через sing-box, т.к. это UDP/QUIC) ---
CHECK_HY2 = True           # False — не проверять hy2 вообще
SINGBOX_BINARY = "sing-box"  # должен быть в PATH (нужна версия 1.11+)
MAX_HY2 = 8                # максимум hy2 в итоге (UDP/QUIC из РФ часто режется; 0 = без лимита)

# Тестовые URL — те же, что обычно использует клиент (google/gstatic) + cloudflare
TEST_URLS = [
    "https://cp.cloudflare.com/generate_204",
    "https://www.gstatic.com/generate_204",
    "https://www.google.com/generate_204",
]

# --- БЫСТРЫЙ ШЛЮЗ (первый шаг полной проверки, на том же запущенном ядре) ---
# Два лёгких запроса параллельно. Отсеивает конфиги, у которых порт открыт, но сам прокси
# не работает (неверный ключ, мёртвый reality и т.п.), за QUICK_TIMEOUT секунд, а не за минуту.
QUICK_CHECK = True
QUICK_URLS = TEST_URLS[:2]  # какие URL дёргаем
QUICK_TIMEOUT = 6.0         # сек на запрос
QUICK_MIN_OK = 1            # сколько из QUICK_URLS должны ответить

# Проверка: тестовые URL должны отвечать, но одиночный сбой прощается.
# Холодный раунд = быстрый шлюз; тёплые запросы (keep-alive и доп. раунды) идут в пинг.
CHECK_ROUNDS = 1            # раундов всего (1 = холодный + один тёплый проход после паузы)
TEST_MAX_FAILS = 1          # сколько запросов можно провалить

# --- Защита от «соединение закрыто» и тайм-аутов ---
IDLE_PAUSE = 1.0            # пауза перед повторным запросом по тому же соединению (было 2.0)
BURST_PARALLEL = 8          # параллельных запросов на новых соединениях
BURST_MAX_FAILS = 2         # сколько из них можно провалить

# --- Скачивание ---
DOWNLOAD_URLS = [           # достаточно, чтобы прошёл ХОТЯ БЫ ОДИН
    "https://speed.cloudflare.com/__down?bytes=1000000",
    "https://proof.ovh.net/files/1Mb.dat",
]
DOWNLOAD_BYTES = 1_000_000
DOWNLOAD_TIMEOUT = 15.0
REQUIRE_DOWNLOAD = True     # False — если раннер не достаёт до DOWNLOAD_URLS
DOWNLOAD_MAX_MS = 10000     # 1 МБ дольше этого — слишком медленно
SPEED_WEIGHT = 0.1          # вклад времени загрузки/отдачи в итоговый балл (ниже = лучше)

# --- Отдача (upload): ловит «полусломанные» туннели, где вниз идёт, а вверх нет ---
UPLOAD_URL = "https://speed.cloudflare.com/__up"
UPLOAD_BYTES = 256 * 1024
UPLOAD_TIMEOUT = 15.0
UPLOAD_MAX_MS = 9000
REQUIRE_UPLOAD = True       # False — если раннер не достаёт до UPLOAD_URL

# --- Доступ к заблокированным сайтам (главное для ЧС-подписки) ---
BLOCKED_URLS = [
    "https://www.youtube.com/generate_204",
    "https://www.tiktok.com/",
    "https://www.instagram.com/",
]
MIN_BLOCKED_OK = 1          # сколько из BLOCKED_URLS должны открыться (0 = не проверять)

# --- Стабильность ---
MAX_JITTER = 4.0            # макс/мин пинг в тёплых запросах (+100 мс запаса)
REQUIRE_STABLE_EXIT_IP = True   # выходной IP не должен «плавать» между запросами

# --- Cloudflare trace: выходной IP + страна ПРЯМО через прокси (без лимитов гео-сервисов) ---
USE_CF_TRACE = True
CF_TRACE_URL = "https://www.cloudflare.com/cdn-cgi/trace"

# Выходы в этих странах отбрасываются (для ЧС-подписки выход в РФ обычно бесполезен).
# Пример: {"RU", "BY"}. Пусто = не фильтровать. Закреплённых это не касается.
EXCLUDE_EXIT_COUNTRIES = set()

# --- Реальная проверка выходного IP ---
# Через каждый прокси спрашиваем у IP-эхо сервисов (параллельно), какой у нас IP.
IP_ECHO_URLS = [
    "https://api.ipify.org",
    "https://icanhazip.com",
    "https://ifconfig.me/ip",
]
REQUIRE_EXIT_IP = True      # не получили выходной IP или он = нашему → конфиг нерабочий
DEDUPE_BY_EXIT_IP = True    # дубли по реальному выходному IP
DEDUPE_BY_SETTINGS = True   # дубли: те же host:port и настройки, но разные uuid/пароли
MAX_PER_SUBNET = 6          # максимум серверов из одной подсети /24 (0 = без лимита):
                            # «фермы» из одной подсети разом падают/блокируются

# --- Проверка «из России» ---
RU_CHECK = True
CHECK_HOST_API = "https://check-host.net"
RU_NODES_MAX = 4            # сколько российских узлов использовать
RU_MIN_OK = 2               # сколько узлов должны достучаться (если ответивших меньше — все они)
RU_CHECK_CONCURRENCY = 5    # одновременных запросов к check-host (было 3; выше — лимиты API, 429)
RU_MAX_CHECKS = 200         # максимум конфигов, которые отправим в check-host за запуск (было 350)
RU_FIRST_POLL = 1.5         # сек до первого опроса результата
RU_POLL_EVERY = 1.0         # сек между опросами (раньше 2.0)
RU_RESULT_WAIT = 12.0       # сек ждать результаты одной проверки (было 14)
RU_FAIL_OPEN = True         # check-host недоступен -> не отбрасывать (иначе подписка опустеет)

# Повторная проверка лучших кандидатов отдельным запуском ядра (идёт ПАРАЛЛЕЛЬНО с проверкой «из РФ»):
# отсекает «мигающие» серверы, которые прошли проверку случайно.
CONFIRM_BEST = True
CONFIRM_RUNS = 1           # сколько ДОПОЛНИТЕЛЬНЫХ прогонов должен пройти конфиг
CONFIRM_PAUSE = 15.0       # пауза между прогонами (работает только при CONFIRM_RUNS > 1)
CONFIRM_SPARE = 10         # сколько лишних кандидатов брать с запасом на выбывших
CONFIRM_CONCURRENCY = 10   # (было 5)

# --- Тип интернета в названии ---
# Определить реальный тип сети (LTE/Wi-Fi) проверкой нельзя, поэтому метка ставится
# по признаку «белого списка»: SNI/host конфига — из домена, который работает на
# мобильном интернете РФ даже при ограничениях.
LTE_TAG_ENABLED = True
LTE_TAG = "LTE 📶"
LTE_SNI_DOMAINS = (
    "ya.ru", "yandex.ru", "yandex.net", "max.ru", "vk.com", "vk.ru", "vkontakte.ru",
    "mail.ru", "ok.ru", "dzen.ru", "rutube.ru", "gosuslugi.ru", "sberbank.ru",
    "sber.ru", "avito.ru", "ozon.ru", "wildberries.ru", "kinopoisk.ru", "2gis.ru",
    "userapi.com", "mycdn.me", "vkuser.net",
)

GEO_CITY_CONCURRENCY = 4   # одновременных запросов города (по IP выхода, бесплатные API)
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
_trace_loc = {}             # config -> страна выхода по Cloudflare trace
_gemini = {}                # config -> True, если Gemini открылся хотя бы в одном прогоне
_fail = Counter()           # причина отказа -> сколько конфигов
_T0 = time.monotonic()


# ============================================================
# ЛОГ (для CI): время от старта + итоговая сводка
# ============================================================

def elapsed():
    s = int(time.monotonic() - _T0)
    return f"{s // 60:02d}:{s % 60:02d}"


def stage(title):
    print(f"\n[⏱ {elapsed()}] {title}")


def write_step_summary(lines):
    """Если CI поддерживает $GITHUB_STEP_SUMMARY — пишем туда короткую сводку (иначе ничего не делаем)."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass


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

# Запасной словарь, если ни один сервис не вернул город по-русски
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

# Длинные названия городов сокращаем (применяется ко всем городам после перевода)
CITY_SHORT = {
    "Франкфурт-на-Майне": "Франкфурт",
    "Франкфурт-на-Одере": "Франкфурт",
    "Франкфурт-Майн": "Франкфурт",
    "Frankfurt am Main": "Франкфурт",
    "Шяуляйское городское самоуправление": "Шауляй",
}


def short_city(city):
    city = str(city).strip()
    if city in CITY_SHORT:
        return CITY_SHORT[city]
    # «Франкфурт-на-...» / «Франкфурт am Main» → «Франкфурт»
    return re.sub(r"^(Франкфурт)(?:-на-[А-Яа-яЁё]+|\s+am\s+Main)$", r"\1", city)


# Серверы за этими CDN не считаем каскадом (страна «входа» там ничего не значит)
CDN_WORDS = ("cloudflare", "fastly", "akamai", "cloudfront", "gcore", "bunny")


# ============================================================
# ЗИМА
# Имя конфига: «[{флаг входа} -> ]{флаг выхода} Страна — Город {тег} [LTE 📶] [🤖]»
# Флаг остаётся первым (клиенты берут из него значок), тег скорости — после города:
#   ❄️ быстрый (≤ GOOD_PING_MS), ⛄ нормальный (≤ 3×), 🧊 медленный.
# Для каскада впереди добавляется «флаг входа -> ». Метка LTE — если подходит.
# 🤖 — в самом конце, только если через конфиг открывается Gemini.
# ============================================================

WINTER_ANNOUNCE = "❄️ Телеграм канал: @PizMod ⛄\n🎄Автообновление каждые 6 часов🧊"


def winter_on():
    if WINTER is True:
        return True
    if WINTER is False:
        return False
    return datetime.date.today().month in (11, 12, 1, 2)  # "auto"


def winter_tag(score):
    if score <= GOOD_PING_MS:
        return WINTER_FAST
    if score <= GOOD_PING_MS * 3:
        return WINTER_MID
    return WINTER_SLOW


def winter_header(lines):
    """Подменяет заголовок подписки (название и анонс) на зимние."""
    out = []
    for line in lines:
        if line.startswith("#profile-title:"):
            title = line.replace("🏴", "❄️")
            if "❄" not in title:
                title = title.rstrip() + "❄️"
            out.append(title)
        elif line.startswith("#announce:"):
            enc = base64.b64encode(WINTER_ANNOUNCE.encode("utf-8")).decode("ascii")
            out.append(f"#announce: base64: {enc}")
        else:
            out.append(line)
    return out


# ============================================================
# HWID
# ============================================================

def make_hwid():
    if HWID_FIXED.strip():
        return HWID_FIXED.strip()
    return hashlib.sha256(HWID_SEED.encode("utf-8")).hexdigest()[:16]


HWID = make_hwid()


def hwid_headers():
    """Заголовки «устройства» (как у Happ): x-hwid, x-device-os, x-ver-os, x-device-model."""
    if not HWID_SPOOF:
        return {}
    return {
        "x-hwid": HWID,
        "x-device-os": HWID_OS,
        "x-ver-os": HWID_OS_VER,
        "x-device-model": HWID_MODEL,
    }


def build_fetch_headers(attempt):
    headers = dict(FETCH_HEADERS_LIST[attempt % len(FETCH_HEADERS_LIST)])
    headers.update(hwid_headers())
    return headers


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
        city = short_city(city)
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


# Параметры, по которым сравниваются «настройки» конфига (без uuid/пароля и названия)
_SETTINGS_PARAMS = ("type", "security", "sni", "pbk", "path", "servicename", "host",
                    "mode", "obfs", "alpn")


def settings_key(line):
    """Ключ «одинаковые настройки»: сервер (host:port) + транспорт/безопасность/SNI/ключ,
    но БЕЗ uuid/пароля. Один сервер, выданный разным пользователям с разными uuid,
    даёт один и тот же ключ."""
    if line.startswith("vmess://"):
        data = b64decode_safe(line[len("vmess://"):])
        if data:
            try:
                o = json.loads(data)
                return ("vmess", str(o.get("add")).strip().lower(), str(o.get("port")),
                        str(o.get("net")), str(o.get("path")), str(o.get("host")),
                        str(o.get("tls")), str(o.get("sni")))
            except Exception:
                pass
        return (line,)

    scheme, _, rest = line.partition("://")
    scheme = scheme.lower()
    if scheme == "hysteria2":
        scheme = "hy2"
    body = rest.split("#", 1)[0]
    main, _, query = body.partition("?")
    netloc = main.split("/", 1)[0]
    _, _, hostport = netloc.rpartition("@")
    params = {k.lower(): v[0] for k, v in parse_qs(query, keep_blank_values=True).items() if v}
    return (scheme, hostport.lower(),
            tuple((k, params.get(k, "")) for k in _SETTINGS_PARAMS))


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
# ТИП ИНТЕРНЕТА (метка LTE)
# ============================================================

def config_sni(line):
    """SNI (или host) конфига в нижнем регистре, либо ''."""
    try:
        if line.startswith("vmess://"):
            data = b64decode_safe(line[len("vmess://"):])
            o = json.loads(data) if data else {}
            return str(o.get("sni") or o.get("host") or "").strip().lower()
        if line.startswith(HY2_SCHEMES):
            parts = split_hy2(line)
            if not parts:
                return ""
            _, host, _, params = parts
            return str(first(params, "sni", "peer") or "").strip().lower()
        params = query_params(urlparse(line))
        return str(first(params, "sni", "servername", "host") or "").strip().lower()
    except Exception:
        return ""


def is_lte(line):
    """True, если SNI/host конфига — из «белого» домена (работает на мобильном интернете)."""
    sni = config_sni(line)
    if not sni:
        return False
    return any(sni == d or sni.endswith("." + d) for d in LTE_SNI_DOMAINS)


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
            await asyncio.sleep(0.05)
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
# IP / TRACE / GEMINI ЧЕРЕЗ ПРОКСИ
# ============================================================

async def _noop(value=None):
    return value


async def fetch_ip(session, timeout=8.0):
    """Выходной IP: все эхо-сервисы опрашиваются параллельно, берём первый валидный ответ."""
    t = aiohttp.ClientTimeout(total=timeout)

    async def one(url):
        async with session.get(url, timeout=t) as resp:
            if resp.status != 200:
                raise ValueError(f"status {resp.status}")
            text = (await resp.text()).strip()
        ipaddress.ip_address(text)  # убедимся, что это именно IP
        return text

    tasks = [asyncio.ensure_future(one(u)) for u in IP_ECHO_URLS]
    try:
        for fut in asyncio.as_completed(tasks):
            try:
                return await fut
            except Exception:
                continue
        return None
    finally:
        for tk in tasks:
            tk.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def fetch_trace(session, timeout=8.0):
    """Cloudflare trace через прокси: возвращает (ip, страна) или None."""
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


async def check_gemini(session):
    """True, если через прокси открывается Gemini (в HTML есть маркер «регион поддерживается»)."""
    try:
        async with session.get(GEMINI_URL, headers=GEMINI_HEADERS,
                               timeout=aiohttp.ClientTimeout(total=GEMINI_TIMEOUT)) as resp:
            if resp.status != 200:
                return False
            body = await resp.text(errors="ignore")
        return any(m in body for m in GEMINI_MARKERS)
    except Exception:
        return False


def _same_family_diff(a, b):
    """True, если оба — IP одной версии (v4/v6) и они РАЗНЫЕ."""
    try:
        ia, ib = ipaddress.ip_address(a), ipaddress.ip_address(b)
    except Exception:
        return False
    return ia.version == ib.version and ia != ib


# ============================================================
# ОДИН ТЕСТОВЫЙ ЗАПРОС: бросает исключение при любой ошибке
# (статус не из ok_status, обрыв, тайм-аут, слишком короткое тело)
# Возвращает время в мс.
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
    """Фиксирует причину отказа (для сводки в конце) и возвращает None."""
    _fail[reason] += 1
    return None


async def _blocked_count(session):
    res = await asyncio.gather(
        *(_fetch_ok(session, u, timeout=10, ok_status=range(200, 400)) for u in BLOCKED_URLS),
        return_exceptions=True,
    )
    return sum(not isinstance(r, Exception) for r in res)


# ============================================================
# РЕАЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ ЯДРО (xray / sing-box) — возвращает балл (мс) или None
# Одно запущенное ядро на весь конфиг, от дешёвых проверок к дорогим:
#   1) быстрый шлюз: 2 запроса параллельно (мёртвые отсеиваются за QUICK_TIMEOUT);
#      пауза и повтор по тому же соединению (keep-alive), HTTPS-сертификаты проверяются,
#      ответ 204 должен быть пустым; джиттер считается сразу;
#   2) выходной IP + Cloudflare trace (страна) + заблокированные сайты — ОДНОВРЕМЕННО;
#      «плавающий» выходной IP отсеивается;
#   3) параллельный залп на новых соединениях;
#   4) скачивание ~1 МБ и отдача (upload) — обрывы и «полусломанные» туннели;
#   5) выходной IP не изменился к концу + проверка Gemini (одновременно).
# Балл = медиана пинга в тёплых запросах + вклад времени загрузки и отдачи.
# Одинаково для vless / vmess / trojan / ss / hy2.
# ============================================================

async def _probe(line, port):
    proxy = f"socks5://127.0.0.1:{port}"
    timeout = aiohttp.ClientTimeout(total=XRAY_TEST_TIMEOUT)

    latencies = []
    fails = 0
    try:
        connector = aiohttp_socks.ProxyConnector.from_url(proxy)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # холодный раунд = быстрый шлюз
            res = await asyncio.gather(
                *(_fetch_ok(session, u, timeout=QUICK_TIMEOUT) for u in QUICK_URLS),
                return_exceptions=True,
            )
            ok = sum(not isinstance(r, Exception) for r in res)
            if QUICK_CHECK and ok < QUICK_MIN_OK:
                return _reject("быстрая проверка: прокси не отвечает")
            fails += len(res) - ok
            if fails > TEST_MAX_FAILS:
                return _reject("тестовые URL / keep-alive")

            # дополнительные тёплые раунды (если CHECK_ROUNDS > 1)
            for _ in range(1, CHECK_ROUNDS):
                for url in TEST_URLS:
                    try:
                        latencies.append(await _fetch_ok(session, url))   # ssl-проверка ВКЛЮЧЕНА
                    except Exception:
                        fails += 1
                        if fails > TEST_MAX_FAILS:
                            return _reject("тестовые URL / keep-alive")

            # пауза + повтор по тому же соединению (рвёт ли сервер keep-alive)
            await asyncio.sleep(IDLE_PAUSE)
            for url in TEST_URLS:
                try:
                    latencies.append(await _fetch_ok(session, url))
                except Exception:
                    fails += 1
                    if fails > TEST_MAX_FAILS:
                        return _reject("тестовые URL / keep-alive")
    except Exception:
        return _reject("тестовые URL / keep-alive")

    # джиттер считаем сразу: это бесплатно, а «плохой» конфиг не доходит до дорогих проверок
    if not latencies:
        return _reject("нет замеров пинга")
    if max(latencies) > MAX_JITTER * min(latencies) + 100:
        return _reject("нестабильный пинг (джиттер)")

    exit_ip = None
    connector_b = aiohttp_socks.ProxyConnector.from_url(proxy)
    async with aiohttp.ClientSession(connector=connector_b, timeout=timeout) as session:
        echo_ip, tr, blocked_ok = await asyncio.gather(
            fetch_ip(session, XRAY_TEST_TIMEOUT),
            fetch_trace(session, XRAY_TEST_TIMEOUT) if USE_CF_TRACE else _noop(),
            _blocked_count(session) if (BLOCKED_URLS and MIN_BLOCKED_OK) else _noop(MIN_BLOCKED_OK),
        )
        t_ip, t_loc = tr if tr else (None, "")

        exit_ip = echo_ip or t_ip
        if REQUIRE_EXIT_IP and (not exit_ip or (_my_ip and exit_ip == _my_ip)):
            return _reject("нет выходного IP / совпал с моим")
        if REQUIRE_STABLE_EXIT_IP and echo_ip and t_ip and _same_family_diff(echo_ip, t_ip):
            return _reject("выходной IP «плавает»")
        if t_loc:
            _trace_loc[line] = t_loc
            if t_loc in EXCLUDE_EXIT_COUNTRIES:
                return _reject("выход в исключённой стране")
        if exit_ip:
            _exit_ip[line] = exit_ip

        if blocked_ok < MIN_BLOCKED_OK:
            return _reject("заблокированные сайты недоступны")

    # параллельный залп на НОВЫХ соединениях + загрузка и отдача
    dl_ms = None
    up_ms = None
    conn2 = aiohttp_socks.ProxyConnector.from_url(proxy, force_close=True)
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

        # финал: стабильность выходного IP и Gemini — одновременно (Gemini только для прошедших всё)
        want_ip2 = REQUIRE_STABLE_EXIT_IP and exit_ip
        ip2, gem = await asyncio.gather(
            fetch_ip(s2, XRAY_TEST_TIMEOUT) if want_ip2 else _noop(),
            check_gemini(s2) if GEMINI_CHECK else _noop(False),
        )
        if want_ip2 and ip2 and _same_family_diff(exit_ip, ip2):
            return _reject("выходной IP «плавает»")
        if GEMINI_CHECK:
            _gemini[line] = _gemini.get(line, False) or bool(gem)

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
# ПРОВЕРКА «ИЗ РОССИИ» через check-host.net (TCP с российских узлов)
# Ловит серверы, которые отвечают зарубежному раннеру, но недоступны
# российским провайдерам (блокировка IP/порта, DNS-подмена) — именно они
# в клиенте показывают «Тайм-аут» и «Соединение закрыто».
# UDP (hy2) так проверить нельзя — они идут без этой проверки (но с лимитом MAX_HY2).
# Решение принимается как только оно очевидно, не дожидаясь всех узлов.
# ============================================================

_ru_nodes = []
_ru_api_dead = False
_ru_api_fails = 0

_CH_HEADERS = {"Accept": "application/json"}


def parse_ru_result(res, need):
    """Разбор ответа check-result.
    res: {node: [ {"time": 0.03, "address": ...} ] | [ {"error": "..."} ] | None}
    Возвращает (ok_nodes, answered_nodes, passed)."""
    ok = answered = 0
    for _node, val in (res or {}).items():
        if val is None:
            continue
        answered += 1
        try:
            item = val[0]
        except Exception:
            continue
        if isinstance(item, dict) and "time" in item and "error" not in item:
            ok += 1
    if answered == 0:
        return 0, 0, None          # узлы не ответили — результат неизвестен
    return ok, answered, ok >= min(need, answered)


async def ru_load_nodes(session):
    """Список российских узлов check-host.net."""
    try:
        async with session.get(f"{CHECK_HOST_API}/nodes/hosts", headers=_CH_HEADERS,
                               timeout=aiohttp.ClientTimeout(total=15)) as r:
            data = await r.json(content_type=None)
        nodes = [n for n in (data.get("nodes") or {}) if str(n).lower().startswith("ru")]
        return sorted(nodes)[:RU_NODES_MAX]
    except Exception:
        return []


def _ru_api_failed():
    global _ru_api_fails, _ru_api_dead
    _ru_api_fails += 1
    if _ru_api_fails >= 8:
        _ru_api_dead = True


async def ru_tcp_check(session, hostport):
    """True/False — доступен ли host:port с российских узлов; None — не удалось узнать."""
    global _ru_api_fails
    params = [("host", hostport)] + [("node", n) for n in _ru_nodes]
    rid = None
    for attempt in range(3):
        try:
            async with session.get(f"{CHECK_HOST_API}/check-tcp", params=params, headers=_CH_HEADERS,
                                   timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 429:
                    await asyncio.sleep(4 * (attempt + 1))
                    continue
                if r.status != 200:
                    break
                data = await r.json(content_type=None)
            rid = data.get("request_id")
            break
        except Exception:
            await asyncio.sleep(1.5)
    if not rid:
        _ru_api_failed()
        return None

    res = {}
    deadline = time.monotonic() + RU_RESULT_WAIT
    await asyncio.sleep(RU_FIRST_POLL)
    while True:
        try:
            async with session.get(f"{CHECK_HOST_API}/check-result/{rid}", headers=_CH_HEADERS,
                                   timeout=aiohttp.ClientTimeout(total=15)) as r:
                res = await r.json(content_type=None)
        except Exception:
            pass

        ok, answered, passed = parse_ru_result(res, RU_MIN_OK)
        total = max(len(res or {}), len(_ru_nodes))
        pending = max(0, total - answered)

        if ok >= RU_MIN_OK:                       # достаточно узлов достучались — решение принято
            _ru_api_fails = 0
            return True
        if answered and answered > ok and ok + pending < RU_MIN_OK:
            _ru_api_fails = 0                     # уже не набрать нужное число — отбрасываем
            return False
        if pending == 0 and answered:             # ответили все
            _ru_api_fails = 0
            return bool(passed)
        if time.monotonic() >= deadline:
            break
        await asyncio.sleep(RU_POLL_EVERY)

    if passed is None:
        _ru_api_failed()
        return None
    _ru_api_fails = 0
    return bool(passed)


def cap_hy2(items):
    """Оставляет не более MAX_HY2 лучших hy2 (UDP из РФ часто режется)."""
    if not MAX_HY2:
        return items
    out, n = [], 0
    for config, score in items:
        if config.startswith(HY2_SCHEMES):
            n += 1
            if n > MAX_HY2:
                _reject("лимит hy2 (MAX_HY2)")
                continue
        out.append((config, score))
    return out


# ============================================================
# ГЕО ВЫХОДА
# Страна — Cloudflare trace через прокси (во время проверки), город — по IP выхода
# у бесплатных сервисов (только для итоговых конфигов). Если trace не ответил —
# страна по консенсусу нескольких сервисов.
# Город по-русски: сервисы с lang=ru, иначе словарь CITY_RU, иначе город не пишем.
# ============================================================

GEO_PROVIDERS = [
    ("ipinfo", "https://ipinfo.io/{ip}/json"),
    ("ipwho",  "https://ipwho.is/{ip}?lang=ru"),
    ("geojs",  "https://get.geojs.io/v1/ip/geo/{ip}.json"),
    ("dbip",   "https://api.db-ip.com/v2/free/{ip}"),
    ("ipapico", "https://ipapi.co/{ip}/json/"),
    ("ipapi",  "http://ip-api.com/json/{ip}?fields=status,countryCode,city&lang=ru"),
    ("sypex",  "https://api.sypexgeo.net/json/{ip}"),
]
CITY_PROVIDERS = ("ipwho", "ipapi", "geojs")   # по порядку: сначала те, что отдают русские названия

GEO_MIN_AGREE = 2              # минимум сервисов, согласных по стране (запасной путь)

_CYRILLIC = re.compile("[А-Яа-яЁё]")


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


def pick_city_ru(cities):
    """Из списка названий города выбирает русское; иначе переводит словарём; иначе None."""
    for c in cities:
        if _CYRILLIC.search(c):
            return c
    for c in cities:
        if c in CITY_RU:
            return CITY_RU[c]
    return None


async def city_lookup(session, ip, code):
    """Город по-русски для IP выхода. Страна уже известна (trace) — берём только город
    у того сервиса, чья страна совпала. Идём по сервисам по очереди до первого успеха."""
    if not ip or not code:
        return None
    for kind in CITY_PROVIDERS:
        for idx, (k, tpl) in enumerate(GEO_PROVIDERS):
            if k != kind:
                continue
            _, cc, city = await _geo_provider(session, idx, k, tpl, ip)
            if cc == code.upper() and city:
                ru = pick_city_ru([str(city).strip()])
                if ru:
                    return ru
    return None


async def geo_lookup(session, ip, extra_code=None):
    """Страна по КОНСЕНСУСУ нескольких сервисов (запасной путь, если trace не ответил).
    Возвращает (code, geo_name)."""
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
    if extra_code:
        votes.setdefault(extra_code.upper(), []).append((-1, None))
    if not votes:
        return None, None

    responded = sum(len(v) for v in votes.values())
    best = max(votes, key=lambda c: (len(votes[c]), -min(i for i, _ in votes[c])))
    agree = len(votes[best])

    # если ответили ≥2 сервиса, но двое не согласились — не верим никому
    if responded >= GEO_MIN_AGREE and agree < GEO_MIN_AGREE:
        return None, None

    cities = [str(c).strip() for _, c in sorted(votes[best], key=lambda x: x[0]) if c]
    city = pick_city_ru(cities)
    return best, make_geo_name(best, city)


# ============================================================
# КАСКАД: вход и выход в разных странах
# Страна выхода — по реальному выходному IP (она в названии конфига),
# страна ВХОДА — по IP сервера из конфига (host:port), пачкой через ip-api.com/batch.
# Серверы за CDN пропускаем.
# В названии: «{флаг входа} -> {флаг выхода} Страна — Город».
# ============================================================

async def entry_geo_batch(session, ips):
    """ip -> (country_code, 'org as' в нижнем регистре)."""
    result = {}
    ips = sorted(set(ips))
    for i in range(0, len(ips), 100):
        if i:
            await asyncio.sleep(4.5)  # лимит ip-api: 15 batch-запросов в минуту
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
    return result


# ============================================================
# СКАЧИВАНИЕ ПОДПИСОК (с подменой HWID, сменой User-Agent и повтором,
# если ответ пустой — частая заглушка у подписок с привязкой к устройству;
# на последней попытке — без проверки SSL)
# ============================================================

def short_name(url):
    """Короткое имя источника для лога (только домен)."""
    name = urlparse(url).netloc or url
    return name if len(name) <= 28 else name[:27] + "…"


async def fetch_source(session, url):
    timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
    last_err = None
    for attempt in range(FETCH_RETRIES):
        ssl_opt = False if attempt == FETCH_RETRIES - 1 else None
        try:
            async with session.get(url, headers=build_fetch_headers(attempt), timeout=timeout,
                                   allow_redirects=True, ssl=ssl_opt) as response:
                response.raise_for_status()
                raw = await response.text(errors="ignore")
            configs = extract_lines(raw)
            if configs:
                print(f"[i] {short_name(url)}: {len(configs)}")
                return url, configs
            last_err = "в ответе нет конфигов"
        except Exception as e:
            last_err = e
        if attempt < FETCH_RETRIES - 1:
            await asyncio.sleep(1.0)
    err = str(last_err) or type(last_err).__name__
    print(f"[!] {short_name(url)}: {err[:60]}")
    return url, []


# ============================================================
# ПРОВЕРКА ВСЕХ КАНДИДАТОВ
# ============================================================

async def check_all(candidates):
    """Проверяет конфиги через xray / sing-box.
    Возвращает (working, failed): working — список (config, score_ms),
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
                if latency is not None:
                    _reject("итоговый балл выше MAX_PING_MS")
                failed.append(config)
            if done % PROGRESS_EVERY == 0:
                print(f"    [{elapsed()}] проверено {done}/{total} ✓{len(working)}")

    await asyncio.gather(*(worker(c) for c in candidates))
    return working, failed


# ============================================================
# УДАЛЕНИЕ ДУБЛЕЙ ПО РЕАЛЬНОМУ IP:ПОРТ И ПО ВЫХОДНОМУ IP
# Разные домены/названия на один и тот же ip:порт — это один сервер.
# Конфиги с одинаковым выходным IP — тоже считаем дублями.
# Из группы остаётся самый быстрый. Плюс не больше MAX_PER_SUBNET серверов
# из одной подсети /24 (чтобы «ферма» из 20 соседних IP не заняла всё место).
# ============================================================

def _subnet24(ip):
    if ip and re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", ip):
        return ".".join(ip.split(".")[:3])
    return None


async def dedupe_by_ip(items, taken=None):
    """items: список (config, latency), уже отсортированный по баллу.
    taken: множество (ip, port), которые уже заняты (закреплённые)."""
    seen = set(taken or ())
    per_subnet = defaultdict(int)

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
        sub = _subnet24(ip)
        if MAX_PER_SUBNET and sub and per_subnet[sub] >= MAX_PER_SUBNET:
            _reject("лимит на подсеть /24 (MAX_PER_SUBNET)")
            continue
        seen.update(keys)
        if sub:
            per_subnet[sub] += 1
        result.append((config, latency))
    return result


# ============================================================
# ОТБОР ЛУЧШИХ: проверка «из РФ» + повторный прогон ядра — ОДНОВРЕМЕННО
# Идём по кандидатам (уже по возрастанию балла) пачками. Каждый кандидат
# параллельно проверяется check-host'ом из РФ и повторным запуском ядра
# (отсекает «мигающие»). Остаются те, кто прошёл оба; набрали TARGET_COUNT — стоп.
# Раньше эти этапы шли друг за другом — теперь время считается как максимум, а не сумма.
# ============================================================

async def select_best(session, items):
    global _ru_nodes
    use_ru = RU_CHECK
    if use_ru:
        _ru_nodes = await ru_load_nodes(session)
        if not _ru_nodes:
            print("[!] check-host.net: российские узлы недоступны — проверка «из РФ» пропущена")
            use_ru = False
        else:
            print(f"[i] Проверка «из РФ»: узлы {', '.join(n.split('.')[0] for n in _ru_nodes)}")

    ru_sem = asyncio.Semaphore(RU_CHECK_CONCURRENCY)
    cf_sem = asyncio.Semaphore(CONFIRM_CONCURRENCY)
    st = {"checked": 0, "dropped": 0, "unknown": 0}
    confirmed = []

    async def ru_ok(config):
        hp = get_host_port(config)
        if not use_ru or config.startswith(HY2_SCHEMES) or not hp:
            return True                            # UDP/нераспознанное — не проверить
        if _ru_api_dead:
            return RU_FAIL_OPEN
        host, port = hp
        hostport = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
        async with ru_sem:
            res = await ru_tcp_check(session, hostport)
        st["checked"] += 1
        if res is None:
            st["unknown"] += 1
            return RU_FAIL_OPEN
        if not res:
            st["dropped"] += 1
            _reject("недоступен из РФ (check-host TCP)")
        return res

    async def confirm_ok(config, first_score):
        if not CONFIRM_BEST:
            return first_score
        scores = [first_score]
        for i in range(CONFIRM_RUNS):
            if i:
                await asyncio.sleep(CONFIRM_PAUSE)   # пауза вне семафора — слот не занят
            async with cf_sem:
                try:
                    latency = await real_check(config)
                except Exception:
                    latency = None
            if latency is None or latency > MAX_PING_MS:
                return None
            scores.append(latency)
        return sum(scores) / len(scores)

    async def one(config, score):
        ru, avg = await asyncio.gather(ru_ok(config), confirm_ok(config, score))
        if ru and avg is not None:
            confirmed.append((config, avg))

    idx = 0
    while idx < len(items) and len(confirmed) < TARGET_COUNT:
        if use_ru and st["checked"] >= RU_MAX_CHECKS and not _ru_api_dead:
            print(f"[i] Лимит проверок «из РФ» ({RU_MAX_CHECKS}) исчерпан")
            break
        need = TARGET_COUNT - len(confirmed)
        chunk = items[idx: idx + need + CONFIRM_SPARE]
        idx += len(chunk)
        await asyncio.gather(*(one(c, s) for c, s in chunk))
        print(f"    [{elapsed()}] подтверждено {len(confirmed)}/{TARGET_COUNT} "
              f"(просмотрено {idx}/{len(items)}; из РФ: проверено {st['checked']}, "
              f"отсеяно {st['dropped']}, неизвестно {st['unknown']})")

    if _ru_api_dead:
        print("[!] check-host.net перестал отвечать — часть конфигов взята без проверки «из РФ»")

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

    try:  # вывод сразу, без буфера (важно для CI) и в UTF-8 (эмодзи в логе)
        sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
    except Exception:
        pass

    init_port_pool(CONCURRENCY)

    winter = winter_on()
    if winter:
        print("[i] ❄️ Зимний режим: названия с тегами скорости")
    if HWID_SPOOF:
        print(f"[i] HWID: {HWID[:6]}… ({HWID_MODEL}, {HWID_OS} {HWID_OS_VER})")

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
        stage("Скачиваю подписки...")
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
        pinned_protos = [c for c in pinned if c.startswith(PROTOCOLS)]
        seen = {dedupe_key(c) for c in pinned_protos}
        seen_settings = {settings_key(c) for c in pinned_protos} if DEDUPE_BY_SETTINGS else set()

        unique = []
        same_settings = 0
        for c in all_configs:
            k = dedupe_key(c)
            if k in seen:
                continue
            seen.add(k)
            if DEDUPE_BY_SETTINGS:
                sk = settings_key(c)
                if sk in seen_settings:
                    same_settings += 1      # те же настройки, другой uuid/пароль
                    continue
                seen_settings.add(sk)
            unique.append(c)

        print(f"[i] После удаления дубликатов: {len(unique)} "
              f"(из них одинаковых настроек с другим uuid убрано: {same_settings})")

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
            stage(f"TCP: проверяю {len(xray_cands)}...")
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

        # ---------- 3.1 реальная проверка (быстрый шлюз — её первый шаг) ----------
        stage(f"Реальная проверка: {len(candidates)} "
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

        # ---------- 4. лучшие по баллу: без дублей, «из РФ» + повторная проверка ----------
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
        print(f"[i] Убрал дубли и «фермы» подсетей: {before - len(working)} (осталось {len(working)})")

        working = cap_hy2(working)

        stage("Отбор лучших (из РФ + повторный прогон одновременно)...")
        best = await select_best(session, working)
        best = best[:TARGET_COUNT]
        print(f"[i] Беру лучших: {len(best)}")

        if not best:
            print("[x] После отбора рабочих не осталось.")
            if _fail:
                print("\n[i] Причины отказов:")
                for reason, n in _fail.most_common():
                    print(f"    {n:>5}  {reason}")
            return

        # ---------- 5. страна/город по реальному выходному IP + каскады ----------
        stage("Определяю страны, города и каскады...")
        geo_sem = asyncio.Semaphore(GEO_CITY_CONCURRENCY)

        async def geo_one(config):
            code = _trace_loc.get(config)             # страна — Cloudflare trace (из проверки)
            exit_ip = _exit_ip.get(config)
            async with geo_sem:
                if code:
                    city = await city_lookup(session, exit_ip, code)
                    return code, make_geo_name(code, city)
                if exit_ip:                           # trace не ответил — консенсус сервисов
                    return await geo_lookup(session, exit_ip)
            return None, None

        async def entry_stage():
            entry_ip = {}
            hosts = {get_host_port(c)[0] for c, _ in best if get_host_port(c)}
            await asyncio.gather(*(resolve_ip(h) for h in hosts))
            for c, _ in best:
                hp = get_host_port(c)
                if hp and _dns_cache.get(hp[0]):
                    entry_ip[c] = _dns_cache[hp[0]]
            geo = await entry_geo_batch(session, entry_ip.values()) if entry_ip else {}
            return entry_ip, geo

        geos, (entry_ip, entry_geo) = await asyncio.gather(
            asyncio.gather(*(geo_one(c) for c, _ in best)),
            entry_stage(),
        )

        items = []  # (country_name, latency, renamed_line)
        cascades = 0
        gemini_n = 0
        for (config, latency), (code, name) in zip(best, geos):
            final_name = name or "🌐 Неизвестно"

            # каскад: страна ВХОДА (сервер из конфига) ≠ страна выхода; вход не за CDN
            ip = entry_ip.get(config)
            eg = entry_geo.get(ip) if ip else None
            if code and eg and ip != _exit_ip.get(config) and eg[0] != code.upper() \
                    and not any(w in eg[1] for w in CDN_WORDS):
                final_name = f"{get_country_flag(eg[0])} -> {final_name}"  # {флаг входа} -> {флаг выхода} ...
                cascades += 1

            if winter:
                final_name += f" {winter_tag(latency)}"
            if LTE_TAG_ENABLED and is_lte(config):
                final_name += f" {LTE_TAG}"             # тип интернета
            if GEMINI_CHECK and _gemini.get(config):
                final_name += f" {GEMINI_TAG}"          # Gemini — самым последним
                gemini_n += 1

            country_key = get_country_name(code) if code else "я_Неизвестно"  # неизвестные — в конец
            items.append((country_key, latency, rename_config(config, final_name)))

        print(f"[i] Каскадов: {cascades}, Gemini {GEMINI_TAG}: {gemini_n}")

        # группируем по стране, внутри страны — по баллу
        items.sort(key=lambda x: (x[0], x[1]))
        renamed = [line for _, _, line in items]

    # ---------- 6. сохраняем ----------
    header = winter_header(pinned) if winter else pinned
    final_list = header + renamed

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(final_list) + "\n", encoding="utf-8")

    print()
    print(f"[✓] Готово за {elapsed()}: {len(final_list)} (закр. {len(pinned)} + {len(renamed)})")
    print(f"[✓] Файл: {OUTPUT_FILE}")

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

    write_step_summary([
        "### PizdukVPN ЧС ❄️",
        f"- Время: **{elapsed()}**",
        f"- В подписке: **{len(renamed)}** (закреплённых {len(pinned)})",
        f"- Каскадов: {cascades}, Gemini {GEMINI_TAG}: {gemini_n}",
    ] + [f"- {n} × {reason}" for reason, n in _fail.most_common(5)])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Остановлено.")
