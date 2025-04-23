import asyncio
import random
from typing import Dict, List, Optional, Tuple
from eth_account import Account
from eth_account.messages import encode_defunct
from loguru import logger
import aiohttp
from web3 import AsyncWeb3, Web3
from colorama import init, Fore, Style
import traceback
from scripts.bean import _bean_approve_token

# Initialize colorama
init(autoreset=True)

# Constants
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz/"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_FAUCET_ADDRESS = "0xF2B87A9C773f468D4C9d1172b8b2C713f9481b80"
DEFAULT_BMBTC_ADDRESS = "0x0bb0aa6aa3a3fd4f7a43fb5e3d90bf9e6b4ef799"
DEFAULT_SPENDER_ADDRESS = "0x07c4b0db9c020296275dceb6381397ac58bbf5c7"
DEFAULT_CHAIN_ID = 10143
DEFAULT_PERCENT_TO_LEND = [20.0, 30.0]

# Default Market Params (Needs verification if these are stable or should be arguments)
DEFAULT_MARKET_PARAMS = (
    Web3.to_checksum_address("0x01a4b3221e078106f9eb60c5303e3ba162f6a92e"),  # loanToken
    Web3.to_checksum_address(DEFAULT_BMBTC_ADDRESS), # collateralToken (bmBTC)
    Web3.to_checksum_address("0x7c47e0c69fb30fe451da48185c78f0c508b3e5b8"),  # oracle
    Web3.to_checksum_address("0xc2d07bd8df5f33453e9ad4e77436b3eb70a09616"),  # irm
    900000000000000000,  # lltv (0.9 in wei)
)

# ABIs (Keep necessary parts)
TOKEN_ABI = [
    {"inputs": [{"internalType": "address", "name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
]
FAUCET_ABI = [
    {"inputs": [{"internalType": "address", "name": "_tokenAddress", "type": "address"}], "name": "getTokens", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
]
LENDING_ABI = [
    {"type": "function", "name": "supplyCollateral", "inputs": [{"name": "marketParams", "type": "tuple", "components": [{"name": "loanToken", "type": "address"}, {"name": "collateralToken", "type": "address"}, {"name": "oracle", "type": "address"}, {"name": "irm", "type": "address"}, {"name": "lltv", "type": "uint256"}]}, {"name": "assets", "type": "uint256"}, {"name": "onBehalf", "type": "address"}, {"name": "data", "type": "bytes"}], "outputs": [], "stateMutability": "nonpayable"}
]

# Helper function to format step messages for logs
def format_step(step, message):
    steps = {
        'login': 'Bima Login',
        'faucet': 'Get Faucet',
        'approve': 'Approve bmBTC',
        'lend': 'Lend bmBTC',
        'balance': 'Check Balance',
        'error': 'Error'
    }
    step_text = steps.get(step, step.capitalize())
    return f"🔸 {step_text:<18} | {message}"

# --- Refactored Main Execution Function --- #
async def execute_bima_lend_cycle(
        private_key: str,
    # Configurable parameters
    rpc_url: str = DEFAULT_RPC_URL,
    percent_to_lend: Optional[List[float]] = None, # e.g., [20.0, 30.0]
    faucet_address: str = DEFAULT_FAUCET_ADDRESS,
    bmbbtc_address: str = DEFAULT_BMBTC_ADDRESS,
    spender_address: str = DEFAULT_SPENDER_ADDRESS,
    market_params: tuple = DEFAULT_MARKET_PARAMS,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    chain_id: int = DEFAULT_CHAIN_ID,
    attempts: int = 3,
    pause_between_actions: List[int] = [5, 15]
) -> dict:

    logs = []
    w3_async = None
    account = None
    session = None
    faucet_tx_hash = None
    approve_tx_hash = None
    lend_tx_hash = None
    approve_hash = None  # Initialize to None to avoid UnboundLocalError

    # Use provided percentage range or default
    lend_percent_range = percent_to_lend if percent_to_lend and len(percent_to_lend) == 2 else DEFAULT_PERCENT_TO_LEND

    # --- Helper: Get Gas Params --- #
    async def _get_gas_params() -> Dict[str, int]:
        try:
            latest_block = await w3_async.eth.get_block('latest')
            base_fee = latest_block['baseFeePerGas']
            max_priority_fee = await w3_async.eth.max_priority_fee
            return {
                "maxFeePerGas": base_fee + max_priority_fee,
                "maxPriorityFeePerGas": max_priority_fee,
            }
        except Exception as e:
            logs.append(format_step('gas', f"⚠️ EIP-1559 gas params retrieval failed: {e}. Using legacy gas pricing."))
            return {"gasPrice": await w3_async.eth.gas_price}

    # --- Helper: Estimate Gas --- #
    async def _estimate_gas(transaction: dict) -> int:
        try:
            # Make a copy of transaction to avoid modifying the original
            tx_for_estimate = transaction.copy()
            
            # For gas estimation only, we don't need these fields
            if 'maxFeePerGas' in tx_for_estimate:
                del tx_for_estimate['maxFeePerGas']
            if 'maxPriorityFeePerGas' in tx_for_estimate:
                del tx_for_estimate['maxPriorityFeePerGas'] 
            if 'gasPrice' in tx_for_estimate:
                del tx_for_estimate['gasPrice']
            if 'type' in tx_for_estimate:
                del tx_for_estimate['type']
                
            estimated = await w3_async.eth.estimate_gas(tx_for_estimate)
            return int(estimated * 1.2)  # Add 20% buffer
        except Exception as e:
            logs.append(format_step('gas', f"⚠️ Gas estimation failed: {e}. Using default."))
            # Determine a reasonable default based on action
            if 'data' in transaction and transaction['data']:
                # Check if the function signature/name appears in the data string
                # transaction['data'] is already a hex string '0x...'
                if 'supplyCollateral' in transaction['data']: # Removed .hex()
                    return 500000  # Higher gas for supply collateral
                elif 'getTokens' in transaction['data']: # Removed .hex()
                    return 200000  # Faucet gas
                elif 'approve' in transaction['data']: # Removed .hex()
                    return 100000  # Approval gas
            # Generic fallback
            return 300000

    # --- Helper: Build Transaction --- #
    async def _build_transaction(function_call, to_address: str, value: int = 0) -> Dict:
        nonce = await w3_async.eth.get_transaction_count(account.address, "latest")
        
        # Get gas parameters for EIP-1559 transaction
        gas_params = await _get_gas_params()
        
        tx = {
            "from": account.address,
            "to": Web3.to_checksum_address(to_address),
            "data": function_call._encode_transaction_data(),
            "chainId": chain_id,
            "value": value,
            "nonce": nonce,
        }
        
        # Add appropriate gas parameters based on what was returned
        if "maxFeePerGas" in gas_params:
            # EIP-1559 transaction
            tx["type"] = 2
            tx["maxFeePerGas"] = gas_params["maxFeePerGas"]
            tx["maxPriorityFeePerGas"] = gas_params["maxPriorityFeePerGas"]
        else:
            # Legacy transaction
            tx["gasPrice"] = gas_params["gasPrice"]
            
        return tx

    # --- Helper: Send Transaction --- #
    async def _send_transaction(transaction: Dict) -> str:
        signed_txn = Account.sign_transaction(transaction, private_key)
        tx_hash_bytes = await w3_async.eth.send_raw_transaction(signed_txn.raw_transaction)
        logs.append(format_step('send', f"Tx Sent: {tx_hash_bytes.hex()}"))
        receipt = await w3_async.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=180)
        if receipt.status != 1:
            raise Exception(f"Transaction failed on-chain (Status: {receipt.status}) - Hash: {tx_hash_bytes.hex()}")
        logs.append(format_step('send', f"✔ Tx Confirmed: {tx_hash_bytes.hex()}"))
        return tx_hash_bytes.hex()

    # --- Helper: Bima Login (Requires aiohttp session) --- #
    async def _bima_login(session: aiohttp.ClientSession) -> bool:
        for _ in range(attempts):
            try:
                # 1. Get Nonce (tip_info and timestamp)
                async with session.get("https://testnet-api-v1.bima.money/bima/wallet/tip_info") as resp:
                    if resp.status != 200:
                         logs.append(format_step('login', f"Failed to get nonce (Status: {resp.status})"))
                         await asyncio.sleep(random.uniform(*pause_between_actions))
                         continue
                    nonce_data = await resp.json()
                    message_to_sign = nonce_data.get("data", {}).get("tip_info", "")
                    timestamp = nonce_data.get("data", {}).get("timestamp", "")
                if not message_to_sign or not timestamp:
                    logs.append(format_step('login', "Nonce/Timestamp not received from API."))
                    await asyncio.sleep(random.uniform(*pause_between_actions))
                    continue

                # 2. Sign Message
                encoded_msg = encode_defunct(text=message_to_sign)
                signed_msg = Account.sign_message(encoded_msg, private_key=private_key)
                signature = signed_msg.signature.hex()

                # 3. Post Signature
                login_payload = {"signature": "0x" + signature, "timestamp": int(timestamp)}
                async with session.post("https://testnet-api-v1.bima.money/bima/wallet/connect", json=login_payload) as login_resp:
                    if login_resp.status == 200:
                        logs.append(format_step('login', "✔ Login successful!"))
                        return True
                    else:
                        logs.append(format_step('login', f"Login API call failed (Status: {login_resp.status})"))
                        await asyncio.sleep(random.uniform(*pause_between_actions))
                        continue
            except Exception as e:
                logs.append(format_step('login', f"Error during login attempt: {e}"))
                await asyncio.sleep(random.uniform(*pause_between_actions))
        logs.append(format_step('login', f"✘ Login failed after {attempts} attempts."))
        return False

    # --- Main Logic --- #
    try:
        # Use default RPC if None is provided
        rpc_url_to_use = rpc_url if rpc_url is not None else DEFAULT_RPC_URL
        w3_async = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url_to_use))
        if not await w3_async.is_connected():
            raise ConnectionError(f"Could not connect to Async RPC: {rpc_url_to_use}")
        account = Account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        faucet_addr_cs = Web3.to_checksum_address(faucet_address)
        bmbbtc_addr_cs = Web3.to_checksum_address(bmbbtc_address)
        spender_addr_cs = Web3.to_checksum_address(spender_address)
        token_contract = w3_async.eth.contract(address=bmbbtc_addr_cs, abi=TOKEN_ABI)
        faucet_contract = w3_async.eth.contract(address=faucet_addr_cs, abi=FAUCET_ABI)
        lending_contract = w3_async.eth.contract(address=spender_addr_cs, abi=LENDING_ABI)

        logs.append(f"Starting Bima Lend Cycle | Wallet: {wallet_short}")

        # 1. Login to Bima API (Requires aiohttp session)
        async with aiohttp.ClientSession() as session:
            login_success = await _bima_login(session)
            if not login_success:
                logs.append(format_step('login', "⚠️ Login failed but continuing with on-chain operations only"))
                # Don't raise exception, continue with the transaction flow
            
            # 2. Check bmBTC Balance & Use Faucet if needed
            logs.append(format_step('balance', "Checking bmBTC balance..."))
            balance_wei = await token_contract.functions.balanceOf(account.address).call()
            balance_str = f"{Web3.from_wei(balance_wei, 'ether'):.6f}"
            logs.append(format_step('balance', f"bmBTC Balance: {balance_str}"))

            if balance_wei == 0:
                logs.append(format_step('faucet', "Balance is 0. Attempting to get tokens from faucet..."))
                # Check MON balance for gas
                mon_balance = await w3_async.eth.get_balance(account.address)
                if mon_balance < Web3.to_wei(0.01, 'ether'):
                    logs.append(format_step('faucet', f"✘ Insufficient MON for faucet gas: {Web3.from_wei(mon_balance, 'ether')} MON"))
                    # Return failure immediately if no gas for faucet
                    return {
                        'success': False, 'message': 'Insufficient MON for faucet gas',
                        'faucet_tx_hash': None, 'approve_tx_hash': None, 'lend_tx_hash': None, 'logs': logs
                    }

                try:
                    faucet_tx = await _build_transaction(faucet_contract.functions.getTokens(bmbbtc_addr_cs), faucet_addr_cs)
                    faucet_tx['gas'] = await _estimate_gas(faucet_tx)
                    faucet_tx_hash = await _send_transaction(faucet_tx)
                    logs.append(format_step('faucet', f"✔ Faucet tokens claimed! Tx: {faucet_tx_hash}"))
                    await asyncio.sleep(random.uniform(5, 10)) # Wait a bit for balance update

                    # Re-check balance after faucet
                    balance_wei = await token_contract.functions.balanceOf(account.address).call()
                    balance_str = f"{Web3.from_wei(balance_wei, 'ether'):.6f}"
                    logs.append(format_step('balance', f"New bmBTC Balance: {balance_str}"))
                    if balance_wei == 0:
                         # Faucet succeeded on chain but balance is still 0 (unlikely but possible timing issue or faucet bug)
                        logs.append(format_step('faucet', "✘ Faucet transaction succeeded, but balance remains 0."))
                        return {
                            'success': False, 'message': 'Faucet claimed but balance still 0',
                            'faucet_tx_hash': faucet_tx_hash, 'approve_tx_hash': None, 'lend_tx_hash': None, 'logs': logs
                        }
                except Exception as faucet_e:
                    # Catch failure during faucet transaction (e.g., reverted on chain)
                    faucet_fail_msg = f"Faucet transaction failed: {str(faucet_e)}"
                    logs.append(format_step('faucet', f"✘ {faucet_fail_msg}"))
                    # Store the attempted hash if available in the exception message (might not be always)
                    # We know faucet_tx_hash is None because send_transaction raises before assigning it if it fails.
                    return {
                        'success': False, 'message': faucet_fail_msg,
                        'faucet_tx_hash': None, 'approve_tx_hash': None, 'lend_tx_hash': None, 'logs': logs
                    }
            else:
                logs.append(format_step('faucet', "Wallet has bmBTC, skipping faucet."))

            # 3. Calculate Lend Amount & Approve
            lend_percent = random.uniform(lend_percent_range[0], lend_percent_range[1])
            amount_to_lend_wei = int(balance_wei * lend_percent / 100)
            amount_to_lend_str = f"{Web3.from_wei(amount_to_lend_wei, 'ether'):.6f}"
            logs.append(format_step('lend', f"Calculated amount to lend ({lend_percent:.2f}%): {amount_to_lend_str} bmBTC"))

            if amount_to_lend_wei <= 0:
                 logs.append(format_step('lend', "Calculated lend amount is 0. Skipping lend."))
                 # Consider this a success or partial success?
                 return {'success': True, 'message': 'Balance too low to lend.', 'logs': logs}

            try:
                approved, approve_tx_hash_str = await _bean_approve_token( # Reusing approve helper
                    w3_async.eth.get_transaction_count, account, private_key, bmbbtc_addr_cs, spender_addr_cs, amount_to_lend_wei, chain_id, logs
                )
                approve_hash = approve_tx_hash_str
                if not approved:
                    raise Exception("bmBTC approval failed")
            except Exception as approve_error:
                logs.append(format_step('approve', f"Failed to approve tokens: {str(approve_error)}"))
                raise Exception(f"bmBTC approval failed: {str(approve_error)}")
                
            await asyncio.sleep(random.uniform(*pause_between_actions))

            # 4. Supply Collateral (Lend)
            logs.append(format_step('lend', "Supplying collateral..."))
            lend_tx = await _build_transaction(
                lending_contract.functions.supplyCollateral(
                    market_params,
                    amount_to_lend_wei,
                    account.address,
                    b""
                ),
                spender_addr_cs
            )
            lend_tx['gas'] = await _estimate_gas(lend_tx)
            lend_tx_hash = await _send_transaction(lend_tx)
            logs.append(format_step('lend', f"✔ Successfully supplied collateral! Tx: {lend_tx_hash}"))

            # --- Success --- #
            final_message = f"Successfully completed Bima lend cycle ({amount_to_lend_str} bmBTC)."
            logs.append(final_message)
            return {
                'success': True,
                'message': final_message,
                'faucet_tx_hash': faucet_tx_hash,
                'approve_tx_hash': approve_hash,
                'lend_tx_hash': lend_tx_hash,
                'logs': logs
            }
    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"Bima lend cycle failed: {str(e)}"
        logs.append(format_step('error', f"✘ Failed: {error_message}"))
        logs.append(f"TRACEBACK: {tb_str}")
        print(f"ERROR in execute_bima_lend_cycle: {error_message}\nTRACEBACK:\n{tb_str}")
        return {
            'success': False,
            'message': error_message,
            'faucet_tx_hash': faucet_tx_hash,
            'approve_tx_hash': approve_hash,
            'lend_tx_hash': lend_tx_hash,
            'logs': logs
        }

# --- Removed original Class Bima and run function --- #
