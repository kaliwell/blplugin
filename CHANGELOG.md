# Changelog

All notable changes to Collection Mask Exporter are recorded here.

## 0.8.0 - 2026-08-02

- Name mask files, Photoshop layers, and Alpha channels after Collection groups.
- Render mask RGB with the same per-group color used by the Color ID output.
- Add one-click delivery for the beauty render, Color ID, masks, Photoshop JSX,
  handoff manifest, export report, and optional compositor nodes.
- Expose the one-click workflow to the Blender UI and background CLI.

## 0.7.0 - 2026-08-02

- Limit the formal support matrix to Blender 4.5.x, 5.0.x, and 5.2.x.
- Raise the Blender Extension minimum version to 4.5.0.
- Mark other installable Blender version lines as `UNVALIDATED` in compatibility reports.
- Rebuild and verify the sample project with Blender 4.5.
- Validate core, UI, translation, sample-project, PNG, OpenEXR, Multilayer EXR,
  Cryptomatte, and batch rendering on every supported version line.
- Add the GPL-3.0-or-later license text, third-party runtime notices, and SPDX
  copyright/license headers to every Python source file.

## 0.6.0 - 0.6.6 - 2026-08-01 to 2026-08-02

- Add evaluated FACE/INT `cmask_id` splitting for dynamic Geometry Nodes output.
- Add Blender-following Simplified Chinese and English localization.
- Add Blender 5.2 panel API and icon compatibility fixes.
- Add Photoshop JSX delivery, named Alpha channels, empty-mask handling, and safe
  degradation when an Alpha operation is unavailable.
- Complete an actual Photoshop delivery with six layers, five Alpha channels, and PSD save.

## 0.5.0 - 0.5.3 - 2026-08-01

- Add output-reachable static Geometry Nodes source splitting.
- Add one-click static GN host configuration and nested group-output analysis.

## 0.4.0 - 0.4.6 - 2026-08-01

- Add CLI/render-farm jobs, Collection Instance handling, Photoshop handoff,
  static Geometry Nodes dependency analysis, sample project, and compatibility reports.

## 0.1.0 - 0.3.5 - 2026-07-31 to 2026-08-01

- Establish Collection scanning, roles, conflict resolution, masks, Color ID,
  presets, batch export, PNG/OpenEXR, Multilayer EXR, and Collection Cryptomatte.
