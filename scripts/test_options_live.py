import requests

resp = requests.post('http://localhost:5050/api/chat', json={
    'message': 'What is the Call Wall and Put Wall for Nifty?'
})
data = resp.json()
print('Model:', data.get('model_used'))
print('--- OPTIONS MICROSTRUCTURE REPLY ---')
print(data.get('reply'))
