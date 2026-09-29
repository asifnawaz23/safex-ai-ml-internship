import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, Upload, Search, Info } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Analyzer from './pages/Analyzer';
import Batch from './pages/Batch';
import Explorer from './pages/Explorer';
import Methodology from './pages/Methodology';

function Sidebar() {
  const links = [
    { to: '/', icon: <LayoutDashboard size={20} />, label: 'Dashboard' },
    { to: '/analyze', icon: <MessageSquare size={20} />, label: 'Feedback Analyzer' },
    { to: '/batch', icon: <Upload size={20} />, label: 'Batch Analysis' },
    { to: '/explore', icon: <Search size={20} />, label: 'Feedback Explorer' },
    { to: '/methodology', icon: <Info size={20} />, label: 'Methodology' },
  ];

  return (
    <div className="w-64 bg-dental-900 text-white min-h-screen p-4 flex flex-col">
      <div className="flex items-center mb-8 mt-2">
        <div className="w-8 h-8 rounded bg-dental-500 flex items-center justify-center mr-3 font-bold text-white">
          DS
        </div>
        <h1 className="text-xl font-bold tracking-wide">DentalSense AI</h1>
      </div>
      <nav className="flex-1 space-y-2">
        {links.map(link => (
          <Link 
            key={link.to} 
            to={link.to} 
            className="flex items-center p-3 rounded-lg hover:bg-dental-600 transition-colors"
          >
            <span className="mr-3">{link.icon}</span>
            {link.label}
          </Link>
        ))}
      </nav>
      <div className="text-xs text-dental-500 pt-4 border-t border-dental-600">
        MVP v1.0.0
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-slate-50 font-sans text-slate-800">
        <Sidebar />
        <main className="flex-1 p-8 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analyze" element={<Analyzer />} />
            <Route path="/batch" element={<Batch />} />
            <Route path="/explore" element={<Explorer />} />
            <Route path="/methodology" element={<Methodology />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
