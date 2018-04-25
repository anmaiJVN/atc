from time import gmtime, strftime

import click
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib as mpl
from sklearn.cluster import DBSCAN

from lib.common_utils import gen_log_file
logger = gen_log_file(path_to_file='tmp/clustering.log')
from lib.plot_utils import lat_lon_plot
from lib.geometric_utils import build_coordinator_dict, flight_id_encoder,\
    build_matrix_distances


def cluster_trajectories(dist_matrix, epsilon=1, min_samples=1):
    """
    Building cluster from distance matrix of all flight

    Args:
        dist_matrix ():
        epsilon (float):
        min_samples (int):

    Returns:
        clusters ()
        labels (list[int]): list of cluster id

    """

    db = DBSCAN(
        eps=epsilon,
        min_samples=min_samples,
        algorithm='auto',
        metric='precomputed'
    )
    db.fit(X=dist_matrix)

    labels = db.labels_
    num_clusters = len(set(labels))
    clusters = pd.Series(
        [dist_matrix[labels == idx] for idx in range(num_clusters)]
    )
    logger.info('Number of clusters: {0} flight ID '.format(num_clusters))
    return clusters, labels


@click.command()
@click.option(
    '--input_path',
    type=str,
    required=True,
    help='Full path to the trajectory file in CSV format')
@click.option(
    '--airport_code',
    type=str,
    default='WSSS',
    help='Air Port Codename')
def main(input_path, airport_code):
    df = pd.read_csv(input_path)
    logger.info(df.head())

    departure_airports = df['Origin'].unique()
    destination_airports = df['Destination'].unique()
    one_airport = df[(df['Destination'] == airport_code)]

    # get fixed
    flights_toward_airport = one_airport[(one_airport['DRemains'] < 1.0) & (one_airport['DRemains'] > 0.01)]
    lat_lon_plot(flights_toward_airport['Latitude'], flights_toward_airport['Longitude'], "tmp")

    flight_ids = flights_toward_airport['Flight_ID'].unique().tolist()
    logger.info("Total # flight ID {}".format(len(flight_ids)))
    flight_encoder = flight_id_encoder(flight_ids)

    encoded_idx, coord_list, flight_dicts,  = build_coordinator_dict(
        df=flights_toward_airport,
        label_encoder=flight_encoder,
        flight_ids=flight_ids,
        max_flights=1000
    )

    dist_matrix = build_matrix_distances(coord_list)
    alpha = 0.01
    upper_bound = max(dist_matrix[0,:])
    lower_bound = min(dist_matrix[0,:])
    step = (upper_bound - lower_bound) * alpha
    # logger.info(upper_bound, lower_bound, step)
    # return -1

    kms_per_radian = 6371.0088
    last_clusters = None

    # encode label cluster colors
    norm = mpl.colors.Normalize(vmin=-20, vmax=20)
    cmap = cm.hot
    m = cm.ScalarMappable(norm=norm, cmap=cmap)

    xy = np.zeros((2, 1000))
    xy[0] = range(1000)
    xy[1] = range(1000)

    for eps in np.arange(step*2, step*5, step):
        epsilon = eps
        # epsilon =  eps / kms_per_radian
        clusters, labels = cluster_trajectories(
            dist_matrix=dist_matrix,
            epsilon=epsilon,
            min_samples=2
        )
        # list of cluster id along side with the  encoded flight id
        logger.info(labels)
        last_clusters = clusters

        unique_labels = set(labels)
        logger.info(unique_labels)
        colors = [plt.cm.Spectral(each)
                  for each in np.linspace(0, 1, len(unique_labels))]
        logger.info(len(colors))

        plt.figure(figsize=(20, 10))
        for index, code in enumerate(encoded_idx):
            # if labels[index] == -1:
            #     # logger.info("outlier")
            #     continue
            plt.scatter(
                flight_dicts[code][:, 0],  # x axis
                flight_dicts[code][:, 1],  # y axis
                alpha=0.8,
                color=colors[labels[index]],
            )
        history = strftime("%Y-%m-%d %H:%M:%S", gmtime()).replace(" ", "_")
        plt.savefig("tmp/cluster_{}.png".format(len(clusters)))
        if len(clusters) == 2:
            break

    logger.info(last_clusters)


if __name__ == '__main__':
    main()
