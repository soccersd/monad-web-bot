import os
import random
import asyncio
from web3 import Web3
from colorama import init # Keep for potential direct testing

init(autoreset=True)

# Constants - Can be overridden by function args
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz/"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_MAGMA_CONTRACT = "0x2c9C959516e9AAEdB2C748224a41249202ca8BE7"
DEFAULT_GAS_LIMIT_STAKE = 500000
DEFAULT_GAS_LIMIT_UNSTAKE = 800000

# --- Helper Functions (from kintsu.py, adapted) ---
def connect_to_rpc(rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to RPC: {rpc_url}")
    return w3

def format_border(text, width=60):
    return f"┌{'─' * (width - 2)}┐\n│ {text:^56} │\n└{'─' * (width - 2)}┘"

def format_step(step, message):
    steps = {'stake': 'Stake MON', 'unstake': 'Unstake gMON'} # Adjusted step name
    step_text = steps.get(step, step.capitalize())
    return f"➤ {step_text:<15} | {message}"

def get_random_amount_wei(w3):
    min_val = 0.01
    max_val = 0.05
    random_amount = random.uniform(min_val, max_val)
    return w3.to_wei(round(random_amount, 4), 'ether')
# ----------------------------------------------------

# Stake MON (Magma) - Refactored
async def execute_magma_stake(
    private_key: str,
    amount_wei: int,
    rpc_url: str = DEFAULT_RPC_URL,
    contract_address: str = DEFAULT_MAGMA_CONTRACT,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    gas_limit: int = DEFAULT_GAS_LIMIT_STAKE
) -> dict:
    logs = []
    try:
        w3 = connect_to_rpc(rpc_url)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        contract_checksum = w3.to_checksum_address(contract_address)

        logs.append(format_border(f"Staking {w3.from_wei(amount_wei, 'ether')} MON (Magma) | {wallet_short}"))

        balance = w3.eth.get_balance(account.address)
        logs.append(format_step('stake', f"Balance: {w3.from_wei(balance, 'ether')} MON"))
        if balance < amount_wei:
            raise ValueError(f"Insufficient balance: {w3.from_wei(balance, 'ether')} < {w3.from_wei(amount_wei, 'ether')}")

        gas_price = w3.eth.gas_price
        tx = {
            'to': contract_checksum,
            'data': '0xd5575982', # Magma stake function selector
            'from': account.address,
            'value': amount_wei,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': w3.eth.chain_id
        }

        logs.append(format_step('stake', 'Sending transaction...'))
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        tx_link = f"{explorer_url}{tx_hash_hex}"

        logs.append(format_step('stake', f"Tx: {tx_link}"))

        receipt = await asyncio.get_event_loop().run_in_executor(
            None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        )

        if receipt.status == 1:
            logs.append(format_step('stake', f"✔ Stake successful!"))
            return {'success': True, 'tx_hash': tx_hash_hex, 'explorer_url': tx_link, 'message': 'Magma stake successful!', 'logs': logs, 'staked_amount_wei': amount_wei}
        else:
            logs.append(format_step('stake', f"✘ Transaction failed: Status {receipt.status}"))
            raise Exception(f"Transaction failed: Status {receipt.status}")

    except ValueError as ve:
        error_message = str(ve)
        logs.append(format_step('stake', f"✘ Failed: {error_message}"))
        return {'success': False, 'tx_hash': None, 'message': error_message, 'logs': logs}
    except Exception as e:
        error_message = f"An unexpected error occurred during Magma stake: {str(e)}"
        logs.append(format_step('stake', f"✘ Failed: {error_message}"))
        tx_hash_hex_on_error = tx_hash.hex() if 'tx_hash' in locals() else None
        return {'success': False, 'tx_hash': tx_hash_hex_on_error, 'message': error_message, 'logs': logs}

# Unstake gMON (Magma) - Refactored
async def execute_magma_unstake(
    private_key: str,
    amount_wei: int, # Amount of gMON (assumed 1:1 for now) to unstake
    rpc_url: str = DEFAULT_RPC_URL,
    contract_address: str = DEFAULT_MAGMA_CONTRACT,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    gas_limit: int = DEFAULT_GAS_LIMIT_UNSTAKE
) -> dict:
    logs = []
    try:
        w3 = connect_to_rpc(rpc_url)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        contract_checksum = w3.to_checksum_address(contract_address)

        logs.append(format_border(f"Unstaking {w3.from_wei(amount_wei, 'ether')} gMON (Magma) | {wallet_short}"))

        # Encode unstake data
        unstake_selector = "0x6fed1ea7"
        encoded_amount = w3.to_hex(amount_wei)[2:].zfill(64)
        data = unstake_selector + encoded_amount

        gas_price = w3.eth.gas_price
        tx = {
            'to': contract_checksum,
            'data': data,
            'from': account.address,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': w3.eth.chain_id
        }

        logs.append(format_step('unstake', 'Sending transaction...'))
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        tx_link = f"{explorer_url}{tx_hash_hex}"

        logs.append(format_step('unstake', f"Tx: {tx_link}"))

        receipt = await asyncio.get_event_loop().run_in_executor(
            None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        )

        if receipt.status == 1:
            logs.append(format_step('unstake', f"✔ Unstake successful!"))
            return {'success': True, 'tx_hash': tx_hash_hex, 'explorer_url': tx_link, 'message': 'Magma unstake successful!', 'logs': logs}
        else:
            logs.append(format_step('unstake', f"✘ Transaction failed: Status {receipt.status}"))
            raise Exception(f"Transaction failed: Status {receipt.status}")

    except Exception as e:
        error_message = f"An unexpected error occurred during Magma unstake: {str(e)}"
        logs.append(format_step('unstake', f"✘ Failed: {error_message}"))
        tx_hash_hex_on_error = tx_hash.hex() if 'tx_hash' in locals() else None
        return {'success': False, 'tx_hash': tx_hash_hex_on_error, 'message': error_message, 'logs': logs}

# --- Removed load_private_keys, run_staking_cycle, run, get_random_delay --- 