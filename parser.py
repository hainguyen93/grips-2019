# create a xml parser to extract the train timetable from the input dataset
# author(s): Hai

import numpy as np
import matlibplot.pyplot as plt
import xml.etree.ElementTree as ET
import os

# input dataset (translated to ENGLISH)

ice_401_dir = "/bzfnguye/dataset/EN_GRIPS2019_401.xml"
ice_402_dir = "/bzfnguye/dataset/EN_GRIPS2019_402.xml"
ice_403_dir = "/bzfnguye/dataset/EN_GRIPS2019_403.xml"
ice_411_dir = "/bzfnguye/dataset/EN_GRIPS2019_411.xml"

root_401 = ET.parse(ice_401_dir).getroot()


