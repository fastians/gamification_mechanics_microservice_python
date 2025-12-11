"""
Quest Catalog Service - Quest and Reward Management
Manages quest and reward catalog for the gamification system
"""

import sqlite3
import logging
from typing import List, Optional
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DATABASE_PATH = "quest_catalog.db"
VALID_REWARD_ITEMS = ["gold", "diamond"]

app = FastAPI(
    title="Quest Catalog Service",
    description="Manages quests and rewards catalog",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Models
class RewardBase(BaseModel):
    reward_name: str = Field(..., min_length=1, max_length=100)
    reward_item: str = Field(..., min_length=1, max_length=50)
    reward_qty: int = Field(..., gt=0, description="Reward quantity must be positive")

    @validator('reward_item')
    def validate_reward_item(cls, v):
        if v.lower() not in VALID_REWARD_ITEMS:
            raise ValueError(f'Reward item must be one of: {", ".join(VALID_REWARD_ITEMS)}')
        return v.lower()


class RewardCreate(RewardBase):
    pass


class Reward(RewardBase):
    reward_id: int

    class Config:
        orm_mode = True


class QuestBase(BaseModel):
    reward_id: int = Field(..., gt=0)
    auto_claim: bool = Field(..., description="Whether quest rewards are auto-claimed")
    streak: int = Field(..., gt=0, description="Number of consecutive actions required")
    duplication: int = Field(..., gt=0, description="How many times this quest can be assigned to a user")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)


class QuestCreate(QuestBase):
    pass


class QuestUpdate(BaseModel):
    reward_id: Optional[int] = Field(None, gt=0)
    auto_claim: Optional[bool] = None
    streak: Optional[int] = Field(None, gt=0)
    duplication: Optional[int] = Field(None, gt=0)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)


class Quest(QuestBase):
    quest_id: int

    class Config:
        orm_mode = True


# Database functions
@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def get_db():
    """Dependency for FastAPI endpoints"""
    with get_db_connection() as conn:
        yield conn


def init_db():
    """Initialize database schema"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            # Create Rewards table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Rewards (
                    reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reward_name TEXT NOT NULL,
                    reward_item TEXT NOT NULL,
                    reward_qty INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Create Quests table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Quests (
                    quest_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reward_id INTEGER NOT NULL,
                    auto_claim BOOLEAN NOT NULL,
                    streak INTEGER NOT NULL,
                    duplication INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (reward_id) REFERENCES Rewards(reward_id)
                );
                """
            )

            # Create indexes for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_quest_reward ON Quests(reward_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_quest_name ON Quests(name);"
            )

            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


# Health Check
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "service": "quest_catalog_service"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


# Reward Endpoints
@app.post("/rewards/", response_model=Reward, status_code=status.HTTP_201_CREATED, tags=["Rewards"])
def create_reward(reward: RewardCreate, db: sqlite3.Connection = Depends(get_db)):
    """Create a new reward"""
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO Rewards (reward_name, reward_item, reward_qty) VALUES (?, ?, ?)",
            (reward.reward_name, reward.reward_item, reward.reward_qty)
        )
        reward_id = cursor.lastrowid
        db.commit()

        logger.info(f"Created reward '{reward.reward_name}' with ID {reward_id}")

        return Reward(reward_id=reward_id, **reward.dict())

    except Exception as e:
        logger.error(f"Error creating reward: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating reward"
        )


@app.get("/rewards/", response_model=List[Reward], tags=["Rewards"])
def get_rewards(db: sqlite3.Connection = Depends(get_db)):
    """Get all rewards"""
    try:
        cursor = db.cursor()
        cursor.execute("SELECT reward_id, reward_name, reward_item, reward_qty FROM Rewards")
        rewards = cursor.fetchall()

        return [Reward(**dict(r)) for r in rewards]

    except Exception as e:
        logger.error(f"Error fetching rewards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching rewards"
        )


@app.get("/rewards/{reward_id}/", response_model=Reward, tags=["Rewards"])
def get_reward(reward_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Get a specific reward by ID"""
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT reward_id, reward_name, reward_item, reward_qty FROM Rewards WHERE reward_id = ?",
            (reward_id,)
        )
        reward = cursor.fetchone()

        if not reward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reward with ID {reward_id} not found"
            )

        return Reward(**dict(reward))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reward {reward_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching reward"
        )


@app.put("/rewards/{reward_id}/", response_model=Reward, tags=["Rewards"])
def update_reward(
    reward_id: int,
    reward: RewardCreate,
    db: sqlite3.Connection = Depends(get_db)
):
    """Update an existing reward"""
    try:
        cursor = db.cursor()

        # Check if reward exists
        cursor.execute("SELECT reward_id FROM Rewards WHERE reward_id = ?", (reward_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reward with ID {reward_id} not found"
            )

        # Update reward
        cursor.execute(
            """
            UPDATE Rewards
            SET reward_name = ?, reward_item = ?, reward_qty = ?
            WHERE reward_id = ?
            """,
            (reward.reward_name, reward.reward_item, reward.reward_qty, reward_id)
        )
        db.commit()

        logger.info(f"Updated reward ID {reward_id}")

        return Reward(reward_id=reward_id, **reward.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reward {reward_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating reward"
        )


@app.delete("/rewards/{reward_id}/", tags=["Rewards"])
def delete_reward(reward_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Delete a reward"""
    try:
        cursor = db.cursor()

        # Check if reward exists
        cursor.execute("SELECT reward_id FROM Rewards WHERE reward_id = ?", (reward_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reward with ID {reward_id} not found"
            )

        # Check if reward is being used by any quest
        cursor.execute("SELECT quest_id FROM Quests WHERE reward_id = ?", (reward_id,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete reward that is linked to existing quests"
            )

        cursor.execute("DELETE FROM Rewards WHERE reward_id = ?", (reward_id,))
        db.commit()

        logger.info(f"Deleted reward ID {reward_id}")

        return {"message": "Reward deleted successfully", "reward_id": reward_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reward {reward_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting reward"
        )


# Quest Endpoints
@app.post("/quests/", response_model=Quest, status_code=status.HTTP_201_CREATED, tags=["Quests"])
def create_quest(quest: QuestCreate, db: sqlite3.Connection = Depends(get_db)):
    """Create a new quest"""
    try:
        cursor = db.cursor()

        # Verify that reward_id exists
        cursor.execute("SELECT reward_id FROM Rewards WHERE reward_id = ?", (quest.reward_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reward with ID {quest.reward_id} not found"
            )

        cursor.execute(
            """
            INSERT INTO Quests (reward_id, auto_claim, streak, duplication, name, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                quest.reward_id,
                quest.auto_claim,
                quest.streak,
                quest.duplication,
                quest.name,
                quest.description
            )
        )
        quest_id = cursor.lastrowid
        db.commit()

        logger.info(f"Created quest '{quest.name}' with ID {quest_id}")

        return Quest(quest_id=quest_id, **quest.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating quest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating quest"
        )


@app.get("/quests/", response_model=List[Quest], tags=["Quests"])
def get_quests(db: sqlite3.Connection = Depends(get_db)):
    """Get all quests"""
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT quest_id, reward_id, auto_claim, streak, duplication, name, description FROM Quests"
        )
        quests = cursor.fetchall()

        return [Quest(**dict(q)) for q in quests]

    except Exception as e:
        logger.error(f"Error fetching quests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching quests"
        )


@app.get("/quests/{quest_id}/", response_model=Quest, tags=["Quests"])
def get_quest(quest_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Get a specific quest by ID"""
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT quest_id, reward_id, auto_claim, streak, duplication, name, description
            FROM Quests WHERE quest_id = ?
            """,
            (quest_id,)
        )
        quest = cursor.fetchone()

        if not quest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quest with ID {quest_id} not found"
            )

        return Quest(**dict(quest))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quest {quest_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching quest"
        )


@app.put("/quests/{quest_id}/", response_model=Quest, tags=["Quests"])
def update_quest(
    quest_id: int,
    quest: QuestUpdate,
    db: sqlite3.Connection = Depends(get_db)
):
    """Update an existing quest"""
    try:
        cursor = db.cursor()

        # Check if quest exists
        cursor.execute(
            """
            SELECT quest_id, reward_id, auto_claim, streak, duplication, name, description
            FROM Quests WHERE quest_id = ?
            """,
            (quest_id,)
        )
        existing_quest = cursor.fetchone()

        if not existing_quest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quest with ID {quest_id} not found"
            )

        # Get update data (only provided fields)
        update_data = quest.dict(exclude_unset=True)

        # If reward_id is being updated, verify it exists
        if "reward_id" in update_data:
            cursor.execute(
                "SELECT reward_id FROM Rewards WHERE reward_id = ?",
                (update_data["reward_id"],)
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Reward with ID {update_data['reward_id']} not found"
                )

        if update_data:
            # Build dynamic UPDATE query
            set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
            values = list(update_data.values()) + [quest_id]

            cursor.execute(
                f"UPDATE Quests SET {set_clause} WHERE quest_id = ?",
                values
            )
            db.commit()

            logger.info(f"Updated quest ID {quest_id}")

        # Fetch updated quest
        cursor.execute(
            """
            SELECT quest_id, reward_id, auto_claim, streak, duplication, name, description
            FROM Quests WHERE quest_id = ?
            """,
            (quest_id,)
        )
        updated_quest = cursor.fetchone()

        return Quest(**dict(updated_quest))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating quest {quest_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating quest"
        )


@app.delete("/quests/{quest_id}/", tags=["Quests"])
def delete_quest(quest_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Delete a quest"""
    try:
        cursor = db.cursor()

        # Check if quest exists
        cursor.execute("SELECT quest_id FROM Quests WHERE quest_id = ?", (quest_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quest with ID {quest_id} not found"
            )

        cursor.execute("DELETE FROM Quests WHERE quest_id = ?", (quest_id,))
        db.commit()

        logger.info(f"Deleted quest ID {quest_id}")

        return {"message": "Quest deleted successfully", "quest_id": quest_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting quest {quest_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting quest"
        )


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when service starts"""
    logger.info("Starting Quest Catalog Service...")
    init_db()
    logger.info("Quest Catalog Service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Quest Catalog Service...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
