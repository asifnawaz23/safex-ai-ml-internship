import React, { useState } from 'react';
import { api } from '../services/api';
import { MessageSquare, AlertCircle } from 'lucide-react';

export default function Analyzer() {
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!feedback.trim()) {
      setError("Please enter feedback to analyze.");
      return;
    }
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const res = await api.analyzeSingle(feedback);
      setResult(res);
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred during analysis.");
    } finally {
      setLoading(false);
    }
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case 'Positive': return 'bg-green-100 text-green-800 border-green-200';
      case 'Negative': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Feedback Analyzer</h1>
        <p className="text-slate-500 mt-1">Paste a single piece of patient feedback for instant analysis.</p>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Patient Feedback
        </label>
        <textarea
          rows={5}
          className="w-full p-4 border border-slate-300 rounded-lg focus:ring-2 focus:ring-dental-500 focus:border-dental-500 outline-none transition-shadow resize-none text-slate-800"
          placeholder="e.g. The dentist explained everything clearly and was very professional, but I had to wait 30 minutes in the waiting room."
          value={feedback}
          onChange={(e) => {
            setFeedback(e.target.value);
            if (error) setError(null);
          }}
        />
        
        {error && (
          <div className="mt-3 flex items-center text-sm text-red-600 bg-red-50 p-2 rounded">
            <AlertCircle size={16} className="mr-2" />
            {error}
          </div>
        )}
        
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleAnalyze}
            disabled={loading || !feedback.trim()}
            className={`px-6 py-2.5 rounded-lg font-medium text-white transition-colors flex items-center
              ${loading || !feedback.trim() ? 'bg-slate-400 cursor-not-allowed' : 'bg-dental-600 hover:bg-dental-700'}
            `}
          >
            {loading && <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></span>}
            {loading ? 'Analyzing...' : 'Analyze Feedback'}
          </button>
        </div>
      </div>

      {result && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 animate-in slide-in-from-bottom-4 fade-in duration-300">
          <h3 className="text-lg font-semibold text-slate-800 border-b pb-3 mb-4 flex items-center">
            <MessageSquare size={18} className="mr-2 text-dental-500" />
            Analysis Results
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="col-span-1 md:col-span-3 bg-slate-50 p-4 rounded-lg italic text-slate-700 border border-slate-100">
              &quot;{result.feedback}&quot;
            </div>
            
            <div className="space-y-1">
              <div className="text-sm text-slate-500 font-medium">Sentiment</div>
              <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${getSentimentColor(result.sentiment)}`}>
                {result.sentiment}
              </div>
            </div>
            
            <div className="space-y-1">
              <div className="text-sm text-slate-500 font-medium">Confidence</div>
              <div className="text-xl font-bold text-slate-800">
                {result.confidence}%
              </div>
            </div>
            
            <div className="space-y-1">
              <div className="text-sm text-slate-500 font-medium">Detected Theme</div>
              <div className="inline-block px-3 py-1 rounded text-sm font-medium bg-blue-50 text-blue-800 border border-blue-200">
                {result.theme}
              </div>
            </div>
            
            <div className="col-span-1 md:col-span-3 text-xs text-slate-400 mt-2 text-right">
              Analyzed at {new Date(result.analyzed_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
