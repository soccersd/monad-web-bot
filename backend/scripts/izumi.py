import os
import random
import asyncio
from web3 import Web3
from colorama import init, Fore, Style
import traceback

# Initialize colorama
init(autoreset=True)

# Constants
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz/"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_WMON_CONTRACT = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
DEFAULT_CHAIN_ID = 10143

# ABI for WMON
wmon_abi = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"},
    {"constant": False, "inputs": [{"name": "amount", "type": "uint256"}], "name": "withdraw", "outputs": [], "payable": False, "stateMutability": "nonpayable", "type": "function"},
]

# Helper function to connect to RPC
def connect_to_rpc(rpc_url):
    # Use default RPC if None is provided
    rpc_url_to_use = rpc_url if rpc_url is not None else DEFAULT_RPC_URL
    w3 = Web3(Web3.HTTPProvider(rpc_url_to_use))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to RPC: {rpc_url_to_use}")
    return w3

# Helper function to format step messages for logs
def format_step(step, message):
    steps = {
        'wrap': 'Wrap MON',
        'unwrap': 'Unwrap WMON'
    }
    step_text = steps.get(step, step.capitalize())
    # Remove color codes for logs, keep formatting
    return f"🔸 {step_text:<15} | {message}"

# --- Refactored Main Execution Function --- #
async def execute_izumi_wrap_unwrap(
    private_key: str,
    amount_mon: float,
    rpc_url: str = DEFAULT_RPC_URL,
    wmon_contract_address: str = DEFAULT_WMON_CONTRACT,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    chain_id: int = DEFAULT_CHAIN_ID
) -> dict:
    logs = []
    w3 = None
    account = None
    amount_wei = 0
    wrap_tx_hash = None
    unwrap_tx_hash = None

    try:
        # --- Setup --- #
        w3 = connect_to_rpc(rpc_url)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        contract = w3.eth.contract(address=w3.to_checksum_address(wmon_contract_address), abi=wmon_abi)
        amount_wei = w3.to_wei(amount_mon, 'ether')
        logs.append(f"Starting Izumi Wrap/Unwrap for {amount_mon} MON | Wallet: {wallet_short}")

        # --- Wrap MON --- #
        logs.append(format_step('wrap', f"Preparing to wrap {amount_mon} MON..."))
        gas_price_wrap = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.gas_price)
        nonce_wrap = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_transaction_count(account.address))

        tx_wrap = contract.functions.deposit().build_transaction({
            'from': account.address,
            'value': amount_wei,
            'gas': 50000, # Adjusted gas limit
            'gasPrice': gas_price_wrap,
            'nonce': nonce_wrap,
            'chainId': chain_id
        })

        logs.append(format_step('wrap', 'Sending wrap transaction...'))
        signed_tx_wrap = w3.eth.account.sign_transaction(tx_wrap, private_key)
        tx_hash_wrap_bytes = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.send_raw_transaction(signed_tx_wrap.raw_transaction))
        wrap_tx_hash = tx_hash_wrap_bytes.hex()
        tx_link_wrap = f"{explorer_url}{wrap_tx_hash}"
        logs.append(format_step('wrap', f"Tx Hash: {tx_link_wrap}"))

        receipt_wrap = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash_wrap_bytes, timeout=180))

        if receipt_wrap.status != 1:
            logs.append(format_step('wrap', f"✘ Wrap transaction failed: Status {receipt_wrap.status}"))
            raise Exception(f"Wrap transaction failed: Status {receipt_wrap.status}")
        logs.append(format_step('wrap', "✔ Wrap successful!"))

        # --- Short delay before Unwrap --- #
        delay_sec = random.randint(5, 10)
        logs.append(f"Waiting {delay_sec}s before unwrapping...")
        await asyncio.sleep(delay_sec)

        # --- Unwrap WMON --- #
        logs.append(format_step('unwrap', f"Preparing to unwrap {amount_mon} WMON..."))
        gas_price_unwrap = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.gas_price)
        nonce_unwrap = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_transaction_count(account.address))

        tx_unwrap = contract.functions.withdraw(amount_wei).build_transaction({
            'from': account.address,
            'gas': 60000, # Adjusted gas limit
            'gasPrice': gas_price_unwrap,
            'nonce': nonce_unwrap,
            'chainId': chain_id
        })

        logs.append(format_step('unwrap', 'Sending unwrap transaction...'))
        signed_tx_unwrap = w3.eth.account.sign_transaction(tx_unwrap, private_key)
        tx_hash_unwrap_bytes = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.send_raw_transaction(signed_tx_unwrap.raw_transaction))
        unwrap_tx_hash = tx_hash_unwrap_bytes.hex()
        tx_link_unwrap = f"{explorer_url}{unwrap_tx_hash}"
        logs.append(format_step('unwrap', f"Tx Hash: {tx_link_unwrap}"))

        receipt_unwrap = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash_unwrap_bytes, timeout=180))

        if receipt_unwrap.status != 1:
            logs.append(format_step('unwrap', f"✘ Unwrap transaction failed: Status {receipt_unwrap.status}"))
            raise Exception(f"Unwrap transaction failed: Status {receipt_unwrap.status}")
        logs.append(format_step('unwrap', "✔ Unwrap successful!"))

        # --- Success --- #
        final_message = f"Successfully wrapped and unwrapped {amount_mon} MON via Izumi script logic."
        logs.append(final_message)
        return {
            'success': True,
            'message': final_message,
            'wrap_tx_hash': wrap_tx_hash,
            'unwrap_tx_hash': unwrap_tx_hash,
            'logs': logs
        }

    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"Izumi Wrap/Unwrap failed: {str(e)}"
        logs.append(format_step('error', f"✘ Failed: {error_message}"))
        logs.append(f"TRACEBACK: {tb_str}")
        print(f"ERROR in execute_izumi_wrap_unwrap: {error_message}\nTRACEBACK:\n{tb_str}") # Print to backend console
        return {
            'success': False,
            'message': error_message,
            'wrap_tx_hash': wrap_tx_hash,
            'unwrap_tx_hash': unwrap_tx_hash,
            'logs': logs
        }

# --- Removed original functions: load_private_keys, print_border, print_step, get_random_amount, get_random_delay, wrap_mon, unwrap_mon, run_swap_cycle, run, if __name__ == "__main__" --- #
