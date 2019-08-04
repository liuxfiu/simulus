from mpi4py import MPI

comm_rank = MPI.COMM_WORLD.Get_rank()
comm_size = MPI.COMM_WORLD.Get_size()
print("running with mpi: comm_size=%d, comm_rank=%d" %
      (comm_size, comm_rank))

if comm_rank == 0:
    v = 10
    adict = {
        'name0' : 0,
        'name1' : 1,
        'long name 2' : 2,
        'long long name 3' : 3
    }
    toall = [
        [1, 2, 3],
        [4, 5],
        [{6:7}],
    ]
else:
    v = 2
    adict = {
        'onename' : 0,
        'two names' : 1,
    }
    toall = [
        [1],
        None,
        [3]
    ]
    
   
#ret = MPI.COMM_WORLD.allgather(adict)
#print("%d/%d=>%r" % (comm_rank, comm_size, ret))

#ret = MPI.COMM_WORLD.allreduce(v, min)
#print("%d/%d=>%r" % (comm_rank, comm_size, ret))


ret = MPI.COMM_WORLD.alltoall(toall)
print("%d/%d=>%r" % (comm_rank, comm_size, ret))
f = [item for sublist in ret if sublist is not None for item in sublist]
print("%d/%d=>%r" % (comm_rank, comm_size, f))
