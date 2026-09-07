class LedgerError(Exception):
    """Raised for any misuse of the point ledger: a zero-amount transaction,
    or an attempt to modify an existing (append-only) `PointTransaction`.
    """
