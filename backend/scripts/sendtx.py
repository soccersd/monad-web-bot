import os
import random
import asyncio
from web3 import Web3
from colorama import init # Keep for direct testing

init(autoreset=True)

# Constants
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz/"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_GAS_LIMIT_SEND = 40000 # Increased from 21000 for more complex operations

# --- Helper Functions --- (Copied)
def connect_to_rpc(rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to RPC: {rpc_url}")
    return w3

def format_border(text, width=60):
    line1 = f"┌{'─' * (width - 2)}┐"
    line2 = f"│ {text:^56} │"
    line3 = f"└{'─' * (width - 2)}┘"
    return f"{line1}\n{line2}\n{line3}"

def format_step(step, message):
    return f"➤ {step.capitalize():<15} | {message}"

def get_random_amount_wei(w3, min_mon=0.0001, max_mon=0.001):
    random_amount = random.uniform(min_mon, max_mon)
    return w3.to_wei(round(random_amount, 6), 'ether') # Use more precision for small amounts

# --- Send Transaction Function --- Refactored
async def execute_send_mon(
    private_key: str,
    recipient_address: str,
    amount_wei: int,
    rpc_url: str = DEFAULT_RPC_URL,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    gas_limit: int = DEFAULT_GAS_LIMIT_SEND
) -> dict:
    logs = []
    tx_hash_hex = None
    try:
        w3 = connect_to_rpc(rpc_url)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        recipient_checksum = w3.to_checksum_address(recipient_address)

        logs.append(format_border(f"Sending {w3.from_wei(amount_wei, 'ether')} MON | {wallet_short} -> {recipient_checksum[:8]}..." ))

        balance = await asyncio.to_thread(w3.eth.get_balance, account.address)
        logs.append(format_step('send', f"Balance: {w3.from_wei(balance, 'ether')} MON"))

        # Estimate gas price - handle both property and callable cases
        try:
            if callable(w3.eth.gas_price):
                gas_price = await asyncio.to_thread(lambda: w3.eth.gas_price())
            else:
                gas_price = w3.eth.gas_price
        except Exception as gas_err:
            logs.append(format_step('send', f"Error getting gas price: {gas_err}. Using default."))
            gas_price = w3.to_wei('50', 'gwei')
            
        estimated_cost = gas_limit * gas_price

        if balance < (amount_wei + estimated_cost):
            raise ValueError(f"Insufficient balance for amount + gas: {w3.from_wei(balance, 'ether')} < ~{w3.from_wei(amount_wei + estimated_cost, 'ether')}")
        elif balance < amount_wei:
             raise ValueError(f"Insufficient balance: {w3.from_wei(balance, 'ether')} < {w3.from_wei(amount_wei, 'ether')}")

        # Build transaction
        nonce = await asyncio.to_thread(w3.eth.get_transaction_count, account.address)
        tx = {
            'to': recipient_checksum,
            'value': amount_wei,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': w3.eth.chain_id
        }

        logs.append(format_step('send', 'Sending transaction...'))
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await asyncio.to_thread(w3.eth.send_raw_transaction, signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        tx_link = f"{explorer_url}{tx_hash_hex}"
        logs.append(format_step('send', f"Tx Hash: {tx_link}"))

        # Wait for receipt
        receipt = await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash, timeout=180)

        if receipt.status == 1:
            logs.append(format_step('send', "✔ Transaction successful!"))
            return {
                'success': True,
                'tx_hash': tx_hash_hex,
                'explorer_url': tx_link,
                'message': f'Successfully sent {w3.from_wei(amount_wei, "ether")} MON to {recipient_address}',
                'logs': logs
            }
        else:
            logs.append(format_step('send', f"✘ Transaction failed: Status {receipt.status}"))
            # Try to get more information about the failure if possible
            try:
                # Try to simulate the transaction to see if we can get a revert reason
                tx_params = {
                    'from': account.address,
                    'to': recipient_checksum,
                    'value': amount_wei
                }
                w3.eth.call(tx_params)
                # If we reach here, it means no revert reason was provided
                error_message = f"Transaction failed on-chain with status 0, but no revert reason available"
            except Exception as call_err:
                # If eth_call fails, we might get a revert reason
                error_message = f"Transaction failed: {str(call_err)}"
            
            raise Exception(error_message)

    except ValueError as ve:
         error_message = str(ve)
         logs.append(format_step('send', f"✘ Failed: {error_message}"))
         return {'success': False, 'tx_hash': tx_hash_hex, 'message': error_message, 'logs': logs}
    except Exception as e:
        error_message = f"An unexpected error occurred during send: {str(e)}"
        logs.append(format_step('send', f"✘ Failed: {error_message}"))
        return {'success': False, 'tx_hash': tx_hash_hex, 'message': error_message, 'logs': logs}

# --- Removed original run_transaction_cycle, run --- # 