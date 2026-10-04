import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# 1. Cargar clave de API de Gemini
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

# 2. Las 11 fuentes culturales y de ocio de Terrassa
FUENTES = [
    {"nombre": "Terrassa Digital", "url": "https://terrassadigital.cat/feed/", "tipo": "rss"},
    {"nombre": "Món Terrassa", "url": "https://monterrassa.cat/feed/", "tipo": "rss"},
    {"nombre": "Diari de Terrassa", "url": "https://www.diarideterrassa.com/", "tipo": "html"},
    {"nombre": "JazzTerrassa / Nova Jazz Cova", "url": "https://www.jazzterrassa.org/ca/programacio/upcoming", "tipo": "html"},
    {"nombre": "LaFact Cultural", "url": "https://www.lafactcultural.cat/programacio/", "tipo": "html"},
    {"nombre": "Visita Terrassa (Turisme/Ajuntament)", "url": "https://visitaterrassa.cat/agenda-events/llista/", "tipo": "html"},
    {"nombre": "Terrassa Arts Escèniques (Teatres)", "url": "https://terrassaartsesceniques.cat/", "tipo": "html"},
    {"nombre": "Terrassa Cultura", "url": "https://www.terrassacultura.cat/", "tipo": "html"},
    {"nombre": "Cinema Catalunya", "url": "https://cinemacatalunya.cat/", "tipo": "html"},
    {"nombre": "Sala Rasa 64", "url": "https://salarasa64.com/", "tipo": "html"},
    {"nombre": "Cinesa Parc Vallès", "url": "https://www.cinesa.es/cines/parc-valles/", "tipo": "html"}
]

eventos_crudos = []

print(f"📅 Fecha de referencia: {fecha_actual}")
print("📡 Extrayendo datos de 11 fuentes de Terrassa...\n")

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
            items = soup.find_all('item')[:12]
            for item in items:
                titulo = item.title.text.strip() if item.title else ""
                desc = item.description.text.strip() if item.description else ""
                if titulo:
                    eventos_crudos.append(f"[{nombre}] Título: {titulo} | Detalle: {desc[:180]}")
                    
        elif tipo == "html":
            soup = BeautifulSoup(res.text, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header", "form", "svg"]):
                tag.extract()
            texto = soup.get_text(separator=' ', strip=True)[:5000]
            if texto.strip():
                eventos_crudos.append(f"[{nombre}] Contenido agenda: {texto}")
            
        print(f"  ✅ {nombre}: Extraído correctamente.")
    except Exception as e:
        print(f"  ❌ {nombre}: No se pudo conectar ({e}). Se omitirá.")

bloque_datos = "\n\n".join(eventos_crudos)

# 3. Consolidar agenda unificada con Gemini
print("\n🤖 Consolidando la super-agenda de Terrassa con Gemini...")

prompt = f"""
Actúa como editor principal de la 'Agenda Cultural, Cine y Ocio Unificada de Terrassa'.

HOY ES: {fecha_actual}.

DATOS EXTRAÍDOS DE FUENTES REALES:
---
{bloque_datos}
---

INSTRUCCIONES DE DISEÑO Y CONTENIDO:
1. MAXIMIZA EL NÚMERO DE EVENTOS: Extrae la máxima cantidad de eventos, películas de cine, conciertos, teatro, fiestas y actividades deportivas posibles. Genera una lista amplia de tarjetas (mínimo 15-30 tarjetas si hay datos suficientes).
2. DESCARTA EVENTOS PASADOS: Omite cualquier evento anterior a hoy ({fecha_actual}).
3. CABECERA CON BOTONES DE FILTRO (JavaScript):
   Crea botones arriba: "Todos", "Música/Jazz", "Teatro/Danza", "Cine", "Cultura/Patrimonio", "Deportes/Ocio".
   Añade un script JavaScript funcional para que al pulsar sobre cada botón se filtren dinámicamente las tarjetas de esa categoría.
4. ESTRUCTURA DE TARJETA DE EVENTO:
   - Título claro
   - Categoría (etiqueta de color)
   - Fecha y Hora (si consta)
   - Lugar en Terrassa (Nova Jazz Cova, Cinema Catalunya, Teatre Principal, Sala Rasa 64, Parc Vallès, etc.)
   - Breve descripción (1-2 líneas)
   - Fuente con enlace original a la URL correspondiente.
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
        print(f"✅ ¡Super-agenda generada con éxito usando {model_name}!")
        break
    except Exception as e:
        print(f"⚠️️ Reintentando con modelo de respaldo...")
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

    print("\n🎉 ¡Proceso finalizado! Refresca 'index.html' en tu navegador para probarlo en local.")
