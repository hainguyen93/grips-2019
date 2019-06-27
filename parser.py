# create a xml parser to extract the train timetable from the input dataset
# author(s): Hai

import xml.etree.ElementTree as ET

# input dataset (translated to ENGLISH)
ice_401_dir = "/home/optimi/bzfnguye/inputData/EN_GRIPS2019_401.xml"
ice_402_dir = "/home/optimi/bzfnguye/inputData/EN_GRIPS2019_402.xml"
ice_403_dir = "/home/optimi/bzfnguye/inputData/EN_GRIPS2019_403.xml"
ice_411_dir = "/home/optimi/bzfnguye/inputData/EN_GRIPS2019_411.xml"

# tree for each xml file
tree_401 = ET.parse(ice_401_dir)
tree_402 = ET.parse(ice_402_dir)
tree_403 = ET.parse(ice_403_dir)
tree_411 = ET.parse(ice_411_dir)

# root of xml files
root_401 = tree_401.getroot()
root_402 = tree_402.getroot()
root_403 = tree_403.getroot()
root_411 = tree_411.getroot()

print root_401.tag, root_401.attrib

for child in root_401:
    print child.tag, child.attrib
