import json
import os
import pytest
import random
import tempfile

import ark.mibi.tiling_utils as tiling_utils
import ark.utils.misc_utils as misc_utils


def test_create_tiled_regions():
    # set tiling_params dict
    sample_tiling_params = {
        'fovFormatVersion': '1.5',
        'fovs': [
            {
                'scanCount': 1,
                'centerPointMicrons': {
                    'x': 0, 'y': 0
                },
                'timingChoice': 7,
                'frameSizePixels': {
                    'width': 2048, 'height': 2048
                },
                'imagingPreset': {
                    'preset': 'Normal',
                    'aperture': '2',
                    'displayName': 'Fine',
                    'defaults': {
                        'timingChoice': 7
                    }
                },
                'sectionId': 8201,
                'slideId': 5931,
                'name': 'TheFirstFOV',
                'timingDescription': '1 ms'
            },
            {
                'scanCount': 1,
                'centerPointMicrons': {
                    'x': 100, 'y': 100
                },
                'timingChoice': 7,
                'frameSizePixels': {
                    'width': 2048, 'height': 2048
                },
                'imagingPreset': {
                    'preset': 'Normal',
                    'aperture': '2',
                    'displayName': 'Fine',
                    'defaults': {
                        'timingChoice': 7
                    }
                },
                'sectionId': 8201,
                'slideId': 5931,
                'name': 'TheSecondFOV',
                'timingDescription': '1 ms'
            }
        ],
        'region_start_x': [0, 50],
        'region_start_y': [100, 150],
        'fov_num_x': [2, 4],
        'fov_num_y': [4, 2],
        'x_fov_size': [5, 10],
        'y_fov_size': [10, 5],
        'randomize': 0
    }

    # set moly point
    sample_moly_point = {
        "scanCount": 3,
        "centerPointMicrons": {
            "x": 14540,
            "y": -10830
        },
        "fovSizeMicrons": 200,
        "timingChoice": 7,
        "frameSizePixels": {
            "width": 128,
            "height": 128
        },
        "imagingPreset": {
        "preset": "Tuning",
        "aperture": "3",
        "displayName": "QC - 100µm",
            "defaults": {
              "timingChoice": 7
            }
        },
        "standardTarget": "Moly Foil",
        "name": "MoQC",
        "notes": None,
        "timingDescription": "1 ms"
    }

    # error checking: bad moly_path provided
    with pytest.raises(FileNotFoundError):
        tiling_utils.create_tiled_regions(sample_tiling_params, 'bad_moly_path')

    with tempfile.TemporaryDirectory() as temp_dir:
        # write moly point
        sample_moly_path = os.path.join(temp_dir, 'moly_point.json')
        with open(sample_moly_path, 'w') as moly:
            json.dump(sample_moly_point, moly)

        # test 1: no randomization, no additional moly point interval
        tiled_regions_base = tiling_utils.create_tiled_regions(
            sample_tiling_params, sample_moly_path
        )

        # get the center points created
        sorted_center_points = [
            (fov['centerPointMicrons']['x'], fov['centerPointMicrons']['y'])
            for fov in tiled_regions_base['fovs']
        ]

        # define the actual center points in the same expected order
        actual_center_points = [
            (0, 100), (0, 110), (0, 120), (0, 130), (5, 100),
            (5, 110), (5, 120), (5, 130), (14540, -10830),
            (50, 150), (50, 155), (60, 150), (60, 155), (70, 150),
            (70, 155), (80, 150), (80, 155)
        ]

        # check that the created center points equal the sorted center points
        assert sorted_center_points == actual_center_points

        # test 2: randomization, no additional moly point interval
        sample_tiling_params['randomize'] = 1
        tiled_regions_random = tiling_utils.create_tiled_regions(
            sample_tiling_params, sample_moly_path
        )

        # get the center points created
        random_center_points = [
            (fov['centerPointMicrons']['x'], fov['centerPointMicrons']['y'])
            for fov in tiled_regions_random['fovs']
        ]

        # ensure the moly point is inserted in the same spot as if the fovs were sorted
        assert random_center_points[8] == sorted_center_points[8]

        # make sure the random center points contain the same elements as the sorted center points
        misc_utils.verify_same_elements(
            random_center_points=random_center_points,
            sorted_center_points=sorted_center_points
        )

        # the random center points should be ordered differently than the sorted center points
        # due to the nature of randomization, this test will fail once in a blue moon
        assert random_center_points != sorted_center_points

        # test 3: no randomization, additional moly point interval
        sample_tiling_params['randomize'] = 0
        sample_tiling_params['moly_interval'] = 3
        tiled_regions_moly_int = tiling_utils.create_tiled_regions(
            sample_tiling_params, sample_moly_path
        )

        # get the center points created
        sorted_center_points = [
            (fov['centerPointMicrons']['x'], fov['centerPointMicrons']['y'])
            for fov in tiled_regions_moly_int['fovs']
        ]

        # define the actual center points in the same expected order with additional moly point
        actual_center_points = [
            (0, 100), (0, 110), (0, 120), (14540, -10830),
            (0, 130), (5, 100), (5, 110), (14540, -10830),
            (5, 120), (5, 130), (14540, -10830), (50, 150),
            (14540, -10830), (50, 155), (60, 150), (60, 155),
            (14540, -10830), (70, 150), (70, 155), (80, 150),
            (14540, -10830), (80, 155)
        ]

        # check that the created center points equal the sorted center points
        assert sorted_center_points == actual_center_points

        # test 4: randomization, additional moly point interval
        sample_tiling_params['randomize'] = 1
        tiled_regions_random_moly_int = tiling_utils.create_tiled_regions(
            sample_tiling_params, sample_moly_path
        )

        # get the center points created
        random_center_points = [
            (fov['centerPointMicrons']['x'], fov['centerPointMicrons']['y'])
            for fov in tiled_regions_random_moly_int['fovs']
        ]

        # define the moly point indices, applies for both sorted and random tiled regions
        # NOTE: the moly points inserted between fovs are not counted when determining intervals
        moly_indices = [3, 6, 8, 10, 13, 16]

        # assert that each moly index is the same in both sorted and random tiled regions
        for mi in moly_indices:
            random_center_points[mi] == sorted_center_points[mi]

        # make sure the random center points contain the same elements as the sorted center points
        misc_utils.verify_same_elements(
            random_center_points=random_center_points,
            sorted_center_points=sorted_center_points
        )

        # the random center points should be ordered differently than the sorted center points
        # due to the nature of randomization, this test will fail once in a blue moon
        assert random_center_points != sorted_center_points
