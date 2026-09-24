"""
Quick email test script — run this directly to diagnose Gmail SMTP issues.
Usage: python test_email.py <recipient@email.com>
"""
import smtplib, sys, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MAIL_USERNAME = (os.environ.get('MAIL_USERNAME') or '').strip()
MAIL_PASSWORD = (os.environ.get('MAIL_PASSWORD') or '').replace(' ', '')

print(f"MAIL_USERNAME : {MAIL_USERNAME or '(not set)'}")
print(f"MAIL_PASSWORD : {'*' * len(MAIL_PASSWORD) if MAIL_PASSWORD else '(not set)'} ({len(MAIL_PASSWORD)} chars)")

if not MAIL_USERNAME or not MAIL_PASSWORD:
    print("\n❌ MAIL_USERNAME or MAIL_PASSWORD is missing in .env")
    sys.exit(1)

to_email = sys.argv[1] if len(sys.argv) > 1 else MAIL_USERNAME
print(f"Sending test email to: {to_email}\n")

# Build email
msg = MIMEMultipart('alternative')
msg['Subject'] = '[PEC Lost & Found] Email Test'
msg['From']    = f'PEC Lost & Found <{MAIL_USERNAME}>'
msg['To']      = to_email
msg.attach(MIMEText('<p>This is a <strong>test email</strong> from PEC Lost &amp; Found.</p>', 'html'))

# ── Try port 587 + STARTTLS ────────────────────────────────────────────────────
print("Trying smtp.gmail.com:587 (STARTTLS)...")
try:
    with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
        smtp.sendmail(MAIL_USERNAME, to_email, msg.as_string())
    print(f"✅ Success! Email sent to {to_email}")
    sys.exit(0)
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ AUTH FAILED on 587: {e}")
    print("\n  ➜ Fix: Generate a new Gmail App Password:")
    print("     1. Go to https://myaccount.google.com/security")
    print("     2. Enable 2-Step Verification if not done")
    print("     3. Search 'App passwords' → create one for 'Mail'")
    print("     4. Paste the 16-char password into .env as MAIL_PASSWORD (no spaces needed)")
except smtplib.SMTPException as e:
    print(f"❌ SMTP error on 587: {e}")
except Exception as e:
    print(f"❌ Connection error on 587: {e}")

# ── Fallback: try port 465 + SSL ───────────────────────────────────────────────
print("\nTrying smtp.gmail.com:465 (SSL)...")
try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as smtp:
        smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
        smtp.sendmail(MAIL_USERNAME, to_email, msg.as_string())
    print(f"✅ Success via SSL! Email sent to {to_email}")
    print("\n  ➜ Update app.py send_email() to use SSL port 465 instead of STARTTLS 587.")
    sys.exit(0)
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ AUTH FAILED on 465: {e}")
except Exception as e:
    print(f"❌ Connection error on 465: {e}")

print("\n─────────────────────────────────────────────────────")
print("Both ports failed. Most likely cause: invalid App Password.")
print("Steps to fix:")
print("  1. Log in to https://myaccount.google.com with peclostandfound@gmail.com")
print("  2. Security → 2-Step Verification → must be ON")
print("  3. Search for 'App passwords' in the search bar")
print("  4. Create a new App Password (select app: Mail, device: Other)")
print("  5. Copy the 16 chars and paste into .env:")
print("     MAIL_PASSWORD=abcdabcdabcdabcd")
