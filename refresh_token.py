#!/usr/bin/env python3
"""Gmail OAuth token refresh script. Run this, open the URL in browser, authorize."""
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import Flow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
PORT = 8855
REDIRECT_URI = f'http://localhost:{PORT}'

flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES, redirect_uri=REDIRECT_URI)
auth_url, state = flow.authorization_url(access_type='offline', prompt='consent')

print(f"\n{'='*60}")
print("Open this URL in your browser:")
print(f"\n{auth_url}\n")
print(f"{'='*60}")
print(f"Waiting for callback on port {PORT}...")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if 'code' in query:
            code = query['code'][0]
            try:
                flow.fetch_token(code=code)
                creds = flow.credentials
                with open('token.json', 'w') as f:
                    f.write(creds.to_json())
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<h1>Success! Token saved. You can close this window.</h1>')
                print("\nSUCCESS - token.json saved!")
                # Shutdown after success
                import threading
                threading.Thread(target=self.server.shutdown).start()
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f'<h1>Error: {e}</h1>'.encode())
                print(f"ERROR: {e}")
        else:
            self.send_response(302)
            self.send_header('Location', auth_url)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs

server = HTTPServer(('', PORT), Handler)
server.serve_forever()
