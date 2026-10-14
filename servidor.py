import os
import io
import base64
import requests
import hashlib
import hmac
import gc  
import time 
import traceback
import numpy as np
from flask import Flask, render_template, request, jsonify, Response, redirect
from flask_cors import CORS
from PIL import Image, ImageChops, ImageOps, ImageEnhance, ImageFilter
from urllib.parse import quote

Image.MAX_IMAGE_PIXELS = None

app = Flask(__name__)
CORS(app)

API_SNAPEDIT = os.environ.get("SNAPEDIT_API_KEY", "sk-snap-uuh6Z0veQTW7z3DSQ7TUr5yuyaC7HIHAoUchqM_KrfI")
BASE = "https://api.snapedit.app"
HEADERS = {"api-key": API_SNAPEDIT, "Authorization": f"Bearer {API_SNAPEDIT}"}
ALLOWED_STYLE_DOMAINS = ("storage.googleapis.com",)

TELEGRAM_BOT_TOKEN = "8812898715:AAHSgtmxCjQ8yRTANb85EuluZgw9Dz3x1Fw" 
TELEGRAM_CHAT_ID = "-1002330690954"

def L(es, en): return {"es": es, "en": en}

MODELS = [
    # --- TUS HERRAMIENTAS DTF ---
    {"slug": "detector-dtf", "label": L("🔍 Detectar Semitransparencias", "🔍 Transparency Scanner"), "icon": "fa-magnifying-glass-chart", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Escanea tu diseño en busca de píxeles fantasmas y repáralos para DTF a 300DPI.", "Scan and fix ghost pixels for DTF."), "endpoint": "/api/reparar", "response_type": "image", "fields": []},
    {"slug": "semitonos-dtf", "label": L("🕸️ Semitonos DTF Pro", "🕸️ Halftones DTF Pro"), "icon": "fa-braille", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Convierte fondos en tramas de puntos, aplica asfixia y limpieza HD.", "Convert to halftones, apply choke and upscale."), "endpoint": "/api/procesar", "response_type": "image", "fields": []},

    # --- TUS HERRAMIENTAS DE IA ORIGINALES ---
    {"slug": "detect-objects", "label": L("Borrador Mágico (Auto)", "Magic Eraser (Auto)"), "icon": "fa-magic", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Encuentra objetos para borrarlos con un clic.", "Finds objects to erase them with a click."), "endpoint": "/v1/images/detect-objects", "response_type": "json", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen Base", "Base Image"), "required": True}, {"name": "lang", "type": "select", "label": L("Idioma", "Language"), "options": [{"value": "es", "label": L("Español", "Spanish")}]}, {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "super", "label": L("Super", "Super")}, {"value": "normal", "label": L("Normal", "Normal")}]}]},
    {"slug": "detect-text", "label": L("Borrar Texto (Auto)", "Erase Text (Auto)"), "icon": "fa-font", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Detecta y borra los textos automáticamente.", "Detects and erases text automatically."), "endpoint": "/v1/images/detect-text", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "detect-wires", "label": L("Borrar Cables (Auto)", "Erase Wires (Auto)"), "icon": "fa-plug", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Detecta y borra cables/postes.", "Detects and erases wires."), "endpoint": "/v1/images/detect-wires", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-logo", "label": L("Quitar Marcas de Agua (Auto)", "Remove Watermarks"), "icon": "fa-copyright", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Detecta y elimina logos y marcas de protección en un clic.", "Auto remove logos and watermarks."), "endpoint": "/v1/images/remove-logo", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "extract-print", "label": L("👕 Extraer Diseño (Mockup a DTF)", "👕 Extract Shirt Design (DTF)"), "icon": "fa-shirt", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Extrae el estampado, recorta bordes, lo escala en Ultra HD (4x) y entrega PNG sin fondo.", "Extracts, crops, upscales 4x HD, and flattens graphic print into transparent PNG."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [
        {"name": "input_image", "type": "image", "label": L("Foto de la Camiseta / Mockup", "Shirt / Mockup Photo"), "required": True},
        {"name": "extract_mode", "type": "select", "label": L("Tipo de Prenda / Diseño", "Garment / Design Type"), "required": True, "options": [
            {"value": "AUTO_BLACK", "label": L("✨ PNG Sin Fondo Ultra HD (Polos Negros / Diseños con líneas blancas)", "✨ Transparent PNG HD (From Black Shirt / White lines)")},
            {"value": "AUTO_WHITE", "label": L("✨ PNG Sin Fondo Ultra HD (Polos Blancos o Claros / Diseños oscuros)", "✨ Transparent PNG HD (From Light Shirt / Dark design)")},
            {"value": "SOLID_BLACK", "label": L("⬛ Extraer en Ultra HD sobre Fondo Negro", "⬛ HD Cropped on Solid Black")},
            {"value": "SOLID_WHITE", "label": L("⬜ Extraer en Ultra HD sobre Fondo Blanco", "⬜ HD Cropped on Solid White")}
        ]}
    ]},
    {"slug": "remove-background", "label": L("Quitar Fondo (Fotos)", "Remove Background"), "icon": "fa-user-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Recorte de personas o productos.", "Cutout for people/products."), "endpoint": "/v1/images/remove-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-background-graphic", "label": L("Quitar Fondo (Arte)", "Remove BG (Graphics)"), "icon": "fa-shapes", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Ideal para anime, stickers y logos.", "Ideal for anime, stickers and logos."), "endpoint": "/v1/images/remove-background-graphic", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-objects", "label": L("Borrar Objetos (Pincel)", "Remove Objects (Brush)"), "icon": "fa-eraser", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Usa el pincel para borrar lo que quieras.", "Use the brush to erase anything."), "endpoint": "/v1/images/remove-objects", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "input_mask", "type": "mask", "label": L("Máscara (B/N)", "Mask (B/W)"), "required": True}, {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "normal", "label": L("Normal", "Normal")}]}]},
    {"slug": "remove-reflection", "label": L("Quitar Reflejos", "Remove Reflections"), "icon": "fa-camera", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Suaviza reflejos en vidrios.", "Softens reflections on glass."), "endpoint": "/v1/images/remove-reflection", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "clean-mirror", "label": L("Limpiar Espejo", "Clean Mirror"), "icon": "fa-broom", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Quita destellos de espejos.", "Removes flash glare from mirrors."), "endpoint": "/v1/images/clean-mirror", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "enhance", "label": L("Escalar Resolución", "Upscale Resolution"), "icon": "fa-expand", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Mejora la calidad general.", "Improves overall quality."), "endpoint": "/v1/images/enhance", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}, {"name": "enhance_faces", "type": "checkbox", "label": L("Mejorar rostros", "Enhance faces"), "default": True}]},
    {"slug": "enhance-pro", "label": L("Escalar Rostros (Pro)", "Upscale Faces (Pro)"), "icon": "fa-user-check", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Ideal para fotos de personas.", "Ideal for photos of people."), "endpoint": "/v1/images/enhance/pro", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}]},
    {"slug": "enhance-art", "label": L("Escalar Arte / Anime", "Upscale Art / Anime"), "icon": "fa-dragon", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Ideal para dibujos.", "Ideal for drawings."), "endpoint": "/v1/images/enhance-art", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}]}]},
    {"slug": "restore-pro", "label": L("Restaurar Antigua (Pro)", "Restore Old (Pro)"), "icon": "fa-hammer", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Reparación severa de rasguños.", "Heavy damage repair."), "endpoint": "/v1/images/restore/pro", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "colorize-pro", "label": L("Colorear B/N (Pro)", "Colorize B/W (Pro)"), "icon": "fa-paint-roller", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Colorización avanzada y realista.", "Advanced colorization."), "endpoint": "/v1/images/colorize/pro", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "light-restore", "label": L("Corregir Iluminación", "Fix Lighting"), "icon": "fa-sun", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Arregla fotos oscuras.", "Fixes dark photos."), "endpoint": "/v1/images/light-restore", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "generate-zimage", "label": L("Crear: Z-Image (Texto)", "Create: Z-Image (Text)"), "icon": "fa-rocket", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Crea imagen rápida.", "Create image fast."), "endpoint": "/v1/images/generates/zimage", "response_type": "image", "needs_image": False, "fields": [
        {"name": "prompt", "type": "textarea", "label": L("Descripción de la imagen", "Prompt"), "required": True},
        {"name": "aspect_ratio", "type": "select", "label": L("Proporción (Tamaño en píxeles)", "Aspect Ratio"), "options": [
            {"value": "1:1", "label": "1:1 (Cuadrado - 1024x1024)"}, 
            {"value": "9:16", "label": "9:16 (Vertical/Story - 576x1024)"}, 
            {"value": "16:9", "label": "16:9 (Horizontal - 1024x576)"}, 
            {"value": "3:4", "label": "3:4 (Retrato - 768x1024)"}, 
            {"value": "4:3", "label": "4:3 (Paisaje - 1024x768)"},
            {"value": "2:3", "label": "2:3 (Póster - 683x1024)"},
            {"value": "3:2", "label": "3:2 (Foto - 1024x683)"}
        ]}
    ]},
    {"slug": "generate-qwen", "label": L("Crear: Qwen (Texto)", "Create: Qwen (Text)"), "icon": "fa-brain", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Motor HD realista.", "HD realistic engine."), "endpoint": "/v1/images/generates/qwen", "response_type": "image", "needs_image": False, "fields": [
        {"name": "prompt", "type": "textarea", "label": L("Descripción de la imagen", "Prompt"), "required": True},
        {"name": "aspect_ratio", "type": "select", "label": L("Proporción (Tamaño en píxeles)", "Aspect Ratio"), "options": [
            {"value": "1:1", "label": "1:1 (Cuadrado - 1024x1024)"}, 
            {"value": "9:16", "label": "9:16 (Vertical/Story - 576x1024)"}, 
            {"value": "16:9", "label": "16:9 (Horizontal - 1024x576)"}, 
            {"value": "3:4", "label": "3:4 (Retrato - 768x1024)"}, 
            {"value": "4:3", "label": "4:3 (Paisaje - 1024x768)"},
            {"value": "2:3", "label": "2:3 (Póster - 683x1024)"},
            {"value": "3:2", "label": "3:2 (Foto - 1024x683)"}
        ]}
    ]},
    {"slug": "fairy-art", "label": L("Retrato a Arte", "Portrait to Art"), "icon": "fa-wand-magic-sparkles", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Convierte fotos a Anime/Boceto o estilos creativos.", "Convert photos to Art."), "endpoint": "/v1/images/generates/art", "response_type": "image", "fields": [
        {"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, 
        {"name": "hybrid_style", "type": "select_hybrid", "label": L("Elige un Estilo", "Style"), "required": True, "options_url": "https://storage.googleapis.com/assets.snapedit.app/fairyai/anime_styles_6mar25.json", "options": [
            {"value": "PROMPT: Keep the exact same original shape, face, clothes and layout. Transform the photo into a highly detailed artistic black and white pencil sketch drawing.", "label": "✏️ Boceto a Lápiz"},
            {"value": "PROMPT: Keep the exact same original shape, face, clothes and layout. Transform the photo into a Studio Ghibli 2D anime style, vibrant flat colors.", "label": "🍃 Estilo Ghibli"},
            {"value": "PROMPT: Keep the exact same original shape, face, clothes and layout. Transform the photo into a 3D Pixar Disney style animated character.", "label": "🧸 Animado 3D"}
        ]}
    ]},
    {"slug": "generate-background", "label": L("Generar Fondo Nuevo", "Generate Background"), "icon": "fa-image", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Fondo para productos. ¡Sube un PNG SIN FONDO!", "Background for products."), "endpoint": "/v1/images/generates-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen (Transparente)", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Descripción del fondo", "Background prompt"), "required": True}]},
    {"slug": "sticker", "label": L("Crear Sticker", "Create Sticker"), "icon": "fa-note-sticky", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Haz un sticker de tu foto con borde blanco al instante.", "Make a sticker from photo."), "endpoint": "/v1/images/generates/sticker", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "master-color", "label": L("🎨 Master Color", "🎨 Master Color"), "icon": "fa-fill-drip", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Sustituye colores seleccionando por gotero y zona.", "Change colors by selecting zone and eyedropper."), "endpoint": "/local/canvas", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Sube tu Diseño", "Upload Design"), "required": True}]},
    {"slug": "edit-multi", "label": L("Fusión IA (Múltiple)", "AI Fusion (Multi)"), "icon": "fa-object-group", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Edita hasta 3 imágenes juntas.", "Edit using up to 3 images."), "endpoint": "/v1/images/edits/multi", "response_type": "image", "fields": [{"name": "input_image_0", "type": "image", "label": L("Imagen Base 1", "Base Image 1"), "required": True}, {"name": "input_image_1", "type": "image", "label": L("Imagen Extra 2", "Extra Image 2"), "required": False}, {"name": "input_image_2", "type": "image", "label": L("Imagen Extra 3", "Extra Image 3"), "required": False}, {"name": "prompt", "type": "textarea", "label": L("Instrucción", "Prompt"), "required": True}]},
    {"slug": "studio-vignette", "label": L("🌟 Resplandor Mágico", "🌟 Magic Glow"), "icon": "fa-star", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Añade resplandor HD a diseños sin fondo.", "Adds a glow to a transparent design."), "endpoint": "/local/canvas", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Sube tu Diseño (Sin Fondo)", "Upload Transparent Design"), "required": True}, {"name": "bg_color", "type": "color", "label": L("Color del Resplandor", "Glow Color"), "default": "#ff0000"}, {"name": "glow_size", "type": "range", "label": L("Grosor del Resplandor", "Glow Thickness"), "min": 1, "max": 100, "default": 30}]},
    {"slug": "textile-styles", "label": L("Texturas Mágicas 3D", "3D Magic Textures"), "icon": "fa-cubes", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Aplica lana, bordado, parche o inflado.", "Applies yarn, thread, patch or puffy styles."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Sube tu Diseño Original", "Upload Design"), "required": True}, {"name": "prompt", "type": "select", "label": L("Elige la Textura", "Select Texture"), "required": True, "options": [{"value": "Convert every single colored region... into a uniform 3D amigurumi crochet texture...", "label": L("🧶 Crochet HD", "HD Crochet")}, {"value": "Convert every single colored region... into a uniform 3D embroidery texture...", "label": L("🧵 Bordado HD", "Realistic Embroidery")}]}]},
    {"slug": "retouch-skin", "label": L("Retoque Facial", "Skin Retouch"), "icon": "fa-face-smile", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Limpia la piel automáticamente.", "Cleans skin automatically."), "endpoint": "/v1/images/retouch-skin", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]}
]

MODELS_BY_SLUG = {m["slug"]: m for m in MODELS}

# ==========================================
# RUTAS DE INTERFAZ
# ==========================================
@app.route("/")
def index():
    html = render_template("index.html")
    if request.args.get("tg_login") == "ok":
        nombre = request.args.get("name", "VIP")
        script_acceso = f"<script>sessionStorage.setItem('jj_session_perm', 'active'); sessionStorage.setItem('jj_user_name', {jsonify(nombre).get_data(as_text=True)}); window.history.replaceState({{}}, document.title, '/');</script>"
        html = html.replace("<head>", "<head>" + script_acceso, 1)
    elif request.args.get("tg_error"):
        err_msg = request.args.get("tg_error")
        script_err = f"<script>window.addEventListener('DOMContentLoaded', function() {{ var ge = document.getElementById('gateError'); if(ge) {{ ge.textContent = {jsonify(err_msg).get_data(as_text=True)}; ge.classList.add('show'); }} window.history.replaceState({{}}, document.title, '/'); }});</script>"
        html = html.replace("<head>", "<head>" + script_err, 1)
    resp = app.make_response(html)
    resp.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
    return resp

@app.route("/login-telegram", methods=["GET"])
def login_telegram_redirect():
    data = request.args.to_dict()
    if not data or 'hash' not in data: return redirect("/?tg_error=" + quote("Datos inválidos"))
    hash_recibido = data.pop('hash')
    data_check_string = '\n'.join(sorted([f'{k}={v}' for k, v in data.items()]))
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode('utf-8')).digest()
    if hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest() != hash_recibido:
        return redirect("/?tg_error=" + quote("Firma no válida"))
    user_id = data.get('id')
    first_name = data.get('first_name', 'VIP')
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember"
    try:
        resp = requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "user_id": user_id}, timeout=10).json()
        if resp.get('ok') and resp['result']['status'] in ['member', 'administrator', 'creator']:
            return redirect(f"/?tg_login=ok&name={quote(first_name)}")
        return redirect("/?tg_error=" + quote("No eres miembro del grupo VIP."))
    except Exception: return redirect("/?tg_error=" + quote("Error verificando grupo VIP."))

@app.route("/verify-telegram", methods=["POST"])
def verify_telegram():
    data = request.json
    if not data or 'hash' not in data: return jsonify({"access": False, "message": "Datos inválidos"}), 400
    data_check_arr = [f'{k}={v}' for k, v in data.items() if k != 'hash']
    data_check_string = '\n'.join(sorted(data_check_arr))
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode('utf-8')).digest()
    hash_calc = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
    if hash_calc != data['hash']: return jsonify({"access": False, "message": "Firma no válida"}), 403
    user_id = data.get('id')
    first_name = data.get('first_name', 'Usuario')
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember"
    try:
        resp = requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "user_id": user_id}, timeout=10).json()
        if resp.get('ok') and resp['result']['status'] in ['member', 'administrator', 'creator']: return jsonify({"access": True, "nombre": first_name})
        return jsonify({"access": False, "message": "No eres miembro del grupo VIP."})
    except Exception as e: return jsonify({"access": False, "message": str(e)}), 500

@app.route("/models")
def get_models(): return jsonify([{k: m[k] for k in ("slug", "label", "icon", "category", "desc", "fields", "response_type", "needs_image") if k in m} for m in MODELS])

@app.route("/proxy-image")
def proxy_image():
    url = request.args.get("url")
    dl = request.args.get("dl", "0")
    if not url: return jsonify({"error": True, "message": "No URL"}), 400
    raw_bytes, err = download_from_cdn_with_retry(url)
    if err: return jsonify({"error": True, "message": err}), 400
    resp_obj, err_img = validate_and_build_response(raw_bytes)
    if err_img: return jsonify({"error": True, "message": err_img}), 400
    if dl == "1": resp_obj.headers["Content-Disposition"] = "attachment; filename=JJ_Studio_Diseno.png"
    return resp_obj

# ==========================================
# MOTOR MATEMÁTICO V36 (SEMITONOS Y DETECTOR)
# ==========================================
def procesar_con_snapedit(ruta_imagen):
    url = "https://api.snapedit.app/v1/images/enhance-art"
    try:
        with open(ruta_imagen, 'rb') as f:
            response = requests.post(url, headers=HEADERS, files={'input_image': f}, data={'zoom_factor': '4'}, timeout=90)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                img_descargada = requests.get(data["data"][0]["url"], timeout=90).content
                nueva_ruta = ruta_imagen.replace(".", "_ia.")
                with open(nueva_ruta, 'wb') as f_out: f_out.write(img_descargada)
                return nueva_ruta
    except: pass
    return ruta_imagen 

def motor_local_semitonos(ruta_entrada, ruta_salida, color_hex, dot_size, angulo, tolerancia, saturacion, trama, reducir_pixeles, modo_suave_clasico, gamma_boost, fix_semi, target_w=None, target_h=None):
    img_orig = Image.open(ruta_entrada).convert("RGBA")
    if target_w and target_h:
        img_orig = img_orig.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if saturacion != 1.0:
        enhancer = ImageEnhance.Color(img_orig)
        img_orig = enhancer.enhance(saturacion)
    
    arr_visual = np.array(img_orig).copy() 
    ancho, alto = img_orig.size
    
    hex_str = color_hex.lstrip('#')
    c_target = np.array([int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)], dtype=np.float32)
    img_rgb = np.array(img_orig.convert("RGB"), dtype=np.float32)
    alpha_orig = np.array(img_orig.split()[3], dtype=np.float32)

    diff = np.sqrt(np.sum((img_rgb - c_target)**2, axis=2))
    
    if modo_suave_clasico:
        dist_max = tolerancia * 2.55 
        opacidad_target = np.clip(1.0 - (diff / (dist_max + 1e-5)), 0.0, 1.0)
    else:
        dist_max = tolerancia * 4.0
        rango_fade = 60.0
        opacidad_target = np.clip(1.0 - ((diff - dist_max + rango_fade) / rango_fade), 0.0, 1.0)

    if gamma_boost != 1.0:
        opacidad_target = np.power(opacidad_target, 1.0/gamma_boost)

    opacidad_target = opacidad_target * (alpha_orig / 255.0)

    x = np.arange(ancho, dtype=np.float32)
    y = np.arange(alto, dtype=np.float32)
    xv, yv = np.meshgrid(x, y)

    theta = np.radians(angulo)
    xr = xv * np.cos(theta) - yv * np.sin(theta)
    yr = xv * np.sin(theta) + yv * np.cos(theta)

    if trama == "line": patron = (np.cos(2 * np.pi * yr / dot_size) + 1.0) / 2.0
    elif trama == "ellipse": patron = (np.cos(2 * np.pi * xr / dot_size) + np.cos(2 * np.pi * yr / (dot_size/2.0))) / 4.0 + 0.5
    elif trama == "roseta":
        p1 = (np.cos(2 * np.pi * xr / dot_size) + np.cos(2 * np.pi * yr / dot_size)) / 4.0 + 0.5
        xr2 = xv * np.cos(theta + np.pi/4) - yv * np.sin(theta + np.pi/4)
        yr2 = xv * np.sin(theta + np.pi/4) + yv * np.cos(theta + np.pi/4)
        p2 = (np.cos(2 * np.pi * xr2 / dot_size) + np.cos(2 * np.pi * yr2 / dot_size)) / 4.0 + 0.5
        patron = (p1 + p2) / 2.0
    else: patron = (np.cos(2 * np.pi * xr / dot_size) + np.cos(2 * np.pi * yr / dot_size)) / 4.0 + 0.5

    mask_remover = opacidad_target > patron
    alpha_final = np.where(mask_remover, 0, alpha_orig).astype(np.uint8)

    if fix_semi: alpha_final = np.where((alpha_final > 15) & (alpha_final < 240), 255, alpha_final)

    arr_visual[:,:,3] = alpha_final
    img_final = Image.fromarray(arr_visual, "RGBA")
    
    if reducir_pixeles: img_final = img_final.filter(ImageFilter.MinFilter(3))

    img_final.save(ruta_salida, "PNG", optimize=True)
    img_orig.close()
    img_final.close()
    gc.collect()

@app.route('/api/procesar', methods=['POST'])
def procesar_dtf():
    try:
        if 'imagen' not in request.files: return jsonify({"error": "No se subió imagen"}), 400
        file = request.files['imagen']
        os.makedirs("temp", exist_ok=True)
        ruta_entrada = os.path.join("temp", f"orig_{int(time.time())}.png")
        ruta_salida = os.path.join("temp", f"final_{int(time.time())}.png")
        file.save(ruta_entrada)

        color_hex = request.form.get('color', '#000000')
        saturacion = float(request.form.get('sat', '1.0'))
        modo = request.form.get('limpieza', 'global')
        trama = request.form.get('trama', 'round')
        tolerancia = int(request.form.get('tolerancia', 20))
        dot_size = int(request.form.get('px', 10))
        angulo = int(request.form.get('angulo', 22))
        
        usar_ia = request.form.get('usar_ia') == 'true'
        choke = request.form.get('choke') == 'true'
        fix_semi = request.form.get('fix_semi') == 'true'

        target_w = int((float(request.form.get('ancho', 29.7)) / 2.54) * 300)
        target_h = int((float(request.form.get('alto', 42.0)) / 2.54) * 300)

        if usar_ia: ruta_entrada = procesar_con_snapedit(ruta_entrada)

        modo_suave_clasico = (modo == "baja")
        gamma_boost = 1.0 if modo_suave_clasico else 0.8 

        motor_local_semitonos(ruta_entrada, ruta_salida, color_hex, dot_size, angulo, tolerancia, saturacion, trama, choke, modo_suave_clasico, gamma_boost, fix_semi, target_w, target_h)
        return send_file(ruta_salida, mimetype='image/png')
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/reparar', methods=['POST'])
def reparar_api():
    try:
        if 'imagen' not in request.files: return "Error", 400
        file = request.files['imagen']
        target_w = int((float(request.form.get('ancho', 29.7)) / 2.54) * 300)
        target_h = int((float(request.form.get('alto', 42.0)) / 2.54) * 300)

        os.makedirs("temp", exist_ok=True)
        ruta_in = os.path.join("temp", f"limpio_in_{int(time.time())}.png")
        ruta_out = os.path.join("temp", f"limpio_out_{int(time.time())}.png")
        file.save(ruta_in)
        
        img = Image.open(ruta_in).convert("RGBA")
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        arr = np.array(img)
        arr[:, :, 3] = np.where(arr[:, :, 3] > 100, 255, 0).astype(np.uint8)
        
        img_final = Image.fromarray(arr, mode="RGBA")
        img_final.save(ruta_out, format="PNG", dpi=(300, 300))
        del arr; gc.collect(); img.close(); img_final.close()
        
        return send_file(ruta_out, mimetype='image/png')
    except Exception as e: return str(e), 500

# ==========================================
# RUTAS DE HERRAMIENTAS DE IA ORIGINALES
# ==========================================
def resize_if_needed(file_bytes, slug, original_filename="image.jpg", zoom_factor="2"):
    if not file_bytes or len(file_bytes) == 0: raise ValueError("0 bytes.")
    try:
        max_dim = 1500 if ("enhance" in slug and str(zoom_factor) != "8") else (500 if "enhance" in slug else 2400)
        img = Image.open(io.BytesIO(file_bytes))
        img_format = (img.format or "PNG").upper()
        width, height = img.size
        if max(width, height) <= max_dim and img_format in ("JPEG", "PNG"):
            img.close(); return file_bytes, original_filename, f"image/{img_format.lower()}"
        filtro = Image.BILINEAR if max(width, height) > 4000 else Image.Resampling.LANCZOS
        img.thumbnail((max_dim, max_dim), filtro)
        buffer = io.BytesIO()
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA"); img.save(buffer, format="PNG", optimize=False); return buffer.getvalue(), "image.png", "image/png"
        else:
            img = img.convert("RGB"); img.save(buffer, format="JPEG", quality=95); return buffer.getvalue(), "image.jpg", "image/jpeg"
    except Exception: return file_bytes, original_filename, "image/png"

def download_from_cdn_with_retry(url_img, retries=3):
    for _ in range(retries):
        try:
            r = requests.get(url_img, headers={'User-Agent': 'Mozilla/5.0'}, timeout=45)
            if r.status_code == 200 and len(r.content) > 100: return r.content, None
        except: time.sleep(1)
    return None, "Error CDN"

def validate_and_build_response(raw_bytes):
    if not raw_bytes or len(raw_bytes) < 64: return None, "Archivo vacío"
    if raw_bytes[:8] == b'\x89PNG\r\n\x1a\n': return Response(raw_bytes, mimetype="image/png"), None
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        out = io.BytesIO(); img.save(out, format="PNG"); return Response(out.getvalue(), mimetype="image/png"), None
    except: return Response(raw_bytes, mimetype="image/png"), None

@app.route("/run/<slug>", methods=["POST"])
def run_model(slug):
    model = MODELS_BY_SLUG.get(slug)
    if not model: return jsonify({"error": True, "message": "Desconocida"}), 404
    try:
        target_endpoint = model.get("endpoint")
        files, data = {}, {}
        for key, value in request.form.items(): data[key] = value
        for key, file_obj in request.files.items():
            if file_obj and file_obj.filename:
                files[key] = (file_obj.filename, file_obj.read(), file_obj.mimetype)

        if slug in ["textile-styles", "edit-multi", "extract-print"]: data["mode"] = "editing"
        if slug == "extract-print":
            data["prompt"] = "Zoom in and crop tightly around the printed graphic artwork... on a pure solid flat background."
        if slug == "fairy-art":
            style_val = data.pop("hybrid_style", "")
            if style_val.startswith("PROMPT:"):
                target_endpoint = "/v1/images/edits"; data["mode"] = "editing"; data["prompt"] = style_val.replace("PROMPT:", "").strip()
            else: target_endpoint = "/v1/images/generates/art"; data["style"] = style_val

        r = requests.post(BASE + target_endpoint, headers=HEADERS, files=files if files else None, data=data if data else None, timeout=180)
        if "application/json" in r.headers.get("Content-Type", "").lower() and model.get("response_type") == "json": return jsonify(r.json()), 200
        
        datos = r.json() if "application/json" in r.headers.get("Content-Type", "").lower() else {}
        url_img = datos.get("data", [{}])[0].get("url") if isinstance(datos.get("data"), list) else None
        if not url_img: url_img = datos.get("url")
        if not url_img: return jsonify({"error": True, "message": "Error de IA"}), 400

        raw_bytes, _ = download_from_cdn_with_retry(url_img)
        resp_obj, _ = validate_and_build_response(raw_bytes)
        return resp_obj
    except Exception as e: return jsonify({"error": True, "message": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
