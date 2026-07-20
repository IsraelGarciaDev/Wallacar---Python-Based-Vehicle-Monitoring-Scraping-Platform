import time
import random
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Optional, Dict, Any

from config import USER_AGENTS, HEADLESS
from logger import logger

class WallapopScraper:
    def __init__(self) -> None:
        self.driver = None

    def _get_options(self) -> webdriver.ChromeOptions:
        # Genera opciones de Chrome con un User-Agent aleatorio para cada sesión.
        options = webdriver.ChromeOptions()
        if HEADLESS:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # ROTACIÓN REAL: Elegimos un UA nuevo cada vez que llamamos a esta función
        ua = random.choice(USER_AGENTS)
        options.add_argument(f"user-agent={ua}")
        logger.debug(f"🎭 User-Agent asignado: {ua[:50]}...")
        
        return options

    def start(self) -> None:
        # Inicializa el driver de Chrome usando WebDriver Manager.
        try:
            service = Service(ChromeDriverManager().install())
            # Generamos opciones nuevas (con nuevo UA) en cada arranque
            self.driver = webdriver.Chrome(service=service, options=self._get_options())
            
            # Antidetección: eliminar la propiedad webdriver
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("🚀 Scraper iniciado (Modo Stealth)")
        except Exception as e:
            logger.critical(f"❌ Error al inicializar el driver de Chrome: {e}")
            raise e

    def stop(self) -> None:
        # Detiene el driver.
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error al cerrar el driver: {e}")

    def random_sleep(self, min_s: float, max_s: float) -> None:
        # Espera un tiempo aleatorio.
        time.sleep(random.uniform(min_s, max_s))

    def handle_cookies(self) -> None:
        # Inyecta un limpiador persistente de cookies en la página.
        if not self.driver: return
        
        logger.debug("🛡️  Inyectando limpieza atómica de cookies...")
        script = """
        const cleanCookies = () => {
            const selectors = [
                '#onetrust-accept-btn-handler', '#didomi-notice-agree-button',
                'button[id*="accept"]', 'button[class*="accept"]',
                '.didomi-continue-without-agreeing', '[aria-label*="aceptar"]'
            ];
            selectors.forEach(s => {
                const b = document.querySelector(s);
                if (b && b.offsetParent !== null) b.click();
            });
            // Fuerza bruta: eliminar capas de bloqueo
            const overlays = document.querySelectorAll('[id*="didomi"], [id*="onetrust"], [class*="didomi"], [class*="overlay"]');
            overlays.forEach(el => el.remove());
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
        };
        cleanCookies();
        // Ejecutamos una vez más un poco después por si acaso
        setTimeout(cleanCookies, 1500);
        """
        try:
            self.driver.execute_script(script)
        except Exception as e:
            logger.debug(f"Error en el script de cookies: {e}")

    def load_more_results(self, max_seconds: int = 60) -> None:
        """
        Scroll orgánico y constante mediante JavaScript con intervalos aleatorios.
        Simula un comportamiento humano rápido pero imperfecto.
        """
        if not self.driver: return
        
        logger.info("📥 Cargando resultados (Velocidad Orgánica)...")
        start_time = time.time()
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        last_change_time = time.time()

        # Inyectamos un bucle recursivo con setTimeout aleatorio en lugar de setInterval fijo
        self.driver.execute_script("""
            window._stopScroller = false;
            
            function humanLikeLoop() {
                if (window._stopScroller) return;

                // 1. Scroll con pequeña variación (no siempre al píxel exacto del fondo)
                const variation = Math.floor(Math.random() * 100); 
                window.scrollTo(0, document.body.scrollHeight - variation);

                // 2. Clicker avanzado (Shadow DOM)
                const wallaButtons = document.querySelectorAll('walla-button');
                let clicked = false;
                
                wallaButtons.forEach(wb => {
                    const shadow = wb.shadowRoot;
                    if (shadow) {
                        const btn = shadow.querySelector('button');
                        if (btn) {
                             const text = btn.textContent.toLowerCase();
                             if (text.includes('cargar m') || text.includes('ver m')) {
                                 btn.click();
                                 clicked = true;
                             }
                        }
                    }
                });

                // 3. Botones normales
                if (!clicked) {
                    document.querySelectorAll('button').forEach(b => {
                        const t = b.innerText.toLowerCase();
                        if (t.includes('ver m') || t.includes('cargar m')) b.click();
                    });
                }

                // 4. Siguiente ciclo con tiempo aleatorio (Humanización)
                // Entre 150ms y 450ms: Rápido, pero no robótico
                const nextAction = Math.floor(Math.random() * 300) + 150;
                setTimeout(humanLikeLoop, nextAction);
            }

            humanLikeLoop();
        """)

        # Control en Python: Monitorizamos el progreso
        while (time.time() - start_time) < max_seconds:
            self.random_sleep(0.8, 1.2) # Comprobamos cada ~1 segundo
            try:
                new_height = self.driver.execute_script("return document.body.scrollHeight")
            except:
                break

            if new_height > last_height:
                last_height = new_height
                last_change_time = time.time()
            elif (time.time() - last_change_time) > 4.0:
                # Si en 4 segundos no ha cambiado la altura, asumimos fin
                logger.info("🏁 Fin de resultados detectado.")
                break

        # Detener el bucle JS
        try:
            self.driver.execute_script("window._stopScroller = true;")
        except:
            pass

    def extract_items(self) -> List[Dict[str, Any]]:
        # Extracción masiva tras la carga total.
        if not self.driver: return []

        # Un último scroll arriba y abajo para asegurar carga de imágenes (Lazy Load)
        self.driver.execute_script("window.scrollTo(0, 0);")
        self.random_sleep(0.5, 1.0)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.random_sleep(0.5, 1.0)

        script_js = """
        return Array.from(document.querySelectorAll('a[class*="item-card_ItemCard"]')).map(item => {
            const img = item.querySelector('img');
            return {
                titulo: item.querySelector('h3')?.innerText || "",
                precio_txt: item.querySelector('strong[aria-label="Item price"]')?.innerText || "0",
                url: item.href,
                info_label: item.querySelector('label')?.innerText || "",
                foto: img ? img.src : null,
                descripcion: item.innerText || ""
            };
        });
        """
        return self.driver.execute_script(script_js)

    def parse_item(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Convierte los datos brutos de JS en un diccionario estructurado.
        try:
            if not raw_data['url']: return None
            id_anuncio = raw_data['url'].split("-")[-1]
            
            # Limpiar precio
            precio_str = raw_data['precio_txt'].replace("€", "").replace(".", "").replace(",", ".").strip()
            if not precio_str or not precio_str[0].isdigit():
                return None 
            precio = float(precio_str)

            partes = raw_data['info_label'].lower().split("·")
            anio, kms, cv = 0, 0, 0
            fuel_detected = None
            
            for p in partes:
                p = p.strip()
                if "cv" in p:
                    cv = int(''.join(filter(str.isdigit, p)))
                elif "km" in p:
                    kms_tmp = int(''.join(filter(str.isdigit, p)))
                    if 0 < kms_tmp < 1000: kms = kms_tmp * 1000
                    else: kms = kms_tmp
                elif p.isdigit() and len(p) == 4:
                    anio = int(p)
                else:
                    # Intento de detectar combustible
                    if "gasolina" in p: fuel_detected = "Gasolina"
                    elif "diésel" in p or "diesel" in p: fuel_detected = "Diesel"
                    elif "híbrido" in p or "hibrido" in p: fuel_detected = "Híbrido"
                    elif "eléctrico" in p or "electrico" in p: fuel_detected = "Eléctrico"

            return {
                'id': id_anuncio, 'titulo': raw_data['titulo'], 'precio': precio,
                'url': raw_data['url'], 'año': anio, 'kms': kms, 'cv': cv, 
                'fuel': fuel_detected,
                'foto': raw_data['foto'], 'descripcion': raw_data['descripcion']
            }
        except Exception:
            return None

    def search(self, url: str) -> List[Dict[str, Any]]:
        # Realiza una operación de búsqueda completa: navegación, gestión de cookies, carga y extracción.
        if not self.driver:
            logger.error("Driver no inicializado. Llama a start() primero.")
            return []

        logger.info(f"🔎 Navegando a la búsqueda...")
        self.driver.get(url)
        
        # Pausa aleatoria inicial (simula tiempo de reacción humano)
        self.random_sleep(2.0, 4.0) 

        self.handle_cookies()
        self.load_more_results()
        return self.extract_items()
