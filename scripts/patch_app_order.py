with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '"chat", "chat/status", "chat/suggestions", "chat/symbols"'
replacement = '"chat", "chat/status", "chat/suggestions", "chat/symbols", "chat/execute_order"'

target_chat = """        if ep == "chat":
            from core.chatbot_engine import handle_chat_query
            return handle_chat_query(p)"""

replacement_chat = """        if ep == "chat":
            from core.chatbot_engine import handle_chat_query
            if self.current_user:
                p["user_id"] = self.current_user.get("user_id") or self.current_user.get("id")
                p["username"] = self.current_user.get("display_name") or self.current_user.get("email")
            return handle_chat_query(p)

        if ep == "chat/execute_order":
            from core.tools.order_execution_tool import execute_in_chat_paper_order
            uid = None
            if self.current_user:
                uid = self.current_user.get("user_id") or self.current_user.get("id")
            return execute_in_chat_paper_order(
                symbol=p.get("symbol", ""),
                shares=p.get("shares", 1),
                entry_price=p.get("entry_price", 0.0),
                stop_loss=p.get("stop_loss", 0.0),
                target1=p.get("target1", 0.0),
                target2=p.get("target2"),
                inv_type=p.get("inv_type", "swing"),
                user_id=uid
            )"""

if target in text:
    text = text.replace(target, replacement, 1)
    text = text.replace(target_chat, replacement_chat, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: Added chat/execute_order to app.py")
else:
    print("Target string not found in app.py")
