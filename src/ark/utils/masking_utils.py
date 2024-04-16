import os
import numpy as np

from alpineer import io_utils, misc_utils, load_utils
from ark.utils import data_utils
from ark.segmentation.ez_seg.composites import composite_builder
from ark.segmentation.ez_seg.ez_object_segmentation import _create_object_mask


def generate_signal_masks(img_dir, mask_dir, channels, mask_name, intensity_thresh_perc=None,
                          sigma=2,min_mask_size=5000, max_hole_size=1000):
    """Creates a single signal mask for each FOV when given the channels to aggregate.

    Args:
        img_dir (str): path to the image tiff directory
        mask_dir (str): path where the masks will be saved
        channels (list): list of channels to combine to create a single mask for
        mask_name (str): name for the new mask file created
        intensity_thresh_perc (int): percentile to threshold intensity values in the image
        sigma (float): sigma for gaussian blur
        min_mask_size (int): minimum size of masked objects to include
        max_hole_size (int): maximum size of holes to leave in masked objects
    """
    # check correct image directory path
    io_utils.validate_paths([img_dir])
    fovs = io_utils.list_folders(img_dir)

    # check valid channel name
    channel_list = io_utils.remove_file_extensions(
        io_utils.list_files(os.path.join(img_dir, fovs[0])))
    misc_utils.verify_in_list(input_channels=channels, all_channels=channel_list)

    if not intensity_thresh_perc:
        intensity_thresh_perc = "auto"

    # create composite image (or read in single image)
    composite_imgs = composite_builder(
        img_dir, img_sub_folder='', fov_list=fovs, images_to_add=channels, images_to_subtract=[],
        image_type='total', composite_method='total')

    for fov in fovs:
        # create mask
        img = composite_imgs[fov]
        img_size = img.shape[0] * img.shape[1]
        mask = _create_object_mask(img, 'blob', sigma, intensity_thresh_perc, max_hole_size,
                                   fov_dim=400, min_object_area=min_mask_size,
                                   max_object_area=img_size)

        # save mask
        save_dir = os.path.join(mask_dir, fov)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        data_utils.save_fov_mask(mask_name, save_dir, mask)


def create_cell_mask(seg_mask, cell_table, fov_name, cell_types, cluster_col, sigma,
                     min_mask_size=0, max_hole_size=0):
    """Generates a binary from the cells listed in `cell_types`

    Args:
        seg_mask (numpy.ndarray): segmentation mask
        cell_table (pandas.DataFrame): cell table containing segmentation IDs and cell types
        fov_name (str): name of the fov to process
        cell_types (list): list of cell types to include in the mask
        cluster_col (str): column in cell table containing cell cluster
        sigma (float): sigma for gaussian smoothing
        min_mask_size (int): minimum size of a mask to include, default 0
        max_hole_size (int): maximum size of a hole to leave without filling, default 0

    Returns:
        numpy.ndarray: binary mask
    """
    # get cell labels for fov and cell type
    cell_subset = cell_table[cell_table['fov'] == fov_name]
    cell_subset = cell_subset[cell_subset[cluster_col].isin(cell_types)]
    cell_labels = cell_subset['label'].values

    # create mask for cell type
    cell_mask = np.isin(seg_mask, cell_labels)
    img_size = cell_mask.shape[0] * cell_mask.shape[1]

    # binarize and blur mask, no minimum size requirement or hole removal for cell masks
    cell_mask = _create_object_mask(cell_mask, 'blob', sigma, None, max_hole_size,
                                    fov_dim=0, min_object_area=min_mask_size,
                                    max_object_area=img_size)
    cell_mask[cell_mask > 0] = 1

    return cell_mask


def generate_cell_masks(seg_dir, mask_dir, cell_table, cell_types, cluster_col, mask_name,
                        sigma=10):
    """Creates a single cell mask for each FOV when given the cell types to aggregate.

    Args:
        seg_dir (str): path to the cell segmentation tiff directory
        mask_dir (str): path where the masks will be saved
        cell_table (pd.DataFrame): Dataframe containing all cell labels and their cell type
        cell_types (list): list of cell phenotypes that will be used to create the mask
        cluster_col (str): column in cell table containing cell cluster
        mask_name (str): name for the new mask file created
        sigma (float): sigma for gaussian smoothing
    """

    fov_files = io_utils.list_files(seg_dir)

    for files in fov_files:
        fov_name = files.replace('_whole_cell.tiff', '')

        seg_mask = load_utils.load_imgs_from_dir(
            data_dir=seg_dir, files=[files], xr_dim_name='compartments',
            xr_channel_names=['whole_cell']
        )

        # create mask
        mask = create_cell_mask(
            np.array(seg_mask[0, :, :, 0]), cell_table, fov_name, cell_types, cluster_col, sigma)

        # save mask
        save_dir = os.path.join(mask_dir, fov_name)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        data_utils.save_fov_mask(mask_name, save_dir, mask)