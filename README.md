# Papers_AIDB
Papers for database systems powered by artificial intelligence

有关机器学习、神经网络、强化学习、自调优技术等在数据库系统中的应用的文章列表
## Systems
* ***SageDB: A Learned Database System (CIDR 2019)***

* Database Learning: Toward a Database that Becomes Smarter Every Time (SIGMOD 2017)

* Self-Driving Database Management Systems (CIDR 2017)

* Self-Driving : From General Purpose to Specialized DBMSs (Phd@PVLDB 2018)  

## Data Access
### Configuration Tuning
* SARD: A statistical approach for ranking database tuning parameters (ICDEW, 2008)

* Regularized Cost-Model Oblivious Database Tuning with Reinforcement Learning （2016）

* Automatic Database Management System Tuning Through Large-scale Machine Learning (SIGMOD 2017)

* The Case for Automatic Database Administration using Deep Reinforcement Learning ( 2018 ArXiv)

* An End-to-End Automatic Cloud Database Tuning System Using Deep Reinforcement Learning

### Physical Design
#### Index
##### Index Structure
* Learning to hash for indexing big data - A survey (2016)

* The Case for Learned Index Structures

* A-Tree: A Bounded Approximate Index Structure (2017)

* Learned Indexes for Dynamic Workloads (2019)
##### Index Recommendation
* Index Selection in a Self- Adaptive Data Base Management System （SIGMOD 1976）

* AutoAdmin 'What-if' Index Analysis Utility (SIGMOD 1998)

* Self-Tuning Database Systems: A Decade of Progress (VLDB 2007)

* AI Meets AI: Leveraging Query Executions to Improve Index Recommendations (SIGMOD 2019)
#### Schema & Partition
##### Offline
* Schism: a Workload-Driven Approach to Database Replication and Partitioning (VLDB 2010)

* Automated Data Partitioning for Highly Scalable and Strongly Consistent Transactions (2016 Transactions on Parallel and distributed systems)
##### Online
* GridFormation : Towards Self-Driven Online Data Partitioning using Reinforcement Learning (aiDM@SIGMOD 2018)
##### DRL
* Learning a Partitioning Advisor with Deep Reinforcement Learning
### Workload
* Workload Models for Autonomic Database Management Systems (International Conference on Autonomic and Autonomous Systems 2006)

* Towards workload shift detection and prediction for autonomic databases (CIKM 2007)

* Query-based Workload Forecasting for Self-Driving Database Management Systems (SIGMOD 2018）
### Query Optimization
#### Cardinality Estimation
##### 传统估算方法的自调优
###### curve-fitting
* Adaptive selectivity estimation using query feedback (SIGMOD 1994)
###### KDE
* Self-Tuning, GPU-Accelerated Kernel Density Models for Multidimensional Selectivity Estimation (SIGMOD 2015)

* Estimating Join Selectivities using Bandwidth-Optimized Kernel Density Models (VLDB 2017)
###### Histogram 自调优
##### Machine Learning
* LEO - DB2's LEarning optimizer （VLDB 2011)

* A Black-Box Approach to Query Cardinality Estimation (CIDR 07)

* Towards a learning optimizer for shared clouds (VLDB 2018)
##### Neural Networks
* Selectivity Estimation in Extensible Databases -A Neural Network Approach （VLDB 1998）

* Effective query size estimation using neural networks.  (Applied Intelligence 2002)

* Cardinality Estimation Using Neural Networks (2015)

* Learning State Representations for Query Optimization with Deep Reinforcement Learning  (DEEM@SIGMOD2018)

* Learned Cardinalities: Estimating Correlated Joins with Deep Learning （CIDR2019）

* Estimating Cardinalities with Deep Sketches (SIGMOD 2019)

* Selectivity estimation for range predicates using lightweight models (VLDB 2019)

* Flexible Operator Embeddings via Deep Learning (2019)

* Multi-Attribute Selectivity Estimation Using Deep Learning (2019)
#### Cost Estimation
##### 非并发

* Statistical learning techniques for costing XML queries (VLDB 2005)

* Predicting multiple metrics for queries: Better decisions enabled by machine learning （icde 2009)
 
* The Case for Predictive Database Systems : Opportunities and Challenges （CIDR 2011)
 
* Learning-based query performance modeling and prediction (ICDE 2012)
 
* Robust estimation of resource consumption for SQL queries using statistical techniques (VLDB 2012)
 
* Plan-Structured Deep Neural Network Models for Query Performance Prediction
##### 并发
###### 静态
* PQR: Predicting query execution times for autonomous workload management （ICAC 2008）

* Performance Prediction for Concurrent Database Workloads (SIGMOD 2011)

* Predicting completion times of batch query workloads using interaction-aware models and simulation(EDBT 2011)

* Interaction-aware scheduling of report-generation workloads (VLDB 2011) （有调度策略）
###### 动态
* Towards predicting query execution time for concurrent and dynamic database workloads (not machine learning) （VLDB 2014）

* Contender: A Resource Modeling Approach for Concurrent Query Performance Prediction （EDBT 2014）
#### Join Optimization
* Adaptive Optimization of Very Large Join Queries (SIGMOD 2018) (Not machine learning

* Deep Reinforcement Learning for Join Order Enumeration (aiDM@SIGMOD 2018)

* Learning to Optimize Join Queries With Deep Reinforcement Learning (ArXiv)
#### Query Plan
* Plan Selection Based on Query Clustering （VLDB 2002)

* Cost-Based Query Optimization via AI Planning (AAAI 2014)

* Sampling-Based Query Re-Optimization (SIGMOD 2016)

* Learning State Representations for Query Optimization with Deep Reinforcement Learning  (DEEM@SIGMOD2018)

* Towards a Hands-Free Query Optimizer through Deep Learning （CIDR 2019)

* Neo: A Learned Query Optimizer (2019)
### Query Execution
#### Join
* SkinnerDB : Regret-Bounded Query Evaluation via Reinforcement Learning (VLDB 2018)
#### Adaptive Query Processing
* Eddies: Continuously adaptive query processing. (SIGMOD 2000)

* Micro adaptivity in Vectorwise (SIGMOD 2013)

* Cuttlefish: A Lightweight Primitive for Adaptive Query Processing (2018)
#### Sheduling
* Workload management for cloud databases via machine learning (ICDE 2016 WiseDB)
* A learning-based service for cost and performance management of cloud databases （ICDEW 2017）(short version for WiSeDB)
* WiSeDB: A Learning-based Workload Management Advisor for Cloud Databases (2016 VLDB)
### SQL Related
* Query2Vec (ArXiv)

* An End-to-end Neural Natural Language Interface for Databases

