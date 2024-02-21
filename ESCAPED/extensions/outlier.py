
import numpy as np


class kNNOutlierDetection():

    def __init__(self, gram):
        self.nb_samples = gram.shape[0]
        diag_helper = np.zeros(gram.shape)
        diag_helper[:] = gram[np.diag_indices(self.nb_samples)]
        squared_distances = diag_helper + np.transpose(diag_helper) -2*gram 
        self.distances = np.sqrt(squared_distances)
        self.knn = np.argsort(self.distances)

    def knn_simple_score(self, k):
        return self.distances[np.arange(self.nb_samples), self.knn[:,k]]

    def knn_weighted_score(self, k):
        return self.distances[np.arange(self.nb_samples),self.knn[:,1:k+1].T].T.sum(axis=1)

    def ldof_score(self, k):
        nrange = np.arange(1, k+1, 1)
        innercombinations = [(n1, n2) for n1 in nrange for n2 in nrange if n1<n2] 
        innerdists = np.zeros(self.nb_samples)
        for i in np.arange(self.nb_samples):
            innerdists[i] = sum(self.distances[self.knn[i,n1], self.knn[i,n2]] for (n1,n2) in innercombinations)/(k*(k-1)/2) 
        knndists = self.distances[np.arange(self.nb_samples),self.knn[:,1:k+1].T].T.sum(axis=1) / k
        return knndists/innerdists
 
    def lof_score(self, k):
        lrd_invs_tk = np.zeros(self.nb_samples)
        lof = np.zeros(self.nb_samples)
        for i in np.arange(self.nb_samples):
            lrd_invs_tk[i] = sum(max(self.distances[n, self.knn[n,k]], self.distances[i,n]) for n in self.knn[i, 1:k+1])
        for i in np.arange(self.nb_samples): 
            lof[i] = sum(lrd_invs_tk[i]/lrd_invs_tk[n] for n in self.knn[i,1:k+1])/k
        return lof


