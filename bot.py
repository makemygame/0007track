import os
import requests
from web3 import Web3
from telegram import Bot
from datetime import datetime, timezone
import asyncio
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Lấy thông tin từ biến môi trường
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
CHAT_ID = os.getenv('CHAT_ID')  # ID nhóm hoặc người dùng Telegram

# Địa chỉ ví cần theo dõi
wallet_address = '0x835678a611b28684005a5e2233695fb6cbbb0007'
# Contract của USDT
usdt_contract = '0xdAC17F958D2ee523a2206206994597C13D831ec7'

# URL API của Etherscan
api_url = f'https://api.etherscan.io/api?module=account&action=tokentx&address={wallet_address}&contractaddress={usdt_contract}&startblock=0&endblock=99999999&sort=asc&apikey={ETHERSCAN_API_KEY}'

# Ngày bắt đầu theo dõi
start_date = datetime(2024, 12, 5, tzinfo=timezone.utc)

# Lưu trạng thái giao dịch gần nhất (transaction hash)
last_transaction_hash = None


async def get_usdt_transactions():
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        data = response.json()

        if data['status'] == '1' and 'result' in data:
            transactions = data['result']
            usdt_transactions = [
                tx for tx in transactions
                if tx['tokenSymbol'] == 'USDT'
                and tx['to'].lower() == wallet_address.lower()
                and datetime.fromtimestamp(int(tx['timeStamp']), timezone.utc) > start_date  # Lọc từ sau ngày 05/12/2024
            ]
            return usdt_transactions
        else:
            print("No valid transactions found or API error.")
            return []
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []


async def send_telegram_message(bot, messages):
    for message in messages:
        while True:
            try:
                await bot.send_message(chat_id=CHAT_ID, text=message)
                await asyncio.sleep(1)  # Tránh gửi quá nhanh
                break
            except Exception as e:
                if "Flood control exceeded" in str(e):
                    retry_after = int(str(e).split("Retry in ")[1].split(" seconds")[0])
                    print(f"Flood control exceeded. Retrying in {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                else:
                    print(f"Error sending Telegram message: {e}")
                    break


async def track_transactions():
    global last_transaction_hash  # Lưu trạng thái giao dịch gần nhất
    bot = Bot(token=TELEGRAM_API_KEY)

    print("Starting transaction tracker...")
    while True:
        usdt_transactions = await get_usdt_transactions()
        new_transactions = []

        # Kiểm tra các giao dịch mới
        for tx in usdt_transactions:
            if last_transaction_hash is None or tx['hash'] > last_transaction_hash:
                new_transactions.append(tx)

        # Tạo danh sách thông báo
        messages = []
        for tx in sorted(new_transactions, key=lambda x: int(x['timeStamp'])):
            timestamp = int(tx['timeStamp'])
            date_time = datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

            message = (
                f"📅 **New USDT Transaction Received** 📅\n\n"
                f"**Transaction Hash:** `{tx['hash']}`\n"
                f"**From:** `{tx['from']}`\n"
                f"**To:** `{tx['to']}`\n"
                f"**Value:** `{Web3.from_wei(int(tx['value']), 'mwei')} USDT`\n"
                f"**Block Number:** `{tx['blockNumber']}`\n"
                f"**Time Received:** `{date_time} UTC`\n"
            )
            messages.append(message)

        # Gửi tất cả tin nhắn trong danh sách
        if messages:
            await send_telegram_message(bot, messages)

        # Cập nhật trạng thái giao dịch gần nhất
        if new_transactions:
            last_transaction_hash = new_transactions[-1]['hash']

        # Đợi 5 phút trước khi kiểm tra lại
        await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(track_transactions())
