import { useState, useEffect } from 'react'
import { api } from '../api'

export default function CredentialsPanel({ onRefresh }: { onRefresh: () => void }) {
  const [keys, setKeys] = useState({ openai: '', anthropic: '', google: '' })
  const [localUrl, setLocalUrl] = useState('http://localhost:10000/v1')
  const [localModel, setLocalModel] = useState('14. Qwen3.8-27B (Q5_K_M)')
  const [enableThinking, setEnableThinking] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<Record<string, { ok: boolean; detail: string }>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getKeys().then(k => {
      // We can't see the keys, only whether they exist
    }).catch(() => {})
  }, [])

  const handleSave = async () => {
    await api.setKeys({
      openai_key: keys.openai || undefined,
      anthropic_key: keys.anthropic || undefined,
      google_key: keys.google || undefined,
      local_base_url: localUrl,
      local_model: localModel,
      local_enable_thinking: enableThinking,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    onRefresh()
  }

  const testProvider = async (provider: 'openai' | 'anthropic' | 'google') => {
    setTesting(provider)
    try {
      const result = await api.testConnection(provider)
      setTestResult(prev => ({ ...prev, [provider]: result }))
    } finally {
      setTesting(null)
    }
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
      <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4">API Credentials</h2>
      <p className="text-sm text-gray-500 dark:text-slate-400 mb-5">
        Keys are stored locally only (never sent to third parties or logged). Leave blank to run a slot as a seeded mock.
      </p>

      <div className="space-y-4">
        {([
          ['openai', 'OpenAI', 'OPENAI_API_KEY'],
          ['anthropic', 'Anthropic', 'ANTHROPIC_API_KEY'],
          ['google', 'Google Gemini', 'GOOGLE_API_KEY'],
        ] as [string, string, string][]).map(([provider, label, envVar]) => (
          <div key={provider} className="flex items-center gap-3">
            <div className="w-24 text-sm font-medium text-gray-700 dark:text-slate-200">{label}</div>
            <input
              type="password"
              placeholder="Enter API key…"
              value={keys[provider as keyof typeof keys]}
              onChange={e => setKeys(prev => ({ ...prev, [provider]: e.target.value }))}
              className="flex-1 px-3 py-1.5 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
            />
            <button
              onClick={() => testProvider(provider as 'openai' | 'anthropic' | 'google')}
              disabled={testing === provider || !keys[provider as keyof typeof keys]}
              className="px-3 py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {testing === provider ? '…' : 'Test'}
            </button>
            {testResult[provider] && (
              <span className={`text-xs ${testResult[provider].ok ? 'text-green-600' : 'text-red-500'}`}>
                {testResult[provider].ok ? '✓ OK' : '✗ ' + testResult[provider].detail}
              </span>
            )}
          </div>
        ))}

        <div className="border-t border-gray-100 dark:border-slate-700 pt-4 mt-4">
          <div className="text-sm font-medium text-gray-900 dark:text-white mb-3">Local Slot (llama.cpp / open-weight)</div>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-32 text-sm font-medium text-gray-700 dark:text-slate-200">Base URL</div>
              <input
                type="text"
                value={localUrl}
                onChange={e => setLocalUrl(e.target.value)}
                className="flex-1 px-3 py-1.5 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-900 dark:text-white font-mono focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
              />
            </div>
            <div className="flex items-center gap-3">
              <div className="w-32 text-sm font-medium text-gray-700 dark:text-slate-200">Model</div>
              <input
                type="text"
                value={localModel}
                onChange={e => setLocalModel(e.target.value)}
                className="flex-1 px-3 py-1.5 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-900 dark:text-white font-mono focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
              />
            </div>
            <div className="flex items-center gap-3">
              <div className="w-32 text-sm font-medium text-gray-700 dark:text-slate-200">Enable thinking</div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableThinking}
                  onChange={e => setEnableThinking(e.target.checked)}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-600 dark:text-slate-400">
                  {enableThinking ? 'ON (for thinking models)' : 'OFF (default — recommended)'}
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <button
          onClick={handleSave}
          className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors"
        >
          {saved ? '✓ Saved' : 'Save credentials'}
        </button>
        <span className="text-xs text-gray-400 dark:text-slate-500">
          Keys are stored in ~/.auslex-ui/keys.json (0600)
        </span>
      </div>
    </div>
  )
}
