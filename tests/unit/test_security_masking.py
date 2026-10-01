"""Unit tests for PIIMasker and IdempotencyHasher."""

import pytest
from services.security.masking import PIIMasker, IdempotencyHasher


def test_ip_masking():
    # IPv4 standard
    assert PIIMasker.mask_ip_address("192.168.1.100") == "192.168.***.***"
    assert PIIMasker.mask_ip_address("10.0.50.2") == "10.0.***.***"

    # None or unknown
    assert PIIMasker.mask_ip_address(None) == "0.0.0.0"
    assert PIIMasker.mask_ip_address("unknown") == "0.0.0.0"

    # IPv6
    ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    assert PIIMasker.mask_ip_address(ipv6).startswith("2001:")


def test_card_token_masking():
    token = "TOKEN_CC_VISA_8841"
    masked = PIIMasker.mask_card_token(token)
    assert masked.endswith("8841")
    assert "****-****-****-" in masked


def test_payload_sanitization_and_redaction():
    raw_payload = {
        "transaction_id": "TXN-SEC-01",
        "customer_id": "CUST-100",
        "ip_address": "172.16.4.22",
        "payment_method": "TOKEN_PAYPAL_3391",
        "cvv": "123",
        "password": "super_secret_pwd",
    }

    sanitized = PIIMasker.sanitize_payload_for_logging(raw_payload)

    assert sanitized["ip_address"] == "172.16.***.***"
    assert sanitized["payment_method"].endswith("3391")
    assert sanitized["cvv"] == "[REDACTED]"
    assert sanitized["password"] == "[REDACTED]"


def test_idempotency_hasher_properties():
    key1 = IdempotencyHasher.generate_key("CUST-1", 100.0, "2026-10-01T12:00:00Z")
    key2 = IdempotencyHasher.generate_key("CUST-1", 100.0, "2026-10-01T12:00:00Z")
    key3 = IdempotencyHasher.generate_key("CUST-2", 100.0, "2026-10-01T12:00:00Z")

    assert len(key1) == 64  # SHA-256 hex string length
    assert key1 == key2      # Deterministic
    assert key1 != key3      # Distinct inputs yield distinct hashes
