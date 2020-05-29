
### Features

1. Algorithm Database
1. Problem Database
1. Individual Skill Generator
1. Individual Training Model
1. Team Skill Generator
1. Team Training Model
1. Automated Training Contest Generator
1. Classroom Based Training
1. Learning Resources
1. Blog
 
#### Algorithm Database
We have a collection of algorithms that most of the contestants use frequently in problem solving.
All these algorithms are divided into two levels. The first level is called the **root level** which contains only
the **root level categories**. And the second level is called the **child level** which consists of all the algorithms.
The child level algorithms are then divided into the root level categories.

For example, some of the root level categories are: *Base Algorithms, Number Theory, Graph, Data Structure, Dynamic Programming, Geometry* etc.
1. Some second level algorithms that fall under **Number Theory**: *GCD, LCM, Prime Number, Sieve, Prime Factorization* etc.
1. Similarly, some second level algorithms that fall under **Graph**: *BFS, DFS, Dijkstra, Bellmanford, SCC, DAG* etc.

Most of the second level algorithms are somewhat dependent on some other second level algorithms. For example,

**Dijkstra** is dependent on Priority Queue, BFS & DFS.

**Prime Factorization** is dependent on Prime Number and Sieve. 

Based on these dependencies we have created a **category-dependency-matrix**. Which is basically a collection of edges from
an weighted DAG, where every edge **a -> (b, f)** in the DAG denotes that the algorithm **a** is dependent
on the algorithm **b** with a factor **f** (_in range 1 to 10_).


#### Problem Database
We have a rich collection of problems from different online judges and contest platforms like Codeforces, Codechef, UVa, SPOJ and LightOJ.
Each of these problems contains a connection list, which denotes how much a problem is connected to some categories.
Considering this connection list for each of the problem, we have created a **problem-category-connection-matrix**.

For example, some problem **X** might be connected to some algorithms **Y** with a factor **P**. Which means, to solve
the problem **X** you need to learn the algorithm **Y** upto a certain level (*depends on the factor*).

At the same time it also means that if you can solve the problem **X** then your skill in algorithm **Y** will get increased
by a factor which depends on the _problem-difficulty_ of the problem and the _factor_ of the connection.


#### Individual Skill Generator
The individual skill generator model generates your overall problem solving skill as well as your skill per each algorithm
considering your problem solving record.

###### How it works?

1. Considering your problem solving record, we generate your skill for each of the second level algorithms.

2. For any algorithm **X**, the skill of that algorithm depends on the problems that have some connections with the algorithm **X**.
Every solved problem of an user contribute to the skill of the algorithms which are connected to that algorithm.

3. As explained in the **Problem Database** section, for any solved problem **P**, how much it'll contribute to the skill of a algorithm
it depends on the following two factors: **problem-difficulty** and **problem-category-connection-matrix**.
Using this factors for each solved problems, we generate a skill value for all the second level algorithms.

4. Now we generate the skill value for the **root level categories** using the skill value of the algorithms that fall under that particular
root category. We have a **algorithm-percentage-matrix** which stores the information of how much an algorithm contribute to the overall
skill value of a root category.

4. Finally we generate the **overall current skill** of an user using our **root-algorithm-percentage-matrix**.
Each entry of this matrix denotes how much a root category contribute to the **overall total skill** of a contestant.


#### Individual Training Model
Our individual training model is based on the algorithm skill value we generated in the previous models. Using the algorithm skill,
our training model generates a **relevant-score** for each problem and algorithm. This **relevant-score** denotes how much
a problem or algorithm is relevant for you right now considering your current problem solving skill.

In the individual training model page, we suggest the top 5 problems and algorithms for you to approach in the upcoming week.
If you don't like a problem or if you think you have already solve a similar before, then you have the option to
move it to **blacklist** or you can **flag** it temporarily for 3 days. Of course, you have the option to undo this operations
from the **tasklist** on the top bar.


#### Team Skill Generator
Our team skill generator model is similar to the Individual Skill Generator model. Here, we just consider all the solved problems
combined by all the team members.


#### Team Training Model
Our team training model is similar to the Individual Training Model. Here, it just considers the
algorithm skill value generated by the **Team Skill Generator** model.


#### Automated Training Contest Generator
We also have a automated training contest generator for your practice. You can generate a contest for your individual practice,
team practice or even for the classroom training purposes.

###### How it works?

1. You can generate a completely automated training contest for your practice. Make a request from our
*Training Contest -> Create Training Contest* page providing the required information. We create a automated contest for
you using our **randomized algorithm model** following ACM ICPC problem structure.

2. You can also request for a customized contest adding some custom filters. For example, let's say you want a problem set where at least
**M** problems must be from ***Data Structure*** with difficulty range **(u - v)** and **N** problems from ***Graph*** with
difficulty range **(p - q)**. Add these options in the customized filter section in **create training contest** page. After you send your
request, we'll create a contest for you satisfying all the filters you inserted.

Note: We generate the contests considering only the unsolved problems. For example, if you create a contest for a team, then we only
consider those problems which are not solved by any of the team members.


#### Classroom Based Training
Classroom Based Training is mainly focused on a group of contestants who want to learn and practice together under a moderator.
The person who creates the classroom becomes the moderator and has all the controls over the features like adding and removing members.

###### Classroom Features?
1. Create tasks for classroom members
2. Make class schedules
3. Compares between the skill level of the classroom members
4. Set training contests for practice
5. Classroom discussion


#### Learning Resources
Each problem and algorithm has a separate page where you can discuss about that particular problem or algorithm.
There are also some statistics and resources list that will help the contestants to improve their knowledge. You can contribute there
by sharing your knowledge and resources about that problem or algorithm.


#### Blogs
Blog is a feature where you can share your knowledge and thoughts about anything related to competitive programming.
You can also publicly discuss with each other about different problems and algorithms. The feature is still in the initial stage.
We'll improve and add more features in the blogs later on.
