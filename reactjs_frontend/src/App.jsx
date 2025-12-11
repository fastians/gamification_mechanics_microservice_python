import { useState, useEffect } from "react";
import axios from "axios";

function App() {
  const API_GATEWAY_URL = "http://localhost:8000";

  // Auth state
  const [signupData, setSignupData] = useState({
    username: "",
    password: "",
  });
  const [loginData, setLoginData] = useState({ username: "", password: "" });
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(null);
  const [message, setMessage] = useState("");

  // Reward state
  const [rewards, setRewards] = useState([]);
  const [rewardForm, setRewardForm] = useState({
    reward_name: "",
    reward_item: "",
    reward_qty: 10,
  });

  // Quest state
  const [quests, setQuests] = useState([]);
  const [questForm, setQuestForm] = useState({
    reward_id: "",
    auto_claim: false,
    streak: 1,
    duplication: 1,
    name: "",
    description: "",
  });

  // User quest state
  const [userQuests, setUserQuests] = useState([]);

  // Active tab
  const [activeTab, setActiveTab] = useState("admin");

  // Decode JWT token to get user_id
  useEffect(() => {
    if (token) {
      try {
        const payload = token.split(".")[1];
        const decoded = JSON.parse(atob(payload));
        if (decoded && decoded.user_id) {
          fetchUser(decoded.user_id);
        }
      } catch (e) {
        console.error("Error decoding token:", e);
        setToken("");
        localStorage.removeItem("token");
      }
    }
  }, [token]);

  // Fetch user data
  const fetchUser = async (user_id) => {
    try {
      const response = await axios.get(`${API_GATEWAY_URL}/users/${user_id}`);
      setUser(response.data);
    } catch (error) {
      console.error("Error fetching user:", error.response?.data || error.message);
      showMessage("Error fetching user data", "error");
    }
  };

  // Show message helper
  const showMessage = (msg, type = "success") => {
    setMessage({ text: msg, type });
    setTimeout(() => setMessage(""), 5000);
  };

  // ==== AUTH FUNCTIONS ====
  const handleSignup = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API_GATEWAY_URL}/signup`, signupData);
      setToken(response.data.access_token);
      localStorage.setItem("token", response.data.access_token);
      showMessage("Signup successful!");
      setSignupData({ username: "", password: "" });
    } catch (error) {
      console.error("Signup error:", error.response?.data || error.message);
      showMessage(`Signup failed: ${error.response?.data.detail || error.message}`, "error");
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API_GATEWAY_URL}/login`, loginData);
      setToken(response.data.access_token);
      localStorage.setItem("token", response.data.access_token);
      showMessage("Login successful!");
      setLoginData({ username: "", password: "" });
      setActiveTab("quests");
    } catch (error) {
      console.error("Login error:", error.response?.data || error.message);
      showMessage(`Login failed: ${error.response?.data.detail || error.message}`, "error");
    }
  };

  const handleLogout = () => {
    setToken("");
    localStorage.removeItem("token");
    setUser(null);
    setUserQuests([]);
    showMessage("Logged out successfully!");
    setActiveTab("admin");
  };

  // ==== REWARD FUNCTIONS ====
  const fetchRewards = async () => {
    try {
      const response = await axios.get(`${API_GATEWAY_URL}/rewards/`);
      setRewards(response.data);
      showMessage("Rewards fetched successfully!");
    } catch (error) {
      console.error("Error fetching rewards:", error.response?.data || error.message);
      showMessage("Error fetching rewards", "error");
    }
  };

  const createReward = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_GATEWAY_URL}/rewards/`, rewardForm);
      showMessage("Reward created successfully!");
      setRewardForm({ reward_name: "", reward_item: "", reward_qty: 10 });
      fetchRewards();
    } catch (error) {
      console.error("Error creating reward:", error.response?.data || error.message);
      showMessage(`Error creating reward: ${error.response?.data.detail || error.message}`, "error");
    }
  };

  // ==== QUEST FUNCTIONS ====
  const fetchQuests = async () => {
    try {
      const response = await axios.get(`${API_GATEWAY_URL}/quests/`);
      setQuests(response.data);
      showMessage("Quests fetched successfully!");
    } catch (error) {
      console.error("Error fetching quests:", error.response?.data || error.message);
      showMessage("Error fetching quests", "error");
    }
  };

  const createQuest = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...questForm,
        reward_id: parseInt(questForm.reward_id),
        streak: parseInt(questForm.streak),
        duplication: parseInt(questForm.duplication),
      };
      await axios.post(`${API_GATEWAY_URL}/quests/`, payload);
      showMessage("Quest created successfully!");
      setQuestForm({
        reward_id: "",
        auto_claim: false,
        streak: 1,
        duplication: 1,
        name: "",
        description: "",
      });
      fetchQuests();
    } catch (error) {
      console.error("Error creating quest:", error.response?.data || error.message);
      showMessage(`Error creating quest: ${error.response?.data.detail || error.message}`, "error");
    }
  };

  // ==== USER QUEST FUNCTIONS ====
  const fetchUserQuests = async () => {
    if (!user) {
      showMessage("Please log in first", "error");
      return;
    }
    try {
      const response = await axios.get(`${API_GATEWAY_URL}/user-quests/${user.user_id}/`);
      setUserQuests(response.data);
      showMessage("Your quests fetched successfully!");
    } catch (error) {
      console.error("Error fetching user quests:", error.response?.data || error.message);
      showMessage("Error fetching your quests", "error");
    }
  };

  const assignQuest = async (quest_id) => {
    if (!user) {
      showMessage("Please log in first", "error");
      return;
    }
    try {
      const payload = {
        user_id: user.user_id,
        quest_id: parseInt(quest_id),
      };
      await axios.post(`${API_GATEWAY_URL}/assign-quest/`, payload);
      showMessage("Quest assigned successfully!");
      fetchUserQuests();
    } catch (error) {
      console.error("Error assigning quest:", error.response?.data || error.message);
      showMessage(`Error assigning quest: ${error.response?.data.detail || error.message}`, "error");
    }
  };

  const completeQuest = async (quest_id) => {
    if (!user) {
      showMessage("Please log in first", "error");
      return;
    }
    try {
      const payload = {
        user_id: user.user_id,
        quest_id: quest_id,
      };
      await axios.post(`${API_GATEWAY_URL}/complete-quest/`, payload);
      showMessage("Quest progress updated!");
      fetchUserQuests();
      fetchUser(user.user_id);
    } catch (error) {
      console.error("Error completing quest:", error.response?.data || error.message);
      showMessage(`Error completing quest: ${error.response?.data.detail || error.message}`, "error");
    }
  };

  const claimQuest = async (quest_id) => {
    if (!user) {
      showMessage("Please log in first", "error");
      return;
    }
    try {
      const payload = {
        user_id: user.user_id,
        quest_id: quest_id,
      };
      await axios.post(`${API_GATEWAY_URL}/claim-quest/`, payload);
      showMessage("Quest claimed and reward granted!");
      fetchUserQuests();
      fetchUser(user.user_id);
    } catch (error) {
      console.error("Error claiming quest:", error.response?.data || error.message);
      showMessage(`Error claiming quest: ${error.response?.data.detail || error.message}`, "error");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-100 to-blue-100 p-4">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-center mb-8 text-purple-800">
          Gamification Platform Test Interface
        </h1>

        {/* Message Display */}
        {message && (
          <div
            className={`mb-6 p-4 rounded-lg text-center font-semibold ${
              message.type === "error"
                ? "bg-red-100 text-red-800 border border-red-400"
                : "bg-green-100 text-green-800 border border-green-400"
            }`}
          >
            {message.text}
          </div>
        )}

        {/* User Info Bar */}
        {token && user && (
          <div className="mb-6 bg-white p-6 rounded-lg shadow-lg border-2 border-purple-200">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-purple-700">
                  Welcome, {user.user_name}!
                </h2>
                <div className="flex gap-6 mt-2 text-lg">
                  <span className="text-yellow-600 font-semibold">
                    Gold: {user.gold || 0}
                  </span>
                  <span className="text-blue-600 font-semibold">
                    Diamonds: {user.diamond || 0}
                  </span>
                  <span className="text-gray-600">
                    Status: <span className="capitalize">{user.status}</span>
                  </span>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="bg-red-500 text-white px-6 py-3 rounded-lg hover:bg-red-600 transition font-semibold"
              >
                Logout
              </button>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="mb-6 flex gap-2 bg-white p-2 rounded-lg shadow">
          <button
            onClick={() => setActiveTab("admin")}
            className={`flex-1 py-3 px-6 rounded-lg font-semibold transition ${
              activeTab === "admin"
                ? "bg-purple-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Admin Panel
          </button>
          <button
            onClick={() => setActiveTab("quests")}
            className={`flex-1 py-3 px-6 rounded-lg font-semibold transition ${
              activeTab === "quests"
                ? "bg-purple-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Quest System
          </button>
          {!token && (
            <button
              onClick={() => setActiveTab("auth")}
              className={`flex-1 py-3 px-6 rounded-lg font-semibold transition ${
                activeTab === "auth"
                  ? "bg-purple-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              Login / Signup
            </button>
          )}
        </div>

        {/* Admin Panel Tab */}
        {activeTab === "admin" && (
          <div className="space-y-6">
            {/* Create Reward Section */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h2 className="text-2xl font-bold mb-4 text-purple-700">
                Create Reward
              </h2>
              <form onSubmit={createReward} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <input
                    type="text"
                    required
                    value={rewardForm.reward_name}
                    onChange={(e) =>
                      setRewardForm({ ...rewardForm, reward_name: e.target.value })
                    }
                    placeholder="Reward Name (e.g., Diamonds)"
                    className="px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                  />
                  <input
                    type="text"
                    required
                    value={rewardForm.reward_item}
                    onChange={(e) =>
                      setRewardForm({ ...rewardForm, reward_item: e.target.value })
                    }
                    placeholder="Reward Item (e.g., diamond)"
                    className="px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                  />
                  <input
                    type="number"
                    required
                    min="1"
                    value={rewardForm.reward_qty}
                    onChange={(e) =>
                      setRewardForm({
                        ...rewardForm,
                        reward_qty: parseInt(e.target.value),
                      })
                    }
                    placeholder="Quantity"
                    className="px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full bg-yellow-500 text-white py-3 rounded-lg hover:bg-yellow-600 transition font-semibold"
                >
                  Create Reward
                </button>
              </form>
            </div>

            {/* Rewards List */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-purple-700">Rewards List</h2>
                <button
                  onClick={fetchRewards}
                  className="bg-purple-500 text-white px-4 py-2 rounded-lg hover:bg-purple-600 transition"
                >
                  Refresh
                </button>
              </div>
              {rewards.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {rewards.map((reward) => (
                    <div
                      key={reward.reward_id}
                      className="border-2 border-yellow-200 p-4 rounded-lg bg-yellow-50"
                    >
                      <div className="font-bold text-lg text-yellow-700">
                        ID: {reward.reward_id}
                      </div>
                      <div className="text-gray-800 font-semibold">
                        {reward.reward_name}
                      </div>
                      <div className="text-sm text-gray-600">
                        Item: {reward.reward_item} | Qty: {reward.reward_qty}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">
                  No rewards created yet. Create one above!
                </p>
              )}
            </div>

            {/* Create Quest Section */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h2 className="text-2xl font-bold mb-4 text-purple-700">
                Create Quest
              </h2>
              <form onSubmit={createQuest} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input
                    type="text"
                    required
                    value={questForm.name}
                    onChange={(e) =>
                      setQuestForm({ ...questForm, name: e.target.value })
                    }
                    placeholder="Quest Name"
                    className="px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                  />
                  <input
                    type="text"
                    required
                    value={questForm.description}
                    onChange={(e) =>
                      setQuestForm({ ...questForm, description: e.target.value })
                    }
                    placeholder="Quest Description"
                    className="px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <input
                    type="number"
                    required
                    min="1"
                    value={questForm.reward_id}
                    onChange={(e) =>
                      setQuestForm({ ...questForm, reward_id: e.target.value })
                    }
                    placeholder="Reward ID"
                    className="px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                  />
                  <input
                    type="number"
                    required
                    min="1"
                    value={questForm.streak}
                    onChange={(e) =>
                      setQuestForm({
                        ...questForm,
                        streak: parseInt(e.target.value),
                      })
                    }
                    placeholder="Streak Required"
                    className="px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                  />
                  <input
                    type="number"
                    required
                    min="1"
                    value={questForm.duplication}
                    onChange={(e) =>
                      setQuestForm({
                        ...questForm,
                        duplication: parseInt(e.target.value),
                      })
                    }
                    placeholder="Duplication"
                    className="px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                  />
                  <label className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-gray-300 rounded-lg bg-gray-50">
                    <input
                      type="checkbox"
                      checked={questForm.auto_claim}
                      onChange={(e) =>
                        setQuestForm({ ...questForm, auto_claim: e.target.checked })
                      }
                      className="w-5 h-5"
                    />
                    <span className="font-semibold">Auto Claim</span>
                  </label>
                </div>
                <button
                  type="submit"
                  className="w-full bg-green-500 text-white py-3 rounded-lg hover:bg-green-600 transition font-semibold"
                >
                  Create Quest
                </button>
              </form>
            </div>

            {/* Quests List */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-purple-700">Quests List</h2>
                <button
                  onClick={fetchQuests}
                  className="bg-purple-500 text-white px-4 py-2 rounded-lg hover:bg-purple-600 transition"
                >
                  Refresh
                </button>
              </div>
              {quests.length > 0 ? (
                <div className="grid grid-cols-1 gap-4">
                  {quests.map((quest) => (
                    <div
                      key={quest.quest_id}
                      className="border-2 border-green-200 p-4 rounded-lg bg-green-50"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-bold text-lg text-green-700">
                            {quest.name} (ID: {quest.quest_id})
                          </div>
                          <div className="text-gray-700 mt-1">
                            {quest.description}
                          </div>
                          <div className="flex gap-4 mt-2 text-sm">
                            <span className="text-purple-600">
                              Reward ID: {quest.reward_id}
                            </span>
                            <span className="text-blue-600">
                              Streak: {quest.streak}
                            </span>
                            <span className="text-orange-600">
                              {quest.auto_claim ? "Auto-Claim" : "Manual Claim"}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">
                  No quests created yet. Create one above!
                </p>
              )}
            </div>
          </div>
        )}

        {/* Quest System Tab */}
        {activeTab === "quests" && (
          <div className="space-y-6">
            {!token ? (
              <div className="bg-white p-12 rounded-lg shadow-lg text-center">
                <h2 className="text-2xl font-bold text-gray-700 mb-4">
                  Please log in to access quests
                </h2>
                <button
                  onClick={() => setActiveTab("auth")}
                  className="bg-purple-600 text-white px-8 py-3 rounded-lg hover:bg-purple-700 transition font-semibold"
                >
                  Go to Login
                </button>
              </div>
            ) : (
              <>
                {/* Available Quests */}
                <div className="bg-white p-6 rounded-lg shadow-lg">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold text-purple-700">
                      Available Quests
                    </h2>
                    <button
                      onClick={fetchQuests}
                      className="bg-purple-500 text-white px-4 py-2 rounded-lg hover:bg-purple-600 transition"
                    >
                      Refresh
                    </button>
                  </div>
                  {quests.length > 0 ? (
                    <div className="grid grid-cols-1 gap-4">
                      {quests.map((quest) => (
                        <div
                          key={quest.quest_id}
                          className="border-2 border-purple-200 p-4 rounded-lg bg-purple-50"
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="font-bold text-lg text-purple-700">
                                {quest.name}
                              </div>
                              <div className="text-gray-700 mt-1">
                                {quest.description}
                              </div>
                              <div className="flex gap-4 mt-2 text-sm">
                                <span className="text-blue-600">
                                  Complete {quest.streak} times
                                </span>
                                <span className="text-orange-600">
                                  {quest.auto_claim ? "Auto-Claim" : "Manual Claim"}
                                </span>
                              </div>
                            </div>
                            <button
                              onClick={() => assignQuest(quest.quest_id)}
                              className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition font-semibold whitespace-nowrap ml-4"
                            >
                              Assign to Me
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-8">
                      No quests available. Create some in the Admin Panel first!
                    </p>
                  )}
                </div>

                {/* My Quests */}
                <div className="bg-white p-6 rounded-lg shadow-lg">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold text-purple-700">
                      My Quests
                    </h2>
                    <button
                      onClick={fetchUserQuests}
                      className="bg-purple-500 text-white px-4 py-2 rounded-lg hover:bg-purple-600 transition"
                    >
                      Refresh
                    </button>
                  </div>
                  {userQuests.length > 0 ? (
                    <div className="grid grid-cols-1 gap-4">
                      {userQuests.map((uq) => (
                        <div
                          key={`${uq.quest_id}-${uq.user_id}`}
                          className={`border-2 p-4 rounded-lg ${
                            uq.status === "claimed"
                              ? "border-green-300 bg-green-50"
                              : uq.status === "completed"
                              ? "border-yellow-300 bg-yellow-50"
                              : "border-blue-300 bg-blue-50"
                          }`}
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="font-bold text-lg">
                                {uq.name || `Quest ${uq.quest_id}`}
                              </div>
                              <div className="mt-2 space-y-1">
                                <div className="text-sm">
                                  <span className="font-semibold">Status:</span>{" "}
                                  <span className="capitalize font-semibold text-purple-600">
                                    {uq.status}
                                  </span>
                                </div>
                                {uq.progress !== undefined && uq.streak && (
                                  <div className="text-sm">
                                    <span className="font-semibold">Progress:</span>{" "}
                                    <span className="text-blue-600 font-bold">
                                      {uq.progress} / {uq.streak}
                                    </span>
                                  </div>
                                )}
                              </div>
                            </div>
                            <div className="flex gap-2 ml-4">
                              {uq.status === "in_progress" && (
                                <button
                                  onClick={() => completeQuest(uq.quest_id)}
                                  className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition font-semibold whitespace-nowrap"
                                >
                                  Complete Step
                                </button>
                              )}
                              {uq.status === "completed" && (
                                <button
                                  onClick={() => claimQuest(uq.quest_id)}
                                  className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 transition font-semibold whitespace-nowrap"
                                >
                                  Claim Reward
                                </button>
                              )}
                              {uq.status === "claimed" && (
                                <span className="text-green-700 font-bold px-4 py-2">
                                  Claimed!
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-8">
                      You have no quests assigned. Assign some from the Available Quests above!
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* Auth Tab */}
        {activeTab === "auth" && !token && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Signup Form */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h2 className="text-2xl font-bold mb-4 text-purple-700">Sign Up</h2>
              <form onSubmit={handleSignup} className="space-y-4">
                <input
                  type="text"
                  required
                  value={signupData.username}
                  onChange={(e) =>
                    setSignupData({ ...signupData, username: e.target.value })
                  }
                  placeholder="Username"
                  className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                />
                <input
                  type="password"
                  required
                  value={signupData.password}
                  onChange={(e) =>
                    setSignupData({ ...signupData, password: e.target.value })
                  }
                  placeholder="Password"
                  className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                />
                <button
                  type="submit"
                  className="w-full bg-blue-500 text-white py-3 rounded-lg hover:bg-blue-600 transition font-semibold"
                >
                  Sign Up
                </button>
              </form>
            </div>

            {/* Login Form */}
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h2 className="text-2xl font-bold mb-4 text-purple-700">Log In</h2>
              <form onSubmit={handleLogin} className="space-y-4">
                <input
                  type="text"
                  required
                  value={loginData.username}
                  onChange={(e) =>
                    setLoginData({ ...loginData, username: e.target.value })
                  }
                  placeholder="Username"
                  className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                />
                <input
                  type="password"
                  required
                  value={loginData.password}
                  onChange={(e) =>
                    setLoginData({ ...loginData, password: e.target.value })
                  }
                  placeholder="Password"
                  className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
                />
                <button
                  type="submit"
                  className="w-full bg-green-500 text-white py-3 rounded-lg hover:bg-green-600 transition font-semibold"
                >
                  Log In
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
