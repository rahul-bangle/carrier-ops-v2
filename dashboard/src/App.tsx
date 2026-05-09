import React, { useEffect, useState } from 'react';
import { supabase } from './lib/supabase';
import { 
  LayoutDashboard, 
  Search, 
  Briefcase, 
  CheckCircle, 
  XCircle, 
  ExternalLink, 
  FileText,
  Clock,
  ChevronRight
} from 'lucide-react';

interface Lead {
  id: number;
  company: string;
  role: string;
  score: string;
  url: string;
  description: string;
  cluster: string;
  dm_draft: string;
  status: string;
  created_at: string;
}

const STATUS_COLUMNS = ['Pending', 'Applied', 'Interviewing', 'Rejected'];

function App() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ scraped: 0, highMatch: 0 });
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, []);

  async function fetchLeads() {
    setLoading(true);
    const { data, error } = await supabase
      .from('leads')
      .select('*')
      .order('created_at', { ascending: false });
    
    if (error) console.error('Error fetching leads:', error);
    else setLeads(data || []);
    setLoading(false);
  }

  async function fetchStats() {
    const today = new Date().toISOString().split('T')[0];
    const { data, error } = await supabase
      .from('daily_stats')
      .select('*')
      .eq('date', today)
      .single();
    
    if (!error && data) {
      setStats({
        scraped: data.scraped_count,
        highMatch: data.high_match_count
      });
    } else {
      setStats({ scraped: 0, highMatch: 0 });
    }
  }

  async function updateStatus(id: number, newStatus: string) {
    const { error } = await supabase
      .from('leads')
      .update({ status: newStatus })
      .eq('id', id);
    
    if (error) console.error('Error updating status:', error);
    else fetchLeads();
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <LayoutDashboard className="w-8 h-8 text-indigo-600" />
            <h1 className="text-2xl font-bold tracking-tight m-0">Career-Ops Dashboard</h1>
          </div>
          
          <div className="flex items-center space-x-6">
            <div className="flex flex-col items-end">
              <span className="text-sm text-gray-500 uppercase font-semibold">Scraped Today</span>
              <span className="text-xl font-bold text-gray-900">{stats.scraped}</span>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-sm text-gray-500 uppercase font-semibold">Gold Leads</span>
              <span className="text-xl font-bold text-indigo-600">{stats.highMatch}</span>
            </div>
            <button 
              onClick={() => { fetchLeads(); fetchStats(); }}
              className="p-2 text-gray-400 hover:text-indigo-600 transition-colors"
            >
              <Clock className="w-6 h-6" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {STATUS_COLUMNS.map(column => (
              <div key={column} className="flex flex-col space-y-4">
                <div className="flex items-center justify-between px-2">
                  <h2 className="text-lg font-semibold text-gray-700 m-0">{column}</h2>
                  <span className="bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full text-xs font-bold">
                    {leads.filter(l => l.status === column).length}
                  </span>
                </div>
                
                <div className="flex-1 space-y-4 min-h-[500px]">
                  {leads
                    .filter(l => l.status === (column === 'Pending' ? 'Pending' : column))
                    .filter(l => l.status === column)
                    .map(lead => (
                      <div 
                        key={lead.id} 
                        className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow group"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                            {lead.score}
                          </span>
                          <span className="text-xs text-gray-400">{lead.cluster}</span>
                        </div>
                        
                        <h3 className="text-lg font-bold text-gray-900 mb-1 leading-tight">{lead.company}</h3>
                        <p className="text-sm text-gray-600 mb-4">{lead.role}</p>
                        
                        <div className="flex items-center space-x-2 mt-4 pt-4 border-t border-gray-100">
                          <a 
                            href={lead.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="p-1.5 text-gray-400 hover:text-indigo-600 transition-colors"
                            title="Open JD"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                          <button 
                            onClick={() => setSelectedLead(lead)}
                            className="p-1.5 text-gray-400 hover:text-indigo-600 transition-colors"
                            title="View Details"
                          >
                            <FileText className="w-4 h-4" />
                          </button>
                          
                          <div className="flex-1" />
                          
                          {column === 'Pending' && (
                            <button 
                              onClick={() => updateStatus(lead.id, 'Applied')}
                              className="text-xs font-semibold text-indigo-600 hover:bg-indigo-50 px-2 py-1 rounded transition-colors"
                            >
                              Mark Applied
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Detail Modal */}
      {selectedLead && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <div>
                <h2 className="text-xl font-bold text-gray-900 m-0">{selectedLead.company}</h2>
                <p className="text-sm text-gray-500 m-0">{selectedLead.role}</p>
              </div>
              <button 
                onClick={() => setSelectedLead(null)}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
              >
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-8">
              <div>
                <h3 className="text-xs uppercase font-bold text-gray-400 mb-3 tracking-widest">AI DM Draft</h3>
                <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-5 text-indigo-900 text-sm italic whitespace-pre-wrap leading-relaxed shadow-inner">
                  {selectedLead.dm_draft || 'No draft generated.'}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs uppercase font-bold text-gray-400 m-0 tracking-widest">Job Description</h3>
                  <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded uppercase tracking-tighter">Read Only</span>
                </div>
                <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed font-normal bg-gray-50/30 rounded-xl p-5 border border-gray-100">
                  {selectedLead.description}
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-100 bg-gray-50/50 flex justify-between items-center">
              <div className="flex items-center space-x-6">
                <div className="flex flex-col">
                  <span className="text-[10px] uppercase font-bold text-gray-400 tracking-tighter">Lead ID</span>
                  <span className="text-xs font-mono text-gray-600">#{selectedLead.id}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] uppercase font-bold text-gray-400 tracking-tighter">Archetype</span>
                  <span className="text-xs text-gray-600">{selectedLead.cluster}</span>
                </div>
              </div>
              <div className="flex space-x-3">
                <button 
                  className="px-5 py-2.5 bg-white border border-gray-200 text-gray-700 rounded-xl font-bold text-sm hover:border-indigo-300 hover:text-indigo-600 transition-all shadow-sm flex items-center space-x-2"
                  onClick={() => alert('PDF generation coming soon!')}
                >
                  <FileText className="w-4 h-4" />
                  <span>Generate Resume</span>
                </button>
                <a 
                  href={selectedLead.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => updateStatus(selectedLead.id, 'Applied')}
                  className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-700 transition-all shadow-md shadow-indigo-200 flex items-center space-x-2"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>Apply Now</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
