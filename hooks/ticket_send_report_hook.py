import os
import sgtk

TITLE_TEMPLATE = '{user} got an error rendering {project}.'
DESCRIPTION_TEMPLATE = ('''
__Report__
```
{report}
```
__Context__
```
{ctx}
```
''').lstrip()


class TicketSendReportHook(sgtk.get_hook_baseclass()):
    '''The default implementation disables the Send Report features.

    Here is an example configuration for use with this hook:
        ...
        send_report_hook: {self}/ticket_send_report_hook.py
        send_report_settings:
            default_assignee: {'type': 'Group', 'id': 10}

    Above we set the default_assignee to a group - in my case the Tech Group. You could
    use a HumanUser Entity as well to assign the Ticket directly to a single user.
    '''

    def is_available(self):
        '''Return True to show the Send button in the UI.'''

        return True

    def send_on_error(self):
        '''When send_on_error returns True, automatically send error reports when
        a render fails. If True, the Send button will be hidden regardless of the value
        of is_available.
        '''

        return False

    def send(self, ctx, runner, report, html_report, settings):
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

        self.create_ticket({
            'title': TITLE_TEMPLATE.format(
                user=ctx.user['name'],
                project=os.path.basename(self.parent.engine.project_path),
            ),
            'description': DESCRIPTION_TEMPLATE.format(
                report=report,
                ctx=self.format_ctx(ctx)
            ),
            'project': ctx.project,
            'addressings_to': [settings['default_assignee']],
        })

    def create_ticket(self, data):
        '''Create a Ticket in ShotGrid.'''

        self.parent.logger.debug('Creating new Ticket: %s' % data.get('title', ''))
        return self.parent.shotgun.create('Ticket', data=data)

    def format_ctx(self, ctx):
        '''Format a context dict to be used in the Ticket "context" field.'''

        lines = ['Context:']
        for key, value in ctx.to_dict().items():
            lines.append('  {}: {}'.format(key, value))
        return '\n'.join(lines)
