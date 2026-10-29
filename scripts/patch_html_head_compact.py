def patch_css():
    with open("pages/_html_head.html", "r", encoding="utf-8") as f:
        c = f.read()

    target = """.admin-inline-lock-pill {
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
}"""

    target_crlf = target.replace("\n", "\r\n")

    replacement = """.admin-inline-lock-pill {
  position: absolute;
  top: 6px;
  right: 8px;
  z-index: 50;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  line-height: 1.2;
}
.admin-inline-lock-pill.locked {
  background: rgba(242, 54, 69, 0.25);
  color: #FF5252;
  border: 1px solid rgba(242, 54, 69, 0.8);
  box-shadow: 0 0 10px rgba(242, 54, 69, 0.3);
}
.admin-inline-lock-pill.locked:hover {
  background: rgba(242, 54, 69, 0.4);
  transform: scale(1.05);
}
.admin-inline-lock-pill.unlocked {
  background: rgba(8, 153, 129, 0.25);
  color: #00E676;
  border: 1px solid rgba(8, 153, 129, 0.8);
  box-shadow: 0 0 10px rgba(8, 153, 129, 0.3);
}
.admin-inline-lock-pill.unlocked:hover {
  background: rgba(8, 153, 129, 0.4);
  transform: scale(1.05);
}

/* Universal Gating for Free Tier (Cards & Sub-Sections) */
.admin-feature-locked-for-free {
  position: relative !important;
}
body.effective-role-free .admin-feature-locked-for-free > *:not(.admin-locked-free-overlay):not(.admin-inline-lock-pill) {
  filter: blur(5px) !important;
  pointer-events: none !important;
  user-select: none !important;
  opacity: 0.35 !important;
  transition: filter 0.25s ease;
}
.admin-locked-free-overlay {
  position: absolute;
  inset: 0;
  background: rgba(11, 14, 20, 0.90);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 16px;
  border-radius: 6px;
  border: 1px dashed rgba(255, 152, 0, 0.5);
  overflow: hidden;
}
.admin-locked-free-overlay.compact {
  flex-direction: row !important;
  gap: 10px !important;
  padding: 4px 10px !important;
  justify-content: center !important;
  align-items: center !important;
}"""

    replacement_crlf = replacement.replace("\n", "\r\n")

    if target in c:
        c = c.replace(target, replacement, 1)
    elif target_crlf in c:
        c = c.replace(target_crlf, replacement_crlf, 1)
    else:
        print("Target not found in pages/_html_head.html!")
        return False

    with open("pages/_html_head.html", "w", encoding="utf-8") as f:
        f.write(c)
    print("Successfully patched pages/_html_head.html CSS!")
    return True

if __name__ == "__main__":
    patch_css()
