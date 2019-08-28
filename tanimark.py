#!/usr/bin/env python

import os, sys, argparse, pandas, numpy
from taniclass import spotmarker
from skimage.external import tifffile

# prepare spot marker
marker = spotmarker.SpotMarker()

# defaults
input_filename = None
marker_filename = None
output_filename = None

# parse arguments
parser = argparse.ArgumentParser(description='plot centroids to check gaussian fitting.', \
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-o', '--output-file', nargs=1, default=output_filename, \
                    help='output multipage-tiff file ([basename]_marked.tif if not specified)')

parser.add_argument('-f', '--marker-file', nargs=1, default=marker_filename, \
                    help='read marker tsv file ([basename].txt if not specified)')
parser.add_argument('-z', '--marker-size', nargs=1, type=int, default=[marker.marker_size], \
                    help='marker size to plot')
parser.add_argument('-c', '--marker-colors', nargs=3, type=str, default=marker.marker_colors, \
                    metavar=('NEW', 'CONT', 'END'), \
                    help='marker colors for new/continued/end spots')
parser.add_argument('-r', '--rainbow-colors', action='store_true', default=marker.rainbow_colors, \
                    help='use rainbow colors')

parser.add_argument('-R', '--mark-regression', action='store_true', default=marker.mark_regression, \
                    help='mark in regression')
parser.add_argument('-E', '--force-mark-emerge', action='store_true', default=marker.force_mark_emerge, \
                    help='force marking emerging spots in regression')

parser.add_argument('-i', '--invert-image', action='store_true', default=marker.invert_image, \
                    help='invert image look-up table')

parser.add_argument('input_file', nargs=1, default=input_filename, \
                    help='input multpage-tiff file to plot markers')

args = parser.parse_args()

# set arguments
input_filename = args.input_file[0]
marker.marker_size = args.marker_size[0]
marker.marker_colors = args.marker_colors
marker.marker_rainbow = args.rainbow_colors
marker.invert_image = args.invert_image
marker.mark_regression = args.mark_regression
marker.force_mark_emerge = args.force_mark_emerge

if args.marker_file is None:
    marker_filename = os.path.join(os.path.dirname(input_filename),\
                      os.path.splitext(os.path.basename(input_filename))[0] + '.txt')
else:
    marker_filename = args.marker_file[0]
    fileext = os.path.splitext(os.path.basename(marker_filename))[1].lower()
    if (fileext == '.stk') or (fileext == '.tif'):
        marker_filename = os.path.splitext(os.path.basename(marker_filename))[0] + '.txt'
        print("Reading %s instead of %s." % (marker_filename, args.marker_file[0]))

if args.output_file is None:
    output_filename = os.path.splitext(os.path.basename(input_filename))[0] + '_marked.tif'
    if input_filename == output_filename:
        raise Exception('input_filename == output_filename')
else:
    output_filename = args.output_file[0]

# read image
orig_image = tifffile.imread(input_filename)
if len(orig_image.shape) == 2:
    orig_image = numpy.array([orig_image])

# convert image to 8-bit RGB color
image_color = marker.convert_to_color(orig_image)

# read results
print("Read spots from %s." % (marker_filename))
spot_table = pandas.read_csv(marker_filename, comment = '#', sep = '\t')

# mark tracking status
print("Marked %d spots on %s." % (len(spot_table), input_filename))
image_color = marker.mark_spots(image_color, spot_table)

# output multipage tiff
print("Output image file to %s." % (output_filename))
tifffile.imsave(output_filename, image_color)
