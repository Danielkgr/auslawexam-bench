interface Props {
  probe: { reachable: boolean; models: unknown[]; error?: string } | null
}

export default function LocalProbe({ probe }: Props) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
      <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Local endpoint</h2>
      {probe === null ? (
        <div className="text-sm text-gray-400 dark:text-slate-500">Probing…</div>
      ) : probe.reachable ? (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-sm text-green-700 dark:text-green-400 font-medium">Endpoint reachable</span>
          </div>
          {probe.models.length > 0 && (
            <div className="text-xs text-gray-500 dark:text-slate-400">
              <div className="font-medium mb-1">Loaded models:</div>
              <ul className="space-y-0.5 font-mono">
                {probe.models.map((m: any, i: number) => (
                  <li key={i}>• {typeof m === 'string' ? m : m.id || JSON.stringify(m)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span className="text-sm text-amber-700 dark:text-amber-400 font-medium">Endpoint not reachable</span>
          </div>
          <p className="text-xs text-gray-500 dark:text-slate-400 mb-2">
            The local OpenAI-compatible endpoint is down. All runs will use the seeded mock for the local slot.
          </p>
          {probe.error && (
            <code className="text-xs text-red-500 font-mono">{probe.error}</code>
          )}
        </div>
      )}
    </div>
  )
}
