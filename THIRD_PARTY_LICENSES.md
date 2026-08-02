# Third-Party Licenses

This notice covers third-party software that CMask integrates with at runtime or
uses during testing. No third-party source code or binary dependency is copied
into the CMask source tree or Blender extension package.

| Component | How CMask uses it | Bundled with CMask | License / terms |
|---|---|---|---|
| Blender and its Python modules (`bpy`, `bmesh`, `mathutils`) | Required host application and API | No | GNU GPL v3 or later for Blender as a whole; Blender contains components under compatible licenses. See <https://www.blender.org/about/license/> and the license files shipped with Blender. |
| Python standard library | General runtime utilities | No; provided by Blender's Python runtime | Python Software Foundation License Version 2. See <https://docs.python.org/3/license.html>. |
| OpenImageIO | EXR writing and validation when available | No; provided by supported Blender installations | Modified BSD / BSD-3-Clause-style license. See <https://github.com/AcademySoftwareFoundation/OpenImageIO/blob/main/LICENSE.md>. |
| Adobe Photoshop scripting host | Executes the generated JSX delivery script | No | Proprietary Adobe software; use is governed by the applicable Adobe terms. CMask does not redistribute Photoshop or Adobe source code. |

The generated Photoshop JSX is original CMask output and is distributed under
the same `GPL-3.0-or-later` terms as CMask unless a generated file states
otherwise.

The example `.blend` file contains project-authored geometry and settings. It
does not intentionally embed third-party textures, fonts, models, or other
assets.

If a future release vendors third-party source, binaries, fonts, textures, or
models, add the exact component version, upstream URL, copyright notice,
license identifier, license text location, and modified/unmodified status here
before publishing.
