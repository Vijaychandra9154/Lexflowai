import '../styles/globals.css'
import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'

const PUBLIC_ROUTES = ['/login']

export default function App({ Component, pageProps }) {
  const router = useRouter()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('lexflow_token')
    if (!token && !PUBLIC_ROUTES.includes(router.pathname)) {
      router.replace('/login')
    } else {
      setChecked(true)
    }
  }, [router.pathname])

  if (!checked && !PUBLIC_ROUTES.includes(router.pathname)) return null

  return <Component {...pageProps} />
}
