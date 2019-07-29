#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
from xml.dom.minidom import getDOMImplementation
from xml.dom import minidom
from xml.dom.minidom import parse

class Node:
    def __init__(self, nodeId, name, x, y ):
        self.id = nodeId
        self.name = name
        self.inEdges = []
        self.outEdges = []
        self.x = x
        self.y = y
        self.breakpoint = False

    def __str__( self ):
        return "Betriebstelle id: %4d name: " % (self.id) + self.name + " x: %.3f y: %.3f" % ( self.x, self.y )

    def addInEdge( self, edge ):
        self.inEdges.append( edge )

    def addOutEdge( self, edge ):
        self.outEdges.append( edge )

class Edge:
    def __init__(self, edgeId, tailNodeId, headNodeId, lines, value ):
        self.id = edgeId
        self.tailNodeId = tailNodeId
        self.headNodeId = headNodeId
        self.lines = lines
        self.value = value

    def __str__( self ):
        return "edge id: %4d tail: %4d head: %4d value: %4d lines: %s" % (self.id, self.tailNodeId, self.headNodeId, self.value, str( self.lines) )

class Graph:
    def __init__(self, graphId, nodes,  edges, nameToIdMap):
        self.nodes = nodes
        self.edges = edges
        self.nameToIdMap = nameToIdMap
        self.id = graphId

    def getEdge(self, tailId, headId):
        if tailId < 0 or tailId >= len( self.nodes ) or headId < 0 or headId >= len( self.nodes ):
            return None
        else:
            for edge in self.nodes[ tailId ].outEdges:
                if edge.headNodeId == headId:
                    return self.edges[ edge.id ]

            for edge in self.nodes[ headId ].outEdges:
                if edge.headNodeId == tailId:
                    return self.edges[ edge.id ]
            return None

    def hasEdge( self, tailId, headId ):
        if len( self.nodes ) <= tailId or len( self.nodes ) <= headId :
            return False
        for edge in self.nodes[tailId].outEdges:
            if edge.headNodeId == headId:
                return True
        for edge in self.nodes[tailId].inEdges:
            if edge.tailNodeId == tailId:
                return True

        return False

    def addNode(self, node):
      if node.id < 0 or node.id > len(self.nodes):
        print( "Invalid node id!")
      else:
        self.nodes.append( node )
        self.nameToIdMap[ node.name ] = node.id

    def addEdge(self, edge):
        if (len( self.nodes ) <= edge.tailNodeId
            or len( self.nodes ) <= edge.headNodeId
            or edge.tailNodeId < 0
            or edge.headNodeId < 0 ):
          print("Edge ids are not suitable for nodes in graph!")
        else:
          found = False

          #print( "Check for node {}".format(self.nodes[ edge.tailNodeId ]))

          for toCheck in self.nodes[ edge.tailNodeId ].outEdges:

            #print("To Check Id {}".format( toCheck.headNodeId ) )

            if toCheck.headNodeId == edge.headNodeId:
              found = True
              toCheck.lines = toCheck.lines[:] + edge.lines[:]
              toCheck.value += edge.value
              break

          if not found:
            self.edges.append( edge )
            self.nodes[ edge.headNodeId ].addInEdge( edge )
            self.nodes[ edge.tailNodeId ].addOutEdge( edge )

def getPassengerData():

  indexToWeekDay = ["07_Mo", "08_Di", "09_Mi", "10_Do", "11_Fr", "12_Sa", "06_So"]

  passengerData = {}

  for i in range( len( indexToWeekDay ) ):

    trainFile = open( "passengerdata/{}1215_{}.csv".format(indexToWeekDay[i][:2],indexToWeekDay[i][-2:]),"r" )

    lines = trainFile.readlines()[1:]

    for line in lines:
      line = line.split(",")

      valStr = "0000000"

      passengerData[ str( line[1] )+"_"+  str( line[2] ) +"_"+  str( line[3] ) + "_" + valStr[:i] +"1" + str( valStr[i+1:]) ] = int( line[4] ) + int( line[5] )

    trainFile.close()

  return passengerData


def buildTikzPic( graph, outNameFile ):
  """ writes tikz pictures for substrate, virtual and solution graphs to outFile or shell"""
  # latex packages
  outStr = "\\documentclass[tikz]{standalone}\n\\usepackage{geometry}\n\\usepackage{booktabs}\n"
  outStr +="\\geometry{a4paper,left=1.5cm,right=1.5cm, top=2cm, bottom=2cm}\n"
  outStr +="\\usepackage{hyperref}\n\\usepackage{tikz}\n"
  # tikz libraries
  outStr +="\\usetikzlibrary{fit}\n\\usetikzlibrary{shapes}\n\\usetikzlibrary{backgrounds}\n\\usetikzlibrary{arrows}\n"
  outStr +="\\usetikzlibrary{decorations}\n\\usetikzlibrary{topaths}\n\\usetikzlibrary{patterns}\n\\usetikzlibrary{calc}\n"
  outStr +="\\usetikzlibrary{intersections}\n\\usetikzlibrary{through}\n\\usetikzlibrary{spy}\n\\usetikzlibrary{matrix}\n"
  outStr +="\\usetikzlibrary{lindenmayersystems}\n\\usetikzlibrary{external}\n\\usetikzlibrary{snakes}\n"
  outStr +="\\usetikzlibrary{3d}\n\\usepackage{anysize}\n\\usepackage{rotating}\n\\begin{document}\n"
  outStr +="\\begin{tikzpicture}[font=\\normalsize]\n\\tikzstyle{singleLine}=[line width=1pt, blue]\n\\tikzstyle{fiveLines}=[line width=3pt, green]\n"
  outStr +="\\tikzstyle{tenLines}=[line width=5pt, yellow]\n\\tikzstyle{twentyLines}=[line width=7pt, orange]\n\\tikzstyle{fiftyLines}=[line width=10pt, red]\n"

  maxX = 0.0
  maxY = 0.0

  for node in graph.nodes:
    #numLines = 0
    #for edge in node.outEdges:
      #numLines += len(edge.lines)

    if( args.onlyGermany ):
      if( node.name[0] == "X"):
        continue

    tag = ""
    if ( node.breakpoint == True ):
      tag = ", label={{${}$}} ".format( node.name )

    maxX = max(maxX, node.x)
    maxY = max(maxY, node.y)


    outStr += "\\node ({}) at ({},{})[circle, fill, inner sep=1pt{}]{{}};\n".format( node.name, 5.0 * node.x, 5.0 * node.y, tag )

  outStr += "\\node (max) at ({},{}){{}};\n".format( 5.0 * maxX + 1, 5.0 * maxY + 1)

  visited = []
  for edge in graph.edges:

    if( args.onlyGermany ):
      if( graph.nodes[edge.headNodeId].name[0] == "X" or graph.nodes[edge.tailNodeId].name[0] == "X"):
        continue

    if edge.id in visited:
      continue

    oppEdge = graph.getEdge(edge.headNodeId, edge.tailNodeId )

    visited.append( oppEdge.id )

    #numLines = len( edge.lines ) + len( oppEdge.lines )
    numLines = edge.value + oppEdge.value

    #outStr += "\\draw[line width={}pt] ({}) to ({});\n".format( int( numLines / 7 ), graph.nodes[ edge.tailNodeId ].name,graph.nodes[ edge.headNodeId ].name )

    lineStyle = "fiftyLines"

    frac = float( numLines / 7 )
    if frac < 2:
      lineStyle = "singleLine"
    elif frac < 10:
      lineStyle = "fiveLines"
    elif frac < 20:
      lineStyle = "tenLines"
    elif frac < 50:
      lineStyle = "twentyLines"

    outStr += "\\draw[{}] ({}) to ({});\n".format( lineStyle, graph.nodes[ edge.tailNodeId ].name,graph.nodes[ edge.headNodeId ].name )
  outStr += "\\node (Dummy) at ({},{}){{}};\n".format( 35.0, 273.0 )
  outStr += "\\node (1LegendS) at ({},{}){{}};\n\\node[anchor = west] (1LegendT) at ({},{}){{\\Huge  1 to 5 Lines}};\n".format( 35.0, 272.0, 36.0, 272.0 )
  outStr += "\\draw[singleLine] (1LegendS) to (1LegendT);\n"
  outStr += "\\node (5LegendS) at ({},{}){{}};\n\\node[anchor = west] (5LegendT) at ({},{}){{\\Huge  5 to 10 Lines}};\n".format( 35.0, 271.0, 36.0, 271.0 )
  outStr += "\\draw[fiveLines] (5LegendS) to (5LegendT);\n"
  outStr += "\\node (10LegendS) at ({},{}){{}};\n\\node[anchor = west] (10LegendT) at ({},{}){{\\Huge 10 to 20 Lines}};\n".format( 35.0, 270.0, 36.0, 270.0 )
  outStr += "\\draw[tenLines] (10LegendS) to (10LegendT);\n"
  outStr += "\\node (20LegendS) at ({},{}){{}};\n\\node[anchor = west] (20LegendT) at ({},{}){{\\Huge 20 to 50 Lines}};\n".format( 35.0, 269.0, 36.0, 269.0 )
  outStr += "\\draw[twentyLines] (20LegendS) to (20LegendT);\n"
  outStr += "\\node (50LegendS) at ({},{}){{}};\n\\node[anchor = west] (50LegendT) at ({},{}){{\\Huge 50+      Lines}};\n".format( 35.0, 268.0, 36.0, 268.0 )
  outStr += "\\draw[fiftyLines] (50LegendS) to (50LegendT);\n"
  #outStr += "\\node ({}) at ({},{})[circle, fill, inner sep=1pt{}]{{}};\n".format( node.name, 5.0 * node.x, 5.0 * node.y, tag )outStr += "\\node ({}) at ({},{})[circle, fill, inner sep=1pt{}]{{}};\n".format( node.name, 5.0 * node.x, 5.0 * node.y, tag )
  #outStr += "\\draw[fiveLines] ({}) to ({});\n".format( lineStyle, graph.nodes[ edge.tailNodeId ].name,graph.nodes[ edge.headNodeId ].name )
  #outStr += "\\draw[tenLines] ({}) to ({});\n".format( lineStyle, graph.nodes[ edge.tailNodeId ].name,graph.nodes[ edge.headNodeId ].name )
  #outStr += "\\draw[twentyLines] ({}) to ({});\n".format( lineStyle, graph.nodes[ edge.tailNodeId ].name,graph.nodes[ edge.headNodeId ].name )
  #outStr += "\\draw[fiftyLines] ({}) to ({});\n".format( lineStyle, graph.nodes[ edge.tailNodeId ].name,graph.nodes[ edge.headNodeId ].name )

  outStr +="\\end{tikzpicture}\n\\end{document}\n"

  print( "Write ouput to file {}".format( outNameFile + ".tex" ) )
  f = open( outNameFile + ".tex", "w" )
  f.write( outStr )
  f.close()



def readCoordinates():

  coordinatesObject = parse( "PlottingCoordinates.xml")

  locations = coordinatesObject.getElementsByTagName( "Bst")

  locToLonLatMap = {}

  for loc in locations:

    locToLonLatMap[ str(loc.getAttribute("ID")) ] = [ float( loc.getAttribute("Lon") ), float( loc.getAttribute("Lat") ) ]

  return locToLonLatMap


def main(argv):

  parser = argparse.ArgumentParser(description='Tikz pic visualization creation')

  parser.add_argument( '-i', '--info',
    action='store_true',
    dest='infoFlag',
    default=False,
    required=False,
    help='show transformation information' )


  parser.add_argument( '-s',
    action='store',
    dest='solution',
    required=False,
    default=None,
    help='solution file name' )

  parser.add_argument( '-o',
      action='store',
      dest='output',
      metavar='outputFileName',
      default='picture',
      help='output file name' )

  parser.add_argument(  '-t',
    action='store',
    dest='timetable',
    metavar='timetableFileName',
    default=None,
    required=False,
    help='name of the xml instance file' )

  parser.add_argument(  '-g',
    action='store_true',
    dest='onlyGermany',
    required=False,
    default=False,
    help='flag for ignoring non german stations' )

  global args

  args = parser.parse_args()

  coordinates = readCoordinates()

  instance = parse( args.timetable )

  locations = {}

  for stop in instance.getElementsByTagName("Zuglaufpunkt"):

    name = str( stop.getAttribute("Betriebsstelle_ID") )

    if name not in locations:
      if name in coordinates:
        locations[ name ] = coordinates[ name ]
      else:
        print( "Coordinates for {} not found!".format( name ))

  print( locations )
  # inserting ruby code here
  import json
  with open('locations.json', 'w') as f:
      json.dump(locations, f)

  graph = Graph(0, [],[],{})

  for key in locations.keys():

    elem = coordinates[ key ]
    graph.addNode( Node( len( graph.nodes ), key, elem[0], elem[1] ) )

  solTrainValidities = {}

  if not args.solution == None:

    solution = parse( args.solution )

    for solTask in solution.getElementsByTagName("Leistungslaufweg"):

      trainNumber = str( solTask.getAttribute("Zugnummer") )

      if trainNumber in solTrainValidities.keys():

        solTaskVal = str(solTask.getAttribute("Bitleiste"))

        for i in range( len( solTaskVal ) ):

          if solTaskVal[i] == "1":
            oldVal = solTrainValidities[ trainNumber ]

            solTrainValidities[ trainNumber ] = oldVal[:i] +"1" + oldVal[i+1:]
      else:
        solTrainValidities[ trainNumber ] = str(solTask.getAttribute("Bitleiste"))

    #print( solTrainValidities )

  #passengerData = getPassengerData()
  #print( passengerData )
  passengerData = {}

  passengers = 0
  passengerKM = 0

  for train in instance.getElementsByTagName("Zug"):

    if( not args.solution == None ):
      if( not str(train.getAttribute("ZugNr")) in solTrainValidities.keys() ):
        continue

    if( train.hasAttribute("ZugAusfall") ):
        continue

    for task in train.getElementsByTagName("Fahrlage"):

      taskVal = str(task.getElementsByTagName("Gueltigkeit")[0].getAttribute("Bitleiste"))
      value = taskVal.count('1')
      trainIdentifier =  str( train.getAttribute("ZugNr") ) + "_" + taskVal

      if( not args.solution == None ):

        zugNr = str( train.getAttribute("ZugNr") )

        if( zugNr not in solTrainValidities.keys() ):
          print("Task in solution for task {}".format( zugNr ) )
          continue
        else:
           trainIdentifier =  zugNr  + "_" + str( solTrainValidities[ zugNr ] )
           value = trainIdentifier[-7:].count("1")

        #found = False
        #for i in range( len( taskVal ) ):
          #if (taskVal[i] == "1" and solTaskVal[i] == "1" ):
            #found = True
            #break
        #if not found:
          #continue


      nodes = task.getElementsByTagName("Zuglaufpunkt")

      graph.nodes[graph.nameToIdMap[ str( nodes[0].getAttribute("Betriebsstelle_ID") ) ]].breakpoint = True
      graph.nodes[graph.nameToIdMap[ str( nodes[-1].getAttribute("Betriebsstelle_ID") ) ]].breakpoint = True

      lastNodes = [ str( nodes[0].getAttribute("Betriebsstelle_ID") ) for l in range( 7 ) ]
      lastLength = [ 0.0 for l in range( 7 ) ]

      for i in range( len( nodes ) - 1 ):



        #print( "search for edge from {} ({}) to {} ({})".format( str( nodes[i].getAttribute("Betriebsstelle_ID") ),
                                                                #graph.nameToIdMap[ str( nodes[i].getAttribute("Betriebsstelle_ID") ) ],
                                                                #str( nodes[i+1].getAttribute("Betriebsstelle_ID") ),
                                                                #graph.nameToIdMap[ str( nodes[i+1].getAttribute("Betriebsstelle_ID") ) ] ) )
        fromId = graph.nameToIdMap[ str( nodes[i].getAttribute("Betriebsstelle_ID") ) ]
        toId = graph.nameToIdMap[ str( nodes[i+1].getAttribute("Betriebsstelle_ID") ) ]

        nodeConfig = nodes[i].getElementsByTagName("Konfiguration")

        solValStr = trainIdentifier[-7:]
        nullStr = "0000000"

        if not ( nodes[i].hasAttribute("Leerzug") ):
          for k in range( len( solValStr ) ):

            if( solValStr[k] == "0"):
              continue

            pasInd = trainIdentifier[:-7] + str( nodes[i].getAttribute("Betriebsstelle_ID") ) + "_" + nodes[i+1].getAttribute("Betriebsstelle_ID") + "_"+ nullStr[:k] +"1"+nullStr[k+1:]
            #print( pasInd )
            if( pasInd not in  passengerData.keys() ):
              newPas = trainIdentifier[:-7] + lastNodes[k]  + "_" + nodes[i+1].getAttribute("Betriebsstelle_ID") + "_"+ nullStr[:k] +"1"+nullStr[k+1:]
              #print("Invalid train Identifier {} try {}".format( pasInd, newPas )  )
              if( newPas not in  passengerData.keys() ):
                #print( "Stil invalid" )
                lastLength[k] += float( str( nodes[i].getAttribute("kmLaenge") ) )
                continue
              else:
                #print("Found new train Identifier {}".format( newPas )  )
                pasInd = newPas
                lastNodes[k] = str( nodes[i+1].getAttribute("Betriebsstelle_ID") )
            actPas = passengerData[ pasInd ]
            lastLength[k] += float( str( nodes[i].getAttribute("kmLaenge") ) )
            passengers += actPas
            passengerKM += actPas * lastLength[k]
            lastNodes[k] = str( nodes[i+1].getAttribute("Betriebsstelle_ID") )
            lastLength[k] = 0.0

        graph.addEdge( Edge( len(graph.edges), fromId, toId, [ trainIdentifier ], value ) )


        if( str( nodes[i].getAttribute("Abschnitt_Beginn_Ende") ) == "true" ):
          graph.nodes[fromId].breakpoint = True


  for edge in graph.edges:
    print( "{} from {} to {}".format( edge, graph.nodes[edge.tailNodeId].name, graph.nodes[edge.headNodeId].name ) )

  print(" Total Number Passengers per Instance = {} passengerKM = {}", passengers, passengerKM )

  buildTikzPic( graph, args.output )


if __name__ == "__main__":
  main(sys.argv[1:])
