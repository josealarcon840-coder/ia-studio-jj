import os
import io
import base64
import requests
import hashlib
import hmac
import gc  
import time 
from flask import Flask, render_template, request, jsonify, Response
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

app = Flask(__name__)

API_KEY = os.environ.get("SNAPEDIT_API_KEY", "sk-snap-uuh6Z0veQTW7z3DSQ7TUr5yuyaC7HIHAoUchqM_KrfI")
BASE = "https://api.snapedit.app"
HEADERS = {"api-key": API_KEY}
ALLOWED_STYLE_DOMAINS = ("storage.googleapis.com",)

TELEGRAM_BOT_TOKEN = "8066431561:AAE4iCEkjw4ynw5VQC4OVsC0liH_lDv9mcY" 
TELEGRAM_CHAT_ID = "-1002330690954"

def L(es, en): return {"es": es, "en": en}

MODELS = [
    {"slug": "detect-objects", "label": L("Borrador Mágico (Auto)", "Magic Eraser (Auto)"), "icon": "fa-magic", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Encuentra objetos para borrarlos con un clic.", "Finds objects to erase them with a click."), "endpoint": "/v1/images/detect-objects", "response_type": "json", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen Base", "Base Image"), "required": True}, {"name": "lang", "type": "select", "label": L("Idioma", "Language"), "options": [{"value": "es", "label": L("Español", "Spanish")}]}, {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "super", "label": L("Super", "Super")}, {"value": "normal", "label": L("Normal", "Normal")}]}]},
    {"slug": "detect-text", "label": L("Borrar Texto (Auto)", "Erase Text (Auto)"), "icon": "fa-font", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Detecta y borra los textos automáticamente.", "Detects and erases text automatically."), "endpoint": "/v1/images/detect-text", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "detect-wires", "label": L("Borrar Cables (Auto)", "Erase Wires (Auto)"), "icon": "fa-plug", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Detecta y borra cables/postes.", "Detects and erases wires."), "endpoint": "/v1/images/detect-wires", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "remove-background", "label": L("Quitar Fondo (Fotos)", "Remove Background"), "icon": "fa-user-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Recorte de personas o productos.", "Cutout for people/products."), "endpoint": "/v1/images/remove-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-background-graphic", "label": L("Quitar Fondo (Arte)", "Remove BG (Graphics)"), "icon": "fa-shapes", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Ideal para anime, stickers y logos.", "Ideal for anime, stickers and logos."), "endpoint": "/v1/images/remove-background-graphic", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-objects", "label": L("Borrar Objetos (Máscara)", "Remove Objects (Mask)"), "icon": "fa-eraser", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Sube tu máscara en blanco y negro.", "Upload a B/W mask to erase."), "endpoint": "/v1/images/remove-objects", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "input_mask", "type": "mask", "label": L("Máscara (B/N)", "Mask (B/W)"), "required": True}, {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "normal", "label": L("Normal", "Normal")}]}]},
    {"slug": "erase-text", "label": L("Borrar Texto (Máscara)", "Erase Text (Mask)"), "icon": "fa-text-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Borra textos usando tu máscara.", "Erase texts using your mask."), "endpoint": "/v1/images/remove-text", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "input_mask", "type": "mask", "label": L("Máscara", "Mask"), "required": True}, {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "normal", "label": L("Normal", "Normal")}]}]},
    {"slug": "erase-wires", "label": L("Borrar Cables (Máscara)", "Erase Wires (Mask)"), "icon": "fa-bolt-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Borra cables usando tu máscara.", "Erase wires using mask."), "endpoint": "/v1/images/remove-wires", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "input_mask", "type": "mask", "label": L("Máscara", "Mask"), "required": True}]},
    {"slug": "remove-reflection", "label": L("Quitar Reflejos", "Remove Reflections"), "icon": "fa-camera", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Suaviza reflejos en vidrios.", "Softens reflections on glass."), "endpoint": "/v1/images/remove-reflection", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "clean-mirror", "label": L("Limpiar Espejo", "Clean Mirror"), "icon": "fa-broom", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Quita destellos de espejos.", "Removes flash glare from mirrors."), "endpoint": "/v1/images/clean-mirror", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "enhance", "label": L("Escalar Resolución", "Upscale Resolution"), "icon": "fa-expand", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Mejora la calidad general.", "Improves overall quality."), "endpoint": "/v1/images/enhance", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen (máx 1500px)", "Image (max)"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}, {"name": "enhance_faces", "type": "checkbox", "label": L("Mejorar rostros", "Enhance faces"), "default": True}]},
    {"slug": "enhance-pro", "label": L("Escalar Rostros (Pro)", "Upscale Faces (Pro)"), "icon": "fa-user-check", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Ideal para fotos de personas.", "Ideal for photos of people."), "endpoint": "/v1/images/enhance/pro", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}]},
    {"slug": "enhance-art", "label": L("Escalar Arte / Anime", "Upscale Art / Anime"), "icon": "fa-dragon", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Ideal para dibujos.", "Ideal for drawings."), "endpoint": "/v1/images/enhance-art", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}]},
    {"slug": "restore", "label": L("Restaurar Antigua", "Restore Old Photo"), "icon": "fa-clock-rotate-left", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Repara rasguños leves.", "Repairs light scratches."), "endpoint": "/v1/images/restore", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "restore-pro", "label": L("Restaurar Antigua (Pro)", "Restore Old (Pro)"), "icon": "fa-hammer", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Reparación severa.", "Heavy damage repair."), "endpoint": "/v1/images/restore/pro", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "colorize", "label": L("Colorear B/N", "Colorize B/W"), "icon": "fa-palette", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Da color a fotos antiguas.", "Adds color to old photos."), "endpoint": "/v1/images/colorize", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "colorize-pro", "label": L("Colorear B/N (Pro)", "Colorize B/W (Pro)"), "icon": "fa-paint-roller", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Colorización avanzada.", "Advanced colorization."), "endpoint": "/v1/images/colorize/pro", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "light-restore", "label": L("Corregir Iluminación", "Fix Lighting"), "icon": "fa-sun", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Arregla fotos oscuras.", "Fixes dark photos."), "endpoint": "/v1/images/light-restore", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "generate-zimage", "label": L("Crear: Z-Image (Texto)", "Create: Z-Image (Text)"), "icon": "fa-rocket", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Crea imagen rápida.", "Create image fast."), "endpoint": "/v1/images/generates/zimage", "response_type": "image", "needs_image": False, "fields": [{"name": "prompt", "type": "textarea", "label": L("Descripción", "Prompt"), "required": True}, {"name": "aspect_ratio", "type": "cm_auto_magic", "label": L("Medidas en Centímetros", "Size (CM)")}]},
    {"slug": "generate-qwen", "label": L("Crear: Qwen (Texto)", "Create: Qwen (Text)"), "icon": "fa-brain", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Motor HD realista.", "HD realistic engine."), "endpoint": "/v1/images/generates/qwen", "response_type": "image", "needs_image": False, "fields": [{"name": "prompt", "type": "textarea", "label": L("Descripción", "Prompt"), "required": True}, {"name": "aspect_ratio", "type": "cm_auto_magic", "label": L("Medidas en Centímetros", "Size (CM)")}]},
    
    {"slug": "fairy-art", "label": L("Retrato a Arte", "Portrait to Art"), "icon": "fa-wand-magic-sparkles", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Convierte fotos a Anime/3D.", "Convert photos to Anime/3D."), "endpoint": "/v1/images/generates/art", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "style", "type": "select", "label": L("Estilo", "Style"), "required": True, "options_url": "https://storage.googleapis.com/assets.snapedit.app/fairyai/anime_styles_6mar25.json"}]},
    {"slug": "generate-background", "label": L("Generar Fondo Nuevo", "Generate Background"), "icon": "fa-image", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Fondo para productos.", "Background for products."), "endpoint": "/v1/images/generates-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Descripción del fondo", "Background prompt"), "required": True}]},
    {"slug": "sticker", "label": L("Crear Sticker", "Create Sticker"), "icon": "fa-note-sticky", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Haz un sticker de tu foto.", "Make a sticker from photo."), "endpoint": "/v1/images/generates/sticker", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Estilo (Ej: Zombie)", "Style (e.g. Zombie)"), "required": True}]},

    {"slug": "edit-image", "label": L("Edición Mágica (Texto)", "Magic Edit (Text)"), "icon": "fa-wand-sparkles", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Edita usando órdenes.", "Edit using text prompts."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Instrucción", "Prompt"), "required": True}, {"name": "mode", "type": "select", "label": L("Modo", "Mode"), "required": True, "options": [{"value": "editing", "label": L("General", "General")}, {"value": "inpaint", "label": L("Inpaint", "Inpaint")}]}, {"name": "input_mask", "type": "mask", "label": L("Máscara", "Mask"), "required": False}]},
    
    {"slug": "textile-styles", "label": L("Texturas Mágicas 3D", "3D Magic Textures"), "icon": "fa-cubes", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Aplica lana, hilo o estilo inflado 3D.", "Applies yarn, thread or puffy textures."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [
        {"name": "input_image", "type": "image", "label": L("Sube tu Diseño Original", "Upload Design"), "required": True}, 
        {"name": "prompt", "type": "select", "label": L("Elige la Textura", "Select Texture"), "required": True, "options": [
            {"value": "Apply 3D amigurumi crochet texture to the entire image. Strictly preserve the exact original background, all elements, composition, original colors, and transparent areas. Do not remove anything, do not add frames, hoops or white backgrounds. Only change the material of existing elements to knitted yarn.", "label": L("🧶 Crochet / Amigurumi (Lana)", "Crochet / Amigurumi")},
            {"value": "Apply highly detailed realistic embroidery texture to the entire image. Strictly preserve the exact original background, all elements, composition, original colors, and transparent areas. Do not remove anything, do not add frames, hoops or white backgrounds. Only change the material of existing elements to thick colorful threads and 3D stitches.", "label": L("🧵 Bordado Realista (Hilos 3D)", "Realistic Embroidery")},
            {"value": "Apply textile embroidery patch style to the entire image. Strictly preserve the exact original background, all elements, composition, original colors, and transparent areas. Do not remove anything, do not add stitched borders if they don't exist, no background fabric. Only change the material of existing elements to high quality thread texture.", "label": L("🏷️ Parche Textil (Sin Bordes)", "Textile Patch")},
            {"value": "Apply 3D inflated balloon puffy texture to the entire image. Make it look like soft, puffy, glossy plastic or vinyl. Strictly preserve the exact original background, all elements, composition, original colors, and transparent areas. Do not remove anything, do not add backgrounds. Only change the material of existing elements to 3D inflated balloon.", "label": L("🎈 Estilo Inflado 3D (Globo/Puffer)", "3D Inflated/Puffer")}
        ]}
    ]},

    {"slug": "retouch-skin", "label": L("Retoque Facial", "Skin Retouch"), "icon": "fa-face-smile", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Limpia la piel automáticamente.", "Cleans skin automatically."), "endpoint": "/v1/images/retouch-skin", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    # 🚀 --- IA PARA VIDEOS ---
    {"slug": "enhance-video", "label": L("Mejorar Video 2K/4K", "Enhance Video Pro"), "icon": "fa-film", "category": L("6. IA para Videos", "6. AI Video"), "desc": L("Sube la resolución de videos.", "Upscale video to 2K/4K."), "endpoint": "/v1/videos/enhance-pro", "response_type": "video", "fields": [
        {"name": "input_image", "type": "image", "label": L("Sube tu Video (MP4)", "Upload Video"), "required": True}, 
        {"name": "zoom_factor", "type": "select", "label": L("Resolución", "Resolution"), "required": True, "options": [{"value": "2K", "label": L("2K Calidad Alta", "2K High Quality")}, {"value": "4K", "label": L("4K Ultra HD", "4K Ultra HD")}]},
        {"name": "is_preview", "type": "select", "label": L("Duración", "Duration"), "required": True, "options": [{"value": "true", "label": L("Muestra rápida (3 Segundos)", "Preview (3 Sec)")}, {"value": "false", "label": L("Video Completo", "Full Video")}]}
    ]},
    {"slug": "image-to-video", "label": L("Animar Foto a Video", "Image to Video"), "icon": "fa-video", "category": L("6. IA para Videos", "6. AI Video"), "desc": L("Dale vida y movimiento a una imagen.", "Animate photo with AI."), "endpoint": "/v1/videos/image-to-video", "response_type": "video", "fields": [
        {"name": "input_image", "type": "image", "label": L("Sube tu Foto", "Upload Image"), "required": True}, 
        {"name": "prompt", "type": "textarea", "label": L("Instrucción de Movimiento", "Motion Prompt"), "required": True},
        {"name": "duration", "type": "select", "label": L("Duración", "Duration"), "required": True, "options": [{"value": "4", "label": L("4 Segundos", "4 Seconds")}, {"value": "8", "label": L("8 Segundos", "8 Seconds")}]}
    ]}
]

MODELS_BY_SLUG = {m["slug"]: m for m in MODELS}

def resize_if_needed(file_bytes, slug, original_filename="image.jpg"):
    try:
        max_dim = 1500 if "enhance" in slug else (512 if "pose" in slug else 3000)
        img = Image.open(io.BytesIO(file_bytes))
        img_format = (img.format or "JPEG").upper()
        width, height = img.size
        
        needs_resize = (max(width, height) > max_dim)
        needs_convert = (img_format == "JPEG" and img.mode in ("RGBA", "P"))
        
        if not needs_resize and not needs_convert:
            return file_bytes, original_filename, f"image/{img_format.lower()}"
            
        if needs_resize:
            scale = max_dim / max(width, height)
            img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
            
        if needs_convert: 
            img = img.convert("RGB")
            
        buffer = io.BytesIO()
        if img_format == "JPEG":
            img.save(buffer, format=img_format, quality=100, subsampling=0)
        else:
            img.save(buffer, format=img_format)
            
        return buffer.getvalue(), original_filename, f"image/{img_format.lower()}"
    except Exception:
        return file_bytes, original_filename, "image/jpeg"
    finally:
        gc.collect()

@app.route("/")
def index(): return render_template("index.html")

@app.route("/models")
def get_models():
    public_fields = ("slug", "label", "icon", "category", "desc", "fields", "response_type", "needs_image")
    return jsonify([{k: m[k] for k in public_fields if k in m} for m in MODELS])

@app.route("/style-list")
def style_list():
    url = request.args.get("url", "")
    if not url or not any(url.startswith(f"https://{d}") for d in ALLOWED_STYLE_DOMAINS): return jsonify({"error": True}), 400
    try: return jsonify(requests.get(url, timeout=15).json())
    except: return jsonify({"error": True}), 500

@app.route("/proxy-image")
def proxy_image():
    url = request.args.get("url")
    dl = request.args.get("dl", "0")
    if not url: return "No URL", 400
    try:
        r = requests.get(url, timeout=60)
        if r.status_code != 200:
            return "Error CDN SnapEdit", 400
            
        headers = {}
        if dl == "1":
            headers["Content-Disposition"] = "attachment; filename=JJ_Studio_Diseño.png"
            
        return Response(r.content, mimetype=r.headers.get("Content-Type", "image/png"), headers=headers)
    except Exception as e:
        return str(e), 500

@app.route("/verify-telegram", methods=["POST"])
def verify_telegram():
    data = request.json
    if not data or 'hash' not in data:
        return jsonify({"access": False, "message": "Datos inválidos"}), 400

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
        if resp.get('ok') and resp['result']['status'] in ['member', 'administrator', 'creator']:
            return jsonify({"access": True, "nombre": first_name})
        return jsonify({"access": False, "message": "No eres miembro del grupo VIP."})
    except Exception as e:
        return jsonify({"access": False, "message": str(e)}), 500

@app.route("/run/<slug>", methods=["POST"])
def run_model(slug):
    model = MODELS_BY_SLUG.get(slug)
    
    if slug == "execute-magic-erase": model = {"endpoint": "/v1/images/remove-objects", "fields": []}
    elif slug in ["erase-text", "erase-wires"]:
        model = model.copy()
        model["endpoint"] = "/v1/images/remove-objects"
        
    if not model: return jsonify({"error": True, "message": "Herramienta desconocida"}), 404

    try:
        # =======================================================
        # 🎬 LÓGICA DE VIDEO ASÍNCRONA
        # =======================================================
        if model.get("response_type") == "video":
            file_obj = list(request.files.values())[0]
            file_bytes = file_obj.read()
            
            payload = {}
            for key, value in request.form.items():
                if value.lower() == "true": payload[key] = True
                elif value.lower() == "false": payload[key] = False
                elif value.isdigit(): payload[key] = int(value)
                else: payload[key] = value

            url_upload_endpoint = f"{BASE}{model['endpoint']}/upload"
            r1 = requests.post(url_upload_endpoint, headers={"api-key": API_KEY, "Content-Type": "application/json"}, json=payload if payload else None)
            
            if r1.status_code != 200: 
                return jsonify({"error": True, "message": f"Fallo al iniciar servidor de video. Detalle: {r1.text}"}), 400
            
            datos_carga = r1.json()
            task_id = datos_carga.get("task_id") or datos_carga.get("data", {}).get("task_id")
            upload_url = (
                datos_carga.get("image_upload_url") or 
                datos_carga.get("video_upload_url") or 
                datos_carga.get("upload_url") or 
                datos_carga.get("url") or 
                datos_carga.get("signed_url") or 
                datos_carga.get("data", {}).get("image_upload_url") or 
                datos_carga.get("data", {}).get("upload_url") or 
                datos_carga.get("data", {}).get("url")
            )
            
            if not task_id or not upload_url:
                return jsonify({"error": True, "message": f"Respuesta inesperada de SnapEdit al subir: {datos_carga}"}), 400

            mime_type = "video/mp4" if "video" in slug and not slug.startswith("image-to") else "image/jpeg"
            r2 = requests.put(upload_url, data=file_bytes, headers={"Content-Type": mime_type})
            if r2.status_code not in [200, 201]: 
                return jsonify({"error": True, "message": f"Fallo al subir el archivo al servidor (Código {r2.status_code}). Detalle: {r2.text}"}), 400

            max_intentos = 45 
            for _ in range(max_intentos):
                time.sleep(5)
                r4 = requests.get(f"{BASE}{model['endpoint']}/tasks/{task_id}", headers=HEADERS)
                if r4.status_code == 200:
                    status_data = r4.json()
                    estado = status_data.get("status")
                    
                    if estado == "COMPLETED":
                        video_url = status_data.get("download_url") or status_data.get("video_url") or status_data.get("url")
                        return jsonify({"is_video": True, "url": video_url})
                    elif estado == "FAILED":
                        return jsonify({"error": True, "message": status_data.get("error_msg", "Error renderizando video.")}), 400
            
            return jsonify({"error": True, "message": "Tiempo de espera agotado. El video está tardando demasiado en renderizarse."}), 400


        # =======================================================
        # 🖼️ LÓGICA DE IMÁGENES (CORREGIDA PARA 'generates-background')
        # =======================================================
        files, data = {}, {}
        
        for key, file_obj in request.files.items():
            if file_obj and file_obj.filename:
                buf, fname, mime = resize_if_needed(file_obj.read(), slug, file_obj.filename)
                
                # 🛠️ CORRECCIÓN: Si es genera-fondo u otro endpoint que pide 'image' en JSON o multipart
                if slug == "generate-background" or model["endpoint"] == "/v1/images/generates-background":
                    # Este endpoint de SnapEdit acepta 'image' en formato archivo o Base64. Lo enviamos como 'image'
                    api_key = "image"
                else:
                    api_key = key
                    
                ext = "png" if "png" in mime else "jpg"
                files[api_key] = (f"imagen.{ext}", buf, mime)

        for key, value in request.form.items():
            if value: data[key] = value

        if slug == "textile-styles":
            data["mode"] = "editing"

        if slug in ["detect-text", "detect-wires"]:
            r1 = requests.post(BASE + model["endpoint"], headers=HEADERS, files=files, timeout=120)
            if r1.status_code == 200:
                d_json = r1.json()
                if d_json.get("detected") and d_json.get("mask"):
                    mask_b64 = d_json["mask"]
                    if "," in mask_b64: mask_b64 = mask_b64.split(",", 1)[1]
                    mask_b64 = mask_b64.replace('\n', '').replace('\r', '').strip()
                    mask_b64 += "=" * ((4 - len(mask_b64) % 4) % 4)
                    
                    f2 = {
                        "input_image": files.get("input_image") or files.get("image"),
                        "input_mask": ("mask.png", base64.b64decode(mask_b64), "image/png")
                    }
                    ep_remove = "/v1/images/remove-text" if slug == "detect-text" else "/v1/images/remove-wires"
                    response = requests.post(BASE + ep_remove, headers=HEADERS, files=f2, data={"erase_mode": "ultra"}, timeout=300)
                else:
                    return jsonify({"error": True, "message": "No se detectó texto o cables en la imagen."}), 400
            else:
                response = r1
        else:
            if slug == "execute-magic-erase":
                files = None
                data.pop("input_image", None)

            if model.get("needs_image") is False:
                payload = {}
                if "prompt" in data: payload["prompt"] = data["prompt"]
                if "aspect_ratio" in data: payload["aspect_ratio"] = data["aspect_ratio"]
                
                headers_gen = {"api-key": API_KEY, "Content-Type": "application/json"}
                response = requests.post(BASE + model["endpoint"], headers=headers_gen, json=payload, timeout=120)
            else:
                response = requests.post(BASE + model["endpoint"], headers=HEADERS, files=files if files else None, data=data if data else None, timeout=300)
        
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            datos = response.json()
            if response.status_code == 200:
                url_img = None
                if "data" in datos and isinstance(datos["data"], list) and len(datos["data"]) > 0 and "url" in datos["data"][0]:
                    url_img = datos["data"][0]["url"]
                elif "data" in datos and isinstance(datos["data"], dict) and "url" in datos["data"]:
                    url_img = datos["data"]["url"]
                elif "url" in datos:
                    url_img = datos["url"]

                if url_img:
                    try:
                        r_img = requests.get(url_img, timeout=60)
                        if r_img.status_code == 200:
                            try:
                                img_obj = Image.open(io.BytesIO(r_img.content))
                                buf = io.BytesIO()
                                img_obj.save(buf, format="PNG", dpi=(300, 300))
                                return Response(buf.getvalue(), mimetype="image/png")
                            except:
                                return jsonify({"error": True, "message": "La IA no devolvió un formato de imagen válido."}), 400
                        else:
                            return jsonify({"error": True, "message": "Fallo al descargar la imagen procesada de la nube."}), 400
                    except Exception as e:
                        return jsonify({"error": True, "message": str(e)}), 400
                else:
                    return jsonify(datos), 200
            else:
                return jsonify({"error": True, "message": datos.get("message", str(datos))}), 400
        else:
            if response.status_code != 200:
                return jsonify({"error": True, "message": f"Servidores de la IA saturados (Código {response.status_code}). Intenta de nuevo."}), 400
            
            try:
                img_obj = Image.open(io.BytesIO(response.content))
                buf = io.BytesIO()
                img_obj.save(buf, format="PNG", dpi=(300, 300))
                return Response(buf.getvalue(), mimetype="image/png")
            except:
                return jsonify({"error": True, "message": "La respuesta de la IA está corrupta."}), 400

    except Exception as e: 
        print(f"❌ ERROR: {str(e)}")
        return jsonify({"error": True, "message": f"Error interno: {str(e)}"}), 400
    finally:
        gc.collect()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
