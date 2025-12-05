import React, { useState } from 'react';
import axios from 'axios';

export default function RegisterForm({ onRegister, onSwitchToLogin }) {
  const [form, setForm] = useState({
    username: '',
    email: '',
    name: '',
    password: '',
    confirmPassword: ''
  })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (!form.username || !form.email || !form.name || !form.password || !form.confirmPassword) {
      setError('Please fill in all fields.')
      return
    }
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8080';
      const res = await axios.post(`${API_BASE_URL}/api/register`, {
        username: form.username,
        email: form.email,
        name: form.name,
        password: form.password
      })
      setSuccess('Registration successful! You can now log in.')
      setForm({ username: '', email: '', name: '', password: '', confirmPassword: '' })
      if (onRegister) onRegister()
    } catch (err) {
      setError(err?.response?.data?.error || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', width: '100vw', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
      <style>{`
        .star {
          position: absolute;
          border-radius: 50%;
          box-shadow: 0 0 8px 2px #fff, 0 0 24px 4px #6ee2f5;
          opacity: 0.8;
          width: 2px;
          height: 2px;
          animation: glow 2.5s infinite ease-in-out;
        }
        @keyframes glow {
          0%, 100% { opacity: 0.8; box-shadow: 0 0 8px 2px #fff, 0 0 24px 4px #6ee2f5; }
          50% { opacity: 0.2; box-shadow: 0 0 16px 6px #fff, 0 0 32px 8px #fbc2eb; }
        }
      `}</style>
      {/* Stars */}
      {[...Array(50)].map((_, i) => (
        <div
          key={i}
          className="star"
          style={{
            top: `${Math.random() * 100}%`,
            left: `${Math.random() * 100}%`,
            width: `${1 + Math.random() * 2}px`,
            height: `${1 + Math.random() * 2}px`,
            animationDelay: `${Math.random() * 2.5}s`
          }}
        />
      ))}
      <h1
        style={{
          marginBottom: 32,
          fontWeight: 700,
          fontSize: 32,
          color: '#26306b',
          letterSpacing: 1,
          textShadow: '0 2px 12px #fff6',
          background: 'rgba(204, 188, 236, 0.85)',
          borderRadius: 16,
          padding: '12px 32px',
          boxShadow: '0 2px 16px #26306b22',
          display: 'inline-block'
        }}
      >Smart OCR Service</h1>
      <div className="card register-card" style={{ padding: '40px 36px', margin: '32px', minWidth: 400, boxSizing: 'border-box', boxShadow: '0 8px 32px #26306b22', borderRadius: 18 }}>
        <form className="register-form" onSubmit={handleSubmit} style={{ padding: '10px 0', margin: '0 8px' }}>
          <h2 className="register-title" style={{ marginBottom: 24 }}>Register</h2>
          {error && <div className="error register-error">{error}</div>}
          {success && <div className="register-success">{success}</div>}
          <div className="row register-row" style={{ marginBottom: 18 }}>
            <input
              id="username"
              type="text"
              name="username"
              placeholder="Username"
              value={form.username}
              onChange={handleChange}
              autoFocus
              className="register-input"
              style={{ padding: '12px 14px', fontSize: 16 }}
            />
          </div>
          <div className="row register-row" style={{ marginBottom: 18 }}>
            <input
              id="email"
              type="email"
              name="email"
              placeholder="Email"
              value={form.email}
              onChange={handleChange}
              className="register-input"
              style={{ padding: '12px 14px', fontSize: 16 }}
            />
          </div>
          <div className="row register-row" style={{ marginBottom: 18 }}>
            <input
              id="name"
              type="text"
              name="name"
              placeholder="Full Name"
              value={form.name}
              onChange={handleChange}
              className="register-input"
              style={{ padding: '12px 14px', fontSize: 16 }}
            />
          </div>
          <div className="row register-row" style={{ marginBottom: 18 }}>
            <input
              id="password"
              type="password"
              name="password"
              placeholder="Password"
              value={form.password}
              onChange={handleChange}
              className="register-input"
              style={{ padding: '12px 14px', fontSize: 16 }}
            />
          </div>
          <div className="row register-row" style={{ marginBottom: 18 }}>
            <input
              id="confirmPassword"
              type="password"
              name="confirmPassword"
              placeholder="Confirm Password"
              value={form.confirmPassword}
              onChange={handleChange}
              className="register-input"
              style={{ padding: '12px 14px', fontSize: 16 }}
            />
          </div>
          <button className="register-btn" type="submit" disabled={loading} style={{ padding: '12px 0', fontSize: 16, marginTop: 10 }}>{loading ? 'Registering...' : 'Register'}</button>
          <div className="register-switch" style={{ marginTop: 18 }}>
            <span>Already have an account? </span>
            <button type="button" className="register-link" onClick={onSwitchToLogin}>Login</button>
          </div>
        </form>
      </div>
    </div>
  )
}
