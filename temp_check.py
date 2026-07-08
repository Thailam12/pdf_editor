import importlib
mods=['tkinter','PIL','pymupdf','customtkinter','paddleocr']
for m in mods:
    try:
        importlib.import_module(m)
        print(m, 'OK')
    except Exception as e:
        print(m, 'ERR', repr(e))
