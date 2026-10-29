import requests

resp = requests.post('http://localhost:5050/api/chat', json={
    'message': 'I am looking to make a new investment of 50000 Help me understand How Should I Distribute it to make better profits'
})
data = resp.json()
print('Model:', data.get('model_used'))
print('--- CAPITAL ALLOCATION REPLY ---')
print(data.get('reply'))
