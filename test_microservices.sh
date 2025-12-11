#!/bin/bash

# Gamification Microservices Test Script
# This script tests all microservice endpoints in the correct order

set -e  # Exit on any error

BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Gamification Microservices Test Script${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Step 1: Create Reward
echo -e "${GREEN}Step 1: Creating a reward...${NC}"
REWARD_RESPONSE=$(curl -s -X POST "$BASE_URL/rewards/" \
  -H "Content-Type: application/json" \
  -d '{
    "reward_name": "Diamonds",
    "reward_item": "diamond",
    "reward_qty": 10
  }')
echo "$REWARD_RESPONSE" | jq '.'
REWARD_ID=$(echo "$REWARD_RESPONSE" | jq -r '.reward_id')
echo -e "${GREEN}✓ Reward created with ID: $REWARD_ID${NC}\n"

# Step 2: Create Quest
echo -e "${GREEN}Step 2: Creating a quest...${NC}"
QUEST_RESPONSE=$(curl -s -X POST "$BASE_URL/quests/" \
  -H "Content-Type: application/json" \
  -d "{
    \"reward_id\": $REWARD_ID,
    \"auto_claim\": false,
    \"streak\": 3,
    \"duplication\": 1,
    \"name\": \"Sign-In-Three-Times\",
    \"description\": \"Log in to the platform three times to receive a reward of 10 diamonds.\"
  }")
echo "$QUEST_RESPONSE" | jq '.'
QUEST_ID=$(echo "$QUEST_RESPONSE" | jq -r '.quest_id')
echo -e "${GREEN}✓ Quest created with ID: $QUEST_ID${NC}\n"

# Step 3: Signup User
echo -e "${GREEN}Step 3: Signing up a user...${NC}"
TIMESTAMP=$(date +%s)
USERNAME="testuser_${TIMESTAMP}"
SIGNUP_RESPONSE=$(curl -s -X POST "$BASE_URL/signup" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$USERNAME\",
    \"password\": \"password123\"
  }")
echo "$SIGNUP_RESPONSE" | jq '.'
ACCESS_TOKEN=$(echo "$SIGNUP_RESPONSE" | jq -r '.access_token')

# Decode JWT to get user_id (from payload, second part of JWT)
if [ "$ACCESS_TOKEN" != "null" ] && [ -n "$ACCESS_TOKEN" ]; then
  JWT_PAYLOAD=$(echo "$ACCESS_TOKEN" | cut -d'.' -f2)
  # Add padding if needed for base64 decode
  JWT_PAYLOAD="${JWT_PAYLOAD}$(printf '%*s' $((4 - ${#JWT_PAYLOAD} % 4)) '' | tr ' ' '=')"
  USER_ID=$(echo "$JWT_PAYLOAD" | base64 -d 2>/dev/null | jq -r '.user_id')
else
  USER_ID="null"
fi
echo -e "${GREEN}✓ User created with ID: $USER_ID${NC}\n"

# Step 4: Login User
echo -e "${GREEN}Step 4: Logging in user...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$USERNAME\",
    \"password\": \"password123\"
  }")
echo "$LOGIN_RESPONSE" | jq '.'
echo -e "${GREEN}✓ User logged in successfully${NC}\n"

# Step 5: Get User Details (Before)
echo -e "${GREEN}Step 5: Fetching user details (before quest)...${NC}"
USER_BEFORE=$(curl -s -X GET "$BASE_URL/users/$USER_ID")
echo "$USER_BEFORE" | jq '.'
echo -e "${GREEN}✓ User balance - Gold: $(echo "$USER_BEFORE" | jq -r '.gold'), Diamonds: $(echo "$USER_BEFORE" | jq -r '.diamond')${NC}\n"

# Step 6: Assign Quest to User
echo -e "${GREEN}Step 6: Assigning quest to user...${NC}"
ASSIGN_RESPONSE=$(curl -s -X POST "$BASE_URL/assign-quest/" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": $USER_ID,
    \"quest_id\": $QUEST_ID
  }")
echo "$ASSIGN_RESPONSE" | jq '.'
echo -e "${GREEN}✓ Quest assigned successfully${NC}\n"

# Step 7: Complete Quest (3 times for streak)
echo -e "${GREEN}Step 7: Completing quest (streak: 3)...${NC}"

for i in 1 2 3; do
  echo -e "${BLUE}Completion #$i:${NC}"
  COMPLETE_RESPONSE=$(curl -s -X POST "$BASE_URL/complete-quest/" \
    -H "Content-Type: application/json" \
    -d "{
      \"user_id\": $USER_ID,
      \"quest_id\": $QUEST_ID
    }")
  echo "$COMPLETE_RESPONSE" | jq '.'
  sleep 1
done
echo -e "${GREEN}✓ Quest completed successfully${NC}\n"

# Step 8: Check User Quests
echo -e "${GREEN}Step 8: Checking user quests...${NC}"
USER_QUESTS=$(curl -s -X GET "$BASE_URL/user-quests/$USER_ID/")
echo "$USER_QUESTS" | jq '.'
QUEST_STATUS=$(echo "$USER_QUESTS" | jq -r '.[0].status')
echo -e "${GREEN}✓ Quest status: $QUEST_STATUS${NC}\n"

# Step 9: Claim Quest Reward
echo -e "${GREEN}Step 9: Claiming quest reward...${NC}"
CLAIM_RESPONSE=$(curl -s -X POST "$BASE_URL/claim-quest/" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": $USER_ID,
    \"quest_id\": $QUEST_ID
  }")
echo "$CLAIM_RESPONSE" | jq '.'
echo -e "${GREEN}✓ Reward claimed successfully${NC}\n"

# Step 10: Verify User Balance (After)
echo -e "${GREEN}Step 10: Verifying user balance (after quest)...${NC}"
USER_AFTER=$(curl -s -X GET "$BASE_URL/users/$USER_ID")
echo "$USER_AFTER" | jq '.'
DIAMONDS_AFTER=$(echo "$USER_AFTER" | jq -r '.diamond')
echo -e "${GREEN}✓ User balance - Gold: $(echo "$USER_AFTER" | jq -r '.gold'), Diamonds: $DIAMONDS_AFTER${NC}\n"

# Final Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ All tests completed successfully!${NC}"
echo -e "Reward ID: $REWARD_ID"
echo -e "Quest ID: $QUEST_ID"
echo -e "User ID: $USER_ID"
echo -e "Diamonds earned: $DIAMONDS_AFTER"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${GREEN}You can now test additional endpoints:${NC}"
echo -e "• List all rewards: curl $BASE_URL/rewards/"
echo -e "• List all quests: curl $BASE_URL/quests/"
echo -e "• Add gold: curl -X POST $BASE_URL/add-gold/ -H 'Content-Type: application/json' -d '{\"user_id\": $USER_ID, \"amount\": 100}'"
echo -e "• Add diamonds: curl -X POST $BASE_URL/add-diamonds/ -H 'Content-Type: application/json' -d '{\"user_id\": $USER_ID, \"amount\": 50}'"
