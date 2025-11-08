import requests

print("Testing Copernicus Data Space Ecosystem authentication...")
print("-" * 60)

token_response = requests.post(
    'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
    data={
        'grant_type': 'client_credentials',
        'client_id': 'sh-92c0921d-b2d3-4e77-8729-1b003b9b42be',
        'client_secret': 'rjUbMsxHMHPYq93Xs5kU76jPpAdfYFvD'
    }
)

print(f"Status Code: {token_response.status_code}")
print()

if token_response.status_code == 200:
    token_data = token_response.json()
    access_token = token_data['access_token']

    print("✓ Authentication successful!")
    print(f"✓ Access Token: {access_token[:50]}...")
    print(f"✓ Token Type: {token_data.get('token_type', 'N/A')}")
    print(f"✓ Expires In: {token_data.get('expires_in', 'N/A')} seconds")
    print()
    print("You can now use this token to make API requests!")
else:
    print(f"✗ Authentication failed!")
    print(f"✗ Error: {token_response.status_code}")
    print(f"✗ Response: {token_response.text}")
