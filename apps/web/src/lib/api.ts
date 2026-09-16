export type CompanySearchResult = { ticker: string; name: string; cik: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

export const api = {
  health: () => request<any>('/api/v1/health'),
  search: (q: string) => request<{ results: CompanySearchResult[] }>(`/api/v1/search?q=${encodeURIComponent(q)}`),
  overview: (ticker: string) => request<any>(`/api/v1/company/${encodeURIComponent(ticker)}/overview`),
  filings: (ticker: string) => request<any>(`/api/v1/company/${encodeURIComponent(ticker)}/filings`),
  filingSearch: (ticker: string, q: string, accession?: string) => request<any>(`/api/v1/company/${encodeURIComponent(ticker)}/filing-search?q=${encodeURIComponent(q)}${accession ? `&accession=${encodeURIComponent(accession)}` : ''}`),
  compare: (tickers: string[]) => request<any>(`/api/v1/compare?tickers=${encodeURIComponent(tickers.join(','))}`),
  dcf: (ticker: string, assumptions: any) => request<any>(`/api/v1/company/${encodeURIComponent(ticker)}/scenario/dcf`, { method: 'POST', body: JSON.stringify(assumptions) }),
};
