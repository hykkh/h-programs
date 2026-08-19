# -*- coding: utf-8 -*-
"""카탈로그가 실제와 맞는지 스스로 확인한다.

왜 만드는가 — 형님이 카탈로그를 직접 열어볼 수 없다(암호화돼 있고, 그냥
grep 하면 잠금화면 평문만 보인다). 그래서 "최신화했습니다" 라는 **말만
믿어야 하는 상태**였다. 실제로 오늘 열어보니 HTrain 이 v2.4.3 에 멈춰
있었고, 크기 표기도 어긋나 있었다 (형님 2026-08-20 "니 말만 믿는데").

무엇을 보는가
  1) 카탈로그가 가리키는 내려받기 주소가 살아 있는가 (HTTP 200)
  2) 적어둔 파일 크기가 실제와 맞는가
  3) 프로그램마다 적어둔 판 번호가 그 프로그램의 실제 판과 같은가

실행: python check_sync.py --pw 0219
      python check_sync.py --pw 0219 --quiet      # 문제 있을 때만 말한다
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRAMS = os.path.dirname(HERE)          # C:\H-Programs
REPO = 'hykkh/h-programs'
TAG = 'v0.4.9'

# 카탈로그에 적힌 이름 → 그 프로그램의 판 번호가 어디 적혀 있는가.
# (파일, 정규식) — 첫 번째 그룹이 판 번호다.
# 링크가 한 겹 더 암호화된 카드(data-enc)는 주소로 짝지을 수 없다. 카드에
# 적힌 이름으로 맞춘다 — HTrain 의 'PC에 설치' 가 그렇다. 그냥 두면 26MB 를
# 22MB 로 적어놔도 아무도 모른다 (2026-08-20 실제로 못 잡았다).
SIZE_BY_LABEL = [
    ('PC에 설치', 'v0.4.9', 'HTrain_Personal_Setup.exe'),
]

VERSION_OF = {
    'H-Train': (os.path.join(PROGRAMS, 'HTrain', 'htrain2', 'version.py'),
                r"VERSION\s*=\s*'([0-9.]+)'"),
    'News Alert': (os.path.join(PROGRAMS, 'news-alert', 'package.json'),
                   r'"version"\s*:\s*"([0-9.]+)"'),
    '부동산 레이더': (os.path.join(PROGRAMS, 'realty-radar', 'package.json'),
                r'"version"\s*:\s*"([0-9.]+)"'),
}


def plain(pw):
    """카탈로그를 복호화해 평문 HTML 로. catalog_edit 를 그대로 쓴다."""
    r = subprocess.run([sys.executable, os.path.join(HERE, 'catalog_edit.py'),
                        'decrypt', '--pw', pw],
                       capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit(f'카탈로그를 열지 못했습니다: {(r.stderr or "")[:120]}')
    return r.stdout


_CACHE = {}


def release_assets(tag=TAG):
    """그 태그에 실제로 올라가 있는 파일들. 프로그램마다 태그가 다르다 —
    사진편집기는 photo-editor-v1.5.6, 카메라는 camera-app-v1.7.0 식이다.
    한 태그로만 보면 멀쩡한 링크를 죽었다고 한다 (2026-08-20 첫 실행에서
    이 검사기가 스스로 오답을 냈다)."""
    if tag in _CACHE:
        return _CACHE[tag]
    r = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO,
                        '--json', 'assets'],
                       capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        _CACHE[tag] = None
        return None
    _CACHE[tag] = {a['name']: a['size'] for a in json.loads(r.stdout)['assets']}
    return _CACHE[tag]


def tag_of(url):
    m = re.search(r'/releases/download/([^/]+)/', url)
    return m.group(1) if m else TAG


def reachable(url):
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except Exception as e:
        return getattr(e, 'code', 0) or 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pw', required=True)
    ap.add_argument('--quiet', action='store_true',
                    help='문제가 있을 때만 말한다')
    a = ap.parse_args()

    html = plain(a.pw)
    bad, checked = [], 0

    # ── 1) 링크가 살아 있는가 ────────────────────────────────
    for url in sorted(set(re.findall(
            r'https://github\.com/[^"\']+/releases/download/[^"\']+', html))):
        checked += 1
        code = reachable(url)
        name = url.rsplit('/', 1)[-1]
        if code != 200:
            bad.append(f'내려받기 링크가 죽었습니다 (HTTP {code}) — {name}')
            continue
        got = release_assets(tag_of(url))
        if got is not None and name not in got:
            bad.append(f'릴리스에 없는 파일을 가리킵니다 — {tag_of(url)}/{name}')

    # ── 2) 적어둔 크기가 맞는가 ──────────────────────────────
    # "Android 8+ · 2.0MB" 처럼 카드 안에 적힌 크기를 그 카드의 파일과 맞춘다.
    for m in re.finditer(r'href="([^"]+/releases/download/[^"]+)"(.{0,400}?)</a>',
                         html, re.S):
        url, tail = m.group(1), m.group(2)
        name = url.rsplit('/', 1)[-1]
        got = release_assets(tag_of(url)) or {}
        size = got.get(name)
        if not size:
            continue
        got = re.search(r'([0-9]+(?:\.[0-9])?)\s*MB', tail)
        if not got:
            continue
        checked += 1
        said, real = float(got.group(1)), size / 1048576
        # 소수 한 자리로 적으니 반올림 오차는 0.05 를 넘지 않는다. 0.2 를
        # 넘으면 사람이 보기에 다른 파일이다. 0.5 로 뒀더니 2.0MB 를
        # 1.7MB 로 적어놔도 못 잡았다 (2026-08-20 스스로 시험).
        if abs(said - real) > 0.2:
            bad.append(f'크기가 다릅니다 — {name}: 적힌 값 {said}MB, 실제 {real:.1f}MB')

    # ── 2-2) 주소가 가려진 카드는 이름으로 짝지어 크기를 본다 ──
    for label, tag, asset in SIZE_BY_LABEL:
        got = release_assets(tag) or {}
        size = got.get(asset)
        where = html.find(label)
        if not size or where < 0:
            continue
        near = re.search(r'([0-9]+(?:\.[0-9])?)\s*MB', html[where:where + 300])   # 크기는 이름 뒤에 온다
        if not near:
            continue
        checked += 1
        said, real = float(near.group(1)), size / 1048576
        if abs(said - real) > 0.2:
            bad.append(f'크기가 다릅니다 — {asset}: 적힌 값 {said}MB, 실제 {real:.1f}MB')

    # ── 3) 판 번호가 실제와 같은가 ───────────────────────────
    for label, (path, pat) in VERSION_OF.items():
        if not os.path.isfile(path):
            continue
        m = re.search(pat, io.open(path, encoding='utf-8').read())
        if not m:
            continue
        real = m.group(1)
        # 카탈로그에서 그 프로그램 이름 뒤에 가장 먼저 나오는 vX.Y.Z
        where = html.find(label)
        if where < 0:
            bad.append(f'카탈로그에 {label} 항목이 없습니다')
            continue
        said = re.search(r'v([0-9]+\.[0-9]+\.[0-9]+)', html[where:where + 400])
        checked += 1
        if not said:
            bad.append(f'{label}: 카탈로그에 판 번호가 없습니다 (실제 {real})')
        elif said.group(1) != real:
            bad.append(f'{label}: 카탈로그 v{said.group(1)} · 실제 v{real}')

    if bad:
        print(f'■ 카탈로그가 실제와 다릅니다 — {len(bad)}건')
        for b in bad:
            print(f'  · {b}')
        return 1
    if not a.quiet:
        print(f'■ 카탈로그가 실제와 같습니다 ({checked}가지 대조)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
