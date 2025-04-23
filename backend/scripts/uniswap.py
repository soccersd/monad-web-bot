import os
import random
import asyncio
import time
from web3 import Web3
from colorama import init # Keep for potential direct testing

init(autoreset=True)

# Constants - Can be overridden
DEFAULT_RPC_URLS = [
    "https://testnet-rpc.monorail.xyz",
    "https://testnet-rpc.monad.xyz",
    "https://monad-testnet.drpc.org"
]
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_UNISWAP_V2_ROUTER_ADDRESS = "0xCa810D095e90Daae6e867c19DF6D9A8C56db2c89"
DEFAULT_WETH_ADDRESS = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701" # WMON

# Default list of supported tokens (can be expanded or passed as arg)
DEFAULT_TOKEN_ADDRESSES = {
    "DAC": "0x0f0bdebf0f83cd1ee3974779bcb7315f9808c714",
    "USDT": "0x88b8e2161dedc77ef4ab7585569d2415a1c1055d",
    "WETH": "0x836047a99e11f376522b447bffb6e3495dd0637c", # Another WETH?
    "MUK": "0x989d38aeed8408452f0273c7d4a17fef20878e62",
    "USDC": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",
    "CHOG": "0xE0590015A873bF326bd645c3E1266d4db41C4E6B"
}

# --- ABIs ---
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}, # Added decimals
]

ROUTER_ABI = [
    {"name": "swapExactETHForTokens", "type": "function", "stateMutability": "payable", "inputs": [{"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]},
    {"name": "swapExactTokensForETH", "type": "function", "stateMutability": "nonpayable", "inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]},
    {"name": "swapExactTokensForTokens", "type": "function", "stateMutability": "nonpayable", "inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "address[]", "name": "path", "type": "address[]"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}]} # Added token-to-token
]

# --- Helper Functions (Adapted) ---
def connect_to_rpc(rpc_urls):
    # Try connecting to multiple RPCs if provided
    urls_to_try = rpc_urls if isinstance(rpc_urls, list) else [rpc_urls]
    for url in urls_to_try:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 60})) # Increased timeout
            if w3.is_connected():
                print(f"Connected to RPC: {url}")
                return w3
            print(f"Failed connection test for {url}")
        except Exception as e:
            print(f"Error connecting to {url}: {e}")
    raise ConnectionError("Could not connect to any provided RPC URL")

def format_border(text, width=60):
    line1 = f"╔{'═' * (width - 2)}╗"
    line2 = f"║ {text:^56} ║"
    line3 = f"╚{'═' * (width - 2)}╝"
    return f"{line1}\n{line2}\n{line3}"

def format_step(step, message):
    steps = {'approve': 'Approve', 'swap': 'Swap'}
    step_text = steps.get(step, step.capitalize())
    return f"🔸 {step_text:<15} | {message}"

async def get_token_decimals(w3, token_address):
    try:
        token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        return await asyncio.to_thread(token_contract.functions.decimals().call)
    except Exception:
        # Default to 18 if decimals call fails (common for ETH/native)
        return 18

async def approve_token_for_router(
    w3: Web3,
    private_key: str,
    account_address: str,
    token_address: str,
    spender_address: str,
    amount_wei: int,
    logs: list
) -> bool:
    token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
    try:
        logs.append(format_step('approve', f'Approving token {token_address} for router...'))
        allowance = await asyncio.to_thread(token_contract.functions.allowance(account_address, spender_address).call)

        if allowance >= amount_wei:
            logs.append(format_step('approve', 'Sufficient allowance already exists.'))
            return True

        # Handle gas_price correctly - check if it's callable
        try:
            # Try as a method first
            gas_price = w3.eth.gas_price()
        except Exception:
            # If that fails, try as a property
            try:
                gas_price = w3.eth.gas_price
            except Exception as e:
                # If both fail, use an estimation instead
                logs.append(format_step('approve', f"Warning: Couldn't get gas price, using default: {e}"))
                gas_price = w3.to_wei('50', 'gwei')  # Use a safe default
                
        nonce = await asyncio.to_thread(w3.eth.get_transaction_count, account_address)

        tx = await asyncio.to_thread(
            token_contract.functions.approve(spender_address, amount_wei).build_transaction, # Use amount_wei directly
            {
                'from': account_address,
                'gas': 150000, # Keep gas limit reasonable
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': w3.eth.chain_id
            }
        )

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await asyncio.to_thread(w3.eth.send_raw_transaction, signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        logs.append(format_step('approve', f"Approval Tx Hash: {tx_hash_hex}"))

        receipt = await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash, timeout=180)

        if receipt.status == 1:
            logs.append(format_step('approve', '✔ Token approved successfully!'))
            return True
        else:
            logs.append(format_step('approve', f'✘ Approval transaction failed: Status {receipt.status}'))
            return False
    except Exception as e:
        logs.append(format_step('approve', f'✘ Approval failed: {str(e)}'))
        return False

# --- Main Swap Execution Function ---

async def execute_uniswap_swap(
    private_key: str,
    token_from_symbol: str,
    token_to_symbol: str,
    amount_str: str, # Amount of token_from to swap, as string
    rpc_urls = DEFAULT_RPC_URLS,
    rpc_url = None, # Added for backward compatibility
    token_list: dict = DEFAULT_TOKEN_ADDRESSES,
    wmon_address: str = DEFAULT_WETH_ADDRESS,
    router_address: str = DEFAULT_UNISWAP_V2_ROUTER_ADDRESS,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    slippage: float = 0.5 # Slippage tolerance in percent
) -> dict:

    logs = []
    tx_hash_hex = None
    w3 = None # Initialize w3

    try:
        # If rpc_url is provided, use it instead of rpc_urls (backward compatibility)
        if rpc_url is not None:
            rpc_urls = rpc_url
            
        w3 = connect_to_rpc(rpc_urls)
        account = w3.eth.account.from_key(private_key)
        account_checksum = account.address
        wallet_short = account_checksum[:8] + "..."

        # Get checksum addresses
        router_checksum = w3.to_checksum_address(router_address)
        wmon_checksum = w3.to_checksum_address(wmon_address)
        token_map = {symbol: w3.to_checksum_address(addr) for symbol, addr in token_list.items()}

        # Find token addresses from symbols - Support both MON and ETH as native token names
        token_from_addr = wmon_checksum if token_from_symbol in ["MON", "ETH"] else token_map.get(token_from_symbol)
        token_to_addr = wmon_checksum if token_to_symbol in ["MON", "ETH"] else token_map.get(token_to_symbol)

        if not token_from_addr or not token_to_addr:
            raise ValueError(f"Invalid token symbol provided: {token_from_symbol} or {token_to_symbol}")

        logs.append(format_border(f"Swapping {amount_str} {token_from_symbol} → {token_to_symbol} | {wallet_short}"))

        # Determine amount in wei
        from_decimals = 18 if token_from_symbol in ["MON", "ETH"] else await get_token_decimals(w3, token_from_addr)
        amount_in_wei = w3.to_wei(amount_str, 'ether') if from_decimals == 18 else int(float(amount_str) * (10**from_decimals))

        # --- Transaction Setup ---
        router_contract = w3.eth.contract(address=router_checksum, abi=ROUTER_ABI)
        deadline = int(time.time()) + 600 # 10 minutes from now
        
        # Handle gas_price correctly - check if it's callable
        try:
            # Try as a method first
            gas_price = w3.eth.gas_price()
        except Exception:
            # If that fails, try as a property
            try:
                gas_price = w3.eth.gas_price
            except Exception as e:
                # If both fail, use an estimation instead
                logs.append(format_step('swap', f"Warning: Couldn't get gas price, using default: {e}"))
                gas_price = w3.to_wei('50', 'gwei')  # Use a safe default
                
        nonce = await asyncio.to_thread(w3.eth.get_transaction_count, account_checksum)
        path = []
        tx_details = {}
        amount_out_min = 0 # TODO: Implement price fetching for accurate min amount

        # Case 1: MON/ETH (Native ETH) to Token
        if token_from_symbol in ["MON", "ETH"]:
            logs.append(format_step('swap', f'Preparing {token_from_symbol} -> {token_to_symbol}'))
            path = [wmon_checksum, token_to_addr]
            tx_func = router_contract.functions.swapExactETHForTokens(
                amount_out_min,
                path,
                account_checksum,
                deadline
            )
            tx_details = {
                'from': account_checksum,
                'value': amount_in_wei,
                'gas': 300000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': w3.eth.chain_id
            }

        # Case 2: Token to MON/ETH (Native ETH)
        elif token_to_symbol in ["MON", "ETH"]:
            logs.append(format_step('swap', f'Preparing {token_from_symbol} -> {token_to_symbol}'))
            # Approve token first
            approved = await approve_token_for_router(w3, private_key, account_checksum, token_from_addr, router_checksum, amount_in_wei, logs)
            if not approved:
                raise Exception("Token approval failed.")
            nonce = await asyncio.to_thread(w3.eth.get_transaction_count, account_checksum) # Get fresh nonce after approval

            path = [token_from_addr, wmon_checksum]
            tx_func = router_contract.functions.swapExactTokensForETH(
                amount_in_wei,
                amount_out_min,
                path,
                account_checksum,
                deadline
            )
            tx_details = {
                'from': account_checksum,
                'gas': 300000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': w3.eth.chain_id
            }

        # Case 3: Token to Token
        else:
            logs.append(format_step('swap', f'Preparing {token_from_symbol} -> {token_to_symbol}'))
            # Approve token first
            approved = await approve_token_for_router(w3, private_key, account_checksum, token_from_addr, router_checksum, amount_in_wei, logs)
            if not approved:
                raise Exception("Token approval failed.")
            nonce = await asyncio.to_thread(w3.eth.get_transaction_count, account_checksum) # Get fresh nonce after approval

            # Simple path: From -> WMON -> To (needs WMON address)
            path = [token_from_addr, wmon_checksum, token_to_addr]
            tx_func = router_contract.functions.swapExactTokensForTokens(
                amount_in_wei,
                amount_out_min,
                path,
                account_checksum,
                deadline
            )
            tx_details = {
                'from': account_checksum,
                'gas': 400000, # Slightly higher gas for token-to-token
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': w3.eth.chain_id
            }

        # --- Build and Send Transaction ---
        tx = await asyncio.to_thread(tx_func.build_transaction, tx_details)

        logs.append(format_step('swap', 'Sending swap transaction...'))
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await asyncio.to_thread(w3.eth.send_raw_transaction, signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        tx_link = f"{explorer_url}{tx_hash_hex}"
        logs.append(format_step('swap', f"Tx Hash: {tx_link}"))

        receipt = await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash, timeout=180)

        if receipt.status == 1:
            logs.append(format_step('swap', '✔ Swap successful!'))
            return {'success': True, 'tx_hash': tx_hash_hex, 'explorer_url': tx_link, 'message': f'Uniswap swap {token_from_symbol} to {token_to_symbol} successful!', 'logs': logs}
        else:
            logs.append(format_step('swap', f'✘ Swap transaction failed: Status {receipt.status}'))
            raise Exception(f"Swap transaction failed: Status {receipt.status}")

    except Exception as e:
        error_message = f"An unexpected error occurred during Uniswap swap: {str(e)}"
        logs.append(format_step('swap', f"✘ Failed: {error_message}"))
        return {'success': False, 'tx_hash': tx_hash_hex, 'message': error_message, 'logs': logs}

# --- Removed original functions like load_private_keys, get_random_eth_amount, run_swap_cycle etc. --- 