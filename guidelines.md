# CodeFlares Features

 - Algorithm Database
 - Problem Database
 - Individual Skill Generator
 - Individual Training Model
 - Team Skill Generator
 - Team Training Model
 - Classroom Based Training
 - Automated Training Contest Generator
 
#### Algorithm Database
We have a collection of algorithms that most of the contestants use frequently in problem solving. All the algorithms are divided into two levels. The top level is called the root level and all the algorithms are divided into these root level categories.
For example, some of the root level categories are: *Base Algorithms, Number Theory, Graph, Data Structure, Dynamic Programming, Geometry* etc.
 - Some lower level algorithms under Number Theory: *GCD, LCM, Prime Number, Sieve, Prime Factorization* etc.
 - Similarly, some lower level algorithms under Graph: *BFS, DFS, Dijkstra, Bellmenford, SCC, DAG* etc.

Most of the lower level algorithms are somewhat dependent on some other lower level algorithms. For example, Dijkstra is dependent on Prority Queue, Prime Factorization is dependent on Prime Number and Sieve. Based on these dependencies we have created a weighted DAG where every edge a -> (b, e) denotes that the algorithm a is dependet on the algorithm b with a factor e (in range 1 to 10).

#### Problem Database
We have a rich collection of problems from different online judges and contest platforms like Codeforces, Codechef, UVa, SPOJ and LightOJ. For each of the problem 

#### Individual Skill Generator
The individual skill generator model generates your overall problem solving skill as well as your skill per each algorithm.

How it works?

1. We consider all the problems that you have solved so far.

 #### Individual Training
Our individual training model is based on your previous problem solving history. It generates the most relevant problems and algorithms considering your current skill level.