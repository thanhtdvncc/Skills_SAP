"""
SAP2000 COM Bridge — Manages connection to a local SAP2000 instance via COM.

Supports two modes:
  - Launch a new SAP2000 instance (given a program path)
  - Attach to an already-running instance

All COM interaction is centralized here. Other modules use this bridge
to obtain SapObject and SapModel references.
"""

import sys

# Crucial: On Windows, ensure thread is attached to interactive desktop BEFORE importing comtypes / COM init
if sys.platform == "win32":
    try:
        import ctypes
        user32 = ctypes.windll.user32
        h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
    except Exception:
        pass

import comtypes.client
import logging

logger = logging.getLogger(__name__)


def _ensure_default_desktop():
    """Ensure the current thread is attached to the interactive 'default' desktop in Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass


class SapBridge:
    """Wrapper around the SAP2000 COM connection."""

    def __init__(self):
        self._sap_object = None
        self._sap_model = None
        self._helper = None

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def sap_object(self):
        """Return the current cOAPI SapObject, or None if not connected."""
        return self._sap_object

    @property
    def sap_model(self):
        """Return the current cSapModel, or None if not connected."""
        return self._sap_model

    @property
    def is_connected(self) -> bool:
        """True when we hold a live SapObject reference."""
        return self._sap_object is not None

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _create_helper(self):
        """Instantiate the SAP2000 COM helper once."""
        _ensure_default_desktop()
        if self._helper is None:
            helper = comtypes.client.CreateObject("SAP2000v1.Helper")
            try:
                self._helper = helper.QueryInterface(comtypes.gen.SAP2000v1.cHelper)
            except Exception:
                self._helper = helper

    def connect(
        self,
        program_path: str | None = None,
        attach_to_existing: bool = True,
    ) -> dict:
        """
        Connect to SAP2000.

        Parameters
        ----------
        program_path : str | None
            Full path to SAP2000.exe.  Ignored when *attach_to_existing* is True.
            When None and attach_to_existing is False, the latest installed
            version is launched via ProgID.
        attach_to_existing : bool
            If True, attach to an already-running SAP2000 instance.

        Returns
        -------
        dict  {connected, version, model_path, units, error}
        """
        if self.is_connected:
            return {
                "connected": True,
                "message": "Already connected to SAP2000.",
                **self._model_summary(),
            }

        self._create_helper()

        try:
            if attach_to_existing:
                try:
                    self._sap_object = self._helper.GetObject(
                        "CSI.SAP2000.API.SapObject"
                    )
                except Exception:
                    self._sap_object = None

                if self._sap_object is None:
                    self._sap_object = self._helper.CreateObjectProgID(
                        "CSI.SAP2000.API.SapObject"
                    )
                logger.info("Attached to existing SAP2000 instance.")
            elif program_path:
                self._sap_object = self._helper.CreateObject(program_path)
                self._sap_object.ApplicationStart()
                logger.info("Started SAP2000 from %s", program_path)
            else:
                self._sap_object = self._helper.CreateObjectProgID(
                    "CSI.SAP2000.API.SapObject"
                )
                self._sap_object.ApplicationStart()
                logger.info("Started latest installed SAP2000 via ProgID.")

            if self._sap_object is None:
                raise RuntimeError("Failed to obtain SapObject from SAP2000v1.Helper")

            self._sap_model = self._sap_object.SapModel
            return {"connected": True, **self._model_summary()}

        except Exception as exc:
            self._sap_object = None
            self._sap_model = None
            logger.exception("Failed to connect to SAP2000.")
            return {"connected": False, "error": str(exc)}

    def disconnect(self, save_model: bool = False) -> dict:
        """
        Disconnect from SAP2000 and optionally save the model.

        Setting references to None is critical — without it SAP2000 may
        hang in Task Manager.
        """
        if not self.is_connected:
            return {"disconnected": True, "message": "Was not connected."}

        try:
            self._sap_object.ApplicationExit(save_model)
        except Exception as exc:
            logger.warning("ApplicationExit raised: %s", exc)
        finally:
            self._sap_model = None
            self._sap_object = None
            logger.info("Disconnected from SAP2000 (save=%s).", save_model)

        return {"disconnected": True, "saved": save_model}

    def get_model_info(self) -> dict:
        """
        Return a summary of the current connection and model state.

        Useful for the agent to verify state before/after executing scripts.
        """
        if not self.is_connected:
            return {"connected": False, "error": "Not connected to SAP2000."}

        return {"connected": True, **self._model_summary()}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _model_summary(self) -> dict:
        """Gather basic info from the live SapModel."""
        info: dict = {}
        try:
            info["model_path"] = self._sap_model.GetModelFilename(True)
        except Exception:
            info["model_path"] = None

        try:
            info["version"] = self._sap_object.GetOAPIVersionNumber()
        except Exception:
            info["version"] = None

        try:
            info["units"] = self._sap_model.GetPresentUnits()
        except Exception:
            info["units"] = None

        try:
            ret_frame = self._sap_model.FrameObj.Count()
            info["num_frames"] = ret_frame if isinstance(ret_frame, int) else ret_frame[0]
        except Exception:
            info["num_frames"] = None

        try:
            ret_point = self._sap_model.PointObj.Count()
            info["num_points"] = ret_point if isinstance(ret_point, int) else ret_point[0]
        except Exception:
            info["num_points"] = None

        try:
            ret_area = self._sap_model.AreaObj.Count()
            info["num_areas"] = ret_area if isinstance(ret_area, int) else ret_area[0]
        except Exception:
            info["num_areas"] = None

        return info


# Module-level singleton so the MCP server and executor share one bridge.
bridge = SapBridge()
