import requests

resp = requests.post('http://localhost:5050/api/chat/execute_order', json={
    'symbol': 'TARIL',
    'shares': 5,
    'entry_price': 303.90,
    'stop_loss': 288.70,
    'target1': 340.00
})
print('HTTP Status:', resp.status_code)
print('Response JSON:', resp.json())
