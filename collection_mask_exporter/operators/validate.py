import bpy

from ..core.conflict_checker import validate_groups
from ..core.compatibility import write_compatibility_report
from ..core.group_resolver import resolve_groups
from ..translations import iface


class CMASK_OT_Validate(bpy.types.Operator):
    bl_idname = "cmask.validate"
    bl_label = "Check Scene"
    bl_description = "Check empty Collections, duplicate names, overlapping membership and instance sources"

    def execute(self, context):
        settings = context.scene.cmask_settings
        issues, _resolution = validate_groups(settings)
        settings.issues.clear()
        for issue in issues:
            item = settings.issues.add()
            item.level = issue.level
            item.code = issue.code
            item.subject = issue.subject
            item.message = issue.message
        settings.issue_count = len(issues)
        if not issues:
            settings.last_status = iface("Check passed; no issues found")
            self.report({"INFO"}, settings.last_status)
            return {"FINISHED"}
        errors = sum(issue.level == "ERROR" for issue in issues)
        settings.last_status = iface("Found {count} issues ({errors} errors)").format(
            count=len(issues), errors=errors
        )
        for issue in issues[:8]:
            self.report({issue.level}, f"{issue.subject}: {issue.message}")
        return {"CANCELLED"} if errors else {"FINISHED"}


class CMASK_OT_CompatibilityReport(bpy.types.Operator):
    bl_idname = "cmask.compatibility_report"
    bl_label = "API Compatibility Report"
    bl_description = "Check critical Blender APIs and write a structured JSON report"

    def execute(self, context):
        settings = context.scene.cmask_settings
        try:
            path, payload = write_compatibility_report(context.scene, settings)
        except (OSError, RuntimeError, ValueError) as exc:
            settings.last_status = iface("Compatibility report failed: {error}").format(error=exc)
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        settings.last_diagnostic_report = path
        if payload["compatible"]:
            status = payload["support_status"]
            if status == "SUPPORTED":
                settings.last_status = iface("API compatibility passed (formally supported): {path}").format(path=path)
                self.report({"INFO"}, settings.last_status)
            elif status == "UNSUPPORTED":
                settings.last_status = iface(
                    "Critical APIs are available, but Blender {version} is below the minimum supported version 4.5: {path}"
                ).format(version=payload["blender_version"], path=path)
                self.report({"WARNING"}, settings.last_status)
            else:
                settings.last_status = iface(
                    "Critical APIs are available, but Blender {version} is not yet in the formal validation matrix: {path}"
                ).format(version=payload["blender_version"], path=path)
                self.report({"WARNING"}, settings.last_status)
            return {"FINISHED"}
        failures = ", ".join(payload["required_failures"])
        settings.last_status = iface("API compatibility failed: {failures}; report: {path}").format(
            failures=failures, path=path
        )
        self.report({"ERROR"}, settings.last_status)
        return {"CANCELLED"}


class CMASK_OT_ConfigureGeometryNodesSplit(bpy.types.Operator):
    bl_idname = "cmask.configure_geometry_nodes_split"
    bl_label = "Configure Static GN Split"
    bl_description = "Set Geometry Nodes hosts with grouped static sources to IGNORE and enable splitting"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.cmask_settings
        resolution = resolve_groups(
            settings.groups, settings.include_children, include_disabled=True
        )
        owners = []
        source_groups = []
        for host, sources in resolution.geometry_node_sources.items():
            owner = resolution.assignments.get(host)
            if owner is None:
                continue
            resolved = []
            for source in sources:
                item = resolution.assignments.get(source)
                if item is not None and item != owner and item not in resolved:
                    resolved.append(item)
            if not resolved:
                continue
            if owner not in owners:
                owners.append(owner)
            for item in resolved:
                if item not in source_groups:
                    source_groups.append(item)
        if not owners:
            message = iface("No splittable Geometry Nodes host and explicit source groups were found")
            settings.last_status = message
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        for owner in owners:
            owner.enabled = True
            owner.role = "IGNORE"
        settings.geometry_nodes_split_sources = True
        settings.last_status = iface(
            "Configured {hosts} GN hosts; resolved {groups} source groups"
        ).format(hosts=len(owners), groups=len(source_groups))
        self.report({"INFO"}, settings.last_status)
        return {"FINISHED"}


CLASSES = (
    CMASK_OT_Validate,
    CMASK_OT_CompatibilityReport,
    CMASK_OT_ConfigureGeometryNodesSplit,
)
