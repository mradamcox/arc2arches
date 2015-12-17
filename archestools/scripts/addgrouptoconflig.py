import arcpy
import os
import json

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

def createGroupFromEntries(input_entries):
    """ the input entries should be a list of tuples:
    (field_name , entity_name) """

    new_dict = dict([i for i in new_entries if not i[0] == ""])
    existing_groups = parseConfligFile(input_config)[2]

    new_name = "Group{0}".format(str(len(existing_groups)+1))
    new_group = {
        new_name:new_dict
        }
    return new_group

def insertNewGroup(conflig_file,input_group):
    """ adds the input group to the input conflig file """

    with open(conflig_file) as con:
        config_contents = con.read()
    config_json = json.loads(config_contents)

    config_json["FIELD_MAP"].append(input_group)
    out_text = json.dumps(config_json,indent=4)

    with open(conflig_file,"w") as out:
        out.write(out_text)

    return conflig_file
        

input_config = arcpy.GetParameterAsText(0)
new_entries = [
    (arcpy.GetParameterAsText(4),arcpy.GetParameterAsText(3)),
    (arcpy.GetParameterAsText(6),arcpy.GetParameterAsText(5)),
    (arcpy.GetParameterAsText(8),arcpy.GetParameterAsText(7)),
    (arcpy.GetParameterAsText(10),arcpy.GetParameterAsText(9)),
    (arcpy.GetParameterAsText(12),arcpy.GetParameterAsText(11))
    ]

group = createGroupFromEntries(new_entries)
output_file = insertNewGroup(input_config,group)




