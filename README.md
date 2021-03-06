## Dependencies

#### Python 3.6

pip install -r requrements.txt

##### Selenium

wget https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz

sudo sh -c 'tar -x geckodriver -zf geckodriver-v0.26.0-linux64.tar.gz -O > /usr/bin/geckodriver'

sudo chmod +x /usr/bin/geckodriver

rm geckodriver-v0.26.0-linux64.tar.gz

## Run Command

* For multiple thread: gunicorn -w 16 -b 0.0.0.0:5056 main:app

* For single thread: python main.py run

## Script dependencies after initialization (Directory: ./scripts)

* sh initial_setup_1.sh

* sh initial_setup_2.sh

* sh initial_setup_3.sh


## Codeflares Guidelines

Codeflares is an automated offline training platform for competitive programmers. We generate a efficient training plan
for the contestants using their problem solving history. We also provide them with some statistical data and other
features to help them completely focus on competitive training. You'll find more details about our features in the following section.

### Features & Models

1. [Algorithm Database](#algorithmdatabase)
1. [Problem Database](#problemdatabase)
1. [Problem Score](#problemscore)
1. [Individual Skill Generator](#individualskillgenerator)
1. [Individual Training Model](#individualtrainingmodel)
1. [Team Skill Generator](#teamskillgenerator)
1. [Team Training Model](#teamtrainingmodel)
1. [Rating System](#ratingsystem)
1. [Automated Training Contest Generator](#automatedtrainingcontestgenerator)
1. [Classroom Based Training](#classroombasedtraining)
1. [Learning Resources](#learningresources)
1. [Blog](#blog)

#### Algorithm Database
We have a collection of algorithms that most of the contestants use frequently in problem solving.
All these algorithms are divided into two levels. The first level is called the **root level** which contains only
the [*root level categories*](/category/list/). And the second level is called the **child level** which consists of all the algorithms.
The child level algorithms are then divided into the root level categories.

For example, some of the root level categories are: *Base Algorithms, Number Theory, Graph, Data Structure, Dynamic Programming, Geometry* etc.
1. Some second level algorithms that fall under [*Number Theory*](/category/list/root/number_theory/): *GCD, LCM, Prime Number, Sieve, Prime Factorization* etc.
1. Similarly, some second level algorithms that fall under [*Graph*](/category/list/root/graph/): *BFS, DFS, Dijkstra, Bellmanford, SCC, DAG* etc.

Most of the second level algorithms are somewhat dependent on some other second level algorithms. For example,

**Dijkstra** is dependent on Priority Queue, BFS & DFS.

**Prime Factorization** is dependent on Prime Number and Sieve. 

Based on these dependencies we have created a _**category-dependency-matrix**_. Which is basically a collection of edges from
an weighted DAG, where every edge **a -> (b, f)** in the DAG denotes that the algorithm **a** is dependent
on the algorithm **b** with a factor **f** (_in range 1 to 10_).

You'll find the problem database section in [*Gateway -> Categories*](/category/list/)


#### Problem Database
We have a rich collection of problems from different online judges and contest platforms like Codeforces, Codechef, UVa, SPOJ and LightOJ.
Each of these problems contains a connection list, which denotes how much a problem is connected to some categories.
Considering this connection list for each of the problem, we have created a _**problem-category-connection-matrix**_.

For example, some problem **X** might be connected to some algorithms **Y** with a factor **P**. Which means, to solve
the problem **X** you need to learn the algorithm **Y** upto a certain level (*depends on the factor*).

At the same time it also means that if you can solve the problem **X** then your skill in algorithm **Y** will get increased
by a factor which depends on the _problem-difficulty_ of the problem and the _factor_ of the connection.

You'll find the problem database section in [*Gateway -> Problems*](/problem/list/all/)

#### Problem Score
We have a problem score formula to calculate the score that a contestant receive after solving any problem.
After solving any problem of difficulty **d**, a contestant receive **sqrt(d)** points. So for the difficulties
**1, 2, 3, 4, 5, 6, 7, 8, 9, 10**, a contestant receive the following scores:
**1, 2.82, 5.19, 8, 11.18, 14.69, 18.52, 22.62, 27, 31.62.**

###### Why this score is important?

1. This score helps us to calculate the minimum efforts you need to put to improve your skill rating. So it
directly affects the rating progress of a contestant.
2. It also helps us to determine your skill level. Your skill level in any algorithm depends partially on the total amount of
score you received solving the problems from that particular algorithm. For example, the more difficult problem you solve from Segment Tree,
the more it increases your skill in Segment Tree, Data Structure and eventually in your total algorithm skill level.


#### Individual Skill Generator
The individual skill generator model generates your overall problem solving skill as well as your skill per each algorithm
considering your problem solving record.

##### How it works?

Considering your problem solving record, we generate your skill for each of the second level algorithms.

For any algorithm **X**, the skill of that algorithm depends on the problems that have some connections with the algorithm **X**.
Every solved problem of an user contribute to the skill of the algorithms which are connected to that algorithm.

As explained in the **Problem Database** section, for any solved problem **P**, how much it'll contribute to the skill of a algorithm,
that depends on the following two factors: **problem-difficulty** and _**problem-category-connection-matrix**_.

Using this factors for each solved problems, we generate a [*skill value*](/training/individual/#overallAlgorithmSkill) for all the second level algorithms
which are directly connected to those solved problems.

After processing the second level algorithms, then we generate the [*skill value*](/training/individual/#topicWiseSkill) for the **root level categories**
using the skill value of the algorithms that fall under that particular
root category. We have a _**algorithm-percentage-matrix**_ which stores the information of how much an algorithm contribute to the overall
skill value of a root category.

Finally we generate the **overall current skill** of an user using our _**root-algorithm-percentage-matrix**_.
Each entry of this matrix denotes how much a root category contribute to the **overall total skill** of a contestant.


#### Individual Training Model
Our individual training model is based on the algorithm skill value we generated in the previous models. Using the algorithm skill,
our training model generates a **relevant-score** for each problems and algorithms. This **relevant-score** denotes how much
a problem or algorithm is relevant for you right now considering your current problem solving skill.

Let's see an example of why this training model for the problems is really important for the contestants.

Let's say your current skill level in **Segment Tree** is somewhere between **5.5** to **6.0**.
Considering your current skill, which problems from segment tree would be more relevant for you to solve right now?
Problem having difficulty **1 - 2** will be too much easier for you, and at the same time, problem having difficulty **9 - 10** will be lot more
harder for you. So none of these problems would be actually relevant for you to solve right now if you focus on improving your skill. Rather,
problems having difficulty **5 - 7** might be more beneficial for your skill.

Similarly, let's say you want to learn **Dijkstra** algorithm right now but you don't have have much knowledge about **DFS**, **BFS**, **Basic STL** etc.
So trying to learn Dijkstra right now would be a really bad idea. Instead, your focus should be more on solving problems from **DFS**, **BFS** and
**Basic STL** first and after gaining a moderate skill in those algorithms, then you can focus on **Dijkstra** algorithm.

Our training model evaluates your relevant score considering your current skill level in each of the algorithms. It is
built in a way so that, if you continue solving problems and focus on learning the algorithms following this models,
your skill will gradually increase in those algorithms.

In the individual training model page, we suggest the top **10** problems and algorithms for you to approach in the upcoming week.
If you don't like a problem or if you think you have already solve a similar problem before, then you have the option to
move it to **blacklist** or you can **flag** it temporarily for 3 days. Of course, you have the option to undo this operations
from the [*tasklist*](/flagged/problem/list/) on the top bar if you feel like trying the problem again later on.

Individual Training Model can be found from [*Training -> Personal Training*](/training/individual/)

#### Team Skill Generator
Our team skill generator model is similar to the Individual Skill Generator model. Here, we just consider all the solved problems
combined by all the team members.


#### Team Training Model
Our team training model is similar to the Individual Training Model. Here, it just considers the
algorithm skill value generated by the **Team Skill Generator** model.

To activate Team Training Model, you first need to set your current active team
from your [*User Settings*](/settings/update/).

Then you'll be able to visit your team training page from [*Training -> Team Training*](/training/team/)

#### Rating System
We have a rating system to help the contestant to keep track of their progress which gets updated exactly once
in a week (for now in every Friday). We recalculate the overall skill and total problem score of every contestants
during this update. We also set a new problem score target for next week. If any contestants fail to reach
their target in the next week, their rating gets decreased.

Let's say after week **W**, the skill of a contestant is **X**, total problem score is **Y** and next week problem score
target is **Z (Z > Y)**. Now, after week **(W+1)**, let's consider that the contestant's achieved total problem score is **P**.

Now, if **(P >= Z)**, then the rating of the contestant gets increased following our regular rating formula.
But if **(P < Z)**, then the rating of the contestant gets decreased by **sqrt(Z - P)**.

More details about the rating system and the models we used will be published later on. We are also continuously
working on improving the rating system gradually.


#### Automated Training Contest Generator
We also have a automated training contest generator for your practice. You can generate a contest for your individual practice,
team practice or even for the classroom training purposes.

##### How it works?

1. You can generate a completely automated training contest for your practice. Make a request from our
*Training Contest -> Create Training Contest* page providing the required information. We create a automated contest for
you using our **randomized algorithm model** following ACM ICPC problem structure.
2. You can also request for a customized contest adding some custom filters. For example, let's say you want a problem set where at least
**M** problems must be from ***Data Structure*** with difficulty range **(u - v)** and **N** problems from ***Graph*** with
difficulty range **(p - q)**. Add these options in the customized filter section in [*Create Training Contest*](/contest/add/) page. After you send your
request, we'll create a contest for you satisfying all the filters that you provided.

Note: We generate the contests considering only the unsolved problems. For example, if you create a contest for a team, then we only
consider those problems which are not already solved by any of the team members.


#### Classroom Based Training
Classroom Based Training is mainly focused on a group of contestants who want to learn and practice together under a moderator.
The person who creates the classroom becomes the moderator and has all the controls over the features like adding and removing members.

###### Classroom Features?
1. Create tasks for classroom members
2. Make class schedules
3. Compares between the skill level of the classroom members
4. Set training contests for practice
5. Classroom discussion

You can create your classroom from [*Classroom -> Create Classroom*](/classroom/add/)

#### Learning Resources
Each problem and algorithm has a separate page where you can discuss about that particular problem or algorithm.
There are also some statistics and resources list that will help the contestants to improve their knowledge. You can contribute there
by sharing your knowledge and resources about that problem or algorithm.

For more details, please checkout the problem page for [*Anagram Division*](/problem/view/lightoj-1158/) and
the category page for [*BFS*](/category/view/bfs/).


#### Blog
Blog is a feature where you can share your knowledge and thoughts about anything related to competitive programming.
You can also publicly discuss with each other about different problems and algorithms. The feature is still in the initial stage.
We'll improve it and add more features in the blog section later on.
