import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup


router = Router()

# -------------------------------------------------------
# Логирование
# -------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# Фоновые задачи
background_tasks = []

# -------------------------------------------------------
# Состояние процесса
# -------------------------------------------------------

class GlobalState:
    def __init__(self):
        # 1. Токен бота
        self.bot_token: str = "8241496751:AAH9DmunV9DkQmpxW_Tq2K7ScpQwsPFNHKs"

        # 2. Код от сигнализации
        self.alarm_code: str = "1234"

        # 3. Порог MQ-2 (датчик газа)
        self.gas_threshold: int = 300

        # 4. Порог LDR (фоторезистор)
        self.light_threshold: int = 500

        # 5. PIR — есть движение на крыльце?
        self.pir_motion: bool = False

        # 6. HC-SR04 — есть кто внутри?
        self.inside_presence: bool = False

        # 7. Времена задержек (в секундах)
        self.alarm_activation_delay: int = 10      # время включения сигнализации после установки
        self.siren_delay: int = 10                 # время запуска сирены при присутствии

        # 8. Состояние окна
        self.window_open: bool = False

        # 9. Управление
        self.control_mode: str = "none"            # "auto" или "manual"

        # 10. Чат по умолчанию
        self.default_chat_id: int = 0

        # 11. Последний результат измерения MQ-2 (датчик газа)
        self.last_mq2: int = 0

        # 12. Последний результат измерения LDR (фоторезистор)
        self.last_ldr: int = 0

        # 13. Состояние сигнализации
        self.alarm_active: bool = False

        # 14. Цвет света
        self.led_color: str = "white"


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

# Глобальное состояние процесса
gb_state = GlobalState()

# -------------------------------------------------------
#   Создание объектов
# -------------------------------------------------------
bot = Bot(
    token=gb_state.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

logger.info("Bot and dispatcher initialized. State object created.")


# =====================================================================
#  Функции управления элементами в Wokwi
# =====================================================================

async def set_led(color: str | None):
    """
    Меняет цвет светодиода или выключает его.
    color: 'red', 'green', 'blue', 'yellow' и т.п.
    Если color=None — выключить LED.
    """
    logger.info(f"[LED] Установлен цвет: {color}")
    # Здесь позже появится код работы с пинами Wokwi
    await asyncio.sleep(0)


async def set_window(opened: bool):
    """
    Управление окном (серводвигатель).
    opened=True  -> открыть окно
    opened=False -> закрыть окно
    """
    gb_state.window_open = opened
    logger.info(f"[SERVO] Окно {'открыто' if opened else 'закрыто'}")
    await send_text(
        f"[SERVO] Окно {'открыто' if opened else 'закрыто'}",
        gb_state.default_chat_id
    )
    # servo.write(0/90/180) — здесь будет Wokwi
    await asyncio.sleep(0)


async def set_buzzer(enabled: bool):
    """
    Включение/выключение пищалки (сирены).
    """
    logger.info(f"[BUZZER] {'ВКЛЮЧЕНА' if enabled else 'ВЫКЛЮЧЕНА'}")
    # buzzer.on() / buzzer.off()
    await asyncio.sleep(0)


# =====================================================================
#  Обработка пин-кода
# =====================================================================

async def wait_for_alarm_code(timeout: int = 10) -> str | None:
    """
    Ждёт ввод кода с физической клавиатуры в течение timeout секунд.
    Возвращает введённый код или None если время вышло.

    В реальности будет подписка на события кнопок Wokwi.
    """
    logger.info("[KEYPAD] Ожидание кода…")

    entered_code = ""
    start = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start < timeout:
        await asyncio.sleep(0.05)

        # Здесь будет чтение кнопок:
        # pressed = keypad.get_pressed()
        pressed = None  # заглушка

        if pressed is not None:
            entered_code += pressed
            logger.info(f"[KEYPAD] Нажато: {pressed}")

            # Если Enter — вернуть
            if pressed == "#":
                return entered_code.replace("#", "")

    logger.info("[KEYPAD] Время ожидания кода истекло.")
    return None


# =====================================================================
#  Функция для датчика температуры и влажности DHT22
# =====================================================================

async def read_dht22():
    """
    Функция чтения температуры и влажности с DHT22.
    В финальном варианте будет читать реальные значения,
    пока поставим заглушку для Wokwi.
    """
    # Здесь будет: temp, humidity = dht22.read()
    temp = 22.5       # заглушка
    humidity = 55.0   # заглушка

    logger.info(f"[DHT22] temp={temp}, humidity={humidity}")
    return temp, humidity


# =====================================================================
#  Опрос датчиков (LDR, PIR, HC-SR04, MQ-2)
#  Вызывают callback только при изменениях состояний или превышении порога
# =====================================================================

async def watch_ldr(callback):
    """
    Отслеживает фоторезистор.
    Вызывает callback(is_dark: bool) только если состояние 'темно/светло' изменилось.
    """
    prev_dark = None
    try:
        while True:
            await asyncio.sleep(0.1)

            # value = adc.read() — здесь будет реальное чтение
            value = gb_state.light_threshold - 50  # заглушка
            gb_state.last_ldr = value
            is_dark = value < gb_state.light_threshold

            if is_dark != prev_dark:
                prev_dark = is_dark
                logger.info(f"[LDR] {'Темно' if is_dark else 'Светло'} (value={value})")
                await callback(is_dark)
    except asyncio.CancelledError:
        logger.info("watch_ldr завершён")
        raise


async def watch_pir(callback):
    """
    Отслеживает PIR.
    Вызывает callback(motion: bool) только при смене состояния.
    motion=True — движение обнаружено.
    """
    prev_motion = None
    try:
        while True:
            await asyncio.sleep(0.1)

            # motion = pir.value()
            motion = False  # заглушка

            if motion != prev_motion:
                prev_motion = motion
                gb_state.pir_motion = motion
                logger.info(f"[PIR] Движение: {motion}")
                await callback(motion)
    except asyncio.CancelledError:
        logger.info("watch_pir завершён")
        raise


async def watch_ultrasonic(callback, distance_threshold: int = 100):
    """
    Отслеживает ультразвуковой дальномер HC-SR04.
    Вызывает callback(presence: bool) при входе в зону ближе distance_threshold и выходе из неё.
    presence=True — объект ближе порога.
    """
    prev_presence = None
    try:
        while True:
            await asyncio.sleep(0.2)

            # distance = ultrasonic.read_cm()
            distance = 1000  # заглушка

            presence = distance < distance_threshold

            if presence != prev_presence:
                prev_presence = presence
                gb_state.inside_presence = presence
                logger.info(f"[HC-SR04] Присутствие: {presence} (distance={distance})")
                await callback(presence)
    except asyncio.CancelledError:
        logger.info("watch_ultrasonic завершён")
        raise


async def watch_gas(callback):
    """
    Отслеживает датчик MQ-2 (газ).
    Вызывает callback(level: int, danger: bool) только при переходах:
      - норм → опасность
      - опасность → норм
    """
    prev_danger = False
    try:
        while True:
            await asyncio.sleep(0.2)

            # gas = mq2.read()
            gas = gb_state.gas_threshold # заглушка

            gb_state.last_mq2 = gas

            danger = gas > gb_state.gas_threshold

            if danger != prev_danger:
                prev_danger = danger
                logger.info(f"[MQ-2] Газ={gas}, опасность={danger}")
                await callback(danger)
    except asyncio.CancelledError:
        logger.info("watch_gas завершён")
        raise



# ---------------------------------------------------------
# Рекомендации по одежде
# ---------------------------------------------------------

async def send_clothing_recommendation(chat_id: int):
    """
    Получает температуру и влажность → отправляет одну из 6 рекомендаций.
    Рекомендации сделаны так, что по тексту ясно,
    какие показатели завышены/занижены.
    """

    temp, hum = await read_dht22()

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

    else:  # temp >= 20 and hum <= 70
        text = (
            f"🌡 Температура: {temp}°C\n💧 Влажность: {hum}%\n\n"
            "Тепло и комфортно. Можно надевать обычную лёгкую одежду. "
            "Показатели в норме."
        )

    await send_text(text, chat_id)


async def send_text(text: str, chat_id: int = None):
    """
    Универсальная функция отправки сообщения в Telegram.
    """

    if chat_id is None:
        chat_id = gb_state.default_chat_id

    try:
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"[BOT] Sent: {text}")
    except Exception as e:
        logger.error(f"[BOT] Error sending message: {e}")


# ================================================================
#   Хелперы
# ================================================================

def main_menu_kb():
    """
        Inline-клавиатура главного меню
    """
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
    """
            Inline-клавиатура главного меню
    """
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
# =====================================================================
#   Хендлеры
# =====================================================================


# =====================================================================
#   /start — запуск
# =====================================================================

@router.message(F.text == "/start")
async def cmd_start(message: Message):

    gb_state.default_chat_id = message.chat.id

    # Переключаем в автоматический режим, если не в нём
    if gb_state.control_mode != "auto":
        await go_auto()
        logger.info("[MODE] Переключено в автоматический режим")

    text = (
        "Система умного дома активирована!\n\n"
        "Все системы работают в штатном режиме.\n\n"
        "Режим управления: автоматический\n\n"
        "Выберите действие:"
    )

    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="Markdown")


# =====================================================================
#   /weather — рекомендации по одежде
# =====================================================================

@router.message(F.text == "/weather")
async def cmd_weather(message: Message):
    await send_clothing_recommendation(message.chat.id)


# =====================================================================
#   /state — опрос всех датчиков
# =====================================================================

@router.message(F.text == "/state")
async def cmd_state(message: Message):
    text = (
        "📟  Состояние системы:\n\n"
        f"💨 Газ (MQ-2): {'ПРЕВЫШЕН' if gb_state.last_mq2 > gb_state.gas_threshold else 'норма'} ({gb_state.last_mq2})\n"
        f"💡 Освещённость (LDR): {gb_state.last_ldr}\n"
        f"👣 Движение (PIR): {'есть движение' if gb_state.pir_motion else 'нет'}\n"
        f"📏 Есть кто внутри? (HC-SR04): {'да' if gb_state.inside_presence else 'нет'}\n"
        f"🪟 Окно: {'открыто' if gb_state.window_open else 'закрыто'}\n"
        f"🔐 Сигнализация: {'включена' if gb_state.alarm_active else 'выключена'}\n"
        f"🛠 Режим управления: {gb_state.control_mode}\n"
    )

    await send_text(text, message.chat.id)


# =====================================================================
#   /mode — переключение режима
# =====================================================================

@router.message(F.text == "/mode")
async def cmd_mode(message: Message, state: FSMContext):
    if gb_state.control_mode == "auto":
        await go_manual(state)
    else:
        await go_auto()



# =====================================================================
#   /code — смена кода сигнализации
# =====================================================================

@router.message(F.text == "/code")
async def cmd_code(message: Message, state: FSMContext):
    await state.set_state(AlarmStates.waiting_for_code)
    await send_text(
        "Введите новый 4-значный код сигнализации:",
        message.chat.id
    )


# =====================================================================
#   FSM
# =====================================================================

@router.message(AlarmStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip()

    if not code.isdigit() or len(code) != 4:
        await message.answer("Код должен состоять из 4 цифр. Попробуйте снова.")
        return

    await state.update_data(alarm_code=code)

    await state.clear()

    await message.answer(f"Новый код сигнализации сохранён: {code}")


@router.message(AlarmCheckStates.waiting_for_alarm_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip()

    if not code.isdigit() or len(code) != 4:
        await message.answer("Код должен состоять из 4 цифр. Попробуйте снова.")
        return False

    await state.clear()

    if code != gb_state.alarm_code:
        return False

    return True


@router.message(CheckStates.checking_for_alarm_code)
async def alarm_code_entered(message: Message, state: FSMContext):
    entered = message.text.strip()

    # Проверяем код
    if entered == gb_state.alarm_code:
        await message.answer("Код верный. Ручной режим активирован.")

        gb_state.control_mode = "manual"

        # Убираем состояние
        await state.clear()

        # Показываем меню ручного режима
        await message.answer(
            "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности. "
            "Выберите, что вы хотите сделать.",
            reply_markup=await manual_mode_menu()
        )
    else:
        await message.answer("❌ Код неверный. Попробуйте снова.")




# =====================================================================
#   Callback'и для inline кнопок
# =====================================================================

@router.callback_query(F.data == "menu_weather")
async def cb_weather(callback: CallbackQuery):
    await send_clothing_recommendation(callback.message.chat.id)


@router.callback_query(F.data == "menu_mode")
async def cb_mode(callback: CallbackQuery, state: FSMContext):
    if gb_state.control_mode == "auto":
        await go_manual(state)
    else:
        await go_auto()

    await callback.answer()


@router.callback_query(F.data == "menu_state")
async def cb_state(callback: CallbackQuery):
    text = (
        "📟  Состояние системы:\n\n"
        f"💨 Газ (MQ-2): {'ПРЕВЫШЕН' if gb_state.last_mq2 > gb_state.gas_threshold else 'норма'} ({gb_state.last_mq2})\n"
        f"💡 Освещённость (LDR): {gb_state.last_ldr}\n"
        f"👣 Движение (PIR): {'есть движение' if gb_state.pir_motion else 'нет'}\n"
        f"📏 Есть кто внутри? (HC-SR04): {'да' if gb_state.inside_presence else 'нет'}\n"
        f"🪟 Окно: {'открыто' if gb_state.window_open else 'закрыто'}\n"
        f"🔐 Сигнализация: {'включена' if gb_state.alarm_active else 'выключена'}\n"
        f"🛠 Режим управления: {gb_state.control_mode}\n"
    )

    await send_text(text, callback.message.chat.id)
    await callback.answer()


@router.callback_query(F.data == "menu_code")
async def cb_code(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AlarmStates.waiting_for_code)
    await send_text(
        "Введите новый 4-значный код сигнализации:",
        callback.message.chat.id
    )

    await callback.answer()

@router.callback_query(F.data == "exit_manual")
async def exit_manual_mode(callback: CallbackQuery):
    gb_state.mode = "auto"
    await go_auto()
    await callback.answer()


@router.callback_query(F.data == "check_state_manual")
async def check_state_manual(callback: CallbackQuery):
    await send_text("Опрос состояния выполняется...", callback.message.chat.id)
    text = (
        "📟  Состояние системы:\n\n"
        # Получение значений напрямую из Wokwi
        f"🔐 Сигнализация: {'включена' if gb_state.alarm_active else 'выключена'}\n"
        f"🛠 Режим управления: {gb_state.control_mode}\n"
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

    await bot.send_message(gb_state.default_chat_id,
                           "Выберите исполнительный элемент:",
                           reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("el_"), ManualControl.choosing_element)
async def choose_element(callback: CallbackQuery, state: FSMContext):
    choice = callback.data

    if choice == "el_cancel":
        await state.clear()
        await bot.send_message(gb_state.default_chat_id,
                               "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности. Выберите, что вы хотите сделать.",
                               reply_markup=await manual_mode_menu())
        return await callback.answer()

    # Светодиод
    if choice == "el_led":
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

    # Окно
    if choice == "el_window":
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

    # Пищалка
    if choice == "el_buzzer":
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

    # Сигнализация
    if choice == "el_alarm":
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

    else:
        return None


@router.callback_query(ManualControl.choosing_led_color)
async def led_control(callback: CallbackQuery, state: FSMContext):
    data = callback.data

    if data == "led_back":
        await state.set_state(ManualControl.choosing_element)
        return await cb_set_element(callback, state)

    if data == "led_off":
        await set_led(None)
        await callback.answer("LED выключен")
    else:
        color = data.replace("led_", "")
        await set_led(color)
        await callback.answer(f"LED установлен: {color}")

    await state.clear()
    await bot.send_message(gb_state.default_chat_id,
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
    await set_window(opened)

    await callback.answer()
    await state.clear()
    await bot.send_message(gb_state.default_chat_id,
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
    await set_buzzer(enabled)

    await callback.answer()
    await state.clear()
    await bot.send_message(gb_state.default_chat_id,
                           "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности. Выберите, что вы хотите сделать.",
                           reply_markup=await manual_mode_menu())
    return None


@router.callback_query(ManualControl.choosing_alarm)
async def alarm_control(callback: CallbackQuery, state: FSMContext):
    data = callback.data

    if data == "alarm_back":
        await state.set_state(ManualControl.choosing_element)
        return await cb_set_element(callback, state)

    gb_state.alarm_active = (data == "alarm_on")

    await send_text(
        f"Сигнализация {'включена' if gb_state.alarm_active else 'выключена'}",
        callback.message.chat.id
    )

    await callback.answer()
    await state.clear()
    await bot.send_message(gb_state.default_chat_id,
                           "Теперь управление ведется в ручном режиме, вам доступно управление каждым элементом по отдельности. Выберите, что вы хотите сделать.",
                           reply_markup=await manual_mode_menu())
    return None


# =====================================================================
#   Запуск фоновых систем
# =====================================================================

async def on_startup():
    global background_tasks
    background_tasks.append(asyncio.create_task(watch_ldr(change_ldr)))
    background_tasks.append(asyncio.create_task(watch_pir(change_pir)))
    background_tasks.append(asyncio.create_task(watch_ultrasonic(change_ultrasonic)))
    background_tasks.append(asyncio.create_task(watch_gas(change_gas)))


# =====================================================================
#   Завершение работы фоновых систем
# =====================================================================

async def stop_background_tasks():
    global background_tasks
    for task in background_tasks:
        task.cancel()

    for task in background_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass

    background_tasks.clear()



# =====================================================================
#   Callback'и для фоновых систем
# =====================================================================

async def change_ldr(value):
    if value:
        await set_led(color=None)
    else:
        await set_led(gb_state.led_color)


async def change_pir(motion):
    if motion:
        await send_text('Внимание! Обнаружено движение возле дома!', gb_state.default_chat_id)


async def change_ultrasonic(presence, fsm_state: FSMContext | None = None):
    if presence:
        if gb_state.alarm_active:
            if await wait_for_alarm_code() == gb_state.alarm_code:
                await send_text(
                    'Добро пожаловать домой. Если это были не вы — срочно вызовите полицию!',
                    gb_state.default_chat_id
                )
                gb_state.alarm_active = False

            else:
                await set_buzzer(True)
                await send_text(
                    'Обнаружен несанкционированный доступ, клавиатура заблокирована. Отправьте код в чат',
                    gb_state.default_chat_id
                )

                if fsm_state and await fsm_state.set_state(AlarmCheckStates.waiting_for_alarm_code):
                    await send_text('Код верный, добро пожаловать', gb_state.default_chat_id)
                    await set_buzzer(False)
                else:
                    await send_text('Код неверный, снять не удалось', gb_state.default_chat_id)

        else:
            if await wait_for_alarm_code() == gb_state.alarm_code:
                await send_text(
                    'Код верный, сигнализация включится через 10 секунд',
                    gb_state.default_chat_id
                )
                asyncio.create_task(asyncio.sleep(10)).add_done_callback(
                    lambda _: setattr(gb_state, "alarm_active", True)
                )

            else:
                await send_text(
                    'Код неверный, клавиатура заблокирована. Отправьте код в чат',
                    gb_state.default_chat_id
                )

                if fsm_state and await fsm_state.set_state(AlarmCheckStates.waiting_for_alarm_code):
                    await send_text(
                        'Код верный, сигнализация включится через 10 секунд',
                        gb_state.default_chat_id
                    )
                    asyncio.create_task(asyncio.sleep(10)).add_done_callback(
                        lambda _: setattr(gb_state, "alarm_active", True)
                    )
                else:
                    await send_text(
                        'Код неверный, сигнализацию включить не удалось',
                        gb_state.default_chat_id
                    )



async def change_gas(danger):
    if danger:
        await send_text(
            'Внимание! Превышен уровень газа в воздухе!',
            gb_state.default_chat_id
        )
        await set_window(True)
    else:
        await send_text(
            'Уровень газа в воздухе нормальный!',
            gb_state.default_chat_id
        )
        await set_window(False)


# =====================================================================
#   Функции переключения режимов
# =====================================================================

async def go_manual(fsm_state: FSMContext):
    gb_state.control_mode = "manual"

    await send_text(
        "Внимание! При переходе в ручной режим все автоматические системы будут остановлены. "
        "Для подтверждения действия отправьте код в чат",
        gb_state.default_chat_id
    )

    # Устанавливаем состояние ожидания кода
    await fsm_state.set_state(CheckStates.checking_for_alarm_code)

    # Останавливаем автоматические фоновые задачи
    await stop_background_tasks()



async def go_auto():
    gb_state.control_mode = "auto"
    await on_startup()
    await send_text(
        'Работа ведется в автоматическом режиме',
        gb_state.default_chat_id
    )


# =====================================================
#   Запуск бота
# =====================================================
dp.include_router(router)

async def main():
    logger.info("Бот запускается...")
    try:
        await dp.start_polling(bot)
    finally:
        # Закрываем бот корректно
        await bot.session.close()
        logger.info("Бот завершил работу.")


if __name__ == "__main__":
    asyncio.run(main())