<div align="center">

# AEQueue (tk-aftereffects-queue)
**An After Effects render queue for ShotGrid Toolkit.**

[![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/nybrandnewschool/tk-aftereffects-queue?label=Version)](https://github.com/nybrandnewschool/tk-aftereffects-queue/releases) *Developed at [Brand New School](https://brandnewschool.com).*

<img src="https://raw.github.com/nybrandnewschool/tk-aftereffects-queue/master/res/aequeue_demo.gif"/>
</div>

## Features
- Render multiple comps to locations defined by templates in your Toolkit config.
- Compress full-res renders as MP4 and GIF using ffmpeg.
- Copy compressed renders to a review folder.
- Upload renders to ShotGrid for review.
- Send reports when errors occur during rendering.

## Error Reporting
When an error occurs during rendering, users can view a report, and when configured, they can send a report directly to the people who need to know!

<p align="center">
    <img src="https://raw.github.com/nybrandnewschool/tk-aftereffects-queue/master/res/aequeue_demo_reporting.gif"/>
</p>

# Installing
To install AEQueue make the changes in the `example_config` directory to your own toolkit config. This includes the following:

1. Modify `env/app_locations.yml` to include tk-aftereffects-queue.
2. Add `env/includes/settings/tk-aftereffects-queue.yml` to configure AEQueue. (See info.yml for details on configuration values.)
3. Modify `env/includes/settings/tk-aftereffects.yml` to include AEQueue in your `asset_step` and `shot_step` sections for the tk-aftereffects engine.

## Enable Sending Reports
1. You can enable sending reports by customizing the `send_report_hook`. Implement your
own or configure the builtin TicketSendReportHook. See `hooks/ticket_send_report_hook.py` for more details.
