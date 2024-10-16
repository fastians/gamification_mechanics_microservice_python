// src/components/UserManagement.js

import React, { useState, useEffect } from "react";
import axios from "axios";

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [userName, setUserName] = useState("");
  const [userStatus, setUserStatus] = useState("");

  const axiosInstance = axios.create({
    baseURL: "http://localhost:8000",
  });

  useEffect(() => {
    fetchUsers();
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

  const addUser = async () => {
    try {
      await axiosInstance.post("/users", {
        user_name: userName,
        status: parseInt(userStatus),
      });
      setUserName("");
      setUserStatus("");
      fetchUsers();
    } catch (error) {
      console.error("Error adding user:", error);
    }
  };

  return (
    <div className="mb-10">
      <h2 className="text-2xl font-semibold mb-4">User Management</h2>
      <div className="mb-4">
        <input
          type="text"
          value={userName}
          onChange={(e) => setUserName(e.target.value)}
          placeholder="User Name"
          className="border rounded-md p-2 mr-2"
        />
        <input
          type="text"
          value={userStatus}
          onChange={(e) => setUserStatus(e.target.value)}
          placeholder="User Status"
          className="border rounded-md p-2 mr-2"
        />
        <button
          onClick={addUser}
          className="bg-blue-500 text-white p-2 rounded-md"
        >
          Add User
        </button>
      </div>
      {users.length > 0 ? (
        <ul className="list-disc pl-5">
          {users.map((user) => (
            <li key={user.user_id} className="mb-1">
              {user.user_name} (Status: {user.status})
            </li>
          ))}
        </ul>
      ) : (
        <p>No users found.</p>
      )}
    </div>
  );
};

export default UserManagement;
