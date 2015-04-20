import os
import argparse
import shapefile
import json
import subprocess

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

def processSHP(infile):
    """ process the input shapefile """

    outfile = os.path.splitext(infile)[0]+".arches"
    relations = os.path.splitext(infile)[0]+".relations"
    config = os.path.splitext(infile)[0]+".conflig"

    if not os.path.isfile(relations):
        with open(relations,"wb") as rel:
            rel.write("RESOURCEID_FROM|RESOURCEID_TO|START_DATE"\
                "|END_DATE|RELATION_TYPE|NOTES\r\n")
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
    checkFieldsInConfig(config_fields,shp_fields)
    f_index = makeFieldIndex(config_fields,shp)

    ## print intro summary
    print "FROM:", os.path.basename(infile)
    print "TO:", os.path.basename(outfile)
    print "CONFLIGURATION:", os.path.basename(config)
    print "\nresource type:", res_type
    print "shape type:", shp_type
    print "field mapping:\n  (shape field --> arches entity)"
    cnt = 1
    for group in groups:
        print "  ~ group", cnt
        for k,v in group.iteritems():
            print "      {0} --> {1}".format(k,v)
        cnt+=1

    resourceid = 100000
    groupid = 300000

    ## print file
    with open(outfile,"wb") as arches:
        arches.write("RESOURCEID|RESOURCETYPE|ATTRIBUTENAME|ATTRIBUTEVALUE|GROUPID\r\n")
        for rec in shp.shapeRecords():
            wkt = getWKT(rec.shape,shp_type)
            arches.write("{0}|{1}|{2}|{3}|{4}\r\n".format(
                resourceid,res_type,"SPATIAL_COORDINATES_GEOMETRY.E47",wkt,groupid))
                
            for group in groups:
                groupid+=1
                for f_in, f_out in group.iteritems():
                    value = rec.record[f_index[f_in]]
                    if value.rstrip() == '':
                        continue
                    arches.write("{0}|{1}|{2}|{3}|{4}\r\n".format(
                        resourceid,res_type,f_out,value,groupid))
            groupid+=1
            resourceid+=1

    return outfile    
    
parser = argparse.ArgumentParser(description=
        """Converts a shapefile into a .arches file, used to load data into
an Arches (v3.0) installation.  Requires an accompanying .conflig file (an
augmented version of the original .config  format) to handle field mapping.""",
                                 epilog="get ready to go!")

## EXAMPLE ARGS
##parser.add_argument('--sum', dest='accumulate', action='store_const',
##                   const=sum, default=max,
##                   help='sum the integers (default: find the max)')
##parser.add_argument('--p', dest='path', action='store_const',
##                   const=sum, default=max,
##                   help='print something if you want')


parser.add_argument("shapefile",help="path to shapefile")

parser.add_argument("-of",dest="openup",default=True,
                    help="open output file on completion (default=True)")

args = parser.parse_args()

file_path = processSHP(args.shapefile)
if args.openup:
    notepadOpen(file_path)
 
