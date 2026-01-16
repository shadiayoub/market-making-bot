'use client'

interface LoginScreenProps {
  onConnect: () => void
  connectors: readonly any[]
}

export function LoginScreen({ onConnect, connectors }: LoginScreenProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600">
      <div className="bg-white p-8 rounded-lg shadow-2xl max-w-md w-full">
        <h1 className="text-3xl font-bold mb-2 text-center text-gray-800">
          Market Making Bot
        </h1>
        <p className="text-gray-600 mb-8 text-center">
          Connect your wallet to access the admin panel
        </p>
        
        <div className="space-y-3">
          {connectors.length > 0 ? (
            connectors.map((connector) => (
              <button
                key={connector.id}
                onClick={onConnect}
                className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <span>Connect with {connector.name || 'Wallet'}</span>
              </button>
            ))
          ) : (
            <button
              onClick={onConnect}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <span>Connect Wallet</span>
            </button>
          )}
        </div>
        
        <p className="text-xs text-gray-500 mt-6 text-center">
          Only authorized admin wallets can access this panel
        </p>
      </div>
    </div>
  )
}
