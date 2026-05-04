import re
import json
import logging
from typing import Any

class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that masks sensitive data like emails and auth tokens.
    """
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self.mask_pii(record.msg)
        elif isinstance(record.msg, dict):
            record.msg = self.mask_dict(record.msg)
        return True

    def mask_pii(self, text: str) -> str:
        # Mask emails: user@example.com -> u***@example.com
        text = re.sub(
            r'([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
            r'\1***@\2',
            text
        )
        # Mask Bearer tokens
        text = re.sub(r'Bearer\s+[a-zA-Z0-9._-]+', 'Bearer [MASKED]', text)
        return text

    def mask_dict(self, data: dict) -> dict:
        masked = data.copy()
        sensitive_keys = {'email', 'password', 'token', 'access_token', 'refresh_token', 'secret'}
        for key in masked:
            if key.lower() in sensitive_keys:
                masked[key] = "[MASKED]"
            elif isinstance(masked[key], dict):
                masked[key] = self.mask_dict(masked[key])
        return masked

def setup_structured_logging():
    """
    Configures the root logger with PII masking.
    """
    handler = logging.StreamHandler()
    handler.addFilter(SensitiveDataFilter())
    
    # Custom Formatter for semi-structured output
    formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s - %(name)s - %(message)s'
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Remove existing handlers to avoid duplicates during reload
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
