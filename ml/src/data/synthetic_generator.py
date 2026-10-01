"""Realistic Synthetic Payment Transaction Generator.

Generates temporal transaction streams with realistic customer profiles,
merchant profiles, diurnal seasonality, and controllable fraud attack scenarios.

Strict Rule: Synthetic identifiers are used throughout. Zero real credentials.
"""

from datetime import datetime, timedelta, timezone
import random
import math
from typing import List, Dict, Tuple, Optional
import numpy as np
import pandas as pd

from ml.src.data.schemas import (
    CustomerProfile,
    MerchantProfile,
    TransactionPayload,
    FraudScenario,
    PaymentMethod,
)


# Cities catalog with coordinates and typical country codes
CITIES_CATALOG = [
    {"city": "Mumbai", "country": "IN", "lat": 19.0760, "lon": 72.8777},
    {"city": "Delhi", "country": "IN", "lat": 28.7041, "lon": 77.1025},
    {"city": "Bengaluru", "country": "IN", "lat": 12.9716, "lon": 77.5946},
    {"city": "Hyderabad", "country": "IN", "lat": 17.3850, "lon": 78.4867},
    {"city": "Chennai", "country": "IN", "lat": 13.0827, "lon": 80.2707},
    {"city": "Kolkata", "country": "IN", "lat": 22.5726, "lon": 88.3639},
    {"city": "Pune", "country": "IN", "lat": 18.5204, "lon": 73.8567},
    {"city": "Singapore", "country": "SG", "lat": 1.3521, "lon": 103.8198},
    {"city": "Dubai", "country": "AE", "lat": 25.2048, "lon": 55.2708},
    {"city": "London", "country": "GB", "lat": 51.5074, "lon": -0.1278},
    {"city": "New York", "country": "US", "lat": 40.7128, "lon": -74.0060},
    {"city": "Tokyo", "country": "JP", "lat": 35.6762, "lon": 139.6503},
]

MERCHANT_CATEGORIES = [
    {"category": "GROCERY", "mcc": "5411", "risk": "LOW", "avg_mult": 0.5},
    {"category": "RESTAURANT", "mcc": "5812", "risk": "LOW", "avg_mult": 0.7},
    {"category": "GAS_STATION", "mcc": "5541", "risk": "LOW", "avg_mult": 0.6},
    {"category": "DEPARTMENT_STORE", "mcc": "5311", "risk": "STANDARD", "avg_mult": 1.2},
    {"category": "ELECTRONICS", "mcc": "5732", "risk": "HIGH", "avg_mult": 3.5},
    {"category": "JEWELRY_LUXURY", "mcc": "5944", "risk": "HIGH", "avg_mult": 6.0},
    {"category": "GAMING_CASINO", "mcc": "7995", "risk": "HIGH", "avg_mult": 2.0},
    {"category": "DIGITAL_WALLET_TRANSFER", "mcc": "4829", "risk": "HIGH", "avg_mult": 4.0},
    {"category": "UTILITIES", "mcc": "4900", "risk": "LOW", "avg_mult": 0.8},
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance in kilometers between two geographic coordinates."""
    r = 6371.0  # Earth radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class TransactionGenerator:
    """Generates synthetic customer populations, merchant ecosystems, and temporal transactions."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.customers: Dict[str, CustomerProfile] = {}
        self.merchants: Dict[str, MerchantProfile] = {}
        self.shared_fraud_devices: List[str] = [f"DEV-SYNDICATE-{i:03d}" for i in range(1, 6)]
        self.last_customer_txn: Dict[str, Dict] = {}

    def generate_population(
        self,
        num_customers: int = 1000,
        num_merchants: int = 100
    ) -> None:
        """Initializes synthetic customer profiles and merchant directory."""
        # 1. Generate Merchants
        for i in range(1, num_merchants + 1):
            merch_id = f"MERCH-{i:04d}"
            cat_info = self.rng.choice(MERCHANT_CATEGORIES)
            city_info = self.rng.choice(CITIES_CATALOG[:7])  # Mostly domestic
            # Small random jitter to coordinates
            lat = city_info["lat"] + self.rng.uniform(-0.05, 0.05)
            lon = city_info["lon"] + self.rng.uniform(-0.05, 0.05)
            
            self.merchants[merch_id] = MerchantProfile(
                merchant_id=merch_id,
                name=f"{cat_info['category'].title()} #{i}",
                category=cat_info["category"],
                mcc_code=cat_info["mcc"],
                country=city_info["country"],
                city=city_info["city"],
                lat=lat,
                lon=lon,
                risk_tier=cat_info["risk"],
                avg_amount=1000.0 * cat_info["avg_mult"],
            )

        # 2. Generate Customers
        merchant_ids = list(self.merchants.keys())
        for i in range(1, num_customers + 1):
            cust_id = f"CUST-{i:05d}"
            city_info = self.rng.choice(CITIES_CATALOG[:7])  # Indian domestic baseline
            
            # Customer spending distribution parameters (Lognormal baseline)
            # Most spend 500 - 3000, some high net worth spend 5000 - 25000
            is_hnw = self.rng.random() < 0.08
            avg_amt = self.rng.uniform(6000.0, 18000.0) if is_hnw else self.rng.uniform(600.0, 2500.0)
            std_amt = avg_amt * self.rng.uniform(0.25, 0.45)
            
            devices = [f"DEV-{cust_id[-5:]}-MOB"]
            if self.rng.random() < 0.4:
                devices.append(f"DEV-{cust_id[-5:]}-LAP")

            self.customers[cust_id] = CustomerProfile(
                customer_id=cust_id,
                created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
                home_country=city_info["country"],
                home_city=city_info["city"],
                home_lat=city_info["lat"],
                home_lon=city_info["lon"],
                avg_amount=round(avg_amt, 2),
                std_amount=round(std_amt, 2),
                min_amount=round(max(10.0, avg_amt - 2 * std_amt), 2),
                max_amount=round(avg_amt + 3 * std_amt, 2),
                preferred_merchants=self.rng.sample(
                    merchant_ids,
                    k=min(len(merchant_ids), self.rng.randint(3, 7))
                ),
                known_devices=devices,
                known_countries=[city_info["country"]],
                typical_hour_start=self.rng.randint(7, 9),
                typical_hour_end=self.rng.randint(21, 23),
                avg_txns_per_week=self.rng.uniform(2.0, 14.0),
            )

    def generate_single_transaction(
        self,
        transaction_id: str,
        timestamp: datetime,
        customer_id: Optional[str] = None,
        force_scenario: Optional[FraudScenario] = None,
    ) -> TransactionPayload:
        """Generates a single valid transaction, either normal or injecting a fraud scenario."""
        if not self.customers:
            self.generate_population(num_customers=500, num_merchants=50)

        cust = self.customers[customer_id] if customer_id else self.rng.choice(list(self.customers.values()))
        
        # Decide scenario
        scenario = force_scenario or FraudScenario.NORMAL
        is_fraud = (scenario != FraudScenario.NORMAL)

        # Baseline attributes
        merch_id = self.rng.choice(cust.preferred_merchants)
        merch = self.merchants[merch_id]
        device_id = self.rng.choice(cust.known_devices)
        country = cust.home_country
        city = cust.home_city
        lat = cust.home_lat + self.rng.uniform(-0.02, 0.02)
        lon = cust.home_lon + self.rng.uniform(-0.02, 0.02)
        payment_method = self.rng.choice([PaymentMethod.CREDIT_CARD, PaymentMethod.UPI, PaymentMethod.DEBIT_CARD])
        
        # Sample normal amount using gamma distribution centered on customer avg
        shape = (cust.avg_amount / cust.std_amount) ** 2
        scale = (cust.std_amount ** 2) / cust.avg_amount
        amount = float(self.np_rng.gamma(shape=shape, scale=scale))
        amount = max(20.0, round(amount, 2))

        # Scenario Injections
        if scenario == FraudScenario.HIGH_VALUE_ANOMALY:
            # 10x to 40x customer baseline
            amount = round(cust.avg_amount * self.rng.uniform(10.0, 40.0), 2)
            payment_method = PaymentMethod.CREDIT_CARD

        elif scenario == FraudScenario.NEW_COUNTRY:
            foreign = self.rng.choice([c for c in CITIES_CATALOG if c["country"] != cust.home_country])
            country = foreign["country"]
            city = foreign["city"]
            lat = foreign["lat"]
            lon = foreign["lon"]
            amount = round(cust.avg_amount * self.rng.uniform(2.0, 8.0), 2)

        elif scenario == FraudScenario.NEW_DEVICE:
            device_id = f"DEV-UNRECOGNIZED-{self.rng.randint(10000, 99999)}"
            amount = round(cust.avg_amount * self.rng.uniform(3.0, 10.0), 2)

        elif scenario == FraudScenario.IMPOSSIBLE_TRAVEL:
            # Must be placed in a city thousands of km away
            dest = self.rng.choice([c for c in CITIES_CATALOG if c["city"] != cust.home_city])
            country = dest["country"]
            city = dest["city"]
            lat = dest["lat"]
            lon = dest["lon"]
            amount = round(cust.avg_amount * self.rng.uniform(2.5, 9.0), 2)

        elif scenario == FraudScenario.DEVICE_SHARING:
            # Re-uses a known syndicate device
            device_id = self.rng.choice(self.shared_fraud_devices)
            amount = round(cust.avg_amount * self.rng.uniform(2.0, 6.0), 2)

        elif scenario == FraudScenario.MERCHANT_ANOMALY:
            # High risk category (Crypto / Electronics / Jewelry)
            high_risk_merchs = [m for m in self.merchants.values() if m.risk_tier == "HIGH"]
            if high_risk_merchs:
                merch = self.rng.choice(high_risk_merchs)
                merch_id = merch.merchant_id
            amount = round(cust.avg_amount * self.rng.uniform(8.0, 25.0), 2)

        elif scenario == FraudScenario.ACCOUNT_TAKEOVER:
            # New device + foreign/distant location + high amount + off hours
            device_id = f"DEV-ATO-{self.rng.randint(10000, 99999)}"
            foreign = self.rng.choice([c for c in CITIES_CATALOG if c["country"] != cust.home_country])
            country = foreign["country"]
            city = foreign["city"]
            lat = foreign["lat"]
            lon = foreign["lon"]
            amount = round(cust.avg_amount * self.rng.uniform(15.0, 35.0), 2)
            payment_method = PaymentMethod.CREDIT_CARD

        elif scenario == FraudScenario.VELOCITY_ATTACK:
            # Small or medium rapid test transaction
            amount = round(self.rng.uniform(50.0, 450.0), 2)

        payload = TransactionPayload(
            transaction_id=transaction_id,
            timestamp=timestamp,
            customer_id=cust.customer_id,
            merchant_id=merch_id,
            amount=amount,
            currency="INR",
            country=country,
            city=city,
            lat=lat,
            lon=lon,
            device_id=device_id,
            payment_method=payment_method,
            ip_address=f"103.{self.rng.randint(1,254)}.{self.rng.randint(1,254)}.{self.rng.randint(1,254)}",
            merchant_category=merch.category,
            is_fraud=is_fraud,
            scenario=scenario,
        )

        # Track last transaction for customer
        self.last_customer_txn[cust.customer_id] = {
            "timestamp": timestamp,
            "lat": lat,
            "lon": lon,
            "city": city,
            "country": country,
            "amount": amount,
        }

        return payload

    def generate_stream(
        self,
        start_time: datetime,
        num_transactions: int = 10000,
        fraud_ratio: float = 0.015,
        avg_seconds_between_txns: float = 10.0,
    ) -> List[TransactionPayload]:
        """Generates a chronologically strictly ordered list of transactions."""
        if not self.customers:
            self.generate_population()

        transactions: List[TransactionPayload] = []
        current_time = start_time
        fraud_scenarios_pool = [
            FraudScenario.HIGH_VALUE_ANOMALY,
            FraudScenario.VELOCITY_ATTACK,
            FraudScenario.NEW_COUNTRY,
            FraudScenario.NEW_DEVICE,
            FraudScenario.IMPOSSIBLE_TRAVEL,
            FraudScenario.DEVICE_SHARING,
            FraudScenario.MERCHANT_ANOMALY,
            FraudScenario.ACCOUNT_TAKEOVER,
        ]

        i = 1
        while len(transactions) < num_transactions:
            # Advance time (diurnal Poisson rate)
            hour = current_time.hour
            # Lower activity between 1 AM and 6 AM
            hour_factor = 0.3 if 1 <= hour <= 6 else 1.2
            delta_seconds = self.rng.expovariate(1.0 / (avg_seconds_between_txns / hour_factor))
            current_time += timedelta(seconds=max(0.5, delta_seconds))

            # Determine whether this transaction is fraud
            is_fraud = self.rng.random() < fraud_ratio
            if is_fraud:
                scenario = self.rng.choice(fraud_scenarios_pool)
                # If velocity attack, burst 3-5 txns within 30 seconds
                if scenario == FraudScenario.VELOCITY_ATTACK:
                    target_cust = self.rng.choice(list(self.customers.values()))
                    burst_count = self.rng.randint(3, 5)
                    for _ in range(burst_count):
                        if len(transactions) >= num_transactions:
                            break
                        burst_time = current_time + timedelta(seconds=self.rng.uniform(1.0, 15.0))
                        txn = self.generate_single_transaction(
                            transaction_id=f"TXN-{i:07d}",
                            timestamp=burst_time,
                            customer_id=target_cust.customer_id,
                            force_scenario=FraudScenario.VELOCITY_ATTACK,
                        )
                        transactions.append(txn)
                        i += 1
                    current_time += timedelta(seconds=20.0)
                    continue
                else:
                    txn = self.generate_single_transaction(
                        transaction_id=f"TXN-{i:07d}",
                        timestamp=current_time,
                        force_scenario=scenario,
                    )
            else:
                txn = self.generate_single_transaction(
                    transaction_id=f"TXN-{i:07d}",
                    timestamp=current_time,
                    force_scenario=FraudScenario.NORMAL,
                )

            transactions.append(txn)
            i += 1

        # Strict sort by timestamp to guarantee chronological order
        transactions.sort(key=lambda x: x.timestamp)
        return transactions

    def to_dataframe(self, transactions: List[TransactionPayload]) -> pd.DataFrame:
        """Converts list of transactions to a clean Pandas DataFrame."""
        records = [txn.model_dump() for txn in transactions]
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.sort_values(by="timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
