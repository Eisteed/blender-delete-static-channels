import bpy
import bpy.types
import math


def is_fcurve_static(fcurve: bpy.types.FCurve, tolerance: float) -> bool:
    if fcurve.lock:
        return False

    # A modifier can make an otherwise constant set of keys evaluate differently.
    if fcurve.modifiers:
        return False

    keyframes = fcurve.keyframe_points
    samples = fcurve.sampled_points
    if not keyframes and not samples:
        return False

    points = keyframes if keyframes else samples
    value_reference = points[0].co[1]

    for point in points[1:]:
        if not math.isclose(point.co[1], value_reference, rel_tol=0.0, abs_tol=tolerance):
            return False

    # Equal Bezier key values can still produce a changing curve when their
    # handles have been moved vertically.
    for index, keyframe in enumerate(keyframes[:-1]):
        if keyframe.interpolation != 'BEZIER':
            continue
        next_keyframe = keyframes[index + 1]
        if not math.isclose(keyframe.handle_right[1], value_reference, rel_tol=0.0, abs_tol=tolerance):
            return False
        if not math.isclose(next_keyframe.handle_left[1], value_reference, rel_tol=0.0, abs_tol=tolerance):
            return False

    return True


def iter_action_fcurve_collections(action: bpy.types.Action):
    """Yield every F-Curve collection in an Action.

    Blender 4.4 and newer store F-Curves in channel bags inside layered
    Actions. Older Blender versions store them directly on ``action.fcurves``.
    """
    layers = getattr(action, "layers", None)
    if layers:
        for layer in layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    yield channelbag.fcurves
        return

    # Compatibility with legacy Actions (Blender 4.0-4.3).
    fcurves = getattr(action, "fcurves", None)
    if fcurves is not None:
        yield fcurves


def iter_animdata_fcurve_collections(animation_data: bpy.types.AnimData):
    """Yield the F-Curve collections belonging to AnimData's assigned slot."""
    action = animation_data.action
    if action is None:
        return

    layers = getattr(action, "layers", None)
    if layers:
        slot = animation_data.action_slot
        if slot is None:
            return

        for layer in layers:
            for strip in layer.strips:
                channelbag = strip.channelbag(slot)
                if channelbag is not None:
                    yield channelbag.fcurves
        return

    # Compatibility with legacy Actions (Blender 4.0-4.3).
    fcurves = getattr(action, "fcurves", None)
    if fcurves is not None:
        yield fcurves


def remove_static_fcurves(fcurve_collections, tolerance: float, predicate=None) -> int:
    """Remove matching static F-Curves from one or more collections."""
    deleted_count = 0

    for fcurves in fcurve_collections:
        for curve in list(fcurves):
            if predicate is not None and not predicate(curve):
                continue
            if is_fcurve_static(curve, tolerance):
                fcurves.remove(curve)
                deleted_count += 1

    return deleted_count


def cleanup_selected_objects(context: bpy.types.Context, tolerance: float) -> int:
    deleted_count = 0

    for obj in context.selected_objects:
        animation_data = obj.animation_data
        if animation_data and animation_data.action:
            deleted_count += remove_static_fcurves(
                iter_animdata_fcurve_collections(animation_data),
                tolerance,
            )

    return deleted_count


def cleanup_scene_actions(context: bpy.types.Context, tolerance: float) -> int:
    deleted_count = 0

    for action in bpy.data.actions:
        deleted_count += remove_static_fcurves(
            iter_action_fcurve_collections(action),
            tolerance,
        )

    return deleted_count


def cleanup_selected_armature_bones(context: bpy.types.Context, tolerance: float) -> int:
    deleted_count = 0
    
    armature = context.active_object
    if not armature or armature.type != 'ARMATURE':
        return 0
    
    selected_bone_names = {bone.name for bone in context.selected_pose_bones} if context.selected_pose_bones else set()
    if not selected_bone_names:
        return 0
    
    animation_data = armature.animation_data
    if not animation_data or not animation_data.action:
        return 0

    def belongs_to_selected_bone(curve: bpy.types.FCurve) -> bool:
        data_path = curve.data_path
        if not data_path.startswith('pose.bones["'):
            return False

        try:
            bone_name = data_path.split('"', 2)[1]
        except IndexError:
            return False

        return bone_name in selected_bone_names

    return remove_static_fcurves(
        iter_animdata_fcurve_collections(animation_data),
        tolerance,
        belongs_to_selected_bone,
    )


class ANIM_OT_delete_static_channels(bpy.types.Operator):
    bl_idname = "animation.delete_static_fcurves"
    bl_label = "Delete Static Channels"
    bl_description = "Remove F-Curves where all keyframe values are constant (within tolerance)"
    bl_options = {'REGISTER', 'UNDO'}
    
    # User-configurable properties
    tolerance: bpy.props.FloatProperty(
        name="Tolerance",
        description="Maximum allowed deviation for values to be considered equal (epsilon)",
        default=1e-6,
        min=0.0,
        max=1.0,
        precision=8,
    )
    
    scope: bpy.props.EnumProperty(
        name="Scope",
        description="Target scope for static channel cleanup",
        items=[
            ('SELECTED_OBJECTS', "Selected Objects", "Clean up F-Curves from currently selected objects"),
            ('SCENE_ACTIONS', "All Scene Actions", "Clean up F-Curves from all actions in the scene"),
            ('SELECTED_BONES', "Selected Armature Bones", "Clean up F-Curves from selected bones in active armature"),
        ],
        default='SELECTED_OBJECTS',
    )
    
    report_status: bpy.props.BoolProperty(
        name="Report Results",
        description="Display the number of deleted F-Curves",
        default=True,
    )
    
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if not context.scene:
            return False
        
        has_selected = len(context.selected_objects) > 0
        has_actions = len(bpy.data.actions) > 0
        
        return has_selected or has_actions
    
    def execute(self, context: bpy.types.Context) -> set:
        deleted_count = 0
        
        if self.scope == 'SELECTED_OBJECTS':
            deleted_count = cleanup_selected_objects(context, self.tolerance)
            
        elif self.scope == 'SCENE_ACTIONS':
            deleted_count = cleanup_scene_actions(context, self.tolerance)
            
        elif self.scope == 'SELECTED_BONES':
            deleted_count = cleanup_selected_armature_bones(context, self.tolerance)
        
        # Provide user feedback
        if self.report_status:
            self.report({'INFO'}, f"Deleted {deleted_count} static F-Curves")
        
        return {'FINISHED'}


def menu_func_delete_static(self, context: bpy.types.Context) -> None:
    self.layout.operator(
        ANIM_OT_delete_static_channels.bl_idname,
        text="Delete Static Channels"
    )


classes = (
    ANIM_OT_delete_static_channels,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.GRAPH_MT_key.append(menu_func_delete_static)
    bpy.types.DOPESHEET_MT_key.append(menu_func_delete_static)


def unregister():
    bpy.types.GRAPH_MT_key.remove(menu_func_delete_static)
    bpy.types.DOPESHEET_MT_key.remove(menu_func_delete_static)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
