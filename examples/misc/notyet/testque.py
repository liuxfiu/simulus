from multiprocessing import Process, Queue
from collections import defaultdict

def f(q):
    q.put(1.0)
    x = defaultdict(list)
    x['a'].append(10)
    x['b'].append((5.0, 'mb2', 0, 4))
    q.put(x)

if __name__ == '__main__':
    q = Queue()
    ps = [Process(target=f, args=(q,)) for _ in range(10)]
    for p in ps: p.start()
    for _ in range(10*2):
        print(q.get())
    for p in ps:
        p.join()
