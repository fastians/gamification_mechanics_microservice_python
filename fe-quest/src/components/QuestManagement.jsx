// src/components/QuestManagement.js

import React, { useState, useEffect } from "react";
import axios from "axios";

const QuestManagement = () => {
  const [quests, setQuests] = useState([]);
  const [questName, setQuestName] = useState("");
  const [questDescription, setQuestDescription] = useState("");
  const [rewardId, setRewardId] = useState("");
  const [autoClaim, setAutoClaim] = useState(false);
  const [streak, setStreak] = useState(0);
  const [duplication, setDuplication] = useState(0);

  const axiosInstance = axios.create({
    baseURL: "http://localhost:8000",
  });

  useEffect(() => {
    fetchQuests();
  }, []);

  const fetchQuests = async () => {
    try {
      const response = await axiosInstance.get("/quests");
      if (Array.isArray(response.data)) {
        setQuests(response.data);
      }
    } catch (error) {
      console.error("Error fetching quests:", error);
    }
  };

  const addQuest = async () => {
    try {
      await axiosInstance.post("/quests", {
        reward_id: parseInt(rewardId),
        auto_claim: autoClaim,
        streak: parseInt(streak),
        duplication: parseInt(duplication),
        name: questName,
        description: questDescription,
      });
      setQuestName("");
      setQuestDescription("");
      setRewardId("");
      setAutoClaim(false);
      setStreak(0);
      setDuplication(0);
      fetchQuests();
    } catch (error) {
      console.error("Error adding quest:", error);
    }
  };

  return (
    <div className="mb-10">
      <h2 className="text-2xl font-semibold mb-4">Quest Management</h2>
      <div className="mb-4">
        <input
          type="text"
          value={questName}
          onChange={(e) => setQuestName(e.target.value)}
          placeholder="Quest Name"
          className="border rounded-md p-2 mr-2"
        />
        <input
          type="text"
          value={questDescription}
          onChange={(e) => setQuestDescription(e.target.value)}
          placeholder="Quest Description"
          className="border rounded-md p-2 mr-2"
        />
        <input
          type="text"
          value={rewardId}
          onChange={(e) => setRewardId(e.target.value)}
          placeholder="Reward ID"
          className="border rounded-md p-2 mr-2"
        />
        <input
          type="checkbox"
          checked={autoClaim}
          onChange={(e) => setAutoClaim(e.target.checked)}
          className="mr-2"
        />
        <label className="mr-4">Auto Claim</label>
        <input
          type="number"
          value={streak}
          onChange={(e) => setStreak(e.target.value)}
          placeholder="Streak"
          className="border rounded-md p-2 mr-2"
        />
        <input
          type="number"
          value={duplication}
          onChange={(e) => setDuplication(e.target.value)}
          placeholder="Duplication"
          className="border rounded-md p-2 mr-2"
        />
        <button
          onClick={addQuest}
          className="bg-green-500 text-white p-2 rounded-md"
        >
          Add Quest
        </button>
      </div>
      {quests.length > 0 ? (
        <ul className="list-disc pl-5">
          {quests.map((quest) => (
            <li key={quest.quest_id} className="mb-1">
              {quest.name} (Description: {quest.description})
            </li>
          ))}
        </ul>
      ) : (
        <p>No quests found.</p>
      )}
    </div>
  );
};

export default QuestManagement;
