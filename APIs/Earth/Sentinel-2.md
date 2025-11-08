# Copernicus Data Space Ecosystem - Sentinel-2 API

**Documentation:** https://docs.sentinel-hub.com/api/latest/reference/#tag/process/operation/process

**OAuth Credentials:**
- Client ID: `sh-92c0921d-b2d3-4e77-8729-1b003b9b42be`
- Client Secret: `rjUbMsxHMHPYq93Xs5kU76jPpAdfYFvD`

## Complete Working Example

```python
import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

# Step 1: Get Access Token
client_id = 'sh-92c0921d-b2d3-4e77-8729-1b003b9b42be'
client_secret = 'rjUbMsxHMHPYq93Xs5kU76jPpAdfYFvD'

# Create OAuth session
client = BackendApplicationClient(client_id=client_id)
oauth = OAuth2Session(client=client)

# Fetch token from Copernicus Data Space Ecosystem
token = oauth.fetch_token(
    token_url='https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
    client_secret=client_secret,
    include_client_id=True
)

access_token = token['access_token']
print(f"✓ Access token obtained: {access_token[:50]}...")

# Step 2: Request Sentinel-2 Imagery
response = requests.post(
    'https://services.sentinel-hub.com/api/v1/process',
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    },
    json={
        "input": {
            "bounds": {
                "bbox": [
                    13.822174072265625,
                    45.85080395917834,
                    14.55963134765625,
                    46.29191774991382
                ]
            },
            "data": [{
                "type": "sentinel-2-l2a"
            }]
        },
        "output": {
            "width": 512,
            "height": 512,
            "responses": [{
                "identifier": "default",
                "format": {"type": "image/png"}
            }]
        },
        "evalscript": """
        //VERSION=3

        function setup() {
          return {
            input: ["B02", "B03", "B04"],
            output: {
              bands: 3,
              sampleType: "AUTO"
            }
          };
        }

        function evaluatePixel(sample) {
          return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
        }
        """
    }
)

# Step 3: Save the Image
if response.status_code == 200:
    with open('sentinel2_image.png', 'wb') as f:
        f.write(response.content)
    print("✓ Image saved as 'sentinel2_image.png'")
else:
    print(f"✗ Error: {response.status_code}")
    print(response.text)
```

## Alternative: Simple Token Request (using requests only)

```python
import requests

# Get access token
token_response = requests.post(
    'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
    data={
        'grant_type': 'client_credentials',
        'client_id': 'sh-92c0921d-b2d3-4e77-8729-1b003b9b42be',
        'client_secret': 'rjUbMsxHMHPYq93Xs5kU76jPpAdfYFvD'
    },
    headers={'Content-Type': 'application/x-www-form-urlencoded'}
)

access_token = token_response.json()['access_token']
print(f"Access Token: {access_token}")
```