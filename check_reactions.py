import ctypes
user32 = ctypes.windll.user32
h_desk = user32.OpenDesktopW('default', 0, False, 0x01FF)
if h_desk:
    user32.SetThreadDesktop(h_desk)

import comtypes.client
sap = comtypes.client.GetActiveObject('CSI.SAP2000.API.SapObject')
model = sap.SapModel

target_cases = ['WXBP', 'WXRP', 'WXBN', 'WXRN', 'WXS', 'WYBP', 'WYRP', 'WYBN', 'WYRN', 'WYS', 'WXIP', 'WXIN', 'WYIP', 'WYIN']

# Standardized values from Excel summary table (rows 808-824):
expected = {
    'WXBP': (34.057, 0.000, 0.000),
    'WXRP': (0.000, 0.000, -33.530),
    'WXBN': (35.140, 0.000, 0.000),
    'WXRN': (0.000, 0.000, -30.027),
    'WXS':  (0.000, -1.510, 0.000),
    'WYBP': (0.000, 26.619, 0.000),
    'WYRP': (0.000, 0.000, -30.027),
    'WYBN': (0.000, 25.797, 0.000),
    'WYRN': (0.000, 0.000, -33.581),
    'WYS':  (1.990, 0.000, 0.000),
    'WXIP': (0.567, 0.000, 8.556),
    'WXIN': (-0.609, 0.000, -8.556),
    'WYIP': (0.000, -0.430, 8.556),
    'WYIN': (0.000, 0.462, -8.556),
}

model.Results.Setup.DeselectAllCasesAndCombosForOutput()
for c in target_cases:
    model.Results.Setup.SetCaseSelectedForOutput(c)

res = model.Results.BaseReact()

print(f"{'CASE':6s} | {'DIR':3s} | {'EXCEL Target':12s} | {'SAP BaseReact':14s} | {'SAP Applied':12s} | {'Diff (%)':9s} | {'Status':6s}")
print('-'*75)

for i in range(res[0]):
    c = res[1][i]
    r_fx, r_fy, r_fz = res[4][i], res[5][i], res[6][i]
    app_fx, app_fy, app_fz = -r_fx, -r_fy, -r_fz
    
    exp_fx, exp_fy, exp_fz = expected[c]
    
    # Check FX
    if abs(exp_fx) > 0.001 or abs(app_fx) > 0.1:
        diff = ((abs(app_fx) - abs(exp_fx)) / abs(exp_fx)) * 100 if abs(exp_fx) > 0.001 else 999.0
        status = 'PASS' if abs(diff) <= 6.0 else 'CHECK'
        print(f"{c:6s} | {'FX':3s} | {exp_fx:12.3f} | {r_fx:14.4f} | {app_fx:12.4f} | {diff:8.2f}% | {status}")

    # Check FY
    if abs(exp_fy) > 0.001 or abs(app_fy) > 0.1:
        diff = ((abs(app_fy) - abs(exp_fy)) / abs(exp_fy)) * 100 if abs(exp_fy) > 0.001 else 999.0
        status = 'PASS' if abs(diff) <= 6.0 else 'CHECK'
        print(f"{c:6s} | {'FY':3s} | {exp_fy:12.3f} | {r_fy:14.4f} | {app_fy:12.4f} | {diff:8.2f}% | {status}")

    # Check FZ
    if abs(exp_fz) > 0.001 or abs(app_fz) > 0.1:
        diff = ((abs(app_fz) - abs(exp_fz)) / abs(exp_fz)) * 100 if abs(exp_fz) > 0.001 else 999.0
        status = 'PASS' if abs(diff) <= 6.0 else 'CHECK'
        print(f"{c:6s} | {'FZ':3s} | {exp_fz:12.3f} | {r_fz:14.4f} | {app_fz:12.4f} | {diff:8.2f}% | {status}")
