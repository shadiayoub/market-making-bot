# Market Making Bot - Web UI

A Next.js web interface for managing the LBank Market Making Bot with Web3 authentication.

## Features

- 🔐 **Web3 Authentication**: Connect with MetaMask wallet
- 👤 **Admin-Only Access**: Only wallets configured in `.env` can access
- ⚙️ **Configuration Management**: Update all bot settings through the UI
- 📊 **Real-Time Status**: Monitor bot status, balances, and market data
- 📝 **Logs Viewer**: View bot logs in real-time

## Setup

### 1. Configure Admin Wallets

Add your admin wallet addresses to `.env`:

```env
ADMIN_WALLETS=0x1234567890123456789012345678901234567890,0xabcdefabcdefabcdefabcdefabcdefabcdefabcd
```

### 2. Start Services

Using Docker Compose (recommended):

```bash
docker-compose up -d
```

This will start:
- **Bot**: `lbank-market-making-bot` (port: internal)
- **API Server**: `market-making-api` (port: 3001)
- **Web UI**: `market-making-web-ui` (port: 3000)

### 3. Access the UI

Open your browser and navigate to:
```
http://localhost:3000
```

Connect your MetaMask wallet (must be one of the admin wallets).

## Manual Setup (Development)

### API Server

```bash
cd api-server
npm install
npm start
```

### Web UI

```bash
cd web
npm install
npm run dev
```

## Configuration

All bot configuration can be managed through the web UI:

- **API Credentials**: LBank API key and secret
- **Trading Pair**: Trading pair and token symbol
- **Compliance Mode**: Enable/disable LBank compliance mode
- **Safety Features**: Max spread, loss, and exposure limits
- **Reference Price Mode**: Configure reference price-based trading
- **Sleep Time**: Configure iteration sleep times
- **Max Buy Price**: Set maximum buy price limit

## Security

- Only wallets listed in `ADMIN_WALLETS` can access the admin panel
- All API requests require admin wallet verification
- Configuration changes are validated before saving

## Troubleshooting

1. **Can't connect wallet**: Make sure MetaMask is installed and unlocked
2. **Access denied**: Verify your wallet address is in `ADMIN_WALLETS` in `.env`
3. **API errors**: Check that the API server is running on port 3001
4. **Config not saving**: Ensure the API server has write access to `.env` file
