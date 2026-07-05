import { useRouter } from 'next/router'
import axios from 'axios'
import { useEffect, useState } from 'react'

export default function CasePage(){
  const r = useRouter()
  const { id } = r.query
  const [caseData, setCaseData] = useState(null)

  useEffect(()=>{
    if(!id) return
    axios.get(`/api/cases/${id}`).then(res=>setCaseData(res.data)).catch(()=>{})
  },[id])

  if(!caseData) return <div className="p-6">Loading...</div>
  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold">{caseData.title}</h2>
      <pre>{JSON.stringify(caseData, null, 2)}</pre>
    </div>
  )
}
