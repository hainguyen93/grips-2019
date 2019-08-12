"""Translator for ROTOR's XML files

This script translates the file input/output of ROTOR from
German to English and vice versa. It is solely based on
regular expressions and does not make use of the XML
structure.

INVOCATION:
$ python xmltranslator.py (de-en|en-de) inputfilename > outputfilename

inputfilename -- name of the XML file that is to be converted.
outputfilename -- name of the XML file to be created.

EXAMPLE:
$ python xmltranslator.py de-en candyland.xml > candyland_en.xml
"""

import sys

if len(sys.argv) != 3 or not (sys.argv[1] in ['de-en','en-de']):
	sys.stderr.write("""USAGE:
$ python xmltranslator.py (de-en|en-de) inputfilename > outputfilename

inputfilename -- name of the XML file that is to be converted.
outputfilename -- name of the XML file to be created.

EXAMPLE:
$ python xmltranslator.py de-en candyland.xml > candyland_en.xml\n""")
	sys.exit(1)

tagTranslations = [
	['Umlauf'                , 'Rotation'           ],
	['Nachtwenden'           , 'NightTurns'         ],
	['Nachtwende'            , 'NightTurn'          ],
	['Bewegungsdaten'        , 'RotationData'       ],
	['Leistungslaufweg'      , 'UsualActivity'      ],
	['AndereLeistung'        , 'OtherActivity'      ],
	['Wende'                 , 'Turn'               ],
	['Zuege'                 , 'Trains'             ],
	['Zug'                   , 'Train'              ],
	['Fahrlagen'             , 'Trips'              ],
	['Fahrlage'              , 'Trip'               ],
	['Gueltigkeit'           , 'Validity'           ],
	['Starken_und_Schwaechen', 'Coupling'           ],
	['Konfigurationen'       , 'Configurations'     ],
	['Konfiguration'         , 'Configuration'      ],
	['Zuglaufpunkte'         , 'Stops'              ],
	['Zuglaufpunkt'          , 'Stop'               ],
	['Betriebsstellen'       , 'Stations'           ],
	['Betriebsstelle'        , 'Station'            ],
	['Wendezeit'             , 'TurnDuration'       ],
	['Entfernungsmatrix'     , 'DistanceMatrix'     ],
	['Entfernung'            , 'Distance'           ],
	['Fahrzeuggruppen'       , 'Fleets'             ],
	['Fahrzeuggruppe'        , 'Fleet'              ],
	['Zuggattungen'          , 'TrainTypes'         ],
	['Zuggattung'            , 'TrainType'          ],
	['Kapazitaetsknoten'     , 'CapacityNode'       ],
	['Knoten'                , 'Node'               ],
	['Kapazitaetsbedingung'  , 'CapacityConstraint' ],
	['Drehfahrten'           , 'ReorientationTrips' ],
	['Drehfahrt'             , 'ReorientationTrip'  ],
	['Behandlungen'          , 'Maintenances'       ],
	['Behandlungsregeln'     , 'MaintenanceRules'   ],
	['Behandlungsmassnahmen ', 'MaintenanceActions' ],
	['Behandlungsregel_Ressource', 'MaintenanceRule_Resource']
	]

attributeTranslations = [
	['Haltekennung'                           , 'StopType'],
	['LinienNr'                               , 'TrainLine'],
	['Verkehrstage'                           , 'OperatingDays'],
	['Zuggattung_ID'                          , 'TrainTypeID'],
	['aufUmlauftag'                           , 'ToBlock'],
	['vonUmlauftag'                           , 'FromBlock'],
	['vonGueltigkeit'                         , 'FromValidity' ],
	['Bitleiste'                              , 'BitString'],
	['Gueltigkeit'                            , 'Validity'],
	['Endzeit'                                , 'EndTime'],
	['Startzeit'                              , 'StartTime'],
	['NachAnkunftszeit'                       , 'DestinationArrivalTime'],
	['VonAbfahrtszeit'                        , 'OriginDepartureTime'],
	['Nachtsprung'                            , 'IsOvernight'],
	['aufLeistung'                            , 'NextActivity'],
	['vonLeistung'                            , 'PreviousActivity'],
	['Hinweistext'                            , 'Note'],
	['Kommentar'                              , 'Comment'],
	['Konfigurationsklasse'                   , 'ConfigurationClass'],
	['LLWID'                                  , 'UActivitiyID'],
	['NachBetriebsstelleDS100'                , 'DestinationStation'],
	['TickTack'                               , 'Orientation'],
	['Typ'                                    , 'TripType'],
	['Umlauftag'                              , 'Block'],
	['Verwaltungsnummer'                      , 'AdministrativeID'],
	['VonBetriebsstelleDS100'                 , 'OriginStation'],
	['Zugnummer'                              , 'TrainID'],
	['Bezeichnung'                            , 'Labeling'],
	['Art'                                    , 'TurnType' ],
	['AnzahlLLWs'                             , 'NumberOfUsualActivities'],
	['AnzahlOertlicheLeistungen'              , 'NumberOfLocalAcitivities'],
	['AnzahlUmlauftage'                       , 'NumberOfRotationDays'],
	['AnzahlWenden'                           , 'NumberOfTurns'],
	['FzgGruppe'                              , 'Fleet'],
	['Heimatstelle'                           , 'HomeStation'],
	['Typ'                                    , 'Type'],
	['Umlaufnummer'                           , 'RotationID'],
	['Betriebsstelle_ID'                      , 'StationID'],
	['Betriebsstellen_ID'                     , 'StationID_'],
	['Abfahrtzeit'                            , 'DepartureTime'],
	['Ankunftzeit'                            , 'ArrivalTime'],
	['Nachtsprung_Ab'                         , 'NewDayOnDeparture'],
	['Nachtsprung_An'                         , 'NewDayOnArrival'],
	['kmLaenge'                               , 'DistanceKM'],
	['Fahrtrichtungswechsel'                  , 'ChangeInMovementDirection'],
	['Ab_Tor'                                 , 'DepartureGate'],
	['An_Tor'                                 , 'ArrivalGate'],
	['Abschnitt_Beginn_Ende'                  , 'IsBreakPoint'],
	['VerwNr'                                 , 'AdministrativeID_'],
	['ZugNr'                                  , 'TrainID_'],
	['Kurzwende_Bahnsteig_Tag'                , 'ShortTurn_Platform_Day'],
	['Kurzwende_Bahnsteig_Tag_OG'             , 'STPD_UpperLimit'],
	['Kurzwende_Bahnsteig_Tag_UG'             , 'STPD_LowerLimit'],
	['Kurzwende_Abstellanlage_Tag'            , 'ShortTurn_StorageSidings_Day'],
	['Kurzwende_Abstellanlage_Tag_UG'         , 'STSSD_UpperLimit'],
	['Kurzwende_Abstellanlage_Tag_OG'         , 'STSSD_LowerLimit'],
	['Qualitaetswende_Abstellanlage_Nacht'    , 'OvernightParking'],
	['Qualitaetswende_Abstellanlage_Nacht_UG' , 'OP_LowerLimit'],
	['Fahrzeit_Hinfahrt'                      , 'DurationJourneyThere'],
	['Fahrzeit_Rueckfahrt'                    , 'DurationReturn'],
	['Anzahl_Kopfmachen'                      , 'NumberOfOrientationsChanges'],
	['Leerdrehfahrt_Dauer'                    , 'EmptyReorientationTripDuration'],
	['Leerdrehfahrt_Entfernung'               , 'EmptyReorientationTripDistance'],
	['Tor_Bis'                                , 'ToGate'],
	['Tor_Von'                                , 'FromGate'],
	['Betriebskosten_Last_pro_km'             , 'OperationalCost_Load_perKM'],
	['Betriebskosten_Leer_pro_km'             , 'OperationalCost_NoLoad_perKM'],
	['Leer_Geschwindigkeit'                   , 'Speed_NoLoad'],
	['Kapitalkosten_pro_Jahr'                 , 'CapitalCostPerYear'],
	['Strafkosten_Mindestanzahl'              , 'PenaltyCostTooFewVehicles'],
	['Leerzug'                                , 'IsEmptyTrain' ],
	['Dauer'                                  , 'Duration'],
	['Entfernung'                             , 'Distance'],
	['Grenzwert_Oben'                         , 'StrictUpperBound'],
	['Grenzwert_Unten'                        , 'StrictLowerBound'],
	['Kosten_ueber_Planwert_Oben'             , 'CostForUpperViolation'], # of desired Bound
	['Kosten_unter_Planwert_Unten'            , 'CostForLowerViolation'], # of desired Bound
	['Planwert_Oben'                          , 'DesiredUpperBound'],
	['Planwert_Unten'                         , 'DesiredLowerBound'],
	['Dauer_Anzeige'                          , 'Duration_Shown'],
	['Dauer_Nacht'                            , 'DurationAtNight'],
	['Dauer_Nacht_UG'                         , 'DAN_LowerLimit'],
	['Dauer_Tag'                              , 'DurationDay'],
	['Dauer_Tag_UG'                           , 'DD_LowerLimit'],
	['Kapazitaetsverbrauch'                   , 'NeedsCapacity'],
	['Kosten'                                 , 'Cost']
	]

if sys.argv[1] == 'en-de':
	for pair in tagTranslations:
		pair.reverse()
	for pair in attributeTranslations:
		pair.reverse()

tagDictionary       = dict(tagTranslations)
attributeDictionary = dict(attributeTranslations)

import re
############ regular expressions ############

# tagPattern matches <tag ...>, </tag> and <tag .../>, but not
# <tag
# ...>
tagPattern = re.compile(r"</?(\w+).*?/?>")

# replacement patterns

# attribute pattern matches attribute="...",
# angle brackets are not relevant
attributePattern = re.compile(r'(\w+)=".*?"')

######### end of regular expressions ########

try:
	with open(sys.argv[2], 'r') as inputFile:
		for line in inputFile:

			# determine tag and attribute names
			tags = tagPattern.findall(line)
			attributes = attributePattern.findall(line)

			# if translations exist, apply them
			for tag in tags:
				translation = tagDictionary.get(tag, '')
				if translation != '':
					tagPattern1 = re.compile('<'+tag+r'(\s+.*?/?|/?)>')
					tagPattern2 = re.compile('</'+tag+'>')
					line = tagPattern1.sub('<'+translation+r'\1>', line)
					line = tagPattern2.sub('</'+translation+'>', line)
			for attribute in attributes:
				translation = attributeDictionary.get(attribute, '')
				if translation != '':
					attributePattern1 = re.compile(attribute+r'(=".*?")')
					line = attributePattern1.sub(translation+r'\1', line)
			sys.stdout.write(line)
					
except IOError,e:
	sys.stderr.write("""Failed to open input file, it might not exist or not be readable.
Caught IOError: {0:>2} {1}
Aborting...\n""".format(e.errno, e.strerror))
	sys.exit(1)
