class InvalidTransition(Exception):
    """Raised when a Bounty transition method is called from the wrong state
    (or by the wrong user). Views (#12-#14) map this to HTTP 409.
    """
