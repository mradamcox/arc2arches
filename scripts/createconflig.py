import arcpy
import os

in_dataset = arcpy.GetParameterAsText(0)
out_dir = arcpy.GetParameterAsText(1)
resource_type = arcpy.GetParameterAsText(3)

template_text = '{'+\
'\n    "DATASET_PATH": "{0}",'.format(in_dataset.replace("\\","/"))+\
'\n    "RESOURCE_TYPE": "{0}",'.format(resource_type)+\
'\n    "GEOM_TYPE": "SPATIAL_COORDINATES_GEOMETRY.E47",'+\
'\n    "FIELD_MAP": ['+\
'\n    ]'+\
'\n}'

ds_name = os.path.basename(in_dataset)
if os.path.splitext(ds_name)[1] != "":
    ds_name = os.path.splitext(ds_name)[0]
out_file = os.path.join(out_dir,ds_name+".conflig")

with open(out_file,"w") as out:
    out.write(template_text)
