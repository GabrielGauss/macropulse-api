#!/usr/bin/env python3
"""
One-off script to create an OWNER-tier API key for dashboard testing.

Run from the macropulse root directory on the server:
    python scripts/create_owner_key.py --email owner@macropulse.live

The plaintext key is printed once and never stored — save it immediately.
"""

import argparse
import asyncio
import hashlib
import secrets
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    return f"mp_{secrets.token_urlsafe(32)}"


async def main(email: str) -> None:
    from config.settings import Settings
    from database.connection import init_pool, close_pool
    from database import queries

    settings = Settings()
    await init_pool(settings.database_url)
    try:
        # Check if user already exists
        user = await queries.get_user_by_email(email)
        if not user:
            user = await queries.create_user(email=email)
            print(f"[+] Created new user: id={user['id']} email={email}")
        else:
            print(f"[~] Using existing user: id={user['id']} email={email}")

        plaintext_key = generate_api_key()
        key_prefix = plaintext_key[:12]

        await queries.create_api_key(
            user_id=user["id"],
            key_hash=hash_key(plaintext_key),
            key_prefix=key_prefix,
            tier="owner",
        )

        print()
        print("=" * 60)
        print("OWNER API KEY (save this — shown once only):")
        print()
        print(f"  {plaintext_key}")
        print()
        print(f"  Prefix : {key_prefix}")
        print(f"  Tier   : owner")
        print(f"  User   : {email}")
        print("=" * 60)
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an OWNER-tier API key")
    parser.add_argument("--email", default="owner@macropulse.live", help="Email for the owner account")
    args = parser.parse_args()
    asyncio.run(main(args.email))
