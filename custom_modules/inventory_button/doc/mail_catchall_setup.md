# Mail Catchall Domain Configuration Guide

This guide explains what the mail catchall domain is, why it's important, and how to configure it properly.

## What is the Mail Catchall Domain?

The mail catchall domain is a system parameter in Odoo that specifies which domain should be used for:

- Generating reply-to addresses for outgoing emails
- Routing incoming emails to the right records
- Handling email bounces

## Why Is It Important?

Without a properly configured mail catchall domain:

1. Replies to your emails won't be automatically associated with the right records
2. The email tracking system won't work correctly
3. You won't know if emails failed to deliver (bounces)

## Automatic Configuration

The "Setup Catchall Domain" button will:

1. Set `mail.catchall.domain` to your Odoo instance's domain
2. Create default values for `mail.catchall.alias` and `mail.bounce.alias`
3. Configure mail aliases for your product records

## Manual Configuration

To manually configure these parameters:

1. Go to Settings > Technical > Parameters > System Parameters
2. Set the following parameters:
   - `mail.catchall.domain`: Your domain name (e.g., `example.com`)
   - `mail.catchall.alias`: Usually set to `catchall`
   - `mail.bounce.alias`: Usually set to `bounce`

## Email Routing Configuration

For complete email functionality, you also need to configure your email server to route messages:

1. Set up email forwarding for `catchall@yourdomain.com` to your Odoo instance
2. Ensure `bounce@yourdomain.com` is forwarded to Odoo
3. Set up email handling for `api_product@yourdomain.com` and `api_product-*@yourdomain.com`

## Testing Your Configuration

After configuring the catchall domain:

1. Send a test email using the "Send Test Email" button
2. Reply to that email from your external email client
3. Check if the reply appears in the product record's message thread

## Common Issues

- **Incorrect Domain Format**: Make sure your domain doesn't include http:// or https:// prefixes
- **Missing MX Records**: Your domain needs proper MX records to receive emails
- **Firewall Blocking**: Ensure your firewall allows incoming email connections
- **Alias Conflicts**: Check for duplicate aliases in your mail server configuration

For more information, refer to the [official Odoo documentation on email routing](https://www.odoo.com/documentation/16.0/applications/productivity/mail_gateway.html).
