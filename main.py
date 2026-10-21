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

# Sesión HTTP configurada con cabeceras avanzadas
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
})

FUENTES = [
    {"nombre": "Terrassa Digital", "url": "https://terrassadigital.cat/cultura/", "tipo": "html"},
    {"nombre": "Món Terrassa", "url": "https://monterrassa.cat/feed/", "tipo": "rss"},
    {"nombre": "Diari de Terrassa", "url": "https://www.diarideterrassa.com/", "tipo": "html"},
    {"nombre": "JazzTerrassa / Nova Jazz Cava", "url": "https://www.jazzterrassa.org/ca/programacio/upcoming", "tipo": "html"},
    {"nombre": "LaFact Cultural", "url": "https://www.lafactcultural.cat/programacio/", "tipo": "html"},
    {"nombre": "Visita Terrassa (Turisme/Ajuntament)", "url": "https://visitaterrassa.cat/wp-json/tribe/events/v1/events?per_page=50", "tipo": "json_tribe"},
    {"nombre": "Terrassa Arts Escèniques (Teatres)", "url": "https://terrassaartsesceniques.cat/", "tipo": "html"},
    {"nombre": "Terrassa Cultura", "url": "https://www.terrassacultura.cat/", "tipo": "html"},
    {"nombre": "Cinema Catalunya", "url": "https://cinemacatalunya.cat/", "tipo": "html"},
    {"nombre": "Sala Rasa 64", "url": "https://salarasa64.com/", "tipo": "html"},
    {"nombre": "Planomato Terrassa", "url": "https://www.planomato.com/es/terrassa/proximos-planes", "tipo": "html"},
    {"nombre": "Sala Born / Zurito Terrassa", "url": "https://zuritoterrassa.com/es/sala-fiestas-born-terrassa/", "tipo": "html"}
]

print(f"📅 Rango de análisis: del {str_inicio} al {str_fin}")
print("📡 Descargando fuentes de Terrassa y procesando calendario institucional...\n")

eventos_crudos = []

# Base de datos completa de Festes Populars i Tradicionals de Terrassa (2026)
CALENDARIO_ANUAL_CULTURA = [
    {"titulo": "Ball de Reis", "categoria": "Cultura/Patrimonio", "fecha": "03/01/2026", "lugar": "Carrers del centre", "descripcion": "Ball de Reis a càrrec dels Bastoners de Terrassa.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Cavalcada de Reis", "categoria": "Cultura/Patrimonio", "fecha": "05/01/2026", "lugar": "Recorregut per la ciutat", "descripcion": "Festa de benvinguda i cavalcada de SSMM els Reis Mags d'Orient.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "XCIX Carnestoltes", "categoria": "Cultura/Patrimonio", "fecha": "12/02/2026", "lugar": "Diversos espais", "descripcion": "Celebració del tradicional Carnestoltes a Terrassa.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Caramelles", "categoria": "Cultura/Patrimonio", "fecha": "06/04/2026", "lugar": "Antic poble de Sant Pere", "descripcion": "Cantada de Caramelles a càrrec de La Xemeneia.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Diada de Sant Jordi", "categoria": "Cultura/Patrimonio", "fecha": "23/04/2026", "lugar": "Pl. Vella i Raval de Montserrat", "descripcion": "Actuacions de grups de cultura popular i exhibició castellera.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Diada del Drac de Terrassa", "categoria": "Cultura/Patrimonio", "fecha": "23/05/2026", "lugar": "Raval de Montserrat", "descripcion": "Celebració de la diada del Drac de Terrassa.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Festa Major de Terrassa", "categoria": "Cultura/Patrimonio", "fecha": "03/07/2026", "lugar": "Diversos espais de la ciutat", "descripcion": "Inici de la Festa Major de Terrassa amb actes culturals i tradicionals.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Aniversari de la colla (Drac i Bruixes de Can Boada)", "categoria": "Cultura/Patrimonio", "fecha": "17/10/2026", "lugar": "Pl. Lluís Companys", "descripcion": "Trobada i celebració de l'aniversari de la colla de Drac i Bruixes.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Trobada dels Gegants Bojos", "categoria": "Cultura/Patrimonio", "fecha": "17/10/2026", "lugar": "Pl. Vapor Ventalló", "descripcion": "Trobada tradicional dels Gegants Bojos de Terrassa.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Concurs Nacional de Colles Sardanistes", "categoria": "Cultura/Patrimonio", "fecha": "18/10/2026", "lugar": "Pl. Nova", "descripcion": "Concurs nacional organitzat per l'Agrupació Folklòrica Amunt i Crits.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Diada dels Diables de la Maurina", "categoria": "Cultura/Patrimonio", "fecha": "24/10/2026", "lugar": "Pl. del Progrés", "descripcion": "Diada de foc i tradició dels Diables de la Maurina.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Festa de la Castanyada", "categoria": "Cultura/Patrimonio", "fecha": "31/10/2026", "lugar": "Pl. del Progrés", "descripcion": "Festa popular de la Castanyada a càrrec de La Xemeneia.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Diada de la Colla Castellers de Terrassa", "categoria": "Cultura/Patrimonio", "fecha": "07/11/2026", "lugar": "Pl. Vella", "descripcion": "Diada castellera amb actuació dels Castellers de Terrassa.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Acte d'Encesa de llums de Nadal", "categoria": "Cultura/Patrimonio", "fecha": "28/11/2026", "lugar": "Raval de Montserrat", "descripcion": "Inici oficial de la campanya nadalenca a Terrassa.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"},
    {"titulo": "Arribada del Patge Xiu-Xiu", "categoria": "Cultura/Patrimonio", "fecha": "19/12/2026", "lugar": "Estació del Nord", "descripcion": "Arribada del carter reial Patge Xiu-Xiu a Terrassa.", "fuente_nombre": "Cultura Popular i Tradicional (PDF)", "fuente_url": "https://www.terrassa.cat/es/cultura-popular-i-tradicional"}
]

# Filtramos dinámicamente los eventos institucionales que caen en el rango de los 30 días
eventos_pdf_filtrados = []
for ev in CALENDARIO_ANUAL_CULTURA:
    try:
        f_evento = datetime.strptime(ev["fecha"], "%d/%m/%Y")
        if fecha_inicio <= f_evento <= fecha_fin:
            eventos_pdf_filtrados.append(ev)
    except Exception:
        pass

# Descarga de fuentes web
for fuente in FUENTES:
    nombre = fuente["nombre"]
    url = fuente["url"]
    tipo = fuente["tipo"]
    
    try:
        domain = "/".join(url.split("/")[:3])
        session.get(domain, timeout=10)
        
        headers_especificos = {
            "Referer": domain + "/",
            "Host": url.replace("https://", "").replace("http://", "").split("/")[0]
        }
        
        res = session.get(url, headers=headers_especificos, timeout=15)
        
        if res.status_code == 403:
            headers_alternativos = {
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
                "Referer": "https://www.google.com/"
            }
            res = session.get(url, headers=headers_alternativos, timeout=15)

        res.raise_for_status()
        
        if tipo == "rss":
            try:
                soup = BeautifulSoup(res.text, 'xml')
            except Exception:
                soup = BeautifulSoup(res.text, 'html.parser')
                
            items = soup.find_all('item')[:20]
            for item in items:
                titulo = item.title.text.strip() if item.title else ""
                desc = item.description.text.strip() if item.description else ""
                link = item.link.text.strip() if item.link else url
                if titulo:
                    eventos_crudos.append(f"[{nombre}] (URL Base: {link}) Título: {titulo} | Detalle: {desc[:250]}")
                    
        elif tipo == "json_tribe":
            data = res.json()
            events = data if isinstance(data, list) else data.get("events", [])
            for ev in events:
                if isinstance(ev, dict):
                    title = ev.get("title", "")
                    start_date = ev.get("start_date", "")
                    venue_data = ev.get("venue", {})
                    venue = venue_data.get("venue", "Terrassa") if isinstance(venue_data, dict) else "Terrassa"
                    description = BeautifulSoup(ev.get("description", ""), 'html.parser').get_text(strip=True)[:250]
                    url_ev = ev.get("url", "https://visitaterrassa.cat/agenda-events/llista/")
                    if title:
                        eventos_crudos.append(f"[{nombre}] (URL Base: {url_ev}) Título: {title} | Fecha: {start_date} | Lugar: {venue} | Detalle: {description}")
                    
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
2. Omite strictly cualquier evento anterior al {str_inicio} o posterior al {str_fin}.
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
        for ev in json_eventos_validos:
            url_val = ev.get("fuente_url", "")
            if any(url_val.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']):
                nombre_f = ev.get("fuente_nombre", "")
                fuente_match = next((f for f in FUENTES if f["nombre"].lower() in nombre_f.lower()), None)
                ev["fuente_url"] = fuente_match["url"] if fuente_match else "https://terrassadigital.cat/cultura/"

        print(f"💾 Total eventos extraídos de las webs: {len(json_eventos_validos)}")
    except Exception as e:
        print(f"❌ Error al procesar JSON devuelto por Gemini: {e}")

# 3. Fusionamos los eventos web con los tradicionales del PDF filtrados por fecha de forma dinámica
for ev_pdf in eventos_pdf_filtrados:
    json_eventos_validos.append(ev_pdf)

print(f"✨ Total eventos finales (Webs + Cultura Popular en rango): {len(json_eventos_validos)}")

json_str_raw = json.dumps(json_eventos_validos, ensure_ascii=False, indent=2)

with open("eventos_30dias.json", "w", encoding="utf-8") as f:
    f.write(json_str_raw)

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
      margin-bottom: 25px;
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
      margin-bottom: 20px;
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
    .date-filter-box {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      margin-bottom: 30px;
      background: #ffffff;
      padding: 10px 18px;
      border-radius: 12px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.04);
      width: fit-content;
      margin-left: auto;
      margin-right: auto;
    }
    .date-filter-box label {
      font-weight: 600;
      color: var(--text);
      font-size: 0.9rem;
    }
    .date-filter-box input[type="date"] {
      padding: 6px 10px;
      border-radius: 6px;
      border: 1px solid #cbd5e1;
      font-family: inherit;
      color: var(--text);
    }
    .btn-clear {
      padding: 6px 12px;
      border-radius: 6px;
      border: none;
      background: #e2e8f0;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.85rem;
      transition: background 0.2s;
    }
    .btn-clear:hover {
      background: #cbd5e1;
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

  <div class="date-filter-box">
    <label for="filtro-fecha">📅 Filtrar por día concreto:</label>
    <input type="date" id="filtro-fecha" onchange="filtrarPorFecha(this.value)">
    <button class="btn-clear" onclick="limpiarFecha()">Mostrar todos</button>
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
        contenedor.innerHTML = '<p style="grid-column: 1/-1; text-align:center; padding: 20px; color: #6b7280;">No hay eventos disponibles para esta selección.</p>';
        return;
      }

      eventos.forEach(ev => {
        const card = document.createElement('div');
        
        const cardClass = ev.categoria && ev.categoria.includes('Cultura') ? 'card cultura' : 'card';
        card.className = cardClass;
        
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
      document.getElementById('filtro-fecha').value = '';
      
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

    function filtrarPorFecha(fechaInput) {
      if (!fechaInput) return;
      
      const partes = fechaInput.split('-');
      const fechaBuscada = `${partes[2]}/${partes[1]}/${partes[0]}`;

      document.querySelectorAll('.btn-filter').forEach(btn => btn.classList.remove('active'));

      const filtrados = todosEventos.filter(e => e.fecha === fechaBuscada);
      renderizar(filtrados);
    }

    function limpiarFecha() {
      document.getElementById('filtro-fecha').value = '';
      filtrar('Todos');
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

print("🎉 ¡index.html actualizado correctamente con selector de fecha integrado!")
