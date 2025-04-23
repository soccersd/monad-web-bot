import sys
import os
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, create_model, field_validator, root_validator
from typing import List, Dict, Any, Optional, Literal, Union, Annotated
import random
import uuid
from datetime import datetime, timezone
from web3 import Web3
from eth_account import Account
from decimal import Decimal
import traceback

# Add scripts directory to path to allow imports
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts')
sys.path.append(SCRIPTS_DIR)

# Import refactored script functions
import_errors = {}
try:
    from kintsu import execute_kitsu_stake, execute_kitsu_unstake, get_random_amount_wei as kintsu_random, connect_to_rpc as kintsu_connect
except ImportError as e_kintsu:
    import_errors['kintsu'] = str(e_kintsu)

try:
    from magma import execute_magma_stake, execute_magma_unstake, get_random_amount_wei as magma_random, connect_to_rpc as magma_connect
except ImportError as e_magma:
    import_errors['magma'] = str(e_magma)

try:
    from uniswap import execute_uniswap_swap
except ImportError as e_uniswap:
    import_errors['uniswap'] = str(e_uniswap)

try:
    from deploy import execute_deploy_counter
except ImportError as e_deploy:
    import_errors['deploy'] = str(e_deploy)

try:
    from sendtx import execute_send_mon, send_random_wei
except ImportError as e_sendtx:
    import_errors['sendtx'] = str(e_sendtx)

# --- NEW: Import Bebop --- #
try:
    from bebop import execute_bebop_wrap_unwrap
except ImportError as e_bebop:
    import_errors['bebop'] = str(e_bebop)

# --- NEW: Import Izumi --- #
try:
    from izumi import execute_izumi_wrap_unwrap
except ImportError as e_izumi:
    import_errors['izumi'] = str(e_izumi)

# --- NEW: Import Lilchogstars --- #
try:
    from lilchogstars import execute_lilchogstars_mint
except ImportError as e_lilchog:
    import_errors['lilchogstars'] = str(e_lilchog)

# --- NEW: Import Mono --- #
try:
    from mono import execute_mono_transaction
except ImportError as e_mono:
    import_errors['mono'] = str(e_mono)

# --- NEW: Import Rubic --- #
try:
    from rubic import execute_rubic_swap
except ImportError as e_rubic:
    import_errors['rubic'] = str(e_rubic)

# --- NEW: Import Ambient --- #
try:
    from ambient import execute_ambient_swap
except ImportError as e_ambient:
    import_errors['ambient'] = str(e_ambient)

# --- NEW: Import Apriori --- #
try:
    from apriori import execute_apriori_full_cycle
except ImportError as e_apriori:
    import_errors['apriori'] = str(e_apriori)

# --- NEW: Import Bean --- #
try:
    from bean import execute_bean_swap, DEFAULT_RPC_URLS
except ImportError as e_bean:
    import_errors['bean'] = str(e_bean)

# --- NEW: Import Bima --- #
try:
    from bima import execute_bima_lend_cycle
except ImportError as e_bima:
    import_errors['bima'] = str(e_bima)

# Define dummy functions if import failed
def create_dummy_func(script_name, error_msg):
    async def dummy_func(*args, **kwargs):
        print(f"Error: Called dummy function because import failed for {script_name}: {error_msg}")
        return {'success': False, 'message': f'{script_name.capitalize()} script import failed', 'logs': [f'Import Error: {error_msg}']}
    return dummy_func

if 'kintsu' in import_errors:
    print(f"Warning: Failed to import kintsu.py: {import_errors['kintsu']}. Using dummy functions.")
    execute_kitsu_stake = create_dummy_func('kitsu_stake', import_errors['kintsu'])
    execute_kitsu_unstake = create_dummy_func('kitsu_unstake', import_errors['kintsu'])
    # Define other kintsu dummies if needed

if 'magma' in import_errors:
    print(f"Warning: Failed to import magma.py: {import_errors['magma']}. Using dummy functions.")
    execute_magma_stake = create_dummy_func('magma_stake', import_errors['magma'])
    execute_magma_unstake = create_dummy_func('magma_unstake', import_errors['magma'])
    # Define other magma dummies if needed

if 'uniswap' in import_errors:
    print(f"Warning: Failed to import uniswap.py: {import_errors['uniswap']}. Using dummy function.")
    execute_uniswap_swap = create_dummy_func('uniswap_swap', import_errors['uniswap'])

if 'deploy' in import_errors:
    print(f"Warning: Failed to import deploy.py: {import_errors['deploy']}. Using dummy function.")
    execute_deploy_counter = create_dummy_func('deploy_counter', import_errors['deploy'])

if 'sendtx' in import_errors:
    print(f"Warning: Failed to import sendtx.py: {import_errors['sendtx']}. Using dummy functions.")
    execute_send_mon = create_dummy_func('send_mon', import_errors['sendtx'])
    # Define other sendtx dummies if needed

# --- NEW: Assign Bebop Dummy --- #
if 'bebop' in import_errors:
    print(f"Warning: Failed to import bebop.py: {import_errors['bebop']}. Using dummy function.")
    execute_bebop_wrap_unwrap = create_dummy_func('bebop_wrap_unwrap', import_errors['bebop'])

# --- NEW: Assign Izumi Dummy --- #
if 'izumi' in import_errors:
    print(f"Warning: Failed to import izumi.py: {import_errors['izumi']}. Using dummy function.")
    execute_izumi_wrap_unwrap = create_dummy_func('izumi_wrap_unwrap', import_errors['izumi'])

# --- NEW: Assign Lilchogstars Dummy --- #
if 'lilchogstars' in import_errors:
    print(f"Warning: Failed to import lilchogstars.py: {import_errors['lilchogstars']}. Using dummy function.")
    execute_lilchogstars_mint = create_dummy_func('lilchogstars_mint', import_errors['lilchogstars'])

# --- NEW: Assign Mono Dummy --- #
if 'mono' in import_errors:
    print(f"Warning: Failed to import mono.py: {import_errors['mono']}. Using dummy function.")
    execute_mono_transaction = create_dummy_func('mono_transaction', import_errors['mono'])

# --- NEW: Assign Rubic Dummy --- #
if 'rubic' in import_errors:
    print(f"Warning: Failed to import rubic.py: {import_errors['rubic']}. Using dummy function.")
    execute_rubic_swap = create_dummy_func('rubic_swap', import_errors['rubic'])

# --- NEW: Assign Ambient Dummy --- #
if 'ambient' in import_errors:
    print(f"Warning: Failed to import ambient.py: {import_errors['ambient']}. Using dummy function.")
    execute_ambient_swap = create_dummy_func('ambient_swap', import_errors['ambient'])

# --- NEW: Assign Apriori Dummy --- #
if 'apriori' in import_errors:
    print(f"Warning: Failed to import apriori.py: {import_errors['apriori']}. Using dummy function.")
    execute_apriori_full_cycle = create_dummy_func('apriori_full_cycle', import_errors['apriori'])

# --- NEW: Assign Bean Dummy --- #
if 'bean' in import_errors:
    print(f"Warning: Failed to import bean.py: {import_errors['bean']}. Using dummy function.")
    execute_bean_swap = create_dummy_func('bean_swap', import_errors['bean'])
    # Define a default value for DEFAULT_RPC_URLS to avoid NameError
    DEFAULT_RPC_URLS = ["https://rpc.monad.xyz/monad-testnet-iteration-0"]

# --- NEW: Assign Bima Dummy --- #
if 'bima' in import_errors:
    print(f"Warning: Failed to import bima.py: {import_errors['bima']}. Using dummy function.")
    execute_bima_lend_cycle = create_dummy_func('bima_lend_cycle', import_errors['bima'])

# --- Task Status Storage ---
# Simple in-memory storage for demo purposes
# In a real application, consider using a database or Redis
task_status_storage: Dict[str, Dict[str, Any]] = {}

# --- Helper function to update task status and logs ---
def update_task_log(task_id: str, message: str, status: str | None = None, level: str = 'info'):
    """Updates the log and optionally the status for a given task."""
    # Check if task exists before proceeding
    task = task_status_storage.get(task_id)
    if not task:
        print(f"Warning: Task ID {task_id} not found in storage for logging.")
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    # Ensure logs list exists
    if 'logs' not in task or not isinstance(task['logs'], list):
        task['logs'] = []

    log_entry = {"timestamp": timestamp, "level": level, "message": message}
    task['logs'].append(log_entry)

    if status:
        task['status'] = status
        task['last_updated'] = timestamp

    # Optional: Prune old logs if needed
    max_logs = 1000 # Limit logs per task
    if len(task['logs']) > max_logs:
       task['logs'] = task['logs'][-max_logs:]


app = FastAPI(
    title="Monad Testnet Bot API",
    description="API to control and monitor the Monad Testnet Bot.",
    version="0.1.0",
)

# --- CORS Middleware ---
origins = [
    "http://localhost:3000", # Allow frontend origin (React default)
    "http://localhost:3001", # Allow potential alternative frontend port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    # Add other origins if needed (e.g., deployed frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)

# --- Pydantic Models for Request Bodies ---
class BaseBotRequest(BaseModel):
    private_keys: List[str] = Field(..., min_items=1)
    rpc_url: str | None = None # Allow overriding default
    delay_between_keys_seconds: int = Field(default=60, ge=0)
    delay_between_cycles_seconds: int = Field(default=120, ge=0)
    task_description: str | None = None # Optional description for the task

class StakeRequest(BaseBotRequest):
    contract_type: str # e.g., 'kitsu', 'apriori', 'magma'
    amount_mon: float # Amount in MON per transaction
    cycles: int = Field(default=1, ge=1)
    recipient_address: str | None = None # Required only for single mode
    tx_count: int = Field(default=1, ge=1) # Number of transactions per key
    mode: str # 'single' or 'random'

class SwapRequest(BaseBotRequest):
    token_from_symbol: str
    token_to_symbol: str
    amount_str: str # Amount as string to handle decimals
    cycles: int = Field(default=1, ge=1) # For random swaps
    mode: str # 'manual' or 'random'

class DeployRequest(BaseBotRequest):
    contract_name: str
    contract_symbol: str
    cycles: int = Field(default=1, ge=1) # Number of deployments per key

class SendRequest(BaseBotRequest):
    amount_mon: float # Amount in MON per transaction
    tx_count: int = Field(default=1, ge=1) # Number of transactions per key
    mode: str # 'single' or 'random'
    recipient_address: str | None = None # Required only for single mode

# Model for the new private key endpoint
class PrivateKeyRequest(BaseModel):
    private_key: str = Field(..., pattern=r"^0x[0-9a-fA-F]{64}$") # Basic validation

# --- NEW: Bebop Request Model --- #
class BebopRequest(BaseBotRequest):
    amount_mon: float = Field(..., gt=0) # Amount to wrap/unwrap
    # Cycles not really applicable here unless defined differently

# --- NEW: Izumi Request Model --- #
class IzumiRequest(BaseBotRequest):
    amount_mon: float = Field(..., gt=0) # Amount to wrap/unwrap
    # Cycles not applicable here

# --- NEW: Lilchogstars Request Model --- #
class LilchogstarsRequest(BaseBotRequest):
    quantity: int = Field(default=1, gt=0) # Default to minting 1 per task run
    # target_mints: Optional[int] = Field(default=None, gt=0) # Optional: Add later if needed
    # Cycles not really applicable here

# --- NEW: Mono Request Model --- #
# This task uses hardcoded values mostly, so Base might be enough
# Add fields here if you want to make value/data/contract configurable later
class MonoRequest(BaseBotRequest):
    recipient_address: str = Field(default="0x052135aBEc9A037C15554dEC1ca60a5B5aD88e52", description="The recipient wallet address (EOA) for the native MON transfer")
    value_mon: float = Field(default=0.005, gt=0, description="Amount of native MON to send")

# --- NEW: Rubic Request Model --- #
class RubicRequest(BaseBotRequest):
    amount_mon: float = Field(..., gt=0) # Amount of MON to swap
    # Cycles not applicable here for a single swap

# --- NEW: Ambient Request Model --- #
class AmbientRequest(BaseBotRequest):
    # Allow specifying tokens or let the script choose randomly
    token_in_symbol: Optional[str] = Field(default=None) # e.g., "native", "usdc", "random"
    token_out_symbol: Optional[str] = Field(default=None) # e.g., "usdt", "native", "random"
    amount_percent: float = Field(default=100.0, ge=0, le=100.0)
    # Cycles not applicable here

# --- NEW: Apriori Request Model --- #
class AprioriRequest(BaseBotRequest):
    # Options for delays could be added here later
    # delay_before_unstake_sec: Optional[int] = None
    # delay_before_claim_sec: Optional[int] = None
    pass # For now, just use base fields for the full cycle

# --- NEW: Bean Request Model --- #
class BeanRequest(BaseBotRequest):
    direction: Literal['to_token', 'to_mon'] # Specify swap direction
    token_symbol: str # e.g., "USDC", "BEAN"
    amount: float = Field(..., gt=0) # Amount of the input token

    @validator('token_symbol')
    def token_symbol_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError('token_symbol must not be empty')
        # Ideally check against DEFAULT_TOKENS keys here if accessible
        return v.upper()

# --- NEW: Bima Request Model --- #
class BimaRequest(BaseBotRequest):
    percent_to_lend: Optional[List[float]] = Field(
        default=None,
        description="Optional range [min_percent, max_percent] for lending, e.g., [20.0, 30.0]"
    )
    # Cycles not applicable for this structure

    @validator('percent_to_lend')
    def check_percent_range(cls, v):
        if v is not None:
            if len(v) != 2:
                raise ValueError('percent_to_lend must contain exactly two elements: [min, max]')
            if not (0 <= v[0] <= 100 and 0 <= v[1] <= 100):
                raise ValueError('Percentages must be between 0 and 100')
            if v[0] > v[1]:
                raise ValueError('Min percent cannot be greater than max percent')
        return v

# --- Helper Function for Web3 Connection ---
def get_w3_connection(rpc_url: str | None = None) -> Web3:
    """Establishes a Web3 connection."""
    rpc_url_to_use = rpc_url or os.environ.get('DEFAULT_RPC_URL', 'https://testnet-rpc.monad.xyz/')
    w3 = Web3(Web3.HTTPProvider(rpc_url_to_use))
    # Add PoA middleware if needed (Monad Testnet might require this)
    # w3.middleware_onion.inject(geth_poa_middleware, layer=0) # Commented out due to ImportError
    if not w3.is_connected():
        raise HTTPException(status_code=503, detail=f"Could not connect to RPC: {rpc_url_to_use}")
    return w3

# --- Background Task Functions ---

async def run_stake_cycle_task(
    task_id: str, # Added
    request: StakeRequest,
):
    """Background task to run stake/unstake cycles."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background stake task for {len(request.private_keys)} keys (Type: {request.contract_type})...", status='running')
    w3 = None
    try:
        w3 = get_w3_connection(request.rpc_url)
        update_task_log(task_id, f"Connected to RPC: {w3.provider.endpoint_uri}")
    except HTTPException as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"Initial RPC connection failed: {e.detail}\nTraceback:\n{tb_str}", status='failed', level='error')
        return
    except Exception as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"An unexpected error occurred during RPC connection: {e}\nTraceback:\n{tb_str}", status='failed', level='error')
        return

    overall_success = True # Track if any part fails
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        # Note: Address derivation moved to wallet import endpoint
        # We assume the PK is valid if it reached here

        try:
            for cycle in range(request.cycles):
                # Check before starting each cycle
                if task_status_storage.get(task_id, {}).get('stop_requested'):
                    update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                    return # Exit the function

                cycle_prefix = f"{key_prefix} [Cycle {cycle+1}/{request.cycles}]"
                update_task_log(task_id, f"{cycle_prefix} Starting cycle...")

                amount_to_stake_wei = 0
                amount_desc = ""
                if request.amount_mon is not None and request.amount_mon > 0:
                    try:
                        amount_to_stake_wei = w3.to_wei(request.amount_mon, 'ether')
                        amount_desc = f"{request.amount_mon} MON"
                    except Exception as e:
                        update_task_log(task_id, f"{cycle_prefix} Invalid amount_mon: {request.amount_mon} - {e}", level='error')
                        overall_success = False
                        break # Stop processing this key's cycles if amount is bad
                else:
                     # Use random amount - Ensure get_random_amount_wei exists and works
                     try:
                         amount_to_stake_wei = get_random_amount_wei(w3)
                         amount_desc = f"{w3.from_wei(amount_to_stake_wei, 'ether')} MON (Random)"
                     except Exception as e:
                         update_task_log(task_id, f"{cycle_prefix} Error getting random amount: {e}", level='error')
                         overall_success = False
                         break # Stop cycles if random amount fails

                stake_result = {}
                contract_type_lower = request.contract_type.lower()
                update_task_log(task_id, f"{cycle_prefix} Attempting stake: {amount_desc}")

                # --- Select and execute stake function ---
                stake_fn = None
                unstake_fn = None
                if contract_type_lower == 'kitsu':
                    stake_fn = execute_kitsu_stake
                    unstake_fn = execute_kitsu_unstake
                elif contract_type_lower == 'magma':
                    stake_fn = execute_magma_stake
                    unstake_fn = execute_magma_unstake
                elif contract_type_lower == 'apriori':
                    stake_fn = execute_apriori_full_cycle
                    unstake_fn = execute_apriori_full_cycle
                else:
                    stake_result = {'success': False, 'message': f'Unsupported contract type: {request.contract_type}', 'logs': []}

                if stake_fn:
                    try:
                        stake_result = await stake_fn(
                            private_key=pk,
                            amount_wei=amount_to_stake_wei,
                            rpc_urls=w3.provider.endpoint_uri # Use connected URL
                            # Pass other relevant args like explorer_url if needed
                        )
                    except Exception as e:
                         update_task_log(task_id, f"{cycle_prefix} Unexpected error during {contract_type_lower} stake execution: {e}", level='error')
                         stake_result = {'success': False, 'message': f'Runtime error during stake: {e}', 'logs': []}

                # Log results from the script execution
                for log_line in stake_result.get('logs', []):
                    update_task_log(task_id, f"{cycle_prefix} {log_line}") # Add cycle prefix to script logs
                update_task_log(task_id, f"{cycle_prefix} Stake Result: {stake_result.get('message', 'No message')}")


                if stake_result.get('success'):
                    # --- Unstake logic removed --- #
                    # staked_amount_for_unstake = stake_result.get('staked_amount_wei', amount_to_stake_wei)
                    # 
                    # # Wait before unstaking if delay > 0
                    # if request.delay_between_cycles_seconds > 0:
                    #     wait_msg = f"{cycle_prefix} Waiting {request.delay_between_cycles_seconds}s before unstake..."
                    #     update_task_log(task_id, wait_msg)
                    #     await asyncio.sleep(request.delay_between_cycles_seconds)
                    # else:
                    #      update_task_log(task_id, f"{cycle_prefix} No delay specified, proceeding directly to unstake.")
                    # 
                    # 
                    # if unstake_fn:
                    #     unstake_result = {}
                    #     update_task_log(task_id, f"{cycle_prefix} Attempting unstake...")
                    #     try:
                    #         unstake_result = await unstake_fn(
                    #             private_key=pk,
                    #             amount_wei=staked_amount_for_unstake, # Use actual staked amount if available
                    #             rpc_urls=w3.provider.endpoint_uri
                    #         )
                    #     except Exception as e:
                    #         update_task_log(task_id, f"{cycle_prefix} Unexpected error during {contract_type_lower} unstake execution: {e}", level='error')
                    #         unstake_result = {'success': False, 'message': f'Runtime error during unstake: {e}', 'logs': []}
                    # 
                    #     # Log unstake results
                    #     for log_line in unstake_result.get('logs', []):
                    #          update_task_log(task_id, f"{cycle_prefix} {log_line}")
                    #     update_task_log(task_id, f"{cycle_prefix} Unstake Result: {unstake_result.get('message', 'No message')}")
                    # 
                    #     if not unstake_result.get('success'):
                    #          overall_success = False # Mark failure if unstake fails
                    #          update_task_log(task_id, f"{cycle_prefix} Unstake failed, marking task as potentially incomplete.", level='warning')
                    # else:
                    #     # This case should not happen if stake_fn was found, but good for safety
                    #     update_task_log(task_id, f"{cycle_prefix} Unstake function not found for {contract_type_lower}.", level='warning')
                    pass # Stake succeeded, no unstake action needed

                else: # Stake failed
                    overall_success = False # Mark failure if stake fails
                    # update_task_log(task_id, f"{cycle_prefix} Skipping unstake due to stake failure.", level='warning') # No longer relevant
                    # Optional: break cycle? continue?

                # Wait between cycles if not the last cycle and delay > 0
                if cycle < request.cycles - 1 and request.delay_between_cycles_seconds > 0 :
                     # Check before sleeping
                     if task_status_storage.get(task_id, {}).get('stop_requested'):
                         update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                         return # Exit the function
                     wait_msg = f"{cycle_prefix} Waiting {request.delay_between_cycles_seconds}s before next stake cycle..."
                     update_task_log(task_id, wait_msg)
                     await asyncio.sleep(request.delay_between_cycles_seconds)

            # End of cycles loop for one key

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Error processing key cycles: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False # Mark failure

        # Wait between keys if not the last key and delay > 0
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # End of keys loop
    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Stake task finished. Final Status: {final_status}", status=final_status)

async def run_swap_task(
    task_id: str, # Added
    request: SwapRequest,
):
    """Background task to run swap operations."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background swap task for {len(request.private_keys)} keys...", status='running')
    w3 = None
    try:
        w3 = get_w3_connection(request.rpc_url)
        update_task_log(task_id, f"Connected to RPC: {w3.provider.endpoint_uri}")
    except HTTPException as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"Initial RPC connection failed: {e.detail}\nTraceback:\n{tb_str}", status='failed', level='error')
        return
    except Exception as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"An unexpected error occurred during RPC connection: {e}\nTraceback:\n{tb_str}", status='failed', level='error')
        return

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            for cycle in range(request.cycles):
                # Check before starting each cycle
                if task_status_storage.get(task_id, {}).get('stop_requested'):
                    update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                    return # Exit the function

                cycle_prefix = f"{key_prefix} [Cycle {cycle+1}/{request.cycles}]"
                update_task_log(task_id, f"{cycle_prefix} Starting swap cycle...")

                # TODO: Handle random swap mode amount/tokens if needed
                update_task_log(task_id, f"{cycle_prefix} Attempting swap {request.amount_str} {request.token_from_symbol} -> {request.token_to_symbol}")

                swap_result = await execute_uniswap_swap( # Assuming this handles both modes or mode='manual'
                    private_key=pk,
                    token_from_symbol=request.token_from_symbol,
                    token_to_symbol=request.token_to_symbol,
                    amount_str=request.amount_str,
                    rpc_urls=w3.provider.endpoint_uri
                    # Pass other needed params
                )

                for log_line in swap_result.get('logs', []):
                    update_task_log(task_id, f"{cycle_prefix} {log_line}")
                update_task_log(task_id, f"{cycle_prefix} Swap Result: {swap_result.get('message', 'No message')}")

                if not swap_result.get('success'):
                    overall_success = False
                    update_task_log(task_id, f"{cycle_prefix} Swap failed.", level='warning')
                    # Decide whether to break or continue cycles/keys on failure

                # Wait between cycles if applicable
                if cycle < request.cycles - 1 and request.delay_between_cycles_seconds > 0:
                    # Check before sleeping
                    if task_status_storage.get(task_id, {}).get('stop_requested'):
                        update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                        return # Exit the function
                    wait_msg = f"{cycle_prefix} Waiting {request.delay_between_cycles_seconds}s before next cycle..."
                    update_task_log(task_id, wait_msg)
                    await asyncio.sleep(request.delay_between_cycles_seconds)

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Error processing key cycles: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False

        # Wait between keys
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
            # Check before sleeping
            if task_status_storage.get(task_id, {}).get('stop_requested'):
                update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                return # Exit the function
            wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
            update_task_log(task_id, wait_msg)
            await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Swap task finished. Final Status: {final_status}", status=final_status)


async def run_deploy_task(
    task_id: str, # Added
    request: DeployRequest,
):
    """Background task to deploy contracts."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background deploy task for {len(request.private_keys)} keys (Contract: {request.contract_name})...", status='running')
    w3 = None
    try:
        w3 = get_w3_connection(request.rpc_url)
        update_task_log(task_id, f"Connected to RPC: {w3.provider.endpoint_uri}")
    except HTTPException as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"Initial RPC connection failed: {e.detail}\nTraceback:\n{tb_str}", status='failed', level='error')
        return
    except Exception as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"An unexpected error occurred during RPC connection: {e}\nTraceback:\n{tb_str}", status='failed', level='error')
        return

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            for cycle in range(request.cycles): # 'cycles' here means deployments per key
                # Check before starting each cycle (deployment)
                if task_status_storage.get(task_id, {}).get('stop_requested'):
                    update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                    return # Exit the function

                cycle_prefix = f"{key_prefix} [Deployment {cycle+1}/{request.cycles}]"
                update_task_log(task_id, f"{cycle_prefix} Attempting deploy {request.contract_name} ({request.contract_symbol})...")

                deploy_result = await execute_deploy_counter( # Assuming this is the deploy script
                    private_key=pk,
                    rpc_urls=w3.provider.endpoint_uri,
                    contract_name=request.contract_name,
                    contract_symbol=request.contract_symbol
                )

                # Process logs from deploy_result first
                for log_line in deploy_result.get('logs', []):
                    # Avoid logging the traceback again if it was already logged in execute_deploy_counter
                    if "Traceback:" not in str(log_line): # Check if it's a simple message or a dict
                        message_to_log = log_line.get("message", str(log_line)) if isinstance(log_line, dict) else str(log_line)
                        update_task_log(task_id, f"{cycle_prefix} {message_to_log}")
                    else:
                         update_task_log(task_id, f"{cycle_prefix} {str(log_line)}") # Log as is if contains traceback

                update_task_log(task_id, f"{cycle_prefix} Deploy Result: {deploy_result.get('message', 'No message')}")
                if deploy_result.get('contract_address'):
                     update_task_log(task_id, f"{cycle_prefix} Deployed Address: {deploy_result['contract_address']}")


                if not deploy_result.get('success'):
                    overall_success = False
                    update_task_log(task_id, f"{cycle_prefix} Deployment reported failure.", level='warning')
                    # Decide handling on failure - maybe break inner loop?
                    # break

                # Wait between cycles (deployments) if applicable
                if cycle < request.cycles - 1 and request.delay_between_cycles_seconds > 0:
                    # Check before sleeping
                    if task_status_storage.get(task_id, {}).get('stop_requested'):
                        update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                        return # Exit the function
                    wait_msg = f"{cycle_prefix} Waiting {request.delay_between_cycles_seconds}s before next deployment..."
                    update_task_log(task_id, wait_msg)
                    await asyncio.sleep(request.delay_between_cycles_seconds)

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Error processing key deployments: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False
            # Maybe continue to the next key instead of stopping everything?
            # continue

        # Wait between keys
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
            # Check before sleeping
            if task_status_storage.get(task_id, {}).get('stop_requested'):
                update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                return # Exit the function
            wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
            update_task_log(task_id, wait_msg)
            await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Deploy task finished. Final Status: {final_status}", status=final_status)


async def run_send_task(
    task_id: str, # Added
    request: SendRequest,
):
    """Background task to send MON."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background send task for {len(request.private_keys)} keys...", status='running')
    w3 = None
    try:
        w3 = get_w3_connection(request.rpc_url)
        update_task_log(task_id, f"Connected to RPC: {w3.provider.endpoint_uri}")
    except HTTPException as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"Initial RPC connection failed: {e.detail}\nTraceback:\n{tb_str}", status='failed', level='error')
        return
    except Exception as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"An unexpected error occurred during RPC connection: {e}\nTraceback:\n{tb_str}", status='failed', level='error')
        return

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            # Amount validation
            amount_to_send_wei = 0
            try:
                amount_to_send_wei = w3.to_wei(request.amount_mon, 'ether')
            except Exception as e:
                 update_task_log(task_id, f"{key_prefix} Invalid amount_mon: {request.amount_mon} - {e}", level='error')
                 overall_success = False
                 continue # Skip this key if amount is bad

            for tx_num in range(request.tx_count):
                # Check before starting each transaction
                if task_status_storage.get(task_id, {}).get('stop_requested'):
                    update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                    return # Exit the function

                tx_prefix = f"{key_prefix} [Tx {tx_num+1}/{request.tx_count}]"
                update_task_log(task_id, f"{tx_prefix} Starting send transaction...")

                recipient = request.recipient_address # Use specified if in single mode
                if request.mode == 'random':
                    # Generate random recipient - HOW? Need a helper or logic here
                    # recipient = generate_random_address() # Placeholder
                    update_task_log(task_id, f"{tx_prefix} Random recipient mode not implemented yet.", level='warning')
                    recipient = None # Or break/continue

                if not recipient:
                    update_task_log(task_id, f"{tx_prefix} No recipient address available. Skipping send.", level='error')
                    overall_success = False
                    continue # Skip this transaction

                update_task_log(task_id, f"{tx_prefix} Attempting send {request.amount_mon} MON to {recipient}")

                # Assuming execute_send_mon handles the actual sending
                send_result = await execute_send_mon(
                    private_key=pk,
                    recipient_address=recipient,
                    amount_wei=amount_to_send_wei,
                    rpc_urls=w3.provider.endpoint_uri
                )

                for log_line in send_result.get('logs', []):
                    update_task_log(task_id, f"{tx_prefix} {log_line}")
                update_task_log(task_id, f"{tx_prefix} Send Result: {send_result.get('message', 'No message')}")

                if not send_result.get('success'):
                    overall_success = False
                    update_task_log(task_id, f"{tx_prefix} Send failed.", level='warning')
                    # Decide handling on failure

                # Small delay between transactions for the same key, if desired
                # Check before potential sleep (if added later)
                # if task_status_storage.get(task_id, {}).get('stop_requested'):
                #     update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                #     return
                # await asyncio.sleep(1)

            # End of tx loop for one key

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Error processing key transactions: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False

        # Wait between keys
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
            # Check before sleeping
            if task_status_storage.get(task_id, {}).get('stop_requested'):
                update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                return # Exit the function
            wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
            update_task_log(task_id, wait_msg)
            await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Send task finished. Final Status: {final_status}", status=final_status)

# --- NEW: Bebop Background Task --- #
async def run_bebop_task(
    task_id: str,
    request: BebopRequest,
):
    """Background task to wrap and unwrap MON using Bebop script."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background Bebop task for {len(request.private_keys)} keys...", status='running')

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            # Execute the wrap/unwrap sequence for the current key
            result = await execute_bebop_wrap_unwrap(
                private_key=pk,
                amount_mon=request.amount_mon,
                rpc_urls=request.rpc_url # Pass RPC from request if provided
            )

            # Log messages returned from the script
            for log_msg in result.get('logs', []):
                update_task_log(task_id, f"{key_prefix} {log_msg}")

            if not result.get('success'):
                overall_success = False
                update_task_log(task_id, f"{key_prefix} Bebop wrap/unwrap failed: {result.get('message', 'Unknown error')}", level='warning')
                # Decide if we should continue to next key or stop?
                # continue

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Unexpected error during Bebop task execution: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False
            # continue # Maybe continue to next key?

        # Wait between keys if applicable
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Bebop task finished. Final Status: {final_status}", status=final_status)

# --- NEW: Izumi Background Task --- #
async def run_izumi_task(
    task_id: str,
    request: IzumiRequest,
):
    """Background task to wrap and unwrap MON using Izumi script logic."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background Izumi task for {len(request.private_keys)} keys...", status='running')

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            result = await execute_izumi_wrap_unwrap(
                private_key=pk,
                amount_mon=request.amount_mon,
                rpc_url=request.rpc_url
            )

            for log_msg in result.get('logs', []):
                update_task_log(task_id, f"{key_prefix} {log_msg}")

            if not result.get('success'):
                overall_success = False
                update_task_log(task_id, f"{key_prefix} Izumi wrap/unwrap failed: {result.get('message', 'Unknown error')}", level='warning')
                # continue

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Unexpected error during Izumi task execution: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False
            # continue

        # Wait between keys if applicable
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Izumi task finished. Final Status: {final_status}", status=final_status)

# --- NEW: Lilchogstars Background Task --- #
async def run_lilchogstars_task(
    task_id: str,
    request: LilchogstarsRequest,
):
    """Background task to mint Lilchogstars NFTs."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background Lilchogstars Mint task for {len(request.private_keys)} keys...", status='running')

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            result = await execute_lilchogstars_mint(
                private_key=pk,
                quantity=request.quantity,
                rpc_url=request.rpc_url
                # target_mints=request.target_mints # Add if model includes it
            )

            for log_msg in result.get('logs', []):
                update_task_log(task_id, f"{key_prefix} {log_msg}")

            if not result.get('success'):
                overall_success = False
                update_task_log(task_id, f"{key_prefix} Lilchogstars mint failed: {result.get('message', 'Unknown error')}", level='warning')
                # continue

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Unexpected error during Lilchogstars task execution: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False
            # continue

        # Wait between keys if applicable
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Lilchogstars Mint task finished. Final Status: {final_status}", status=final_status)

# --- NEW: Mono Background Task --- #
async def run_mono_task(
    task_id: str,
    request: MonoRequest, # Use the new request model
):
    """Background task to execute the Mono transaction."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background Mono task for {len(request.private_keys)} keys...", status='running')

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            # Execute the transaction for the current key
            result = await execute_mono_transaction(
                private_key=pk,
                recipient_address=request.recipient_address,
                value_mon=request.value_mon,
                rpc_url=request.rpc_url
            )

            for log_msg in result.get('logs', []):
                update_task_log(task_id, f"{key_prefix} {log_msg}")

            if not result.get('success'):
                overall_success = False
                update_task_log(task_id, f"{key_prefix} Mono transaction failed: {result.get('message', 'Unknown error')}", level='warning')
                # continue

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Unexpected error during Mono task execution: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False
            # continue

        # Wait between keys if applicable
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Mono task finished. Final Status: {final_status}", status=final_status)

# --- NEW: Rubic Background Task --- #
async def run_rubic_task(
    task_id: str,
    request: RubicRequest,
):
    """Background task to execute the Rubic swap (MON to USDT)."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background Rubic Swap task for {len(request.private_keys)} keys...", status='running')
    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            result = await execute_rubic_swap(
                private_key=pk,
                amount_mon=request.amount_mon,
                rpc_url=request.rpc_url
            )
            for log_msg in result.get('logs', []):
                update_task_log(task_id, f"{key_prefix} {log_msg}")
            if not result.get('success'):
                overall_success = False
                update_task_log(task_id, f"{key_prefix} Rubic swap failed: {result.get('message', 'Unknown error')}", level='warning')
        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Unexpected error during Rubic task execution: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False

        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Rubic Swap task finished. Final Status: {final_status}", status=final_status)

# --- NEW: Ambient Background Task --- #
async def run_ambient_task(
    task_id: str,
    request: AmbientRequest, # Use the new request model
):
    """Background task to execute the Ambient swap."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background Ambient Swap task for {len(request.private_keys)} keys...", status='running')

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            # Execute the swap for the current key
            result = await execute_ambient_swap(
                private_key=pk,
                token_in_symbol=request.token_in_symbol,
                token_out_symbol=request.token_out_symbol,
                amount_percent=request.amount_percent,
                rpc_url=request.rpc_url
                # Pass other config if needed
            )

            # Check if result is None before accessing it
            if result is None:
                update_task_log(task_id, f"{key_prefix} Ambient swap failed: Function returned None", level='error')
                overall_success = False
                continue
                
            for log_msg in result.get('logs', []):
                update_task_log(task_id, f"{key_prefix} {log_msg}")

            if not result.get('success'):
                overall_success = False
                update_task_log(task_id, f"{key_prefix} Ambient swap failed: {result.get('message', 'Unknown error')}", level='warning')
                # continue

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Unexpected error during Ambient task execution: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False
            # continue

        # Wait between keys if applicable
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Ambient Swap task finished. Final Status: {final_status}", status=final_status)

# --- NEW: Apriori Background Task --- #
async def run_apriori_task(
    task_id: str,
    request: AprioriRequest, # Use the new request model
):
    """Background task to execute the Apriori full stake/unstake/claim cycle."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background Apriori task for {len(request.private_keys)} keys...", status='running')

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            # Execute the full cycle for the current key
            result = await execute_apriori_full_cycle(
                private_key=pk,
                rpc_url=request.rpc_url
                # Pass delay parameters if they are added to the request model
            )

            for log_msg in result.get('logs', []):
                update_task_log(task_id, f"{key_prefix} {log_msg}")

            if not result.get('success'):
                overall_success = False
                update_task_log(task_id, f"{key_prefix} Apriori cycle failed: {result.get('message', 'Unknown error')}", level='warning')
                # continue

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Unexpected error during Apriori task execution: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False
            # continue

        # Wait between keys if applicable
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Apriori task finished. Final Status: {final_status}", status=final_status)

# --- NEW: Bean Background Task --- #
async def run_bean_task(
    task_id: str,
    request: BeanRequest,
):
    """Background task to execute the Bean swap."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background Bean Swap task for {len(request.private_keys)} keys...", status='running')

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            # Execute the swap for the current key
            rpc_list = [request.rpc_url] if request.rpc_url else DEFAULT_RPC_URLS

            result = await execute_bean_swap(
                private_key=pk,
                direction=request.direction,
                token_symbol=request.token_symbol,
                amount=request.amount,
                rpc_urls=rpc_list
            )

            for log_msg in result.get('logs', []):
                update_task_log(task_id, f"{key_prefix} {log_msg}")

            if not result.get('success'):
                overall_success = False
                update_task_log(task_id, f"{key_prefix} Bean swap failed: {result.get('message', 'Unknown error')}", level='warning')
                # continue

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Unexpected error during Bean task execution: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False
            # continue

        # Wait between keys if applicable
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Bean Swap task finished. Final Status: {final_status}", status=final_status)

# --- NEW: Bima Background Task --- #
async def run_bima_task(
    task_id: str,
    request: BimaRequest, # Use the new request model
):
    """Background task to execute the Bima lend cycle."""
    # Initial check
    if task_status_storage.get(task_id, {}).get('stop_requested'):
        update_task_log(task_id, "Task stopping before start.", status='stopped', level='warning')
        return

    update_task_log(task_id, f"Starting background Bima Lend task for {len(request.private_keys)} keys...", status='running')

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        # Check before processing each key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
            return # Exit the function

        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")
        try:
            # Execute the lend cycle for the current key
            result = await execute_bima_lend_cycle(
                private_key=pk,
                rpc_url=request.rpc_url,
                percent_to_lend=request.percent_to_lend # Pass optional percentage
            )

            for log_msg in result.get('logs', []):
                update_task_log(task_id, f"{key_prefix} {log_msg}")

            if not result.get('success'):
                overall_success = False
                update_task_log(task_id, f"{key_prefix} Bima lend cycle failed: {result.get('message', 'Unknown error')}", level='warning')
                # continue

        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"{key_prefix} Unexpected error during Bima task execution: {e}"
            update_task_log(task_id, f"{error_msg}\nTraceback:\n{tb_str}", level='error')
            overall_success = False
            # continue

        # Wait between keys if applicable
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Bima Lend task finished. Final Status: {final_status}", status=final_status)


# --- API Endpoints ---

@app.get("/", tags=["Root"])
async def read_root():
    """Basic API root endpoint."""
    return {"message": "Welcome to the Monad Testnet Bot API"}

# --- Wallet Info Endpoints --- (NEW)

@app.post("/api/v1/get-address-from-key", tags=["Wallet Info"], response_model=Dict[str, str])
async def get_address_from_key(request: PrivateKeyRequest):
    """Derives the public address from a private key."""
    try:
        account = Account.from_key(request.private_key)
        return {"address": account.address}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid private key format.")
    except Exception as e:
        # Catch any other unexpected errors during account generation
        print(f"Error deriving address: {e}") # Log the error server-side
        raise HTTPException(status_code=500, detail=f"Could not derive address: {e}")


@app.get("/api/v1/get-balance/{address}", tags=["Wallet Info"], response_model=Dict[str, str])
async def get_wallet_balance(address: str):
    """Gets the MON balance for a given wallet address."""
    try:
        # Validate address format using Web3
        if not Web3.is_address(address):
             raise HTTPException(status_code=400, detail="Invalid wallet address format.")

        # Use checksum address
        checksum_address = Web3.to_checksum_address(address)

        w3 = get_w3_connection() # Use default RPC

        balance_wei = w3.eth.get_balance(checksum_address)
        # Convert Wei to MON (Ether) using Decimal for precision
        balance_mon = w3.from_wei(balance_wei, 'ether')

        # Return as string for consistent JSON representation of potentially large/small numbers
        return {"address": checksum_address, "balance": str(balance_mon)}

    except HTTPException as e:
        # Re-raise HTTPExceptions (like connection errors from get_w3_connection or invalid address)
        raise e
    except Exception as e:
        # Catch other errors during balance fetching
        print(f"Error fetching balance for {address}: {e}") # Log server-side
        raise HTTPException(status_code=500, detail=f"Could not fetch balance: {e}")

# --- Task Status Endpoints ---

@app.get("/api/v1/tasks", tags=["Tasks"])
async def get_tasks():
    """Retrieves the status and summary of all managed tasks."""
    # Return a copy to avoid modifying the original data structure directly
    return {"tasks": task_status_storage.copy()}


@app.get("/api/v1/tasks/{task_id}", tags=["Tasks"])
async def get_task_status(task_id: str):
    """Retrieves the detailed status and logs for a specific task."""
    task = task_status_storage.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

# --- NEW: Stop Task Endpoint ---
@app.post("/api/v1/stop-task/{task_id}", tags=["Tasks"])
async def stop_task(task_id: str):
    """Requests a running or pending task to stop."""
    task = task_status_storage.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    current_status = task.get("status")
    if current_status not in ["running", "pending"]:
        raise HTTPException(status_code=400, detail=f"Task is not in a stoppable state (current: {current_status})")

    if task.get("stop_requested"):
        return {"message": "Task stop already requested.", "task_id": task_id}

    # Set the flag and update status
    task["stop_requested"] = True
    update_task_log(task_id, "Stop request received by user.", status='stopping', level='info')

    return {"message": "Task stop request sent.", "task_id": task_id}


# --- Bot Action Endpoints ---

@app.post("/api/v1/start-stake-cycle", tags=["Bot Actions"])
async def start_stake_bot(request: StakeRequest, background_tasks: BackgroundTasks):
    """Starts the stake/unstake bot cycles in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Stake Cycle ({request.contract_type})"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "stake", # Add type
        "config": request.model_dump(exclude={'private_keys'}), # Store config excluding sensitive data
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_stake_cycle_task, task_id, request)
    return {"message": "Stake bot cycle initiated in background.", "task_id": task_id}


@app.post("/api/v1/start-swap", tags=["Bot Actions"])
async def start_swap_bot(request: SwapRequest, background_tasks: BackgroundTasks):
    """Starts swap operations in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Swap ({request.token_from_symbol} -> {request.token_to_symbol})"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "swap",
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_swap_task, task_id, request)
    return {"message": "Swap operations initiated in background.", "task_id": task_id}


@app.post("/api/v1/start-deploy", tags=["Bot Actions"])
async def start_deploy_bot(request: DeployRequest, background_tasks: BackgroundTasks):
    """Starts contract deployment operations in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Deploy ({request.contract_name})"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "deploy",
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_deploy_task, task_id, request)
    return {"message": "Contract deployment initiated in background.", "task_id": task_id}


@app.post("/api/v1/start-send", tags=["Bot Actions"])
async def start_send_bot(request: SendRequest, background_tasks: BackgroundTasks):
    """Starts MON sending operations in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Send MON ({request.mode})"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "send",
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_send_task, task_id, request)
    return {"message": "MON sending initiated in background.", "task_id": task_id}

# --- NEW: Bebop API Endpoint --- #
@app.post("/api/v1/start-bebop", tags=["Bot Actions"])
async def start_bebop_bot(request: BebopRequest, background_tasks: BackgroundTasks):
    """Starts Bebop MON wrap/unwrap operations in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Bebop Wrap/Unwrap ({request.amount_mon} MON)"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "bebop", # Add type
        "config": request.model_dump(exclude={'private_keys'}), # Store config
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_bebop_task, task_id, request)
    return {"message": "Bebop wrap/unwrap task initiated in background.", "task_id": task_id}

# --- NEW: Izumi API Endpoint --- #
@app.post("/api/v1/start-izumi", tags=["Bot Actions"])
async def start_izumi_bot(request: IzumiRequest, background_tasks: BackgroundTasks):
    """Starts Izumi MON wrap/unwrap operations in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Izumi Wrap/Unwrap ({request.amount_mon} MON)"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "izumi", # Add type
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_izumi_task, task_id, request)
    return {"message": "Izumi wrap/unwrap task initiated in background.", "task_id": task_id}

# --- NEW: Lilchogstars API Endpoint --- #
@app.post("/api/v1/start-lilchogstars", tags=["Bot Actions"])
async def start_lilchogstars_bot(request: LilchogstarsRequest, background_tasks: BackgroundTasks):
    """Starts Lilchogstars NFT minting in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Lilchogstars Mint (Qty: {request.quantity})"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "lilchogstars", # Add type
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_lilchogstars_task, task_id, request)
    return {"message": "Lilchogstars mint task initiated in background.", "task_id": task_id}

# --- NEW: Mono API Endpoint --- #
@app.post("/api/v1/start-mono", tags=["Bot Actions"])
async def start_mono_bot(request: MonoRequest, background_tasks: BackgroundTasks):
    """Starts the Mono transaction task in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Mono Transaction"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "mono", # Add type
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_mono_task, task_id, request)
    return {"message": "Mono transaction task initiated in background.", "task_id": task_id}

# --- NEW: Rubic API Endpoint --- #
@app.post("/api/v1/start-rubic", tags=["Bot Actions"])
async def start_rubic_bot(request: RubicRequest, background_tasks: BackgroundTasks):
    """Starts the Rubic swap (MON to USDT) task in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Rubic Swap ({request.amount_mon} MON -> USDT)"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "rubic",
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_rubic_task, task_id, request)
    return {"message": "Rubic swap task initiated in background.", "task_id": task_id}

# --- NEW: Ambient API Endpoint --- #
@app.post("/api/v1/start-ambient", tags=["Bot Actions"])
async def start_ambient_bot(request: AmbientRequest, background_tasks: BackgroundTasks):
    """Starts the Ambient swap task in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Ambient Swap ({request.token_in_symbol} -> {request.token_out_symbol})"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "ambient", # Add type
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_ambient_task, task_id, request)
    return {"message": "Ambient swap task initiated in background.", "task_id": task_id}

# --- NEW: Apriori API Endpoint --- #
@app.post("/api/v1/start-apriori", tags=["Bot Actions"])
async def start_apriori_bot(request: AprioriRequest, background_tasks: BackgroundTasks):
    """Starts the Apriori full cycle task in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Apriori Full Cycle"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "apriori", # Add type
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_apriori_task, task_id, request)
    return {"message": "Apriori full cycle task initiated in background.", "task_id": task_id}

# --- NEW: Bean API Endpoint --- #
@app.post("/api/v1/start-bean", tags=["Bot Actions"])
async def start_bean_bot(request: BeanRequest, background_tasks: BackgroundTasks):
    """Starts the Bean swap task in the background."""
    task_id = str(uuid.uuid4())
    swap_dir = "MON->Token" if request.direction == 'to_token' else f"{request.token_symbol}->MON"
    desc = request.task_description or f"Bean Swap ({swap_dir}: {request.amount})"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "bean",
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_bean_task, task_id, request)
    return {"message": "Bean swap task initiated in background.", "task_id": task_id}

# --- NEW: Bima API Endpoint --- #
@app.post("/api/v1/start-bima", tags=["Bot Actions"])
async def start_bima_bot(request: BimaRequest, background_tasks: BackgroundTasks):
    """Starts the Bima lend cycle task in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Bima Lend Cycle ({request.percent_to_lend})"
    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "bima",
        "config": request.model_dump(exclude={'private_keys'}),
        "logs": []
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_bima_task, task_id, request)
    return {"message": "Bima lend cycle task initiated in background.", "task_id": task_id}

# --- NEW: Pydantic Models for Multi-Step Workflow ---

# Define Config models for each step type (excluding BaseBotRequest fields)
class DelayStepConfig(BaseModel):
    duration_seconds: int = Field(..., ge=1, description="Duration to wait in seconds")

class StakeStepConfig(StakeRequest):
    # Exclude fields managed by the main request or step runner
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True) # Delay between cycles within a single key might be handled differently or removed
    task_description: Optional[str] = Field(None, exclude=True)
    # Add specific fields required only for stake step config
    contract_type: str # Keep required fields
    amount_mon: float
    cycles: Optional[int] = Field(default=1) # Cycles might now mean iterations *within* this step for a single key
    recipient_address: Optional[str] = None
    tx_count: Optional[int] = Field(default=1)
    mode: Optional[str] = None # Optional now? Or fixed per step?

class SwapStepConfig(SwapRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    # Add specific fields required only for swap step config
    token_from_symbol: str
    token_to_symbol: str
    amount_str: str
    cycles: Optional[int] = Field(default=1)
    mode: Optional[str] = None

class DeployStepConfig(DeployRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    # Add specific fields required only for deploy step config
    contract_name: str
    contract_symbol: str
    cycles: Optional[int] = Field(default=1)

class SendStepConfig(SendRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    # Add specific fields required only for send step config
    amount_mon: float
    tx_count: Optional[int] = Field(default=1)
    mode: str # Keep mode if needed for random recipient generation within step
    recipient_address: Optional[str] = None # Required only for single mode

class BebopStepConfig(BebopRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    amount_mon: float

class IzumiStepConfig(IzumiRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    amount_mon: float

class LilchogstarsStepConfig(LilchogstarsRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    quantity: int

class MonoStepConfig(MonoRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    recipient_address: str
    value_mon: float

class RubicStepConfig(RubicRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    amount_mon: float

class AmbientStepConfig(AmbientRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    token_in_symbol: Optional[str]
    token_out_symbol: Optional[str]
    amount_percent: float

class AprioriStepConfig(AprioriRequest): # Assuming Apriori cycle takes no specific config for now
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)

class BeanStepConfig(BeanRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    direction: Literal['to_token', 'to_mon']
    token_symbol: str
    amount: float

class BimaStepConfig(BimaRequest):
    private_keys: Optional[List[str]] = Field(None, exclude=True)
    rpc_url: Optional[str] = Field(None, exclude=True)
    delay_between_keys_seconds: Optional[int] = Field(None, exclude=True)
    delay_between_cycles_seconds: Optional[int] = Field(None, exclude=True)
    task_description: Optional[str] = Field(None, exclude=True)
    percent_to_lend: Optional[List[float]]

# Use a discriminated union for the config based on the 'type' field
StepConfig = Annotated[
    Union[
        DelayStepConfig, StakeStepConfig, SwapStepConfig, DeployStepConfig, SendStepConfig,
        BebopStepConfig, IzumiStepConfig, LilchogstarsStepConfig, MonoStepConfig,
        RubicStepConfig, AmbientStepConfig, AprioriStepConfig, BeanStepConfig, BimaStepConfig
    ],
    Field(discriminator="type") # Pydantic v2 uses discriminator on the Union
]


# Define the Step model
class Step(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal[
        'delay', 'stake', 'swap', 'deploy', 'send', 'bebop', 'izumi',
        'lilchogstars', 'mono', 'rubic', 'ambient', 'apriori', 'bean', 'bima'
    ]
    config: Dict[str, Any] # Store config as dict for now, validation happens later

    # We need a way to validate config based on type during request parsing,
    # Pydantic's discriminated unions might handle this if structured correctly,
    # or we need a root validator. Let's try simple dict first and validate in task runner.

# Define the main request model for multi-step workflows
class MultiStepWorkflowRequest(BaseModel):
    private_keys: List[str] = Field(..., min_items=1)
    rpc_url: Optional[str] = None
    task_description: Optional[str] = "Multi-Step Workflow"
    delay_between_keys_seconds: int = Field(default=60, ge=0)
    steps: List[Step] = Field(..., min_items=1)


# --- NEW: Background Task Function for Multi-Step Workflow ---
async def run_multi_step_task(
    task_id: str,
    request: MultiStepWorkflowRequest,
):
    """Background task to run a sequence of steps for multiple keys."""
    desc = request.task_description or f"Multi-Step Task ({len(request.steps)} steps)"
    update_task_log(task_id, f"Starting background task: {desc} for {len(request.private_keys)} keys...", status='running')

    w3 = None
    try:
        w3 = get_w3_connection(request.rpc_url)
        update_task_log(task_id, f"Connected to RPC: {w3.provider.endpoint_uri}")
        rpc_to_use = w3.provider.endpoint_uri
    except HTTPException as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"Initial RPC connection failed: {e.detail}\\nTraceback:\\n{tb_str}", status='failed', level='error')
        return
    except Exception as e:
        tb_str = traceback.format_exc()
        update_task_log(task_id, f"An unexpected error occurred during RPC connection: {e}\\nTraceback:\\n{tb_str}", status='failed', level='error')
        return

    overall_success = True
    for i, pk in enumerate(request.private_keys):
        key_prefix = f"[Key {i+1}/{len(request.private_keys)}]"
        update_task_log(task_id, f"{key_prefix} Processing key...")

        # Check for stop request before starting steps for this key
        if task_status_storage.get(task_id, {}).get('stop_requested'):
            update_task_log(task_id, "Task execution stopped by user before processing key.", status='stopped', level='warning')
            return

        key_step_success = True # Track success for the current key across all steps
        for step_index, step in enumerate(request.steps):
            step_prefix = f"{key_prefix} [Step {step_index+1}/{len(request.steps)} ({step.type})]"
            update_task_log(task_id, f"{step_prefix} Starting step...")

            # Check for stop request before each step
            if task_status_storage.get(task_id, {}).get('stop_requested'):
                update_task_log(task_id, f"{step_prefix} Task execution stopped by user.", status='stopped', level='warning')
                return

            step_result = {'success': False, 'message': 'Step not executed', 'logs': []}
            config_data = step.config or {}

            try:
                # --- Add logging before execution ---
                update_task_log(task_id, f"{step_prefix} Attempting to execute step type: {step.type} with config: {config_data}")

                if step.type == 'delay':
                    duration = config_data.get('duration_seconds', 0)
                    if duration > 0:
                        update_task_log(task_id, f"{step_prefix} Waiting for {duration} seconds...")
                        await asyncio.sleep(duration)
                        step_result = {'success': True, 'message': f'Waited {duration}s', 'logs': []}
                    else:
                         step_result = {'success': False, 'message': 'Invalid delay duration', 'logs': []}

                elif step.type == 'stake':
                     # Validate config (example - ideally done via Pydantic model validation)
                    contract_type = config_data.get('contract_type')
                    amount_mon = config_data.get('amount_mon')
                    if not contract_type or amount_mon is None:
                         raise ValueError("Missing required config for stake step: contract_type, amount_mon")
                    
                    amount_wei = w3.to_wei(amount_mon, 'ether') # Convert here or in execute function?
                    stake_fn = None
                    if contract_type.lower() == 'kitsu': stake_fn = execute_kitsu_stake
                    elif contract_type.lower() == 'magma': stake_fn = execute_magma_stake
                    elif contract_type.lower() == 'apriori': stake_fn = execute_apriori_full_cycle # Treat full cycle as one step
                    
                    if stake_fn:
                        step_result = await stake_fn(
                            private_key=pk,
                            amount_wei=amount_wei, # Assuming amount is passed as wei
                            rpc_urls=rpc_to_use, # Pass correct RPC
                            # Pass other relevant config from config_data if needed
                            # e.g., cycles=config_data.get('cycles', 1) if execute_fn supports it
                        )
                    else:
                        step_result = {'success': False, 'message': f'Unsupported stake contract type: {contract_type}', 'logs': []}

                elif step.type == 'swap':
                    # Validate config
                    from_sym = config_data.get('token_from_symbol')
                    to_sym = config_data.get('token_to_symbol')
                    amount_str = config_data.get('amount_str')
                    if not from_sym or not to_sym or not amount_str:
                         raise ValueError("Missing required config for swap step: token_from_symbol, token_to_symbol, amount_str")
                    
                    step_result = await execute_uniswap_swap( # Assuming Uniswap for now
                         private_key=pk,
                         token_from_symbol=from_sym,
                         token_to_symbol=to_sym,
                         amount_str=amount_str,
                         rpc_urls=rpc_to_use
                         # Add mode/cycles if supported
                    )

                elif step.type == 'deploy':
                    name = config_data.get('contract_name')
                    symbol = config_data.get('contract_symbol')
                    if not name or not symbol:
                        raise ValueError("Missing required config for deploy step: contract_name, contract_symbol")
                    step_result = await execute_deploy_counter(
                        private_key=pk,
                        rpc_urls=rpc_to_use,
                        contract_name=name,
                        contract_symbol=symbol
                        # Add cycles if supported
                    )

                elif step.type == 'send':
                    amount_mon = config_data.get('amount_mon')
                    recipient = config_data.get('recipient_address')
                    mode = config_data.get('mode')
                    if amount_mon is None or (mode == 'single' and not recipient):
                        raise ValueError("Missing required config for send step")
                    if mode == 'random':
                        # Implement random recipient generation if needed
                        update_task_log(task_id, f"{step_prefix} Random recipient mode not implemented in multi-step yet.", level='warning')
                        recipient = None # Placeholder - skip this step?

                    if recipient:
                         amount_wei = w3.to_wei(amount_mon, 'ether')
                         step_result = await execute_send_mon(
                            private_key=pk,
                            recipient_address=recipient,
                            amount_wei=amount_wei,
                            rpc_urls=rpc_to_use
                            # Add tx_count if supported
                         )
                    else:
                         step_result = {'success': False, 'message': 'Recipient address missing or invalid mode', 'logs': []}

                elif step.type == 'bebop':
                     amount = config_data.get('amount_mon')
                     if amount is None: raise ValueError("Missing amount_mon for bebop step")
                     step_result = await execute_bebop_wrap_unwrap(private_key=pk, amount_mon=amount, rpc_urls=rpc_to_use)

                elif step.type == 'izumi':
                     amount = config_data.get('amount_mon')
                     if amount is None: raise ValueError("Missing amount_mon for izumi step")
                     step_result = await execute_izumi_wrap_unwrap(private_key=pk, amount_mon=amount, rpc_url=rpc_to_use) # Note: takes rpc_url

                elif step.type == 'lilchogstars':
                     update_task_log(task_id, f"{step_prefix} >>> Preparing to call execute_lilchogstars_mint") # DEBUG LOG
                     qty = config_data.get('quantity', 1)
                     if qty is None: raise ValueError("Missing quantity for lilchogstars step") # Add validation
                     step_result = await execute_lilchogstars_mint(private_key=pk, quantity=qty, rpc_url=rpc_to_use)

                elif step.type == 'mono':
                     recipient = config_data.get('recipient_address')
                     value = config_data.get('value_mon')
                     if not recipient or value is None: raise ValueError("Missing config for mono step")
                     step_result = await execute_mono_transaction(private_key=pk, recipient_address=recipient, value_mon=value, rpc_url=rpc_to_use)

                elif step.type == 'rubic':
                     update_task_log(task_id, f"{step_prefix} >>> Preparing to call execute_rubic_swap") # DEBUG LOG
                     amount = config_data.get('amount_mon')
                     if amount is None: raise ValueError("Missing amount_mon for rubic step")
                     step_result = await execute_rubic_swap(private_key=pk, amount_mon=amount, rpc_url=rpc_to_use)

                elif step.type == 'ambient':
                     step_result = await execute_ambient_swap(
                         private_key=pk,
                         token_in_symbol=config_data.get('token_in_symbol'),
                         token_out_symbol=config_data.get('token_out_symbol'),
                         amount_percent=config_data.get('amount_percent', 100.0),
                         rpc_url=rpc_to_use
                     )

                elif step.type == 'apriori': # Assuming full cycle needs no extra config here
                     step_result = await execute_apriori_full_cycle(private_key=pk, rpc_url=rpc_to_use)

                elif step.type == 'bean':
                     direction = config_data.get('direction')
                     symbol = config_data.get('token_symbol')
                     amount = config_data.get('amount')
                     if not direction or not symbol or amount is None: raise ValueError("Missing config for bean step")
                     rpc_list = [rpc_to_use] if rpc_to_use else DEFAULT_RPC_URLS # Need to handle default RPCs better
                     step_result = await execute_bean_swap(
                         private_key=pk,
                         direction=direction,
                         token_symbol=symbol,
                         amount=amount,
                         rpc_urls=rpc_list
                     )

                elif step.type == 'bima':
                     step_result = await execute_bima_lend_cycle(
                         private_key=pk,
                         rpc_url=rpc_to_use,
                         percent_to_lend=config_data.get('percent_to_lend')
                     )

                else:
                    step_result = {'success': False, 'message': f'Unsupported step type: {step.type}', 'logs': []}

            except Exception as e:
                 tb_str = traceback.format_exc()
                 step_result = {'success': False, 'message': f'Error during step execution: {e}', 'logs': [f"Traceback: {tb_str}"]}
                 update_task_log(task_id, f"{step_prefix} Error: {e}", level='error')
                 # Optionally log traceback to task log as well

            # Log results from the step execution
            if step_result:
                for log_line in step_result.get('logs', []):
                     update_task_log(task_id, f"{step_prefix} {log_line}") # Add step prefix to script logs
                update_task_log(task_id, f"{step_prefix} Result: {step_result.get('message', 'No message')}")

                if not step_result.get('success'):
                    key_step_success = False
                    overall_success = False
                    update_task_log(task_id, f"{step_prefix} Step failed. Stopping steps for this key.", level='warning')
                    break # Stop processing further steps for this key if one fails

            else:
                # Should not happen if logic is correct, but handle defensively
                key_step_success = False
                overall_success = False
                update_task_log(task_id, f"{step_prefix} Step execution returned None or unexpected result.", level='error')
                break


            # --- No delay *between* steps within a key defined here ---
            # Delay is now its own step type 'delay'

        # End of steps loop for one key

        # Wait between keys if specified and not the last key
        if i < len(request.private_keys) - 1 and request.delay_between_keys_seconds > 0:
             # Check before sleeping
             if task_status_storage.get(task_id, {}).get('stop_requested'):
                 update_task_log(task_id, "Task execution stopped by user.", status='stopped', level='warning')
                 return # Exit the function
             wait_msg = f"Waiting {request.delay_between_keys_seconds}s before next key..."
             update_task_log(task_id, wait_msg)
             await asyncio.sleep(request.delay_between_keys_seconds)

    # End of keys loop
    # Only update final status if not stopped
    if not task_status_storage.get(task_id, {}).get('stop_requested'):
        final_status = 'completed' if overall_success else 'failed'
        update_task_log(task_id, f"Multi-Step Task finished. Final Status: {final_status}", status=final_status)


# --- API Endpoints ---

# ... (Existing endpoints: read_root, get_address_from_key, get_balance, get_tasks, get_task_status, stop_task) ...

# --- NEW: Multi-Step Workflow Endpoint ---
@app.post("/api/v1/start-multi-step-workflow", tags=["Bot Actions"])
async def start_multi_step_workflow(request: MultiStepWorkflowRequest, background_tasks: BackgroundTasks):
    """Starts a multi-step workflow in the background."""
    task_id = str(uuid.uuid4())
    desc = request.task_description or f"Multi-Step Workflow ({len(request.steps)} steps)"

    # Basic validation - ensure steps list is not empty (already done by Pydantic Field)
    # More complex validation (e.g., config based on type) should ideally happen via Pydantic models

    task_status_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "description": desc,
        "task_type": "multi_step", # New type
        "config": { # Store non-sensitive config
            "rpc_url": request.rpc_url,
            "delay_between_keys_seconds": request.delay_between_keys_seconds,
            "steps": [step.model_dump() for step in request.steps] # Store steps config
        },
        "logs": [],
        "stop_requested": False # Ensure stop flag is initialized
    }
    update_task_log(task_id, f"Task '{desc}' created with ID: {task_id}. Queued for execution.")
    background_tasks.add_task(run_multi_step_task, task_id, request)
    return {"message": "Multi-step workflow initiated in background.", "task_id": task_id}


# Example of how to run the app (e.g., using uvicorn)
# uvicorn backend.api.main:app --reload --port 8000