import requests

r = requests.get('http://localhost:5050/api/chat/status')
print('Chat Status HTTP:', r.status_code)
data = r.json()
print('Chat Status OK:', data.get('status') == 'ok', '| RAG Instruments:', data.get('rag_instruments_count'))

r_chat = requests.post('http://localhost:5050/api/chat', json={'message': 'Top gainers today'})
print('Chat Query HTTP:', r_chat.status_code)
c_data = r_chat.json()
print('Chat Model:', c_data.get('model_used'))
print('First line:', c_data.get('reply', '').split('\n')[0])
