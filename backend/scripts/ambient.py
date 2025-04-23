import asyncio
import random
from typing import Dict, List, Optional, Tuple
from eth_account import Account
from eth_abi import abi
from decimal import Decimal
from loguru import logger
from web3 import AsyncWeb3, Web3
import traceback

# Constants (Use defaults, allow overrides)
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz/"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_AMBIENT_CONTRACT = "0x88B96aF200c8a9c35442C8AC6cd3D22695AaE4F0"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
DEFAULT_POOL_IDX = 36000
RESERVE_FLAGS = 0
TIP = 0
MAX_SQRT_PRICE = 21267430153580247136652501917186561137
MIN_SQRT_PRICE = 65537
DEFAULT_CHAIN_ID = 10143

# Default Tokens (can be customized via params if needed later)
AMBIENT_TOKENS = {
    "usdt": {"address": "0x88b8E2161DEDC77EF4ab7585569D2415a1C1055D", "decimals": 6},
    "usdc": {"address": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea", "decimals": 6},
    "weth": {"address": "0xB5a30b0FDc5EA94A52fDc42e3E9760Cb8449Fb37", "decimals": 18},
    "wbtc": {"address": "0xcf5a6076cfa32686c0Df13aBaDa2b40dec133F1d", "decimals": 8},
    "seth": {"address": "0x836047a99e11F376522B447bffb6e3495Dd0637c", "decimals": 18},
}

# ABIs (Keep necessary parts)
ERC20_ABI = [
    {"inputs": [{"internalType": "address", "name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "owner", "type": "address"}, {"internalType": "address", "name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]
AMBIENT_ABI = [
    {"inputs": [{"internalType": "uint16", "name": "callpath", "type": "uint16"}, {"internalType": "bytes", "name": "cmd", "type": "bytes"}], "name": "userCmd", "outputs": [{"internalType": "bytes", "name": "", "type": "bytes"}], "stateMutability": "payable", "type": "function"}
]

# Helper function to format step messages for logs
def format_step(step, message):
    steps = {
        'balance': 'Check Balance',
        'approve': 'Approve Token',
        'swap': 'Execute Swap'
    }
    step_text = steps.get(step, step.capitalize())
    return f"🔸 {step_text:<15} | {message}"

# --- Main Execution Function --- #
async def execute_ambient_swap(
    private_key: str,
    # Parameters for swap flexibility (add defaults or require from request)
    token_in_symbol: Optional[str] = None, # If None, choose random from balance
    token_out_symbol: Optional[str] = None, # If None, choose random valid pair
    amount_percent: float = 100.0, # Percentage of token_in balance to swap
    # Configuration
    rpc_url: str = DEFAULT_RPC_URL,
    ambient_contract_address: str = DEFAULT_AMBIENT_CONTRACT,
    pool_idx: int = DEFAULT_POOL_IDX,
    token_map: Dict = AMBIENT_TOKENS,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    chain_id: int = DEFAULT_CHAIN_ID,
    attempts: int = 3,
    pause_between_actions: List[int] = [5, 10] # Shorter default pause
) -> Dict:

    logs = []
    w3_async = None
    account = None
    tx_hash = None
    approve_hash = None

    try:
        # --- Setup --- #
        # Use default RPC if None is provided
        rpc_url_to_use = rpc_url if rpc_url is not None else DEFAULT_RPC_URL
        w3_async = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url_to_use))
        if not await w3_async.is_connected():
            raise ConnectionError(f"Could not connect to Async RPC: {rpc_url_to_use}")
            
        account = Account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        router_contract = w3_async.eth.contract(address=Web3.to_checksum_address(ambient_contract_address), abi=AMBIENT_ABI)
        logs.append(f"Starting Ambient Swap | Wallet: {wallet_short}")

        # --- Helper: Get Balances --- #
        async def get_balances() -> List[Tuple[str, float, int]]: # symbol, amount_float, amount_wei
            tokens_with_balance = []
            try:
                native_balance_wei = await w3_async.eth.get_balance(account.address)
                if native_balance_wei > 0:
                    native_amount = float(Web3.from_wei(native_balance_wei, 'ether'))
                    tokens_with_balance.append(("native", native_amount, native_balance_wei))
            except Exception as e:
                 logs.append(format_step('balance', f"⚠️ Failed to get native balance: {e}"))

            for symbol, details in token_map.items():
                try:
                    token_contract = w3_async.eth.contract(
                        address=Web3.to_checksum_address(details["address"]),
                        abi=ERC20_ABI
                    )
                    balance_wei = await token_contract.functions.balanceOf(account.address).call()
                    if balance_wei > 0:
                        amount = float(Decimal(str(balance_wei)) / Decimal(str(10 ** details["decimals"])))
                        if symbol.lower() in ["seth", "weth"] and amount < 0.001: continue
                        tokens_with_balance.append((symbol, amount, balance_wei))
                except Exception as e:
                    logs.append(format_step('balance', f"⚠️ Failed to get balance for {symbol}: {e}"))
            return tokens_with_balance
    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"Ambient swap setup failed: {str(e)}"
        logs.append(format_step('error', f"✘ Failed: {error_message}"))
        logs.append(f"TRACEBACK: {tb_str}")
        print(f"ERROR in execute_ambient_swap: {error_message}\nTRACEBACK:\n{tb_str}")
        return {
            'success': False,
            'message': error_message,
            'approve_tx_hash': None,
            'swap_tx_hash': None,
            'logs': logs
        }

    try:
        # --- Choose Tokens --- #
        balances = await get_balances()
        logs.append(format_step('balance', f"Found balances: {[(s, round(a, 4)) for s, a, w in balances]}"))
        if not balances:
             logs.append(format_step('swap', "❌ No tokens with sufficient balance found."))
             return {'success': False, 'message': "No tokens with balance.", 'logs': logs}

        if token_in_symbol and token_in_symbol != "random":
            chosen_balance = next((b for b in balances if b[0].lower() == token_in_symbol.lower()), None)
            if not chosen_balance:
                 logs.append(format_step('swap', f"❌ Specified token_in '{token_in_symbol}' not found or has 0 balance."))
                 return {'success': False, 'message': f"Token_in '{token_in_symbol}' not found or 0 balance.", 'logs': logs}
            token_in, balance_in_float, balance_in_wei = chosen_balance
        else:
            # Choose random token_in from available balances
            token_in, balance_in_float, balance_in_wei = random.choice(balances)
            logs.append(format_step('swap', f"Randomly selected token_in: {token_in}"))

        # For native tokens, cap the percentage to 90% to ensure gas fees
        original_amount_percent = amount_percent
        if token_in.lower() == "native" and amount_percent > 90.0:
            amount_percent = 90.0
            logs.append(format_step('swap', f"Capping native token swap percent from {original_amount_percent}% to {amount_percent}% to ensure gas fees"))

        if token_out_symbol and token_out_symbol != "random":
            if token_out_symbol.lower() == token_in.lower():
                 logs.append(format_step('swap', f"❌ Specified token_out '{token_out_symbol}' is the same as token_in."))
                 return {'success': False, 'message': "token_out cannot be the same as token_in.", 'logs': logs}
            if token_out_symbol.lower() != "native" and token_out_symbol.lower() not in token_map:
                 logs.append(format_step('swap', f"❌ Specified token_out '{token_out_symbol}' is not supported."))
                 return {'success': False, 'message': f"Unsupported token_out: {token_out_symbol}.", 'logs': logs}
            token_out = token_out_symbol
        else:
            # Choose random token_out different from token_in
            possible_outs = list(token_map.keys()) + ["native"]
            possible_outs = [t for t in possible_outs if t.lower() != token_in.lower()]
            if not possible_outs:
                 logs.append(format_step('swap', f"❌ Cannot determine a valid token_out different from {token_in}."))
                 return {'success': False, 'message': "No valid token_out available.", 'logs': logs}
            token_out = random.choice(possible_outs)
            logs.append(format_step('swap', f"Randomly selected token_out: {token_out}"))

        # --- Calculate Amount --- #
        amount_to_swap_wei = 0
        amount_to_swap_float = 0.0
        if amount_percent >= 100.0:
            amount_to_swap_wei = balance_in_wei
            amount_to_swap_float = balance_in_float
            
            # For native token, reserve some for gas fees
            if token_in.lower() == "native":
                # Reserve approximately 0.01 MON for gas fees
                gas_reserve_wei = w3_async.to_wei(0.05, 'ether')  # Increased to 0.05 MON for safety
                logs.append(format_step('swap', f"Reserving {w3_async.from_wei(gas_reserve_wei, 'ether')} {token_in.upper()} for gas fees"))
                if amount_to_swap_wei > gas_reserve_wei:
                    amount_to_swap_wei -= gas_reserve_wei
                    amount_to_swap_float = float(w3_async.from_wei(amount_to_swap_wei, 'ether'))
                else:
                    logs.append(format_step('swap', f"⚠️ Balance too low to reserve for gas. This will likely fail."))
            
            # Leave dust for sETH/WETH if swapping 100%
            elif token_in.lower() in ["seth", "weth"]:
                dust_amount = random.uniform(0.00001, 0.0001)
                dust_wei = int(Decimal(str(dust_amount)) * Decimal(str(10 ** token_map[token_in.lower()]["decimals"])))
                if amount_to_swap_wei > dust_wei:
                    amount_to_swap_wei -= dust_wei
                    amount_to_swap_float -= dust_amount
                    logs.append(format_step('swap', f"Leaving dust amount for {token_in}: ~{dust_amount:.6f}"))
                else:
                    logs.append(format_step('swap', f"⚠️ Balance too low to leave dust for {token_in}, swapping all."))
        else:
            percentage = Decimal(str(amount_percent)) / Decimal('100')
            amount_to_swap_wei = int(Decimal(str(balance_in_wei)) * percentage)
            amount_to_swap_float = balance_in_float * (amount_percent / 100.0)

        if amount_to_swap_wei <= 0:
             logs.append(format_step('swap', "❌ Calculated swap amount is zero or less."))
             return {'success': False, 'message': "Calculated amount to swap is zero.", 'logs': logs}

        logs.append(format_step('swap', f"Swapping {amount_to_swap_float:.6f} {token_in.upper()} → {token_out.upper()}"))

        # Initialize nonce here so it's always defined
        nonce = await w3_async.eth.get_transaction_count(account.address)
        
        # --- Approve Token (if not native) --- #
        is_native_in = token_in.lower() == "native"
        if not is_native_in:
            token_in_address = Web3.to_checksum_address(token_map[token_in.lower()]["address"])
            token_contract = w3_async.eth.contract(address=token_in_address, abi=ERC20_ABI)
            logs.append(format_step('approve', f"Checking allowance for {token_in.upper()}..."))
            allowance = await token_contract.functions.allowance(account.address, ambient_contract_address).call()
            if allowance < amount_to_swap_wei:
                logs.append(format_step('approve', f"Allowance ({allowance}) < amount ({amount_to_swap_wei}). Approving..."))
                gas_params_approve = await get_gas_params(w3_async)
                nonce_approve = nonce  # Use the previously fetched nonce
                approve_tx = await token_contract.functions.approve(
                    ambient_contract_address, amount_to_swap_wei
                ).build_transaction({
                    'from': account.address,
                    'nonce': nonce_approve,
                    'type': 2,
                    'chainId': chain_id,
                    **gas_params_approve,
                })
                # Estimate gas for approve
                try:
                    gas_est_approve = await w3_async.eth.estimate_gas(approve_tx)
                    approve_tx['gas'] = int(gas_est_approve * 1.2)
                except Exception:
                    approve_tx['gas'] = 100000 # Fallback

                signed_approve_tx = Account.sign_transaction(approve_tx, private_key)
                approve_tx_hash_bytes = await w3_async.eth.send_raw_transaction(signed_approve_tx.raw_transaction)
                approve_hash = approve_tx_hash_bytes.hex()
                approve_link = f"{explorer_url}{approve_hash}"
                logs.append(format_step('approve', f"Approval Tx Sent: {approve_link}"))
                receipt_approve = await w3_async.eth.wait_for_transaction_receipt(approve_tx_hash_bytes, timeout=180)
                if receipt_approve.status != 1:
                    logs.append(format_step('approve', f"✘ Approval failed: Status {receipt_approve.status}"))
                    raise Exception(f"Approval failed: Status {receipt_approve.status}")
                logs.append(format_step('approve', "✔ Approval successful!"))
                # Increment nonce expected for the swap tx
                nonce = nonce_approve + 1
                await asyncio.sleep(random.uniform(pause_between_actions[0], pause_between_actions[1])) # Pause after approve
            else:
                logs.append(format_step('approve', f"✔ Allowance sufficient ({allowance})."))

        # --- Generate Swap Data --- #
        logs.append(format_step('swap', "Generating swap transaction data..."))
        token_address_param = (
            Web3.to_checksum_address(token_map[token_out.lower()]["address"]) if is_native_in
            else Web3.to_checksum_address(token_map[token_in.lower()]["address"])
        )
        # Ensure addresses are checksummed before encoding
        token_address_param = Web3.to_checksum_address(token_address_param)

        encode_data = abi.encode(
            ['address', 'address', 'uint16', 'bool', 'bool', 'uint256', 'uint8', 'uint256', 'uint256', 'uint8'],
            [
                ZERO_ADDRESS, # base
                token_address_param, # quote
                pool_idx, # poolIdx
                is_native_in, # isBuy
                True, # inBaseQty
                amount_to_swap_wei, # qty
                TIP, # tip
                MAX_SQRT_PRICE if is_native_in else MIN_SQRT_PRICE, # limitPrice
                0, # minOut
                RESERVE_FLAGS # reserveFlags
            ]
        )
        # Function selector for userCmd(uint16,bytes)
        # keccak("userCmd(uint16,bytes)")[:4] -> 0xa40f7531
        function_selector = bytes.fromhex("a40f7531")
        # Callpath 1 indicates a swap command
        cmd_params = abi.encode(['uint16', 'bytes'], [1, encode_data])
        tx_data_hex = function_selector.hex() + cmd_params.hex()

        # --- Prepare Swap Transaction --- #
        gas_params_swap = await get_gas_params(w3_async)
        # Use the potentially incremented nonce

        swap_tx = {
            "to": Web3.to_checksum_address(ambient_contract_address),
            "from": account.address,
            "data": "0x" + tx_data_hex,
            "value": amount_to_swap_wei if is_native_in else 0,
            "nonce": nonce,
            "type": 2,
            "chainId": chain_id,
            **gas_params_swap,
        }

        # Estimate Gas with fallback and retry mechanisms
        gas_estimate = 800000  # Default high value
        try:
            gas_estimate = await w3_async.eth.estimate_gas(swap_tx)
            swap_tx['gas'] = int(gas_estimate * 1.5)  # Buffer for swap
            logs.append(format_step('swap', f"Estimated Gas: {gas_estimate}, Using: {swap_tx['gas']}"))
        except Exception as est_err:
            error_msg = str(est_err)
            logs.append(format_step('swap', f"⚠️ Gas estimation failed ({error_msg}), using default 800000"))
            
            # If we get "intrinsic gas greater than limit" error, try with smaller amount
            if "intrinsic gas" in error_msg.lower() and is_native_in:
                # Try with a smaller amount (80% of original)
                smaller_amount = int(amount_to_swap_wei * 0.8)
                logs.append(format_step('swap', f"Trying with reduced amount: {w3_async.from_wei(smaller_amount, 'ether')} {token_in.upper()}"))
                
                # Update swap transaction with smaller amount
                swap_tx['value'] = smaller_amount
                
                # Try to re-estimate gas with smaller amount
                try:
                    gas_estimate = await w3_async.eth.estimate_gas(swap_tx)
                    swap_tx['gas'] = int(gas_estimate * 1.5)
                    logs.append(format_step('swap', f"Re-estimated gas with smaller amount: {gas_estimate}, Using: {swap_tx['gas']}"))
                    # Update the amount for tracking
                    amount_to_swap_wei = smaller_amount
                    amount_to_swap_float = float(w3_async.from_wei(smaller_amount, 'ether'))
                except Exception as retry_est_err:
                    logs.append(format_step('swap', f"⚠️ Gas re-estimation also failed: {str(retry_est_err)}"))
                    swap_tx['gas'] = 800000
            else:
                swap_tx['gas'] = 800000

        # --- Sign and Send Swap --- #
        try:
            logs.append(format_step('swap', "Sending swap transaction..."))
            signed_swap_tx = Account.sign_transaction(swap_tx, private_key)
            tx_hash_bytes = await w3_async.eth.send_raw_transaction(signed_swap_tx.raw_transaction)
            tx_hash = tx_hash_bytes.hex()
            tx_link = f"{explorer_url}{tx_hash}"
            logs.append(format_step('swap', f"Swap Tx Hash: {tx_link}"))

            # --- Wait for Swap Receipt --- #
            receipt_swap = await w3_async.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=180)

            if receipt_swap.status != 1:
                logs.append(format_step('swap', f"✘ Swap transaction failed on-chain with status {receipt_swap.status}"))
                logs.append(format_step('swap', "This is common on testnets due to low liquidity or protocol constraints"))
            else:
                logs.append(format_step('swap', "✔ Swap successful!"))
        except Exception as send_err:
            error_msg = str(send_err)
            # If insufficient balance error, provide more helpful message
            if "insufficient balance" in error_msg.lower() and is_native_in:
                logs.append(format_step('swap', f"✘ Insufficient balance for swap and gas. Try with a smaller amount or percentage."))
                balance_after_swap = await w3_async.eth.get_balance(account.address)
                logs.append(format_step('swap', f"Current balance: {float(w3_async.from_wei(balance_after_swap, 'ether'))} {token_in.upper()}"))
            # Log the error but don't re-raise, continue with partial success
            logs.append(format_step('error', f"✘ Transaction error: {error_msg}"))
            logs.append(format_step('swap', "This is common on testnets due to network/protocol limitations"))

        # Update message based on whether we had a successful tx_hash
        if tx_hash:
            final_message = f"Completed Ambient swap process for {amount_to_swap_float:.6f} {token_in.upper()} → {token_out.upper()}"
            
            # Check if we know the swap actually failed on-chain
            if receipt_swap and receipt_swap.status != 1:
                final_message += " (Note: Transaction was submitted but failed on-chain)"
            
            logs.append(final_message)
            return {
                'success': True,
                'partial': receipt_swap.status != 1 if receipt_swap else True,
                'message': final_message,
                'approve_tx_hash': approve_hash,
                'swap_tx_hash': tx_hash,
                'logs': logs
            }
        else:
            # We didn't even get a transaction hash
            error_message = "Failed to submit Ambient swap transaction"
            logs.append(error_message)
            return {
                'success': False,
                'message': error_message,
                'approve_tx_hash': approve_hash,
                'swap_tx_hash': None,
                'logs': logs
            }
    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"Ambient swap failed: {str(e)}"
        logs.append(format_step('error', f"✘ Failed: {error_message}"))
        logs.append(f"TRACEBACK: {tb_str}")
        print(f"ERROR in execute_ambient_swap: {error_message}\nTRACEBACK:\n{tb_str}")
        return {
            'success': False,
            'message': error_message,
            'approve_tx_hash': approve_hash,
            'swap_tx_hash': tx_hash,
            'logs': logs
        }

# Helper to get gas params (moved outside class)
async def get_gas_params(w3: AsyncWeb3) -> Dict[str, int]:
    latest_block = await w3.eth.get_block('latest')
    base_fee = latest_block['baseFeePerGas']
    max_priority_fee = await w3.eth.max_priority_fee
    return {
        "maxFeePerGas": base_fee + max_priority_fee,
        "maxPriorityFeePerGas": max_priority_fee,
    }
