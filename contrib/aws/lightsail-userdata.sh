#!/bin/bash
# BitcoinCard Node - AWS Lightsail User Data Script
# This script automatically sets up a BitcoinCard seed node on Ubuntu

set -e

# Configuration
BITCOINCARD_VERSION="1.0.0"
BITCOINCARD_USER="bitcoincard"
BITCOINCARD_DATA="/home/${BITCOINCARD_USER}/.bitcoincard"
BITCOINCARD_PORT=9333
BITCOINCARD_RPCPORT=9332

echo "=== BitcoinCard Node Setup Starting ==="

# Update system
apt-get update
apt-get upgrade -y

# Install dependencies
apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    libtool \
    autotools-dev \
    automake \
    bsdmainutils \
    python3 \
    libssl-dev \
    libevent-dev \
    libboost-system-dev \
    libboost-filesystem-dev \
    libboost-test-dev \
    libboost-thread-dev \
    libdb-dev \
    libdb++-dev \
    libgmp-dev \
    git

# Create bitcoincard user
useradd -m -s /bin/bash ${BITCOINCARD_USER} || true

# Clone and build BitcoinCard
cd /home/${BITCOINCARD_USER}
if [ ! -d "bitcoincard-node" ]; then
    git clone https://github.com/space0org/bitcoincard-node.git
fi
cd bitcoincard-node

# Build
mkdir -p build && cd build
cmake -GNinja .. \
    -DBUILD_BITCOIN_QT=OFF \
    -DBUILD_BITCOIN_WALLET=ON \
    -DENABLE_UPNP=OFF \
    -DENABLE_NATPMP=OFF \
    -DBUILD_BITCOIN_ZMQ=OFF \
    -DENABLE_MAN=OFF
ninja -j$(nproc) bitcoind bitcoin-cli

# Install binaries
cp src/bitcoind /usr/local/bin/bitcoincardd
cp src/bitcoin-cli /usr/local/bin/bitcoincard-cli
chmod +x /usr/local/bin/bitcoincardd /usr/local/bin/bitcoincard-cli

# Create data directory
mkdir -p ${BITCOINCARD_DATA}

# Generate random RPC credentials
RPC_USER="bitcoincardrpc"
RPC_PASS=$(openssl rand -hex 32)

# Create configuration file
cat > ${BITCOINCARD_DATA}/bitcoincard.conf << CONF
# BitcoinCard Node Configuration
# Seed Node Setup

# Network
listen=1
port=${BITCOINCARD_PORT}
maxconnections=125

# RPC (localhost only for security)
server=1
rpcuser=${RPC_USER}
rpcpassword=${RPC_PASS}
rpcport=${BITCOINCARD_RPCPORT}
rpcallowip=127.0.0.1
rpcbind=127.0.0.1

# Logging
debug=0
printtoconsole=0

# Performance
dbcache=256
maxmempool=300
CONF

# Set ownership
chown -R ${BITCOINCARD_USER}:${BITCOINCARD_USER} /home/${BITCOINCARD_USER}

# Create systemd service
cat > /etc/systemd/system/bitcoincard.service << SERVICE
[Unit]
Description=BitcoinCard Node
After=network.target

[Service]
Type=simple
User=${BITCOINCARD_USER}
Group=${BITCOINCARD_USER}
ExecStart=/usr/local/bin/bitcoincardd -datadir=${BITCOINCARD_DATA} -conf=${BITCOINCARD_DATA}/bitcoincard.conf
ExecStop=/usr/local/bin/bitcoincard-cli -datadir=${BITCOINCARD_DATA} stop
Restart=on-failure
RestartSec=30
TimeoutStopSec=60

# Security
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
SERVICE

# Enable and start service
systemctl daemon-reload
systemctl enable bitcoincard
systemctl start bitcoincard

# Configure firewall (if ufw is available)
if command -v ufw &> /dev/null; then
    ufw allow ${BITCOINCARD_PORT}/tcp comment 'BitcoinCard P2P'
    # Note: RPC port is NOT opened - keep it localhost only
fi

echo "=== BitcoinCard Node Setup Complete ==="
echo "Node is starting. Check status with: systemctl status bitcoincard"
echo "View logs with: journalctl -u bitcoincard -f"
echo ""
echo "RPC credentials saved in: ${BITCOINCARD_DATA}/bitcoincard.conf"
echo "Public IP: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo 'N/A')"
