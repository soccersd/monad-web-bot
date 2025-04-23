import os
import asyncio
import random
from web3 import Web3
import traceback

# Constants
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_CHAIN_ID = 10143
DEFAULT_VALUE_MON = 0.005 # Further reduced amount

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
        'balance': 'Check Balance',
        'send': 'Send Mono Tx'
    }
    step_text = steps.get(step, step.capitalize())
    return f"🔸 {step_text:<15} | {message}"

# --- Refactored Main Execution Function --- #
async def execute_mono_transaction(
    private_key: str,
    recipient_address: str,
    rpc_url: str = DEFAULT_RPC_URL,
    value_mon: float = DEFAULT_VALUE_MON,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    chain_id: int = DEFAULT_CHAIN_ID
) -> dict:
    logs = []
    w3 = None
    account = None
    tx_hash = None

    try:
        # --- Setup --- #
        w3 = connect_to_rpc(rpc_url)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."

        # Prepare native MON transfer
        value_wei = w3.to_wei(value_mon, 'ether')

        logs.append(f"Starting Mono Transaction | Wallet: {wallet_short}")

        # --- Check Balance --- #
        logs.append(format_step('balance', "Checking balance..."))
        balance_wei = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_balance(account.address))
        balance_mon_str = f"{w3.from_wei(balance_wei, 'ether'):.6f}"
        logs.append(format_step('balance', f"Balance: {balance_mon_str} MON"))

        required_wei = w3.to_wei(0.01, 'ether') # Buffer for gas only now
        if balance_wei < required_wei:
            logs.append(format_step('send', f"✘ Insufficient balance ({balance_mon_str} MON) for transaction (gas)"))
            raise ValueError(f"Insufficient balance: Have {balance_mon_str}, need ~{w3.from_wei(required_wei, 'ether')}")

        # --- Prepare Transaction --- #
        # Prepare native transfer to provided recipient address
        recipient = w3.to_checksum_address(recipient_address)
        logs.append(format_step('send', f"Preparing native MON transfer to {recipient} (amount: {value_mon} MON)..."))
        gas_price = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.gas_price)
        nonce = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_transaction_count(account.address))

        # Build native transaction dict
        tx = {
            'from': account.address,
            'to': recipient,
            'value': value_wei,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': chain_id
        }

        # Estimate Gas
        try:
            gas_limit = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.estimate_gas(tx))
            tx['gas'] = int(gas_limit * 1.2) # Add buffer
            logs.append(format_step('send', f"Estimated Gas: {gas_limit}, Using: {tx['gas']}"))
        except Exception as est_err:
            logs.append(format_step('send', f"⚠️ Gas estimation failed ({est_err}), using default 500000"))
            tx['gas'] = 500000 # Fallback gas limit

        # --- Sign and Send --- #
        logs.append(format_step('send', "Sending transaction..."))
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash_bytes = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.send_raw_transaction(signed_tx.raw_transaction))
        tx_hash = tx_hash_bytes.hex()
        tx_link = f"{explorer_url}{tx_hash}"
        logs.append(format_step('send', f"Tx Hash: {tx_link}"))

        # --- Wait for Receipt --- #
        receipt = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=180))

        if receipt.status != 1:
            logs.append(format_step('send', f"✘ Transaction failed: Status {receipt.status}"))
            raise Exception(f"Transaction failed: Status {receipt.status}")

        logs.append(format_step('send', "✔ Transaction successful!"))

        # --- Success --- #
        final_message = f"Successfully sent Mono transaction."
        logs.append(final_message)
        return {
            'success': True,
            'message': final_message,
            'tx_hash': tx_hash,
            'logs': logs
        }

    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"Mono transaction failed: {str(e)}"
        logs.append(format_step('error', f"✘ Failed: {error_message}"))
        logs.append(f"TRACEBACK: {tb_str}")
        print(f"ERROR in execute_mono_transaction: {error_message}\nTRACEBACK:\n{tb_str}")
        return {
            'success': False,
            'message': error_message,
            'tx_hash': tx_hash,
            'logs': logs
        }
