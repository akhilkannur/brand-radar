'use client';

import React, { useState } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Briefcase, 
  Zap, 
  AlertCircle, 
  ExternalLink, 
  ShieldCheck, 
  ArrowLeft,
  ChevronRight,
  Target,
  Lightbulb,
  CheckCircle2
} from 'lucide-react';
import intelligence from '../data/intelligence.json';

const BrandRadarDashboard = () => {
  const [selectedBrand, setSelectedBrand] = useState<any>(null);
  const { scores } = intelligence;

  // Detail View Component
  const BrandDetail = ({ brand, onBack }: { brand: any, onBack: () => void }) => {
    return (
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-indigo-600 font-bold text-sm mb-8 hover:translate-x-[-4px] transition-transform"
        >
          <ArrowLeft size={16} /> Back to Dashboard
        </button>

        <div className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-sm">
          {/* Header Section */}
          <div className="p-8 md:p-12 border-b border-slate-100 bg-slate-50/50">
            <div className="flex flex-col md:flex-row justify-between items-start gap-6">
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="bg-indigo-600 text-white px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider">
                    {brand.category}
                  </span>
                  <span className="text-slate-400 font-bold text-xs uppercase tracking-widest">
                    {brand.stage} Stage
                  </span>
                </div>
                <h2 className="text-5xl font-black text-slate-900 tracking-tight mb-2">{brand.company}</h2>
                <div className="flex items-center gap-4 mt-4">
                  <div className="flex items-center gap-1 text-slate-600 text-sm font-medium">
                    <CheckCircle2 className="w-4 h-4 text-indigo-500" /> {brand.signal_count} Intelligence Signals Detected
                  </div>
                  {brand.trend === 'rising' && (
                    <span className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
                      <TrendingUp size={14} /> Accelerating Momentum
                    </span>
                  )}
                </div>
              </div>
              <div className="text-center md:text-right bg-white p-6 rounded-2xl border border-slate-100 shadow-sm min-w-[160px]">
                <div className="text-5xl font-black text-indigo-600 leading-none mb-1">{brand.score}</div>
                <div className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Intent Score</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
            {/* Main Content Area */}
            <div className="lg:col-span-2 p-8 md:p-12 border-r border-slate-100">
              {/* Strategic Brief */}
              <section className="mb-12">
                <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900 mb-6 uppercase tracking-wider">
                  <Zap className="w-5 h-5 text-indigo-500" /> Strategic Intelligence Brief
                </h3>
                <div className="bg-indigo-50/50 border-l-4 border-indigo-500 p-8 rounded-r-2xl leading-relaxed text-slate-800 text-lg italic font-serif">
                  {brand.insight || "No detailed strategic insight available for this snapshot."}
                </div>
              </section>

              {/* Signals Feed */}
              <section className="mb-12">
                <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900 mb-6 uppercase tracking-wider">
                  <AlertCircle className="w-5 h-5 text-indigo-500" /> Recent Intent Signals
                </h3>
                <div className="space-y-4">
                  {brand.top_signals.map((sig: any, i: number) => (
                    <div key={i} className="bg-white border border-slate-100 p-6 rounded-xl hover:border-indigo-200 transition-colors">
                      <div className="flex justify-between items-start gap-4 mb-2">
                        <h4 className="font-bold text-slate-900 leading-tight">{sig.title}</h4>
                        <span className="bg-slate-50 text-slate-400 text-[10px] font-bold px-2 py-1 rounded whitespace-nowrap uppercase">
                          {sig.signal_type}
                        </span>
                      </div>
                      <p className="text-slate-500 text-sm mb-4 leading-relaxed">{sig.summary}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{sig.source}</span>
                        <a href={sig.url} target="_blank" className="text-indigo-600 text-xs font-bold hover:underline flex items-center gap-1">
                          View Source <ExternalLink size={12} />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            {/* Sidebar / Pitch Angles */}
            <div className="bg-slate-50/30 p-8 md:p-12">
              <section>
                <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900 mb-8 uppercase tracking-wider">
                  <Target className="w-5 h-5 text-indigo-500" /> Agency Action Plan
                </h3>
                <div className="space-y-8">
                  <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm relative">
                    <div className="absolute -top-3 left-6 bg-indigo-600 text-white text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded">
                      The Hook
                    </div>
                    <p className="text-slate-700 text-sm leading-relaxed mt-2 italic font-serif">
                      "Saw the recent developments at <strong>{brand.company}</strong>. High-growth periods like this often put a strain on internal resources—we specialize in scaling GTM for AI leaders."
                    </p>
                  </div>

                  <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
                    <h4 className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-400 mb-4">
                      <Briefcase size={14} className="text-indigo-500" /> Signal Breakdown
                    </h4>
                    <div className="space-y-4">
                      {Object.entries(brand.breakdown).map(([key, val]: [string, any]) => (
                        <div key={key}>
                          <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                            <span>{key.replace('_', ' ')}</span>
                            <span>{Math.round(val)} pts</span>
                          </div>
                          <div className="w-full bg-slate-200 h-1 rounded-full overflow-hidden">
                            <div className="bg-indigo-500 h-full transition-all duration-1000" style={{ width: `${(val / 20) * 100}%` }}></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-indigo-900 p-8 rounded-2xl text-white shadow-xl shadow-indigo-900/20">
                    <Lightbulb className="w-8 h-8 text-indigo-300 mb-4" />
                    <h4 className="text-sm font-black uppercase tracking-widest mb-2 text-indigo-200">Pro Pitch Tip</h4>
                    <p className="text-xs text-indigo-100 leading-relaxed font-medium">
                      Focus your pitch on <strong>speed-to-market</strong>. These AI companies are in an arms race—they care more about moving fast than about lowest cost.
                    </p>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-20">
      {/* HEADER */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => setSelectedBrand(null)}>
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-black italic">B</div>
            <h1 className="text-xl font-bold tracking-tight">Brand <span className="text-indigo-600">Radar</span></h1>
          </div>
          <div className="flex items-center gap-4 text-sm font-medium text-slate-500">
            <span className="hidden md:flex items-center gap-1"><ShieldCheck className="w-4 h-4 text-green-500" /> AI Intent Intelligence</span>
            <span className="bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full text-xs">Updated {intelligence.generated_at ? new Date(intelligence.generated_at).toLocaleDateString() : 'Today'}</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-12">
        {selectedBrand ? (
          <BrandDetail brand={selectedBrand} onBack={() => setSelectedBrand(null)} />
        ) : (
          <>
            {/* HERO */}
            <div className="mb-12">
              <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 mb-4 tracking-tight leading-tight">The AI "Who's Next" Board</h2>
              <p className="text-lg text-slate-600 max-w-2xl leading-relaxed">
                Real-time intent signals for 50 AI leaders. We monitor news and direct company signals to predict which brands are about to spend on agency services.
              </p>
            </div>

            {/* LIST */}
            <div className="space-y-4">
              {scores.map((s, idx) => (
                <div 
                  key={s.company} 
                  onClick={() => setSelectedBrand(s)}
                  className="group bg-white rounded-2xl border border-slate-200 p-6 transition-all hover:border-indigo-400 hover:shadow-xl hover:shadow-indigo-500/10 cursor-pointer overflow-hidden relative"
                >
                  <div className="flex items-center justify-between gap-6">
                    <div className="flex items-center gap-4 min-w-0 flex-1">
                      <div className="text-2xl font-black text-slate-200 min-w-[3rem] text-center group-hover:text-indigo-100 transition-colors">
                        {idx + 1}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-3 mb-1 flex-wrap">
                          <h3 className="text-xl font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{s.company}</h3>
                          <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 bg-slate-50 px-2 py-1 rounded">{s.category}</span>
                          {s.trend === 'rising' ? (
                            <span className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded text-[10px] font-black uppercase"><TrendingUp size={12} /> Rising</span>
                          ) : (
                            <span className="flex items-center gap-1 text-slate-400 bg-slate-50 px-2 py-0.5 rounded text-[10px] font-black uppercase"><TrendingDown size={12} /> Stable</span>
                          )}
                        </div>
                        <p className="text-slate-600 text-sm line-clamp-1 leading-relaxed max-w-2xl">
                          {(s as any).insight ? (s as any).insight.split('. ')[0] : 'Strategic assessment in progress'}...
                        </p>
                        <div className="flex gap-2 mt-4">
                          {Object.keys(s.breakdown).slice(0, 3).map(type => (
                            <span key={type} className="text-[9px] font-black uppercase tracking-wider bg-slate-100 text-slate-500 px-2 py-1 rounded-md">
                              {type.replace('_', ' ')}
                            </span>
                          ))}
                          {Object.keys(s.breakdown).length > 3 && (
                            <span className="text-[9px] font-black uppercase tracking-wider bg-slate-50 text-slate-300 px-2 py-1 rounded-md">
                              +{Object.keys(s.breakdown).length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-8">
                      <div className="text-right">
                        <div className="text-4xl font-black text-slate-900 group-hover:text-indigo-600 transition-colors leading-none mb-1">{s.score}</div>
                        <div className="text-[9px] font-black uppercase tracking-widest text-slate-400">Intent Score</div>
                      </div>
                      <div className="bg-slate-50 p-3 rounded-xl group-hover:bg-indigo-600 transition-all">
                        <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-white transition-colors" />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>

      {/* FOOTER */}
      <footer className="max-w-6xl mx-auto px-4 py-20 text-center border-t border-slate-200 mt-20">
        <p className="text-slate-400 text-sm font-medium tracking-wide">© 2026 Brand Radar Intelligence. Built for AI-Native Operators.</p>
      </footer>
    </div>
  );
};

export default BrandRadarDashboard;
