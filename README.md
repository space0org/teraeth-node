BitcoinCard Node
================

BitcoinCard is a new blockchain network forked from Bitcoin Cash Node. It aims to provide
a converging platform for BTC, BCH, and BSV ecosystems with enhanced scalability and
NFC card-based wallet integration.

What is BitcoinCard?
--------------------

BitcoinCard (BCD) is a digital currency that enables instant payments to anyone,
anywhere in the world. It uses peer-to-peer technology to operate with no
central authority: managing transactions and issuing money are carried out
collectively by the network.

Key Features:
- SHA-256 Proof of Work (compatible with Bitcoin mining hardware)
- 32MB default block size (scalable)
- ASERT difficulty adjustment algorithm
- CashAddr format with "bitcoincard:" prefix

Network Parameters
------------------

| Parameter | Mainnet | Testnet | Regtest |
|-----------|---------|---------|---------|
| Default Port | 9333 | 19333 | 19444 |
| RPC Port | 9332 | 19332 | 19443 |
| Address Prefix | bitcoincard: | bcdtest: | bcdreg: |
| Magic Bytes | 0xb1d3c2f4 | - | 0xdcd5c2fc |

Genesis Block
-------------

- Timestamp: December 27, 2025 (1735315200)
- Message: "BitcoinCard Genesis 27/Dec/2025 Converging BTC BCH BSV into One Future"
- Hash: `000000ffab1f5e1a4449198369b7a927929f836e79c981141c7506a975c7fbcf`
- Merkle Root: `b2025da4eb73530a5ad6290ee74f89834850bcb6cf4bc674566801568745acae`
- Difficulty: 0x1e00ffff (256x easier than Bitcoin's difficulty 1)

Quick Start
-----------

### Building from Source

```bash
git clone https://github.com/space0org/bitcoincard-node.git
cd bitcoincard-node
mkdir build && cd build
cmake -GNinja .. -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_WALLET=ON
ninja bitcoind bitcoin-cli
```

### Running a Node

Start the BitcoinCard daemon:

```bash
# Mainnet
./src/bitcoind -datadir=/path/to/data -daemon

# Regtest (for testing)
./src/bitcoind -regtest -datadir=/path/to/data -daemon
```

### Basic Commands

```bash
# Get blockchain info
./src/bitcoin-cli -datadir=/path/to/data getblockchaininfo

# Get network info
./src/bitcoin-cli -datadir=/path/to/data getnetworkinfo

# Stop the node
./src/bitcoin-cli -datadir=/path/to/data stop
```

Seed Node Setup
---------------

BitcoinCard uses DNS seeds and fixed seed nodes for peer discovery. As a new network,
you can help by running a seed node.

### Option 1: Connect to Known Nodes (Command Line)

If you know the IP address of another BitcoinCard node, connect directly:

```bash
./src/bitcoind -datadir=/path/to/data -addnode=IP_ADDRESS:9333
```

Or add to your configuration file (`bitcoincard.conf`):

```
addnode=IP_ADDRESS:9333
addnode=ANOTHER_IP:9333
```

### Option 2: Run a Seed Node

To run a seed node that others can connect to:

1. Ensure your node is publicly accessible on port 9333
2. Run with listen enabled:

```bash
./src/bitcoind -datadir=/path/to/data -listen=1 -port=9333
```

3. Share your IP address or domain with other network participants

### Option 3: DNS Seed Setup

For production networks, DNS seeds provide automatic peer discovery.

1. Set up a DNS server that responds to seed queries
2. Configure A records pointing to known BitcoinCard nodes
3. Add your DNS seed to `src/chainparams.cpp`:

```cpp
vSeeds.emplace_back("seed.yourdomain.com");
```

### Configuration File

Create `~/.bitcoincard/bitcoincard.conf` (Linux/Mac) or 
`%APPDATA%\BitcoinCard\bitcoincard.conf` (Windows):

```ini
# Network settings
listen=1
port=9333
rpcport=9332

# Seed nodes (add known nodes here)
addnode=node1.example.com:9333
addnode=node2.example.com:9333

# RPC settings (for local access)
rpcuser=yourusername
rpcpassword=yourpassword
rpcallowip=127.0.0.1

# Optional: Enable mining
# gen=1

# Optional: Prune old blocks to save disk space
# prune=10000
```

Mining
------

BitcoinCard uses SHA-256 Proof of Work, compatible with Bitcoin ASIC miners.

### Solo Mining (Regtest)

```bash
# Generate blocks in regtest mode
./src/bitcoin-cli -regtest -datadir=/path/to/data generatetoaddress 1 YOUR_ADDRESS
```

### Pool Mining

Use `getblocktemplate` RPC for pool integration:

```bash
./src/bitcoin-cli -datadir=/path/to/data getblocktemplate '{"rules": ["segwit"]}'
```

System Requirements
-------------------

Minimum:
- CPU: 2 cores
- RAM: 2GB
- Disk: 10GB (pruned mode) / 500GB+ (full node, as chain grows)
- Network: Stable internet connection

Recommended:
- CPU: 4+ cores
- RAM: 4GB+
- Disk: SSD with 1TB+
- Network: 100Mbps+

License
-------

BitcoinCard Node is released under the terms of the MIT license. See
[COPYING](COPYING) for more information or see
[https://opensource.org/licenses/MIT](https://opensource.org/licenses/MIT).

This software is based on Bitcoin Cash Node, which includes software developed
by the OpenSSL Project for use in the [OpenSSL Toolkit](https://www.openssl.org/),
cryptographic software written by [Eric Young](mailto:eay@cryptsoft.com), and
UPnP software written by Thomas Bernard.

Development
-----------

BitcoinCard development takes place at:
- GitHub: [https://github.com/space0org/bitcoincard-node](https://github.com/space0org/bitcoincard-node)

Disclosure Policy
-----------------

We have a [Disclosure Policy](DISCLOSURE_POLICY.md) for responsible disclosure
of security issues.

Further Info
------------

See [doc/README.md](doc/README.md) for further info on installation, building,
development and more.
