import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes, PreCheckoutQueryHandler

from config import TELEGRAM_TOKEN, FUEL_OPTIONS, TIERS, CAR_BRANDS, PAYMENT_TOKEN
from database import DatabaseManager

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Inicializar la base de datos
db = DatabaseManager()

# Estados de la conversación
(MODELO, P_MAX, K_MAX, CV_MIN, YEAR_RANGE, FUEL, CONFIRM) = range(7)

# --- Ayudantes ---
HELP_REMINDER = "\n\nUsa /ayuda para ver todos los comandos."
CANCEL_REMINDER = "\n\n<i>(Usa /cancelar para detener este proceso)</i>"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Maneja el comando /start.
    user = update.effective_user
    db.register_user(str(user.id), user.username)
    
    await update.message.reply_html(
        f"¡Hola, {user.first_name}! 👋\n\n"
        "Soy <b>Wallacar</b>, tu asistente personal para encontrar chollos de coches en Wallapop.\n\n"
        "Usa /ayuda para ver la lista de comandos disponibles."
    )

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Muestra la lista de comandos disponibles.
    await update.message.reply_html(
        "<b>🤖 COMANDOS DISPONIBLES</b>\n\n"
        "  - /buscar: Para crear una nueva alerta de búsqueda.\n"
        "  - /misbusquedas: Para ver tus alertas activas.\n"
        "  - /borrar: Para eliminar una de tus búsquedas.\n"
        "  - /planes: Para ver precios y mejorar tu cuenta.\n"
        "  - /cancelar: Para detener cualquier proceso en curso."
    )

async def mis_busquedas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Muestra las búsquedas activas del usuario.
    user_id = str(update.effective_user.id)
    searches = db.get_user_searches(user_id)
    tier = db.get_user_tier(user_id)
    limit = TIERS[tier]['max_searches']
    
    if not searches:
        await update.message.reply_text(f"❌ No tienes ninguna búsqueda activa.\nPlan actual: {tier.upper()} ({0}/{limit})" + HELP_REMINDER)
        return

    msg = f"📋 <b>TUS BÚSQUEDAS ({len(searches)}/{limit}):</b>\n\n"
    for i, s in enumerate(searches, 1):
        msg += (
            f"🔹 <b>{i}. {s['keywords']}</b>\n"
            f"   💰 Max: {s['p_max']}€ | 🛣️ Max: {s['k_max']}km\n"
            f"   🐎 Min: {s['cv_min']}cv | 📅 {s['year_min']}-{s['year_max']}\n"
            f"   ⛽ {s['fuel_label']}\n\n"
        )
    
    await update.message.reply_html(msg + HELP_REMINDER)

# --- BORRADO DE BÚSQUEDAS ---

async def borrar_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Muestra las búsquedas del usuario con botones para borrar.
    user_id = str(update.effective_user.id)
    searches = db.get_user_searches(user_id)
    
    if not searches:
        await update.message.reply_text("❌ No tienes ninguna búsqueda para borrar." + HELP_REMINDER)
        return

    keyboard = []
    for s in searches:
        # El callback_data contiene el ID de la búsqueda a borrar
        keyboard.append([InlineKeyboardButton(f"🗑️ {s['keywords']}", callback_data=f"del_{s['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👇 Haz clic en la búsqueda que quieres eliminar:", reply_markup=reply_markup)

async def borrar_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Elimina la búsqueda seleccionada.
    query = update.callback_query
    await query.answer()
    
    search_id = int(query.data.split("_")[1])
    db.delete_search(search_id)
    
    await query.edit_message_text("✅ Búsqueda eliminada correctamente." + HELP_REMINDER)


# --- PAGOS ---

async def planes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Muestra los planes de suscripción dinámicamente.
    user_id = str(update.effective_user.id)
    current_tier = db.get_user_tier(user_id)

    # Textos de los planes
    text_free = "<b>🆓 FREE</b>" + (" (Actual)" if current_tier == 'free' else "")
    text_premium = "<b>💎 PREMIUM</b>" + (" (Actual)" if current_tier == 'premium' else "")
    text_pro = "<b>🚀 PRO</b>" + (" (Actual)" if current_tier == 'pro' else "")

    # Botones dinámicos
    keyboard = []
    if current_tier == 'free':
        keyboard.append([InlineKeyboardButton("💎 Comprar Premium (9.99€/mes)", callback_data="buy_premium")])
    if current_tier != 'pro': # Siempre se puede subir a Pro
        keyboard.append([InlineKeyboardButton("🚀 Comprar Pro (29.99€/mes)", callback_data="buy_pro")])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await update.message.reply_html(
        "<b>💎 MEJORA TU CUENTA</b>\n\n"
        f"{text_free}\n"
        "• 1 Búsqueda\n"
        "• Sin fotos\n\n"
        f"{text_premium}\n"
        "• 10 Búsquedas\n"
        "• Fotos incluidas\n"
        "• Escaneo rápido (15 min)\n\n"
        f"{text_pro}\n"
        "• Búsquedas ILIMITADAS\n"
        "• Fotos incluidas\n"
        "• Escaneo Real-Time (5 min)\n" + HELP_REMINDER,
        reply_markup=reply_markup
    )

async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Inicia el proceso de pago.
    query = update.callback_query
    await query.answer()
    
    tier = query.data.split("_")[1] # premium o pro
    
    if not PAYMENT_TOKEN:
        await query.edit_message_text("⚠️ Los pagos están desactivados temporalmente.")
        return

    prices = {
        "premium": [LabeledPrice("Suscripción Premium (30 días)", 999)], # 9.99€
        "pro": [LabeledPrice("Suscripción PRO (30 días)", 2999)] # 29.99€
    }
    
    title = f"Wallacar {tier.capitalize()}"
    description = f"Acceso {tier.capitalize()} durante 30 días"
    payload = f"sub_{tier}_{update.effective_user.id}"
    
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=title,
        description=description,
        payload=payload,
        provider_token=PAYMENT_TOKEN,
        currency="EUR",
        prices=prices[tier],
        start_parameter="test-payment"
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Responde a la solicitud de pre-compra.
    query = update.pre_checkout_query
    # Si todo está bien, respondemos ok=True
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Maneja el pago exitoso.
    payment = update.message.successful_payment
    payload = payment.invoice_payload # ej: sub_premium_123456
    
    tier = payload.split("_")[1]
    user_id = str(update.effective_user.id)
    
    # Actualizar DB
    db.update_user_tier(user_id, tier, days=30)
    
    await update.message.reply_html(
        f"🎉 <b>¡PAGO RECIBIDO!</b>\n\n"
        f"Tu cuenta ha sido actualizada a <b>{tier.upper()}</b>.\n"
        "Disfruta de todas las ventajas durante 30 días. 🚀" + HELP_REMINDER
    )

# --- FLUJO DE BÚSQUEDA ---

async def buscar_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Inicia la conversación para crear una búsqueda.
    user_id = str(update.effective_user.id)
    tier = db.get_user_tier(user_id)
    current_searches = db.count_user_searches(user_id)
    max_searches = TIERS[tier]['max_searches']
    
    if current_searches >= max_searches:
        await update.message.reply_html(
            f"⛔ <b>Límite alcanzado</b>\n\n"
            f"Tu plan actual ({tier.upper()}) solo permite {max_searches} búsquedas.\n"
            "Usa /planes para mejorar tu cuenta."
        )
        return ConversationHandler.END

    await update.message.reply_html("✨ ¡Genial! Vamos a configurar tu nueva alerta.\n\nPrimero, dime el <b>modelo</b> que buscas (ej: BMW M3, Seat Ibiza, Golf GTI...):" + CANCEL_REMINDER)
    return MODELO

async def received_modelo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Guarda el modelo y pregunta el precio máximo.
    text = update.message.text.strip()
    found_brand = False
    for brand in CAR_BRANDS:
        if brand in text.lower():
            found_brand = True
            break
    
    if not found_brand:
        await update.message.reply_html(
            "❌ <b>Marca no reconocida</b>\n"
            "Por favor, asegúrate de escribir la marca del coche (ej: 'Audi A3', 'Ford Focus').\n"
            "Inténtalo de nuevo:" + CANCEL_REMINDER
        )
        return MODELO

    context.user_data['keywords'] = text
    await update.message.reply_html("💰 ¿Cuál es el <b>precio máximo</b> que quieres pagar? (solo el número, ej: 15000)" + CANCEL_REMINDER)
    return P_MAX

async def received_p_max(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Guarda el precio y pregunta los km máximos.
    context.user_data['p_max'] = int(update.message.text)
    await update.message.reply_html("🛣️ ¿Y el <b>kilometraje máximo</b>? (ej: 100000)" + CANCEL_REMINDER)
    return K_MAX

async def received_k_max(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Guarda los km y pregunta la potencia mínima.
    context.user_data['k_max'] = int(update.message.text)
    await update.message.reply_html("🐎 ¿Qué <b>potencia mínima (CV)</b> te interesa? (ej: 110). Pon 0 si no te importa." + CANCEL_REMINDER)
    return CV_MIN

async def received_cv_min(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Guarda los CV y pregunta el rango de años.
    context.user_data['cv_min'] = int(update.message.text)
    await update.message.reply_html(
        "📅 ¿Qué <b>rango de años</b> buscas? (Formato: min-max)\n"
        "Ejemplos:\n"
        "  - 2010-2020\n"
        "  - 2015-2025\n"
        "  - 0-9999 (si te da igual)" + CANCEL_REMINDER
    )
    return YEAR_RANGE

async def received_year_range(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Guarda el rango de años y pregunta el combustible.
    text = update.message.text.strip()
    try:
        if '-' in text:
            parts = text.split('-')
            y_min = int(parts[0])
            y_max = int(parts[1])
        else:
            y_min = 0
            y_max = 9999
    except ValueError:
        y_min = 0
        y_max = 9999

    context.user_data['year_min'] = y_min
    context.user_data['year_max'] = y_max
    
    keyboard = [
        [InlineKeyboardButton(label, callback_data=key) for key, (_, label) in FUEL_OPTIONS.items()],
        [InlineKeyboardButton("Cualquiera 🌍", callback_data="any")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html("⛽ Por último, elige el <b>combustible</b>:" + CANCEL_REMINDER, reply_markup=reply_markup)
    return FUEL

async def received_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Guarda el combustible y pide confirmación.
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    if choice == "any":
        context.user_data['fuel_code'] = ""
        context.user_data['fuel_label'] = "Cualquiera 🌍"
    else:
        context.user_data['fuel_code'] = FUEL_OPTIONS[choice][0]
        context.user_data['fuel_label'] = FUEL_OPTIONS[choice][1]

    search = context.user_data
    summary = (
        f"✅ ¡Búsqueda lista para guardar!\n\n"
        f"  - <b>Modelo:</b> {search['keywords']}\n"
        f"  - <b>Precio Máx:</b> {search['p_max']}€\n"
        f"  - <b>Kms Máx:</b> {search['k_max']} km\n"
        f"  - <b>CV Mín:</b> {search['cv_min']} CV\n"
        f"  - <b>Años:</b> {search['year_min']} - {search['year_max']}\n"
        f"  - <b>Combustible:</b> {search['fuel_label']}\n\n"
        "¿Es correcto?"
    )
    
    keyboard = [
        [InlineKeyboardButton("Sí, guardar ✅", callback_data="save")],
        [InlineKeyboardButton("No, empezar de nuevo ❌", callback_data="restart")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=summary, reply_markup=reply_markup, parse_mode='HTML')
    return CONFIRM

async def confirm_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Confirma y guarda la búsqueda en la base de datos.
    query = update.callback_query
    await query.answer()
    
    if query.data == "save":
        user_id = db.register_user(str(update.effective_user.id))
        db.add_search(user_id, context.user_data)
        await query.edit_message_text("¡Perfecto! He guardado tu búsqueda. Te avisaré en cuanto encuentre algo interesante. 🚀" + HELP_REMINDER)
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await query.edit_message_text("Ok, empecemos de nuevo.")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Dime el <b>modelo</b> que buscas:", parse_mode='HTML')
        return MODELO

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Cancela la conversación.
    await update.message.reply_text("Operación cancelada." + HELP_REMINDER)
    context.user_data.clear()
    return ConversationHandler.END

async def notify_startup(application: Application) -> None:
    # Notifica el arranque a todos los usuarios.
    users = db.get_all_users()
    logger.info(f"Notificando arranque a {len(users)} usuarios...")
    for user_id in users:
        try:
            await application.bot.send_message(chat_id=user_id, text="🟢 <b>Wallacar Bot está ONLINE</b>\nListo para buscar chollos. 🚀" + HELP_REMINDER, parse_mode='HTML')
        except Exception as e:
            logger.warning(f"No se pudo notificar al usuario {user_id}: {e}")

def main() -> None:
    # Inicia el bot de Telegram.
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN no configurado en .env")

    application = Application.builder().token(TELEGRAM_TOKEN).post_init(notify_startup).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("buscar", buscar_start)],
        states={
            MODELO: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_modelo)],
            P_MAX: [MessageHandler(filters.Regex(r'^\d+$'), received_p_max)],
            K_MAX: [MessageHandler(filters.Regex(r'^\d+$'), received_k_max)],
            CV_MIN: [MessageHandler(filters.Regex(r'^\d+$'), received_cv_min)],
            YEAR_RANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_year_range)],
            FUEL: [CallbackQueryHandler(received_fuel)],
            CONFIRM: [CallbackQueryHandler(confirm_search)]
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(CommandHandler("misbusquedas", mis_busquedas))
    application.add_handler(CommandHandler("borrar", borrar_start))
    application.add_handler(CommandHandler("planes", planes))
    
    # Handlers de Pagos
    application.add_handler(CallbackQueryHandler(buy_subscription, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(borrar_confirm, pattern="^del_"))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    application.add_handler(conv_handler)
    
    logger.info("🤖 El bot_handler de Telegram está en marcha...")
    application.run_polling()

if __name__ == "__main__":
    main()