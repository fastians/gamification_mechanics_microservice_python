# quest_processing_service.py

import sqlite3
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import requests
import logging
import re

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_SERVICE_ADD_DIAMONDS_URL = "http://api_gateway:8000/add-diamonds/{user_id}/"
AUTH_SERVICE_ADD_GOLD_URL = "http://api_gateway:8000/add-gold/{user_id}/"
QUEST_CATALOG_SERVICE_URL = "http://api_gateway:8000"


def get_db():
    conn = sqlite3.connect("quest_processing.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect("quest_processing.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS User_Quest_Rewards (
            user_id INTEGER,
            quest_id INTEGER,
            status TEXT NOT NULL, -- "in_progress", "completed", "claimed"
            progress INTEGER NOT NULL DEFAULT 0,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, quest_id)
        );
        """
    )
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")


init_db()


class AssignQuest(BaseModel):
    user_id: int
    quest_id: int


class UserQuestReward(BaseModel):
    user_id: int
    quest_id: int
    status: str
    progress: int
    date: str  # ISO format


class TrackSignIn(BaseModel):
    user_id: int


class ClaimQuest(BaseModel):
    user_id: int
    quest_id: int


def get_quest_details(quest_id: int):
    """Fetches quest details from the Quest Catalog Service."""
    try:
        response = requests.get(f"{QUEST_CATALOG_SERVICE_URL}/quests/{quest_id}/")
        if response.status_code == 200:
            logger.info(f"Fetched details for quest_id {quest_id}.")
            return response.json()
        else:
            logger.error(
                f"Failed to fetch quest {quest_id}: {response.status_code} {response.text}"
            )
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Quest Catalog Service: {e}")
        return None


def get_all_quests():
    try:
        response = requests.get(f"{QUEST_CATALOG_SERVICE_URL}/quests/")
        if response.status_code == 200:
            quests = response.json()
            logger.info(f"Fetched {len(quests)} quests successfully.")
            return quests
        else:
            logger.error(
                f"Failed to fetch quests: {response.status_code} {response.text}"
            )
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Quest Catalog Service: {e}")
        return []


def get_reward_details(reward_id: int):
    try:
        response = requests.get(f"{QUEST_CATALOG_SERVICE_URL}/rewards/{reward_id}/")
        if response.status_code == 200:
            logger.info(f"Fetched details for reward_id {reward_id}.")
            return response.json()
        else:
            logger.error(
                f"Failed to fetch reward {reward_id}: {response.status_code} {response.text}"
            )
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Quest Catalog Service: {e}")
        return None


def reward_user(user_id: int, qty: int, item: str):
    try:
        if item.lower() == "diamond":
            url = AUTH_SERVICE_ADD_DIAMONDS_URL.format(user_id=user_id)
            payload = {"diamonds": qty}
        elif item.lower() == "gold":
            url = AUTH_SERVICE_ADD_GOLD_URL.format(user_id=user_id)
            payload = {"gold": qty}
        else:
            logger.warning(f"Unknown reward item '{item}' for user {user_id}.")
            return
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info(f"Successfully added {qty} {item} to user {user_id}.")
        else:
            logger.error(
                f"Failed to add {item} to user {user_id}: {response.status_code} {response.text}"
            )
    except Exception as e:
        logger.error(f"Exception while rewarding user {user_id}: {e}")


@app.post("/assign-quest/")
def assign_quest(assign_quest: AssignQuest, db: sqlite3.Connection = Depends(get_db)):
    """
    Assigns a quest to a user if duplication limits allow.
    """
    try:
        # Fetch quest details to verify existence and duplication limits
        quest = get_quest_details(assign_quest.quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")

        duplication_limit = quest.get("duplication", 1)

        cursor = db.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as count FROM User_Quest_Rewards
            WHERE user_id = ? AND quest_id = ?
            """,
            (assign_quest.user_id, assign_quest.quest_id),
        )
        result = cursor.fetchone()
        current_count = result["count"] if result else 0

        if current_count >= duplication_limit:
            raise HTTPException(
                status_code=400, detail="Quest duplication limit reached for user"
            )

        # Assign the quest
        cursor.execute(
            """
            INSERT INTO User_Quest_Rewards (user_id, quest_id, status, progress)
            VALUES (?, ?, ?, ?)
            """,
            (assign_quest.user_id, assign_quest.quest_id, "in_progress", 0),
        )
        db.commit()
        logger.info(
            f"Assigned quest {assign_quest.quest_id} to user {assign_quest.user_id}."
        )
        return {"message": "Quest assigned successfully"}
    except HTTPException as he:
        logger.error(f"HTTPException: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Error assigning quest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user-quests/{user_id}/", response_model=List[UserQuestReward])
def get_user_quests(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieves all quests assigned to a user.
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT quest_id, status, progress, date FROM User_Quest_Rewards WHERE user_id = ?
            """,
            (user_id,),
        )
        user_quests = cursor.fetchall()
        return [
            UserQuestReward(
                user_id=user_id,
                quest_id=quest["quest_id"],
                status=quest["status"],
                progress=quest["progress"],
                date=quest["date"],
            )
            for quest in user_quests
        ]
    except Exception as e:
        logger.error(f"Error fetching user quests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/complete-quest/")
def complete_quest(assign_quest: AssignQuest, db: sqlite3.Connection = Depends(get_db)):
    """
    Marks a quest as completed or claimed based on auto_claim settings.
    """
    try:
        # Fetch quest details
        quest = get_quest_details(assign_quest.quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")

        cursor = db.cursor()
        cursor.execute(
            """
            SELECT status, progress FROM User_Quest_Rewards
            WHERE user_id = ? AND quest_id = ?
            """,
            (assign_quest.user_id, assign_quest.quest_id),
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Quest not assigned to user")

        current_status = result["status"]
        current_progress = result["progress"]

        if current_status == "claimed":
            raise HTTPException(status_code=400, detail="Quest already claimed")
        if current_status == "completed":
            if not quest.get("auto_claim", False):
                # Awaiting manual claim
                raise HTTPException(
                    status_code=400,
                    detail="Quest already completed. Please claim your reward.",
                )
            else:
                # Auto-claimed quests should already be "claimed"
                raise HTTPException(status_code=400, detail="Quest already claimed.")
        # Determine if quest completion criteria are met
        if current_progress >= quest["streak"]:
            if quest["auto_claim"]:
                # Automatically claim the quest and grant reward
                cursor.execute(
                    """
                    UPDATE User_Quest_Rewards
                    SET status = ?, progress = ?
                    WHERE user_id = ? AND quest_id = ?
                    """,
                    (
                        "claimed",
                        quest["streak"],
                        assign_quest.user_id,
                        assign_quest.quest_id,
                    ),
                )
                db.commit()
                logger.info(
                    f"Quest {assign_quest.quest_id} for user {assign_quest.user_id} auto-claimed."
                )
                # Fetch reward details
                reward = get_reward_details(quest["reward_id"])
                if reward:
                    reward_user(
                        assign_quest.user_id,
                        reward["reward_qty"],
                        reward["reward_item"],
                    )
                    return {"message": "Quest completed and reward granted."}
                else:
                    raise HTTPException(
                        status_code=500, detail="Reward details not found."
                    )
            else:
                # Mark quest as completed, awaiting manual claim
                cursor.execute(
                    """
                    UPDATE User_Quest_Rewards
                    SET status = ?
                    WHERE user_id = ? AND quest_id = ?
                    """,
                    ("completed", assign_quest.user_id, assign_quest.quest_id),
                )
                db.commit()
                logger.info(
                    f"Quest {assign_quest.quest_id} for user {assign_quest.user_id} marked as completed."
                )
                return {"message": "Quest completed. Please claim your reward."}
        else:
            raise HTTPException(status_code=400, detail="Quest not yet completed.")

    except HTTPException as he:
        logger.error(f"HTTPException: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Error completing quest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/track-sign-in/")
def track_sign_in(data: TrackSignIn, db: sqlite3.Connection = Depends(get_db)):
    user_id = data.user_id
    try:
        all_quests = get_all_quests()
        if not all_quests:
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch quests from Quest Catalog Service",
            )

        logger.info(f"All quests fetched: {all_quests}")

        messages = []
        cursor = db.cursor()

        for quest in all_quests:
            quest_id = quest["quest_id"]
            streak_required = quest["streak"]
            auto_claim = quest["auto_claim"]
            duplication_limit = quest.get("duplication", 1)
            reward_id = quest["reward_id"]

            # Fetch current progress and status
            cursor.execute(
                """
                SELECT status, progress FROM User_Quest_Rewards
                WHERE user_id = ? AND quest_id = ?
                """,
                (user_id, quest_id),
            )
            result = cursor.fetchone()

            if result:
                current_status = result["status"]
                current_progress = result["progress"]
            else:
                current_status = None
                current_progress = 0

            if current_status == "claimed":
                messages.append(f"Quest '{quest['name']}' already claimed.")
                continue

            if result:
                # Quest is already assigned, increment progress
                new_progress = current_progress + 1
                if new_progress >= streak_required:
                    if auto_claim:
                        # Automatically claim the quest and grant reward
                        cursor.execute(
                            """
                            UPDATE User_Quest_Rewards
                            SET status = ?, progress = ?
                            WHERE user_id = ? AND quest_id = ?
                            """,
                            ("claimed", streak_required, user_id, quest_id),
                        )
                        db.commit()
                        logger.info(
                            f"Quest {quest_id} for user {user_id} auto-claimed."
                        )
                        # Fetch reward details
                        reward = get_reward_details(reward_id)
                        if reward:
                            reward_user(
                                user_id, reward["reward_qty"], reward["reward_item"]
                            )
                            messages.append(
                                f"Quest '{quest['name']}' completed and reward granted."
                            )
                        else:
                            messages.append(
                                f"Quest '{quest['name']}' completed but failed to grant reward."
                            )
                    else:
                        # Mark quest as completed, awaiting manual claim
                        cursor.execute(
                            """
                            UPDATE User_Quest_Rewards
                            SET status = ?
                            WHERE user_id = ? AND quest_id = ?
                            """,
                            ("completed", user_id, quest_id),
                        )
                        db.commit()
                        logger.info(
                            f"Quest {quest_id} for user {user_id} marked as completed."
                        )
                        messages.append(
                            f"Quest '{quest['name']}' completed. Please claim your reward."
                        )
                else:
                    # Update progress
                    cursor.execute(
                        """
                        UPDATE User_Quest_Rewards
                        SET progress = ?
                        WHERE user_id = ? AND quest_id = ?
                        """,
                        (new_progress, user_id, quest_id),
                    )
                    db.commit()
                    logger.info(
                        f"Quest {quest_id} for user {user_id} progress updated to {new_progress}."
                    )
                    messages.append(
                        f"Progress for quest '{quest['name']}': {new_progress}/{streak_required}"
                    )
            else:
                # Quest not assigned yet, check duplication limit
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM User_Quest_Rewards
                    WHERE user_id = ? AND quest_id = ?
                    """,
                    (user_id, quest_id),
                )
                count_result = cursor.fetchone()
                current_count = count_result["count"] if count_result else 0

                if current_count >= duplication_limit:
                    messages.append(
                        f"Quest '{quest['name']}' duplication limit reached."
                    )
                    continue

                # Assign quest with initial progress of 1
                cursor.execute(
                    """
                    INSERT INTO User_Quest_Rewards (user_id, quest_id, status, progress)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, quest_id, "in_progress", 1),
                )
                db.commit()
                logger.info(
                    f"Assigned quest {quest_id} to user {user_id}. Progress set to 1."
                )
                messages.append(
                    f"Progress for quest '{quest['name']}': 1/{streak_required}"
                )

        return {"messages": messages}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/claim-quest/")
def claim_quest(assign_quest: AssignQuest, db: sqlite3.Connection = Depends(get_db)):
    """
    Allows users to manually claim rewards for quests that require manual claiming.
    """
    try:
        # Fetch quest details
        quest = get_quest_details(assign_quest.quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")

        cursor = db.cursor()
        cursor.execute(
            """
            SELECT status, progress FROM User_Quest_Rewards
            WHERE user_id = ? AND quest_id = ?
            """,
            (assign_quest.user_id, assign_quest.quest_id),
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Quest not assigned to user")

        current_status = result["status"]
        current_progress = result["progress"]

        if current_status == "claimed":
            raise HTTPException(status_code=400, detail="Quest already claimed")
        if current_status != "completed":
            raise HTTPException(status_code=400, detail="Quest not yet completed")

        # Update status to "claimed"
        cursor.execute(
            """
            UPDATE User_Quest_Rewards
            SET status = ?
            WHERE user_id = ? AND quest_id = ?
            """,
            ("claimed", assign_quest.user_id, assign_quest.quest_id),
        )
        db.commit()
        logger.info(
            f"Quest {assign_quest.quest_id} for user {assign_quest.user_id} claimed."
        )

        # Fetch reward details
        reward = get_reward_details(quest["reward_id"])
        if reward:
            reward_user(
                assign_quest.user_id, reward["reward_qty"], reward["reward_item"]
            )
            return {"message": "Quest claimed and reward granted."}
        else:
            raise HTTPException(status_code=500, detail="Reward details not found.")

    except HTTPException as he:
        logger.error(f"HTTPException: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Error claiming quest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
