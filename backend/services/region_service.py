from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.models import Region
from backend.models.schemas import RegionCreate
from database.session import Base, engine, SessionLocal
from backend.utils.logger import logger

# Initial configured regions for AirGuard AI
DEFAULT_REGIONS = [
    {
        "name": "Chennai",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "state": "Tamil Nadu",
        "country": "India"
    },
    {
        "name": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "state": "Karnataka",
        "country": "India"
    },
    {
        "name": "Hyderabad",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "state": "Telangana",
        "country": "India"
    },
    {
        "name": "Mumbai",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "state": "Maharashtra",
        "country": "India"
    },
    {
        "name": "Delhi",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "state": "Delhi",
        "country": "India"
    }
]


def init_db_and_seed():
    """
    Creates database tables if they do not exist, syncs columns, and seeds initial regions idempotently.
    """
    try:
        # Create all tables defined in Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully.")

        # Ensure schema backward-compatibility for SQLite
        with engine.connect() as conn:
            from sqlalchemy import text
            for table in ["air_quality_observations", "weather_observations"]:
                try:
                    res = conn.execute(text(f"PRAGMA table_info({table})"))
                    cols = [row[1] for row in res.fetchall()]
                    if "created_at" not in cols:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN created_at TIMESTAMP"))
                        conn.commit()
                    if table == "weather_observations" and "source" not in cols:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN source VARCHAR(100) DEFAULT 'Open-Meteo'"))
                        conn.commit()
                except Exception as ex:
                    logger.debug(f"Schema column check notice on {table}: {ex}")

            # Check alerts table for Phase 6 columns
            try:
                res = conn.execute(text("PRAGMA table_info(alerts)"))
                alert_cols = [row[1] for row in res.fetchall()]
                if alert_cols:
                    if "title" not in alert_cols:
                        conn.execute(text("ALTER TABLE alerts ADD COLUMN title VARCHAR(200)"))
                    if "created_at" not in alert_cols:
                        conn.execute(text("ALTER TABLE alerts ADD COLUMN created_at TIMESTAMP"))
                    if "read_at" not in alert_cols:
                        conn.execute(text("ALTER TABLE alerts ADD COLUMN read_at TIMESTAMP"))
                    if "acknowledged_at" not in alert_cols:
                        conn.execute(text("ALTER TABLE alerts ADD COLUMN acknowledged_at TIMESTAMP"))
                    if "dedupe_key" not in alert_cols:
                        conn.execute(text("ALTER TABLE alerts ADD COLUMN dedupe_key VARCHAR(150)"))
                    if "expires_at" not in alert_cols:
                        conn.execute(text("ALTER TABLE alerts ADD COLUMN expires_at TIMESTAMP"))
                    conn.commit()
            except Exception as ex:
                logger.debug(f"Schema column check notice on alerts: {ex}")

        db = SessionLocal()
        try:
            existing_count = db.query(Region).count()
            if existing_count == 0:
                logger.info("Seeding initial reference regions...")
                for item in DEFAULT_REGIONS:
                    region = Region(
                        name=item["name"],
                        latitude=item["latitude"],
                        longitude=item["longitude"],
                        state=item["state"],
                        country=item["country"],
                        is_active=True
                    )
                    db.add(region)
                db.commit()
                logger.info(f"Seeded {len(DEFAULT_REGIONS)} regions successfully.")
            else:
                logger.info(f"Database already contains {existing_count} regions. Skipping seed.")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error during database initialization/seeding: {e}")
        raise


def get_all_regions(db: Session, active_only: bool = True, only_active: Optional[bool] = None) -> List[Region]:
    """Retrieves all monitored regions from the database."""
    if only_active is not None:
        active_only = only_active
    query = db.query(Region)
    if active_only:
        query = query.filter(Region.is_active == True)
    return query.order_by(Region.name.asc()).all()


def get_region_by_id(db: Session, region_id: int) -> Optional[Region]:
    """Retrieves a specific region by its unique ID."""
    return db.query(Region).filter(Region.id == region_id).first()


def get_region_by_name(db: Session, name: str) -> Optional[Region]:
    """Retrieves a specific region by its name (case-insensitive)."""
    return db.query(Region).filter(Region.name.ilike(name.strip())).first()


def get_region_by_identifier(db: Session, identifier: str) -> Optional[Region]:
    """
    Retrieves a region by either its integer ID or its name string.
    """
    clean_id = str(identifier).strip()
    if clean_id.isdigit():
        region = get_region_by_id(db, int(clean_id))
        if region:
            return region
    return get_region_by_name(db, clean_id)


def create_region(db: Session, region_data: RegionCreate) -> Region:
    """Adds a new region to the monitored region registry."""
    existing = db.query(Region).filter(Region.name.ilike(region_data.name)).first()
    if existing:
        raise ValueError(f"Region '{region_data.name}' already exists.")

    region = Region(
        name=region_data.name,
        latitude=region_data.latitude,
        longitude=region_data.longitude,
        state=region_data.state,
        country=region_data.country,
        is_active=region_data.is_active
    )
    db.add(region)
    db.commit()
    db.refresh(region)
    logger.info(f"Created new region: {region.name} (ID: {region.id})")
    return region
