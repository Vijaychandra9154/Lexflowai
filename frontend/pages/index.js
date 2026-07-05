import useSWR from 'swr'
import axios from 'axios'

const fetcher = (url) => axios.get(url).then(r => r.data)

export default function Home(){
  const {data, error} = useSWR('/api/health', fetcher)
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">LexFlowAI — Dashboard</h1>
      <p>{error ? 'Backend not reachable' : (data ? JSON.stringify(data) : 'Checking backend...')}</p>
      <div className="mt-6">
        <a href="/case/1">Open Sample Case</a>
      </div>
    </div>
  )
}
