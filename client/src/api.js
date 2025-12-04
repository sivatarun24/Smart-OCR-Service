
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'
console.log('API_BASE set to:', API_BASE)

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  try {
    console.log('Uploading file:', file)
    const { data } = await axios.post(`${API_BASE}/api/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    console.log('Upload response:', data)
    return data // { job_id }
  } catch (error) {
    console.error('Error uploading file:', error)
    throw error
  }
}

export async function getStatus(jobId) {
  try {
    console.log('Fetching status for job:', jobId)
    const { data } = await axios.get(`${API_BASE}/api/status/${jobId}`)
    console.log('Status response:', data)
    return data
  } catch (error) {
    console.error('Error fetching status:', error)
    return { error: true, message: error.message }
  }
}

export async function getResult(jobId) {
  try {
    console.log('Fetching result for job:', jobId)
    const { data } = await axios.get(`${API_BASE}/api/result/${jobId}`)
    console.log('Result response:', data)
    return data
  } catch (error) {
    console.error('Error fetching result:', error)
    return { error: true, message: error.message }
  }
}

export async function searchDocs(q) {
  try {
    console.log('Searching docs with query:', q)
    const { data } = await axios.get(`${API_BASE}/api/search`, { params: { q } })
    console.log('Search response:', data)
    return data.results || []
  } catch (error) {
    console.error('Error searching docs:', error)
    return []
  }
}

export async function getDownloadUrl(jobId) {
  try {
    console.log('Getting download URL for job:', jobId)
    const { data } = await axios.get(`${API_BASE}/api/download/${jobId}`)
    console.log('Download URL response:', data)
    return data.url
  } catch (error) {
    console.error('Error getting download URL:', error)
    return null
  }
}