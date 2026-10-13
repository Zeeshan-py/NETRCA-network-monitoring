class NetworkError(RuntimeError):
    code = "NETWORK_ERROR"
    http_status = 500


class NetworkUnavailable(NetworkError):
    code = "MININET_UNAVAILABLE"
    http_status = 503


class NetworkAlreadyRunning(NetworkError):
    code = "NETWORK_ALREADY_RUNNING"
    http_status = 409


class NetworkNotRunning(NetworkError):
    code = "NETWORK_NOT_RUNNING"
    http_status = 409


class OperationBusy(NetworkError):
    code = "NETWORK_OPERATION_IN_PROGRESS"
    http_status = 409


class StartupFailure(NetworkError):
    code = "NETWORK_START_FAILED"
    http_status = 503


class ShutdownFailure(NetworkError):
    code = "NETWORK_STOP_FAILED"
    http_status = 503


class ConnectivityFailure(NetworkError):
    code = "CONNECTIVITY_FAILED"
    http_status = 503


class MonitoringFailure(NetworkError):
    code = "MONITORING_FAILED"
    http_status = 503


class InvalidProbeTarget(NetworkError):
    code = "INVALID_PROBE_TARGET"
    http_status = 400
