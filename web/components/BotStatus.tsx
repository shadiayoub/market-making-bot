'use client'

'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'

export function BotStatus() {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/status`)
      setStatus(response.data)
    } catch (error) {
      console.error('Error fetching status:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="bg-white rounded-lg shadow p-6">Loading status...</div>
  }

  if (!status) {
    return <div className="bg-white rounded-lg shadow p-6">No status available</div>
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-6">
      <h2 className="text-2xl font-bold">Bot Status</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-blue-50 rounded-lg">
          <div className="text-sm text-gray-600">Status</div>
          <div className="text-2xl font-bold text-blue-600">
            {status.isRunning ? '🟢 Running' : '🔴 Stopped'}
          </div>
        </div>
        
        <div className="p-4 bg-green-50 rounded-lg">
          <div className="text-sm text-gray-600">USDT Balance</div>
          <div className="text-2xl font-bold text-green-600">
            {status.balance?.usdt?.toFixed(2) || '0.00'} USDT
          </div>
        </div>
        
        <div className="p-4 bg-purple-50 rounded-lg">
          <div className="text-sm text-gray-600">Token Balance</div>
          <div className="text-2xl font-bold text-purple-600">
            {status.balance?.tokens?.toFixed(2) || '0.00'} {status.balance?.tokenSymbol || ''}
          </div>
        </div>
        
        <div className="p-4 bg-yellow-50 rounded-lg">
          <div className="text-sm text-gray-600">Active Orders</div>
          <div className="text-2xl font-bold text-yellow-600">
            {status.activeOrders || 0}
          </div>
        </div>
        
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="text-sm text-gray-600">Current Bid</div>
          <div className="text-xl font-bold text-gray-700">
            {status.market?.bid?.toFixed(6) || 'N/A'}
          </div>
        </div>
        
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="text-sm text-gray-600">Current Ask</div>
          <div className="text-xl font-bold text-gray-700">
            {status.market?.ask?.toFixed(6) || 'N/A'}
          </div>
        </div>
        
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="text-sm text-gray-600">Spread</div>
          <div className="text-xl font-bold text-gray-700">
            {status.market?.spread?.toFixed(2) || 'N/A'}%
          </div>
        </div>
      </div>
    </div>
  )
}
