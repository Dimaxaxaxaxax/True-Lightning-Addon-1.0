bl_info = {
    "name": "True Procedural Lightning",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "category": "Object",
    "location": "View3D > Sidebar > Lightning",
    "author": "Дима",
    "description": "Creation of lightning with animation",
}
###############
### IMPORTS ###
###############

import bpy
import math
import random
from bpy.props import BoolProperty, FloatProperty, IntProperty, PointerProperty, EnumProperty
from bpy.types import Operator, Panel, PropertyGroup

################################
### POINT MANAGING FUNCTIONS ###
################################

#Seting up sky and ground point depending on their type and their relationship
def pick_sky_and_ground(sky, ground, sky_mode, ground_mode, sky_allowness, ground_allowness):
    #Point-to-Point
    if sky_mode == "POINT" and ground_mode == "POINT":
        sky = sky
        ground = ground
    #Point-to-Object
    elif sky_mode == "POINT" and ground_mode != "POINT":
        ground_allowness = ground_allowness if ground_allowness <= len(ground) else len(ground)
        ground = find_nearest_points_in_array(ground, sky, ground_allowness)[random.randint(0, ground_allowness-1)]
    #Object-to-Object
    elif sky_mode != "POINT" and ground_mode == "POINT":
        sky_allowness = sky_allowness if sky_allowness <= len(sky) else len(sky)
        sky = find_nearest_points_in_array(sky, ground, sky_allowness)[random.randint(0, sky_allowness-1)]
    #Object-to-Object
    else:
        pairs = find_nearest_pairs_in_arrays(sky, ground, sky_allowness, ground_allowness)
        print (len(pairs))
        rand_i = random.randint(0, len(pairs)-1)
        sky = pairs[rand_i][0]
        ground = pairs[rand_i][1]
    return [sky, ground]
  
#Find n points in array, nearest to some point and choose one of them
def find_nearest_points_in_array(source, target, count):
    if count >= len(source):
        return source
    res = [None] * count
    fpi = 0                 #a.k.a. farest point index
    for point in source:
        for i in range(count):
            if res[i] == None:
                fpi = i
                break
            elif math.dist(res[i], target) > math.dist(res[fpi], target):
                fpi = i
        if res[fpi] == None or math.dist(res[fpi], target) > math.dist(point, target):
            res[fpi] = point
    return res
    
#Find n shortest pairs of two points from two separate arrays
def find_nearest_pairs_in_arrays(arr1, arr2, count1, count2):
    #Limitation of final array
    count1 = count1 if count1 < len(arr1) else len(arr1)
    count2 = count2 if count2 < len(arr2) else len(arr2)
    count = count1*count2
    #
    all_count = len(arr1)*len(arr2)
    res = []
    all_pairs = []
    left_set = []
    right_set = []
    flag = True
    #
    for p1 in arr1:
        for p2 in arr2:   
           all_pairs.append([p1,p2])      
    all_pairs.sort(key=lambda p: math.dist(p[0], p[1]))
    #
    for l, r in all_pairs:
        new_left = l not in left_set
        new_right = r not in right_set
        if len(left_set) >= count1 and len(right_set) >= count2 and len(res) >= count1*count2:
            break
        
        elif ((new_left and len(left_set) < count1 and new_right and len(right_set) < count2)
        or (new_left and len(left_set) < count1 and not new_right)
        or (not new_left and new_right and len(right_set) < count2)
        or (not new_left and not new_right)
        ):
            res.append((l, r))
            if new_left:
                left_set.append(l)
            if new_right:
                right_set.append(r)
    return res

#Get all point coordinates from some object or mesh or from entire scene
def get_all_points(target, exception = None):
    if target != bpy.context.scene.objects:
        target = [target]
    points = []
    for obj in target:
        #if regular mesh obj and not exception
        if isinstance(obj, bpy.types.Object) and obj.type == "MESH" and obj != exception:
            mesh = obj.data
            for vert in mesh.vertices:
                points.append(obj.matrix_world @ vert.co)
        #if anything else
        elif isinstance(obj, bpy.types.Object) and target != bpy.context.scene.objects:
            points.append(obj.location)                
    return points

#Find random direction to the point nearest to "to" point in the area of "fr" point
def random_nearest_direction(fr, to, allowness, size):
    dirs = []

    for _ in range(100):
        x = fr[0] + random.uniform(-size,size)
        y = fr[1] + random.uniform(-size,size)
        z = fr[2] + random.uniform(-size,size)
        new_point = [x,y,z]
        if new_point != fr:
            dirs.append(new_point)
    dirs.sort(key=lambda p: math.dist(p, to))
    k = min(allowness+1, len(dirs))
    dir = random.choice(dirs[:k])
    dir = [
        dir[0] - fr[0],
        dir[1] - fr[1],
        dir[2] - fr[2]
    ]
    return dir

################################
### CURVE CREATING FUNCTIONS ###
################################

#Create curve with only one point
def create_single_point_curve(name, position):
    curve_data = bpy.data.curves.new(name, type="CURVE")
    curve_data.dimensions = '3D'
    polyline = curve_data.splines.new('POLY')
    point = (position[0],position[1],position[2],1)
    polyline.points[0].co = point
    curve_obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(curve_obj)
    return curve_obj

#create lightning-like curve from "sky" to "ground"
def create_lightning(sky, ground, spread, step, thickness, resolution, is_mesh):
    is_connected = False
    #Creating a curve with a single point spline
    curve_obj = create_single_point_curve("Lightning", sky)   
    bpy.context.view_layer.objects.active = curve_obj
    bpy.ops.object.mode_set(mode='EDIT') 
    curve = curve_obj.data
    curve.splines.new('POLY')
    sky_spline = curve.splines[0]
    ground_spline = curve.splines[1]
    ###
    ground_spline.points.add(0)
    ground_spline.points[0].co = [ground[0], ground[1], ground[2],1]
    ###
    i = 0
    j = 0
    #Branching cycle
    while not is_connected:
        bpy.ops.curve.select_all(action='DESELECT')
        sk = sky_spline.points[i]
        gr = ground_spline.points[j]
        sk.select = True
        skcords = [sk.co.xyz.x, sk.co.xyz.y, sk.co.xyz.z]
        grcords = [gr.co.xyz.x, gr.co.xyz.y, gr.co.xyz.z]
        dir = random_nearest_direction (skcords, grcords, spread, step)
        bpy.ops.curve.extrude_move(
            TRANSFORM_OT_translate={"value": dir})
        i+=1    
        #Launching the oncoming branch when the main one is close to the ground
        if math.dist(skcords, grcords) < step*5:
            bpy.ops.curve.select_all(action='DESELECT')
            gr = ground_spline.points[j]
            gr.select = True
            sk = sky_spline.points[i]
            grcords = [gr.co.xyz.x, gr.co.xyz.y, gr.co.xyz.z]
            skcords = [sk.co.xyz.x, sk.co.xyz.y, sk.co.xyz.z]
            dir = random_nearest_direction (grcords, skcords, spread, step)
            bpy.ops.curve.extrude_move(
            TRANSFORM_OT_translate={"value": dir})   
            j+=1   
        #Connecting branches when they are too close
        gr = ground_spline.points[j]
        grcords = [gr.co.xyz.x, gr.co.xyz.y, gr.co.xyz.z]
        if math.dist(skcords, grcords) < step:
            bpy.ops.curve.select_all(action='DESELECT')
            sk = sky_spline.points[i]
            gr = ground_spline.points[j]
            sk.select = True
            gr.select = True
            bpy.ops.curve.make_segment()
            is_connected = True 
    #Fin
    bpy.ops.object.mode_set(mode='OBJECT') 
    curve.bevel_depth = thickness
    curve.bevel_resolution = resolution
    curve.use_fill_caps = True
    if is_mesh:
        bpy.ops.object.select_all(action='DESELECT')
        curve_obj.select_set(True)
        bpy.context.view_layer.objects.active = curve_obj
        bpy.ops.object.convert(target = "MESH")
        bpy.ops.object.select_all(action='DESELECT')
    return curve

##################################
### MATERIAL CREATING FUNCTION ###
##################################

#Create speific material
def create_material(frame, duration, brightness, color, strikes):
    #Сreating and set-up material
    mat = bpy.data.materials.new(name="LightningMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.remove(nodes.get("Principled BSDF"))
    emis = nodes.new("ShaderNodeEmission")
    output = nodes.get("Material Output")
    links.new(
        emis.outputs[0],
        output.inputs[0]
    )
    emis.inputs[0].default_value = color
    emis.inputs[1].default_value = 0
    #Creating keyframes
    dif = (int)(duration/10) if duration >= 10 else 1
    strike_frame = frame
    start_frame = frame-dif if duration >= 10 else frame-1
    end_frame = start_frame+duration if duration >= 3 else frame+1
    #Duration keys
    bpy.context.scene.frame_set(start_frame)
    emis.inputs[1].keyframe_insert("default_value")
    bpy.context.scene.frame_set(end_frame)
    emis.inputs[1].keyframe_insert("default_value")
    bpy.context.scene.frame_set(strike_frame)
    emis.inputs[1].default_value = brightness
    emis.inputs[1].keyframe_insert("default_value")
    
    if end_frame > strike_frame:
        bright_frame = strike_frame

    for _ in range(strikes-1):
        fade_frame = bright_frame + dif
        bright_frame = fade_frame + dif
        if bright_frame >= end_frame:
            break
        bpy.context.scene.frame_set(fade_frame)
        emis.inputs[1].default_value = random.uniform(0.1,0.5)
        emis.inputs[1].keyframe_insert("default_value")
        
        bpy.context.scene.frame_set(bright_frame)
        emis.inputs[1].default_value = brightness
        emis.inputs[1].keyframe_insert("default_value")
        
    return mat

##################################
### GEONODE MANAGING FUNCTIONS ###
##################################


#Made with Node to Python Addon
#Creates addon, that make lightning's geometry dissapears, when it needs
def create_geonode():
    """Initialize Lightning Disappearance node group"""
    lightning_disappearance = bpy.data.node_groups.new(type='GeometryNodeTree', name="Lightning Disappearance")
    #
    lightning_disappearance.color_tag = 'NONE'
    lightning_disappearance.description = ""
    lightning_disappearance.default_group_node_width = 140
    lightning_disappearance.is_modifier = True
    lightning_disappearance.show_modifier_manage_panel = True
    
    # lightning_disappearance interface
    # Socket Geometry
    geometry_socket = lightning_disappearance.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'
    geometry_socket.default_input = 'VALUE'
    geometry_socket.structure_type = 'AUTO'
    # Socket Geometry
    geometry_socket_1 = lightning_disappearance.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'
    geometry_socket_1.default_input = 'VALUE'
    geometry_socket_1.structure_type = 'AUTO'
    # Socket Start
    start_socket = lightning_disappearance.interface.new_socket(name="Start", in_out='INPUT', socket_type='NodeSocketInt')
    start_socket.default_value = 0
    start_socket.min_value = -2147483648
    start_socket.max_value = 2147483647
    start_socket.subtype = 'NONE'
    start_socket.attribute_domain = 'POINT'
    start_socket.default_input = 'VALUE'
    start_socket.structure_type = 'AUTO'
    # Socket End
    end_socket = lightning_disappearance.interface.new_socket(name="End", in_out='INPUT', socket_type='NodeSocketInt')
    end_socket.default_value = 0
    end_socket.min_value = -2147483648
    end_socket.max_value = 2147483647
    end_socket.subtype = 'NONE'
    end_socket.attribute_domain = 'POINT'
    end_socket.default_input = 'VALUE'
    end_socket.structure_type = 'AUTO'

    # Initialize lightning_disappearance nodes
    # Node Group Input
    group_input = lightning_disappearance.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    # Node Group Output
    group_output = lightning_disappearance.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # Node Scene Time
    scene_time = lightning_disappearance.nodes.new("GeometryNodeInputSceneTime")
    scene_time.name = "Scene Time"
    scene_time.outputs[0].hide = True

    # Node Math
    math = lightning_disappearance.nodes.new("ShaderNodeMath")
    math.name = "Math"
    math.operation = 'GREATER_THAN'
    math.use_clamp = False

    # Node Delete Geometry
    delete_geometry = lightning_disappearance.nodes.new("GeometryNodeDeleteGeometry")
    delete_geometry.name = "Delete Geometry"
    delete_geometry.domain = 'POINT'
    delete_geometry.mode = 'ALL'

    # Node Boolean Math
    boolean_math = lightning_disappearance.nodes.new("FunctionNodeBooleanMath")
    boolean_math.name = "Boolean Math"
    boolean_math.operation = 'OR'

    # Node Math.001
    math_001 = lightning_disappearance.nodes.new("ShaderNodeMath")
    math_001.name = "Math.001"
    math_001.operation = 'GREATER_THAN'
    math_001.use_clamp = False

    # Node Integer Math
    integer_math = lightning_disappearance.nodes.new("FunctionNodeIntegerMath")
    integer_math.name = "Integer Math"
    integer_math.hide = True
    integer_math.operation = 'ADD'
    # Value_001
    integer_math.inputs[1].default_value = 1

    # Node Integer Math.001
    integer_math_001 = lightning_disappearance.nodes.new("FunctionNodeIntegerMath")
    integer_math_001.name = "Integer Math.001"
    integer_math_001.hide = True
    integer_math_001.operation = 'SUBTRACT'
    # Value_001
    integer_math_001.inputs[1].default_value = 1

    # Node Reroute
    reroute = lightning_disappearance.nodes.new("NodeReroute")
    reroute.name = "Reroute"
    reroute.socket_idname = "NodeSocketGeometry"
    # Node Frame
    frame = lightning_disappearance.nodes.new("NodeFrame")
    frame.label = "Area of Deletion"
    frame.name = "Frame"
    frame.label_size = 20
    frame.shrink = True

    # Set parents
    lightning_disappearance.nodes["Scene Time"].parent = lightning_disappearance.nodes["Frame"]
    lightning_disappearance.nodes["Math"].parent = lightning_disappearance.nodes["Frame"]
    lightning_disappearance.nodes["Boolean Math"].parent = lightning_disappearance.nodes["Frame"]
    lightning_disappearance.nodes["Math.001"].parent = lightning_disappearance.nodes["Frame"]
    lightning_disappearance.nodes["Integer Math"].parent = lightning_disappearance.nodes["Frame"]
    lightning_disappearance.nodes["Integer Math.001"].parent = lightning_disappearance.nodes["Frame"]

    # Set locations
    lightning_disappearance.nodes["Group Input"].location = (-722.7017211914062, -233.44180297851562)
    lightning_disappearance.nodes["Group Output"].location = (507.94134521484375, -39.03900146484375)
    lightning_disappearance.nodes["Scene Time"].location = (41.638031005859375, -202.81802368164062)
    lightning_disappearance.nodes["Math"].location = (243.82493591308594, -35.970458984375)
    lightning_disappearance.nodes["Delete Geometry"].location = (281.90167236328125, 10.990325927734375)
    lightning_disappearance.nodes["Boolean Math"].location = (476.00714111328125, -73.52445983886719)
    lightning_disappearance.nodes["Math.001"].location = (243.10719299316406, -202.30313110351562)
    lightning_disappearance.nodes["Integer Math"].location = (36.878173828125, -114.58709716796875)
    lightning_disappearance.nodes["Integer Math.001"].location = (29.51654052734375, -351.409423828125)
    lightning_disappearance.nodes["Reroute"].location = (-507.4955139160156, -72.01289367675781)
    lightning_disappearance.nodes["Frame"].location = (-480.0, -100.0)

    # Set dimensions
    lightning_disappearance.nodes["Group Input"].width  = 140.0
    lightning_disappearance.nodes["Group Input"].height = 100.0

    lightning_disappearance.nodes["Group Output"].width  = 140.0
    lightning_disappearance.nodes["Group Output"].height = 100.0

    lightning_disappearance.nodes["Scene Time"].width  = 140.0
    lightning_disappearance.nodes["Scene Time"].height = 100.0

    lightning_disappearance.nodes["Math"].width  = 140.0
    lightning_disappearance.nodes["Math"].height = 100.0

    lightning_disappearance.nodes["Delete Geometry"].width  = 140.0
    lightning_disappearance.nodes["Delete Geometry"].height = 100.0

    lightning_disappearance.nodes["Boolean Math"].width  = 140.0
    lightning_disappearance.nodes["Boolean Math"].height = 100.0

    lightning_disappearance.nodes["Math.001"].width  = 140.0
    lightning_disappearance.nodes["Math.001"].height = 100.0

    lightning_disappearance.nodes["Integer Math"].width  = 140.0
    lightning_disappearance.nodes["Integer Math"].height = 100.0

    lightning_disappearance.nodes["Integer Math.001"].width  = 140.0
    lightning_disappearance.nodes["Integer Math.001"].height = 100.0

    lightning_disappearance.nodes["Reroute"].width  = 10.0
    lightning_disappearance.nodes["Reroute"].height = 100.0

    lightning_disappearance.nodes["Frame"].width  = 646.0
    lightning_disappearance.nodes["Frame"].height = 405.0

    # Initialize lightning_disappearance links
    # boolean_math.Boolean -> delete_geometry.Selection
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Boolean Math"].outputs[0],
        lightning_disappearance.nodes["Delete Geometry"].inputs[1]
    )
    # math.Value -> boolean_math.Boolean
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Math"].outputs[0],
        lightning_disappearance.nodes["Boolean Math"].inputs[0]
    )
    # integer_math_001.Value -> math_001.Value
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Integer Math.001"].outputs[0],
        lightning_disappearance.nodes["Math.001"].inputs[1]
    )
    # math_001.Value -> boolean_math.Boolean
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Math.001"].outputs[0],
        lightning_disappearance.nodes["Boolean Math"].inputs[1]
    )
    # group_input.Start -> integer_math.Value
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Group Input"].outputs[1],
        lightning_disappearance.nodes["Integer Math"].inputs[0]
    )
    # group_input.End -> integer_math_001.Value
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Group Input"].outputs[2],
        lightning_disappearance.nodes["Integer Math.001"].inputs[0]
    )
    # scene_time.Frame -> math_001.Value
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Scene Time"].outputs[1],
        lightning_disappearance.nodes["Math.001"].inputs[0]
    )
    # scene_time.Frame -> math.Value
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Scene Time"].outputs[1],
        lightning_disappearance.nodes["Math"].inputs[1]
    )
    # integer_math.Value -> math.Value
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Integer Math"].outputs[0],
        lightning_disappearance.nodes["Math"].inputs[0]
    )
    # group_input.Geometry -> reroute.Input
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Group Input"].outputs[0],
        lightning_disappearance.nodes["Reroute"].inputs[0]
    )
    # reroute.Output -> delete_geometry.Geometry
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Reroute"].outputs[0],
        lightning_disappearance.nodes["Delete Geometry"].inputs[0]
    )
    # delete_geometry.Geometry -> group_output.Geometry
    lightning_disappearance.links.new(
        lightning_disappearance.nodes["Delete Geometry"].outputs[0],
        lightning_disappearance.nodes["Group Output"].inputs[0]
    )
    return lightning_disappearance

#Create dissappearing geonode, if it doesn't exists, and apply it
def apply_geonode(lightning_obj, start, end):
    mod = lightning_obj.modifiers.get("Lightning Disappearance")
    
    if mod is None:
        mod = lightning_obj.modifiers.new(
            name="Lightning Disappearance",
            type='NODES'
        )
    geo_tree = bpy.data.node_groups.get("Lightning Disappearance")
    if (geo_tree == None):
        create_geonode()
        geo_tree = bpy.data.node_groups.get("Lightning Disappearance")
    mod.node_group = geo_tree
    mod["Socket_2"] = start
    mod["Socket_3"] = end

#######################################
### UI CLASSES, FUNCTIONS AND PROPS ###
#######################################

#Points Props for draw
def point_settings(layout, point_mode, point_type, props):
    if (point_type == "POINT" and point_mode == "SKY"):
        sky_col = layout.column(align=True)
        sky_col.label(text="Sky:")
        sky_col.prop(props, "sky_x", text = "X")
        sky_col.prop(props, "sky_y", text = "Y")
        sky_col.prop(props, "sky_z", text = "Z")        
    elif (point_type=="OBJECT" and point_mode == "SKY"):
        sky_col = layout.column(align=True)
        sky_col.label(text = "Sky")
        sky_col.prop(props, "sky_object")
        sky_col.prop(props, "sky_allowness", text = "Allowness")         
    if (point_type=="POINT" and point_mode == "GROUND"):
        ground_col = layout.column(align=True)
        ground_col.label(text="Ground:")
        ground_col.prop(props, "ground_x", text = "X")
        ground_col.prop(props, "ground_y", text = "Y")
        ground_col.prop(props, "ground_z", text = "Z")      
    elif (point_type=="OBJECT" and point_mode == "GROUND"):
        ground_col = layout.column(align=True)
        ground_col.label(text = "Ground")
        ground_col.prop(props, "ground_object")
        ground_col.prop(props, "ground_allowness", text = "Allowness")    
    elif (point_type=="NEAREST_OBJECT" and point_mode == "GROUND"):
        ground_col = layout.column(align=True)
        ground_col.label(text="Ground:")
        ground_col.prop(props, "ground_allowness", text = "Allowness") 

#Panel
class TL_PT_Main(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Create a Lightning"
    bl_category = "True Lightning"
    
    def draw (self, context):
        scene = context.scene
        props = scene.lightning
        l = self.layout        
    #Choosing points types
        if (props.panel_mode == 1):
            l.label(text = "Choose creation mode:")
            l.prop(props, "sky_type", text="Sky")
            l.prop(props, "ground_type", text="Ground")
            l.operator("lightning.continue", text = "Continue")
    #Setting up points
        elif (props.panel_mode == 2):
            l.label(text="Set up sky and ground:")
            point_settings(l, "SKY", props.sky_type, props)
            point_settings(l, "GROUND", props.ground_type, props)
            row_nav = l.row()
            row_nav.operator("lightning.back", text = "Back")
            row_nav.operator("lightning.continue", text = "Continue")
    #Final settings
        elif (props.panel_mode == 3):
            col = l.column(align=True)
            col.label(text="Shape settings:")
            col.prop(props, "spread", text="Spread")
            col.prop(props, "step", text="Step")
            col.prop(props, "brightness", text="Brightness")
            col.prop(props, "color", text="Color")
            col.separator()
            col.label(text="Timeline settings:")
            col.prop(props, "frame", text="Strike Frame")
            col.prop(props, "duration", text="Duration")
            col.prop(props, "count_of_strikes", text="Count Of Strikes")
            col.separator()
            col.label(text="Curve settings:")
            col.prop(props, "curve_resolution", text="Resolution")
            col.prop(props, "curve_thickness", text="Thickness")
            col.prop(props, "is_mesh", text="Convert to Mesh")
            row_nav = l.row()
            row_nav.operator("lightning.back", text = "Back")
            row_nav.operator("lightning.create", text = "Create")
    #Postcriptum
        elif (props.panel_mode == 4):
            l.label(text="Lightning Created!")
            row_nav = l.row()
            row_nav.operator("lightning.back", text = "Back")
            row_nav.operator("lightning.return", text = "Return")
            row_nav.operator("lightning.create", text = "Recreate")
    #In any other case
        else:
            row_nav = l.row()
            row_nav.operator("lightning.return", text = "return")

#Navbar Operators:
#Back
class TL_OT_Back(Operator):
    bl_idname = "lightning.back"
    bl_label = "Back"
    bl_description = "Go on previos screen"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        props = context.scene.lightning
        props.panel_mode -= 1
        return {'FINISHED'}
#Continue
class TL_OT_Continue(Operator):
    bl_idname = "lightning.continue"
    bl_label = "Continue"
    bl_description = "Go forward"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        #check if objects are legit
        props = context.scene.lightning
        if props.panel_mode == 2 and props.sky_type == "OBJECT" and props.sky_object == None:
            self.report({'ERROR'}, "Sky object doesn't exists!")
            return {'CANCELLED'}
        if props.panel_mode == 2 and props.ground_type == "OBJECT" and props.ground_object == None:
            self.report({'ERROR'}, "Ground object doesn't exists!")
            return {'CANCELLED'}
        #
        props.panel_mode += 1
        return {'FINISHED'} 
#Return (to the start)
class TL_OT_Return(Operator):
    bl_idname = "lightning.return"
    bl_label = "Return"
    bl_description = "Go to the start"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        props = context.scene.lightning
        props.panel_mode = 1
        return {'FINISHED'}
#Create Lightning
class TL_OT_CreateLightning(Operator):
    bl_idname = "lightning.create"
    bl_label = "Create"
    bl_description = "Create Lightning"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        props = context.scene.lightning
    #Points normalization
        #sky
        if props.sky_type == "POINT":
            sky = [props.sky_x, props.sky_y, props.sky_z]
        else:     
            if props.sky_type == "OBJECT":
                source = props.sky_object
            sky = get_all_points(source)
            
            if sky ==  None:
                return {'CANCELLED'}
        #ground
        exception = None
        if props.ground_type == "POINT":
            ground = [props.ground_x, props.ground_y, props.ground_z]
        else:     
            source = props.ground_object
            if props.ground_type == "NEAREST_OBJECT":
                source = bpy.context.scene.objects
                if props.sky_type == "OBJECT":
                    exception = props.sky_object
            ground = get_all_points(source, exception)
            if ground ==  None:
                return {'CANCELLED'}
        #
        pair = pick_sky_and_ground(sky, ground, props.sky_type, props.ground_type, 
        props.sky_allowness, props.ground_allowness)
        sky = pair[0]
        ground = pair[1]
        spread = props.spread
        step = props.step
        thickness = props.curve_thickness
        resolution = props.curve_resolution
        is_mesh = props.is_mesh
        
    #Lightning creation
        #create mesh
        lightning = create_lightning(sky, ground, spread, step, thickness, resolution, is_mesh)
        #
        frame = props.frame
        duration = props.duration
        brightness = props.brightness
        color = props.color
        count_of_strikes = props.count_of_strikes
        #create and set up materal       
        material = create_material(frame, duration, brightness, color, count_of_strikes)
        lightning.materials.append(material)
        lightning_obj = bpy.context.active_object
        #
        dif = (int)(duration/10) if duration >= 10 else 1
        start_frame = frame-dif if duration >= 10 else frame-1
        end_frame = start_frame+duration if duration >= 3 else frame+1
        #create (if it needs) and apply geonode_group
        apply_geonode(lightning_obj, start_frame, end_frame)
        #
        props.panel_mode += 1
        return {'FINISHED'}
    
#Properties
class LT_PT_Properties(bpy.types.PropertyGroup):
    #Enums
    sky_types = [
    ("POINT", "Point", "XYZ point in scene"),
    #("SKY_MESH", "Mesh", "Nearest point on some mesh"),
    ("OBJECT", "Object", "Nearest point on some object"),
    ]
    ground_types = [
    ("POINT", "Point", "XYZ point in scene"),
    #("GROUND_MESH", "Mesh", "Nearest point on some mesh"),
    ("OBJECT", "Object", "Nearest point on some object"),
    ("NEAREST_OBJECT", "Nearest Object", "Point on object nearest to the point"),
    ]
    #Panel condition
    panel_mode : IntProperty(
        name = "Scene panel condition",
        description = "",
        default = 1,
        min = 1,
        max = 4
    )
    #Final settings
    frame : IntProperty(
        name = "Strike Frame",
        description = "Frame when lightning strikes",
        default = 1
    )
    duration : IntProperty(
        name = "Duration",
        description = "Duration of the first strike (when lightning is glowing)",
        default = 10,
        min = 1
    )
    count_of_strikes : IntProperty(
        name = "Count of strikes",
        description = "Count of strikes",
        default = 1,
        min = 1
    )
    step : FloatProperty(
        name = "Step",
        description = "Size of every step",
        default = 1,
        subtype='DISTANCE',
        step = 0.01,
        precision = 6
    )
    spread : IntProperty(
        name = "Spread",
        description = "How lightning will spead",
        min = 0,
        max = 100,
        default = 1
    )
    brightness : FloatProperty(
        name = "Brightness",
        description = "Brightness of lightning in moment of strike",
        default = 10000,
        max = 1000000000
    )
    color: bpy.props.FloatVectorProperty(
        name = "Color",
        subtype = 'COLOR',
        size = 4,
        min = 0.0,
        max = 1.0,
        default = (1.0, 1.0, 1.0, 1.0)
    )
    curve_resolution: IntProperty(
        name = "Curve Resolution",
        description = "Resolution of curve in these bevel option",
        min = 4,
        max = 100,
        default = 1
    )
    curve_thickness: FloatProperty(
        name = "Brightness",
        description = "Thickness of curve in these bevel option",
        default = 0.02,
        step = 1,
        min = 0
    )
    is_mesh : BoolProperty(
        name = "Convert to Mesh",
        description = "Convert to Mesh",
        default = False
    )
    #Sky and Ground type
    sky_type : EnumProperty(
        name = "Sky Point",
        description = "First point of lightning (sky)",
        items = sky_types,
        default = "POINT"
    )
    ground_type : EnumProperty(
        name = "Ground Point",
        description = "Last point of lightning (ground)",
        items = ground_types,
        default = "POINT"
    )
    #Sky and Ground settings
    sky_x : FloatProperty(
        name = "Sky X",
        description = "Sky Point X coordinate",
        default = 0,
        subtype='DISTANCE',
        unit='LENGTH',
        step = 0.1,
        precision = 6
    ) 
    sky_y : FloatProperty(
        name = "Sky Y",
        description = "Sky Point Y coordinate",
        default = 0,
        subtype='DISTANCE',
        unit='LENGTH',
        step = 0.1,
        precision = 6
    )
    sky_z : FloatProperty(
        name = "Sky Z",
        description = "Sky Point Z coordinate",
        default = 0,
        subtype='DISTANCE',
        unit='LENGTH',
        step = 0.1,
        precision = 6
    )
    ground_x : FloatProperty(
        name = "Ground X",
        description = "Ground Point X coordinate",
        default = 0,
        subtype='DISTANCE',
        unit='LENGTH',
        step = 0.1,
        precision = 6
    ) 
    ground_y : FloatProperty(
        name = "Ground Y",
        description = "Ground Point Y coordinate",
        default = 0,
        subtype='DISTANCE',
        unit='LENGTH',
        step = 0.1,
        precision = 6
    )
    ground_z : FloatProperty(
        name = "Ground Z",
        description = "Ground Point Z coordinate",
        default = 0,
        subtype='DISTANCE',
        unit='LENGTH',
        step = 0.1,
        precision = 6
    )
    sky_object : PointerProperty(
        name = "",
        description = "Sky Object",
        type = bpy.types.Object
    )
    ground_object : PointerProperty(
        name = "",
        description = "Ground Object",
        type = bpy.types.Object
    )
    sky_allowness : IntProperty(
        name = "Allownes",
        description = "Count of vertices, that could be strike points",
        default = 1,
        min = 1
    )
    ground_allowness : IntProperty(
        name = "Allownes",
        description = "Count of vertices, that could be strike points",
        default = 1,
        min = 1
    )
    
################
### REGISTER ###
################

#classes
classes = [
    TL_PT_Main,
    LT_PT_Properties,
    TL_OT_Back,
    TL_OT_Continue,
    TL_OT_CreateLightning,
    TL_OT_Return
]

#register
def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.lightning = PointerProperty(type = LT_PT_Properties)
    
#unregister
def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.lightning    
    
###
if __name__ == "__main__":
    register()  
    
#     :3