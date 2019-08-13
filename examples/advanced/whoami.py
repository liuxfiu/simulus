import simulus

rank = simulus.sync.comm_rank()
psize = simulus.sync.comm_size()

print('rank=%d, psize=%d' % (rank, psize))
