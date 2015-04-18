import os
import argparse

parser = argparse.ArgumentParser(description=
                "collect arguments for shp2arches.py", epilog="get ready to go!")

##
##parser.add_argument('--sum', dest='accumulate', action='store_const',
##                   const=sum, default=max,
##                   help='sum the integers (default: find the max)')
##
##parser.add_argument('--p', dest='path', action='store_const',
##                   const=sum, default=max,
##                   help='print something if you want')

parser.add_argument("shapefile",help="input path to shapefile")

parser.add_argument("-ow",dest="overwrite",default=True,
                    help="input path to shapefile")

args = parser.parse_args()

inputfile = args.inputfile
overwrite = args.overwrite

print "overwrite: ",overwrite

if os.path.isfile(inputfile):
    print True

else:
    print False



##print(args.accumulate(args.integers))
