# ─── SAP2000 Script ─────────────────────────────────────────────
# Name:        taller_v05_analizar_disenar
# Description: Reanalizar y correr el diseño de acero
# Created:     2026-08-21 13:27:01 UTC
# Status:      ✓ Verified (executed successfully)
# Result:      {"locked_antes": false, "run": 0, "locked_tras_analisis": true, "design": 0, "diseno_hecho": true}
# Tags:        
# ──────────────────────────────────────────────────────────────


result["locked_antes"] = SapModel.GetModelIsLocked()
SapModel.Analyze.SetRunCaseFlag("", True, True)
result["run"] = SapModel.Analyze.RunAnalysis()
result["locked_tras_analisis"] = SapModel.GetModelIsLocked()
result["design"] = SapModel.DesignSteel.StartDesign()
result["diseno_hecho"] = SapModel.DesignSteel.GetResultsAvailable()
