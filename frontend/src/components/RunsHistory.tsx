import { RunSummary } from '../api'

interface Props {
  runs: RunSummary[]
  onOpen: (runId: string) => void
  onRefresh: () => void
}

export default function RunsHistory({ runs, onOpen, onRefresh }: Props) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">Runs history</h2>
        <button onClick={onRefresh} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">Refresh</button>
      </div>
      {runs.length === 0 ? (
        <div className="p-8 text-center text-gray-500 dark:text-slate-400 text-sm">
          No runs yet. Launch a run to see it here.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-slate-700/50">
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400">Run ID</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400">Started</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400">Models</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">Items</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">Reps</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">OK</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">Errors</th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 dark:text-slate-400">Action</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(r => (
                <tr key={r.run_id} className="border-t border-gray-100 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/30">
                  <td className="px-4 py-3 font-mono text-xs text-indigo-600 dark:text-indigo-400">{r.run_id}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 dark:text-slate-400">{r.started_at}</td>
                  <td className="px-4 py-3 text-xs text-gray-700 dark:text-slate-200">{r.models.join(', ')}</td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-gray-600 dark:text-slate-300">{r.n_items}</td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-gray-600 dark:text-slate-300">{r.n_reps}</td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-green-600 dark:text-green-400">{r.n_ok}</td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-red-600 dark:text-red-400">{r.n_error}</td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => onOpen(r.run_id)}
                      className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
