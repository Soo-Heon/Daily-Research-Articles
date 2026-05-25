"""
Gmail SMTP 발송 모듈 — 디버깅 친화적으로 설계.

이전 시도에서 가장 자주 실패하는 지점들을 전부 방어:
1) App Password에 공백이 들어간 채로 저장된 경우 → 자동 제거
2) 비밀번호로 일반 Google 계정 비번을 쓴 경우 → 인증 오류 시 명확한 안내
3) try/except로 예외가 삼켜져서 워크플로우가 성공으로 끝나는 경우 → 반드시 False 반환
4) STARTTLS 협상 실패 → 기본을 SSL(465)로 사용
5) 무엇이 실패했는지 모르는 경우 → set_debuglevel(1)로 SMTP 전 송수신 로그 출력
"""
from __future__ import annotations

import smtplib
import socket
import ssl
import sys
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import Iterable


class EmailSender:
    def __init__(
        self,
        user: str,
        password: str,
        host: str = "smtp.gmail.com",
        port: int = 465,
        use_ssl: bool = True,
        timeout: int = 30,
        debug: bool = True,
    ):
        # ----- 입력값 검증 (실패 빨리, 명확히) -----
        if not user or not user.strip():
            raise ValueError(
                "GMAIL_USER 가 비어 있습니다. GitHub Secret에 등록하세요."
            )
        if not password or not password.strip():
            raise ValueError(
                "GMAIL_APP_PASSWORD 가 비어 있습니다. GitHub Secret에 등록하세요."
            )

        # ----- 공백/줄바꿈/하이픈 제거 (가장 흔한 실패 원인) -----
        self.user = user.strip()

        # Google이 App Password를 보여줄 때 "abcd efgh ijkl mnop" 처럼
        # 공백을 넣어서 보여줍니다. 실제 사용 시에는 공백 없이 16자 연속.
        # 또한 줄바꿈/탭/하이픈도 혹시 모르니 모두 제거.
        cleaned = password.strip()
        for ch in (" ", "\t", "\r", "\n", "-"):
            cleaned = cleaned.replace(ch, "")
        self.password = cleaned

        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.debug = debug

        # ----- 자기진단 출력 (비밀번호는 마스킹) -----
        print(
            f"[Email] user={self._mask(self.user)} "
            f"password_len={len(self.password)} (App Password는 보통 16자) "
            f"host={self.host}:{self.port} ssl={self.use_ssl}"
        )
        if len(self.password) != 16:
            print(
                f"[Email] ⚠️ App Password 길이가 16자가 아닙니다 ({len(self.password)}자). "
                f"Gmail App Password가 맞는지 확인하세요."
            )

    # -------------------------------------------------------------- #
    # 공개 API
    # -------------------------------------------------------------- #
    def test_connection(self) -> bool:
        """SMTP 연결 + 인증만 테스트. 메일은 보내지 않음."""
        print(f"\n[Email Test] {self.host}:{self.port} 연결 시도...")
        try:
            with self._open_smtp() as server:
                print("[Email Test] 인증 시도...")
                server.login(self.user, self.password)
                print("[Email Test] ✅ 인증 성공")
                return True
        except Exception as e:
            self._print_error(e, where="test_connection")
            return False

    def send(
        self,
        to: str | Iterable[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        """메일 발송. 성공/실패를 명확히 반환."""
        recipients = [to] if isinstance(to, str) else list(to)
        recipients = [r.strip() for r in recipients if r and r.strip()]
        if not recipients:
            print("[Email Send] ❌ 수신자가 비어 있습니다.")
            return False

        print(f"\n[Email Send] To: {recipients}")
        print(f"[Email Send] Subject: {subject}")
        print(f"[Email Send] HTML 본문 길이: {len(html_body)} chars")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.user
        msg["To"] = ", ".join(recipients)
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="github-actions.local")

        # plain text fallback (스팸 필터 통과율 향상)
        if text_body is None:
            text_body = "이 메일은 HTML 본문이 포함되어 있습니다. HTML 지원 메일 클라이언트에서 확인하세요."
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with self._open_smtp() as server:
                print("[Email Send] 인증 시도...")
                server.login(self.user, self.password)
                print("[Email Send] 인증 성공. 발송 시작...")
                refused = server.sendmail(self.user, recipients, msg.as_string())
                if refused:
                    print(f"[Email Send] ⚠️ 일부 수신자 거부됨: {refused}")
                    return False
                print(f"[Email Send] ✅ 발송 완료: {recipients}")
                return True
        except Exception as e:
            self._print_error(e, where="send")
            return False

    # -------------------------------------------------------------- #
    # 내부 도구
    # -------------------------------------------------------------- #
    def _open_smtp(self):
        """SSL 또는 STARTTLS SMTP 클라이언트 생성."""
        if self.use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(
                self.host, self.port, context=context, timeout=self.timeout
            )
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()

        if self.debug:
            # SMTP 전체 송수신 내용을 stderr로 출력 (GitHub Actions 로그에서 확인 가능)
            server.set_debuglevel(1)
        return server

    @staticmethod
    def _mask(s: str) -> str:
        if not s or "@" not in s:
            return "***"
        local, _, domain = s.partition("@")
        if len(local) <= 2:
            return f"**@{domain}"
        return f"{local[0]}***{local[-1]}@{domain}"

    @staticmethod
    def _print_error(e: BaseException, where: str) -> None:
        """예외 타입별로 사람이 읽을 수 있는 진단 메시지 출력."""
        print(f"\n[Email {where}] ❌ {type(e).__name__}: {e}", file=sys.stderr)

        if isinstance(e, smtplib.SMTPAuthenticationError):
            code, resp = e.smtp_code, e.smtp_error
            print(f"  SMTP 응답: {code} {resp!r}", file=sys.stderr)
            print(
                "  → 원인 후보:\n"
                "    1) Gmail 일반 비밀번호를 사용 (App Password가 아님)\n"
                "    2) 2단계 인증이 비활성화\n"
                "    3) App Password를 잘못 복사 (공백/누락 등)\n"
                "    4) GMAIL_USER 와 App Password 발급 계정이 다름\n"
                "  해결:\n"
                "    - https://myaccount.google.com/security 에서 2단계 인증 ON\n"
                "    - https://myaccount.google.com/apppasswords 에서 App Password 발급\n"
                "    - 16자(공백 제거) 그대로 GitHub Secret(GMAIL_APP_PASSWORD)에 저장",
                file=sys.stderr,
            )
        elif isinstance(e, smtplib.SMTPRecipientsRefused):
            print(f"  거부된 수신자: {e.recipients}", file=sys.stderr)
        elif isinstance(e, smtplib.SMTPServerDisconnected):
            print("  → 서버가 연결을 끊었습니다. 포트/방화벽 확인.", file=sys.stderr)
        elif isinstance(e, (socket.timeout, TimeoutError)):
            print("  → 연결 타임아웃. GitHub Actions 러너 네트워크 문제 가능성.", file=sys.stderr)
        elif isinstance(e, ssl.SSLError):
            print("  → SSL 오류. use_ssl=False, port=587(STARTTLS)로 시도해 보세요.", file=sys.stderr)

        traceback.print_exc()
