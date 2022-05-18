import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from ark.utils import misc_utils


def draw_boxplot(cell_data, col_name, col_split=None,
                 split_vals=None, dpi=None, save_dir=None, save_file=None):
    """Draws a boxplot for a given column, optionally with help from a split column

    Args:
        cell_data (pandas.DataFrame):
            Dataframe containing columns with Patient ID and Cell Name
        col_name (str):
            Name of the column we wish to draw a box-and-whisker plot for
        col_split (str):
            If specified, used for additional box-and-whisker plot faceting
        split_vals (list):
            If specified, only visualize the specified values in the col_split column
        dpi (float):
            The resolution of the image to save, ignored if save_dir is None
        save_dir (str):
            If specified, a directory where we will save the plot
        save_file (str):
            If save_dir specified, specify a file name you wish to save to.
            Ignored if save_dir is None
    """

    # the col_name must be valid
    misc_utils.verify_in_list(col_name=col_name, column_names=cell_data.columns.values)

    # if col_split is not None, it must exist as a column in cell_data
    if col_split is not None and col_split not in cell_data.columns.values:
        misc_utils.verify_in_list(col_split=col_split, column_names=cell_data.columns.values)

    # basic error checks if split_vals is set
    if split_vals is not None:
        # the user cannot specify split_vales without specifying col_split
        if col_split is None:
            raise ValueError("If split_vals is set, then col_split must also be set")

        # all the values in split_vals must exist in the col_name of cell_data
        misc_utils.verify_in_list(split_vals=split_vals,
                                  column_split_values=cell_data[col_split].unique())

    # don't modify cell_data in anyway
    data_to_viz = cell_data.copy(deep=True)

    # ignore values in col_split not in split_vals if split_vals is set
    if split_vals:
        data_to_viz = data_to_viz[data_to_viz[col_split].isin(split_vals)]

    if col_split:
        # if col_split, then we explicitly facet the visualization
        # labels are automatically generated in Seaborn
        sns.boxplot(x=col_split, y=col_name, data=data_to_viz)
        plt.title("Distribution of %s, faceted by %s" % (col_name, col_split))
    else:
        # otherwise, we don't facet anything, but we have to explicitly make vertical
        sns.boxplot(x=col_name, data=data_to_viz, orient="v")
        plt.title("Distribution of %s" % col_name)

    # save visualization to a directory if specified
    if save_dir is not None:
        misc_utils.save_figure(save_dir, save_file, dpi=dpi)


def draw_heatmap(data, x_labels, y_labels, dpi=None, center_val=None, min_val=None, max_val=None,
                 cbar_ticks=None, colormap="vlag", row_colors=None, row_cluster=True,
                 col_colors=None, col_cluster=True, left_start=None, right_start=None,
                 w_spacing=None, h_spacing=None, save_dir=None, save_file=None):
    """Plots the z scores between all phenotypes as a clustermap.

    Args:
        data (numpy.ndarray):
            The data array to visualize
        x_labels (list):
            List of names displayed on horizontal axis
        y_labels (list):
            List of all names displayed on vertical axis
        dpi (float):
            The resolution of the image to save, ignored if save_dir is None
        center_val (float):
            value at which to center the heatmap
        min_val (float):
            minimum value the heatmap should take
        max_val (float):
            maximum value the heatmap should take
        cbar_ticks (int):
            list of values containing tick labels for the heatmap colorbar
        colormap (str):
            color scheme for visualization
        row_colors (list):
            Include these values as an additional color-coded cluster bar for row values
        row_cluster (bool):
            Whether to include dendrogram clustering for the rows
        col_colors (list):
            Include these values as an additional color-coded cluster bar for column values
        col_cluster (bool):
            Whether to include dendrogram clustering for the columns
        left_start (float):
            The position to set the left edge of the figure to (from 0-1)
        right_start (float):
            The position to set the right edge of the figure to (from 0-1)
        w_spacing (float):
            The amount of spacing to put between the subplots width-wise (from 0-1)
        h_spacing (float):
            The amount of spacing to put between the subplots height-wise (from 0-1)
        save_dir (str):
            If specified, a directory where we will save the plot
        save_file (str):
            If save_dir specified, specify a file name you wish to save to.
            Ignored if save_dir is None
    """

    # Replace the NA's and inf values with 0s
    data[np.isnan(data)] = 0
    data[np.isinf(data)] = 0

    # Assign numpy values respective phenotype labels
    data_df = pd.DataFrame(data, index=x_labels, columns=y_labels)
    sns.set(font_scale=.7)

    heatmap = sns.clustermap(
        data_df, cmap=colormap, center=center_val,
        vmin=min_val, vmax=max_val, row_colors=row_colors, row_cluster=row_cluster,
        col_colors=col_colors, col_cluster=col_cluster,
        cbar_kws={'ticks': cbar_ticks}
    )

    # ensure the row color axis doesn't have a label attacked to it
    if row_colors:
        _ = heatmap.ax_row_colors.xaxis.set_visible(False)

    if col_colors:
        _ = heatmap.ax_col_colors.yaxis.set_visible(False)

    # update the figure dimensions to accommodate Jupyter widget backend
    _ = heatmap.gs.update(
        left=left_start, right=right_start, wspace=w_spacing, hspace=h_spacing
    )

    # ensure the y-axis labels are horizontal, will be misaligned if vertical
    _ = plt.setp(heatmap.ax_heatmap.get_yticklabels(), rotation=0)

    if save_dir is not None:
        misc_utils.save_figure(save_dir, save_file, dpi=dpi)


def get_sorted_data(cell_data, sort_by_first, sort_by_second, is_normalized=False):
    """Gets the cell data and generates a new Sorted DataFrame with each row representing a
    patient and column representing Population categories

    Args:
        cell_data (pandas.DataFrame):
            Dataframe containing columns with Patient ID and Cell Name
        sort_by_first (str):
            The first attribute we will be sorting our data by
        sort_by_second (str):
            The second attribute we will be sorting our data by
        is_normalized (bool):
            Boolean specifying whether to normalize cell counts or not, default is False

    Returns:
        pandas.DataFrame:
            DataFrame with rows and columns sorted by population
    """

    cell_data_stacked = pd.crosstab(
        cell_data[sort_by_first],
        cell_data[sort_by_second],
        normalize='index' if is_normalized else False
    )

    # Sorts by Kagel Method :)
    index_facet_order = cell_data.groupby(sort_by_first).count().sort_values(
        by=sort_by_second,
        ascending=False
    ).index.values

    column_facet_order = cell_data.groupby(sort_by_second).count().sort_values(
        by=sort_by_first,
        ascending=False
    ).index.values

    cell_data_stacked = cell_data_stacked.reindex(index_facet_order, axis='index')
    cell_data_stacked = cell_data_stacked.reindex(column_facet_order, axis='columns')

    return cell_data_stacked


def plot_barchart(data, title, x_label, y_label, color_map="jet", is_stacked=True,
                  is_legend=True, legend_loc='center left', bbox_to_anchor=(1.0, 0.5),
                  dpi=None, save_dir=None, save_file=None):
    """A helper function to visualize_patient_population_distribution

    Args:
        data (pandas.DataFrame):
            The data we wish to visualize
        title (str):
            The title of the graph
        x_label (str):
            The label on the x-axis
        y_label (str):
            The label on the y-axis
        color_map (str):
            The name of the Matplotlib colormap used
        is_stacked (bool):
            Whether we want a stacked barchart or not
        is_legend (bool):
            Whether we want a legend or not
        legend_loc (str):
            If is_legend is set, specify where we want the legend to be
            Ignored if is_legend is False
        bbox_to_anchor (tuple):
            If is_legend is set, specify the bounding box of the legend
            Ignored if is_legend is False
        dpi (float):
            The resolution of the image to save, ignored if save_dir is None
        save_dir (str):
            Directory to save plots, default is None
        save_file (str):
            If save_dir specified, specify a file name you wish to save to.
            Ignored if save_dir is None
    """

    data.plot.bar(colormap=color_map, stacked=is_stacked, legend=is_legend)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)

    if is_legend:
        plt.legend(loc=legend_loc, bbox_to_anchor=bbox_to_anchor)

    if save_dir is not None:
        misc_utils.save_figure(save_dir, save_file, dpi=dpi)


def visualize_patient_population_distribution(cell_data, patient_col_name, population_col_name,
                                              color_map="jet", show_total_count=True,
                                              show_distribution=True, show_proportion=True,
                                              dpi=None, save_dir=None):
    """Plots the distribution of the population given by total count, direct count, and proportion

    Args:
        cell_data (pandas.DataFrame):
            Dataframe containing columns with Patient ID and Cell Name
        patient_col_name (str):
            Name of column containing categorical Patient data
        population_col_name (str):
            Name of column in dataframe containing Population data
        color_map (str):
            Name of MatPlotLib ColorMap used. Default is jet
        show_total_count (bool):
            Boolean specifying whether to show graph of total population count, default is true
        show_distribution (bool):
            Boolean specifying whether to show graph of population distribution, default is true
        show_proportion (bool):
            Boolean specifying whether to show graph of total count, default is true
        dpi (float):
            The resolution of the image to save, ignored if save_dir is None
        save_dir (str):
            Directory to save plots, default is None
    """

    cell_data = cell_data.dropna()

    # Plot by total count
    if show_total_count:
        population_values = cell_data[population_col_name].value_counts()
        title = "Distribution of Population in all patients"
        x_label = "Population Type"
        y_label = "Population Count"

        plot_barchart(population_values, title, x_label, y_label, is_legend=False,
                      dpi=dpi, save_dir=save_dir, save_file="PopulationDistribution.png")

    # Plot by count
    if show_distribution:
        sorted_data = get_sorted_data(cell_data, patient_col_name, population_col_name)
        title = "Distribution of Population Count in Patients"

        plot_barchart(sorted_data, title, patient_col_name, population_col_name,
                      dpi=dpi, save_dir=save_dir, save_file="TotalPopulationDistribution.png")

    # Plot by Proportion
    if show_proportion:
        sorted_data = get_sorted_data(cell_data, patient_col_name, population_col_name,
                                      is_normalized=True)
        title = "Distribution of Population Count Proportion in Patients"

        plot_barchart(sorted_data, title, patient_col_name, population_col_name,
                      dpi=dpi, save_dir=save_dir, save_file="PopulationProportion.png")


def visualize_neighbor_cluster_metrics(neighbor_cluster_stats, dpi=None, save_dir=None):
    """Visualize the cluster performance results of a neighborhood matrix

    Args:
        neighbor_cluster_stats (xarray.DataArray):
            contains the desired statistic we wish to visualize, should have one
            coordinate called cluster_num labeled starting from 2
        dpi (float):
            The resolution of the image to save, ignored if save_dir is None
        save_dir (str):
            Directory to save plots, default is None
    """

    # get the coordinates and values we'll need
    x_coords = neighbor_cluster_stats.coords['cluster_num'].values
    scores = neighbor_cluster_stats.values

    # plot the results
    plt.plot(x_coords, scores)
    plt.title("silhouette score vs number of clusters")
    plt.xlabel("Number of clusters")
    plt.ylabel("silhouette score")

    # save if desired
    if save_dir is not None:
        misc_utils.save_figure(save_dir, "neighborhood_cluster_scores.png", dpi=dpi)
