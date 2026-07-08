- [ ] Add missing temp document workflow in editor.py: new_temp_document()
- [ ] Add save_as_pdf() and adjust save_pdf()/export_pdf() to match shortcut rules:
  - Ctrl+S => save_pdf() (if temp => overwrite temp)
  - Ctrl+Shift+S => save_as_pdf() (prompt)
- [ ] Hook Ctrl+Shift+S in keybindings
- [ ] Ensure temp document path is created once per New Temp and reused
- [ ] Verify with quick local run: create temp, add text, Ctrl+S works, Ctrl+Shift+S prompts output

