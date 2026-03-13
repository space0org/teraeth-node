#!/bin/bash
# TeraETH Node - AWS Lightsail User Data Script
# This script automatically sets up a TeraETH seed node on Ubuntu

set -e

# Configuration
TERAETH_VERSION="1.0.0"
TERAETH_USER="teraeth"
TERAETH_DATA="/home/${TERAETH_USER}/.teraeth"
TERAETH_PORT=9333
TERAETH_RPCPORT=9332

echo "=== TeraETH Node Setup Starting ==="

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

# Create teraeth user
useradd -m -s /bin/bash ${TERAETH_USER} || true

# Clone and build TeraETH
cd /home/${TERAETH_USER}
if [ ! -d "teraeth-node" ]; then
    git clone https://github.com/space0org/teraeth-node.git
fi
cd teraeth-node

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
cp src/bitcoind /usr/local/bin/teraethd
cp src/bitcoin-cli /usr/local/bin/teraeth-cli
chmod +x /usr/local/bin/teraethd /usr/local/bin/teraeth-cli

# Create data directory
mkdir -p ${TERAETH_DATA}

# Generate random RPC credentials
RPC_USER="teraethrpc"
RPC_PASS=$(openssl rand -hex 32)

# Create configuration file
cat > ${TERAETH_DATA}/teraeth.conf << CONF
# TeraETH Node Configuration
# Seed Node Setup

# Network
listen=1
port=${TERAETH_PORT}
maxconnections=125

# RPC (localhost only for security)
server=1
rpcuser=${RPC_USER}
rpcpassword=${RPC_PASS}
rpcport=${TERAETH_RPCPORT}
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
chown -R ${TERAETH_USER}:${TERAETH_USER} /home/${TERAETH_USER}

# Create systemd service
cat > /etc/systemd/system/teraeth.service << SERVICE
[Unit]
Description=TeraETH Node
After=network.target

[Service]
Type=simple
User=${TERAETH_USER}
Group=${TERAETH_USER}
ExecStart=/usr/local/bin/teraethd -datadir=${TERAETH_DATA} -conf=${TERAETH_DATA}/teraeth.conf
ExecStop=/usr/local/bin/teraeth-cli -datadir=${TERAETH_DATA} stop
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
systemctl enable teraeth
systemctl start teraeth

# Configure firewall (if ufw is available)
if command -v ufw &> /dev/null; then
    ufw allow ${TERAETH_PORT}/tcp comment 'TeraETH P2P'
    # Note: RPC port is NOT opened - keep it localhost only
fi

echo "=== TeraETH Node Setup Complete ==="
echo "Node is starting. Check status with: systemctl status teraeth"
echo "View logs with: journalctl -u teraeth -f"
echo ""
echo "RPC credentials saved in: ${TERAETH_DATA}/teraeth.conf"
echo "Public IP: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo 'N/A')"
