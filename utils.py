import random

def randf(a,b):
    return a + (b-a)*random.random()

def bernoulli(p):
    return randf(0,1) <= p