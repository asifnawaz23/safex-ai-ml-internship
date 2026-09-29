import React from 'react';
import { Database, Brain, Tag, ShieldAlert } from 'lucide-react';

export default function Methodology() {
  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Methodology & About</h1>
        <p className="text-slate-500 mt-1">Understanding the NLP architecture and data boundaries of DentalSense AI.</p>
      </div>

      <div className="space-y-6">
        <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <div className="flex items-center mb-4 text-dental-600">
            <Brain size={24} className="mr-3" />
            <h2 className="text-xl font-bold text-slate-800">1. Sentiment Analysis Model</h2>
          </div>
          <p className="text-slate-600 leading-relaxed mb-4">
            DentalSense AI utilizes the Hugging Face Transformers ecosystem. Specifically, it employs the 
            <code className="bg-slate-100 px-2 py-1 rounded mx-1 text-sm text-pink-600">distilbert-base-uncased-finetuned-sst-2-english</code> 
            model to classify text into sentiment polarities.
          </p>
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 text-sm">
            <strong className="text-slate-800">Neutral Class Strategy:</strong> The base model inherently classifies text strictly as POSITIVE or NEGATIVE. 
            To accommodate real-world ambiguous feedback, we implement an application-level threshold: any prediction yielding a model confidence score of less than 
            <strong> 75.0%</strong> is intercepted and re-classified as <strong>Neutral</strong>.
          </div>
        </section>

        <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <div className="flex items-center mb-4 text-dental-600">
            <Tag size={24} className="mr-3" />
            <h2 className="text-xl font-bold text-slate-800">2. Theme Detection</h2>
          </div>
          <p className="text-slate-600 leading-relaxed">
            Unlike sentiment which is determined by a neural network, <strong>theme detection is strictly rule-based</strong>. 
            This ensures complete explainability and predictability. A lexical matching system scans the feedback against categorized 
            dental dictionaries (e.g., matching "receptionist" to "Staff", or "expensive" to "Pricing"). If no keywords match, the record 
            defaults to the "General" theme.
          </p>
        </section>

        <section className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <div className="flex items-center mb-4 text-dental-600">
            <Database size={24} className="mr-3" />
            <h2 className="text-xl font-bold text-slate-800">3. Synthetic Dataset</h2>
          </div>
          <p className="text-slate-600 leading-relaxed mb-4">
            For demonstration, testing, and portfolio review purposes, a strictly synthetic dataset comprising 100+ simulated feedback records is utilized. 
            This enables full testing of the batch processing engine, charting dynamics, and KPI calculation limits.
          </p>
        </section>

        <section className="bg-white p-6 rounded-xl shadow-sm border border-red-200">
          <div className="flex items-center mb-4 text-red-600">
            <ShieldAlert size={24} className="mr-3" />
            <h2 className="text-xl font-bold text-slate-800">4. Privacy & Limitations</h2>
          </div>
          <ul className="list-disc pl-5 space-y-2 text-slate-600">
            <li><strong>No Real Patient Data:</strong> This application contains zero real Protected Health Information (PHI).</li>
            <li><strong>No Medical Diagnosis:</strong> This is a business analytics tool, not a clinical recommendation engine.</li>
            <li><strong>Domain Adaptation:</strong> The SST-2 model is trained on general English corpus, so highly specific dental jargon may occasionally be misinterpreted compared to a custom-trained healthcare model.</li>
            <li><strong>Confidence ≠ Accuracy:</strong> The statistical confidence score reflects the model's certainty relative to its training distribution, not absolute truth.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
