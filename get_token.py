import requests

url = "https://api.sandbox.freeagent.com/v2/token_endpoint"
payload = {
    "grant_type": "authorization_code",
    "code": "1Mr_VRSj1NKtGVywd2F5YC4uf0pJDPn2WDoB0ASYS",
    "redirect_uri": "http://localhost:8080/callback",
    "client_id": "FREEAGENT_CLIENT_ID",
    "client_secret": "FREEAGENT_CLIENT_SECRET",
}

response = requests.post(url, data=payload, headers={"Accept": "application/json"})
print(response.json())