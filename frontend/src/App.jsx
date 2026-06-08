import { useEffect, useMemo, useState } from 'react'
import {
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const COLORS = ['#c4786e', '#7878b4', '#5e8e74', '#5e7e9e', '#a07848', '#8e68a4']

function formatChartData(chart, data) {
  if (!data || !chart) return []
  const { x_key, y_key } = chart
  return data.map((row) => ({
    name: row[x_key]?.toString() || 'Unknown',
    value: typeof row[y_key] === 'number' ? row[y_key] : Number(row[y_key]) || 0,
    ...row,
  }))
}

function ChartPanel({ chart, data }) {
  const chartData = useMemo(() => formatChartData(chart, data), [chart, data])

  if (!chartData.length) {
    return <div className="chart-panel empty">No chart data available</div>
  }

  if (chart.type.includes('pie')) {
    return (
      <div className="chart-panel">
        <h3>{chart.title}</h3>
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie data={chartData} dataKey="value" nameKey="name" outerRadius={100} label>
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    )
  }

  const isLine = chart.type.includes('line')
  const isHorizontal = chart.type.includes('horizontal')

  return (
    <div className="chart-panel">
      <h3>{chart.title}</h3>
      <ResponsiveContainer width="100%" height={280}>
        {isLine ? (
          <LineChart data={chartData} margin={{ top: 12, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6a6460' }} />
            <YAxis tick={{ fontSize: 11, fill: '#6a6460' }} />
            <Tooltip contentStyle={{ background: '#2a2a2a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
            <Legend />
            <Line type="monotone" dataKey="value" stroke="#c4786e" strokeWidth={2} dot={false} />
          </LineChart>
        ) : (
          <BarChart data={chartData} margin={{ top: 12, right: 20, left: 0, bottom: 0 }} layout={isHorizontal ? 'vertical' : 'horizontal'}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            {isHorizontal ? (
              <XAxis type="number" tick={{ fontSize: 11, fill: '#6a6460' }} />
            ) : (
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6a6460' }} />
            )}
            <YAxis type={isHorizontal ? 'category' : 'number'} dataKey={isHorizontal ? 'name' : undefined} tick={{ fontSize: 11, fill: '#6a6460' }} />
            <Tooltip contentStyle={{ background: '#2a2a2a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
            <Legend />
            <Bar dataKey="value" fill="#7878b4" radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}

function App() {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const samples = [
    'show total revenue by product category',
    'top 5 customers by order count',
    'monthly sales trend for the last year',
    'total payments received by month',
  ]

  useEffect(() => { fetchHistory() }, [])

  async function fetchHistory() {
    try {
      const res = await fetch(`${API_URL}/history`)
      const json = await res.json()
      setHistory(json.history || [])
    } catch (err) { console.error(err) }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!question.trim()) return
    setLoading(true)
    setError(null)
    setResponse(null)
    try {
      const res = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
      })
      if (!res.ok) {
        const json = await res.json()
        throw new Error(json.detail || json.message || 'Request failed')
      }
      const json = await res.json()
      setResponse(json)
      await fetchHistory()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const insightItems = useMemo(() => response?.key_insights || [], [response])

  return (
    <div className="app-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <p className="eyebrow">Dashboard</p>
          <h1>Drax BI</h1>
          <p className="subtitle">Ask business questions in natural language.</p>
        </div>

        <div className="panel panel-primary sidebar-panel">
          <h2>Ask a question</h2>
          <form onSubmit={handleSubmit} className="query-form">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. show total revenue by product category"
              rows={3}
            />
            <div className="form-actions">
              <button type="submit" disabled={loading}>
                {loading ? 'Generating…' : 'Run query'}
              </button>
              <button type="button" className="secondary" onClick={() => setQuestion('')}>
                Clear
              </button>
            </div>
          </form>
          <div className="examples">
            <strong>Examples:</strong>
            <div className="example-list">
              {samples.map((sample) => (
                <button key={sample} type="button" onClick={() => setQuestion(sample)}>
                  {sample}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="panel panel-secondary sidebar-panel sidebar-history">
          <h2>Session history</h2>
          <div className="history-card">
            {history.length === 0 ? (
              <p className="empty-text">No history yet.</p>
            ) : (
              <ol className="history-list">
                {history.slice().reverse().map((item, index) => (
                  <li key={`${item.question}-${index}`}>
                    <div className="history-meta">
                      <span>{new Date(item.timestamp).toLocaleString()}</span>
                      <span>{item.row_count} rows</span>
                    </div>
                    <p>{item.question}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main dashboard ── */}
      <main className="dashboard">
        <div className="dashboard-header">
          <h2>Dashboard</h2>
        </div>

        {error && <div className="alert">{error}</div>}

        {response ? (
          <div className="dashboard-content">
            <div className="summary-grid">
              <div className="summary-card">
                <span className="label">Answer</span>
                <p>{response.answer}</p>
              </div>
              <div className="summary-card">
                <span className="label">DB Type</span>
                <p>{response.db_type}</p>
              </div>
              <div className="summary-card">
                <span className="label">Rows</span>
                <p>{response.row_count}</p>
              </div>
              <div className="summary-card">
                <span className="label">Self-Healed</span>
                <p>{response.self_healed ? 'Yes' : 'No'}</p>
              </div>
            </div>

            <div className="insights">
              <h3>Key insights</h3>
              <ul>
                {insightItems.map((insight, index) => (
                  <li key={index}>{insight}</li>
                ))}
              </ul>
            </div>

            <div className="charts-grid">
              {response.charts.length ? (
                response.charts.map((chart, idx) => (
                  <ChartPanel key={`${chart.title}-${idx}`} chart={chart} data={response.data} />
                ))
              ) : (
                <div className="chart-panel empty">No charts returned from the API.</div>
              )}
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon">⬡</div>
            <p>Run a query to generate the dashboard and charts.</p>
          </div>
        )}
      </main>
    </div>
  )
}

export default App