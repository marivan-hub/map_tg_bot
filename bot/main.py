import os
import django
import logging
from asgiref.sync import sync_to_async
import os
from telegram import InputFile
from django.core.files.storage import default_storage
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from pathlib import Path
# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activeBot.settings')
django.setup()

from navigation.models import Route, Step, Building
from navigation.utils import parse_building_from_code
from django.conf import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# ORM-функции (синхронные → async)
# =========================


@sync_to_async
def get_route_by_room_code(code: str):
    return Route.objects.select_related('building').prefetch_related('steps').filter(room_code__iexact=code).first()

@sync_to_async
def get_building_by_code(code: str):
    return Building.objects.filter(code=code).first()

# =========================
# Команды
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе найти нужную аудиторию. Просто отправь номер, например: 312Т или 104B7"
    )

# =========================
# Обработка сообщений
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    route = await get_route_by_room_code(text)
    if route:
        await update.message.reply_text(
            f"Маршрут к аудитории {route.room_code}:\nЭтаж: {route.floor}, Корпус: {route.building.name}"
        )

        for step in route.steps.all():
            if step.image:
                BASE_DIR = Path(__file__).resolve().parent.parent
                image_path = BASE_DIR / "route_steps" / Path(step.image.name).name
                logger.info(f"Отправка фото: {image_path}")

                if os.path.exists(image_path):
                    with open(image_path, 'rb') as image_file:
                        telegram_file = InputFile(image_file)
                        await update.message.reply_photo(photo=telegram_file, caption=step.description)
                else:
                    logger.warning(f"Файл не найден: {image_path}")
                    await update.message.reply_text(f"(⚠️ Изображение не найдено)\n{step.description}")
            else:
                await update.message.reply_text(step.description)

    else:
        # Попробуем угадать корпус
        code = parse_building_from_code(text)
        building = await get_building_by_code(code)

        if building:
            await update.message.reply_text(
                f"Маршрут не найден, но аудитория, вероятно, находится в корпусе: {building.name}"
            )
        else:
            await update.message.reply_text(
                "Маршрут не найден. Возможно, аудитория находится в Главном корпусе (север/центр)."
            )
# =========================
# Запуск
# =========================

if __name__ == '__main__':
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("Переменная окружения TELEGRAM_BOT_TOKEN не установлена")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    app.run_polling()
