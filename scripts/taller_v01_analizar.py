# ─── SAP2000 Script ─────────────────────────────────────────────
# Name:        taller_v01_analizar
# Description: Guardar y correr el análisis (DEAD y MODAL)
# Created:     2026-08-20 17:27:51 UTC
# Status:      ✓ Verified (executed successfully)
# Result:      {"save": 0, "casos": ["DEAD", "MODAL"], "run": 0, "locked_tras_analisis": true}
# Tags:        
# ──────────────────────────────────────────────────────────────


r={}
SapModel.SetPresentUnits(6)
# guardar ANTES de analizar: File.Save desbloquea y descarta resultados
r["save"] = SapModel.File.Save(r"C:\Proyectos_Python\Struct_Harness\_run\taller-neumaticos\v01_TRAZA_2026-08-20.sdb")
# correr solo DEAD y MODAL
n,cn,_ = SapModel.LoadCases.GetNameList(0,[])
r["casos"]=list(cn)
SapModel.Analyze.SetRunCaseFlag("", False, True)     # todos off
for c in ["DEAD","MODAL"]:
    SapModel.Analyze.SetRunCaseFlag(c, True, False)
r["run"] = SapModel.Analyze.RunAnalysis()
r["locked_tras_analisis"] = SapModel.GetModelIsLocked()
result=r
