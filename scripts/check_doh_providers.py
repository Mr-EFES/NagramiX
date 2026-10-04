#!/usr/bin/env python3
"""Проверить штатные DoH endpoint настоящими DNS-запросами из текущей сети.

Это диагностика доступности, а не проверка NSURLSession или работы iPhone.
Нестандартный DoH пользователя проверяется самим приложением при сохранении.
"""
import base64
import concurrent.futures
import ipaddress
from pathlib import Path
import re
import struct
import urllib.request


def query(hostname, qtype, identifier):
    labels = hostname.encode('ascii').split(b'.')
    return struct.pack('!6H', identifier, 0x100, 1, 0, 0, 0) + b''.join(bytes([len(x)]) + x for x in labels) + b'\0' + struct.pack('!2H', qtype, 1)


def skip_name(data, offset):
    for _ in range(128):
        length = data[offset]
        offset += 1
        if length == 0:
            return offset
        if length & 0xc0 == 0xc0:
            target = ((length & 0x3f) << 8) | data[offset]
            if not 12 <= target < len(data):
                raise ValueError('неверный указатель DNS')
            return offset + 1
        if length > 63 or offset + length > len(data):
            raise ValueError('повреждённое имя DNS')
        offset += length
    raise ValueError('слишком длинное имя DNS')


def addresses(data, identifier, qtype):
    rid, flags, questions, answers, _, _ = struct.unpack_from('!6H', data)
    if rid != identifier or not flags & 0x8000 or flags & 0x7a0f:
        raise ValueError('неуспешный или усечённый DNS-ответ')
    offset = 12
    for _ in range(questions):
        offset = skip_name(data, offset) + 4
    result = []
    for _ in range(answers):
        offset = skip_name(data, offset)
        rtype, cls, _, size = struct.unpack_from('!HHIH', data, offset)
        offset += 10
        value = data[offset:offset + size]
        if len(value) != size:
            raise ValueError('усечённые данные DNS')
        if cls == 1 and rtype == qtype and size == (4 if qtype == 1 else 16):
            result.append(str(ipaddress.ip_address(value)))
        offset += size
    if not result:
        raise ValueError('в ответе нет адресов')
    return result


def check(endpoint):
    results = []
    for qtype, label in [(1, 'A'), (28, 'AAAA')]:
        for method in ('GET', 'POST'):
            try:
                payload = query('example.com', qtype, 0)
                url = endpoint if method == 'POST' else endpoint + '?dns=' + base64.urlsafe_b64encode(payload).decode().rstrip('=')
                request = urllib.request.Request(url, data=payload if method == 'POST' else None, headers={'Content-Type': 'application/dns-message', 'Accept': 'application/dns-message'}, method=method)
                with urllib.request.urlopen(request, timeout=12) as response:
                    result = addresses(response.read(65536), 0, qtype)
                results.append(f'{label}/{method}: OK ({len(result)} адресов)')
            except Exception as error:
                results.append(f'{label}/{method}: ОШИБКА ({type(error).__name__}: {error})')
    return f'{endpoint}: ' + '; '.join(results)


def main():
    source = (Path(__file__).resolve().parents[1] / 'ios/Sources/MtProtoKit/NagramiXDNSResolver.m').read_text()
    endpoints = re.findall(r'return @"(https://[^"\n]+/dns-query)";', source)
    if len(endpoints) != 5:
        raise SystemExit('Ожидались пять штатных DoH endpoint; проверьте список провайдеров')
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for result in pool.map(check, endpoints):
            print(result)
    print('Системный DNS и сеть iPhone этим скриптом не проверяются.')


if __name__ == '__main__':
    main()
