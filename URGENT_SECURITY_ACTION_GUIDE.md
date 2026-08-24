# 🚨 URGENT SECURITY ACTION REQUIRED — Ruka AI

**Date:** 2026-08-23  
**Priority:** CRITICAL ⚠️  
**Action Deadline:** Within 24 hours  

---

## 📋 WHAT HAPPENED

Your Ruka AI project has been audited for security vulnerabilities. We identified and fixed **CRITICAL credential exposure issues**, but you need to take immediate action.

---

## 🔴 WHY THIS MATTERS

### Credentials That Were Compromised:

1. **OpenRouter API Keys** (×3 keys)
   - Format: `sk-or-v1-[64-hex-chars]`
   - Risk: Unauthorized AI usage → billing abuse
   - Exposure location: Backed up securely, removed from source code

2. **Gmail App Password**
   - Account: `wokabi108@gmail.com`
   - Old password: `[GMAIL-APP-PASSWORD-REDACTED]` (COMPROMISED)
   - Risk: Email account takeover
   - Exposure location: `SKILL/config/email/msmtprc`

3. **Moltbook API Key**
   - Key: `moltbook_sk_48TKppT2...` (truncated)
   - Agent: `rukaai`
   - Risk: Platform access theft
   - Exposure location: `SKILL/config/moltbook/credentials.json`

---

## ✅ WHAT WE DID TO PROTECT YOU

### 1. Removed All Hardcoded Credentials ✅
- Deleted 3 OpenRouter API keys from `config.py`
- Cleaned sensitive files from repository
- Enhanced `.gitignore` to block future leaks

### 2. Installed Pre-Commit Protection ✅
```bash
.git/hooks/pre-commit  # Active secret detection hook
```
This will automatically block any commits containing secrets.

### 3. Created Secure Backups ✅
```bash
~/.ruka/backup/
├── .env.backup.[timestamp]        ← Your .env backup
├── msmtprc.backup.[timestamp]     ← Email config backup
├── moltbook_credentials.backup    ← Moltbook API key backup
└── users.json.backup              ← Collaborator list backup
```

All backups stored with **restrictive permissions (0600)**.

### 4. Added Security Validation ✅
Ruka AI now checks at startup:
- Validates API key format before running
- Warns if no credentials detected
- Prevents execution with invalid/expired keys

### 5. Implemented Audit Logging ✅
```python
from security_logger import get_security_logger
# All credential access events logged to ~/.ruka/logs/security.log
```

---

## 🚨 YOUR ACTION ITEMS (DO WITHIN 24 HOURS)

### STEP 1: Rotate ALL Credentials Immediately

#### A. OpenRouter API Keys
**Where:** https://openrouter.ai/keys

1. Go to "API Keys" section
2. Find the 3 keys that were in your `config.py`:
   - One starting with `sk-or-v1-07bbc...`
   - One starting with `sk-cdt-eyJpZCI6...`
   - One starting with `sk-yEXLQSYJr5DO...`
3. Click "Revoke" on each one
4. Generate NEW keys:
   - Name: "Ruka AI - Dev" (for development)
   - Name: "Ruka AI - Staging" (if you have staging)
   - Name: "Ruka AI - Production" (for production)
5. Copy new keys somewhere safe (password manager recommended)

**Backup old keys temporarily:**
```bash
mkdir -p ~/.old-keys && cd ~/.old-keys
cat > OPENROUTER_API_KEY_old << 'EOF'
[API-KEY-REDACTED]
[REDACTED-REAL-KEY]
[REDACTED-REAL-KEY]
EOF
chmod 600 OPENROUTER_API_KEY_old
```

#### B. Gmail App Password
**Where:** Google Account → Security → 2-Step Verification → App Passwords

1. Sign in to your Gmail account
2. Navigate to: https://myaccount.google.com/security
3. Scroll to "2-Step Verification" → "App passwords"
4. Select device: "Other (Ruka AI)" 
5. Click "Generate"
6. **Copy the new password immediately** (format: 4 groups of 4 letters)
7. Old password (`[GMAIL-APP-PASSWORD-REDACTED]`) is now invalid

⚠️ **Important:** You must use an **App Password**, not your regular Gmail password!

#### C. Moltbook API Key
**Where:** https://www.moltbook.com/u/rukaai/settings

1. Login to Moltbook
2. Go to Settings/API section
3. Find current API key: `[MOLTBOOK-API-KEY-REDACTED]`
4. Click "Regenerate Key"
5. Copy new key to password manager

---

### STEP 2: Update Configuration Files

After generating new credentials, update these files:

#### A. Update `.env` File
```bash
nano .env
```

Replace content with:
```
OPENROUTER_API_KEY=sk-or-v1-YOUR_NEW_KEY_HERE
# Optional model override
# RUKA_MODEL=openrouter/owl-alpha
```

#### B. Update Email Config
```bash
nano SKILL/config/email/msmtprc
```

Replace line:
```
password [GMAIL-APP-PASSWORD-REDACTED]  # OLD COMPROMISED PASSWORD
```

With:
```
password YOur-New-Gmail-App-PassHere  # New 16-char app password
```

#### C. Update Moltbook Config
```bash
nano SKILL/config/moltbook/credentials.json
```

Replace:
```json
{
  "api_key": "YOUR-MOLTBOOK-NEW-API-KEY",
  "agent_name": "rukaai"
}
```

---

### STEP 3: Verify Everything Works

Run these tests:

#### Test 1: Start Ruka AI
```bash
python main.py
```

✅ Expected output: No warnings about missing API key  
❌ If error: Double-check `.env` file syntax (no extra quotes/spaces)

---

#### Test 2: Check Pre-Commit Hook
```bash
cat > test-secret.txt << 'EOF'
OPENROUTER_API_KEY=sk-or-v1-test-key
EOF

git add test-secret.txt
# Try to commit → Should be BLOCKED by pre-commit hook
```

✅ Expected output:
```
🚫 REJECTED: Potential secret detected in 'test-secret.txt'
📝 Pattern matched: sk-or-v1-[a-zA-Z0-9]{32,}
```

❌ If it commits successfully → reinstall hook

---

#### Test 3: Verify Secure Command Executor
```bash
python -c "
from secure_command_executor import SecureCommandExecutor, SecurityException

executor = SecureCommandExecutor()

# This should SUCCEED
stdout, stderr, rc = executor.execute('echo hello')
assert stdout.strip() == 'hello', f'Unexpected output: {stdout}'

# This should FAIL
try:
    executor.execute('\`whoami\`')
    print('❌ SECURITY BREACH: Backtick bypass successful!')
except SecurityException:
    print('✅ PASSED: Backtick command blocked correctly')
"
```

✅ Expected output:
```
✅ PASSED: Backtick command blocked correctly
```

---

### STEP 4: Backup New Credentials Securely

```bash
# Create encrypted offline backup
mkdir -p ~/secure-backups/ruka-$(date +%Y%m%d)
cp .env ~/secure-backups/ruka-*/
cp SKILL/config/email/msmtprc ~/secure-backups/ruka-*/
cp SKILL/config/moltbook/credentials.json ~/secure-backups/ruka-*/
chmod 600 ~/secure-backups/ruka-*/*
```

Store this folder:
- In encrypted drive (VeraCrypt disk)
- On USB stick in physical safe
- Or upload to secure cloud storage (Encrypted ZIP + password)

---

## 📊 WHAT'S SAFE NOW

### Already Resolved ✅
- No more hardcoded API keys in source code
- Pre-commit hook prevents future leaks
- Credential validation at startup
- Audit logging operational
- Environment variable scrubbing enhanced

### Still Needs Your Attention ⚠️
- Integrate `SecureCommandExecutor` into actual tool (done by us, just needs testing)
- Rotate all credentials (YOU do this!)
- Enable session encryption (optional, high recommendation)

---

## ❓ COMMON QUESTIONS

### Q: What if I don't rotate credentials?
**A:** Attacker could:
- Use your OpenRouter account → incur $100s in charges
- Send emails from your Gmail account → spam/phishing
- Access Moltbook platform → impersonate you

**Risk Level:** HIGH - Immediate action required

---

### Q: How long until credentials expire?
**A:** OpenRouter keys don't auto-expire, but compromised keys are considered expired NOW. Always revoke when suspected compromise.

---

### Q: Can I restore from the backups we created?
**A:** YES! The backup files in `~/.ruka/backup/` contain your OLD credentials. These are useful if:
- New keys fail unexpectedly
- You need to rollback quickly
- Testing purposes

But remember: Old credentials are now compromised, so only use as emergency fallback.

---

### Q: What if I forgot to back up credentials?
**A:** Check if you still have them stored:
```bash
ls -la ~/.ruka/backup/  # Look for backup files
grep -r "sk-or-v1-" /path/to/backups  # Search in old backups
```

If none found, generate completely fresh keys (don't try to recover old ones).

---

### Q: Do I need to change git history?
**A:** Probably not, because:
1. `.env` was already gitignored when added
2. Sensitive configs were never committed to public repo

But if you manually committed sensitive files before today, run:
```bash
git filter-repo --invert-paths --path .env
git push --force --all origin  # Warning: breaks other collaborators' repos!
```

---

## 🛡️ OPTIONAL ENHANCEMENTS (Recommended but Not Critical)

### 1. Enable Session Encryption
See `SECURITY_RELEASE_CHECKLIST.md` → Section H2 for PBKDF2+Fernet implementation guide.

**Benefit:** Sessions stored encrypted → even if someone gets local access, they can't read conversation history without password.

**Cost:** Requires user to set a master password per session

**Decision:** Recommended for production use, optional for personal/local use

---

### 2. Add Rate Limiting
See `SECURITY_HARDENING_SUMMARY.md` → Section M7

**Benefit:** Prevents DDoS attacks against your instance

**Implementation:** Sliding window rate limiter (100 requests/minute per user)

**ETA:** ~2 hours coding + testing

---

### 3. Containerize Command Execution
See `SECURITY_FINAL_REPORT.md` → Section Pending: H3

**Benefit:** Commands run in isolated Docker containers

**Complexity:** High (requires Docker setup, resource management)

**Recommendation:** Phase 2 improvement after basic hardening complete

---

## 📞 NEED HELP?

### Support Channels

**GitHub Issues:**
- Tag: `[SECURITY]`
- Include: Error messages, steps to reproduce

**Direct Contact:**
- Repository owner: Hamzah82
- Email: Check README.md or GitHub profile

**Documentation:**
- Full audit report: `SECURITY_AUDIT_REPORT.md`
- Release checklist: `SECURITY_RELEASE_CHECKLIST.md`
- Executive summary: `SECURITY_HARDENING_SUMMARY.md`
- Final verdict: `SECURITY_FINAL_REPORT.md`

---

## ⏰ TIMELINE SUMMARY

| Task | Estimated Time | Priority |
|------|----------------|----------|
| Rotate OpenRouter key | 5 minutes | 🔴 CRITICAL |
| Regenerate Gmail app password | 10 minutes | 🔴 CRITICAL |
| Regenerate Moltbook API key | 5 minutes | 🔴 CRITICAL |
| Update configuration files | 5 minutes | 🔴 CRITICAL |
| Test Ruka AI startup | 2 minutes | 🔥 HIGH |
| Verify pre-commit hook | 1 minute | ⚠️ MEDIUM |
| Test SecureCommandExecutor | 3 minutes | ⚠️ MEDIUM |
| Backup credentials offline | 5 minutes | ⚠️ MEDIUM |
| Implement session encryption | 2 hours | ℹ️ LOW |

**Total Critical Tasks:** ~30 minutes  
**Total Work Required:** ~2.5 hours (including optional enhancements)

---

## ✅ CHECKLIST FOR COMPLETION

Print this and check off as you go:

```
[ ] 1. Revoked 3 OpenRouter API keys
[ ] 2. Generated 1+ new OpenRouter keys
[ ] 3. Updated .env with new OpenRouter key
[ ] 4. Generated new Gmail app password
[ ] 5. Updated SKILL/config/email/msmtprc
[ ] 6. Regenerated Moltbook API key
[ ] 7. Updated SKILL/config/moltbook/credentials.json
[ ] 8. Tested python main.py startup
[ ] 9. Verified pre-commit hook blocks secrets
[ ] 10. Tested SecureCommandExecutor evasion blocking
[ ] 11. Created offline credential backup
[ ] 12. Documented where new keys are stored
```

---

**Deadline:** Complete by 2026-08-24 17:00 UTC (24 hours from notification)

**Status Tracker:** Mark completion in GitHub PR or comment below with checkmarks.

---

**Thank you for taking security seriously.** Your prompt action protects:
- Your billing accounts
- Your email identity  
- Your digital presence across platforms

If you've completed all steps above, respond with:

```
✅ SECURE COMPLETE
   • OpenRouter key rotated: [new key prefix, e.g., sk-or-v1-XXXX]
   • Gmail app password updated: [YYYY-MM-DD HH:MM]
   • Moltbook key regenerated: [YYYY-MM-DD HH:MM]
   • Tests passed: ✓ Startup ✓ Pre-commit ✓ Exec executor
   • Offline backup created: Yes/No
```

We'll review and confirm production readiness.
