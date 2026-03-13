"""
TeraETH EVM RPC Proxy Configuration
"""

# TeraETH L2 Network Configuration
CHAIN_ID = 200011
NETWORK_ID = 200011
CHAIN_NAME = "TeraETH"
NATIVE_CURRENCY_NAME = "Ether"
NATIVE_CURRENCY_SYMBOL = "ETH"
NATIVE_CURRENCY_DECIMALS = 18

# EVM RPC Proxy Settings
EVM_RPC_HOST = "0.0.0.0"
EVM_RPC_PORT = 8545

# TeraETH Node RPC Connection (underlying node)
NODE_RPC_HOST = "127.0.0.1"
NODE_RPC_PORT = 9332
NODE_RPC_USER = "teraeth"
NODE_RPC_PASSWORD = "teraeth"

# Block gas limit (similar to Ethereum)
BLOCK_GAS_LIMIT = 30000000

# Base fee per gas (in wei) - fixed for L2
BASE_FEE_PER_GAS = 1000000000  # 1 Gwei

# Genesis block hash (TeraETH genesis)
GENESIS_BLOCK_HASH = "0x00000000371248c26ab056f39e5b554f1417c23a11d19e8f7cd7f849868c68ca"

# EIP-155 replay protection
EIP155_BLOCK = 0

# Protocol version
PROTOCOL_VERSION = "0x41"  # 65

# Client version string
CLIENT_VERSION = "TeraETH/v1.0.0"
