# hope u liek capital letters

# default segmented csv column names
CELL_SIZE = 'cell_size'                     # cell size
CELL_LABEL = 'label'                        # cell label number (regionprops)
FOV_ID = 'SampleID'                         # cell's fov name
CELL_TYPE = 'cell_type'                     # cell type name (flowsom)
CLUSTER_ID = 'FlowSOM_ID'                   # cell cluster id (flowsom)
PATIENT_ID = 'PatientID'                    # cell's patient id
KMEANS_CLUSTER = 'cluster_labels'           # generated cluster column name

# standardized columns surrounding channel data
PRE_CHANNEL_COL = CELL_SIZE                 # last column before channel data
POST_CHANNEL_COL = CELL_LABEL               # first column after channel data

# MIBI tiling parameters
REGION_PARAM_FIELDS = ['region_start_x', 'region_start_y', 'fov_num_x', 'fov_num_y',
                       'x_fov_size', 'y_fov_size', 'region_rand']
MICRON_TO_STAGE_X_MULTIPLIER = 0.001001
MICRON_TO_STAGE_X_OFFSET = 0.3116
MICRON_TO_STAGE_Y_MULTIPLIER = 0.001018
MICRON_TO_STAGE_Y_OFFSET = 0.6294
STAGE_TO_PIXEL_X_MULTIPLIER = 1 / 0.06887
STAGE_TO_PIXEL_X_OFFSET = 27.79
STAGE_TO_PIXEL_Y_MULTIPLIER = 1 / -0.06926
STAGE_TO_PIXEL_Y_OFFSET = -77.40

# regionprops extraction
REGIONPROPS_BASE = ['label', 'area', 'eccentricity', 'major_axis_length',
                    'minor_axis_length', 'perimeter', 'centroid',
                    'convex_area', 'equivalent_diameter']
REGIONPROPS_SINGLE_COMP = ['major_minor_axis_ratio', 'perim_square_over_area',
                           'major_axis_equiv_diam_ratio', 'convex_hull_resid',
                           'centroid_dif', 'num_concavities']
REGIONPROPS_MULTI_COMP = ['nc_ratio']

# mibitracker
MIBITRACKER_BACKEND = 'https://backend-dot-mibitracker-angelolab.appspot.com'
