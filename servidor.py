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

# ========================================================
# 🚀 CONFIGURACIÓN DE TELEGRAM Y SNAPEDIT
# ========================================================
API_KEY = os.environ.get("SNAPEDIT_API_KEY", "sk-snap-uuh6Z0veQTW7z3DSQ7TUr5yuyaC7HIHAoUchqM_KrfI")
BASE = "https://api.snapedit.app"
HEADERS = {"api-key": API_KEY}
ALLOWED_STYLE_DOMAINS = ("storage.googleapis.com",)

TELEGRAM_BOT_TOKEN = "8066431561:AAE4iCEkjw4ynw5VQC4OVsC0liH_lDv9mcY" 
TELEGRAM_CHAT_ID = "-1002330690954"

def L(es, en): return {"es": es, "en": en}

MODELS = [
    # --- Detección y Borrado Mágico ---
    {"slug": "detect-objects", "label": L("Borrador Mágico (Auto)", "Magic Eraser (Auto)"), "icon": "fa-magic", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Encuentra objetos para borrarlos con un clic.", "Finds objects to erase them with a click."), "endpoint": "/v1/images/detect-objects", "response_type": "json", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen Base", "Base Image"), "required": True}, {"name": "lang", "type": "select", "label": L("Idioma", "Language"), "options": [{"value": "es", "label": L("Español", "Spanish")}]}, {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "super", "label": L("Super", "Super")}, {"value": "normal", "label": L("Normal", "Normal")}]}]},
    {"slug": "detect-text", "label": L("Borrar Texto (Auto)", "Erase Text (Auto)"), "icon": "fa-font", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Detecta y borra los textos automáticamente.", "Detects and erases text automatically."), "endpoint": "/v1/images/detect-text", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    
    # --- Eliminar y Máscaras ---
    {"slug": "remove-background", "label": L("Quitar Fondo (Fotos)", "Remove Background"), "icon": "fa-user-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Recorte de personas o productos.", "Cutout for people/products."), "endpoint": "/v1/images/remove-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-background-graphic", "label": L("Quitar Fondo (Arte)", "Remove BG (Graphics)"), "icon": "fa-shapes", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Ideal para anime, stickers y logos.", "Ideal for anime, stickers and logos."), "endpoint": "/v1/images/remove-background-graphic", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    # --- EDICIÓN DE VIDEO (NUEVO) ---
    {"slug": "enhance-video", "label": L("Mejorar Video 2K/4K", "Enhance Video Pro"), "icon": "fa-film", "category": L("6. IA para Videos", "6. AI Video"), "desc": L("Sube la resolución de videos.", "Upscale video to 2K/4K."), "endpoint": "/v1/videos/enhance-pro", "response_type": "video", "fields": [
        {"name": "input_image", "type": "image", "label": L("Sube tu Video (MP4)", "Upload Video"), "required": True}, 
        {"name": "zoom_factor", "type": "select", "label": L("Resolución", "Resolution"), "required": True, "options": [{"value": "2K", "label": "2K Calidad Alta"}, {"value": "4K", "label": "4K Ultra HD"}]},
        {"name": "is_preview", "type": "select", "label": L("Duración", "Duration"), "required": True, "options": [{"value": "true", "label": "Muestra rápida (3 Segundos)"}, {"value": "false", "label": "Video Completo"}]}
    ]},
    {"slug": "image-to-video", "label": L("Animar Foto a Video", "Image to Video"), "icon": "fa-video", "category": L("6. IA para Videos", "6. AI Video"), "desc": L("Dale vida y movimiento a una imagen.", "Animate photo with AI."), "endpoint": "/v1/videos/image-to-video", "response_type": "video", "fields": [
        {"name": "input_image", "type": "image", "label": L("Sube tu Foto", "Upload Image"), "required": True}, 
        {"name": "prompt", "type": "textarea", "label": L("Instrucción de Movimiento", "Motion Prompt"), "required": True},
        {"name": "duration", "type": "select", "label": L("Duración", "Duration"), "required": True, "options": [{"value": "4", "label": "4 Segundos"}, {"value": "8", "label": "8 Segundos"}]}
    ]},

    # --- Mejorar Imagen ---
    {"slug": "enhance", "label": L("Escalar Resolución", "Upscale Resolution"), "icon": "fa-expand", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Mejora la calidad general.", "Improves overall quality."), "endpoint": "/v1/images/enhance", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen (máx 1500px)", "Image (max)"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}, {"name": "enhance_faces", "type": "checkbox", "label": L("Mejorar rostros", "Enhance faces"), "default": True}]},
    {"slug": "restore", "label": L("Restaurar Antigua", "Restore Old Photo"), "icon": "fa-clock-rotate-left", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Repara rasguños leves.", "Repairs light scratches."), "endpoint": "/v1/images/restore", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "colorize", "label": L("Colorear B/N", "Colorize B/W"), "icon": "fa-palette", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Da color a fotos antiguas.", "Adds color to old photos."), "endpoint": "/v1/images/colorize", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    # --- Generación Z-Image & Edición de Belleza ---
    {"slug": "edit-image", "label": L("Edición Mágica (Texto)", "Magic Edit (Text)"), "icon": "fa-wand-sparkles", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Edita usando órdenes.", "Edit using text prompts."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Instrucción", "Prompt"), "required": True}, {"name": "mode", "type": "select", "label": L("Modo", "Mode"), "required": True, "options": [{"value": "editing", "label": L("General", "General")}, {"value": "inpaint", "label": L("Inpaint", "Inpaint")}]}, {"name": "input_mask", "type": "mask", "label": L("Máscara", "Mask"), "required": False}]},
    {"slug": "textile-styles", "label": L("Texturas Mágicas 3D", "3D Magic Textures"), "icon": "fa-cubes", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Aplica lana, hilo o estilo inflado 3D.", "Applies yarn, thread or puffy textures."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [
        {"name": "input_image", "type": "image", "label": L("Sube tu Diseño Original", "Upload Design"), "required": True}, 
        {"name": "prompt", "type": "select", "label": L("Elige la Textura", "Select Texture"), "required": True, "options": [
            {"value": "Apply 3D amigurumi crochet texture to the entire image. Strictly preserve the exact original background, all elements, composition, original colors, and transparent areas. Do not remove anything, do not add frames, hoops or white backgrounds. Only change the material of existing elements to knitted yarn.", "label": L("🧶 Crochet / Amigurumi (Lana)", "Crochet / Amigurumi")},
            {"value": "Apply highly detailed realistic embroidery texture to the entire image. Strictly preserve the exact original background, all elements, composition, original colors, and transparent areas. Do not remove anything, do not add frames, hoops or white backgrounds. Only change the material of existing elements to thick colorful threads and 3D stitches.", "label": L("🧵 Bordado Realista (Hilos 3D)", "Realistic Embroidery")},
            {"value": "Apply 3D inflated balloon puffy texture ONLY to the main subjects. Make them look like soft, puffy, glossy plastic or vinyl. STRICTLY PRESERVE the exact original background (including textured paper, colors, and transparent areas). DO NOT turn the background white. DO NOT remove anything.", "label": L("🎈 Estilo Inflado 3D (Globo/Puffer)", "3D Inflated/Puffer")}
        ]}
    ]}
]

MODELS_BY_SLUG = {m["slug"]: m for m in MODELS}

def resize_if_needed(file_bytes, slug, original_filename="image.jpg"):
    try:
        max_dim = 1500 if "enhance" in slug else 3000
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
            
        if needs_convert: img = img.convert("RGB")
            
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
    if not model: return jsonify({"error": True, "message": "Herramienta desconocida"}), 404

    try:
        # ==========================================
        # 🎬 MOTOR DE GENERACIÓN DE VIDEO (ASÍNCRONO)
        # ==========================================
        if model.get("response_type") == "video":
            file_obj = list(request.files.values())[0]
            file_bytes = file_obj.read()
            
            # Paso 1: Pedir URL de carga a SnapEdit
            url_upload_endpoint = f"{BASE}{model['endpoint']}/upload"
            r1 = requests.post(url_upload_endpoint, headers=HEADERS)
            if r1.status_code != 200: return jsonify({"error": True, "message": "Fallo al iniciar el servidor de video."}), 400
            
            datos_carga = r1.json()
            task_id = datos_carga["task_id"]
            upload_url = datos_carga["upload_url"]

            # Paso 2: Subir el archivo (Foto o MP4 original)
            r2 = requests.put(upload_url, data=file_bytes)
            if r2.status_code != 200: return jsonify({"error": True, "message": "Fallo al subir el archivo multimedia."}), 400

            # Paso 3: Crear la Tarea
            payload = {"task_id": task_id}
            for key, value in request.form.items():
                if value.lower() == "true": payload[key] = True
                elif value.lower() == "false": payload[key] = False
                elif value.isdigit(): payload[key] = int(value)
                else: payload[key] = value

            r3 = requests.post(BASE + model["endpoint"], headers={"api-key": API_KEY, "Content-Type": "application/json"}, json=payload)
            if r3.status_code != 200: return jsonify({"error": True, "message": f"Fallo al procesar el renderizado: {r3.text}"}), 400

            # Paso 4: Esperar (Polling) hasta que termine
            max_intentos = 45 # Esperará hasta 3.5 minutos
            for _ in range(max_intentos):
                time.sleep(5)
                r4 = requests.get(f"{BASE}{model['endpoint']}/tasks/{task_id}", headers=HEADERS)
                if r4.status_code == 200:
                    status_data = r4.json()
                    estado = status_data.get("status")
                    
                    if estado == "COMPLETED":
                        video_url = status_data.get("download_url")
                        # 🚀 Devolvemos un JSON especial para que el navegador sepa que es un video
                        return jsonify({"is_video": True, "url": video_url})
                    
                    elif estado == "FAILED":
                        return jsonify({"error": True, "message": status_data.get("error_msg", "Error renderizando video.")}), 400
            
            return jsonify({"error": True, "message": "Tiempo de espera agotado. El video está tardando demasiado en renderizarse."}), 400

        # ==========================================
        # 🖼️ MOTOR DE IMÁGENES NORMAL (SÍNCRONO)
        # ==========================================
        else:
            files, data = {}, {}
            for key, file_obj in request.files.items():
                if file_obj and file_obj.filename:
                    buf, fname, mime = resize_if_needed(file_obj.read(), slug, file_obj.filename)
                    ext = "png" if "png" in mime else "jpg"
                    files[key] = (f"imagen.{ext}", buf, mime)

            for key, value in request.form.items():
                if value: data[key] = value

            if slug == "textile-styles": data["mode"] = "editing"

            response = requests.post(BASE + model["endpoint"], headers=HEADERS, files=files if files else None, data=data if data else None, timeout=300)
            
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                datos = response.json()
                if response.status_code == 200:
                    url_img = None
                    if "data" in datos and isinstance(datos["data"], list) and len(datos["data"]) > 0: url_img = datos["data"][0].get("url")
                    elif "data" in datos and isinstance(datos["data"], dict): url_img = datos["data"].get("url")
                    elif "url" in datos: url_img = datos["url"]

                    if url_img:
                        r_img = requests.get(url_img, timeout=60)
                        img_obj = Image.open(io.BytesIO(r_img.content))
                        buf = io.BytesIO()
                        img_obj.save(buf, format="PNG", dpi=(300, 300))
                        return Response(buf.getvalue(), mimetype="image/png")
                    else:
                        return jsonify(datos), 200
                else:
                    return jsonify({"error": True, "message": datos.get("message", "Error en IA")}), 400
            else:
                if response.status_code != 200: return jsonify({"error": True, "message": "Servidores IA saturados."}), 400
                img_obj = Image.open(io.BytesIO(response.content))
                buf = io.BytesIO()
                img_obj.save(buf, format="PNG", dpi=(300, 300))
                return Response(buf.getvalue(), mimetype="image/png")

    except Exception as e: 
        print(f"❌ ERROR: {str(e)}")
        return jsonify({"error": True, "message": f"Error interno: {str(e)}"}), 400
    finally:
        gc.collect()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
