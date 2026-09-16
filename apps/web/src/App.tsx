import { useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowUpRight, BarChart3, ChevronRight, CircleDollarSign,
  Database, ExternalLink, FileSearch, Gauge, GitCompare, LineChart as LineIcon,
  Plus, Search, Server, ShieldCheck, Sparkles, Terminal, Wallet, X,
} from 'lucide-react';
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { api, CompanySearchResult } from './lib/api';

type View = 'overview' | 'compare' | 'filings' | 'scenario';

const fmtMoney = (n: any) => {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  const abs = Math.abs(v);
  if (abs >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};
const fmtNum = (n: any, suffix = '') => n === null || n === undefined || Number.isNaN(Number(n)) ? '—' : `${Number(n).toFixed(2)}${suffix}`;

function Metric({ label, value, meta }: { label: string; value: string; meta?: string }) {
  return <div className="metric-card">
    <div className="eyebrow">{label}</div>
    <div className="metric-value">{value}</div>
    {meta && <div className="metric-meta">{meta}</div>}
  </div>;
}

function App() {
  const [ticker, setTicker] = useState('AAPL');
  const [view, setView] = useState<View>('overview');
  const [data, setData] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CompanySearchResult[]>([]);
  const [watchlist, setWatchlist] = useState<string[]>(() => JSON.parse(localStorage.getItem('finengine.watchlist') || '["AAPL","MSFT","NVDA"]'));
  const [compareInput, setCompareInput] = useState('AAPL, MSFT, NVDA');
  const [compareData, setCompareData] = useState<any[]>([]);
  const [filings, setFilings] = useState<any[]>([]);
  const [filingQuery, setFilingQuery] = useState('revenue growth risks');
  const [filingResult, setFilingResult] = useState<any>(null);
  const [scenario, setScenario] = useState({ growth_rate: 5, discount_rate: 10, terminal_growth_rate: 2.5, years: 5 });
  const [scenarioResult, setScenarioResult] = useState<any>(null);

  useEffect(() => { localStorage.setItem('finengine.watchlist', JSON.stringify(watchlist)); }, [watchlist]);
  useEffect(() => { api.health().then(setHealth).catch(() => setHealth(null)); }, []);

  const loadCompany = async (symbol: string) => {
    setLoading(true); setError(''); setFilingResult(null); setScenarioResult(null);
    try {
      const [overview, filingData] = await Promise.all([api.overview(symbol), api.filings(symbol)]);
      setTicker(symbol.toUpperCase()); setData(overview); setFilings(filingData.filings || []);
    } catch (e: any) { setError(e.message || 'Unable to load company.'); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadCompany('AAPL'); }, []);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (query.trim().length < 1) return setResults([]);
      try { setResults((await api.search(query)).results); } catch { setResults([]); }
    }, 180);
    return () => clearTimeout(t);
  }, [query]);

  const runCompare = async () => {
    setError('');
    try { setCompareData((await api.compare(compareInput.split(',').map(s => s.trim()).filter(Boolean))).results || []); }
    catch (e: any) { setError(e.message); }
  };

  const runFilingSearch = async () => {
    setError(''); setFilingResult(null);
    try { setFilingResult(await api.filingSearch(ticker, filingQuery)); }
    catch (e: any) { setError(e.message); }
  };

  const runScenario = async () => {
    setError(''); setScenarioResult(null);
    try { setScenarioResult(await api.dcf(ticker, scenario)); }
    catch (e: any) { setError(e.message); }
  };

  const chartData = useMemo(() => (data?.price_series || []).map((r: any) => ({ date: r.datetime, close: Number(r.close) })).filter((r: any) => Number.isFinite(r.close)), [data]);
  const currentPrice = data?.quote?.close || data?.quote?.price || data?.market_statistics?.last;

  return <div className="shell">
    <div className="ambient ambient-a"/><div className="ambient ambient-b"/><div className="scanlines"/>
    <aside className="rail">
      <div>
        <div className="brand-mark"><span>FE</span></div>
        <div className="rail-word">FINENGINE</div>
      </div>
      <nav className="level-nav">
        {([
          ['overview', '01', 'Overview', Gauge],
          ['compare', '02', 'Compare', GitCompare],
          ['filings', '03', 'Filing Lens', FileSearch],
          ['scenario', '04', 'Scenario Lab', LineIcon],
        ] as const).map(([id, num, label, Icon]) => <button key={id} className={`level ${view === id ? 'active' : ''}`} onClick={() => setView(id)}>
          <span className="level-dot"/><span className="level-num">{num}</span><Icon size={15}/><span>{label}</span>
        </button>)}
      </nav>
      <div className="rail-status">
        <span className={`status-dot ${health?.ok ? 'online' : ''}`}/>
        <span>{health?.ok ? 'SYSTEM ONLINE' : 'API OFFLINE'}</span>
      </div>
    </aside>

    <main className="main">
      <header className="topbar">
        <div>
          <div className="micro">PRODUCT × DATA SYSTEMS × FINANCIAL ANALYTICS</div>
          <div className="top-title">COMPANY INTELLIGENCE OS</div>
        </div>
        <div className="provider-state">
          <Database size={14}/><span>SEC EDGAR</span>
          <span className="sep">/</span>
          <Activity size={14}/><span>{health?.market_data_configured ? 'TWELVE DATA LIVE' : 'MARKET KEY REQUIRED'}</span>
        </div>
      </header>

      <section className="search-strip">
        <div className="search-wrap">
          <Search size={18}/>
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search ticker or company…" />
          <kbd>/</kbd>
          {results.length > 0 && <div className="search-results">{results.map(r => <button key={r.ticker} onClick={() => { setQuery(''); setResults([]); loadCompany(r.ticker); setView('overview'); }}>
            <span><strong>{r.ticker}</strong><small>{r.name}</small></span><ChevronRight size={14}/>
          </button>)}</div>}
        </div>
        <div className="watchlist">{watchlist.map(s => <button key={s} onClick={() => loadCompany(s)} className={ticker === s ? 'active' : ''}>{s}</button>)}
          {!watchlist.includes(ticker) && <button onClick={() => setWatchlist(w => [...w, ticker])}><Plus size={13}/>{ticker}</button>}
        </div>
      </section>

      {error && <div className="error-banner"><ShieldCheck size={16}/><span>{error}</span><button onClick={() => setError('')}><X size={14}/></button></div>}

      {loading ? <div className="loading-stage"><div className="loader-orbit"/><div className="micro">RESOLVING SEC FACTS + MARKET SERIES</div></div> : <>
        <section className="hero-grid">
          <div className="hero-copy">
            <div className="micro accent">LIVE COMPANY NODE // {data?.company?.cik}</div>
            <div className="ticker-display">{ticker}</div>
            <h1>{data?.company?.name}</h1>
            <p>One research surface for market behavior, SEC-normalized fundamentals, filing evidence, peer context, and transparent valuation scenarios.</p>
          </div>
          <div className="hero-price">
            <div className="micro">LATEST MARKET PRICE</div>
            <div className="price">{currentPrice ? `$${Number(currentPrice).toFixed(2)}` : '—'}</div>
            <div className="submetric">{data?.market_statistics?.period_return_pct != null ? `${fmtNum(data.market_statistics.period_return_pct, '%')} / selected history` : 'Configure Twelve Data for live market series'}</div>
          </div>
          <div className="hero-meta">
            <div><span>SOURCE</span><strong>SEC + MARKET API</strong></div>
            <div><span>MODE</span><strong>TRACEABLE ANALYTICS</strong></div>
            <div><span>ENGINE</span><strong>PYTHON / FASTAPI</strong></div>
          </div>
        </section>

        {view === 'overview' && <section className="content-grid">
          <div className="panel chart-panel span-8">
            <div className="panel-head"><div><div className="micro">MARKET TELEMETRY</div><h2>Price trajectory</h2></div><BarChart3 size={18}/></div>
            {chartData.length ? <div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}>
              <defs><linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#79ddff" stopOpacity={0.28}/><stop offset="100%" stopColor="#79ddff" stopOpacity={0}/></linearGradient></defs>
              <CartesianGrid stroke="rgba(255,255,255,.05)" vertical={false}/><XAxis dataKey="date" hide/><YAxis domain={['auto','auto']} hide/><Tooltip contentStyle={{background:'#0b1116',border:'1px solid rgba(121,221,255,.2)',borderRadius:12}}/>
              <Area type="monotone" dataKey="close" stroke="#79ddff" strokeWidth={2} fill="url(#priceFill)" dot={false}/>
            </AreaChart></ResponsiveContainer></div> : <div className="empty"><LineIcon/><span>No market series yet. Add your Twelve Data API key to activate live telemetry.</span></div>}
            <div className="chart-stats"><span>VOLATILITY <b>{fmtNum(data?.market_statistics?.annualized_volatility_pct, '%')}</b></span><span>MAX DRAWDOWN <b>{fmtNum(data?.market_statistics?.max_drawdown_pct, '%')}</b></span><span>RANGE <b>{fmtMoney(data?.market_statistics?.low)} → {fmtMoney(data?.market_statistics?.high)}</b></span></div>
          </div>

          <div className="panel span-4 system-panel">
            <div className="panel-head"><div><div className="micro">FINANCIAL SYSTEM</div><h2>Signal diagnostics</h2></div><Server size={18}/></div>
            <div className="signals">{(data?.diagnostics || []).map((d:any) => <div className={`signal ${d.level}`} key={d.code}><span className="signal-code">{d.code}</span><div><strong>{d.title}</strong><p>{d.detail}</p></div></div>)}</div>
          </div>

          <div className="metrics-grid span-12">
            <Metric label="Revenue" value={fmtMoney(data?.snapshot?.revenue)} meta={`SEC period ${data?.snapshot?.revenue_period || '—'}`}/>
            <Metric label="Free Cash Flow" value={fmtMoney(data?.snapshot?.free_cash_flow)} meta="Operating CF less capex"/>
            <Metric label="Operating Margin" value={fmtNum(data?.metrics?.operating_margin_pct, '%')} meta="Normalized SEC concepts"/>
            <Metric label="Net Margin" value={fmtNum(data?.metrics?.net_margin_pct, '%')} meta="Latest mapped period"/>
            <Metric label="P / Sales" value={fmtNum(data?.metrics?.price_to_sales)} meta="Market cap / revenue"/>
            <Metric label="P / Earnings" value={fmtNum(data?.metrics?.price_to_earnings)} meta="Market cap / net income"/>
            <Metric label="Debt / Equity" value={fmtNum(data?.metrics?.debt_to_equity)} meta="Reported debt / equity"/>
            <Metric label="Net Cash" value={fmtMoney(data?.metrics?.net_cash)} meta="Cash minus debt"/>
          </div>

          <div className="panel span-12 provenance">
            <div><div className="micro">DATA PROVENANCE</div><h2>Know where every layer comes from.</h2></div>
            <div className="provenance-flow"><span><Database/>SEC companyfacts<strong>Fundamentals</strong></span><i>→</i><span><Terminal/>Python normalization<strong>Metrics + flags</strong></span><i>→</i><span><Activity/>Twelve Data<strong>Market series</strong></span><i>→</i><span><Sparkles/>FINENGINE<strong>Unified research view</strong></span></div>
          </div>
        </section>}

        {view === 'compare' && <section className="content-grid">
          <div className="panel span-12"><div className="panel-head"><div><div className="micro">PEER MATRIX</div><h2>Compare normalized operating profiles</h2></div><GitCompare size={18}/></div>
            <div className="inline-form"><input value={compareInput} onChange={e => setCompareInput(e.target.value)} placeholder="AAPL, MSFT, NVDA"/><button onClick={runCompare}>RUN COMPARISON <ArrowUpRight size={15}/></button></div>
            {compareData.length > 0 && <div className="table-wrap"><table><thead><tr><th>Ticker</th><th>Price</th><th>Revenue</th><th>Op Margin</th><th>FCF Margin</th><th>P/E</th><th>Debt/Equity</th></tr></thead><tbody>{compareData.map((r:any) => <tr key={r.ticker}><td><strong>{r.ticker}</strong><small>{r.company?.name}</small></td><td>{fmtMoney(r.price)}</td><td>{fmtMoney(r.snapshot?.revenue)}</td><td>{fmtNum(r.metrics?.operating_margin_pct,'%')}</td><td>{fmtNum(r.metrics?.fcf_margin_pct,'%')}</td><td>{fmtNum(r.metrics?.price_to_earnings)}</td><td>{fmtNum(r.metrics?.debt_to_equity)}</td></tr>)}</tbody></table></div>}
          </div>
        </section>}

        {view === 'filings' && <section className="content-grid">
          <div className="panel span-5"><div className="panel-head"><div><div className="micro">SEC DOCUMENT STREAM</div><h2>Recent filings</h2></div><FileSearch size={18}/></div>
            <div className="filing-list">{filings.map((f:any) => <a href={f.url} target="_blank" rel="noreferrer" key={f.accession}><span className="form-badge">{f.form}</span><div><strong>{f.report_date || f.filing_date}</strong><small>{f.accession}</small></div><ExternalLink size={14}/></a>)}</div>
          </div>
          <div className="panel span-7"><div className="panel-head"><div><div className="micro">FILING LENS</div><h2>Search the actual filing text</h2></div><Search size={18}/></div>
            <p className="panel-copy">FINENGINE fetches the newest 10-K/10-Q from EDGAR, strips presentation noise, ranks text passages against your query, and returns the evidence instead of inventing an answer.</p>
            <div className="inline-form"><input value={filingQuery} onChange={e => setFilingQuery(e.target.value)} placeholder="e.g. supply chain risks"/><button onClick={runFilingSearch}>SEARCH FILING</button></div>
            {filingResult && <div className="excerpt-stack"><div className="result-meta">{filingResult.filing.form} · {filingResult.filing.report_date} · “{filingResult.query}”</div>{filingResult.excerpts.map((x:any) => <div className="excerpt" key={x.rank}><span>{String(x.rank).padStart(2,'0')}</span><p>{x.text}</p></div>)}</div>}
          </div>
        </section>}

        {view === 'scenario' && <section className="content-grid">
          <div className="panel span-5"><div className="panel-head"><div><div className="micro">TRANSPARENT MODEL</div><h2>DCF Scenario Lab</h2></div><CircleDollarSign size={18}/></div>
            <p className="panel-copy">Change the assumptions yourself. FINENGINE uses latest normalized SEC free cash flow, cash, debt and diluted shares. This is an educational scenario engine, not an investment recommendation.</p>
            <div className="scenario-form">
              {([['growth_rate','FCF growth %'],['discount_rate','Discount rate %'],['terminal_growth_rate','Terminal growth %']] as const).map(([k,l]) => <label key={k}><span>{l}</span><input type="number" step="0.1" value={scenario[k]} onChange={e => setScenario({...scenario,[k]:Number(e.target.value)})}/></label>)}
              <label><span>Forecast years</span><input type="number" min="1" max="10" value={scenario.years} onChange={e => setScenario({...scenario,years:Number(e.target.value)})}/></label>
            </div><button className="primary" onClick={runScenario}>RUN SCENARIO <ArrowUpRight size={15}/></button>
          </div>
          <div className="panel span-7 scenario-output"><div className="micro">MODEL OUTPUT</div>{scenarioResult ? <><div className="implied"><span>IMPLIED VALUE / SHARE</span><strong>{fmtMoney(scenarioResult.implied_value_per_share)}</strong></div><div className="scenario-metrics"><Metric label="Enterprise Value" value={fmtMoney(scenarioResult.enterprise_value)}/><Metric label="Equity Value" value={fmtMoney(scenarioResult.equity_value)}/><Metric label="Base FCF" value={fmtMoney(scenarioResult.base_fcf)}/></div><div className="forecast-bars">{scenarioResult.forecast.map((x:any) => <div key={x.year}><span>Y{x.year}</span><i style={{width:`${Math.min(100, (x.present_value / Math.max(...scenarioResult.forecast.map((v:any)=>v.present_value))) * 100)}%`}}/><b>{fmtMoney(x.present_value)}</b></div>)}</div><p className="disclaimer">{scenarioResult.disclaimer}</p></> : <div className="empty tall"><Wallet/><span>Run a scenario to convert reported cash flow into a transparent assumption-driven model.</span></div>}</div>
        </section>}
      </>}

      <footer><span>FINENGINE // 2026</span><span>SEC-SOURCED FUNDAMENTALS · TRACEABLE ANALYTICS · NO BUY/SELL SIGNALS</span><span>{ticker} NODE</span></footer>
    </main>
  </div>;
}

export default App;
