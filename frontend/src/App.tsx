import { useCallback, useRef, useState, useEffect } from 'react'
import NavigationLayout from './components/NavigationLayout'
import type { NavigationLayoutHandle } from './components/NavigationLayout'
import { fetchSearch } from './api/navigate'
import type { SearchResult } from './types'
import './App.css'

function App() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const navRef = useRef<NavigationLayoutHandle>(null)
  const searchRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null)

  const handleSearch = useCallback((value: string) => {
    setQuery(value)
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    if (value.length < 2) {
      setResults([])
      setShowDropdown(false)
      return
    }
    debounceRef.current = setTimeout(async () => {
      try {
        const data = await fetchSearch(value)
        setResults(data)
        setShowDropdown(data.length > 0)
      } catch {
        setResults([])
        setShowDropdown(false)
      }
    }, 300)
  }, [])

  const handleSelect = (result: SearchResult) => {
    navRef.current?.navigateTo(result.id)
    setQuery('')
    setResults([])
    setShowDropdown(false)
  }

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setShowDropdown(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">
          <img src="/robot-buddha.png" alt="Buddhist Dharma Navigator" className="app-logo" />
          <h2>Buddhist Dharma Navigator</h2>
        </div>
        <div className="search-container" ref={searchRef}>
          <input
            type="text"
            className="search-input"
            placeholder="Search lists & dhammas..."
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => results.length > 0 && setShowDropdown(true)}
          />
          {showDropdown && (
            <ul className="search-dropdown">
              {results.map((r) => (
                <li key={r.id}>
                  <button className="search-result" onClick={() => handleSelect(r)}>
                    {r.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>
      <NavigationLayout ref={navRef} />
    </div>
  )
}

export default App
