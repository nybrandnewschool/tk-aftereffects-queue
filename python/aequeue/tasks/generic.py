from .. import const
from .core import Task, sleep


class LongRunningTask(Task):
    def __init__(self, steps, step_interval=0.1, *args, **kwargs):
        self.steps = steps
        self.step_interval = step_interval
        super(LongRunningTask, self).__init__(*args, **kwargs)

    def execute(self):
        for i in range(self.steps):
            if self.status_request == const.Cancelled:
                return self.accept(const.Cancelled)

            self.set_status(const.Running, (i / (self.steps - 1)) * 100)
            self.log.debug("Step %d of %d" % (i + 1, self.steps))
            sleep(self.step_interval)


class FunctionTask(Task):
    def __init__(self, func, func_kwargs=None, *args, **kwargs):
        self.func = func
        self.func_args = (self,)
        self.func_kwargs = func_kwargs or {}
        super(FunctionTask, self).__init__(*args, **kwargs)

    def __str__(self):
        return "<FunctionTask:{}:{}>".format(self.func.__name__, self.id)

    def execute(self):
        return self.func(*self.func_args, **self.func_kwargs)


class ErrorTask(Task):
    def execute(self):
        for i in range(5):
            sleep(0.1)
        raise RuntimeError("TASK RAISED AN ERROR!!!")
