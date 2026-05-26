#!/usr/bin/env python3
"""
이메일 발송만 단독으로 테스트하는 스크립트.

이 스크립트가 성공해야 메인 워크플로우의 메일 발송도 성공합니다.
GitHub Actions의 workflow_dispatch에서 'test_email_only=true' 로 실행하면
PubMed 검색 없이 이것만 돌릴 수 있습니다.

실행:
  GMAIL_USER=...  GMAIL_APP_PASSWORD=...  EMAIL_TO=...  python scripts/test_email.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# src 모듈 import 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.emailer import EmailSender


def main() -> int:
    user = os.environ.get("GMAIL_USER", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    to = os.environ.get("EMAIL_TO", user)  # 기본값: 자기 자신
    # 기본적으로 실제 메일은 안 보냄. 디버깅 시 TEST_SEND_EMAIL=true 로만 발송.
    do_send = os.environ.get("TEST_SEND_EMAIL", "false").strip().lower() in ("true", "1", "yes")

    print("=" * 60)
    print("이메일 인증 테스트" + ("  (+ 실제 발송)" if do_send else "  (연결/인증만)"))
    print("=" * 60)
    print(f"GMAIL_USER         : {'설정됨' if user else '❌ 비어있음'}")
    print(f"GMAIL_APP_PASSWORD : {'설정됨 (len=' + str(len(password.strip())) + ')' if password else '❌ 비어있음'}")
    print(f"EMAIL_TO           : {to}")
    print(f"TEST_SEND_EMAIL    : {do_send}")
    print()

    if not user or not password:
        print("❌ 환경변수가 설정되지 않았습니다. GitHub Secret 등록 후 재실행하세요.")
        return 1

    try:
        sender = EmailSender(user=user, password=password)
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    # 1단계: 연결 + 인증만 테스트 (매 실행마다)
    print("\n--- 1단계: SMTP 연결/인증 테스트 ---")
    if not sender.test_connection():
        print("\n❌ 연결/인증 단계에서 실패. 위의 진단 메시지를 확인하세요.")
        return 1

    # 2단계: 실제 테스트 메일 발송 (TEST_SEND_EMAIL=true 일 때만)
    if not do_send:
        print("\n--- 2단계: 건너뜀 (TEST_SEND_EMAIL != true) ---")
        print("✅ 인증 OK. 실제 메일은 발송하지 않음.")
        print("   디버깅 목적으로 발송 테스트가 필요하면 workflow_dispatch에서")
        print("   test_email_only=true 로 실행하세요.")
        return 0

    print("\n--- 2단계: 테스트 메일 발송 ---")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = f"""<!DOCTYPE html><html><body style="font-family: sans-serif;">
    <h2>✅ Daily Research Articles — 이메일 테스트 성공</h2>
    <p>이 메일이 보인다면, GitHub Actions에서 Gmail SMTP 발송이 정상 동작합니다.</p>
    <ul>
      <li>발송 시각: {timestamp}</li>
      <li>발송자: {user}</li>
      <li>수신자: {to}</li>
    </ul>
    <p style="color: #666; font-size: 12px;">
      이 메일을 받으셨다면, 메인 워크플로우(run_daily.py)도 정상 동작할 것입니다.
    </p>
    </body></html>"""

    ok = sender.send(
        to=to,
        subject=f"[TEST] Daily Research Articles 발송 테스트 ({timestamp})",
        html_body=html,
        text_body=f"이메일 테스트 성공. {timestamp}",
    )

    if ok:
        print("\n✅ 테스트 메일 발송 성공. 받은편지함(또는 스팸함)을 확인하세요.")
        return 0
    else:
        print("\n❌ 발송 실패. 위 로그를 확인하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
