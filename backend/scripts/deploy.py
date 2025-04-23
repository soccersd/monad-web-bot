import os
import asyncio
from web3 import Web3
from solcx import compile_source, install_solc
from colorama import init # Keep for direct testing
import traceback # Import traceback
from dotenv import load_dotenv

init(autoreset=True)

# Dotenv for sensitive config
load_dotenv()

# Constants
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz/"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_GAS_LIMIT_DEPLOY = 1500000 # Deployment needs more gas

# ประกาศตัวแปร bytecode ที่ระดับโมดูล สำหรับ import จากไฟล์อื่น
bytecode = None

# Simple Counter Contract Source Code
COUNTER_CONTRACT_SOURCE = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Counter {
    uint public count;
    string public name = "Default Counter"; // Add name
    string public symbol = "DCTR"; // Add symbol

    // Set the initial count and optionally name/symbol
    constructor(uint initialCount, string memory _name, string memory _symbol) {
        count = initialCount;
        if (bytes(_name).length > 0) {
            name = _name;
        }
        if (bytes(_symbol).length > 0) {
            symbol = _symbol;
        }
    }

    // Function to increment the count
    function increment() public {
        count += 1;
    }
}
"""

# --- Helper Functions --- (Copied)
def connect_to_rpc(rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to RPC: {rpc_url}")
    return w3

def format_border(text, width=60):
    line1 = f"╔{'═' * (width - 2)}╗"
    line2 = f"║ {text:^56} ║"
    line3 = f"╚{'═' * (width - 2)}╝"
    return f"{line1}\n{line2}\n{line3}"

def format_step(step, message):
    return f"🔸 {step.capitalize():<15} | {message}"
# --------------------------

# Compile Contract Function
def compile_contract(source_code: str, contract_name: str) -> tuple:
    global bytecode  # Access the global bytecode variable
    try:
        # Ensure solc is installed - Specify a version instead of latest
        target_solc_version = '0.8.20' # Use a specific, compatible version
        print(f"Ensuring solc version {target_solc_version} is installed...")
        install_solc(version=target_solc_version)
        print(f"solc version {target_solc_version} should be installed.")
        compiled_sol = compile_source(source_code, output_values=["abi", "bin"], solc_version=target_solc_version)
        contract_interface = compiled_sol[f'<stdin>:{contract_name}']
        abi = contract_interface['abi']
        contract_bytecode = contract_interface['bin']
        
        # Set the global bytecode variable for importing from other files
        bytecode = contract_bytecode
        
        return abi, contract_bytecode
    except Exception as e:
        raise RuntimeError(f"Failed to compile contract (solc version: {target_solc_version}): {e}")

# Deploy Counter Contract Function - Refactored
async def execute_deploy_counter(
    private_key: str,
    contract_name: str, # Provided by user, used for logs
    contract_symbol: str, # Provided by user, used for logs
    initial_count: int = 0,
    rpc_url: str = DEFAULT_RPC_URL,
    rpc_urls = None, # Added for compatibility
    explorer_url: str = DEFAULT_EXPLORER_URL,
    gas_limit: int = DEFAULT_GAS_LIMIT_DEPLOY
) -> dict:
    logs = []
    tx_hash_hex = None
    contract_address = None
    try:
        # Use rpc_urls if provided (for compatibility with main.py)
        if rpc_urls is not None:
            rpc_url = rpc_urls
            
        # Connect synchronously
        w3 = connect_to_rpc(rpc_url)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."

        log_name = f"{contract_name} ({contract_symbol})"
        logs.append(format_border(f"Deploying {log_name} | {wallet_short}"))

        # Compile the contract in a thread
        logs.append(format_step('compile', "Compiling Counter contract..."))
        try:
             abi, bytecode = await asyncio.to_thread(compile_contract, COUNTER_CONTRACT_SOURCE, 'Counter')
             logs.append(format_step('compile', "✔ Contract compiled successfully."))
        except Exception as compile_error:
            logs.append(format_step('compile', f"✘ Compile Error: {compile_error}"))
            raise compile_error # Re-raise to be caught by outer except

        # Create contract instance
        Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

        # Get chain ID synchronously
        chain_id = w3.eth.chain_id

        # Estimate gas price synchronously
        gas_price = w3.eth.gas_price

        # Build constructor transaction synchronously
        nonce = w3.eth.get_transaction_count(account.address)

        # Print types for debugging
        print(f"[Debug deploy.py] Types before build_transaction:")
        print(f"  initial_count: {type(initial_count)}")
        print(f"  contract_name: {type(contract_name)}")
        print(f"  contract_symbol: {type(contract_symbol)}")
        print(f"  account.address: {type(account.address)}")
        print(f"  gas_limit: {type(gas_limit)}")
        print(f"  gas_price: {type(gas_price)}")
        print(f"  nonce: {type(nonce)}")
        print(f"  chain_id: {type(chain_id)}")
        print(f"  Contract.constructor: {type(Contract.constructor)}")
        print(f"  build_transaction method: {type(Contract.constructor(initial_count, contract_name, contract_symbol).build_transaction)}")

        constructor_tx = Contract.constructor(initial_count, contract_name, contract_symbol).build_transaction(
            {
                'from': account.address,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': chain_id # Use fetched chain_id
            }
        )

        logs.append(format_step('deploy', 'Sending deployment transaction...'))
        # Sign synchronously
        signed_tx = w3.eth.account.sign_transaction(constructor_tx, private_key)
        # Send synchronously
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        tx_link = f"{explorer_url}{tx_hash_hex}"
        logs.append(format_step('deploy', f"Tx Hash: {tx_link}"))

        # Wait for transaction receipt synchronously
        logs.append(format_step('wait', 'Waiting for transaction receipt...'))
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        logs.append(format_step('wait', f"✔ Receipt received (Status: {receipt.status})"))

        if receipt.status == 1:
            contract_address = receipt.contractAddress
            logs.append(format_step('deploy', f"✔ Contract deployed successfully! Address: {contract_address}"))
            return {
                'success': True,
                'tx_hash': tx_hash_hex,
                'explorer_url': tx_link,
                'contract_address': contract_address,
                'message': f'Counter contract {log_name} deployed successfully!',
                'logs': logs
            }
        else:
            logs.append(format_step('deploy', f"✘ Deployment transaction failed: Status {receipt.status}"))
            raise Exception(f"Deployment transaction failed: Status {receipt.status}")

    except Exception as e:
        error_message = f"An unexpected error occurred during deployment: {str(e)}"
        logs.append(format_step('deploy', f"✘ Failed: {error_message}"))
        # Add traceback logging within deploy.py's except block
        tb_str = traceback.format_exc()
        print(f"ERROR in execute_deploy_counter: {error_message}\nTRACEBACK:\n{tb_str}") # Print to backend console
        logs.append(f"TRACEBACK: {tb_str}") # Add traceback to logs for frontend
        return {'success': False, 'tx_hash': tx_hash_hex, 'contract_address': None, 'message': error_message, 'logs': logs}

# --- Removed original functions --- # 