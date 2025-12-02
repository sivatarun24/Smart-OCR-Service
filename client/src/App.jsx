import React, { useEffect, useState } from 'react'
import UploadArea from './components/UploadArea'
import JobCard from './components/JobCard'
import SearchBar from './components/SearchBar'
import SearchResults from './components/SearchResults'
import LoginForm from './components/LoginForm'
import RegisterForm from './components/RegisterForm'
import { getStatus, searchDocs, getDownloadUrl } from './api'


export default function App() {
  const [showRegister, setShowRegister] = useState(false)
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user')
    return saved ? JSON.parse(saved) : null
  })
  // Use a user-specific key for jobs
  const getJobsKey = (u) => u ? `jobs_${u.username}` : null
  const [jobs, setJobs] = useState(() => {
    const savedUser = localStorage.getItem('user')
    if (!savedUser) return []
    const userObj = JSON.parse(savedUser)
    const jobsKey = getJobsKey(userObj)
    const savedJobs = localStorage.getItem(jobsKey)
    return savedJobs ? JSON.parse(savedJobs) : []
  })
  const [results, setResults] = useState([])

  // Persist user info
  useEffect(() => { localStorage.setItem('user', JSON.stringify(user)) }, [user])
  // Persist jobs for the current user
  useEffect(() => {
    if (user) {
      localStorage.setItem(getJobsKey(user), JSON.stringify(jobs))
    }
  }, [jobs, user])

  useEffect(() => {
    if (!user) return
    const interval = setInterval(async () => {
      const updated = await Promise.all(jobs.map(async j => {
        if (['COMPLETED','FAILED'].includes(j.status)) return j
        const s = await getStatus(j.id).catch(() => null)
        return s ? {...j, ...s} : j
      }))
      setJobs(updated)
    }, 1500)
    return () => clearInterval(interval)
  }, [jobs, user])

  const handleSearch = async (q) => {
    const items = await searchDocs(q)
    setResults(items)
  }

  const handleDownload = async (id) => {
    try {
      const url = await getDownloadUrl(id)
      window.location.href = url
    } catch {
      alert('Download not available yet.')
    }
  }

  const handleLogin = (userObj) => {
    setUser(userObj)
    // On login, load jobs for this user
    const jobsKey = getJobsKey(userObj)
    const savedJobs = localStorage.getItem(jobsKey)
    setJobs(savedJobs ? JSON.parse(savedJobs) : [])
  }

  const handleLogout = () => {
    setUser(null)
    setJobs([])
    localStorage.removeItem('user')
  }

  const handleClearJobs = () => {
    if (user) {
      localStorage.removeItem(getJobsKey(user))
      setJobs([])
    }
  }

  if (!user) {
    if (showRegister) {
      return <RegisterForm onRegister={() => setShowRegister(false)} onSwitchToLogin={() => setShowRegister(false)} />
    }
    return <LoginForm onLogin={handleLogin} onSwitchToRegister={() => setShowRegister(true)} />
  }

  return (
    <div className="container">
      <header>
        <h1>Smart OCR & Tagging</h1>
        <p>Upload, extract, tag, search and download your documents.</p>
        <div className="user-info">
          <span>Welcome, {user.username}!</span>
          <button onClick={handleLogout} style={{marginLeft:8}}>Logout</button>
          <button onClick={handleClearJobs} style={{marginLeft:8, background:'#26306b'}}>Clear Jobs</button>
        </div>
      </header>

      <UploadArea onNewJob={(job) => setJobs([job, ...jobs])} />

      <SearchBar onSearch={handleSearch} />
      <SearchResults items={results} onDownload={handleDownload} />

      <section className="jobs">
        {jobs.length === 0 && <p className="empty">No jobs yet. Upload a file to begin.</p>}
        {jobs.map(job => <JobCard key={job.id} job={job} />)}
      </section>
    </div>
  )
}