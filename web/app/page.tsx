import React from 'react';
import { TrendingUp, TrendingDown, Briefcase, Zap, AlertCircle, ExternalLink, ShieldCheck } from 'lucide-react';
import intelligence from '../data/intelligence.json';

const BrandRadarDashboard = () => {
  const { scores } = intelligence;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* HEADER */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-black italic">B</div>
            <h1 className="text-xl font-bold tracking-tight">Brand <span className="text-indigo-600">Radar</span></h1>
          </div>
          <div className="flex items-center gap-4 text-sm font-medium text-slate-500">
            <span className="flex items-center gap-1"><ShieldCheck className="w-4 h-4 text-green-500" /> AI Intent Intelligence</span>
            <span className="bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full text-xs">Updated {intelligence.generated_at ? new Date(intelligence.generated_at).toLocaleDateString() : 'Today'}</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-12">
        {/* HERO */}
        <div className="mb-12">
          <h2 className="text-4xl font-extrabold text-slate-900 mb-4 tracking-tight">The AI "Who's Next" Board</h2>
          <p className="text-lg text-slate-600 max-w-2xl leading-relaxed">
            Real-time intent signals for 50 AI leaders. We monitor news and direct company signals to predict which brands are about to spend on agency services.
          </p>
        </div>

        {/* LIST */}
        <div className="space-y-4">
          {scores.map((s, idx) => (
            <div key={s.company} className="group bg-white rounded-xl border border-slate-200 p-6 transition-all hover:border-indigo-400 hover:shadow-xl hover:shadow-indigo-500/10 cursor-pointer">
              <div className="flex items-center justify-between gap-6">
                <div className="flex items-center gap-4 min-w-0 flex-1">
                  <div className="text-2xl font-black text-slate-200 min-w-[3rem] text-center group-hover:text-indigo-100 transition-colors">
                    {idx + 1}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-xl font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{s.company}</h3>
                      <span className="text-xs font-bold uppercase tracking-widest text-slate-400">{s.category}</span>
                      {s.trend === 'rising' ? (
                        <span className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded text-[10px] font-black uppercase"><TrendingUp size={12} /> Rising</span>
                      ) : (
                        <span className="flex items-center gap-1 text-slate-400 bg-slate-50 px-2 py-0.5 rounded text-[10px] font-black uppercase"><TrendingDown size={12} /> Stable</span>
                      )}
                    </div>
                    <p className="text-slate-600 text-sm line-clamp-1 leading-relaxed">
                      {(s as any).insight ? (s as any).insight.split('. ')[0] : 'Strategic assessment in progress'}.
                    </p>
                    <div className="flex gap-2 mt-3">
                      {Object.keys(s.breakdown).map(type => (
                        <span key={type} className="text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-500 px-2 py-1 rounded">
                          {type.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-8">
                  <div className="text-right">
                    <div className="text-3xl font-black text-slate-900 group-hover:text-indigo-600 transition-colors">{s.score}</div>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Intent Score</div>
                  </div>
                  <div className="bg-slate-50 p-2 rounded-lg group-hover:bg-indigo-50 transition-colors">
                    <ExternalLink className="w-5 h-5 text-slate-300 group-hover:text-indigo-500 transition-colors" />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* FOOTER */}
      <footer className="max-w-6xl mx-auto px-4 py-20 text-center border-t border-slate-200 mt-20">
        <p className="text-slate-400 text-sm">© 2026 Brand Radar Intelligence. Powered by Firehose & Crawl4AI.</p>
      </footer>
    </div>
  );
};

export default BrandRadarDashboard;
