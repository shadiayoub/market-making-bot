const express = require('express')
const cors = require('cors')
const fs = require('fs')
const path = require('path')
const { exec } = require('child_process')

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())

// Admin wallets from environment
const ADMIN_WALLETS = (process.env.ADMIN_WALLETS || '')
  .split(',')
  .map((addr) => addr.toLowerCase().trim())
  .filter(Boolean)

// Path to .env file (try multiple locations)
let ENV_PATH = path.join(__dirname, '..', '.env')
if (!fs.existsSync(ENV_PATH)) {
  // Try current directory
  ENV_PATH = path.join(process.cwd(), '.env')
}

// Middleware to check admin status
const checkAdmin = (req, res, next) => {
  const address = req.query.adminAddress || req.body.adminAddress
  if (!address) {
    return res.status(401).json({ error: 'Wallet address required' })
  }

  if (!ADMIN_WALLETS.includes(address.toLowerCase())) {
    return res.status(403).json({ error: 'Unauthorized: Not an admin wallet' })
  }

  next()
}

// Read .env file
function readEnvFile() {
  try {
    const content = fs.readFileSync(ENV_PATH, 'utf8')
    const config = {}
    content.split('\n').forEach((line) => {
      const trimmed = line.trim()
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=')
        if (key && valueParts.length > 0) {
          config[key.trim()] = valueParts.join('=').trim()
        }
      }
    })
    return config
  } catch (error) {
    console.error('Error reading .env file:', error)
    return {}
  }
}

// Write .env file
function writeEnvFile(config) {
  try {
    // Read existing file to preserve comments
    let content = fs.existsSync(ENV_PATH)
      ? fs.readFileSync(ENV_PATH, 'utf8')
      : ''

    // Update or add each config value
    Object.entries(config).forEach(([key, value]) => {
      const regex = new RegExp(`^${key}=.*$`, 'm')
      const newLine = `${key}=${value}`
      if (regex.test(content)) {
        content = content.replace(regex, newLine)
      } else {
        content += `\n${newLine}`
      }
    })

    fs.writeFileSync(ENV_PATH, content, 'utf8')
    return true
  } catch (error) {
    console.error('Error writing .env file:', error)
    return false
  }
}

// API Routes
app.get('/api/admin/check', (req, res) => {
  const address = req.query.address
  if (!address) {
    return res.json({ isAdmin: false })
  }
  res.json({
    isAdmin: ADMIN_WALLETS.includes(address.toLowerCase()),
  })
})

app.get('/api/config', (req, res) => {
  const config = readEnvFile()
  res.json(config)
})

app.post('/api/config', checkAdmin, (req, res) => {
  const newConfig = req.body
  if (writeEnvFile(newConfig)) {
    res.json({ success: true, message: 'Configuration saved' })
  } else {
    res.status(500).json({ error: 'Failed to save configuration' })
  }
})

app.get('/api/status', async (req, res) => {
  // This would need to connect to the bot process or read from a status file
  // For now, return mock data
  res.json({
    isRunning: true,
    balance: {
      usdt: 159.87,
      tokens: 39448.35,
      tokenSymbol: 'ACCES',
    },
    activeOrders: 20,
    market: {
      bid: 0.285,
      ask: 0.290,
      spread: 1.75,
    },
  })
})

app.get('/api/logs', (req, res) => {
  // Read logs from docker or log file
  // For now, return empty array
  res.json({ logs: [] })
})

app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`)
  console.log(`Admin wallets: ${ADMIN_WALLETS.join(', ') || 'None configured'}`)
})
