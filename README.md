# Monad Testnet Bot Web Interface

This project provides a web-based user interface for interacting with the Monad Testnet Bot scripts.

## Features

*   Dashboard for monitoring bot status (balances, transactions)
*   Import and manage multiple private keys
*   Configure bot settings (cycles, delay, RPC)
*   Run bot functions (Stake, Swap, Deploy, Send) via UI
*   View transaction logs with links to the Monad Explorer
*   Define custom workflows (e.g., Swap then Stake)
*   Responsive design for desktop and mobile
*   Dark/Light theme support

## Tech Stack

*   **Frontend:** Next.js, React, Tailwind CSS (or Chakra UI), Web3.js
*   **Backend:** FastAPI (or Flask), Python

## Project Structure

```
monad-testnet-bot-web/
├── backend/
│   ├── scripts/               # Original Python bot scripts
│   ├── api/                   # FastAPI/Flask API endpoints
│   ├── config/                # Config files (RPC, private keys)
│   └── requirements.txt       # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/        # React UI components
│   │   ├── pages/             # Next.js pages
│   │   ├── styles/            # CSS/Tailwind styles
│   │   └── utils/             # Web3.js interaction logic
│   ├── public/                # Static assets (logo, etc.)
│   └── package.json           # Frontend Node.js dependencies
└── README.md                  # This file
```

## Setup

*(Instructions will be added here)*

## Usage

*(Instructions will be added here)* 