from simulus import simulator

CHANNEL_NAME = "test"

def writer(sim: simulator):
    iconn = sim.attach_writer(CHANNEL_NAME)
    for _ in range(5):
        print(f"({sim.now}) put")
        iconn.put(f"data({sim.now})")
        sim.sleep(2)

def reader(sim: simulator, rank: int):
    oconn = sim.attach_reader(CHANNEL_NAME)
    for i in range(0, 10, 2):
        print(f"({sim.now}) calling get on rank={rank} time={i}")
        data, timedout = oconn.get(i)
        print(f"({sim.now}) get(rank={rank},time={i}):", data.value)
    print(f"({sim.now}) calling get on rank={rank} time={10}")
    data, timedout = oconn.get(10, timeout=3)
    print(f"({sim.now}) get(rank={rank},time=10):", data, f"timedout={timedout}")

    
sim = simulator()
sim.create_channel(CHANNEL_NAME)
sim.process(writer, sim)
sim.process(reader, sim, 1)
sim.process(reader, sim, 2)
sim.process(reader, sim, 3)
sim.run()
