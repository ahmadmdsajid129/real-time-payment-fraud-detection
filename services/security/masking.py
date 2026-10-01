"""Security, Masking & Synthetic Tokenization Safeguards.

Ensures zero PII leakage into log streams, anonymizes IP addresses,
and generates cryptographically secure transaction idempotency hashes.
"""

import hashlib
import re
from typing import Dict, Any, Optional


class PIIMasker:
    """Sanitizes transaction dictionaries and string values before logging or persistent export."""

    @staticmethod
    def mask_ip_address(ip: Optional[str]) -> str:
        """Anonymizes IPv4 and IPv6 addresses by masking host octets."""
        if not ip or ip == "unknown":
            return "0.0.0.0"
        # IPv4: keep first two octets, mask last two
        ipv4_match = re.match(r"^(\d{1,3}\.\d{1,3})\.\d{1,3}\.\d{1,3}$", ip)
        if ipv4_match:
            return f"{ipv4_match.group(1)}.***.***"
        # IPv6: truncate to first prefix segment
        if ":" in ip:
            segments = ip.split(":")
            return f"{segments[0]}:****:****"
        return "***.***.***.***"

    @staticmethod
    def mask_card_token(token: str) -> str:
        """Masks payment tokens preserving only last 4 digits."""
        if not token:
            return "TOKEN-****"
        clean = str(token).strip()
        if len(clean) <= 4:
            return "****"
        return f"****-****-****-{clean[-4:]}"

    @classmethod
    def sanitize_payload_for_logging(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a sanitized copy of a transaction payload safe for structured JSON logging."""
        sanitized = dict(payload)

        # Mask IP
        if "ip_address" in sanitized:
            sanitized["ip_address"] = cls.mask_ip_address(sanitized["ip_address"])

        # Mask card or payment method tokens
        if "payment_method" in sanitized and "token" in str(sanitized["payment_method"]).lower():
            sanitized["payment_method"] = cls.mask_card_token(sanitized["payment_method"])

        # Remove raw passwords or sensitive credentials if accidentally passed
        for sensitive_key in ["password", "secret", "cvv", "pan", "ssn", "pin"]:
            if sensitive_key in sanitized:
                sanitized[sensitive_key] = "[REDACTED]"

        return sanitized


class IdempotencyHasher:
    """Generates deterministic SHA-256 transaction idempotency digests."""

    @staticmethod
    def generate_key(customer_id: str, amount: float, timestamp: str, salt: str = "fraud-salt") -> str:
        """Computes SHA-256 fingerprint from immutable payment tuple."""
        raw = f"{customer_id}|{amount:.2f}|{timestamp}|{salt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
