#!/usr/bin/env python

import os, platform, sys, glob, argparse
import numpy, pandas, tifffile
from taniguchi import alignsift
from PIL import Image

# prepare aligner
aligner = alignsift.AlignSift()

# defaults
input_filenames = None
output_tsv_filename = 'align.txt'
output_image = False
output_image_filename = None
reference_image_filename = None
invert_image = False

parser = argparse.ArgumentParser(description='Calculate misalignment using SIFT algorithm', \
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-f', '--output-tsv-file', nargs=1, default = [output_tsv_filename], \
                    help='output tsv file name (alignment.txt if not specified)')

parser.add_argument('-r', '--reference-image', nargs=1, default = [reference_image_filename], \
                    help='reference image file name (first plane is used)')

parser.add_argument('-O', '--output-image', action='store_true', default=output_image, \
                    help='output image tiff')
parser.add_argument('-o', '--output-image-file', nargs=1, default = None, \
                    help='output image file name([basename]_aligned.tif if not specified)')

parser.add_argument('-i', '--invert-image', action='store_true', default=invert_image, \
                    help='invert image LUT')

parser.add_argument('input_file', nargs='+', default=None, \
                    help='input multpage-tiff file(s) to align')
args = parser.parse_args()

# collect input filenames
if (platform.system() == "Windows"):
    input_filenames = []
    for pattern in args.input_file:
        input_filenames.extend(sorted(glob.glob(pattern)))
else:
    input_filenames = args.input_file

# set arguments
output_tsv_file = args.output_tsv_file[0]
invert_image = args.invert_image
reference_image_filename = args.reference_image[0]

output_image = args.output_image
if args.output_image_file is None:
    output_image_filename = os.path.splitext(os.path.basename(input_filenames[0]))[0] + '_aligned.tif'
    if output_image_filename in args.input_file:
        raise Exception('input_filename == output_filename')
else:
    output_image_filename = args.output_image_file[0]

# read input image(s)
image_list = []
for input_filename in input_filenames:
    images = tifffile.imread(input_filename)
    if len(images.shape) == 2:
        image_list += [images]
    else:
        image_list += [images[i] for i in range(len(images))]

orig_images = numpy.asarray(image_list)

# make 8bit image (required for sift algorithm)
images_uint8 = aligner.convert_to_uint8(orig_images)
if invert_image is True:
    images_uint8 = 255 - images_uint8

# read reference image
reference_uint8 = None
if reference_image_filename is not None:
    image = tifffile.imread(reference_image_filename)
    if len(images.shape) > 2:
        image = image[0]
    reference_uint8 = aligner.convert_to_uint8(images)
    if invert_image is True:
        reference_uint8 = 255 - reference_uint8

# alignment
results = aligner.calculate_alignments(images_uint8, reference_uint8)

# open tsv file and write header
output_tsv_file = open(output_tsv_filename, 'w', newline='')
aligner.output_header(output_tsv_file, input_filenames[0], reference_image_filename)
output_tsv_file.write('\t'.join(results.columns) + '\n')

# output result and close
results.to_csv(output_tsv_file, columns = results.columns, \
               sep='\t', index = False, header = False, mode = 'a')
output_tsv_file.close()
print("Output alignment tsv file to %s." % (output_tsv_filename))

# output image
if output_image is True:
    output_image_array = numpy.zeros(images_uint8.shape, dtype=numpy.uint8)
    
    for row, align in results.iterrows():
        plane = results.plane[row]
        if plane not in range(len(images_uint8)):
            print("Skip plane %d due to out-of-range." % (results.plane[row]))
            continue

        image = Image.fromarray(images_uint8[plane])
        image = image.rotate(0, translate=(int(-align.x), int(-align.y)))
        output_image_array[plane] = numpy.asarray(image, dtype=numpy.uint8)

    # output multipage tiff
    print("Output image file to %s." % (output_image_filename))
    tifffile.imsave(output_image_filename, output_image_array)

