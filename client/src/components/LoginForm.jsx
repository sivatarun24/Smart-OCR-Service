
import React, { useState } from 'react'
import axios from 'axios';

export default function LoginForm({ onLogin, onSwitchToRegister, onForgotPassword }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username || !password) {
      setError('Please enter username and password.');
      return;
    }
    try {
      const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8080';
      console.log('API_BASE_URL set to:', API_BASE_URL);
      const res = await axios.post(`${API_BASE_URL}/api/login`, { username, password });
      if (onLogin) onLogin(res.data.user);
    } catch (err) {
      setError(err?.response?.data?.error || 'Login failed');
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
      <h1 style={{ marginBottom: 32, fontWeight: 700, fontSize: 32, color: '#26306b', letterSpacing: 1 }}>Smart OCR Service</h1>
      <div className="card" style={{ maxWidth: 480, margin: '40px auto', padding: '48px 40px', boxSizing: 'border-box' }}>
        <form onSubmit={handleSubmit}>
          <h2 style={{ textAlign: 'center', marginBottom: 24 }}>Login</h2>
          {error && <div className="error" style={{ marginBottom: 16 }}>{error}</div>}
          <div className="row" style={{ marginBottom: 20 }}>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoFocus
              style={{ flex: 1, padding: '16px 18px', borderRadius: 14, border: '1.5px solid #26306b', background:'#0e142b', color:'#c9d0ff', fontSize: 18 }}
            />
          </div>
          <div className="row" style={{ marginBottom: 32 }}>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              style={{ flex: 1, padding: '16px 18px', borderRadius: 14, border: '1.5px solid #26306b', background:'#0e142b', color:'#c9d0ff', fontSize: 18 }}
            />
          </div>
          <button type="submit" style={{ width: '100%', padding: '14px 0', fontSize: 18, marginBottom: 8 }}>Login</button>
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <button type="button" style={{ background: 'none', color: '#4b61ff', textDecoration: 'underline', padding: 0, fontSize: 15 }} onClick={onForgotPassword}>Forgot Password?</button>
          </div>
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <span>Don't have an account? </span>
            <button type="button" style={{ background: 'none', color: '#4b61ff', textDecoration: 'underline', padding: 0 }} onClick={onSwitchToRegister}>Register</button>
          </div>
        </form>
      </div>
    </div>
  )
}
