def patch_html_head():
    with open("pages/_html_head.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    target = "  box-shadow: inset 0 0 25px rgba(0, 212, 255, 0.12);\n}"
    if target not in content:
        # try CRLF
        target = "  box-shadow: inset 0 0 25px rgba(0, 212, 255, 0.12);\r\n}"
        if target not in content:
            print("Target not found in _html_head.html!")
            return False
    
    css_addition = """

/* Admin In-Tab Lock/Unlock Controller Badges & Gating Styles */
.admin-inline-lock-pill {
  position: absolute;
  top: 10px;
  right: 12px;
  z-index: 50;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}
.admin-inline-lock-pill.locked {
  background: rgba(242, 54, 69, 0.2);
  color: #FF5252;
  border: 1px solid rgba(242, 54, 69, 0.7);
  box-shadow: 0 0 10px rgba(242, 54, 69, 0.25);
}
.admin-inline-lock-pill.locked:hover {
  background: rgba(242, 54, 69, 0.35);
  transform: scale(1.05);
}
.admin-inline-lock-pill.unlocked {
  background: rgba(8, 153, 129, 0.2);
  color: #00E676;
  border: 1px solid rgba(8, 153, 129, 0.7);
  box-shadow: 0 0 10px rgba(8, 153, 129, 0.25);
}
.admin-inline-lock-pill.unlocked:hover {
  background: rgba(8, 153, 129, 0.35);
  transform: scale(1.05);
}

/* Card Gating for Free Tier */
.card.admin-feature-locked-for-free {
  position: relative !important;
}
body.effective-role-free .card.admin-feature-locked-for-free > *:not(.admin-locked-free-overlay):not(.admin-inline-lock-pill) {
  filter: blur(5.5px) !important;
  pointer-events: none !important;
  user-select: none !important;
  opacity: 0.45 !important;
  transition: filter 0.3s ease;
}
.admin-locked-free-overlay {
  position: absolute;
  inset: 0;
  background: rgba(11, 14, 20, 0.88);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 24px;
  border-radius: 6px;
  border: 1px dashed rgba(255, 152, 0, 0.5);
}

/* Admin Toast Notifications */
#admin-toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 999999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}
.admin-toast {
  background: rgba(21, 25, 36, 0.96);
  color: var(--white);
  border: 1px solid var(--border);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(10px);
  padding: 12px 18px;
  border-radius: 6px;
  font-family: 'Inter', sans-serif;
  font-size: 0.82rem;
  display: flex;
  align-items: center;
  gap: 10px;
  animation: adminToastIn 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  pointer-events: auto;
}
@keyframes adminToastIn {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}"""

    updated = content.replace(target, target + css_addition)
    with open("pages/_html_head.html", "w", encoding="utf-8") as f:
        f.write(updated)
    print("Successfully patched pages/_html_head.html!")
    return True

if __name__ == "__main__":
    patch_html_head()
