import time
import os
import random
from typing import List, Dict, Any

from config import DEFAULT_SCAN_TIME, DEFAULT_MIN_PRICE, FUEL_OPTIONS
from database import DatabaseManager
from scraper import WallapopScraper
from notifier import enviar_telegram, calcular_puntuacion, formatear_alerta, crear_grafica_precios, formatear_resumen_top
from logger import logger
import ui # Mantenemos UI solo para logs visuales en el servidor

# Inicializar la base de datos
db = DatabaseManager()

def construir_url(keywords: str) -> str:
    """
    Construye una URL de búsqueda genérica para la palabra clave.
    Obtenemos resultados amplios y los filtramos luego por usuario.
    """
    # Buscamos sin límite de precio ni km para capturar todo el mercado.
    # Luego filtraremos en memoria para cada usuario.
    return (
        f"https://es.wallapop.com/app/search?"
        f"keywords={keywords.replace(' ', '%20')}&"
        f"category_ids=100&min_sale_price={DEFAULT_MIN_PRICE}"
        f"&order_by=newest" # Importante: los más nuevos primero
    )

def es_un_coche_valido(item: Dict[str, Any], keywords: str) -> bool:
    # Filtra artículos no válidos (piezas, coches averiados, etc.).
    contenido = (item['titulo'] + " " + item['descripcion']).lower()
    palabras_clave = keywords.lower().split()

    if not any(p in item['titulo'].lower() for p in palabras_clave):
        return False

    lista_negra = [
        "despiece", "piezas", "siniestro", "golpe", "roto", "averiado", "para reparar", "donante", "culata"
    ]
    if any(p in contenido for p in lista_negra):
        return False

    if item['precio'] < DEFAULT_MIN_PRICE:
        return False

    return True

def procesar_palabra_clave(scraper: WallapopScraper, keywords: str) -> None:
    """
    1. Scrapea Wallapop en busca de una palabra clave.
    2. Guarda los coches en el Catálogo Global.
    3. Distribuye alertas a los usuarios interesados.
    """
    ui.log_step(f"Analizando mercado global para: [bold]{keywords}[/bold]...")
    
    # 1. SCRAPING (Una sola vez para todos los clientes)
    url = construir_url(keywords)
    try:
        raw_items = scraper.search(url)
    except Exception as e:
        ui.log_error(f"Error scrapeando {keywords}: {e}")
        return

    # 2. PROCESAMIENTO Y CATALOGACIÓN
    coches_validos = []
    for raw in raw_items:
        item = scraper.parse_item(raw)
        if item and es_un_coche_valido(item, keywords):
            coches_validos.append(item)
            # Guardamos en catálogo global
            db.insert_car(item)
            # Actualizamos puntuación global
            market_stats = db.get_market_stats(keywords)
            score = calcular_puntuacion(item['precio'], item['kms'], item['año'], market_stats['avg'] if market_stats else None)
            db.update_score(item['id'], score)

    # 3. DISTRIBUCIÓN A CLIENTES
    interesados = db.get_interested_users(keywords)
    if not interesados:
        logger.info(f"No se han encontrado usuarios activos para {keywords}")
        return

    for user in interesados:
        procesar_alertas_usuario(user, coches_validos, keywords)

def procesar_alertas_usuario(user: Dict[str, Any], coches: List[Dict[str, Any]], keywords: str) -> None:
    # Filtra y envía alertas personalizadas a un usuario específico.
    user_id = user['user_id']
    chat_id = user['telegram_id']
    tier = user['tier'] # Recuperamos el tier del usuario
    
    market_stats = db.get_market_stats(keywords)
    nuevas_para_user = 0
    
    for item in coches:
        # --- FILTROS PERSONALIZADOS DEL USUARIO ---
        if item['precio'] > user['p_max']: continue
        if item['kms'] > user['k_max']: continue
        if item['cv'] < user['cv_min']: continue
        
        # Filtro de años
        y_min = user.get('year_min', 0)
        y_max = user.get('year_max', 9999)
        if not (y_min <= item['año'] <= y_max): continue
        
        # Filtro de combustible
        req_fuel = user['fuel_label']
        det_fuel = item.get('fuel')
        if "Cualquiera" not in req_fuel and det_fuel:
            req_clean = req_fuel.split()[0].lower()
            det_clean = det_fuel.lower()
            match = False
            if req_clean in det_clean: match = True
            if req_clean == "diesel" and "diésel" in det_clean: match = True
            if req_clean == "electrico" and "eléctrico" in det_clean: match = True
            if not match: continue

        # --- VERIFICACIÓN DE DUPLICADOS ---
        if db.has_user_seen_car(user_id, item['id']):
            continue # Ya se lo enviamos antes

        # --- ENVÍO DE ALERTA ---
        msg = formatear_alerta(item, market_stats)
        # Pasamos el tier para que notifier decida si enviar foto o no
        enviar_telegram(msg, chat_id, tier=tier, foto_url=item['foto'], inline_link=item['url'])
        
        # Marcar como visto para este usuario
        db.mark_car_as_seen(user_id, item['id'])
        nuevas_para_user += 1

    # --- RESUMEN FINAL (Opcional, solo si hubo novedades) ---
    if nuevas_para_user > 0:
        # Enviar gráfica y top 5 personalizado
        enviar_resumen_personalizado(user, keywords)
        
        # --- RECORDATORIO DE COMANDOS ---
        msg_comandos = (
            "🤖 <b>¿Qué quieres hacer ahora?</b>\n\n"
            "👉 /buscar - Crear nueva alerta\n"
            "👉 /misbusquedas - Ver mis alertas\n"
            "👉 /cancelar - Detener proceso"
        )
        enviar_telegram(msg_comandos, chat_id, tier=tier)

def enviar_resumen_personalizado(user: Dict[str, Any], keywords: str) -> None:
    # Envía el Top 5 y la gráfica al usuario.
    chat_id = user['telegram_id']
    tier = user['tier']
    
    # Top 5 Global (podríamos personalizarlo también, pero el global suele ser relevante)
    top_deals = db.get_top_deals(keywords, limit=5)
    precios = db.get_all_prices(keywords)
    
    if top_deals:
        summary_msg = formatear_resumen_top(keywords, top_deals)
        graph_path = None
        if len(precios) > 5:
            graph_path = crear_grafica_precios(keywords, precios)
        
        # Pasamos el tier también aquí (aunque la gráfica suele ser un gancho visual bueno para todos)
        # Si quieres restringir la gráfica a Premium, podrías hacerlo aquí.
        # Por ahora, dejamos la gráfica para todos como "cebo", pero las fotos de coches individuales restringidas.
        enviar_telegram(summary_msg, chat_id, tier=tier, foto_url=graph_path)

def main() -> None:
    # Bucle principal de SaaS.
    ui.show_banner()
    logger.info("🚀 Iniciando el servidor SaaS de Wallacar...")
    
    scraper = WallapopScraper()

    while True:
        try:
            # 1. Obtener qué hay que buscar hoy
            keywords_list = db.get_all_unique_keywords()
            
            if not keywords_list:
                logger.warning("No hay búsquedas activas en la BD. Esperando a los usuarios de Telegram...")
                time.sleep(60) # Espera 1 minuto antes de volver a comprobar la BD
                continue

            ui.log_vps_status(f"Iniciando ciclo para {len(keywords_list)} modelos distintos...")
            
            # --- OPTIMIZACIÓN: Arrancamos el navegador UNA vez por ciclo ---
            scraper.start()
            
            for kw in keywords_list:
                procesar_palabra_clave(scraper, kw)
                time.sleep(5) # Pequeña pausa entre modelos
            
            # --- FIN DEL CICLO: Cerramos navegador ---
            scraper.stop()
            
            ui.log_vps_status("Mantenimiento de BD...")
            db.set_inactive_old_cars(days=1)
            db.clean_old_records(days=30)
            
            ui.log_success(f"Ciclo completado. Durmiendo {DEFAULT_SCAN_TIME} min.")
            time.sleep(DEFAULT_SCAN_TIME * 60)
            
        except KeyboardInterrupt:
            logger.info("Deteniendo servidor...")
            break
        except Exception as e:
            logger.critical(f"Caída del servidor: {e}")
            try: scraper.stop() 
            except: pass
            time.sleep(300)

if __name__ == "__main__":
    main()