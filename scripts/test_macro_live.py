import requests

resp = requests.post('http://localhost:5050/api/chat', json={
    'message': 'What happens to my portfolio if Nifty drops 500 points?'
})
data = resp.json()
print('Model:', data.get('model_used'))
print('--- REPLY ---')
print(data.get('reply'))
