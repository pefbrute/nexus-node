import os
import time
import shutil
from pathlib import Path
from web3 import Web3
from dotenv import load_dotenv
import argparse

# Constants
RPC_URL = "https://rpc.nexus.xyz/"
CHAIN_ID = 392

# These will be initialized in main()
PRIVATE_KEY = None
AMOUNT = None
GAS_LIMIT = None
MAX_BASE_FEE = None
PRIORITY_FEE = None
DELAY = None

# Load environment variables
load_dotenv()

# Remove 0x prefix if present
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "").replace("0x", "")
AMOUNT = float(os.getenv("AMOUNT", 0.001))  # Amount of NEX to send
GAS_LIMIT = int(os.getenv("GAS_LIMIT", 21000))

# Конвертируем значения газа из gwei в wei
MAX_BASE_FEE = Web3.to_wei(float(os.getenv("MAX_BASE_FEE", 2.0)), "gwei")
PRIORITY_FEE = Web3.to_wei(float(os.getenv("PRIORITY_FEE", 0.1)), "gwei")

DELAY = int(os.getenv("DELAY", 60))  # Delay between transactions in seconds

# Debug prints
print("\n=== Configuration ===")
print(f"RPC URL: {RPC_URL}")
print(f"Chain ID: {CHAIN_ID}")
print(f"Amount to send: {AMOUNT} NEX")
print(f"Gas limit: {GAS_LIMIT}")
print(f"Max base fee: {MAX_BASE_FEE}")
print(f"Priority fee: {PRIORITY_FEE}")

# Connect to network
print("\n=== Connecting to network ===")
web3 = Web3(Web3.HTTPProvider(RPC_URL))
if web3.is_connected():
    print("✅ Successfully connected to Nexus RPC")
    print(f"Current block number: {web3.eth.block_number}")
else:
    raise Exception("Failed to connect to Nexus RPC")

def load_wallets():
    """Load wallet addresses from wallets.txt"""
    try:
        script_dir = Path(__file__).parent
        wallets_path = script_dir / "wallets.txt"
        with open(wallets_path, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ Error: wallets.txt not found")
        return []

def check_balance(account_address):
    """Check if sender has sufficient balance"""
    try:
        balance = web3.eth.get_balance(account_address)
        balance_in_nex = web3.from_wei(balance, "ether")
        print(f"💰 Account balance: {balance_in_nex} NEX")
        return balance_in_nex
    except Exception as e:
        print(f"❌ Error checking balance: {e}")
        return 0

# Get current base fee and set gas prices dynamically
def get_gas_prices():
    try:
        # Get latest block
        latest_block = web3.eth.get_block('latest')
        base_fee = latest_block['baseFeePerGas']
        
        # Set max fee 20% higher than current base fee
        suggested_max_fee = int(base_fee * 1.2)
        
        # Set priority fee to 0.1 gwei
        suggested_priority_fee = Web3.to_wei(0.1, 'gwei')
        
        print(f"\n⛽ Current base fee: {web3.from_wei(base_fee, 'gwei')} gwei")
        print(f"⛽ Suggested max fee: {web3.from_wei(suggested_max_fee, 'gwei')} gwei")
        print(f"⛽ Priority fee: {web3.from_wei(suggested_priority_fee, 'gwei')} gwei")
        
        return suggested_max_fee, suggested_priority_fee
    except Exception as e:
        print(f"❌ Error getting gas prices: {e}")
        return MAX_BASE_FEE, PRIORITY_FEE

def send_transaction(private_key, to_address):
    """Send transaction to specified address"""
    try:
        # Create account from private key
        account = web3.eth.account.from_key(private_key)
        print(f"\n🔑 Using account: {account.address}")
        
        # Get current gas prices
        max_fee, priority_fee = get_gas_prices()
        
        # Verify sender's balance
        balance = check_balance(account.address)
        if balance < AMOUNT:
            print(f"❌ Insufficient balance: {balance} NEX (needed: {AMOUNT} NEX)")
            return False

        # Verify recipient address
        if not Web3.is_address(to_address):
            print(f"❌ Invalid address: {to_address}")
            return False

        to_address = Web3.to_checksum_address(to_address)
        nonce = web3.eth.get_transaction_count(account.address)
        print(f"📝 Current nonce: {nonce}")

        # Prepare transaction with dynamic gas prices
        tx = {
            "to": to_address,
            "value": web3.to_wei(AMOUNT, "ether"),
            "gas": GAS_LIMIT,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "type": 2
        }
        
        print("\n=== Transaction details ===")
        print(f"To: {to_address}")
        print(f"Value: {AMOUNT} NEX")
        print(f"Gas limit: {GAS_LIMIT}")
        print(f"Max fee per gas: {web3.from_wei(max_fee, 'gwei')} gwei")
        print(f"Priority fee: {web3.from_wei(priority_fee, 'gwei')} gwei")

        # Sign and send transaction
        print("\n=== Signing transaction ===")
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        print("✅ Transaction signed successfully")
        
        print("\n=== Sending transaction ===")
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"📤 Transaction sent! Hash: {web3.to_hex(tx_hash)}")
        
        # Wait for transaction receipt
        print("\n=== Waiting for confirmation ===")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt["status"] == 1:
            print(f"\n✅ Transaction confirmed!")
            print(f"   Hash: {web3.to_hex(tx_hash)}")
            print(f"   Block number: {receipt['blockNumber']}")
            print(f"   Gas used: {receipt['gasUsed']}")
            return True
        else:
            print(f"\n❌ Transaction failed!")
            print(f"   Hash: {web3.to_hex(tx_hash)}")
            return False

    except Exception as e:
        print(f"\n❌ Error sending to {to_address}: {str(e)}")
        return False

def setup_env(force_setup=False):
    """Setup environment variables by prompting user for values"""
    # Get the directory where the script is located
    script_dir = Path(__file__).parent
    env_path = script_dir / '.env'
    env_example_path = script_dir / '.env.example'
    
    if not env_example_path.exists():
        print("❌ .env.example file not found!")
        exit(1)
    
    # Проверяем существование .env и флаг принудительной настройки
    if env_path.exists() and not force_setup:
        return
        
    print("\n⚙️ Setting up .env file...")
    
    # Read template from .env.example
    with open(env_example_path, 'r') as f:
        template_lines = f.readlines()
    
    # Process each line and get user input for variables
    env_contents = []
    for line in template_lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, default_value = line.split('=', 1)
            key = key.strip()
            default_value = default_value.strip().strip('"')
            
            # Skip non-configurable variables
            if key in ['RPC_URL', 'CHAIN_ID']:
                env_contents.append(line)
                continue
                
            # Remove comments from default value
            if '#' in default_value:
                default_value = default_value.split('#')[0].strip()
            
            # Get user input
            user_value = input(f"Enter {key} [{default_value}]: ").strip()
            if not user_value:
                user_value = default_value
                
            # Add quotes if value contains spaces
            if ' ' in user_value:
                user_value = f'"{user_value}"'
                
            env_contents.append(f"{key}={user_value}")
        else:
            env_contents.append(line)
    
    # Write to .env file
    with open(env_path, 'w') as f:
        f.write('\n'.join(env_contents))
    
    print("✅ Created .env file with your settings!")

def validate_env():
    """Validate that all required environment variables are set"""
    required_vars = {
        'PRIVATE_KEY': 'Your wallet private key',
        'AMOUNT': 'Amount of NEX to send',
        'GAS_LIMIT': 'Transaction gas limit',
        'MAX_BASE_FEE': 'Maximum base fee in gwei',
        'PRIORITY_FEE': 'Priority fee in gwei'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var) or os.getenv(var) == f'your_{var.lower()}_here':
            missing_vars.append(f"- {var}: {description}")
    
    if missing_vars:
        print("\n❌ Missing or default environment variables:")
        print('\n'.join(missing_vars))
        print("\nPlease configure these variables in your .env file")
        exit(1)

def main():
    """Main function"""
    # Добавляем аргумент командной строки для принудительной настройки
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true', help='Force environment setup')
    args = parser.parse_args()
    
    # Setup environment before loading variables
    setup_env(force_setup=args.setup)
    
    # Move load_dotenv() before any variable initialization
    script_dir = Path(__file__).parent
    env_path = script_dir / '.env'
    load_dotenv(env_path)
    validate_env()
    
    # Initialize variables after loading .env
    global PRIVATE_KEY, AMOUNT, GAS_LIMIT, MAX_BASE_FEE, PRIORITY_FEE, DELAY
    PRIVATE_KEY = os.getenv("PRIVATE_KEY", "").replace("0x", "")
    AMOUNT = float(os.getenv("AMOUNT", 0.001))
    GAS_LIMIT = int(os.getenv("GAS_LIMIT", 21000))
    MAX_BASE_FEE = Web3.to_wei(float(os.getenv("MAX_BASE_FEE", 2.0)), "gwei")
    PRIORITY_FEE = Web3.to_wei(float(os.getenv("PRIORITY_FEE", 0.1)), "gwei")
    DELAY = int(os.getenv("DELAY", 60))
    
    # Debug prints
    print("\n=== Configuration ===")
    print(f"RPC URL: {RPC_URL}")
    print(f"Chain ID: {CHAIN_ID}")
    print(f"Amount to send: {AMOUNT} NEX")
    print(f"Gas limit: {GAS_LIMIT}")
    print(f"Max base fee: {MAX_BASE_FEE}")
    print(f"Priority fee: {PRIORITY_FEE}")
    
    print("\n=== Starting transaction sender ===")
    
    if not PRIVATE_KEY:
        print("❌ Error: PRIVATE_KEY not set in .env file")
        return

    wallets = load_wallets()
    if not wallets:
        print("❌ Error: No wallet addresses found")
        return

    print(f"\n📝 Loaded {len(wallets)} wallet addresses:")
    for wallet in wallets:
        print(f"   - {wallet}")
    
    for recipient in wallets:
        print(f"\n💫 Sending {AMOUNT} NEX to {recipient}")
        success = send_transaction(PRIVATE_KEY, recipient)
        if success:
            print("\n✅ Transaction completed successfully")
        else:
            print("\n❌ Transaction failed")
    
    print("\n👋 All transactions completed")

if __name__ == "__main__":
    main() 