# Credits: https://github.com/bntan/tesla-tokens
# Added access_token and refresh_token code

import os
import base64
import hashlib
import requests
import webbrowser

# Generate parameters

code_verifier = base64.urlsafe_b64encode(os.urandom(86)).rstrip(b"=")
code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier).digest()).rstrip(b"=").decode("utf-8")
state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("utf-8")

headers = {
    "User-Agent": "",
    "x-tesla-user-agent": "",
    "X-Requested-With": "com.teslamotors.tesla",
}

# Open a session

session = requests.Session()

# GET https://auth.tesla.com/oauth2/v3/authorize

print("***** Open the link below in a browser and authenticate with your TESLA credentials as always *****")
print("")
print("https://auth.tesla.com/oauth2/v3/authorize?audience=https%3A%2F%2Fownership.tesla.com%2F&client_id=ownerapi&code_challenge=" + str(code_challenge) + "&code_challenge_method=S256&locale=en-US&prompt=login&redirect_uri=https%3A%2F%2Fauth.tesla.com%2Fvoid%2Fcallback&response_type=code&scope=openid+email+offline_access&state=" + str(state))
webbrowser.open("https://auth.tesla.com/oauth2/v3/authorize?audience=https%3A%2F%2Fownership.tesla.com%2F&client_id=ownerapi&code_challenge=" + str(code_challenge) + "&code_challenge_method=S256&locale=en-US&prompt=login&redirect_uri=https%3A%2F%2Fauth.tesla.com%2Fvoid%2Fcallback&response_type=code&scope=openid+email+offline_access&state=" + str(state))

print("")
print("***** Press F12 to activate dev mode and go to Network tab to capture traffic before hitting submit button *****")

print("")
print("***** Once authenticated, you are redirected to an URL which looks like https://auth.tesla.com/void/callback?code={code}&state={state}&issuer={issuer} *****")

print("")
print("***** Grab the {code} in the URL and paste it below  *****")
code = input("Code: ")

# POST https://auth.tesla.com/oauth2/v3/token

data = {
    "grant_type": "authorization_code",
    "client_id": "ownerapi",
    "code_verifier": code_verifier.decode("utf-8"),
    "code": code,
    "redirect_uri": "https://auth.tesla.com/void/callback",
}

response = session.post("https://auth.tesla.com/oauth2/v3/token", headers=headers, json=data)
response.raise_for_status()
print(response.text)

payload = {
    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    'client_id': '81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384',
    'client_secret': 'c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3'
}
newheaders = { "Authorization": f"Bearer {response.json()['access_token']}" }
response = requests.post(url="https://owner-api.teslamotors.com/oauth/token", headers=newheaders, json=payload)
response.raise_for_status()
print(response.text)
