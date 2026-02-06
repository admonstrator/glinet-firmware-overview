import urllib.request
import json

BASE_URL = "https://firmware-api.gl-inet.com/cloud-api/products?modelType="
TYPES = ["ROUTER", "IOT", "KVM"]

def fetch_products(model_type):
    url = BASE_URL + model_type
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'info' in data:
                return data['info']
            return []
    except Exception as e:
        print(f"Error fetching {model_type}: {e}")
        return []

all_models = {}

for t in TYPES:
    products = fetch_products(t)
    print(f"Fetched {len(products)} products for type {t}")
    for p in products:
        code = p.get('code')
        name = p.get('name')
        if code:
            all_models[code] = {
                'name': name,
                'type': t
            }

with open('models.json', 'w', encoding='utf-8') as f:
    json.dump(all_models, f, indent=4)

print(f"Saved {len(all_models)} unique models to models.json")
