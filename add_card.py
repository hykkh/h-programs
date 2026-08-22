# -*- coding: utf-8 -*-
"""
hyt.kr/hp 카탈로그(잠금 안쪽)에 카드 하나를 추가하는 도구.

카드 HTML 은 URL 또는 로컬 파일에서 읽는다. 카탈로그 그리드의 마지막 카드 뒤에
삽입하고, 재암호화한 뒤 index.html 을 갱신한다. 그 다음 git add/commit/push
는 사용자가 직접 한다(변경 사항을 검토할 여지를 남기려고 자동화 X).

사용법:
  python add_card.py --url  https://tesla.hyt.kr/o/.../hesla-card.txt --pw 0219
  python add_card.py --file some-card.html                           --pw 0219

의존: pip install cryptography requests
"""
import argparse
import os
import re
import sys

from catalog_edit import INDEX, decrypt, encrypt, _read_enc


# 마지막 공개 카드로 삼을 앵커. 그 카드 </a> 다음 개행에 새 카드를 삽입한다.
# camera-app 카드가 지금 마지막이라 앵커로 사용. 나중에 새 카드가 이보다 뒤에
# 붙으면 여기 문자열만 갱신하면 된다.
_LAST_CARD_ANCHOR = 'camera-app-v1.7.0/_v1.7.0.apk" class="card">'


def _fetch_card(url: str, file: str) -> str:
    if url:
        import requests
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        r.encoding = "utf-8"
        return r.text
    if file:
        with open(file, encoding="utf-8") as f:
            return f.read()
    sys.exit("!! --url 또는 --file 중 하나 필요")


def _find_insert_point(plaintext: str) -> int:
    """마지막 공개 카드 블록의 </a> 다음 위치를 돌려준다."""
    anchor_at = plaintext.find(_LAST_CARD_ANCHOR)
    if anchor_at < 0:
        sys.exit(
            "!! 앵커('%s') 를 카탈로그에서 못 찾음. "
            "add_card.py 의 _LAST_CARD_ANCHOR 를 최신 카드로 갱신하세요." % _LAST_CARD_ANCHOR
        )
    # 앵커 뒤로 이어지는 카드 블록의 첫 </a> 를 찾는다.
    close_at = plaintext.find("</a>", anchor_at)
    if close_at < 0:
        sys.exit("!! 앵커 뒤에 </a> 없음 — HTML 구조 이상.")
    return close_at + len("</a>")


def main():
    ap = argparse.ArgumentParser(description="hyt.kr/hp 카탈로그에 카드 하나 추가.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="카드 HTML 을 받을 URL")
    src.add_argument("--file", help="카드 HTML 파일 경로")
    ap.add_argument("--pw", default=os.environ.get("HP_CATALOG_PW"))
    ap.add_argument("--dry-run", action="store_true", help="index.html 안 바꾸고 삽입 결과만 보기")
    a = ap.parse_args()
    if not a.pw:
        sys.exit("!! 비밀번호 필요: --pw <pw> 또는 환경변수 HP_CATALOG_PW")

    card_html = _fetch_card(a.url, a.file).strip()
    if not card_html:
        sys.exit("!! 카드 HTML 이 비어있음")

    content = decrypt(a.pw)
    at = _find_insert_point(content)
    new_content = content[:at] + "\n\n" + card_html + "\n" + content[at:]

    if a.dry_run:
        sys.stdout.reconfigure(encoding="utf-8")
        print("[DRY-RUN] 삽입 위치: %d, 삽입 길이: %d" % (at, len(card_html)))
        print("--- 삽입 전후 200자 ---")
        show_from = max(0, at - 100)
        show_to = min(len(new_content), at + len(card_html) + 100)
        print(new_content[show_from:show_to])
        return

    new_enc = encrypt(a.pw, new_content)
    html, _ = _read_enc()
    html2 = re.sub(r'const ENC = "[^"]+"', 'const ENC = "' + new_enc + '"', html, count=1)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(html2)

    # 자체검증: 재복호화해서 카드가 실제로 들어갔는지
    verify = decrypt(a.pw)
    if card_html not in verify:
        sys.exit("!! 재암호화 검증 실패 — index.html 을 git 으로 되돌리세요")
    print("[OK] 카드 삽입 + 재암호화 + 자체검증 통과.")
    print("     이제: git add docs/index.html && git commit -m '카드 추가' && git push")


if __name__ == "__main__":
    main()
