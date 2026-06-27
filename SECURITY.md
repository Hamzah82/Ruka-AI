# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | ✅ |

## Reporting a Vulnerability

If you discover a security vulnerability, please open an issue with the "security" label.

## Setup Credentials

### 1. OpenRouter API Key

Copy `.env.example` to `.env` and fill in your own API key:

```bash
cp .env.example .env
```

Then edit `.env` with your OpenRouter API key.

### 2. Email (msmtp)

Email config is NOT included in this repo. You need to create it manually:

1. Copy the example file from root:

```bash
cp msmtprc.example SKILL/config/email/msmtprc
```

2. Edit `SKILL/config/email/msmtprc` with your Gmail credentials:

```
account default
host smtp.gmail.com
port 587
tls on
tls_starttls on
auth on
user your_email@gmail.com
password your_app_password_here
from your_email@gmail.com
logfile ~/.msmtp.log
```

3. For Gmail, you MUST use an **App Password** (not your regular password).
   Go to Google Account → Security → 2-Step Verification → App Passwords.

4. Set proper permissions:

```bash
chmod 600 SKILL/config/email/msmtprc
```

### 3. Users / Collaborators

Copy `users.json.example` to `users.json` and fill in your collaborators.

**NEVER commit real credentials to the repository.**
