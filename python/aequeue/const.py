# Flow Steps
Queued = "queued"
Rendering = "rendering"
Encoding = "encoding"
Moving = "moving"
Copying = "copying"
Uploading = "uploading"
Publishing = "publishing"
Cleaning = "cleaning"
Done = "done"
StepList = [
    Queued,
    Rendering,
    Encoding,
    Moving,
    Copying,
    Uploading,
    Publishing,
    Cleaning,
    Done,
]

# Flow/Task Statuses
Waiting = "waiting"  # Task/Run is waiting to run.
Running = "running"  # Task/Run is running.
Cancelled = "cancelled"  # Task/Run has been requested to stop.
Revoked = "revoked"  # When a Task has upstream dependencies that have failed.
Failed = "failed"  # Task has failed - usually raising an exception.
Success = "success"  # Task has finished running successfully.
StatusList = [Waiting, Running, Cancelled, Revoked, Failed, Success]
DoneList = [Done, Cancelled, Failed, Revoked, Success]

# Default Options
DefaultOptions = {
    "Quality": [
        "High Quality",
        "Medium Quality",
        "Low Quality",
        "Min Quality",
    ],
    "Resolution": [
        "Full",
        "Half",
        "Quarter",
        "1920",
        "1080",
        "960",
        "720",
        "360",
    ],
}
