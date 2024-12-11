import requests
from web3 import Web3
from telegram import Bot
from telegram.ext import Application, CommandHandler
import asyncio
from datetime import datetime, timezone

# Etherscan API Key và Telegram Bot Token
ETHERSCAN_API_KEY = 'V4ZM3I63HRFWDFZMXCHC7Q7XDDUSQZQWBU'
TELEGRAM_API_KEY = '7707122193:AAEBAgSi_XvypWQLrwhZ6beqf1VYsTN381w'
CHAT_ID = '-1002412475707'  # ID của nhóm hoặc người nhận thông báo

# Địa chỉ ví cần theo dõi
wallet_address = '0x835678a611b28684005a5e2233695fb6cbbb0007'
# Contract của USDT
usdt_contract = '0xdAC17F958D2ee523a2206206994597C13D831ec7'

# Etherscan API URL cho Token Transfers
api_url = f'https://api.etherscan.io/api?module=account&action=tokentx&address={wallet_address}&contractaddress={usdt_contract}&startblock=0&endblock=99999999&sort=asc&apikey={ETHERSCAN_API_KEY}'

# Ngày bắt đầu theo dõi (yyyy-mm-dd)
start_date = datetime(2024, 12, 5, tzinfo=timezone.utc)

async def get_usdt_transactions():
    response = requests.get(api_url)
    data = response.json()
    if data['status'] == '1':
        transactions = data['result']
        usdt_transactions = [
            tx for tx in transactions
            if tx['tokenSymbol'] == 'USDT'
            and tx['to'].lower() == wallet_address.lower()
            and datetime.fromtimestamp(int(tx['timeStamp']), timezone.utc) > start_date
        ]
        return usdt_transactions
    else:
        return []

async def send_telegram_message(bot, message):
    await bot.send_message(chat_id=CHAT_ID, text=message)

async def track_transactions():
    bot = Bot(token=TELEGRAM_API_KEY)
    application = Application.builder().token(TELEGRAM_API_KEY).build()

    last_checked = datetime.now(timezone.utc)
    while True:
        usdt_transactions = await get_usdt_transactions()
        for tx in usdt_transactions:
            timestamp = int(tx['timeStamp'])
            date_time = datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            # Chỉ gửi thông báo cho các giao dịch mới sau lần kiểm tra trước đó
            if datetime.fromtimestamp(timestamp, timezone.utc) > last_checked:
                message = (
                    f"📅 **New USDT Transaction Received** 📅\n\n"
                    f"**Transaction Hash:** {tx['hash']}\n"
                    f"**From:** {tx['from']}\n"
                    f"**To:** {tx['to']}\n"
                    f"**Value:** {Web3.from_wei(int(tx['value']), 'mwei')} USDT\n"
                    f"**Block Number:** {tx['blockNumber']}\n"
                    f"**Time Received:** {date_time} UTC\n"
                )
                await send_telegram_message(bot, message)
        
        last_checked = datetime.now(timezone.utc)
        await asyncio.sleep(300)  # Đợi 300 giây (5 phút) trước khi kiểm tra lại

if __name__ == "__main__":
    asyncio.run(track_transactions())
