# Security & Data Privacy Architecture

---

## 1. Security Architecture & Threat Model

The **Real-Time Payment Fraud Detection & Risk Engine** models threats relevant to financial technology infrastructure:

```text
 ┌──────────────────────┐         ┌────────────────────────┐         ┌─────────────────────────┐
 │ External Attackers   │         │ Malicious Cardholders  │         │ Infrastructure Threats  │
 │ - Credential Stuffing│         │ - Friendly Fraud       │         │ - Secret Exposure       │
 │ - Automated Botnets  │         │ - Card Testing Attacks │         │ - SQL / Command Injection│
 │ - Denial of Service  │         │ - Account Takeover     │         │ - Kafka Poison Pill     │
 └──────────┬───────────┘         └───────────┬────────────┘         └────────────┬────────────┘
            │                                 │                                   │
            └─────────────────────────────────┼───────────────────────────────────┘
                                              ▼
                         ┌─────────────────────────────────────────┐
                         │       Security Control Perimeter        │
                         │ 1. Zero Real Cardholder Data (PII/PAN)  │
                         │ 2. Strict Input Validation (Pydantic)   │
                         │ 3. Parameterized Queries (SQLAlchemy)   │
                         │ 4. Environment-Isolated Secret Storage  │
                         │ 5. Rate Limiting & Network Segregation │
                         └─────────────────────────────────────────┘
```

---

## 2. Zero-PII Policy & Synthetic Identifiers

### Strict Rule
**No real Primary Account Numbers (PANs), Card Verification Values (CVVs), expiration dates, bank passwords, or live customer identities are ever ingested, processed, or persisted in this repository.**

### Identifier Tokenization Scheme
- **Customer IDs**: Formatted as synthetic pseudorandom tokens (`CUST-` + integer/hash).
- **Merchant IDs**: Formatted as merchant tokens (`MERCH-` + integer/hash).
- **Device IDs**: Cryptographically salted client hashes (`DEV-` + SHA256 snippet).
- **Payment Method Tokens**: Generic tokens (e.g., `TOKEN_CC_VISA_8841`, `UPI_VPA_7712`).

---

## 3. Application Security Safeguards

### 3.1 Input Validation & Strict Typing
- All inbound network payloads pass through **Pydantic V2** schemas before execution.
- Payloads containing unexpected types, negative amounts, out-of-range timestamps ($> 5$ minutes in the future), or script injection strings are rejected at the edge with HTTP 422.

### 3.2 SQL Injection Prevention
- Relational access uses **SQLAlchemy 2.0 Async ORM** and parameterized queries.
- Raw string formatting or unescaped concatenation in SQL statements is strictly prohibited.

### 3.3 Network Isolation & Docker Security
- Backing datastores (PostgreSQL, Redis, Kafka) are bounded within the internal Docker network (`fraud-engine-net`).
- In production deployments, only the API gateway and Next.js frontend expose public listening ports.

### 3.4 Rate Limiting & Denial-of-Service Defense
- FastAPI middleware enforces client IP rate limiting (configurable via `slowapi` or Redis token bucket) to prevent botnets from overwhelming the inference pipeline.

---

## 4. Secret Management & Configuration Hygiene

- All credentials (database passwords, Redis tokens, secret keys) reside in externalized environment files (`.env`).
- `.env` is permanently excluded via `.gitignore`.
- `.env.example` provides non-sensitive mock variables for local developer bootup.
- Docker containers run as non-root unprivileged users where applicable.

---

## 5. PCI-DSS Scope & Honest Limitations

> [!WARNING]
> **Portfolio Simulation Notice**:  
> While this architecture adheres to modern software security standards (encryption in transit, tokenization, defense-in-depth), it is an educational and portfolio system.  
> **It is NOT certified under PCI-DSS Level 1.**  
> It does not implement physical HSM (Hardware Security Module) key management, dedicated SOC 2 Type II audit controls, or formal cardholder data environment (CDE) segmentation required for handling live Visa/Mastercard transactions.
