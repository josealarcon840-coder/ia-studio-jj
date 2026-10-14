import os
import io
import base64
import requests
import hashlib
import hmac
import gc  
import time 
from flask import Flask, render_template, request, jsonify, Response, send_file
from flask_cors import CORS
from PIL import Image, ImageChops

Image.MAX_IMAGE_PIXELS = None

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("SNAPEDIT_API_KEY", "sk-snap-uuh6Z0veQTW7z3DSQ7TUr5yuyaC7HIHAoUchqM_KrfI")
BASE = "https://api.snapedit.app"
HEADERS = {"api-key": API_KEY, "Authorization": f"Bearer {API_KEY}"}
ALLOWED_STYLE_DOMAINS = ("storage.googleapis.com",)

TELEGRAM_BOT_TOKEN = "8812898715:AAHSgtmxCjQ8yRTANb85EuluZgw9Dz3x1Fw" 
TELEGRAM_CHAT_ID = "-1002330690954"

def L(es, en): return {"es": es, "en": en}

MODELS = [
    {"slug": "detect-objects", "label": L("Borrador Mágico (Auto)", "Magic Eraser (Auto)"), "icon": "fa-magic", "category": L("1. Detección Inteligente", "1. Smart Detection"), "desc": L("Encuentra objetos para borrarlos con un clic.", "Finds objects to erase them with a click."), "endpoint": "/v1/images/detect-objects", "response_type": "json", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen Base", "Base Image"), "required": True}]},
    {"slug": "extract-print", "label": L("👕 Extraer Diseño (Mockup a DTF)", "👕 Extract Shirt Design (DTF)"), "icon": "fa-shirt", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Extrae el estampado y lo escala en Ultra HD.", "Extracts and upscales 4x HD."), "endpoint": "/v1/images/edits", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Foto de la Camiseta", "Shirt Photo"), "required": True}]},
    {"slug": "remove-background", "label": L("Quitar Fondo (Fotos)", "Remove Background"), "icon": "fa-user-slash", "category": L("2. Extraer y Borrar", "2. Extract & Erase"), "desc": L("Recorte de personas o productos.", "Cutout for people/products."), "endpoint": "/v1/images/remove-background", "response_type": "image", "fields": [{"name": "input_image", "type": "image", "label": L("Imagen", "Image"), "required": True}]},
    {"slug": "dtf-semitonos", "label": L("🖨️ DTF Studio (Semitonos)", "🖨️ DTF Halftones"), "icon": "fa-print", "category": L("6. Especiales DTF", "6. DTF Specials"), "desc": L("Genera tramas y semitonos avanzados a 300DPI.", "Generate advanced halftones."), "endpoint": "/dtf-semitonos", "response_type": "page", "fields": []},
    {"slug": "dtf-detector", "label": L("🛡️ Detector Semitransparencias", "🛡️ DTF Detector"), "icon": "fa-shield-halved", "category": L("6. Especiales DTF", "6. DTF Specials"), "desc": L("Encuentra y repara píxeles peligrosos para DTF.", "Find and fix dangerous pixels."), "endpoint": "/dtf-detector", "response_type": "page", "fields": []}
]

MODELS_BY_SLUG = {m["slug"]: m for m in MODELS}

def resize_if_needed(file_bytes, slug, original_filename="image.jpg", zoom_factor="2"):
    return file_bytes, original_filename, "image/png"

def validate_and_build_response(raw_bytes):
    if not raw_bytes or len(raw_bytes) < 64:
        return None, "El servidor devolvió un archivo vacío."
    return Response(raw_bytes, mimetype="image/png"), None

def download_from_cdn_with_retry(url_img, retries=3):
    try:
        r = requests.get(url_img, headers={'User-Agent': 'Mozilla/5.0'}, timeout=45)
        return r.content, None
    except Exception as e:
        return None, str(e)

@app.route("/")
def index(): return render_template("index.html")

@app.route("/models")
def get_models():
    public_fields = ("slug", "label", "icon", "category", "desc", "fields", "response_type", "needs_image")
    return jsonify([{k: m[k] for k in public_fields if k in m} for m in MODELS])

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

@app.route('/api/reparar', methods=['POST'])
def reparar_api():
    try:
        if 'imagen' not in request.files: return "Error", 400
        file = request.files['imagen']
        ancho_cm = float(request.form.get('ancho', 29.7))
        alto_cm = float(request.form.get('alto', 42.0))
        target_w = int((ancho_cm / 2.54) * 300)
        target_h = int((alto_cm / 2.54) * 300)
        ruta_in = f"/tmp/temp_in_{int(time.time())}.png"
        ruta_out = f"/tmp/temp_out_{int(time.time())}.png"
        file.save(ruta_in)
        img = Image.open(ruta_in).convert("RGBA")
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        arr = np.array(img)
        arr[:, :, 3] = np.where(arr[:, :, 3] > 100, 255, 0).astype(np.uint8)
        Image.fromarray(arr, mode="RGBA").save(ruta_out, format="PNG", dpi=(300, 300))
        return send_file(ruta_out, mimetype='image/png')
    except Exception as e:
        return str(e), 500

@app.route('/api/procesar', methods=['POST'])
def procesar_api():
    try:
        if 'imagen' not in request.files: return "Error", 400
        file = request.files['imagen']
        ruta_out = f"/tmp/temp_semi_{int(time.time())}.png"
        file.save(ruta_out)
        return send_file(ruta_out, mimetype='image/png')
    except Exception as e:
        return str(e), 500

@app.route("/run/<slug>", methods=["POST"])
def run_model(slug):
    model = MODELS_BY_SLUG.get(slug)
    if not model: return jsonify({"error": True, "message": "Herramienta desconocida"}), 404
    try:
        files = {}
        for key, file_obj in request.files.items():
            if file_obj and file_obj.filename:
                files[key] = (file_obj.filename, file_obj.read(), "image/png")
        res = requests.post(BASE + model.get("endpoint"), headers=HEADERS, files=files if files else None, data=request.form, timeout=120)
        raw_bytes, err = extract_raw_bytes_from_response(res)
        if err: return jsonify({"error": True, "message": err}), 400
        return validate_and_build_response(raw_bytes)
    except Exception as e:
        return jsonify({"error": True, "message": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
    
