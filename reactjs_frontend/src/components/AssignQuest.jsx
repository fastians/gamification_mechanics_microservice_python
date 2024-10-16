// src/components/AssignQuest.js

import React, { useState, useEffect } from "react";
import axios from "axios";

const AssignQuest = () => {
  const [users, setUsers] = useState([]);
  const [quests, setQuests] = useState([]);
  const [selectedUser, setSelectedUser] = useState("");
  const [selectedQuest, setSelectedQuest] = useState("");

  const axiosInstance = axios.create({
    baseURL: "http://localhost:8000",
  });

  useEffect(() => {
    fetchUsers();
    fetchQuests();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axiosInstance.get("/users");
      if (Array.isArray(response.data)) {
        setUsers(response.data);
      }
    } catch (error) {
      console.error("Error fetching users:", error);
    }
  };

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

  const assignQuest = async () => {
    try {
      await axiosInstance.post("/assign-quest", {
        user_id: parseInt(selectedUser),
        quest_id: parseInt(selectedQuest),
      });
      setSelectedUser("");
      setSelectedQuest("");
    } catch (error) {
      console.error("Error assigning quest:", error);
    }
  };

  return (
    <div className="mb-10">
      <h2 className="text-2xl font-semibold mb-4">Assign Quest to User</h2>
      <div className="mb-4">
        <select
          value={selectedUser}
          onChange={(e) => setSelectedUser(e.target.value)}
          className="border rounded-md p-2 mr-2"
        >
          <option value="">Select User</option>
          {users.map((user) => (
            <option key={user.user_id} value={user.user_id}>
              {user.user_name}
            </option>
          ))}
        </select>
        <select
          value={selectedQuest}
          onChange={(e) => setSelectedQuest(e.target.value)}
          className="border rounded-md p-2 mr-2"
        >
          <option value="">Select Quest</option>
          {quests.map((quest) => (
            <option key={quest.quest_id} value={quest.quest_id}>
              {quest.name}
            </option>
          ))}
        </select>
        <button
          onClick={assignQuest}
          className="bg-purple-500 text-white p-2 rounded-md"
        >
          Assign Quest
        </button>
      </div>
    </div>
  );
};

export default AssignQuest;
