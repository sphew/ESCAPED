# ESCAPED with outlier detection

The Efficient Secure and Private Dot Product Framework (ESCAPED) proposed by Ünal et al.  [1, 2] enables the secure and private computation of the dot product of vectors from different data sources. 
Data owners pairwise communicate with each other and a function party, sharing masked versions of their data, thereby allowing the function party to compute the dot product in the plaintext domain without learning the original data.  Once the dot product is determined, it can be used to statistically evaluate the combined data.
This is my reimplementation of the framework which I used in my master's thesis. I have extended ESCAPED with an outlier detection module that takes the dot product as input and calculates outlier scores for each data point. The kNN-based outlier detection algorithms presented here are knn [3], wknn [4], lof [5] and ldof [6].
For a plug-and-play setup, please refer to example.py

## Sources

[1] A. B. Ünal, M. Akgün, and N. Pfeifer, “ESCAPED: Efficient Secure and Private Dot Product Framework for Kernel-based Machine Learning Algorithms with Applications in Healthcare”, _AAAI_, vol. 35, no. 11, pp. 9988-9996, May 2021.
[2] https://github.com/mdppml/ESCAPED
[3] Sridhar Ramaswamy, Rajeev Rastogi, and Kyuseok Shim. Eﬀicient algorithms for mining outliers from large data sets. In Proceedings of the 2000 ACM SIGMOD International Conference on Management of Data, SIGMOD ’00, page 427–438, New York, NY, USA, 2000. Association for Computing Machinery. doi: 10.1145/342009.335437
[4] Fabrizio Angiulli and Clara Pizzuti. Fast outlier detection in high dimensional spaces. Proceedings of the Sixth European Conference on the Principles of Data Mining and Knowledge Discovery, 2431:15–26, 08 2002. doi: 10.1007/3-540-45681-3_2.
[5] Markus M. Breunig, Hans-Peter Kriegel, Raymond T. Ng, and Jörg Sander. Lof: Identifying density-based local outliers. In Proceedings of the 2000 ACM SIG-MOD International Conference on Management of Data, SIGMOD ’00, page 93–104, New York, NY, USA, 2000. Association for Computing Machinery.  doi: 10.1145/342009.335388.
[6] Ke Zhang, Marcus Hutter, and Huidong Jin. A new local distance-based outlier detection approach for scattered real-world data. volume 5476, 03 2009. doi: 10.1007/978-3-642-01307-2_84.
