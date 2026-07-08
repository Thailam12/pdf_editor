import os
import importlib
import traceback

root='d:/pdf_editor'
exclude_dirs={'output','tests','.git'}
count=0
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
    for name in filenames:
        if name.endswith('.py'):
            path=os.path.join(dirpath,name)
            try:
                with open(path,'r',encoding='utf-8') as fh:
                    count += sum(1 for _ in fh)
            except Exception:
                pass
print('line_count=', count)
mods=['tkinter','PIL','pymupdf','customtkinter','paddleocr']
for m in mods:
    try:
        importlib.import_module(m)
        print(m, 'OK')
    except Exception as e:
        print(m, 'ERR', repr(e))

try:
    import editor
    print('editor_import=OK')
except Exception as e:
    print('editor_import=ERR', repr(e))
    traceback.print_exc()
