# =============================================================================
# Module: newsagent.notify
# Responsibilities: Email delivery of a Report (currently disabled by configuration).
# Dependencies: jinja2, config
# Dependents: pipeline, cli
# ADRs: ADR-0013
# Traceability: docs/decisions/README.md
# =============================================================================
"""Email delivery of a Report (stdlib smtplib; appearance in ui/email/)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate
from pathlib import Path
from typing import Any

import jinja2

from .config import Config


def _recipients(config: Config) -> list[str]:
    to = config.get("email.to") or []
    if isinstance(to, str):
        to = [to]
    return [str(address).strip() for address in to if str(address).strip()]


def _counts(report: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for section in report.get("sections") or []:
        counts[str(section.get("key"))] = len(section.get("items") or [])
    return counts


def build_email(config: Config, report: dict[str, Any], markdown_text: str = "") -> EmailMessage:
    """Render a Report into an EmailMessage (HTML + plain fallback).

    Preconditions:
        Report dict follows the report.py contract; email.to is configured.
    Postconditions:
        EmailMessage with subject/from/to and both text and html parts.
    Prohibitions:
        Do not send the message from this function.
    Raises:
        jinja2.TemplateNotFound when the template is missing.
    """
    template_dir = config.root / "ui" / "email"
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)), autoescape=True
    )
    html = environment.get_template("report.html").render(
        report=report,
        leads=report.get("leads") or [],
        sections=report.get("sections") or [],
        windows=report.get("windows") or {},
    )

    counts = _counts(report)
    subject = (
        f"{config.get('email.subject_prefix', 'AI 新闻日报')} · {report.get('date', '')}"
        f"（科技 {counts.get('tech', 0)} / 财务 {counts.get('finance', 0)} / 政策 {counts.get('policy', 0)}）"
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((
        str(config.get("email.from_name", "AI News Agent")),
        str(config.get("email.smtp_user") or ""),
    ))
    message["To"] = ", ".join(_recipients(config))
    message["Date"] = formatdate(localtime=True)
    plain = markdown_text or f"AI 新闻日报 {report.get('date', '')}"
    message.set_content(plain)
    message.add_alternative(html, subtype="html")
    return message


def send_report_email(config: Config, report: dict[str, Any], markdown_text: str = "") -> tuple[bool, str]:
    """Send a Report by SMTP using configured credentials.

    Preconditions:
        email.enabled is true; SMTP_PASSWORD and smtp_user are configured; recipients exist.
    Postconditions:
        (True, detail) on send; (False, reason) when skipped or failed.
    Prohibitions:
        Never block the pipeline: callers must treat failures as non-fatal.
    Raises:
        smtplib exceptions are caught and returned as failure details.
    """
    if not bool(config.get("email.enabled", True)):
        return False, "email disabled"
    recipients = _recipients(config)
    if not recipients:
        return False, "email.to 未配置"
    password = config.secret("SMTP_PASSWORD")
    if not password:
        return False, "SMTP_PASSWORD 未配置（Gmail 需要应用专用密码）"
    password = password.replace(" ", "").strip()  # Gmail 应用密码常带空格，登录时去掉
    user = str(config.get("email.smtp_user") or config.secret("SMTP_USER") or "")
    if not user:
        return False, "email.smtp_user 未配置"

    message = build_email(config, report, markdown_text)
    host = str(config.get("email.smtp_host", "smtp.gmail.com"))
    port = int(config.get("email.smtp_port", 465))
    timeout = 30
    try:
        if bool(config.get("email.use_ssl", True)):
            smtp = smtplib.SMTP_SSL(host, port, timeout=timeout)
        else:
            smtp = smtplib.SMTP(host, port, timeout=timeout)
            smtp.starttls()
        with smtp:
            smtp.login(user, password)
            smtp.send_message(message)
        return True, f"sent to {', '.join(recipients)}"
    except Exception as exc:  # noqa: BLE001 - email must never break the pipeline
        return False, f"send failed: {exc}"


def write_preview(config: Config, report: dict[str, Any], markdown_text: str = "") -> Path:
    """Render the email HTML to out/email-preview.html.

    Preconditions:
        report follows the report contract; template exists.
    Postconditions:
        Path of the written preview file.
    Prohibitions:
        Do not use as a substitute for a real delivery test.
    Raises:
        OSError when the output directory is not writable.
    """
    message = build_email(config, report, markdown_text)
    html_body = ""
    for part in message.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                html_body = payload.decode("utf-8", errors="replace")
            break
    preview_dir = config.out_dir
    preview_dir.mkdir(parents=True, exist_ok=True)
    path = preview_dir / "email-preview.html"
    path.write_text(html_body, encoding="utf-8")
    return path
