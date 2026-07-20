import sqlite3
import statistics
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any, Union

from config import DB_NAME
from logger import logger

class DatabaseManager:
    # Gestiona las interacciones con la base de datos SQLite para el Scraper de Wallapop (Versión Multi-Cliente).

    def __init__(self, db_path: str = DB_NAME) -> None:
        self.db_path = db_path
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _create_tables(self) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. TABLA DE COCHES (Catálogo Global)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS coches (
                        id_anuncio TEXT PRIMARY KEY,
                        modelo TEXT,
                        precio REAL,
                        kilometros INTEGER,
                        año INTEGER,
                        cv INTEGER,
                        combustible TEXT,
                        url TEXT,
                        fecha_visto DATETIME,
                        precio_original REAL,
                        cambio_precio REAL DEFAULT 0,
                        activo INTEGER DEFAULT 1,
                        score REAL DEFAULT 0,
                        foto TEXT,
                        visto_por_ultima_viva DATETIME
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS historial_precios (
                        id_anuncio TEXT,
                        precio REAL,
                        fecha DATETIME
                    )
                ''')

                # 2. TABLA DE USUARIOS (Clientes)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id TEXT UNIQUE,
                        username TEXT,
                        is_active INTEGER DEFAULT 1,
                        joined_at DATETIME,
                        tier TEXT DEFAULT 'free',
                        subscription_end DATETIME
                    )
                ''')

                # 3. TABLA DE BÚSQUEDAS (Vinculada a Usuarios)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS searches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        keywords TEXT,
                        p_max REAL,
                        k_max INTEGER,
                        cv_min INTEGER DEFAULT 0,
                        year_min INTEGER DEFAULT 0,
                        year_max INTEGER DEFAULT 9999,
                        fuel_label TEXT,
                        fuel_code TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                ''')

                # 4. TABLA DE VISTOS POR USUARIO (Para no repetir alertas)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_seen_cars (
                        user_id INTEGER,
                        car_id TEXT,
                        seen_at DATETIME,
                        PRIMARY KEY (user_id, car_id),
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        FOREIGN KEY(car_id) REFERENCES coches(id_anuncio)
                    )
                ''')
                
                # --- MIGRACIONES AUTOMÁTICAS ---
                try: cursor.execute("ALTER TABLE searches ADD COLUMN year_min INTEGER DEFAULT 0")
                except sqlite3.OperationalError: pass
                try: cursor.execute("ALTER TABLE searches ADD COLUMN year_max INTEGER DEFAULT 9999")
                except sqlite3.OperationalError: pass
                try: cursor.execute("ALTER TABLE users ADD COLUMN tier TEXT DEFAULT 'free'")
                except sqlite3.OperationalError: pass
                try: cursor.execute("ALTER TABLE users ADD COLUMN subscription_end DATETIME")
                except sqlite3.OperationalError: pass

                conn.commit()
        except sqlite3.Error as e:
            logger.critical(f"Error al crear las tablas de la base de datos: {e}")

    # --- GESTIÓN DE USUARIOS Y BÚSQUEDAS ---

    def register_user(self, telegram_id: str, username: str = "") -> int:
        # Registra un nuevo usuario o devuelve su ID si ya existe.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (telegram_id, username, joined_at, tier) VALUES (?, ?, ?, 'free')", 
                           (telegram_id, username, datetime.now()))
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            return cursor.fetchone()[0]

    def get_all_users(self) -> List[str]:
        # Devuelve una lista con los telegram_id de todos los usuarios activos.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id FROM users WHERE is_active = 1")
            return [row[0] for row in cursor.fetchall()]

    def get_user_tier(self, telegram_id: str) -> str:
        # Devuelve el nivel de suscripción del usuario (free, premium, pro).
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tier, subscription_end FROM users WHERE telegram_id = ?", (telegram_id,))
            res = cursor.fetchone()
            if not res: return 'free'
            
            tier, sub_end_str = res
            
            # Comprobar expiración
            if tier != 'free' and sub_end_str:
                try:
                    sub_end = datetime.strptime(sub_end_str, '%Y-%m-%d %H:%M:%S.%f')
                    if sub_end < datetime.now():
                        # ¡Expirado! Degradar a free
                        self.update_user_tier(telegram_id, 'free', 0)
                        return 'free'
                except ValueError:
                    pass # Error de formato de fecha, ignorar
            
            return tier

    def update_user_tier(self, telegram_id: str, tier: str, days: int) -> None:
        # Actualiza el nivel y la fecha de caducidad.
        if tier == 'free':
            sub_end = None
        else:
            sub_end = datetime.now() + timedelta(days=days)
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET tier = ?, subscription_end = ? WHERE telegram_id = ?", 
                           (tier, sub_end, telegram_id))
            conn.commit()
            logger.info(f"Usuario {telegram_id} actualizado a {tier} hasta {sub_end}")

    def count_user_searches(self, telegram_id: str) -> int:
        # Cuenta cuántas búsquedas activas tiene un usuario.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM searches s
                JOIN users u ON s.user_id = u.id
                WHERE u.telegram_id = ?
            """, (telegram_id,))
            return cursor.fetchone()[0]

    def add_search(self, user_id: int, search_config: Dict[str, Any]) -> None:
        # Añade una búsqueda para un usuario.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO searches (user_id, keywords, p_max, k_max, cv_min, year_min, year_max, fuel_label, fuel_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, 
                search_config['keywords'], 
                search_config['p_max'], 
                search_config['k_max'], 
                search_config.get('cv_min', 0),
                search_config.get('year_min', 0),
                search_config.get('year_max', 9999),
                search_config['fuel_label'], 
                search_config.get('fuel_code', '')
            ))
            conn.commit()

    def get_user_searches(self, telegram_id: str) -> List[Dict[str, Any]]:
        # Recupera todas las búsquedas activas de un usuario, incluyendo su ID.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.keywords, s.p_max, s.k_max, s.cv_min, s.year_min, s.year_max, s.fuel_label
                FROM searches s
                JOIN users u ON s.user_id = u.id
                WHERE u.telegram_id = ?
            """, (telegram_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0], # Devolvemos el ID de la búsqueda
                    'keywords': row[1],
                    'p_max': row[2],
                    'k_max': row[3],
                    'cv_min': row[4],
                    'year_min': row[5],
                    'year_max': row[6],
                    'fuel_label': row[7]
                })
            return results

    def delete_search(self, search_id: int) -> None:
        # Elimina una búsqueda específica por su ID.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM searches WHERE id = ?", (search_id,))
            conn.commit()
            logger.info(f"Búsqueda eliminada con ID: {search_id}")

    def get_all_unique_keywords(self) -> List[str]:
        # Devuelve todas las palabras clave únicas que se están buscando.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT keywords FROM searches")
            return [row[0] for row in cursor.fetchall()]

    def get_interested_users(self, keywords: str) -> List[Dict[str, Any]]:
        # Devuelve los usuarios y sus filtros interesados en una palabra clave.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.user_id, u.telegram_id, s.p_max, s.k_max, s.cv_min, s.year_min, s.year_max, s.fuel_label, u.tier
                FROM searches s
                JOIN users u ON s.user_id = u.id
                WHERE s.keywords = ? AND u.is_active = 1
            """, (keywords,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'user_id': row[0],
                    'telegram_id': row[1],
                    'p_max': row[2],
                    'k_max': row[3],
                    'cv_min': row[4],
                    'year_min': row[5],
                    'year_max': row[6],
                    'fuel_label': row[7],
                    'tier': row[8] # Añadimos el tier para saber si enviar fotos o no
                })
            return results

    def has_user_seen_car(self, user_id: int, car_id: str) -> bool:
        # Verifica si un usuario específico ya ha recibido alerta de este coche.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM user_seen_cars WHERE user_id = ? AND car_id = ?", (user_id, car_id))
            return cursor.fetchone() is not None

    def mark_car_as_seen(self, user_id: int, car_id: str) -> None:
        # Marca un coche como visto para un usuario.
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO user_seen_cars (user_id, car_id, seen_at) VALUES (?, ?, ?)",
                           (user_id, car_id, datetime.now()))
            conn.commit()

    # --- GESTIÓN DE COCHES (GLOBAL) ---

    def get_car_price(self, car_id: str) -> Optional[float]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT precio FROM coches WHERE id_anuncio = ?", (car_id,))
            res = cursor.fetchone()
            return res[0] if res else None

    def update_car(self, car_id: str, new_price: float, savings: float, kms: int) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE coches SET precio=?, cambio_precio=?, kilometros=? WHERE id_anuncio=?", 
                               (new_price, savings, kms, car_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error al actualizar el coche {car_id}: {e}")

    def insert_car(self, car: Dict[str, Any]) -> None:
        fecha_hoy = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO coches
                    (id_anuncio, modelo, precio, kilometros, año, cv, combustible, url, fecha_visto, precio_original, foto, visto_por_ultima_viva)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    car['id'], car['titulo'], car['precio'], car['kms'], 
                    car['año'], car['cv'], car.get('fuel', 'Desconocido'), 
                    car['url'], fecha_hoy, car['precio'], car.get('foto'),
                    fecha_hoy
                ))
                if cursor.rowcount > 0:
                    cursor.execute("INSERT INTO historial_precios (id_anuncio, precio, fecha) VALUES (?, ?, ?)", 
                                   (car['id'], car['precio'], fecha_hoy))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error al insertar el coche {car.get('id')}: {e}")

    def update_visto(self, car_id: str) -> None:
        fecha_hoy = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE coches SET visto_por_ultima_viva = ?, activo = 1 WHERE id_anuncio = ?", (fecha_hoy, car_id))
            conn.commit()

    def set_inactive_old_cars(self, days: int = 2) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE coches SET activo = 0 WHERE visto_por_ultima_viva < datetime('now', '-' || ? || ' days') AND activo = 1", (days,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error al desactivar coches antiguos: {e}")

    def get_market_stats(self, keywords: str) -> Optional[Dict[str, float]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT precio FROM coches WHERE modelo LIKE ?", (f'%{keywords}%',))
            precios = [row[0] for row in cursor.fetchall()]
            if not precios: return None
            avg = statistics.mean(precios)
            stdev = statistics.stdev(precios) if len(precios) > 1 else 0
            return {'avg': avg, 'stdev': stdev, 'count': len(precios)}

    def clean_old_records(self, days: int = 30) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM coches WHERE visto_por_ultima_viva < datetime('now', '-' || ? || ' days')", (days,))
                cursor.execute("DELETE FROM historial_precios WHERE fecha < datetime('now', '-' || ? || ' days')", (days,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error al limpiar registros antiguos: {e}")

    def update_score(self, car_id: str, score: float) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE coches SET score = ? WHERE id_anuncio = ?", (score, car_id))
            conn.commit()

    def get_all_prices(self, keywords: str) -> List[float]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT precio FROM coches WHERE modelo LIKE ?", (f'%{keywords}%',))
            return [f[0] for f in cursor.fetchall()]
            
    def get_top_deals(self, keywords: str, limit: int = 10) -> List[Tuple]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT precio, kilometros, año, url, score
                FROM coches
                WHERE modelo LIKE ? AND activo = 1
                ORDER BY score ASC LIMIT ?
            """, (f'%{keywords}%', limit))
            return cursor.fetchall()
