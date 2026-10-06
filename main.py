import os
import time
import json
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# ==========================================
# 1. Configuración de API y Fechas
# ==========================================
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: No se encontró la GEMINI_API_KEY en el archivo .env")
    exit()

client = genai.Client(api_key=api_key)

fecha_inicio = datetime.now()
fecha_fin = fecha_inicio + timedelta(days=30)

str_inicio = fecha_inicio.strftime("%d/%m/%Y")
str_fin = fecha_fin.strftime("%d/%m/%Y")

# Sesión HTTP con cabeceras completas de navegador
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1"
})

FUENTES = [
    {"nombre": "Terrassa Digital", "url": "https://terrassadigital.cat/cultura/", "tipo": "html"},
    {"nombre": "Món Terrassa", "url": "https://monterrassa.cat/feed/", "tipo": "rss"},
    {"nombre": "Diari de Terrassa", "url": "https://www.diarideterrassa.com/", "tipo": "html"},
    {"nombre": "JazzTerrassa / Nova Jazz Cava", "url": "https://www.jazzterrassa.org/ca/programacio/upcoming", "tipo": "html"},
    {"nombre": "LaFact Cultural", "url": "https://www.lafactcultural.cat/programacio/", "tipo": "html"},
    {"nombre": "Visita Terrassa (Turisme/Ajuntament)", "url": "https://visitaterrassa.cat/agenda-events/llista/", "tipo": "html"},
    {"nombre": "Terrassa Arts Escèniques (Teatres)", "url": "https://terrassaartsesceniques.cat/", "tipo": "html"},
    {"nombre": "Terrassa Cultura", "url": "https://www.terrassacultura.cat/", "tipo": "html"},
    {"nombre": "Cinema Catalunya", "url": "https://cinemacatalunya.cat/", "tipo": "html"},
    {"nombre": "Sala Rasa 64", "url": "https://salarasa64.com/", "tipo": "html"}
]

print(f"📅 Rango de análisis: del {str_inicio} al {str_fin}")
print("📡 Descargando fuentes de Terrassa...\n")

eventos_crudos = []

for fuente in FUENTES:
    nombre = fuente["nombre"]
    url = fuente["url"]
    tipo = fuente["tipo"]
    
    try:
        headers_especificos = {"Referer": "https://www.google.com/"}
        res = session.get(url, headers=headers_especificos, timeout=12)
        res.raise_for_status()
        
        if tipo == "rss":
            soup = BeautifulSoup(res.text, 'xml')
            items = soup.find_all('item')[:20]
            for item in items:
                titulo = item.title.text.strip() if item.title else ""
                desc = item.description.text.strip() if item.description else ""
                link = item.link.text.strip() if item.link else url
                if titulo:
                    eventos_crudos.append(f"[{nombre}] (URL Base: {link}) Título: {titulo} | Detalle: {desc[:250]}")
                    
        elif tipo == "html":
            soup = BeautifulSoup(res.text, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header", "form", "svg"]):
                tag.extract()
            texto = soup.get_text(separator=' ', strip=True)[:7000]
            if texto.strip():
                eventos_crudos.append(f"[{nombre}] (URL Base: {url}) Contenido: {texto}")
            
        print(f"  ✅ {nombre}: OK.")
    except Exception as e:
        print(f"  ❌ {nombre}: Omitido ({e}).")

bloque_datos = "\n\n".join(eventos_crudos)

# ==========================================
# 2. Extracción de Eventos con Gemini
# ==========================================
print("\n🤖 Analizando eventos con Gemini...")

prompt_fase1 = f"""
Eres un extractor de datos de eventos culturales.
Analiza la siguiente información de Terrassa:

--- INICIO DATOS ---
{bloque_datos}
--- FIN DATOS ---

INSTRUCCIONES CRÍTICAS DE URL:
- El campo `fuente_url` DEBE SER la URL web o enlace especificado como 'URL Base' para la fuente correspondiente.
- NUNCA uses enlaces a archivos de imagen (como .png, .jpg, .webp, logos, etc.) en `fuente_url`.

INSTRUCCIONES GENERALES:
1. Extrae TODOS los eventos, películas, conciertos, obras de teatro y actividades deportivas programadas entre el {str_inicio} y el {str_fin}.
2. Omite estrictamente cualquier evento anterior al {str_inicio} o posterior al {str_fin}.
3. Devuelve únicamente una lista en formato JSON estructurada exactamente así por evento:
[
  {{
    "titulo": "Nombre del evento",
    "categoria": "Música/Jazz",
    "fecha": "DD/MM/YYYY",
    "lugar": "Ubicación en Terrassa",
    "descripcion": "Resumen breve de 1-2 líneas",
    "fuente_nombre": "Nombre de la fuente",
    "fuente_url": "URL Base especificada de la fuente"
  }}
]
Categorías válidas permitidas: "Música/Jazz", "Teatro/Danza", "Cine", "Cultura/Patrimonio", "Deportes/Ocio".
4. Devuelve ÚNICAMENTE el array JSON plano. No incluyas explicaciones ni etiquetas markdown.
"""

modelos = ['gemini-3.5-flash-lite', 'gemini-3.8-flash', 'gemini-1.5-flash']
datos_json_str = ""

for model_name in modelos:
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt_fase1
        )
        datos_json_str = response.text.strip()
        print(f"✅ Respuesta recibida con éxito de {model_name}.")
        break
    except Exception as e:
        print(f"⚠ Error con {model_name}: {e}. Probando el siguiente modelo...")
        time.sleep(1)

json_eventos_validos = []

if datos_json_str:
    match = re.search(r'\[.*\]', datos_json_str, re.DOTALL)
    if match:
        datos_json_str = match.group(0)

    try:
        json_eventos_validos = json.loads(datos_json_str)
        # Limpieza de respaldo para eliminar cualquier URL que termine en extensiones de imagen
        for ev in json_eventos_validos:
            url_val = ev.get("fuente_url", "")
            if any(url_val.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']):
                # Buscar URL por defecto de la fuente
                nombre_f = ev.get("fuente_nombre", "")
                fuente_match = next((f for f in FUENTES if f["nombre"].lower() in nombre_f.lower()), None)
                ev["fuente_url"] = fuente_match["url"] if fuente_match else "https://terrassadigital.cat/cultura/"

        print(f"💾 Total eventos extraídos correctamente: {len(json_eventos_validos)}")
    except Exception as e:
        print(f"❌ Error al procesar JSON devuelto por Gemini: {e}")

json_str_raw = json.dumps(json_eventos_validos, ensure_ascii=False, indent=2)

# ==========================================
# 3. Generación de index.html
# ==========================================
print("\n🎨 Generando 'index.html'...")

html_template = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agenda Unificada de Terrassa</title>
  <style>
    :root {
      --primary: #c0392b;
      --bg: #f8f9fa;
      --card-bg: #ffffff;
      --text: #2c3e50;
    }
    body {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 20px;
    }
    header {
      text-align: center;
      margin-bottom: 30px;
    }
    h1 {
      color: var(--primary);
      margin-bottom: 5px;
    }
    .subtitle {
      color: #7f8c8d;
      font-size: 0.95rem;
    }
    .filters {
      display: flex;
      justify-content: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 30px;
    }
    .btn-filter {
      background: #e2e8f0;
      border: none;
      padding: 8px 16px;
      border-radius: 20px;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.2s;
    }
    .btn-filter.active, .btn-filter:hover {
      background: var(--primary);
      color: white;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }
    .card {
      background: var(--card-bg);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.05);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border-left: 5px solid var(--primary);
      transition: transform 0.2s;
    }
    .card:hover {
      transform: translateY(-3px);
    }
    .tag {
      display: inline-block;
      background: #fee2e2;
      color: #991b1b;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: bold;
      margin-bottom: 10px;
      width: fit-content;
    }
    .card h3 {
      margin: 0 0 10px 0;
      font-size: 1.15rem;
    }
    .info {
      font-size: 0.88rem;
      color: #4b5563;
      margin-bottom: 6px;
    }
    .desc {
      font-size: 0.9rem;
      color: #6b7280;
      margin: 12px 0;
      line-height: 1.4;
    }
    .link-btn {
      display: inline-block;
      text-align: center;
      background: #f3f4f6;
      color: #1f2937;
      text-decoration: none;
      padding: 8px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: bold;
      margin-top: 10px;
    }
    .link-btn:hover {
      background: #e5e7eb;
    }
  </style>
</head>
<body>

  <header>
    <h1>Agenda Unificada de Terrassa</h1>
    <p class="subtitle">Eventos del {{STR_INICIO}} al {{STR_FIN}} • Actualización diaria</p>
  </header>

  <div class="filters">
    <button class="btn-filter active" onclick="filtrar('Todos')">Todos</button>
    <button class="btn-filter" onclick="filtrar('Música/Jazz')">Música/Jazz</button>
    <button class="btn-filter" onclick="filtrar('Teatro/Danza')">Teatro/Danza</button>
    <button class="btn-filter" onclick="filtrar('Cine')">Cine</button>
    <button class="btn-filter" onclick="filtrar('Cultura/Patrimonio')">Cultura/Patrimonio</button>
    <button class="btn-filter" onclick="filtrar('Deportes/Ocio')">Deportes/Ocio</button>
  </div>

  <div class="grid" id="contenedor-eventos"></div>

  <script id="datos-eventos" type="application/json">
{{JSON_DATOS}}
  </script>

  <script>
    let todosEventos = [];

    try {
      const jsonText = document.getElementById('datos-eventos').textContent;
      todosEventos = JSON.parse(jsonText);
    } catch (e) {
      console.error('Error al parsear eventos:', e);
    }

    function renderizar(eventos) {
      const contenedor = document.getElementById('contenedor-eventos');
      contenedor.innerHTML = '';

      if (!eventos || eventos.length === 0) {
        contenedor.innerHTML = '<p style="grid-column: 1/-1; text-align:center;">No hay eventos disponibles para esta selección.</p>';
        return;
      }

      eventos.forEach(ev => {
        const card = document.createElement('div');
        card.className = 'card';
        
        const cat = ev.categoria || 'Cultura';
        const tit = ev.titulo || 'Sin título';
        const fec = ev.fecha || 'Consultar fecha';
        const lug = ev.lugar || 'Terrassa';
        const des = ev.descripcion || '';
        const url = (ev.fuente_url && ev.fuente_url.length > 5) ? ev.fuente_url : '#';
        const fue = ev.fuente_nombre || 'Fuente original';

        card.innerHTML = `
          <div>
            <span class="tag">${cat}</span>
            <h3>${tit}</h3>
            <div class="info">📅 ${fec}</div>
            <div class="info">📍 ${lug}</div>
            <p class="desc">${des}</p>
          </div>
          <a href="${url}" target="_blank" class="link-btn">Ver en ${fue} ↗</a>
        `;
        contenedor.appendChild(card);
      });
    }

    function filtrar(cat) {
      document.querySelectorAll('.btn-filter').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.trim() === cat);
      });

      if (cat === 'Todos') {
        renderizar(todosEventos);
      } else {
        const clave = cat.split('/')[0].toLowerCase();
        const filtrados = todosEventos.filter(e => e.categoria && e.categoria.toLowerCase().includes(clave));
        renderizar(filtrados);
      }
    }

    document.addEventListener('DOMContentLoaded', () => renderizar(todosEventos));
  </script>
</body>
</html>
"""

html_final = html_template.replace("{{STR_INICIO}}", str_inicio)\
                          .replace("{{STR_FIN}}", str_fin)\
                          .replace("{{JSON_DATOS}}", json_str_raw)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_final)

print("🎉 ¡index.html actualizado correctamente con los enlaces corregidos!")
