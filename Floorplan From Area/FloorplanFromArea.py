
from Autodesk.Revit.DB import Transaction, Element, BuiltInCategory, BoundingBoxXYZ, View, ViewPlan, DisplayStyle, SpatialElementBoundaryOptions, ViewFamilyType, ViewDrafting, ViewFamily
from Autodesk.Revit.DB import FilteredElementCollector, CurveLoop, XYZ, ViewDetailLevel, BuiltInParameter, BoundarySegment, Curve, BoundarySegment, ElementTransformUtils, Area, Parameter

from Autodesk.Revit.DB import Curve, CurveLoop, DirectShape, ElementId, Line, BoundingBoxXYZ, ViewCropRegionShapeManager, ElementId, SpatialElementBoundaryLocation
from Autodesk.Revit.DB import SolidOptions, GeometryCreationUtilities, Transform, ViewDuplicateOption, TemporaryViewMode

from Autodesk.Revit.DB.Analysis import VectorAtPoint

from System.Collections.Generic import List

from rpw import db, ui, doc, uidoc
from pyrevit import forms, revit

import sys
import math



# Create a parameter to point at the current document
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
view = doc.ActiveView

t = Transaction(doc, "FloorPlan From Area")
t1 = Transaction(doc, "Temporary Hide / Isolate")



# Check if the active view has the neccessary parameters set
if(doc.ActiveView.LookupParameter("Phasing").AsString() == None):
    print("Please, set value for the parameter 'Phasing' of your active view and try again!")
    sys.exit()



# Isolate only Areas in the active view
area_ids = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Areas).WhereElementIsNotElementType().ToElementIds()
t1.Start()

view.IsolateElementsTemporary(area_ids)

t1.Commit()



# Make a selection for desired Areas
selection = revit.get_selection()
selection_list = revit.pick_rectangle()

elements = []

for element in selection_list:
    element_id = element.Id
    elements.append(doc.GetElement(element_id))



# Filter View Types and set the one to apply to apply to new views
viewfamily_types = FilteredElementCollector(doc).OfClass(ViewFamilyType)
viewfamily_types_list = []

for view_type in viewfamily_types:
    if("Plan" in view_type.LookupParameter("Type Name").AsString()):
        viewfamily_types_list.append(view_type.LookupParameter("Type Name").AsString())
    if("Gross" in view_type.LookupParameter("Type Name").AsString()):
         viewfamily_types_list.append(view_type.LookupParameter("Type Name").AsString())
    if("Rentable" in view_type.LookupParameter("Type Name").AsString()):
        viewfamily_types_list.append(view_type.LookupParameter("Type Name").AsString())

type = forms.SelectFromList.show(viewfamily_types_list,
                                multiselect = False,
                                title = "Select View Type to assign:",
                                button_name = "ASSIGN VIEW TYPE")

for view_type in viewfamily_types:
    if(type == view_type.LookupParameter("Type Name").AsString()):
        type_id = view_type.Id


    
# Filter View Templates and set the one to apply to apply to new views
templates_collector = FilteredElementCollector(doc).OfClass(View).ToElements()
templates_list_name = []

for template in templates_collector:
    if(template.IsTemplate == True):
        if("Plan" in template.Name):
            templates_list_name.append(template.Name)

res = forms.SelectFromList.show(templates_list_name,
                                multiselect = False,
                                title = "Select View Template to assign",
                                button_name = "ASSIGN TEMPLATE")

for template in templates_collector:
    if(template.Name == res):
        res_id = template.Id



# Input angle of rotation
rotationAngle = forms.ask_for_string(
	    default="0.00",
	    prompt="Enter angle of rotation /decimal degrees, direction: counter - clockwise/:",
	    title="Angle of rotation"
	    )
        
floatAngle = (-float(rotationAngle) * math.pi) / 180



# Input for duplicating the view with detailing
detailing = forms.CommandSwitchWindow.show(
    ["YES", "NO"],
     message="Create new floorplan? 'YES' or 'NO' (duplicate the active view with detailing):"
	)

if detailing == "YES":
    noDetailing = True
else:
    noDetailing = False



# Create floorplan of selected view type and apply selected view template
newplans = []
rotation_angles = []
areas = []
errorlist = []

t.Start()

for a in elements:
    
    Options = SpatialElementBoundaryOptions()
    Options.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Center
    s = a.GetBoundarySegments(Options)[0][1].GetCurve()
    sp1 = s.GetEndPoint(0)
    sp2 = s.GetEndPoint(1)
    vector = (sp2 - sp1).Normalize()
    
    if noDetailing:
        AreaPlan = ViewPlan.Create(doc, type_id, a.LevelId)
    else:
        AreaPlan = doc.GetElement(doc.ActiveView.Duplicate(ViewDuplicateOption.WithDetailing))
        AreaPlan.DisableTemporaryViewMode(TemporaryViewMode.TemporaryHideIsolate)
        AreaPlan.CropBoxActive = False
        AreaPlan.ViewTemplateId = ElementId(-1)
    AreaPlan.LookupParameter("IPA View Sub Group").Set("400")
    AreaPlan.LookupParameter("Phasing").Set(doc.ActiveView.LookupParameter("Phasing").AsString())
    AreaPlan.ViewTemplateId = res_id
    active_view_name = view.Name.ToString()
    
    a_crop = []
    area_segments = a.GetBoundarySegments(Options)
    
    for area_segment in area_segments[0]:
            p1 = area_segment.GetCurve().GetEndPoint(0)
            p2 = area_segment.GetCurve().GetEndPoint(1)
            a_crop.append(Line.CreateBound(p1, p2))
    
    try:
        AreaPlan.CropBoxActive = True
        AreaPlan.GetCropRegionShapeManager().SetCropShape(CurveLoop.Create(a_crop))
    except:
        errorlist.append(a.Id)
    
    newplans.append(AreaPlan)
    areas.append(a)

    try:
        AreaPlan.Name = active_view_name + "PC" + "-" + a.Number.ToString()
    except:
		AreaPlan.Name = active_view_name + "PC" + "-" + a.Number.ToString() + ".01"

t.Commit()



# rotate floorplans if rotation angle is set
if(floatAngle != math.radians(0)):
    for counter, plan in enumerate(newplans):

        area = areas[counter]        
        new_crop = []
    
        # Transactions for the purpose of obtaining and rotating the crop region
        temp1 = Transaction(doc, "Hide crop region")
        temp2 = Transaction(doc, "Unhide crop region")
        temp3 = Transaction(doc, "Rotate crop region")
        temp4 = Transaction(doc, "Create new crop region offset")
    
        temp1.Start()
        plan.CropBoxVisible = False
        temp1.Commit()
    
        all_in_view_crop_hidden = FilteredElementCollector(doc, plan.Id).ToElementIds()
    
        temp2.Start()
        plan.CropBoxVisible = True
        temp2.Commit()
    
        cropId = FilteredElementCollector(doc, plan.Id).Excluding(all_in_view_crop_hidden).ToElementIds()
    
        bbox = plan.CropBox
        center = 0.5 * (bbox.Min + bbox.Max)
        axis = Line.CreateBound(center, center + XYZ.BasisZ)
    
        temp3.Start()
        ElementTransformUtils.RotateElement(doc, cropId[0], axis, floatAngle)
        temp3.Commit()
        
        Options_new = SpatialElementBoundaryOptions()
        Options_new.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Center
        segments = area.GetBoundarySegments(Options_new)
        
        for segment in segments[0]:
        
            pt1 = segment.GetCurve().GetEndPoint(0)
            pt2 = segment.GetCurve().GetEndPoint(1)
            new_crop.append(Line.CreateBound(pt1, pt2))
          
        temp4.Start()
        try:
            plan.GetCropRegionShapeManager().SetCropShape(CurveLoop.Create(new_crop))
        except:
            pass
        temp4.Commit()


# disable temporary hide isolate mode of the active view
t1.Start()
view.DisableTemporaryViewMode(TemporaryViewMode.TemporaryHideIsolate)
t1.Commit()


if errorlist != []:  
    print("The following Areas were found to have problematic contours, thus their floorplan views do not have Crop Region applied. You could check those areas' contours by their ids:\n\n {}".format(errorlist))
else:
    print("All area plans were created successfully!")
