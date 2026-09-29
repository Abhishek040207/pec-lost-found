"""
Email diagnostic script — run this directly to check email delivery is working
before (or after) deploying, without needing to click through the whole app.

Usage:  python test_email.py <recipient@email.com>

This tests whatever transport is actually configured in your environment
(via .env locally, or Render's Environment tab when run there):
  - MAIL_RELAY_URL + MAIL_RELAY_SECRET  -> HTTPS relay (what Render must use)
  - MAIL_USERNAME + MAIL_PASSWORD       -> Gmail SMTP (local development only;
                                            this WILL fail on Render, since Render
                                            blocks outbound SMTP ports entirely)
"""
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import mailer
import os

to_email = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('MAIL_USERNAME', '')
if not to_email:
    print("Usage: python test_email.py <recipient@email.com>")
    sys.exit(1)

relay_url = os.environ.get('MAIL_RELAY_URL', '').strip()
mail_user = os.environ.get('MAIL_USERNAME', '').strip()

if relay_url:
    print(f"Transport : HTTPS relay ({relay_url})")
elif mail_user:
    print(f"Transport : Gmail SMTP ({mail_user}) — local dev only, will NOT work on Render")
else:
    print("Transport : none configured! Set MAIL_RELAY_URL + MAIL_RELAY_SECRET")
    print("            (see docs/mail_relay.gs), or MAIL_USERNAME + MAIL_PASSWORD for local dev.")
    sys.exit(1)

print(f"Sending test email to: {to_email}\n")

ok, detail = mailer.deliver_email(
    to_email,
    '[PEC Lost & Found] Email Test',
    '<p>This is a <strong>test email</strong> from PEC Lost &amp; Found.</p>',
)

if ok:
    print(f"✅ Success — {detail}")
    sys.exit(0)
else:
    print(f"❌ Failed — {detail}")
    if not relay_url:
        print("\n  → If this is meant to run on Render: SMTP is blocked there no matter what.")
        print("    Set up docs/mail_relay.gs and add MAIL_RELAY_URL / MAIL_RELAY_SECRET instead.")
    sys.exit(1)
