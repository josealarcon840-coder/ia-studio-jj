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
HEADERS = {"api-key": API_KEY, "Authorization": f"Bearer {API_KEY}"}
ALLOWED_STYLE_DOMAINS = ("storage.googleapis.com",)

TELEGRAM_BOT_TOKEN = "8812898715:AAHSgtmxCjQ8yRTANb85EuluZgw9Dz3x1Fw" 
TELEGRAM_CHAT_ID = "-1002330690954"

def L(es, en): return {"es": es, "en": en}

MODELS = [
    {"slug": "detect-objects", "label": L("Borrador Mágico (Auto)", "Magic Eraser (Auto)"), "icon": "fa-magic", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Encuentra objetos para borrarlos con un clic.", "Finds objects to erase them with a click."), "endpoint": "/v1/images/detect-objects", "response_type": "json", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen Base", "Base Image"), "required": True}, {"name": "lang", "type": "select", "label": L("Idioma", "Language"), "options": [{"value": "es", "label": L("Español", "Spanish")}]}, {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "super", "label": L("Super", "Super")}, {"value": "normal", "label": L("Normal", "Normal")}]}]},
    {"slug": "detect-text", "label": L("Borrar Texto (Auto)", "Erase Text (Auto)"), "icon": "fa-font", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Detecta y borra los textos automáticamente.", "Detects and erases text automatically."), "endpoint": "/v1/images/detect-text", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "detect-wires", "label": L("Borrar Cables (Auto)", "Erase Wires (Auto)"), "icon": "fa-plug", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Detecta y borra cables/postes.", "Detects and erases wires."), "endpoint": "/v1/images/detect-wires", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-logo", "label": L("Quitar Marcas de Agua (Auto)", "Remove Watermarks"), "icon": "fa-copyright", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Detecta y elimina logos y marcas de protección en un clic.", "Auto remove logos and watermarks."), "endpoint": "/v1/images/remove-logo", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "remove-background", "label": L("Quitar Fondo (Fotos)", "Remove Background"), "icon": "fa-user-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Recorte de personas o productos.", "Cutout for people/products."), "endpoint": "/v1/images/remove-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-background-graphic", "label": L("Quitar Fondo (Arte)", "Remove BG (Graphics)"), "icon": "fa-shapes", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Ideal para anime, stickers y logos.", "Ideal for anime, stickers and logos."), "endpoint": "/v1/images/remove-background-graphic", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-objects", "label": L("Borrar Objetos (Pincel)", "Remove Objects (Brush)"), "icon": "fa-eraser", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Usa el pincel para borrar lo que quieras.", "Use the brush to erase anything."), "endpoint": "/v1/images/remove-objects", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "input_mask", "type": "mask", "label": L("Máscara (B/N)", "Mask (B/W)"), "required": True}, {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "normal", "label": L("Normal", "Normal")}]}]},
    {"slug": "remove-reflection", "label": L("Quitar Reflejos", "Remove Reflections"), "icon": "fa-camera", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Suaviza reflejos en vidrios.", "Softens reflections on glass."), "endpoint": "/v1/images/remove-reflection", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "clean-mirror", "label": L("Limpiar Espejo", "Clean Mirror"), "icon": "fa-broom", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Quita destellos de espejos.", "Removes flash glare from mirrors."), "endpoint": "/v1/images/clean-mirror", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "enhance", "label": L("Escalar Resolución", "Upscale Resolution"), "icon": "fa-expand", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Mejora la calidad general.", "Improves overall quality."), "endpoint": "/v1/images/enhance", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen (máx 1500px)", "Image (max)"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}, {"name": "enhance_faces", "type": "checkbox", "label": L("Mejorar rostros", "Enhance faces"), "default": True}]},
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
            {"value": "PROMPT: Keep the exact same original shape, face, clothes and layout. Transform the photo into a 3D Pixar Disney style animated character.", "label": "🧸 Animado 3D"},
            {"value": "PROMPT: Keep the exact same original shape, face, clothes and layout. Transform the photo into a funny 2D cartoon caricature.", "label": "🤪 Caricatura"},
            {"value": "PROMPT: Keep the exact same original shape, face, clothes and layout. Transform the photo into a classic 2D Cartoon network style.", "label": "📺 Cartoons"},
            {"value": "PROMPT: Keep the exact same original shape, face, clothes and layout. Transform the photo into a cute kawaii anime Chibi style character.", "label": "👶 Chibi Anime"},
            {"value": "PROMPT: Keep the exact same original shape, face, clothes and layout. Transform the photo into a beautiful comic book illustration drawing.", "label": "🎨 Dibujo / Ilustración"}
        ]}
    ]},

    {"slug": "generate-background", "label": L("Generar Fondo Nuevo", "Generate Background"), "icon": "fa-image", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Fondo para productos. ¡Sube un PNG SIN FONDO!", "Background for products."), "endpoint": "/v1/images/generates-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen (Transparente)", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Descripción del fondo", "Background prompt"), "required": True}]},
    
    {"slug": "sticker", "label": L("Crear Sticker", "Create Sticker"), "icon": "fa-note-sticky", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Haz un sticker de tu foto con borde blanco al instante.", "Make a sticker from photo."), "endpoint": "/v1/images/generates/sticker", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    {"slug": "master-color", "label": L("🎨 Master Color", "🎨 Master Color"), "icon": "fa-fill-drip", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Sustituye colores seleccionando por gotero y zona.", "Change colors by selecting zone and eyedropper."), "endpoint": "/local/canvas", "response_type": "image", "fields": [
        {"name": "input_image", "type": "image", "label": L("Sube tu Diseño", "Upload Design"), "required": True}
    ]},

    {"slug": "edit-multi", "label": L("Fusión IA (Múltiple)", "AI Fusion (Multi)"), "icon": "fa-object-group", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Edita hasta 3 imágenes juntas (Ej: Pon a la persona de la Imagen 2 en la 1).", "Edit using up to 3 images."), "endpoint": "/v1/images/edits/multi", "response_type": "image", "fields": [
        {"name": "input_image_0", "type": "image", "label": L("Imagen Base 1", "Base Image 1"), "required": True},
        {"name": "input_image_1", "type": "image", "label": L("Imagen Extra 2 (Opcional)", "Extra Image 2 (Optional)"), "required": False},
        {"name": "input_image_2", "type": "image", "label": L("Imagen Extra 3 (Opcional)", "Extra Image 3 (Optional)"), "required": False},
        {"name": "prompt", "type": "textarea", "label": L("Instrucción (Ej: Reemplaza a la chica por la de la imagen 2)", "Prompt"), "required": True}
    ]},

    {"slug": "studio-vignette", "label": L("🌟 Resplandor Mágico", "🌟 Magic Glow"), "icon": "fa-star", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Añade resplandor HD a diseños sin fondo.", "Adds a glow to a transparent design."), "endpoint": "/local/canvas", "response_type": "image", "fields": [
        {"name": "input_image", "type": "image", "label": L("Sube tu Diseño (Sin Fondo)", "Upload Transparent Design"), "required": True}, 
        {"name": "bg_color", "type": "color", "label": L("Elige el Color del Resplandor", "Glow Color"), "default": "#ff0000"},
        {"name": "glow_size", "type": "range", "label": L("Grosor del Resplandor", "Glow Thickness"), "min": 1, "max": 100, "default": 30}
    ]},

    {"slug": "edit-image", "label": L("Edición Mágica (Texto)", "Magic Edit (Text)"), "icon": "fa-wand-sparkles", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Edita usando órdenes.", "Edit using text prompts."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Instrucción", "Prompt"), "required": True}, {"name": "mode", "type": "select", "label": L("Modo", "Mode"), "required": True, "options": [{"value": "editing", "label": L("General", "General")}, {"value": "inpaint", "label": L("Inpaint", "Inpaint")}]}]},
    
    {"slug": "textile-styles", "label": L("Texturas Mágicas 3D", "3D Magic Textures"), "icon": "fa-cubes", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Aplica lana, bordado, parche o inflado.", "Applies yarn, thread, patch or puffy styles."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [
        {"name": "input_image", "type": "image", "label": L("Sube tu Diseño Original", "Upload Design"), "required": True}, 
        {"name": "prompt", "type": "select", "label": L("Elige la Textura", "Select Texture"), "required": True, "options": [
            {"value": "Transform the entire graphic and all its existing shapes and details into a realistic 3D amigurumi crochet style with thick, visible knitted yarn loops. Keep the exact original colors, shapes, and composition. Do not add any new elements, words, or symbols.", "label": L("🧶 Crochet / Amigurumi HD", "HD Crochet")},
            {"value": "Transform the entire graphic and all its existing shapes and details into a realistic 3D embroidery style with thick, glossy thread stitches. Keep the exact original colors, shapes, and composition. Do not add any new elements, words, or symbols.", "label": L("🧵 Bordado Realista HD", "Realistic Embroidery")},
            {"value": "Transform the graphic into a 3D embroidered patch with a tight stitched thread border strictly following the current outer edges. Keep the exact original colors and composition. Do not add any new elements, words, or extra outlines.", "label": L("🏷️ Parche (Sin Fondo - Borde Ajustado)", "Patch Tight Border")},
            {"value": "Transform the graphic into a 3D embroidered patch on a square fabric background with a stitched thread border around the outer square edge. Keep the main subject's exact original colors and shapes. Do not add any new words or symbols.", "label": L("⬛ Parche (Fondo Cuadrado)", "Square Patch")},
            {"value": "Transform the graphic into a 3D embroidered patch on a circular fabric background with a stitched thread border around the outer circle edge. Keep the main subject's exact original colors and shapes. Do not add any new words or symbols.", "label": L("🔴 Parche (Fondo Redondo)", "Round Patch")},
            {"value": "Transform the entire graphic and all its existing shapes into a 3D inflated puffy balloon texture made of glossy soft vinyl. Keep the exact original colors, shapes, and composition. Do not add any new elements, words, or symbols.", "label": L("🎈 Estilo Inflado 3D (Globo)", "3D Inflated/Puffer")}
        ]}
    ]},

    {"slug": "retouch-skin", "label": L("Retoque Facial", "Skin Retouch"), "icon": "fa-face-smile", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Limpia la piel automáticamente.", "Cleans skin automatically."), "endpoint": "/v1/images/retouch-skin", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]}
]

MODELS_BY_SLUG = {m["slug"]: m for m in MODELS}

def resize_if_needed(file_bytes, slug, original_filename="image.jpg"):
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("El archivo enviado está vacío (0 bytes).")
    try:
        max_dim = 1500 if "enhance" in slug else 2400
        img = Image.open(io.BytesIO(file_bytes))
        img_format = (img.format or "PNG").upper()
        width, height = img.size

        needs_resize = (max(width, height) > max_dim)
        needs_convert = (img_format == "JPEG" and img.mode in ("RGBA", "P", "LA")) or (img_format not in ("JPEG", "PNG"))

        if not needs_resize and not needs_convert:
            img.close()
            return file_bytes, original_filename, f"image/{img_format.lower()}"

        if img_format == "JPEG" and needs_resize:
            img.draft("RGB", (max_dim, max_dim))

        if needs_resize:
            filtro = Image.BILINEAR if max(width, height) > 4000 else Image.LANCZOS
            img.thumbnail((max_dim, max_dim), filtro)

        buffer = io.BytesIO()
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
            img.save(buffer, format="PNG", optimize=False)
            out_bytes = buffer.getvalue()
            img.close()
            return out_bytes, "image.png", "image/png"
        else:
            img = img.convert("RGB")
            img.save(buffer, format="JPEG", quality=95)
            out_bytes = buffer.getvalue()
            img.close()
            return out_bytes, "image.jpg", "image/jpeg"
    except Exception as e:
        print(f"⚠️ Aviso en resize_if_needed: {e}")
        return file_bytes, original_filename, "image/png"
    finally:
        gc.collect()

def validate_and_build_response(raw_bytes):
    if not raw_bytes or len(raw_bytes) < 64:
        return None, "El servidor de IA devolvió un archivo vacío (0 bytes)."

    if raw_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return Response(raw_bytes, mimetype="image/png"), None
    elif raw_bytes[:3] == b'\xff\xd8\xff':
        return Response(raw_bytes, mimetype="image/jpeg"), None
    elif raw_bytes[:4] == b'RIFF' and raw_bytes[8:12] == b'WEBP':
        try:
            img = Image.open(io.BytesIO(raw_bytes))
            out = io.BytesIO()
            img.save(out, format="PNG")
            png_bytes = out.getvalue()
            img.close()
            gc.collect()
            return Response(png_bytes, mimetype="image/png"), None
        except Exception:
            return Response(raw_bytes, mimetype="image/webp"), None
    else:
        return None, "La IA devolvió un archivo corrupto o está saturada. Intenta nuevamente."

def download_from_cdn_with_retry(url_img, retries=3):
    for attempt in range(retries):
        try:
            r_img = requests.get(url_img, headers={'User-Agent': 'Mozilla/5.0'}, timeout=45)
            if r_img.status_code == 200 and len(r_img.content) > 100:
                return r_img.content, None
            time.sleep(1)
        except Exception as e:
            if attempt == retries - 1:
                return None, str(e)
            time.sleep(1)
    return None, "El CDN de SnapEdit entregó 0 bytes."

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
    if not url: return jsonify({"error": True, "message": "No URL"}), 400
    raw_bytes, err = download_from_cdn_with_retry(url)
    if err: return jsonify({"error": True, "message": err}), 400
    resp_obj, err_img = validate_and_build_response(raw_bytes)
    if err_img: return jsonify({"error": True, "message": err_img}), 400
    if dl == "1":
        resp_obj.headers["Content-Disposition"] = "attachment; filename=JJ_Studio_Diseno.png"
    return resp_obj

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

@app.route("/check-task", methods=["GET"])
def check_task():
    task_id = request.args.get("task_id")
    endpoint = request.args.get("endpoint")
    if not task_id or not endpoint: return jsonify({"error": True, "message": "Faltan datos de la tarea."})
    try:
        r = requests.get(f"{BASE}{endpoint}/tasks/{task_id}", headers=HEADERS, timeout=15)
        return jsonify(r.json())
    except Exception as e: return jsonify({"error": True, "message": str(e)})

@app.route("/run/<slug>", methods=["POST"])
def run_model(slug):
    model = MODELS_BY_SLUG.get(slug)
    if slug == "execute-magic-erase": model = {"endpoint": "/v1/images/remove-objects", "fields": []}
    if not model: return jsonify({"error": True, "message": "Herramienta desconocida"}), 404

    try:
        target_endpoint = model.get("endpoint")
        files, data = {}, {}
        mime = "image/png"

        for key, file_obj in request.files.items():
            if file_obj and file_obj.filename:
                raw_input = file_obj.read()
                buf, fname, mime = resize_if_needed(raw_input, slug, file_obj.filename)
                ext = "png" if "png" in mime else "jpg"
                files[key] = (f"{key}.{ext}", buf, mime)

        for key, value in request.form.items():
            if value: data[key] = value

        if slug in ["textile-styles", "edit-multi"]: data["mode"] = "editing"
            
        if slug == "generate-background" and ("png" not in mime.lower()):
             return jsonify({"error": True, "message": "¡Debes subir un PNG transparente (sin fondo)! Ve primero a 'Quitar Fondo'."}), 400
             
        if slug == "sticker":
             data["prompt"] = "Die-cut sticker style, thick crisp white border around the subject, isolated on a solid highly contrasting neon green background"

        if slug == "fairy-art":
             style_val = data.pop("hybrid_style", "")
             if style_val.startswith("PROMPT:"):
                 target_endpoint = "/v1/images/edits"
                 data["mode"] = "editing"
                 data["prompt"] = style_val.replace("PROMPT:", "").strip()
             else:
                 target_endpoint = "/v1/images/generates/art"
                 data["style"] = style_val

        if slug in ["detect-text", "detect-wires"]:
            r1 = requests.post(BASE + target_endpoint, headers=HEADERS, files=files, timeout=90)
            if r1.status_code == 200:
                d_json = r1.json()
                if d_json.get("detected") and d_json.get("mask"):
                    mask_b64 = d_json["mask"]
                    if "," in mask_b64: mask_b64 = mask_b64.split(",", 1)[1]
                    mask_b64 = mask_b64.replace('\n', '').replace('\r', '').strip()
                    mask_b64 += "=" * ((4 - len(mask_b64) % 4) % 4)
                    f2 = {"input_image": files.get("input_image") or files.get("image"), "input_mask": ("mask.png", base64.b64decode(mask_b64), "image/png")}
                    ep_remove = "/v1/images/remove-text" if slug == "detect-text" else "/v1/images/remove-wires"
                    response = requests.post(BASE + ep_remove, headers=HEADERS, files=f2, data={"erase_mode": "ultra"}, timeout=180)
                else: return jsonify({"error": True, "message": "No se detectó texto o cables en la imagen."}), 400
            else: response = r1
        else:
            response = None
            for attempt in range(2):
                if model.get("needs_image") is False:
                    payload = {"prompt": data.get("prompt", ""), "aspect_ratio": data.get("aspect_ratio", "1:1")}
                    response = requests.post(BASE + target_endpoint, headers=HEADERS, json=payload, timeout=90)
                    if response.status_code >= 500:
                        multipart_data = {k: (None, str(v)) for k, v in payload.items()}
                        response = requests.post(BASE + target_endpoint, headers=HEADERS, files=multipart_data, timeout=90)
                else:
                    response = requests.post(BASE + target_endpoint, headers=HEADERS, files=files if files else None, data=data if data else None, timeout=180)
                
                if response.status_code not in (502, 503, 504):
                    break
                time.sleep(1.5)
        
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/json" in content_type:
            datos = response.json()
            if response.status_code == 200:
                if model.get("response_type") == "json" or "detected_objects" in datos:
                    return jsonify(datos), 200

                data_field = datos.get("data")
                url_img, b64_img = None, None

                if isinstance(data_field, list) and len(data_field) > 0:
                    url_img = data_field[0].get("url") or data_field[0].get("image_url")
                    b64_img = data_field[0].get("b64_json") or data_field[0].get("image") or data_field[0].get("output_image")
                elif isinstance(data_field, dict):
                    url_img = data_field.get("url") or data_field.get("image_url")
                    b64_img = data_field.get("b64_json") or data_field.get("image") or data_field.get("output_image")

                url_img = url_img or datos.get("url") or datos.get("image_url")
                b64_img = b64_img or datos.get("output_image") or datos.get("image") or datos.get("b64_json")

                if url_img:
                    if url_img.startswith("data:image"):
                        _, encoded = url_img.split(",", 1)
                        raw_bytes = base64.b64decode(encoded)
                    else:
                        raw_bytes, err_dl = download_from_cdn_with_retry(url_img)
                        if err_dl: return jsonify({"error": True, "message": f"Error descargando imagen: {err_dl}"}), 400
                    
                    resp_obj, err_img = validate_and_build_response(raw_bytes)
                    if err_img: return jsonify({"error": True, "message": err_img}), 400
                    return resp_obj

                if b64_img:
                    if "," in b64_img: b64_img = b64_img.split(",", 1)[1]
                    b64_img = b64_img.replace('\n', '').replace('\r', '').strip()
                    b64_img += "=" * ((4 - len(b64_img) % 4) % 4)
                    raw_bytes = base64.b64decode(b64_img)
                    resp_obj, err_img = validate_and_build_response(raw_bytes)
                    if err_img: return jsonify({"error": True, "message": err_img}), 400
                    return resp_obj

                return jsonify(datos), 200
            return jsonify({"error": True, "message": datos.get("message", str(datos))}), 400
        else:
            if response.status_code != 200:
                return jsonify({"error": True, "message": f"Servidores de IA ocupados (HTTP {response.status_code}). Intenta en unos segundos."}), 400
            resp_obj, err_img = validate_and_build_response(response.content)
            if err_img: return jsonify({"error": True, "message": err_img}), 400
            return resp_obj
    except Exception as e: 
        print(f"❌ ERROR: {str(e)}")
        return jsonify({"error": True, "message": f"Error interno: {str(e)}"}), 400
    finally:
        gc.collect()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
