# quest_catalog_service.py

import sqlite3
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect("quest_catalog.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect("quest_catalog.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Rewards (
            reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reward_name TEXT NOT NULL,
            reward_item TEXT NOT NULL, -- "gold" or "diamond"
            reward_qty INTEGER NOT NULL
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Quests (
            quest_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reward_id INTEGER,
            auto_claim BOOLEAN NOT NULL,
            streak INTEGER NOT NULL,
            duplication INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (reward_id) REFERENCES Rewards(reward_id)
        );
        """
    )
    conn.commit()
    conn.close()


init_db()


# Pydantic Models
class RewardBase(BaseModel):
    reward_name: str
    reward_item: str
    reward_qty: int


class RewardCreate(RewardBase):
    pass


class Reward(RewardBase):
    reward_id: int

    class Config:
        orm_mode = True


class QuestBase(BaseModel):
    reward_id: int
    auto_claim: bool
    streak: int
    duplication: int
    name: str
    description: str


class QuestCreate(QuestBase):
    pass


class QuestUpdate(BaseModel):
    reward_id: Optional[int] = None
    auto_claim: Optional[bool] = None
    streak: Optional[int] = None
    duplication: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None


class Quest(QuestBase):
    quest_id: int

    class Config:
        orm_mode = True


# Reward Endpoints
@app.post("/rewards/", response_model=Reward)
def create_reward(reward: RewardCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO Rewards (reward_name, reward_item, reward_qty) VALUES (?, ?, ?)",
        (reward.reward_name, reward.reward_item, reward.reward_qty),
    )
    reward_id = cursor.lastrowid
    db.commit()
    return Reward(reward_id=reward_id, **reward.dict())


@app.get("/rewards/", response_model=List[Reward])
def get_rewards(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Rewards")
    rewards = cursor.fetchall()
    return [Reward(**dict(r)) for r in rewards]


@app.get("/rewards/{reward_id}/", response_model=Reward)
def get_reward(reward_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Rewards WHERE reward_id = ?", (reward_id,))
    reward = cursor.fetchone()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    return Reward(**dict(reward))


@app.put("/rewards/{reward_id}/", response_model=Reward)
def update_reward(
    reward_id: int, reward: RewardCreate, db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Rewards WHERE reward_id = ?", (reward_id,))
    existing_reward = cursor.fetchone()
    if not existing_reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    cursor.execute(
        """
        UPDATE Rewards
        SET reward_name = ?, reward_item = ?, reward_qty = ?
        WHERE reward_id = ?
        """,
        (reward.reward_name, reward.reward_item, reward.reward_qty, reward_id),
    )
    db.commit()
    cursor.execute("SELECT * FROM Rewards WHERE reward_id = ?", (reward_id,))
    updated_reward = cursor.fetchone()
    return Reward(**dict(updated_reward))


@app.delete("/rewards/{reward_id}/")
def delete_reward(reward_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Rewards WHERE reward_id = ?", (reward_id,))
    reward = cursor.fetchone()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    cursor.execute("DELETE FROM Rewards WHERE reward_id = ?", (reward_id,))
    db.commit()
    return {"message": "Reward deleted successfully"}


# Quest Endpoints
@app.post("/quests/", response_model=Quest)
def create_quest(quest: QuestCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    # Verify that reward_id exists
    cursor.execute("SELECT * FROM Rewards WHERE reward_id = ?", (quest.reward_id,))
    reward = cursor.fetchone()
    if not reward:
        raise HTTPException(status_code=404, detail="Associated reward not found")
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
            quest.description,
        ),
    )
    quest_id = cursor.lastrowid
    db.commit()
    return Quest(quest_id=quest_id, **quest.dict())


@app.get("/quests/", response_model=List[Quest])
def get_quests(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Quests")
    quests = cursor.fetchall()
    return [Quest(**dict(q)) for q in quests]


@app.get("/quests/{quest_id}/", response_model=Quest)
def get_quest(quest_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Quests WHERE quest_id = ?", (quest_id,))
    quest = cursor.fetchone()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return Quest(**dict(quest))


@app.put("/quests/{quest_id}/", response_model=Quest)
def update_quest(
    quest_id: int, quest: QuestUpdate, db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Quests WHERE quest_id = ?", (quest_id,))
    existing_quest = cursor.fetchone()
    if not existing_quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    update_data = quest.dict(exclude_unset=True)

    if "reward_id" in update_data:
        cursor.execute(
            "SELECT * FROM Rewards WHERE reward_id = ?", (update_data["reward_id"],)
        )
        reward = cursor.fetchone()
        if not reward:
            raise HTTPException(status_code=404, detail="Associated reward not found")

    # Build the SET part of the SQL dynamically
    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values()) + [quest_id]

    cursor.execute(
        f"""
        UPDATE Quests
        SET {set_clause}
        WHERE quest_id = ?
        """,
        values,
    )
    db.commit()
    cursor.execute("SELECT * FROM Quests WHERE quest_id = ?", (quest_id,))
    updated_quest = cursor.fetchone()
    return Quest(**dict(updated_quest))


@app.delete("/quests/{quest_id}/")
def delete_quest(quest_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Quests WHERE quest_id = ?", (quest_id,))
    quest = cursor.fetchone()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    cursor.execute("DELETE FROM Quests WHERE quest_id = ?", (quest_id,))
    db.commit()
    return {"message": "Quest deleted successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
