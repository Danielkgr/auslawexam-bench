import { StatsReport } from '../api'

interface Props {
  report: StatsReport
  onOpenAudit: (runId: string, model: string, question: string) => void
}

export default function Leaderboard({ report, onOpenAudit }: Props) {
  return (
    <div className="space-y-6">
      {/* Main leaderboard table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Leaderboard</h2>
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
            {report.n_models} models · {report.n_questions_total} questions · Bootstrap 95% CI · Paired permutation tests
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-slate-700/50">
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400">#</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400">Model</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">Mean score (95% CI)</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">Fabricated rate (95% CI)</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">Q</th>
              </tr>
            </thead>
            <tbody>
              {report.models.map((m, i) => (
                <tr key={m.model} className="border-t border-gray-100 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-gray-500 dark:text-slate-400 font-mono text-xs">{i + 1}</td>
                  <td className="px-4 py-3">
                    <span className={`font-medium ${i === 0 ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-900 dark:text-white'}`}>
                      {m.model}
                    </span>
                    {m.is_mock && (
                      <span className="ml-2 text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 px-1.5 py-0.5 rounded">
                        mock
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs">
                    {m.mean_item_score_100.point.toFixed(1)}
                    <span className="text-gray-400 dark:text-slate-500">
                      [{m.mean_item_score_100.ci95[0].toFixed(1)}, {m.mean_item_score_100.ci95[1].toFixed(1)}]
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs">
                    <span className={m.fabricated_rate.point > 0.1 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}>
                      {m.fabricated_rate.point.toFixed(3)}
                    </span>
                    <span className="text-gray-400 dark:text-slate-500">
                      [{m.fabricated_rate.ci95[0].toFixed(3)}, {m.fabricated_rate.ci95[1].toFixed(3)}]
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 dark:text-slate-400">{m.n_questions}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pairwise significance */}
      {report.pairwise_permutation.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white">Pairwise significance</h2>
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">Paired permutation test (two-sided, α=0.05)</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-700/50">
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400">Model A</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400">Model B</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">Mean diff (A−B)</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">p-value</th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 dark:text-slate-400">Significant</th>
                </tr>
              </thead>
              <tbody>
                {report.pairwise_permutation.map(p => (
                  <tr key={`${p.a}-${p.b}`} className="border-t border-gray-100 dark:border-slate-700">
                    <td className="px-4 py-2 text-gray-900 dark:text-white font-medium">{p.a}</td>
                    <td className="px-4 py-2 text-gray-900 dark:text-white font-medium">{p.b}</td>
                    <td className="px-4 py-2 text-right font-mono text-xs">{p.mean_diff.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right font-mono text-xs">{p.p_value.toFixed(4)}</td>
                    <td className="px-4 py-2 text-center">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${p.significant_05 ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' : 'bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400'}`}>
                        {p.significant_05 ? 'yes' : 'n.s.'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* By difficulty */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">By difficulty</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-slate-700/50">
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400">Model</th>
                {['pass', 'credit', 'distinction', 'high_distinction'].map(d => (
                  <th key={d} className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">{d}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.models.map(m => (
                <tr key={m.model} className="border-t border-gray-100 dark:border-slate-700">
                  <td className="px-4 py-2 text-gray-900 dark:text-white font-medium">{m.model}</td>
                  {['pass', 'credit', 'distinction', 'high_distinction'].map(d => {
                    const v = m.per_difficulty[d] as { n: number; mean_item_score_100: number } | undefined
                    return (
                      <td key={d} className="px-4 py-2 text-right font-mono text-xs text-gray-600 dark:text-slate-300">
                        {v ? `${v.mean_item_score_100.toFixed(1)} (n=${v.n})` : '—'}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* By Priestley area */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">By Priestley area</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-slate-700/50">
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-slate-400">Model</th>
                {Object.keys(report.models[0]?.per_priestley ?? {}).map(area => (
                  <th key={area} className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-slate-400">{area}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.models.map(m => (
                <tr key={m.model} className="border-t border-gray-100 dark:border-slate-700">
                  <td className="px-4 py-2 text-gray-900 dark:text-white font-medium">{m.model}</td>
                  {Object.keys(m.per_priestley).map(area => {
                    const v = m.per_priestley[area] as { n: number; mean_item_score_100: number } | undefined
                    return (
                      <td key={area} className="px-4 py-2 text-right font-mono text-xs text-gray-600 dark:text-slate-300">
                        {v ? `${v.mean_item_score_100.toFixed(1)} (n=${v.n})` : '—'}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Method note */}
      <div className="text-xs text-gray-400 dark:text-slate-500">
        <p>{(report.method.ci as string)}. {(report.method.comparison as string)}.</p>
        <p className="mt-1">Run <code className="font-mono bg-gray-100 dark:bg-slate-700 px-1 rounded">{report.run_id}</code></p>
      </div>
    </div>
  )
}
