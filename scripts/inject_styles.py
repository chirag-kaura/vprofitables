css_addition = """
/* Interactive Swarm Execution & Options Ladder */
.vprof-order-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-left: 4px solid #3b82f6;
  border-radius: 8px;
  padding: 14px;
  margin: 10px 0;
  transition: transform 0.15s ease, border-color 0.15s ease;
}
.vprof-order-card:hover {
  border-color: #38bdf8;
  transform: translateY(-1px);
}
.vprof-btn-execute {
  background: #2563eb;
  color: #ffffff;
  font-weight: 600;
  font-size: 12px;
  border: none;
  border-radius: 6px;
  padding: 8px 14px;
  cursor: pointer;
  width: 100%;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.vprof-btn-execute:hover {
  background: #1d4ed8;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
}
.vprof-btn-execute:disabled {
  background: #059669 !important;
  color: #f8fafc !important;
  cursor: default !important;
  box-shadow: none !important;
}
.vprof-options-ladder {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 10px;
  padding: 14px;
  margin: 12px 0;
}
.vprof-preference-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: #34d399;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  margin: 6px 0;
}
"""

with open('pages/_html_head.html', 'r', encoding='utf-8') as f:
    content = f.read()

if '.vprof-order-card' not in content:
    target = '</style>'
    idx = content.rfind(target)
    if idx != -1:
        new_content = content[:idx] + css_addition + "\n" + content[idx:]
        with open('pages/_html_head.html', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Updated pages/_html_head.html successfully.")
    else:
        print("Target </style> not found.")
else:
    print("Styles already present in pages/_html_head.html.")
