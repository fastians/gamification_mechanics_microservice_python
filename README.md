# Gamification Mechanics Microservice

A complete gamification platform with microservices for managing users, quests, and rewards using FastAPI. Each service runs independently and communicates through an API Gateway. Docker is used to containerize the microservices.

## What Does This Do?

This platform enables game-like mechanics in your application:
- 🎁 **Create Rewards**: Define rewards (gold, diamonds, items) users can earn
- 🎯 **Create Quests**: Set up challenges that require multiple completions (streaks)
- 👤 **User Management**: Authenticate users with JWT tokens
- 📊 **Progress Tracking**: Monitor user progress on assigned quests
- 💎 **Reward Distribution**: Auto-claim or manual reward claiming upon quest completion

## Architecture

This project consists of the following services:

- **Frontend** (React + Vite + TailwindCSS) - Web UI for testing all microservice endpoints
- **API Gateway** (Port 8000) - Central entry point routing requests to backend services
- **User Authentication Service** (Port 8001) - User signup, login, and profile management
- **Quest Catalog Service** (Port 8002) - Reward and quest management
- **Quest Processing Service** (Port 8003) - Quest assignment, completion, and reward claiming

## Quick Start

```bash
# 1. Start all services
docker-compose up --build

# 2. In a new terminal, run the automated test script
./test_microservices.sh

# OR open the web UI in your browser
open http://localhost:3001
```

That's it! The test script or web UI will guide you through the complete quest workflow.

## Getting Started

### Prerequisites
- Docker
- Docker Compose
- (Optional) jq - for running the automated test script

### Running the Services

To start all the microservices using Docker Compose:

```bash
docker-compose up --build
```

This will build the images and start the following services:

- **Frontend**: http://localhost:3001 - Web UI for testing
- **API Gateway**: http://localhost:8000 - Central API endpoint
- **Auth Service**: http://localhost:8001 - User authentication
- **Quest Catalog Service**: http://localhost:8002 - Rewards and quests
- **Quest Processing Service**: http://localhost:8003 - Quest assignment and completion

### Stop the Services

```bash
docker-compose down
```

## Quest Workflow

```
1. Create Reward → 2. Create Quest → 3. Signup User → 4. Login
                ↓
5. Get User Details (Balance: 0) → 6. Assign Quest to User
                ↓
7. Complete Quest (x3 for streak=3) → 8. Check User Quests (status: completed)
                ↓
9. Claim Reward → 10. Verify Balance (Balance: +10 diamonds)
```

## API Usage

Once the services are running, you can interact with them via the following API endpoints:

### Automated Testing Script

For quick testing of all endpoints, use the provided test script:

```bash
./test_microservices.sh
```

This script will automatically:
1. Create a reward
2. Create a quest
3. Signup and login a user
4. Assign the quest to the user
5. Complete the quest (3 times for streak)
6. Claim the reward
7. Verify the user balance

**Note:** Requires `jq` for JSON parsing. Install with:
- macOS: `brew install jq`
- Ubuntu/Debian: `sudo apt-get install jq`
- Windows: Download from https://jqlang.github.io/jq/

### Manual Testing with cURL Commands

Follow these steps in order to test the complete quest workflow manually:

#### Step 1: Create a Reward

Create a new reward that will be given to users upon quest completion.

```bash
curl -X POST http://localhost:8000/rewards/ \
     -H "Content-Type: application/json" \
     -d '{
           "reward_name": "Diamonds",
           "reward_item": "diamond",
           "reward_qty": 10
         }'
```

**Expected Response:**
```json
{
  "reward_id": 1,
  "reward_name": "Diamonds",
  "reward_item": "diamond",
  "reward_qty": 10
}
```

#### Step 2: Create a Quest

Create a quest and link it to the reward created above. Use `reward_id: 1` from the previous step.

```bash
curl -X POST http://localhost:8000/quests/ \
     -H "Content-Type: application/json" \
     -d '{
           "reward_id": 1,
           "auto_claim": false,
           "streak": 3,
           "duplication": 1,
           "name": "Sign-In-Three-Times",
           "description": "Log in to the platform three times to receive a reward of 10 diamonds."
         }'
```

**Expected Response:**
```json
{
  "quest_id": 1,
  "reward_id": 1,
  "auto_claim": false,
  "streak": 3,
  "duplication": 1,
  "name": "Sign-In-Three-Times",
  "description": "Log in to the platform three times to receive a reward of 10 diamonds."
}
```

**Note:**
- `auto_claim: true` - Rewards are automatically granted when quest is completed
- `auto_claim: false` - User must manually claim the reward after completion
- `streak: 3` - User must complete the action 3 times to finish the quest

#### Step 3: Signup a User

Register a new user in the system.

```bash
curl -X POST http://localhost:8000/signup \
     -H "Content-Type: application/json" \
     -d '{
           "username": "testuser",
           "password": "password123"
         }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 1
}
```

#### Step 4: Login User

Log in with the created user credentials.

```bash
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/json" \
     -d '{
           "username": "testuser",
           "password": "password123"
         }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Step 5: Get User Details

Fetch user profile to see current rewards balance.

```bash
curl -X GET http://localhost:8000/users/1
```

**Expected Response:**
```json
{
  "user_id": 1,
  "user_name": "testuser",
  "status": "new",
  "gold": 0,
  "diamond": 0
}
```

#### Step 6: Assign Quest to User

Assign the created quest to the user.

```bash
curl -X POST http://localhost:8000/assign-quest/ \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": 1,
           "quest_id": 1
         }'
```

**Expected Response:**
```json
{
  "message": "Quest assigned successfully",
  "user_id": 1,
  "quest_id": 1,
  "status": "in_progress"
}
```

#### Step 7: Complete Quest (Progress Tracking)

Mark quest progress. Since `streak: 3`, you need to call this **3 times** to complete the quest.

**First completion:**
```bash
curl -X POST http://localhost:8000/complete-quest/ \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": 1,
           "quest_id": 1
         }'
```

**Expected Response:**
```json
{
  "message": "Quest progress updated",
  "progress": 1,
  "streak": 3,
  "status": "in_progress"
}
```

**Second completion:**
```bash
curl -X POST http://localhost:8000/complete-quest/ \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": 1,
           "quest_id": 1
         }'
```

**Third completion (Quest will be marked as completed):**
```bash
curl -X POST http://localhost:8000/complete-quest/ \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": 1,
           "quest_id": 1
         }'
```

**Expected Response:**
```json
{
  "message": "Quest completed! You can now claim your reward.",
  "progress": 3,
  "streak": 3,
  "status": "completed"
}
```

#### Step 8: Check User Quests

View all quests assigned to the user and their status.

```bash
curl -X GET http://localhost:8000/user-quests/1/
```

**Expected Response:**
```json
[
  {
    "user_id": 1,
    "quest_id": 1,
    "status": "completed",
    "progress": 3,
    "name": "Sign-In-Three-Times",
    "description": "Log in to the platform three times to receive a reward of 10 diamonds.",
    "streak": 3,
    "auto_claim": false
  }
]
```

#### Step 9: Claim Quest Reward

Claim the reward for the completed quest (only needed if `auto_claim: false`).

```bash
curl -X POST http://localhost:8000/claim-quest/ \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": 1,
           "quest_id": 1
         }'
```

**Expected Response:**
```json
{
  "message": "Reward claimed successfully",
  "reward": {
    "reward_item": "diamond",
    "reward_qty": 10
  },
  "user_balance": {
    "gold": 0,
    "diamond": 10
  }
}
```

#### Step 10: Verify User Balance

Check that the rewards have been added to the user's account.

```bash
curl -X GET http://localhost:8000/users/1
```

**Expected Response:**
```json
{
  "user_id": 1,
  "user_name": "testuser",
  "status": "new",
  "gold": 0,
  "diamond": 10
}
```

### Additional API Endpoints

#### List All Rewards

```bash
curl -X GET http://localhost:8000/rewards/
```

#### List All Quests

```bash
curl -X GET http://localhost:8000/quests/
```

#### Add Gold to User

```bash
curl -X POST http://localhost:8000/add-gold/ \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": 1,
           "amount": 100
         }'
```

#### Add Diamonds to User

```bash
curl -X POST http://localhost:8000/add-diamonds/ \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": 1,
           "amount": 50
         }'
```

## Testing with Web UI (Alternative Method)

If you prefer a visual interface instead of curl commands:

1. **Open your browser** and navigate to: http://localhost:3001

2. **Admin Panel Tab:**
   - Create rewards and quests using the forms
   - View all created rewards and quests

3. **Login/Signup Tab:**
   - Create a new user account
   - Login with existing credentials

4. **Quest System Tab:**
   - Browse available quests
   - Assign quests to yourself
   - Track progress and complete quest steps
   - Claim rewards
   - See your gold and diamond balance update in real-time

## API Documentation

Access the Swagger UI for each microservice:

- **API Gateway**: http://localhost:8000/docs
- **Auth Service**: http://localhost:8001/docs
- **Quest Catalog Service**: http://localhost:8002/docs
- **Quest Processing Service**: http://localhost:8003/docs

## Development Setup (Frontend Only)

If you want to run the frontend in development mode without Docker:

### Prerequisites
- Node.js (v18 or higher)
- Backend services must be running via docker-compose

### Steps

1. Navigate to the frontend directory:
```bash
cd reactjs_frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

4. Open http://localhost:5173 in your browser

## Project Structure

```
.
├── api_gateway/              # API Gateway service
├── auth_service/             # User authentication service
├── quest_catalog_service/    # Quest and reward catalog service
├── quest_processing_service/ # Quest processing and assignment service
├── reactjs_frontend/         # React frontend test interface
│   ├── src/
│   │   ├── App.jsx          # Main application component
│   │   ├── components/      # React components
│   │   └── ...
│   ├── Dockerfile           # Frontend Docker configuration
│   └── nginx.conf           # Nginx configuration for production
└── docker-compose.yml        # Docker Compose configuration
```

## Key Features

### Quest System
- **Streak-based quests**: Require multiple completions before reward is granted
- **Auto-claim**: Automatically grant rewards upon quest completion
- **Manual claim**: Require users to manually claim rewards after completion
- **Progress tracking**: Real-time tracking of user progress on each quest
- **Quest duplication**: Support for repeatable quests

### Reward System
- Multiple reward types (gold, diamonds, custom items)
- Configurable reward quantities
- Automatic or manual reward distribution
- User balance tracking

### User Management
- JWT-based authentication
- Secure password hashing
- User profiles with reward balances
- User status management (new, returning, banned)

### API Gateway
- Central routing for all microservices
- CORS support for web applications
- Health check monitoring for all services
- Request/response logging

## Technologies Used

### Backend
- **FastAPI**: Modern, fast Python web framework
- **SQLite**: Lightweight database for each service
- **JWT**: Secure authentication tokens
- **Docker**: Containerization and orchestration
- **Uvicorn**: ASGI server

### Frontend
- **React 18**: Modern React with hooks
- **Vite**: Fast build tool and dev server
- **TailwindCSS**: Utility-first CSS framework
- **Axios**: HTTP client for API calls
- **Nginx**: Production web server

## Troubleshooting

### Docker not starting
If you see "Cannot connect to the Docker daemon":
1. Make sure Docker Desktop is running
2. Try restarting Docker Desktop
3. Check Docker Desktop settings to ensure the engine is started

### Port already in use
If you see "port is already allocated":
```bash
# Find and kill the process using the port
lsof -ti:8000 | xargs kill -9  # For API Gateway
lsof -ti:3000 | xargs kill -9  # For Frontend
```

### Services not responding
1. Check if all containers are running:
```bash
docker-compose ps
```

2. Check service logs:
```bash
docker-compose logs [service_name]
```

3. Restart services:
```bash
docker-compose restart
```

## License

MIT