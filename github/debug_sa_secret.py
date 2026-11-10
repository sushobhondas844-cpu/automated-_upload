"""
Diagnostic helper to print the top keys of GOOGLE_SERVICE_ACCOUNT_JSON without exposing private keys.
"""
import os
import json
import base64

sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
print("Length of GOOGLE_SERVICE_ACCOUNT_JSON:", len(sa_json))

try:
    if sa_json.strip().startswith("{"):
        d = json.loads(sa_json)
    else:
        d = json.loads(base64.b64decode(sa_json).decode('utf-8'))
    print("Detected JSON Keys:", list(d.keys()))
    if "type" in d:
        print("Type field:", d.get("type"))
    if "client_email" in d:
        print("Client Email:", d.get("client_email"))
    else:
        print("MISSING 'client_email'! Keys found:", list(d.keys()))
except Exception as e:
    print("Error parsing JSON:", e)
    print("Preview of start:", repr(sa_json[:40]))
