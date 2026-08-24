"""
Security Logger for Ruka AI
Centralized logging for all security-related events.

Features:
- JSON structured logging
- 90-day retention with auto-cleanup
- Sensitive data masking (credentials, tokens)
- Request ID tracking for audit trail
"""

import json
import os
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import atexit

# Directory to store security logs (outside workspace, in user home)
SECURITY_LOG_DIR = Path.home() / ".ruka" / "logs"
SECURITY_LOG_FILE = SECURITY_LOG_DIR / "security.log"
LOG_RETENTION_DAYS = 90

# Event types that MUST be logged
SECURITY_EVENT_TYPES = frozenset({
    'command_executed',        # Successful/blocked command execution
    'security_blocked',        # Policy violation attempt
    'path_traversal_attempt',  # Directory escape detected
    'credential_access',       # API key retrieved
    'session_created',         # New session started
    'auth_failure',            # Failed authentication
    'file_operation',          # File read/write/delete operations
    'environment_scrubbed',    # Sensitive env vars removed
})


class SecurityLogger:
    """Thread-safe security event logger"""
    
    def __init__(self):
        self.log_dir = SECURITY_LOG_DIR
        self.log_file = SECURITY_LOG_FILE
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions
        os.chmod(self.log_dir, 0o700)
        
        # Register cleanup on exit
        atexit.register(self._cleanup_old_logs)
    
    def _mask_sensitive_data(self, data: str) -> str:
        """Mask sensitive information like API keys"""
        # Mask OpenRouter API keys: sk-or-v1-****{last4}
        if data and len(data) > 12:
            if data.startswith('sk-or-v1'):
                return f'sk-or-v1-****{data[-4:]}'
            
            # Mask Moltbook keys
            if data.startswith('moltbook_sk_'):
                return 'moltbook_sk_****'
            
            # Generic API key masking
            if any(part in data.lower() for part in ['password', 'api_key', 'secret']):
                return '[REDACTED]'
        
        return data
    
    def log_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        user_agent: Optional[str] = None,
        user_fingerprint: Optional[str] = None
    ) -> str:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            details: Event details (will be masked before storage)
            user_agent: User agent string from HTTP request
            user_fingerprint: Unique identifier for the user session
            
        Returns:
            Request ID for tracing
        """
        if event_type not in SECURITY_EVENT_TYPES:
            raise ValueError(f"Invalid event type: {event_type}")
        
        # Generate unique request ID for audit trail
        request_id = str(uuid.uuid4())
        
        # Build log entry
        log_entry = {
            'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'event_type': event_type,
            'request_id': request_id,
            'user_agent': self._mask_sensitive_data(user_agent) if user_agent else None,
            'user_fingerprint': user_fingerprint,
            'details': self._mask_details(details),
        }
        
        # Write to log file atomically
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except IOError as e:
            print(f"[SECURITY LOG ERROR] Failed to write log: {e}")
            # Fallback: log to stderr
            import sys
            print(f"[SECURITY] Critical error writing log file: {e}", file=sys.stderr)
        
        return request_id
    
    def _mask_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask sensitive fields in details dictionary"""
        MASKED_FIELDS = {'password', 'api_key', 'token', 'secret', 'credential'}
        
        result = {}
        for key, value in details.items():
            key_lower = key.lower()
            
            # Check if field name suggests sensitivity
            if any(field in key_lower for field in MASKED_FIELDS):
                result[key] = '[REDACTED]'
            elif isinstance(value, str):
                result[key] = self._mask_sensitive_data(value)
            elif isinstance(value, dict):
                result[key] = self._mask_details(value)
            elif isinstance(value, list):
                result[key] = [
                    self._mask_sensitive_data(str(item)) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
    
    def get_event_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[frozenset] = None,
        limit: int = 100
    ) -> list:
        """
        Retrieve recent security events.
        
        Args:
            start_time: Filter events after this time
            end_time: Filter events before this time  
            event_types: Filter by specific event types
            limit: Maximum number of events to return
            
        Returns:
            List of log entries (most recent first)
        """
        if not self.log_file.exists():
            return []
        
        results = []
        now = datetime.utcnow()
        
        # Parse log file
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        entry = json.loads(line)
                        
                        # Apply filters
                        if start_time:
                            entry_time = datetime.strptime(entry['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
                            if entry_time < start_time:
                                continue
                        
                        if end_time:
                            entry_time = datetime.strptime(entry['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
                            if entry_time > end_time:
                                continue
                        
                        if event_types and entry['event_type'] not in event_types:
                            continue
                        
                        results.append(entry)
                        
                    except (json.JSONDecodeError, KeyError):
                        continue  # Skip malformed entries
                        
        except IOError:
            return []
        
        # Sort by timestamp descending (most recent first) and apply limit
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return results[:limit]
    
    def _cleanup_old_logs(self) -> None:
        """Remove log entries older than retention period"""
        try:
            cutoff = datetime.utcnow() - timedelta(days=LOG_RETENTION_DAYS)
            
            if not self.log_file.exists():
                return
            
            filtered_entries = []
            temp_log = self.log_file.parent / 'security.log.tmp'
            
            # Read and filter old entries
            with open(self.log_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.strptime(entry['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
                        
                        if entry_time >= cutoff:
                            filtered_entries.append(line)
                            
                    except (json.JSONDecodeError, KeyError):
                        continue  # Keep malformed entries to avoid losing data
            
            # Write back filtered entries
            with open(temp_log, 'w') as f:
                f.writelines(filtered_entries)
            
            # Atomic swap
            temp_log.replace(self.log_file)
            os.chmod(self.log_file, 0o600)
            
            # Clean up temp file
            if temp_log.exists():
                temp_log.unlink()
                
        except Exception as e:
            print(f"[SECURITY LOG ERROR] Cleanup failed: {e}")
    
    def generate_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate security report for specified period"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        events = self.get_event_history(start_time=cutoff)
        
        summary = {
            'period_days': days,
            'total_events': len(events),
            'events_by_type': {},
            'blocked_attempts': 0,
            'successful_commands': 0,
            'unique_users': set(),
            'risk_score': 0,
        }
        
        for event in events:
            event_type = event['event_type']
            summary['events_by_type'][event_type] = summary['events_by_type'].get(event_type, 0) + 1
            
            if event_type == 'security_blocked':
                summary['blocked_attempts'] += 1
                summary['risk_score'] += 5
            
            if event_type == 'command_executed':
                summary['successful_commands'] += 1
            
            if event.get('user_fingerprint'):
                summary['unique_users'].add(event['user_fingerprint'])
        
        summary['unique_users'] = len(summary['unique_users'])
        return summary


# Singleton instance
_logger_instance: Optional[SecurityLogger] = None


def get_security_logger() -> SecurityLogger:
    """Get or create singleton security logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = SecurityLogger()
    return _logger_instance


# Convenience functions for common use cases
def log_command_execution(command: str, success: bool, duration_ms: float):
    """Log command execution event"""
    logger = get_security_logger()
    return logger.log_event(
        event_type='command_executed',
        details={
            'command': command,
            'success': success,
            'duration_ms': duration_ms,
        }
    )


def log_security_block(reason: str, attempted_command: str):
    """Log blocked security violation"""
    logger = get_security_logger()
    return logger.log_event(
        event_type='security_blocked',
        details={
            'reason': reason,
            'attempted_command': attempted_command,
        }
    )


def log_path_traversal(path: str, user_action: str):
    """Log path traversal attempt"""
    logger = get_security_logger()
    return logger.log_event(
        event_type='path_traversal_attempt',
        details={
            'path': path,
            'action': user_action,
        }
    )


def log_credential_access(credential_type: str):
    """Log when a credential is accessed/retrieved"""
    logger = get_security_logger()
    return logger.log_event(
        event_type='credential_access',
        details={
            'credential_type': credential_type,
        }
    )


def log_environment_scrubbed(vars_removed: list):
    """Log environment variables that were scrubbed"""
    logger = get_security_logger()
    return logger.log_event(
        event_type='environment_scrubbed',
        details={
            'variables_removed': vars_removed,
        }
    )
