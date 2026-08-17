import { useState, useEffect, useCallback } from 'react'
import { api, SlotStatus, RunConfig, RunStatus, StatsReport, ItemResult, RunSummary } from './api'
import CredentialsPanel from './components/CredentialsPanel'
import RunConfigPanel from './components/RunConfigPanel'
import LiveProgress from './components/LiveProgress'
import Leaderboard from './components/Leaderboard'
import ItemAudit from './components/ItemAudit'
import RunsHistory from './components/RunsHistory'
import LocalProbe from './components/LocalProbe'

type Tab = 'configure' | 'results' | 'audit' | 'history'

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('configure')
  const [slots, setSlots] = useState<SlotStatus[]>([])
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null)
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [report, setReport] = useState<StatsReport | null>(null)
  const [itemResults, setItemResults] = useState<ItemResult[] | null>(null)
  const [selectedItem, setSelectedItem] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [localProbe, setLocalProbe] = useState<{ reachable: boolean; models: unknown[]; error?: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshSlots = useCallback(async () => {
    try {
      const s = await api.getSlots()
      setSlots(s)
    } catch (e) {
      console.error('Failed to load slots', e)
    }
  }, [])

  const refreshRuns = useCallback(async () => {
    try {
      const r = await api.listRuns()
      setRuns(r)
    } catch (e) {
      console.error('Failed to load runs', e)
    }
  }, [])

  const refreshReport = useCallback(async (runId: string) => {
    try {
      const r = await api.getReport(runId)
      setReport(r)
    } catch (e) {
      console.error('Failed to load report', e)
    }
  }, [])

  const refreshItemResults = useCallback(async (runId: string, model?: string, question?: string) => {
    try {
      const r = await api.getItemResults(runId, model, question)
      setItemResults(r)
    } catch (e) {
      console.error('Failed to load item results', e)
    }
  }, [])

  useEffect(() => {
    refreshSlots()
    refreshRuns()
    api.probeLocal().then(setLocalProbe).catch(() => {})
  }, [refreshSlots, refreshRuns])

  const launchRun = async (cfg: RunConfig) => {
    setLoading(true)
    setError(null)
    try {
      const { run_id } = await api.createRun(cfg)
      setCurrentRunId(run_id)
      setActiveTab('results')
      // Poll status
      const poll = async () => {
        const s = await api.getRunStatus(run_id)
        setRunStatus(s)
        if (s.status === 'running') {
          setTimeout(poll, 1000)
        } else {
          setLoading(false)
          await refreshReport(run_id)
        }
      }
      poll()
      // Also stream via SSE
      api.streamRun(run_id, (event) => {
        if (event.type === 'done') {
          setLoading(false)
          refreshReport(run_id)
        }
      }, () => {
        setLoading(false)
        refreshReport(run_id)
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setLoading(false)
    }
  }

  const openAudit = (runId: string, model: string, question: string) => {
    setSelectedModel(model)
    setSelectedItem(question)
    refreshItemResults(runId, model, question)
    setActiveTab('audit')
  }

  const openRun = (runId: string) => {
    setCurrentRunId(runId)
    refreshReport(runId)
    setActiveTab('results')
    refreshRuns()
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">A</div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">AusLawExam-Bench</h1>
            <span className="text-xs text-gray-500 dark:text-slate-400 bg-gray-100 dark:bg-slate-700 px-2 py-0.5 rounded">Evaluator</span>
          </div>
          <nav className="flex gap-1 ml-auto">
            {([
              ['configure', 'Configure &amp; Run'],
              ['results', 'Results'],
              ['audit', 'Item Audit'],
              ['history', 'Runs'],
            ] as [Tab, string][]).map(([tab, label]) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  activeTab === tab
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center gap-2 text-red-700 dark:text-red-400 text-sm">
            <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/></svg>
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">✕</button>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'configure' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <CredentialsPanel onRefresh={refreshSlots} />
              <RunConfigPanel
                slots={slots}
                localProbe={localProbe}
                onLaunch={launchRun}
                loading={loading}
                onRunDemo={() => launchRun({ models: ['gpt', 'claude', 'gemini', 'local'], n_reps: 3, base_seed: 0 })}
              />
            </div>
            <div className="space-y-6">
              <LocalProbe probe={localProbe} />
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Slot Status</h2>
                <div className="space-y-2">
                  {slots.map(s => (
                    <div key={s.name} className="flex items-center gap-2 text-sm">
                      <span className={`w-2 h-2 rounded-full ${s.is_real ? 'bg-green-500' : 'bg-amber-500'}`} />
                      <span className="font-medium text-gray-700 dark:text-slate-200">{s.name}</span>
                      <span className="text-gray-400 dark:text-slate-500 text-xs">{s.model}</span>
                      <span className={`ml-auto text-xs px-1.5 py-0.5 rounded ${s.is_mock ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'}`}>
                        {s.is_mock ? 'MOCK' : 'REAL'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'results' && currentRunId && (
          <div className="space-y-6">
            {runStatus && (
              <LiveProgress status={runStatus} />
            )}
            {report && (
              <Leaderboard report={report} onOpenAudit={openAudit} />
            )}
            {!report && !loading && (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-8 text-center text-gray-500">
                No results yet. Launch a run first.
              </div>
            )}
          </div>
        )}

        {activeTab === 'audit' && currentRunId && (
          <ItemAudit
            runId={currentRunId}
            selectedItem={selectedItem}
            selectedModel={selectedModel}
            onBack={() => setActiveTab('results')}
          />
        )}

        {activeTab === 'history' && (
          <RunsHistory
            runs={runs}
            onOpen={openRun}
            onRefresh={refreshRuns}
          />
        )}
      </main>
    </div>
  )
}
