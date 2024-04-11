import sys
import logging
LIB_PATH = comp.MapPath("TestDir:/Scripts/Lib")
if LIB_PATH not in sys.path:
    sys.path.append(LIB_PATH)
from ajc.fusion.flow import organize_table
from ajc.fusion.util import get_selected_tools
from ajc.fusion.auto import *
logger = logging.getLogger('proj.prep')

def basic_char_prep_layer(comp, loader):

    chain = NodeChain(comp, loader)
    base_name = get_tool_name(loader)

    #Rename Gui
    options = {1: {1:"rename","Name":"ReName Node",2:"Text","ReadOnly":False, "Default":base_name},
              2: {1:"float16","Name":"Float 16",2:"Checkbox","Default":1},
              3: {1:"p3gammut", "Name":"P3 Gammut",2:"Checkbox","Default":1}
    }
    dialog = comp.AskUser("AJC Wireless", options)

    if dialog is None :
        print("Wireless Canceled")
    else:
        #Use original node name if rename is left blank
        if dialog["rename"] == "":
            base_name = get_tool_name(loader)
            print(base_name)
        else:
            base_name = dialog["rename"]
            print(dialog["rename"])

        # Depth node
        if dialog["float16"] == 1:
            node = chain.add_next_node('ChangeDepth', name='CD_Float16'.format(
            base_name), values=dict(Depth=DEPTH_FLOAT16))
            set_tool_pos(comp, node, chain.x, chain.y+1)


        # Gamut node
        if dialog["p3gammut"] == 1:
            node = chain.add_next_node('GamutConvert', name='GmtToP3'.format(base_name), values=dict(PreDividePostMultiply=1, SourceSpace='sRGB', OutputSpace='Custom',
                                        RemoveGamma=1, AddGamma=0, CustomOutputRed=P3_RED, CustomOutputGreen=P3_GREEN, CustomOutputBlue=P3_BLUE, CustomOutputWhite=D65))
            set_tool_pos(comp, node, chain.x, chain.y+1)
    
        # Wireless Out
        node = chain.add_next_node('AutoDomain', name='{}_OUT'.format(base_name))
        node.TileColor = {'R' : 0/255, 'G' : 50/255, 'B' : 255/255}
        set_tool_pos(comp, node, chain.x, chain.y+2)

        node = make_wi(comp, node)
        set_tool_name(node, 'IN_{}'.format(base_name))
        node.TileColor = {'R' : 0/255, 'G' : 50/255, 'B' : 255/255}
        set_tool_pos(comp, node, chain.x, chain.y+3)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    comp.StartUndo('Prep Character Import')
    tools = get_selected_tools(comp)
    organize_table(comp, tools, cols=100)
    for tool in tools:
        basic_char_prep_layer(comp, tool)
    comp.EndUndo()
