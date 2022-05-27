## Unreleased Changes

## 0.5.0

* Add cancel support. Tasks are now interruptable via the cancel button in the UI.
* Add AEPopupMonitor to close any AE popups that appear while background rendering.
* Add experimental support for background rendering. (Disabled by default.)
* Adjust context menus. You can now copy paths prior to rendering.
* Improve render startup time.
* Fix issue where SG instance timed out in Publish and Upload tasks.

  * Should implement task retrying to avoid any stupid upload failures to SG.

* Fix issue parsing float frame numbers like 29.97.

## 0.4.0

* Added *move_to_review_area* option. When enabled this will move encoded media to the
  review area, rather than copying the files.
* Added *publish_on_upload* option. When enabled this will register a PublishedFile
  linked to the Version file in ShotGrid. The Publish task also generates a thumbnail
  and filmstrip for the PublishedFile.

## 0.3.1

* Fixed issue on Mac OS where outputModule paths were not being set correctly.
* Improved reported of task exceptions and errors.

## 0.3.0

* Improved gif encoding to reduce file size.

  * Reduced color palette to 128 colors.
  * Clamped maximum resolution to 2160px wide.

    * _High Quality:_ Comp Width clamped to 2160px
    * _Medium Quality:_ Comp Width * 0.5 clamped to 1080px
    * _Low Quality:_ Comp Widget * 0.25 clamped to 540px

  * Default quality set to _Medium Quality._

* Improved mp4 encoding.

  * Pixel format is now yuv420p. Mp4s should now load properly in Windows 10 built-in media players.
  * Audio codec is now AAC. This should prevent errors when the audio track in AE is not mp4 compatible.

* Fixed error encoding mp4 with audio. The audio codec for mp4 is now AAC.
* Further improvements to report formatting.
* Refresh the available output modules each time the dialog is opened.
* ShotGird context is now updated just before rendering. This allows artists to open scenes using either the AE File Open dialog or the SG File Open dialog.
* Defer loading UI until menu action is called. Prevents AE from flagging scene as changed.

## 0.2.2

* Fix error while retrieving output module templates.
* Improved html reporting.
* Suppress dropEvent errors in AE2021.

## 0.2.1

* Fix Show in ShotGrid link when Version updated.

## 0.2.0

* Adjusted UI design to facilitate adding tools to the footer after a render completes.
* Added View Report button to allow users to see a step by step log of the render process.
* Added Send Error Report to allowing users to create a Ticket in ShotGrid when an error occurs.

    ![aequeue_demo_reporting.gif](https://raw.github.com/nybrandnewschool/tk-aftereffects-queue/master/res/aequeue_demo_reporting.gif)

* Added support for dragging and dropping AE comps directly into the Queue.

    ![aequeue_demo_dragndrop.gif](https://raw.github.com/nybrandnewschool/tk-aftereffects-queue/master/res/aequeue_demo_dragndrop.gif)

## 0.1.0

* Render your comps to the correct location!
* Encode your renders as MP4 and GIF for review.
* Copy MP4s and GIFs directly to the project review folder for your shot.
* Upload to ShotGrid for Review.
* After rendering perform useful actions like previewing, copying the path, importing, or showing in ShotGrid or your file browser.
* Initial release of code and readme.
* Available through github!
