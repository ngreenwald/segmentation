import numpy as np
import xarray as xr
import pandas as pd
import skimage.measure
import scipy
import os
import xarray as xr
import copy

from random import seed
from random import randint
from segmentation.utils import spatial_analysis_utils as sau
from segmentation.utils import visualize as viz
from scipy.spatial.distance import cdist
from skimage.measure import label


def direct_init_dist_matrix(num_A=100, num_B=100, num_C=100,
                            distr_AB=(10, 1), distr_random=(200, 1),
                            seed=None):
    """
    This function will return a random dist matrix specifying the distance between cells of
    types A and B and between cells of all other groups (type C)

    Each row and column representing a cell.
    We generate the points using Gaussian distributions
    Ideally, the parameters for A to B distances will be set such that they produce a lower range of values
    than A to C distances.

    Args:
        num_A: the number of A cells we wish to generate. Default 100
        num_B: the number of B cells we wish to generate. Default 100
        num_C: the number of C cells we wish to generate. Default 100
        distr_AB: if specified, will be a tuple listing the mean and variance of the Gaussian distribution
            we wish to generate numbers from. Default mean=10 and var=1
        distr_random: similar to dist_AB, except it's what we set the distribution of
            all other distances to be. Default mean=200 and var=1
        seed: whether to fix the random seed or not. Useful for testing.
            Should be a specified integer value. Default None.

    Returns:
        dist_mat: the randomized distance matrix we generate directly from predefined distributions
            where the average distances between cell types of a and b > average distances between
            cell types of b and c
    """

    # set the mean and variance of the Gaussian distributions of both AB and AC distances
    mean_ab = distr_AB[0]
    var_ab = distr_AB[1]

    mean_random = distr_random[0]
    var_random = distr_random[1]

    # set random seed if set
    if seed:
        np.random.seed(seed)

    # we initialize the random distances across different types of points
    # note that we don't really care about aa, bb, bc, or cc, so we
    # initialize those to garbage. We do need them for a proper
    # distance matrix format, however.
    random_aa = np.abs(np.random.normal(mean_random, var_random, (num_A, num_A)))
    random_ab = np.abs(np.random.normal(mean_ab, var_ab, (num_A, num_B)))
    random_ac = np.abs(np.random.normal(mean_random, var_random, (num_A, num_C)))
    random_bb = np.abs(np.random.normal(mean_random, var_random, (num_B, num_B)))
    random_bc = np.abs(np.random.normal(mean_random, var_random, (num_B, num_C)))
    random_cc = np.abs(np.random.normal(mean_random, var_random, (num_C, num_C)))

    # create each partition one-by-one first
    # we need to correct each aa, bb, and cc matrix to ensure symmetry
    a_partition = np.concatenate(((random_aa + random_aa.T) / 2, random_ab, random_ac), axis=1)
    b_partition = np.concatenate((random_ab.T, (random_bb + random_bb.T) / 2, random_bc), axis=1)
    c_partition = np.concatenate((random_ac.T, random_bc.T, (random_cc + random_cc.T) / 2), axis=1)

    # then concatenate them together
    dist_mat = np.concatenate((a_partition, b_partition, c_partition), axis=0)

    # finally, fill the diagonals with 0 to ensure a proper distance matrix
    np.fill_diagonal(dist_mat, 0)

    return dist_mat


def generate_random_centroids(size_img=(1024, 1024), num_A=100, num_B=100, num_C=100,
                              mean_A_factor=None, cov_A=None, mean_B_factor=None, cov_B=None,
                              mean_C_factor=None, cov_C=None, seed=None):
    """
    Generate a set of random centroids given distribution parameters.
    Used as a helper function by point_init_dist_matrix and generate_random_cell_shapes.

    Args:
        size_img: a tuple indicating the size of the image. Default 1024 x 1024
        num_A: the number of A centroids to generate. Default 100.
        num_B: the number of B centroids to generate. Default 100.
        num_C: the number of C centroids to generate. Default 100.

        mean_A_factor: a tuple to determine which number to multiply the height and width by
            to indicate the center (mean) of the distribution to generate A points.
            Will be randomly set to a predefined value if None.
        cov_A: the covariance used to generate A poins in the format [[varXX, varXY], [varYX, varYY]].
            Will be randomly set to a predefined value if None.
        mean_B_factor: similar to mean_A_factor
        cov_B: similar to cov_A
        mean_C_factor: similar to mean_A_factor
        cov_C: similar to cov_A

        seed: whether to fix the random seed or not. Useful for testing.
            Should be a specified integer value. Default None.

    Returns:
        total_points: a list of non-duplicated cell centroids.
    """

    # extract the height and width
    height = size_img[0]
    width = size_img[1]

    a_mean = (height * mean_A_factor, width * mean_A_factor) if mean_A_factor else (0.5, 0.5)
    a_cov = cov_A if cov_A else [[200, 0], [0, 200]]

    b_mean = (height * mean_B_factor, width * mean_B_factor) if mean_B_factor else (0.6, 0.6)
    b_cov = cov_B if cov_B else [[200, 0], [0, 200]]

    c_mean = (height * mean_C_factor, width * mean_C_factor) if mean_C_factor else (0.1, 0.1)
    c_cov = cov_C if cov_C else [[200, 0], [0, 200]]

    # if specified, set the random seed
    if seed:
        np.random.seed(seed)

    # use the multivariate_normal distribution to generate the points
    # because we're passing these into skimage.measure.label, it is important
    # that we convert these to integers beforehand
    # since label only takes a binary matrix
    a_points = np.random.multivariate_normal(a_mean, a_cov, num_A).astype(np.int16)
    b_points = np.random.multivariate_normal(b_mean, b_cov, num_B).astype(np.int16)
    c_points = np.random.multivariate_normal(c_mean, c_cov, num_C).astype(np.int16)

    # combine the points together into one list
    total_points = np.concatenate((a_points, b_points, c_points), axis=0)

    # remove points with negative values since they're out of range
    total_points = total_points[np.logical_and(sample_arr[:, 0] >= 0, sample_arr[:, 1] >= 0), :]

    # remove points with values greater than the size_img dimensions since they're out of range
    total_points = total_points[np.logical_and(sample_arr[:, 0] < size_img[0], sample_arr[:, 1] < size_img[1]), :]

    # this ensures that we only keep the points that are not duplicate across different cell types
    non_dup_points, non_dup_counts = np.unique(total_points, axis=0, return_counts=True)
    total_points = non_dup_points[non_dup_counts == 1]

    return total_points


def point_init_dist_matrix(size_img=(1024, 1024), num_A=100, num_B=100, num_C=100,
                           mean_A_factor=None, cov_A=None, mean_B_factor=None, cov_B=None,
                           mean_C_factor=None, cov_C=None, seed=None):
    """
    This function generates random centroid centers in the form of a label map
    such that those of type A will have centers closer on average to those of type B
    than those of type C

    We will use a multivariate Gaussian distribution for A, B, and C type cells to generate their respective centers.

    Args:
        size_img: a tuple indicating the size of the image. Default 1024 x 1024
        num_A: the number of A centroids to generate. Default 100.
        num_B: the number of B centroids to generate. Default 100.
        num_C: the number of C centroids to generate. Default 100.

        mean_A_factor: a tuple to determine which number to multiply the height and width by
            to indicate the center (mean) of the distribution to generate A points.
            Will be randomly set to a predefined value if None.
        cov_A: the covariance used to generate A poins in the format [[varXX, varXY], [varYX, varYY]].
            Will be randomly set to a predefined value if None.
        mean_B_factor: similar to mean_A_factor
        cov_B: similar to cov_A
        mean_C_factor: similar to mean_A_factor
        cov_C: similar to cov_A

        seed: whether to fix the random seed or not. Useful for testing.
            Should be a specified integer value. Default None.

    Returns:
        sample_img_xr: the data in xarray format containing the randomized label matrix
            based on the randomized centroid centers we generated. The label mat portion
            of sample_img_xr is generated from a randomly initialized set of cell centroids
            where those of type a are on average closer to those of type b than they
            are to those of type c.
    """

    # generate the list of centroids and zip them into x and y coords
    all_centroids = \
        generate_random_centroids(size_img=size_img, num_A=num_A, num_B=num_B, num_C=num_C,
                                  mean_A_factor=mean_A_factor, cov_A=cov_A,
                                  mean_B_factor=mean_B_factor, cov_B=cov_B,
                                  mean_C_factor=mean_C_factor, cov_C=cov_C,
                                  seed=seed)

    point_x_coords, point_y_coords = zip(*all_centroids)

    # to compute the indices of the original centroid locations, needed to adjust the distance matrix
    # back to what it was because calc_dist_matrix automatically sorts the centrodis by ascending order
    centroid_indices = np.lexsort(all_centroids[:, ::-1].T)

    # generate the label matrix for the image
    # doing it this way because using the label function in skimage does so based on
    # connected components and that messes up the regionprops call in calc_dist_matrix
    # we don't want to assume that we won't get points of distance 1 away from each other
    # so we can just use the labels generated from centroid_indices to assign this
    label_mat = np.zeros(size_img)
    label_mat[point_x_coords, point_y_coords] = centroid_indices + 1

    # now generate the sample xarray
    sample_img = np.zeros((1, size_img[0], size_img[1], 1)).astype(np.int16)
    sample_img[0, :, :, 0] = copy.deepcopy(label_mat)
    sample_img_xr = xr.DataArray(sample_img,
                                 coords=[[1], range(size_img[0]), range(size_img[1]), ['segmentation_label']],
                                 dims=['fovs', 'rows', 'cols', 'channels'])

    # and return the xarray to pass into calc_dist_matrix
    return sample_img_xr, centroid_indices
