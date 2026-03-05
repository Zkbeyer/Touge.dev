"""
Seed the database with tracks, perks, cars, and cosmetics.
Run with: python seeds/seed.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal, engine, Base
from app.models.car import CarCatalog, Perk
from app.models.cosmetic import Cosmetic
from app.models.track import Track


async def load_json(filename: str) -> list:
    seeds_dir = Path(__file__).parent
    with open(seeds_dir / filename) as f:
        return json.load(f)


async def seed_tracks(db: AsyncSession) -> None:
    data = await load_json("tracks.json")
    for item in data:
        existing = await db.scalar(select(Track).where(Track.slug == item["slug"]))
        if existing:
            continue
        db.add(Track(**item))
    await db.flush()
    print(f"  Seeded {len(data)} tracks")


async def seed_perks(db: AsyncSession) -> dict[str, Perk]:
    data = await load_json("perks.json")
    perk_map: dict[str, Perk] = {}
    for item in data:
        existing = await db.scalar(select(Perk).where(Perk.slug == item["slug"]))
        if existing:
            perk_map[item["slug"]] = existing
            continue
        perk = Perk(**item)
        db.add(perk)
        await db.flush()
        perk_map[item["slug"]] = perk
    print(f"  Seeded {len(data)} perks")
    return perk_map


async def seed_cars(db: AsyncSession, perk_map: dict[str, Perk]) -> None:
    data = await load_json("cars.json")
    for item in data:
        existing = await db.scalar(select(CarCatalog).where(CarCatalog.slug == item["slug"]))
        if existing:
            continue
        perk_slug = item.pop("perk_slug", None)
        perk_id = perk_map[perk_slug].id if perk_slug and perk_slug in perk_map else None
        db.add(CarCatalog(**item, perk_id=perk_id))
    await db.flush()
    print(f"  Seeded {len(data)} cars")


async def seed_cosmetics(db: AsyncSession) -> None:
    data = await load_json("cosmetics.json")
    for item in data:
        existing = await db.scalar(select(Cosmetic).where(Cosmetic.slug == item["slug"]))
        if existing:
            continue
        db.add(Cosmetic(**item))
    await db.flush()
    print(f"  Seeded {len(data)} cosmetics")


async def main() -> None:
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Seeding database...")
    async with SessionLocal() as db:
        await seed_tracks(db)
        perk_map = await seed_perks(db)
        await seed_cars(db, perk_map)
        await seed_cosmetics(db)
        await db.commit()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
