import asyncio
import logging
import datetime
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import pytz
import config
from handlers import router, set_bot, setup_handlers
import sys
import io
from db import UsersDataBase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    global bot
    bot = Bot(token=config.TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    db = UsersDataBase()
    set_bot(bot)
    setup_handlers()
    await db.create_table()
    await bot.delete_webhook(drop_pending_updates=True)
    tasks = [dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()), update_index(db)]
    await asyncio.gather(*tasks)


async def update_index(db):
    while True:
        tz = pytz.timezone('Europe/Kiev')
        now = datetime.datetime.now(tz)
        name = 'dbs/users.db'
        
        async with aiosqlite.connect(name) as db:
            cursor = await db.cursor()
        
            if now.hour == 23 and now.minute == 57:

                query = 'SELECT * FROM users ORDER BY id DESC'
                await cursor.execute(query)
                users = await cursor.fetchall()
                
                all_messages = []
                for user in users:
                    if user[1] == 'manager':
                        
                        query = 'SELECT * FROM requests WHERE manager = ?'
                        await cursor.execute(query, (user[0],))
                        reqs = await cursor.fetchall()
                            
                        success = []
                        bad = []
                        for req in reqs:
                            data = {
                                'username': user[4],
                                'kategory': req[4],
                                'status': req[2],
                                'balance': float(req[5])
                            }
                            if data['status'] == 'Успешно оплачено ✅':
                                success.append(data)
                            else:
                                bad.append(data)
                        message = generate_message(user[4], success, bad)
                        all_messages.append(message)

                for message in all_messages:
                    await bot.send_message(chat_id=config.ADMIN_ID, text=message)
            
            elif now.hour == 0 and now.minute == 0:
                
                query = 'DELETE FROM requests'
                await cursor.execute(query)
                await db.commit()

            elif now.hour == 0 and now.minute == 5:
                
                query = 'SELECT * FROM cards ORDER BY id DESC'
                await cursor.execute(query)
                cards = await cursor.fetchall()
                    
                for card in cards:
                    query = 'UPDATE cards SET uses = ? WHERE name = ?'
                    await cursor.execute(query, (0, card[1]))
                    await db.commit()
                
            await asyncio.sleep(60)
        
# --====================== ФУНКЦИИ ======================-- #

def generate_message(manager_name, success, bad):
    manager_message = f"👾 {manager_name}:\n"

    success_message = "✅ Успешные:\n"
    for category in set(item['kategory'] for item in success):
        count = sum(1 for item in success if item['kategory'] == category)
        success_message += f"{category}: {count}\n"
    total_success = sum(item['balance'] for item in success)

    bad_message = "❌ Не успешные:\n"
    for category in set(item['kategory'] for item in bad):
        count = sum(1 for item in bad if item['kategory'] == category)
        bad_message += f"{category}: {count}\n"
    total_bad = sum(item['balance'] for item in bad)    
    
    total_count = total_success + total_bad
    total_message = f"💰 Общая сумма: {total_count}₴\n"

    final_message = manager_message + "\n" + success_message + "\n" + bad_message + "\n" + total_message
    
    return final_message


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
