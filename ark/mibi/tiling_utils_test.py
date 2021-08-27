import copy
import json
import numpy as np
import os
import pytest
import random
import tempfile

from ark.mibi import tiling_utils
import ark.settings as settings
from ark.utils import misc_utils
from ark.utils import test_utils


def test_read_tiling_param(monkeypatch):
    # test 1: int inputs
    # test an incorrect response then a correct response
    user_inputs_int = iter([0, 1])

    # make sure the function receives the incorrect input first then the correct input
    monkeypatch.setattr('builtins.input', lambda _: next(user_inputs_int))

    # simulate the input sequence for
    sample_tiling_param = tiling_utils.read_tiling_param(
        "Sample prompt: ",
        "Sample error message",
        lambda x: x == 1,
        dtype=int
    )

    # assert sample_tiling_param was set to 1
    assert sample_tiling_param == 1

    # test 2: str inputs
    # test an incorrect response then a correct response
    user_inputs_str = iter(['N', 'Y'])

    # make sure the function receives the incorrect input first then the correct input
    monkeypatch.setattr('builtins.input', lambda _: next(user_inputs_str))

    # simulate the input sequence for
    sample_tiling_param = tiling_utils.read_tiling_param(
        "Sample prompt: ",
        "Sample error message",
        lambda x: x == 'Y',
        dtype=str
    )

    # assert sample_tiling_param was set to 'Y'
    assert sample_tiling_param == 'Y'


def test_read_tma_region_input(monkeypatch):
    # define a sample fovs list
    sample_fovs_list = test_utils.generate_sample_fovs_list(
        fov_coords=[(0, 0), (100, 100), (100, 100), (200, 200)],
        fov_names=["TheFirstFOV", "TheFirstFOV", "TheSecondFOV", "TheSecondFOV"]
    )

    # define sample region_params to read data into
    sample_region_params = {rpf: [] for rpf in settings.REGION_PARAM_FIELDS}

    # basic error check: odd number of FOVs provided
    with pytest.raises(ValueError):
        sample_fovs_list_bad = sample_fovs_list.copy()
        sample_fovs_list_bad['fovs'] = sample_fovs_list_bad['fovs'][:3]

        # use the dummy user data to read values into the params lists
        tiling_utils._read_tma_region_input(
            sample_fovs_list_bad, sample_region_params
        )

    # basic error check: start coordinate cannot be greater than end coordinate
    with pytest.raises(ValueError):
        # define a sample fovs list
        sample_fovs_list_bad = test_utils.generate_sample_fovs_list(
            fov_coords=[(100, 100), (0, 0), (0, 0), (100, 100)],
            fov_names=["TheFirstFOV", "TheFirstFOV", "TheSecondFOV", "TheSecondFOV"]
        )

        # use the dummy user data to read values into the params lists
        tiling_utils._read_tma_region_input(
            sample_fovs_list_bad, sample_region_params
        )

    # set the user inputs, also tests the validation check for num and spacing vals for x and y
    user_inputs = iter([300, 300, 100, 100, 3, 3, 1, 1, 'Y',
                        300, 300, 100, 100, 3, 3, 1, 1, 'Y'])

    # override the default functionality of the input function
    monkeypatch.setattr('builtins.input', lambda _: next(user_inputs))

    # use the dummy user data to read values into the params lists
    tiling_utils._read_tma_region_input(
        sample_fovs_list, sample_region_params
    )

    # assert the values were set properly
    assert sample_region_params['region_start_x'] == [0, 100]
    assert sample_region_params['region_start_y'] == [0, 100]
    assert sample_region_params['fov_num_x'] == [3, 3]
    assert sample_region_params['fov_num_y'] == [3, 3]
    assert sample_region_params['x_fov_size'] == [1, 1]
    assert sample_region_params['y_fov_size'] == [1, 1]
    assert sample_region_params['x_intervals'] == [[0, 50, 100], [100, 150, 200]]
    assert sample_region_params['y_intervals'] == [[0, 50, 100], [100, 150, 200]]
    assert sample_region_params['region_rand'] == ['Y', 'Y']


def test_read_non_tma_region_input(monkeypatch):
    # define a sample fovs list
    sample_fovs_list = test_utils.generate_sample_fovs_list(
        fov_coords=[(0, 0), (100, 100)], fov_names=["TheFirstFOV", "TheSecondFOV"]
    )

    # define sample region_params to read data into
    sample_region_params = {rpf: [] for rpf in settings.REGION_PARAM_FIELDS}
    sample_region_params.pop('x_intervals')
    sample_region_params.pop('y_intervals')

    # set the user inputs
    user_inputs = iter([3, 3, 1, 1, 'Y', 3, 3, 1, 1, 'Y'])

    # override the default functionality of the input function
    monkeypatch.setattr('builtins.input', lambda _: next(user_inputs))

    # use the dummy user data to read values into the params lists
    tiling_utils._read_non_tma_region_input(
        sample_fovs_list, sample_region_params
    )

    # assert the values were set properly
    assert sample_region_params['region_start_x'] == [0, 100]
    assert sample_region_params['region_start_y'] == [0, 100]
    assert sample_region_params['fov_num_x'] == [3, 3]
    assert sample_region_params['fov_num_y'] == [3, 3]
    assert sample_region_params['x_fov_size'] == [1, 1]
    assert sample_region_params['y_fov_size'] == [1, 1]
    assert sample_region_params['region_rand'] == ['Y', 'Y']


def test_generate_region_info():
    # test for TMA and non-TMA region inputs
    for tma in [False, True]:
        # sample_region_inputs will already be set so we can just add on
        if tma:
            sample_region_inputs['x_interval'] = [[100, 200, 300], [100, 200, 300]]
            sample_region_inputs['y_interval'] = [[200, 400, 600], [200, 400, 600]]
        # otherwise define dummy inputs that are needed for both TMA and non-TMA
        else:
            sample_region_inputs = {
                'region_start_x': [1, 1],
                'region_start_y': [2, 2],
                'fov_num_x': [3, 3],
                'fov_num_y': [4, 4],
                'x_fov_size': [5, 5],
                'y_fov_size': [6, 6],
                'region_rand': ['Y', 'Y']
            }

        # generate the region params
        sample_region_params = tiling_utils.generate_region_info(sample_region_inputs)

        # assert both region_start_x's are 1
        assert all(
            sample_region_params[i]['region_start_x'] == 1 for i in
            range(len(sample_region_params))
        )

        # assert both region_start_y's are 2
        assert all(
            sample_region_params[i]['region_start_y'] == 2 for i in
            range(len(sample_region_params))
        )

        # assert both num_fov_x's are 3
        assert all(
            sample_region_params[i]['fov_num_x'] == 3 for i in
            range(len(sample_region_params))
        )

        # assert both num_fov_y's are 4
        assert all(
            sample_region_params[i]['fov_num_y'] == 4 for i in
            range(len(sample_region_params))
        )

        # assert both x_fov_size's are 5
        assert all(
            sample_region_params[i]['x_fov_size'] == 5 for i in
            range(len(sample_region_params))
        )

        # assert both y_fov_size's are 6
        assert all(
            sample_region_params[i]['y_fov_size'] == 6 for i in
            range(len(sample_region_params))
        )

        # assert both randomize's are 0
        assert all(
            sample_region_params[i]['region_rand'] == 'Y' for i in
            range(len(sample_region_params))
        )

        if tma:
            # assert x_interval set properly for TMA
            assert all(
                sample_region_params[i]['x_interval'] == [100, 200, 300] for i in
                range(len(sample_region_params))
            )

            # assert y_interval set properly for TMA
            assert all(
                sample_region_params[i]['x_interval'] == [100, 200, 300] for i in
                range(len(sample_region_params))
            )
        else:
            # assert x_interval not set for non-TMA
            assert all(
                'x_interval' not in sample_region_params[i] for i in
                range(len(sample_region_params))
            )

            # assert y_interval not set for non-TMA
            assert all(
                'y_interval' not in sample_region_params[i] for i in
                range(len(sample_region_params))
            )


def test_set_tiling_params(monkeypatch):
    # define a sample set of fovs
    for tma in [False, True]:
        if tma:
            sample_fovs_list = test_utils.generate_sample_fovs_list(
                fov_coords=[(0, 0), (100, 100), (100, 100), (200, 200)],
                fov_names=["TheFirstFOV", "TheFirstFOV", "TheSecondFOV", "TheSecondFOV"]
            )
        else:
            sample_fovs_list = test_utils.generate_sample_fovs_list(
                fov_coords=[(0, 0), (100, 100)], fov_names=["TheFirstFOV", "TheSecondFOV"]
            )

        sample_moly_point = test_utils.generate_sample_fov_tiling_entry(
            coord=(14540, -10830), name="MoQC"
        )

        # set the user inputs
        user_inputs = iter([3, 3, 1, 1, 'Y', 3, 3, 1, 1, 'Y', 'Y', 'Y', 1])

        # override the default functionality of the input function
        monkeypatch.setattr('builtins.input', lambda _: next(user_inputs))

        # bad fov list path provided
        with pytest.raises(FileNotFoundError):
            tiling_utils.set_tiling_params('bad_fov_list_path.json', 'bad_moly_path.json')

        with tempfile.TemporaryDirectory() as temp_dir:
            # write fov list
            sample_fov_list_path = os.path.join(temp_dir, 'fov_list.json')
            with open(sample_fov_list_path, 'w') as fl:
                json.dump(sample_fovs_list, fl)

            # bad moly path provided
            with pytest.raises(FileNotFoundError):
                tiling_utils.set_tiling_params(sample_fov_list_path, 'bad_moly_path.json')

            # write moly point
            sample_moly_path = os.path.join(temp_dir, 'moly_point.json')
            with open(sample_moly_path, 'w') as moly:
                json.dump(sample_moly_point, moly)

            # run tiling parameter setting process with predefined user inputs
            sample_tiling_params, moly_point = tiling_utils.set_tiling_params(
                sample_fov_list_path, sample_moly_path, tma=tma
            )

            # assert the fovs in the tiling params are the same as in the original fovs list
            assert sample_tiling_params['fovs'] == sample_fovs_list['fovs']

            # assert region start x and region start y values are correct
            sample_region_params = sample_tiling_params['region_params']
            fov_0 = sample_fovs_list['fovs'][0]
            fov_1 = sample_fovs_list['fovs'][1]

            assert sample_region_params[0]['region_start_x'] == fov_0['centerPointMicrons']['x']
            assert sample_region_params[1]['region_start_x'] == fov_1['centerPointMicrons']['x']
            assert sample_region_params[0]['region_start_y'] == fov_0['centerPointMicrons']['y']
            assert sample_region_params[1]['region_start_y'] == fov_1['centerPointMicrons']['y']

            # assert fov_num_x and fov_num_y are all set to 3
            assert all(
                sample_region_params[i]['fov_num_x'] == 3 for i in
                range(len(sample_region_params))
            )
            assert all(
                sample_region_params[i]['fov_num_y'] == 3 for i in
                range(len(sample_region_params))
            )

            # assert x_fov_size and y_fov_size are all set to 1
            assert all(
                sample_region_params[i]['x_fov_size'] == 1 for i in
                range(len(sample_region_params))
            )
            assert all(
                sample_region_params[i]['y_fov_size'] == 1 for i in
                range(len(sample_region_params))
            )

            # assert randomize is set to Y for both fovs
            assert all(
                sample_region_params[i]['region_rand'] == 'Y' for i in
                range(len(sample_region_params))
            )

            # assert moly run is set to Y
            assert sample_tiling_params['moly_run'] == 'Y'

            # assert moly interval is set to 1
            assert sample_tiling_params['moly_interval'] == 1

            # for TMAs, assert that the x interval and y intervals were created properly
            if tma:
                # TheFirstFOV
                assert sample_region_params[0]['x_intervals'] == [0, 50, 100]
                assert sample_region_params[0]['y_intervals'] == [0, 50, 100]

                # TheSecondFOV
                assert sample_region_params[1]['x_intervals'] == [100, 150, 200]
                assert sample_region_params[1]['y_intervals'] == [100, 150, 200]


def test_generate_x_y_fov_pairs():
    # define sample x and y pair lists
    sample_x_range = [0, 5]
    sample_y_range = [2, 4]

    # generate the sample (x, y) pairs
    sample_pairs = tiling_utils.generate_x_y_fov_pairs(sample_x_range, sample_y_range)

    assert sample_pairs == [(0, 2), (0, 4), (5, 2), (5, 4)]


def test_create_tiled_regions_non_tma():
    sample_fovs_list = test_utils.generate_sample_fovs_list(
        fov_coords=[(0, 0), (100, 100)], fov_names=["TheFirstFOV", "TheSecondFOV"]
    )

    sample_region_inputs = {
        'region_start_x': [0, 50],
        'region_start_y': [100, 150],
        'fov_num_x': [2, 4],
        'fov_num_y': [4, 2],
        'x_fov_size': [5, 10],
        'y_fov_size': [10, 5],
        'region_rand': ['N', 'N']
    }

    sample_region_params = tiling_utils.generate_region_info(sample_region_inputs)

    sample_tiling_params = {
        'fovFormatVersion': '1.5',
        'fovs': sample_fovs_list['fovs'],
        'region_params': sample_region_params,
        'moly_run': 'N',
        'moly_interval': 3
    }

    sample_moly_point = test_utils.generate_sample_fov_tiling_entry(
        coord=(14540, -10830), name="MoQC"
    )

    # we need these globals to set baselines for both moly run and moly interval settings
    actual_center_points_no_run_no_int = None
    actual_center_points_no_run_int = None
    actual_center_points_run_no_int = None
    actual_center_points_run_int = None

    # test randomization for no fovs, some fovs, and all fovs
    for randomize_setting in [['N', 'N'], ['N', 'Y'], ['Y', 'Y']]:
        # set the randomization parameters accordingly
        sample_tiling_params['region_params'][0]['region_rand'] = randomize_setting[0]
        sample_tiling_params['region_params'][1]['region_rand'] = randomize_setting[1]

        # test both moly run settings
        for moly_run in ['N', 'Y']:
            sample_tiling_params['moly_run'] = moly_run

            # test both moly interval settings
            for moly_interval_setting in [False, True]:
                # place the moly_interval param in if True, else remove
                if moly_interval_setting:
                    sample_tiling_params['moly_interval'] = 3
                else:
                    del sample_tiling_params['moly_interval']

                # create the tiles
                tiled_regions = tiling_utils.create_tiled_regions(
                    sample_tiling_params, sample_moly_point
                )

                # retrieve the center points
                center_points = [
                    (fov['centerPointMicrons']['x'], fov['centerPointMicrons']['y'])
                    for fov in tiled_regions['fovs']
                ]

                if randomize_setting == ['N', 'N'] and moly_run == 'Y':
                    if moly_interval_setting:
                        # since True will run after False for moly_interval_setting
                        # actual_center_points_run_no_int will be set so we can piggyback
                        actual_center_points_run_int = actual_center_points_run_no_int[:]

                        # define the indices to add moly points
                        moly_indices_run = [3, 7, 12, 16, 20]

                        # insert moly points
                        for mi in moly_indices_run:
                            actual_center_points_run_int.insert(mi, (14540, -10830))

                        # the center points should match up exactly with no sorting
                        assert center_points == actual_center_points_run_int
                    else:
                        # set a baseline for what the center points should be
                        actual_center_points_run_no_int = [
                            (x, y) for x in np.arange(0, 10, 5) for y in np.arange(100, 140, 10)
                        ] + [(14540, -10830)] + [
                            (x, y) for x in np.arange(50, 90, 10) for y in np.arange(150, 160, 5)
                        ]

                        # the center points should match up exactly with no sorting
                        assert center_points == actual_center_points_run_no_int
                elif randomize_setting == ['N', 'N'] and moly_run == 'N':
                    if moly_interval_setting:
                        # since True will run after False for moly_interval_setting
                        # actual_center_points_no_run_no_int will be set so we can piggyback
                        actual_center_points_no_run_int = actual_center_points_no_run_no_int[:]

                        # define the indices to add moly points
                        moly_indices_no_run = [3, 7, 11, 15, 19]

                        # insert moly points
                        for mi in moly_indices_no_run:
                            actual_center_points_no_run_int.insert(mi, (14540, -10830))

                        # the center points should match up exactly with no sorting
                        assert center_points == actual_center_points_no_run_int
                    else:
                        # set a baseline for what the center points should be
                        actual_center_points_no_run_no_int = [
                            (x, y) for x in np.arange(0, 10, 5) for y in np.arange(100, 140, 10)
                        ] + [
                            (x, y) for x in np.arange(50, 90, 10) for y in np.arange(150, 160, 5)
                        ]

                        # the center points should match up exactly with no sorting
                        assert center_points == actual_center_points_no_run_no_int

                elif randomize_setting == ['N', 'Y']:
                    if moly_run == 'Y':
                        # define the end of fov 1
                        fov_1_end = 11 if moly_interval_setting else 9

                        # define the baseline points we will be testing against
                        actual_points = actual_center_points_run_int if moly_interval_setting \
                            else actual_center_points_run_no_int
                    else:
                        # define the end of fov 1
                        fov_1_end = 10 if moly_interval_setting else 8

                        # define the baseline points we will be testing against
                        actual_points = actual_center_points_no_run_int if moly_interval_setting \
                            else actual_center_points_no_run_no_int

                    # ensure the fov 1 center points are the same for both sorted and random
                    assert center_points[:fov_1_end] == actual_points[:fov_1_end]

                    # ensure the random center points for fov 2 contain the same elements
                    # as its sorted version
                    misc_utils.verify_same_elements(
                        computed_center_points=center_points[fov_1_end:],
                        actual_center_points=actual_points[fov_1_end:]
                    )

                    # however, fov 2 sorted entries should NOT equal fov 2 random entries
                    # NOTE: due to randomization, this test will fail once in a blue moon
                    assert center_points[fov_1_end:] != actual_points[fov_1_end:]

                elif randomize_setting == ['Y', 'Y']:
                    if moly_run == 'Y':
                        # define the end of fov 1
                        fov_1_end = 11 if moly_interval_setting else 9

                        # define the baseline points we will be testing against
                        actual_points = actual_center_points_run_int if moly_interval_setting \
                            else actual_center_points_run_no_int
                    else:
                        # define the end of fov 1
                        fov_1_end = 10 if moly_interval_setting else 8

                        # define the baseline points we will be testing against
                        actual_points = actual_center_points_no_run_int if moly_interval_setting \
                            else actual_center_points_no_run_no_int

                    # ensure the random center points for fov 1 contain the same elements
                    # as its sorted version
                    misc_utils.verify_same_elements(
                        computed_center_points=center_points[:fov_1_end],
                        actual_center_points=actual_points[:fov_1_end]
                    )

                    # however, fov 1 sorted entries should NOT equal fov 1 random entries
                    # NOTE: due to randomization, this test will fail once in a blue moon
                    assert center_points[:fov_1_end] != actual_points[:fov_1_end]

                    # ensure the random center points for fov 2 contain the same elements
                    # as its sorted version
                    misc_utils.verify_same_elements(
                        computed_center_points=center_points[fov_1_end:],
                        actual_center_points=actual_points[fov_1_end:]
                    )

                    # however, fov 2 sorted entries should NOT equal fov 2 random entries
                    # NOTE: due to randomization, this test will fail once in a blue moon
                    assert center_points[fov_1_end:] != actual_points[fov_1_end:]


def test_create_tiled_regions_tma():
    sample_fovs_list = test_utils.generate_sample_fovs_list(
        fov_coords=[(0, 0), (100, 100), (100, 100), (200, 200)],
        fov_names=["TheFirstFOV", "TheFirstFOV", "TheSecondFOV", "TheSecondFOV"]
    )

    sample_region_inputs = {
        'region_start_x': [0, 50],
        'region_start_y': [100, 150],
        'fov_num_x': [2, 4],
        'fov_num_y': [4, 2],
        'x_fov_size': [5, 10],
        'y_fov_size': [10, 5],
        'x_intervals': [[0, 50, 100], [100, 150, 200]],
        'y_intervals': [[0, 50, 100], [100, 150, 200]],
        'region_rand': ['N', 'N']
    }

    sample_region_params = tiling_utils.generate_region_info(sample_region_inputs)

    sample_tiling_params = {
        'fovFormatVersion': '1.5',
        'fovs': sample_fovs_list['fovs'],
        'region_params': sample_region_params,
        'moly_run': 'N',
        'moly_interval': 3
    }

    sample_moly_point = test_utils.generate_sample_fov_tiling_entry(
        coord=(14540, -10830), name="MoQC"
    )

    # we need these globals to set baselines for both moly run and moly interval settings
    actual_center_points_no_run_no_int = None
    actual_center_points_no_run_int = None
    actual_center_points_run_no_int = None
    actual_center_points_run_int = None

    # test randomization for no fovs, some fovs, and all fovs
    for randomize_setting in [['N', 'N'], ['N', 'Y'], ['Y', 'Y']]:
        # set the randomization parameters accordingly
        sample_tiling_params['region_params'][0]['region_rand'] = randomize_setting[0]
        sample_tiling_params['region_params'][1]['region_rand'] = randomize_setting[1]

        # test both moly run settings
        for moly_run in ['N', 'Y']:
            sample_tiling_params['moly_run'] = moly_run

            # test both moly interval settings
            for moly_interval_setting in [False, True]:
                # place the moly_interval param in if True, else remove
                if moly_interval_setting:
                    sample_tiling_params['moly_interval'] = 5
                else:
                    del sample_tiling_params['moly_interval']

                # create the tiles
                tiled_regions = tiling_utils.create_tiled_regions(
                    sample_tiling_params, sample_moly_point, tma=True
                )

                # retrieve the center points
                center_points = [
                    (fov['centerPointMicrons']['x'], fov['centerPointMicrons']['y'])
                    for fov in tiled_regions['fovs']
                ]

                if randomize_setting == ['N', 'N'] and moly_run == 'Y':
                    if moly_interval_setting:
                        # since True will run after False for moly_interval_setting
                        # actual_center_points_run_no_int will be set so we can piggyback
                        actual_center_points_run_int = actual_center_points_run_no_int[:]

                        # define the indices to add moly points
                        moly_indices_run = [5, 12, 18]

                        # insert moly points
                        for mi in moly_indices_run:
                            actual_center_points_run_int.insert(mi, (14540, -10830))

                        # the center points should match up exactly with no sorting
                        assert center_points == actual_center_points_run_int
                    else:
                        # set a baseline for what the center points should be
                        actual_center_points_run_no_int = [
                            (x, y) for x in np.arange(0, 150, 50) for y in
                            np.arange(0, 150, 50)
                        ] + [(14540, -10830)] + [
                            (x, y) for x in np.arange(100, 250, 50) for y in
                            np.arange(100, 250, 50)
                        ]

                        # the center points should match up exactly with no sorting
                        assert center_points == actual_center_points_run_no_int
                elif randomize_setting == ['N', 'N'] and moly_run == 'N':
                    if moly_interval_setting:
                        # since True will run after False for moly_interval_setting
                        # actual_center_points_no_run_no_int will be set so we can piggyback
                        actual_center_points_no_run_int = actual_center_points_no_run_no_int[:]

                        # define the indices to add moly points
                        moly_indices_no_run = [5, 11, 17]

                        # insert moly points
                        for mi in moly_indices_no_run:
                            actual_center_points_no_run_int.insert(mi, (14540, -10830))

                        # the center points should match up exactly with no sorting
                        assert center_points == actual_center_points_no_run_int
                    else:
                        # set a baseline for what the center points should be
                        actual_center_points_no_run_no_int = [
                            (x, y) for x in np.arange(0, 150, 50) for y in
                            np.arange(0, 150, 50)
                        ] + [
                            (x, y) for x in np.arange(100, 250, 50) for y in
                            np.arange(100, 250, 50)
                        ]

                        # the center points should match up exactly with no sorting
                        assert center_points == actual_center_points_no_run_no_int

                elif randomize_setting == ['N', 'Y']:
                    if moly_run == 'Y':
                        # define the end of fov 1
                        fov_1_end = 11 if moly_interval_setting else 10

                        # define the baseline points we will be testing against
                        actual_points = actual_center_points_run_int if moly_interval_setting \
                            else actual_center_points_run_no_int
                    else:
                        # define the end of fov 1
                        fov_1_end = 10 if moly_interval_setting else 9

                        # define the baseline points we will be testing against
                        actual_points = actual_center_points_no_run_int if moly_interval_setting \
                            else actual_center_points_no_run_no_int

                    # ensure the fov 1 center points are the same for both sorted and random
                    assert center_points[:fov_1_end] == actual_points[:fov_1_end]

                    # ensure the random center points for fov 2 contain the same elements
                    # as its sorted version
                    misc_utils.verify_same_elements(
                        computed_center_points=center_points[fov_1_end:],
                        actual_center_points=actual_points[fov_1_end:]
                    )

                    # however, fov 2 sorted entries should NOT equal fov 2 random entries
                    # NOTE: due to randomization, this test will fail once in a blue moon
                    assert center_points[fov_1_end:] != actual_points[fov_1_end:]

                elif randomize_setting == ['Y', 'Y']:
                    if moly_run == 'Y':
                        # define the end of fov 1
                        fov_1_end = 11 if moly_interval_setting else 10

                        # define the baseline points we will be testing against
                        actual_points = actual_center_points_run_int if moly_interval_setting \
                            else actual_center_points_run_no_int
                    else:
                        # define the end of fov 1
                        fov_1_end = 10 if moly_interval_setting else 9

                        # define the baseline points we will be testing against
                        actual_points = actual_center_points_no_run_int if moly_interval_setting \
                            else actual_center_points_no_run_no_int

                    # ensure the random center points for fov 1 contain the same elements
                    # as its sorted version
                    misc_utils.verify_same_elements(
                        computed_center_points=center_points[:fov_1_end],
                        actual_center_points=actual_points[:fov_1_end]
                    )

                    # however, fov 1 sorted entries should NOT equal fov 1 random entries
                    # NOTE: due to randomization, this test will fail once in a blue moon
                    assert center_points[:fov_1_end] != actual_points[:fov_1_end]

                    # ensure the random center points for fov 2 contain the same elements
                    # as its sorted version
                    misc_utils.verify_same_elements(
                        computed_center_points=center_points[fov_1_end:],
                        actual_center_points=actual_points[fov_1_end:]
                    )

                    # however, fov 2 sorted entries should NOT equal fov 2 random entries
                    # NOTE: due to randomization, this test will fail once in a blue moon
                    assert center_points[fov_1_end:] != actual_points[fov_1_end:]
