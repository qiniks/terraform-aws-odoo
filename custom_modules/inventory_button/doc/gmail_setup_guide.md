# Gmail Setup Guide for Odoo

This guide explains how to configure Gmail as an outgoing mail server in Odoo.

## Prerequisites

1. A Gmail account (or Google Workspace account)
2. Admin access to your Odoo instance

## Step 1: Generate an App Password in Google

For security reasons, Google requires using App Passwords for less secure applications:

1. Go to your [Google Account](https://myaccount.google.com/)
2. Select "Security" on the left
3. Under "Signing in to Google," select "App passwords"
   - If you don't see this option, it might be because:
     - 2FA is not enabled on your account (you need to enable it)
     - 2FA is enabled, but you selected an option to trust your device
     - Your administrator has disabled this setting
4. At the bottom, select "Select app" and choose "Mail"
5. Select "Other" and type "Odoo Mail"
6. Click "Generate"
7. Copy the 16-character password that appears - this is your App Password

## Step 2: Configure Odoo Outgoing Mail Server

1. In Odoo, go to Settings > Technical > Email > Outgoing Mail Servers
2. Click "Create"
3. Fill in the following details:
   - **Description**: Gmail SMTP Server
   - **SMTP Server**: smtp.gmail.com
   - **SMTP Port**: 587
   - **Connection Security**: TLS (STARTTLS)
   - **Username**: your full Gmail address (e.g., yourname@gmail.com)
   - **Password**: the App Password you generated in Step 1
4. Click "Test Connection" to verify the setup
5. If the test succeeds, check "Is the Default SMTP Server"
6. Click "Save"

## Step 2.1: Configure Incoming Mail Server

1. In Odoo, navigate to Settings > Technical > Email > Incoming Mail Servers
2. Click "Create" to add a new server
3. Fill in the following details:
   - **Name**: Gmail IMAP Server
   - **Server Type**: IMAP Server
   - **Server**: imap.gmail.com
   - **Port**: 993
   - **Security**: SSL/TLS
   - **Username**: your full Gmail address (e.g., yourname@gmail.com)
   - **Password**: the App Password you generated in Step 1
4. Configure additional options:
   - Set "Actions to Perform on Incoming Mails" as needed
   - Configure "Folders to Monitor" (typically INBOX)
5. Click "Test & Confirm" to verify the connection
6. If successful, click "Save"

## Step 3: Test Your Configuration

1. Go to any product record
2. Navigate to the Messages tab
3. Click "Test Mail Configuration" button
4. If configured correctly, you should see a success message
5. Send a test email to verify the complete setup

## Troubleshooting

- If you receive authentication errors, double-check your App Password
- Ensure you're using port 587 with TLS (not SSL)
- If emails are not sending, check Odoo's email queue in Technical > Emails > Outgoing Emails
- Gmail has a sending limit of 500 emails per day for regular accounts
