# Changelog

## 2026-11-11

- Add GitHub CLI to the devcontainer; document the branch flow (fd3447b744)
  - Add GitHub CLI feature to devcontainer; slim apt install
  - Document branch flow
- Rename to LiveCues VideoCues with a new icon; slim the devcontainer (e42f33546c)
  - Rename to LiveCues VideoCues
  - Stop showing the app name twice in window titles
  - Add Node to devcontainer; ignore Impeccable files
  - New app icon in the ReaperRemote hardware style
  - Speed up and slim down the devcontainer
- Rework the control window in the LiveCues suite look (8b658052a1)
  - Rework the control window in the LiveCues suite look
  - Update design doc and control window
  - Restructure the Run page view controls as steppers with a collapsible Crop
  - Update control window and theme
  - Move Test Trigger to the Edit page; fix Crop buttons passing clicked bool as side
  - Remove the global Test Trigger key, align Crop with Move and Zoom, add empty states
- Add community files, Dependabot and security CI (8bc1e6f443)
  - Add community files, Dependabot, and security CI; pin dependencies
  - Audit every branch weekly; document Dependabot security updates
- Publish releases from tags and check for updates in the app (a4e9e56854)
  - Publish releases from tags and check for updates in the app
