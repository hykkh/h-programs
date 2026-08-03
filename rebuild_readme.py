# -*- coding: utf-8 -*-
"""카탈로그 README 를 index.html 에서 다시 만든다.

원래 README 는 한글이 깨져 있었다. UTF-8 로 쓴 것을 cp949 로 읽어 굳은
것인데, 그 과정에서 매핑 없는 바이트가 '?' 로 치환돼 되돌릴 수 없다
(예: '매장' → '留ㅼ옣' 은 '׺장' 까지만 복구된다).

반쯤 복구한 문서는 깨진 문서보다 나쁘다 — 읽는 사람이 어디가 틀렸는지
알 수 없기 때문이다. 그래서 멀쩡한 index.html 을 원본 삼아 다시 만든다.
설명 문구를 지어내지 않고 그대로 옮긴다.

실행: python rebuild_catalog_readme.py [--write]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'C:\H-Programs\h-programs-catalog'
NL = '\n'


def strip_tags(t):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', t or '')).strip()


def cards(html):
    out = []
    for m in re.finditer(r'<a ([^>]*)class="card[^"]*"([^>]*)>(.*?)</a>', html, re.S):
        attrs, body = m.group(1) + m.group(2), m.group(3)
        href = re.search(r'href="([^"]*)"', attrs)
        h2 = re.search(r'<h2>(.*?)</h2>', body, re.S)
        p = re.search(r'<p>(.*?)</p>', body, re.S)
        ver = re.search(r'<span class="version">(.*?)</span>', body, re.S)
        tags = [strip_tags(t) for t in
                re.findall(r'<span class="tag[^"]*">(.*?)</span>', body, re.S)]
        title = strip_tags(h2.group(1) if h2 else '')
        title = title.replace('NEW', '').strip()
        out.append({
            'title': title,
            'tags': [t for t in tags if t],
            'desc': strip_tags(p.group(1) if p else ''),
            'meta': strip_tags(ver.group(1) if ver else ''),
            'href': (href.group(1) if href else '').strip(),
        })
    return out


def build(items):
    lines = [
        '# H-Programs',
        '',
        'hykkh(@hykkh) 개인 프로그램 다운로드 카탈로그.',
        '',
        '> 모든 앱은 **개인용**입니다. 직접 연락이 닿는 분에 한해 사용 권장.',
        '',
        '카탈로그 웹페이지: <https://hyt.kr/hp>',
        '',
        '---',
        '',
    ]
    for it in items:
        lines.append(f'## {it["title"]}')
        lines.append('')
        if it['desc']:
            lines.append(f'> {it["desc"]}')
            lines.append('')
        bits = []
        if it['tags']:
            bits.append(' · '.join(it['tags']))
        if it['meta']:
            bits.append(it['meta'])
        if bits:
            lines.append('**' + ' / '.join(bits) + '**')
            lines.append('')
        href = it['href']
        if href.startswith('http'):
            lines.append(f'[내려받기]({href})')
        elif href and href not in ('#',):
            lines.append(f'[자세히](./{href.lstrip("./")})')
        else:
            lines.append('_다운로드 링크는 카탈로그 페이지에서 (비공개 배포)_')
        lines.append('')
        lines.append('---')
        lines.append('')
    lines.append('<sub>이 문서는 docs/index.html 에서 생성됩니다. '
                 '내용을 고칠 때는 index.html 을 고치세요.</sub>')
    lines.append('')
    return NL.join(lines)


def main(write=False):
    html = io.open(os.path.join(ROOT, 'docs', 'index.html'), encoding='utf-8').read()
    items = cards(html)
    print(f'카드 {len(items)} 개를 읽었습니다')
    for it in items:
        print(f'  · {it["title"]}')
    text = build(items)

    broken = sum(1 for c in text if c == '\ufffd' or c == '?')
    print(f'\n생성된 문서 {len(text)} 자 · 물음표/치환문자 {broken} 개')

    path = os.path.join(ROOT, 'README.md')
    if write:
        old = io.open(path, encoding='utf-8', errors='replace').read()
        io.open(path + '.broken-backup', 'w', encoding='utf-8').write(old)
        io.open(path, 'w', encoding='utf-8').write(text)
        print(f'\n새로 썼습니다. 깨진 원본은 README.md.broken-backup')
    else:
        print('\n───── 미리보기 (앞 40줄) ─────')
        print(NL.join(text.split(NL)[:40]))
        print('\n(--write 를 붙이면 적용합니다)')
    return 0


if __name__ == '__main__':
    sys.exit(main('--write' in sys.argv))
