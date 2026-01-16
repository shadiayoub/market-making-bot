'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'

interface BotStatusProps {
  address: string
}

export function BotStatus({ address }: BotStatusProps) {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)

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

  const handleStartBot = async () => {
    if (!address) {
      alert('Admin address not found. Please reconnect your wallet.')
      return
    }
    
    setActionLoading(true)
    try {
      const response = await axios.post(
        `${API_URL}/api/bot/start?adminAddress=${address.toLowerCase()}`
      )
      alert(response.data.message || 'Bot started successfully!')
      await fetchStatus() // Refresh status
    } catch (error: any) {
      alert(`Error starting bot: ${error.response?.data?.error || error.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const handleStopBot = async () => {
    if (!address) {
      alert('Admin address not found. Please reconnect your wallet.')
      return
    }
    
    if (!confirm('Are you sure you want to stop the bot? This will cancel all active orders.')) {
      return
    }
    
    setActionLoading(true)
    try {
      const response = await axios.post(
        `${API_URL}/api/bot/stop?adminAddress=${address.toLowerCase()}`
      )
      alert(response.data.message || 'Bot stopped successfully!')
      await fetchStatus() // Refresh status
    } catch (error: any) {
      alert(`Error stopping bot: ${error.response?.data?.error || error.message}`)
    } finally {
      setActionLoading(false)
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
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Bot Status</h2>
        <div className="flex gap-3">
          <button
            onClick={handleStartBot}
            disabled={actionLoading || status?.isRunning}
            className="px-6 py-2 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-bold rounded-lg transition-colors"
          >
            {actionLoading ? 'Processing...' : 'Start Bot'}
          </button>
          <button
            onClick={handleStopBot}
            disabled={actionLoading || !status?.isRunning}
            className="px-6 py-2 bg-red-500 hover:bg-red-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-bold rounded-lg transition-colors"
          >
            {actionLoading ? 'Processing...' : 'Stop Bot'}
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-blue-50 rounded-lg">
          <div className="text-sm text-gray-600">Status</div>
          <div className="text-2xl font-bold text-blue-600">
            {status.isRunning ? '🟢 Running' : '🔴 Stopped'}
          </div>
          {status.containerStatus && (
            <div className="text-xs text-gray-500 mt-1">{status.containerStatus}</div>
          )}
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
      
      {status.error && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-sm text-yellow-800">
            <strong>Warning:</strong> {status.error}
          </div>
        </div>
      )}
    </div>
  )
}
