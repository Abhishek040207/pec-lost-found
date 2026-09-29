"""
Email delivery for PEC Lost & Found.

WHY THIS EXISTS
---------------
Render's free tier blocks ALL outbound SMTP traffic (ports 25, 465 and 587) at the
network firewall, so Gmail SMTP can never work there, no matter how correct the
credentials are. HTTPS (port 443) is never blocked, so on Render we send mail through
a tiny Google Apps Script "relay" that runs on the peclostandfound@gmail.com account
and sends the message from that address. See docs/mail_relay.gs for the script.

HOW IT PICKS A TRANSPORT
------------------------
1. MAIL_RELAY_URL (+ MAIL_RELAY_SECRET) set  -> HTTPS relay   (use this on Render)
2. else on Render                            -> clear error explaining what to configure
3. else MAIL_USERNAME + MAIL_PASSWORD set    -> Gmail SMTP     (fine for local development)

This module has no Flask or database dependency, so it can also be run standalone
(see test_email.py) to verify email delivery before deploying.
"""
import json
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

RELAY_TIMEOUT = 25   # seconds; Apps Script can take a few seconds to respond
SMTP_TIMEOUT = 12    # seconds; fail fast instead of hanging on a blocked port

SENDER_NAME = 'PEC Lost & Found'


def _plain_text(html_body):
    """Very small HTML -> text conversion for the plain-text alternative part."""
    text = re.sub(r'(?is)<(script|style).*?>.*?</\1>', '', html_body or '')
    text = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</h\d>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = (text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                .replace('&quot;', '"').replace('&#x27;', "'").replace('&nbsp;', ' '))
    return re.sub(r'\n\s*\n+', '\n\n', text).strip()


def _via_relay(url, secret, to_email, subject, html_body, reply_to):
    payload = {
        'secret': secret,
        'to': to_email,
        'subject': subject,
        'html': html_body,
        'text': _plain_text(html_body),
        'name': SENDER_NAME,
    }
    if reply_to:
        payload['replyTo'] = reply_to
    try:
        # Apps Script answers a POST with a 302 to a one-time result URL; requests follows it.
        resp = requests.post(
            url,
            data=json.dumps(payload),
            headers={'Content-Type': 'text/plain;charset=utf-8'},
            timeout=RELAY_TIMEOUT,
            allow_redirects=True,
        )
    except requests.exceptions.Timeout:
        return False, f'relay timed out after {RELAY_TIMEOUT}s'
    except requests.exceptions.RequestException as e:
        return False, f'could not reach relay: {e}'

    try:
        data = resp.json()
    except ValueError:
        return False, (
            f'relay returned a non-JSON response (HTTP {resp.status_code}). This usually means '
            'the Apps Script web app is not deployed with "Who has access: Anyone", or '
            'MAIL_RELAY_URL is not the /exec URL of the deployment.'
        )
    if data.get('ok'):
        return True, 'sent via HTTPS relay'
    return False, f'relay rejected the request: {data.get("error", "unknown error")}'


def _via_smtp(user, password, to_email, subject, html_body, reply_to):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'{SENDER_NAME} <{user}>'
    msg['To'] = to_email
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.attach(MIMEText(_plain_text(html_body), 'plain'))
    msg.attach(MIMEText(html_body, 'html'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=SMTP_TIMEOUT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(user, password)
            smtp.sendmail(user, to_email, msg.as_string())
        return True, 'sent via Gmail SMTP'
    except smtplib.SMTPAuthenticationError as e:
        return False, f'Gmail rejected the login (check the App Password): {e}'
    except (smtplib.SMTPException, OSError) as e:
        return False, f'SMTP connection failed ({e}). If this is running on Render, SMTP is blocked there.'


def deliver_email(to_email, subject, html_body, reply_to=None):
    """Send one email. Returns (ok: bool, detail: str). Never raises."""
    try:
        relay_url = os.environ.get('MAIL_RELAY_URL', '').strip()
        relay_secret = os.environ.get('MAIL_RELAY_SECRET', '').strip()
        if relay_url:
            if not relay_secret:
                return False, 'MAIL_RELAY_URL is set but MAIL_RELAY_SECRET is missing'
            return _via_relay(relay_url, relay_secret, to_email, subject, html_body, reply_to)

        if os.environ.get('RENDER'):
            return False, (
                'no email transport configured. Render blocks SMTP ports, so set MAIL_RELAY_URL and '
                'MAIL_RELAY_SECRET (see docs/mail_relay.gs).'
            )

        user = os.environ.get('MAIL_USERNAME', '').strip()
        password = os.environ.get('MAIL_PASSWORD', '').replace(' ', '')
        if user and password:
            return _via_smtp(user, password, to_email, subject, html_body, reply_to)
        return False, 'no email transport configured (set MAIL_RELAY_URL/MAIL_RELAY_SECRET, or MAIL_USERNAME/MAIL_PASSWORD for local dev)'
    except Exception as e:  # last-resort guard: email must never crash a request
        return False, f'unexpected error: {e}'
