

# Flow Steps
Queued = 'queued'
Rendering = 'rendering'
Encoding = 'encoding'
Copying = 'copying'
Uploading = 'uploading'
Done = 'done'
StepList = [Queued, Rendering, Encoding, Copying, Uploading, Done]

# Flow/Task Statuses
Waiting = 'waiting'  # Task/Run is waiting to run.
Running = 'running'  # Task/Run is running.
Cancelled = 'cancelled'  # Task/Run has been requested to stop.
Revoked = 'revoked'  # When a Task has upstream dependencies that have failed.
Failed = 'failed'  # Task has failed - usually raising an exception.
Success = 'success'  # Task has finished running successfully.
StatusList = [Waiting, Running, Cancelled, Revoked, Failed, Success]
DoneList = [Done, Cancelled, Failed, Revoked, Success]