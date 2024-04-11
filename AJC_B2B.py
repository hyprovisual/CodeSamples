import os
import sys
import logging
LIB_PATH = comp.MapPath("DirData:/Scripts/Lib")
if LIB_PATH not in sys.path:
    sys.path.append(LIB_PATH)
from ajc.fusion.flow import organize_table
from ajc.fusion.util import *
from ajc.fusion.uiwindow import error_window
logger = logging.getLogger('localDir.prep')

### Main Reference Doc:https://docs.chaos.com/display/VMAX/VRayBackToBeauty
### Refer to readme.txt for full description

def AJC_B2B(comp, tool):
    # Place selected exr file path into variable
    loaderExrPath = get_loader_filename(tool)
    
    # print(loaderExrPath) worlds
    flow = comp.CurrentFrame.FlowView
    
    # find latest B2B Template and places directory into variable
    #templates_dir = "\\\\serverDir\\Common\\Fusion\\Templates\\Project"    #Legacy serverDir Location
    templates_dir = "C:\\local\\FusionTemplates\\Fusion" #New location
    files = os.listdir(templates_dir)
    cleaned_files = [f for f in files if f.startswith('AJC_3D_B2B_Template')]
    season = len(cleaned_files)
    #ver = '_v00' + str(season) + '.setting' #Incriments latest version, but archiving old templates
    ver = '_v002.setting' #To strong-arm a specific file or version, replace this variable with the template's file name
    template_file = "AJC_3D_B2B_Template" + ver 
    print(template_file)
    filepath = os.path.join(templates_dir, template_file)

    # opens Template and Pastes noded into active doc
    comp_load = fu.LoadComp(filepath, True)
    tools = comp_load.GetToolList(False)
    flow = comp_load.CurrentFrame.FlowView
    globalIn = tool.GlobalIn[comp.CurrentTime]
    trimIn = tool.ClipTimeStart[comp.CurrentTime]

    #Cycle thruogh Nodes and replace loaders
    for tool in tools.values():
        flow.Select(tool)
        tool.Clip = (loaderExrPath)
        c = 1
        #turns off self illumation loader if pass is missing
        if tool.GetAttrs()["TOOLS_Name"] == "SelfIllumination":
            tool.SetAttrs({ "TOOLB_PassThrough" : True })
            sourceChannels = tool.Clip1.OpenEXRFormat.RedName.GetAttrs()["INPIDT_ComboControl_ID"].values()
            c = 0
            for channel in sourceChannels:
                if channel == "SelfIllumination.R":
                    tool.SetAttrs({ "TOOLB_PassThrough" : False })
                    c = 1
        #turns off self illumination's timespeed node
        if tool.GetAttrs()["TOOLS_Name"] == "Instance_TimeSpeed_SelfIllum":
            if c == 1:
                tool.SetAttrs({ "TOOLB_PassThrough" : False })   
            if c == 0:
                tool.SetAttrs({ "TOOLB_PassThrough" : True })       
        tool.GlobalIn = globalIn
        tool.ClipTimeStart = trimIn

        if tool.GetAttrs()["TOOLS_Name"] == "WindowRFL" or tool.GetAttrs()["TOOLS_Name"] == "TechPasses":
            tool.Depth = 4

    comp_load.Copy()
    flow.Select()
    comp_load.Close()
    comp.Paste()

     
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    ui = fu.UIManager
    disp = bmd.UIDispatcher(ui)
    comp = fusion.GetCurrentComp()
    comp.StartUndo('AJC_B2B')
    comp.Lock()

    tools = get_selected_tools(comp)

    for tool in tools:
        tool_type = get_tool_type(tool)
        x, y = comp.CurrentFrame.FlowView.GetPosTable(tool).values()
        if tool_type == "Loader":
            AJC_B2B(comp, tool)
            comp.CurrentFrame.FlowView.SetPos(tool, x - 6, y - 6)
        else:
            errorTxt = "Not supported: {}".format(tool_type)
            error_window(ui, disp, errorTxt)
            logger.warning("Not supported: {}".format(tool_type))

    comp.Unlock()
    comp.EndUndo()
    print('B2B Done')