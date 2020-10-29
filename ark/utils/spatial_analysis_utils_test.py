import os
import pytest
import tempfile
import numpy as np
import pandas as pd
import xarray as xr
import random
import pytest
import tempfile
from copy import deepcopy
from ark.utils import spatial_analysis_utils
from ark.utils import test_utils


def test_calc_dist_matrix():
    test_mat_data = np.zeros((2, 512, 512, 1), dtype="int")
    # Create pythagorean triple to test euclidian distance
    test_mat_data[0, 0, 20] = 1
    test_mat_data[0, 4, 17] = 2
    test_mat_data[0, 0, 17] = 3
    test_mat_data[1, 5, 25] = 1
    test_mat_data[1, 9, 22] = 2
    test_mat_data[1, 5, 22] = 3

    coords = [["1", "2"], range(test_mat_data[0].data.shape[0]),
              range(test_mat_data[0].data.shape[1]), ["segmentation_label"]]
    dims = ["fovs", "rows", "cols", "channels"]
    test_mat = xr.DataArray(test_mat_data, coords=coords, dims=dims)

    distance_mat = spatial_analysis_utils.calc_dist_matrix(test_mat)

    real_mat = np.array([[0, 5, 3], [5, 0, 4], [3, 4, 0]])

    assert np.array_equal(distance_mat["1"].loc[range(1, 4), range(1, 4)], real_mat)
    assert np.array_equal(distance_mat["2"].loc[range(1, 4), range(1, 4)], real_mat)

    # file save testing
    with pytest.raises(ValueError):
        # trying to save to a non-existent directory
        distance_mat = spatial_analysis_utils.calc_dist_matrix(test_mat, save_path="bad_path")

    with tempfile.TemporaryDirectory() as temp_dir:
        # validate_paths requires data as a prefix, so add one
        data_path = os.path.join(temp_dir, "data_dir")
        os.mkdir(data_path)

        # assert we actually save and save to the correct path if specified
        spatial_analysis_utils.calc_dist_matrix(test_mat, save_path=data_path)

        assert os.path.exists(os.path.join(data_path, "dist_matrices.npz"))


def test_get_pos_cell_labels_channel():
    all_data, _ = test_utils._make_dist_exp_mats_spatial_utils_test()
    example_thresholds = test_utils._make_threshold_mat(in_utils=True)

    # Only include the columns of markers
    fov_channel_data = all_data.drop(all_data.columns[[
        0, 1, 14, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]], axis=1)

    thresh_vec = example_thresholds.iloc[0:20, 1]

    cell_labels = all_data.iloc[:, 24]

    pos_cell_labels = spatial_analysis_utils.get_pos_cell_labels_channel(
        thresh_vec.iloc[0], fov_channel_data, cell_labels, fov_channel_data.columns[0])

    assert len(pos_cell_labels) == 4


def test_get_pos_cell_labels_cluster():
    all_data, _ = test_utils._make_dist_exp_mats_spatial_utils_test()
    example_thresholds = test_utils._make_threshold_mat(in_utils=True)

    # Only include the columns of markers
    fov_channel_data = all_data.drop(all_data.columns[[
        0, 1, 14, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]], axis=1)

    cluster_ids = all_data.iloc[:, 31].drop_duplicates()

    pos_cell_labels = spatial_analysis_utils.get_pos_cell_labels_cluster(
        cluster_ids.iloc[0], all_data, "cellLabelInImage", "FlowSOM_ID")

    assert len(pos_cell_labels) == 4


def test_compute_close_cell_num():
    # Test the closenum function
    all_data, example_dist_mat = test_utils._make_dist_exp_mats_spatial_utils_test()
    example_thresholds = test_utils._make_threshold_mat(in_utils=True)

    # Only include the columns of markers
    fov_channel_data = all_data.drop(all_data.columns[[
        0, 1, 14, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]], axis=1)

    # Subsetting threshold matrix to only include column with threshold values
    thresh_vec = example_thresholds.iloc[0:20, 1].values

    # basic error checking
    with pytest.raises(ValueError):
        # ensure we throw an error if a bad analysis type is passed
        example_closenum, m1 = spatial_analysis_utils.compute_close_cell_num(
            dist_mat=example_dist_mat, dist_lim=100, analysis_type="bad_type",
            current_fov_data=all_data, current_fov_channel_data=fov_channel_data,
            thresh_vec=thresh_vec)

    # not taking into account mark1labels_per_id return value
    example_closenum, m1 = spatial_analysis_utils.compute_close_cell_num(
        dist_mat=example_dist_mat, dist_lim=100, analysis_type="channel",
        current_fov_data=all_data, current_fov_channel_data=fov_channel_data,
        thresh_vec=thresh_vec)

    assert (example_closenum[:2, :2] == 16).all()
    assert (example_closenum[3:5, 3:5] == 25).all()
    assert (example_closenum[5:7, 5:7] == 1).all()

    # Now test indexing with cell labels by removing a cell label from the expression matrix but
    # not the distance matrix
    all_data = all_data.drop(3, axis=0)
    # Only include the columns of markers
    fov_channel_data = all_data.drop(all_data.columns[[
        0, 1, 14, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]], axis=1)

    # Subsetting threshold matrix to only include column with threshold values
    thresh_vec = example_thresholds.iloc[0:20, 1].values

    example_closenum, m1 = spatial_analysis_utils.compute_close_cell_num(
        dist_mat=example_dist_mat, dist_lim=100, analysis_type="channel",
        current_fov_data=all_data, current_fov_channel_data=fov_channel_data,
        thresh_vec=thresh_vec)

    assert (example_closenum[:2, :2] == 9).all()
    assert (example_closenum[3:5, 3:5] == 25).all()
    assert (example_closenum[5:7, 5:7] == 1).all()

    # now, test for cluster enrichment
    all_data, example_dist_mat = test_utils._make_dist_exp_mats_spatial_utils_test()
    cluster_ids = all_data.iloc[:, 31].drop_duplicates().values

    example_closenum, m1 = spatial_analysis_utils.compute_close_cell_num(
        dist_mat=example_dist_mat, dist_lim=100, analysis_type="cluster",
        current_fov_data=all_data, cluster_ids=cluster_ids)

    assert example_closenum[0, 0] == 16
    assert example_closenum[1, 1] == 25
    assert example_closenum[2, 2] == 1


def test_compute_close_cell_num_random():
    data_markers, example_distmat = test_utils._make_dist_exp_mats_spatial_utils_test()

    # Generate random inputs to test shape
    marker_nums = [random.randrange(0, 10) for i in range(20)]

    example_closenumrand = spatial_analysis_utils.compute_close_cell_num_random(
        marker_nums, example_distmat, dist_lim=100, bootstrap_num=100
    )

    assert example_closenumrand.shape == (20, 20, 100)


def test_compute_close_cell_num_random_context():
    all_data, example_distmat = test_utils._make_dist_exp_mats_spatial_utils_test()

    # Only include the columns of markers for fov_channel_data
    fov_channel_data = all_data.drop(all_data.columns[[
        0, 1, 14, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]], axis=1)

    # Generate random inputs to test shape
    marker_nums = [random.randrange(0, 10) for i in range(20)]

    # Generate example thresholds, subset threshold matrix to only include
    # column with threshold values
    example_thresholds = test_utils._make_threshold_mat(in_utils=True)
    thresh_vec = example_thresholds.iloc[0:20, 1]

    example_closenumrand_context = spatial_analysis_utils.compute_close_cell_num_random_context(
        marker_nums=marker_nums, dist_mat=example_distmat, dist_lim=100, bootstrap_num=100,
        thresh_vec=thresh_vec, current_fov_data=all_data,
        current_fov_channel_data=fov_channel_data
    )

    assert example_closenumrand_context.shape == (20, 20, 100)

    # error checking
    with pytest.raises(ValueError):
        # attempt to specify a cell_lin_col that doesn't exist in current_fov_data
        _, stats_no_enrich = \
            spatial_analysis_utils.compute_close_cell_num_random_context(
                marker_nums=marker_nums, dist_mat=example_distmat, dist_lim=100,
                bootstrap_num=100, thresh_vec=thresh_vec, current_fov_data=all_data,
                current_fov_channel_data=fov_channel_data, cell_lin_col="bad_cell_lin_col")

    with pytest.raises(ValueError):
        # attempt to specify a cell_label_col that doesn't exist in current_fov_data
        _, stats_no_enrich = \
            spatial_analysis_utils.compute_close_cell_num_random_context(
                marker_nums=marker_nums, dist_mat=example_distmat, dist_lim=100,
                bootstrap_num=100, thresh_vec=thresh_vec, current_fov_data=all_data,
                current_fov_channel_data=fov_channel_data, cell_label_col="bad_cell_label_col")

    with pytest.raises(ValueError):
        # attempt to include non-existant cell_types for context-based randomization
        _, stats_no_enrich = \
            spatial_analysis_utils.compute_close_cell_num_random_context(
                marker_nums=marker_nums, dist_mat=example_distmat, dist_lim=100,
                bootstrap_num=100, thresh_vec=thresh_vec, current_fov_data=all_data,
                current_fov_channel_data=fov_channel_data)


def test_calculate_enrichment_stats():
    # Positive enrichment

    # Generate random closenum matrix
    stats_cnp = np.zeros((20, 20))
    stats_cnp[:, :] = 80

    # Generate random closenumrand matrix, ensuring significant positive enrichment
    stats_cnrp = np.random.randint(1, 40, (20, 20, 100))

    stats_xr_pos = spatial_analysis_utils.calculate_enrichment_stats(stats_cnp, stats_cnrp)

    assert stats_xr_pos.loc["z", 0, 0] > 0
    assert stats_xr_pos.loc["p_pos", 0, 0] < .05

    # Negative enrichment

    # Generate random closenum matrix
    stats_cnn = np.zeros((20, 20))

    # Generate random closenumrand matrix, ensuring significant negative enrichment
    stats_cnrn = np.random.randint(40, 80, (20, 20, 100))

    stats_xr_neg = spatial_analysis_utils.calculate_enrichment_stats(stats_cnn, stats_cnrn)

    assert stats_xr_neg.loc["z", 0, 0] < 0
    assert stats_xr_neg.loc["p_neg", 0, 0] < .05

    # No enrichment

    # Generate random closenum matrix
    stats_cn = np.zeros((20, 20))
    stats_cn[:, :] = 80

    # Generate random closenumrand matrix, ensuring no enrichment
    stats_cnr = np.random.randint(78, 82, (20, 20, 100))

    stats_xr = spatial_analysis_utils.calculate_enrichment_stats(stats_cn, stats_cnr)

    assert abs(stats_xr.loc["z", 0, 0]) < 1
    assert stats_xr.loc["p_neg", 0, 0] > .05
    assert stats_xr.loc["p_pos", 0, 0] > .05


def test_compute_neighbor_counts():
    fov_col = "SampleID"
    cluster_id_col = "FlowSOM_ID"
    cell_label_col = "cellLabelInImage"
    cluster_name_col = "cell_type"
    distlim = 100

    fov_data, dist_matrix = test_utils._make_dist_exp_mats_spatial_utils_test()

    cluster_names = fov_data[cluster_name_col].drop_duplicates()
    fov_data = fov_data[[fov_col, cell_label_col, cluster_id_col, cluster_name_col]]
    cluster_num = len(fov_data[cluster_id_col].drop_duplicates())

    cell_neighbor_counts = pd.DataFrame(np.zeros((fov_data.shape[0], cluster_num + 2)))

    cell_neighbor_counts[[0, 1]] = fov_data[[fov_col, cell_label_col]]

    # Rename the columns to match cell phenotypes
    cols = [fov_col, cell_label_col] + list(cluster_names)
    cell_neighbor_counts.columns = cols

    cell_neighbor_freqs = cell_neighbor_counts.copy(deep=True)

    counts, freqs = spatial_analysis_utils.compute_neighbor_counts(
        fov_data, dist_matrix, distlim)

    # add to neighbor counts/freqs for only matched phenos between the fov and the whole dataset
    cell_neighbor_counts.loc[fov_data.index, cluster_names] = counts
    cell_neighbor_freqs.loc[fov_data.index, cluster_names] = freqs

    assert (cell_neighbor_counts.loc[:3, "Pheno1"] == 4).all()
    assert (cell_neighbor_counts.loc[4:8, "Pheno2"] == 5).all()
    assert (cell_neighbor_counts.loc[9, "Pheno3"] == 1).all()

    assert (cell_neighbor_freqs.loc[:3, "Pheno1"] == 1).all()
    assert (cell_neighbor_freqs.loc[4:8, "Pheno2"] == 1).all()
    assert (cell_neighbor_freqs.loc[9, "Pheno3"] == 1).all()

    # now test for self_neighbor is False, first reset values
    cell_neighbor_counts = pd.DataFrame(np.zeros((fov_data.shape[0], cluster_num + 2)))
    cell_neighbor_counts[[0, 1]] = fov_data[[fov_col, cell_label_col]]
    cell_neighbor_counts.columns = cols
    cell_neighbor_freqs = cell_neighbor_counts.copy(deep=True)

    counts, freqs = spatial_analysis_utils.compute_neighbor_counts(
        fov_data, dist_matrix, distlim, self_neighbor=False)

    cell_neighbor_counts.loc[fov_data.index, cluster_names] = counts
    cell_neighbor_freqs.loc[fov_data.index, cluster_names] = freqs

    assert (cell_neighbor_counts.loc[:3, "Pheno1"] == 3).all()
    assert (cell_neighbor_counts.loc[4:8, "Pheno2"] == 4).all()
    assert (cell_neighbor_counts.loc[9, "Pheno3"] == 0).all()

    assert (cell_neighbor_freqs.loc[:3, "Pheno1"] == 1).all()
    assert (cell_neighbor_freqs.loc[4:8, "Pheno2"] == 1).all()
    assert (np.isnan(cell_neighbor_freqs.loc[9, "Pheno3"])).all()


def test_generate_cluster_labels():
    neighbor_mat = test_utils._make_neighborhood_matrix()[['feature1', 'feature2']]
    neighbor_cluster_labels = spatial_analysis_utils.generate_cluster_labels(neighbor_mat,
                                                                             cluster_num=3)

    assert len(np.unique(neighbor_cluster_labels) == 3)


def test_compute_kmeans_cluster_metric():
    neighbor_mat = test_utils._make_neighborhood_matrix()[['feature1', 'feature2']]

    neighbor_cluster_stats = spatial_analysis_utils.compute_kmeans_cluster_metric(
        neighbor_mat, max_k=3)

    # assert we have the right cluster_num values
    assert list(neighbor_cluster_stats.coords["cluster_num"].values) == [2, 3]

    # assert k=3 produces the best silhouette score
    three_cluster_score = neighbor_cluster_stats.loc[3].values
    assert np.all(three_cluster_score >= neighbor_cluster_stats.values)
