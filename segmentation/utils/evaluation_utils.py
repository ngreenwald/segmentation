import numpy as np
import skimage.measure
import pandas as pd

# TODO: decide where sequential relabeling happens so that it doesn't have to be repeated


# accuracy evaluation
def compare_contours(predicted_label, contour_label):

    """Compares two distinct segmentation outputs

    Args:
        predicted_label: label map generated by algorithm
        contour_label: label map generated from ground truth data

    Returns:
        cell_frame: a pandas dataframe containing metrics for each cell in ground truth data"""

    # check to see if data has been supplied with labels already, or needs to be labeled
    if len(np.unique(predicted_label)) < 3:
        predicted_label = skimage.measure.label(predicted_label, connectivity=1)

    if len(np.unique(contour_label)) < 3:
        contour_label = skimage.measure.label(contour_label, connectivity=1)

    # get region props of predicted cells and initialize datastructure for storing values
    cell_frame = pd.DataFrame(columns=["contour_cell", "contour_cell_size", "predicted_cell", "predicted_cell_size",
                                       "percent_overlap", "merged", "split", "missing", "low_quality", "created"])

    # loop through each contoured cell, and compute accuracy metrics for overlapping predicting cells
    for contour_cell in range(1, np.max(contour_label) + 1):
        # generate a mask for the contoured cell, get all predicted cells that overlap the mask
        mask = contour_label == contour_cell
        if np.sum(mask) < 15:
            print("found another small cell {}".format(contour_cell))
            continue

        overlap_id, overlap_count = np.unique(predicted_label[mask], return_counts=True)
        overlap_id, overlap_count = np.array(overlap_id), np.array(overlap_count)

        # remove cells that aren't at least 5% of current cell
        contour_cell_size = np.sum(mask)
        idx = overlap_count > 0.05 * contour_cell_size
        overlap_id, overlap_count = overlap_id[idx], overlap_count[idx]

        # sort the overlap counts in decreasing order
        sort_idx = np.argsort(-overlap_count)
        overlap_id, overlap_count = overlap_id[sort_idx], overlap_count[sort_idx]

        # check and see if maps primarily to background
        if overlap_id[0] == 0:
            if overlap_count[0] / contour_cell_size > 0.8:
                # more than 80% of cell is overlapping with background, classify predicted cell as missing
                cell_frame = cell_frame.append({"contour_cell": contour_cell, "contour_cell_size": contour_cell_size,
                                                "predicted_cell": 0, "predicted_cell_size": 0,
                                                "percent_overlap": overlap_count[0] / contour_cell_size, "merged": False,
                                                "split": False, "missing": True, "low_quality": False,
                                                "created": False}, ignore_index=True)
                continue
            else:
                # not missing, just bad segmentation. Classify predicted cell as bad
                # TODO: figure out how often this condition is true, what do we do with remaining overlap targets
                cell_frame = cell_frame.append(
                    {"contour_cell": contour_cell, "contour_cell_size": contour_cell_size,
                     "predicted_cell": overlap_id[1], "predicted_cell_size": np.sum(predicted_label == overlap_id[1]),
                     "percent_overlap": overlap_count[0] / contour_cell_size, "merged": False,
                     "split": False, "missing": False, "low_quality": True, "created": False}, ignore_index=True)
                continue
        else:
            # remove background as target cell and change cell size to for calculation
            if 0 in overlap_id:
                keep_idx = overlap_id != 0
                contour_cell_size -= overlap_count[~keep_idx][0]
                overlap_id, overlap_count = overlap_id[keep_idx], overlap_count[keep_idx]

        # go through logic to determine relationship between overlapping cells
        # TODO: change logic to include a too small category for when cell is completely contained within but is smaller
        if overlap_count[0] / contour_cell_size > 0.9:

            # if greater than 90% of pixels contained in first overlap, assign to that cell
            pred_cell = overlap_id[0]
            pred_cell_size = np.sum(predicted_label == pred_cell)
            percnt = overlap_count[0] / contour_cell_size

            cell_frame = cell_frame.append({"contour_cell": contour_cell, "contour_cell_size": contour_cell_size,
                                            "predicted_cell": pred_cell, "predicted_cell_size": pred_cell_size,
                                            "percent_overlap": percnt, "merged": False, "split": False,
                                            "missing": False, "low_quality": False, "created": False}, ignore_index=True)
        else:
            # No single predicted cell occupies more than 90% of contour cell size, figure out the type of error made
            split_flag = False
            bad_flag = False
            # TODO check if first cell also has at least 80% of volume contained in contour cell?
            # TODO can keep a counter of number of cells that meet this criteria, if >2 then split?

            # keep only cells that overlap at least 20% with target cell
            idx = overlap_count > 0.2 * contour_cell_size
            overlap_id, overlap_count = overlap_id[idx], overlap_count[idx]
            for cell in range(1, len(overlap_id)):
                pred_cell_size = np.sum(predicted_label == overlap_id[cell])
                percnt = overlap_count[cell] / contour_cell_size
                if overlap_count[cell] / pred_cell_size > 0.7:
                    # multiple predicted cells were assigned to single target cell, hence split
                    split_flag = True
                    cell_frame = cell_frame.append(
                        {"contour_cell": contour_cell, "contour_cell_size": contour_cell_size,
                         "predicted_cell": overlap_id[cell], "predicted_cell_size": pred_cell_size,
                         "percent_overlap": percnt, "merged": False, "split": True,
                         "missing": False, "low_quality": False, "created": False}, ignore_index=True)
                else:
                    # this cell hasn't been split, just poorly assigned
                    bad_flag = True
                    cell_frame = cell_frame.append(
                        {"contour_cell": contour_cell, "contour_cell_size": contour_cell_size,
                         "predicted_cell": overlap_id[cell], "predicted_cell_size": pred_cell_size,
                         "percent_overlap": percnt, "merged": False, "split": False,
                         "missing": False, "low_quality": True, "created": False}, ignore_index=True)

            # assign the first cell, based on whether or not subsequent cells indicate split or bad
            if bad_flag and split_flag:
                bad_flag = False
            cell_frame = cell_frame.append({"contour_cell": contour_cell, "contour_cell_size": contour_cell_size,
                                            "predicted_cell": overlap_id[0], "predicted_cell_size": overlap_count[0],
                                            "percent_overlap": overlap_count[0] / contour_cell_size, "merged": False,
                                            "split": split_flag, "missing": False, "low_quality": bad_flag,
                                            "created": False}, ignore_index=True)

    # check and see if any new cells were created in predicted_label that don't exist in contour_label
    for predicted_cell in range(1, np.max(predicted_label) + 1):
        if not np.isin(predicted_cell, cell_frame["predicted_cell"]):
            cell_frame = cell_frame.append({"contour_cell": 0, "contour_cell_size": 0, "predicted_cell": predicted_cell,
                                            "predicted_cell_size": np.sum(predicted_label == predicted_cell),
                                            "percent_overlap": 0, "merged": False, "split": split_flag,
                                            "missing": False, "low_quality": False, "created": True}, ignore_index=True)

    return cell_frame, predicted_label, contour_label

# DSB-score adapted from https://www.biorxiv.org/content/10.1101/580605v1.full
# object IoU matrix adapted from code written by Morgan Schwartz in deepcell-tf/metrics


def calc_iou_matrix(ground_truth_label, predicted_label):
    """Calculates pairwise ious between all cells from two masks

    Args:
        ground_truth_label: 2D label array representing ground truth contours
        predicted_label: 2D labeled array representing predicted contours

    Returns:
        iou_matrix: matrix of ground_truth x predicted cells with iou value for each
    """

    iou_matrix = np.zeros((np.max(ground_truth_label), np.max(predicted_label)))

    for i in range(1, iou_matrix.shape[0] + 1):
        gt_img = ground_truth_label == i
        overlaps = np.unique(predicted_label[gt_img])
        overlaps = overlaps[overlaps > 0]
        for j in overlaps:
            pd_img = predicted_label == j
            intersect = np.sum(np.logical_and(gt_img, pd_img))
            union = np.sum(np.logical_or(gt_img, pd_img))

            # add values to matrix, adjust for background (0) not counted
            iou_matrix[i - 1, j - 1] = intersect / union
    return iou_matrix


def calc_modified_average_precision(iou_matrix, thresholds):
    """Calculates the average precision between two masks across a range of iou thresholds

    Args:
        iou_matrix: intersection over union matrix created by calc_iou_matrix function
        thresholds: list used to threshold iou values in matrix

    Returns:
        scores: list of modified average precision values for each threshold
        false_neg_idx: array of booleans indicating whether cell was flagged as false positive at each threshold
        false_pos_idx: array of booleans indicating whether cell was flagged as false negative at each threshold"""

    if np.any(np.logical_or(thresholds > 1, thresholds < 0)):
        raise ValueError("Thresholds must be between 0 and 1")

    scores = []
    false_negatives = []
    false_positives = []

    for i in range(len(thresholds)):

        # threshold iou_matrix as designated value
        iou_matrix_thresh = iou_matrix > thresholds[i]

        # Calculate values based on projecting along prediction axis
        pred_proj = iou_matrix_thresh.sum(axis=1)

        # Zeros (aka absence of hits) correspond to true cells missed by prediction
        false_neg = pred_proj == 0
        false_neg_count = np.sum(false_neg)
        false_neg_ids = np.where(false_neg)[0] + 1
        false_negatives.append(false_neg_ids)

        # Calculate values based on projecting along truth axis
        truth_proj = iou_matrix_thresh.sum(axis=0)

        # Empty hits indicate predicted cells that do not exist in true cells
        false_pos = truth_proj == 0
        false_pos_count = np.sum(false_pos)
        false_pos_ids = np.where(false_pos)[0] + 1
        false_positives.append(false_pos_ids)

        # Ones are true positives
        true_pos_count = np.sum(pred_proj == 1)

        score = true_pos_count / (true_pos_count + false_pos_count + false_neg_count)
        scores.append(score)

    return scores, false_positives, false_negatives
