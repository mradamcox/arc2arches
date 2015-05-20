# arc2arches
Convert ESRI spatial data formats to the .arches format for upload to an Arches v3 deployment. Arc2arches includes an ESRI toolbox (.tbx) for use in ArcMap or ArcCatalog with tools that will help to configure and ultimately convert input datasets (any dataset read by arcpy, such as a file geodatabase table or shapefile) to the .arches format.  Once a .arches file has been created, you can upload it to arches usings the built-in arches command line operations (python manage.py packages -o load_resources -s path/to/.arches/file)

# dependencies
The arc2arches tools require two non-standard python packages: unicodecsv and pyshp.  The best way to fill these dependencies is install these packages with pip or easy_install.  This is the recommended route, because it's good to understand pip/easy_install and will be useful in the future.  Information on installing python packages can be found here: https://packaging.python.org/en/latest/installing.html or here: https://pythonhosted.org/setuptools/easy_install.html.

However, for ease of use, these packages have been included in the arc2arches package, so if you do not want to add those packages to your python installation (or don't have permission),  you can just skip this step and the tools will use the packages that have already been included.  

## simple use
Download and unzip (or clone or fork) this repository.  Using ArcMap or ArcCatalog, navigate to the .tbx that is in the archestools directory.

1. Create a "conflig" file to accompany the dataset you plan to convert
2. Add groups to the conflig file to correctly map specific fields in the dataset to existing arches nodes.  Error handling has been added that relies completely on your existing autority documents, so you must set the path to those documents.  NOTE: The current tool interface only allows for the addition of 10 entity:field entries into a new group.  However, you can open the .conflig file at any time in any text editor and copy/paste/write as many entries in a group as you like.
3. Convert the datasets (multiple are fine) to .arches format. A (required) .relations file will be created as well.  The handling of relationships is described below, and is ready for improvment...

## relationships between resources
At present, you are able to automate relationships between uploaded resources in a useful but limited manor. When using the convert to .arches tool, you are able to choose a field from each input dataset whose value will be matched with values in other selected fields in other selected datasets.  At this point, all relationship types default to RELATIONSHIP_TYPE:1.  The following two examples will illustrate the good and bad qualities of the way that relationships are handled currently.

### example 1, cemetery data
There are two datasets: One with a polygon for every grave in a cemetery, and each polygon has a plot number stored in field "plot_id". The other is a geodatabase table of all the names of individuals that are interred in these graves, with the interment grave number stored in a field also named "plot_id".  Not all graves have (indentified) individuals in them, and some graves hold more than on individual.

While running the Convert to .arches tool, the "plot_id" fields are selected as the relate fields.  When the tool has finished, relationships will have been entered in the .relations file that will connect all resources that have the same plot_id value.

### example 2, building survey data
A windshield survey was carried out, and the information to make a single Activity resource to represent it in Arches is entered in a geodatabase table.  A field is added named "surv" and its value is 'windshield'.  The survey data itself is stored in a shapefile which is actually an aggregate of many building datasets. A field is added named "survname" and all building features that were part of the windshield survey are given the value "windshield" (all others left blank).

When running the tool, the "surv" and "survname" fields are chosen as relate fields for the survey table and the building shapefile, respectively.  When the conversion is finished, the .relations file will have created a relationship between EVERY resource that had the same value in the relate fields.  This means that in addition to each building being associated with the windshield survey activity resource, it is also related to every other building that was part of the survey.  In this case, editing was done directly to the resulting .relations file in excel to remove all unwanted relationships between buildings. (Open in excel, choose "|" as the delimiter character, and then save as tab delimited csv and use notepad++ to replace all tabs with "|"...)

## standalone shp2arches.py script
This script is intended to be used in a command-line, preferably within the package root directory so the authority documents paths can be imported from settings.py.  It is in pretty rough shape.