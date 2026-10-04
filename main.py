import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# 1. Cargar clave de API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: No se encontró la GEMINI_API_KEY en el archivo .env")
    exit()

client = genai.Client(api_key=api_key)
fecha_actual = datetime.now().strftime("%d/%m/%Y")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

FUENTES = [
    {"nombre": "Terrassa Digital", "url": "https://terrassadigital.cat/feed/", "tipo": "rss"},
    {"nombre": "JazzTerrassa / Nova Jazz Cova", "url": "https://www.jazzterrassa.org/ca/programacio/upcoming", "tipo": "html"},
    {"nombre": "Món Terrassa", "url": "https://monterrassa.cat/feed/", "tipo": "rss"},
    {"nombre": "LaFact Cultural", "url": "https://www.lafactcultural.cat/programacio/", "tipo": "html"}
]

eventos_crudos = []

print(f"📅 Fecha de referencia: {fecha_actual}")
print("📡 Extrayendo y pre-filtrando eventos de múltiples fuentes...\n")

for fuente in FUENTES:
    nombre = fuente["nombre"]
    url = fuente["url"]
    tipo = fuente["tipo"]
    
    print(f"🔍 Procesando: {nombre}...")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        
        if tipo == "rss":
            soup = BeautifulSoup(res.text, 'xml')
            items = soup.find_all('item')[:15] # 15 elementos por feed
            for item in items:
                titulo = item.title.text.strip() if item.title else ""
                desc = item.description.text.strip() if item.description else ""
                if titulo:
                    eventos_crudos.append(f"[{nombre}] Título: {titulo} | Detalle: {desc[:200]}")
                    
        elif tipo == "html":
            soup = BeautifulSoup(res.text, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
                tag.extract()
            texto = soup.get_text(separator=' ', strip=True)[:8000]
            eventos_crudos.append(f"[{nombre}] Contenido completo agenda: {texto}")
            
        print(f"  ✅ {nombre}: Extraído correctamente.")
    except Exception as e:
        print(f"  ❌ {nombre}: Error ({e}). Omitido.")

bloque_datos = "\n\n".join(eventos_crudos)

print("\n🤖 Generando agenda completa en HTML...")

prompt = f"""
Actúa como un desarrollador web experto. Tu tarea es construir la página web 'Agenda de Terrassa'.

HOY ES: {fecha_actual}.

DATOS EXTRAÍDOS DE FUENTES REALES:
---
{bloque_datos}
---

INSTRUCCIONES DE DISEÑO Y CONTENIDO:
1. MAXIMIZA EL NÚMERO DE EVENTOS: Incluye TODOS los eventos o noticias de agenda reales que encuentres en el texto. No te limites, incluye una lista extensa (mínimo 10-20 tarjetas si existen datos).
2. DESCARTA EVENTOS PASADOS: Omite cualquier evento anterior a {fecha_actual}.
3. CABECERA CON BOTONES DE FILTRO (JavaScript):
   Crea botones arriba: "Todos", "Música/Jazz", "Teatro/Danza", "Cultura", "Deportes".
   Añade un script JavaScript simple para que al hacer clic en un botón se muestren solo las tarjetas de esa categoría.
4. ESTRUCTURA DE TARJETA DE EVENTO:
   - Título
   - Categoría (tag de color)
   - Fecha y Hora
   - Lugar en Terrassa
   - Breve descripción (1-2 líneas)
   - Fuente con enlace original
5. Devuelve ÚNICAMENTE el código HTML completo con CSS en <style> y JS en <script>. Sin formato markdown (```html).
"""

modelos = ['gemini-3.8-flash', 'gemini-3.5-flash']
html_content = None

for model_name in modelos:
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        html_content = response.text.strip()
        print(f"✅ Agenda web generada con éxito usando {model_name}!")
        break
    except Exception as e:
        print(f"⚠️ Reintentando con modelo de respaldo...")
        time.sleep(2)

if html_content:
    if html_content.startswith("```html"):
        html_content = html_content[7:]
    if html_content.startswith("```"):
        html_content = html_content[3:]
    if html_content.endswith("```"):
        html_content = html_content[:-3]

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("\n🎉 ¡Proceso finalizado! Refresca 'index.html' en tu navegador.")