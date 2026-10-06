import { useState, useEffect } from 'react'
import { api, ItemResult, QuestionDetail, QuestionItem } from '../api'

interface Props {
  runId: string
  models: string[]
  selectedItem: string | null
  selectedModel: string | null
  onSelect: (model: string, item: string) => void
  onBack: () => void
}

export default function ItemAudit({ runId, models, selectedItem, selectedModel, onSelect, onBack }: Props) {
  const [results, setResults] = useState<ItemResult[]>([])
  const [questions, setQuestions] = useState<QuestionItem[]>([])
  const [question, setQuestion] = useState<QuestionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedRep, setSelectedRep] = useState<number | null>(null)

  const model = selectedModel || models[0] || ''
  const item = selectedItem || ''

  useEffect(() => {
    api.getQuestions().then(setQuestions).catch(() => setQuestions([]))
  }, [])

  // Pick the first question this slot answered when none is chosen yet.
  useEffect(() => {
    if (!model) return
    setLoading(true)
    api.getItemResults(runId, model, item || undefined)
      .then(rows => {
        if (!item && rows.length > 0) {
          onSelect(model, rows[0].item_id)
        } else {
          setResults(rows)
          setSelectedRep(rows.length > 0 ? rows[0].rep : null)
        }
      })
      .catch(() => setResults([]))
      .finally(() => setLoading(false))
  }, [runId, model, item])

  useEffect(() => {
    if (item) api.getQuestion(item).then(setQuestion).catch(() => setQuestion(null))
  }, [item])

  const itemResults = results.filter(r => r.item_id === item && r.model === model)
  const reps = [...new Set(itemResults.map(r => r.rep))]
  const active = itemResults.find(r => r.rep === selectedRep) ?? itemResults[0]
  const maxFor = (criterion: string) =>
    question?.rubric.find(c => c.criterion === criterion)?.max ?? 1

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={onBack} className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-slate-200">Back</button>
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Item audit</h2>
          <select
            aria-label="Model slot"
            value={model}
            onChange={e => onSelect(e.target.value, item)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-md px-2 py-1 bg-white dark:bg-slate-700 dark:text-white"
          >
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <select
            aria-label="Question"
            value={item}
            onChange={e => onSelect(model, e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-md px-2 py-1 bg-white dark:bg-slate-700 dark:text-white"
          >
            {questions.map(q => <option key={q.id} value={q.id}>{q.id} ({q.priestley_area})</option>)}
          </select>
          {reps.length > 1 && (
            <div className="flex gap-2 ml-auto">
              {reps.map(rep => (
                <button
                  key={rep}
                  onClick={() => setSelectedRep(rep)}
                  className={`px-3 py-1 text-sm rounded-lg border transition-colors ${
                    active?.rep === rep
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
      </div>

      {loading ? (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-8 text-center text-gray-500">Loading...</div>
      ) : active ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Question */}
          <div className="lg:col-span-1 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 space-y-3">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Question</h3>
            <div className="space-y-1 text-xs">
              <div><span className="text-gray-500 dark:text-slate-400">ID:</span> <code className="font-mono text-gray-700 dark:text-slate-200">{active.item_id}</code></div>
              <div><span className="text-gray-500 dark:text-slate-400">Area:</span> <span className="text-gray-700 dark:text-slate-200">{active.priestley_area}</span></div>
              <div><span className="text-gray-500 dark:text-slate-400">Difficulty:</span> <span className="text-gray-700 dark:text-slate-200">{active.difficulty}</span></div>
              {active.is_mock ? (
                <div className="text-amber-600 dark:text-amber-400 font-medium">Mock slot: this answer is synthetic</div>
              ) : (
                <div className="text-green-700 dark:text-green-400 font-medium">Real model output</div>
              )}
              {active.contamination_flag && (
                <div className="text-red-600 dark:text-red-400 font-medium">Contamination flag</div>
              )}
            </div>
            {question && (
              <>
                <p className="text-xs text-gray-700 dark:text-slate-200 leading-relaxed">{question.question_text}</p>
                <div>
                  <div className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Required authorities</div>
                  <ul className="space-y-1">
                    {question.required_authorities.map(a => (
                      <li key={a.cite} className="text-xs font-mono text-gray-700 dark:text-slate-200">{a.cite}</li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>

          {/* Answer */}
          <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Model answer</h3>
            <pre className="text-xs text-gray-700 dark:text-slate-200 font-mono bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 whitespace-pre-wrap overflow-auto max-h-96">
              {active.answer_text || '[no answer]'}
            </pre>
          </div>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-8 text-center text-gray-500">No scored answer for this slot and question.</div>
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
              <div className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Rubric breakdown (seeded mock judge)</div>
              <div className="space-y-1">
                {Object.entries(active.rubric).map(([criterion, score]) => (
                  <div key={criterion} className="flex items-center gap-3 text-xs">
                    <span className="text-gray-600 dark:text-slate-300 w-64 truncate">{criterion}</span>
                    <div className="flex-1 h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500" style={{ width: `${Math.min(100, (score / maxFor(criterion)) * 100)}%` }} />
                    </div>
                    <span className="font-mono text-gray-500 dark:text-slate-400 w-16 text-right">{score.toFixed(2)} / {maxFor(criterion)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Citation audit */}
          {active.citations.length > 0 ? (
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
          ) : (
            <div className="mt-4 text-xs text-gray-400 dark:text-slate-500">No citations extracted from this answer.</div>
          )}
        </div>
      )}
    </div>
  )
}
