
# [Paper List] AI4DB / autonomous database / 智能数据库 / self-driving database
Paper list for database systems with artificial intelligence (machine learning, deep learning, reinforcement learning)

有关机器学习、神经网络、强化学习、自调优技术等在数据库系统中的应用的文章列表

Welcome to PR! 

欢迎大家补充！

Table of Contents
=================
* [System & Tutorial](#system-and-tutorial)
* [Data Access](#data-access)
  * [Configuration Tuning](#configuration-tuning)
  * [Physical Design](#physical-design)
    * [LSM-tree related](#lsm-tree-related)
    * [Index](#index)
      * [Index Structure](#index-structure)
      * [Index Recommendation](#index-recommendation)
    * [Schema &amp; Partition](#schema--partition)
* [Workload](#workload)
* [Query Optimization](#query-optimization)
    * [Cardinality Estimation](#cardinality-estimation)
      * [Data-based](#data-based)
      * [Query-based](#query-based)
  * [Cost Estimation](#cost-estimation)
    * [Single Query](#single-query)
    * [Concurrent](#Concurrent)
  * [Join Optimization](#join-optimization)
  * [Query Plan](#query-plan)
* [Query Execution](#query-execution)
  * [Sort](#sort)
  * [Join](#join)
  * [Adaptive Query Processing](#adaptive-query-processing)
  * [Approximate Query Processing](#Approximate-query-processing)
  * [Sheduling](#sheduling)
* [SQL Related](#sql-related)


## System and Tutorial
* ***SageDB: A Learned Database System (CIDR 2019)***

* Database Learning: Toward a Database that Becomes Smarter Every Time (SIGMOD 2017)

* Self-Driving Database Management Systems (CIDR 2017)

* Self-Driving : From General Purpose to Specialized DBMSs (Phd@PVLDB 2018)  

* Active Learning for ML Enhanced Database Systems (SIGMOD 2020)

* Database Meets Artificial Intelligence: A Survey (TKDE 2020)

* Self-driving database systems: a conceptual approach (Distributed and Parallel Databases 2020)
## Data Access
### Configuration Tuning
* SARD: A statistical approach for ranking database tuning parameters (ICDEW, 2008)

* Regularized Cost-Model Oblivious Database Tuning with Reinforcement Learning （2016）

* Automatic Database Management System Tuning Through Large-scale Machine Learning (SIGMOD 2017)

* The Case for Automatic Database Administration using Deep Reinforcement Learning ( 2018 ArXiv)

* An End-to-End Automatic Cloud Database Tuning System Using Deep Reinforcement Learning (SIGMOD 2019)

* External vs. Internal : An Essay on Machine Learning Agents for Autonomous Database Management Systems

* QTune: A Query-Aware Database Tuning System with Deep Reinforcement Learning (VLDB 2019)

* Optimizing Databases by Learning Hidden Parameters of Solid State Drives (VLDB 2019)

* iBTune: Individualized Buffer Tuning for Large-scale Cloud Databases (VLDB 2019)

* Black or White? How to Develop an AutoTuner for Memory-based Analytics (SIGMOD 2020)

* Learning Efficient Parameter Server Synchronization Policies for Distributed SGD (ICLR 2020)
### Physical Design
#### LSM-tree related
* Leaper: A Learned Prefetcher for Cache Invalidation in LSM-tree based Storage Engines （VLDB 2020）
#### Index
##### Index Structure
* Learning to hash for indexing big data - A survey (2016)

* The Case for Learned Index Structures (SIGMOD 2018)

* A-Tree: A Bounded Approximate Index Structure (2017)

* FITing-Tree: A Data-aware Index Structure (SIGMOD 2019)

* Learned Indexes for Dynamic Workloads (2019)

* SOSD: A Benchmark for Learned Indexes (2019)

* Learning Multi-dimensional Indexes (2019)

* ALEX: An Updatable Adaptive Learned Index (SIGMOD 2020)

* The ML-Index: A Multidimensional, Learned Index for Point, Range, and Nearest-Neighbor Queries (EDBT 2020)

* Effectively Learning Spatial Indices (VLDB 2020)

* Stable Learned Bloom Filters for Data Streams (VLDB 2020)

* START — Self-Tuning Adaptive Radix Tree (ICDEW 2020)

* Learned Data Structures (2020)

* The ML-Index: A Multidimensional, Learned Index for Point, Range, and Nearest-Neighbor Queries (EDBT 2020)
##### Index Recommendation
* Index Selection in a Self- Adaptive Data Base Management System （SIGMOD 1976）

* AutoAdmin 'What-if' Index Analysis Utility (SIGMOD 1998)

* Self-Tuning Database Systems: A Decade of Progress (VLDB 2007)

* AI Meets AI: Leveraging Query Executions to Improve Index Recommendations (SIGMOD 2019)

* Automated Database Indexing using Model-free Reinforcement Learning (2020)

* DRLindex: deep reinforcement learning index advisor for a cluster database (2020 Symposium on International Database Engineering & Applications)
#### Schema & Partition
* Schism: a Workload-Driven Approach to Database Replication and Partitioning (VLDB 2010)

* Automated Data Partitioning for Highly Scalable and Strongly Consistent Transactions (2016 Transactions on Parallel and distributed systems)

* GridFormation : Towards Self-Driven Online Data Partitioning using Reinforcement Learning (aiDM@SIGMOD 2018)

* Learning a Partitioning Advisor with Deep Reinforcement Learning (2019)

* Qd-tree: Learning Data Layouts for Big Data Analytics (SIGMOD 2020)
## Workload
* Workload Models for Autonomic Database Management Systems (International Conference on Autonomic and Autonomous Systems 2006)

* Towards workload shift detection and prediction for autonomic databases (CIKM 2007)

* Query-based Workload Forecasting for Self-Driving Database Management Systems (SIGMOD 2018）

* Diagnosing Root Causes of Intermittent Slow Queries in Cloud Databases (VLDB 2020)
## Query Optimization
### Cardinality Estimation

#### Data-based
(kernal density model)
* Self-Tuning, GPU-Accelerated Kernel Density Models for Multidimensional Selectivity Estimation (SIGMOD 2015)

* Estimating Join Selectivities using Bandwidth-Optimized Kernel Density Models (VLDB 2017)

(sum-product network)
* DeepDB: Learn from Data, not from Queries! (VLDB 2020)

(autoregressive model)
* Deep Unsupervised Cardinality Estimation (VLDB 2019) 

* Multi-Attribute Selectivity Estimation Using Deep Learning (arXiv 2019)

* Deep Learning Models for Selectivity Estimation of Multi-Attribute Queries (SIGMOD 2020)

* NeuroCard: One Cardinality Estimator for All Tables (2020)

(graphical models)
* Selectivity estimation using probabilistic models (SIGMOD 2001)

* Lightweight graphical models for selectivity estimation without independence assumptions (VLDB 2011)

* An Approach Based on Bayesian Networks for Query Selectivity Estimation (DASFAA 2019)

* Efficiently adapting graphical models for selectivity estimation (VLDB 2013)

#### Query-based
* Adaptive selectivity estimation using query feedback (SIGMOD 1994)

* Selectivity Estimation in Extensible Databases -A Neural Network Approach （VLDB 1998）

* Effective query size estimation using neural networks.  (Applied Intelligence 2002)

* LEO - DB2's LEarning optimizer （VLDB 2011)

* A Black-Box Approach to Query Cardinality Estimation (CIDR 07)

* Cardinality Estimation Using Neural Networks (2015)

* Towards a learning optimizer for shared clouds (VLDB 2018)

* Learning State Representations for Query Optimization with Deep Reinforcement Learning  (DEEM@SIGMOD2018)

* Learned Cardinalities: Estimating Correlated Joins with Deep Learning （CIDR2019）

* Estimating Cardinalities with Deep Sketches (SIGMOD 2019)

* Selectivity estimation for range predicates using lightweight models (VLDB 2019)

* (Review) An Empirical Analysis of Deep Learning for Cardinality Estimation (arXiv 2019)

* Flexible Operator Embeddings via Deep Learning (arXiv 2019)

* Improved Cardinality Estimation by Learning Queries Containment Rates (EDBT 2020)

* NN-based Transformation of Any SQL Cardinality Estimator for Handling DISTINCT, AND, OR and NOT (2020)

* QuickSel: Quick Selectivity Learning with Mixture Models (SIGMOD 2020)

* Efficiently Approximating Selectivity Functions using Low Overhead Regression Models (VLDB 2020)
### Cost Estimation
#### Single Query
* Statistical learning techniques for costing XML queries (VLDB 2005)

* Predicting multiple metrics for queries: Better decisions enabled by machine learning （icde 2009)
 
* The Case for Predictive Database Systems : Opportunities and Challenges （CIDR 2011)
 
* Learning-based query performance modeling and prediction (ICDE 2012)
 
* Robust estimation of resource consumption for SQL queries using statistical techniques (VLDB 2012)
 
* Plan-Structured Deep Neural Network Models for Query Performance Prediction (arXiv 2019)

* An End-to-End Learning-based Cost Estimator (arXiv 2019)(VLDB 2019)

* Cost Models for Big Data Query Processing: Learning, Retrofitting, and Our Findings (2020)

* DBMS Fitting: Why should we learn what we already know? (CIDR 2020)

* A Note On Operator-Level Query Execution Cost Modeling (2020)
#### Concurrent
* PQR: Predicting query execution times for autonomous workload management （ICAC 2008）

* Performance Prediction for Concurrent Database Workloads (SIGMOD 2011)

* Predicting completion times of batch query workloads using interaction-aware models and simulation(EDBT 2011)

* Interaction-aware scheduling of report-generation workloads (VLDB 2011) （有调度策略）

* Towards predicting query execution time for concurrent and dynamic database workloads (not machine learning) （VLDB 2014）

* Contender: A Resource Modeling Approach for Concurrent Query Performance Prediction （EDBT 2014）

* Query Performance Prediction for Concurrent Queries using Graph Embedding (VLDB 2020)
### Join Optimization
* Adaptive Optimization of Very Large Join Queries (SIGMOD 2018) (Not machine learning

* Deep Reinforcement Learning for Join Order Enumeration (aiDM@SIGMOD 2018)

* Learning to Optimize Join Queries With Deep Reinforcement Learning (ArXiv)

* Reinforcement Learning with Tree-LSTM for Join Order Selection (ICDE 2020)
### Query Plan
* Plan Selection Based on Query Clustering （VLDB 2002)

* Cost-Based Query Optimization via AI Planning (AAAI 2014)

* Sampling-Based Query Re-Optimization (SIGMOD 2016)

* Learning State Representations for Query Optimization with Deep Reinforcement Learning  (DEEM@SIGMOD2018)

* Towards a Hands-Free Query Optimizer through Deep Learning （CIDR 2019)

* Neo: A Learned Query Optimizer (VLDB 2019)

* Bao: Learning to Steer Query Optimizers (2020)

* ML-based Cross-Platform Query Optimization (ICDE 2020)
## Query Execution
### Sort
* The Case for a Learned Sorting Algorithm (SIGMOD 2020)
### Join
* SkinnerDB : Regret-Bounded Query Evaluation via Reinforcement Learning (VLDB 2018)
### Adaptive Query Processing
* Eddies: Continuously adaptive query processing. (SIGMOD 2000)

* Micro adaptivity in Vectorwise (SIGMOD 2013)

* Cuttlefish: A Lightweight Primitive for Adaptive Query Processing (2018)
### Approximate Query Processing
* DBEST: Revisiting approximate query processing engines with machine learning models (SIGMOD 2019)

* LAQP: Learning-based Approximate Query Processing (2020)

* Approximate Query Processing for Data Exploration using Deep Generative Models (ICDE 2020)

* ML-AQP: Query-Driven Approximate Query Processing based on Machine Learning (2020)
### Sheduling
* Workload management for cloud databases via machine learning (ICDE 2016 WiseDB)

* A learning-based service for cost and performance management of cloud databases （ICDEW 2017）(short version for WiSeDB)

* WiSeDB: A Learning-based Workload Management Advisor for Cloud Databases (2016 VLDB)

* Buffer Pool Aware Query Scheduling via Deep Reinforcement Learning (Computer Science 2020)

* CrocodileDB: Efficient Database Execution through Intelligent Deferment (CIDT 2020)

(transaction 👇)

* Scheduling OLTP transactions via learned abort prediction (aiDM@SIGMOD 2019)

* Scheduling OLTP Transactions via Machine Learning （2019）
## SQL Related
* Query2Vec (ArXiv)

* An End-to-end Neural Natural Language Interface for Databases

* SQLNet: Generating Structured Queries From Natural Language Without Reinforcement Learning （ArXiv）

* Facilitating SQL Query Composition and Analysis (ArXiv 2020)

* Natural language to SQL: Where are we today? (VLDB 2020）
