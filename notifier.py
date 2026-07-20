import os
import requests
import matplotlib.pyplot as plt
from typing import Optional, List, Dict, Union, Any

from config import TELEGRAM_TOKEN, TIERS
from logger import logger

def detectar_urgencia(titulo: str, descripcion: str) -> str:
    #Analyzes text to detect urgency keywords.

    tokens = ["urge", "negociable", "mudanza", "divorcio", "falta de espacio", "arranca pero", "sin itv", "oportunidad", "chollo"]
    texto = (titulo + " " + descripcion).lower()
    encontrados = [t for t in tokens if t in texto]
    if encontrados:
        return "ALTA 🔥 (" + ", ".join(encontrados) + ")"
    return "Normal"

def calcular_puntuacion(precio: float, kms: int, anio: int, avg_mercado: Optional[float] = None) -> float:
    #Calculates an opportunity score (lower is better).

    current_year = 2026
    antiguedad = current_year - anio
    
    if kms < 1000 and antiguedad > 2:
        return 999999.0

    penalizacion_desgaste = 0.0
    if kms > 200000:
        penalizacion_desgaste = (kms - 200000) * 0.2

    score = (precio * 0.7) + (kms * 0.05) + (antiguedad * 500) + penalizacion_desgaste
    
    if avg_mercado:
        desviacion = (precio / avg_mercado)
        score = score * desviacion

    return round(score, 2)

def enviar_telegram(mensaje: str, chat_id: str, tier: str = 'free', foto_url: Optional[str] = None, inline_link: Optional[str] = None) -> None:
    #Sends a message to a SPECIFIC Telegram chat ID, respecting Tier limits.

    if not TELEGRAM_TOKEN:
        logger.warning("Telegram Token not configured.")
        return

    url_base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    
    # --- TIER CHECK: PHOTOS ---
    # Check if this tier is allowed to see photos
    allows_photos = TIERS.get(tier, {}).get('photos', False)
    
    if not allows_photos and foto_url:
        # If user is Free, we hide the photo and add a upsell message
        foto_url = None
        mensaje += "\n\n📷 <i>[Foto oculta. Pásate a Premium para verla]</i>"

    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "caption" if foto_url else "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    if inline_link:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": "🛒 VER EN WALLAPOP", "url": inline_link}]]
        }

    try:
        if foto_url and os.path.exists(foto_url):
            with open(foto_url, 'rb') as f:
                requests.post(f"{url_base}/sendPhoto", data=payload, files={'photo': f})
            # Remove local image after sending if it was a graph
            if "grafica_" in foto_url:
                os.remove(foto_url)
        elif foto_url and foto_url.startswith("http"):
            payload["photo"] = foto_url
            requests.post(f"{url_base}/sendPhoto", json=payload)
        else:
            requests.post(f"{url_base}/sendMessage", json=payload)
        
        logger.debug(f"Telegram notification sent to {chat_id} (Tier: {tier}).")
        
    except Exception as e:
        logger.error(f"Error sending Telegram message to {chat_id}: {e}")

def formatear_alerta(c: Dict[str, Any], stats: Optional[Dict[str, float]] = None, es_bajada: bool = False) -> str:
    #Formats the notification message for a car.

    avg = stats['avg'] if stats else c['precio'] * 1.2 # fallback
    ratio = c['precio'] / avg if avg else 1.0
    
    emoji_status = "🔴" 
    if ratio < 0.8: emoji_status = "🟢 (SUPER CHOLLO)"
    elif ratio < 1.0: emoji_status = "🟡 (Buen precio)"
    
    urgencia = detectar_urgencia(c['titulo'], c['descripcion'])
    margen = int(avg - c['precio']) if stats else 0
    
    titulo_msg = "🚨¡DESPLOME DE PRECIO!🚨" if es_bajada else "✨ ¡NUEVA OPORTUNIDAD!"
    
    msg = (
        f"{titulo_msg}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🚗 <b>{c['titulo']}</b>\n"
        f"💰 <b>Precio:</b> {int(c['precio'])}€ {emoji_status}\n"
        f"📅 <b>Año:</b> {c['año']} | 🛣️ <b>Kms:</b> {c['kms']}\n"
        f"🐎 <b>CV:</b> {c['cv']} | ⛽ <b>Comb:</b> {c.get('fuel', '?')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🧠 <b>Inteligencia de Mercado:</b>\n"
        f"📊 Media Modelo: {int(avg)}€\n"
        f"💰 Margen Potencial: +{margen}€\n"
        f"⚠️ Urgencia: {urgencia}\n"
    )
    return msg

def formatear_resumen_top(marca: str, top_coches: List[Dict[str, Any]]) -> str:
    #Generates a summary message for the top deals.

    msg = f"🏆 <b>TOP 5 MEJORES OPORTUNIDADES: {marca.upper()}</b> 🏆\n\n"
    for i, c in enumerate(top_coches, 1):
        precio, kms, anio, url, score = c
        msg += (
            f"{i}. <b>{int(precio)}€</b> | {anio} | {kms}km\n"
            f"   🔗 <a href='{url}'>Ver Anuncio</a> (Score: {score:.1f})\n\n"
        )
    return msg

def crear_grafica_precios(palabra_clave: str, precios: List[float]) -> Optional[str]:
    #Generates a histogram of prices for a search term.

    if len(precios) < 3: return None
    try:
        plt.figure(figsize=(8, 5))
        plt.hist(precios, bins=12, color='skyblue', edgecolor='black')
        plt.title(f'Distribución de Precios: {palabra_clave}')
        plt.grid(axis='y', alpha=0.3)
        path = f"grafica_{palabra_clave}.png"
        plt.savefig(path)
        plt.close()
        return path
    except Exception as e:
        logger.error(f"Error creating price graph: {e}")
        return None
