# CodeFlares Features

 - Algorithm Database
 - Problem Database
 - Individual Skill Generator
 - Individual Training Model
 - Team Skill Generator
 - Team Training Model
 - Automated Training Contest Generator
 - Classroom Based Training
 
### Algorithm Database
We have a collection of algorithms that most of the contestants use frequently in problem solving. All these algorithms are divided into two levels. The top level is called the root level which contains the root level categories and all the algorithms are divided into these root level categories.
For example, some of the root level categories are: *Base Algorithms, Number Theory, Graph, Data Structure, Dynamic Programming, Geometry* etc.
 - Some lower level algorithms under Number Theory: *GCD, LCM, Prime Number, Sieve, Prime Factorization* etc.
 - Similarly, some lower level algorithms under Graph: *BFS, DFS, Dijkstra, Bellmenford, SCC, DAG* etc.

Most of the lower level algorithms are somewhat dependent on some other lower level algorithms. For example, Dijkstra is dependent on Prority Queue, Prime Factorization is dependent on Prime Number and Sieve. Based on these dependencies we have created a **category-dependency-matrix**. Which is basically a collection of edges from an weighted DAG where every edge **a -> (b, e)** denotes that the algorithm **a** is dependent on the algorithm **b** with a factor **e** (in range 1 to 10).

### Problem Database
We have a rich collection of problems from different online judges and contest platforms like Codeforces, Codechef, UVa, SPOJ and LightOJ. Each of these problems contains a connection list which denotes how much a problem is connected to some categories. Considering this connection list for each of the problem, we have created a **problem-category-connection-matrix**.

For example, some problem X might be connected to some algorithms Y with a factor  P. Which means, to solve the problem X you need to learn the algorithm Y upto a certain level (*which depends on the factor*).

At the same time it also means that if you can solve the problem X then your skill in algorithm Y will get increased. How much it'll increase it depends on the difficulty of the problem and the factor of the connection.

### Individual Skill Generator
The individual skill generator model generates your overall problem solving skill as well as your skill per each algorithm. It considers your previous problem solving record for each algorithms.

How it works?

1. Considering your problem solving record, we generate your skill for each of the lower level algorithms. For any algorithm X, the skill of that algorithm depends on the problems that have some connections with the algorithm X. Every solved problem of a user contribute to the skill of the algorithms which are connected to that algorithm. As explained in the Problem Database section, for any solved problem P, how much it'll contribute to the skill of a algorithm it depends on the following two factors: **problem-difficulty** and **problem-category-connection-matrix**. Using this factors for each solved problems, we generate a slill value for all the lower level algorithms.
3. Now we generate the skill for the the root categories using the skill of the algorithm of that particular root category. We have a **algorithm-percentage-matrix** which stores the information about how much an algorithm contribute to the overall skill of a root category.
4. Finally we generate the overall current skill of an user using our **root-algorithm-percentage-matrix**. Each entry of this matrix denotes how much a root category contribute to the overall total skill of a contestant.

 ### Individual Training Model
Our individual training model is based on the algorithm skill we generated in the previous steps. Using the algorithm skill, our training model generates a **relevant-score** for each problem and algorithm. This **relevant-score** denotes how much a problem or algorithm is relevant for you right now considering your current problem solving skill.

In the individual training model page, we suggest the top 5 problems and algorithms for you to approach in the upcoming week. If you don't like a problem or if you think you have already solve a problem like that before, then you have the option to move it to **blacklist** or you can **flag** it temporarily for 3 days. Ofcourse, you have the option to undo this operations from the **tasklist** on your top bar.

### Team Skill Generator
Our team skill generator model is similar to the Individual Skill Generator model. Here, it just considers all the solved problems combinedly by all the team members.

### Team Training Model
Our team training model is similar to the Individual Training Model. Here, it just considers all the solved problems combinedly by all the team members.

### Automated Training Contest Generator
We also have a automated training contest generator for your practice.
