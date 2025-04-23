import asyncio
import random
from typing import Dict, List, Optional
from eth_account import Account
from web3 import AsyncWeb3, Web3
from loguru import logger
import traceback

# Constants
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz/"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_NFT_CONTRACT_ADDRESS = "0xb33D7138c53e516871977094B249C8f2ab89a4F4"
DEFAULT_CHAIN_ID = 10143

# ERC1155 ABI (Simplified for mint)
ERC1155_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "quantity", "type": "uint256"}],
        "name": "mint",
        "outputs": [],
        "stateMutability": "payable", # It's free, but marked payable in provided ABI
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "mintedCount", # Function to check how many this address has minted
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Helper function to connect to RPC
def connect_to_rpc(rpc_url):
    # Use synchronous Web3 for setup, async for calls within the main function
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
        'mint': 'Mint NFT'
    }
    step_text = steps.get(step, step.capitalize())
    return f"🔸 {step_text:<15} | {message}"

# --- Refactored Main Execution Function --- #
async def execute_lilchogstars_mint(
    private_key: str,
    quantity: int = 1, # Quantity to mint per call (contract seems to only support 1)
    rpc_url: str = DEFAULT_RPC_URL,
    nft_contract_address: str = DEFAULT_NFT_CONTRACT_ADDRESS,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    chain_id: int = DEFAULT_CHAIN_ID,
    target_mints: Optional[int] = None # Optional: Target total mints for this wallet
) -> dict:
    logs = []
    w3_async = None
    account = None
    tx_hash = None

    try:
        # --- Setup --- #
        # Use default RPC URL if none provided and create AsyncWeb3 for interactions
        rpc_url_to_use = rpc_url if rpc_url is not None else DEFAULT_RPC_URL
        w3_async = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url_to_use))
        if not await w3_async.is_connected():
            raise ConnectionError(f"Could not connect to Async RPC: {rpc_url_to_use}")

        account = Account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        contract = w3_async.eth.contract(address=Web3.to_checksum_address(nft_contract_address), abi=ERC1155_ABI)
        logs.append(f"Starting Lilchogstars Mint | Wallet: {wallet_short}")

        # --- Check Current Mint Count --- #
        logs.append(format_step('balance', "Checking current mint count..."))
        current_mints = await contract.functions.mintedCount(account.address).call()
        logs.append(format_step('balance', f"Currently minted: {current_mints}"))

        # --- Determine Mints Needed --- #
        mints_needed = quantity
        if target_mints is not None:
            if current_mints >= target_mints:
                logs.append(format_step('mint', f"✔ Target mints ({target_mints}) already reached ({current_mints}). Skipping."))
                return {
                    'success': True,
                    'message': f'Target mints ({target_mints}) already reached.',
                    'tx_hash': None,
                    'logs': logs
                }
            mints_needed = max(0, target_mints - current_mints)
            # Contract mint function seems to take quantity=1, so we might loop
            # For simplicity with backend, let's assume we only mint 'quantity' (e.g., 1) per task run if needed.
            if current_mints >= quantity: # Simple check if we need to mint at all based on basic quantity
                 logs.append(format_step('mint', f"✔ Already minted {current_mints} (>= requested {quantity}). Skipping."))
                 return {'success': True, 'message': 'Already minted sufficient quantity.', 'tx_hash': None, 'logs': logs}
            mints_to_attempt = 1 # Hardcode to 1 as contract likely takes quantity=1
            logs.append(format_step('mint', f"Target: {target_mints if target_mints else 'N/A'}. Need to mint: {mints_to_attempt} (contract likely mints 1)"))
        else:
            # If no target, just mint the requested quantity (likely 1)
            mints_to_attempt = quantity
            logs.append(format_step('mint', f"Attempting to mint quantity: {mints_to_attempt}"))

        if mints_to_attempt <= 0:
             logs.append(format_step('mint', "No mints needed based on logic."))
             return {'success': True, 'message': 'No mints needed.', 'tx_hash': None, 'logs': logs}

        # --- Prepare Mint Transaction (assuming quantity=1) --- #
        logs.append(format_step('mint', f"Preparing mint transaction (quantity=1)..."))
        latest_block = await w3_async.eth.get_block('latest')
        base_fee = latest_block['baseFeePerGas']
        max_priority_fee = await w3_async.eth.max_priority_fee
        gas_params = {
            "maxFeePerGas": base_fee + max_priority_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }
        nonce = await w3_async.eth.get_transaction_count(account.address)

        mint_tx = await contract.functions.mint(1).build_transaction({
            "from": account.address,
            "value": 0, # Free mint
            "nonce": nonce,
            "type": 2,
            "chainId": chain_id,
            **gas_params,
        })

        # Estimate gas (optional but good practice)
        try:
            gas_estimate = await w3_async.eth.estimate_gas(mint_tx)
            mint_tx['gas'] = int(gas_estimate * 1.2) # Add 20% buffer
            logs.append(format_step('mint', f"Estimated Gas: {gas_estimate}, Using: {mint_tx['gas']}"))
        except Exception as est_err:
            logs.append(format_step('mint', f"⚠️ Gas estimation failed ({est_err}), using default 300000"))
            mint_tx['gas'] = 300000 # Fallback gas limit

        # --- Sign and Send --- #
        logs.append(format_step('mint', "Sending mint transaction..."))
        signed_tx = Account.sign_transaction(mint_tx, private_key)
        tx_hash_bytes = await w3_async.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = tx_hash_bytes.hex()
        tx_link = f"{explorer_url}{tx_hash}"
        logs.append(format_step('mint', f"Tx Hash: {tx_link}"))

        # --- Wait for Receipt --- #
        receipt = await w3_async.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=180)

        if receipt.status != 1:
            logs.append(format_step('mint', f"✘ Mint transaction failed: Status {receipt.status}"))
            raise Exception(f"Mint transaction failed: Status {receipt.status}")

        logs.append(format_step('mint', "✔ Successfully minted!"))

        # --- Success --- #
        final_message = f"Successfully minted Lilchogstars NFT."
        logs.append(final_message)
        return {
            'success': True,
            'message': final_message,
            'tx_hash': tx_hash,
            'logs': logs
        }

    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"Lilchogstars mint failed: {str(e)}"
        logs.append(format_step('error', f"✘ Failed: {error_message}"))
        logs.append(f"TRACEBACK: {tb_str}")
        print(f"ERROR in execute_lilchogstars_mint: {error_message}\nTRACEBACK:\n{tb_str}")
        return {
            'success': False,
            'message': error_message,
            'tx_hash': tx_hash, # Include hash if tx was sent before error
            'logs': logs
        }
