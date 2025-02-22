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

script_dir = Path(__file__).parent
env_path = script_dir / '.env'

# Если .env не существует, создаем его
if not env_path.exists():
    print("\n⚙️ Creating new .env file...")
    
    # Запрашиваем приватный ключ
    print("\nPlease enter your private key:")
    
    while True:
        pk = input("\nEnter wallet private key (without 0x prefix): ").strip().replace('0x', '')
        if len(pk) == 64:
            break
        print("❌ Invalid key length. Private key must be 64 characters long.")
    
    # Создаем .env с дефолтными настройками
    env_content = f"""# Network configuration
RPC_URL="{RPC_URL}"
CHAIN_ID={CHAIN_ID}

# Wallet configuration
PRIVATE_KEY={pk}  # Wallet private key without 0x prefix

# Transaction settings
AMOUNT=0.1  # Amount of NEX to send
GAS_LIMIT=21000  # Transaction gas limit

# Gas price settings (in gwei)
MAX_BASE_FEE=2.0  # Maximum base fee
PRIORITY_FEE=0.1  # Priority fee

# Other settings
DELAY=60  # Delay between transactions in seconds
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print("\n✅ Created .env file with your private key and default settings")

# Load environment variables
load_dotenv(env_path)

# Initialize variables
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "").replace("0x", "")
AMOUNT = float(os.getenv("AMOUNT", 0.1))
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

def save_wallets(addresses):
    """Save wallet addresses to wallets.txt"""
    try:
        script_dir = Path(__file__).parent
        wallets_path = script_dir / "wallets.txt"
        with open(wallets_path, "w") as f:
            for address in addresses:
                f.write(f"{address}\n")
        print(f"✅ Saved {len(addresses)} addresses to wallets.txt")
    except Exception as e:
        print(f"❌ Error saving wallets: {e}")

def get_recipient_addresses():
    """Get recipient addresses from wallets.txt or user input"""
    script_dir = Path(__file__).parent
    wallets_path = script_dir / "wallets.txt"
    
    # Create wallets.txt if it doesn't exist
    if not wallets_path.exists():
        print("\n📝 Creating new wallets.txt file...")
        wallets_path.touch()
    
    # Read existing addresses
    addresses = load_wallets()
    
    # If no addresses found, prompt for input
    if not addresses:
        print("\nℹ️ No recipient addresses found in wallets.txt")
        print("Enter recipient addresses (press Enter with empty input to finish):")
        
        while True:
            address = input("\nEnter recipient address: ").strip()
            if not address:
                break
            if Web3.is_address(address):
                addresses.append(address)
                print("✅ Address added")
            else:
                print("❌ Invalid address format")
        
        if addresses:
            # Save entered addresses to file
            save_wallets(addresses)
    
    return addresses

def main():
    """Main function"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true', help='Force environment setup')
    args = parser.parse_args()
    
    if args.setup and env_path.exists():
        os.remove(env_path)
        print("Removed existing .env file")
    
    # Get sender wallet address
    wallet = web3.eth.account.from_key(PRIVATE_KEY).address
    print(f"\nSender wallet: {wallet}")
    
    print("\n=== Starting transaction sender ===")
    
    if not PRIVATE_KEY:
        print("❌ Error: PRIVATE_KEY not set in .env file")
        return
    
    # Get recipient addresses using new function
    recipient_addresses = get_recipient_addresses()
    
    if not recipient_addresses:
        print("❌ No recipient addresses provided. Exiting...")
        return
    
    print(f"\nFound {len(recipient_addresses)} recipient address(es):")
    for addr in recipient_addresses:
        print(f"  • {addr}")
    
    try:
        current_index = 0
        
        while True:
            # Проверяем баланс отправителя
            balance = check_balance(wallet)
            
            if balance < AMOUNT:
                print("\n❌ Insufficient balance. Stopping script.")
                break
            
            recipient = recipient_addresses[current_index]
            print(f"\n💫 Sending {AMOUNT} NEX to {recipient}")
            
            success = send_transaction(PRIVATE_KEY, recipient)
            if success:
                print(f"\n✅ Transaction completed successfully")
            else:
                print(f"\n❌ Transaction failed")
            
            # Переходим к следующему получателю
            current_index = (current_index + 1) % len(recipient_addresses)
            
            print(f"\n⏳ Waiting {DELAY} seconds before next transaction...")
            time.sleep(DELAY)
            print("\n🔄 Starting next transaction...")
            
    except KeyboardInterrupt:
        print("\n\n👋 Script stopped by user")
        print("Thank you for using the transaction sender!")

if __name__ == "__main__":
    main()