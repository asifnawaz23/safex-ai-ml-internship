import React, { useState } from 'react';
import { api } from '../services/api';
import { UploadCloud, FileText, CheckCircle, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Batch() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.analyzeBatch(file);
      setResult(res);
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred during upload.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Batch Analysis</h1>
        <p className="text-slate-500 mt-1">Upload a CSV containing multiple feedback records to process them all at once.</p>
      </div>

      <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
        <div 
          className="border-2 border-dashed border-slate-300 rounded-lg p-12 text-center hover:bg-slate-50 transition-colors"
        >
          <UploadCloud className="mx-auto h-12 w-12 text-slate-400 mb-4" />
          <h3 className="text-lg font-medium text-slate-900 mb-1">Upload CSV Document</h3>
          <p className="text-sm text-slate-500 mb-4">Required columns: id, date, feedback</p>
          <input 
            type="file" 
            id="file-upload" 
            className="hidden" 
            accept=".csv" 
            onChange={handleFileChange}
          />
          <label 
            htmlFor="file-upload" 
            className="cursor-pointer bg-dental-600 text-white px-5 py-2.5 rounded-lg hover:bg-dental-700 transition-colors inline-flex items-center"
          >
            Select File
          </label>
        </div>

        {file && (
          <div className="mt-6 flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
            <div className="flex items-center">
              <FileText className="text-dental-500 mr-3" />
              <div>
                <div className="font-medium text-slate-800">{file.name}</div>
                <div className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</div>
              </div>
            </div>
            <button 
              onClick={handleUpload}
              disabled={loading}
              className={`px-4 py-2 rounded-lg font-medium text-white transition-colors ${loading ? 'bg-slate-400' : 'bg-dental-600 hover:bg-dental-700'}`}
            >
              {loading ? 'Processing...' : 'Analyze Now'}
            </button>
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-start">
            <AlertTriangle className="shrink-0 mr-3 mt-0.5" size={20} />
            <div>
              <h4 className="font-medium">Upload Failed</h4>
              <p className="text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {result && (
          <div className="mt-6 p-6 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center text-green-800 mb-4">
              <CheckCircle className="mr-2" size={24} />
              <h3 className="text-lg font-bold">Analysis Complete</h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white p-3 rounded shadow-sm">
                <div className="text-xs text-slate-500">Processed</div>
                <div className="font-bold text-xl">{result.total_processed}</div>
              </div>
              <div className="bg-white p-3 rounded shadow-sm">
                <div className="text-xs text-slate-500">Positive</div>
                <div className="font-bold text-xl text-green-600">{result.positive_count}</div>
              </div>
              <div className="bg-white p-3 rounded shadow-sm">
                <div className="text-xs text-slate-500">Negative</div>
                <div className="font-bold text-xl text-red-600">{result.negative_count}</div>
              </div>
              <div className="bg-white p-3 rounded shadow-sm">
                <div className="text-xs text-slate-500">Avg Confidence</div>
                <div className="font-bold text-xl text-slate-700">{result.average_confidence}%</div>
              </div>
            </div>
            <button
              onClick={() => navigate('/')}
              className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 font-medium transition-colors"
            >
              View Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
