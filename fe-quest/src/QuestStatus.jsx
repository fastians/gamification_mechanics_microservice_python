import React, { useEffect, useState } from "react";
import axios from "axios";

const QuestStatus = ({ userId }) => {
  const [quests, setQuests] = useState([]);

  useEffect(() => {
    const fetchQuests = async () => {
      try {
        const response = await axios.get(
          `http://localhost:8003/user-quests/${userId}`
        );
        setQuests(response.data);
      } catch (error) {
        console.error("Error fetching quest status:", error);
      }
    };

    fetchQuests();
  }, [userId]);

  return (
    <div className="bg-white p-4 rounded shadow">
      <h2 className="text-2xl font-semibold mb-2">Your Quests</h2>
      {quests.length === 0 ? (
        <p>No quests found.</p>
      ) : (
        <ul>
          {quests.map((quest, index) => (
            <li key={index} className="border-b py-2">
              Quest ID: {quest.quest_id} - Progress: {quest.progress} - Reward:{" "}
              {quest.reward}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default QuestStatus;
