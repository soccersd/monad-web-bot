import os
import random
import asyncio
from web3 import Web3
from web3.exceptions import ContractLogicError
# Keep colorama for potential direct script testing, but API won't use colors directly
from colorama import init, Fore, Style

init(autoreset=True) # Initialize colorama

# Constants - Can be overridden by function args
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz/"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_KITSU_STAKING_CONTRACT = "0x07AabD925866E8353407E67C1D157836f7Ad923e"
DEFAULT_CHAIN_ID = 10143 # Monad testnet chain ID

# ABI remains the same
staking_abi = [
    {"name": "stake", "type": "function", "stateMutability": "payable", "inputs": [], "outputs": []},
    {"name": "withdraw", "type": "function", "stateMutability": "nonpayable", "inputs": [{"name": "amount", "type": "uint256"}], "outputs": [{"type": "bool"}]},
    {"name": "withdrawWithSelector", "type": "function", "stateMutability": "nonpayable", "inputs": [{"name": "amount", "type": "uint256"}], "outputs": [{"type": "bool"}], "selector": "0x30af6b2e"}
]

# Helper function to connect to RPC
def connect_to_rpc(rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to RPC: {rpc_url}")
    return w3

# Function to display pretty border (returns string)
def format_border(text, width=60):
    return f"╔{'═' * (width - 2)}╗\n║ {text:^56} ║\n╚{'═' * (width - 2)}╝"

# Function to display step (returns string)
def format_step(step, message):
    steps = {'stake': 'Stake MON', 'unstake': 'Unstake sMON'}
    step_text = steps.get(step, step.capitalize())
    return f"🔸 {step_text:<15} | {message}"

# Generate random amount (0.01 - 0.05 MON) - Keep as helper
def get_random_amount_wei(w3):
    min_val = 0.01
    max_val = 0.05
    random_amount = random.uniform(min_val, max_val)
    return w3.to_wei(round(random_amount, 4), 'ether')

# Stake MON function (Refactored)
async def execute_kitsu_stake(
    private_key: str,
    amount_wei: int,
    rpc_url: str = DEFAULT_RPC_URL,
    contract_address: str = DEFAULT_KITSU_STAKING_CONTRACT,
    explorer_url: str = DEFAULT_EXPLORER_URL
) -> dict:
    logs = []
    try:
        w3 = connect_to_rpc(rpc_url)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=staking_abi)

        logs.append(format_border(f"Staking {w3.from_wei(amount_wei, 'ether')} MON | {wallet_short}"))

        balance = w3.eth.get_balance(account.address)
        logs.append(format_step('stake', f"Balance: {w3.from_wei(balance, 'ether')} MON"))
        if balance < amount_wei:
            raise ValueError(f"Insufficient balance: {w3.from_wei(balance, 'ether')} < {w3.from_wei(amount_wei, 'ether')}")

        # Estimate gas price (using legacy method here for simplicity, consider EIP-1559 later)
        gas_price = w3.eth.gas_price

        tx = contract.functions.stake().build_transaction({
            'from': account.address,
            'value': amount_wei,
            'gas': 500000, # Keep generous gas limit for now
            'gasPrice': gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': w3.eth.chain_id # Get chain ID from connected node
        })

        logs.append(format_step('stake', "Sending stake transaction..."))
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        tx_link = f"{explorer_url}{tx_hash_hex}"

        logs.append(format_step('stake', f"Tx Hash: {tx_link}"))

        # Wait for receipt (consider adding timeout)
        receipt = await asyncio.get_event_loop().run_in_executor(
            None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        )

        if receipt.status == 1:
            logs.append(format_step('stake', "✔ Stake successful!"))
            return {'success': True, 'tx_hash': tx_hash_hex, 'explorer_url': tx_link, 'message': 'Stake successful!', 'logs': logs, 'staked_amount_wei': amount_wei}
        else:
            logs.append(format_step('stake', f"✘ Transaction failed: Status {receipt.status}"))
            raise Exception(f"Transaction failed: Status {receipt.status}")

    except ContractLogicError as cle:
        error_message = f"Contract reverted: {str(cle)}"
        logs.append(format_step('stake', f"✘ Failed: {error_message}"))
        return {'success': False, 'tx_hash': None, 'message': error_message, 'logs': logs}
    except ValueError as ve:
        error_message = str(ve)
        logs.append(format_step('stake', f"✘ Failed: {error_message}"))
        return {'success': False, 'tx_hash': None, 'message': error_message, 'logs': logs}
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logs.append(format_step('stake', f"✘ Failed: {error_message}"))
        # Include tx_hash if available
        tx_hash_hex_on_error = tx_hash.hex() if 'tx_hash' in locals() else None
        return {'success': False, 'tx_hash': tx_hash_hex_on_error, 'message': error_message, 'logs': logs}


# Unstake sMON function (Refactored)
async def execute_kitsu_unstake(
    private_key: str,
    amount_wei: int, # Amount of sMON/underlying MON to unstake (needs contract verification)
    rpc_url: str = DEFAULT_RPC_URL,
    contract_address: str = DEFAULT_KITSU_STAKING_CONTRACT,
    explorer_url: str = DEFAULT_EXPLORER_URL
) -> dict:
    logs = []
    try:
        w3 = connect_to_rpc(rpc_url)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        # Create contract instance using the ABI
        contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=staking_abi)

        # Log based on the assumption it withdraws the underlying MON equivalent
        logs.append(format_border(f"Unstaking {w3.from_wei(amount_wei, 'ether')} MON (amount) | {wallet_short}"))

        # Estimate gas price
        gas_price = w3.eth.gas_price

        # Build transaction using the withdraw function from ABI
        tx = contract.functions.withdraw(amount_wei).build_transaction({
            'from': account.address,
            # 'value' is not needed for withdraw as it's not payable
            'gas': 500000, # Keep generous gas limit
            'gasPrice': gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': w3.eth.chain_id
        })

        logs.append(format_step('unstake', "Sending unstake transaction..."))
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        tx_link = f"{explorer_url}{tx_hash_hex}"

        logs.append(format_step('unstake', f"Tx Hash: {tx_link}"))

        # Wait for receipt
        receipt = await asyncio.get_event_loop().run_in_executor(
             None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        )

        if receipt.status == 1:
            logs.append(format_step('unstake', "✔ Unstake successful!"))
            return {'success': True, 'tx_hash': tx_hash_hex, 'explorer_url': tx_link, 'message': 'Unstake successful!', 'logs': logs}
        else:
             logs.append(format_step('unstake', f"✘ Transaction failed: Status {receipt.status}"))
             # Improve error message slightly
             raise Exception(f"Unstake transaction failed on-chain (Status: {receipt.status})")

    except ContractLogicError as cle:
        error_message = f"Contract reverted during unstake: {str(cle)}"
        logs.append(format_step('unstake', f"✘ Failed: {error_message}"))
        return {'success': False, 'tx_hash': None, 'message': error_message, 'logs': logs}
    except Exception as e:
        error_message = f"An unexpected error occurred during unstake: {str(e)}"
        logs.append(format_step('unstake', f"✘ Failed: {error_message}"))
        tx_hash_hex_on_error = tx_hash.hex() if 'tx_hash' in locals() else None
        return {'success': False, 'tx_hash': tx_hash_hex_on_error, 'message': error_message, 'logs': logs}

# --- Removed load_private_keys, run_staking_cycle, run, get_random_delay ---
# --- get_random_amount_wei is kept as a helper ---
# --- connect_to_rpc is kept as a helper ---
# --- format_border and format_step are kept as helpers returning strings ---

