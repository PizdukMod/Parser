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

from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote


# ============================================================
# ИСТОЧНИКИ — НЕ МЕНЯТЬ
# ============================================================

SOURCES = [
    "https://freevpnhappcluchi.duckdns.org/sub/lzjrpfi55soz18q9",
    "https://raw.githubusercontent.com/flaafix/AetrisVPN-black-list/refs/heads/main/configs.txt",
    "https://raw.githubusercontent.com/Buffetbarko/Universal-Proxy-Config-Parser-/main/blacklist_vpn.txt",
    "https://mifa.world/star",
    "https://pozor.bond/sub/utcwry9vug6k",
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
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@qq.utiltools.site:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=qq.utiltools.site&fp=qq&security=reality&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&sid=#%F0%9F%95%B8%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B7%F0%9F%87%BA%20%28telegram-only%29%F0%9F%8E%83",
    "vless://4054fdc2-ee80-4419-8a8e-d937df4719e2@78.159.250.214:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=qq.utiltools.site&fp=firefox&security=reality&pbk=drY21DHNOr6ezJLA2B10mzTExeJ9-gVBfTBNLwVBtWI&sid=00000000#%F0%9F%91%89%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20%F0%9F%87%B7%F0%9F%87%BA%20%D1%8D%D1%82%D0%BE%202%20%28telegram-only%29",
    "vless://ff0b6ba8-bed0-4c4d-bbc9-23af47582615@wstg.datasynctrue.online:443/?type=ws&encryption=none&flow=&host=wstg.datasynctrue.online&path=%2Fapi%2Fconnect&security=tls&sni=wstg.datasynctrue.online&fp=chrome#%F0%9F%87%B7%F0%9F%87%BA%20%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%20LTE%F0%9F%93%B6%20Wi-Fi",
    "vless://ff0b6ba8-bed0-4c4d-bbc9-23af47582615@91.210.169.181:443/?type=ws&encryption=none&flow=&host=wstg.datasynctrue.online&path=%2Fapi%2Fconnect&security=tls&sni=wstg.datasynctrue.online&fp=firefox#%F0%9F%87%B7%F0%9F%87%BA%20%D0%A2%D0%B5%D0%BB%D0%B5%D0%B3%D1%80%D0%B0%D0%BC%202%20LTE%F0%9F%93%B6%20Wi-Fi",
    "vless://3bb97d46-789b-4229-88f6-9beb222a4137@yoy-api.bachidze.com:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=yoy-api.bachidze.com&fp=firefox&security=reality&pbk=ZJlfiMh4ebjrTl2_kwAk_zXMAaCiwNS7yMd5XzlUgmI&sid=#%F0%9F%87%B7%F0%9F%87%BA%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F%20YT%E2%9C%85",
    "ss://YWVzLTI1Ni1nY206TlRpSEJnNjRmc1k4dThEYkdydHlwRDlnUEdTTDM4NnA@185.22.155.121:18443#🇷🇺 Россия ss",
    "vless://5c2b47d0-38c0-4b01-b8ff-ab1c145292f0@188.130.209.222:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=thumbs.mycdn-io.ru&fp=firefox&security=reality&pbk=6vubZmkLVtaiFF8JyGFy7XSy2pc7ywN4P625QLKw8wc&sid=11979c0c9b2da371#%F0%9F%87%B7%F0%9F%87%BA%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F%20%F0%9F%8E%BA",
    "vless://1fe01c8a-ab37-4e95-bbfc-95d4a608931e@95.56.251.12:47443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=kz1.waspnest.space&fp=firefox&security=reality&pbk=z1GSwCEACvO9RLcMVpcURiT8er4oeIdeSJhraw_0cGU&sid=ae97223a8f799877#%F0%9F%87%B0%F0%9F%87%BF%20%D0%9A%D0%B0%D0%B7%D0%B0%D1%85%D1%81%D1%82%D0%B0%D0%BD%20%F0%9F%8C%A0",
    "vmess://eyJhZGQiOiJjZi4wc20uY29tIiwiYWlkIjoiMCIsImFscG4iOiIiLCJmcCI6IiIsImhvc3QiOiJ2bWVzcy5sYnc2NjYuZHBkbnMub3JnIiwiaWQiOiIwY2Y2ZDk3MC0zZjFkLTRhYWUtYTk4OS05MmE4Zjc2YWUzZGIiLCJuZXQiOiJ3cyIsInBhdGgiOiIvd3M/ZWRcdTAwM2QyMDQ4IiwicG9ydCI6IjgwIiwicHMiOiLwn4e68J+HuCDinKYg0KHQqNCQIOKcpiDwn4yAIiwic2N5IjoiYXV0byIsInNuaSI6IiIsInRscyI6IiIsInR5cGUiOiIiLCJ2IjoiMiJ9",
    "vmess://eyJhZGQiOiIxNzIuNjcuMTg3LjE0NSIsImFpZCI6IjAiLCJhbHBuIjoiIiwiZnAiOiIiLCJob3N0Ijoidm1lc3MubGJ3NjY2LmRwZG5zLm9yZyIsImlkIjoiMGNmNmQ5NzAtM2YxZC00YWFlLWE5ODktOTJhOGY3NmFlM2RiIiwibmV0Ijoid3MiLCJwYXRoIjoiL3dzP2VkXHUwMDNkMjA0OCIsInBvcnQiOiI4MCIsInBzIjoi8J+HuvCfh7gg0KHQqNCQIiwic2N5IjoiYXV0byIsInNuaSI6IiIsInRscyI6IiIsInR5cGUiOiIiLCJ2IjoiMiJ9",
    "trojan://0ab6c98dae3b48e8b9c4a776b6c9c19a@216.152.156.81:443/?type=tcp&security=tls&sni=www.healthcarejobshubenhancemedicalprofessionalskillstoday.com&fp=chrome#%F0%9F%87%BA%F0%9F%87%B8%20%D0%A1%D0%A8%D0%90%20Trojan",
    "trojan://0ab6c98dae3b48e8b9c4a776b6c9c19a@208.69.78.19:443/?type=tcp&security=tls&sni=www.yourultimateprofessionalcareerhub.com&allowInsecure=1#%F0%9F%87%BA%F0%9F%87%B8%20%D0%A1%D0%A8%D0%90",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTprMWRCT21PQjRvcWk3VW1wMzdhMWJR@82.38.31.212:8080#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20YT%E2%9C%85",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTprMWRCT21PQjRvcWk3VW1wMzdhMWJR@82.38.31.178:8080#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpvWklvQTY5UTh5aGNRVjhrYTNQYTNB@82.38.31.54:8080#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20ss",
    "vless://6da2c981-8c77-4340-bda3-93399b7aea26@lectures.blog-forme.ru:443/?type=xhttp&encryption=none&flow=&path=%2Fv2%2Fsync%2Faf2c0c&mode=auto&extra=%7B%0A%20%20%22xmux%22%3A%20%7B%0A%20%20%20%20%22maxConcurrency%22%3A%20%2216-32%22%2C%0A%20%20%20%20%22cMaxReuseTimes%22%3A%20%220%22%2C%0A%20%20%20%20%22hMaxRequestTimes%22%3A%20%221800-3000%22%2C%0A%20%20%20%20%22hMaxReusableSecs%22%3A%20%2210800-14400%22%2C%0A%20%20%20%20%22hKeepAlivePeriod%22%3A%200%0A%20%20%7D%0A%7D&sni=lectures.blog-forme.ru&fp=edge&security=reality&pbk=nalACuCZjV1sZx7QOH6yAIDio8mFI0FgVKYQvQHBKS4&sid=fb3a5f2d4ca346ed#%F0%9F%87%B3%F0%9F%87%B1%20%E2%9D%96%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%F0%9F%93%9A%20%E2%9D%96",
    "vless://6da2c981-8c77-4340-bda3-93399b7aea26@shorts.blog-forme.ru:443/?type=xhttp&encryption=none&flow=&path=%2Fv2%2Fsync%2Faf2c0c&mode=auto&extra=%7B%0A%20%20%22xmux%22%3A%20%7B%0A%20%20%20%20%22maxConcurrency%22%3A%20%2216-32%22%2C%0A%20%20%20%20%22cMaxReuseTimes%22%3A%200%2C%0A%20%20%20%20%22hMaxRequestTimes%22%3A%20%221800-3000%22%2C%0A%20%20%20%20%22hMaxReusableSecs%22%3A%20%2210800-14400%22%2C%0A%20%20%20%20%22hKeepAlivePeriod%22%3A%200%0A%20%20%7D%0A%7D&sni=shorts.blog-forme.ru&fp=edge&security=reality&pbk=nalACuCZjV1sZx7QOH6yAIDio8mFI0FgVKYQvQHBKS4&sid=fb3a5f2d4ca346ed#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%F0%9F%90%8C",
    "hy2://6da2c981-8c77-4340-bda3-93399b7aea26@video.blog-forme.ru:443/?hop_interval=10&sni=video.blog-forme.ru#🇳🇱 Нидерланды 🎬",
    "vless://3bb97d46-789b-4229-88f6-9beb222a4137@direct-nl.bachidze.com:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=direct-nl.bachidze.com&fp=firefox&security=reality&pbk=E12wXXagR8xuql7KlWCLTgMaXj74JcU__lg66yz6iTw&sid=#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B",
    "vless://7d43670b-6b08-45b9-8a24-8f3971abc132@netherlands.biznes.lol:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=netherlands.biznes.lol&fp=firefox&security=reality&pbk=p2QUi5Oyqwc3unA19NqgnF4h3I_SjLOkn0cUkzWCOE0&sid=#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B",
    "vless://6da2c981-8c77-4340-bda3-93399b7aea26@178.17.52.236:2083/?type=xhttp&encryption=none&flow=&path=%2Fv2%2Fsync%2F6e9367&mode=auto&sni=maps.blog-forme.ru&fp=edge&security=reality&pbk=mbi4BZAuiq_L6pfhG2xxWmtosq0Z1Pzf18fvNSWKMxY&sid=3258252d44113e23#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%F0%9F%97%BA",
    "vless://727a9178-d7f0-4142-8205-b0d19959ded0@de-2.ffpn.pro:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=de-2.ffpn.pro&fp=firefox&security=reality&pbk=DCpi9-1rSXxBnEIAQ9U3mTqHivk7vHJRV_T2pWw5vCc&sid=681fc2dd643bc2f3#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F",
    "vless://6da2c981-8c77-4340-bda3-93399b7aea26@213.165.54.59:8443/?type=xhttp&encryption=none&flow=&path=%2Fentry-xh&mode=auto&sni=www.kinopoisk.ru&fp=edge&security=reality&pbk=CI4hMTvVsem9mloOgRCW9A6WC-srPPwu3jlylwOnd3A&sid=2e6d668958829998#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%F0%9F%8E%AC",
    "trojan://0ab6c98dae3b48e8b9c4a776b6c9c19a@193.108.119.78:443/?type=tcp&security=tls&sni=www.iloverussia2026.com&fp=chrome#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F%20%E2%9D%A4%EF%B8%8F%F0%9F%87%B7%F0%9F%87%BA",
    "vless://558b26f6-061b-4079-9b84-ca13b3e90ae3@191.44.108.6:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=c9.qwyak.ru&fp=firefox&security=reality&pbk=A0QL_j-ReX7AotEj1w8qX9rHRgN2WycTZ43gUvuvZ00&sid=3cf8d11aa0415d29#%F0%9F%87%A9%F0%9F%87%AA%20%D0%93%D0%B5%D1%80%D0%BC%D0%B0%D0%BD%D0%B8%D1%8F",
    "ss://YWVzLTI1Ni1nY206WlJwZ2FCZUd4dEVOSVhndmhwa1pCS3o5R25XUlMyZFljeDlPK2EyaXdOND0@202.50.253.72:19999#%F0%9F%87%AE%F0%9F%87%B9%20%D0%98%D1%82%D0%B0%D0%BB%D0%B8%D1%8F",
    "ss://YWVzLTI1Ni1nY206WlJwZ2FCZUd4dEVOSVhndmhwa1pCS3o5R25XUlMyZFljeDlPK2EyaXdOND0@202.50.253.99:19999#🇮🇹 ⟡ Италия 🍕 ⟡",
    "vless://3de59cd0-f92c-40bf-829c-db7bf6043d1d@bg.reus.lol:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=bg.reus.lol&fp=safari&security=reality&pbk=OWnQ9xwvYFlNw_Fnmf4ceZMtb0SVLuVUoq2WP5P8lkw&sid=5f2d02dc7ec1e539#%F0%9F%87%A7%F0%9F%87%AC%20%D0%91%D0%BE%D0%BB%D0%B3%D0%B0%D1%80%D0%B8%D1%8F%20%F0%9F%A4%A3",
    "vless://3de59cd0-f92c-40bf-829c-db7bf6043d1d@45.137.201.74:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=bg.reus.lol&fp=firefox&security=reality&pbk=OWnQ9xwvYFlNw_Fnmf4ceZMtb0SVLuVUoq2WP5P8lkw&sid=5f2d02dc7ec1e539#%F0%9F%87%A7%F0%9F%87%AC%20%D0%91%D0%BE%D0%BB%D0%B3%D0%B0%D1%80%D0%B8%D1%8F%20%F0%9F%A4%A3%202",
    "vless://50a87e21-f0e2-4b53-a787-91adfe748f63@swedenafteraventura.space:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=swedenafteraventura.space&fp=chrome&security=reality&pbk=TyuIIquHoesD9YwMQJHda0YZ3Hy9Dh123dQ00iGK0QY&sid=#%F0%9F%87%B8%F0%9F%87%AA%20%D0%A8%D0%B2%D0%B5%D1%86%D0%B8%D1%8F%20%E2%9A%A1%EF%B8%8F",
    "vless://a0fa7e19-70ec-41e0-b0cc-bcc984d4201a@s12.bsh-net.ru:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=s12.bsh-net.ru&fp=firefox&security=reality&pbk=QvT-t_h_AF2EAT4Ggh_a6pcCK3StY8G9WCXn6-dJbxk&sid=51079f144d661484#%F0%9F%87%B8%F0%9F%87%AA%20%D0%A8%D0%B2%D0%B5%D1%86%D0%B8%D1%8F%20%F0%9F%8C%90",
    "vless://3bb97d46-789b-4229-88f6-9beb222a4137@smart.bachidze.com:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=smart.bachidze.com&fp=firefox&security=reality&pbk=vzRgIP8Mvd9V6krwKxw5EwwzvC4uiaW3wo0Y2ri2_Wc&sid=#%F0%9F%87%B8%F0%9F%87%AA%20%D0%A8%D0%B2%D0%B5%D1%86%D0%B8%D1%8F",
    "vless://c29fa587-b10d-445d-b7e3-eaa6d1bd1330@31.76.55.162:443/?type=xhttp&encryption=none&flow=&path=%2Ffwlink%2F&mode=stream-up&sni=est1.dnsfire.fun&fp=firefox&security=reality&pbk=nNoxOT_HzUZkKbHiK34iSfF89wlXAXBdlkquGVqGUDk&sid=f4e0550a#%F0%9F%87%AA%F0%9F%87%AA%20%D0%AD%D1%81%D1%82%D0%BE%D0%BD%D0%B8%D1%8F",
    "vless://c29fa587-b10d-445d-b7e3-eaa6d1bd1330@media.aava.lalibobi.online:443/?type=ws&encryption=none&flow=&host=media.aava.lalibobi.online&path=%2Flive%2Fshowroom&security=tls&sni=media.aava.lalibobi.online&alpn=http%2F1.1&fp=firefox#%F0%9F%87%AA%F0%9F%87%AA%D0%AD%D1%81%D1%82%D0%BE%D0%BD%D0%B8%D1%8F%20%F0%9F%8E%AC",
    "vless://f8d52ece-fad4-478d-875d-df6eed3befa7@pl-b1.golangwikito.cfd:61374/?type=xhttp&encryption=none&flow=&host=pl-b1.golangwikito.cfd&path=%2F&mode=packet-up&extra=%7B%0A%20%20%22xPaddingBytes%22%3A%20%22100-500%22%2C%0A%20%20%22xmux%22%3A%20%7B%0A%20%20%20%20%22maxConnections%22%3A%20%223%22%0A%20%20%7D%0A%7D&sni=pl-b1.golangwikito.cfd&fp=chrome&security=reality&pbk=QrNs0ew7snHqLfpVXS9RAhlRzgAzzGZK9fXmDcx9xHI&sid=&packetEncoding=xudp#%F0%9F%87%B5%F0%9F%87%B1%20%D0%9F%D0%BE%D0%BB%D1%8C%D1%88%D0%B0",
    "vless://8263aa5b-601d-4e05-b61d-a70e15d97869@45.198.0.88:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=pl1.edge.rbullet.net&fp=firefox&security=reality&pbk=GG5vpbtQpYpZkAa3qQfLe3f9kzym3EU5t8_MYUkX_z0&sid=458374ae#%F0%9F%87%B5%F0%9F%87%B1%20%D0%9F%D0%BE%D0%BB%D1%8C%D1%88%D0%B0",
    "vless://1fe01c8a-ab37-4e95-bbfc-95d4a608931e@31.59.143.147:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=pl2.waspnest.space&fp=firefox&security=reality&pbk=Liu35gmIQJtbul5AeCrceJTjsmln4RaqxX6joKlaBjk&sid=ae97223a8f799889#%F0%9F%87%B5%F0%9F%87%B1%20%D0%9F%D0%BE%D0%BB%D1%8C%D1%88%D0%B0",
    "vless://a0fa7e19-70ec-41e0-b0cc-bcc984d4201a@67.159.52.51:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=snp.bsh-net.ru&fp=firefox&security=reality&pbk=iE4sTz-Q2Frkm7WM32P1wm4at49Wpaj5vo-2FsLcN1M&sid=8854f17e2a5af2d8#%F0%9F%87%B8%F0%9F%87%AC%20%D0%A1%D0%B8%D0%BD%D0%B3%D0%B0%D0%BF%D1%83%D1%80%2067",
    "vless://a0fa7e19-70ec-41e0-b0cc-bcc984d4201a@snp.bsh-net.ru:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=snp.bsh-net.ru&fp=firefox&security=reality&pbk=iE4sTz-Q2Frkm7WM32P1wm4at49Wpaj5vo-2FsLcN1M&sid=8854f17e2a5af2d8#%F0%9F%87%B8%F0%9F%87%AC%20%D0%A1%D0%B8%D0%BD%D0%B3%D0%B0%D0%BF%D1%83%D1%80%20%F0%9F%8C%90",
    "ss://YWVzLTI1Ni1nY206Z2oxK1hLdWxLVjBubXc2SVRoY2tPa2tKaDVEU003K0M@45.207.207.25:443#🇭🇰 Гонконг ss",
    "vless://7d1a74fd-8a38-4a29-863f-5da53a9e557e@api.ferrin.uk:443/?type=xhttp&encryption=none&flow=&path=%2Fes&mode=stream-one&security=tls&sni=7d1a74fd.ferrin.uk#%F0%9F%87%AA%F0%9F%87%B8%20%D0%98%D1%81%D0%BF%D0%B0%D0%BD%D0%B8%D1%8F",
    #пропуск (не удалять!) . - , получается хуйня такая
]


# ============================================================
# НАСТРОЙКИ
# ============================================================

TARGET_COUNT = 60          # сколько конфигов взять в итоге (не считая закреплённых)
EARLY_STOP_MULT = 3        # остановить проверку, когда найдено TARGET_COUNT * N рабочих
                           # (из них берутся лучшие по пингу). 0 = проверять все

MAX_PING_MS = 3000         # отсечка совсем медленных (итоговый балл: пинг + вклад скорости)
GOOD_PING_MS = 300         # «быстрый» сервер (🎃 в названии); ≤3× — 👻, дальше — 🦇

MAX_TCP_PING_MS = 1700     # TCP-пинг выше этого (или нет ответа) — в xray не идёт
TCP_CONCURRENCY = 200      # одновременных TCP-проверок

# --- Хеллоуин ---
# True — всегда, False — никогда, "auto" — только с 25 октября по 2 ноября
HALLOWEEN = "auto"

# --- Скачивание подписок ---
FETCH_TIMEOUT = 20.0
FETCH_RETRIES = 3          # сколько раз пробовать каждый источник
FETCH_HEADERS_LIST = [     # User-Agent меняется от попытки к попытке
    {"User-Agent": "v2rayN/6.42"},
    {"User-Agent": "Happ/7.0.0"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64;)"},
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
# Первый раунд — «холодный» (рукопожатие), остальные — «тёплые», по ним считается пинг.
CHECK_ROUNDS = 3

# --- Защита от «соединение закрыто» и тайм-аутов ---
IDLE_PAUSE = 2.0            # пауза перед повторным запросом по тому же соединению
BURST_PARALLEL = 8          # параллельных запросов на новых соединениях
BURST_MAX_FAILS = 0         # сколько из них можно провалить

# --- Скачивание ---
DOWNLOAD_URLS = [           # достаточно, чтобы прошёл ХОТЯ БЫ ОДИН
    "https://speed.cloudflare.com/__down?bytes=1000000",
    "https://proof.ovh.net/files/1Mb.dat",
]
DOWNLOAD_BYTES = 1_000_000
DOWNLOAD_TIMEOUT = 15.0
REQUIRE_DOWNLOAD = True     # False — если раннер не достаёт до DOWNLOAD_URLS
DOWNLOAD_MAX_MS = 7000      # 1 МБ дольше этого — слишком медленно
SPEED_WEIGHT = 0.1          # вклад времени загрузки/отдачи в итоговый балл (ниже = лучше)

# --- Отдача (upload): ловит «полусломанные» туннели, где вниз идёт, а вверх нет ---
UPLOAD_URL = "https://speed.cloudflare.com/__up"
UPLOAD_BYTES = 256 * 1024
UPLOAD_TIMEOUT = 15.0
UPLOAD_MAX_MS = 6000
REQUIRE_UPLOAD = True       # False — если раннер не достаёт до UPLOAD_URL

# --- Доступ к заблокированным сайтам (главное для ЧС-подписки) ---
BLOCKED_URLS = [
    "https://www.youtube.com/generate_204",
    "https://www.instagram.com/",
    "https://api.telegram.org/",
]
MIN_BLOCKED_OK = 2          # сколько из BLOCKED_URLS должны открыться (0 = не проверять)

# --- Стабильность ---
MAX_JITTER = 2.5            # макс/мин пинг в тёплых раундах (+100 мс запаса)
REQUIRE_STABLE_EXIT_IP = True   # выходной IP не должен «плавать» между запросами

# --- Cloudflare trace: выходной IP + страна ПРЯМО через прокси (без лимитов гео-сервисов) ---
USE_CF_TRACE = True
CF_TRACE_URL = "https://www.cloudflare.com/cdn-cgi/trace"

# Выходы в этих странах отбрасываются (для ЧС-подписки выход в РФ обычно бесполезен).
# Пример: {"RU", "BY"}. Пусто = не фильтровать. Закреплённых это не касается.
EXCLUDE_EXIT_COUNTRIES = set()

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
CONFIRM_CONCURRENCY = 5    # при повторной проверке меньше нагрузки = честнее скорость

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
_trace_loc = {}             # config -> страна выхода по Cloudflare trace
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

# Серверы за этими CDN не считаем каскадом (страна «входа» там ничего не значит)
CDN_WORDS = ("cloudflare", "fastly", "akamai", "cloudfront", "gcore", "bunny")


# ============================================================
# ХЕЛЛОУИН
# Имя конфига: «{флаг} Страна — Город {тег} [{флаг входа}Каскад]»
# Флаг остаётся первым (клиенты берут из него значок), тег скорости — в конце:
#   🎃 быстрый (≤ GOOD_PING_MS), 👻 нормальный (≤ 3×), 🦇 медленный.
# Каскад по-прежнему заканчивает название.
# ============================================================

HALLOWEEN_ANNOUNCE = "🎃 Телеграм канал: @PizMod 👻\n🦇Автообновление каждые 6 часов🕷"


def halloween_on():
    if HALLOWEEN is True:
        return True
    if HALLOWEEN is False:
        return False
    t = datetime.date.today()
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
            title = line.replace("🏴", "🎃")
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


# ============================================================
# РЕАЛЬНАЯ ПРОВЕРКА ЧЕРЕЗ ЯДРО (xray / sing-box) — возвращает балл (мс) или None
# Порядок: от дешёвых проверок к дорогим (быстрее отсев).
#   1) все тестовые URL во всех раундах, HTTPS-сертификаты проверяются;
#      ответ 204 должен быть пустым (иначе подмена);
#   2) пауза и повтор по тому же соединению (keep-alive);
#   3) выходной IP определён, не равен нашему; Cloudflare trace подтверждает
#      тот же IP (и даёт страну выхода) — «плавающий» выход отсеивается;
#   4) доступ к заблокированным сайтам (YouTube / Instagram / Telegram);
#   5) параллельный залп на новых соединениях;
#   6) скачивание ~1 МБ и отдача (upload) — обрывы и «полусломанные» туннели;
#   7) выходной IP не изменился к концу проверки; разброс пинга небольшой.
# Балл = медиана пинга в тёплых раундах + вклад времени загрузки и отдачи.
# Одинаково для vless / vmess / trojan / ss / hy2.
# ============================================================

async def _probe(line, port):
    connector = aiohttp_socks.ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
    timeout = aiohttp.ClientTimeout(total=XRAY_TEST_TIMEOUT)

    latencies = []
    exit_ip = None
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for rnd in range(CHECK_ROUNDS):
                for url in TEST_URLS:
                    ms = await _fetch_ok(session, url)   # ssl-проверка ВКЛЮЧЕНА
                    if rnd > 0:                          # первый раунд «холодный» — не считаем
                        latencies.append(ms)

            # пауза + повтор по тому же соединению (рвёт ли сервер keep-alive)
            await asyncio.sleep(IDLE_PAUSE)
            for url in TEST_URLS:
                await _fetch_ok(session, url)
    except Exception:
        return _reject("тестовые URL / keep-alive")

    # со второй сессии — всё остальное (первая закрыта, соединения свежие)
    connector_b = aiohttp_socks.ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
    async with aiohttp.ClientSession(connector=connector_b, timeout=timeout) as session:
        # реальная проверка выходного IP
        exit_ip = await fetch_ip(session, XRAY_TEST_TIMEOUT)
        if REQUIRE_EXIT_IP and (not exit_ip or (_my_ip and exit_ip == _my_ip)):
            return _reject("нет выходного IP / совпал с моим")

        # Cloudflare trace: подтверждение IP + страна выхода
        if USE_CF_TRACE:
            tr = await fetch_trace(session, XRAY_TEST_TIMEOUT)
            if tr:
                t_ip, t_loc = tr
                if REQUIRE_STABLE_EXIT_IP and exit_ip and _same_family_diff(exit_ip, t_ip):
                    return _reject("выходной IP «плавает»")
                exit_ip = exit_ip or t_ip
                if t_loc:
                    _trace_loc[line] = t_loc
                    if t_loc in EXCLUDE_EXIT_COUNTRIES:
                        return _reject("выход в исключённой стране")
        if exit_ip:
            _exit_ip[line] = exit_ip

        # доступ к заблокированным сайтам
        if BLOCKED_URLS and MIN_BLOCKED_OK:
            res_b = await asyncio.gather(
                *(_fetch_ok(session, u, timeout=10, ok_status=range(200, 400))
                  for u in BLOCKED_URLS),
                return_exceptions=True,
            )
            if sum(not isinstance(r, Exception) for r in res_b) < MIN_BLOCKED_OK:
                return _reject("заблокированные сайты недоступны")

    # параллельный залп на НОВЫХ соединениях + загрузка и отдача
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

        # выходной IP не должен измениться к концу проверки
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
# GEO: консенсус нескольких сервисов
# ip="" -> сначала узнаём выходной IP через прокси, затем страну по нему
# extra_code — страна по Cloudflare trace (даётся как самый приоритетный голос).
# Город берём по-русски: сервисы с lang=ru / name_ru, иначе словарь CITY_RU,
# иначе город не пишем.
# ============================================================

GEO_PROVIDERS = [
    ("ipinfo", "https://ipinfo.io/{ip}/json"),
    ("ipwho",  "https://ipwho.is/{ip}?lang=ru"),
    ("geojs",  "https://get.geojs.io/v1/ip/geo/{ip}.json"),
    ("dbip",   "https://api.db-ip.com/v2/free/{ip}"),
    ("ipapico","https://ipapi.co/{ip}/json/"),
    ("ipapi",  "http://ip-api.com/json/{ip}?fields=status,countryCode,city&lang=ru"),
    ("sypex",  "https://api.sypexgeo.net/json/{ip}"),
]

GEO_MIN_AGREE = 2              # минимум сервисов, согласных по стране
GEO_USE_SERVER_FALLBACK = False  # гео по IP сервера часто врёт — выключено

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


async def geo_lookup(session, ip="", extra_code=None):
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
    if extra_code:
        votes.setdefault(extra_code.upper(), []).append((-1, None))  # голос Cloudflare trace
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
                return await geo_lookup(s, extra_code=_trace_loc.get(line))
    except Exception:
        return None, None


# ============================================================
# КАСКАД: вход и выход в разных странах
# Страна выхода — по реальному выходному IP (она в названии конфига),
# страна входа — по IP сервера из конфига. Серверы за CDN пропускаем.
# ============================================================

async def detect_cascade(session, config, exit_ip, exit_code):
    """Флаг страны ВХОДА, если конфиг — каскад, иначе None."""
    hp = get_host_port(config)
    if not hp or not exit_code:
        return None
    ip = await resolve_ip(hp[0])
    if not ip or ip == exit_ip:
        return None
    try:
        async with session.get(f"https://ipinfo.io/{ip}/json",
                               timeout=aiohttp.ClientTimeout(total=8)) as r:
            org = str((await r.json(content_type=None)).get("org", "")).lower()
        if any(w in org for w in CDN_WORDS):
            return None
    except Exception:
        pass
    code, _ = await geo_lookup(session, ip)
    if code and code != exit_code.upper():
        return get_country_flag(code)
    return None


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
    """items: список (config, latency), уже отсортированный по баллу.
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
# Берём кандидатов по порядку балла и проверяем второй раз отдельным ядром.
# Остаются только те, кто прошёл оба раза. Идём, пока не наберём TARGET_COUNT.
# ============================================================

async def confirm_best(items):
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

    spooky = halloween_on()
    if spooky:
        print("[i] 🎃 Хеллоуин-режим: названия с тегами скорости")

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

        # ---------- 4. лучшие по баллу, без дублей, с повторной проверкой ----------
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
        print(f"[i] Беру лучших: {len(best)}")

        if not best:
            print("[x] После повторной проверки рабочих не осталось.")
            return

        # ---------- 5. страна/город по реальному выходному IP + каскады + переименование ----------
        print("\n[i] Определяю страны (по выходному IP)...")
        geo_sem = asyncio.Semaphore(CONCURRENCY)
        geo_done = 0

        async def geo_one(config):
            nonlocal geo_done
            async with geo_sem:
                code, name = None, None
                trace = _trace_loc.get(config)
                # 1) гео по уже известному выходному IP (без запуска ядра)
                exit_ip = _exit_ip.get(config)
                if exit_ip:
                    code, name = await geo_lookup(session, exit_ip, extra_code=trace)
                # 2) через ядро, если выходной IP неизвестен/не определился
                if not code:
                    code, name = await exit_geo(config)
                # 3) запасной путь: гео по IP сервера (по умолчанию выключен)
                if not code:
                    hp = get_host_port(config)
                    if hp:
                        ip = await resolve_ip(hp[0])
                        code, name = await get_server_geo(session, ip)
                # 4) если сервисы не договорились, но Cloudflare знает страну — берём её
                if not code and trace:
                    code, name = trace, make_geo_name(trace, None)
                # 5) каскад: страна входа отличается от страны выхода
                casc = None
                try:
                    casc = await detect_cascade(session, config, exit_ip, code)
                except Exception:
                    casc = None
                await asyncio.sleep(GEO_DELAY)
                geo_done += 1
                if geo_done % 10 == 0 or geo_done == len(best):
                    print(f"    гео {geo_done}/{len(best)}")
                return code, name, casc

        geos = await asyncio.gather(*(geo_one(c) for c, _ in best))

        items = []  # (country_name, latency, renamed_line)
        for (config, latency), (code, name, casc) in zip(best, geos):
            final_name = name or "🌐 Неизвестно"
            if spooky:
                final_name += f" {spooky_tag(latency)}"
            if casc:
                final_name += f" {casc}Каскад"
            country_key = get_country_name(code) if code else "я_Неизвестно"  # неизвестные — в конец
            items.append((country_key, latency, rename_config(config, final_name)))

        # группируем по стране, внутри страны — по баллу
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
