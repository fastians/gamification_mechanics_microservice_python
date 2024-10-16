// src/components/RewardManagement.js

import React, { useState, useEffect } from "react";
import axios from "axios";

const RewardManagement = () => {
  const [rewards, setRewards] = useState([]);
  const [rewardName, setRewardName] = useState("");
  const [rewardItem, setRewardItem] = useState("");
  const [rewardQty, setRewardQty] = useState(0);

  const axiosInstance = axios.create({
    baseURL: "http://localhost:8000",
  });

  useEffect(() => {
    fetchRewards();
  }, []);

  const fetchRewards = async () => {
    try {
      const response = await axiosInstance.get("/rewards");
      if (Array.isArray(response.data)) {
        setRewards(response.data);
      }
    } catch (error) {
      console.error("Error fetching rewards:", error);
    }
  };

  const addReward = async () => {
    try {
      await axiosInstance.post("/rewards", {
        reward_name: rewardName,
        reward_item: rewardItem,
        reward_qty: parseInt(rewardQty),
      });
      setRewardName("");
      setRewardItem("");
      setRewardQty(0);
      fetchRewards();
    } catch (error) {
      console.error("Error adding reward:", error);
    }
  };

  return (
    <div className="mb-10">
      <h2 className="text-2xl font-semibold mb-4">Reward Management</h2>
      <div className="mb-4">
        <input
          type="text"
          value={rewardName}
          onChange={(e) => setRewardName(e.target.value)}
          placeholder="Reward Name"
          className="border rounded-md p-2 mr-2"
        />
        <input
          type="text"
          value={rewardItem}
          onChange={(e) => setRewardItem(e.target.value)}
          placeholder="Reward Item"
          className="border rounded-md p-2 mr-2"
        />
        <input
          type="number"
          value={rewardQty}
          onChange={(e) => setRewardQty(e.target.value)}
          placeholder="Reward Quantity"
          className="border rounded-md p-2 mr-2"
        />
        <button
          onClick={addReward}
          className="bg-yellow-500 text-white p-2 rounded-md"
        >
          Add Reward
        </button>
      </div>
      {rewards.length > 0 ? (
        <ul className="list-disc pl-5">
          {rewards.map((reward) => (
            <li key={reward.reward_id} className="mb-1">
              {reward.reward_name} (Item: {reward.reward_item}, Qty:{" "}
              {reward.reward_qty})
            </li>
          ))}
        </ul>
      ) : (
        <p>No rewards found.</p>
      )}
    </div>
  );
};

export default RewardManagement;
