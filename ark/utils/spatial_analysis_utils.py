import numpy as np
import xarray as xr
import pandas as pd
import skimage.measure
import scipy
from statsmodels.stats.multitest import multipletests
from scipy.spatial.distance import cdist
import os


def calc_dist_matrix(label_maps, path=None):
    """Generate matrix of distances between center of pairs of cells

    Args:
        label_maps (xarray.DataArray):
            array with unique cells given unique pixel labels per fov
        path (str):
            path to save file. If None, then will directly return
    Returns:
        dict:
            Contains a cells x cells matrix with the euclidian
            distance between centers of corresponding cells for every fov,
            note that each distance matrix is of type xarray
    """

    # Check that file path exists, if given

    if path is not None:
        if not os.path.exists(path):
            raise FileNotFoundError("File path not valid")

    dist_mats_list = []

    # Extract list of fovs
    fovs = label_maps.coords['fovs'].values

    for fov in fovs:
        # extract region properties of label map, then just get centroids
        props = skimage.measure.regionprops(label_maps.loc[fov, :, :, 'segmentation_label'].values)
        centroids = [prop.centroid for prop in props]
        centroid_labels = [prop.label for prop in props]

        # generate the distance matrix, then assign centroid_labels as coords
        dist_matrix = cdist(centroids, centroids)
        dist_mat_xarr = xr.DataArray(dist_matrix, coords=[centroid_labels, centroid_labels])

        # append final result to dist_mats_list
        dist_mats_list.append(dist_mat_xarr)

    # Create dictionary to store distance matrices per fov
    dist_matrices = dict(zip(fovs, dist_mats_list))

    # If path is None, function will directly return the dictionary
    # else it will save it as a file with location specified by path
    if path is None:
        return dist_matrices
    else:
        np.savez(path + "dist_matrices.npz", **dist_matrices)


def get_pos_cell_labels(analysis_type, pheno=None, current_fov_neighborhood_data=None,
                        thresh=None, current_fov_channel_data=None, cell_labels=None,
                        current_marker=None):
    """Based on the type of the analysis, the function finds positive labels that match the
    current phenotype or identifies cells with positive expression values for the current marker
    (greater than the marker threshold).

    Args:
        analysis_type (str):
            type of analysis, either "cluster" or "channel"
        pheno (str):
            the current cell phenotype
        current_fov_neighborhood_data (pandas.DataFrame):
            data for the current patient
        thresh (int):
            current threshold for marker
        current_fov_channel_data (pandas.DataFrame):
            expression data for column markers for current patient
        cell_labels (pandas.DataFrame):
            the column of cell labels for current patient
        current_marker (str):
            the current marker that the positive labels are being found for

    Returns:
        list:
            List of all the positive labels"""

    if not np.isin(analysis_type, ("cluster", "channel")).all():
        raise ValueError("Incorrect analysis type")

    if analysis_type == "cluster":
        if pheno is None or current_fov_neighborhood_data is None:
            raise ValueError("Incorrect arguments passed for analysis type")
        # Subset only cells that are of the same phenotype
        pheno1posinds = current_fov_neighborhood_data["FlowSOM_ID"] == pheno
        # Get the cell labels of the cells of the phenotype
        mark1poslabels = current_fov_neighborhood_data.iloc[:, 1][pheno1posinds]
    else:
        if(
            thresh is None
            or current_fov_channel_data is None
            or cell_labels is None or current_marker is None
        ):
            raise ValueError("Incorrect arguments passed for analysis type")
        # Subset only cells that are positive for the given marker
        marker1posinds = current_fov_channel_data[current_marker] > thresh
        # Get the cell labels of the positive cells
        mark1poslabels = cell_labels[marker1posinds]
    return mark1poslabels


def get_pos_cell_labels_channel(thresh=None, current_fov_channel_data=None,
                                cell_labels=None, current_marker=None):
    if(
        thresh is None
        or current_fov_channel_data is None
        or cell_labels is None or current_marker is None
    ):
        raise ValueError("Incorrect arguments passed for analysis type")
    # Subset only cells that are positive for the given marker
    marker1posinds = current_fov_channel_data[current_marker] > thresh
    # Get the cell labels of the positive cells
    mark1poslabels = cell_labels[marker1posinds]

    return mark1poslabels



def get_pos_cell_labels_cluster(pheno=None, current_fov_neighborhood_data=None):
    if pheno is None or current_fov_neighborhood_data is None:
        raise ValueError("Incorrect arguments passed for analysis type")

    # Subset only cells that are of the same phenotype
    pheno1posinds = current_fov_neighborhood_data["FlowSOM_ID"] == pheno
    # Get the cell labels of the cells of the phenotype
    mark1poslabels = current_fov_neighborhood_data.iloc[:, 1][pheno1posinds]

    return mark1poslabels


def compute_close_cell_num(dist_mat, dist_lim, num, analysis_type,
                           current_fov_data=None, current_fov_channel_data=None,
                           cluster_ids=None, cell_types_analyze=None, thresh_vec=None):
    """Finds positive cell labels and creates matrix with counts for cells positive for
    corresponding markers. Computes close_num matrix for both Cell Label and Threshold spatial
    analyses.

    This function loops through all the included markers in the patient data and identifies cell
    labels positive for corresponding markers. It then subsets the distance matrix to only include
    these positive cells and records interactions based on whether cells are close to each other
    (within the dist_lim). It then stores the number of interactions in the index of close_num
    corresponding to both markers (for instance markers 1 and 2 would be in index [0, 1]).

    Args:
        dist_mat (numpy.ndarray):
            cells x cells matrix with the euclidian distance between centers of corresponding cells
        dist_lim (int):
            threshold for spatial enrichment distance proximity
        num (int):
            number of markers or cell phenotypes, based on analysis
        analysis_type (str):
            type of analysis, either cluster or channel
        current_fov_data (pandas.DataFrame):
            data for specific patient in expression matrix
        current_fov_channel_data (pandas.DataFrame):
            data of only column markers for Channel Analysis
        cluster_ids (pandas.DataFrame):
            all the cell phenotypes in Cluster Analysis
        cell_types_analyze (list):
            a list of the cell types we wish to analyze, if None we set it equal to all cell types
        thresh_vec (numpy.ndarray):
            matrix of thresholds column for markers

    Returns:
        numpy.ndarray:
            2D array containing marker x marker matrix with counts for cells positive for
            corresponding markers, as well as a list of number of cell labels for marker 1
    """

    # assert our analysis type is valid
    if not np.isin(analysis_type, ("cluster", "channel")).all():
        raise ValueError("Incorrect analysis type")

    # Initialize variables

    cell_labels = []

    # Assign column names for subsetting (cell labels)
    cell_label_col = "cellLabelInImage"

    # Subset data based on analysis type
    if analysis_type == "channel":
        # Subsetting the column with the cell labels
        cell_labels = current_fov_data[cell_label_col]

    # Create close_num, marker1_num, and marker2_num
    close_num = np.zeros((num, num), dtype='int')

    mark1_num = []
    mark1poslabels = []

    dist_mat_bin = xr.DataArray(
        (dist_mat.values < dist_lim).astype(np.int8),
        coords=dist_mat.coords
    )

    for j in range(0, num):
        if analysis_type == "cluster":
            mark1poslabels.append(get_pos_cell_labels_cluster(cluster_ids.iloc[j],
                                                              current_fov_data))
        else:
            mark1poslabels.append(get_pos_cell_labels_channel(thresh=thresh_vec.iloc[j],
                                                              current_fov_channel_data=current_fov_channel_data,
                                                              cell_labels=cell_labels,
                                                              current_marker=current_fov_channel_data.columns[j]))
        mark1_num.append(len(mark1poslabels[j]))
        # TODO: we also need to extract the marker counts for each type of cell we wish to analyze
        # this will require also setting a parameter that allows us to count the number of "else" cells
        # best to store in a dictionary mapping marker counts to their respective cell type

    mark1_num_per_id = None
    if analysis_type == "cluster":
        mark1_num_per_id = dict(zip(cluster_ids, mark1_num))

    # iterating k from [j, end] cuts out 1/2 the steps (while symmetric)
    for j, m1n in enumerate(mark1_num):
        for k, m2n in enumerate(mark1_num[j:], j):
            dist_mat_bin_subset = dist_mat_bin.loc[
                mark1poslabels[j].values,
                mark1poslabels[k].values
            ].values
            count_close_num_hits = np.sum(dist_mat_bin_subset)

            close_num[j, k] = count_close_num_hits
            # symmetry :)
            close_num[k, j] = close_num[j, k]

    return close_num, mark1_num, mark1_num_per_id


def compute_close_cell_num_random(marker_nums, dist_mat, dist_lim, bootstrap_num):
    """Uses bootstrapping to permute cell labels randomly and records the number of close cells
    (within the dit_lim) in that random setup.

    Args:
        marker_nums (numpy.ndarray):
            list of cell counts of each marker type
        dist_mat (numpy.ndarray):
            cells x cells matrix with the euclidian distance between centers of corresponding cells
        dist_lim (int):
            threshold for spatial enrichment distance proximity
        bootstrap_num (int):
            number of permutations

    Returns:
        numpy.ndarray:
            Large matrix of random positive marker counts for every permutation in the bootstrap
    """

    # Create close_num_rand
    close_num_rand = np.zeros((
        len(marker_nums), len(marker_nums), bootstrap_num), dtype='int')

    dist_mat_bin = xr.DataArray(
        (dist_mat.values < dist_lim).astype(np.int8),
        coords=dist_mat.coords
    )

    for j, m1n in enumerate(marker_nums):
        for k, m2n in enumerate(marker_nums[j:], j):
            samples_dim = (m1n * m2n, bootstrap_num)
            dist_mat_bin_flattened = dist_mat_bin.values.flatten()
            count_close_num_rand_hits = np.sum(
                np.random.choice(dist_mat_bin_flattened, samples_dim, True),
                axis=0
            )

            close_num_rand[j, k, :] = count_close_num_rand_hits
            # symmetry :)
            close_num_rand[k, j, :] = close_num_rand[j, k, :]

    return close_num_rand


def calculate_enrichment_stats(close_num, close_num_rand):
    """Calculates z score and p values from spatial enrichment analysis.

    Args:
        close_num (numpy.ndarray):
            marker x marker matrix with counts for cells positive for corresponding markers
        close_num_rand (numpy.ndarray):
            random positive marker counts for every permutation in the bootstrap

    Returns:
        xarray.DataArray:
            xarray contining the following statistics for marker to marker enrichment
                - z: z scores for corresponding markers
                - muhat: predicted mean values of close_num_rand random distribution
                - sigmahat: predicted standard deviations of close_num_rand random distribution
                - p: p values for corresponding markers, for both positive and negative enrichment
                - h: matrix indicating whether corresponding marker interactions are significant
                - adj_p: fdh_br adjusted p values
    """
    # Get the number of markers and number of permutations
    marker_num = close_num.shape[0]
    bootstrap_num = close_num_rand.shape[2]

    # Create z, muhat, sigmahat, and p
    z = np.zeros((marker_num, marker_num))
    muhat = np.zeros((marker_num, marker_num))
    sigmahat = np.zeros((marker_num, marker_num))
    p_pos = np.zeros((marker_num, marker_num))
    p_neg = np.zeros((marker_num, marker_num))

    for j in range(0, marker_num):
        for k in range(0, marker_num):
            # Get close_num_rand value for every marker combination and reshape for norm fit
            tmp = np.reshape(close_num_rand[j, k, :], (bootstrap_num, 1))
            # Get muhat and sigmahat values for distribution from 100 permutations
            (muhat[j, k], sigmahat[j, k]) = scipy.stats.norm.fit(tmp)
            # Calculate z score based on distribution
            z[j, k] = (close_num[j, k] - muhat[j, k]) / sigmahat[j, k]
            # Calculate both positive and negative enrichment p values
            p_pos[j, k] = (1 + (np.sum(tmp >= close_num[j, k]))) / (bootstrap_num + 1)
            p_neg[j, k] = (1 + (np.sum(tmp < close_num[j, k]))) / (bootstrap_num + 1)

    # Get fdh_br adjusted p values
    p_summary = np.zeros_like(p_pos[:, :])
    for j in range(0, marker_num):
        for k in range(0, marker_num):
            # Use negative enrichment p values if the z score is negative, and vice versa
            if z[j, k] > 0:
                p_summary[j, k] = p_pos[j, k]
            else:
                p_summary[j, k] = p_neg[j, k]
    (h, adj_p, aS, aB) = multipletests(
        p_summary, alpha=.05
    )

    # Create an Xarray with the dimensions (stats variables, number of markers, number of markers)
    stats_data = np.stack((z, muhat, sigmahat, p_pos, p_neg, h, adj_p), axis=0)
    coords = [["z", "muhat", "sigmahat", "p_pos", "p_neg", "h", "p_adj"],
              range(stats_data[0].data.shape[0]), range(stats_data[0].data.shape[1])]
    dims = ["stats", "rows", "cols"]
    stats_xr = xr.DataArray(stats_data, coords=coords, dims=dims)
    return stats_xr


def compute_neighbor_counts(current_fov_neighborhood_data, dist_matrix, distlim,
                            self_neighbor=True, cell_label_col="cellLabelInImage"):
    """Calculates the number of neighbor phenotypes for each cell. The cell counts itself as a
    neighbor.

    Args:
        current_fov_neighborhood_data (pandas.DataFrame):
            data for the current fov, including the cell labels, cell phenotypes, and cell
            phenotype ID
        dist_matrix (numpy.ndarray):
            cells x cells matrix with the euclidian distance between centers of corresponding cells
        distlim (int):
            threshold for spatial enrichment distance proximity
        self_neighbor (bool):
            If true, cell counts itself as a neighbor in the analysis.
        cell_label_col (str):
            Column name with the cell labels
    Returns:
        tuple (pandas.DataFrame, pandas.DataFrame):
            - phenotype counts per cell
            - phenotype frequencies of counts per total for each cell
    """

    # TODO remove non-cell2cell lines (indices of distance matrix do not correspond to cell labels)
    #  after our own inputs for functions are created
    # refine distance matrix to only cover cell labels in fov_data

    cell_dist_mat = dist_matrix.loc[
        current_fov_neighborhood_data[cell_label_col].values,
        current_fov_neighborhood_data[cell_label_col].values
    ].values

    # cell_dist_mat = np.take(dist_matrix, current_fov_neighborhood_data[cell_label_col] - 1, 0)
    # cell_dist_mat = np.take(cell_dist_mat, current_fov_neighborhood_data[cell_label_col] - 1, 1)

    # binarize distance matrix
    cell_dist_mat_bin = np.zeros(cell_dist_mat.shape)
    cell_dist_mat_bin[cell_dist_mat < distlim] = 1

    # default is that cell counts itself as a matrix
    if not self_neighbor:
        cell_dist_mat_bin[dist_matrix == 0] = 0

    # get num_neighbors for freqs
    num_neighbors = np.sum(cell_dist_mat_bin, axis=0)

    # create the 'phenotype has cell?' matrix, excluding non cell-label rows
    pheno_has_cell = pd.get_dummies(current_fov_neighborhood_data.iloc[:, 2]).to_numpy().T

    # dot binarized 'is neighbor?' matrix with pheno_has_cell to get counts
    counts = pheno_has_cell.dot(cell_dist_mat_bin).T

    # compute freqs with num_neighbors
    freqs = counts.T / num_neighbors

    return counts, freqs.T
