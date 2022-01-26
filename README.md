# AEQueue
An After Effects render queue for ShotGrid Toolkit.

<p align="center">
    <img src="https://raw.github.com/nybrandnewschool/tk-aftereffects-queue/master/res/aequeue_demo.gif"/>
</p>

## Features
- Render multiple comps to locations defined by templates in your Toolkit config.
- Compress full-res renders as MP4 and GIF using ffmpeg.
- Copy compressed renders to a review folder.
- Upload renders to ShotGrid for review.

## TODO
- Make UI dpi-aware.
- Add Publish step to publish the base render (and aep?)
- Add pre and post render hooks.

# Installing
To install AEQueue make the changes in the `example_config` directory to your own toolkit config. This includes the following:

1. Modify `env/app_locations.yml` to include tk-aftereffects-queue.
2. Add `env/includes/settings/tk-aftereffects-queue.yml` to configure AEQueue. (See info.yml for details on configuration values.)
3. Modify `env/includes/settings/tk-aftereffects.yml` to include AEQueue in your `asset_step` and `shot_step` sections for the tk-aftereffects engine.
