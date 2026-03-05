import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.car import CarCatalog, Perk
from app.models.stats import LifetimeStats
from app.models.track import Track
from app.models.user import User

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncSession:
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        github_id=12345,
        github_username="testuser",
        email="test@example.com",
        display_name="Test User",
        timezone="UTC",
        gas=0,
        streak=0,
    )
    db.add(user)
    db.add(LifetimeStats(id=user_id, user_id=user_id))
    await db.flush()
    return user


@pytest_asyncio.fixture
async def test_track(db: AsyncSession) -> Track:
    track = Track(
        name="Test Pass",
        slug="test-pass",
        description="A test track",
        length_days=7,
        base_seconds_per_segment=45,
        difficulty="beginner",
    )
    db.add(track)
    await db.flush()
    return track


@pytest_asyncio.fixture
async def test_perk(db: AsyncSession) -> Perk:
    perk = Perk(
        slug="smooth_line",
        name="Smooth Line",
        description="Base segment time -5%",
        effect_type="segment_time_multiplier",
        effect_value=-0.05,
    )
    db.add(perk)
    await db.flush()
    return perk


@pytest_asyncio.fixture
async def test_car(db: AsyncSession, test_perk: Perk) -> CarCatalog:
    car = CarCatalog(
        name="Test AE86",
        slug="test-ae86",
        base_model="AE86 Trueno",
        rarity="common",
        perk_id=test_perk.id,
    )
    db.add(car)
    await db.flush()
    return car
