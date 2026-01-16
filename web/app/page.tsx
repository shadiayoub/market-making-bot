'use client'

import { useAccount, useConnect, useDisconnect } from 'wagmi'
import { useState, useEffect } from 'react'
import { AdminDashboard } from '@/components/AdminDashboard'
import { LoginScreen } from '@/components/LoginScreen'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'

export default function Home() {
  const { address, isConnected } = useAccount()
  const { connect, connectors } = useConnect()
  const { disconnect } = useDisconnect()
  const [isAdmin, setIsAdmin] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isConnected && address) {
      checkAdminStatus()
    } else {
      setIsAdmin(false)
      setLoading(false)
    }
  }, [isConnected, address])

  const checkAdminStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/check`, {
        params: { address: address?.toLowerCase() },
      })
      setIsAdmin(response.data.isAdmin)
    } catch (error) {
      console.error('Error checking admin status:', error)
      setIsAdmin(false)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  if (!isConnected) {
    return (
      <LoginScreen 
        onConnect={() => {
          if (connectors[0]) {
            connect({ connector: connectors[0] })
          }
        }} 
        connectors={connectors} 
      />
    )
  }

  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
          <h1 className="text-2xl font-bold mb-4 text-center">Access Denied</h1>
          <p className="text-gray-600 mb-6 text-center">
            Your wallet ({address?.slice(0, 6)}...{address?.slice(-4)}) is not authorized as an admin.
          </p>
          <button
            onClick={() => disconnect()}
            className="w-full bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded"
          >
            Disconnect Wallet
          </button>
        </div>
      </div>
    )
  }

  return <AdminDashboard address={address!} onDisconnect={disconnect} />
}
