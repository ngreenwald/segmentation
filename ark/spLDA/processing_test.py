import numpy as np
import pytest
from sklearn.cluster import KMeans

import ark.settings as settings
import ark.spLDA.processing as pros
from ark.utils.misc_utils import verify_in_list
from ark.utils.test_utils import make_cell_table

# Generate a test cell table
N_CELLS = 1000
TEST_CELL_TABLE = make_cell_table(N_CELLS)


def test_format_cell_table():
    # call formatting function
    all_clusters = list(np.unique(TEST_CELL_TABLE[settings.CLUSTER_ID]))
    all_markers = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    some_clusters = all_clusters[2:]
    some_markers = all_markers[2:]

    cluster_format1 = pros.format_cell_table(cell_table=TEST_CELL_TABLE, clusters=all_clusters)
    marker_format1 = pros.format_cell_table(cell_table=TEST_CELL_TABLE, markers=all_markers)
    cluster_format2 = pros.format_cell_table(cell_table=TEST_CELL_TABLE, clusters=some_clusters)
    marker_format2 = pros.format_cell_table(cell_table=TEST_CELL_TABLE, markers=some_markers)

    # Check that number of FOVS match
    cluster_fovs = [x for x in cluster_format1.keys() if x not in ['fovs', 'markers', 'clusters']]
    marker_fovs = [x for x in marker_format1.keys() if x not in ['fovs', 'markers', 'clusters']]
    verify_in_list(
        fovs1=list(np.unique(TEST_CELL_TABLE[settings.FOV_ID])), fovs2=cluster_fovs)
    verify_in_list(
        fovs1=list(np.unique(TEST_CELL_TABLE[settings.FOV_ID])), fovs2=marker_fovs)

    # Check that columns were retained/renamed
    verify_in_list(
        cols1=["x", "y", "cluster_id", "cluster", "is_index"],
        cols2=list(cluster_format1[1].columns))
    verify_in_list(
        cols1=["x", "y", "cluster_id", "cluster", "is_index"],
        cols2=list(marker_format1[1].columns))

    # Check that columns were dropped
    assert len(TEST_CELL_TABLE.columns) > len(cluster_format1[1].columns)
    assert len(TEST_CELL_TABLE.columns) > len(marker_format1[1].columns)

    # check that only specified clusters and markers are kept
    assert not np.isin(all_clusters[:2], np.unique(cluster_format2[1].cluster_id)).any()
    assert not np.isin(all_markers[:2], np.unique(marker_format2[1].columns)).any()


def test_featurize_cell_table():
    # call formatting function
    all_clusters = list(np.unique(TEST_CELL_TABLE[settings.CLUSTER_ID]))
    all_markers = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    cluster_names = list(np.unique(TEST_CELL_TABLE["cluster_labels"]))
    cell_table_format = pros.format_cell_table(cell_table=TEST_CELL_TABLE, clusters=all_clusters,
                                               markers=all_markers)

    # call featurization
    features1 = pros.featurize_cell_table(cell_table=cell_table_format, featurization='cluster',
                                          train_frac=0.75)
    features2 = pros.featurize_cell_table(cell_table=cell_table_format, featurization='cluster',
                                          train_frac=0.5)
    features3 = pros.featurize_cell_table(cell_table=cell_table_format, featurization='marker',
                                          train_frac=0.75)

    # Check for consistent dimensions and correct column names
    assert features1["featurized_fovs"].shape[0] == TEST_CELL_TABLE.shape[0] == N_CELLS
    assert features2["featurized_fovs"].shape[0] == TEST_CELL_TABLE.shape[0] == N_CELLS
    assert features1["train_features"].shape[0] == 0.75 * N_CELLS
    assert features2["train_features"].shape[0] == 0.5 * N_CELLS
    verify_in_list(correct=all_markers, actual=list(features3["featurized_fovs"].columns))
    verify_in_list(correct=cluster_names, actual=list(features1["featurized_fovs"].columns))


def test_gap_stat():
    # call formatting & featurization - only test on clusters to avoid repetition
    all_clusters = list(np.unique(TEST_CELL_TABLE[settings.CLUSTER_ID]))
    cluster_format = pros.format_cell_table(cell_table=TEST_CELL_TABLE, clusters=all_clusters)
    features = pros.featurize_cell_table(cell_table=cluster_format, featurization='cluster')
    inert = KMeans(n_clusters=5).fit(features['featurized_fovs']).inertia_

    # compute gap_stat
    gap = pros.gap_stat(features=features['featurized_fovs'], k=5, clust_inertia=inert,
                        num_boots=25)

    # check correct output length
    assert len(gap) == 2
    # check for non-negative outputs
    assert gap[0] >= 0 and gap[1] >= 0


def test_compute_topic_eda():
    # Format & featurize cell table. Only test on clusters and 0.75 train frac to avoid repetition
    all_clusters = list(np.unique(TEST_CELL_TABLE[settings.CLUSTER_ID]))
    cluster_format = pros.format_cell_table(cell_table=TEST_CELL_TABLE, clusters=all_clusters)
    features = pros.featurize_cell_table(cell_table=cluster_format, featurization='cluster')
    # at least 25 bootstrap iterations
    with pytest.raises(ValueError, match="Number of bootstrap samples must be at least"):
        pros.compute_topic_eda(features["featurized_fovs"], topics=[5], num_boots=20)
    # appropriate range of topics
    with pytest.raises(ValueError, match="Number of topics must be in"):
        pros.compute_topic_eda(features["featurized_fovs"], topics=[2], num_boots=25)
    with pytest.raises(ValueError, match=r"Number of topics must be in"):
        pros.compute_topic_eda(features["featurized_fovs"], topics=[1000], num_boots=25)
    # check for correct output
    eda = pros.compute_topic_eda(features=features["featurized_fovs"], topics=[5], num_boots=25)
    verify_in_list(eda_correct_keys=settings.EDA_KEYS, eda_actual_keys=list(eda.keys()))


def test_create_difference_matrices():
    # Format & featurize cell table. Only test on clusters and 0.75 train frac to avoid repetition
    all_clusters = list(np.unique(TEST_CELL_TABLE[settings.CLUSTER_ID]))
    cluster_format = pros.format_cell_table(cell_table=TEST_CELL_TABLE, clusters=all_clusters)
    features = pros.featurize_cell_table(cell_table=cluster_format, featurization='cluster')

    # create difference matrices
    diff_mat = pros.create_difference_matrices(cell_table=cluster_format, features=features)
    diff_mat_train = pros.create_difference_matrices(cell_table=cluster_format,
                                                     features=features, inference=False)
    diff_mat_infer = pros.create_difference_matrices(cell_table=cluster_format,
                                                     features=features, training=False,
                                                     inference=True)

    # check for valid inputs
    with pytest.raises(ValueError, match="One or both of"):
        pros.create_difference_matrices(cell_table=cluster_format, features=features,
                                        training=False, inference=False)

    # check output names
    verify_in_list(correct=['train_diff_mat', 'inference_diff_mat'], actual=list(diff_mat.keys()))
    verify_in_list(correct=['train_diff_mat', 'inference_diff_mat'], actual=list(
        diff_mat_train.keys()))
    # check output values
    assert all(list(diff_mat.values()))
    assert diff_mat_train['inference_diff_mat'] is None
    assert diff_mat_infer['train_diff_mat'] is None


def test_fov_density():
    # Format cell table
    all_clusters = list(np.unique(TEST_CELL_TABLE[settings.CLUSTER_ID]))
    cluster_format = pros.format_cell_table(cell_table=TEST_CELL_TABLE, clusters=all_clusters)
    cell_dens = pros.fov_density(cluster_format)

    # check for correct names
    verify_in_list(correct=["average_area", "cellular_density"], actual=list(cell_dens.keys()))
    # check for correct dims
    assert len(cell_dens["average_area"]) == len(cluster_format["fovs"])
    assert len(cell_dens["cellular_density"]) == len(cluster_format["fovs"])
    # check for non-negative output
    assert all([x >= 0 for x in cell_dens["average_area"].values()])
    assert all([x >= 0 for x in cell_dens["cellular_density"].values()])
