export interface NodeSummary {
  id: string
  name: string
  type?: string
}

export interface CurrentNode {
  id: string
  type: 'list' | 'dhamma'
  name: string
  pali_name: string
  essay: string | null
  description: string | null
}

export interface NavigateResponse {
  current: CurrentNode
  up: NodeSummary | null
  down: NodeSummary | null
  left: NodeSummary[]
  right: NodeSummary[]
  breadcrumbs: NodeSummary[]
}

export interface ListSummary {
  id: string
  name: string
  pali_name: string
  slug: string
  item_count: number
}

export interface SearchResult {
  id: string
  name: string
  pali_name: string
  type: 'list' | 'dhamma'
}
