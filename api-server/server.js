const express = require('express')
const cors = require('cors')
const fs = require('fs')
const path = require('path')
const { exec } = require('child_process')
const { promisify } = require('util')
const execPromise = promisify(exec)

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())

// Path to .env file (try multiple locations)
let ENV_PATH = path.join(process.cwd(), '.env') // Try current directory first (Docker mount location)
if (!fs.existsSync(ENV_PATH)) {
  // Try parent directory (for local development)
  ENV_PATH = path.join(__dirname, '..', '.env')
}
if (!fs.existsSync(ENV_PATH)) {
  // Try root directory
  ENV_PATH = path.join(__dirname, '..', '..', '.env')
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

// Normalize Ethereum address (remove 0x prefix if present, ensure lowercase, trim)
function normalizeAddress(address) {
  if (!address) return null
  let normalized = String(address).trim().toLowerCase()
  // Ensure it starts with 0x
  if (!normalized.startsWith('0x')) {
    normalized = '0x' + normalized
  }
  return normalized
}

// Function to get admin wallets from .env file
function getAdminWallets() {
  // First try process.env (for Docker env_file)
  if (process.env.ADMIN_WALLETS) {
    const wallets = (process.env.ADMIN_WALLETS || '')
      .split(',')
      .map((addr) => normalizeAddress(addr))
      .filter(Boolean)
    console.log(`[AUTH] Loaded admin wallets from process.env: ${wallets.join(', ')}`)
    return wallets
  }
  
  // Fallback to reading from .env file
  const config = readEnvFile()
  const wallets = (config.ADMIN_WALLETS || '')
    .split(',')
    .map((addr) => normalizeAddress(addr))
    .filter(Boolean)
  console.log(`[AUTH] Loaded admin wallets from .env file: ${wallets.join(', ')}`)
  return wallets
}

// Middleware to check admin status
const checkAdmin = (req, res, next) => {
  const address = req.query.adminAddress || req.body.adminAddress
  if (!address) {
    console.log(`[AUTH] checkAdmin: No address provided in ${req.method} ${req.path}`)
    return res.status(401).json({ error: 'Wallet address required' })
  }

  const normalizedAddress = normalizeAddress(address)
  const adminWallets = getAdminWallets()
  const isAdmin = adminWallets.includes(normalizedAddress)
  
  console.log(`[AUTH] checkAdmin: ${req.method} ${req.path}`)
  console.log(`[AUTH] checkAdmin: Checking "${normalizedAddress}" (original: "${address}")`)
  console.log(`[AUTH] checkAdmin: Admin wallets: [${adminWallets.join(', ')}]`)
  console.log(`[AUTH] checkAdmin: Match found: ${isAdmin}`)
  
  if (!isAdmin) {
    console.log(`[AUTH] checkAdmin: Address comparison:`)
    adminWallets.forEach((wallet, idx) => {
      const matches = wallet === normalizedAddress
      console.log(`[AUTH]   Wallet ${idx}: "${wallet}" === "${normalizedAddress}" ? ${matches}`)
      if (wallet && normalizedAddress) {
        console.log(`[AUTH]     Length: ${wallet.length} vs ${normalizedAddress.length}`)
      }
    })
    return res.status(403).json({ error: 'Unauthorized: Not an admin wallet' })
  }

  next()
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
    console.log(`[AUTH] /api/admin/check: No address provided`)
    return res.json({ isAdmin: false })
  }
  const normalizedAddress = normalizeAddress(address)
  const adminWallets = getAdminWallets()
  const isAdmin = adminWallets.includes(normalizedAddress)
  console.log(`[AUTH] /api/admin/check: Checking "${normalizedAddress}" (original: "${address}")`)
  console.log(`[AUTH] /api/admin/check: Admin wallets: [${adminWallets.join(', ')}]`)
  console.log(`[AUTH] /api/admin/check: Match found: ${isAdmin}`)
  if (!isAdmin) {
    console.log(`[AUTH] /api/admin/check: Address comparison:`)
    adminWallets.forEach((wallet, idx) => {
      const matches = wallet === normalizedAddress
      console.log(`[AUTH]   Wallet ${idx}: "${wallet}" === "${normalizedAddress}" ? ${matches}`)
      if (wallet && normalizedAddress) {
        console.log(`[AUTH]     Length: ${wallet.length} vs ${normalizedAddress.length}`)
        console.log(`[AUTH]     Char codes match: ${wallet === normalizedAddress}`)
      }
    })
  }
  res.json({
    isAdmin: isAdmin,
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
  try {
    // Check Docker container status
    const { stdout } = await execPromise('docker ps --filter "name=lbank-market-making-bot" --format "{{.Status}}"')
    const isRunning = stdout.trim().length > 0 && stdout.includes('Up')
    
    // This would need to connect to the bot process or read from a status file
    // For now, return container status
    res.json({
      isRunning: isRunning,
      containerStatus: stdout.trim() || 'Not running',
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
  } catch (error) {
    // If docker command fails, assume not running
    res.json({
      isRunning: false,
      containerStatus: 'Unknown',
      error: error.message,
    })
  }
})

app.post('/api/bot/start', checkAdmin, async (req, res) => {
  try {
    // Start the bot container
    const { stdout, stderr } = await execPromise('docker start lbank-market-making-bot')
    res.json({ 
      success: true, 
      message: 'Bot started successfully',
      output: stdout 
    })
  } catch (error) {
    // If container doesn't exist, try docker-compose
    try {
      const { stdout } = await execPromise('docker-compose up -d market-making-bot', {
        cwd: path.join(__dirname, '..')
      })
      res.json({ 
        success: true, 
        message: 'Bot started successfully via docker-compose',
        output: stdout 
      })
    } catch (composeError) {
      res.status(500).json({ 
        success: false, 
        error: 'Failed to start bot',
        details: composeError.message 
      })
    }
  }
})

app.post('/api/bot/stop', checkAdmin, async (req, res) => {
  try {
    // Stop the bot container
    const { stdout, stderr } = await execPromise('docker stop lbank-market-making-bot')
    res.json({ 
      success: true, 
      message: 'Bot stopped successfully',
      output: stdout 
    })
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: 'Failed to stop bot',
      details: error.message 
    })
  }
})

app.get('/api/logs', (req, res) => {
  // Read logs from docker or log file
  // For now, return empty array
  res.json({ logs: [] })
})

// Debug endpoint to check admin wallet configuration
app.get('/api/debug/admin-wallets', (req, res) => {
  const adminWallets = getAdminWallets()
  const envPath = ENV_PATH
  const envExists = fs.existsSync(envPath)
  let envContent = null
  if (envExists) {
    try {
      envContent = fs.readFileSync(envPath, 'utf8')
        .split('\n')
        .filter(line => line.includes('ADMIN_WALLETS'))
        .join('\n')
    } catch (e) {
      envContent = `Error reading: ${e.message}`
    }
  }
  
  res.json({
    adminWallets: adminWallets,
    envPath: envPath,
    envExists: envExists,
    processEnvAdminWallets: process.env.ADMIN_WALLETS || 'not set',
    envFileContent: envContent,
  })
})

app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`)
  const adminWallets = getAdminWallets()
  console.log(`Admin wallets: ${adminWallets.join(', ') || 'None configured'}`)
  console.log(`Reading .env from: ${ENV_PATH}`)
  if (fs.existsSync(ENV_PATH)) {
    console.log(`✓ .env file found`)
  } else {
    console.log(`⚠ .env file not found at ${ENV_PATH}`)
  }
})
