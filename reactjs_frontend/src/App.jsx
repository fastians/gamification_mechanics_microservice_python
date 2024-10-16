// src/App.jsx

import React, { useState, useEffect } from "react";
import axios from "axios";

function App() {
  const AUTH_SERVICE_URL = "http://localhost:8001";
  const QUEST_CATALOG_URL = "http://localhost:8002";
  const QUEST_PROCESSING_URL = "http://localhost:8003";

  const [signupData, setSignupData] = useState({
    user_name: "",
    password: "",
    status: "new",
  });
  const [loginData, setLoginData] = useState({ user_name: "", password: "" });
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(null);
  const [quests, setQuests] = useState([]);
  const [assignQuestData, setAssignQuestData] = useState({ quest_id: "" });
  const [userQuests, setUserQuests] = useState([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (token) {
      const decodeToken = (token) => {
        try {
          const payload = token.split(".")[1];
          return JSON.parse(atob(payload));
        } catch (e) {
          return null;
        }
      };
      const decoded = decodeToken(token);
      if (decoded && decoded.user_id) {
        fetchUser(decoded.user_id);
      }
    }
  }, [token]);

  const fetchUser = async (user_id) => {
    try {
      const response = await axios.get(`${AUTH_SERVICE_URL}/users/${user_id}`);
      setUser(response.data);
    } catch (error) {
      console.error(
        "Error fetching user:",
        error.response?.data || error.message
      );
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(
        `${AUTH_SERVICE_URL}/signup`,
        signupData
      );
      setToken(response.data.access_token);
      localStorage.setItem("token", response.data.access_token);
      setMessage("Signup successful!");
    } catch (error) {
      console.error("Signup error:", error.response?.data || error.message);
      setMessage(
        `Signup failed: ${error.response?.data.detail || error.message}`
      );
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${AUTH_SERVICE_URL}/login`, loginData);
      setToken(response.data.access_token);
      localStorage.setItem("token", response.data.access_token);
      setMessage("Login successful!");
    } catch (error) {
      console.error("Login error:", error.response?.data || error.message);
      setMessage(
        `Login failed: ${error.response?.data.detail || error.message}`
      );
    }
  };

  const fetchQuests = async () => {
    try {
      const response = await axios.get(`${QUEST_CATALOG_URL}/quests/`);
      setQuests(response.data);
    } catch (error) {
      console.error(
        "Error fetching quests:",
        error.response?.data || error.message
      );
    }
  };

  const assignQuest = async (e, quest_id) => {
    e.preventDefault();
    if (!user) {
      alert("Please log in first.");
      return;
    }
    try {
      const payload = {
        user_id: user.user_id,
        quest_id: parseInt(quest_id),
      };
      await axios.post(`${QUEST_PROCESSING_URL}/assign-quest/`, payload);
      setMessage("Quest assigned successfully!");
      fetchUserQuests();
    } catch (error) {
      console.error(
        "Error assigning quest:",
        error.response?.data || error.message
      );
      setMessage(
        `Assign quest failed: ${error.response?.data.detail || error.message}`
      );
    }
  };

  const fetchUserQuests = async () => {
    if (!user) {
      alert("Please log in first.");
      return;
    }
    try {
      const response = await axios.get(
        `${QUEST_PROCESSING_URL}/user-quests/${user.user_id}/`
      );
      setUserQuests(response.data);
    } catch (error) {
      console.error(
        "Error fetching user quests:",
        error.response?.data || error.message
      );
    }
  };

  const completeQuest = async (quest_id) => {
    if (!user) {
      alert("Please log in first.");
      return;
    }
    try {
      const payload = {
        user_id: user.user_id,
        quest_id: quest_id,
      };
      await axios.post(`${QUEST_PROCESSING_URL}/complete-quest/`, payload);
      setMessage("Quest completed successfully!");
      fetchUserQuests();
      fetchUser(user.user_id); // Refresh user data to see updated rewards
    } catch (error) {
      console.error(
        "Error completing quest:",
        error.response?.data || error.message
      );
      setMessage(
        `Complete quest failed: ${error.response?.data.detail || error.message}`
      );
    }
  };

  const claimQuest = async (quest_id) => {
    console.log("ok");
    alert("Please log in first.");
    if (!user) {
      alert("Please log in first.");
      return;
    }
    try {
      const payload = {
        user_id: user.user_id,
        quest_id: quest_id,
      };
      await axios.post(`${QUEST_PROCESSING_URL}/claim-quest/`, payload);
      setMessage("Quest claimed and reward granted!");
      fetchUserQuests();
      fetchUser(user.user_id); // Refresh user data to see updated rewards
    } catch (error) {
      console.error(
        "Error claiming quest:",
        error.response?.data || error.message
      );
      setMessage(
        `Claim quest failed: ${error.response?.data.detail || error.message}`
      );
    }
  };

  const handleLogout = () => {
    setToken("");
    localStorage.removeItem("token");
    setUser(null);
    setUserQuests([]);
    setMessage("Logged out successfully!");
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-6">
          Gamification Platform
        </h1>

        {!token ? (
          <div className="flex flex-col md:flex-row justify-between mb-8">
            <form
              onSubmit={handleSignup}
              className="bg-white p-6 rounded shadow-md mb-4 md:mb-0 md:mr-4 w-full"
            >
              <h2 className="text-xl font-semibold mb-4">Sign Up</h2>
              <div className="mb-3">
                <input
                  type="text"
                  required
                  value={signupData.user_name}
                  onChange={(e) =>
                    setSignupData({ ...signupData, user_name: e.target.value })
                  }
                  placeholder="Username"
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              <div className="mb-3">
                <input
                  type="password"
                  required
                  value={signupData.password}
                  onChange={(e) =>
                    setSignupData({ ...signupData, password: e.target.value })
                  }
                  placeholder="Password"
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              <div className="mb-3">
                <select
                  value={signupData.status}
                  onChange={(e) =>
                    setSignupData({ ...signupData, status: e.target.value })
                  }
                  className="w-full px-3 py-2 border rounded"
                >
                  <option value="new">New</option>
                  <option value="not_new">Not New</option>
                  <option value="banned">Banned</option>
                </select>
              </div>
              <button
                type="submit"
                className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600"
              >
                Sign Up
              </button>
            </form>

            <form
              onSubmit={handleLogin}
              className="bg-white p-6 rounded shadow-md w-full"
            >
              <h2 className="text-xl font-semibold mb-4">Log In</h2>
              <div className="mb-3">
                <input
                  type="text"
                  required
                  value={loginData.user_name}
                  onChange={(e) =>
                    setLoginData({ ...loginData, user_name: e.target.value })
                  }
                  placeholder="Username"
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              <div className="mb-3">
                <input
                  type="password"
                  required
                  value={loginData.password}
                  onChange={(e) =>
                    setLoginData({ ...loginData, password: e.target.value })
                  }
                  placeholder="Password"
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              <button
                type="submit"
                className="w-full bg-green-500 text-white py-2 rounded hover:bg-green-600"
              >
                Log In
              </button>
            </form>
          </div>
        ) : (
          <div className="mb-8 flex justify-between items-center bg-white p-6 rounded shadow-md">
            <div>
              <h2 className="text-xl font-semibold">
                Welcome, {user?.user_name}!
              </h2>
              <p>
                Gold: {user?.gold} | Diamonds: {user?.diamond} | Status:{" "}
                {user?.status}
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
            >
              Log Out
            </button>
          </div>
        )}

        {token && (
          <>
            <div className="bg-white p-6 rounded shadow-md mb-8">
              <h2 className="text-2xl font-semibold mb-4">Available Quests</h2>
              <button
                onClick={fetchQuests}
                className="mb-4 bg-indigo-500 text-white px-4 py-2 rounded hover:bg-indigo-600"
              >
                Fetch Quests
              </button>
              {quests.length > 0 ? (
                <table className="w-full table-auto">
                  <thead>
                    <tr className="bg-gray-200">
                      <th className="px-4 py-2">ID</th>
                      <th className="px-4 py-2">Name</th>
                      <th className="px-4 py-2">Description</th>
                      <th className="px-4 py-2">Reward</th>
                      <th className="px-4 py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {quests.map((quest) => (
                      <tr key={quest.quest_id} className="border-t">
                        <td className="px-4 py-2">{quest.quest_id}</td>
                        <td className="px-4 py-2">{quest.name}</td>
                        <td className="px-4 py-2">{quest.description}</td>
                        <td className="px-4 py-2">
                          {quest.auto_claim ? "Auto-Claim" : "Manual Claim"}
                          <br />
                          {quest.streak} times needed
                          <br />
                          Reward: {quest.reward_qty} {quest.reward_item}
                        </td>
                        <td className="px-4 py-2">
                          <button
                            onClick={(e) => {
                              setAssignQuestData({ quest_id: quest.quest_id });
                              assignQuest(e, quest.quest_id);
                            }}
                            className="bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600"
                          >
                            Assign Quest
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p>No quests available. Click "Fetch Quests" to load quests.</p>
              )}
            </div>

            <div className="bg-white p-6 rounded shadow-md mb-8">
              <h2 className="text-2xl font-semibold mb-4">Your Quests</h2>
              <button
                onClick={fetchUserQuests}
                className="mb-4 bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600"
              >
                Fetch Your Quests
              </button>
              {userQuests.length > 0 ? (
                <table className="w-full table-auto">
                  <thead>
                    <tr className="bg-gray-200">
                      <th className="px-4 py-2">Quest ID</th>
                      <th className="px-4 py-2">Quest Name</th>
                      <th className="px-4 py-2">Status</th>
                      <th className="px-4 py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {userQuests.map((uq) => (
                      <tr
                        key={`${uq.quest_id}-${uq.user_id}`}
                        className="border-t"
                      >
                        <td className="px-4 py-2">{uq.quest_id}</td>
                        <td className="px-4 py-2">{uq.name}</td>
                        <td className="px-4 py-2 capitalize">{uq.status}</td>
                        <td className="px-4 py-2">
                          {uq.status === "completed" && (
                            <button
                              onClick={() => claimQuest(uq.quest_id)}
                              className="bg-green-500 text-white px-3 py-1 rounded hover:bg-green-600"
                            >
                              Claim Reward
                            </button>
                          )}
                          {uq.status === "claimed" && (
                            <span className="text-green-700 font-semibold">
                              Claimed
                            </span>
                          )}
                          {uq.status === "in_progress" && (
                            <span className="text-blue-500 font-semibold">
                              In Progress
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p>
                  You have no assigned quests. Assign a quest to get started!
                </p>
              )}
            </div>
          </>
        )}

        {message && <p className="mt-4 text-center text-red-500">{message}</p>}
      </div>
    </div>
  );
}

export default App;
