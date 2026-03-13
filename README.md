TeraETH Node
============

TeraETH is an Ethereum L2 network built by hard-forking BitcoinCard (Bitcoin Cash Node fork).
It provides a MetaMask-compatible blockchain with ETH as the native payment token.

What is TeraETH?
----------------

TeraETH is a Layer 2 Ethereum network (Chain ID: 200011) that combines the proven
UTXO-based transaction model with an EVM-compatible JSON-RPC interface, enabling
standard Ethereum wallets like MetaMask to interact with the network.

Key Features:
- MetaMask Compatible: Full EVM JSON-RPC proxy on port 8545
- Native ETH Token: Uses ETH as the native currency (18 decimals)
- Chain ID 200011: Unique network identifier for wallet configuration
- SHA-256 Proof of Work: Compatible with Bitcoin mining hardware
- 32MB Block Size: High throughput capacity
- ASERT Difficulty Adjustment: Responsive difficulty algorithm

Network Parameters
------------------

| Parameter | Value |
|-----------|-------|
| Chain ID | 200011 |
| Native Token | ETH |
| Token Decimals | 18 |
| P2P Port | 9333 |
| Node RPC Port | 9332 |
| EVM RPC Port | 8545 |
| Block Time | ~10 minutes |
| Block Size | 32MB |
| Consensus | SHA-256 PoW |

MetaMask Configuration
----------------------

To add TeraETH to MetaMask:

| Setting | Value |
|---------|-------|
| Network Name | TeraETH |
| RPC URL | http://YOUR_NODE_IP:8545 |
| Chain ID | 200011 |
| Currency Symbol | ETH |
| Block Explorer URL | (optional) |

Quick Start
-----------

### 1. Build the TeraETH Node

    git clone https://github.com/space0org/teraeth-node.git
    cd teraeth-node
    mkdir build && cd build
    cmake -GNinja .. -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_WALLET=ON
    ninja bitcoind bitcoin-cli

### 2. Configure the Node

Create ~/.teraeth/teraeth.conf:

    # Network
    listen=1
    port=9333
    maxconnections=125

    # RPC (required for EVM proxy)
    server=1
    rpcuser=teraeth
    rpcpassword=YOUR_SECURE_PASSWORD
    rpcport=9332
    rpcallowip=127.0.0.1
    rpcbind=127.0.0.1

### 3. Start the Node

    # Mainnet
    ./src/bitcoind -datadir=~/.teraeth -daemon

    # Regtest (for testing)
    ./src/bitcoind -regtest -datadir=~/.teraeth -daemon

### 4. Start the EVM RPC Proxy

    cd evm-rpc-proxy
    pip3 install -r requirements.txt
    python3 evm_rpc_proxy.py \
        --node-host 127.0.0.1 \
        --node-port 9332 \
        --node-user teraeth \
        --node-password YOUR_SECURE_PASSWORD

The EVM RPC proxy will listen on port 8545 and translate MetaMask requests
to TeraETH node RPC calls.

### 5. Connect MetaMask

1. Open MetaMask
2. Click "Add Network"
3. Enter the TeraETH configuration (see table above)
4. Your RPC URL should point to your node's IP on port 8545

Architecture
------------

    MetaMask / EVM Wallets
            |
            | (JSON-RPC over HTTP, port 8545)
            v
    +-------------------+
    | EVM RPC Proxy     |  Python/aiohttp
    | (evm-rpc-proxy/)  |  Translates eth_* calls
    +-------------------+
            |
            | (Bitcoin JSON-RPC, port 9332)
            v
    +-------------------+
    | TeraETH Node      |  C++ (forked from BCHN)
    | (src/bitcoind)    |  UTXO-based blockchain
    +-------------------+
            |
            | (P2P protocol, port 9333)
            v
       TeraETH Network

EVM RPC Methods Supported
-------------------------

The EVM RPC proxy supports the following Ethereum JSON-RPC methods:

Core:
- eth_chainId - Returns 200011 (0x30D4B)
- eth_blockNumber - Current block height
- eth_syncing - Sync status
- eth_gasPrice - Gas price (fixed at 1 Gwei)
- eth_estimateGas - Gas estimation

Blocks:
- eth_getBlockByNumber
- eth_getBlockByHash
- eth_getBlockTransactionCountByHash
- eth_getBlockTransactionCountByNumber

Transactions:
- eth_getTransactionByHash
- eth_getTransactionReceipt
- eth_sendRawTransaction
- eth_getTransactionByBlockHashAndIndex
- eth_getTransactionByBlockNumberAndIndex

Account:
- eth_getBalance
- eth_getTransactionCount
- eth_getCode
- eth_getStorageAt
- eth_accounts

Filters:
- eth_newFilter
- eth_newBlockFilter
- eth_newPendingTransactionFilter
- eth_getFilterChanges
- eth_uninstallFilter
- eth_getLogs

Fees:
- eth_feeHistory
- eth_maxPriorityFeePerGas

Network:
- net_version
- net_listening
- net_peerCount
- web3_clientVersion
- web3_sha3

Docker Deployment
-----------------

    # Build EVM RPC proxy
    cd evm-rpc-proxy
    docker build -t teraeth-evm-proxy .

    # Run the EVM proxy
    docker run -d --name teraeth-evm-proxy \
        -p 8545:8545 \
        teraeth-evm-proxy \
        --node-host YOUR_NODE_HOST --node-port 9332 \
        --node-user teraeth --node-password YOUR_PASSWORD

Seed Node Setup
---------------

    ./src/bitcoind -datadir=~/.teraeth -addnode=IP_ADDRESS:9333

Or add to teraeth.conf:

    addnode=IP_ADDRESS:9333

Mining
------

TeraETH uses SHA-256 Proof of Work, compatible with Bitcoin ASIC miners.

    # Solo mining in regtest mode
    ./src/bitcoin-cli -regtest -datadir=~/.teraeth generatetoaddress 1 YOUR_ADDRESS

System Requirements
-------------------

Minimum:
- CPU: 2 cores
- RAM: 2GB
- Disk: 10GB (pruned) / 500GB+ (full node)
- Network: Stable internet
- Python 3.8+ (for EVM RPC proxy)

Recommended:
- CPU: 4+ cores
- RAM: 4GB+
- Disk: SSD 1TB+
- Network: 100Mbps+

License
-------

TeraETH Node is released under the terms of the MIT license. See
COPYING for more information or see https://opensource.org/licenses/MIT.

Based on Bitcoin Cash Node, which includes software developed by the OpenSSL Project,
cryptographic software by Eric Young, and UPnP software by Thomas Bernard.

Development
-----------

TeraETH development takes place at:
- GitHub: https://github.com/space0org/teraeth-node
- Domain: cyberdiver.jp

Disclosure Policy
-----------------

We have a Disclosure Policy (DISCLOSURE_POLICY.md) for responsible disclosure
of security issues.
