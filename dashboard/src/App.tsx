import React, { useEffect, useState, useMemo } from 'react';
import { supabase } from './lib/supabase';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  ExternalLink,
  FileText,
  Clock,
  TrendingUp,
  Target,
  Zap,
  Copy,
  CheckCircle2,
  X,
  Sun,
  Moon,
  Monitor,
  Search,
  Filter,
  BarChart3,
  ArrowUpRight,
  MoreHorizontal,
  Briefcase,
  Sparkles
} from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { format } from 'date-fns';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';

// ─── Types ───────────────────────────────────────────────────────────

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

interface DailyStats {
  scraped_count: number;
  high_match_count: number;
  date: string;
}

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'info' | 'error';
}

// ─── Constants ───────────────────────────────────────────────────────

const STATUS_COLUMNS = ['Pending', 'Applied', 'Interviewing', 'Rejected'] as const;

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  Pending: { color: 'bg-slate-500', icon: <Clock className="w-3 h-3" />, label: 'Pending' },
  Applied: { color: 'bg-cyan-500', icon: <CheckCircle2 className="w-3 h-3" />, label: 'Applied' },
  Interviewing: { color: 'bg-purple-500', icon: <Sparkles className="w-3 h-3" />, label: 'Interviewing' },
  Rejected: { color: 'bg-red-500', icon: <X className="w-3 h-3" />, label: 'Rejected' },
};

// ─── Helpers ─────────────────────────────────────────────────────────

function parseScore(scoreStr: string): number {
  const match = scoreStr.match(/(\d+(?:\.\d+)?)/);
  return match ? parseFloat(match[1]) : 0;
}

function getScoreClass(score: number): string {
  if (score >= 8) return 'score-high';
  if (score >= 6) return 'score-mid';
  return 'score-low';
}

function getScoreColor(score: number): string {
  if (score >= 8) return '#10b981';
  if (score >= 6) return '#f59e0b';
  return '#ef4444';
}

// ─── Components ──────────────────────────────────────────────────────

function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('system');

  useEffect(() => {
    const root = document.documentElement;
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = theme === 'dark' || (theme === 'system' && systemDark);

    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="btn-secondary p-2">
          {theme === 'dark' ? <Moon className="w-4 h-4" /> :
            theme === 'light' ? <Sun className="w-4 h-4" /> :
              <Monitor className="w-4 h-4" />}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="glass-strong rounded-xl p-1 min-w-[160px] z-50"
          sideOffset={5}
        >
          <DropdownMenu.Item
            className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[var(--accent)]/10 cursor-pointer text-sm"
            onClick={() => setTheme('light')}
          >
            <Sun className="w-4 h-4" /> Light
          </DropdownMenu.Item>
          <DropdownMenu.Item
            className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[var(--accent)]/10 cursor-pointer text-sm"
            onClick={() => setTheme('dark')}
          >
            <Moon className="w-4 h-4" /> Dark
          </DropdownMenu.Item>
          <DropdownMenu.Item
            className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[var(--accent)]/10 cursor-pointer text-sm"
            onClick={() => setTheme('system')}
          >
            <Monitor className="w-4 h-4" /> System
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 50, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 50, scale: 0.9 }}
            className="glass-strong px-4 py-3 rounded-xl shadow-lg flex items-center gap-3 min-w-[280px]"
          >
            <div className={`w-2 h-2 rounded-full ${toast.type === 'success' ? 'bg-emerald-500' :
                toast.type === 'error' ? 'bg-red-500' : 'bg-cyan-500'
              }`} />
            <span className="text-sm font-medium flex-1">{toast.message}</span>
            <button onClick={() => onDismiss(toast.id)} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  trend,
  delay = 0
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="card card-hover p-5 flex items-start justify-between group"
    >
      <div>
        <p className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider mb-1">{label}</p>
        <p className="text-2xl font-bold text-[var(--text-primary)]">{value}</p>
        {trend && (
          <p className="text-xs text-[var(--success)] mt-1 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> {trend}
          </p>
        )}
      </div>
      <div className="p-2.5 rounded-xl bg-[var(--accent)]/10 text-[var(--accent)] group-hover:bg-[var(--accent)]/20 transition-colors">
        {icon}
      </div>
    </motion.div>
  );
}

function FunnelBar({ leads }: { leads: Lead[] }) {
  const counts = useMemo(() => {
    const total = leads.length;
    if (total === 0) return [];
    return STATUS_COLUMNS.map(status => {
      const count = leads.filter(l => l.status === status).length;
      return {
        status,
        count,
        pct: Math.round((count / total) * 100),
        ...STATUS_CONFIG[status]
      };
    });
  }, [leads]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.4 }}
      className="card p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-[var(--accent)]" />
          Pipeline Flow
        </h3>
        <span className="text-xs text-[var(--text-tertiary)]">{leads.length} total</span>
      </div>
      <div className="flex gap-1 h-3 rounded-full overflow-hidden bg-[var(--bg-sunken)]">
        {counts.map((item, i) => (
          item.count > 0 && (
            <motion.div
              key={item.status}
              initial={{ width: 0 }}
              animate={{ width: `${item.pct}%` }}
              transition={{ delay: 0.5 + i * 0.1, duration: 0.6, ease: 'easeOut' }}
              className={`${item.color} relative group cursor-pointer`}
            >
              <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div className="glass-strong px-2 py-1 rounded-lg text-xs whitespace-nowrap">
                  {item.label}: {item.count} ({item.pct}%)
                </div>
              </div>
            </motion.div>
          )
        ))}
      </div>
      <div className="flex gap-4 mt-3">
        {counts.map(item => (
          <div key={item.status} className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${item.color}`} />
            <span className="text-xs text-[var(--text-secondary)]">{item.label}</span>
            <span className="text-xs font-semibold text-[var(--text-primary)]">{item.count}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function ScoreDistribution({ leads }: { leads: Lead[] }) {
  const data = useMemo(() => {
    const buckets = [
      { range: '9-10', min: 9, count: 0, color: '#10b981' },
      { range: '7-8', min: 7, count: 0, color: '#34d399' },
      { range: '5-6', min: 5, count: 0, color: '#fbbf24' },
      { range: '3-4', min: 3, count: 0, color: '#f87171' },
      { range: '0-2', min: 0, count: 0, color: '#57534e' },
    ];

    leads.forEach(lead => {
      const score = parseScore(lead.score);
      for (const bucket of buckets) {
        if (score >= bucket.min) {
          bucket.count++;
          break;
        }
      }
    });

    return buckets.reverse();
  }, [leads]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.4 }}
      className="card p-5"
    >
      <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2 mb-4">
        <Target className="w-4 h-4 text-[var(--accent)]" />
        Score Distribution
      </h3>
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
            <XAxis type="number" hide />
            <YAxis
              dataKey="range"
              type="category"
              width={40}
              tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                fontSize: '12px'
              }}
              cursor={{ fill: 'var(--bg-sunken)' }}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

function LeadCard({
  lead,
  index,
  onSelect,
  onStatusChange
}: {
  lead: Lead;
  index: number;
  onSelect: () => void;
  onStatusChange: (id: number, status: string) => void;
}) {
  const score = parseScore(lead.score);
  const scoreClass = getScoreClass(score);
  const statusConfig = STATUS_CONFIG[lead.status] || STATUS_CONFIG.Pending;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ delay: index * 0.03, duration: 0.3 }}
      className="card card-hover p-4 cursor-pointer group relative overflow-hidden"
      onClick={onSelect}
    >
      {/* Score indicator bar */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5 opacity-60"
        style={{ backgroundColor: getScoreColor(score) }}
      />

      <div className="flex items-start justify-between mb-3">
        <span className={`badge ${scoreClass}`}>
          {lead.score}
        </span>
        <span className="text-[10px] font-medium text-[var(--text-tertiary)] uppercase tracking-wider">
          {lead.cluster}
        </span>
      </div>

      <h3 className="font-bold text-[var(--text-primary)] text-base leading-tight mb-1 group-hover:text-[var(--accent)] transition-colors">
        {lead.company}
      </h3>
      <p className="text-sm text-[var(--text-secondary)] line-clamp-2 mb-3">
        {lead.role}
      </p>

      <div className="flex items-center justify-between pt-3 border-t border-[var(--border-subtle)]">
        <div className="flex items-center gap-1">
          <span className={`w-2 h-2 rounded-full ${statusConfig.color}`} />
          <span className="text-xs text-[var(--text-tertiary)]">{statusConfig.label}</span>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => {
              e.stopPropagation();
              window.open(lead.url, '_blank');
            }}
            className="p-1.5 rounded-lg hover:bg-[var(--bg-sunken)] text-[var(--text-tertiary)] hover:text-[var(--accent)] transition-colors"
            title="Open JD"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
          {lead.status === 'Pending' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStatusChange(lead.id, 'Applied');
              }}
              className="p-1.5 rounded-lg hover:bg-[var(--accent)]/10 text-[var(--text-tertiary)] hover:text-[var(--accent)] transition-colors"
              title="Mark Applied"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function LeadModal({
  lead,
  onClose,
  onStatusChange
}: {
  lead: Lead;
  onClose: () => void;
  onStatusChange: (id: number, status: string) => void;
}) {
  const [activeTab, setActiveTab] = useState<'overview' | 'jd' | 'dm'>('overview');
  const [copied, setCopied] = useState(false);
  const score = parseScore(lead.score);

  const copyDM = () => {
    navigator.clipboard.writeText(lead.dm_draft || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Dialog.Root open={!!lead} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay asChild>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
        </Dialog.Overlay>
        <Dialog.Content asChild>
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.97 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 
                       md:w-full md:max-w-3xl md:max-h-[85vh]
                       bg-[var(--bg-elevated)] rounded-2xl shadow-2xl z-50 
                       flex flex-col overflow-hidden border border-[var(--border)]"
          >
            {/* Header */}
            <div className="px-6 py-5 border-b border-[var(--border)] flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`badge ${getScoreClass(score)} text-xs`}>
                    {lead.score}
                  </span>
                  <span className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider">
                    {lead.cluster}
                  </span>
                </div>
                <Dialog.Title className="text-xl font-bold text-[var(--text-primary)]">
                  {lead.company}
                </Dialog.Title>
                <p className="text-sm text-[var(--text-secondary)] mt-0.5">{lead.role}</p>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-xl hover:bg-[var(--bg-sunken)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors ml-4"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="px-6 border-b border-[var(--border)] flex gap-1">
              {[
                { id: 'overview' as const, label: 'Overview', icon: <Briefcase className="w-4 h-4" /> },
                { id: 'jd' as const, label: 'Job Description', icon: <FileText className="w-4 h-4" /> },
                { id: 'dm' as const, label: 'DM Draft', icon: <Sparkles className="w-4 h-4" /> },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors
                    ${activeTab === tab.id
                      ? 'border-[var(--accent)] text-[var(--accent)]'
                      : 'border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
                    }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <AnimatePresence mode="wait">
                {activeTab === 'overview' && (
                  <motion.div
                    key="overview"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    className="space-y-6"
                  >
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="card p-3 bg-[var(--bg-sunken)]">
                        <p className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)] mb-1">Lead ID</p>
                        <p className="text-sm font-mono font-semibold">#{lead.id}</p>
                      </div>
                      <div className="card p-3 bg-[var(--bg-sunken)]">
                        <p className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)] mb-1">Status</p>
                        <div className="flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full ${STATUS_CONFIG[lead.status]?.color || 'bg-gray-500'}`} />
                          <span className="text-sm font-medium">{lead.status}</span>
                        </div>
                      </div>
                      <div className="card p-3 bg-[var(--bg-sunken)]">
                        <p className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)] mb-1">Score</p>
                        <p className="text-sm font-bold" style={{ color: getScoreColor(score) }}>{lead.score}</p>
                      </div>
                      <div className="card p-3 bg-[var(--bg-sunken)]">
                        <p className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)] mb-1">Added</p>
                        <p className="text-sm">{format(new Date(lead.created_at), 'MMM d, yyyy')}</p>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Archetype</h4>
                      <span className="badge bg-[var(--accent)]/10 text-[var(--accent)] border-[var(--accent)]/20">
                        {lead.cluster}
                      </span>
                    </div>

                    <div>
                      <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Quick Actions</h4>
                      <div className="flex gap-2">
                        <a
                          href={lead.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-primary flex items-center gap-2 text-sm"
                          onClick={() => onStatusChange(lead.id, 'Applied')}
                        >
                          <ExternalLink className="w-4 h-4" />
                          Apply Now
                        </a>
                        <button
                          className="btn-secondary flex items-center gap-2 text-sm"
                          onClick={() => alert('PDF generation coming soon!')}
                        >
                          <FileText className="w-4 h-4" />
                          Generate Resume
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}

                {activeTab === 'jd' && (
                  <motion.div
                    key="jd"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-semibold text-[var(--text-primary)]">Job Description</h4>
                      <span className="text-[10px] text-[var(--text-tertiary)] bg-[var(--bg-sunken)] px-2 py-1 rounded-full uppercase tracking-wider">
                        Read Only
                      </span>
                    </div>
                    <div className="bg-[var(--bg-sunken)] rounded-xl p-5 text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap border border-[var(--border-subtle)]">
                      {lead.description}
                    </div>
                  </motion.div>
                )}

                {activeTab === 'dm' && (
                  <motion.div
                    key="dm"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-[var(--accent)]" />
                        AI DM Draft
                      </h4>
                      <button
                        onClick={copyDM}
                        className="flex items-center gap-1.5 text-xs text-[var(--accent)] hover:text-[var(--accent-dark)] transition-colors"
                      >
                        {copied ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        {copied ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                    <div className="bg-gradient-to-br from-[var(--accent)]/5 to-[var(--info)]/5 rounded-xl p-5 text-sm text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap border border-[var(--accent)]/10 italic">
                      {lead.dm_draft || 'No draft generated yet.'}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-[var(--border)] bg-[var(--bg-sunken)]/50 flex items-center justify-between">
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <button className="btn-secondary text-sm flex items-center gap-2">
                    <MoreHorizontal className="w-4 h-4" />
                    Change Status
                  </button>
                </DropdownMenu.Trigger>
                <DropdownMenu.Portal>
                  <DropdownMenu.Content className="glass-strong rounded-xl p-1 min-w-[160px] z-50">
                    {STATUS_COLUMNS.map(status => (
                      <DropdownMenu.Item
                        key={status}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[var(--accent)]/10 cursor-pointer text-sm"
                        onClick={() => onStatusChange(lead.id, status)}
                      >
                        <span className={`w-2 h-2 rounded-full ${STATUS_CONFIG[status].color}`} />
                        {status}
                      </DropdownMenu.Item>
                    ))}
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>

              <span className="text-xs text-[var(--text-tertiary)]">
                Last updated: {format(new Date(lead.created_at), 'MMM d, h:mm a')}
              </span>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function SkeletonCard() {
  return (
    <div className="card p-4 space-y-3">
      <div className="flex justify-between">
        <div className="skeleton w-16 h-5" />
        <div className="skeleton w-12 h-4" />
      </div>
      <div className="skeleton w-3/4 h-5" />
      <div className="skeleton w-full h-4" />
      <div className="skeleton w-1/2 h-4" />
      <div className="pt-3 border-t border-[var(--border-subtle)] flex justify-between">
        <div className="skeleton w-20 h-4" />
        <div className="skeleton w-16 h-4" />
      </div>
    </div>
  );
}

// ─── Main App ────────────────────────────────────────────────────────

function App() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DailyStats | null>(null);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const addToast = (message: string, type: Toast['type'] = 'info') => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  async function fetchLeads() {
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('leads')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setLeads(data || []);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error fetching leads:', err);
      addToast('Failed to fetch leads', 'error');
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

      if (!error && data) {
        setStats(data);
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }

  async function updateStatus(id: number, newStatus: string) {
    try {
      const { error } = await supabase
        .from('leads')
        .update({ status: newStatus })
        .eq('id', id);

      if (error) throw error;

      setLeads(prev => prev.map(lead =>
        lead.id === id ? { ...lead, status: newStatus } : lead
      ));

      addToast(`Status updated to ${newStatus}`, 'success');
      if (selectedLead?.id === id) {
        setSelectedLead(prev => prev ? { ...prev, status: newStatus } : null);
      }
    } catch (err) {
      console.error('Error updating status:', err);
      addToast('Failed to update status', 'error');
    }
  }

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, []);

  // Real-time subscription
  useEffect(() => {
    const subscription = supabase
      .channel('leads_changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'leads' }, () => {
        fetchLeads();
        addToast('New leads available', 'info');
      })
      .subscribe();

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const filteredLeads = useMemo(() => {
    if (!searchQuery) return leads;
    const q = searchQuery.toLowerCase();
    return leads.filter(lead =>
      lead.company.toLowerCase().includes(q) ||
      lead.role.toLowerCase().includes(q) ||
      lead.cluster.toLowerCase().includes(q)
    );
  }, [leads, searchQuery]);

  const topLeads = useMemo(() => {
    return filteredLeads
      .filter(l => parseScore(l.score) >= 8)
      .slice(0, 5);
  }, [filteredLeads]);

  const pipelineMetrics = useMemo(() => {
    const total = filteredLeads.length;
    const applied = filteredLeads.filter(l => l.status === 'Applied').length;
    const interviewing = filteredLeads.filter(l => l.status === 'Interviewing').length;
    return {
      total,
      active: applied + interviewing,
      responseRate: total > 0 ? Math.round((applied / total) * 100) : 0,
      interviewRate: applied > 0 ? Math.round((interviewing / applied) * 100) : 0,
    };
  }, [filteredLeads]);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
      {/* ─── Header ───────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 glass border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--info)] flex items-center justify-center shadow-lg">
                <LayoutDashboard className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold leading-none">Career Ops</h1>
                <p className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider">Mission Control</p>
              </div>
            </div>

            {/* Search */}
            <div className="hidden md:flex items-center flex-1 max-w-md mx-8">
              <div className="relative w-full">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-tertiary)]" />
                <input
                  type="text"
                  placeholder="Search companies, roles, archetypes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-[var(--bg-sunken)] border border-[var(--border)] rounded-xl
                           text-sm placeholder:text-[var(--text-tertiary)]
                           focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/20
                           transition-all"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => { fetchLeads(); fetchStats(); }}
                className="btn-secondary p-2"
                title="Refresh"
              >
                <Clock className="w-4 h-4" />
              </button>
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* ─── Stats Row ────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Scraped Today"
            value={stats?.scraped_count ?? 0}
            icon={<Zap className="w-5 h-5" />}
            trend="Live"
            delay={0}
          />
          <StatCard
            label="Gold Leads"
            value={stats?.high_match_count ?? 0}
            icon={<Target className="w-5 h-5" />}
            delay={0.1}
          />
          <StatCard
            label="Active Pipeline"
            value={pipelineMetrics.active}
            icon={<TrendingUp className="w-5 h-5" />}
            trend={`${pipelineMetrics.responseRate}% response`}
            delay={0.2}
          />
          <StatCard
            label="Total Leads"
            value={pipelineMetrics.total}
            icon={<Briefcase className="w-5 h-5" />}
            delay={0.3}
          />
        </div>

        {/* ─── Analytics Row ────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <FunnelBar leads={filteredLeads} />
          </div>
          <ScoreDistribution leads={filteredLeads} />
        </div>

        {/* ─── Top Opportunities ────────────────────────────── */}
        {topLeads.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-[var(--accent)]" />
                Top Opportunities
              </h2>
              <span className="text-xs text-[var(--text-tertiary)]">
                Score 8+ leads
              </span>
            </div>
            <div className="flex gap-4 overflow-x-auto pb-2 snap-x">
              {topLeads.map((lead, i) => (
                <motion.div
                  key={lead.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + i * 0.1 }}
                  className="card card-hover p-4 min-w-[280px] max-w-[280px] snap-start cursor-pointer"
                  onClick={() => setSelectedLead(lead)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className={`badge ${getScoreClass(parseScore(lead.score))} text-xs`}>
                      {lead.score}
                    </span>
                    <ArrowUpRight className="w-4 h-4 text-[var(--text-tertiary)]" />
                  </div>
                  <h3 className="font-bold text-[var(--text-primary)] mb-1">{lead.company}</h3>
                  <p className="text-xs text-[var(--text-secondary)] line-clamp-2 mb-2">{lead.role}</p>
                  <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider">
                    {lead.cluster}
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}

        {/* ─── Kanban Board ─────────────────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <LayoutDashboard className="w-5 h-5 text-[var(--accent)]" />
              Pipeline Board
            </h2>
            <div className="flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
              <Filter className="w-3.5 h-3.5" />
              <span>Last updated: {format(lastUpdated, 'h:mm a')}</span>
            </div>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {STATUS_COLUMNS.map((column) => {
                const columnLeads = filteredLeads.filter(l => l.status === column);
                const avgScore = columnLeads.length > 0
                  ? (columnLeads.reduce((sum, l) => sum + parseScore(l.score), 0) / columnLeads.length).toFixed(1)
                  : '0';

                return (
                  <div key={column} className="flex flex-col">
                    {/* Column Header */}
                    <div className="flex items-center justify-between mb-3 px-1">
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${STATUS_CONFIG[column].color}`} />
                        <h3 className="text-sm font-semibold text-[var(--text-primary)]">{column}</h3>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-[var(--text-tertiary)]">
                          avg {avgScore}
                        </span>
                        <span className="badge bg-[var(--bg-sunken)] text-[var(--text-secondary)] text-xs">
                          {columnLeads.length}
                        </span>
                      </div>
                    </div>

                    {/* Cards */}
                    <div className="flex-1 space-y-3 min-h-[200px]">
                      <AnimatePresence mode="popLayout">
                        {columnLeads.map((lead, i) => (
                          <LeadCard
                            key={lead.id}
                            lead={lead}
                            index={i}
                            onSelect={() => setSelectedLead(lead)}
                            onStatusChange={updateStatus}
                          />
                        ))}
                      </AnimatePresence>

                      {columnLeads.length === 0 && (
                        <div className="text-center py-8 text-[var(--text-tertiary)] text-sm">
                          No leads here
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>

      {/* ─── Lead Detail Modal ────────────────────────────── */}
      <AnimatePresence>
        {selectedLead && (
          <LeadModal
            lead={selectedLead}
            onClose={() => setSelectedLead(null)}
            onStatusChange={updateStatus}
          />
        )}
      </AnimatePresence>

      {/* ─── Toast Notifications ──────────────────────────── */}
      <ToastContainer
        toasts={toasts}
        onDismiss={(id) => setToasts(prev => prev.filter(t => t.id !== id))}
      />
    </div>
  );
}

export default App;