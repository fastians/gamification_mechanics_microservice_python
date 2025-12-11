"""
Auth Service - User Authentication and Management
Handles user signup, login, and user data management
"""

import sqlite3
import hashlib
import jwt
import datetime
import logging
from typing import Optional
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
SECRET_KEY = "your_secret_key"  # TODO: Move to environment variables
QUEST_PROCESSING_SERVICE_URL = "http://quest_processing_service:8003/track-sign-in/"
DATABASE_PATH = "auth.db"
TOKEN_EXPIRY_HOURS = 24

app = FastAPI(
    title="User Authentication Service",
    description="Manages user authentication and user data",
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
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must contain only alphanumeric characters, hyphens, or underscores')
        return v.lower()


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

    @validator('username')
    def validate_username(cls, v):
        return v.lower()


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    user_id: int
    user_name: str
    gold: int
    diamond: int
    status: str


class AddDiamonds(BaseModel):
    diamonds: int = Field(..., gt=0, description="Number of diamonds to add (must be positive)")


class AddGold(BaseModel):
    gold: int = Field(..., gt=0, description="Number of gold to add (must be positive)")


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
                CREATE TABLE IF NOT EXISTS Users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    gold INTEGER DEFAULT 0,
                    diamond INTEGER DEFAULT 0,
                    status INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
                """
            )

            # Create indexes for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_name ON Users(user_name);"
            )

            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


# Security functions
def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(user_id: int) -> str:
    """Create JWT token for authenticated user"""
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> int:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def track_sign_in(user_id: int) -> None:
    """Track user sign-in with Quest Processing Service"""
    try:
        response = requests.post(
            QUEST_PROCESSING_SERVICE_URL,
            json={"user_id": user_id},
            timeout=5
        )
        if response.status_code != 200:
            logger.error(
                f"Failed to track sign-in for user {user_id}: "
                f"{response.status_code} {response.text}"
            )
    except requests.exceptions.Timeout:
        logger.error(f"Timeout tracking sign-in for user {user_id}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to Quest Processing Service: {e}")


# API Endpoints
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "service": "auth_service"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@app.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def signup(user: UserCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Register a new user
    - Creates new user account
    - Initializes user with 20 gold
    - Tracks initial sign-in for quests
    - Returns authentication token
    """
    try:
        hashed_password = hash_password(user.password)
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO Users (user_name, password, status, gold, last_login)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (user.username, hashed_password, 0, 20)
        )
        db.commit()
        user_id = cursor.lastrowid

        logger.info(f"User '{user.username}' signed up successfully with user_id {user_id}")

        # Track initial sign-in asynchronously
        track_sign_in(user_id)

        token = create_token(user_id)
        return {"access_token": token, "token_type": "bearer"}

    except sqlite3.IntegrityError:
        logger.warning(f"Signup attempt with existing username: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during signup"
        )


@app.post("/login", response_model=Token, tags=["Authentication"])
def login(user: UserLogin, db: sqlite3.Connection = Depends(get_db)):
    """
    Authenticate existing user
    - Validates credentials
    - Tracks sign-in for quests
    - Returns authentication token
    """
    try:
        hashed_password = hash_password(user.password)
        cursor = db.cursor()

        cursor.execute(
            "SELECT user_id, status FROM Users WHERE user_name = ? AND password = ?",
            (user.username, hashed_password)
        )
        result = cursor.fetchone()

        if not result:
            logger.warning(f"Failed login attempt for username: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        user_id = result["user_id"]
        user_status = result["status"]

        # Check if user is banned
        if user_status == 2:
            logger.warning(f"Banned user login attempt: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is banned"
            )

        # Update last login time
        cursor.execute(
            "UPDATE Users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        db.commit()

        logger.info(f"User '{user.username}' logged in successfully")

        # Track sign-in asynchronously
        track_sign_in(user_id)

        token = create_token(user_id)
        return {"access_token": token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@app.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
def get_user(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    """Get user information by user_id"""
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT user_id, user_name, gold, diamond, status
            FROM Users
            WHERE user_id = ?
            """,
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        status_map = {0: "new", 1: "active", 2: "banned"}

        return UserResponse(
            user_id=user["user_id"],
            user_name=user["user_name"],
            gold=user["gold"],
            diamond=user["diamond"],
            status=status_map.get(user["status"], "unknown")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user data"
        )


@app.post("/add-diamonds/{user_id}", tags=["Rewards"])
def add_diamonds(user_id: int, data: AddDiamonds, db: sqlite3.Connection = Depends(get_db)):
    """Add diamonds to user account"""
    try:
        cursor = db.cursor()
        cursor.execute(
            "UPDATE Users SET diamond = diamond + ? WHERE user_id = ?",
            (data.diamonds, user_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        db.commit()
        logger.info(f"Added {data.diamonds} diamonds to user {user_id}")

        return {
            "message": "Diamonds added successfully",
            "user_id": user_id,
            "diamonds_added": data.diamonds
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding diamonds to user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding diamonds"
        )


@app.post("/add-gold/{user_id}", tags=["Rewards"])
def add_gold(user_id: int, data: AddGold, db: sqlite3.Connection = Depends(get_db)):
    """Add gold to user account"""
    try:
        cursor = db.cursor()
        cursor.execute(
            "UPDATE Users SET gold = gold + ? WHERE user_id = ?",
            (data.gold, user_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        db.commit()
        logger.info(f"Added {data.gold} gold to user {user_id}")

        return {
            "message": "Gold added successfully",
            "user_id": user_id,
            "gold_added": data.gold
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding gold to user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding gold"
        )


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when service starts"""
    logger.info("Starting Auth Service...")
    init_db()
    logger.info("Auth Service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Auth Service...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
