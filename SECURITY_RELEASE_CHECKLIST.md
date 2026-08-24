# 🔒 Pre-Release Security Checklist — Ruka AI

**Status**: ❌ NOT READY FOR PRODUCTION  
**Last Updated**: 2026-06-23  
**Auditor**: Qoder + Automated Security Analysis

---

## 🔴 CRITICAL (BLOCKING) — MUST COMPLETE BEFORE RELEASE

### C1: Credential Rotation
```bash
[ ] ALL OpenRouter keys rotated at dashboard.openrouter.ai
    → Generate NEW key per environment (dev/staging/prod only)
    → Format validation: ^sk-or-v1-[a-f0-9]{64}$
    
[ ] Gmail App Password regenerated
    → Google Account → Security → 2SV → App Passwords → "Ruka AI" device
    → OLD password `nout eyjo kfss foze` now compromised
    
[ ] Moltbook API Key regenerated
    → moltbook.com/u/rukaai/settings
    → OLD key `moltbook_sk_48TKppT2...` now compromised
    
[ ] Hardcoded keys REMOVED from config.py (lines 196-198)
    git diff HEAD config.py | grep -E "^[-+](OPENROUTER_API_KEY[0-9]?|password|moltbook)"
    # Should show: ONLY removal lines, NO new secret additions
    
[ ] Secure credential loading implemented
    cat config.py | grep -A 20 "def load_credentials"
    # Must include: env var validation, ~/.ruka/config fallback with mode check
```

**Verification Commands**:
```bash
# No credentials should exist in working tree
git status --short | grep -E '\.env|msmtprc|credentials\.json'

# No secrets in source files
grep -r "sk-or-v1-\|password.*gmail\|moltbook_sk" . --include="*.py" --include="*.json" --include="*.rc" --include="*.conf" | grep -v "\.example$"

# Output: EMPTY LIST (no matches)
```

---

### C2: Git History Sanitization
```bash
[ ] Pre-commit hook installed with secret detection
    cat .git/hooks/pre-commit | head -20
    # Should contain: sk-or-v1 pattern, molltbook_sk pattern, password patterns

[ ] Verify no credentials ever existed in history
    git log --all --oneline -- .env | wc -l         # Should be: 0
    git grep -l "sk-or-v1-" $(git rev-list --all)   # Should return: nothing

[ ] Back up sensitive files offline before cleanup
    mkdir -p ~/.backup/secrets && cd ~/.backup/secrets
    cp ../../../.env . 2>/dev/null || echo "No .env found (expected if already cleaned)"
    chmod 600 *

[ ] Force push after cleanup (warn collaborators!)
    git filter-repo --invert-paths --path .env       # If .env was committed
    git filter-repo --invert-paths --path SKILL/config/email/msmtprc
    git filter-repo --invert-paths --path SKILL/config/moltbook/credentials.json
    git push --force --all origin
    git push --force --tags origin
```

**Verification Checklist**:
```bash
# Run these commands — all must return empty:
git log --all --diff-filter=A -- .env
git rev-list --all --objects | grep -E '(^|/)\\.env$'
git log --all --diff-filter=A -- SKILL/config/email/msmtprc
git log --all --diff-filter=A -- SKILL/config/moltbook/credentials.json
```

---

### C3: Command Injection Fix
```python
[ ] SecureCommandExecutor implemented with 3-layer defense
    grep -n "class SecureCommandExecutor:" main.py
    # Line number must exist
    
[ ] Layer 1: Pre-scan syntax blocking verified
    grep -A 10 "FORBIDDEN_PATTERNS = re.compile" main.py
    # Must block: backticks, $(), newlines, ;, &&, ||, redirects to /dev/

[ ] Layer 2: Behavior analysis deterministic
    grep -A 5 "ALLOWED_PIPELINE_CMDS = frozenset" main.py
    # Whitleist must include: cat, grep, head, tail, wc, sort, awk, sed, find, ls

[ ] Layer 3: Sandboxed execution tested
    grep -A 15 "_execute_pipeline_sandboxed" main.py
    # Timeout hardcoded (max 30s), cwd isolated, env scrubbed

[ ] Unit tests for evasion techniques passing
    pytest test_command_security.py -v
    # All test cases blocked/allowed must pass
```

**Manual Test Cases** (run interactively):
```python
# THESE SHOULD BE BLOCKED:
try:
    executor.execute("rm -rf /; ls")
    print("❌ FAILED — command chain allowed!")
except SecurityException:
    print("✅ PASS — command chain blocked")

try:
    executor.execute("cat $(ls /etc)")
    print("❌ FAILED — command sub allowed!")
except SecurityException:
    print("✅ PASS — cmd substitution blocked")

try:
    executor.execute("`whoami`")
    print("❌ FAILED — backtick execution allowed!")
except SecurityException:
    print("✅ PASS — backtick blocked")

# THESE SHOULD WORK:
try:
    stdout, stderr, code = executor.execute("ls -la")
    print("✅ PASS — safe command executed")
except Exception as e:
    print(f"❌ FAILED — safe command blocked: {e}")
```

---

## 🔥 HIGH-RISK (MUST FIX)

### H1: Path Traversal Bug Fixes
```python
[ ] _count_symlink_depth() fixed (calculate BEFORE realpath)
    grep -A 15 "_count_symlink_depth" main.py | head -20
    # Logic must count symlinks WHILE traversing path string, NOT after resolution

[ ] _is_safe_script_dir() syntax error fixed
    python -c "import ast; ast.parse(open('main.py').read())"
    # Exit code 0 = no syntax errors

[ ] Regex whitespace acceptance corrected
    grep "sanitize_path" main.py | grep -o "[^\]]*\$[^,]*[^\\]"
    # Pattern must include \s character class: `[a-zA-Z0-9_\.\-/\s]+`
```

### H2: Encrypted Session Storage
```python
[ ] PBKDF2 + Fernet encryption implemented
    grep -n "from cryptography" main.py sessions/session_store.py
    # Must import: PBKDF2HMAC, hashes.SHA256(), Fernet

[ ] Salt storage mechanism verified
    grep -A 10 "salt = os.urandom(16)" session_store.py
    # Must generate 16-byte random salt for EACH session

[ ] Iteration count set to OWASP recommended
    grep "iterations.*480_000\|ITERATIONS.*480_000" session_store.py
    # Value must be 480,000 (not 10,000 or lower)

[ ] File permissions explicit 0600
    os.chmod(session_file, 0o600)
    # Must appear AFTER file write
```

**Test Encryption Round-Trip**:
```python
session_data = {"messages": [...], "user_id": "test"}
encrypted = encrypt_session(session_data, "test-password")
decrypted = decrypt_session(encrypted, "test-password")
assert decrypted == session_data, "Encryption round-trip failed!"

# Tamper detection test:
tampered = encrypted[:-10] + b"x"*10
try:
    decrypt_session(tampered, "test-password")
    print("❌ Tamper detection FAILED")
except InvalidToken:
    print("✅ Tamper detected correctly")
```

### H3: Environment Variable Scrubbing
```python
[ ] DANGEROUS_ENV_VARS list complete
    grep -A 20 "DANGEROUS_ENV_VARS = \[" main.py
    # Must include: AWS_*, AZURE_*, GCP_*, DATABASE_URL, SECRET_KEY, GITHUB_TOKEN

[ ] Scrubbing applied to subprocess calls
    grep -B 5 -A 5 "env={k: v for k, v in os.environ.items()" main.py
    # Pattern must exclude all DANGEROUS_ENV_VARS

[ ] Audit logging for credential access
    # Every time OPENROUTER_API_KEY loaded → log to SECURITY_LOG
```

### H4: Input Validation Completeness
```python
[ ] Session name regex strict
    SESSION_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
    # Reject: slashes, quotes, control characters, ampersands

[ ] Command length limit enforced
    MAX_COMMAND_LENGTH = 4096
    if len(command) > MAX_COMMAND_LENGTH:
        raise ValueError("Command too long")

[ ] Tool output cap applied before LLM context
    MAX_TOOL_OUTPUT_CHARS = 64_000
    truncated = output[:MAX_TOOL_OUTPUT_CHARS]
    escaped_control_chars = unescape_controls(truncated)
```

### H5: Audit Trail Implementation
```python
[ ] Centralized security logging module created
    touch security_logger.py
    cat security_logger.py
    # Must have: log_event(event_type, details, user_agent, timestamp)

[ ] Event types defined and logged
    LOG_EVENTS = ['command_executed', 'security_blocked', 'credential_access', ...]
    # Each event logged with: request_id, timestamp, user fingerprint, details dict

[ ] Retention policy automated
    # Auto-delete logs older than 90 days via cron job
    # Or implement rotating file handlers
```

---

## ⚠️ MEDIUM-RISK (SHOULD FIX BEFORE v1.0)

### M1: File Permission Hardening
```bash
[ ] umask set at application startup
    [ ] In main.py: os.umask(0o077) added before any file operations

[ ] _secure_write helper function implemented
    def _secure_write(path: str, data: bytes, mode: int = 0o600):
        # Uses os.O_EXCL flag for atomic creation

[ ] Session files permission verified post-write
    stat(session_file).st_mode & 0o077 == 0o000  # No group/world perms
```

### M2: TOCTOU Race Mitigation
```python
[ ] Critical paths use O_NOFOLLOW flag
    fd = os.open(path, flags=os.O_RDONLY | os.O_NOFOLLOW)
    # Prevent symlink swap during file access window

[ ] Documentation acknowledges remaining race condition
    """Note: Small TOCTOU window exists between realpath() and open().
    For most use cases this is acceptable risk (see OpenWall writeup)."""
```

### M3: Timeout Enforcement
```python
[ ] Global timeout decorator implemented
    @timeout(seconds=30, max_timeout_override={"export_db": 120})
    def execute_command(cmd):
        ...

[ ] Exemption list version-controlled
    TIMEOUT_EXCEPTIONS = {
        "copy_large_files": 60,
        "search_deep_dirs": 90,
        "export_database": 120,
    }
    # Each exception: documented reason + audit log entry on usage
```

### M4: Dependency Pinning
```bash
[ ] requirements.txt exact versions
    requests==2.31.0
    python-dotenv==1.0.0
    python-pptx==1.0.0
    
[ ] Pipfile/Pipenv.lock or poetry.lock present
    # Lock files ensure reproducible builds across environments

[ ] pip-audit scan passed
    pip-audit -r requirements.txt
    # No high/critical CVEs reported
```

### M5: Error Message Sanitization
```python
[ ] Generic error responses to LLM
    Instead of: "Error reading /home/user/secret/data.txt"
    Use: "Unable to process that file"
    
[ ] Detailed errors logged securely (stderr only)
    secure_logger.error(f"{traceback.format_exc()}")

[ ] Stack traces never exposed via tool output
    try:
        dangerous_operation()
    except Exception as e:
        logger.exception(str(e))  # Log internally
        raise SafeError("Operation failed")  # Return safe message
```

### M6: Certificate Pinning (Optional)
```python
[ ] Optional SSL cert pinning for OpenRouter
    import ssl
    import hashlib
    
    pinned_cert_hash = "sha256/Base64Hash=="
    ssl_context = create_ssl_context(pinned_cert=pinned_cert_hash)
    
# Only enable if critical endpoint compromise acceptable risk
```

### M7: Rate Limiting
```python
[ ] Sliding window rate limiter implemented
    class RateLimiter:
        def __init__(self, max_requests=100, window_seconds=60):
            self.requests = deque()
        
        def allow_request(self, user_id):
            now = time.time()
            while self.requests and now - self.requests[0] > self.window_seconds:
                self.requests.popleft()
            
            return len(self.requests) < self.max_requests

[ ] Applied per user/session/fingerprint
    limiter = RateLimiter(max_requests=100, window_seconds=60)
    if not limiter.allow_request(user_fingerprint):
        raise TooManyRequestsError("Rate limit exceeded")
```

---

## ℹ️ LOW-PRIORITY (NICE TO HAVE)

### L1: Unit Tests Coverage
```bash
[ ] Security-critical functions covered
    pytest --cov=main.py --cov-report=term-missing tests/
    # Minimum 90% coverage for: SecureCommandExecutor, path validators, encryptor

[ ] Fuzzing tests for inputs
    afl-fuzz ./fuzz_tester
    # All malformed inputs handled gracefully (no crashes)
```

### L2: Documentation Updates
```bash
[ ] SECURITY.md comprehensive threat model
    # Attack surfaces: network, local filesystem, environment, user input, third-party APIs

[ ] INCIDENT_RESPONSE.md playbook
    # Steps for: credential compromise, command injection success, data breach

[ ] GDPR compliance statement
    # How session data stored, retained, deleted under EU regulations
```

### L3: Containerization
```bash
[ ] Docker container for command execution
    # exec_command runs inside isolated container with:
    #   - No network access (--network=none)
    #   - Read-only filesystem (/tmp writable temp dir)
    #   - Resource limits (CPU/memory caps)

[ ] Namespace isolation for critical ops
    nsenter --target=$(pidof python) --all python subprocess_script.py
```

### L4: Automatic Updates
```bash
[ ] Opt-in update mechanism
    python main.py --auto-update
    
[ ] Signature verification for updates
    gpg --verify Ruka-AI-latest.tar.gz.sig Ruka-AI-latest.tar.gz
```

---

## 📊 METRICS CHECKLIST

Before release, verify these metrics meet thresholds:

```bash
[ ] Zero critical/high CVEs in dependencies
    pip-audit -r requirements.txt | grep -E "(CRITICAL|HIGH)" | wc -l
    # Must equal: 0

[ ] All command injection tests pass
    pytest tests/command_security.py -v | grep -E "passed|failed"
    # Failed: 0

[ ] All path traversal attempts blocked
    pytest tests/path_traversal.py -v | grep "100% passed"
    # 100% pass rate

[ ] Encryption round-trip tests pass
    pytest tests/session_encryption.py -v
    # Round-trip + tamper detection: 100% pass

[ ] Average execution overhead < 50ms added
    time python main.py "list all files" | grep real
    # Overhead vs baseline: < 50ms

[ ] Memory footprint stable over 1-hour run
    ps aux | grep main.py | awk '{print $6}'
    # RSS unchanged within ±5% after 1 hour
```

---

## ✅ FINAL SIGN-OFF TEMPLATE

```markdown
## Security Release Sign-Off

### Date
YYYY-MM-DD HH:MM UTC

### Audited By
[Auditor Name + Contact Info]

### Scope
Files reviewed: main.py, config.py, session_store.py, security_logger.py
Tools tested: read_file, write_file, exec_command, copy_file, delete_file

### Critical Issues Status
- [x] C1: Credential rotation verified ✅
- [x] C2: Git history sanitized ✅
- [x] C3: Command injection mitigated ✅

### High Issues Status
- [x] H1: Symlink bugs fixed ✅
- [x] H2: Encryption implemented ✅
- [x] H3: Env var scrubbing active ✅
- [x] H4: Input validation complete ✅
- [x] H5: Audit trail logging enabled ✅

### Medium Issues Status
- [x] M1-M7: Partially addressed (document outstanding items)

### Low Issues Status
- [ ] L1-L4: Deferred to future releases

### Penetration Test Results
- Command injection: 0 successful exploits out of N attempts
- Path traversal: 0 escapes out of N attempts
- Credential access: 0 leaks detected
- DoS resistance: sustained 100 req/min for 5 minutes ✅

### Performance Impact Assessment
- Baseline latency: XX ms
- With security controls: YY ms (+ZZ%)
- Acceptable? Yes/No ✅

### Final Recommendation
☐ **NOT APPROVED** — Critical issues remain unresolved
☐ **APPROVED WITH CONDITIONS** — High-risk items scheduled for fix by DATE
☑ **APPROVED FOR RELEASE** — All blocking items complete, medium-risk accepted

### Notes
[List any caveats or monitoring requirements]

Signature: _________________________
Date: YYYY-MM-DD
```

---

**🚫 DO NOT DEPLOY UNTIL ALL [x] MARKS IN CRITICAL/HIGH SECTIONS**

Next review: After implementing Medium/Low priority items, target pre-v1.0 milestone.
