# BitcoinCard Seed Node - AWS Lightsail Setup Guide

This guide explains how to set up a BitcoinCard seed node on AWS Lightsail for $3.50/month.

## Prerequisites

- AWS Account
- Credit card for billing (first month may be free with AWS credits)

## Step 1: Create Lightsail Instance

1. Go to [AWS Lightsail Console](https://lightsail.aws.amazon.com/)
2. Click **Create instance**
3. Select settings:
   - **Region**: Choose closest to your users (e.g., Tokyo for Japan)
   - **Platform**: Linux/Unix
   - **Blueprint**: OS Only → **Ubuntu 22.04 LTS**
   - **Instance plan**: $3.50/month (512 MB RAM, 1 vCPU, 20 GB SSD)
   - **Instance name**: `bitcoincard-seed-1`

4. Expand **Add launch script** and paste the contents of `lightsail-userdata.sh`

5. Click **Create instance**

## Step 2: Configure Static IP

1. In Lightsail console, go to **Networking** tab
2. Click **Create static IP**
3. Attach to your instance
4. **Note down this IP address** - this will be your seed node IP

## Step 3: Configure Firewall

1. Click on your instance
2. Go to **Networking** tab
3. Under **IPv4 Firewall**, click **Add rule**:
   - **Application**: Custom
   - **Protocol**: TCP
   - **Port**: 9333
4. Click **Create**

**Important**: Do NOT open port 9332 (RPC) - keep it localhost only for security.

## Step 4: Verify Node is Running

1. SSH into your instance:
   ```bash
   ssh -i your-key.pem ubuntu@YOUR_STATIC_IP
   ```

2. Check node status:
   ```bash
   sudo systemctl status bitcoincard
   ```

3. Check blockchain info:
   ```bash
   sudo -u bitcoincard bitcoincard-cli -datadir=/home/bitcoincard/.bitcoincard getblockchaininfo
   ```

4. Check network connections:
   ```bash
   sudo -u bitcoincard bitcoincard-cli -datadir=/home/bitcoincard/.bitcoincard getnetworkinfo
   ```

## Step 5: Report Your IP

Once your node is running, report your static IP address so it can be added to the seed node list in the BitcoinCard source code.

Your seed node IP: `YOUR_STATIC_IP:9333`

## Monitoring

### View Logs
```bash
sudo journalctl -u bitcoincard -f
```

### Restart Node
```bash
sudo systemctl restart bitcoincard
```

### Stop Node
```bash
sudo systemctl stop bitcoincard
```

## Cost Breakdown

| Item | Monthly Cost |
|------|-------------|
| Lightsail Instance ($3.50 plan) | $3.50 |
| Static IP (attached to running instance) | $0.00 |
| Data Transfer (first 1TB) | $0.00 |
| **Total** | **$3.50/month** |

## Troubleshooting

### Node won't start
```bash
# Check logs
sudo journalctl -u bitcoincard -n 100

# Check if port is in use
sudo netstat -tlnp | grep 9333
```

### Build failed
```bash
# Re-run build manually
cd /home/bitcoincard/bitcoincard-node/build
sudo -u bitcoincard cmake -GNinja .. -DBUILD_BITCOIN_QT=OFF -DBUILD_BITCOIN_WALLET=ON
sudo -u bitcoincard ninja -j1 bitcoind bitcoin-cli
```

### Out of memory during build
Use `-j1` instead of `-j$(nproc)` to reduce memory usage during compilation.

## Security Notes

1. **Never expose RPC port (9332)** to the internet
2. Keep your SSH key secure
3. Regularly update the system: `sudo apt update && sudo apt upgrade`
4. Consider enabling automatic security updates

## Next Steps

After your seed node is running:
1. Share your static IP with the BitcoinCard team
2. The IP will be added to `src/chainparams.cpp` as a fixed seed
3. New nodes will automatically connect to your seed node
