# Email Troubleshooting Guide

This guide helps you troubleshoot common issues with sending emails to external recipients from Odoo.

## Common Issues

### 1. Outgoing Mail Server Not Configured

**Symptoms:**

- Error message "No outgoing mail servers are configured"
- Emails never leave the system

**Solution:**

1. Go to Settings > Technical > Email > Outgoing Mail Servers
2. Create a new mail server with your email provider's SMTP settings
3. Test the connection before saving

### 2. Authentication Failures

**Symptoms:**

- Error messages about authentication failures
- "Username and password not accepted"

**Solutions:**

- For Gmail: Use an App Password instead of your regular password
- Verify username is your complete email address (e.g., user@example.com)
- Check that 2FA isn't blocking the connection
- Ensure the mail server allows SMTP access

### 3. Connection Issues

**Symptoms:**

- "Connection refused" errors
- Timeout errors

**Solutions:**

- Verify the SMTP server address and port are correct
- Check if your network/firewall blocks outgoing SMTP traffic
- Try different connection security options (SSL/TLS/STARTTLS)
- Ensure the mail server isn't blocking connections due to rate limits

### 4. Emails Being Marked as Spam

**Symptoms:**

- Emails deliver but end up in recipient's spam folder
- No errors in Odoo but recipients say they never got the email

**Solutions:**

- Verify your domain has proper SPF/DKIM/DMARC records
- Use a consistent "From" address that matches your sending domain
- Avoid spam-like content and excessive links
- Start with low volume to build sending reputation

### 5. Mail Queue Problems

**Symptoms:**

- Emails stuck in "Outgoing" status
- Delayed delivery

**Solutions:**

- Check if the cron job for sending emails is running
- Verify the Odoo email worker hasn't crashed
- Look for Python errors in the Odoo logs
- Restart the Odoo service

## Testing Your Email Configuration

1. Use the "Check Mail Configuration" button to verify your setup
2. Send a test email to yourself using the "Send Test Email" button
3. Check both your inbox and spam folder for the test email
4. If the test fails, the error message should guide you to the specific issue

## Gmail-Specific Settings

If using Gmail as your outgoing mail server:

1. You must enable "Less secure app access" or use an App Password
2. Be aware of daily sending limits (500 emails for regular accounts)
3. Sending from an address that doesn't match your Gmail account may trigger security measures

## Common SMTP Settings

| Provider           | Server                          | Port | Security |
| ------------------ | ------------------------------- | ---- | -------- |
| Gmail              | smtp.gmail.com                  | 587  | STARTTLS |
| Outlook/Office 365 | smtp.office365.com              | 587  | STARTTLS |
| Yahoo              | smtp.mail.yahoo.com             | 587  | STARTTLS |
| Amazon SES         | email-smtp.region.amazonaws.com | 587  | STARTTLS |

## Advanced Troubleshooting

If basic troubleshooting doesn't solve the issue:

1. Check the Odoo server logs for detailed error messages
2. Use an SMTP testing tool to verify your mail server settings outside of Odoo
3. Temporarily try a different mail provider to isolate the issue
4. Consider using a dedicated transactional email service like SendGrid or Mailgun
