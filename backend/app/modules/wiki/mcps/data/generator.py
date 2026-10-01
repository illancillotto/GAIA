"""Reproducible synthetic dataset; never reads the GAIA database."""

from __future__ import annotations

import random
from uuid import NAMESPACE_URL, uuid5

GENERATOR_VERSION = "gaia-synthetic-v1"
TABLES = (
    "subjects",
    "districts",
    "parcels",
    "irrigation_accounts",
    "subject_accounts",
    "account_parcels",
    "irrigation_applications",
    "role_notices",
    "role_lines",
    "payments",
)


def record_id(seed: str, entity: str, index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"{GENERATOR_VERSION}:{seed}:{entity}:{index}"))


def base_entities(seed: str, rng: random.Random) -> dict[str, list[dict]]:
    subjects = [
        {
            "id": record_id(seed, "subjects", index),
            "subject_type": "company" if index % 5 == 0 else "person",
            "display_name": "Soggetto sintetico omonimo"
            if index < 2
            else f"Soggetto sintetico {index:04d}",
            "synthetic_identifier": f"SYN-SUBJECT-{index:04d}",
            "municipality": f"Comune sintetico {index % 4 + 1}",
            "status": "inactive" if index % 17 == 0 else "active",
        }
        for index in range(300)
    ]
    districts = [
        {
            "id": record_id(seed, "districts", index),
            "code": f"SYN-D{index + 1:02d}",
            "name": f"Distretto sintetico {index + 1}",
            "active": 1,
        }
        for index in range(12)
    ]
    parcels = [
        {
            "id": record_id(seed, "parcels", index),
            "municipality_code": f"SYN-M{index % 4 + 1:02d}",
            "sheet": str(index // 100 + 1),
            "parcel_number": f"SYN-P{index:04d}",
            "subaltern": "0",
            "district_id": districts[index % 12]["id"],
            "surface_m2": rng.randint(1000, 100000),
            "crop": ("mais", "riso", "olivo", "prato")[index % 4],
            "is_current": int(index != 0),
        }
        for index in range(1000)
    ]
    accounts = [
        {
            "id": record_id(seed, "irrigation_accounts", index),
            "account_code": f"SYN-A{index:04d}",
            "status": "closed" if index % 11 == 0 else "active",
            "campaign_year": 2024 + index % 3,
            "district_id": districts[index % 12]["id"],
            "irrigated_surface_m2": rng.randint(500, 50000),
        }
        for index in range(450)
    ]
    return {
        "subjects": subjects,
        "districts": districts,
        "parcels": parcels,
        "irrigation_accounts": accounts,
    }


def relationships(seed: str, data: dict[str, list[dict]]) -> dict[str, list[dict]]:
    subjects, accounts, parcels = data["subjects"], data["irrigation_accounts"], data["parcels"]
    subject_accounts = [
        {
            "id": record_id(seed, "subject_accounts", index),
            "subject_id": subjects[index % 300]["id"],
            "account_id": accounts[index % 450]["id"],
            "role": "holder" if index < 450 else "coholder",
        }
        for index in range(600)
    ]
    account_parcels = [
        {
            "id": record_id(seed, "account_parcels", index),
            "account_id": accounts[index % 450]["id"],
            "parcel_id": parcels[index % 1000]["id"],
            "irrigated_surface_m2": 1000 + index,
            "valid_from_year": accounts[index % 450]["campaign_year"],
            "valid_to_year": accounts[index % 450]["campaign_year"],
        }
        for index in range(1500)
    ]
    applications = [
        {
            "id": record_id(seed, "irrigation_applications", index),
            "application_code": f"SYN-APP{index:04d}",
            "account_id": accounts[index % 450]["id"],
            "campaign_year": accounts[index % 450]["campaign_year"],
            "status": ("submitted", "approved", "rejected")[index % 3],
            "submitted_at": f"{accounts[index % 450]['campaign_year']}-03-01T10:00:00+00:00",
        }
        for index in range(500)
    ]
    return {
        "subject_accounts": subject_accounts,
        "account_parcels": account_parcels,
        "irrigation_applications": applications,
    }


def financial_entities(
    seed: str, data: dict[str, list[dict]], rng: random.Random
) -> dict[str, list[dict]]:
    notices, lines, payments = [], [], []
    for index in range(800):
        notice_id = record_id(seed, "role_notices", index)
        amount = rng.randint(1000, 50000)
        mode = index % 3 if index < 750 else 0
        notices.append(
            {
                "id": notice_id,
                "notice_code": f"SYN-N{index:04d}",
                "subject_id": data["subjects"][index % 300]["id"],
                "tax_year": 2024 + index % 3,
                "account_code": data["irrigation_accounts"][index % 450]["account_code"],
                "total_amount_cents": amount,
                "status": ("unpaid", "partial", "paid")[mode],
            }
        )
        first_amount = amount // 2 if index < 700 else amount
        for portion in range(2 if index < 700 else 1):
            lines.append(
                {
                    "id": record_id(seed, "role_lines", len(lines)),
                    "notice_id": notice_id,
                    "parcel_id": data["parcels"][index % 950]["id"],
                    "tribute_code": "0648",
                    "maintenance_amount_cents": first_amount
                    if portion == 0
                    else amount - first_amount,
                    "irrigation_amount_cents": 0,
                    "institutional_amount_cents": 0,
                }
            )
        if mode:
            payments.append(
                {
                    "id": record_id(seed, "payments", len(payments)),
                    "notice_id": notice_id,
                    "paid_at": f"{2024 + index % 3}-06-01T12:00:00+00:00",
                    "amount_cents": amount // 2 if mode == 1 else amount,
                    "method": "synthetic_transfer",
                    "status": "valid",
                }
            )
    return {"role_notices": notices, "role_lines": lines, "payments": payments}


def generate_dataset(seed: str) -> dict[str, list[dict]]:
    if not isinstance(seed, str) or not 1 <= len(seed) <= 120:
        raise ValueError("Synthetic seed must contain 1 to 120 characters")
    rng = random.Random(seed)
    data = base_entities(seed, rng)
    data.update(relationships(seed, data))
    data.update(financial_entities(seed, data, rng))
    return data
