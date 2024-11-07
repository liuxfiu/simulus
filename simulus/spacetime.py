from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from .mailbox import Mailbox
from .pqdict import _PQDict_
import uuid

if TYPE_CHECKING:
    from simulus import simulator

class _ChannelData_:
    """
    The data structure that a channel will store
    """
    def __init__(self, value, time: int):
        self.value = value
        self.time = time
    
    def __lt__(self, other):
        return self.time < other.time

@dataclass
class _Channel_Read_Request_:
    origin_mb_name: str
    time: int | None = None
    timeout: int | None = None

@dataclass
class _Channel_Write_Request_:
    value: Any
    time: int

@dataclass
class _Channel_Read_Response_:
    data: _ChannelData_ | None
    timedout: bool = False

def channel_name_to_mb_name(channel_name: str):
    return f"STM_Channel_{channel_name}"

class _Channel_:
    """
    A STM channel, which is a data structure that holds timestamped data
    """
    def __init__(self, sim: "simulator", channel_name: str):
        self.sim = sim
        self.pqueue = _PQDict_()
        # requests that are waiting for data
        self.pending_requests: dict[int, list[_Channel_Read_Request_]] = {}
        # requests_mb is a sort of request queue
        self.requests_mb = self.sim.mailbox(channel_name_to_mb_name(channel_name))
        # start listening for requests
        self.requests_mb.add_callback(self.handle_request)
    
    def __contains__(self, time: int):
        return time in self.pqueue
    
    def __getitem__(self, time: int) -> _ChannelData_:
        return self.pqueue[time]
    
    def handle_request(self):
        req: Any | None = self.requests_mb.retrieve(isall=False)
        if not req:
            return
        if isinstance(req, _Channel_Read_Request_):
            self.handle_read_request(req)
        elif isinstance(req, _Channel_Write_Request_):
            self.handle_write_request(req)
        else:
            print("recieved invalid request")
            return
    
    def handle_read_request(self, req: _Channel_Read_Request_):
        if not req.time:
            self.respond_to_read_request(req, _Channel_Read_Response_(self.peek_min()))
            return
        # todo: do not allow gets for a time below a certain horizon (use sync group?)
        if req.time not in self:
            if req.time not in self.pending_requests:
                self.pending_requests[req.time] = []
            self.pending_requests[req.time].append(req)
            if req.timeout:
                self.sim.sched(self.create_timeout_handler(req), offset=req.timeout)
            return
        self.respond_to_read_request(req, _Channel_Read_Response_(self[req.time]))

    def respond_to_read_request(self, req: _Channel_Read_Request_, res: _Channel_Read_Response_):
        if req.origin_mb_name in self.sim._mailboxes:
            mb = self.sim._mailboxes[req.origin_mb_name]
            mb.send(res)
        else:
            raise NotImplementedError("STM across simulators not implemented yet")

    def handle_write_request(self, req: _Channel_Write_Request_):
        if req.time < 0:
            print("recieved invalid request")
            return
        # todo: do not allow writes in the synchronized past
        self.insert(req.value, req.time)
    
    def create_timeout_handler(self, req: _Channel_Read_Request_):
        def handle_timeout():
            if req.time in self.pending_requests and req in self.pending_requests[req.time]:
                self.pending_requests[req.time].remove(req)
                self.respond_to_read_request(req, _Channel_Read_Response_(None, timedout=True))
        return handle_timeout
    
    def insert(self, value, time: int):
        data = _ChannelData_(value, time)
        self.pqueue[time] = data
        if time in self.pending_requests:
            reqs = self.pending_requests.pop(time)
            for req in reqs:
                self.respond_to_read_request(req, _Channel_Read_Response_(data))

    def peek_min(self) -> _ChannelData_:
        _, data = self.pqueue.peek()
        return data

class _Connection_:
    """
    Encapsulates shared connection logic for a STM channel
    """

    def __init__(self, sim: "simulator", chan: str):
        self._sim = sim
        self._chan = chan
        self.channel_mb_name = channel_name_to_mb_name(chan)

class _ConnReader(_Connection_):
    def get(self, time: int | None = None, timeout: int | None = None) -> tuple[Any, bool]:
        "Reads the channel for data at a given time"
        if self.channel_mb_name not in self._sim._mailboxes:
            raise NotImplementedError("STM across simulators not implemented yet")
        dst_mb = self._sim._mailboxes[self.channel_mb_name]

        # todo: determine whether a one-off mailbox is good
        mb_name = uuid.uuid4()
        mb: Mailbox = self._sim.mailbox(mb_name)

        req = _Channel_Read_Request_(mb_name, time, timeout)
        dst_mb.send(req)
        
        res = mb.recv(isall=False)

        # todo: delete/cleanup mailbox
        return res.data, res.timedout
    
    def consume(self, time: int):
        "Mark a value in the channel as consumed by this connection"
        raise NotImplementedError("STM garbage collection not implemented yet")


class _ConnWriter(_Connection_):
    def put(self, value, time: int | None = None):
        "Places 'value' as the channel's data at 'time'"
        now = self._sim.now
        if time == None:
            assert isinstance(now, (int, float))
            time = int(now)
        assert time >= now

        if self.channel_mb_name not in self._sim._mailboxes:
            raise NotImplementedError("STM across simulators not implemented yet")

        dst_mb = self._sim._mailboxes[self.channel_mb_name]
        dst_mb.send(_Channel_Write_Request_(value, time))
