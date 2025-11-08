
# Historical PSI

```python 
import requests
          
dataset_id = "d_b4cf557f8750260d229c49fd768e11ed"
url = "https://data.gov.sg/api/action/datastore_search?resource_id="  + dataset_id
        
response = requests.get(url)
print(response.json())
```

# Current PSI

https://data.gov.sg/datasets/d_fe37906a0182569d891506e815e819b7/view

```bash
curl https://api-open.data.gov.sg/v2/real-time/api/psi \
  --header 'X-Api-Key: YOUR_SECRET_TOKEN'
```