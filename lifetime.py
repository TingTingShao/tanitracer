#!/usr/bin/env python

import os, sys, argparse, pandas, numpy
from taniclass import spotfilter

# prepare filter
filter = spotfilter.SpotFilter()

# defaults
input_filename = None
output_filename = None
count_modes = ['regression', 'lifetime', 'counting']
selected_mode = count_modes[0]
lifetime_span = [1, 20]
lifetime_sum_every = 1
count_plane = 0
start_regression = 0
time_scale = 1
center_quadrant = False
center_x = [120, 380]
center_y = [80, 320]

# parse arguments
parser = argparse.ArgumentParser(description='count lifetime using regression.', \
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-o', '--output-file', nargs=1, default = None, \
                    help='output tsv file name ([basename].txt if not specified)')

group = parser.add_mutually_exclusive_group()
group.add_argument('-R', '--regression', action='store_const', default=selected_mode, \
                    dest='selected_mode', const=count_modes[0], \
                    help='count using regression (default)')
group.add_argument('-L', '--lifetime', action='store_const', \
                    dest='selected_mode', const=count_modes[1], \
                    help='count using lifetime')
group.add_argument('-C', '--counting', action='store_const', \
                    dest='selected_mode', const=count_modes[2], \
                    help='count spots withoug tracking')

parser.add_argument('-x', '--time-scale', nargs = 1, type = float, \
                    metavar = ('SCALE'), default=[time_scale], \
                    help='interval of time-lapse (in seconds)')

parser.add_argument('-l', '--lifetime-span', nargs = 2, type = int, \
                    metavar = ('START', 'END'), default = lifetime_span, \
                    help='specify the span to coung using lifetime (start >= 1)')
parser.add_argument('-e', '--lifetime-sum-every', nargs = 1, type = int, \
                    metavar = ('X'), default = [lifetime_sum_every], \
                    help='sum lifetime every X plane')
parser.add_argument('-r', '--start-regression', nargs = 1, type = int, \
                    metavar = ('PLANE'), default=[start_regression], \
                    help='specify the plane to start regression')
parser.add_argument('-c', '--count-plane', nargs = 1, type = int, \
                    metavar = ('PLANE'), default=[count_plane], \
                    help='specify the plane to count spots')

parser.add_argument('-Q', '--center-quadrant', action = 'store_true', default = center_quadrant, \
                    help = 'use spots of center area')

parser.add_argument('input_file', nargs=1, default=input_filename, \
                    help='input multpage-tiff file to plot markers')

args = parser.parse_args()

# set arguments
input_filename = args.input_file[0]

fileext = os.path.splitext(os.path.basename(input_filename))[1].lower()
if (fileext == '.stk') or (fileext == '.tif'):
    input_filename = os.path.splitext(os.path.basename(input_filename))[0] + '.txt'
    print("Reading %s instead of %s." % (input_filename, args.input_file[0]))

selected_mode = args.selected_mode
count_plane = args.count_plane[0]
start_regression = args.start_regression[0]
lifetime_span = args.lifetime_span
lifetime_sum_every = args.lifetime_sum_every[0]
time_scale = args.time_scale[0]
center_quadrant = args.center_quadrant

if lifetime_span[0] < 1:
    raise Exception('lifetime starting plane must be >= 1')

if args.output_file is None:
    if selected_mode == 'lifetime':
        output_filename = os.path.splitext(os.path.basename(input_filename))[0] + '_liftime.txt'
    elif selected_mode == 'regression':
        output_filename = os.path.splitext(os.path.basename(input_filename))[0] + '_regression.txt'
    elif selected_mode == 'counting':
        output_filename = os.path.splitext(os.path.basename(input_filename))[0] + '_counting.txt'
    else:
        raise Exception('invalid counting mode')

    if input_filename == output_filename:
        raise Exception('input_filename == output_filename')
else:
    output_filename = args.output_file[0]

# read results, sort, and RESET index (important)
spot_table = pandas.read_table(input_filename, comment = '#')
spot_table = spot_table.sort_values(by = ['total_index', 'plane']).reset_index(drop=True)

# lifetime or regression
if selected_mode == 'regression':
    # spots to be counted
    if center_quadrant is True:
        index_set = set(spot_table[(spot_table.plane == start_regression) & \
                                   (center_x[0] <= spot_table.x) & (spot_table.x < center_x[1]) & \
                                   (center_y[0] <= spot_table.y) & (spot_table.y < center_y[1])].total_index.tolist())
    else:
        index_set = set(spot_table[spot_table.plane == start_regression].total_index.tolist())

    print(index_set)
    # regression
    output_indexes = []
    output_counts = []
    for index in range(start_regression, spot_table.plane.max() + 1):
        spot_count = len(spot_table[(spot_table.total_index.isin(index_set)) & (spot_table.plane == index)])
        if spot_count == 0:
            break
        output_indexes += [index]
        output_counts += [spot_count]

    # prepare data
    output_columns = ['lifecount', 'lifetime', 'regression']
    output_times = [i * time_scale for i in output_indexes]

elif selected_mode == 'lifetime':
    # calculate lifetime
    spot_table = filter.calculate_lifetime(spot_table)
    spot_table = filter.keep_first_spots(spot_table)
    spot_table = spot_table[(lifetime_span[0] <= spot_table.plane) & \
                            (spot_table.plane <= lifetime_span[1])].reset_index(drop=True)

    if center_quadrant is True:
        spot_table = spot_table[(center_x[0] <= spot_table.x) & (spot_table.x < center_x[1]) & \
                                (center_y[0] <= spot_table.y) & (spot_table.y < center_y[1])].reset_index(drop=True)
        print(spot_table)

    # prepare data
    output_columns = ['lifecount', 'lifetime', 'spotcount']
    lifecount_max = spot_table.lifetime.max()
    if lifetime_sum_every == 1:
        output_indexes = [i for i in range(1, lifecount_max + 1)]
        output_times = [i * time_scale for i in output_indexes]
        output_counts = [len(spot_table[spot_table.lifetime == i]) for i in output_indexes]
    else:
        output_indexes = [i * lifetime_sum_every for i in range(1, ((lifecount_max - 1) // lifetime_sum_every) + 2)]
        output_times = [i * time_scale for i in output_indexes]
        output_counts = [len(spot_table[((i - lifetime_sum_every) < spot_table.lifetime) & (spot_table.lifetime <= i)]) \
                         for i in output_indexes]

elif selected_mode == 'counting':
    # prepare data
    output_columns = ['plane', 'lifetime', 'spots']
    plane_max = spot_table.plane.max()
    output_indexes = [i for i in range(1, plane_max + 1)]
    output_times = [i * time_scale for i in output_indexes]
    output_counts = [len(spot_table[spot_table.plane == i]) for i in output_indexes]

else:
    raise Exception('invalid counting mode')

output_table = pandas.DataFrame({ \
                    output_columns[0] : output_indexes, \
                    output_columns[1] : output_times, \
                    output_columns[2] : output_counts}, \
                    columns = output_columns)

output_table.to_csv(output_filename, sep='\t', index=False)
print(output_table)
