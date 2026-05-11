import { useEffect, useMemo, useState } from 'react';
import { supabase } from './lib/supabase';
import {
  ArrowUpRight,
  BarChart3,
  Briefcase,
  Clock,
  ExternalLink,
  Filter,
  LayoutDashboard,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  Target,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { format } from 'date-fns';

type LeadStatus = 'Pending' | 'Applied' | 'Interviewing' | 'Rejected';

interface Lead {
  id: string;
  company: string | null;
  role: string | null;
  score: string | null;
  url: string | null;
  description: string | null;
  cluster: string | null;
  dm_draft: string | null;
  status: LeadStatus | string | null;
  created_at: string;
}

interface DailyStats {
  scraped_count: number;
  high_match_count: number;
  filtered_count?: number;
  date: string;
}

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'info' | 'error';
}

const STATUS_COLUMNS: LeadStatus[] = ['Pending', 'Applied', 'Interviewing', 'Rejected'];
const PAGE_SIZE = 20;

const STATUS_CONFIG: Record<LeadStatus, { dot: string; label: string }> = {
  Pending: { dot: 'bg-slate-500', label: 'Pending' },
  Applied: { dot: 'bg-cyan-500', label: 'Applied' },
  Interviewing: { dot: 'bg-violet-500', label: 'Interviewing' },
  Rejected: { dot: 'bg-red-500', label: 'Rejected' },
};

const SCORE_FILTERS = [
  { label: 'All', min: 0 },
  { label: '8+', min: 8 },
  { label: '6+', min: 6 },
  { label: 'Below 6', min: -1 },
];

function parseScore(scoreStr?: string | null): number {
  const match = String(scoreStr ?? '').match(/(\d+(?:\.\d+)?)/);
  return match ? Number.parseFloat(match[1]) : 0;
}

function normalizeStatus(status?: string | null): LeadStatus {
  return STATUS_COLUMNS.includes(status as LeadStatus) ? (status as LeadStatus) : 'Pending';
}

function getScoreTone(score: number): string {
  if (score >= 8) return 'score-high';
  if (score >= 6) return 'score-mid';
  return 'score-low';
}

function getFitLabel(score: number): string {
  if (score >= 8) return 'High fit';
  if (score >= 6) return 'Review';
  return 'Low signal';
}

function safeText(value?: string | null, fallback = 'Unknown') {
  return value?.trim() || fallback;
}

function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  return (
    <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2">
      {toasts.map((toast) => (
        <div key={toast.id} className="toast">
          <span className={`h-2 w-2 rounded-full ${toast.type === 'error' ? 'bg-red-500' : toast.type === 'success' ? 'bg-emerald-500' : 'bg-cyan-500'}`} />
          <span className="flex-1">{toast.message}</span>
          <button onClick={() => onDismiss(toast.id)} className="icon-button h-7 w-7">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}

function MetricCard({
  label,
  value,
  meta,
  icon,
}: {
  label: string;
  value: string | number;
  meta?: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="metric-card">
      <div className="flex items-center justify-between">
        <span className="metric-label">{label}</span>
        <span className="metric-icon">{icon}</span>
      </div>
      <div className="mt-4 flex items-end justify-between gap-3">
        <span className="text-3xl font-semibold tracking-tight text-[var(--text-primary)]">{value}</span>
        {meta && <span className="mb-1 text-xs font-medium text-[var(--text-tertiary)]">{meta}</span>}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: LeadStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <span className="status-pill">
      <span className={`h-2 w-2 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
}

function LeadModal({
  lead,
  onClose,
  onStatusChange,
}: {
  lead: Lead;
  onClose: () => void;
  onStatusChange: (id: string, status: LeadStatus) => void;
}) {
  const score = parseScore(lead.score);
  const status = normalizeStatus(lead.status);

  return (
    <Dialog.Root open={!!lead} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-stone-950/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[86vh] w-[calc(100vw-2rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] shadow-2xl">
          <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] px-6 py-5">
            <div className="min-w-0">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className={`score-badge ${getScoreTone(score)}`}>{lead.score ?? '0/10'}</span>
                <StatusPill status={status} />
                <span className="quiet-badge">{safeText(lead.cluster, 'Unclustered')}</span>
              </div>
              <Dialog.Title className="text-xl font-semibold tracking-tight">{safeText(lead.company)}</Dialog.Title>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">{safeText(lead.role, 'Role not available')}</p>
            </div>
            <button onClick={onClose} className="icon-button">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid gap-5 overflow-y-auto p-6 md:grid-cols-[1fr_220px]">
            <div className="space-y-5">
              <section>
                <h3 className="section-label">Job Description</h3>
                <div className="jd-panel">{safeText(lead.description, 'No description stored for this lead.')}</div>
              </section>
              <section>
                <h3 className="section-label">DM Draft</h3>
                <div className="jd-panel">{safeText(lead.dm_draft, 'No outreach draft generated yet.')}</div>
              </section>
            </div>

            <aside className="space-y-3">
              <div className="side-panel">
                <span className="section-label">Fit</span>
                <p className="mt-2 text-lg font-semibold">{getFitLabel(score)}</p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">Score {lead.score ?? '0/10'}</p>
              </div>
              <div className="side-panel">
                <span className="section-label">Added</span>
                <p className="mt-2 text-sm font-medium">{format(new Date(lead.created_at), 'MMM d, yyyy')}</p>
              </div>
              <a className="btn-primary w-full justify-center" href={lead.url ?? '#'} target="_blank" rel="noreferrer">
                <ExternalLink className="h-4 w-4" />
                Open role
              </a>
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <button className="btn-secondary w-full justify-center">
                    <Filter className="h-4 w-4" />
                    Change status
                  </button>
                </DropdownMenu.Trigger>
                <DropdownMenu.Portal>
                  <DropdownMenu.Content className="dropdown-menu" sideOffset={8}>
                    {STATUS_COLUMNS.map((nextStatus) => (
                      <DropdownMenu.Item
                        key={nextStatus}
                        className="dropdown-item"
                        onClick={() => onStatusChange(lead.id, nextStatus)}
                      >
                        <span className={`h-2 w-2 rounded-full ${STATUS_CONFIG[nextStatus].dot}`} />
                        {nextStatus}
                      </DropdownMenu.Item>
                    ))}
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
            </aside>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function App() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DailyStats | null>(null);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'All' | LeadStatus>('All');
  const [scoreFilter, setScoreFilter] = useState('All');
  const [currentPage, setCurrentPage] = useState(1);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const addToast = (message: string, type: Toast['type'] = 'info') => {
    const id = Math.random().toString(36).slice(2);
    setToasts((current) => [...current, { id, message, type }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 3500);
  };

  async function fetchLeads() {
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('leads')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setLeads(data ?? []);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Error fetching leads:', error);
      addToast('Could not load leads', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function fetchStats() {
    try {
      const today = new Date().toISOString().split('T')[0];
      const { data, error } = await supabase
        .from('daily_stats')
        .select('*')
        .eq('date', today)
        .single();

      if (!error && data) setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }

  async function updateStatus(id: string, newStatus: LeadStatus) {
    const previous = leads;
    setLeads((current) => current.map((lead) => (lead.id === id ? { ...lead, status: newStatus } : lead)));
    setSelectedLead((current) => (current?.id === id ? { ...current, status: newStatus } : current));

    try {
      const { error } = await supabase.from('leads').update({ status: newStatus }).eq('id', id);
      if (error) throw error;
      addToast(`Moved to ${newStatus}`, 'success');
    } catch (error) {
      console.error('Error updating status:', error);
      setLeads(previous);
      addToast('Status update failed', 'error');
    }
  }

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, statusFilter, scoreFilter]);

  useEffect(() => {
    const subscription = supabase
      .channel('leads_changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'leads' }, () => {
        fetchLeads();
      })
      .subscribe();

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const filteredLeads = useMemo(() => {
    const scoreOption = SCORE_FILTERS.find((option) => option.label === scoreFilter) ?? SCORE_FILTERS[0];
    const query = searchQuery.trim().toLowerCase();

    return leads.filter((lead) => {
      const score = parseScore(lead.score);
      const status = normalizeStatus(lead.status);
      const matchesSearch =
        !query ||
        safeText(lead.company, '').toLowerCase().includes(query) ||
        safeText(lead.role, '').toLowerCase().includes(query) ||
        safeText(lead.cluster, '').toLowerCase().includes(query);
      const matchesStatus = statusFilter === 'All' || status === statusFilter;
      const matchesScore = scoreOption.min === -1 ? score < 6 : score >= scoreOption.min;
      return matchesSearch && matchesStatus && matchesScore;
    });
  }, [leads, scoreFilter, searchQuery, statusFilter]);

  const sortedLeads = useMemo(() => {
    return [...filteredLeads].sort((a, b) => parseScore(b.score) - parseScore(a.score));
  }, [filteredLeads]);

  const totalPages = Math.max(1, Math.ceil(sortedLeads.length / PAGE_SIZE));
  const visiblePage = Math.min(currentPage, totalPages);
  const paginatedLeads = useMemo(() => {
    const start = (visiblePage - 1) * PAGE_SIZE;
    return sortedLeads.slice(start, start + PAGE_SIZE);
  }, [sortedLeads, visiblePage]);

  const statusCounts = useMemo(() => {
    return STATUS_COLUMNS.reduce<Record<LeadStatus, number>>((acc, status) => {
      acc[status] = leads.filter((lead) => normalizeStatus(lead.status) === status).length;
      return acc;
    }, { Pending: 0, Applied: 0, Interviewing: 0, Rejected: 0 });
  }, [leads]);

  const metrics = useMemo(() => {
    const highFit = leads.filter((lead) => parseScore(lead.score) >= 8).length;
    const reviewQueue = leads.filter((lead) => normalizeStatus(lead.status) === 'Pending').length;
    const active = statusCounts.Applied + statusCounts.Interviewing;
    const average = leads.length
      ? (leads.reduce((sum, lead) => sum + parseScore(lead.score), 0) / leads.length).toFixed(1)
      : '0.0';

    return { highFit, reviewQueue, active, average };
  }, [leads, statusCounts.Applied, statusCounts.Interviewing]);

  const pipelinePreview = useMemo(() => {
    return STATUS_COLUMNS.map((status) => ({
      status,
      leads: sortedLeads.filter((lead) => normalizeStatus(lead.status) === status).slice(0, 4),
      total: filteredLeads.filter((lead) => normalizeStatus(lead.status) === status).length,
    }));
  }, [filteredLeads, sortedLeads]);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
      <header className="border-b border-[var(--border)] bg-[var(--bg-elevated)]/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1500px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--text-primary)] text-white">
              <LayoutDashboard className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-tight">Career Ops</h1>
              <p className="text-xs text-[var(--text-tertiary)]">Lead command center</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-xs text-[var(--text-tertiary)] sm:inline">
              Updated {format(lastUpdated, 'h:mm a')}
            </span>
            <button className="btn-secondary px-3" onClick={() => { fetchLeads(); fetchStats(); }}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6 lg:px-8">
        <section className="mb-4 flex flex-col justify-between gap-3 md:flex-row md:items-end">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-[var(--accent)]">
              <Sparkles className="h-4 w-4" />
              Live sourcing inbox
            </div>
            <h2 className="text-2xl font-semibold tracking-tight">Lead review queue</h2>
            <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
              Prioritized Supabase leads with fast filters and a compact pipeline view.
            </p>
          </div>
          <div className="flex min-w-[190px] items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text-secondary)]">
            <Clock className="h-4 w-4 text-[var(--text-tertiary)]" />
            {stats?.scraped_count ?? 0} scanned today
          </div>
        </section>

        <section className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Total leads" value={leads.length} meta={`${filteredLeads.length} shown`} icon={<Briefcase className="h-4 w-4" />} />
          <MetricCard label="Pending review" value={metrics.reviewQueue} meta="needs triage" icon={<Clock className="h-4 w-4" />} />
          <MetricCard label="High fit" value={metrics.highFit} meta="score 8+" icon={<Target className="h-4 w-4" />} />
          <MetricCard label="Average score" value={metrics.average} meta={`${metrics.active} active`} icon={<BarChart3 className="h-4 w-4" />} />
        </section>

        <section className="mb-4 rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-3">
          <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                className="search-input"
                placeholder="Search company, role, or cluster"
              />
            </div>
            <div className="segmented-control">
              {(['All', ...STATUS_COLUMNS] as const).map((status) => (
                <button
                  key={status}
                  className={statusFilter === status ? 'active' : ''}
                  onClick={() => setStatusFilter(status)}
                >
                  {status}
                </button>
              ))}
            </div>
            <div className="segmented-control">
              {SCORE_FILTERS.map((filter) => (
                <button
                  key={filter.label}
                  className={scoreFilter === filter.label ? 'active' : ''}
                  onClick={() => setScoreFilter(filter.label)}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)]">
            <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
              <div>
                <h3 className="text-sm font-semibold">Priority inbox</h3>
                <p className="text-xs text-[var(--text-tertiary)]">Sorted by score, then newest first</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="quiet-badge">{sortedLeads.length} leads</span>
                <span className="quiet-badge">20 per page</span>
              </div>
            </div>

            {loading ? (
              <div className="flex items-center justify-center gap-2 p-12 text-sm text-[var(--text-secondary)]">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading leads
              </div>
            ) : sortedLeads.length === 0 ? (
              <div className="p-12 text-center text-sm text-[var(--text-secondary)]">No leads match these filters.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="lead-table">
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Role</th>
                      <th>Score</th>
                      <th>Status</th>
                      <th>Cluster</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedLeads.map((lead) => {
                      const score = parseScore(lead.score);
                      const status = normalizeStatus(lead.status);
                      return (
                        <tr key={lead.id} onClick={() => setSelectedLead(lead)}>
                          <td>
                            <div className="truncate font-medium text-[var(--text-primary)]">{safeText(lead.company)}</div>
                            <div className="text-[11px] text-[var(--text-tertiary)]">{format(new Date(lead.created_at), 'MMM d, h:mm a')}</div>
                          </td>
                          <td className="max-w-[520px]">
                            <div className="truncate text-[var(--text-secondary)]">{safeText(lead.role, 'Role unavailable')}</div>
                          </td>
                          <td>
                            <span className={`score-badge ${getScoreTone(score)}`}>{lead.score ?? '0/10'}</span>
                          </td>
                          <td><StatusPill status={status} /></td>
                          <td><span className="quiet-badge max-w-24 truncate">{safeText(lead.cluster, 'N/A')}</span></td>
                          <td className="text-right">
                            <button className="icon-button" onClick={(event) => { event.stopPropagation(); window.open(lead.url ?? '#', '_blank'); }}>
                              <ArrowUpRight className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div className="sticky bottom-0 z-10 flex flex-col gap-3 border-t border-[var(--border)] bg-[var(--bg-elevated)]/95 px-4 py-3 backdrop-blur sm:flex-row sm:items-center sm:justify-between">
                  <div className="text-xs text-[var(--text-tertiary)]">
                    Showing {sortedLeads.length === 0 ? 0 : (visiblePage - 1) * PAGE_SIZE + 1}
                    {'-'}
                    {Math.min(visiblePage * PAGE_SIZE, sortedLeads.length)} of {sortedLeads.length}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      className="pagination-button"
                      disabled={visiblePage === 1}
                      onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </button>
                    <span className="quiet-badge">Page {visiblePage} of {totalPages}</span>
                    <button
                      className="pagination-button"
                      disabled={visiblePage === totalPages}
                      onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <aside className="space-y-4">
            <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-4">
              <h3 className="text-sm font-semibold">Pipeline snapshot</h3>
              <div className="mt-3 space-y-3">
                {STATUS_COLUMNS.map((status) => {
                  const pct = leads.length ? Math.round((statusCounts[status] / leads.length) * 100) : 0;
                  return (
                    <div key={status}>
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="flex items-center gap-2 font-medium">
                          <span className={`h-2 w-2 rounded-full ${STATUS_CONFIG[status].dot}`} />
                          {status}
                        </span>
                        <span className="text-[var(--text-tertiary)]">{statusCounts[status]}</span>
                      </div>
                      <div className="h-2 rounded-full bg-[var(--bg-sunken)]">
                        <div className={`h-2 rounded-full ${STATUS_CONFIG[status].dot}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-4">
              <h3 className="text-sm font-semibold">Board preview</h3>
              <div className="mt-3 space-y-3">
                {pipelinePreview.map((column) => (
                  <div key={column.status}>
                    <div className="mb-2 flex items-center justify-between">
                      <StatusPill status={column.status} />
                      <span className="text-xs text-[var(--text-tertiary)]">{column.total}</span>
                    </div>
                    <div className="space-y-2">
                      {column.leads.length === 0 ? (
                        <div className="rounded-md border border-dashed border-[var(--border)] px-3 py-4 text-center text-xs text-[var(--text-tertiary)]">Empty</div>
                      ) : (
                        column.leads.map((lead) => (
                          <button key={lead.id} className="mini-lead" onClick={() => setSelectedLead(lead)}>
                            <span className="truncate font-medium">{safeText(lead.company)}</span>
                            <span className={`score-badge ${getScoreTone(parseScore(lead.score))}`}>{lead.score ?? '0/10'}</span>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </section>
      </main>

      {selectedLead && (
        <LeadModal
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
          onStatusChange={updateStatus}
        />
      )}

      <ToastContainer toasts={toasts} onDismiss={(id) => setToasts((current) => current.filter((toast) => toast.id !== id))} />
    </div>
  );
}

export default App;
