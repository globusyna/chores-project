class InvalidTransition(Exception):
    """Raised when a Purchase transition method is called from the wrong
    state. The fulfilment view (#19) maps this to HTTP 409.
    """
