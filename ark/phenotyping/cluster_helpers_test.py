from copy import deepcopy
import feather
import numpy as np
import os
import pandas as pd
import pathlib
import pytest
import random
from typing import Iterator, List, Tuple

from ark.phenotyping.cluster_helpers import PixieConsensusCluster, PixelSOMCluster, CellSOMCluster
from ark.utils.misc_utils import verify_same_elements


@pytest.fixture(scope="session")
def som_base_dir_gen(tmp_path_factory) -> Iterator[pathlib.Path]:
    """Creates the directory to hold all the test data needed for SOM clustering

    Args:
        tmp_path_factory (pytest.TempPathFactory):
            Temp dir to place SOM data in

    Yields:
        Iterator[pathlib.Path]:
            The path to place the SOM data in
    """
    print("Generating SOM cluster")
    som_output_dir = tmp_path_factory.mktemp("som_data")
    yield som_output_dir


@pytest.fixture(scope="session")
def pixel_pyflowsom_object(som_base_dir_gen) -> Iterator[Tuple[PixelSOMCluster, PixelSOMCluster]]:
    """Generates sample pixel SOM object

    Args:
        som_base_dir_gen (pytest.fixture):
            The base dir to store the consensus data

    Yields:
        Iterator[Tuple[PixelSOMCluster, PixelSOMCluster]]:
            Tuple containing two PixelSOMCluster objects: one with an existing weights path
            and one without
    """

    # define the paths, using a temporary directory as the motherbase
    pixel_sub_path = som_base_dir_gen / "pixel_subset_dir"
    norm_vals_path = som_base_dir_gen / "norm_vals.feather"
    weights_path = som_base_dir_gen / "weights_test.feather"

    # define the FOVs and channels to use
    fovs = [f'fov{i}' % i for i in np.arange(1, 5)]
    channels = [f'chan{i}' % i for i in np.arange(1, 7)]

    # generate dummy data directories
    os.mkdir(pixel_sub_path)
    for fov in fovs:
        # generate dummy sub data for fov
        fov_data = pd.DataFrame(
            np.random.rand(500, 10),
            columns=channels + ['fov', 'row_index', 'column_index', 'segmentation_label']
        )
        fov_data['fov'] = fov
        fov_data['row_index'] = np.repeat(np.arange(1, 51), 10)
        fov_data['col_index'] = np.tile(np.arange(1, 11), 50)
        fov_data['segmentation_label'] = np.arange(1, 501)

        feather.write_dataframe(fov_data, os.path.join(pixel_sub_path, fov + '.feather'))

    # generate dummy norm vals data
    norm_vals = pd.DataFrame(np.expand_dims(np.repeat(0.5, 6), 0), columns=channels)
    feather.write_dataframe(norm_vals, norm_vals_path)

    # generate dummy weights data, this will be used to test loading in an existing weights file
    weights_vals = pd.DataFrame(np.random.rand(200, 6), columns=channels)
    feather.write_dataframe(weights_vals, weights_path)

    # define a PixelSOMCluster object with weights
    pixel_som_with_weights = PixelSOMCluster(
        pixel_subset_folder=pixel_sub_path, norm_vals_path=norm_vals_path,
        weights_path=weights_path, columns=channels, xdim=20, ydim=10
    )

    # define a PixelSOMCluster object without weights
    pixel_som_sans_weights = PixelSOMCluster(
        pixel_subset_folder=pixel_sub_path, norm_vals_path=norm_vals_path,
        weights_path=som_base_dir_gen / 'weights_new.feather', columns=channels, xdim=20, ydim=10
    )

    yield pixel_som_with_weights, pixel_som_sans_weights


@pytest.fixture(scope="session")
def cell_pyflowsom_object(som_base_dir_gen) -> Iterator[Tuple[CellSOMCluster, CellSOMCluster]]:
    """Generates sample cell SOM object

    Args:
        som_base_dir_gen (pytest.fixture):
            The base dir to store the SOM data

    Yields:
        Iterator[Tuple[CellSOMCluster, CellSOMCluster]]:
            Tuple containing two CellSOMCluster objects: one with an existing weights path
            and one without
    """

    # define the paths, using a temporary directory as the motherbase
    cell_data_path = som_base_dir_gen / "cluster_counts_size_norm.feather"
    weights_path = som_base_dir_gen / "weights_test.feather"

    # define the pixel count count expression columns to use
    count_cols = [f'pixel_meta_cluster_{i}' for i in np.arange(1, 7)]

    # define dummy cell data
    cluster_counts_size_norm = pd.DataFrame(
        np.random.rand(100, 10),
        columns=['cell_size', 'fov'] + count_cols + ['segmentation_label']
    )
    cluster_counts_size_norm['cell_size'] = 150
    cluster_counts_size_norm.loc['fov', 0:50] = 'fov0'
    cluster_counts_size_norm.loc['fov', 50:100] = 'fov1'
    cluster_counts_size_norm['segmentation_label'] = np.arange(1, 101)

    feather.write_dataframe(cluster_counts_size_norm, cell_data_path)

    # generate dummy weights data, this will be used to test loading in an existing weights file
    weights_vals = pd.DataFrame(np.random.rand(200, 6), columns=count_cols)
    feather.write_dataframe(weights_vals, weights_path)

    # define a CellSOMCluster object with weights
    cell_som_with_weights = CellSOMCluster(
        cell_data_path=cell_data_path, weights_path=weights_path,
        columns=count_cols, xdim=20, ydim=10
    )

    # define a CellSOMCluster object without weights
    cell_som_sans_weights = CellSOMCluster(
        cell_data_path=cell_data_path, weights_path=som_base_dir_gen / 'weights_new.feather',
        columns=count_cols, xdim=20, ydim=10
    )

    yield cell_som_with_weights, cell_som_sans_weights


@pytest.fixture(scope="session")
def consensus_base_dir_gen(tmp_path_factory) -> Iterator[pathlib.Path]:
    """Creates the directory to hold all the test data needed for consensus clustering

    Args:
        tmp_path_factory (pytest.TempPathFactory):
            Temp dir to place consensus data in

    Yields:
        Iterator[pathlib.Path]:
            The path to place the consensus data in
    """

    consensus_output_dir = tmp_path_factory.mktemp("consensus_data")
    yield consensus_output_dir


@pytest.fixture(scope="session")
def pixel_consensus_input_gen(consensus_base_dir_gen) -> Iterator[Tuple[pathlib.Path, List[str]]]:
    """Generates sample pixel consensus data and save

    Args:
        consensus_base_dir_gen (pytest.fixture):
            The base dir to store the consensus data

    Yields:
        Iterator[Tuple[pathlib.Path, List[str]]]:
            Tuple containing path to the input to pixel SOM channel expression averages
            and expression columns
    """

    # define the paths, using a temporary directory as the motherbase
    output_file_path = consensus_base_dir_gen / "pixel_channel_avg_som_cluster.csv"

    # define the channel expression columns
    chan_cols = [f'chan{i}' for i in np.arange(1, 7)]

    # generate the sample data
    sample_pixel_consensus_data = pd.DataFrame(
        np.random.rand(100, 6), columns=chan_cols
    )

    # generate sample SOM cluster data values
    sample_pixel_consensus_data['pixel_som_cluster'] = np.arange(1, 101)

    # save the data
    sample_pixel_consensus_data.to_csv(output_file_path)

    yield output_file_path, chan_cols


@pytest.fixture(scope="session")
def cell_consensus_input_gen(consensus_base_dir_gen) -> Iterator[Tuple[pathlib.Path, List[str]]]:
    """Generates sample cell consensus data and save

    Args:
        consensus_base_dir_gen (pytest.fixture):
            The base dir to store the consensus data

    Yields:
        Iterator[Tuple[pathlib.Path, List[str]]]:
            Tuple containing path to the input to cell SOM count expression averages
            and expression columns
    """

    # define the paths, using a temporary directory as the motherbase
    output_file_path = consensus_base_dir_gen / "cell_som_cluster_avgs.csv"

    # define the pixel cluster count expression columns
    count_cols = [f'pixel_meta_cluster_{i}' for i in np.arange(1, 7)]

    # generate the sample data
    sample_cell_consensus_data = pd.DataFrame(
        np.random.rand(100, 6), columns=count_cols
    )

    # generate sample SOM cluster data values
    sample_cell_consensus_data['cell_som_cluster'] = np.arange(1, 101)

    # save the data
    sample_cell_consensus_data.to_csv(output_file_path)

    yield output_file_path, count_cols


@pytest.fixture(scope="session")
def pixel_cc_object(pixel_consensus_input_gen):
    yield PixieConsensusCluster(
        cluster_type='pixel',
        input_file=pixel_consensus_input_gen[0],
        columns=pixel_consensus_input_gen[1]
    )


@pytest.fixture(scope="session")
def cell_cc_object(cell_consensus_input_gen):
    yield PixieConsensusCluster(
        cluster_type='cell',
        input_file=cell_consensus_input_gen[0],
        columns=cell_consensus_input_gen[1]
    )


class TestPixelSOMCluster:
    @pytest.fixture(autouse=True, scope="function")
    def _setup(self, pixel_pyflowsom_object):
        # NOTE: we'll be working with pixel_pysom_nonweights mostly
        # pixel_pysom_weights is to check case where user already loaded data
        self.pixel_pysom_weights = pixel_pyflowsom_object[0]
        self.pixel_pysom_nonweights = pixel_pyflowsom_object[1]

    def test_normalize_data(self):
        # create a random dataset with the same columns
        meta_cols = ['fov', 'row_index', 'column_index', 'segmentation_label']
        sample_external_data = pd.DataFrame(
            np.random.rand(1000, 10),
            columns=self.pixel_pysom_nonweights.columns + meta_cols
        )

        # normalize sample_external_data
        normalized_data = self.pixel_pysom_weights.normalize_data(sample_external_data)

        # assert all values were divided by 0.5
        norm_data_cols = self.pixel_pysom_nonweights.norm_data.columns
        assert np.allclose(
            sample_external_data[norm_data_cols].values / 0.5,
            normalized_data[norm_data_cols].values
        )

    def test_train_pixel_som(self):
        self.pixel_pysom_nonweights.train_pixel_som()

        # assert the weights path exists
        assert os.path.exists(self.pixel_pysom_nonweights.weights_path)

        # load in the weights
        weights = feather.read_dataframe(self.pixel_pysom_nonweights.weights_path)

        # assert the column names match
        assert list(weights.columns.values) == self.pixel_pysom_nonweights.columns

        # assert the shape is correct
        assert weights.shape == (200, 6)

    def test_train_pixel_som_restart(self):
        with pytest.warns(UserWarning, match='Pixel SOM already trained'):
            self.pixel_pysom_weights.train_pixel_som()

    def test_generate_som_clusters(self):
        # generate sample external data
        # NOTE: test on shuffled data to ensure column matching
        col_shuffle = deepcopy(self.pixel_pysom_nonweights.columns)
        random.shuffle(col_shuffle)
        meta_cols = ['fov', 'row_index', 'column_index', 'segmentation_label']
        sample_external_data = pd.DataFrame(
            np.random.rand(1000, 10),
            columns=col_shuffle + meta_cols
        )

        # assign SOM labels to sample_external_data
        som_label_data = self.pixel_pysom_nonweights.assign_som_clusters(sample_external_data)

        # assert the som labels were assigned and they are all in the range 1 to 200
        assert 'pixel_som_cluster' in som_label_data.columns.values
        som_clusters = som_label_data['pixel_som_cluster'].values
        assert np.all(np.logical_and(som_clusters >= 1, som_clusters <= 200))


class TestPixieConsensusCluster:
    @pytest.fixture(autouse=True, scope="function")
    def _setup(self, pixel_cc_object, cell_cc_object):
        self.pixel_cc = pixel_cc_object
        self.cell_cc = cell_cc_object

    def test_bad_cluster_type(self):
        with pytest.raises(ValueError):
            PixieConsensusCluster(
                'bad_cluster_type', 'sample_input_file', ['col1', 'col2']
            )

    def test_pixel_scale_data(self):
        self.pixel_cc.scale_data()
        assert np.all(self.pixel_cc.input_data[self.pixel_cc.columns].values >= -3)
        assert np.all(self.pixel_cc.input_data[self.pixel_cc.columns].values <= 3)

    def test_cell_scale_data(self):
        self.cell_cc.scale_data()
        assert np.all(self.cell_cc.input_data[self.cell_cc.columns].values >= -3)
        assert np.all(self.cell_cc.input_data[self.cell_cc.columns].values <= 3)

    def test_run_pixel_consensus_clustering(self):
        self.pixel_cc.run_consensus_clustering()

        # assert we've created both internal Mk and bestK values for predict_data
        assert self.pixel_cc.cc.Mk is not None
        assert self.pixel_cc.cc.bestK is not None

    def test_run_cell_consensus_clustering(self):
        self.cell_cc.run_consensus_clustering()

        # assert we've created both internal Mk and bestK values for predict_data
        assert self.cell_cc.cc.Mk is not None
        assert self.cell_cc.cc.bestK is not None

    def test_generate_pixel_som_to_meta_map(self):
        self.pixel_cc.generate_som_to_meta_map()
        verify_same_elements(
            generated_meta_clusters=self.pixel_cc.mapping[self.pixel_cc.meta_col],
            required_meta_clusters=np.arange(1, 21)
        )

    def test_generate_cell_som_to_meta_map(self):
        self.cell_cc.generate_som_to_meta_map()
        verify_same_elements(
            generated_meta_clusters=self.cell_cc.mapping[self.cell_cc.meta_col],
            required_meta_clusters=np.arange(1, 21)
        )

    def test_save_pixel_som_to_meta_map(self):
        pixel_file = f'{self.pixel_cc.cluster_type}_clust_to_meta.feather'
        pixel_map_path = self.pixel_cc.input_file.parents[0] / pixel_file
        self.pixel_cc.save_som_to_meta_map(pixel_map_path)

        # assert we created the save path
        assert pixel_map_path.exists()

    def test_save_cell_som_to_meta_map(self):
        cell_file = f'{self.cell_cc.cluster_type}_clust_to_meta.feather'
        cell_map_path = self.cell_cc.input_file.parents[0] / cell_file
        self.cell_cc.save_som_to_meta_map(cell_map_path)

        # assert we created the save path
        assert cell_map_path.exists()

    def test_assign_pixel_consensus_labels(self):
        # generate sample external data with SOM labels
        sample_external_data = pd.DataFrame(
            np.random.rand(1000, 10)
        )
        sample_external_data[self.pixel_cc.som_col] = np.repeat(np.arange(1, 101), 10)

        labeled_external_data = self.pixel_cc.assign_consensus_labels(sample_external_data)

        # ensure we've created a meta cluster column
        assert self.pixel_cc.meta_col in sample_external_data.columns.values

        # ensure all the mappings match up
        external_mappings = labeled_external_data[
            [self.pixel_cc.som_col, self.pixel_cc.meta_col]
        ].copy()
        external_mappings = external_mappings.drop_duplicates().sort_values(
            by=self.pixel_cc.som_col
        )
        true_mappings = self.pixel_cc.mapping.sort_values(by=self.pixel_cc.som_col)
        assert np.all(external_mappings.values == true_mappings.values)

    def test_assign_cell_consensus_labels(self):
        # generate sample external data with SOM labels
        sample_external_data = pd.DataFrame(
            np.random.rand(1000, 10)
        )
        sample_external_data[self.cell_cc.som_col] = np.repeat(np.arange(1, 101), 10)

        labeled_external_data = self.cell_cc.assign_consensus_labels(sample_external_data)

        # ensure we've created a meta cluster column
        assert self.cell_cc.meta_col in sample_external_data.columns.values

        # ensure all the mappings match up
        external_mappings = labeled_external_data[
            [self.cell_cc.som_col, self.cell_cc.meta_col]
        ].copy()
        external_mappings = external_mappings.drop_duplicates().sort_values(
            by=self.cell_cc.som_col
        )
        true_mappings = self.cell_cc.mapping.sort_values(by=self.cell_cc.som_col)
        assert np.all(external_mappings.values == true_mappings.values)
