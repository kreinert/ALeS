# ALeS: Adaptive-Length Spaced-seed design

**Author:**

Arnab Mallik, Lucian Ilie  
Arnab Mallik (amallik3@uwo.ca), Lucian Ilie (ilie@uwo.ca)  
Department of Computer Science  
The University of Western Ontario, London, Ontario, Canada

**Description:**

Similarity search is one of the most critical challenges in bioinformatics. It is time and memory intensive, hence heuristic methods using multiple spaced seeds are commonly employed. A spaced seed is a string of matches interspersed with don’t care positions. Sensitivity, the probability of hitting a similarity region, is used to evaluate their quality. High sensitivity increases the probability of detecting more remote homologs.

We present ALeS: Adaptive-length spaced-seed design, a software program to generate highly sensitivity seeds. It uses two novel optimization techniques: indel optimization and adaptive length. In indel optimization, a random don’t care position is either inserted or deleted, following the hill-climbing approach with sensitivity as cost-function. In the adaptive length algorithm, the seed lengths are modified using previously found good seeds. It consistently outperforms all leading programs used for designing multiple spaced seeds like Rasbhari, AcoSeeD, SpEED, and Iedera.

ALeS will benefit numerous software programs in a variety of areas, including traditional ones, such as PatternHunter for similarity search, SHRiMP and BFAST for read mapping, bestPrimer for designing primers, as well as emerging topics, including alignment-free comparisons and evolutionary distance programs, such as protSpaM, MultiSpaM for phylogeny reconstruction.

**Installation:**

A C++ compiler is required. Download the repository, enter the ALeS directory, and build with **make**:

```
make ALeS    # original adaptive-length designer (ALeS.cpp)
make ALeSc   # core-constrained designer (ALeSc.cpp; OpenMP if available)
```

On macOS, `make ALeSc` uses Homebrew `libomp` when it is installed (`brew install libomp`). Set `OMP_NUM_THREADS` to control the number of restart threads.

**How to run ALeS:**

ALeS accepts 4 arguments by default. Since the v_1.5 release, ALeS can accept an optional fifth argument which corresponds to the maximum seed length allowed.
Use the command format as shown:

```
./ALeS <weight_of_seed> <number_of_seeds> <similarity> <region_length> [<seed_length_upperBound>]
```
For example,
```
./ALeS 10 4 .75 50
```
This will generate 4 spaced seeds, each of weight 10 having similarity level of 0.75 for region length 50.

```
./ALeS 10 4 .75 50 20
```
This will generate 4 spaced seeds, each of weight 10 having similarity level of 0.75 for region length 50 and the seeds can have a maximum length of 20. The last argument is optional.

```
<weight> : Number of match positions in each seed
<numberOfSeeds> : Number of seeds
<similarity> : Similarity level
<lengthOfHomologyRegion> : Length of homologous region
<seed_length_upperBound> [optional] : Seed length upper bound
```

**Output:**

The software produces multiple spaced seeds as output along with its sensitivity value.
For the command shown above, a sample ALeS output would be: 
```
1111010110111  
1110100110001111  
1110101000100100111  
110110000100001000101011  
Real sensitivity = 0.90968
```

**ALeSc (required *m*-core):**

`ALeSc` is the same sensitivity-based designer with one extra constraint: every shape must contain at least `corelength` consecutive match positions (`1`s). That *m*-core is kept during search. Seed weight, optional length upper bound, and the Li et al. multiple-seed sensitivity DP are unchanged.

```
./ALeSc <weight> <numberOfSeeds> <similarity> <region_length> <corelength> [<upperBound>] [<symmetryFlag>] [frozenSeeds...]
```

Example (weight 31, two seeds, similarity 0.90, homology length 100, core 19, length at most 39, score each seed with its reverse):

```
./ALeSc 31 2 0.90 100 19 39 1
```

```
<weight>            : Number of match positions in each seed
<numberOfSeeds>     : Number of designed seeds (k)
<similarity>        : Similarity level
<region_length>     : Length of homologous region
<corelength>        : Minimum run of consecutive 1s in every shape
<upperBound>        : Optional; maximum seed length (must be < region_length and >= weight)
<symmetryFlag>      : Optional; 1 to score and print each designed seed together with its reverse
[frozenSeeds...]    : Optional 01-strings; freeze these k-1 seeds (cores stay put) and search for the rest
```

When `k > 1` and no frozen seeds are given, ALeSc grows the set from 1 to *k*: it freezes the best *k*−1 cores, searches for the new seed, and still allows flank `1`/`0` moves on the older seeds. A final polish unfreezes all seeds.

If `<symmetryFlag>` is `1` (reverse-doubling), every sensitivity evaluation uses the *k* designed seeds plus their reverses (2*k* shapes in the DP). Overlap-complexity uses that same doubled set. Designing *k* seeds this way matches designing 2*k* seeds without doubling on the grids we ran (`w=31`, `p=0.90`, `N=100`, length bound 39).

After an improving batch, ALeSc tries small core slides (the extra `1`s stay put when they remain outside the new core) and a greedy climb of the flanks.

**Cite:**

@article{10.1093/bioinformatics/btaa945,
    author = {Mallik, Arnab and Ilie, Lucian},    
    title = "{ALeS: adaptive-length spaced-seed design}",    
    journal = {Bioinformatics},    
    volume = {37},    
    number = {9},    
    pages = {1206-1210},    
    year = {2020},    
    month = {12},    
    abstract = "{Sequence similarity is the most frequently used procedure in biological research, as proved by the widely used BLAST program. The consecutive seed used by BLAST can be dramatically improved by considering multiple spaced seeds. Finding the best seeds is a hard problem and much effort went into developing heuristic algorithms and software for designing highly sensitive spaced seeds.We introduce a new algorithm and software, ALeS, that produces more sensitive seeds than the current state-of-the-art programs, as shown by extensive testing. We also accurately estimate the sensitivity of a seed, enabling its computation for arbitrary seeds.The source code is freely available at github.com/lucian-ilie/ALeS.Supplementary data are available at Bioinformatics online.}",    
    issn = {1367-4803},    
    doi = {10.1093/bioinformatics/btaa945},    
    url = {https://doi.org/10.1093/bioinformatics/btaa945},    
    eprint = {https://academic.oup.com/bioinformatics/article-pdf/37/9/1206/38575185/btaa945\_supplementary\_data.pdf},
}

**View Poster:**

https://f1000research.com/posters/9-838 
