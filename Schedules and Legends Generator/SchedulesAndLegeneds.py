# -*- coding: utf-8 -*-

from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import *

from collections import OrderedDict 

from pyrevit import revit, DB, UI
from rpw import db

import sys
import logexporter

doc = __revit__.ActiveUIDocument.Document


# check for doors from different families with identical Type Mark parameter values
allDoorTypes = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsElementType()
allDoorFamilies, uniqueDoorFamilies, uniqueDoorFamilyNames, allDoorTypeMarks = [], [], [], []

for doorType in allDoorTypes:
    allDoorFamilies.append(doorType.Family)

for doorFamily in allDoorFamilies:
    if doorFamily.Name not in uniqueDoorFamilyNames:
        uniqueDoorFamilyNames.append(doorFamily.Name)
        uniqueDoorFamilies.append(doorFamily)
        
for uniqueFamily in uniqueDoorFamilies:
    templist = []
    
    for id in uniqueFamily.GetFamilySymbolIds():
        templist.append(doc.GetElement(id).LookupParameter('Type Mark').AsString())
        
    templist = list(dict.fromkeys(templist))
    
    for uniqueTypeMark in templist:
        allDoorTypeMarks.append(uniqueTypeMark)
     
if len(allDoorTypeMarks) != len(dict.fromkeys(allDoorTypeMarks)):
    TaskDialog.Show("Warning", "Different doors with identical Type Marks were found in the project. Please revise them and try again. All Type Marks for elements from different families must be unique!")
    sys.exit()


# get all schedules, check if the default legend and Schedule are loaded and check if all doors have different Type Marks
schedule=db.Collector(of_class='View',where=lambda x: x.get_Parameter(DB.BuiltInParameter.VIEW_NAME).AsString() == "Door Schedule Type DA" ).get_first(wrapped=False)

if schedule == None:
    TaskDialog.Show("Warning", "Please load the default Door Schedule Type DA view and try again!")
    sys.exit()

legend = db.Collector(of_class='View',where=lambda x: x.get_Parameter(DB.BuiltInParameter.VIEW_NAME).AsString() == "Door Type DA" ).get_first(wrapped=False)

if legend == None:
    TaskDialog.Show("Warning", "Please load the default Door Type DA legend and try again!")
    sys.exit()


# get a collection of all the door instances, available in the project
doorInput = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType().ToElements()


# check if any of the doors already has legend and schedules associated to their type. Remove them from the list if any
allDoorSchedules = db.Collector(of_class="View",where=lambda x: "Door Schedule Type" in x.get_Parameter(DB.BuiltInParameter.VIEW_NAME).AsString())

doorDuplicates = []

for scheduleView in allDoorSchedules:
    name = scheduleView.Name
    
    if name[-3] == " ":
        typeName = scheduleView.Name[len(scheduleView.Name) - 2:]
    elif name[-4] == " ":
        typeName = scheduleView.Name[len(scheduleView.Name) - 3:]
        
    for door in doorInput:
        if typeName == door.Symbol.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_MARK).AsString() and typeName != "DA":
            doorDuplicates.append(door)
            
uniqueNewDoors = [x for x in doorInput if x not in doorDuplicates]


# check doors for copyrights data
finalDoorsList, nonIpaDoorNamesList = [], []

for door in uniqueNewDoors:
    if door.Symbol.LookupParameter('Family Copyright ©'):
        if door.Symbol.LookupParameter('Family Copyright ©').AsString() == 'Ivo Petrov Architects':
            finalDoorsList.append(door)
        else:
            nonIpaDoorNamesList.append(door.Symbol.FamilyName)
    else:
        nonIpaDoorNamesList.append(door.Symbol.FamilyName)


# create definitions for extracting the elements and family types
def unique_types(elm_list):
	unique=[]
	fam_types=[]
	for l in elm_list:
		if l.Symbol.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_MARK).AsString() not in unique and l.Symbol.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_MARK).AsString() != "DA":
			unique.append(l.Symbol.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_MARK).AsString())
			fam_types.append(l.Symbol.Id)
	return zip(unique,fam_types)

def standard_type(elm_list):
	unique=[]
	fam_types=[]
	for l in elm_list:
		if l.Symbol.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_MARK).AsString() not in unique and l.Symbol.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_MARK).AsString() == "DA":
			unique.append(l.Symbol.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_MARK).AsString())
			fam_types.append(l.Symbol.Id)
	return zip(unique,fam_types)
    
    
# create new schedules and legends and update WA
filter=schedule.Definition.GetFilter(0)

t=DB.Transaction(doc,"Duplicate Schedules&Legends")
t.Start()

for ut,ft in unique_types(finalDoorsList):

    new_schedule=schedule.Duplicate(DB.ViewDuplicateOption.Duplicate)
    filter.SetValue(ut)
    doc.GetElement(new_schedule).Definition.SetFilter(0,filter)
    table_data=doc.GetElement(new_schedule).GetTableData().GetSectionData(DB.SectionType.Header).SetCellText(0,0,'Спецификация врати - Tип '+ut)
    doc.GetElement(new_schedule).Name="Door Schedule Type "+ ut
	
    new_legend=legend.Duplicate(DB.ViewDuplicateOption.WithDetailing)
    doc.GetElement(new_legend).Name="Door Type "+ ut
    legend_component=db.Collector(view=doc.GetElement(new_legend), of_category='OST_LegendComponents')#.get_first(wrapped=False).get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).Set(ft)
    legend_component[0].get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).Set(ft)
    legend_component[1].get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).Set(ft)

for ut,ft in standard_type(finalDoorsList):

    legend_component=db.Collector(view=legend, of_category='OST_LegendComponents')#.get_first(wrapped=False).get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).Set(ft)
    legend_component[0].get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).Set(ft)
    legend_component[1].get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT).Set(ft)

t.Commit()


# Display reports after completion
if len(uniqueNewDoors) != 1:
    reportMsg = str(len(uniqueNewDoors)) + " new Legends and schedules were created successfully! Enjoy ;)"
elif len(uniqueNewDoors) == 1:
    reportMsg = "<Door Schedule Type DA> and <Door Type DA> schedule and legend views were updated. No other new Type Marks were found in the project! "

if nonIpaDoorNamesList != []:
    reportMsg += 'The following door families were found in the project, not being subject to IPA copyrights. Please contact the BIM team for evaluation of these families: ' + str(nonIpaDoorNamesList)
    
TaskDialog.Show("Report", reportMsg)


# Export log file
current_file = __file__.split("\\")
logexporter.logExport(current_file)
