import os
import shutil
import tempfile
import math
import random
import itertools

import numpy as np
import pandas as pd
import pytest
from alpineer import io_utils
from pytest_mock import MockerFixture

import ark.settings as settings
from ark.segmentation import fiber_segmentation
from ark.utils import example_dataset


def test_plot_fiber_segmentation_steps():

    with tempfile.TemporaryDirectory() as temp_dir:
        # download example data, keep only 3 fovs for testing
        example_dataset.get_example_dataset(dataset="segment_image_data", save_dir=temp_dir)
        img_dir = os.path.join(temp_dir, 'image_data')
        for fov in ['fov3', 'fov4', 'fov5', 'fov6', 'fov7', 'fov8', 'fov9', 'fov10']:
            shutil.rmtree(os.path.join(temp_dir, 'image_data', fov))

        # bad directory should raise an errors
        with pytest.raises(FileNotFoundError):
            _, _ = fiber_segmentation.plot_fiber_segmentation_steps('bad_dir', 'fov1', 'Collagen1')

        # bad channel should raise an errors
        with pytest.raises(ValueError):
            _, _ = fiber_segmentation.plot_fiber_segmentation_steps(img_dir, 'fov1', 'bad_channel')

        # bad subdirectory should raise an errors
        with pytest.raises(FileNotFoundError):
            _, _ = fiber_segmentation.plot_fiber_segmentation_steps(
                img_dir, 'fov1', 'Collagen1', img_sub_folder='bad_subdir')

        # test success
        fiber_segmentation.plot_fiber_segmentation_steps(img_dir, 'fov1', 'Collagen1')


def test_run_fiber_segmentation():
    with tempfile.TemporaryDirectory() as temp_dir:

        # download example data, keep only 3 fovs for testing
        example_dataset.get_example_dataset(dataset="segment_image_data", save_dir=temp_dir)
        img_dir = os.path.join(temp_dir, 'image_data')
        for fov in ['fov3', 'fov4', 'fov5', 'fov6', 'fov7', 'fov8', 'fov9', 'fov10']:
            shutil.rmtree(os.path.join(temp_dir, 'image_data', fov))
        out_dir = os.path.join(temp_dir, 'fiber_segmentation')
        os.makedirs(out_dir)

        # bad directories should raise an error
        with pytest.raises(FileNotFoundError):
            _ = fiber_segmentation.run_fiber_segmentation('bad_path', 'Collagen1', out_dir)

        with pytest.raises(FileNotFoundError):
            _ = fiber_segmentation.run_fiber_segmentation(img_dir, 'Collagen1', 'bad_path')

        # bad subdirectory should raise an errors
        with pytest.raises(FileNotFoundError):
            _ = fiber_segmentation.run_fiber_segmentation(img_dir, 'Collagen1', out_dir,
                                                          img_sub_folder='bad_folder')

        # bad channel should raise an errors
        with pytest.raises(ValueError):
            _ = fiber_segmentation.run_fiber_segmentation(img_dir, 'bad_channel', out_dir)

        # test success
        fiber_object_table = fiber_segmentation.run_fiber_segmentation(
            img_dir, 'Collagen1', out_dir)

        # check all fovs are processed
        assert fiber_object_table[settings.FOV_ID].unique().sort() == \
               io_utils.list_folders(img_dir).sort()
        # check for fiber alignment column
        assert 'alignment_score' in fiber_object_table.columns

        # check output files
        for fov in io_utils.list_files(img_dir):
            assert os.path.exists(os.path.join(out_dir, f'{fov}_fiber_labels.tiff'))
        assert os.path.exists(os.path.join(out_dir, 'fiber_object_table.csv'))

        # test success with debugging
        fiber_object_table = fiber_segmentation.run_fiber_segmentation(
            img_dir, 'Collagen1', out_dir, debug=True)

        # check debug output files
        intermediate_imgs = ['fov1_thresholded.tiff', 'fov1_ridges_thresholded.tiff',
                             'fov1_frangi_filter.tiff', 'fov1_contrast_adjusted.tiff']
        for img in intermediate_imgs:
            img_path = os.path.join(out_dir, '_debug', img)
            assert os.path.exists(img_path)


@pytest.mark.parametrize("neighbors", [1, 2])
def test_calculate_fiber_alignment(neighbors):
    ex_fiber_table = pd.DataFrame({
        'fov': ['fov1', 'fov1', 'fov1', 'fov1'],
        'label': [1, 2, 3, 4],
        'orientation': [-30, -15, 15, 0],
        'centroid-0': [0, 3, 1, 2],
        'centroid-1': [0, 3, 3, 2],
        'major_axis_length': [2, 2, 2, 1.5],
        'minor_axis_length': [1, 1, 1, 1]
    })
    closest_fibers = {
        1: [3, 2],
        2: [3, 1],
        3: [2, 1]
    }

    # calculate alignment scores with k=1
    align_table = fiber_segmentation.calculate_fiber_alignment(ex_fiber_table, k=neighbors)

    # check that fiber 4 was excluded
    short_fiber = align_table[align_table.label == 4]
    assert math.isnan(short_fiber.alignment_score)

    # check that alignments are calculated correctly, ignoring fiber 4 when it is closest
    for fiber in [1, 2, 3]:
        angle = int(ex_fiber_table[ex_fiber_table.label == fiber].orientation)
        neighbor_fibers = closest_fibers[fiber][:neighbors]
        neighbor_orientations = np.array(ex_fiber_table[ex_fiber_table.label.isin(neighbor_fibers)]
                                         .orientation.values)
        alignment_score = 1 / (np.sqrt(np.sum((neighbor_orientations - angle) ** 2)) / neighbors)

        assert (alignment_score == align_table[align_table.label == fiber].alignment_score).all()


@pytest.mark.parametrize(
    "areas", [random.sample(range(100, 200), 10), random.sample(range(100, 200), 10)])
def test_calculate_density(areas):
    ex_fiber_table = pd.DataFrame({
        'fov': ['fov1'] * len(areas),
        'label': list(range(1, 11)),
        'area': areas,
    })

    pixel_density, fiber_density = fiber_segmentation.calculate_density(ex_fiber_table,
                                                                        total_pixels=50**2)
    assert pixel_density == (np.sum(areas) / 50**2) * 100
    assert fiber_density == (len(areas) / 50**2) * 100


def test_generate_summary_stats(mocker: MockerFixture):
    fov_length = 16
    mocker.patch('skimage.io.imread', return_value=np.zeros((fov_length, fov_length)))

    fiber_object_table = pd.DataFrame({
        'fov': ['fov1', 'fov1', 'fov1', 'fov2', 'fov2', 'fov2'],
        'label': list(range(1, 7)),
        'alignment_score': [30, 50, 30, 15, 0, 20],
        'centroid-0': [0, 5, 19, 0, 0, 5],
        'centroid-1': [0, 5, 19, 0, 5, 0],
        'major_axis_length': [2, 4, 5, 3, 1, 6],
        'area': [1]*6
    })

    with tempfile.TemporaryDirectory() as temp_dir:
        # bad tile size should raise an error
        with pytest.raises(ValueError, match="Tile length must be a factor"):
            _, _ = fiber_segmentation.generate_summary_stats(None, temp_dir, tile_length=5)

        # test success
        tile_length = 8
        fov_stats, tile_stats = fiber_segmentation.generate_summary_stats(
            fiber_object_table, temp_dir, tile_length=tile_length, save_tiles=True)

        assert os.path.exists(os.path.join(temp_dir, 'fiber_stats_table.csv'))
        tile_dir = os.path.join(temp_dir, f'tile_stats_{tile_length}')
        assert os.path.exists(os.path.join(temp_dir, tile_dir,
                                           f'fiber_stats_table-tile_{tile_length}.csv'))

        # only confirm avg length and alignment, densities are tested above
        assert fov_stats[fov_stats.fov == 'fov1'].avg_lengt[0] == 11/3
        assert fov_stats[fov_stats.fov == 'fov2'].avg_length[0] == 10/3

        tile_corners = [tile_length * i for i in range(int(fov_length / tile_length))]
        fov1_tile_length = {(0, 0): (2+4)/2, (0, 10): 0, (10, 0): 0, (10, 10): 5}
        fov2_tile_length = {(0, 0): (3+1+6)/3, (0, 10): 0, (10, 0): 0, (10, 10): 0}
        fov1_tile_align = {(0, 0): (30+50)/2, (0, 10): 0, (10, 0): 0, (10, 10): 30}
        fov2_tile_align = {(0, 0): (15+0+20) / 3, (0, 10): 0, (10, 0): 0, (10, 10): 0}
        for x, y in itertools.product(tile_corners, tile_corners):
            tile_fov1 = tile_stats[tile_stats.fov == 'fov1']
            assert tile_fov1[tile_fov1.tile_y == y and tile_fov1.tile_x == x].avg_length[0] \
                   == fov1_tile_length[(y, x)]
            assert tile_fov1[tile_fov1.tile_y == y and tile_fov1.tile_x == x].alignment[0] \
                   == fov1_tile_align[(y, x)]

            tile_fov2 = tile_stats[tile_stats.fov == 'fov2']
            assert tile_fov2[tile_fov2.tile_y == y and tile_fov2.tile_x == x].avg_length[0] \
                   == fov2_tile_length[(y, x)]
            assert tile_fov2[tile_fov2.tile_y == y and tile_fov2.tile_x == x].alignment[0] \
                   == fov2_tile_align[(y, x)]

        # check for saved tile images
        for x, y, fov in \
                itertools.product(tile_corners, tile_corners, np.uniqe(fiber_object_table.fov)):
            assert os.path.exists(os.path.join(tile_dir, f'tile_{y},{x}.tiff'))
