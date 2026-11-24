"""Interactive file-storage client with Cognito authorization-code flow and PKCE."""
import argparse
import base64
import hashlib
import json
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

CALLBACK = "http://localhost:8765/callback"


def login(domain, client):
    verifier = secrets.token_urlsafe(48)
    state = secrets.token_urlsafe(24)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            params = parse_qs(url.query)
            code = params.get("code", [None])[0]
            valid = url.path == "/callback" and params.get("state") == [state] and code
            self.send_response(200 if valid else 400)
            self.end_headers()
            self.wfile.write(b"Sign-in complete. Return to the terminal." if valid else b"Invalid sign-in callback.")
            if valid:
                result["code"] = code

        def log_message(self, *_):
            pass

    query = urlencode({"client_id": client, "response_type": "code", "scope": "openid",
                       "redirect_uri": CALLBACK, "state": state, "code_challenge": challenge,
                       "code_challenge_method": "S256"})
    with HTTPServer(("localhost", 8765), Callback) as server:
        server.timeout = 1
        print("Complete sign-in in your browser. Press Ctrl-C to cancel.")
        webbrowser.open(f"{domain}/oauth2/authorize?{query}")
        while "code" not in result:
            server.handle_request()
    fields = urlencode({"grant_type": "authorization_code", "client_id": client,
                        "code": result["code"], "redirect_uri": CALLBACK,
                        "code_verifier": verifier}).encode()
    with urlopen(Request(f"{domain}/oauth2/token", data=fields), timeout=20) as response:
        return json.load(response)["id_token"]


def upload(form, path):
    if not 1 <= path.stat().st_size <= 10 * 1024 * 1024:
        raise ValueError("Choose a file from 1 byte to 10 MiB.")
    boundary = secrets.token_hex(24)
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        for key, value in form["fields"].items()
    ]
    parts.extend([
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="upload"\r\n'
        'Content-Type: application/octet-stream\r\n\r\n'.encode(),
        path.read_bytes(), f"\r\n--{boundary}--\r\n".encode(),
    ])
    request = Request(form["url"], data=b"".join(parts),
                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urlopen(request, timeout=60):
        print("Uploaded.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint")
    parser.add_argument("login_domain")
    parser.add_argument("client_id")
    args = parser.parse_args()
    token = login(args.login_domain, args.client_id)
    print("Commands: list [cursor], upload <path>, versions <name>, download <name> [|version], share <name> [|version], quit")
    while True:
        try:
            action, _, value = input("> ").strip().partition(" ")
            if action == "quit":
                return
            if action not in {"list", "upload", "versions", "download", "share"}:
                continue
            params = {"action": action}
            if action == "list":
                if value:
                    params["cursor"] = value
            elif action == "upload":
                path = Path(value).expanduser()
                params["name"] = path.name
            else:
                name, _, version = value.partition("|")
                params["name"] = name.strip()
                if version.strip():
                    params["version"] = version.strip()
            request = Request(f"{args.endpoint}?{urlencode(params)}",
                              headers={"Authorization": f"Bearer {token}"})
            with urlopen(request, timeout=20) as response:
                result = json.load(response)
            if action == "upload":
                upload(result, path)
            elif action == "download":
                webbrowser.open(result["url"])
            else:
                print(json.dumps(result, indent=2))
        except EOFError:
            return
        except (OSError, ValueError) as error:
            print(f"Request failed: {error}")


if __name__ == "__main__":
    main()
