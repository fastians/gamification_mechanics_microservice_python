# Microservices

This project consists of microservices for managing users, quests, rewards, and assigning quests using FastAPI. Each service runs independently and communicates through an API Gateway. Docker is used to containerize the microservices.

## Getting Started

### Prerequisites
- Docker
- Docker Compose

### Running the Services

To start all the microservices using Docker Compose:

```bash
docker-compose up --build
```

This will build the images and start the following services:

	•	API Gateway (Port: 8000)
	•	User Authentication Service (Port: 8001)
	•	Quest Catalog Service (Port: 8002)
	•	Quest Processing Service (Port: 8003)

API Usage

Once the services are running, follow the steps to test the application:

1. Create Reward

To create a new reward, use the following cURL command:

curl -X POST http://localhost:8000/rewards/ \
     -H "Content-Type: application/json" \
     -d '{
           "reward_name": "Diamonds",
           "reward_item": "diamond",
           "reward_qty": 10
         }'

2. Create Quest 

To create a quest and link it to a reward:

curl -X POST http://localhost:8000/quests/ \
     -H "Content-Type: application/json" \
     -d '{
           "reward_id": 1,
           "auto_claim": true,
           "streak": 3,
           "duplication": 1,
           "name": "Sign-In-Three-Times",
           "description": "Log in to the platform three times to receive a reward of 10 diamonds."
         }'

3. Assign Quest to User

To assign a quest to a specific user:

curl -X POST http://localhost:8000/assign-quest/ \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": 1,
           "quest_id": 1
         }'

4. Signup User

To register a new user:

curl -X POST "http://localhost:8001/signup" \
     -H "Content-Type: application/json" \
     -d '{
           "username": "testuser",
           "password": "password123"
         }'

5. Login User

To log in an existing user:

curl -X POST "http://localhost:8001/login" \
     -H "Content-Type: application/json" \
     -d '{
           "username": "testuser",
           "password": "password123"
         }'


## Accessing Documentation

Access the Swagger UI for each microservice using the following URLs:

	•	API Gateway: http://localhost:8000/docs
	•	Auth Service: http://localhost:8001/docs
	•	Quest Catalog Service: http://localhost:8002/docs
	•	Quest Processing Service: http://localhost:8003/docs

## FE code
go to project folder

### Prerequisites
- Node Js

```
npm install
npm run dev
```