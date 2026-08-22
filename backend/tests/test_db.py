import pytest
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import MarketSignature, DailyMarketRegime

def test_db_connection():
    db = SessionLocal()
    try:
        # Check if database can be queried
        regimes = db.query(DailyMarketRegime).all()
        signatures = db.query(MarketSignature).limit(5).all()
        
        assert len(regimes) > 0, "No daily regimes found. Seed script might have failed."
        assert len(signatures) == 5, f"Expected 5 signatures, got {len(signatures)}"
        
        # Verify columns exist and are readable
        for sig in signatures:
            assert sig.instrument is not None
            assert sig.mae_pips is not None
            assert sig.mfe_pips is not None
            
        print("Database connection and integration test passed!")
    finally:
        db.close()

if __name__ == "__main__":
    test_db_connection()
