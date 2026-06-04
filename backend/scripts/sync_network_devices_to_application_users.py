from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
import re
import unicodedata

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.application_user import ApplicationUser
from app.modules.network.models import NetworkDevice

PHONE_EXTENSION_PATTERN = re.compile(r"\bInterno\s+(\d+)\b", re.IGNORECASE)
DEVICE_PREFIX_PATTERN = re.compile(r"^(pc|nb|notebook)\s+", re.IGNORECASE)
NON_PERSON_KEYWORDS = (
    "access point",
    "router",
    "stampante",
    "printer",
    "server",
    "canon ",
    "ir-adv",
)
MANUAL_USERNAME_ALIASES = {
    "anna maria salaris": "salaris.annamaria",
    "aramu martina": "aramu.martina",
    "armas ernesto": "armas.ernesto",
    "catagna francesco": "castagna.francesco",
    "caterina ginesu": "ginesu.caterina",
    "cuccu marika": "cuccu.marika",
    "francesca manca": "manca.francesca",
    "ibba marianna": "ibba.marianna",
    "licandro angelo": "licandro.angelo",
    "alessandro porcu": "porcu.alessandro",
    "pc alessandro porcu": "porcu.alessandro",
    "pinna marina": "pinna.marina",
    "pintus sandra": "pintus.sandra",
    "tronu gianfranco": "tronu.gianfranco",
}
PLACEHOLDER_PASSWORD = "gaia-profile-placeholder"


@dataclass
class MatchCandidate:
    user_id: int
    username: str
    full_name: str | None


def normalize_text(value: str | None) -> str | None:
    if not value:
        return None
    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = " ".join(normalized.split())
    return normalized or None


def canonical_person_name(value: str | None) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    normalized = DEVICE_PREFIX_PATTERN.sub("", normalized)
    return normalized or None


def is_apparent_person(value: str | None) -> bool:
    normalized = canonical_person_name(value)
    if not normalized:
        return False
    if any(keyword in normalized for keyword in NON_PERSON_KEYWORDS):
        return False
    tokens = normalized.split()
    if len(tokens) < 2:
        return False
    return all(token.isalpha() for token in tokens)


def principal_variants(value: str | None) -> set[str]:
    normalized = canonical_person_name(value)
    if not normalized:
        return set()
    tokens = normalized.split()
    variants = {normalized}
    if len(tokens) >= 2:
        variants.add(" ".join(tokens[1:] + tokens[:1]))
        variants.add(" ".join(reversed(tokens)))
    return {item for item in variants if item}


def user_match_keys(user: ApplicationUser) -> set[str]:
    keys = set()
    keys.update(principal_variants(user.full_name))
    keys.update(principal_variants(user.username.replace(".", " ")))
    keys.update(principal_variants(user.email.split("@", 1)[0].replace(".", " ")))
    return keys


def parse_phone_extension(notes: str | None) -> str | None:
    if not notes:
        return None
    match = PHONE_EXTENSION_PATTERN.search(notes)
    if not match:
        return None
    return match.group(1)


def username_from_person_name(value: str) -> str:
    normalized = canonical_person_name(value)
    if not normalized:
        raise ValueError("Cannot build username from empty person name")
    manual = MANUAL_USERNAME_ALIASES.get(normalized)
    if manual:
        return manual
    parts = normalized.split()
    if len(parts) < 2:
        raise ValueError(f"Cannot build username from single token name: {value}")
    surname = "".join(parts[:-1]) if len(parts) > 2 else parts[0]
    given = parts[-1] if len(parts) == 2 else parts[-1]
    return f"{surname}.{given}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collega i network devices agli application_users e importa il profilo utente dai label gia presenti."
    )
    parser.add_argument("--apply", action="store_true", help="Applica le modifiche al database.")
    parser.add_argument(
        "--create-missing-users",
        action="store_true",
        help="Crea profili application_users inattivi per i nomi persona non ancora presenti.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        users = db.query(ApplicationUser).order_by(ApplicationUser.id).all()
        devices = (
            db.query(NetworkDevice)
            .filter(NetworkDevice.display_name.isnot(None))
            .order_by(NetworkDevice.id)
            .all()
        )

        def rebuild_user_keys() -> dict[str, list[MatchCandidate]]:
            mapping: dict[str, list[MatchCandidate]] = defaultdict(list)
            for current_user in users:
                for key in user_match_keys(current_user):
                    mapping[key].append(
                        MatchCandidate(
                            user_id=current_user.id,
                            username=current_user.username,
                            full_name=current_user.full_name,
                        )
                    )
            return mapping

        users_by_key = rebuild_user_keys()

        for device in devices:
            person_name = canonical_person_name(device.display_name)
            manual_username = MANUAL_USERNAME_ALIASES.get(person_name or "")
            if manual_username:
                exact_user = next((item for item in users if item.username == manual_username), None)
                if exact_user:
                    users_by_key.setdefault(person_name, []).append(
                        MatchCandidate(
                            user_id=exact_user.id,
                            username=exact_user.username,
                            full_name=exact_user.full_name,
                        )
                    )

        matched = 0
        assigned = 0
        ambiguous = 0
        unmatched = 0
        created_users = 0
        profile_updates = 0
        preview: list[dict[str, object]] = []

        for device in devices:
            key = canonical_person_name(device.display_name)
            if not key:
                continue

            candidates = users_by_key.get(key, [])
            unique_candidates = {candidate.user_id: candidate for candidate in candidates}
            if not unique_candidates and args.create_missing_users and is_apparent_person(device.display_name):
                username = username_from_person_name(device.display_name or "")
                existing = next((item for item in users if item.username == username), None)
                if existing is None:
                    email = f"{username}@users.local"
                    existing_email = next((item for item in users if item.email == email), None)
                    if existing_email is not None:
                        email = f"{username}.{existing_email.id}@users.local"

                    created_user = ApplicationUser(
                        username=username,
                        email=email,
                        full_name=" ".join(part.capitalize() for part in key.split()),
                        office_location=device.location_hint,
                        phone_extension=parse_phone_extension(device.notes),
                        password_hash=hash_password(PLACEHOLDER_PASSWORD),
                        role="viewer",
                        is_active=False,
                        module_accessi=False,
                        module_rete=False,
                        module_inventario=False,
                        module_catasto=False,
                        module_utenze=False,
                        module_operazioni=False,
                        module_riordino=False,
                        module_ruolo=False,
                        module_inaz=False,
                    )
                    db.add(created_user)
                    db.flush()
                    users.append(created_user)
                    created_users += 1
                    users_by_key = rebuild_user_keys()
                    unique_candidates = {
                        candidate.user_id: candidate
                        for candidate in users_by_key.get(key, [])
                    }
                    preview.append(
                        {
                            "device_id": device.id,
                            "ip_address": device.ip_address,
                            "device_display_name": device.display_name,
                            "status": "created_user",
                            "created_username": username,
                        }
                    )
                else:
                    users_by_key = rebuild_user_keys()
                    unique_candidates = {
                        candidate.user_id: candidate
                        for candidate in users_by_key.get(key, [])
                    }

            if len(unique_candidates) != 1:
                if unique_candidates:
                    ambiguous += 1
                    preview.append(
                        {
                            "device_id": device.id,
                            "ip_address": device.ip_address,
                            "device_display_name": device.display_name,
                            "status": "ambiguous",
                            "candidates": [
                                {"user_id": candidate.user_id, "username": candidate.username}
                                for candidate in unique_candidates.values()
                            ],
                        }
                    )
                else:
                    unmatched += 1
                continue

            candidate = next(iter(unique_candidates.values()))
            user = next(item for item in users if item.id == candidate.user_id)
            matched += 1

            changes: dict[str, object] = {}
            if device.assigned_user_id != user.id:
                changes["assigned_user_id"] = user.id
            if not user.full_name and device.display_name:
                changes["user.full_name"] = device.display_name
            if not user.office_location and device.location_hint:
                changes["user.office_location"] = device.location_hint
            phone_extension = parse_phone_extension(device.notes)
            if not user.phone_extension and phone_extension:
                changes["user.phone_extension"] = phone_extension

            if not changes:
                continue

            assigned += int("assigned_user_id" in changes)
            profile_updates += sum(1 for key_name in changes if key_name.startswith("user."))
            preview.append(
                {
                    "device_id": device.id,
                    "ip_address": device.ip_address,
                    "device_display_name": device.display_name,
                    "matched_user_id": user.id,
                    "matched_username": user.username,
                    "changes": changes,
                }
            )

            if args.apply:
                if "assigned_user_id" in changes:
                    device.assigned_user_id = user.id
                if "user.full_name" in changes:
                    user.full_name = str(changes["user.full_name"])
                if "user.office_location" in changes:
                    user.office_location = str(changes["user.office_location"])
                if "user.phone_extension" in changes:
                    user.phone_extension = str(changes["user.phone_extension"])

        print(
            json.dumps(
                {
                    "devices_with_display_name": len(devices),
                    "matched_devices": matched,
                    "assigned_devices": assigned,
                    "profile_field_updates": profile_updates,
                    "ambiguous_devices": ambiguous,
                    "unmatched_devices": unmatched,
                    "mode": "apply" if args.apply else "dry-run",
                    "created_users": created_users,
                    "preview": preview[:50],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        if args.apply:
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
