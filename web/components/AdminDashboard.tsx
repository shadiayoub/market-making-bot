'use client'

'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'
import { ConfigForm } from './ConfigForm'
import { BotStatus } from './BotStatus'
import { LogsViewer } from './LogsViewer'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'

interface AdminDashboardProps {
  address: string
  onDisconnect: () => void
}

export function AdminDashboard({ address, onDisconnect }: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState<'config' | 'status' | 'logs'>('config')
  const [config, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchConfig()
    // Store admin address for use in child components
    if (typeof window !== 'undefined' && address) {
      localStorage.setItem('adminAddress', address)
      // Also add to URL for API calls
      if (!window.location.search.includes('adminAddress')) {
        const url = new URL(window.location.href)
        url.searchParams.set('adminAddress', address)
        window.history.replaceState({}, '', url.toString())
      }
    }
  }, [address])

  const fetchConfig = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/config`)
      setConfig(response.data)
    } catch (error) {
      console.error('Error fetching config:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveConfig = async (newConfig: any) => {
    try {
      await axios.post(`${API_URL}/api/config?adminAddress=${address?.toLowerCase()}`, newConfig, {
        headers: { 'Content-Type': 'application/json' },
      })
      await fetchConfig()
      alert('Configuration saved successfully! Bot will need to be restarted to apply changes.')
    } catch (error: any) {
      alert(`Error saving configuration: ${error.response?.data?.error || error.message}`)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading configuration...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">Market Making Bot Control Panel</h1>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">
                {address.slice(0, 6)}...{address.slice(-4)}
              </span>
              <button
                onClick={onDisconnect}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm"
              >
                Disconnect
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'config', label: 'Configuration' },
              { id: 'status', label: 'Bot Status' },
              { id: 'logs', label: 'Logs' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="mt-6">
          {activeTab === 'config' && (
            <ConfigForm config={config} onSave={handleSaveConfig} />
          )}
          {activeTab === 'status' && <BotStatus address={address} />}
          {activeTab === 'logs' && <LogsViewer />}
        </div>
      </div>
    </div>
  )
}
