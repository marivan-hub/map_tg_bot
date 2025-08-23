import os
import django
import logging
from asgiref.sync import sync_to_async
from telegram import InputFile, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activeBot.settings')
django.setup()
from PIL import Image, ImageDraw
from navigation.models import Route, Step, Building
from navigation.utils import parse_building_from_code, normalize
from django.conf import settings

# Set logging to DEBUG for detailed troubleshooting
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# BUILDING_MARKS with normalized (Latin) keys
BUILDING_MARKS = {
    "T": (293, 732),
    "MT": (396, 932),
    "BM": (275, 859),
    "B2": (319, 834),
    "B4": (285, 758),
    "B5": (267, 708),
    "B6": (299, 711),
    "B7": (326, 723),
    "B8": (342, 699),
    "B9": (348, 591),
    "C1": (313, 869),
    "C3": (239, 864),
    "E": (692, 610),
    "M": (752, 561),
    "L": (785, 447),
    "YU": (459, 908),
    "X": (366, 750),
    "KK": (785, 447),
    "K": (276, 888),
}

# Define special buildings with normalized (Latin) codes
SPECIAL_BUILDINGS = ['B4', 'B5', 'B6', 'B7', 'B8', 'X', 'MT']

# Define steps for special buildings with normalized (Latin) keys
SPECIAL_STEPS = {
    'B4': [
        ("/app/howto/kh_photo1.jpg", "Корпуса B1-B8 и конгресс-холл располагаются через дорогу от входа в проходные главного корпуса."),
        ("/app/howto/kh_photo2.jpg", "Для прохода необходимо перейти дорогу и подняться по лестницу"),
        ("/app/howto/kh_photo3.jpg", "Далее проходите прямо и на площади у дерева будут располагаться нужные вам корпуса."),
    ],
    'B5': [
        ("/app/howto/kh_photo1.jpg", "Корпуса B1-B8 и конгресс-холл располагаются через дорогу от входа в проходные главного корпуса."),
        ("/app/howto/kh_photo2.jpg", "Для прохода необходимо перейти дорогу и подняться по лестницу"),
        ("/app/howto/kh_photo3.jpg", "Далее проходите прямо и на площади у дерева будут располагаться нужные вам корпуса."),
    ],
    'B6': [
        ("/app/howto/kh_photo1.jpg", "Корпуса B1-B8 и конгресс-холл располагаются через дорогу от входа в проходные главного корпуса."),
        ("/app/howto/kh_photo2.jpg", "Для прохода необходимо перейти дорогу и подняться по лестницу"),
        ("/app/howto/kh_photo3.jpg", "Далее проходите прямо и на площади у дерева будут располагаться нужные вам корпуса."),
    ],
    'B7': [
        ("/app/howto/kh_photo1.jpg", "Корпуса B1-B8 и конгресс-холл располагаются через дорогу от входа в проходные главного корпуса."),
        ("/app/howto/kh_photo2.jpg", "Для прохода необходимо перейти дорогу и подняться по лестницу"),
        ("/app/howto/kh_photo3.jpg", "Далее проходите прямо и на площади у дерева будут располагаться нужные вам корпуса."),
    ],
    'B8': [
        ("/app/howto/kh_photo1.jpg", "Корпуса B1-B8 и конгресс-холл располагаются через дорогу от входа в проходные главного корпуса."),
        ("/app/howto/kh_photo2.jpg", "Для прохода необходимо перейти дорогу и подняться по лестницу"),
        ("/app/howto/kh_photo3.jpg", "Далее проходите прямо и на площади у дерева будут располагаться нужные вам корпуса."),
    ],
    'X': [
        ("/app/howto/himlab1.jpg", "Вход в корпус находится через дорогу от первой проходной главного корпуса."),
        ("/app/howto/himlab2.jpg", "Вам нужен корпус В1. Для входа необходимо подняться по лестнице."),
    ],
    'MT': [
        ("/app/howto/mt_photo1.jpg", "Для прохода к корпусам А2 и А3 необходимо зайти на территорию главного корпуса через одну из проходных (удобнее всего через 2 - на фото)."),
        ("/app/howto/mt_photo2.jpg", "Затем повернуть направо и пройти мимо главного корпуса (чтобы оно было слева от вас)."),
        ("/app/howto/mt_photo3.jpg", "Вход в корпус А2 будет располагаться далее в углублении между двумя зданиями по левую сторону от вас."),
    ],
}

def extract_floor(room_code: str) -> int | None:
    code = normalize(room_code.strip().upper())
    token = parse_building_from_code(code)
    core = code
    if token and token != "DEFAULT":
        if core.startswith(token):
            core = core[len(token):]
        elif core.endswith(token):
            core = core[:-len(token)]
    digits = ''.join(ch for ch in core if ch.isdigit())
    if not digits:
        return None
    if len(digits) >= 4:
        return int(digits[:2])
    elif len(digits) >= 3:
        return int(digits[0])
    return None

def mark_building_on_scheme(building_code: str) -> str:
    scheme_path = "/app/howto/scheme.png"
    output_path = f"/app/tmp/scheme_{building_code}.png"
    os.makedirs("/app/tmp", exist_ok=True)
    img = Image.open(scheme_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    normalized_code = normalize(building_code.upper())
    logger.debug(f"Attempting to mark building: {normalized_code}")
    if normalized_code in BUILDING_MARKS:
        x, y = BUILDING_MARKS[normalized_code]
        r = 12
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0, 255))
    else:
        logger.warning(f"Building code {normalized_code} not found in BUILDING_MARKS")
    img.save(output_path)
    return output_path

@sync_to_async
def get_route_by_room_code(code: str):
    normalized_code = normalize(code.upper())
    routes = Route.objects.select_related('building').prefetch_related('steps').all()
    for route in routes:
        if normalize(route.room_code.upper()) == normalized_code:
            logger.debug(f"Route found for {normalized_code}: {route.room_code}")
            return route
    logger.debug(f"No route found for {normalized_code}")
    return None

@sync_to_async
def get_building_by_code(code: str):
    normalized_code = normalize(code.upper())
    buildings = Building.objects.all()
    for building in buildings:
        if normalize(building.code.upper()) == normalized_code:
            logger.debug(f"Building found for {normalized_code}: {building.code}")
            return building
    logger.debug(f"No building found for {normalized_code}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("Start command received")
    await update.message.reply_text(
        "Привет! Я помогу тебе найти нужную аудиторию. Просто отправь номер, например: 219 или 312Т."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    logger.debug(f"Received message: {text}")
    route = await get_route_by_room_code(text)
    building_code = None

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
        building_code = normalize(route.building.code.upper())
        logger.debug(f"Route building code (normalized): {building_code}")
    else:
        code = parse_building_from_code(text)
        logger.debug(f"Parsed building code: {code}")
        building = await get_building_by_code(code)
        floor = extract_floor(text)
        if building:
            msg = f"Маршрут не найден, но аудитория, вероятно, находится в корпусе: {building.name}"
            if floor:
                msg += f"\nЭтаж: {floor}"
            await update.message.reply_text(msg)
            marked_scheme_path = mark_building_on_scheme(building.code)
            if os.path.exists(marked_scheme_path):
                with open(marked_scheme_path, 'rb') as image_file:
                    await update.message.reply_photo(photo=image_file, caption=f"Отмечен корпус {building.code}")
            else:
                logger.warning(f"Scheme file not found: {marked_scheme_path}")
                await update.message.reply_text(f"⚠️ Схема для корпуса {building.code} не найдена")
            building_code = normalize(building.code.upper())
            logger.debug(f"Building code (normalized): {building_code}")
        else:
            msg = "Маршрут не найден. Возможно, аудитория находится в Главном корпусе в северном крыле."
            if floor:
                msg += f"\nЭтаж: {floor}"
            await update.message.reply_text(msg)
            logger.debug("No building or route found")

    # Send button with command-based callback
    normalized_building_code = normalize(building_code) if building_code else None
    logger.debug(f"Checking if {normalized_building_code} is in SPECIAL_BUILDINGS: {SPECIAL_BUILDINGS}")
    if normalized_building_code in SPECIAL_BUILDINGS:
        keyboard = [
            [InlineKeyboardButton("Как добраться до корпуса", url=f"https://t.me/GuimcActiveHelpBot?start=get_to_{normalized_building_code}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Дополнительная информация:", reply_markup=reply_markup)
        logger.debug(f"Sent button with command: /start get_to_{normalized_building_code}")

async def how_to_navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("howtonavigate command received")
    steps = [
        ("/app/howto/scheme.png", "Общая схема территории МГТУ"),
        ("/app/howto/gz.jpg", "Как ориентироваться в главном корпусе (ГЗ)"),
        ("/app/howto/audit.jpg",
         "Как понять номер кабинета\n\n"
         "— Первая цифра — этаж\n"
         "— Следующие две — номер аудитории\n"
         "— Буквы в конце — корпус\n\n"
         "Примеры букв в конце номера аудитории:\n"
         "Т — Технологический\n"
         "МТ — Инженерный бизнес и менеджмент\n"
         "БМ — Центр биомедицинских систем и технологий\n"
         "К — Инжиниринговый центр НТС\n"
         "B2 — Квантум Парк\n"
         "B4 — Инновационный хаб, Конгресс-центр\n"
         "B5 — Технолгия защиты природы\n"
         "B6 — Цифровое материаловедение\n"
         "B7 — кластер информационных технологий\n"
         "B8 — Федеральный испытательный центр\n"
         "B9 — Исследовательский центр\n"
         "С1 — Медицинский центр\n"
         "С3 — Роботоцентр\n"
         "Э — Энергомашиностроение\n"
         "М — Специальное машиностроение\n"
         "Л — Учебно-лабораторный корпус\n"
         "Ю — Южное крыло Главного корпуса\n"
         "Х — Химическая лаборатория\n"
         "КК — Компьютерный класс\n\n"
        "Примеры букв в начале номера аудитории:\n"
         "К — Конгресс-центр\n"
         "КХ — Иновационный хаб\n\n"
         "_Если буквы нет — Главный корпус северное крыло_")
    ]
    for image_path, text in steps:
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                await update.message.reply_photo(photo=InputFile(f), caption=text, parse_mode="Markdown")
        else:
            logger.warning(f"File not found: {image_path}")
            await update.message.reply_text(text, parse_mode="Markdown")

async def send_scheme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("scheme command received")
    scheme_path = "/app/howto/scheme.png"
    if os.path.exists(scheme_path):
        with open(scheme_path, 'rb') as f:
            await update.message.reply_photo(photo=InputFile(f), caption="Общая схема территории МГТУ")
    else:
        logger.warning(f"Scheme file not found: {scheme_path}")
        await update.message.reply_text("⚠️ Схема не найдена")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug(f"Start command received with args: {context.args}")
    if context.args and context.args[0].startswith("get_to_"):
        building_code = context.args[0].removeprefix("get_to_")
        logger.debug(f"Processing start command for building: {building_code}")
        steps = SPECIAL_STEPS.get(building_code, [])
        if steps:
            logger.debug(f"Found steps for {building_code}")
            for image_path, text in steps:
                if os.path.exists(image_path):
                    with open(image_path, 'rb') as f:
                        await update.message.reply_photo(photo=InputFile(f), caption=text, parse_mode="Markdown")
                else:
                    logger.warning(f"Image not found: {image_path}")
                    await update.message.reply_text(text, parse_mode="Markdown")
        else:
            logger.warning(f"No steps found for {building_code}")
            await update.message.reply_text("Инструкции по добиранию до корпуса не найдены.")
    else:
        await update.message.reply_text(
            "Привет! Я помогу тебе найти нужную аудиторию. Просто отправь номер, например: 219 или 312Т."
        )

if __name__ == '__main__':
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("Переменная окружения TELEGRAM_BOT_TOKEN не установлена")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('howtonavigate', how_to_navigate))
    app.add_handler(CommandHandler('scheme', send_scheme))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен...")
    app.run_polling()