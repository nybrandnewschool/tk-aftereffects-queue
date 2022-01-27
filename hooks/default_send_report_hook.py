import sgtk


class DefaultSendReportHook(sgtk.get_hook_baseclass()):
    '''The default implementation disables the Send Report features.'''

    def is_available(self):
        '''Return True to show the Send button in the UI.'''

        return False

    def send_on_error(self):
        '''When send_on_error returns True, automatically send error reports when
        a render fails. If True, the Send button will be hidden regardless of the value
        of is_available.
        '''

        return False

    def send(self, ctx, runner, report, html_report):
        '''Called to by application to send a report.

        Arguments:
            ctx (Context): ShotGrid context that the Runner was executed in.
            runner (Runner): The finished Runner including Flows for each comp that was
                in the Queue. The Runner was responsible for executing all Flows and
                their associated Tasks.
            report (str): A plaintext report generated from the Runners log records.
            html_report (str): An html report generated from the Runners log records.

        Return:
            None
        '''

        return NotImplemented
