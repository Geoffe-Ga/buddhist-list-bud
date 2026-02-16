import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { fetchLists, fetchNavigate } from '../api/navigate'
import type { NavigateResponse, NodeSummary } from '../types'
import './NavigationLayout.css'

export interface NavigationLayoutHandle {
  navigateTo: (id: string) => void
}

const NavigationLayout = forwardRef<NavigationLayoutHandle>(function NavigationLayout(_props, ref) {
  const [data, setData] = useState<NavigateResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<{ id: string; name: string }[]>([])
  const dataRef = useRef<NavigateResponse | null>(null)

  const navigateTo = useCallback(async (id: string, addToHistory = true) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchNavigate(id)
      if (addToHistory && dataRef.current) {
        setHistory((h) => [...h, { id: dataRef.current!.current.id, name: dataRef.current!.current.name }])
      }
      dataRef.current = result
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Navigation failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useImperativeHandle(ref, () => ({ navigateTo }), [navigateTo])

  useEffect(() => {
    let cancelled = false
    async function loadRoot() {
      try {
        const lists = await fetchLists()
        if (cancelled) return
        const fnt = lists.find((l) => l.slug === 'four-noble-truths')
        if (fnt) {
          await navigateTo(fnt.id, false)
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load')
          setLoading(false)
        }
      }
    }
    loadRoot()
    return () => { cancelled = true }
  }, [navigateTo])

  const handleNavigate = (node: NodeSummary) => {
    navigateTo(node.id)
  }

  const handleBack = () => {
    if (history.length === 0) return
    const prev = history[history.length - 1]
    setHistory((h) => h.slice(0, -1))
    setLoading(true)
    setError(null)
    fetchNavigate(prev.id)
      .then((result) => {
        dataRef.current = result
        setData(result)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Navigation failed'))
      .finally(() => setLoading(false))
  }

  if (error) {
    return <div className="error-message">{error}</div>
  }

  if (loading || !data) {
    return (
      <div className="loading">
        <div className="spinner" />
        <span>Loading...</span>
      </div>
    )
  }

  return (
    <div className="nav-layout">
      {history.length > 0 && (
        <div className="breadcrumbs">
          <button className="breadcrumb-btn" onClick={handleBack}>
            &larr; Back
          </button>
          <span className="breadcrumb-trail">
            {history.map((h) => h.name).join(' > ')} &gt; {data.current.name}
          </span>
        </div>
      )}

      <div className="nav-edge nav-up">
        {data.up && (
          <button className="nav-btn nav-btn-horizontal" onClick={() => handleNavigate(data.up!)}>
            <span className="arrow">&#9650;</span>
            <span className="label">{data.up.name}</span>
          </button>
        )}
      </div>

      <div className="nav-middle">
        <div className="nav-edge nav-left">
          {data.left.map((node) => (
            <button key={node.id} className="nav-btn nav-btn-vertical" onClick={() => handleNavigate(node)}>
              <span className="label">{node.name}</span>
            </button>
          ))}
        </div>

        <div className="content-area">
          <h1>{data.current.name}</h1>
          <p className="pali">{data.current.pali_name}</p>
          {data.current.description && <p className="description">{data.current.description}</p>}
          {data.current.type === 'list' && data.right.length > 0 && (
            <ol className="list-items">
              {data.right.map((node) => (
                <li key={node.id}>
                  <button className="list-item-link" onClick={() => handleNavigate(node)}>
                    {node.name}
                  </button>
                </li>
              ))}
            </ol>
          )}
          {data.current.essay && (
            <div className="essay">{data.current.essay}</div>
          )}
        </div>

        <div className="nav-edge nav-right">
          {data.right.map((node) => (
            <button key={node.id} className="nav-btn nav-btn-vertical" onClick={() => handleNavigate(node)}>
              <span className="label">{node.name}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="nav-edge nav-down">
        {data.down && (
          <button className="nav-btn nav-btn-horizontal" onClick={() => handleNavigate(data.down!)}>
            <span className="label">{data.down.name}</span>
            <span className="arrow">&#9660;</span>
          </button>
        )}
      </div>
    </div>
  )
})

export default NavigationLayout
