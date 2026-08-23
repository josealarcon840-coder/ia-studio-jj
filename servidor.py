import os
import io
import base64
import requests
from flask import Flask, render_template, request, jsonify, Response
from PIL import Image

# Sin límites de lectura para que no colapse con fotos gigantes (Escaladas a 8x)
Image.MAX_IMAGE_PIXELS = None

app = Flask(__name__)

API_KEY = os.environ.get("SNAPEDIT_API_KEY", "sk-snap-uuh6Z0veQTW7z3DSQ7TUr5yuyaC7HIHAoUchqM_KrfI")
BASE = "https://api.snapedit.app"
HEADERS = {"api-key": API_KEY}
ALLOWED_STYLE_DOMAINS = ("storage.googleapis.com",)

def L(es, en): return {"es": es, "en": en}

MODELS = [
    # --- Detección y Borrado Mágico ---
    {
        "slug": "detect-objects", "label": L("Borrador Mágico (Auto)", "Magic Eraser (Auto)"), "icon": "fa-magic", "category": L("1. Detección Inteligente", "1. Smart Detection"),
        "desc": L("Encuentra objetos para borrarlos con un clic.", "Finds objects to erase them with a click."), "endpoint": "/v1/images/detect-objects", "response_type": "json",
        "fields": [
            {"name": "input_image", "type": "image", "label": L("Imagen Base", "Base Image"), "required": True},
            {"name": "lang", "type": "select", "label": L("Idioma", "Language"), "options": [{"value": "es", "label": L("Español", "Spanish")}]},
            {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "super", "label": L("Super", "Super")}, {"value": "normal", "label": L("Normal", "Normal")}]}
        ]
    },
    {
        "slug": "detect-text", "label": L("Borrar Texto (Auto)", "Erase Text (Auto)"), "icon": "fa-font", "category": L("1. Detección Inteligente", "1. Smart Detection"),
        "desc": L("Detecta y borra los textos de la imagen automáticamente.", "Detects and erases text automatically."), "endpoint": "/v1/images/detect-text", "response_type": "image", 
        "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]
    },
    {
        "slug": "detect-wires", "label": L("Borrar Cables (Auto)", "Erase Wires (Auto)"), "icon": "fa-plug", "category": L("1. Detección Inteligente", "1. Smart Detection"),
        "desc": L("Detecta y borra cables/postes automáticamente.", "Detects and erases wires automatically."), "endpoint": "/v1/images/detect-wires", "response_type": "image", 
        "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]
    },

    # --- Eliminar y Máscaras ---
    {"slug": "remove-background", "label": L("Quitar Fondo (Fotos)", "Remove Background"), "icon": "fa-user-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Recorte de personas o productos.", "Cutout for people/products."), "endpoint": "/v1/images/remove-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "remove-background-graphic", "label": L("Quitar Fondo (Logos/Arte)", "Remove BG (Graphics)"), "icon": "fa-shapes", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Ideal para anime, stickers y logos.", "Ideal for anime, stickers and logos."), "endpoint": "/v1/images/remove-background-graphic", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {
        "slug": "remove-objects", "label": L("Borrar Objetos (Máscara)", "Remove Objects (Mask)"), "icon": "fa-eraser", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Sube tu máscara en blanco y negro.", "Upload a B/W mask to erase."), "endpoint": "/v1/images/remove-objects", "response_type": "image",
        "fields": [
            {"name": "input_image", "type": "image", "label": L("Imagen Original", "Image"), "required": True},
            {"name": "input_mask", "type": "mask", "label": L("Máscara (B/N)", "Mask (B/W)"), "required": True},
            {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "normal", "label": L("Normal", "Normal")}]}
        ]
    },
    {
        "slug": "erase-text", "label": L("Borrar Texto (Máscara)", "Erase Text (Mask)"), "icon": "fa-text-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Borra textos usando tu máscara.", "Erase texts using your mask."), "endpoint": "/v1/images/remove-text", "response_type": "image",
        "fields": [
            {"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True},
            {"name": "input_mask", "type": "mask", "label": L("Máscara", "Mask"), "required": True},
            {"name": "erase_mode", "type": "select", "label": L("Calidad", "Quality"), "options": [{"value": "ultra", "label": L("Ultra HD", "Ultra HD")}, {"value": "normal", "label": L("Normal", "Normal")}]}
        ]
    },
    {"slug": "erase-wires", "label": L("Borrar Cables (Máscara)", "Erase Wires (Mask)"), "icon": "fa-bolt-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Borra cables usando tu máscara.", "Erase wires using your mask."), "endpoint": "/v1/images/remove-wires", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "input_mask", "type": "mask", "label": L("Máscara", "Mask"), "required": True}]},
    {"slug": "remove-reflection", "label": L("Quitar Reflejos", "Remove Reflections"), "icon": "fa-camera", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Suaviza reflejos en vidrios.", "Softens reflections on glass."), "endpoint": "/v1/images/remove-reflection", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "clean-mirror", "label": L("Limpiar Espejo", "Clean Mirror"), "icon": "fa-broom", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Quita destellos de espejos.", "Removes flash glare from mirrors."), "endpoint": "/v1/images/clean-mirror", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    # --- Mejorar ---
    {
        "slug": "enhance", "label": L("Escalar Resolución", "Upscale Resolution"), "icon": "fa-expand", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Mejora la calidad general.", "Improves overall quality."), "endpoint": "/v1/images/enhance", "response_type": "image",
        "fields": [{"name": "input_image", "type": "image", "label": L("Imagen (máx 1500px)", "Image (max 1500px)"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}, {"name": "enhance_faces", "type": "checkbox", "label": L("Mejorar rostros", "Enhance faces"), "default": True}]
    },
    {
        "slug": "enhance-pro", "label": L("Escalar Rostros (Pro)", "Upscale Faces (Pro)"), "icon": "fa-user-check", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Ideal para fotos de personas.", "Ideal for photos of people."), "endpoint": "/v1/images/enhance/pro", "response_type": "image",
        "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}]
    },
    {
        "slug": "enhance-art", "label": L("Escalar Arte / Anime", "Upscale Art / Anime"), "icon": "fa-dragon", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Ideal para dibujos.", "Ideal for drawings."), "endpoint": "/v1/images/enhance-art", "response_type": "image",
        "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True, "resize_max": 1500}, {"name": "zoom_factor", "type": "select", "label": L("Factor", "Factor"), "required": True, "options": [{"value": "2", "label": L("2x", "2x")}, {"value": "4", "label": L("4x", "4x")}, {"value": "8", "label": L("8x (Máximo)", "8x (Max)")}]}]
    },
    {"slug": "restore", "label": L("Restaurar Antigua", "Restore Old Photo"), "icon": "fa-clock-rotate-left", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Repara rasguños leves.", "Repairs light scratches."), "endpoint": "/v1/images/restore", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "restore-pro", "label": L("Restaurar Antigua (Pro)", "Restore Old (Pro)"), "icon": "fa-hammer", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Reparación severa.", "Heavy damage repair."), "endpoint": "/v1/images/restore/pro", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "colorize", "label": L("Colorear B/N", "Colorize B/W"), "icon": "fa-palette", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Da color a fotos antiguas.", "Adds color to old photos."), "endpoint": "/v1/images/colorize", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "colorize-pro", "label": L("Colorear B/N (Pro)", "Colorize B/W (Pro)"), "icon": "fa-paint-roller", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Colorización avanzada.", "Advanced colorization."), "endpoint": "/v1/images/colorize/pro", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "light-restore", "label": L("Corregir Iluminación", "Fix Lighting"), "icon": "fa-sun", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Arregla fotos oscuras.", "Fixes dark photos."), "endpoint": "/v1/images/light-restore", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "backlit-fix", "label": L("Corregir Contraluz", "Fix Backlight"), "icon": "fa-cloud-sun", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Aclara sombras por contraluz.", "Lightens backlit shadows."), "endpoint": "/v1/images/backlit-fix", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "night-flash", "label": L("Flash Nocturno", "Night Flash"), "icon": "fa-moon", "category": L("3. Mejora y Restauración", "3. Enhance & Restore"), "desc": L("Añade flash realista.", "Adds realistic flash."), "endpoint": "/v1/images/night-flash", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},

    # --- Generación ---
    {"slug": "generate-zimage", "label": L("Crear: Z-Image (Texto)", "Create: Z-Image (Text)"), "icon": "fa-rocket", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Crea imagen rápida.", "Create image fast."), "endpoint": "/v1/images/generates/zimage", "response_type": "image", "needs_image": False, "fields": [{"name": "prompt", "type": "textarea", "label": L("Descripción", "Prompt"), "required": True}, {"name": "aspect_ratio", "type": "select", "label": L("Proporción", "Ratio"), "options": [{"value": "1:1", "label": L("1:1", "1:1")}, {"value": "16:9", "label": L("16:9", "16:9")}, {"value": "9:16", "label": L("9:16", "9:16")}]}]},
    {"slug": "generate-qwen", "label": L("Crear: Qwen (Texto)", "Create: Qwen (Text)"), "icon": "fa-brain", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Motor HD realista.", "HD realistic engine."), "endpoint": "/v1/images/generates/qwen", "response_type": "image", "needs_image": False, "fields": [{"name": "prompt", "type": "textarea", "label": L("Descripción", "Prompt"), "required": True}, {"name": "aspect_ratio", "type": "select", "label": L("Proporción", "Ratio"), "options": [{"value": "1:1", "label": L("1:1", "1:1")}, {"value": "16:9", "label": L("16:9", "16:9")}, {"value": "9:16", "label": L("9:16", "9:16")}]}]},
    {"slug": "fairy-art", "label": L("Retrato a Arte", "Portrait to Art"), "icon": "fa-wand-magic-sparkles", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Convierte fotos a Anime/3D.", "Convert photos to Anime/3D."), "endpoint": "/v1/images/generates/art", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "style", "type": "select", "label": L("Estilo", "Style"), "required": True, "options_url": "https://storage.googleapis.com/assets.snapedit.app/fairyai/anime_styles_6mar25.json"}]},
    {"slug": "generate-background", "label": L("Generar Fondo Nuevo", "Generate Background"), "icon": "fa-image", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Fondo para productos.", "Background for products."), "endpoint": "/v1/images/generates-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Descripción del fondo", "Background prompt"), "required": True}]},
    {"slug": "headshot", "label": L("Foto Perfil Profesional", "Professional Headshot"), "icon": "fa-user-tie", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Viste a la persona con IA.", "Dress the person with AI."), "endpoint": "/v1/images/generates/headshot", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Atuendo/Fondo", "Outfit/Background"), "required": True}]},
    {"slug": "sticker", "label": L("Crear Sticker", "Create Sticker"), "icon": "fa-note-sticky", "category": L("4. Inteligencia Artificial", "4. AI Generation"), "desc": L("Haz un sticker de tu foto.", "Make a sticker from photo."), "endpoint": "/v1/images/generates/sticker", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Estilo (Ej: Zombie)", "Style (e.g. Zombie)"), "required": True}]},

    # --- Edición y Belleza ---
    {"slug": "edit-image", "label": L("Edición Mágica (Texto)", "Magic Edit (Text)"), "icon": "fa-wand-sparkles", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Edita usando órdenes.", "Edit using text prompts."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "prompt", "type": "textarea", "label": L("Instrucción", "Prompt"), "required": True}, {"name": "mode", "type": "select", "label": L("Modo", "Mode"), "required": True, "options": [{"value": "editing", "label": L("General", "General")}, {"value": "inpaint", "label": L("Inpaint", "Inpaint")}]}, {"name": "input_mask", "type": "mask", "label": L("Máscara (Solo Inpaint)", "Mask (Inpaint only)"), "required": False}]},
    {"slug": "edit-multi", "label": L("Edición Multi-Imagen", "Multi-Image Edit"), "icon": "fa-layer-group", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Combina hasta 3 fotos.", "Combine up to 3 photos."), "endpoint": "/v1/images/edits/multi", "response_type": "image", "fields": [{"name": "input_image_0", "type": "image", "label": L("Imagen 1", "Image 1"), "required": True}, {"name": "input_image_1", "type": "image", "label": L("Imagen 2", "Image 2")}, {"name": "input_image_2", "type": "image", "label": L("Imagen 3", "Image 3")}, {"name": "prompt", "type": "textarea", "label": L("Instrucción", "Prompt"), "required": True}, {"name": "mode", "type": "select", "label": L("Modo", "Mode"), "options": [{"value": "editing", "label": L("Edición", "Edit")}]}]},
    {"slug": "retouch-skin", "label": L("Retoque Facial", "Skin Retouch"), "icon": "fa-face-smile", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Limpia la piel automáticamente.", "Cleans skin automatically."), "endpoint": "/v1/images/retouch-skin", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "makeup", "label": L("Maquillaje Digital", "Digital Makeup"), "icon": "fa-eye", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Aplica maquillaje a rostros.", "Applies makeup to faces."), "endpoint": "/v1/images/transfer-makeup", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "style", "type": "select", "label": L("Estilo", "Style"), "required": True, "options_url": "https://storage.googleapis.com/assets.snapedit.app/makeup/makeup_v1_1.json"}]},
    {"slug": "hairstyle", "label": L("Cambiar Peinado", "Change Hairstyle"), "icon": "fa-scissors", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Prueba peinados distintos.", "Try different hairstyles."), "endpoint": "/v1/images/hairstyle", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "style", "type": "select", "label": L("Peinado", "Hairstyle"), "required": True, "options_url": "https://storage.googleapis.com/assets.snapedit.app/hairstyle/hair_styles_v3.json"}]},
    {"slug": "virtual-tryon", "label": L("Probador Virtual (Ropa)", "Virtual Try-On"), "icon": "fa-shirt", "category": L("5. Belleza y Edición", "5. Beauty & Edit"), "desc": L("Viste a una persona con IA.", "Dress someone with AI."), "endpoint": "/v1/images/try-on", "response_type": "task", "status_endpoint": "/v1/images/try-on/tasks/{task_id}", "fields": [{"name": "model_image", "type": "image", "label": L("Modelo", "Model"), "required": True}, {"name": "cloth_image", "type": "image", "label": L("Prenda Alta", "Upper Cloth"), "required": True}, {"name": "lower_cloth_image", "type": "image", "label": L("Prenda Baja (Opc)", "Lower Cloth (Opt)")}, {"name": "cloth_type", "type": "select", "label": L("Tipo", "Type"), "required": True, "options": [{"value": "upper", "label": L("Superior", "Upper")}, {"value": "lower", "label": L("Inferior", "Lower")}, {"value": "full", "label": L("Completo", "Full")}]}, {"name": "hd_mode", "type": "select", "label": L("Calidad HD", "HD Quality"), "options": [{"value": "false", "label": L("Normal", "Normal")}, {"value": "true", "label": L("HD (Lento)", "HD (Slow)")}]}]},

    # --- Utilidad ---
    {"slug": "outpaint", "label": L("Expandir Bordes", "Expand Image"), "icon": "fa-crop-simple", "category": L("6. Utilidades", "6. Utilities"), "desc": L("Crea contenido en los bordes.", "Generates content beyond edges."), "endpoint": "/v1/images/outpaint", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}, {"name": "input_mask", "type": "mask", "label": L("Máscara del área", "Mask of area"), "required": True}]},
    {"slug": "pose-suggest", "label": L("Sugerir Poses", "Pose Suggestions"), "icon": "fa-person", "category": L("6. Utilidades", "6. Utilities"), "desc": L("Propone poses nuevas.", "Suggests new poses."), "endpoint": "/v1/images/pose-suggest", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Referencia", "Reference"), "required": True, "resize_max": 512}, {"name": "num_models", "type": "number", "label": L("Cantidad", "Amount"), "required": True, "default": 3}, {"name": "gender", "type": "select", "label": L("Género", "Gender"), "required": True, "options": [{"value": "female", "label": L("Mujer", "Female")}, {"value": "male", "label": L("Hombre", "Male")}]}]}
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

@app.route("/run/<slug>", methods=["POST"])
def run_model(slug):
    model = MODELS_BY_SLUG.get(slug)
    
    if slug == "execute-magic-erase":
        model = {"endpoint": "/v1/images/remove-objects", "fields": []}
    elif slug in ["erase-text", "erase-wires"]:
        model = model.copy()
        model["endpoint"] = "/v1/images/remove-objects"
        
    if not model: return jsonify({"error": True, "message": "Herramienta desconocida"}), 404

    try:
        files, data = {}, {}
        
        def get_resize_max(field_name):
            for f in model.get("fields", []):
                if f.get("name") == field_name: return f.get("resize_max")
            return None

        # 1. Archivos Normales
        for key, file_obj in request.files.items():
            if file_obj and file_obj.filename:
                max_d = get_resize_max(key)
                buf, fname, mime = resize_if_needed(file_obj.read(), slug, file_obj.filename)
                
                api_key = key
                if key == "input_image" and any(x in model["endpoint"] for x in ["generates-background", "pose-suggest", "outpaint"]):
                    api_key = "image"
                files[api_key] = (fname, buf, mime)

        # 2. Enlaces HTTP (Acciones Rápidas)
        for key, value in request.form.items():
            if value:
                if key in ["input_image", "model_image", "input_image_0"] and value.startswith("http"):
                    try:
                        r_img = requests.get(value, timeout=60)
                        if r_img.status_code == 200:
                            max_d = get_resize_max(key)
                            buf, fname, mime = resize_if_needed(r_img.content, slug, "chain.png")
                            
                            api_key = key
                            if key == "input_image" and any(x in model["endpoint"] for x in ["generates-background", "pose-suggest", "outpaint"]):
                                api_key = "image"
                            files[api_key] = (fname, buf, mime)
                        else:
                            return jsonify({"error": True, "message": "No se pudo conectar a SnapEdit para la foto previa."}), 400
                    except Exception as e:
                        return jsonify({"error": True, "message": f"Error encadenando imagen: {str(e)}"}), 400
                else:
                    data[key] = value

        # ---------------------------------------------------------
        # FLUJO DE ENVÍO DE DATOS CORREGIDO PARA GENERACIÓN Y EDICIÓN
        # ---------------------------------------------------------
        if slug in ["detect-text", "detect-wires"]:
            r1 = requests.post(BASE + model["endpoint"], headers=HEADERS, files=files, timeout=120)
            if r1.status_code == 200:
                try:
                    d_json = r1.json()
                    if d_json.get("detected") and d_json.get("mask"):
                        mask_b64 = d_json["mask"]
                        if "," in mask_b64:
                            mask_b64 = mask_b64.split(",", 1)[1]
                        mask_b64 = mask_b64.replace('\n', '').replace('\r', '').strip()
                        mask_b64 += "=" * ((4 - len(mask_b64) % 4) % 4)
                        mask_bytes = base64.b64decode(mask_b64)
                        
                        f2 = {
                            "input_image": files.get("input_image") or files.get("image"),
                            "input_mask": ("mask.png", mask_bytes, "image/png")
                        }
                        
                        ep_remove = "/v1/images/remove-text" if slug == "detect-text" else "/v1/images/remove-wires"
                        
                        response = requests.post(BASE + ep_remove, headers=HEADERS, files=f2, data={"erase_mode": "ultra"}, timeout=300)
                    else:
                        return jsonify({"error": True, "message": "No se detectó texto o cables en la imagen."}), 400
                except Exception as e:
                    return jsonify({"error": True, "message": f"Error del servidor al procesar la máscara: {str(e)}"}), 500
            else:
                response = r1
        else:
            # Envío como JSON si es generación por texto puro (zimage o qwen)
            if model.get("needs_image") is False:
                json_headers = HEADERS.copy()
                json_headers["Content-Type"] = "application/json"
                response = requests.post(BASE + model["endpoint"], headers=json_headers, json=data, timeout=300)
            else:
                response = requests.post(BASE + model["endpoint"], headers=HEADERS, files=files if files else None, data=data if data else None, timeout=300)
        
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type: return jsonify(response.json()), response.status_code
        return Response(response.content, mimetype=content_type), response.status_code

    except Exception as e: 
        return jsonify({"error": True, "message": str(e)}), 500

@app.route("/task-status/<slug>/<task_id>")
def task_status(slug, task_id):
    try: return jsonify(requests.get(f"{BASE}/v1/images/try-on/tasks/{task_id}", headers=HEADERS, timeout=30).json()), 200
    except Exception as e: return jsonify({"error": True, "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
