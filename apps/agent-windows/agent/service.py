import os
import sys
import threading

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

SERVICE_NAME = "PatchManagerAgent"
SERVICE_DISPLAY = "Patch Manager Agent"
SERVICE_DESC = "Gerencia atualizacoes do host via Patch Manager."


def _run_direct() -> None:
    from main import main  # noqa: PLC0415
    main()


def _run_as_service() -> None:
    import servicemanager  # noqa: PLC0415
    import win32service  # noqa: PLC0415
    import win32serviceutil  # noqa: PLC0415

    class PatchManagerAgentService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY
        _svc_description_ = SERVICE_DESC
        _svc_start_type_ = win32service.SERVICE_AUTO_START

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self._stop_event = threading.Event()

        def GetAcceptedControls(self):
            return win32service.SERVICE_ACCEPT_STOP | win32service.SERVICE_ACCEPT_SHUTDOWN

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self._stop_event.set()

        def SvcShutdown(self):
            self.SvcStop()

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            from main import main  # noqa: PLC0415
            main(stop_event=self._stop_event)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ""),
            )

    if len(sys.argv) == 1:
        # Iniciado pelo Windows Service Control Manager (sem argumentos)
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PatchManagerAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Chamado com argumentos: install, remove, start, stop, etc.
        win32serviceutil.HandleCommandLine(PatchManagerAgentService)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "run":
        _run_direct()
    else:
        _run_as_service()
