#!/usr/bin/env python3
"""
TeraETH EVM RPC Proxy

This proxy translates Ethereum-compatible JSON-RPC calls into TeraETH node
RPC calls, enabling MetaMask and other EVM wallets to interact with the
TeraETH L2 network.

Usage:
    python3 evm_rpc_proxy.py [--host HOST] [--port PORT] [--node-rpc-url URL]
"""

import argparse
import asyncio
import hashlib
import json
import logging
import struct
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from aiohttp import web

from config import (
    BASE_FEE_PER_GAS,
    BLOCK_GAS_LIMIT,
    CHAIN_ID,
    CLIENT_VERSION,
    EVM_RPC_HOST,
    EVM_RPC_PORT,
    NATIVE_CURRENCY_DECIMALS,
    NATIVE_CURRENCY_NAME,
    NATIVE_CURRENCY_SYMBOL,
    NETWORK_ID,
    NODE_RPC_HOST,
    NODE_RPC_PASSWORD,
    NODE_RPC_PORT,
    NODE_RPC_USER,
    PROTOCOL_VERSION,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("teraeth-evm-rpc")


class NodeRPCClient:
    """Client for communicating with the underlying TeraETH node."""

    def __init__(self, host: str, port: int, user: str, password: str):
        self.url = f"http://{host}:{port}"
        self.auth = (user, password)
        self._id = 0

    async def call(self, method: str, params: Optional[List] = None) -> Any:
        """Make an RPC call to the TeraETH node."""
        import aiohttp

        self._id += 1
        payload = {
            "jsonrpc": "1.0",
            "id": self._id,
            "method": method,
            "params": params or [],
        }

        auth = aiohttp.BasicAuth(self.auth[0], self.auth[1])

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    json=payload,
                    auth=auth,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    result = await resp.json()
                    if result.get("error"):
                        logger.warning(
                            "Node RPC error: %s", result["error"]
                        )
                        return None
                    return result.get("result")
        except Exception as e:
            logger.error("Node RPC connection error: %s", e)
            return None


def satoshi_to_wei(satoshi: int) -> int:
    """Convert satoshi (1e-8) to wei (1e-18) scale.
    1 ETH = 1e8 satoshi in TeraETH node = 1e18 wei in EVM.
    So 1 satoshi = 1e10 wei.
    """
    return satoshi * (10 ** 10)


def wei_to_satoshi(wei: int) -> int:
    """Convert wei (1e-18) to satoshi (1e-8) scale."""
    return wei // (10 ** 10)


def to_hex(value: int) -> str:
    """Convert integer to hex string with 0x prefix."""
    return hex(value)


def to_hex_padded(value: int, byte_length: int = 32) -> str:
    """Convert integer to zero-padded hex string."""
    return "0x" + format(value, f"0{byte_length * 2}x")


def hash_to_eth_address(address_str: str) -> str:
    """Convert a TeraETH address to an Ethereum-style 0x address.
    Uses SHA-256 hash truncated to 20 bytes.
    """
    if address_str.startswith("0x") and len(address_str) == 42:
        return address_str.lower()
    h = hashlib.sha256(address_str.encode()).hexdigest()
    return "0x" + h[:40]


def node_block_to_eth_block(
    block_data: Dict, full_tx: bool = False
) -> Optional[Dict]:
    """Convert a TeraETH node block to Ethereum block format."""
    if block_data is None:
        return None

    block_height = block_data.get("height", 0)
    block_hash = "0x" + block_data.get("hash", "0" * 64)
    prev_hash = "0x" + block_data.get(
        "previousblockhash", "0" * 64
    )
    merkle_root = "0x" + block_data.get(
        "merkleroot", "0" * 64
    )
    timestamp = block_data.get("time", 0)
    nonce_val = block_data.get("nonce", 0)
    difficulty = block_data.get("difficulty", 1)
    size = block_data.get("size", 0)
    num_tx = block_data.get("nTx", 0)

    transactions = []
    if "tx" in block_data:
        for i, tx in enumerate(block_data["tx"]):
            if isinstance(tx, str):
                transactions.append("0x" + tx)
            elif isinstance(tx, dict) and full_tx:
                transactions.append(
                    node_tx_to_eth_tx(tx, block_hash, block_height, i)
                )
            elif isinstance(tx, dict):
                transactions.append("0x" + tx.get("txid", "0" * 64))

    eth_block = {
        "number": to_hex(block_height),
        "hash": block_hash,
        "parentHash": prev_hash,
        "nonce": to_hex_padded(nonce_val, 8),
        "sha3Uncles": "0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347",
        "logsBloom": "0x" + "00" * 256,
        "transactionsRoot": merkle_root,
        "stateRoot": merkle_root,
        "receiptsRoot": "0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
        "miner": "0x0000000000000000000000000000000000000000",
        "difficulty": to_hex(int(difficulty)),
        "totalDifficulty": to_hex(int(difficulty) * (block_height + 1)),
        "extraData": "0x",
        "size": to_hex(size),
        "gasLimit": to_hex(BLOCK_GAS_LIMIT),
        "gasUsed": to_hex(num_tx * 21000),
        "timestamp": to_hex(timestamp),
        "transactions": transactions,
        "uncles": [],
        "baseFeePerGas": to_hex(BASE_FEE_PER_GAS),
        "mixHash": "0x" + "00" * 32,
    }

    return eth_block


def node_tx_to_eth_tx(
    tx_data: Dict,
    block_hash: str = "0x" + "00" * 32,
    block_number: int = 0,
    tx_index: int = 0,
) -> Dict:
    """Convert a TeraETH node transaction to Ethereum transaction format."""
    txid = "0x" + tx_data.get("txid", tx_data.get("hash", "0" * 64))

    # Extract value from vout
    total_value = 0
    to_address = "0x0000000000000000000000000000000000000000"
    for vout in tx_data.get("vout", []):
        value_btc = vout.get("value", 0)
        total_value += int(value_btc * 1e8)
        # Try to extract address from scriptPubKey
        spk = vout.get("scriptPubKey", {})
        addresses = spk.get("addresses", [])
        if addresses:
            to_address = hash_to_eth_address(addresses[0])

    from_address = "0x0000000000000000000000000000000000000000"
    for vin in tx_data.get("vin", []):
        if "coinbase" not in vin:
            # Use the previous tx output address if available
            addr = vin.get("address", vin.get("addr", ""))
            if addr:
                from_address = hash_to_eth_address(addr)
                break

    eth_tx = {
        "hash": txid,
        "nonce": "0x0",
        "blockHash": block_hash,
        "blockNumber": to_hex(block_number),
        "transactionIndex": to_hex(tx_index),
        "from": from_address,
        "to": to_address,
        "value": to_hex(satoshi_to_wei(total_value)),
        "gas": to_hex(21000),
        "gasPrice": to_hex(BASE_FEE_PER_GAS),
        "input": "0x",
        "v": to_hex(CHAIN_ID * 2 + 35),
        "r": "0x" + "00" * 32,
        "s": "0x" + "00" * 32,
        "type": "0x0",
    }

    return eth_tx


class TeraETHEvmRpcProxy:
    """EVM-compatible JSON-RPC proxy for TeraETH."""

    def __init__(self, node_client: NodeRPCClient):
        self.node = node_client
        self._filter_id = 0
        self._filters: Dict[str, Dict] = {}
        self._pending_transactions: List[str] = []

        # Map of supported EVM RPC methods
        self.methods = {
            "eth_chainId": self.eth_chain_id,
            "eth_blockNumber": self.eth_block_number,
            "eth_getBlockByNumber": self.eth_get_block_by_number,
            "eth_getBlockByHash": self.eth_get_block_by_hash,
            "eth_getBalance": self.eth_get_balance,
            "eth_getTransactionCount": self.eth_get_transaction_count,
            "eth_getTransactionByHash": self.eth_get_transaction_by_hash,
            "eth_getTransactionReceipt": self.eth_get_transaction_receipt,
            "eth_sendRawTransaction": self.eth_send_raw_transaction,
            "eth_call": self.eth_call,
            "eth_estimateGas": self.eth_estimate_gas,
            "eth_gasPrice": self.eth_gas_price,
            "eth_maxPriorityFeePerGas": self.eth_max_priority_fee_per_gas,
            "eth_feeHistory": self.eth_fee_history,
            "eth_getCode": self.eth_get_code,
            "eth_getStorageAt": self.eth_get_storage_at,
            "eth_getLogs": self.eth_get_logs,
            "eth_newFilter": self.eth_new_filter,
            "eth_newBlockFilter": self.eth_new_block_filter,
            "eth_newPendingTransactionFilter": self.eth_new_pending_transaction_filter,
            "eth_getFilterChanges": self.eth_get_filter_changes,
            "eth_uninstallFilter": self.eth_uninstall_filter,
            "eth_accounts": self.eth_accounts,
            "eth_mining": self.eth_mining,
            "eth_hashrate": self.eth_hashrate,
            "eth_syncing": self.eth_syncing,
            "eth_protocolVersion": self.eth_protocol_version,
            "net_version": self.net_version,
            "net_listening": self.net_listening,
            "net_peerCount": self.net_peer_count,
            "web3_clientVersion": self.web3_client_version,
            "web3_sha3": self.web3_sha3,
            "eth_getBlockTransactionCountByHash": self.eth_get_block_transaction_count_by_hash,
            "eth_getBlockTransactionCountByNumber": self.eth_get_block_transaction_count_by_number,
            "eth_getTransactionByBlockHashAndIndex": self.eth_get_transaction_by_block_hash_and_index,
            "eth_getTransactionByBlockNumberAndIndex": self.eth_get_transaction_by_block_number_and_index,
            "eth_coinbase": self.eth_coinbase,
        }

    # === Core Methods ===

    async def eth_chain_id(self, params: List) -> str:
        return to_hex(CHAIN_ID)

    async def net_version(self, params: List) -> str:
        return str(NETWORK_ID)

    async def eth_protocol_version(self, params: List) -> str:
        return PROTOCOL_VERSION

    async def web3_client_version(self, params: List) -> str:
        return CLIENT_VERSION

    async def web3_sha3(self, params: List) -> str:
        if not params:
            return "0x"
        data = bytes.fromhex(params[0].replace("0x", ""))
        from hashlib import sha3_256
        return "0x" + sha3_256(data).hexdigest()

    # === Block Methods ===

    async def eth_block_number(self, params: List) -> str:
        info = await self.node.call("getblockchaininfo")
        if info is None:
            return "0x0"
        return to_hex(info.get("blocks", 0))

    async def eth_get_block_by_number(self, params: List) -> Optional[Dict]:
        if len(params) < 1:
            return None

        block_tag = params[0]
        full_tx = params[1] if len(params) > 1 else False

        height = await self._resolve_block_tag(block_tag)
        if height is None:
            return None

        block_hash = await self.node.call("getblockhash", [height])
        if block_hash is None:
            return None

        verbosity = 2 if full_tx else 1
        block_data = await self.node.call(
            "getblock", [block_hash, verbosity]
        )
        return node_block_to_eth_block(block_data, full_tx)

    async def eth_get_block_by_hash(self, params: List) -> Optional[Dict]:
        if len(params) < 1:
            return None

        block_hash = params[0].replace("0x", "")
        full_tx = params[1] if len(params) > 1 else False

        verbosity = 2 if full_tx else 1
        block_data = await self.node.call(
            "getblock", [block_hash, verbosity]
        )
        return node_block_to_eth_block(block_data, full_tx)

    async def eth_get_block_transaction_count_by_hash(
        self, params: List
    ) -> Optional[str]:
        if len(params) < 1:
            return None
        block_hash = params[0].replace("0x", "")
        block_data = await self.node.call("getblock", [block_hash, 1])
        if block_data is None:
            return None
        return to_hex(block_data.get("nTx", 0))

    async def eth_get_block_transaction_count_by_number(
        self, params: List
    ) -> Optional[str]:
        if len(params) < 1:
            return None
        height = await self._resolve_block_tag(params[0])
        if height is None:
            return None
        block_hash = await self.node.call("getblockhash", [height])
        if block_hash is None:
            return None
        block_data = await self.node.call("getblock", [block_hash, 1])
        if block_data is None:
            return None
        return to_hex(block_data.get("nTx", 0))

    # === Transaction Methods ===

    async def eth_get_transaction_by_hash(
        self, params: List
    ) -> Optional[Dict]:
        if len(params) < 1:
            return None
        txid = params[0].replace("0x", "")
        tx_data = await self.node.call("getrawtransaction", [txid, True])
        if tx_data is None:
            return None

        block_hash = "0x" + tx_data.get("blockhash", "00" * 32)
        block_height = 0
        if tx_data.get("blockhash"):
            block_data = await self.node.call(
                "getblock", [tx_data["blockhash"], 1]
            )
            if block_data:
                block_height = block_data.get("height", 0)

        return node_tx_to_eth_tx(tx_data, block_hash, block_height, 0)

    async def eth_get_transaction_receipt(
        self, params: List
    ) -> Optional[Dict]:
        if len(params) < 1:
            return None
        txid = params[0].replace("0x", "")
        tx_data = await self.node.call("getrawtransaction", [txid, True])
        if tx_data is None:
            return None

        block_hash = "0x" + tx_data.get("blockhash", "00" * 32)
        block_height = 0
        if tx_data.get("blockhash"):
            block_data = await self.node.call(
                "getblock", [tx_data["blockhash"], 1]
            )
            if block_data:
                block_height = block_data.get("height", 0)

        tx_hash = "0x" + tx_data.get("txid", "00" * 32)

        receipt = {
            "transactionHash": tx_hash,
            "transactionIndex": "0x0",
            "blockHash": block_hash,
            "blockNumber": to_hex(block_height),
            "from": "0x0000000000000000000000000000000000000000",
            "to": "0x0000000000000000000000000000000000000000",
            "cumulativeGasUsed": to_hex(21000),
            "gasUsed": to_hex(21000),
            "contractAddress": None,
            "logs": [],
            "logsBloom": "0x" + "00" * 256,
            "status": "0x1",  # success
            "effectiveGasPrice": to_hex(BASE_FEE_PER_GAS),
            "type": "0x0",
        }

        return receipt

    async def eth_send_raw_transaction(self, params: List) -> Optional[str]:
        """Accept raw EVM transactions.
        In the full implementation, this would decode the RLP-encoded
        Ethereum transaction, extract the transfer details, and create
        a corresponding TeraETH transaction.
        """
        if len(params) < 1:
            return None

        raw_tx = params[0]
        # For now, compute a transaction hash from the raw data
        tx_hash = hashlib.sha256(
            bytes.fromhex(raw_tx.replace("0x", ""))
        ).hexdigest()

        logger.info("Received raw EVM transaction: %s...", raw_tx[:20])
        logger.info("Transaction hash: 0x%s", tx_hash)

        # TODO: In production, decode RLP transaction, extract:
        # - nonce, gasPrice, gasLimit, to, value, data, v, r, s
        # - Recover sender address from signature
        # - Create and broadcast TeraETH transaction
        # - Return the transaction hash

        return "0x" + tx_hash

    async def eth_get_transaction_by_block_hash_and_index(
        self, params: List
    ) -> Optional[Dict]:
        if len(params) < 2:
            return None
        block_hash = params[0].replace("0x", "")
        tx_index = int(params[1], 16)
        block_data = await self.node.call("getblock", [block_hash, 2])
        if block_data is None:
            return None
        txs = block_data.get("tx", [])
        if tx_index >= len(txs):
            return None
        return node_tx_to_eth_tx(
            txs[tx_index],
            "0x" + block_hash,
            block_data.get("height", 0),
            tx_index,
        )

    async def eth_get_transaction_by_block_number_and_index(
        self, params: List
    ) -> Optional[Dict]:
        if len(params) < 2:
            return None
        height = await self._resolve_block_tag(params[0])
        if height is None:
            return None
        block_hash = await self.node.call("getblockhash", [height])
        if block_hash is None:
            return None
        tx_index = int(params[1], 16)
        block_data = await self.node.call("getblock", [block_hash, 2])
        if block_data is None:
            return None
        txs = block_data.get("tx", [])
        if tx_index >= len(txs):
            return None
        return node_tx_to_eth_tx(
            txs[tx_index],
            "0x" + block_hash,
            block_data.get("height", 0),
            tx_index,
        )

    # === Account / State Methods ===

    async def eth_get_balance(self, params: List) -> str:
        """Get balance for an address.
        Maps the 0x address back to a TeraETH address lookup.
        """
        # In the full implementation, maintain a mapping of
        # 0x addresses to TeraETH addresses
        # For now, return 0 for unknown addresses
        return "0x0"

    async def eth_get_transaction_count(self, params: List) -> str:
        """Get nonce for an address (transaction count)."""
        return "0x0"

    async def eth_get_code(self, params: List) -> str:
        """Get contract code at address.
        TeraETH L2 does not support smart contracts in v1.
        """
        return "0x"

    async def eth_get_storage_at(self, params: List) -> str:
        """Get storage at position.
        TeraETH L2 does not support smart contracts in v1.
        """
        return "0x0000000000000000000000000000000000000000000000000000000000000000"

    async def eth_accounts(self, params: List) -> List:
        """List accounts. Returns empty as this is not a wallet provider."""
        return []

    async def eth_coinbase(self, params: List) -> str:
        return "0x0000000000000000000000000000000000000000"

    # === Gas / Fee Methods ===

    async def eth_gas_price(self, params: List) -> str:
        return to_hex(BASE_FEE_PER_GAS)

    async def eth_max_priority_fee_per_gas(self, params: List) -> str:
        return to_hex(0)

    async def eth_fee_history(self, params: List) -> Dict:
        block_count = int(params[0], 16) if params else 1
        newest_block = await self._resolve_block_tag(
            params[1] if len(params) > 1 else "latest"
        )
        if newest_block is None:
            newest_block = 0

        oldest_block = max(0, newest_block - block_count + 1)

        base_fees = [to_hex(BASE_FEE_PER_GAS)] * (block_count + 1)
        gas_used_ratios = [0.5] * block_count

        reward = []
        if len(params) > 2 and params[2]:
            reward = [[to_hex(0)] * len(params[2])] * block_count

        result = {
            "oldestBlock": to_hex(oldest_block),
            "baseFeePerGas": base_fees,
            "gasUsedRatio": gas_used_ratios,
        }
        if reward:
            result["reward"] = reward
        return result

    async def eth_estimate_gas(self, params: List) -> str:
        return to_hex(21000)

    async def eth_call(self, params: List) -> str:
        """Execute a call (read-only).
        Smart contracts not supported in v1 - return empty.
        """
        return "0x"

    # === Mining Methods ===

    async def eth_mining(self, params: List) -> bool:
        info = await self.node.call("getmininginfo")
        if info is None:
            return False
        return info.get("blocks", 0) > 0

    async def eth_hashrate(self, params: List) -> str:
        info = await self.node.call("getmininginfo")
        if info is None:
            return "0x0"
        hashrate = info.get("networkhashps", 0)
        return to_hex(int(hashrate))

    # === Network Methods ===

    async def net_listening(self, params: List) -> bool:
        info = await self.node.call("getnetworkinfo")
        if info is None:
            return False
        return True

    async def net_peer_count(self, params: List) -> str:
        info = await self.node.call("getnetworkinfo")
        if info is None:
            return "0x0"
        connections = info.get("connections", 0)
        return to_hex(connections)

    async def eth_syncing(self, params: List) -> Any:
        """Check sync status."""
        info = await self.node.call("getblockchaininfo")
        if info is None:
            return False

        blocks = info.get("blocks", 0)
        headers = info.get("headers", 0)

        if blocks >= headers:
            return False

        return {
            "startingBlock": "0x0",
            "currentBlock": to_hex(blocks),
            "highestBlock": to_hex(headers),
        }

    # === Filter Methods ===

    async def eth_new_filter(self, params: List) -> str:
        self._filter_id += 1
        filter_id = to_hex(self._filter_id)
        self._filters[filter_id] = {
            "type": "log",
            "params": params[0] if params else {},
            "last_block": 0,
        }
        return filter_id

    async def eth_new_block_filter(self, params: List) -> str:
        self._filter_id += 1
        filter_id = to_hex(self._filter_id)
        info = await self.node.call("getblockchaininfo")
        current_block = info.get("blocks", 0) if info else 0
        self._filters[filter_id] = {
            "type": "block",
            "last_block": current_block,
        }
        return filter_id

    async def eth_new_pending_transaction_filter(self, params: List) -> str:
        self._filter_id += 1
        filter_id = to_hex(self._filter_id)
        self._filters[filter_id] = {
            "type": "pending_tx",
            "last_check": time.time(),
        }
        return filter_id

    async def eth_get_filter_changes(self, params: List) -> List:
        if len(params) < 1:
            return []
        filter_id = params[0]
        f = self._filters.get(filter_id)
        if f is None:
            return []

        if f["type"] == "block":
            info = await self.node.call("getblockchaininfo")
            current_block = info.get("blocks", 0) if info else 0
            last = f["last_block"]
            f["last_block"] = current_block
            hashes = []
            for h in range(last + 1, current_block + 1):
                bh = await self.node.call("getblockhash", [h])
                if bh:
                    hashes.append("0x" + bh)
            return hashes

        return []

    async def eth_uninstall_filter(self, params: List) -> bool:
        if len(params) < 1:
            return False
        filter_id = params[0]
        if filter_id in self._filters:
            del self._filters[filter_id]
            return True
        return False

    async def eth_get_logs(self, params: List) -> List:
        """Get logs matching filter. No smart contract logs in v1."""
        return []

    # === Helper Methods ===

    async def _resolve_block_tag(self, tag: str) -> Optional[int]:
        """Resolve a block tag to a block height."""
        if tag in ("latest", "pending", "safe", "finalized"):
            info = await self.node.call("getblockchaininfo")
            if info is None:
                return None
            return info.get("blocks", 0)
        elif tag == "earliest":
            return 0
        else:
            try:
                return int(tag, 16)
            except (ValueError, TypeError):
                return None


# === HTTP Server ===


async def handle_rpc(request: web.Request) -> web.Response:
    """Handle incoming JSON-RPC requests."""
    proxy: TeraETHEvmRpcProxy = request.app["proxy"]

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
        )

    # Handle batch requests
    if isinstance(body, list):
        responses = []
        for req in body:
            resp = await process_single_request(proxy, req)
            responses.append(resp)
        return web.json_response(responses)

    resp = await process_single_request(proxy, body)
    return web.json_response(resp)


async def process_single_request(
    proxy: TeraETHEvmRpcProxy, request: Dict
) -> Dict:
    """Process a single JSON-RPC request."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", [])

    logger.debug("RPC call: %s(%s)", method, params)

    handler = proxy.methods.get(method)
    if handler is None:
        logger.warning("Unsupported method: %s", method)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}",
            },
        }

    try:
        result = await handler(params)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        }
    except Exception as e:
        logger.error("Error handling %s: %s", method, e, exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}",
            },
        }


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    proxy: TeraETHEvmRpcProxy = request.app["proxy"]
    info = await proxy.node.call("getblockchaininfo")
    healthy = info is not None

    return web.json_response(
        {
            "status": "ok" if healthy else "error",
            "chain_id": CHAIN_ID,
            "network": CHAIN_NAME if hasattr(sys.modules[__name__], 'CHAIN_NAME') else "TeraETH",
            "node_connected": healthy,
            "block_height": info.get("blocks", 0) if info else 0,
        },
        status=200 if healthy else 503,
    )


def create_app(
    node_host: str = NODE_RPC_HOST,
    node_port: int = NODE_RPC_PORT,
    node_user: str = NODE_RPC_USER,
    node_password: str = NODE_RPC_PASSWORD,
) -> web.Application:
    """Create the aiohttp web application."""
    app = web.Application()

    node_client = NodeRPCClient(node_host, node_port, node_user, node_password)
    proxy = TeraETHEvmRpcProxy(node_client)
    app["proxy"] = proxy

    # CORS middleware
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    app.middlewares.append(cors_middleware)

    app.router.add_post("/", handle_rpc)
    app.router.add_get("/health", handle_health)
    # Some wallets send to root with GET
    app.router.add_get("/", handle_health)
    # Handle OPTIONS for CORS preflight
    app.router.add_options("/", handle_rpc)

    return app


def main():
    parser = argparse.ArgumentParser(
        description="TeraETH EVM RPC Proxy - MetaMask compatible JSON-RPC endpoint"
    )
    parser.add_argument(
        "--host", default=EVM_RPC_HOST, help=f"Listen host (default: {EVM_RPC_HOST})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=EVM_RPC_PORT,
        help=f"Listen port (default: {EVM_RPC_PORT})",
    )
    parser.add_argument(
        "--node-host",
        default=NODE_RPC_HOST,
        help=f"TeraETH node RPC host (default: {NODE_RPC_HOST})",
    )
    parser.add_argument(
        "--node-port",
        type=int,
        default=NODE_RPC_PORT,
        help=f"TeraETH node RPC port (default: {NODE_RPC_PORT})",
    )
    parser.add_argument(
        "--node-user",
        default=NODE_RPC_USER,
        help="TeraETH node RPC username",
    )
    parser.add_argument(
        "--node-password",
        default=NODE_RPC_PASSWORD,
        help="TeraETH node RPC password",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting TeraETH EVM RPC Proxy")
    logger.info("  Chain ID: %d (0x%x)", CHAIN_ID, CHAIN_ID)
    logger.info("  Native Token: %s (%s)", NATIVE_CURRENCY_NAME, NATIVE_CURRENCY_SYMBOL)
    logger.info("  EVM RPC: http://%s:%d", args.host, args.port)
    logger.info("  Node RPC: http://%s:%d", args.node_host, args.node_port)

    app = create_app(args.node_host, args.node_port, args.node_user, args.node_password)
    web.run_app(app, host=args.host, port=args.port, print=logger.info)


if __name__ == "__main__":
    main()
