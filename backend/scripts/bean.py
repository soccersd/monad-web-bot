import os
import random
import asyncio
import time
from web3 import Web3
from web3.exceptions import ContractLogicError
import traceback
from typing import Dict, List, Optional, Tuple

# Constants
DEFAULT_RPC_URLS = [
    "https://testnet-rpc.monorail.xyz",
    "https://testnet-rpc.monad.xyz",
    "https://monad-testnet.drpc.org"
]
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_ROUTER_ADDRESS = "0xCa810D095e90Daae6e867c19DF6D9A8C56db2c89"
DEFAULT_WMON_ADDRESS = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
DEFAULT_CHAIN_ID = 10143

# Default Tokens (can be customized)
DEFAULT_TOKENS = {
    "USDC": {
        "address": "0x62534E4bBD6D9ebAC0ac99aeaa0aa48E56372df0",
        "decimals": 6,
    },
    "USDT": {
        "address": "0x88b8e2161dedc77ef4ab7585569d2415a1c1055d",
        "decimals": 6,
    },
    "BEAN": {
        "address": "0x268E4E24E0051EC27b3D27A95977E71cE6875a05",
        "decimals": 6,
    },
    "JAI": {
        "address": "0x70F893f65E3C1d7f82aad72f71615eb220b74D10",
        "decimals": 6,
    },
}

# ABI for ERC20 token
ERC20_ABI = [
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"}
]

# ABI for router
ROUTER_ABI = [
    {"inputs": [{"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactETHForTokens", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactTokensForETH", "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}], "stateMutability": "nonpayable", "type": "function"}
]

# Helper function to connect to RPC (picks one randomly)
def connect_to_rpc(rpc_urls: List[str] = DEFAULT_RPC_URLS):
    # Use default if None is provided
    urls_to_use = rpc_urls if rpc_urls is not None else DEFAULT_RPC_URLS
    random.shuffle(urls_to_use)
    for url in urls_to_use:
        try:
            w3 = Web3(Web3.HTTPProvider(url))
            if w3.is_connected():
                return w3
        except Exception:
            continue # Try next URL
    raise ConnectionError(f"Could not connect to any RPC in list: {urls_to_use}")

# Helper function to format step messages for logs
def format_step(step, message):
    steps = {'approve': 'Approve Token', 'swap': 'Execute Swap', 'balance': 'Check Balance'}
    step_text = steps.get(step, step.capitalize())
    return f"🔸 {step_text:<15} | {message}"

# Helper: Approve Token
async def _bean_approve_token(
    w3: Web3, account, private_key: str, token_address: str, spender: str, amount_wei: int, chain_id: int, logs: list
) -> Tuple[bool, Optional[str]]:
    try:
        token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        symbol = await asyncio.get_event_loop().run_in_executor(None, token_contract.functions.symbol().call)
        logs.append(format_step('approve', f'Checking approval for {symbol}...'))

        allowance = await asyncio.get_event_loop().run_in_executor(None, lambda: token_contract.functions.allowance(account.address, spender).call())
        if allowance >= amount_wei:
            logs.append(format_step('approve', f"✔ Allowance sufficient for {symbol} ({allowance} >= {amount_wei})."))
            return True, None

        logs.append(format_step('approve', f'Approving {symbol} for {spender[:8]}...'))
        gas_price = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.gas_price)
        nonce = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_transaction_count(account.address))

        tx = token_contract.functions.approve(spender, amount_wei).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': chain_id
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash_bytes = await asyncio.get_event_loop().run_in_executor(None, w3.eth.send_raw_transaction, signed_tx.raw_transaction)
        approve_hash = tx_hash_bytes.hex()
        logs.append(format_step('approve', f"Approval Tx Sent: {approve_hash}"))

        receipt = await asyncio.get_event_loop().run_in_executor(None, w3.eth.wait_for_transaction_receipt, tx_hash_bytes, timeout=180)
        if receipt.status != 1:
            logs.append(format_step('approve', f"✘ Approval failed: Status {receipt.status}"))
            raise Exception(f"Approval failed: Status {receipt.status}")

        logs.append(format_step('approve', f"✔ {symbol} approved!"))
        return True, approve_hash
    except Exception as e:
        logs.append(format_step('approve', f"✘ Approval failed: {str(e)}"))
        return False, None

# --- Refactored Main Execution Function --- #
async def execute_bean_swap(
    private_key: str,
    direction: str, # 'to_token' or 'to_mon'
    token_symbol: str,
    amount: float, # Amount of the input token (MON or the other token)
    # Configurable parameters
    rpc_urls: List[str] = DEFAULT_RPC_URLS,
    router_address: str = DEFAULT_ROUTER_ADDRESS,
    wmon_address: str = DEFAULT_WMON_ADDRESS,
    token_map: Dict = DEFAULT_TOKENS,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    chain_id: int = DEFAULT_CHAIN_ID
) -> dict:

    logs = []
    w3 = None
    account = None
    approve_hash = None
    swap_hash = None

    try:
        # --- Setup --- #
        w3 = connect_to_rpc(rpc_urls)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        router_contract = w3.eth.contract(address=w3.to_checksum_address(router_address), abi=ROUTER_ABI)
        wmon_address_cs = w3.to_checksum_address(wmon_address)

        # Validate token symbol
        token_symbol = token_symbol.upper()
        if token_symbol not in token_map:
            raise ValueError(f"Unsupported token symbol: {token_symbol}")
        token_info = token_map[token_symbol]
        token_address_cs = w3.to_checksum_address(token_info["address"])

        logs.append(f"Starting Bean Swap | Wallet: {wallet_short}")

        # --- Swap Logic --- #
        if direction == 'to_token': # MON -> Token
            amount_mon = amount
            amount_wei = w3.to_wei(amount_mon, 'ether')
            logs.append(format_step('swap', f"MON → {token_symbol} | Amount: {amount_mon}"))

            # Check MON balance
            balance_wei = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_balance(account.address))
            if balance_wei < amount_wei:
                logs.append(format_step('balance', f"✘ Insufficient MON balance: {w3.from_wei(balance_wei, 'ether')} < {amount_mon}"))
                raise ValueError("Insufficient MON balance")
            logs.append(format_step('balance', f"MON Balance: {w3.from_wei(balance_wei, 'ether')}"))

            path = [wmon_address_cs, token_address_cs]
            deadline = int(time.time()) + 600

            swap_func = router_contract.functions.swapExactETHForTokens(0, path, account.address, deadline)

            gas_price = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.gas_price)
            nonce = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_transaction_count(account.address))

            tx = swap_func.build_transaction({
                'from': account.address,
                'value': amount_wei,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': chain_id
            })

        elif direction == 'to_mon': # Token -> MON
            amount_token = amount
            decimals = token_info["decimals"]
            amount_token_wei = int(amount_token * (10**decimals))
            logs.append(format_step('swap', f"{token_symbol} → MON | Amount: {amount_token}"))

            # Check Token balance
            token_contract = w3.eth.contract(address=token_address_cs, abi=ERC20_ABI)
            balance_token_wei = await asyncio.get_event_loop().run_in_executor(None, lambda: token_contract.functions.balanceOf(account.address).call())
            if balance_token_wei < amount_token_wei:
                logs.append(format_step('balance', f"✘ Insufficient {token_symbol} balance: {balance_token_wei / (10**decimals)} < {amount_token}"))
                raise ValueError(f"Insufficient {token_symbol} balance")
            logs.append(format_step('balance', f"{token_symbol} Balance: {balance_token_wei / (10**decimals)}"))

            # Approve Token
            approved, approve_tx_hash_str = await _bean_approve_token(
                w3, account, private_key, token_address_cs, router_contract.address, amount_token_wei, chain_id, logs
            )
            approve_hash = approve_tx_hash_str # Store hash if approval happened
            if not approved:
                raise Exception("Token approval failed")
            # Increment nonce only if approval tx was actually sent
            nonce = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_transaction_count(account.address))

            path = [token_address_cs, wmon_address_cs]
            deadline = int(time.time()) + 600

            swap_func = router_contract.functions.swapExactTokensForETH(amount_token_wei, 0, path, account.address, deadline)

            gas_price = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.gas_price)
            # Use potentially incremented nonce

            tx = swap_func.build_transaction({
                'from': account.address,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': chain_id,
                'value': 0
            })

        else:
            raise ValueError(f"Invalid swap direction: {direction}")

        # Estimate Gas
        try:
            gas_limit = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.estimate_gas(tx))
            tx['gas'] = int(gas_limit * 1.5) # Buffer
            logs.append(format_step('swap', f"Estimated Gas: {gas_limit}, Using: {tx['gas']}"))
        except Exception as est_err:
            fallback_gas = 300000 if direction == 'to_token' else 400000 # Higher fallback for token->ETH
            logs.append(format_step('swap', f"⚠️ Gas estimation failed ({est_err}), using default {fallback_gas}"))
            tx['gas'] = fallback_gas

        # Sign and Send Swap
        logs.append(format_step('swap', "Sending swap transaction..."))
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash_bytes = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.send_raw_transaction(signed_tx.raw_transaction))
        swap_hash = tx_hash_bytes.hex()
        tx_link = f"{explorer_url}{swap_hash}"
        logs.append(format_step('swap', f"Tx Hash: {tx_link}"))

        # Wait for receipt
        receipt = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=180))

        if receipt.status != 1:
            logs.append(format_step('swap', f"✘ Transaction failed: Status {receipt.status}"))
            raise Exception(f"Swap transaction failed: Status {receipt.status}")

        logs.append(format_step('swap', "✔ Swap successful!"))

        # --- Success --- #
        final_message = f"Successfully swapped on Bean Router."
        logs.append(final_message)
        return {
            'success': True,
            'message': final_message,
            'approve_tx_hash': approve_hash,
            'swap_tx_hash': swap_hash,
            'logs': logs
        }

    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"Bean swap failed: {str(e)}"
        logs.append(format_step('error', f"✘ Failed: {error_message}"))
        logs.append(f"TRACEBACK: {tb_str}")
        print(f"ERROR in execute_bean_swap: {error_message}\nTRACEBACK:\n{tb_str}")
        return {
            'success': False,
            'message': error_message,
            'approve_tx_hash': approve_hash,
            'swap_tx_hash': swap_hash,
            'logs': logs
        }
