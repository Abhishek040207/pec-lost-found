/**
 * PEC Lost & Found — Gmail Relay (Google Apps Script)
 * =====================================================
 * DEPLOY INSTRUCTIONS (do this once):
 *   1. Open https://script.google.com and create a new project.
 *   2. Paste this entire file into the editor (replace any existing code).
 *   3. Set YOUR_SECRET below to any strong random string (e.g. "pec2024secretXYZ").
 *      Copy this same string — you will paste it into Render as MAIL_RELAY_SECRET.
 *   4. Click Deploy > New deployment > Type: Web app
 *      - Execute as: Me  (your peclostandfound@gmail.com account)
 *      - Who has access: Anyone
 *   5. Click Deploy > Copy the Web app URL  (ends in /exec)
 *      Paste this URL into Render as MAIL_RELAY_URL.
 *   6. Done. The relay is live.
 *
 * On every new code change you must click Deploy > Manage deployments >
 * select the deployment > click the pencil (Edit) > "New version" > Deploy.
 */

// CHANGE THIS — must match MAIL_RELAY_SECRET on Render
var SECRET = 'REPLACE_WITH_YOUR_SECRET';

function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);

    // 1. Verify shared secret
    if (payload.secret !== SECRET) {
      return jsonResp({ ok: false, error: 'invalid secret' });
    }

    var to      = payload.to      || '';
    var subject = payload.subject || '(no subject)';
    var html    = payload.html    || '';
    var text    = payload.text    || '';
    var name    = payload.name    || 'PEC Lost & Found';
    var replyTo = payload.replyTo || '';

    if (!to) {
      return jsonResp({ ok: false, error: 'missing "to" field' });
    }

    // 2. Build and send the email via Gmail
    var opts = {
      htmlBody:  html,
      name:      name,
      noReply:   false,   // keep reply-to working so students can reply
      // Headers that reduce spam scoring:
      // List-Unsubscribe signals this is a transactional/notification email
      headers: {
        'List-Unsubscribe': '<mailto:peclostandfound@gmail.com?subject=unsubscribe>',
        'X-Mailer': 'PEC Lost & Found Notification System',
        'Precedence': 'bulk'
      }
    };
    if (replyTo) opts.replyTo = replyTo;
    if (text)    opts.body    = text;

    // cc/bcc intentionally omitted — keep recipient list minimal
    GmailApp.sendEmail(to, subject, text || 'Please view this email in an HTML-capable client.', opts);
    return jsonResp({ ok: true });

  } catch (err) {
    return jsonResp({ ok: false, error: String(err) });
  }
}

function jsonResp(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
