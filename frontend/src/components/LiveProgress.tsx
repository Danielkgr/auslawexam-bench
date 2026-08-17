import { RunStatus } from '../api'

interface Props {
  status: RunStatus
}

export default function LiveProgress({ status }: Props) {
  const pct = status.n_total > 0 ? Math.round((status.n_completions / status.n_total) * 100) : 0
  const isRunning = status.status === 'running'

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
      <div className="flex items-center gap-2 mb-4">
        {isRunning && <span className="sse-dot" />}
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          {isRunning ? 'Run in progress' : status.status === 'done' ? 'Run complete' : 'Run errored'}
        </h2>
        {isRunning && (
          <span className="text-xs text-indigo-600 dark:text-indigo-400 font-mono">{status.run_id}</span>
        )}
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-gray-500 dark:text-slate-400 mb-1">
          <span>{status.n_completions} / {status.n_total} completions</span>
          <span>{pct}%</span>
        </div>
        <div className="h-2 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-600 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Model progress */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {status.models.map(m => (
          <div key={m.name} className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <span className={`w-1.5 h-1.5 rounded-full ${m.is_mock ? 'bg-amber-400' : 'bg-green-500'}`} />
              <span className="text-sm font-medium text-gray-900 dark:text-white">{m.name}</span>
              {m.is_mock && <span className="text-xs text-amber-600 dark:text-amber-400">mock</span>}
            </div>
            <div className="text-xs text-gray-500 dark:text-slate-400">
              {m.n_done}/{m.n_total} done · {m.n_ok} ok · {m.n_error} err
            </div>
            <div className="mt-1 h-1 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500"
                style={{ width: `${m.n_total > 0 ? (m.n_done / m.n_total) * 100 : 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {status.started_at && (
        <div className="mt-3 text-xs text-gray-400 dark:text-slate-500 font-mono">
          Started: {status.started_at}
          {status.finished_at && ` · Finished: {status.finished_at}`}
        </div>
      )}
    </div>
  )
}
