"""Best-effort secret redaction before prompts, traces and review exports."""
import os
import re

TOKEN = re.compile(r'\bgsk_[A-Za-z0-9]{20,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}|\bAIza[A-Za-z0-9_-]{30,}')


def scrub(value):
    if isinstance(value, str):
        for name in ('GROQ_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_API_KEY'):
            secret = os.getenv(name, '')
            if secret and len(secret) > 8:
                value = value.replace(secret, '[REDACTED]')
        return TOKEN.sub('[REDACTED]', value)
    if isinstance(value, dict):
        return {scrub(key): scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value
