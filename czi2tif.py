#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# czi2tif.py

import os

import czifile
import skimage.io
import numpy as np


def read_czi(fname):
    """shape: [1, 1, channel, z, x, y, 1]"""
    return fname, czifile.imread(fname)


def arr_to_tif(fname, arr, save_dir):
    """
    fname: original filename
    arr: array from read_czi()
    save_dir: directory in which to save .tifs
    """
    fname = os.sep.join(fname.split(os.sep)[-2:])
    arr = np.squeeze(arr)
    # if arr.ndim != 4:
    #     raise ValueError(f"unexpected number of dimensions, expected 4, got {arr.ndim}")
    for channel_num, channel in enumerate(arr):
        for z_num, sub_arr in enumerate(channel):
            new_basename = fname.replace(".czi", "")
            new_basename = f"{new_basename}_ch{channel_num}_z{z_num}.tif"
            new_filename = os.path.join(save_dir, new_basename)
            os.makedirs(os.path.dirname(new_filename), exist_ok=True)
            print(f"DEBUG, saving: {new_filename}")
            skimage.io.imsave(new_filename, sub_arr)


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        "convert directory of .czi files to .tif files with the same naming convention"
    )

    parser.add_argument(
        "input_dir", 
        help="directory containing .czi images", 
        type=str
    )

    parser.add_argument(
        "output_dir",
        help="directory to save tifs",
        type=str
    )

    args = parser.parse_args()

    files = os.listdir(args.input_dir)
    files = [os.path.join(args.input_dir, i) for i in files]
    files = [i for i in files if i.endswith(".czi")]

    for file in files:
        fname, arr = read_czi(file)
        arr_to_tif(fname, arr, args.output_dir)
