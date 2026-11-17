import ctypes, sys
sys.stdout.reconfigure(encoding='utf-8')
user32 = ctypes.windll.user32
h_desk = user32.OpenDesktopW('default', 0, False, 0x01FF)
if h_desk:
    user32.SetThreadDesktop(h_desk)

import win32com.client
app = win32com.client.GetActiveObject('Excel.Application')
wb = app.ActiveWorkbook
ws = wb.Sheets('5.0 Reaction')

print('=== FULL SCAN OF REACTION CHECK TABLE IN 5.0 REACTION ===')
current_pat = ''
results = []

for r in range(98, 242):
    pat = ws.Range(f'C{r}').Value
    direction = ws.Range(f'F{r}').Value
    inp = ws.Range(f'I{r}').Value
    out = ws.Range(f'M{r}').Value
    chk = ws.Range(f'Q{r}').Value
    
    if pat is not None and str(pat).strip() != '' and str(pat).strip() != 'Load Pattem':
        current_pat = str(pat).strip()
        
    if direction in ['X', 'Y', 'Z']:
        results.append({
            'row': r,
            'pat': current_pat,
            'dir': direction,
            'input': inp,
            'output': out,
            'check': chk
        })

ng_list = [x for x in results if str(x['check']) == 'NG']
err_list = [x for x in results if str(x['check']) not in ['OK', 'NG']]
ok_list = [x for x in results if str(x['check']) == 'OK']

print(f'Total checks: {len(results)}')
print(f'OK count: {len(ok_list)}')
print(f'NG count: {len(ng_list)}')
print(f'ERROR / #REF! count: {len(err_list)}')

print('\n--- LIST OF NG CASES ---')
for x in ng_list:
    inp_str = f"{x['input']:.4f}" if isinstance(x['input'], (int, float)) else str(x['input'])
    out_str = f"{x['output']:.4f}" if isinstance(x['output'], (int, float)) else str(x['output'])
    diff = ''
    if isinstance(x['input'], (int, float)) and isinstance(x['output'], (int, float)) and abs(x['input']) > 0:
        d = (abs(x['output']) - abs(x['input'])) / abs(x['input']) * 100
        diff = f' (Diff: {d:+.2f}%)'
    print(f"Row {x['row']:3d}: Pat={x['pat']:10s} | Dir={x['dir']} | Input={inp_str:12s} | Output={out_str:12s} | Check=NG{diff}")

print('\n--- LIST OF ERROR / #REF! CASES ---')
for x in err_list:
    print(f"Row {x['row']:3d}: Pat={x['pat']:10s} | Dir={x['dir']} | Input={x['input']} | Output={x['output']} | Check={x['check']}")
