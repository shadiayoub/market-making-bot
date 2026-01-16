'use client'

'use client'

import { useState, useEffect } from 'react'

interface ConfigFormProps {
  config: any
  onSave: (config: any) => void
}

export function ConfigForm({ config, onSave }: ConfigFormProps) {
  const [formData, setFormData] = useState<any>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (config) {
      setFormData(config)
    }
  }, [config])

  const handleChange = (key: string, value: any) => {
    setFormData((prev: any) => ({
      ...prev,
      [key]: value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await onSave(formData)
    } finally {
      setSaving(false)
    }
  }

  if (!config) {
    return <div>Loading configuration...</div>
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* API Credentials */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-semibold mb-4 pb-2 border-b">API Credentials</h2>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            API Key
          </label>
          <input
            type="text"
            value={formData.LBANK_API_KEY || ''}
            onChange={(e) => handleChange('LBANK_API_KEY', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Your LBank API Key"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            API Secret
          </label>
          <input
            type="password"
            value={formData.LBANK_API_SECRET || ''}
            onChange={(e) => handleChange('LBANK_API_SECRET', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Your LBank API Secret"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Sign Method
          </label>
          <select
            value={formData.LBANK_SIGN_METHOD || 'HMACSHA256'}
            onChange={(e) => handleChange('LBANK_SIGN_METHOD', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="HMACSHA256">HMACSHA256</option>
            <option value="RSA">RSA</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Base URL
          </label>
          <input
            type="text"
            value={formData.LBANK_BASE_URL || 'https://api.lbkex.com/'}
            onChange={(e) => handleChange('LBANK_BASE_URL', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Trading Pair */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-semibold mb-4 pb-2 border-b mt-6">Trading Pair</h2>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Trading Pair
          </label>
          <input
            type="text"
            value={formData.TRADING_PAIR || ''}
            onChange={(e) => handleChange('TRADING_PAIR', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="acces_usdt"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Token Symbol
          </label>
          <input
            type="text"
            value={formData.TOKEN_SYMBOL || ''}
            onChange={(e) => handleChange('TOKEN_SYMBOL', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="acces"
          />
        </div>

        {/* Compliance Mode */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-semibold mb-4 pb-2 border-b mt-6">Compliance Mode</h2>
        </div>
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={formData.ENABLE_COMPLIANCE_MODE === 'true' || formData.ENABLE_COMPLIANCE_MODE === true}
              onChange={(e) => handleChange('ENABLE_COMPLIANCE_MODE', e.target.checked ? 'true' : 'false')}
              className="mr-2 w-4 h-4"
            />
            <span className="text-sm font-medium text-gray-700">Enable Compliance Mode</span>
          </label>
        </div>

        {/* Safety Features */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-semibold mb-4 pb-2 border-b mt-6">Safety Features</h2>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Spread %
          </label>
          <input
            type="number"
            step="0.1"
            value={formData.MAX_SPREAD_PCT || '30.0'}
            onChange={(e) => handleChange('MAX_SPREAD_PCT', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Loss %
          </label>
          <input
            type="number"
            step="0.1"
            value={formData.MAX_LOSS_PCT || '20.0'}
            onChange={(e) => handleChange('MAX_LOSS_PCT', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Exposure %
          </label>
          <input
            type="number"
            step="0.1"
            value={formData.MAX_EXPOSURE_PCT || '80.0'}
            onChange={(e) => handleChange('MAX_EXPOSURE_PCT', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Reference Price Mode */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-semibold mb-4 pb-2 border-b mt-6">Reference Price Mode</h2>
        </div>
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={formData.ENABLE_REFERENCE_PRICE_MODE === 'true' || formData.ENABLE_REFERENCE_PRICE_MODE === true}
              onChange={(e) => handleChange('ENABLE_REFERENCE_PRICE_MODE', e.target.checked ? 'true' : 'false')}
              className="mr-2 w-4 h-4"
            />
            <span className="text-sm font-medium text-gray-700">Enable Reference Price Mode</span>
          </label>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Reference Price
          </label>
          <input
            type="number"
            step="0.0001"
            value={formData.REFERENCE_PRICE || '0.2000'}
            onChange={(e) => handleChange('REFERENCE_PRICE', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Order Value Per Side (USDT)
          </label>
          <input
            type="number"
            step="1"
            value={formData.ORDER_VALUE_PER_SIDE || '250'}
            onChange={(e) => handleChange('ORDER_VALUE_PER_SIDE', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Orders Per Side
          </label>
          <input
            type="number"
            step="1"
            value={formData.ORDERS_PER_SIDE || '10'}
            onChange={(e) => handleChange('ORDERS_PER_SIDE', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Ladder Order Sizes (comma-separated, USDT)
          </label>
          <input
            type="text"
            value={formData.LADDER_ORDER_SIZES || '15,15,15,20,25,25,30,35,35,35'}
            onChange={(e) => handleChange('LADDER_ORDER_SIZES', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="15,15,15,20,25,25,30,35,35,35"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Buy Price (leave empty to disable)
          </label>
          <input
            type="number"
            step="0.0001"
            value={formData.MAX_BUY_PRICE || ''}
            onChange={(e) => handleChange('MAX_BUY_PRICE', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="0.22"
          />
        </div>

        {/* Sleep Time */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-semibold mb-4 pb-2 border-b mt-6">Sleep Time Configuration</h2>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Base Sleep Time (seconds)
          </label>
          <input
            type="number"
            step="1"
            value={formData.BASE_SLEEP_TIME || '60'}
            onChange={(e) => handleChange('BASE_SLEEP_TIME', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Sleep Time (seconds)
          </label>
          <input
            type="number"
            step="1"
            value={formData.MAX_SLEEP_TIME || '180'}
            onChange={(e) => handleChange('MAX_SLEEP_TIME', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Min Sleep Time (seconds)
          </label>
          <input
            type="number"
            step="1"
            value={formData.MIN_SLEEP_TIME || '30'}
            onChange={(e) => handleChange('MIN_SLEEP_TIME', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Min Random Delay (seconds)
          </label>
          <input
            type="number"
            step="0.1"
            value={formData.MIN_RANDOM_DELAY || '1'}
            onChange={(e) => handleChange('MIN_RANDOM_DELAY', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Random Delay (seconds)
          </label>
          <input
            type="number"
            step="0.1"
            value={formData.MAX_RANDOM_DELAY || '3'}
            onChange={(e) => handleChange('MAX_RANDOM_DELAY', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex justify-end pt-6 border-t">
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </form>
  )
}
