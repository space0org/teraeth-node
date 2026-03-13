#!/bin/bash
# TeraETH EVM RPC Proxy - Start Script
#
# This starts the EVM-compatible JSON-RPC proxy that allows MetaMask
# and other Ethereum wallets to connect to the TeraETH L2 network.
#
# Prerequisites:
#   - Python 3.8+
#   - TeraETH node running with RPC enabled
#   - pip install -r requirements.txt
#
# Usage:
#   ./run.sh [--node-host HOST] [--node-port PORT] [--node-user USER] [--node-password PASS]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Install dependencies if needed
if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
fi

echo "============================================"
echo "  TeraETH EVM RPC Proxy"
echo "  Chain ID: 200011"
echo "  Native Token: ETH"
echo "  RPC Endpoint: http://0.0.0.0:8545"
echo "============================================"
echo ""

python3 evm_rpc_proxy.py "$@"
