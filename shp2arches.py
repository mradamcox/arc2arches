import os
import argparse
import shapefile
import json
import subprocess
import csv
import sys
import unicodecsv
import itertools

## try to get the path to the authority docs with the settings
## otherwise, hardcode path to likely location
try:
    from crip import settings
    auth_doc_directory = settings.CONCEPT_SCHEME_LOCATIONS
except:
    thisdir = os.path.dirname(sys.argv[0])
    auth_doc_directory = \
    r"E:\CRNHA_archesproject\repo\crip\crip\source_data\concepts\authority_files"

def getShapeType(reader):
    """ returns the shapetype of the input reader object """
    shp_type_dict = {
    0:"NULL",
    1:"POINT",
    3:"POLYLINE",
    5:"POLYGON",
    8:"MULTIPOINT",
    11:"POINTZ",
    13:"POLYLINEZ",
    15:"POLYGONZ",
    18:"MULTIPOINTZ",
    21:"POINTM",
    23:"POLYLINEM",
    25:"POLYGONM",
    28:"MULTIPOINTM",
    31:"MULTIPATCH"
    }

    shp_ind = reader.shapes()[0].shapeType
    shp_type = shp_type_dict[shp_ind]
    if not shp_ind in (1,3,5):
        raise Exception("{0} shapetype not supported at this time".format(
            shp_type))
    return shp_type   

def getWKT(shape,shp_type):
    """ converts a shape from the shapefile libary to WKT""" 
   
    pointlist = [" ".join([str(i) for i in coord]) for coord in shape.points]
    wkt = "{0} ({1})".format(shp_type,", ".join(pointlist))
    return wkt

def getFieldNames(reader):
    """ return list of field names """
    fieldnames = [i[0] for i in reader.fields]
    return fieldnames

def checkFieldsInConfig(config_fields,shp_fields):
    """makes sure all fields in the field map are present in the shapefile"""
    for i in config_fields:
        if not str(i) in shp_fields:
            raise Exception("Invalid field name in conflig file")
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
        raise Exception("""
  There are two or more corresponding concept ids for this Preflabel.
  You'll have to find the correct conceptid and apply it to the original
  dataset.""")

    conceptid = False
    if input_value in auth_dict.keys():
        conceptid = input_value

    else:
        for k,v in auth_dict.iteritems():
            if v == input_value:
                conceptid = k
                break

    if not conceptid:
        raise Exception("""
  The value listed below can not be reconciled with the Preflabels or
  conceptids that are available for this entity type.  Double-check your
  original data before trying again.
    PROBLEM: {0}""".format(input_value))
                        
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
        raise Exception("""
  This entity seems to need an authority document, yet no document was found.
  Double check settings.CONCEPT_SCHEME_LOCATIONS and make sure an authority
  document exists named:\n    {0}""".format(doc_name))

    return doc_path

def makeRelationsFile(arches_file,relationship_dict,relation_type):
    """ makes an empty relations file to match the given arches file """

    if not relation_type:
        relation_type = "RELATIONSHIP_TYPE:1"

    relations = os.path.splitext(arches_file)[0]+".relations"
    with open(relations,"wb") as rel:
        rel.write("RESOURCEID_FROM|RESOURCEID_TO|START_DATE"\
            "|END_DATE|RELATION_TYPE|NOTES\r\n")

        if len(relationship_dict.keys()) == 0:
            print "no relationships to write"
            return

        for k, v in relationship_dict.iteritems():
            for a, b in itertools.combinations(v,2):
                rel.write("{0}|{1}|||{2}|\r\n".format(
                a,b,relation_type,""))
                
    return

def processSHP(infile,relation_info):
    """ process the input shapefile """

    outfile = os.path.splitext(infile)[0]+".arches"
    config = os.path.splitext(infile)[0]+".conflig"
    
    if not os.path.isfile(config):
        raise Exception("no conflig file")
    if os.path.isfile(outfile):
        os.remove(outfile)

    ## access shapefile
    shp = shapefile.Reader(infile)
    shp_fields = getFieldNames(shp)
    shp_type = getShapeType(shp)

    ## access conflig file
    result = parseConfligFile(config)
    res_type,config_fields,groups =  result[0],result[1],result[2]

    ## compare config and shp information
    relation_field = relation_info[0]
    if relation_field:
        config_fields.append(relation_field)
    checkFieldsInConfig(config_fields,shp_fields)
    f_index = makeFieldIndex(config_fields,shp)

    ## print intro summary
    print """FROM: {0}
TO: {1}
CONFLIGURATION: {2}

resource type: {3}
shape type: {4}
field mapping:
  (shape field --> arches entity)""".format(os.path.basename(infile),
    os.path.basename(outfile),os.path.basename(config),res_type,shp_type)
    cnt = 1
    for group in groups:
        print "  ~ group", cnt
        for k,v in group.iteritems():
            print "      {0} --> {1}".format(k,v)
        cnt+=1

    ## dictionary of created authority document dictionaries
    auth_dict_dict = {}

    ## dictionary of related resources
    relation_dict = {}

    resourceid = 100000
    groupid = 300000

    ## print file
    with open(outfile,"wb") as arches:
        arches.write("RESOURCEID|RESOURCETYPE|ATTRIBUTENAME|ATTRIBUTEVALUE|GROUPID\r\n")
        for rec in shp.shapeRecords()[:8]:

            ## get relationship key if necessary
            if relation_field:
                key = rec.record[f_index[relation_field]]
                if not key.strip() == "":
                    if key in relation_dict.keys():
                        relation_dict[key].append(resourceid)
                    else:
                        relation_dict[key] = [resourceid]

            ## write geometry row
            wkt = getWKT(rec.shape,shp_type)
            arches.write("{0}|{1}|{2}|{3}|{4}\r\n".format(
                resourceid,res_type,"SPATIAL_COORDINATES_GEOMETRY.E47",wkt,groupid))
                
            for group in groups:
                groupid+=1
                for f_in, entity in group.iteritems():

                    value = rec.record[f_index[f_in]]
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

    makeRelationsFile(outfile,relation_dict,relation_info[1])

    return outfile    
    
parser = argparse.ArgumentParser(description=
        """Converts a shapefile into a .arches file, used to load data into
an Arches (v3.0) installation.  Requires an accompanying .conflig file (an
augmented version of the original .config  format) to handle field mapping.""",
                                 epilog="get ready to go!")

parser.add_argument("shapefile",help="path to shapefile")

parser.add_argument("-of",dest="openup",action="store_true",
                    help="open output file on completion (default=TRUE)")

parser.add_argument("-rf",dest="relation_field",
                    help="indicate a field that holds keys for related "\
                    "resources within this dataset")

parser.add_argument("-rt",dest="relation_type",
                    help="indicate the relationship type to be applied to "\
                    "all relationships")

args = parser.parse_args()

relation_info = (args.relation_field,args.relation_type)

file_path = processSHP(args.shapefile,relation_info)
if args.openup:
    notepadOpen(file_path)
 
