with open('scripts/append_chat_js.py', 'r', encoding='utf-8') as f:
    content = f.read()

func_code = '''
  // ── Institutional In-Chat Paper Trade Execution ─────────────────────────────
  window.executePaperTrade = async function(symbol, shares, entryPrice, stopLoss, target1, btnElem) {
    if (!btnElem) return;
    const originalText = btnElem.innerHTML;
    btnElem.disabled = true;
    btnElem.innerHTML = '⏳ Committing Order to Risk Engine...';

    try {
      const resp = await fetch('/api/chat/execute_order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol,
          shares: shares,
          entry_price: entryPrice,
          stop_loss: stopLoss,
          target1: target1,
          order_type: 'BUY'
        })
      });
      const data = await resp.json();
      if (data && data.status === 'success') {
        btnElem.innerHTML = `✅ Order Filled (#${data.order_id || 'OPEN'}) · Active in Portfolio`;
        btnElem.style.background = '#059669';
        btnElem.style.cursor = 'default';
        btnElem.disabled = true;
      } else {
        alert('Order Execution Error: ' + (data.error || 'Failed to place paper trade.'));
        btnElem.disabled = false;
        btnElem.innerHTML = originalText;
      }
    } catch (e) {
      alert('Network Error placing order: ' + e.message);
      btnElem.disabled = false;
      btnElem.innerHTML = originalText;
    }
  };
'''

if 'executePaperTrade' not in content:
    target = '// Keyboard shortcut: Ctrl + Space'
    if target in content:
        content = content.replace(target, func_code + '\n  ' + target, 1)
        with open('scripts/append_chat_js.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Injected executePaperTrade into scripts/append_chat_js.py")
    else:
        print("Target shortcut comment not found.")
else:
    print("executePaperTrade already present.")
