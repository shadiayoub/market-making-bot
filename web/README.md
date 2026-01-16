# Market Making Bot - Web UI

Next.js web interface for managing the LBank Market Making Bot.

## Features

- Web3 wallet authentication (MetaMask)
- Admin-only access (wallet addresses configured in .env)
- Real-time configuration management
- Bot status monitoring
- Logs viewer

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure admin wallets in `.env`:
```
ADMIN_WALLETS=0x1234...,0x5678...
```

3. Run development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
npm start
```

## Docker

The web UI is included in docker-compose.yml and will start automatically with:
```bash
docker-compose up
```

Access the UI at: http://localhost:3000
