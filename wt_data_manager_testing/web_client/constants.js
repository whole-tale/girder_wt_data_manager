var TransferStatus = {
    INITIALIZING: 0,
    QUEUED: 1,
    TRANSFERRING: 2,
    DONE: 3,
    FAILED: 4,
    toString: function(status) {
        switch(status) {
            case TransferStatus.INITIALIZING:
                return "Initializing";
            case TransferStatus.QUEUED:
                return "Queued";
            case TransferStatus.TRANSFERRING:
                return "Transferring";
            case TransferStatus.DONE:
                return "Done";
            case TransferStatus.FAILED:
                return "Failed";

        }
    }
};

export default TransferStatus;