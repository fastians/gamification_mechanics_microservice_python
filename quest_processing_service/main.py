"""
Quest Processing Service - Quest Assignment and Progress Tracking
Handles quest assignments, progress tracking, and reward claiming
"""

import sqlite3
import logging
from typing import List
from contextlib import contextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
AUTH_SERVICE_ADD_DIAMONDS_URL = "http://auth_service:8001/add-diamonds/{user_id}"
AUTH_SERVICE_ADD_GOLD_URL = "http://auth_service:8001/add-gold/{user_id}"
QUEST_CATALOG_SERVICE_URL = "http://quest_catalog_service:8002"
DATABASE_PATH = "quest_processing.db"
REQUEST_TIMEOUT = 5

app = FastAPI(
    title="Quest Processing Service",
    description="Handles quest assignments, progress tracking, and rewards",
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
class AssignQuest(BaseModel):
    user_id: int = Field(..., gt=0)
    quest_id: int = Field(..., gt=0)


class UserQuestReward(BaseModel):
    user_id: int
    quest_id: int
    status: str
    progress: int
    date: str


class TrackSignIn(BaseModel):
    user_id: int = Field(..., gt=0)


class ClaimQuest(BaseModel):
    user_id: int = Field(..., gt=0)
    quest_id: int = Field(..., gt=0)


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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS User_Quest_Rewards (
                    user_id INTEGER NOT NULL,
                    quest_id INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('in_progress', 'completed', 'claimed')),
                    progress INTEGER NOT NULL DEFAULT 0,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, quest_id)
                );
                """
            )

            # Create indexes for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_quests ON User_Quest_Rewards(user_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_quest_users ON User_Quest_Rewards(quest_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_status ON User_Quest_Rewards(status);"
            )

            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


# External Service Calls
def get_quest_details(quest_id: int):
    """Fetch quest details from Quest Catalog Service"""
    try:
        response = requests.get(
            f"{QUEST_CATALOG_SERVICE_URL}/quests/{quest_id}/",
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch quest {quest_id}: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching quest {quest_id}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Quest Catalog Service: {e}")
        return None


def get_all_quests():
    """Fetch all quests from Quest Catalog Service"""
    try:
        response = requests.get(
            f"{QUEST_CATALOG_SERVICE_URL}/quests/",
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch quests: {response.status_code}")
            return []
    except requests.exceptions.Timeout:
        logger.error("Timeout fetching quests")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Quest Catalog Service: {e}")
        return []


def get_reward_details(reward_id: int):
    """Fetch reward details from Quest Catalog Service"""
    try:
        response = requests.get(
            f"{QUEST_CATALOG_SERVICE_URL}/rewards/{reward_id}/",
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch reward {reward_id}: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching reward {reward_id}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Quest Catalog Service: {e}")
        return None


def reward_user(user_id: int, qty: int, item: str) -> bool:
    """Add reward to user account via Auth Service"""
    try:
        if item.lower() == "diamond":
            url = AUTH_SERVICE_ADD_DIAMONDS_URL.format(user_id=user_id)
            payload = {"diamonds": qty}
        elif item.lower() == "gold":
            url = AUTH_SERVICE_ADD_GOLD_URL.format(user_id=user_id)
            payload = {"gold": qty}
        else:
            logger.warning(f"Unknown reward item '{item}' for user {user_id}")
            return False

        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            logger.info(f"Successfully added {qty} {item} to user {user_id}")
            return True
        else:
            logger.error(
                f"Failed to add {item} to user {user_id}: "
                f"{response.status_code} {response.text}"
            )
            return False

    except requests.exceptions.Timeout:
        logger.error(f"Timeout rewarding user {user_id}")
        return False
    except Exception as e:
        logger.error(f"Exception while rewarding user {user_id}: {e}")
        return False


# Health Check
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "service": "quest_processing_service"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


# Quest Assignment Endpoints
@app.post("/assign-quest/", tags=["Quest Management"])
def assign_quest(assign_quest: AssignQuest, db: sqlite3.Connection = Depends(get_db)):
    """
    Manually assign a quest to a user
    - Checks duplication limits
    - Creates quest assignment in in_progress status
    """
    try:
        # Fetch quest details
        quest = get_quest_details(assign_quest.quest_id)
        if not quest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quest with ID {assign_quest.quest_id} not found"
            )

        duplication_limit = quest.get("duplication", 1)
        cursor = db.cursor()

        # Check current assignment count
        cursor.execute(
            """
            SELECT COUNT(*) as count FROM User_Quest_Rewards
            WHERE user_id = ? AND quest_id = ?
            """,
            (assign_quest.user_id, assign_quest.quest_id)
        )
        result = cursor.fetchone()
        current_count = result["count"] if result else 0

        if current_count >= duplication_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quest duplication limit reached for this user"
            )

        # Assign the quest
        cursor.execute(
            """
            INSERT INTO User_Quest_Rewards (user_id, quest_id, status, progress)
            VALUES (?, ?, ?, ?)
            """,
            (assign_quest.user_id, assign_quest.quest_id, "in_progress", 0)
        )
        db.commit()

        logger.info(f"Assigned quest {assign_quest.quest_id} to user {assign_quest.user_id}")

        return {
            "message": "Quest assigned successfully",
            "user_id": assign_quest.user_id,
            "quest_id": assign_quest.quest_id,
            "status": "in_progress",
            "progress": 0
        }

    except HTTPException:
        raise
    except sqlite3.IntegrityError:
        logger.warning(
            f"Quest {assign_quest.quest_id} already assigned to user {assign_quest.user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quest already assigned to this user"
        )
    except Exception as e:
        logger.error(f"Error assigning quest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error assigning quest"
        )


@app.get("/user-quests/{user_id}/", response_model=List[UserQuestReward], tags=["Quest Management"])
def get_user_quests(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Get all quests assigned to a specific user"""
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT quest_id, status, progress, date
            FROM User_Quest_Rewards
            WHERE user_id = ?
            ORDER BY date DESC
            """,
            (user_id,)
        )
        user_quests = cursor.fetchall()

        return [
            UserQuestReward(
                user_id=user_id,
                quest_id=quest["quest_id"],
                status=quest["status"],
                progress=quest["progress"],
                date=quest["date"]
            )
            for quest in user_quests
        ]

    except Exception as e:
        logger.error(f"Error fetching user quests for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user quests"
        )


@app.post("/complete-quest/", tags=["Quest Management"])
def complete_quest(data: AssignQuest, db: sqlite3.Connection = Depends(get_db)):
    """
    Mark a quest as completed (for manual progress tracking)
    - Validates quest completion criteria
    - Handles auto-claim if enabled
    """
    try:
        # Fetch quest details
        quest = get_quest_details(data.quest_id)
        if not quest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quest with ID {data.quest_id} not found"
            )

        cursor = db.cursor()
        cursor.execute(
            """
            SELECT status, progress FROM User_Quest_Rewards
            WHERE user_id = ? AND quest_id = ?
            """,
            (data.user_id, data.quest_id)
        )
        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quest not assigned to this user"
            )

        current_status = result["status"]
        current_progress = result["progress"]

        if current_status == "claimed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quest already claimed"
            )

        if current_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quest already completed. Please claim your reward."
            )

        # Check if streak requirement met
        if current_progress >= quest["streak"]:
            if quest["auto_claim"]:
                # Auto-claim the reward
                cursor.execute(
                    """
                    UPDATE User_Quest_Rewards
                    SET status = ?, progress = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND quest_id = ?
                    """,
                    ("claimed", quest["streak"], data.user_id, data.quest_id)
                )
                db.commit()

                # Grant reward
                reward = get_reward_details(quest["reward_id"])
                if reward:
                    reward_user(data.user_id, reward["reward_qty"], reward["reward_item"])
                    logger.info(f"Quest {data.quest_id} auto-claimed for user {data.user_id}")
                    return {"message": "Quest completed and reward granted automatically"}
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Reward details not found"
                    )
            else:
                # Mark as completed for manual claim
                cursor.execute(
                    """
                    UPDATE User_Quest_Rewards
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND quest_id = ?
                    """,
                    ("completed", data.user_id, data.quest_id)
                )
                db.commit()

                logger.info(f"Quest {data.quest_id} completed for user {data.user_id}")
                return {"message": "Quest completed. Please claim your reward."}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quest not yet completed. Progress: {current_progress}/{quest['streak']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing quest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error completing quest"
        )


@app.post("/track-sign-in/", tags=["Progress Tracking"])
def track_sign_in(data: TrackSignIn, db: sqlite3.Connection = Depends(get_db)):
    """
    Track user sign-in and update all applicable quests
    - Automatically assigns quests if duplication allows
    - Updates progress for existing quests
    - Auto-claims rewards when applicable
    """
    user_id = data.user_id

    try:
        all_quests = get_all_quests()
        if not all_quests:
            logger.warning("No quests available in catalog")
            return {"messages": ["No quests available"]}

        messages = []
        cursor = db.cursor()

        for quest in all_quests:
            quest_id = quest["quest_id"]
            streak_required = quest["streak"]
            auto_claim = quest["auto_claim"]
            duplication_limit = quest.get("duplication", 1)
            reward_id = quest["reward_id"]

            # Check existing assignment
            cursor.execute(
                """
                SELECT status, progress FROM User_Quest_Rewards
                WHERE user_id = ? AND quest_id = ?
                """,
                (user_id, quest_id)
            )
            result = cursor.fetchone()

            if result:
                current_status = result["status"]
                current_progress = result["progress"]

                if current_status == "claimed":
                    continue  # Skip already claimed quests

                # Increment progress
                new_progress = current_progress + 1

                if new_progress >= streak_required:
                    if auto_claim:
                        # Auto-claim the reward
                        cursor.execute(
                            """
                            UPDATE User_Quest_Rewards
                            SET status = ?, progress = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ? AND quest_id = ?
                            """,
                            ("claimed", streak_required, user_id, quest_id)
                        )
                        db.commit()

                        # Grant reward
                        reward = get_reward_details(reward_id)
                        if reward:
                            if reward_user(user_id, reward["reward_qty"], reward["reward_item"]):
                                messages.append(
                                    f"Quest '{quest['name']}' completed and reward granted!"
                                )
                            else:
                                messages.append(
                                    f"Quest '{quest['name']}' completed but failed to grant reward"
                                )
                        else:
                            messages.append(
                                f"Quest '{quest['name']}' completed but reward not found"
                            )
                    else:
                        # Mark as completed
                        cursor.execute(
                            """
                            UPDATE User_Quest_Rewards
                            SET status = ?, progress = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ? AND quest_id = ?
                            """,
                            ("completed", new_progress, user_id, quest_id)
                        )
                        db.commit()
                        messages.append(
                            f"Quest '{quest['name']}' completed! Please claim your reward."
                        )
                else:
                    # Update progress
                    cursor.execute(
                        """
                        UPDATE User_Quest_Rewards
                        SET progress = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND quest_id = ?
                        """,
                        (new_progress, user_id, quest_id)
                    )
                    db.commit()
                    messages.append(
                        f"Progress for quest '{quest['name']}': {new_progress}/{streak_required}"
                    )
            else:
                # Quest not assigned yet - check duplication limit
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM User_Quest_Rewards
                    WHERE user_id = ? AND quest_id = ?
                    """,
                    (user_id, quest_id)
                )
                count_result = cursor.fetchone()
                current_count = count_result["count"] if count_result else 0

                if current_count >= duplication_limit:
                    continue  # Skip if duplication limit reached

                # Auto-assign quest with initial progress of 1
                cursor.execute(
                    """
                    INSERT INTO User_Quest_Rewards (user_id, quest_id, status, progress)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, quest_id, "in_progress", 1)
                )
                db.commit()
                messages.append(
                    f"Quest '{quest['name']}' assigned! Progress: 1/{streak_required}"
                )

        return {"messages": messages if messages else ["Sign-in tracked successfully"]}

    except Exception as e:
        logger.error(f"Error tracking sign-in for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error tracking sign-in"
        )


@app.post("/claim-quest/", tags=["Quest Management"])
def claim_quest(data: ClaimQuest, db: sqlite3.Connection = Depends(get_db)):
    """
    Manually claim a completed quest reward
    - Validates quest is in completed status
    - Grants reward to user
    - Updates status to claimed
    """
    try:
        # Fetch quest details
        quest = get_quest_details(data.quest_id)
        if not quest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quest with ID {data.quest_id} not found"
            )

        cursor = db.cursor()
        cursor.execute(
            """
            SELECT status, progress FROM User_Quest_Rewards
            WHERE user_id = ? AND quest_id = ?
            """,
            (data.user_id, data.quest_id)
        )
        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quest not assigned to this user"
            )

        current_status = result["status"]

        if current_status == "claimed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quest reward already claimed"
            )

        if current_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quest is not completed yet"
            )

        # Update status to claimed
        cursor.execute(
            """
            UPDATE User_Quest_Rewards
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND quest_id = ?
            """,
            ("claimed", data.user_id, data.quest_id)
        )
        db.commit()

        # Grant reward
        reward = get_reward_details(quest["reward_id"])
        if reward:
            if reward_user(data.user_id, reward["reward_qty"], reward["reward_item"]):
                logger.info(f"Quest {data.quest_id} claimed by user {data.user_id}")
                return {
                    "message": "Quest claimed and reward granted successfully",
                    "reward": {
                        "name": reward["reward_name"],
                        "item": reward["reward_item"],
                        "quantity": reward["reward_qty"]
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to grant reward"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Reward details not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming quest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error claiming quest"
        )


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when service starts"""
    logger.info("Starting Quest Processing Service...")
    init_db()
    logger.info("Quest Processing Service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Quest Processing Service...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
