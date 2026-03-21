# Liquidation Guard

AI-powered DeFi liquidation protection agent.

## Stack
- **Agent**: Python + Claude API (Anthropic)
- **Chain**: Aave V3 on Ethereum / Sepolia
- **Automation**: Gelato Web3 Functions
- **Contracts**: Solidity + Foundry
- **Frontend**: Next.js + wagmi (coming later)

## Structure
```
liquidation-guard/
├── agent/          # Python AI Agent
│   ├── venv/       # Python virtual environment
│   └── ...
├── contracts/      # Solidity contracts (Foundry)
└── frontend/       # Next.js frontend (coming later)
```

## Setup
```bash
cp .env.example .env
# Fill in your keys in .env

# Python agent
cd agent && source venv/bin/activate
pip install -r requirements.txt

# Contracts
cd contracts && forge build
```
