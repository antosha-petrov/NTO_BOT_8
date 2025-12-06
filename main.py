import asyncio
import logging
import aiohttp


from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup


# ---------- Адрес сервера ----------
SERVER_URL = "http://localhost:8000"

# ---------- Токен бота ----------
bot_token = "8241496751:AAH9DmunV9DkQmpxW_Tq2K7ScpQwsPFNHKs"

# ---------- Задержка для сигнализации ----------
alarm_delay = 10

# ---------- Чат по умолчанию ----------
default_chat_id = 0

# ---------- Маршрутизация ----------
router = Router()

# ---------- Фоновые оповещения ----------
task = None


# ---------- Классы для FSM ----------
class AlarmStates(StatesGroup):
    waiting_for_code = State()

class AlarmCheckStates(StatesGroup):
    waiting_for_alarm_code = State()

class CheckStates(StatesGroup):
    checking_for_alarm_code = State()

class ManualControl(StatesGroup):
    choosing_element = State()
    choosing_led_color = State()
    choosing_window = State()
    choosing_buzzer = State()
    choosing_alarm = State()


# ---------- Post-запросы ----------
async def set_alarm_code(new_code: str) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/set/alarm_code", json={"value": new_code}) as r:
            return r.status == 200


async def set_event(new_code: str) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/set/event", json={"value": new_code}) as r:
            return r.status == 200


async def set_window_open(is_open: bool) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/set/window_open", json={"value": is_open}) as r:
            return r.status == 200


async def set_control_mode(mode: str) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/set/control_mode", json={"value": mode}) as r:
            return r.status == 200


async def set_alarm_active(active: bool) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/set/alarm_active", json={"value": active}) as r:
            return r.status == 200


async def set_buzzer_active(active: bool) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/set/buzzer_active", json={"value": active}) as r:
            return r.status == 200


async def set_led_color(color: str) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{SERVER_URL}/set/led_color", json={"value": color}) as r:
            return r.status == 200


# ---------- Get-запросы ----------
async def get_alarm_code() -> str | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/alarm_code") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_event() -> str | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/event") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_pir_motion() -> bool | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/pir_motion") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_inside_presence() -> bool | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/inside_presence") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_last_mq2() -> int | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/last_mq2") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_last_ldr() -> int | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/last_ldr") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_last_temp() -> int | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/last_temp") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_last_hum() -> int | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/last_hum") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_window_open() -> bool | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/window_open") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_control_mode() -> str | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/control_mode") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_alarm_active() -> bool | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/alarm_active") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_buzzer_active() -> bool | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/buzzer_active") as r:
            if r.status == 200:
                return (await r.json())["value"]


async def get_led_color() -> str | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{SERVER_URL}/get/led_color") as r:
            if r.status == 200:
                return (await r.json())["value"]


# ---------- Отправка текстовых сообщений без маркеров ----------
async def send_text(text: str, chat_id: int = None):
    if chat_id is None:
        chat_id = default_chat_id

    try:
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"[BOT] Sent: {text}")
    except Exception as e:
        logger.error(f"[BOT] Error sending message: {e}")


# ---------- Рекомендации одежды ----------
async def send_clothing_recommendation(chat_id: int):
    temp = await get_last_temp()
    hum = await get_last_hum()

    if temp < 10 and hum > 70:
        text = (
            f"🌡 Температура: {temp}°C\n💧 Влажность: {hum}%\n\n"
            "Очень холодно и влажно. Рекомендую тёплую куртку, "
            "водонепроницаемую обувь и головной убор. "
            "Влажность повышена, охлаждение усиливается."
        )

    elif temp < 10 and hum <= 70:
        text = (
            f"🌡 Температура: {temp}°C\n💧 Влажность: {hum}%\n\n"
            "Холодно, но влажность в норме. Возьми тёплую куртку "
            "и перчатки. Основной фактор — низкая температура."
        )

    elif 10 <= temp < 20 and hum > 70:
        text = (
            f"🌡 Температура: {temp}°C\n💧 Влажность: {hum}%\n\n"
            "Прохладно и влажно. Возьми лёгкую куртку. "
            "Высокая влажность делает воздух холоднее ощущаемо."
        )

    elif 10 <= temp < 20 and hum <= 70:
        text = (
            f"🌡 Температура: {temp}°C\n💧 Влажность: {hum}%\n\n"
            "Прохладно, влажность нормальная. Подойдёт кофта или ветровка. "
            "Условия комфортные."
        )

    elif temp >= 20 and hum > 70:
        text = (
            f"🌡 Температура: {temp}°C\n💧 Влажность: {hum}%\n\n"
            "Тепло, но влажность повышена. Рекомендую лёгкую одежду, "
            "дышащие ткани. Влажность делает воздух душным."
        )

    else:
        text = (
            f"🌡 Температура: {temp}°C\n💧 Влажность: {hum}%\n\n"
            "Тепло и комфортно. Можно надевать обычную лёгкую одежду. "
            "Показатели в норме."
        )

    await send_text(text, chat_id)


# ---------- Inline-клавиатуры ----------
def main_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Рекомендации по одежде", callback_data="menu_weather"),
            ],
            [
                InlineKeyboardButton(text="Переключить режим", callback_data="menu_mode"),
            ],
            [
                InlineKeyboardButton(text="Опрос датчиков", callback_data="menu_state"),
            ],
            [
                InlineKeyboardButton(text="Сменить код сигнализации", callback_data="menu_code"),
            ]
        ]
    )


async def manual_mode_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Выйти из ручного режима", callback_data="exit_manual"),
            ],
            [
                InlineKeyboardButton(text="Опрос состояния", callback_data="check_state_manual"),
            ],
            [
                InlineKeyboardButton(text="Задать значение исполнительному элементу", callback_data="set_element_manual")
            ]
        ]
    )


# ---------- Хендлеры ----------
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    global default_chat_id

    default_chat_id = message.chat.id

    if await get_control_mode() != "auto":
        await set_control_mode("auto")
        logger.info("[MODE] Переключено в автоматический режим")

    text = (
        "Система умного дома активирована!\n\n"
        "Все системы работают в штатном режиме.\n\n"
        "Режим управления: автоматический\n\n"
        "Выберите действие:"
    )

    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="Markdown")


@router.message(F.text == "/weather")
async def cmd_weather(message: Message):
    await send_clothing_recommendation(message.chat.id)


@router.message(F.text == "/state")
async def cmd_state(message: Message):
    text = (
        "📟 Состояние системы:\n\n"
        f"💨 Есть кто дома? - {'да' if await get_inside_presence() else 'нет'}\n"
        f"👣 Есть движение перед домом? - : {'да' if await get_pir_motion() else 'нет'}\n"
        f"📏 Освещенность на улице - {await get_last_ldr()}\n"
        f"🪟 Уровень газа в доме - {await get_last_mq2()}\n"
        f"🔐 Температура на улице - {await get_last_temp()}\n"
        f"📏 Влажность на улице - {await get_last_hum()}\n"
        f"🪟 Цвет освещения (None - выключено) - {await get_led_color()}\n"
        f"🔐 Окно открыто? - {'да' if await get_window_open() else 'нет'}\n"
        f"🛠 Пищалка включена? - {'да' if await get_buzzer_active() else 'нет'}\n"
    )

    await send_text(text, message.chat.id)


@router.message(F.text == "/mode")
async def cmd_mode(message: Message, state: FSMContext):
    if await get_control_mode() == "auto":
        await go_manual(state)
        await set_control_mode("manual")
    else:
        await set_control_mode("auto")


@router.message(F.text == "/code")
async def cmd_code(message: Message, state: FSMContext):
    await send_text(
        "Введите новый 4-значный код сигнализации:",
        message.chat.id
    )

    await state.set_state(AlarmStates.waiting_for_code)


# ---------- Callback'и для inline-кнопок ----------
@router.callback_query(F.data == "menu_weather")
async def cb_weather(callback: CallbackQuery):
    await send_clothing_recommendation(callback.message.chat.id)


@router.callback_query(F.data == "menu_mode")
async def cb_mode(callback: CallbackQuery, state: FSMContext):
    if await get_control_mode() == "auto":
        await go_manual(state)
        await set_control_mode("manual")
    else:
        await set_control_mode("auto")

    await callback.answer()


@router.callback_query(F.data == "menu_state")
async def cb_state(callback: CallbackQuery):
    text = (
        "📟 Состояние системы:\n\n"
        f"💨 Есть кто дома? - {'да' if await get_inside_presence() else 'нет'}\n"
        f"👣 Есть движение перед домом? - : {'да' if await get_pir_motion() else 'нет'}\n"
        f"📏 Освещенность на улице - {await get_last_ldr()}\n"
        f"🪟 Уровень газа в доме - {await get_last_mq2()}\n"
        f"🔐 Температура на улице - {await get_last_temp()}\n"
        f"📏 Влажность на улице - {await get_last_hum()}\n"
        f"🪟 Цвет освещения (None - выключено) - {await get_led_color()}\n"
        f"🔐 Окно открыто? - {'да' if await get_window_open() else 'нет'}\n"
        f"🛠 Пищалка включена? - {'да' if await get_buzzer_active() else 'нет'}\n"
    )

    await send_text(text, callback.message.chat.id)
    await callback.answer()


@router.callback_query(F.data == "menu_code")
async def cb_code(callback: CallbackQuery, state: FSMContext):
    await send_text(
        "Введите новый 4-значный код сигнализации:",
        callback.message.chat.id
    )

    await state.set_state(AlarmStates.waiting_for_code)
    await callback.answer()


@router.callback_query(F.data == "exit_manual")
async def exit_manual_mode(callback: CallbackQuery):
    await set_control_mode("auto")
    await callback.answer()


@router.callback_query(F.data == "check_state_manual")
async def check_state_manual(callback: CallbackQuery):
    text = (
        "📟 Состояние системы:\n\n"
        f"💨 Есть кто дома? - {'да' if await get_inside_presence() else 'нет'}\n"
        f"👣 Есть движение перед домом? - : {'да' if await get_pir_motion() else 'нет'}\n"
        f"📏 Освещенность на улице - {await get_last_ldr()}\n"
        f"🪟 Уровень газа в доме - {await get_last_mq2()}\n"
        f"🔐 Температура на улице - {await get_last_temp()}\n"
        f"📏 Влажность на улице - {await get_last_hum()}\n"
        f"🪟 Цвет освещения (None - выключено) - {await get_led_color()}\n"
        f"🔐 Окно открыто? - {'да' if await get_window_open() else 'нет'}\n"
        f"🛠 Пищалка включена? - {'да' if await get_buzzer_active() else 'нет'}\n"
    )
    await send_text(text, callback.message.chat.id)
    await callback.answer()


@router.callback_query(F.data == "set_element_manual")
async def cb_set_element(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ManualControl.choosing_element)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Свет (LED)", callback_data="el_led")],
            [InlineKeyboardButton(text="Окно (серво)", callback_data="el_window")],
            [InlineKeyboardButton(text="Пищалка", callback_data="el_buzzer")],
            [InlineKeyboardButton(text="Сигнализация", callback_data="el_alarm")],
            [InlineKeyboardButton(text="Отмена", callback_data="el_cancel")]
        ]
    )

    await bot.send_message(callback.message.chat.id,
                           "Выберите исполнительный элемент:",
                           reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("el_"), ManualControl.choosing_element)
async def choose_element(callback: CallbackQuery, state: FSMContext):
    choice = callback.data

    match choice:
        case "el_cancel":
            await state.clear()
            await bot.send_message(callback.message.chat.id,
                                   "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности. Выберите, что вы хотите сделать.",
                                   reply_markup=await manual_mode_menu())
            return await callback.answer()


        case "el_led":
            await state.set_state(ManualControl.choosing_led_color)

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Красный", callback_data="led_red")],
                    [InlineKeyboardButton(text="Зеленый", callback_data="led_green")],
                    [InlineKeyboardButton(text="Синий", callback_data="led_blue")],
                    [InlineKeyboardButton(text="Жёлтый", callback_data="led_yellow")],
                    [InlineKeyboardButton(text="Выключить", callback_data="led_off")],
                    [InlineKeyboardButton(text="Назад", callback_data="led_back")]
                ]
            )

            await bot.send_message(callback.message.chat.id, "Выберите цвет LED:", reply_markup=keyboard)
            return await callback.answer()


        case "el_window":
            await state.set_state(ManualControl.choosing_window)

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Открыть", callback_data="win_open")],
                    [InlineKeyboardButton(text="Закрыть", callback_data="win_close")],
                    [InlineKeyboardButton(text="Назад", callback_data="win_back")]
                ]
            )

            await bot.send_message(callback.message.chat.id, "Управление окном:", reply_markup=keyboard)
            return await callback.answer()

        case "el_buzzer":
            await state.set_state(ManualControl.choosing_buzzer)

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Включить", callback_data="buzz_on")],
                    [InlineKeyboardButton(text="Выключить", callback_data="buzz_off")],
                    [InlineKeyboardButton(text="Назад", callback_data="buzz_back")]
                ]
            )

            await bot.send_message(callback.message.chat.id, "Управление пищалкой:",  reply_markup=keyboard)
            return await callback.answer()

        case "el_alarm":
            await state.set_state(ManualControl.choosing_alarm)

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Включить", callback_data="alarm_on")],
                    [InlineKeyboardButton(text="Выключить", callback_data="alarm_off")],
                    [InlineKeyboardButton(text="Назад", callback_data="alarm_back")]
                ]
            )

            await bot.send_message(callback.message.chat.id, "Управление сигнализацией:",  reply_markup=keyboard)
            return await callback.answer()


@router.callback_query(ManualControl.choosing_led_color)
async def led_control(callback: CallbackQuery, state: FSMContext):
    data = callback.data

    if data == "led_back":
        await state.set_state(ManualControl.choosing_element)
        return await cb_set_element(callback, state)

    if data == "led_off":
        await set_led_color("None")
        await callback.answer("LED выключен")
    else:
        color = data.replace("led_", "")
        await set_led_color(color)
        await callback.answer(f"LED установлен: {color}")

    await state.clear()
    await bot.send_message(callback.message.chat.id,
                           "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности. Выберите, что вы хотите сделать.",
                           reply_markup=await manual_mode_menu())
    return None


@router.callback_query(ManualControl.choosing_window)
async def window_control(callback: CallbackQuery, state: FSMContext):
    data = callback.data

    if data == "win_back":
        await state.set_state(ManualControl.choosing_element)
        return await cb_set_element(callback, state)

    opened = data == "win_open"
    await set_window_open(opened)

    await callback.answer()
    await state.clear()
    await bot.send_message(callback.message.chat.id,
                           "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности. Выберите, что вы хотите сделать.",
                           reply_markup=await manual_mode_menu())
    return None


@router.callback_query(ManualControl.choosing_buzzer)
async def buzzer_control(callback: CallbackQuery, state: FSMContext):
    data = callback.data

    if data == "buzz_back":
        await state.set_state(ManualControl.choosing_element)
        return await cb_set_element(callback, state)

    enabled = data == "buzz_on"
    await set_buzzer_active(enabled)

    await callback.answer()
    await state.clear()
    await bot.send_message(callback.message.chat.id,
                           "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности. Выберите, что вы хотите сделать.",
                           reply_markup=await manual_mode_menu())
    return None


@router.callback_query(ManualControl.choosing_alarm)
async def alarm_control(callback: CallbackQuery, state: FSMContext):
    data = callback.data

    if data == "alarm_back":
        await state.set_state(ManualControl.choosing_element)
        return await cb_set_element(callback, state)

    await set_alarm_active(data == "alarm_on")

    await send_text(
        f"Сигнализация {'включена' if await get_alarm_active() else 'выключена'}",
        callback.message.chat.id
    )

    await callback.answer()
    await state.clear()
    await bot.send_message(callback.message.chat.id,
                           "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности. Выберите, что вы хотите сделать.",
                           reply_markup=await manual_mode_menu())
    return None


# ---------- FSM ----------
@router.message(AlarmStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip()

    if not code.isdigit() or len(code) != 4:
        await message.answer("Код должен состоять из 4 цифр. Попробуйте снова.")
        return

    await set_alarm_code(code)
    await state.clear()
    await message.answer(f"Новый код сигнализации сохранён: {code}")


@router.message(AlarmCheckStates.waiting_for_alarm_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip()

    if not code.isdigit() or len(code) != 4:
        await message.answer("Код должен состоять из 4 цифр. Попробуйте снова.")
        return False

    await state.clear()

    if code != await get_alarm_code():
        return False

    return True


@router.message(CheckStates.checking_for_alarm_code)
async def alarm_code_entered(message: Message, state: FSMContext):
    entered = message.text.strip()

    if entered == await get_alarm_code():
        await message.answer("Код верный. Ручной режим активирован.")

        await set_control_mode("manual")
        await state.clear()
        await message.answer(
            "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности."
            "Выберите, что вы хотите сделать.",
            reply_markup=await manual_mode_menu()
        )
    else:
        await message.answer("❌ Код неверный. Попробуйте снова.")


# ---------- Переход в ручной режим ----------
async def go_manual(fsm_state: FSMContext):
    await send_text(
        "Внимание! При переходе в ручной режим все автоматические системы будут остановлены. "
        "Для подтверждения действия отправьте код в чат",
        default_chat_id
    )

    await fsm_state.set_state(CheckStates.checking_for_alarm_code)
    await set_control_mode("manual")


async def check_event():
    try:
        logger.info("Информатор запущен")
        while True:
            if get_control_mode() == "auto":
                match get_event():
                    case "None":
                        pass
                    case "Gas, open":
                        await send_text("Внимание! Превышен уровень газа в воздухе. Окно открыто")
                    case "Gas, close":
                        await send_text("Уровень газа в норме. Окно закрыто")
                    case "Illegal access":
                        await send_text("Внимание! Несанкционированное проникновение в домЙ")
                    case "Moving near":
                        await send_text("Обнаружено движение перед домом")
                    case "Light_on":
                        await send_text("Стемнело. Свет включен")
                    case "Light_off":
                        await send_text("Посветлело. Свет выключен")

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Информатор остановлен")


# ---------- Логирование ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ---------- Бот и диспетчер ----------
bot = Bot(
    token=bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
logger.info("Bot and dispatcher initialized. State object created.")


# ---------- Запуск ----------
dp.include_router(router)
async def main():
    global task
    logger.info("Бот запускается...")
    try:
        await dp.start_polling(bot)
        task = asyncio.create_task(check_event())
    finally:
        await bot.session.close()
        logger.info("Бот завершил работу.")


if __name__ == "__main__":
    asyncio.run(main())