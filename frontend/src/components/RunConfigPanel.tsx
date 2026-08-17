import { useState } from 'react'
import { api, SlotStatus, RunConfig } from '../api'

interface Props {
  slots: SlotStatus[]
  localProbe: { reachable: boolean; models: unknown[]; error?: string } | null
  onLaunch: (cfg: RunConfig) => void
  loading: boolean
  onRunDemo: () => void
}

export default function RunConfigPanel({ slots, localProbe, onLaunch, loading, onRunDemo }: Props) {
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set(['gpt', 'claude', 'gemini', 'local']))
  const [nReps, setNReps] = useState(3)
  const [baseSeed, setBaseSeed] = useState(0)
  const [questionFilter, setQuestionFilter] = useState('')
  const [priestleyFilter, setPriestleyFilter] = useState('')
  const [jurisdictionFilter, setJurisdictionFilter] = useState('')
  const [difficultyFilter, setDifficultyFilter] = useState('')

  const toggleModel = (name: string) => {
    setSelectedModels(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const handleLaunch = () => {
    onLaunch({
      models: Array.from(selectedModels),
      n_reps: nReps,
      base_seed: baseSeed,
      question_filter: questionFilter || undefined,
      priestley_filter: priestleyFilter || undefined,
      jurisdiction_filter: jurisdictionFilter || undefined,
      difficulty_filter: difficultyFilter || undefined,
    })
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
      <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4">Run Configuration</h2>

      {/* Model selection */}
      <div className="mb-5">
        <div className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-2">Model slots</div>
        <div className="flex flex-wrap gap-2">
          {slots.map(s => (
            <button
              key={s.name}
              onClick={() => toggleModel(s.name)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-all ${
                selectedModels.has(s.name)
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200 border-gray-200 dark:border-slate-600 hover:border-indigo-300'
              }`}
            >
              <span className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${s.is_real ? 'bg-green-400' : 'bg-amber-400'}`} />
                {s.name}
                <span className="text-xs opacity-60">{s.is_mock ? 'mock' : 'real'}</span>
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Parameters */}
      <div className="grid grid-cols-2 gap-4 mb-5">
        <div>
          <div className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Repetitions</div>
          <input
            type="number"
            min="1"
            max="20"
            value={nReps}
            onChange={e => setNReps(Number(e.target.value))}
            className="w-full px-3 py-1.5 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
          />
        </div>
        <div>
          <div className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Base seed</div>
          <input
            type="number"
            min="0"
            value={baseSeed}
            onChange={e => setBaseSeed(Number(e.target.value))}
            className="w-full px-3 py-1.5 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
          />
        </div>
      </div>

      {/* Filters */}
      <div className="mb-5">
        <div className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-2">Filters (leave blank for all)</div>
        <div className="grid grid-cols-2 gap-3">
          <input
            placeholder="Question IDs (comma-separated)"
            value={questionFilter}
            onChange={e => setQuestionFilter(e.target.value)}
            className="px-3 py-1.5 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-900 dark:text-white font-mono text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
          />
          <input
            placeholder="Priestley areas (comma-separated)"
            value={priestleyFilter}
            onChange={e => setPriestleyFilter(e.target.value)}
            className="px-3 py-1.5 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-900 dark:text-white font-mono text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
          />
          <input
            placeholder="Jurisdictions (Cth, NSW, VIC…)"
            value={jurisdictionFilter}
            onChange={e => setJurisdictionFilter(e.target.value)}
            className="px-3 py-1.5 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-900 dark:text-white font-mono text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
          />
          <input
            placeholder="Difficulty (pass, credit…)"
            value={difficultyFilter}
            onChange={e => setDifficultyFilter(e.target.value)}
            className="px-3 py-1.5 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-900 dark:text-white font-mono text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
          />
        </div>
      </div>

      {/* Temperature note */}
      <div className="mb-5 text-xs text-gray-400 dark:text-slate-500 flex items-center gap-2">
        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 00-1 1 1 1 0 102 0v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/></svg>
        Temperature is fixed at 0 for reproducibility.
      </div>

      {/* Buttons */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleLaunch}
          disabled={loading || selectedModels.size === 0}
          className="px-5 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/></svg>
              Running…
            </>
          ) : (
            'Launch run'
          )}
        </button>
        <button
          onClick={onRunDemo}
          disabled={loading}
          className="px-5 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors disabled:opacity-50"
        >
          Run demo (mock)
        </button>
      </div>
    </div>
  )
}
