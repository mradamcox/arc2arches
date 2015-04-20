import os
import argparse
import shapefile
import json
import subprocess
import csv
import sys
import unicodecsv
import arcpy

def getShapeType(feature_class):
    """ returns the shapetype of the input reader object """
    desc = arcpy.Describe(feature_class)
    shp_type = desc.shapeType
    arcpy.AddMessage(shp_type)
    if not shp_type.upper() in ("POINT","POLYLINE","POLYGON"):
        arcpy.AddError("{0} shapetype not supported at this time".format(
            shp_type))
        exit()
    return shp_type.upper()

##def getWKT(shape,shp_type):
##    """ converts a shape from the shapefile libary to WKT""" 
##   
##    pointlist = [" ".join([str(i) for i in coord]) for coord in shape.points]
##    wkt = "{0} ({1})".format(shp_type,", ".join(pointlist))
##    return wkt

def getFieldNames(feature_class):
    """ return list of field names """
    fieldnames = [i[0] for i in reader.fields]
    return fieldnames

def checkFieldsInConfig(config_fields,shp_fields):
    """makes sure all fields in the field map are present in the shapefile"""
    for i in config_fields:
        if not i in shp_fields:
            arcpy.AddError("Invalid field name in conflig file:\n{0}".format(
                i))
            exit()
    return True

def makeFieldIndex(fields,reader):
    """ returns a dictionary with index number for fields in fieldmap """
    f_index = {}
    for i,field in enumerate(reader.fields):
        if field[0] in fields:
            f_index[field[0]] = i-1
    return f_index

def parseFieldMap(field_map_full):
    """ take field map from json to list of group dictionaries """
    groups = []
    for item in field_map_full:
        for k,v in item.iteritems():
            groups.append(v)
    return groups

def parseConfligFile(conflig_path):
    """ parses the input .conflig (augmented .config) file, return info set """
    ## access config (conflig) file
    with open(conflig_path) as con:
        config_contents = con.read()
    config_json = json.loads(config_contents)
    
    resource_type = config_json["RESOURCE_TYPE"]
    full_field_map = config_json["FIELD_MAP"]
    groups = parseFieldMap(full_field_map)
    fields = []
    for group in groups:
        for k, v in group.iteritems():
            fields.append(k)

    return resource_type, fields, groups

def notepadOpen(inputfile):
    """ opens the input file with notepad++ """
    ## path to notepad executable
    notepad = r"C:\Program Files (x86)\Notepad++\notepad++.exe"     
    subprocess.call([notepad,inputfile])
    return

def convertTypeValue(input_value,auth_dict):
    """ takes the input value, and compares it with the authority document
    dictionary.  if the value is a Preflabel, the corresponding conceptid
    is returned.  if it is already a conceptid, that id is returned."""

    if auth_dict.values().count(input_value) > 1:
        arcpy.AddError("""
  There are two or more corresponding concept ids for this Preflabel.
  You'll have to find the correct conceptid and apply it to the original
  dataset.""")
        exit()

    conceptid = False
    if input_value in auth_dict.keys():
        conceptid = input_value

    else:
        for k,v in auth_dict.iteritems():
            if v == input_value:
                conceptid = k
                break

    if not conceptid:
        arcpy.AddError("""
  The value listed below can not be reconciled with the Preflabels or
  conceptids that are available for this entity type.  Double-check your
  original data before trying again.
    PROBLEM: {0}""".format(input_value))
        exit()
                        
    return conceptid

def getAuthDict(auth_doc_path):
    """ makes a dictionary for the accepted values present in an autority
    document """

    auth_dict = {}
    with open(auth_doc_path, 'rU') as f:
        fields = ['conceptid','Preflabel','altlabels','ParentConceptid',
                      'ConceptType','Provider']
        rows = unicodecsv.DictReader(f, fieldnames=fields,
            encoding='utf-8-sig', delimiter=',', restkey='ADDITIONAL',
                                     restval='MISSING')
        rows.next()
        rownum = 2
        for row in rows:
            auth_dict[row['conceptid']] = row['Preflabel']
            rownum += 1

    return auth_dict

def checkForAuthDoc(entity_name,auth_doc_directory):
    """ checks the entity name against the authority documents, returns path
    to document if there is one present, returns False if no authority document
    exists for this entity. """
    doc_name = entity_name[:-4] + "_AUTHORITY_DOCUMENT.csv"
    doc_path = os.path.join(auth_doc_directory,doc_name)
    if not os.path.isfile(doc_path):
        arcpy.AddError("""
  This entity seems to need an authority document, yet no document was found.
  Double check settings.CONCEPT_SCHEME_LOCATIONS and make sure an authority
  document exists named:\n    {0}""".format(doc_name))
        exit()

    return doc_path

def makeRelationsFile(arches_file):
    """ makes an empty relations file to match the given arches file """

    relations = os.path.splitext(arches_file)[0]+".relations"
    if not os.path.isfile(relations):
        with open(relations,"wb") as rel:
            rel.write("RESOURCEID_FROM|RESOURCEID_TO|START_DATE"\
                "|END_DATE|RELATION_TYPE|NOTES\r\n")
    return

def processLayer(inlayer,config,output_dir,auth_doc_directory):
    """ process the input shapefile """
    arcpy.AddMessage(inlayer)

    outfile = os.path.join(out_dir,inlayer+".arches")
    makeRelationsFile(outfile)

    if os.path.isfile(outfile):
        os.remove(outfile)

    fc_fields = [f.name for f in arcpy.ListFields(inlayer)]
    shp_type = getShapeType(inlayer)

    result = parseConfligFile(config)
    res_type,config_fields,groups =  result[0],result[1],result[2]

    ## compare config and shp information
    checkFieldsInConfig(config_fields,fc_fields)
    config_fields.append("SHAPE@WKT")

    ## print intro summary
    arcpy.AddMessage("""FROM: {0}
TO: {1}
CONFLIGURATION: {2}

resource type: {3}
shape type: {4}
field mapping:
  (shape field --> arches entity)""".format(os.path.basename(inlayer),
    os.path.basename(outfile),os.path.basename(config),res_type,shp_type))
    cnt = 1
    for group in groups:
        arcpy.AddMessage("  ~ group" + str(cnt))
        for k,v in group.iteritems():
            arcpy.AddMessage("      {0} --> {1}".format(k,v))
        cnt+=1

    ## dictionary of created authority document dictionaries
    auth_dict_dict = {}                

    resourceid = 100000
    groupid = 300000

    ## print file
    with open(outfile,"wb") as arches:
        arches.write(
            "RESOURCEID|RESOURCETYPE|ATTRIBUTENAME|ATTRIBUTEVALUE|GROUPID\r\n")
        with arcpy.da.SearchCursor(inlayer,config_fields) as rows:
            for row in rows:

                #first, write geometry row
                wkt = row[-1]
                arches.write("{0}|{1}|{2}|{3}|{4}\r\n".format(
            resourceid,res_type,"SPATIAL_COORDINATES_GEOMETRY.E47",wkt,groupid))

                #next, loop through fields and add values
                for group in groups:
                    groupid+=1
                    for f_in, entity in group.iteritems():

                        value = row[config_fields.index(f_in)]
                        if value.rstrip() == '':
                            continue

                        ## if it's a type, it may need translation
                        if ".E55" in entity:

                            auth_path = checkForAuthDoc(entity,auth_doc_directory)
                            if not entity in auth_dict_dict.keys():
                                auth_dict_dict[entity] = getAuthDict(auth_path)
                            auth_dict = auth_dict_dict[entity]
                            value = convertTypeValue(value,auth_dict)

                        arches.write("{0}|{1}|{2}|{3}|{4}\r\n".format(
                            resourceid,res_type,entity,value,groupid))
                groupid+=1
                resourceid+=1

    return outfile   
    
input_layer = arcpy.GetParameterAsText(0)
config_file = arcpy.GetParameterAsText(1)
auth_doc_directory = arcpy.GetParameterAsText(2)
out_dir = arcpy.GetParameterAsText(3)
open_output = arcpy.GetParameterAsText(4)

file_path = processLayer(input_layer,config_file,out_dir,auth_doc_directory)

if open_output:
    notepadOpen(file_path)
 
