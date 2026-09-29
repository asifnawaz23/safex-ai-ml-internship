import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function Explorer() {
  const [feedback, setFeedback] = useState([]);
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [sentimentFilter, setSentimentFilter] = useState('All');
  const [themeFilter, setThemeFilter] = useState('All');
  const [search, setSearch] = useState('');

  useEffect(() => {
    Promise.all([api.getFeedback(), api.getThemes()])
      .then(([feedbackRes, themesRes]) => {
        setFeedback(feedbackRes.data);
        setThemes(themesRes.themes);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const filteredData = feedback.filter(item => {
    const matchSentiment = sentimentFilter === 'All' || item.sentiment === sentimentFilter;
    const matchTheme = themeFilter === 'All' || item.theme === themeFilter;
    const matchSearch = search === '' || item.feedback.toLowerCase().includes(search.toLowerCase());
    return matchSentiment && matchTheme && matchSearch;
  });

  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case 'Positive': return 'bg-green-100 text-green-800 border-green-200';
      case 'Negative': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-dental-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Feedback Explorer</h1>
        <p className="text-slate-500 mt-1">Search, filter, and review analyzed patient feedback.</p>
      </div>

      <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex flex-col md:flex-row gap-4 items-center">
        <div className="flex-1 w-full">
          <input 
            type="text" 
            placeholder="Search feedback text..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-dental-500 outline-none"
          />
        </div>
        
        <select 
          className="px-4 py-2 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-dental-500 min-w-[150px]"
          value={sentimentFilter}
          onChange={(e) => setSentimentFilter(e.target.value)}
        >
          <option value="All">All Sentiments</option>
          <option value="Positive">Positive</option>
          <option value="Neutral">Neutral</option>
          <option value="Negative">Negative</option>
        </select>

        <select 
          className="px-4 py-2 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-dental-500 min-w-[150px]"
          value={themeFilter}
          onChange={(e) => setThemeFilter(e.target.value)}
        >
          <option value="All">All Themes</option>
          {themes.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 text-slate-600 text-sm border-b border-slate-200">
                <th className="py-3 px-6 font-medium">Date</th>
                <th className="py-3 px-6 font-medium">Feedback</th>
                <th className="py-3 px-6 font-medium text-center">Sentiment</th>
                <th className="py-3 px-6 font-medium text-center">Conf.</th>
                <th className="py-3 px-6 font-medium text-center">Theme</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {filteredData.length === 0 ? (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-500">
                    No feedback records match the current filters.
                  </td>
                </tr>
              ) : (
                filteredData.map((item, i) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-6 text-slate-500 whitespace-nowrap">{item.date}</td>
                    <td className="py-3 px-6 text-slate-800 max-w-md truncate" title={item.feedback}>
                      {item.feedback}
                    </td>
                    <td className="py-3 px-6 text-center">
                      <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium border ${getSentimentColor(item.sentiment)}`}>
                        {item.sentiment}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-center text-slate-600">{item.confidence}%</td>
                    <td className="py-3 px-6 text-center">
                      <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-blue-50 text-blue-800 border border-blue-100">
                        {item.theme}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="p-4 border-t border-slate-200 text-xs text-slate-500">
          Showing {filteredData.length} of {feedback.length} records.
        </div>
      </div>
    </div>
  );
}
