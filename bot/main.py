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
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activeBot.settings')
django.setup()
from PIL import Image, ImageDraw
from navigation.models import Route, Step, Building
from navigation.utils import parse_building_from_code
from django.conf import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


BUILDING_MARKS = {
    "Т": (293, 732),
    "МТ": (396, 932),
    "БМ": (275, 859),
    "B2": (319, 834),
    "B4": (285, 758),
    "B5": (267, 708),
    "B6": (299, 711),
    "B7": (326, 723),
    "B8": (342,699),
    "B9": (348, 591),
    "C1": (313, 869),
    "C3": (239, 864),
    "Э": (692, 610),
    "М": (752, 561),
    "Л": (785, 447),
    "Ю": (459, 908),
    "Х": (366, 750),
    "КК": (785, 447),
}

def mark_building_on_scheme(building_code: str) -> str:
    """Создаёт копию схемы с отметкой на корпусе и возвращает путь к временному файлу"""
    scheme_path = "/app/howto/scheme.png"
    output_path = f"/app/tmp/scheme_{building_code}.png"

    os.makedirs("/app/tmp", exist_ok=True)

    img = Image.open(scheme_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    if building_code in BUILDING_MARKS:
        x, y = BUILDING_MARKS[building_code]
        r = 12  # радиус точки
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0, 255))

    img.save(output_path)
    return output_path


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
        "Привет! Я помогу тебе найти нужную аудиторию. Просто отправь номер, например: 219 или 312Т."
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
                image_path = BASE_DIR / "media/route_steps" / Path(step.image.name).name
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
            marked_scheme_path = mark_building_on_scheme(building.code)
            with open(marked_scheme_path, 'rb') as image_file:
                await update.message.reply_photo(photo=image_file, caption=f"Отмечен корпус {building.code}")
        else:
            await update.message.reply_text(
                "Маршрут не найден. Возможно, аудитория находится в Главном корпусе (север/центр)."
            )


async def how_to_navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет серию картинок с подписями для навигации
    """
    steps = [
        ("/app/howto/scheme.png", "Общая схема территории МГТУ"),
        ("/app/howto/gz.jpg", "Как ориентироваться в главном корпусе (ГЗ)"),
        ("/app/howto/audit.jpg",
         "Как понять номер кабинета\n\n"
         "— Первая цифра — этаж\n"
         "— Следующие две — номер аудитории\n"
         "— Буквы в конце — корпус\n\n"
         "Примеры букв:\n"
         "Т — Технологический\n"
         "МТ — Инж. бизнес и менеджмент\n"
         "БМ — Биомедицинские системы\n"
         "К — Инжиниринговый центр\n"
         "B2 — Квантум Парк\n"
         "B4 — Инновационный хаб\n"
         "B7 — ИТ кластер\n"
         "Э — Энергомашиностроение\n"
         "М — Спец. машиностроение\n"
         "Л — Учебно-лабораторный\n"
         "Ю — Южное крыло\n"
         "Х — Хим. лаборатория\n\n"
         "_Если буквы нет — Северное/Центральное крыло_")
    ]

    for image_path, text in steps:
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                await update.message.reply_photo(photo=InputFile(f))
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")


async def send_scheme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет схему территории
    """
    scheme_path = "/app/howto/scheme.png"
    if os.path.exists(scheme_path):
        with open(scheme_path, 'rb') as f:
            await update.message.reply_photo(photo=InputFile(f), caption="Общая схема территории МГТУ")
    else:
        await update.message.reply_text("⚠️ Схема не найдена")



# =========================
# Запуск
# =========================

if __name__ == '__main__':
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("Переменная окружения TELEGRAM_BOT_TOKEN не установлена")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('howtonavigate', how_to_navigate))
    app.add_handler(CommandHandler('scheme', send_scheme))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    app.run_polling()
