# -*- coding: utf-8 -*-
"""
hyt.kr/hp 카탈로그(docs/index.html) 암호화 콘텐츠 편집 도구.

index.html 은 [평문 잠금화면(🔒) + 전체 콘텐츠 AES-CBC 암호화] 구조다.
  const ENC = "base64( iv[16] + AES-CBC-ciphertext )"
  key = SHA-256(비밀번호),  padding = PKCS7,  브라우저 crypto.subtle 과 호환.

⚠️ index.html 을 그냥 grep/curl 하면 '잠금화면' 평문만 보여 콘텐츠가 구버전인 줄
   착각하기 쉽다. 실제 카드 내용은 ENC 안에 있으니 반드시 이 도구로 복호화해 확인할 것.

비밀번호는 코드에 넣지 않는다(repo 공개 안전). --pw 인자 또는 환경변수 HP_CATALOG_PW 로 전달.
평문을 디스크에 절대 안 남긴다(과거 .bak 유출 사고) — 전부 메모리에서 처리.

사용법:
  python catalog_edit.py decrypt --pw 0219              # 복호화된 HTML 을 stdout 으로
  python catalog_edit.py grep "부동산" --pw 0219        # 복호화 후 키워드 포함 줄만
  python catalog_edit.py replace "옛문구" "새문구" --pw 0219   # 치환→재암호화→index.html 갱신(+자체검증)

의존: pip install cryptography
"""
import sys
import os
import re
import hashlib
import base64
import argparse

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "index.html")


def _key(pw):
    return hashlib.sha256(pw.encode("utf-8")).digest()


def _read_enc():
    html = open(INDEX, encoding="utf-8").read()
    m = re.search(r'const ENC = "([^"]+)"', html)
    if not m:
        sys.exit("!! index.html 에서 const ENC 를 못 찾음 (암호화 구조 아님?)")
    return html, m.group(1)


def decrypt(pw):
    _, enc = _read_enc()
    comb = base64.b64decode(enc)
    d = Cipher(algorithms.AES(_key(pw)), modes.CBC(comb[:16])).decryptor()
    padded = d.update(comb[16:]) + d.finalize()
    u = padding.PKCS7(128).unpadder()
    try:
        return (u.update(padded) + u.finalize()).decode("utf-8")
    except Exception:
        sys.exit("!! 복호화 실패 — 비밀번호가 틀렸을 수 있음")


def encrypt(pw, plaintext):
    iv = os.urandom(16)
    pad = padding.PKCS7(128).padder()
    pd = pad.update(plaintext.encode("utf-8")) + pad.finalize()
    e = Cipher(algorithms.AES(_key(pw)), modes.CBC(iv)).encryptor()
    ct = e.update(pd) + e.finalize()
    return base64.b64encode(iv + ct).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["decrypt", "grep", "replace"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--pw", default=os.environ.get("HP_CATALOG_PW"))
    a = ap.parse_args()
    if not a.pw:
        sys.exit("!! 비밀번호 필요: --pw <pw> 또는 환경변수 HP_CATALOG_PW")

    content = decrypt(a.pw)

    if a.cmd == "decrypt":
        sys.stdout.reconfigure(encoding="utf-8")
        print(content)
    elif a.cmd == "grep":
        sys.stdout.reconfigure(encoding="utf-8")
        kw = a.args[0] if a.args else ""
        for ln in content.split("\n"):
            if kw in ln:
                print(ln.strip())
    elif a.cmd == "replace":
        if len(a.args) < 2:
            sys.exit('사용법: replace "옛문구" "새문구" --pw <pw>')
        old, new = a.args[0], a.args[1]
        if old not in content:
            sys.exit('!! 옛 문구를 평문에서 못 찾음 (먼저 grep 으로 정확한 문자열 확인)')
        content2 = content.replace(old, new)
        new_enc = encrypt(a.pw, content2)
        # 자체검증: 재암호화본을 다시 풀어 new 포함 확인
        html, _ = _read_enc()
        html2 = re.sub(r'const ENC = "[^"]+"', 'const ENC = "' + new_enc + '"', html, count=1)
        open(INDEX, "w", encoding="utf-8").write(html2)
        verify = decrypt(a.pw)
        if new not in verify:
            sys.exit("!! 재암호화 검증 실패 — index.html 을 git 으로 되돌리세요")
        print("[OK] 치환+재암호화 완료, 자체 복호화 검증 통과. git commit/push 하세요.")


if __name__ == "__main__":
    main()
