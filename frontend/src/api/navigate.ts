import type { NavigateResponse, ListSummary, SearchResult } from '../types'

export async function fetchNavigate(id: string): Promise<NavigateResponse> {
  const resp = await fetch(`/api/navigate/${id}`)
  if (!resp.ok) {
    throw new Error(`Navigate failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchLists(): Promise<ListSummary[]> {
  const resp = await fetch('/api/lists')
  if (!resp.ok) {
    throw new Error(`Lists failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchSearch(query: string): Promise<SearchResult[]> {
  const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
  if (!resp.ok) {
    throw new Error(`Search failed: ${resp.status}`)
  }
  return resp.json()
}
