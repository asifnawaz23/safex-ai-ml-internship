import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

function MetricCard({ title, value, subtitle }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100">
      <h3 className="text-slate-500 text-sm font-medium">{title}</h3>
      <div className="text-3xl font-bold text-slate-800 mt-2">{value}</div>
      {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAnalytics().then(res => {
      setData(res);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-dental-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!data || data.total_reviews === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto">
        <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
          <span className="text-2xl">📊</span>
        </div>
        <h2 className="text-2xl font-bold text-slate-800">No feedback data available yet</h2>
        <p className="text-slate-500 mt-2">
          Analyze individual feedback or upload a CSV to begin generating insights.
        </p>
      </div>
    );
  }

  const sentimentData = [
    { name: 'Positive', value: data.positive_count, color: '#10b981' },
    { name: 'Neutral', value: data.neutral_count, color: '#94a3b8' },
    { name: 'Negative', value: data.negative_count, color: '#ef4444' }
  ];

  const themeData = Object.keys(data.theme_counts).map(key => ({
    name: key,
    count: data.theme_counts[key]
  })).sort((a, b) => b.count - a.count);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Analytics Overview</h1>
          <p className="text-slate-500 mt-1">Aggregated insights from patient feedback</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Total Reviews" value={data.total_reviews} />
        <MetricCard title="Positive Rate" value={`${data.positive_percentage}%`} />
        <MetricCard title="Negative Rate" value={`${data.negative_percentage}%`} />
        <MetricCard title="Avg Confidence" value={`${data.average_confidence}%`} subtitle="Model confidence" />
      </div>

      {data.insights && data.insights.length > 0 && (
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
          <h3 className="text-blue-800 font-semibold mb-2">Automated Insights</h3>
          <ul className="list-disc pl-5 space-y-1">
            {data.insights.map((insight, i) => (
              <li key={i} className="text-blue-700 text-sm">{insight}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-bold text-slate-800 mb-6">Sentiment Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={sentimentData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                  isAnimationActive={false}
                >
                  {sentimentData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 mt-2">
            {sentimentData.map(s => (
              <div key={s.name} className="flex items-center text-sm text-slate-600">
                <span className="w-3 h-3 rounded-full mr-2" style={{backgroundColor: s.color}}></span>
                {s.name} ({s.value})
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-bold text-slate-800 mb-6">Feedback by Theme</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={themeData} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} fontSize={12} />
                <RechartsTooltip cursor={{fill: '#f1f5f9'}} />
                <Bar dataKey="count" fill="#0ea5e9" radius={[0, 4, 4, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
