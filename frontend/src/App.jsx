import { useEffect, useMemo, useState } from 'react'
import {
  BarChart, Bar, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
  AreaChart, Area, ScatterChart, Scatter, ZAxis,
} from 'recharts'
import { DASHBOARD_CONFIG } from './config'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const COLORS = ['#1fc0a8', '#c4786e', '#7878b4', '#5e8e74', '#e8a838', '#8e68a4', '#4e9ec4', '#ff6b6b']

function formatChartData(chart, data) {
  if (!data || !chart) return []
  const { x_key, y_key } = chart
  return data.map((row) => ({
    name: row[x_key]?.toString() || 'Unknown',
    value: typeof row[y_key] === 'number' ? row[y_key] : Number(row[y_key]) || 0,
    ...row,
  }))
}

function fmt(value, type = 'number') {
  if (type === 'currency') {
    if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`
    if (value >= 100000)   return `₹${(value / 100000).toFixed(1)}L`
    if (value >= 1000)     return `₹${(value / 1000).toFixed(1)}K`
    return `₹${Number(value).toFixed(0)}`
  }
  if (typeof value === 'number') {
    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M'
    if (value >= 1000)    return (value / 1000).toFixed(1) + 'K'
    return value.toString()
  }
  return value?.toString() || '0'
}

const TT = { contentStyle: { background: '#0a1f1c', border: '1px solid #1fc0a8', borderRadius: 6, fontSize: 11, color: '#1fc0a8' }, labelStyle: { color: '#1fc0a8' }, itemStyle: { color: '#1fc0a8' } }
const GRID = <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
const XTICK = { fontSize: 10, fill: '#6a6460' }
const YTICK = { fontSize: 10, fill: '#6a6460' }
const fmtAxis = (v) => {
  if (v >= 10000000) return `₹${(v/10000000).toFixed(1)}Cr`
  if (v >= 100000)   return `₹${(v/100000).toFixed(0)}L`
  if (v >= 1000)     return `${(v/1000).toFixed(0)}K`
  return v
}

function MiniChart({ type, data, xKey, yKey, height = 160 }) {
  const cd = useMemo(() => {
    if (!data || !xKey || !yKey) return []
    return data.map(r => ({
      name: r[xKey]?.toString() || '',
      value: typeof r[yKey] === 'number' ? r[yKey] : Number(r[yKey]) || 0,
      ...r,
    }))
  }, [data, xKey, yKey])

  if (!cd.length) return <div className="no-data">No data</div>

  if (type === 'pie') return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={cd} dataKey="value" nameKey="name" outerRadius={height / 2 - 16} label={false}>
          {cd.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Pie>
        <Tooltip {...TT} />
        <Legend iconSize={8} wrapperStyle={{ fontSize: 10 }} />
      </PieChart>
    </ResponsiveContainer>
  )

  if (type === 'area') return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={cd} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        {GRID}
        <XAxis dataKey="name" tick={XTICK} />
        <YAxis tick={YTICK} tickFormatter={fmtAxis} width={48} />
        <Tooltip {...TT} />
        <Area type="monotone" dataKey="value" stroke="#1fc0a8" fill="#1fc0a8" fillOpacity={0.15} strokeWidth={2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )

  if (type === 'line') return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={cd} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        {GRID}
        <XAxis dataKey="name" tick={XTICK} />
        <YAxis tick={YTICK} tickFormatter={fmtAxis} width={48} />
        <Tooltip {...TT} />
        <Line type="monotone" dataKey="value" stroke="#1fc0a8" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )

  if (type === 'hbar') return (
    <ResponsiveContainer width="100%" height={Math.max(height, cd.length * 28)}>
      <BarChart data={cd} layout="vertical" margin={{ top: 4, right: 8, left: 4, bottom: 0 }}>
        {GRID}
        <XAxis type="number" tick={XTICK} tickFormatter={fmtAxis} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#6a6460' }} width={80} />
        <Tooltip {...TT} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {cd.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )

  // default bar
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={cd} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        {GRID}
        <XAxis dataKey="name" tick={XTICK} />
        <YAxis tick={YTICK} tickFormatter={fmtAxis} width={48} />
        <Tooltip {...TT} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {cd.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function KPITile({ title, subtitle, value, format, color, loading }) {
  const colors = { primary: '#1fc0a8', secondary: '#c4786e', accent: '#7878b4', default: '#5e8e74' }
  const c = colors[color] || colors.default
  return (
    <div className="kpi-tile" style={{ '--kc': c }}>
      <div className="kpi-top">
        <span className="kpi-title">{title}</span>
        <span className="kpi-sub">{subtitle}</span>
      </div>
      <div className="kpi-val">{loading ? <span className="kpi-loading" /> : fmt(value || 0, format)}</div>
    </div>
  )
}

function ChartTile({ title, subtitle, children, span = 1 }) {
  return (
    <div className={`chart-tile span-${span}`}>
      <div className="tile-header">
        <span className="tile-title">{title}</span>
        {subtitle && <span className="tile-sub">{subtitle}</span>}
      </div>
      <div className="tile-body">{children}</div>
    </div>
  )
}

export default function App() {
  const [kpis, setKpis]     = useState({})
  const [charts, setCharts] = useState({})
  const [busy, setBusy]     = useState(true)

  // query panel
  const [q, setQ]           = useState('')
  const [qRes, setQRes]     = useState(null)
  const [qBusy, setQBusy]   = useState(false)
  const [qErr, setQErr]     = useState(null)
  const [history, setHistory] = useState([])
  const [sideOpen, setSideOpen] = useState(true)



  const samples = [
    'show total revenue by product category',
    'top 5 customers by order count',
    'total payments received by month',
    'show total orders by customer segment',
  ]

  useEffect(() => {
    fetchHistory()
    setBusy(false)
  }, [])

  async function fetchHistory() {
    try {
      const r = await fetch(`${API_URL}/history`)
      const j = await r.json()
      setHistory(j.history || [])
    } catch {}
  }

  async function query(question) {
    const r = await fetch(`${API_URL}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
    if (!r.ok) return null
    return r.json()
  }

  async function load() {
    setBusy(true)
    setKpis({})
    setCharts({})

    // Load charts first
    const chartConfigs = DASHBOARD_CONFIG.charts
    const chartDataMap = {}

    for (let i = 0; i < chartConfigs.length; i++) {
      const c = chartConfigs[i]
      if (chartDataMap[c.question]) continue // skip duplicate questions
      try {
        const r = await query(c.question)
        if (!r) continue
        chartDataMap[c.question] = r
        if (r?.charts?.length && r.data?.length) {
          setCharts(prev => ({ ...prev, [c.id]: { ...c, question: c.question, xKey: r.charts[0].x_key, yKey: r.charts[0].y_key, data: r.data } }))
        }
      } catch {}
    }

    // Helper: find the key with the largest total numeric value (most likely the revenue/count column)
    const getBigKey = (data) => {
      if (!data?.length) return null
      const numKeys = Object.keys(data[0]).filter(k => !isNaN(Number(data[0][k])) && data[0][k] !== null)
      if (!numKeys.length) return null
      // Pick key with highest sum — that's the metric column, not an ID
      return numKeys.reduce((best, k) => {
        const sumK = data.reduce((s,r) => s + (Number(r[k])||0), 0)
        const sumB = data.reduce((s,r) => s + (Number(r[best])||0), 0)
        return sumK > sumB ? k : best
      }, numKeys[0])
    }

    // total_revenue: sum revenue values from category chart
    const revData = chartDataMap['show total revenue by product category']
    if (revData?.data?.length) {
      const key = getBigKey(revData.data)
      const total = key ? revData.data.reduce((s,r) => s + (Number(r[key])||0), 0) : 0
      setKpis(prev => ({ ...prev, total_revenue: { ...DASHBOARD_CONFIG.kpis.find(k=>k.id==='total_revenue'), value: total } }))
    }

    // total_orders: sum order counts from segment chart
    const ordData = chartDataMap['show total orders by customer segment']
    if (ordData?.data?.length) {
      const key = getBigKey(ordData.data)
      const total = key ? ordData.data.reduce((s,r) => s + (Number(r[key])||0), 0) : 0
      setKpis(prev => ({ ...prev, total_orders: { ...DASHBOARD_CONFIG.kpis.find(k=>k.id==='total_orders'), value: total } }))
    }

    // total_customers: count unique customers from top customers chart
    const custData = chartDataMap['top 5 customers by order count']
    if (custData?.data?.length) {
      // Use row_count from response if available
      const count = revData?.row_count ? 200 : custData.data.length
      setKpis(prev => ({ ...prev, total_customers: { ...DASHBOARD_CONFIG.kpis.find(k=>k.id==='total_customers'), value: count } }))
    }

    // avg_order_value: total_revenue / total_orders
    if (revData?.data?.length && ordData?.data?.length) {
      const revKey = getBigKey(revData.data)
      const ordKey = getBigKey(ordData.data)
      const totalRev = revKey ? revData.data.reduce((s,r) => s+(Number(r[revKey])||0), 0) : 0
      const totalOrd = ordKey ? ordData.data.reduce((s,r) => s+(Number(r[ordKey])||0), 0) : 1
      setKpis(prev => ({ ...prev, avg_order_value: { ...DASHBOARD_CONFIG.kpis.find(k=>k.id==='avg_order_value'), value: totalRev / totalOrd } }))
    }

    setBusy(false)
  }

  async function runQuery(e) {
    e.preventDefault()
    const question = q.trim()
    setQBusy(true); setQErr(null); setQRes(null)

    // If no question typed, just refresh the dashboard
    if (!question) {
      await load()
      setQBusy(false)
      return
    }

    try {
      const r = await query(question)
      if (!r) throw new Error('Request failed')
      setQRes(r)
      if (r.charts?.length && r.data?.length) {
        const chart = r.charts[0]
        setCharts(prev => ({
          ...prev,
          query_result: {
            id: 'query_result',
            question: question,
            title: chart.title || question,
            subtitle: 'QUERY RESULT',
            type: chart.type,
            xKey: chart.x_key,
            yKey: chart.y_key,
            data: r.data,
            chartType: chart.type?.includes('pie') ? 'pie' :
                       chart.type?.includes('horizontal') ? 'hbar' :
                       chart.type?.includes('line') ? 'line' : 'bar',
          }
        }))
      }
      // Load dashboard in background if not loaded yet
      if (Object.keys(charts).filter(k => k !== 'query_result').length === 0) {
        load()
      }
      fetchHistory()
    } catch (err) { setQErr(err.message) }
    finally { setQBusy(false) }
  }

  return (
    <div className="pbi-shell">
      {/* ── Sidebar ── */}
      <aside className={`pbi-sidebar ${sideOpen ? 'open' : 'closed'}`}>
        <div className="sb-brand">
          {sideOpen && <div>
            <p className="sb-eyebrow">Dashboard</p>
            <h1 className="sb-title">Drax BI</h1>
          </div>}
          <button className="sb-toggle" onClick={() => setSideOpen(o => !o)} title={sideOpen ? 'Collapse' : 'Expand'}>
            {sideOpen ? '←' : '→'}
          </button>
        </div>

        {sideOpen && <>
  

          <div className="sb-section">
            <p className="sb-label">Ask a question</p>
            <form onSubmit={runQuery}>
              <textarea className="sb-textarea" value={q} onChange={e => setQ(e.target.value)} rows={3}
                placeholder="Type a question or leave empty to refresh dashboard" />
              <div className="sb-row">
                <button type="submit" className="sb-run" disabled={qBusy || busy}>
                {busy ? 'Loading…' : qBusy ? '…' : 'Run Query'}
              </button>
                <button type="button" className="sb-clear" onClick={() => setQ('')}>Clear</button>
              </div>
            </form>
            {qErr && <p className="sb-err">{qErr}</p>}
            {qRes?.answer && <p className="sb-answer">{qRes.answer}</p>}
          </div>

          <div className="sb-section">
            <p className="sb-label">Examples</p>
            <div className="sb-examples">
              {samples.map(s => (
                <button key={s} className="sb-ex" onClick={() => setQ(s)}>{s}</button>
              ))}
            </div>
          </div>

          <div className="sb-section sb-hist-section">
            <p className="sb-label">Session history</p>
            <div className="sb-hist">
              {history.length === 0
                ? <p className="sb-none">No history yet.</p>
                : history.slice().reverse().map((h, i) => (
                  <div key={i} className="sb-hist-item" onClick={() => setQ(h.question)}>
                    <span className="sb-hist-q">{h.question}</span>
                    <span className="sb-hist-meta">{h.row_count} rows</span>
                  </div>
                ))
              }
            </div>
          </div>
        </>}
      </aside>

      {/* ── Main ── */}
      <main className="pbi-main">
        <div className="pbi-topbar">
          <h2>{DASHBOARD_CONFIG.title}</h2>
          {charts.query_result && <button className="clear-qres" onClick={() => setCharts(prev => { const n = {...prev}; delete n.query_result; return n })}>✕ Clear query result</button>}
        </div>

        <div className="pbi-canvas">
          {/* Query result banner */}
          {qRes?.charts?.length > 0 && (
            <div className="qres-row">
              {qRes.charts.map((c, i) => (
                <ChartTile key={i} title={c.title || 'Query Result'} subtitle={qRes.answer} span={1}>
                  <MiniChart type={c.type?.includes('pie') ? 'pie' : c.type?.includes('horizontal') ? 'hbar' : c.type?.includes('line') ? 'line' : 'bar'}
                    data={qRes.data} xKey={c.x_key} yKey={c.y_key} height={200} />
                </ChartTile>
              ))}
            </div>
          )}

          {/* KPI Row — only show after data loaded */}
          {Object.keys(kpis).length > 0 && (
            <div className="kpi-row">
              {DASHBOARD_CONFIG.kpis.map(k => (
                <KPITile key={k.id} {...k} value={kpis[k.id]?.value} loading={false} />
              ))}
            </div>
          )}

          {/* Charts grid */}
          <div className="tiles-grid">
            {/* Revenue Trend - wide */}
            {charts.revenue_trend && (
              <ChartTile title={charts.revenue_trend.title} subtitle={charts.revenue_trend.subtitle} span={2}>
                <MiniChart type="area" data={charts.revenue_trend.data}
                  xKey={charts.revenue_trend.xKey} yKey={charts.revenue_trend.yKey} height={200} />
              </ChartTile>
            )}



            {/* Top Customers - hbar */}
            {charts.top_customers && (
              <ChartTile title={charts.top_customers.title} subtitle={charts.top_customers.subtitle}>
                <MiniChart type="hbar" data={charts.top_customers.data?.slice(0,8)}
                  xKey={charts.top_customers.xKey} yKey={charts.top_customers.yKey} height={210} />
              </ChartTile>
            )}

            {/* Regional Sales */}
            {charts.regional_sales && (
              <ChartTile title={charts.regional_sales.title} subtitle={charts.regional_sales.subtitle}>
                <MiniChart type="bar" data={charts.regional_sales.data}
                  xKey={charts.regional_sales.xKey} yKey={charts.regional_sales.yKey} height={200} />
              </ChartTile>
            )}

            {/* Daily Orders */}
            {charts.daily_orders && (
              <ChartTile title={charts.daily_orders.title} subtitle={charts.daily_orders.subtitle} span={2}>
                <MiniChart type="area" data={charts.daily_orders.data}
                  xKey={charts.daily_orders.xKey} yKey={charts.daily_orders.yKey} height={200} />
              </ChartTile>
            )}

            {/* Top Products */}
            {charts.product_performance && (
              <ChartTile title={charts.product_performance.title} subtitle={charts.product_performance.subtitle}>
                <MiniChart type="hbar" data={charts.product_performance.data?.slice(0,8)}
                  xKey={charts.product_performance.xKey} yKey={charts.product_performance.yKey} height={210} />
              </ChartTile>
            )}

            {/* Query result tile — only show if different from existing dashboard charts */}
            {charts.query_result && (() => {
              const isDuplicate = Object.entries(charts)
                .filter(([k]) => k !== 'query_result')
                .some(([, v]) => v.question === charts.query_result.question ||
                  v.title?.toLowerCase() === charts.query_result.title?.toLowerCase())
              if (isDuplicate) return null
              return (
                <ChartTile title={charts.query_result.title} subtitle="QUERY RESULT" span={2}>
                  <MiniChart type={charts.query_result.chartType || 'bar'}
                    data={charts.query_result.data}
                    xKey={charts.query_result.xKey}
                    yKey={charts.query_result.yKey}
                    height={200} />
                </ChartTile>
              )
            })()}

            {/* Skeleton tiles while loading */}
            {busy && Object.keys(charts).length < DASHBOARD_CONFIG.charts.length &&
              DASHBOARD_CONFIG.charts.filter(c => !charts[c.id]).map(c => (
                <ChartTile key={c.id} title={c.title} subtitle={c.subtitle}>
                  <div className="chart-skeleton" style={{height: 220}} />
                </ChartTile>
              ))
            }
            {/* Empty / idle state — only show if no query result either */}
            {!busy && Object.keys(charts).length === 0 && (
              <div className="idle-state">
                <div className="idle-icon">◈</div>
                <p className="idle-title">Dashboard ready</p>
                <p className="idle-sub">Ask a question to load the dashboard.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}