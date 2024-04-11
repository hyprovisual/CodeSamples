import os
import math
import logging
import sys
import BlackmagicFusion as bmd

LIB_PATH = comp.MapPath("TestDir:/Scripts/Lib")
if LIB_PATH not in sys.path:
    sys.path.append(LIB_PATH)
from ajc.fusion.util import get_selected_tools
from ajc.fusion.photoshop import is_photoshop_loader
from ajc.fusion.uiwindow import ProcessDone
logger = logging.getLogger()

sys.path.append(os.path.join(os.environ["FUSIONPYTHON"], "Lib", 'site-packages'))
import psd_tools

##------------------------##

def layer_blend_mode_to_fusion(blend_mode):
    # Map PSD blend mode to Fusion blend mode
    apply_modes_mapping = {
        "normal": "Normal",
        "multiply": "Multiply",
        "screen": "Screen",
        "overlay": "Overlay",
        "darken": "Darken",
        "lighten": "Lighten",
        "color_dodge": "Color Dodge",
        "color_burn": "Color Burn",
        "soft_light": "Soft Light",
        "hard_light": "Hard Light",
        "linear_light": "Linear Light",
        "difference": "Difference",
        "exclusion": "Exclusion",
        "pass_through": "Normal"
        # Add more mappings as needed
    }
    return apply_modes_mapping.get(blend_mode.lower(), "Normal")


# ---- Extract Layers inside SubFolders ---- #
def get_folder_layers(folder):
    layers = []
    for layer in folder:
        if layer.is_group():
            layers.extend(get_folder_layers(layer)) # Recursive call for subfolders
            logger.warning("Subfolder detected, this will offset layer blendmodes")
        else:
            layers.append(layer)
    return layers


# ---- Extract Layers inside Folders ---- #
def get_layers_inside_psd(psd_path):
    print("Please wait a moment, Warning Unknown Image Resource 1092 is normal...")
    psd = psd_tools.PSDImage.open(psd_path)
    all_layers = []
    for layer in psd:
        if layer.is_group():
            all_layers.extend(get_folder_layers(layer))
        else:
            all_layers.append(layer)
    return all_layers


# ----- Create loader and merge for each PSD Layer ----- #
def psd_splitter(comp, tool):    
    tool.SaveSettings("PSDLayers.setting")
    localized = False
    psd_file = tool.GetAttrs()["TOOLST_Clip_Name"][1]
    if psd_file.startswith('Dir:'):
        old_Dir = 'Dir:'
        new_Dir = '\\\Dir'
        psd_path = psd_file.replace(old_Dir, new_Dir)
    elif psd_file.startswith('LocalDir:'):
        #-- Replace relative local path to absolute for PSD python library --#
        localized = True
        old_local = 'LocalDir:'
        new_local = fusion.MapPath("LocalDir:/")
        psd_path = psd_file.replace(old_local, new_local)
    else:
        psd_path = tool.GetAttrs()["TOOLST_Clip_Name"][1]
    
    print("Loading PSD File...")
    
    layers = get_layers_inside_psd(psd_path)
    layer_info = []
    lyr_name = []
    
    #----- Get PSD Layers Blend Mode and Opacity -----#
    for layer in layers:
        layer_name = layer.name
        lyr_name.append(layer_name)
        layer_opacity = layer.opacity / 255.0
        layer_blend_mode = layer_blend_mode_to_fusion(layer.blend_mode.name)
        layer_info.append((layer_opacity, layer_blend_mode))

    # ---- Set Variables ---- #
    flow = comp.CurrentFrame.FlowView
    org_x_pos, org_y_pos = flow.GetPosTable(tool).values()
    tool.Clip = psd_path
    channelList = tool.Clip1.PSDFormat.Layer.GetAttrs()["INPST_ComboControl_String"]
    keys = [k for k in channelList]
    c = 0  # -- used to sync PSD layers and fusion loaders/merges
    skip = 0
    mrg_amount = 0
    vers = tool.ClipTimeEnd[0]
    row = 0
    col = 0
    print("\n")
    
    # -- Revert local filepath to "LocalDir:" for Checkin Script -- #
    if localized:
        old_local = "LocalDir:"
        psd_path = psd_file.replace(new_local, old_local)
        tool.Clip = psd_path
        print(psd_path)

    # ----- Breakout Layers into Loaders ----- #
    for key in keys:
        name = channelList[key]
        #---- Filter out Placeholder Folder Layers ----#
        if name not in lyr_name:
            skip += 1
            continue
        else:         
            #Folder Fix
            if key > c:
               layer_info.append((0, "Normal"))
               """ This loop will allow the script to continue splitting psd files even with 
                nested groups, but blend modes will be offset and will need to be flattened 
                if blend modes are important to the comp artist """
            
            #Print layer info to Fusion Console
            print("{} : {}".format(name, layer_info[c][1]))  
           
            myloader = comp.Loader({"Clip" : psd_path})
            myloader.LoadSettings("PSDLayers.setting")
            myloader.SetAttrs({"TOOLB_NameSet": True, "TOOLS_Name": name})
            myloader.Clip1.PSDFormat.Layer = key - 1
            myloader.ClipTimeStart = vers
            myloader.Loop = 1
            if name.startswith('+_'): # -- Makes the PSD Lighting layers Violet
                myloader.TileColor = dict(R=0.584313725490196, G=0.294117647058824, B=0.803921568627451)

            # -- Variables for neatly stacking nodes -- #
            if row >= 8:
                row = 1
                col +=2
                x_pos = org_x_pos + col
                y_pos = org_y_pos + 1
            
            if row == 0:
                x_pos = org_x_pos
                y_pos = org_y_pos
            flow.SetPos(myloader, x_pos, y_pos + 1)
            x_pos, y_pos = flow.GetPosTable(myloader).values()
            

            # -- Create Merge node and set PSD layer attributes -- #
            if mrg_amount == 0:
                last_merge = myloader
            if mrg_amount > 0:
                mymerge = comp.Merge({"Background": last_merge, "Foreground": myloader})
                mymerge.SetAttrs({"TOOLB_NameSet": True, "TOOLS_Name": layer_info[c][1]})
                mymerge["ApplyMode"] = layer_info[c][1]
                mymerge.Blend = layer_info[c][0]
                flow.SetPos(mymerge, x_pos + 1, y_pos)
                last_merge = mymerge

            # -- Increment Vars to cycle stacking and layers blend modes -- #       
            c += 1
            row += 1
            mrg_amount += 1

#----- Main Loop -----#
if __name__ == "__main__":
    # Use Fusion's file dialog to select the PSD file
    ui = fu.UIManager
    disp = bmd.UIDispatcher(ui)
    script_Name = "PSD Splitter"
    comp = fusion.GetCurrentComp()
    print("Attempting to split PSD from selected tools.")
    ui = fu.UIManager
    disp = bmd.UIDispatcher(ui)

    comp.StartUndo('Starting Split PSD')
    comp.Lock()
    
    try:
        for tool in get_selected_tools(comp, "Loader"):
            vers = tool.ClipTimeEnd[0]
            tool.ClipTimeStart = vers #set psd to latest version
            tool.Loop = 1
            tool.GlobalIn = 1
            tool.GlobalOut = 1
            OriginalPath = tool.GetAttrs()["TOOLST_Clip_Name"][1]
            if is_photoshop_loader(tool):
                psd_splitter(comp, tool)
            else:
                print("No PSD file selected.")
            
    finally:
        comp.Unlock()
        comp.EndUndo(True) 
    print("Done Splitting PSD")
    ProcessDone(ui, disp, script_Name)
