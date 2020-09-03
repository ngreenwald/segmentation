import numpy as np
import xarray as xr
import os.path
from os import path
from skimage.measure import regionprops
import tempfile

from ark.utils import segmentation_utils, data_utils


def _generate_channel_xr(fov_num=2, chan_num=5):
    fovs = ["fov" + str(i) for i in range(fov_num)]
    channels = ["channel" + str(i) for i in range(chan_num)]
    output = np.random.randint(0, 20, len(fovs) * 50 * 50 * len(channels))
    output = output.reshape((len(fovs), 50, 50, len(channels)))

    output_xr = xr.DataArray(output, coords=[fovs, range(50), range(50), channels],
                             dims=["fovs", "rows", "cols", "channels"])

    return output_xr


def _generate_deepcell_ouput(fov_num=2):
    fovs = ["fov" + str(i) for i in range(fov_num)]
    models = ["pixelwise_interior", "watershed_inner", "watershed_outer",
              "fgbg_foreground", "pixelwise_sum"]
    output = np.random.rand(len(fovs) * 50 * 50 * len(models))
    output = output.reshape((len(fovs), 50, 50, len(models)))

    output_xr = xr.DataArray(output, coords=[fovs, range(50), range(50), models],
                             dims=["fovs", "rows", "cols", "models"])

    # label_map_tifs = np.zeros((fov_num, 50, 50, 1))
    # return label_map_tifs
    return output_xr



def _create_test_extraction_data():
    # first create segmentation masks
    cell_mask = np.zeros((40, 40), dtype='int16')
    cell_mask[4:10, 4:10] = 1
    cell_mask[15:25, 20:30] = 2
    cell_mask[27:32, 3:28] = 3
    cell_mask[35:40, 15:22] = 5

    # then create channels data
    channel_data = np.zeros((40, 40, 5), dtype="int16")
    channel_data[:, :, 0] = 1
    channel_data[:, :, 1] = 5
    channel_data[:, :, 2] = 5
    channel_data[:, :, 3] = 10
    channel_data[:, :, 4] = 0

    # cell1 is the only cell negative for channel 3
    cell1 = cell_mask == 1
    channel_data[cell1, 3] = 0

    # cell2 is the only cell positive for channel 4
    cell2 = cell_mask == 2
    channel_data[cell2, 4] = 10

    return cell_mask, channel_data


def test_find_nuclear_mask_id():
    # create cell labels with 5 distinct cells
    cell_labels = np.zeros((60, 10), dtype='int')
    for i in range(6):
        cell_labels[(i * 10):(i * 10 + 8), :8] = i + 1

    # create nuc labels with varying degrees of overlap
    nuc_labels = np.zeros((60, 60), dtype='int')

    # perfect overlap
    nuc_labels[:8, :8] = 1

    # greater than majority overlap
    nuc_labels[10:16, :6] = 2

    # only partial overlap
    nuc_labels[20:23, :3] = 3

    # no overlap for cell 4

    # two cells overlapping, larger cell_id correct
    nuc_labels[40:48, :2] = 5
    nuc_labels[40:48, 2:8] = 20

    # two cells overlapping, background is highest
    nuc_labels[50:58, :1] = 21
    nuc_labels[50:58, 1:3] = 6

    true_nuc_ids = [1, 2, 3, None, 20, 6]

    cell_props = regionprops(cell_labels)

    # check that predicted nuclear id is correct for all cells in image
    for idx, prop in enumerate(cell_props):
        predicted_nuc = \
            segmentation_utils.find_nuclear_mask_id(nuc_segmentation_mask=nuc_labels,
                                                    cell_coords=prop.coords)

        assert predicted_nuc == true_nuc_ids[idx]


# TODO: refactor to avoid code reuse
def test_transform_expression_matrix():
    # create expression matrix
    cell_data = np.random.choice([0, 1, 2, 3, 4], 70, replace=True)
    cell_data = cell_data.reshape((1, 10, 7)).astype('float')

    coords = [['whole_cell'], list(range(10)),
              ['cell_size', 'chan1', 'chan2', 'chan3', 'label', 'morph_1', 'morph_2']]
    dims = ['compartments', 'cell_id', 'features']

    cell_data = xr.DataArray(cell_data, coords=coords, dims=dims)

    unchanged_cols = ['cell_size', 'label', 'morph_1', 'morph_2']
    modified_cols = ['chan1', 'chan2', 'chan3']

    # test size_norm
    normalized_data = segmentation_utils.transform_expression_matrix(cell_data,
                                                                     transform='size_norm')

    assert np.array_equal(normalized_data.loc[:, :, unchanged_cols].values,
                          cell_data.loc[:, :, unchanged_cols].values)

    # TODO: In general it's bad practice for tests to call the same function as code under test
    for cell in cell_data.cell_id:
        if cell_data.loc['whole_cell', cell, 'cell_size'] != 0:
            normalized_vals = np.divide(cell_data.loc['whole_cell', cell, modified_cols].values,
                                        cell_data.loc['whole_cell', cell, 'cell_size'].values)
            assert np.array_equal(normalized_data.loc['whole_cell', cell, modified_cols].values,
                                  normalized_vals)

    # test arcsinh transform
    transform_kwargs = {'linear_factor': 1}
    arcsinh_data = segmentation_utils.transform_expression_matrix(
        cell_data,
        transform='arcsinh',
        transform_kwargs=transform_kwargs
    )

    assert np.array_equal(arcsinh_data.loc[:, :, unchanged_cols].values,
                          cell_data.loc[:, :, unchanged_cols].values)

    # TODO: In general it's bad practice for tests to call the same function as code under test
    for cell in cell_data.cell_id:
        arcsinh_vals = np.arcsinh(cell_data.loc[:, cell, modified_cols].values)
        assert np.array_equal(arcsinh_data.loc[:, cell, modified_cols].values, arcsinh_vals)


def test_transform_expression_matrix_multiple_compartments():
    # create expression matrix
    cell_data = np.random.choice([0, 1, 2, 3, 4], 140, replace=True)
    cell_data = cell_data.reshape((2, 10, 7)).astype('float')

    coords = [['whole_cell', 'nuclear'], list(range(10)),
              ['cell_size', 'chan1', 'chan2', 'chan3', 'label', 'morph_1', 'morph_2']]
    dims = ['compartments', 'cell_id', 'features']

    cell_data = xr.DataArray(cell_data, coords=coords, dims=dims)

    unchanged_cols = ['cell_size', 'label', 'morph_1', 'morph_2']
    modified_cols = ['chan1', 'chan2', 'chan3']

    # test size_norm
    normalized_data = segmentation_utils.transform_expression_matrix(cell_data,
                                                                     transform='size_norm')

    assert np.array_equal(normalized_data.loc[:, :, unchanged_cols].values,
                          cell_data.loc[:, :, unchanged_cols].values)

    # TODO: In general it's bad practice for tests to call the same function as code under test
    for cell in cell_data.cell_id:
        if cell_data.loc['whole_cell', cell, 'cell_size'] != 0:
            normalized_vals = np.divide(cell_data.loc['whole_cell', cell, modified_cols].values,
                                        cell_data.loc['whole_cell', cell, 'cell_size'].values)
            assert np.array_equal(normalized_data.loc['whole_cell', cell, modified_cols].values,
                                  normalized_vals)

    # test arcsinh transform
    transform_kwargs = {'linear_factor': 1}
    arcsinh_data = segmentation_utils.transform_expression_matrix(
        cell_data,
        transform='arcsinh',
        transform_kwargs=transform_kwargs
    )

    assert np.array_equal(arcsinh_data.loc[:, :, unchanged_cols].values,
                          cell_data.loc[:, :, unchanged_cols].values)

    # TODO: In general it's bad practice for tests to call the same function as code under test
    for cell in cell_data.cell_id:
        arcsinh_vals = np.arcsinh(cell_data.loc[:, cell, modified_cols].values)
        assert np.array_equal(arcsinh_data.loc[:, cell, modified_cols].values, arcsinh_vals)


def test_visualize_watershed():
    with tempfile.TemporaryDirectory() as temp_dir:
        model_output = _generate_deepcell_ouput()
        channel_xr = _generate_channel_xr()
        overlay_channels = [channel_xr.channels.values[:2]],
        segmentation_labels_xr = \
            xr.DataArray(np.zeros((model_output.shape[:-1] + (1,)), dtype="int16"),
                         coords=[model_output.fovs, range(model_output.shape[1]),
                                 range(model_output.shape[2]),
                                 ['whole_cell']],
                         dims=['fovs', 'rows', 'cols', 'compartments'])
        #label_map_tifs = np.zeros((50, 50, 50, 1))
        #segmentation_labels_xr = xr.DataArray(model_output, ...)

        segmentation_utils.visualize_watershed_transform(
            segmentation_labels_xr=segmentation_labels_xr, model_output=model_output,
            fovs=model_output.fovs, channel_data_xr=channel_xr,
            overlay_channels=overlay_channels,
            output_dir=temp_dir)
        for mod_output_fov in model_output.fovs:
            assert os.path.exists(
                os.path.join(temp_dir, "{}_segmentation_labels.tiff".format(mod_output_fov)))

        segmentation_utils.visualize_watershed_transform(
            segmentation_labels_xr=segmentation_labels_xr, model_output=model_output,
            fovs=model_output.fovs, channel_data_xr=channel_xr,
            overlay_channels=overlay_channels,
            output_dir=temp_dir, save_tifs='all')
        for mod_output_fov in model_output.fovs:
            assert os.path.exists(
                os.path.join(temp_dir, "{}_segmentation_borders.tiff".format(mod_output_fov)))
            assert os.path.exists(
                os.path.join(temp_dir, "{}_segmentation_labels.tiff".format(mod_output_fov)))
