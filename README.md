# 🚗 Wallapop Opportunities Scraper

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Selenium](https://img.shields.io/badge/selenium-4.0%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Un rastreador avanzado de oportunidades de coches en Wallapop. Este bot automatiza la búsqueda de vehículos, analiza precios de mercado y notifica ofertas "chollo" directamente a Telegram.

## ✨ Características

-   **Búsqueda Automatizada**: Rastreo continuo de múltiples modelos de coches.
-   **Análisis de Mercado**: Calcula el precio medio de mercado y detecta desviaciones (chollos).
-   **Notificaciones Inteligentes**: Envía alertas a Telegram con fotos, datos clave y clasificación de la oferta (🟢 Chollo, 🟡 Buen precio, 🔴 Caro).
-   **Evasión de Bots**: Utiliza `undetected-chromedriver` y rotación de User-Agents para evitar bloqueos.
-   **Gestión de Recursos**: Sistema robusto para limpiar procesos de Chrome y gestionar memoria.
-   **Base de Datos**: Almacenamiento local en SQLite para historial de precios y estadísticas.

## 🚀 Instalación

### Requisitos Previos

-   Python 3.10 o superior.
-   Google Chrome instalado.
-   Docker (opcional, para despliegue en contenedor).

### Configuración Local

1.  **Clonar el repositorio** (o descargar los archivos):
    ```bash
    git clone https://github.com/tu-usuario/wallapop-scraper.git
    cd wallapop-scraper
    ```

2.  **Crear un entorno virtual** (recomendado):
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Linux/Mac
    venv\Scripts\activate     # En Windows
    ```

3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuración**:
    Copia el archivo de ejemplo y configura tus variables:
    ```bash
    cp .env.example .env
    ```
    Edita `.env` con tu Token de Bot de Telegram y tu Chat ID.

## ⚙️ Uso

Para iniciar el bot:

```bash
python main.py
```

Sigue las instrucciones en pantalla para añadir nuevas búsquedas o cargar las existentes.

## 🐳 Docker (Opcional)

Puedes ejecutar el bot en un contenedor aislado:

```bash
docker build -t wallapop-bot .
docker run -d --env-file .env -v $(pwd)/searches.json:/app/searches.json -v $(pwd)/rastreador_coches.db:/app/rastreador_coches.db wallapop-bot
```

## 🛠️ Estructura del Proyecto

-   `main.py`: Punto de entrada y orquestador del ciclo de vida.
-   `scraper.py`: Lógica de navegación y extracción con Selenium.
-   `database.py`: Gestión de SQLite (precios, historial, estadísticas).
-   `notifier.py`: Integración con la API de Telegram.
-   `logger.py`: Configuración centralizada de logs.
-   `config.py`: Gestión de variables de entorno y configuración.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o un pull request para discutir cambios importantes.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.
