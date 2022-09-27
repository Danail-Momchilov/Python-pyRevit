# -*- coding: utf-8 -*-

from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import *

from pyrevit import revit, UI, forms

import logexporter


# define a variable for the active document
doc = __revit__.ActiveUIDocument.Document


# define a sorting function, based on location
def ElementSorted(elm_list):
	return sorted(elm_list,key= lambda x: (round(x.Location.Point.Z,2),\
										round(x.Location.Point.Y,2),\
										round(x.Location.Point.X,2)
										))


# define a renumbering function
def RenumberElements(elm_list):

    prefix = forms.ask_for_string(default="W1", prompt='Enter prefix:', title='Element Prefix')

    fill = forms.ask_for_string(default="2", prompt='Enter number total length:', title='Number Length')
    
    floatFill = float(fill)
    
    for i, e in enumerate(elm_list):
        e.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set(prefix+str(i).zfill(floatFill))
        

# define a function, filtering windows, based on their host
def FilterWindows(windowsList):

    filteredWindows = []
    
    for window in windowsList:
        if 'Wall' in str(window.Host):
            if 'Curtain' not in str(window.Host.WallType.Kind):
                filteredWindows.append(window)
    
    return filteredWindows


# define selection filter
class SelectionFilter(UI.Selection.ISelectionFilter):
	def __init__(self, nom_type):
		self.nom_type = nom_type
	def AllowElement(self, e):		
		if e.Category.Name == self.nom_type:
			return True
		else:
			return False
	def AllowReference(self, ref, point):
		return true


# main program body - renumbering
t = Transaction(doc, 'Renumber Windows')


selected_option = forms.CommandSwitchWindow.show(
    ['All Windows', 'Windows In View', 'Select Windows'],
     message='Select Windows to Renumber:',
	)


if selected_option == 'Windows In View':

    initialWindows = FilteredElementCollector(doc, doc.ActiveView.Id).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsNotElementType()
    
    windows = FilterWindows(initialWindows)
    finalwindows = ElementSorted(windows)
    
    reportMsg = 'The specified ' + str(len(finalwindows)) + ' windows were successfully renumbered!'
    
    t.Start()
    RenumberElements(finalwindows)
    t.Commit()


elif selected_option == 'Select Windows':

    initialWindows = []

    with forms.WarningBar(title='Select Doors:'):
        el_ref= revit.uidoc.Selection.PickObjects(UI.Selection.ObjectType.Element, SelectionFilter("Windows"), 'Select Windows To Renumber')
	
    [initialWindows.append(doc.GetElement(er.ElementId)) for er in el_ref]
    
    windows = FilterWindows(initialWindows)
    finalwindows = ElementSorted(windows)
    
    reportMsg = 'The specified ' + str(len(finalwindows)) + ' windows were successfully renumbered!'
    
    t.Start()
    RenumberElements(finalwindows)
    t.Commit()


elif selected_option == 'All Windows':

    initialWindows = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsNotElementType()
    
    windows = FilterWindows(initialWindows)
    finalwindows = ElementSorted(windows)
    
    reportMsg = 'The specified ' + str(len(finalwindows)) + ' windows were successfully renumbered!'
    
    t.Start()
    RenumberElements(finalwindows)
    t.Commit()
    
else:
    reportMsg = 'The command was cancelled'


# return a report
TaskDialog.Show('Report', reportMsg)


# export log file
current_file = __file__.split("\\")
logexporter.logExport(current_file)
