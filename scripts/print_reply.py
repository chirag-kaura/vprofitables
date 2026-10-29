import requests

resp = requests.post('http://localhost:5050/api/chat', json={
    'message': 'Help me with what all investments i already have in my portfolio'
})
data = resp.json()
print('Model:', data.get('model_used'))
print('--- REPLY ---')
print(data.get('reply'))
