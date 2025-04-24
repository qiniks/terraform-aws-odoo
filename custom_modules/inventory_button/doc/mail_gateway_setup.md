# Setting Up Mail Gateway for Customer Replies

This guide explains how to configure an incoming mail gateway in Odoo to receive customer replies.

## Prerequisites

1. A domain name that you control
2. Admin access to your Odoo instance
3. Access to your domain's DNS settings
4. A mail server that can forward emails to Odoo

## Step 1: Configure Odoo System Parameters

1. In Odoo, go to Settings > Technical > Parameters > System Parameters
2. Set the following parameters:
   - `mail.catchall.domain`: Your domain (e.g., `example.com`)
   - `mail.catchall.alias`: A catch-all alias (e.g., `catchall` or `support`)

## Step 2: Set Up Mail Aliases

1. Go to Settings > Technical > Email > Aliases
2. Create a new alias:
   - Name: `api_product` (or a preferred name)
   - Model: `api.product`
   - Record Thread: Yes
   - Default Values: Leave empty (these will be filled automatically)

## Step 3: Configure Your Mail Server

### Option A: Using a Hosted Email Service

1. Configure your email provider to forward emails sent to `api_product@yourdomain.com` to Odoo
2. This usually involves setting up mail forwarding rules in your email provider

### Option B: Direct Mail Server Configuration

1. Set up a mail server (like Postfix) to handle incoming emails
2. Configure it to pipe emails to Odoo's mail gateway script:

```bash
# Example configuration for Postfix
api_product@yourdomain.com    odoo@localhost
```

3. Create a procmail or similar rule to pipe emails to Odoo:

```
:0
* ^To:.*api_product@yourdomain.com
| /opt/odoo/odoo-bin --config=/etc/odoo.conf --load=web,mail --database=your_database_name -d your_database_name addons/mail/static/scripts/odoo-mailgate.py
```

## Step 4: DNS Configuration

1. Set up proper MX records for your domain pointing to your mail server
2. Ensure SPF records are correctly configured to avoid emails being marked as spam

## Step 5: Test the Configuration

1. Send an email to `api_product-ID@yourdomain.com` (where ID is the product record ID)
2. Check if the email appears in the corresponding product's message thread
3. If not, check Odoo server logs for possible errors

## Common Issues

- **Emails not being received**: Check your mail server logs and Odoo logs
- **Wrong record association**: Ensure emails have the correct reference in the subject line or are sent to the correct alias
- **Permissions issues**: Make sure the Odoo service has permissions to execute the mail gateway script

For more detailed instructions, refer to the [official Odoo documentation on mail gateways](https://www.odoo.com/documentation/16.0/applications/productivity/mail_gateway.html).
