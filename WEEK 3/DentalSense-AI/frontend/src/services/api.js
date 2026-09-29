import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export const api = {
  health: async () => {
    const res = await axios.get('http://localhost:8000/health');
    return res.data;
  },
  analyzeSingle: async (feedbackText) => {
    const res = await axios.post(`${API_BASE_URL}/analyze`, { feedback: feedbackText });
    return res.data;
  },
  analyzeBatch: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await axios.post(`${API_BASE_URL}/analyze/batch`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },
  getAnalytics: async () => {
    const res = await axios.get(`${API_BASE_URL}/analytics`);
    return res.data;
  },
  getFeedback: async () => {
    const res = await axios.get(`${API_BASE_URL}/feedback`);
    return res.data;
  },
  getThemes: async () => {
    const res = await axios.get(`${API_BASE_URL}/themes`);
    return res.data;
  }
};
