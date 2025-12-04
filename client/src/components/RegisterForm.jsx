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
    <div className="card register-card">
      <form className="register-form" onSubmit={handleSubmit}>
        <h2 className="register-title">Register</h2>
        {error && <div className="error register-error">{error}</div>}
        {success && <div className="register-success">{success}</div>}
        <div className="row register-row">
          <input
            type="text"
            name="username"
            placeholder="Username"
            value={form.username}
            onChange={handleChange}
            autoFocus
            className="register-input"
          />
        </div>
        <div className="row register-row">
          <input
            type="email"
            name="email"
            placeholder="Email"
            value={form.email}
            onChange={handleChange}
            className="register-input"
          />
        </div>
        <div className="row register-row">
          <input
            type="text"
            name="name"
            placeholder="Full Name"
            value={form.name}
            onChange={handleChange}
            className="register-input"
          />
        </div>
        <div className="row register-row">
          <input
            type="password"
            name="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
            className="register-input"
          />
        </div>
        <div className="row register-row">
          <input
            type="password"
            name="confirmPassword"
            placeholder="Confirm Password"
            value={form.confirmPassword}
            onChange={handleChange}
            className="register-input"
          />
        </div>
        <button className="register-btn" type="submit" disabled={loading}>{loading ? 'Registering...' : 'Register'}</button>
        <div className="register-switch">
          <span>Already have an account? </span>
          <button type="button" className="register-link" onClick={onSwitchToLogin}>Login</button>
        </div>
      </form>
    </div>
  )
}
