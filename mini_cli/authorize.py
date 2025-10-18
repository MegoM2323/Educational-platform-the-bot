import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs
import requests

from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPES

AUTH_URL = "https://yoomoney.ru/oauth/authorize"
TOKEN_URL = "https://yoomoney.ru/oauth/token"
TOKEN_FILE = ".yoomoney_token.json"


def save_token(data: dict):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_token():
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def build_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }
    r = requests.post(TOKEN_URL, data=data, timeout=20)
    r.raise_for_status()
    return r.json()


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # parse ?code=... из запроса
        q = parse_qs(urlparse(self.path).query)
        code = q.get("code", [None])[0]
        try:
            if not code:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing ?code in callback.")
                return

            token_payload = exchange_code_for_token(code)
            save_token(token_payload)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"YooMoney authorized. You can close this tab.")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())

    # отключаем шум в консоли
    def log_message(self, format, *args):
        return


def run_local_server():
    parsed = urlparse(REDIRECT_URI)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8765
    server = HTTPServer((host, port), CallbackHandler)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    return server


def authorize_once():
    url = build_auth_url()
    server = run_local_server()
    print("Откроется окно авторизации YooMoney…")
    print("Если не открылось — перейди вручную:\n", url)
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass

    input("После подтверждения в браузере нажми Enter здесь…\n")
    server.shutdown()

    token = load_token()
    if not token or "access_token" not in token:
        raise SystemExit("Токен не получен. Проверь CLIENT_ID/SECRET/REDIRECT_URI/SCOPES.")

    at = token["access_token"]
    preview = at[:6] + "..." if len(at) > 6 else at
    print("OK, access_token сохранён в", TOKEN_FILE)
    print("Предпросмотр токена:", preview)


def get_access_token() -> str:
    """Вызывай в своих скриптах. Если токена нет — запускает авторизацию."""
    token = load_token()
    if token and "access_token" in token:
        return token["access_token"]
    authorize_once()
    token = load_token()
    return token["access_token"]


if __name__ == "__main__":
    # Первый запуск: получаем и сохраняем токен.
    authorize_once()

    # Дальше можно просто:
    # from authorize import get_access_token
    # token = get_access_token()
