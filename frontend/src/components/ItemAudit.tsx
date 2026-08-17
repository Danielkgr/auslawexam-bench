import { useState, useEffect } from 'react'
import { api, ItemResult } from '../api'

interface Props {
  runId: string
  selectedItem: string | null
  selectedModel: string | null
  onBack: () => void
}

export default function ItemAudit({ runId, selectedItem, selectedModel, onBack }: Props) {
  const [results, setResults] = useState<ItemResult[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedRep, setSelectedRep] = useState<number | null>(null)

  useEffect(() => {
    if (selectedItem && selectedModel) {
      setLoading(true)
      api.getItemResults(runId, selectedModel, selectedItem)
        .then(setResults)
        .finally(() => setLoading(false))
      if (results.length > 0) {
        setSelectedRep(results[0].rep)
      }
    }
  }, [runId, selectedItem, selectedModel])

  if (!selectedItem || !selectedModel) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-8 text-center text-gray-500">
        No item selected. <button onClick={onBack} className="text-indigo-600 hover:underline">Go back</button>
      </div>
    )
  }

  const itemResults = results.filter(r => r.item_id === selectedItem && r.model === selectedModel)
  const reps = [...new Set(itemResults.map(r => r.rep))]
  const active = selectedRep !== null ? itemResults.find(r => r.rep === selectedRep) ?? itemResults[0] : itemResults[0]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
        <div className="flex items-center gap-3 mb-3">
          <button onClick={onBack} className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-slate-200">← Back</button>
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            Item Audit: <span className="font-mono">{selectedItem}</span>
          </h2>
          <span className="text-sm text-gray-500 dark:text-slate-400">{selectedModel}</span>
        </div>

        {/* Rep selector */}
        {reps.length > 1 && (
          <div className="flex gap-2 mb-4">
            {reps.map(rep => (
              <button
                key={rep}
                onClick={() => setSelectedRep(rep)}
                className={`px-3 py-1 text-sm rounded-lg border transition-colors ${
                  selectedRep === rep
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200 border-gray-200 dark:border-slate-600 hover:border-indigo-300'
                }`}
              >
                Rep {rep}
              </button>
            ))}
          </div>
        )}
      </div>

      {loading ? (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-8 text-center text-gray-500">Loading…</div>
      ) : active ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Question */}
          <div className="lg:col-span-1 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Question</h3>
            <div className="space-y-2 text-xs mb-4">
              <div><span className="text-gray-500 dark:text-slate-400">ID:</span> <code className="font-mono text-gray-700 dark:text-slate-200">{active.item_id}</code></div>
              <div><span className="text-gray-500 dark:text-slate-400">Type:</span> <span className="text-gray-700 dark:text-slate-200">{active.priestley_area}</span></div>
              <div><span className="text-gray-500 dark:text-slate-400">Difficulty:</span> <span className="text-gray-700 dark:text-slate-200">{active.difficulty}</span></div>
              <div><span className="text-gray-500 dark:text-slate-400">Rep:</span> <span className="text-gray-700 dark:text-slate-200">{active.rep}</span></div>
              {active.is_mock && (
                <div><span className="text-amber-600 dark:text-amber-400">⚠ MOCK slot</span></div>
              )}
              {active.contamination_flag && (
                <div><span className="text-red-600 dark:text-red-400 font-medium">⚠ Contamination flag</span></div>
              )}
            </div>
          </div>

          {/* Answer */}
          <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Model Answer</h3>
            <pre className="text-xs text-gray-700 dark:text-slate-200 font-mono bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 whitespace-pre-wrap overflow-auto max-h-96">
              {active.answer_text || '[no answer]'}
            </pre>
          </div>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-8 text-center text-gray-500">No results for this combination.</div>
      )}

      {/* Metrics */}
      {active && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Scoring</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
              <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">Item score</div>
              <div className="text-xl font-bold font-mono text-gray-900 dark:text-white">{active.item_score_100.toFixed(1)}<span className="text-sm text-gray-400">/100</span></div>
            </div>
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
              <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">Fabricated rate</div>
              <div className={`text-xl font-bold font-mono ${active.fabricated_rate > 0.1 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                {active.fabricated_rate.toFixed(3)}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
              <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">Total citations</div>
              <div className="text-xl font-bold font-mono text-gray-900 dark:text-white">{active.total_citations}</div>
            </div>
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
              <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">On-point rate</div>
              <div className="text-xl font-bold font-mono text-gray-900 dark:text-white">{active.on_point_rate.toFixed(3)}</div>
            </div>
          </div>

          {/* Rubric breakdown */}
          {Object.keys(active.rubric).length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Rubric breakdown</div>
              <div className="space-y-1">
                {Object.entries(active.rubric).map(([criterion, score]) => (
                  <div key={criterion} className="flex items-center gap-3 text-xs">
                    <span className="text-gray-600 dark:text-slate-300 w-40 truncate">{criterion}</span>
                    <div className="flex-1 h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500" style={{ width: `${Math.min(100, score * 100)}%` }} />
                    </div>
                    <span className="font-mono text-gray-500 dark:text-slate-400 w-12 text-right">{score.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Citation audit */}
          {active.citations.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Citation audit</div>
              <div className="space-y-1">
                {active.citations.map((c, i) => (
                  <div key={i} className="flex items-start gap-3 text-xs py-1.5 border-b border-gray-50 dark:border-slate-700/50 last:border-0">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium shrink-0 ${
                      c.classification === 'on_point' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                      : c.classification === 'known_other' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                      : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                    }`}>
                      {c.classification}
                    </span>
                    <span className="text-gray-500 dark:text-slate-500 w-16 shrink-0">{c.kind}</span>
                    <code className="font-mono text-gray-700 dark:text-slate-200 flex-1 overflow-x-auto">{c.raw}</code>
                  </div>
                ))}
              </div>
            </div>
          )}

          {active.citations.length === 0 && (
            <div className="mt-4 text-xs text-gray-400 dark:text-slate-500">No citations extracted from this answer.</div>
          )}
        </div>
      )}
    </div>
  )
}
