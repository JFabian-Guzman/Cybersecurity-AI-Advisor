import { useQuery } from '@tanstack/react-query'
import { fetchDbCheck } from './api'
import './App.css'

function App() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['db-check'],
    queryFn: fetchDbCheck,
  })

  return (
    <main className="status">
      <h1>CyberSecurity Advisor</h1>
      <p>Walking skeleton: frontend → backend → database</p>
      {isLoading && <p>Checking backend…</p>}
      {isError && <p className="error">Backend unreachable: {(error as Error).message}</p>}
      {data && (
        <div className="card">
          <p>Backend: online</p>
          <p>Database: {data.database}</p>
          <p>SELECT 1 → {data.select_1}</p>
          <p>Checked at {data.checked_at}</p>
        </div>
      )}
    </main>
  )
}

export default App
