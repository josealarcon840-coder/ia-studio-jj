import os, io, time, hmac, hashlib, requests
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file, redirect
from flask_cors import CORS
from PIL import Image, ImageOps, ImageEnhance
from urllib.parse import quote

app = Flask(__name__)
CORS(app)

TELEGRAM_BOT_TOKEN = "8812898715:AAHSgtmxCjQ8yRTANb85EuluZgw9Dz3x1Fw"
TELEGRAM_CHAT_ID = "-1002330690954"
SNAPEDIT_API_KEY = os.environ.get("SNAPEDIT_API_KEY", "")

@app.route("/")
def index():
    html = render_template("index.html")
    if request.args.get("tg_login") == "ok":
        nombre = request.args.get("name", "VIP")
        script_acceso = f"""
        <script>
            sessionStorage.setItem("jj_session_perm", "active");
            sessionStorage.setItem("jj_user_name", {jsonify(nombre).get_data(as_text=True)});
            window.history.replaceState({{}}, document.title, "/");
        </script>
        """
        html = html.replace("<head>", "<head>" + script_acceso, 1)
    elif request.args.get("tg_error"):
        err_msg = request.args.get("tg_error")
        script_err = f"""
        <script>
            window.addEventListener("DOMContentLoaded", function() {{
                var ge = document.getElementById("gateError");
                if (ge) {{ ge.textContent = {jsonify(err_msg).get_data(as_text=True)}; ge.classList.add("show"); }}
                window.history.replaceState({{}}, document.title, "/");
            }});
        </script>
        """
        html = html.replace("<head>", "<head>" + script_err, 1)
    resp = app.make_response(html)
    resp.headers['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
    return resp

@app.route("/verify-telegram", methods=["POST"])
def verify_telegram():
    data = request.json
    if not data or 'hash' not in data:
        return jsonify({"access": False, "message": "Datos inválidos"}), 400
    data_check_arr = [f'{k}={v}' for k, v in data.items() if k != 'hash']
    data_check_string = '\n'.join(sorted(data_check_arr))
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode('utf-8')).digest()
    hash_calc = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
    if hash_calc != data['hash']:
        return jsonify({"access": False, "message": "Firma no válida"}), 403
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

@app.route("/login-telegram", methods=["GET"])
def login_telegram_redirect():
    data = request.args.to_dict()
    if not data or 'hash' not in data:
        return redirect("/?tg_error=" + quote("Datos de Telegram inválidos"))
    hash_recibido = data.pop('hash')
    data_check_arr = [f'{k}={v}' for k, v in data.items()]
    data_check_string = '\n'.join(sorted(data_check_arr))
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode('utf-8')).digest()
    hash_calc = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
    if hash_calc != hash_recibido:
        return redirect("/?tg_error=" + quote("Firma no válida"))
    user_id = data.get('id')
    first_name = data.get('first_name', 'Usuario')
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember"
    try:
        resp = requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "user_id": user_id}, timeout=10).json()
        if resp.get('ok') and resp['result']['status'] in ['member', 'administrator', 'creator']:
            return redirect(f"/?tg_login=ok&name={quote(first_name)}")
        return redirect("/?tg_error=" + quote("No eres miembro del grupo VIP."))
    except Exception:
        return redirect("/?tg_error=" + quote("Error verificando grupo VIP."))

@app.route("/procesar-semitonos", methods=["POST"])
def procesar_semitonos():
    try:
        if "imagen" not in request.files:
            return jsonify({"error": "No se envió imagen"}), 400
        file = request.files["imagen"]
        lpi = float(request.form.get("lpi", 35))
        angle = float(request.form.get("angle", 45))
        contrast = float(request.form.get("contrast", 1.2))
        shirt_color = request.form.get("shirt_color", "black")

        img = Image.open(file.stream).convert("RGBA")
        w, h = img.size
        r, g, b, a = img.split()

        gray = ImageOps.grayscale(img)
        if contrast != 1.0:
            gray = ImageEnhance.Contrast(gray).enhance(contrast)

        arr_gray = np.array(gray, dtype=np.float32) / 255.0
        arr_a = np.array(a, dtype=np.float32) / 255.0

        # Generación de malla de puntos (semitono)
        dpi = 300.0
        period = max(4.0, dpi / max(10.0, lpi))
        theta = np.radians(angle)
        y_idx, x_idx = np.indices((h, w), dtype=np.float32)
        x_rot = x_idx * np.cos(theta) - y_idx * np.sin(theta)
        y_rot = x_idx * np.sin(theta) + y_idx * np.cos(theta)

        screen = (np.cos(2 * np.pi * x_rot / period) + np.cos(2 * np.pi * y_rot / period)) / 4.0 + 0.5

        if shirt_color == "black":
            intensity = arr_gray * arr_a
        else:
            intensity = (1.0 - arr_gray) * arr_a

        mask = (intensity > screen).astype(np.uint8) * 255
        final_a = np.where(arr_a > 0.05, mask, 0).astype(np.uint8)

        out_rgba = np.dstack((np.array(r), np.array(g), np.array(b), final_a))
        out_img = Image.fromarray(out_rgba, "RGBA")

        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
    
