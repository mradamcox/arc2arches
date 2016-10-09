import os
import argparse
import json
import subprocess
import csv
import sys
import arcpy
import itertools

## prefer site-packages modules, use local ones if necessary
try:
    import shapefile
except:
    import shapefile_local as shapefile
try:
    import unicodecsv
except:
    import unicodecsv_local as unicodecsv

def checkSpatialReference(dataset):
    """ makes sure the dataset is in EPSG: 4326 (GCS WGS84) """
    sr = arcpy.Describe(dataset).spatialReference
    wgs84 = arcpy.SpatialReference(4326)

    if sr != wgs84:
        arcpy.AddError("""
  This dataset does not have the correct spatial reference, EPSG 4326 (GCS
  WSG 1984).  Project the dataset to this coordinate system before continuing.
  """)
        exit()

    return True

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
    try:
        config_json = json.loads(config_contents)
    except:
        arcpy.AddMessage(conflig_path)
    
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

def convertTypeValue(input_value,auth_dict,fieldname,dataset):
    """ takes the input value, and compares it with the authority document
    dictionary.  if the value is a Preflabel, the corresponding conceptid
    is returned.  if it is already a conceptid, that id is returned."""
    conceptids = auth_dict.keys()
    conceptids.sort(key=lambda x: int(x.split(":")[-1]))
    labels = auth_dict.values()

    if labels.count(input_value) > 1:
        arcpy.AddError("""
  There are two or more corresponding concept ids for this Preflabel.
  You'll have to find the correct conceptid and apply it to the original
  dataset.
    PROBLEM: {0}
    AUTHORITY DOCUMENT CONTENTS:""".format(input_value))
        for k in conceptids:
            arcpy.AddError("      {0} | {1}".format(k,auth_dict[k])) 
        exit()

    conceptid = False
    if input_value in auth_dict.keys():
        conceptid = input_value

    else:
        for k,v in auth_dict.iteritems():
            if v.rstrip() == input_value.rstrip():
                conceptid = k
                break

    if not conceptid:
        dataset_name = os.path.basename(dataset)
        arcpy.AddError("""
  The value listed below can not be reconciled with the Preflabels or
  conceptids that are available for this entity type.  Double-check your
  original data and conflig files before trying again.
    DATASET: {0}
    FIELD: {1}
    VALUE: {2}
    AUTHORITY DOCUMENT CONTENTS:
      conceptid | Preflabel""".format(dataset_name,fieldname,input_value))
        for k in conceptids:
            arcpy.AddError("      {0} | {1}".format(k,auth_dict[k]))                                   
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
        for row in rows:
            auth_dict[row['conceptid']] = row['Preflabel']

    return auth_dict

def makeEntityAuthDocDict(auth_doc_directory):
    """ makes a dictionary of the items in the ENTITY_TYPE_X_ADOC.csv file """

    entity_auth = os.path.join(auth_doc_directory,"ENTITY_TYPE_X_ADOC.csv")
    if not os.path.isfile(entity_auth):
        arcpy.AddError("""
  Unable to locate the ENTITY_TYPE_X_ADOC.csv document.  This document must be
  present and correctly named in the authority document directory in order for
  you to continue.
    AUTHORITY DOCUMENT DIRECTORY: {0}""".format(
      auth_doc_directory))
        exit()

    entity_auth_dict = {}
    with open(entity_auth, 'rU') as f:
        fields = ['entitytype','authoritydoc','authoritydocconceptschemename']
        rows = unicodecsv.DictReader(f, fieldnames=fields,
            encoding='utf-8-sig', delimiter=',', restkey='ADDITIONAL',
                                     restval='')
        rows.next()
        for row in rows:
            entity_auth_dict[row['entitytype']] = os.path.join(
                auth_doc_directory,row['authoritydoc'])

    missing = [v for v in entity_auth_dict.values() if not os.path.isfile(v)]
    if len(missing) > 0:
        arcpy.AddError("""
  The authority documents listed below are used in ENTITY_TYPE_X_ADOC.csv, but
  do not exist in the authority document directory.  Fix this problem before
  trying again.""")
        for m in missing:
            arcpy.AddError("    {0}".format(os.path.basename(m)))               
        exit()

    return entity_auth_dict

def makeRelationsFile(arches_file,relation_dict):
    """ makes an empty relations file to match the given arches file """

    arcpy.AddMessage("\ncreating relations file")
    
    relation_type = "RELATIONSHIP_TYPE:1"
    relations = os.path.splitext(arches_file)[0]+".relations"
    with open(relations,"wb") as rel:
        rel.write("RESOURCEID_FROM|RESOURCEID_TO|START_DATE"\
            "|END_DATE|RELATION_TYPE|NOTES\r\n")
        if len(relation_dict.keys()) == 0:
            print "no relationships to write"
            return

        for k in sorted(relation_dict.keys()):
            v = relation_dict[k]
            for a, b in itertools.combinations(v,2):
                rel.write("{0}|{1}|||{2}|\r\n".format(
                a,b,relation_type,""))
    arcpy.AddMessage("\n  finished")
    return

def createArchesFile(input_dataset,out_dir):
    """ creates basic .arches file with only header rows printed """

    ds_name = os.path.basename(input_dataset)
    if os.path.splitext(ds_name)[1] != "":
        ds_name = os.path.splitext(ds_name)[0]
    outfile = os.path.join(out_dir,ds_name+".arches")
    
    with open(outfile,"wb") as arches:
        arches.write(
            "RESOURCEID|RESOURCETYPE|ATTRIBUTENAME|ATTRIBUTEVALUE|GROUPID\r\n")
    return outfile

def getCounts(arches_file):
    """ gets the current resourceid and groupid for the input .arches file """

    with open(arches_file,"r") as f:
        lines = tuple(f)
        long_resourceid = lines[-1].split("|")[0]
        if long_resourceid == "RESOURCEID":
            resourceid = 100000
            groupid = 300000
        else:
            resourceid = long_resourceid.split("-")[1]
            groupid = lines[-1].split("|")[-1].rstrip("\r\n")
            
    return (int(resourceid),int(groupid))

def checkForGeom(dataset):
    """ returns true if this is a spatial dataset, false if table """
    
    spatial = False
    if "Shape" in [f.name for f in arcpy.ListFields(dataset) if f.required]:
        spatial = True
    return spatial

def printSummary(input_dataset,config_file):
    """ creates little print summary of the input dataset """

    ## get shape type
    shp_type = "NON-SPATIAL"
    if checkForGeom(input_dataset):
        shp_type = getShapeType(input_dataset)

    ## get config info
    result = parseConfligFile(config_file)
    res_type,config_fields,groups =  result[0],result[1],result[2]

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

def processLayer(input_data,arches_file,entity_auth_dict,relate_dict={}):
    """ process the input shapefile """

    inlayer = input_data[0]
    config = input_data[1]
    relate_key = input_data[2]
    dataset_name = os.path.splitext(os.path.basename(inlayer))[0]

    arcpy.AddMessage("\nprocessing: "+inlayer)

    ## get info from conflig file
    result = parseConfligFile(config)
    res_type,config_fields,groups =  result[0],result[1],result[2]

    ## build field list
    fc_fields = [f.name for f in arcpy.ListFields(inlayer)]
    if relate_key != "":
        fc_fields.append(relate_key)
        config_fields.append(relate_key)

    ## compare config and dataset fields
    checkFieldsInConfig(config_fields,fc_fields)

    ## add geometry as WKT field if spatial
    spatial = checkForGeom(inlayer)
    if spatial:    
        config_fields.append("SHAPE@WKT")

    ## dictionary of created authority document dictionaries
    auth_dict_dict = {}              

    ## get current id counts from existing .arches file
    counts = getCounts(arches_file)
    resourceid, groupid = counts[0]+1, counts[1]+1

    ## print first input dataset
    with open(arches_file,"ab") as arches:
        with arcpy.da.SearchCursor(inlayer,config_fields) as rows:
            for row in rows:
                
                long_resourceid = dataset_name+"-"+str(resourceid)

                #first, write geometry row
                if spatial:
                    wkt = row[-1]
                    arches.write("{0}|{1}|{2}|{3}|{4}\r\n".format(
        long_resourceid,res_type,"SPATIAL_COORDINATES_GEOMETRY.E47",wkt,groupid))

                #next, loop through fields and add values
                for group in groups:
                    groupid+=1
                    for f_in, entity in group.iteritems():

                        raw_value = row[config_fields.index(f_in)]
                        if raw_value == None:
                            continue
                        if raw_value.rstrip() == '':
                            continue

                        ## make it unicode?
                        value = raw_value.encode('utf8')

                        ## if it's a type, it may need translation
                        if entity in entity_auth_dict.keys():

                            auth_path = entity_auth_dict[entity]
                            if not entity in auth_dict_dict.keys():
                                auth_dict_dict[entity] = getAuthDict(auth_path)
                            auth_dict = auth_dict_dict[entity]
                            value = convertTypeValue(value,auth_dict,
                                        f_in,inlayer)

                        arches.write("{0}|{1}|{2}|{3}|{4}\r\n".format(
                    long_resourceid,res_type,entity,value,groupid))

                ## after writing rows, update relationship dictionary
                if relate_key != "":
                    key_val = row[config_fields.index(relate_key)]
                    if not key_val in relate_dict.keys():
                        relate_dict[key_val] = [long_resourceid]
                    else:
                        relate_dict[key_val].append(long_resourceid)                

                ## advance groupid for geometry row
                if spatial:
                    groupid+=1
                resourceid+=1

    arcpy.AddMessage("  finished")
    return relate_dict

## gather input dataset info
datasets = []
dataset_params = [3,6,9,12]
for i in dataset_params:
    if not arcpy.GetParameterAsText(i) == "":
        conflig_file = arcpy.GetParameterAsText(i)
        dataset_path = arcpy.GetParameterAsText(i+1)
        relate_field_name = arcpy.GetParameterAsText(i+2)
        info = (
            dataset_path,
            conflig_file,
            relate_field_name
        )
        datasets.append(info)

auth_doc_directory = arcpy.GetParameterAsText(0)
out_dir = arcpy.GetParameterAsText(1)
open_output = arcpy.GetParameterAsText(2)

## create empty arches file
arches_file = createArchesFile(datasets[0][0], out_dir)

## make dictionary of entities and their corresponding authority documents
entity_auth_dict = makeEntityAuthDocDict(auth_doc_directory)

## iterate all input datasets, adding each to the output arches file
relate_dict = {}
for dataset in datasets:
    relate_dict = processLayer(dataset,arches_file,entity_auth_dict,relate_dict)

## use cumulative relationship dictionary to create relations file
makeRelationsFile(arches_file, relate_dict)

if open_output:
    try:
        notepadOpen(arches_file)
    except:
        arcpy.AddWarning("Unable to find Notepad++. Please open this file "\
                         "manually:\n"+arches_file)

