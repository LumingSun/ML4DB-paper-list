
# [Paper List] AI4DB / ML4DB / Autonomous Database / Self-driving Database / 智能数据库 / 自治数据库

Paper list for database systems with artificial intelligence (machine learning, deep learning, reinforcement learning)

New papers keep coming, remember to **Watch** this repo if you are interested in this topic.

有关机器学习、神经网络、强化学习、自调优技术等在数据库系统中的应用的文章列表，列表持续更新中，记得按赞、分享、打开小铃铛！

Welcome to PR!

欢迎大家补充！


Table of Contents
=================
* [System & Tutorial](#system-and-tutorial)
* [Data Access](#data-access)
  * [Configuration Tuning](#configuration-tuning)
  * [Physical Design](#physical-design)
    * [Learned structure](#learned-structure)
    * [LSM-tree related](#lsm-tree-related)
    * [Index](#index)
      * [Index Structure](#index-structure)
      * [Index Recommendation](#index-recommendation)
    * [Materialized View](#materialized-view)
    * [Schema &amp; Partition](#schema--partition)
      * [Offline](#offline)
      * [Online](#online)
  * [Cache related](#cache-related)
* [Workload](#workload)
    * [Resource Estimation and Auto-scaling](#resource-estimation-and-auto-scaling)
    * [Performance Diagnosis and Modeling](#performance-diagnosis-and-modeling)
    * [Workload Shift Detection](#workload-shift-detection)
    * [Metrics Prediction for Queries](#metrics-prediction-for-queries)
    * [Workload Characterization & Forecasting](#workload-characterization-&-forecasting)
* [Query Optimization](#query-optimization)
   * [Query Rewrite](#query-write)
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
* One Model to Rule them All: Towards Zero-Shot Learning for Databases (arXiv 2021)
* UDO: Universal Database Optimization using Reinforcement Learning (arXiv 2021)
* Towards a Benchmark for Learned Systems (SMDB workshop 2021)
* A Unified Transferable Model for ML-Enhanced DBMS [Vision] (arXiv 2021)
* AI Meets Database: AI4DB and DB4AI (SIGMOD 2021)
* Expand your Training Limits! Generating Training Data for ML-based Data Management (SIGMOD 2021)
* MB2: Decomposed Behavior Modeling for Self-Driving Database Management Systems (SIGMOD 2021)
* Towards instance-optimized data systems (VLDB 2021 from Tim Kraska)
* Make Your Database System Dream of Electric Sheep: Towards Self-Driving Operation (VLDB 2021 from Andy Pavlo)
* openGauss: An Autonomous Database System (VLDB 2021 from Guoliang Li)
* Experience-Enhanced Learning: One Size Still does not Fit All in Automatic Database Management (arXiv 2021)
* Baihe: SysML Framework for AI-driven Databases (arXiv 2022)
* Survey on Learnable Databases: A Machine Learning Perspective (Big Data Research 2021)
* Database Optimizers in the Era of Learning (ICDE 2022)
* Machine Learning for Data Management: A System View (ICDE 2022)
* Tastes Great! Less Filling! High Performance and Accurate Training Data Collection for Self-Driving Database Management Systems (SIGMOD 2022)
* SAM: Database Generation from Query Workload with Supervised Autoregressive Model (SIGMOD 2022)
* Detect, Distill and Update: Learned DB Systems Facing Out of Distribution Data (SIGMOD 2023)
* SageDB: An Instance-Optimized Data Analytics System (VLDB 2023)
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
* Too Many Knobs to Tune? Towards Faster Database Tuning by Pre-selecting Important Knobs (HotStorage 2020)
* Dynamic Configuration Tuning of Working Database Management Systems (LifeTech 2020)
* Adaptive Multi-Model Reinforcement Learning for Online Database Tuning (EDBT 2021)
* An inquiry into machine learning-based automatic configuration tuning services on real-world database management systems (VLDB 2021)
* The Case for NLP-Enhanced Database Tuning: Towards Tuning Tools that "Read the Manual" (VLDB 2021)
* CGPTuner: a Contextual Gaussian Process Bandit Approach for the Automatic Tuning of IT Configurations Under Varying Workload Conditions (VLDB 2021)
* ResTune: Resource Oriented Tuning Boosted by Meta-Learning for Cloud Databases (SIGMOD 2021)
* KML: Using Machine Learning to Improve Storage Systems (arXiv 2021)
* Database Tuning using Natural Language Processing (SIGMOD Record 2021)
* Towards Dynamic and Safe Configuration Tuning for Cloud Databases (SIGMOD 2022)
* Automatic Performance Tuning for Distributed Data Stream Processing Systems (ICDE 2022)
* Adaptive Code Learning for Spark Configuration Tuning (ICDE 2022)
* DB-BERT: A Database Tuning Tool that "Reads the Manual" (SIGMOD 2022)
* HUNTER: An Online Cloud Database Hybrid Tuning System for Personalized Requirements (SIGMOD 2022)
* LOCAT: Low-Overhead Online Configuration Auto-Tuning of Spark SQL Applications (SIGMOD 2022)
* Facilitating Database Tuning with Hyper-Parameter Optimization: A Comprehensive Experimental Evaluation (VLDB 2022)
* LlamaTune: Sample-Efficient DBMS Configuration Tuning (VLDB 2022)
* BLUTune: Query-informed Multi-stage IBM Db2 Tuning via ML (CIKM 2022)
* A Unified and Efficient Coordinating Framework for Autonomous DBMS Tuning (arXiv 2023)
* Automatic Database Knob Tuning: A Survey (TKDE)
### Physical Design
* Tiresias: Enabling Predictive Autonomous Storage and Indexing (VLDB 2022)
#### Learned structure
* Stacked Filters: Learning to Filter by Structure (VLDB 2021)
* LEA: A Learned Encoding Advisor for Column Stores (aiDM 2021)
#### LSM-tree related
* Leaper: A Learned Prefetcher for Cache Invalidation in LSM-tree based Storage Engines （VLDB 2020）
* From WiscKey to Bourbon: A Learned Index for Log-Structured Merge Trees (OSDI 2020)
* TridentKV: A Read-Optimized LSM-Tree Based KV Store via Adaptive Indexing and Space-Efficient Partitioning (TPDS 2022)
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
* Effectively Learning Spatial Indices (VLDB 2020) [GitHub Link](https://github.com/Liuguanli/RSMI)
* Stable Learned Bloom Filters for Data Streams (VLDB 2020)
* START — Self-Tuning Adaptive Radix Tree (ICDEW 2020)
* Learned Data Structures (2020)
* RadixSpline: a single-pass learned index (aiDM2020)
* The ML-Index: A Multidimensional, Learned Index for Point, Range, and Nearest-Neighbor Queries (EDBT 2020)
* The PGM-index: a fully-dynamic compressed learned index with provable worst-case bounds (VLDB 2020)
* A Tutorial on Learned Multi-dimensional Indexes (SIGSPATIAL 2020)
* Why Are Learned Indexes So Effective? (ICML 2020)
* Learned Indexes for a Google-scale Disk-based Database (arXiv 2020)
* SIndex: A Scalable Learned Index for String Keys （APSys 2020)
* XIndex: A Scalable Learned Index for Multicore Data Storage （PPoPP 2020)
* Tsunami: A Learned Multi-dimensional Index for Correlated Data and Skewed Workloads (VLDB 2021)
* A Lazy Approach for Efficient Index Learning (2021)
* The RLR-Tree: A Reinforcement Learning Based R-Tree for Spatial Data (arXiv 2021)
* Spatial Interpolation-based Learned Index for Range and kNN Queries (arXiv 2021)
* APEX: A High-Performance Learned Index on Persistent Memory (arXiv 2021)
* RUSLI: Real-time Updatable Spline Learned Index (aiDM 2021)
* PLEX: Towards Practical Learned Indexing (arXiv 2021)
* SPRIG: A Learned Spatial Index for Range and kNN Queries (SSTD 2021)
* Benchmarking Learned Indexes (VLDB 2021)
* Updatable Learned Index with Precise Positions (VLDB 2021)
* The Case for Learned In-Memory Joins (arXiv 2021)
* Bounding the Last Mile: Efficient Learned String Indexing (arXiv 2021)
* FINEdex: A Fine-grained Learned Index Scheme for Scalable and Concurrent Memory Systems (VLDB 2022)
* The next 50 Years in Database Indexing or: The Case for Automatically Generated Index Structures (VLDB 2022)
* The Concurrent Learned Indexes for Multicore Data Storage (Transactions on Storage 2022)
* TONE: cutting tail-latency in learned indexes (CHEOPS 22)
* A Learned Index for Exact Similarity Search in Metric Spaces (ArXiv 2022)
* RW-tree: A Learned Workload-aware Framework for R-tree Construction (ICDE 2022)
* The "AI+R"-tree: An Instance-optimized R-tree (MDM 2022)
* LHI: A Learned Hamming Space Index Framework for Efficient Similarity Search (SIGMOD 2022)
* Entropy Learned Hashing: 10X Faster Hashing with Controllable Uniformity (SIGMOD 2022)
* Tuning Hierarchical Learned Indexes on Disk and Beyond (SIGMOD 2022)
* FLIRT: A Fast Learned Index for Rolling Time frames (EDBT 2022)
* Testing the Robustness of Learned Index Structures (arXiv 2022)
* The Case for ML-Enhanced High-Dimensional Indexes (2022)
* A Learned Index for Exact Similarity Search in Metric Spaces (arxiv 2022)
* PLIN: A Persistent Learned Index for Non-Volatile Memory with High Performance and Instant Recovery (VLDB 2023)
* A Data-aware Learned Index Scheme for Efficient Writes (ICPP 2022)
* Frequency Estimation in Data Streams: Learning the Optimal Hashing Scheme (TKDE)
* FILM: A Fully Learned Index for Larger-Than-Memory Databases (VLDB 2023)
* WISK: A Workload-aware Learned Index for Spatial Keyword Queries (arXiv 2023)
* Efficiently Learning Spatial Indices (ICDE 2023)
* Cutting Learned Index into Pieces: An In-depth Inquiry into Updatable Learned Indexes (ICDE 2023)
* DILI: A Distribution-Driven Learned Index (arXiv 2023)
* Learned Index: A Comprehensive Experimental Evaluation (VLDB 2023)
* LMSFC: A Novel Multidimensional Index based on Learned Monotonic Space Filling Curves (Extended Version) (arXiv 2023)
##### Index Recommendation
* Index Selection in a Self- Adaptive Data Base Management System （SIGMOD 1976）
* AutoAdmin 'What-if' Index Analysis Utility (SIGMOD 1998)
* Self-Tuning Database Systems: A Decade of Progress (VLDB 2007)
* AI Meets AI: Leveraging Query Executions to Improve Index Recommendations (SIGMOD 2019) 
* Automated Database Indexing using Model-free Reinforcement Learning (ICAPS 2020)
* DRLindex: deep reinforcement learning index advisor for a cluster database (2020 Symposium on International Database Engineering & Applications)
* Magic mirror in my hand, which is the best in the land? An Experimental Evaluation of Index Selection Algorithms (VLDB 2020) [GitHub Link](https://github.com/hyrise/index_selection_evaluation)
* An Index Advisor Using Deep Reinforcement Learning (CIKM 2020) [GitHub Link](https://github.com/rmitbggroup/IndexAdvisor)
* DBA bandits: Self-driving index tuning under ad-hoc, analytical workloads with safety guarantees (ICDE 2021)
* MANTIS: Multiple Type and Attribute Index Selection using Deep Reinforcement Learning (IDEAS 2021)
* AutoIndex: An Incremental Index Management System for Dynamic Workloads (ICDE 2022) [GitHub Link](https://github.com/zhouxh19/AutoIndex)
* SWIRL: Selection of Workload-aware Indexes using Reinforcement Learning (EDBT 2022) [GitHub Link](https://github.com/hyrise/rl_index_selection)
* Indexer++: workload-aware online index tuning with transformers and reinforcement learning (ACM SIGAPP SAC, 2022)
* Budget-aware Index Tuning with Reinforcement Learning (SIGMOD 2022)
* ISUM: Efficiently Compressing Large and Complex Workloads for Scalable Index Tuning (SIGMOD 2022)
* DISTILL: Low-Overhead Data-Driven Techniques for Filtering and Costing Indexes for Scalable Index Tuning (VLDB 2022)
* SmartIndex: An Index Advisor with Learned Cost Estimator (CIKM 2022)
* HMAB: self-driving hierarchy of bandits for integrated physical database design tuning (VLDB 2022)
* Learned Index Benefits: Machine Learning Based Index Performance Estimation (VLDB 2023) [GitHub Link](https://github.com/JC-Shi/Learned-Index-Benefits)
* AIM: A practical approach to automated index management for SQL databases (ICDE 2023)
### Materialized View
* Automatic View Generation with Deep Learning and Reinforcement Learning (ICDE 2020)
* An Autonomous Materialized View Management System with Deep Reinforcement Learning (ICDE 2021)
* A Technical Report on Dynamic Materialized View Management using Graph Neural Network
* HMAB: self-driving hierarchy of bandits for integrated physical database design tuning (VLDB 2022)
* AutoView: An Autonomous Materialized View Management System with Encoder-Reducer (TKDE 2022)
* Dynamic Materialized View Management using Graph Neural Network (ICDE 2023)
#### Schema & Partition
##### Offline

* Schism: a Workload-Driven Approach to Database Replication and Partitioning (VLDB 2010)
* Skew-Aware Automatic Database Partitioning in Shared-Nothing, Parallel OLTP Systems (SIGMOD 2012)
* Automated Data Partitioning for Highly Scalable and Strongly Consistent Transactions (2016 Transactions on Parallel and distributed systems)
* GridFormation : Towards Self-Driven Online Data Partitioning using Reinforcement Learning (aiDM@SIGMOD 2018)
* Learning a Partitioning Advisor with Deep Reinforcement Learning (2019)
* Qd-tree: Learning Data Layouts for Big Data Analytics (SIGMOD 2020)
* A Genetic Optimization Physical Planner for Big Data Warehouses (2020)
* Lachesis: Automated Partitioning for UDF-Centric Analytics (VLDB 2021)
* Instance-Optimized Data Layouts for Cloud Analytics Workloads (SIGMOD 2021)
* Jigsaw: A Data Storage and Query Processing Engine for Irregular Table Partitioning (SIGMOD 2021)
* Dalton: Learned Partitioning for Distributed Data Streams (VLDB 2023)
* Grep: A Graph Learning Based Database Partitioning System (SIGMOD 2023)
##### Online

- Relax and Let the Database Do the Partitioning Online (BIRTE 2011)
- SWORD: Scalable Workload-Aware Data Placement for Transactional Workloads (EDBT 2013)
- Online Data Partitioning in Distributed Database Systems (EDBT 2015)
- A Robust Partitioning Scheme for Ad-Hoc Query Workloads (SOCC 2017)

### Cache related
* A Learned Cache Eviction Framework with Minimal Overhead (arXiv 2023)

## Workload

### Resource Management and Auto-scaling

* Automated Demand-driven Resource Scaling in Relational Database-as-a-Service (SIGMOD 2016)
* Database Workload Capacity Planning using Time Series Analysis and Machine Learning (SIGMOD 2020)
* Seagull: An Infrastructure for Load Prediction and Optimized Resource Allocation (VLDB 2020)
* FIRM: An Intelligent Fine-grained Resource Management Framework for SLO-Oriented Microservices (OSDI 2020)
* Optimal Resource Allocation for Serverless Queries (arXiv 2021)
* sinan: ml-based and qos-aware resource management for cloud microservices (ASPLOS 2021)
* Towards Optimal Resource Allocation for Big Data Analytics (EDBT 2022)
* Tenant Placement in Over-subscribed Database-as-a-Service Clusters (VLDB 2022)
* Fine-Grained Modeling and Optimization for Intelligent Resource Management in Big Data Processing (arXiv 2022)
* SIMPPO: a scalable and incremental online learning framework for serverless resource management (SoCC 2022)
* SUFS: A Generic Storage Usage Forecasting Service Through Adaptive Ensemble Learning (ICDE 2023)

### Performance Diagnosis and Modeling

- Performance and resource modeling in highly-concurrent OLTP workloads (SIGMOD 2013)
- DBSherlock: A Performance Diagnostic Tool for Transactional Databases (SIGMOD 2016)
- A Top-Down Approach to Achieving Performance Predictability in Database Systems (SIGMOD 2017)
- Diagnosing Root Causes of Intermittent Slow Queries in Cloud Databases (VLDB 2020)
- Workload-Aware Performance Tuning for Autonomous DBMSs (ICDE 2021)
- Sage: Practical and Scalable ML-Driven Performance Debugging in Microservices (ASPLOS 2021)

### Workload Shift Detection

- Towards workload shift detection and prediction for autonomic databases (CIKM 2007)
- Consistent on-line classification of dbs workload events (CIKM 2009)
- On predictive modeling for optimizing transaction execution in parallel OLTP systems (VLDB 2011)

### Workload Characterization & Forecasting

* On Workload Characterization of Relational Database Environments (TSE 1992)
* Workload Models for Autonomic Database Management Systems (International Conference on Autonomic and Autonomous Systems 2006)
* Workload characterization and prediction in the cloud: A multiple time series approach (APNOMS 2012）
* Query-based Workload Forecasting for Self-Driving Database Management Systems (SIGMOD 2018）
* Query2Vec: An Evaluation of NLP Techniques for Generalized Workload Analytics (Arxiv 2018)
* Database Workload Characterization with Query Plan Encoders (arXiv 2021)
* Explaining Inference Queries with Bayesian Optimization (VLDB 2021)
* Statistical Schema Learning with Occam's Razor (SIGMOD 2022)
* Intelligent Automated Workload Analysis for Database Replatforming (SIGMOD 2022)
* Stitcher: Learned Workload Synthesis from Historical Performance Footprints (EDBT 2022)
* DBAugur: An Adversarial-based Trend Forecasting System for Diversified Workloads (ICDE 2023)
* An Efficient Online Prediction of Host Workloads Using Pruned GRU Neural Nets (arXiv 2023)
* Uncertainty-Aware Workload Prediction in Cloud Computing (arXiv 2023)

## Query Optimization
### Query Rewrite
* Sia: Optimizing Queries using Learned Predicates (SIGMOD 2021)
* A Learned Query Rewrite System using Monte Carlo Tree Search (VLDB 2022)
* WeTune: Automatic Discovery and Verification of Query Rewrite Rules (SIGMOD 2022)
### Cardinality Estimation
* Are We Ready For Learned Cardinality Estimation? (VLDB 2021) [GitHub Link](https://github.com/sfu-db/AreCELearnedYet)
* A Unified Deep Model of Learning from both Data and Queries for Cardinality Estimation (SIGMOD 2021)
* LATEST: Learning-Assisted Selectivity Estimation Over Spatio-Textual Streams (ICDE 2021)
* Fauce: Fast and Accurate Deep Ensembles with Uncertainty for Cardinality Estimation (VLDB 2021)
* Cardinality Estimation in DBMS: A Comprehensive Benchmark Evaluation (arXiv 2021) [GitHub Link](https://github.com/Nathaniel-Han/End-to-End-CardEst-Benchmark)
* Learned Cardinality Estimation: A Design Space Exploration and A Comparative Evaluation (VLDB 2022)
* Glue: Adaptively Merging Single Table Cardinality to Estimate Join Query Size (aiXiv 2021)
* Unsupervised Selectivity Estimation by Integrating Gaussian Mixture Models and an Autoregressive Model (EDBT 2022)
* Selectivity Functions of Range Queries are Learnable (SIGMOD 2022)
* Prediction Intervals for Learned Cardinality Estimation: An Experimental Evaluation (ICDE 2022)
* Learned Cardinality Estimation: An In-depth Study (SIGMOD 2022)
* FactorJoin: A New Cardinality Estimation Framework for Join Queries (SIGMOD 2023)
* AutoCE: An Accurate and Efficient Model Advisor for Learned Cardinality Estimation (ICDE 2023)
* Couper: Memory-Efficient Cardinality Estimation under Unbalanced Distribution (ICDE 2023)
#### Data-based
(kernal density model)
* Self-Tuning, GPU-Accelerated Kernel Density Models for Multidimensional Selectivity Estimation (SIGMOD 2015)
* Estimating Join Selectivities using Bandwidth-Optimized Kernel Density Models (VLDB 2017)
(sum-product network)
* DeepDB: Learn from Data, not from Queries! (VLDB 2020) [GitHub Link](https://github.com/DataManagementLab/deepdb-public)

(autoregressive model)
* Deep Unsupervised Cardinality Estimation (VLDB 2019) 
* Multi-Attribute Selectivity Estimation Using Deep Learning (arXiv 2019)
* Deep Learning Models for Selectivity Estimation of Multi-Attribute Queries (SIGMOD 2020)
* NeuroCard: One Cardinality Estimator for All Tables (VLDB 2020) [GitHub Link](https://github.com/neurocard/neurocard)
* Learning to Sample: Counting with Complex Queries (VLDB 2020)
(graphical models)
* Selectivity estimation using probabilistic models (SIGMOD 2001)
* Lightweight graphical models for selectivity estimation without independence assumptions (VLDB 2011)
* Efficiently adapting graphical models for selectivity estimation (VLDB 2013)
* An Approach Based on Bayesian Networks for Query Selectivity Estimation (DASFAA 2019)
* BayesCard: A Unified Bayesian Framework for Cardinality Estimation (arXiv 2020) [GitHub Link](https://github.com/wuziniu/BayesCard)
* Online Sketch-based Query Optimization (arXiv 2021)
* LMKG: Learned Models for Cardinality Estimation in Knowledge Graphs (arXiv 2021)
* LHist: Towards Learning Multi-dimensional Histogram for Massive Spatial Data (ICDE 2021)
* FLAT: Fast, Lightweight and Accurate Method for Cardinality Estimation (VLDB 2021) [GitHub Link](https://github.com/wuziniu/FSPN)
* Astrid: Accurate Selectivity Estimation for String Predicates using Deep Learning (VLDB 2021)
* FACE: A Normalizing Flow based Cardinality Estimator (VLDB 2022)
* Pre-training Summarization Models of Structured Datasets for Cardinality Estimation (VLDB 2022)
* Cardinality Estimation of Approximate Substring Queries using Deep Learning (VLDB 2022)
#### Query-based
* Adaptive selectivity estimation using query feedback (SIGMOD 1994)
* Selectivity Estimation in Extensible Databases -A Neural Network Approach （VLDB 1998）
* Effective query size estimation using neural networks.  (Applied Intelligence 2002)
* LEO - DB2's LEarning optimizer （VLDB 2011)
* A Black-Box Approach to Query Cardinality Estimation (CIDR 07)
* Cardinality Estimation Using Neural Networks (2015)
* Towards a learning optimizer for shared clouds (VLDB 2018)
* Learning State Representations for Query Optimization with Deep Reinforcement Learning  (DEEM@SIGMOD2018)
* Learned Cardinalities: Estimating Correlated Joins with Deep Learning （CIDR2019）[GitHub Link](https://github.com/andreaskipf/learnedcardinalities)
* Estimating Cardinalities with Deep Sketches (SIGMOD 2019) [GitHub Link](https://github.com/andreaskipf/learnedcardinalities)
* Selectivity estimation for range predicates using lightweight models (VLDB 2019)
* (Review) An Empirical Analysis of Deep Learning for Cardinality Estimation (arXiv 2019)
* Flexible Operator Embeddings via Deep Learning (arXiv 2019)
* Improved Cardinality Estimation by Learning Queries Containment Rates (EDBT 2020)
* NN-based Transformation of Any SQL Cardinality Estimator for Handling DISTINCT, AND, OR and NOT (2020)
* QuickSel: Quick Selectivity Learning with Mixture Models (SIGMOD 2020)
* Efficiently Approximating Selectivity Functions using Low Overhead Regression Models (VLDB 2020)
* Learned Cardinality Estimation for Similarity Queries (SIGMOD 2021)
* Uncertainty-aware Cardinality Estimation by Neural Network Gaussian Process (arXiv 2021)
* Flow-Loss: Learning Cardinality Estimates That Matter (VLDB 2021)
* Warper: Efficiently Adapting Learned Cardinality Estimators to Data and Workload Drifts (SIGMOD 2022)
* Lightweight and Accurate Cardinality Estimation by Neural Network Gaussian Process for Approximate Complex Event Processing (SIGMOD 2022)
* Enhanced Featurization of Queries with Mixed Combinations of Predicates for ML-based Cardinality Estimation (EDBT 2023)
* Speeding Up End-to-end Query Execution via Learning-based Progressive Cardinality Estimation (SIGMOD 2023)
* Robust Query Driven Cardinality Estimation under Changing Workloads (VLDB 2023)
### Cost Estimation
#### Single Query
* Statistical learning techniques for costing XML queries (VLDB 2005)
* Predicting multiple metrics for queries: Better decisions enabled by machine learning （icde 2009)
* The Case for Predictive Database Systems : Opportunities and Challenges （CIDR 2011)
* Learning-based query performance modeling and prediction (ICDE 2012)
* Robust estimation of resource consumption for SQL queries using statistical techniques (VLDB 2012)
* Learning-based SPARQL query performance modeling and prediction (WWW 2017)
* Plan-Structured Deep Neural Network Models for Query Performance Prediction (arXiv 2019)
* An End-to-End Learning-based Cost Estimator (arXiv 2019)(VLDB 2019)
* Cost Models for Big Data Query Processing: Learning, Retrofitting, and Our Findings (2020)
* DBMS Fitting: Why should we learn what we already know? (CIDR 2020)
* A Note On Operator-Level Query Execution Cost Modeling (2020)
* Zero-Shot Cost Models for Out-of-the-box Learned Cost Prediction (VLDB 2022)
* Efficient Learning with Pseudo Labels for Query Cost Estimation (CIKM 2022)
* gCBO: A Cost-based Optimizer for Graph Databases (CIKM 2022)
* QueryFormer: A Tree Transformer Model for Query Plan Representation (VLDB 2022)

#### Concurrent
* PQR: Predicting query execution times for autonomous workload management （ICAC 2008）
* Performance Prediction for Concurrent Database Workloads (SIGMOD 2011)
* Predicting completion times of batch query workloads using interaction-aware models and simulation(EDBT 2011)
* Interaction-aware scheduling of report-generation workloads (VLDB 2011) （有调度策略）
* Towards predicting query execution time for concurrent and dynamic database workloads (not machine learning) （VLDB 2014）
* Contender: A Resource Modeling Approach for Concurrent Query Performance Prediction （EDBT 2014）
* Query Performance Prediction for Concurrent Queries using Graph Embedding (VLDB 2020)
* Efficient Deep Learning Pipelines for Accurate Cost Estimations Over Large Scale Query Workload (SIGMOD 2021)
* A Resource-Aware Deep Cost Model for Big Data Query Processing (ICDE 2022)
### Join Optimization
* Adaptive Optimization of Very Large Join Queries (SIGMOD 2018) (Not machine learning
* Deep Reinforcement Learning for Join Order Enumeration (aiDM@SIGMOD 2018)
* Learning to Optimize Join Queries With Deep Reinforcement Learning (ArXiv)
* Reinforcement Learning with Tree-LSTM for Join Order Selection (ICDE 2020)
* Research Challenges in Deep Reinforcement Learning-based Join Query Optimization (aiDM 2020)
* Efficient Join Order Selection Learning with Graph-based Representation (KDD 2022)
* SOAR:A Learned Join Order Selector with Graph Attention Mechanism （IJCNN 2022）
* Query Join Order Optimization Method Based on Dynamic Double Deep Q-Network (Electronics 2023)
### Query Plan
* Plan Selection Based on Query Clustering （VLDB 2002)
* Cost-Based Query Optimization via AI Planning (AAAI 2014)
* Sampling-Based Query Re-Optimization (SIGMOD 2016)
* Learning State Representations for Query Optimization with Deep Reinforcement Learning  (DEEM@SIGMOD2018)
* Towards a Hands-Free Query Optimizer through Deep Learning （CIDR 2019)
* Neo: A Learned Query Optimizer (VLDB 2019)
* Bao: Learning to Steer Query Optimizers (2020)
* ML-based Cross-Platform Query Optimization (ICDE 2020)
* Learning-based Declarative Query Optimization (2021)
* **Bao: Making Learned Query Optimization Practical** (SIGMOD 2021 **Best Paper**!) [Doc](https://rmarcus.info/bao_docs/introduction.html) [GitHub Link](https://github.com/learnedsystems/BaoForPostgreSQL)
* Microlearner: A fine-grained Learning Optimizer for Big Data Workloads at Microsoft (2021)
* Steering Query Optimizers: A Practical Take on Big Data Workloads (SIGMOD 2021)
* A Unified Transferable Model for ML-Enhanced DBMS (CIDR 2021)
* Balsa: Learning a Query Optimizer Without Expert Demonstrations (SIGMOD 2022)
* Leveraging Query Logs and Machine Learning for Parametric Query Optimization (VLDB 2022)
* Deploying a Steered Query Optimizer in Production at Microsoft (SIGMOD 2022)
* Building Learned Federated Query Optimizers (VLDB 2022 PhD Workshop)
* Cost-based or Learning-based? A Hybrid Query Optimizer for Query Plan Selection (VLDB 2022)
* Lero: A Learning-to-Rank Query Optimizer (VLDB 2023) [GitHub Link](https://github.com/AlibabaIncubator/Lero-on-PostgreSQL)
* Learned Query Superoptimization (arXiv 2023)
* Kepler: Robust Learning for Faster Parametric Query Optimization (SIGMOD 2023)
* LOGER: A Learned Optimizer towards Generating Efficient and Robust Query Execution Plans (VLDB 2023)


## Query Execution
### Sort
* The Case for a Learned Sorting Algorithm (SIGMOD 2020)
* Defeating duplicates: A re-design of the LearnedSort algorithm (aiXiv 2021)
* Towards Parallel Learned Sorting (arXiv 2022)
### Join
* SkinnerDB : Regret-Bounded Query Evaluation via Reinforcement Learning (VLDB 2018)
* The Case for Learned In-Memory Joins (arXiv 2021)
### Adaptive Query Processing
* Eddies: Continuously adaptive query processing. (SIGMOD 2000)
* Micro adaptivity in Vectorwise (SIGMOD 2013)
* Cuttlefish: A Lightweight Primitive for Adaptive Query Processing (2018)
* Scalable Multi-Query Execution using Reinforcement Learning (SIGMOD 2021)
### Approximate Query Processing
* DBEST: Revisiting approximate query processing engines with machine learning models (SIGMOD 2019)
* LAQP: Learning-based Approximate Query Processing (2020)
* Approximate Query Processing for Data Exploration using Deep Generative Models (ICDE 2020)
* ML-AQP: Query-Driven Approximate Query Processing based on Machine Learning (2020)
* Approximate Query Processing for Group-By Queries based on Conditional Generative Models (2021)
* Learned Approximate Query Processing: Make it Light, Accurate and Fast (CIDR 2021)
* NeuroSketch: Fast and Approximate Evaluation of Range Aggregate Queries with Neural Networks (arXiv 2022)
* Exploiting Machine Learning Models for Approximate Query Processing (Big Data 2022)
### Sheduling
* Workload management for cloud databases via machine learning (ICDE 2016 WiseDB)
* A learning-based service for cost and performance management of cloud databases （ICDEW 2017）(short version for WiSeDB)
* WiSeDB: A Learning-based Workload Management Advisor for Cloud Databases (2016 VLDB)
* Learning Scheduling Algorithms for Data Processing Clusters (SIGCOMM 2019)
* CrocodileDB: Efficient Database Execution through Intelligent Deferment (CIDT 2020)
* Buffer Pool Aware Query Scheduling via Deep Reinforcement Learning (2020)
* Self-Tuning Query Scheduling for Analytical Workloads (SIGMOD 2021)
* LSched: A Workload-Aware Learned Query Scheduler for Analytical Database Systems (SIGMOD 2022)

(transaction 👇)

* Scheduling OLTP transactions via learned abort prediction (aiDM@SIGMOD 2019)
* Scheduling OLTP Transactions via Machine Learning （2019）
* Polyjuice: High-Performance Transactions via Learned Concurrency Control (OSDI 2021)
## SQL Related
* Query2Vec (ArXiv)
* An End-to-end Neural Natural Language Interface for Databases
* SQLNet: Generating Structured Queries From Natural Language Without Reinforcement Learning （ArXiv）
* Facilitating SQL Query Composition and Analysis (ArXiv 2020)
* Natural language to SQL: Where are we today? (VLDB 2020）
* From Natural Language Processing to Neural Databases (VLDB 2021)
* BERT Meets Relational DB: Contextual Representations of Relational Databases
* CodexDB: Generating Code for Processing SQL Queries using GPT-3 Codex (ArXiv 2022)
* Natural language to SQL [Resource repo](https://github.com/yechens/NL2SQL)
* LearnedSQLGen: Constraint-aware SQL Generation using Reinforcement Learning (SIGMOD 2022)
* PreQR: Pre-training Representation for SQL Understanding (SIGMDO 2022)
* From BERT to GPT-3 Codex: Harnessing the Potential of Very Large Language Models for Data Management (VLDB 2022)
* A survey on deep learning approaches for text-to-SQL (VLDBJ)
* GAR: A Generate-and-Rank Approach for Natural Language to SQL Translation (ICDE 2023)
* Query Generation based on Generative Adversarial Networks (arXiv 2023)
* GAR: A Generate-and-Rank Approach for Natural Language to SQL Translation (ICDE 2023)
=================
## Stargazers over time

[![Stargazers over time](https://starchart.cc/LumingSun/ML4DB-paper-list.svg)](https://starchart.cc/LumingSun/ML4DB-paper-list)
