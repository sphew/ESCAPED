import numpy as np
import matplotlib.pyplot as plt
import logging 
from threading import Thread  

from ESCAPED.setup.function_party import FP
from ESCAPED.setup.peer import Peer
from ESCAPED.setup.connector import Connserver
from ESCAPED.extensions.outlier import kNNOutlierDetection


# settings to play around with
nb_peers = 6 # number of simulated input parties
nb_samples = 1000 # total number of samples in the combined data set
nb_features = 2 # number of features, set to 2 if you want to plot the data 

# outlier detection parameters
k = 15
n = nb_samples // 20  # top_n outlier
algorithms = ['knn', 'wknn', 'lof', 'ldof']

# should the result be plotted?
plot_results = True 
if plot_results and nb_features != 2:
    print("This example can only plot data with two features, sorry")
    plot_results = False


# for more information use level=logging.DEBUG
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


# data is randomly generated
data = np.random.normal(0, 3, size=(nb_samples, nb_features))

cuts = [(nb_samples // nb_peers)*i for i in range(nb_peers)] + [nb_samples] 
peer_ids = ['client_'+str(i+1) for i in range(nb_peers)]

# our helper for establishing connections
connector_address = ('localhost', 9999)
connector = Connserver(connector_address, peer_ids)
conn_t = Thread(target=connector.run)
conn_t.start()

# start all input parties
for i, peer_id in enumerate(peer_ids):
    peer_data = data[cuts[i]:cuts[i+1],:] # respective share of data
    peer = Peer(peer_id, connector_address, peer_data)
    peer_t = Thread(target=peer.cooperate)
    peer_t.start()

# start function party
fp = FP(connector_address)
fp_t = Thread(target=fp.cooperate)
fp_t.start()

# wait until communication successfully finished
fp_t.join()
dp_by_escaped = fp.get_dot_product()

# compare to reference dot product
dp_cmp = data @ np.transpose(data)
dp_correct = np.isclose(dp_by_escaped.astype(np.float64), dp_cmp.astype(np.float64)).all() 
print("DP is correct:", dp_correct) 


# offline phase: outlier detection
detector = kNNOutlierDetection(dp_by_escaped)
if plot_results:
    fig, axes = plt.subplots(1, len(algorithms)) 
for i, algo in enumerate(algorithms):
    if algo == 'knn':
         score = detector.knn_simple_score(k)
    if algo == 'wknn':
         score = detector.knn_weighted_score(k)
    if algo == 'lof':
         score = detector.lof_score(k)
    if algo == 'ldof':
         score = detector.ldof_score(k)
    print("calculated score for", algo)
    outlier_sorted = np.argsort(-score)
    outlier_idx = outlier_sorted[:n]
    inlier_idx = outlier_sorted[n:]
    outlier = data[outlier_idx,:]
    inlier = data[inlier_idx,:]
    if plot_results:
        axes[i].scatter(inlier[:,0], inlier[:,1], color='b')
        axes[i].scatter(outlier[:,0], outlier[:,1], color='r', marker='*', s=100)
        axes[i].set_title(algo)
if plot_results:
    plt.show()




